/**********************************************************************************************************************
 * File Name    : r_tfat_lib.h
 * Description  : Phase 8b 第3次 段階5-4c-2 (rx72n-envision-kit#56) shim.
 *                Legacy aws_demos の `firm_update.c` は `r_tfat_lib.h` の `R_tfat_f_*` ラッパー API
 *                と `TFAT_FA_*` / `TFAT_FR_*` 定数群を使うが、v3 baseline (iot-reference-rx の r_tfat_rx)
 *                には同名ヘッダが存在しない。本 shim は legacy API を v3 ff.h (FatFs R0.15) 直接 API へ
 *                マッピングして firm_update.c の include 解決と動作互換を提供する。
 *
 *                - TFAT_FA_*, TFAT_FR_* 定数 → ff.h の FA_*, FR_* に macro alias
 *                - R_tfat_f_open/close/lseek/read/write → ff.h の f_open 等を呼ぶ inline wrapper
 *                  (型不一致 safe: legacy uint16_t* br を v3 UINT* br に経由バッファで橋渡し)
 *********************************************************************************************************************/

#ifndef R_TFAT_LIB_H_SHIM
#define R_TFAT_LIB_H_SHIM

#include <stdint.h>
#include "ff.h"

/* ===== File access mode flags (legacy TFAT_FA_* → ff.h FA_*) ===== */
#define TFAT_FA_OPEN_EXISTING   FA_OPEN_EXISTING
#define TFAT_FA_READ            FA_READ
#define TFAT_FA_WRITE           FA_WRITE
#define TFAT_FA_CREATE_NEW      FA_CREATE_NEW
#define TFAT_FA_CREATE_ALWAYS   FA_CREATE_ALWAYS
#define TFAT_FA_OPEN_ALWAYS     FA_OPEN_ALWAYS

/* ===== File attribute (legacy TFAT_AM_* → ff.h AM_*) ===== */
#define TFAT_AM_RDO             AM_RDO
#define TFAT_AM_HID             AM_HID
#define TFAT_AM_SYS             AM_SYS
#define TFAT_AM_DIR             AM_DIR
#define TFAT_AM_ARC             AM_ARC

/* ===== FRESULT 定数 (legacy TFAT_FR_* → ff.h FR_*) ===== */
#define TFAT_FR_OK                  FR_OK
#define TFAT_FR_DISK_ERR            FR_DISK_ERR
#define TFAT_FR_INT_ERR             FR_INT_ERR
#define TFAT_FR_NOT_READY           FR_NOT_READY
#define TFAT_FR_NO_FILE             FR_NO_FILE
#define TFAT_FR_NO_PATH             FR_NO_PATH
#define TFAT_FR_INVALID_NAME        FR_INVALID_NAME
#define TFAT_FR_DENIED              FR_DENIED
#define TFAT_FR_EXIST               FR_EXIST
#define TFAT_FR_INVALID_OBJECT      FR_INVALID_OBJECT
#define TFAT_FR_WRITE_PROTECTED     FR_WRITE_PROTECTED
#define TFAT_FR_INVALID_DRIVE       FR_INVALID_DRIVE
#define TFAT_FR_NOT_ENABLED         FR_NOT_ENABLED
#define TFAT_FR_NO_FILESYSTEM       FR_NO_FILESYSTEM
#define TFAT_FR_MKFS_ABORTED        FR_MKFS_ABORTED
#define TFAT_FR_TIMEOUT             FR_TIMEOUT
#define TFAT_FR_LOCKED              FR_LOCKED
#define TFAT_FR_NOT_ENOUGH_CORE     FR_NOT_ENOUGH_CORE
#define TFAT_FR_TOO_MANY_OPEN_FILES FR_TOO_MANY_OPEN_FILES
#define TFAT_FR_INVALID_PARAMETER   FR_INVALID_PARAMETER

/* ===== Disk I/O result (legacy TFAT_RES_*) ===== */
#define TFAT_RES_OK             0
#define TFAT_RES_ERROR          1
#define TFAT_RES_WRPRT          2
#define TFAT_RES_NOTRDY         3
#define TFAT_RES_PARERR         4

/* ===== Drive number (legacy TFAT_DRIVE_NUM_0) ===== */
#define TFAT_DRIVE_NUM_0        0

/* ===== Function wrappers ===== */
/* legacy R_tfat_f_open(FIL*, const char*, uint8_t)  → ff.h f_open(FIL*, const TCHAR*, BYTE) */
static inline FRESULT R_tfat_f_open( FIL * fp, const char * path, uint8_t mode )
{
    return f_open( fp, path, ( BYTE ) mode );
}

/* legacy R_tfat_f_close(FIL*) */
static inline FRESULT R_tfat_f_close( FIL * fp )
{
    return f_close( fp );
}

/* legacy R_tfat_f_lseek(FIL*, uint32_t)  → ff.h f_lseek(FIL*, FSIZE_t) */
static inline FRESULT R_tfat_f_lseek( FIL * fp, uint32_t ofs )
{
    return f_lseek( fp, ( FSIZE_t ) ofs );
}

/* legacy R_tfat_f_read(FIL*, void*, uint16_t, uint16_t*)  → ff.h f_read(FIL*, void*, UINT, UINT*)
 *  br ポインタのサイズ違いを safe に橋渡し (UINT は通常 32-bit、uint16_t* に直接書くとアライメント
 *  問題と幅オーバーフローの両方が起こり得るため経由バッファを使う)。 */
static inline FRESULT R_tfat_f_read( FIL * fp, void * buff, uint16_t btr, uint16_t * br )
{
    UINT    br_local = 0U;
    FRESULT r = f_read( fp, buff, ( UINT ) btr, &br_local );
    if( br != NULL )
    {
        *br = ( uint16_t ) br_local;
    }
    return r;
}

/* legacy R_tfat_f_write(FIL*, const void*, uint16_t, uint16_t*) */
static inline FRESULT R_tfat_f_write( FIL * fp, const void * buff, uint16_t btw, uint16_t * bw )
{
    UINT    bw_local = 0U;
    FRESULT r = f_write( fp, buff, ( UINT ) btw, &bw_local );
    if( bw != NULL )
    {
        *bw = ( uint16_t ) bw_local;
    }
    return r;
}

/* legacy R_tfat_f_mount(uint8_t drv, FATFS*) → ff.h f_mount(FATFS*, const TCHAR*, BYTE) */
static inline FRESULT R_tfat_f_mount( uint8_t drv, FATFS * fs )
{
    char path[ 4 ];
    path[ 0 ] = ( char ) ( '0' + drv );
    path[ 1 ] = ':';
    path[ 2 ] = '\0';
    return f_mount( fs, path, 1U );
}

#endif /* R_TFAT_LIB_H_SHIM */
