/**********************************************************************************************************************
 * File Name    : rx72n_envision_kit_system.h
 * Description  : Phase 8b 第3次 段階5-1 (rx72n-envision-kit#49 / MR !86) の最小スタブ。
 *                Legacy aws_demos の同名ヘッダから AppWizard CustomCode が参照する範囲だけを抽出。
 *                依存 FIT モジュール (r_usb_basic, r_tfat_lib, r_simple_filesystem_on_dataflash,
 *                firm_update 等) は段階5-3 / 5-4 で v3 に取り込み次第、対応するフィールド更新ロジックを
 *                足していく。本ヘッダ自体は AppWizard CustomCode の再生成耐性のため CustomCode/ に同居させる。
 *********************************************************************************************************************/

#ifndef RX72N_ENVISION_KIT_SYSTEM_H
#define RX72N_ENVISION_KIT_SYSTEM_H

#include <stdint.h>
#include <stdbool.h>

#include "FreeRTOS.h"
#include "task.h"

#include "GUI.h"
#include "DIALOG.h"

#define MAX_HISTORY_FPS_INDEX           ( 300 )   /* 3 seconds average @ 100fps */
#define UNIQUE_ID_LENGTH                ( 16 )    /* bytes */
#define EMWIN_VERSION_STRING_LENGTH     ( 16 )
#define FIRMWARE_VERSION_STRING_LENGTH  ( 16 )
#define SOFTWARE_RESET_WAIT_TIME        ( 5000 )  /* ms */

/* SYS_TIME mirrors r_sys_time_rx_if.h SYS_TIME (FIT module not yet imported in v3). */
typedef struct sys_time_
{
    uint32_t sec;
    uint32_t min;
    uint32_t hour;
    uint32_t day;
    uint32_t month;
    uint32_t year;
    uint32_t unix_time;
    uint8_t  time_zone[ 16 ];
} SYS_TIME;

typedef struct _hardware_info
{
    char * cpu_name;
    char * memory_size;
    char * frequency;
    char * crypto;
    char * board_capability;
    char * unique_id;
} HARDWARE_INFO;

typedef struct _software_info
{
    char * firmware_version;
    char * amazon_freertos_version;
    char * emwin_version;
    char * compiled_time;
} SOFTWARE_INFO;

typedef struct _task_info
{
    /* FreeRTOS task handles (legacy uses these for xTaskNotifyGive on GUI ready) */
    TaskHandle_t main_task_handle;
    TaskHandle_t serial_terminal_task_handle;
    TaskHandle_t gui_task_handle;
    TaskHandle_t sdcard_task_handle;
    TaskHandle_t task_manager_task_handle;
    TaskHandle_t sntp_task_handle;
    TaskHandle_t tcp_send_performance_task_handle;
    TaskHandle_t tcp_receive_performance_task_handle;
    TaskHandle_t serial_flash_task_handle;
    TaskHandle_t audio_task_handle;

    /* emWin window handles */
    WM_HWIN hWin_serial_terminal;
    WM_HWIN hWin_d2_audio;
    WM_HWIN hWin_firmware_update_via_sd_card;
    WM_HWIN hWin_task_manager;
    WM_HWIN hWin_system_log;
    WM_HWIN hWin_frame;
    WM_HWIN hWin_title_logo;

    /* runtime telemetry */
    SYS_TIME  sys_time;
    uint32_t  cpu_load;
    uint32_t  sd_status;        /* 0 = detach, 1 = attach */
    uint8_t * ip_address;       /* 4-byte array pointer */

    /* fps tracking */
    float    history_fps[ MAX_HISTORY_FPS_INDEX ];
    uint32_t history_fps_index;
    float    current_fps;
    float    average_fps;

    /* static info */
    SOFTWARE_INFO software_info;
    HARDWARE_INFO hardware_info;

    /* system flags */
    volatile uint32_t gui_initialize_complete_flag;
    volatile uint32_t software_reset_requested_flag;

    /* firmware update progress */
    uint32_t file_size;
    uint32_t processed_file_size;
    uint32_t progress;
} TASK_INFO;

extern TASK_INFO * get_task_info( void );

/* Legacy firmware update API stubs.
 * 段階5-4 で `firm_update.c` / `sdcard_task.c` を v3 に取り込む際、本宣言は
 * 正式な firm_update.h に置き換わる予定。それまでは AppWizard CustomCode
 * (ID_SCREEN_01_Slots.c の SD update ボタンハンドラ) が link 解決できる
 * ようにスタブ実装を提供する。
 */
extern bool is_firmware_updating( void );
extern void firmware_update_request( const char * file_name );
extern void firmware_update_log_string( TASK_INFO * task_info, const char * msg );

#endif /* RX72N_ENVISION_KIT_SYSTEM_H */
