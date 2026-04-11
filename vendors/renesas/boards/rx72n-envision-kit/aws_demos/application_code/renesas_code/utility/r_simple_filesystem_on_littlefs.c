/***********************************************************************************************************************
* DISCLAIMER
* This software is supplied by Renesas Electronics Corporation and is only intended for use with Renesas products. No
* other uses are authorized. This software is owned by Renesas Electronics Corporation and is protected under all
* applicable laws, including copyright laws.
* THIS SOFTWARE IS PROVIDED "AS IS" AND RENESAS MAKES NO WARRANTIES REGARDING
* THIS SOFTWARE, WHETHER EXPRESS, IMPLIED OR STATUTORY, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY,
* FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. ALL SUCH WARRANTIES ARE EXPRESSLY DISCLAIMED. TO THE MAXIMUM
* EXTENT PERMITTED NOT PROHIBITED BY LAW, NEITHER RENESAS ELECTRONICS CORPORATION NOR ANY OF ITS AFFILIATED COMPANIES
* SHALL BE LIABLE FOR ANY DIRECT, INDIRECT, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES FOR ANY REASON RELATED TO THIS
* SOFTWARE, EVEN IF RENESAS OR ITS AFFILIATES HAVE BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
* Renesas reserves the right, without notice, to make changes to this software and to discontinue the availability of
* this software. By using this software, you agree to the additional terms and conditions found by accessing the
* following link:
* http://www.renesas.com/disclaimer
*
* Copyright (C) 2026 Renesas Electronics Corporation. All rights reserved.
***********************************************************************************************************************/

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "FreeRTOS.h"
#include "semphr.h"
#include "task.h"
#include "platform.h"
#include "r_flash_rx_if.h"

#include "r_simple_filesystem_on_dataflash_if.h"
#include "serial_term_uart.h"
#include "littlefs/lfs.h"

#define LITTLEFS_FLASH_READ_SIZE      ( 1U )
#define LITTLEFS_FLASH_PROGRAM_SIZE   ( 4U )
#define LITTLEFS_FLASH_BLOCK_SIZE     ( 128U )
#define LITTLEFS_FLASH_BLOCK_COUNT    ( 70U )
#define LITTLEFS_FLASH_CACHE_SIZE     ( 64U )
#define LITTLEFS_FLASH_LOOKAHEAD_SIZE ( 16U )
#define LITTLEFS_FLASH_DATA_START     ( ( uint32_t ) FLASH_DF_BLOCK_32 )
#define LITTLEFS_FLASH_OP_TIMEOUT_TICKS pdMS_TO_TICKS( 5000 )

extern flash_err_t rx72n_littlefs_flash_interrupt_config( bool state, void * pcfg );

typedef enum e_littlefs_flash_state
{
    LITTLEFS_FLASH_IDLE = 0,
    LITTLEFS_FLASH_WAIT_ERASE,
    LITTLEFS_FLASH_WAIT_WRITE,
    LITTLEFS_FLASH_ERROR
} littlefs_flash_state_t;

typedef struct sfd_cache_entry
{
    char pcLabel[ SFD_HANDLES_LABEL_MAX_LENGTH + 1 ];
    uint8_t * pucData;
    uint32_t ulDataLength;
    BaseType_t xActive;
} sfd_cache_entry_t;

static StaticSemaphore_t xSfdMutexStorage;
static StaticSemaphore_t xSfdFlashDoneStorage;
static SemaphoreHandle_t xSfdMutex = NULL;
static SemaphoreHandle_t xSfdFlashDone = NULL;

static BaseType_t xLittleFsFlashInitialized = pdFALSE;
static BaseType_t xLittleFsMounted = pdFALSE;
static littlefs_flash_state_t xLittleFsFlashState = LITTLEFS_FLASH_IDLE;

static lfs_t xLittleFs;
static uint8_t ucLittleFsReadBuffer[ LITTLEFS_FLASH_CACHE_SIZE ];
static uint8_t ucLittleFsProgBuffer[ LITTLEFS_FLASH_CACHE_SIZE ];
static uint8_t ucLittleFsLookaheadBuffer[ LITTLEFS_FLASH_LOOKAHEAD_SIZE ];
static struct lfs_config xLittleFsConfig;

static sfd_cache_entry_t xSfdCacheEntries[ SFD_OBJECT_HANDLES_NUM ];
static lfs_dir_t xScanDirectory;
static BaseType_t xScanDirectoryOpen = pdFALSE;

static void prvLittleFsFlashCallback( void * pvEvent );
static BaseType_t prvLittleFsNormalizeLabel( const uint8_t * pucLabel,
                                             uint32_t ulLabelLength,
                                             char pcNormalizedLabel[ SFD_HANDLES_LABEL_MAX_LENGTH + 1 ] );
static BaseType_t prvLittleFsEnsureInitialized( void );
static BaseType_t prvLittleFsEnsureMounted( void );
static void prvLittleFsResetScanState( void );
static SFD_HANDLE prvLittleFsLookupHandle( const char * pcLabel );
static SFD_HANDLE prvLittleFsAllocateHandle( const char * pcLabel );
static sfd_cache_entry_t * prvLittleFsHandleToEntry( SFD_HANDLE xHandle );
static BaseType_t prvLittleFsRefreshEntry( sfd_cache_entry_t * pxEntry );
static void prvLittleFsClearEntryData( sfd_cache_entry_t * pxEntry );
static uint32_t prvLittleFsMeasureAllocatedSize( void );

static int prvLittleFsRead( const struct lfs_config * pxConfig,
                            lfs_block_t xBlock,
                            lfs_off_t xOffset,
                            void * pvBuffer,
                            lfs_size_t xSize );
static int prvLittleFsProg( const struct lfs_config * pxConfig,
                            lfs_block_t xBlock,
                            lfs_off_t xOffset,
                            const void * pvBuffer,
                            lfs_size_t xSize );
static int prvLittleFsErase( const struct lfs_config * pxConfig,
                             lfs_block_t xBlock );
static int prvLittleFsSync( const struct lfs_config * pxConfig );
static void prvLittleFsDiag( const char * pcMessage );

static void prvLittleFsDiag( const char * pcMessage )
{
    uart_string_printf_immediate( pcMessage );
}

static void prvLittleFsFlashCallback( void * pvEvent )
{
    uint32_t ulEventCode = *( ( uint32_t * ) pvEvent );
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;

    if( ulEventCode == FLASH_INT_EVENT_ERASE_COMPLETE )
    {
        if( xLittleFsFlashState == LITTLEFS_FLASH_WAIT_ERASE )
        {
            xLittleFsFlashState = LITTLEFS_FLASH_IDLE;
        }
        else
        {
            xLittleFsFlashState = LITTLEFS_FLASH_ERROR;
        }
    }
    else if( ulEventCode == FLASH_INT_EVENT_WRITE_COMPLETE )
    {
        if( xLittleFsFlashState == LITTLEFS_FLASH_WAIT_WRITE )
        {
            xLittleFsFlashState = LITTLEFS_FLASH_IDLE;
        }
        else
        {
            xLittleFsFlashState = LITTLEFS_FLASH_ERROR;
        }
    }
    else
    {
        xLittleFsFlashState = LITTLEFS_FLASH_ERROR;
    }

    if( xSfdFlashDone != NULL )
    {
        xSemaphoreGiveFromISR( xSfdFlashDone, &xHigherPriorityTaskWoken );
        portYIELD_FROM_ISR( xHigherPriorityTaskWoken );
    }
}

static BaseType_t prvLittleFsNormalizeLabel( const uint8_t * pucLabel,
                                             uint32_t ulLabelLength,
                                             char pcNormalizedLabel[ SFD_HANDLES_LABEL_MAX_LENGTH + 1 ] )
{
    uint32_t ulIndex = 0;
    uint32_t ulCopyLength = 0;

    if( ( pucLabel == NULL ) || ( pcNormalizedLabel == NULL ) || ( ulLabelLength == 0U ) )
    {
        return pdFALSE;
    }

    ulCopyLength = ulLabelLength;

    if( ulCopyLength > SFD_HANDLES_LABEL_MAX_LENGTH )
    {
        ulCopyLength = SFD_HANDLES_LABEL_MAX_LENGTH;
    }

    while( ( ulIndex < ulCopyLength ) && ( pucLabel[ ulIndex ] != '\0' ) )
    {
        pcNormalizedLabel[ ulIndex ] = ( char ) pucLabel[ ulIndex ];
        ulIndex++;
    }

    pcNormalizedLabel[ ulIndex ] = '\0';

    return ( ulIndex > 0U ) ? pdTRUE : pdFALSE;
}

static BaseType_t prvLittleFsEnsureInitialized( void )
{
    flash_interrupt_config_t xInterruptConfig;
    flash_err_t xFlashErr;

    if( xLittleFsFlashInitialized == pdTRUE )
    {
        return pdTRUE;
    }

    prvLittleFsDiag( "diag: lfs flash init start\r\n" );

    xSfdMutex = xSemaphoreCreateMutexStatic( &xSfdMutexStorage );
    xSfdFlashDone = xSemaphoreCreateBinaryStatic( &xSfdFlashDoneStorage );

    if( ( xSfdMutex == NULL ) || ( xSfdFlashDone == NULL ) )
    {
        prvLittleFsDiag( "diag: lfs flash sem create failed\r\n" );
        return pdFALSE;
    }

    prvLittleFsDiag( "diag: lfs flash sem create ok\r\n" );

    prvLittleFsDiag( "diag: lfs flash open start\r\n" );
    xFlashErr = R_FLASH_Open();

    if( ( xFlashErr != FLASH_SUCCESS ) && ( xFlashErr != FLASH_ERR_ALREADY_OPEN ) )
    {
        prvLittleFsDiag( "diag: lfs flash open failed\r\n" );
        return pdFALSE;
    }

    prvLittleFsDiag( "diag: lfs flash open ok\r\n" );

    xInterruptConfig.pcallback = prvLittleFsFlashCallback;
    xInterruptConfig.int_priority = 14;
    prvLittleFsDiag( "diag: lfs callback set start\r\n" );
    rx72n_littlefs_flash_interrupt_config( true, &xInterruptConfig );
    prvLittleFsDiag( "diag: lfs callback set ok\r\n" );

    memset( &xLittleFsConfig, 0, sizeof( xLittleFsConfig ) );
    xLittleFsConfig.context = NULL;
    xLittleFsConfig.read = prvLittleFsRead;
    xLittleFsConfig.prog = prvLittleFsProg;
    xLittleFsConfig.erase = prvLittleFsErase;
    xLittleFsConfig.sync = prvLittleFsSync;
    xLittleFsConfig.read_size = LITTLEFS_FLASH_READ_SIZE;
    xLittleFsConfig.prog_size = LITTLEFS_FLASH_PROGRAM_SIZE;
    xLittleFsConfig.block_size = LITTLEFS_FLASH_BLOCK_SIZE;
    xLittleFsConfig.block_count = LITTLEFS_FLASH_BLOCK_COUNT;
    xLittleFsConfig.block_cycles = 1024;
    xLittleFsConfig.cache_size = LITTLEFS_FLASH_CACHE_SIZE;
    xLittleFsConfig.lookahead_size = LITTLEFS_FLASH_LOOKAHEAD_SIZE;
    xLittleFsConfig.read_buffer = ucLittleFsReadBuffer;
    xLittleFsConfig.prog_buffer = ucLittleFsProgBuffer;
    xLittleFsConfig.lookahead_buffer = ucLittleFsLookaheadBuffer;

    xLittleFsFlashInitialized = pdTRUE;
    prvLittleFsDiag( "diag: lfs flash init ok\r\n" );
    return pdTRUE;
}

static BaseType_t prvLittleFsEnsureMounted( void )
{
    int lfs_err;

    if( prvLittleFsEnsureInitialized() != pdTRUE )
    {
        return pdFALSE;
    }

    if( xLittleFsMounted == pdTRUE )
    {
        return pdTRUE;
    }

    prvLittleFsDiag( "diag: lfs mount start\r\n" );

    lfs_err = lfs_mount( &xLittleFs, &xLittleFsConfig );

    if( lfs_err != LFS_ERR_OK )
    {
        prvLittleFsDiag( "diag: lfs mount failed, formatting\r\n" );
        lfs_err = lfs_format( &xLittleFs, &xLittleFsConfig );

        if( lfs_err == LFS_ERR_OK )
        {
            prvLittleFsDiag( "diag: lfs format ok, remounting\r\n" );
            lfs_err = lfs_mount( &xLittleFs, &xLittleFsConfig );
        }
    }

    if( lfs_err != LFS_ERR_OK )
    {
        prvLittleFsDiag( "diag: lfs mount failed final\r\n" );
        return pdFALSE;
    }

    xLittleFsMounted = pdTRUE;
    prvLittleFsDiag( "diag: lfs mount ok\r\n" );
    return pdTRUE;
}

static void prvLittleFsResetScanState( void )
{
    if( xScanDirectoryOpen == pdTRUE )
    {
        ( void ) lfs_dir_close( &xLittleFs, &xScanDirectory );
        xScanDirectoryOpen = pdFALSE;
    }
}

static SFD_HANDLE prvLittleFsLookupHandle( const char * pcLabel )
{
    uint32_t ulIndex;

    for( ulIndex = 0; ulIndex < SFD_OBJECT_HANDLES_NUM; ulIndex++ )
    {
        if( ( xSfdCacheEntries[ ulIndex ].xActive == pdTRUE ) &&
            ( strcmp( xSfdCacheEntries[ ulIndex ].pcLabel, pcLabel ) == 0 ) )
        {
            return ( SFD_HANDLE ) ( ulIndex + 1U );
        }
    }

    return SFD_HANDLE_INVALID;
}

static SFD_HANDLE prvLittleFsAllocateHandle( const char * pcLabel )
{
    uint32_t ulIndex;

    for( ulIndex = 0; ulIndex < SFD_OBJECT_HANDLES_NUM; ulIndex++ )
    {
        if( xSfdCacheEntries[ ulIndex ].xActive != pdTRUE )
        {
            memset( &xSfdCacheEntries[ ulIndex ], 0, sizeof( xSfdCacheEntries[ ulIndex ] ) );
            strncpy( xSfdCacheEntries[ ulIndex ].pcLabel, pcLabel, SFD_HANDLES_LABEL_MAX_LENGTH );
            xSfdCacheEntries[ ulIndex ].pcLabel[ SFD_HANDLES_LABEL_MAX_LENGTH ] = '\0';
            xSfdCacheEntries[ ulIndex ].xActive = pdTRUE;
            return ( SFD_HANDLE ) ( ulIndex + 1U );
        }
    }

    return SFD_HANDLE_INVALID;
}

static sfd_cache_entry_t * prvLittleFsHandleToEntry( SFD_HANDLE xHandle )
{
    uint32_t ulIndex = 0;

    if( ( xHandle == SFD_HANDLE_INVALID ) || ( xHandle == 0U ) )
    {
        return NULL;
    }

    ulIndex = ( uint32_t ) xHandle - 1U;

    if( ulIndex >= SFD_OBJECT_HANDLES_NUM )
    {
        return NULL;
    }

    if( xSfdCacheEntries[ ulIndex ].xActive != pdTRUE )
    {
        return NULL;
    }

    return &xSfdCacheEntries[ ulIndex ];
}

static void prvLittleFsClearEntryData( sfd_cache_entry_t * pxEntry )
{
    if( ( pxEntry != NULL ) && ( pxEntry->pucData != NULL ) )
    {
        vPortFree( pxEntry->pucData );
        pxEntry->pucData = NULL;
        pxEntry->ulDataLength = 0U;
    }
}

static BaseType_t prvLittleFsRefreshEntry( sfd_cache_entry_t * pxEntry )
{
    lfs_file_t xFile;
    lfs_soff_t lfs_size;
    lfs_ssize_t lfs_read;
    uint8_t * pucBuffer;

    if( ( pxEntry == NULL ) || ( prvLittleFsEnsureMounted() != pdTRUE ) )
    {
        return pdFALSE;
    }

    prvLittleFsClearEntryData( pxEntry );

    if( lfs_file_open( &xLittleFs, &xFile, pxEntry->pcLabel, LFS_O_RDONLY ) != LFS_ERR_OK )
    {
        return pdFALSE;
    }

    lfs_size = lfs_file_size( &xLittleFs, &xFile );

    if( lfs_size < 0 )
    {
        ( void ) lfs_file_close( &xLittleFs, &xFile );
        return pdFALSE;
    }

    pucBuffer = pvPortMalloc( ( size_t ) lfs_size + 1U );

    if( pucBuffer == NULL )
    {
        ( void ) lfs_file_close( &xLittleFs, &xFile );
        return pdFALSE;
    }

    lfs_read = lfs_file_read( &xLittleFs, &xFile, pucBuffer, ( lfs_size_t ) lfs_size );
    ( void ) lfs_file_close( &xLittleFs, &xFile );

    if( lfs_read != lfs_size )
    {
        vPortFree( pucBuffer );
        return pdFALSE;
    }

    pucBuffer[ lfs_size ] = '\0';
    pxEntry->pucData = pucBuffer;
    pxEntry->ulDataLength = ( uint32_t ) lfs_size;

    return pdTRUE;
}

static uint32_t prvLittleFsMeasureAllocatedSize( void )
{
    lfs_dir_t xDir;
    struct lfs_info xInfo;
    uint32_t ulAllocatedSize = 0U;
    int lfs_err;

    if( prvLittleFsEnsureMounted() != pdTRUE )
    {
        return 0U;
    }

    lfs_err = lfs_dir_open( &xLittleFs, &xDir, "/" );

    if( lfs_err != LFS_ERR_OK )
    {
        return 0U;
    }

    while( 1 )
    {
        lfs_err = lfs_dir_read( &xLittleFs, &xDir, &xInfo );

        if( lfs_err <= 0 )
        {
            break;
        }

        if( xInfo.type == LFS_TYPE_REG )
        {
            ulAllocatedSize += ( uint32_t ) xInfo.size;
        }
    }

    ( void ) lfs_dir_close( &xLittleFs, &xDir );
    return ulAllocatedSize;
}

static int prvLittleFsRead( const struct lfs_config * pxConfig,
                            lfs_block_t xBlock,
                            lfs_off_t xOffset,
                            void * pvBuffer,
                            lfs_size_t xSize )
{
    uint32_t ulAddress = LITTLEFS_FLASH_DATA_START +
                         ( ( uint32_t ) pxConfig->block_size * ( uint32_t ) xBlock ) +
                         ( uint32_t ) xOffset;

    ( void ) pxConfig;

    memcpy( pvBuffer, ( const void * ) ulAddress, xSize );
    return LFS_ERR_OK;
}

static int prvLittleFsProg( const struct lfs_config * pxConfig,
                            lfs_block_t xBlock,
                            lfs_off_t xOffset,
                            const void * pvBuffer,
                            lfs_size_t xSize )
{
    flash_err_t xFlashErr;
    uint32_t ulAddress = LITTLEFS_FLASH_DATA_START +
                         ( ( uint32_t ) pxConfig->block_size * ( uint32_t ) xBlock ) +
                         ( uint32_t ) xOffset;

    ( void ) pxConfig;

    xLittleFsFlashState = LITTLEFS_FLASH_WAIT_WRITE;
    xFlashErr = R_FLASH_Write( ( uint32_t ) pvBuffer, ulAddress, ( uint32_t ) xSize );

    if( xFlashErr != FLASH_SUCCESS )
    {
        xLittleFsFlashState = LITTLEFS_FLASH_ERROR;
        return LFS_ERR_IO;
    }

    if( xSemaphoreTake( xSfdFlashDone, LITTLEFS_FLASH_OP_TIMEOUT_TICKS ) != pdTRUE )
    {
        prvLittleFsDiag( "diag: lfs prog timeout\r\n" );
        xLittleFsFlashState = LITTLEFS_FLASH_ERROR;
        return LFS_ERR_IO;
    }

    return ( xLittleFsFlashState == LITTLEFS_FLASH_IDLE ) ? LFS_ERR_OK : LFS_ERR_IO;
}

static int prvLittleFsErase( const struct lfs_config * pxConfig,
                             lfs_block_t xBlock )
{
    flash_err_t xFlashErr;
    uint32_t ulAddress = LITTLEFS_FLASH_DATA_START +
                         ( ( uint32_t ) pxConfig->block_size * ( uint32_t ) xBlock );
    uint32_t ulBlocks = ( uint32_t ) pxConfig->block_size / FLASH_DF_BLOCK_SIZE;

    ( void ) pxConfig;

    xLittleFsFlashState = LITTLEFS_FLASH_WAIT_ERASE;
    xFlashErr = R_FLASH_Erase( ( flash_block_address_t ) ulAddress, ulBlocks );

    if( xFlashErr != FLASH_SUCCESS )
    {
        xLittleFsFlashState = LITTLEFS_FLASH_ERROR;
        return LFS_ERR_IO;
    }

    if( xSemaphoreTake( xSfdFlashDone, LITTLEFS_FLASH_OP_TIMEOUT_TICKS ) != pdTRUE )
    {
        prvLittleFsDiag( "diag: lfs erase timeout\r\n" );
        xLittleFsFlashState = LITTLEFS_FLASH_ERROR;
        return LFS_ERR_IO;
    }

    return ( xLittleFsFlashState == LITTLEFS_FLASH_IDLE ) ? LFS_ERR_OK : LFS_ERR_IO;
}

static int prvLittleFsSync( const struct lfs_config * pxConfig )
{
    ( void ) pxConfig;
    return LFS_ERR_OK;
}

sfd_err_t R_SFD_Open( void )
{
    prvLittleFsDiag( "diag: lfs open start\r\n" );
    if( prvLittleFsEnsureMounted() != pdTRUE )
    {
        prvLittleFsDiag( "diag: lfs open failed\r\n" );
        return SFD_FATAL_ERROR;
    }

    prvLittleFsDiag( "diag: lfs open ok\r\n" );
    return SFD_SUCCESS;
}

SFD_HANDLE R_SFD_SaveObject( uint8_t * pucLabel,
                             uint32_t ulLabelLength,
                             uint8_t * pucData,
                             uint32_t ulDataLength )
{
    char pcLabel[ SFD_HANDLES_LABEL_MAX_LENGTH + 1 ];
    SFD_HANDLE xHandle;
    sfd_cache_entry_t * pxEntry;
    lfs_file_t xFile;
    int lfs_err;

    if( ( prvLittleFsNormalizeLabel( pucLabel, ulLabelLength, pcLabel ) != pdTRUE ) ||
        ( prvLittleFsEnsureMounted() != pdTRUE ) ||
        ( pucData == NULL ) )
    {
        return SFD_HANDLE_INVALID;
    }

    R_SFD_SemaphoreTake();

    ( void ) lfs_remove( &xLittleFs, pcLabel );
    lfs_err = lfs_file_open( &xLittleFs, &xFile, pcLabel, LFS_O_WRONLY | LFS_O_TRUNC | LFS_O_CREAT );

    if( lfs_err == LFS_ERR_OK )
    {
        lfs_err = lfs_file_write( &xLittleFs, &xFile, pucData, ulDataLength );
        ( void ) lfs_file_close( &xLittleFs, &xFile );
    }

    if( lfs_err != ( int ) ulDataLength )
    {
        R_SFD_SemaphoreGive();
        return SFD_HANDLE_INVALID;
    }

    xHandle = prvLittleFsLookupHandle( pcLabel );

    if( xHandle == SFD_HANDLE_INVALID )
    {
        xHandle = prvLittleFsAllocateHandle( pcLabel );
    }

    pxEntry = prvLittleFsHandleToEntry( xHandle );

    if( pxEntry != NULL )
    {
        prvLittleFsClearEntryData( pxEntry );
        pxEntry->pucData = pvPortMalloc( ulDataLength + 1U );

        if( pxEntry->pucData != NULL )
        {
            memcpy( pxEntry->pucData, pucData, ulDataLength );
            pxEntry->pucData[ ulDataLength ] = '\0';
            pxEntry->ulDataLength = ulDataLength;
        }
    }

    R_SFD_SemaphoreGive();
    return xHandle;
}

SFD_HANDLE R_SFD_FindObject( uint8_t * pucLabel,
                             uint8_t ucLabelLength )
{
    char pcLabel[ SFD_HANDLES_LABEL_MAX_LENGTH + 1 ];
    struct lfs_info xInfo;
    SFD_HANDLE xHandle;

    if( ( prvLittleFsNormalizeLabel( pucLabel, ucLabelLength, pcLabel ) != pdTRUE ) ||
        ( prvLittleFsEnsureMounted() != pdTRUE ) )
    {
        return SFD_HANDLE_INVALID;
    }

    R_SFD_SemaphoreTake();
    xHandle = prvLittleFsLookupHandle( pcLabel );

    if( xHandle == SFD_HANDLE_INVALID )
    {
        if( lfs_stat( &xLittleFs, pcLabel, &xInfo ) == LFS_ERR_OK )
        {
            xHandle = prvLittleFsAllocateHandle( pcLabel );
        }
    }

    R_SFD_SemaphoreGive();
    return xHandle;
}

sfd_err_t R_SFD_GetObjectValue( SFD_HANDLE xHandle,
                                uint8_t ** ppucData,
                                uint32_t * pulDataLength )
{
    sfd_cache_entry_t * pxEntry;
    BaseType_t xResult;

    if( ( ppucData == NULL ) || ( pulDataLength == NULL ) || ( prvLittleFsEnsureMounted() != pdTRUE ) )
    {
        return SFD_INVALID_ARGUMENT;
    }

    R_SFD_SemaphoreTake();
    pxEntry = prvLittleFsHandleToEntry( xHandle );

    if( pxEntry == NULL )
    {
        R_SFD_SemaphoreGive();
        return SFD_INVALID_ARGUMENT;
    }

    xResult = prvLittleFsRefreshEntry( pxEntry );

    if( xResult != pdTRUE )
    {
        R_SFD_SemaphoreGive();
        return SFD_FATAL_ERROR;
    }

    *ppucData = pxEntry->pucData;
    *pulDataLength = pxEntry->ulDataLength;
    R_SFD_SemaphoreGive();

    return SFD_SUCCESS;
}

sfd_err_t R_SFD_Scan( uint8_t ** ppucLabel,
                      uint32_t * pulLabelLength,
                      uint8_t ** ppucData,
                      uint32_t * pulDataLength )
{
    struct lfs_info xInfo;
    int lfs_err;
    SFD_HANDLE xHandle;
    sfd_cache_entry_t * pxEntry;

    if( ( ppucLabel == NULL ) || ( pulLabelLength == NULL ) ||
        ( ppucData == NULL ) || ( pulDataLength == NULL ) ||
        ( prvLittleFsEnsureMounted() != pdTRUE ) )
    {
        return SFD_INVALID_ARGUMENT;
    }

    R_SFD_SemaphoreTake();

    if( xScanDirectoryOpen != pdTRUE )
    {
        lfs_err = lfs_dir_open( &xLittleFs, &xScanDirectory, "/" );

        if( lfs_err != LFS_ERR_OK )
        {
            R_SFD_SemaphoreGive();
            return SFD_FATAL_ERROR;
        }

        xScanDirectoryOpen = pdTRUE;
    }

    while( 1 )
    {
        lfs_err = lfs_dir_read( &xLittleFs, &xScanDirectory, &xInfo );

        if( lfs_err <= 0 )
        {
            prvLittleFsResetScanState();
            R_SFD_SemaphoreGive();
            return SFD_END_OF_LIST;
        }

        if( xInfo.type == LFS_TYPE_REG )
        {
            xHandle = prvLittleFsLookupHandle( xInfo.name );

            if( xHandle == SFD_HANDLE_INVALID )
            {
                xHandle = prvLittleFsAllocateHandle( xInfo.name );
            }

            pxEntry = prvLittleFsHandleToEntry( xHandle );

            if( ( pxEntry != NULL ) && ( prvLittleFsRefreshEntry( pxEntry ) == pdTRUE ) )
            {
                *ppucLabel = ( uint8_t * ) pxEntry->pcLabel;
                *pulLabelLength = ( uint32_t ) strlen( pxEntry->pcLabel );
                *ppucData = pxEntry->pucData;
                *pulDataLength = pxEntry->ulDataLength;
                R_SFD_SemaphoreGive();
                return SFD_SUCCESS;
            }
        }
    }
}

sfd_err_t R_SFD_ResetScan( void )
{
    R_SFD_SemaphoreTake();
    prvLittleFsResetScanState();
    R_SFD_SemaphoreGive();
    return SFD_SUCCESS;
}

sfd_err_t R_SFD_EraseAll( void )
{
    uint32_t ulIndex;
    int lfs_err;

    if( prvLittleFsEnsureMounted() != pdTRUE )
    {
        return SFD_FATAL_ERROR;
    }

    R_SFD_SemaphoreTake();

    prvLittleFsResetScanState();
    ( void ) lfs_unmount( &xLittleFs );
    xLittleFsMounted = pdFALSE;

    lfs_err = lfs_format( &xLittleFs, &xLittleFsConfig );

    if( lfs_err == LFS_ERR_OK )
    {
        lfs_err = lfs_mount( &xLittleFs, &xLittleFsConfig );
    }

    if( lfs_err == LFS_ERR_OK )
    {
        xLittleFsMounted = pdTRUE;
    }

    for( ulIndex = 0; ulIndex < SFD_OBJECT_HANDLES_NUM; ulIndex++ )
    {
        prvLittleFsClearEntryData( &xSfdCacheEntries[ ulIndex ] );
        memset( &xSfdCacheEntries[ ulIndex ], 0, sizeof( xSfdCacheEntries[ ulIndex ] ) );
    }

    R_SFD_SemaphoreGive();
    return ( lfs_err == LFS_ERR_OK ) ? SFD_SUCCESS : SFD_FATAL_ERROR;
}

uint32_t R_SFD_ReadPysicalSize( void )
{
    return LITTLEFS_FLASH_BLOCK_SIZE * LITTLEFS_FLASH_BLOCK_COUNT;
}

uint32_t R_SFD_ReadAllocatedStorageSize( void )
{
    return prvLittleFsMeasureAllocatedSize();
}

uint32_t R_SFD_ReadFreeSize( void )
{
    uint32_t ulPhysicalSize = R_SFD_ReadPysicalSize();
    uint32_t ulAllocatedSize = R_SFD_ReadAllocatedStorageSize();

    if( ulAllocatedSize >= ulPhysicalSize )
    {
        return 0U;
    }

    return ulPhysicalSize - ulAllocatedSize;
}

sfd_err_t R_SFD_Close( void )
{
    return SFD_SUCCESS;
}

void R_SFD_SemaphoreTake( void )
{
    if( prvLittleFsEnsureInitialized() == pdTRUE )
    {
        xSemaphoreTake( xSfdMutex, portMAX_DELAY );
    }
}

void R_SFD_SemaphoreGive( void )
{
    if( xSfdMutex != NULL )
    {
        xSemaphoreGive( xSfdMutex );
    }
}
