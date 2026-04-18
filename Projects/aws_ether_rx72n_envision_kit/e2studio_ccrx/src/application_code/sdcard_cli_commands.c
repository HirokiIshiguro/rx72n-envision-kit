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
#include <stdlib.h>

#include "FreeRTOS.h"
#include "FreeRTOS_CLI.h"

#include "ff.h"
#include "AppWizard.h"

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
    "  sdcard mount                       Mount SD card (drive 0:)\r\n"
    "  sdcard ls <path>                   List directory entries\r\n"
    "  sdcard cat <path>                  Dump file contents (hex + ascii)\r\n"
    "  sdcard write_open <path>           Open file for sequential write\r\n"
    "  sdcard write_chunk <base64>        Append base64-decoded chunk to open file\r\n"
    "  sdcard write_close                 Close write file (returns total bytes)\r\n",
    prvSdcardCommand,
    -1  /* variable args */
};

/* `touch <hex_id>` — Phase 8b 第3次 段階5-4b (#54) AppWizard event 注入 */
static BaseType_t prvTouchCommand( char * pcWriteBuffer,
                                   size_t xWriteBufferLen,
                                   const char * pcCommandString );
static const CLI_Command_Definition_t xTouchCommand =
{
    "touch",
    "\r\ntouch <hex_id>:\r\n"
    "  Inject AppWizard event by setting Var(<hex_id>) = 1.\r\n"
    "  Use to trigger ID_SCREEN_00 -> ID_SCREEN_01 transition or screen buttons.\r\n",
    prvTouchCommand,
    1  /* exactly one parameter */
};

void vRegisterSdcardCLICommands( void );

/**********************************************************************************************************************
 * Function Name: vRegisterSdcardCLICommands
 * Description  : main_task から呼出。FreeRTOS-Plus-CLI に sdcard / touch コマンドを登録する。
 *********************************************************************************************************************/
void vRegisterSdcardCLICommands( void )
{
    FreeRTOS_CLIRegisterCommand( &xSdcardCommand );
    FreeRTOS_CLIRegisterCommand( &xTouchCommand );
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

/* ===== sdcard write_open / write_chunk / write_close ===== */
/* Phase 8b 第3次 段階5-4b (#54): line-oriented base64 write protocol.
 * Legacy aws_demos の `sdcard write <filename> <size>` は raw binary 転送だったが、
 * FreeRTOS-Plus-CLI は line-oriented のため簡易化。バイナリ生転送 (READY/W/DONE 互換)
 * は build green 後の follow-up で検討。 */

static FIL        s_write_fp;
static BaseType_t s_write_open = pdFALSE;
static uint32_t   s_write_total = 0U;

/* Inline base64 decoder (RFC4648 standard alphabet, ignore whitespace).
 * Returns decoded byte count, or -1 on invalid char. Output buffer must be >= (input_len * 3 / 4). */
static int prvBase64Decode( const char * pcIn, int xInLen, uint8_t * pOut, int xOutCap )
{
    static const int8_t map[ 256 ] = {
        ['A']= 0,['B']= 1,['C']= 2,['D']= 3,['E']= 4,['F']= 5,['G']= 6,['H']= 7,['I']= 8,['J']= 9,
        ['K']=10,['L']=11,['M']=12,['N']=13,['O']=14,['P']=15,['Q']=16,['R']=17,['S']=18,['T']=19,
        ['U']=20,['V']=21,['W']=22,['X']=23,['Y']=24,['Z']=25,
        ['a']=26,['b']=27,['c']=28,['d']=29,['e']=30,['f']=31,['g']=32,['h']=33,['i']=34,['j']=35,
        ['k']=36,['l']=37,['m']=38,['n']=39,['o']=40,['p']=41,['q']=42,['r']=43,['s']=44,['t']=45,
        ['u']=46,['v']=47,['w']=48,['x']=49,['y']=50,['z']=51,
        ['0']=52,['1']=53,['2']=54,['3']=55,['4']=56,['5']=57,['6']=58,['7']=59,['8']=60,['9']=61,
        ['+']=62,['/']=63
    };
    int  i, out_count = 0;
    int  buf = 0, buf_bits = 0;

    for( i = 0; i < xInLen; i++ )
    {
        char c = pcIn[ i ];
        if( ( c == ' ' ) || ( c == '\t' ) || ( c == '\r' ) || ( c == '\n' ) ) { continue; }
        if( c == '=' ) { break; }
        if( ( ( unsigned char ) c >= sizeof( map ) ) || ( ( map[ ( unsigned char ) c ] == 0 ) && ( c != 'A' ) ) )
        {
            return -1;
        }
        buf = ( buf << 6 ) | map[ ( unsigned char ) c ];
        buf_bits += 6;
        if( buf_bits >= 8 )
        {
            buf_bits -= 8;
            if( out_count >= xOutCap ) { return -1; }
            pOut[ out_count++ ] = ( uint8_t )( ( buf >> buf_bits ) & 0xFF );
        }
    }
    return out_count;
}

static BaseType_t prvDoWriteOpen( const char * pcPath, char * pcWriteBuffer, size_t xWriteBufferLen )
{
    FRESULT fr;

    if( s_mounted != pdTRUE )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen, "sdcard: not mounted.\r\n" );
        return pdFALSE;
    }
    if( s_write_open == pdTRUE )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen, "sdcard: write already open. Run 'sdcard write_close' first.\r\n" );
        return pdFALSE;
    }
    fr = f_open( &s_write_fp, pcPath, FA_WRITE | FA_CREATE_ALWAYS );
    if( fr != FR_OK )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen, "sdcard: write_open(%s) failed (FRESULT=%d)\r\n", pcPath, ( int ) fr );
        return pdFALSE;
    }
    s_write_open = pdTRUE;
    s_write_total = 0U;
    prvBufPrintf( pcWriteBuffer, xWriteBufferLen, "sdcard: write_open OK (%s). Send chunks via 'sdcard write_chunk <base64>'.\r\n", pcPath );
    return pdFALSE;
}

static BaseType_t prvDoWriteChunk( const char * pcB64, int xB64Len, char * pcWriteBuffer, size_t xWriteBufferLen )
{
    uint8_t  decoded[ 192 ];   /* 256 base64 chars -> 192 raw bytes max */
    int      decoded_len;
    UINT     bw = 0U;
    FRESULT  fr;

    if( s_write_open != pdTRUE )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen, "sdcard: write not open. Run 'sdcard write_open <path>' first.\r\n" );
        return pdFALSE;
    }
    decoded_len = prvBase64Decode( pcB64, xB64Len, decoded, ( int ) sizeof( decoded ) );
    if( decoded_len < 0 )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen, "sdcard: write_chunk base64 decode error or chunk too large (max 192 raw bytes).\r\n" );
        return pdFALSE;
    }
    fr = f_write( &s_write_fp, decoded, ( UINT ) decoded_len, &bw );
    if( ( fr != FR_OK ) || ( ( int ) bw != decoded_len ) )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen, "sdcard: write_chunk f_write failed (FRESULT=%d, bw=%u/%d)\r\n", ( int ) fr, ( unsigned int ) bw, decoded_len );
        return pdFALSE;
    }
    s_write_total += ( uint32_t ) bw;
    prvBufPrintf( pcWriteBuffer, xWriteBufferLen, "sdcard: W %lu\r\n", ( unsigned long ) s_write_total );
    return pdFALSE;
}

static BaseType_t prvDoWriteClose( char * pcWriteBuffer, size_t xWriteBufferLen )
{
    FRESULT fr;
    uint32_t total = s_write_total;

    if( s_write_open != pdTRUE )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen, "sdcard: no write in progress.\r\n" );
        return pdFALSE;
    }
    fr = f_close( &s_write_fp );
    s_write_open = pdFALSE;
    s_write_total = 0U;
    if( fr != FR_OK )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen, "sdcard: write_close failed (FRESULT=%d)\r\n", ( int ) fr );
        return pdFALSE;
    }
    prvBufPrintf( pcWriteBuffer, xWriteBufferLen, "sdcard: DONE %lu\r\n", ( unsigned long ) total );
    return pdFALSE;
}

/* ===== touch <hex_id> ===== */
/* Phase 8b 第3次 段階5-4b (#54): AppWizard event 注入 */
static BaseType_t prvTouchCommand( char * pcWriteBuffer,
                                   size_t xWriteBufferLen,
                                   const char * pcCommandString )
{
    const char * pcArg;
    BaseType_t   xArgLen;
    char         id_buf[ 16 ];
    uint32_t     id;
    int          ret;

    if( pcWriteBuffer != NULL )
    {
        pcWriteBuffer[ 0 ] = '\0';
    }

    pcArg = FreeRTOS_CLIGetParameter( pcCommandString, 1, &xArgLen );
    if( ( pcArg == NULL ) || ( xArgLen <= 0 ) )
    {
        prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                      "touch: missing <hex_id>. Usage: touch <hex_id>\r\n" );
        return pdFALSE;
    }
    if( ( size_t ) xArgLen >= sizeof( id_buf ) )
    {
        xArgLen = ( BaseType_t )( sizeof( id_buf ) - 1U );
    }
    memcpy( id_buf, pcArg, ( size_t ) xArgLen );
    id_buf[ xArgLen ] = '\0';

    /* Accept "0xNNNN" or "NNNN" (hex). */
    id = ( uint32_t ) strtoul( id_buf, NULL, 16 );

    ret = APPW_SetVarData( ( uint16_t ) id, 1 );
    prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                  "touch: APPW_SetVarData(0x%04lX, 1) -> %d\r\n",
                  ( unsigned long ) id, ret );
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

    /* Phase 8b 第3次 段階5-4b (#54): line-oriented base64 SD write */
    if( ( xSubcmdLen == 10 ) && ( strncmp( pcSubcmd, "write_open", 10 ) == 0 ) )
    {
        char path_buf[ 64 ];

        pcArg = FreeRTOS_CLIGetParameter( pcCommandString, 2, &xArgLen );
        if( ( pcArg == NULL ) || ( xArgLen <= 0 ) )
        {
            prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                          "sdcard: write_open needs a path. Usage: sdcard write_open <path>\r\n" );
            return pdFALSE;
        }
        if( ( size_t ) xArgLen >= sizeof( path_buf ) )
        {
            xArgLen = ( BaseType_t )( sizeof( path_buf ) - 1U );
        }
        memcpy( path_buf, pcArg, ( size_t ) xArgLen );
        path_buf[ xArgLen ] = '\0';
        return prvDoWriteOpen( path_buf, pcWriteBuffer, xWriteBufferLen );
    }

    if( ( xSubcmdLen == 11 ) && ( strncmp( pcSubcmd, "write_chunk", 11 ) == 0 ) )
    {
        pcArg = FreeRTOS_CLIGetParameter( pcCommandString, 2, &xArgLen );
        if( ( pcArg == NULL ) || ( xArgLen <= 0 ) )
        {
            prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                          "sdcard: write_chunk needs base64 data.\r\n" );
            return pdFALSE;
        }
        return prvDoWriteChunk( pcArg, ( int ) xArgLen, pcWriteBuffer, xWriteBufferLen );
    }

    if( ( xSubcmdLen == 11 ) && ( strncmp( pcSubcmd, "write_close", 11 ) == 0 ) )
    {
        return prvDoWriteClose( pcWriteBuffer, xWriteBufferLen );
    }

    prvBufPrintf( pcWriteBuffer, xWriteBufferLen,
                  "sdcard: unknown subcommand '%.*s'. Try mount|ls|cat|write_open|write_chunk|write_close.\r\n",
                  ( int ) xSubcmdLen, pcSubcmd );
    return pdFALSE;
}
