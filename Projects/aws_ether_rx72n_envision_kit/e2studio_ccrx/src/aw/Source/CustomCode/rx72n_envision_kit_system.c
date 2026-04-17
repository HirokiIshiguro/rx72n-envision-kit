/**********************************************************************************************************************
 * File Name    : rx72n_envision_kit_system.c
 * Description  : Phase 8b 第3次 段階5-1 (rx72n-envision-kit#49 / MR !86) の最小スタブ実装。
 *                Static TASK_INFO instance を1つ用意し、char* 系のフィールドを空文字列で初期化する。
 *                これで AppWizard CustomCode (ID_SCREEN_01_Slots.c) の sprintf("%s", ...) が NULL ポインタで
 *                落ちないようにしつつ、未実装フィールドは "" で表示される。
 *                段階5-2 以降で task_manager_task / sdcard_task / serial_flash_task 等が移植されたら、
 *                各タスクから本構造体に runtime 情報を書き込むようにする。
 *********************************************************************************************************************/

#include "rx72n_envision_kit_system.h"

static uint8_t s_ip_address[ 4 ] = { 0, 0, 0, 0 };

static TASK_INFO s_task_info =
{
    .ip_address    = s_ip_address,
    .hardware_info = { "", "", "", "", "", "" },
    .software_info = { "", "", "", "" },
};

TASK_INFO * get_task_info( void )
{
    return &s_task_info;
}

/* Legacy firmware update API stubs (段階5-4 で正式実装に置換予定). */

bool is_firmware_updating( void )
{
    return false;
}

void firmware_update_request( const char * file_name )
{
    (void) file_name;
}

void firmware_update_log_string( TASK_INFO * task_info, const char * msg )
{
    (void) task_info;
    (void) msg;
}
