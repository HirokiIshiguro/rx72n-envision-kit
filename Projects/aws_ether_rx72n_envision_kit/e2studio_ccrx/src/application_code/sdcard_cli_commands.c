/**********************************************************************************************************************
 * File Name    : sdcard_cli_commands.c
 * Description  : Phase 8b 第3次 段階5-4a (rx72n-envision-kit#53): SD カード操作 CLI コマンド 3 種
 *                を v3 baseline FreeRTOS-Plus-CLI に追加する。段階5-3 (#51 / MR !88) で取り込んだ
 *                r_sdhi_rx + r_sdc_sdmem_rx + r_tfat_rx + r_tfat_driver_rx を実際に叩く最初の
 *                アプリ側コード。
 *
 *                提供コマンド:
 *                  sdcard mount         - SD カードマウント (or 状態表示)
 *                  sdcard ls <path>     - ディレクトリ列挙
 *                  sdcard cat <path>    - ファイル内容を hex+ascii で出力
 *
 *                段階5-4b で `sdcard write` (UART → SD 書き込み) を追加予定。
 *                段階5-4c で SD 上 RSU からのファームアップデート本体を実装予定。
 *********************************************************************************************************************/

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "FreeRTOS.h"
#include "FreeRTOS_CLI.h"

#include "ff.h"

/* tfat 設定: TFAT_DRIVE_ALLOC_NUM_0 = TFAT_CTRL_SDMEM (drive 0 = SD card) を r_tfat_driver_rx_config.h で設定済 */
#define SDCARD_DRIVE_PATH       "0:"
#define SDCARD_LS_BUFSIZE       ( 80 )
#define SDCARD_CAT_CHUNK        ( 64 )    /* 1 行あたりの hex dump バイト数 */

static FATFS s_fatfs;
static BaseType_t s_mounted = pdFALSE;

/* CLI command handlers */
static BaseType_t prvSdcardCommand( char * pcWriteBuffer,
                                    size_t xWriteBufferLen,
                                    const char * pcCommandString );

static const CLI_Command_Definition_t xSdcardCommand =
{
    "sdcard",
    "\r\nsdcard <subcmd> [args]:\r\n"
    "  sdcard mount         Mount SD card (drive 0:)\r\n"
    "  sdcard ls <path>     List directory entries\r\n"
    "  sdcard cat <path>    Dump file contents (hex + ascii)\r\n",
    prvSdcardCommand,
    -1  /* variable args */
};

void vRegisterSdcardCLICommands( void );

/**********************************************************************************************************************
 * Function Name: vRegisterSdcardCLICommands
 * Description  : main_task から呼出。FreeRTOS-Plus-CLI に sdcard コマンドを登録する。
 *********************************************************************************************************************/
void vRegisterSdcardCLICommands( void )
{
    FreeRTOS_CLIRegisterCommand( &xSdcardCommand );
}

/* helper: write a printf-style line into pcWriteBuffer (truncating safely) */
static void prvBufPrintf( char * pcWriteBuffer, size_t xWriteBufferLen, const char * fmt, ... )
{
    va_list ap;

    if( ( pcWriteBuffer == NULL ) || ( xWriteBufferLen == 0U ) )
    {
        return;
    }

    va_start( ap, fmt );
    ( void ) vsnprintf( pcWriteBuffer, xWriteBufferLen, fmt, ap );
    va_end( ap );

    pcWriteBuffer[ xWriteBufferLen - 1U ] = '\0';
}

static BaseType_t prvDoMount( char * pcWriteBuffer, size_t xWriteBufferLen )
{
    FRESULT fr;

    if( s_mounted == pdTRUE )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                      "sdcard: already mounted (%s)\r\n", SDCARD_DRIVE_PATH );
        return pdFALSE;
    }

    fr = f_mount( &s_fatfs, SDCARD_DRIVE_PATH, 1U );

    if( fr == FR_OK )
    {
        s_mounted = pdTRUE;
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                      "sdcard: mount OK (%s)\r\n", SDCARD_DRIVE_PATH );
    }
    else
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                      "sdcard: mount failed (FRESULT=%d)\r\n", ( int ) fr );
    }
    return pdFALSE;
}

static BaseType_t prvDoLs( const char * pcPath, char * pcWriteBuffer, size_t xWriteBufferLen )
{
    DIR     dir;
    FILINFO fno;
    FRESULT fr;
    int     written = 0;
    int     entries = 0;

    if( s_mounted != pdTRUE )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                      "sdcard: not mounted. Run 'sdcard mount' first.\r\n" );
        return pdFALSE;
    }

    fr = f_opendir( &dir, pcPath );
    if( fr != FR_OK )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                      "sdcard: opendir(%s) failed (FRESULT=%d)\r\n", pcPath, ( int ) fr );
        return pdFALSE;
    }

    written = snprintf( pcWriteBuffer, xWriteBufferLen,
                        "sdcard: ls %s\r\n", pcPath );

    for( ; ; )
    {
        fr = f_readdir( &dir, &fno );
        if( ( fr != FR_OK ) || ( fno.fname[ 0 ] == '\0' ) )
        {
            break;
        }

        if( ( ( size_t ) written + SDCARD_LS_BUFSIZE ) >= xWriteBufferLen )
        {
            written += snprintf( pcWriteBuffer + written, xWriteBufferLen - ( size_t ) written,
                                 "  ... (truncated, output too large)\r\n" );
            break;
        }

        written += snprintf( pcWriteBuffer + written, xWriteBufferLen - ( size_t ) written,
                             "  %s%-32s  %lu bytes\r\n",
                             ( fno.fattrib & AM_DIR ) ? "[DIR] " : "      ",
                             fno.fname,
                             ( unsigned long ) fno.fsize );
        entries++;
    }

    ( void ) f_closedir( &dir );

    if( ( ( size_t ) written + 64U ) < xWriteBufferLen )
    {
        ( void ) snprintf( pcWriteBuffer + written, xWriteBufferLen - ( size_t ) written,
                           "  total: %d entries\r\n", entries );
    }

    pcWriteBuffer[ xWriteBufferLen - 1U ] = '\0';
    return pdFALSE;
}

static BaseType_t prvDoCat( const char * pcPath, char * pcWriteBuffer, size_t xWriteBufferLen )
{
    FIL     fp;
    FRESULT fr;
    BYTE    chunk[ SDCARD_CAT_CHUNK ];
    UINT    br = 0U;
    int     written;
    int     i;

    if( s_mounted != pdTRUE )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                      "sdcard: not mounted. Run 'sdcard mount' first.\r\n" );
        return pdFALSE;
    }

    fr = f_open( &fp, pcPath, FA_READ );
    if( fr != FR_OK )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                      "sdcard: open(%s) failed (FRESULT=%d)\r\n", pcPath, ( int ) fr );
        return pdFALSE;
    }

    fr = f_read( &fp, chunk, sizeof( chunk ), &br );
    ( void ) f_close( &fp );

    if( fr != FR_OK )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                      "sdcard: read(%s) failed (FRESULT=%d)\r\n", pcPath, ( int ) fr );
        return pdFALSE;
    }

    /* hex dump first SDCARD_CAT_CHUNK bytes (or fewer if file smaller).
     * 段階5-4a は read 動作確認なので large file の全文 dump はしない。 */
    written = snprintf( pcWriteBuffer, xWriteBufferLen,
                        "sdcard: %s (%u bytes shown)\r\n", pcPath, ( unsigned int ) br );

    for( i = 0; ( i < ( int ) br ) && ( ( size_t ) written + 8U < xWriteBufferLen ); i++ )
    {
        if( ( i % 16 ) == 0 )
        {
            written += snprintf( pcWriteBuffer + written, xWriteBufferLen - ( size_t ) written,
                                 "\r\n  %04x: ", i );
        }
        written += snprintf( pcWriteBuffer + written, xWriteBufferLen - ( size_t ) written,
                             "%02x ", chunk[ i ] );
    }

    if( ( ( size_t ) written + 4U ) < xWriteBufferLen )
    {
        ( void ) snprintf( pcWriteBuffer + written, xWriteBufferLen - ( size_t ) written, "\r\n" );
    }

    pcWriteBuffer[ xWriteBufferLen - 1U ] = '\0';
    return pdFALSE;
}

static BaseType_t prvSdcardCommand( char * pcWriteBuffer,
                                    size_t xWriteBufferLen,
                                    const char * pcCommandString )
{
    const char * pcSubcmd;
    BaseType_t   xSubcmdLen;
    const char * pcArg;
    BaseType_t   xArgLen;

    if( pcWriteBuffer == NULL )
    {
        return pdFALSE;
    }

    pcWriteBuffer[ 0 ] = '\0';

    pcSubcmd = FreeRTOS_CLIGetParameter( pcCommandString, 1, &xSubcmdLen );
    if( pcSubcmd == NULL )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                      "sdcard: missing subcommand. Try 'sdcard mount|ls|cat'\r\n" );
        return pdFALSE;
    }

    if( ( xSubcmdLen == 5 ) && ( strncmp( pcSubcmd, "mount", 5 ) == 0 ) )
    {
        return prvDoMount( pcWriteBuffer, xWriteBufferLen );
    }

    if( ( xSubcmdLen == 2 ) && ( strncmp( pcSubcmd, "ls", 2 ) == 0 ) )
    {
        char path_buf[ 64 ];

        pcArg = FreeRTOS_CLIGetParameter( pcCommandString, 2, &xArgLen );
        if( ( pcArg == NULL ) || ( xArgLen <= 0 ) )
        {
            return prvDoLs( "0:/", pcWriteBuffer, xWriteBufferLen );
        }
        if( ( size_t ) xArgLen >= sizeof( path_buf ) )
        {
            xArgLen = ( BaseType_t )( sizeof( path_buf ) - 1U );
        }
        memcpy( path_buf, pcArg, ( size_t ) xArgLen );
        path_buf[ xArgLen ] = '\0';
        return prvDoLs( path_buf, pcWriteBuffer, xWriteBufferLen );
    }

    if( ( xSubcmdLen == 3 ) && ( strncmp( pcSubcmd, "cat", 3 ) == 0 ) )
    {
        char path_buf[ 64 ];

        pcArg = FreeRTOS_CLIGetParameter( pcCommandString, 2, &xArgLen );
        if( ( pcArg == NULL ) || ( xArgLen <= 0 ) )
        {
            prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                          "sdcard: cat needs a path. Usage: sdcard cat <path>\r\n" );
            return pdFALSE;
        }
        if( ( size_t ) xArgLen >= sizeof( path_buf ) )
        {
            xArgLen = ( BaseType_t )( sizeof( path_buf ) - 1U );
        }
        memcpy( path_buf, pcArg, ( size_t ) xArgLen );
        path_buf[ xArgLen ] = '\0';
        return prvDoCat( path_buf, pcWriteBuffer, xWriteBufferLen );
    }

    prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                  "sdcard: unknown subcommand '%.*s'. Try mount|ls|cat.\r\n",
                  ( int ) xSubcmdLen, pcSubcmd );
    return pdFALSE;
}
