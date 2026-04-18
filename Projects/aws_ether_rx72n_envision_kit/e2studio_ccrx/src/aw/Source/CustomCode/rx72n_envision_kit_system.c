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

/* Phase 8b 第3次 段階5-4c-2 (#56): code flash 排他制御用 global semaphore.
 * firm_update.c / bank_swap.c が触る。本実体定義のみ提供 (NULL 初期値)。
 * `xSemaphoreCreateBinary()` + `xSemaphoreGive()` は main_task() の早期に
 * 呼ぶ必要がある (5-4c-3 で sdcard_task と一緒に組み込み)。本 sub では
 * extern declaration の解決のため実体だけ用意する形で build green。 */
SemaphoreHandle_t xSemaphoreCodeFlashAccess = NULL;

/* Phase 8b 第3次 段階5-4c-2 (#56): 段階5-1 で追加した firmware_update_*
 * stub のうち、`firmware_update_request()` / `is_firmware_updating()` は
 * sd_update/firm_update.c が本実装を提供するため削除。
 * `firmware_update_log_string()` は legacy では sdcard_task / GUI 連動の log
 * 関数だが、段階5-4c-3 で sdcard_task 移植時に正式実装する予定。それまで
 * stub を維持する。 */

void firmware_update_log_string( TASK_INFO * task_info, const char * msg )
{
    (void) task_info;
    (void) msg;
}

/* Phase 8b 第3次 段階5-4c-2 (#56): legacy r_simple_filesystem_on_dataflash (SFD) は
 * v3 baseline では LittleFS に置換済で不要。firm_update.c が SFD と code flash 競合
 * 防止のため `R_SFD_SemaphoreTake/Give()` を呼んでいるが、v3 では LittleFS 自体が
 * 内部で flash 排他制御を持つため stub no-op で良い。実際の flash 並行アクセス保護は
 * `xSemaphoreCodeFlashAccess` 単独で十分 (5-4c-3 の sdcard_task で初期化)。 */
void R_SFD_SemaphoreTake( void )
{
}

void R_SFD_SemaphoreGive( void )
{
}
