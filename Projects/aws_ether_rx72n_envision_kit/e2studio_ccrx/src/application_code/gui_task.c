/**********************************************************************************************************************
 * File Name    : gui_task.c
 * Description  : emWin/AppWizard GUI task for v3 baseline.
 *                Phase 8b 第3次 段階5-1 (rx72n-envision-kit#49) における最小実装。
 *                Legacy aws_demos の gui_task.c (vendors/.../renesas_code/gui_task.c) の起動順序に
 *                準拠する。
 *********************************************************************************************************************/

#include <stdint.h>

#include "FreeRTOS.h"
#include "task.h"

#include "GUI.h"
#include "DIALOG.h"
#include "AppWizard.h"

#include "Resource.h"

/* Phase 8b 第3次 段階5-x: TASK_INFO / get_task_info() 用 (sdcard / serial_flash の handle 取得)。 */
#include "rx72n_envision_kit_system.h"

void gui_task( void * pvParameters );

/**********************************************************************************************************************
 * Function Name: gui_task
 * Description  : emWin の初期化と AppWizard 初期画面 (ID_SCREEN_00) を表示する。
 *                10ms 周期で APPW_Exec() + GUI_Exec() を呼び、AppWizard の状態更新と
 *                emWin ウィンドウマネージャを駆動する (legacy main_10ms_display_update 準拠)。
 *
 *                Legacy aws_demos の gui_task と同じく、GUI 初期化完了後に
 *                gui_initialize_complete_flag を立て、依存タスク (sdcard / serial_flash) へ
 *                xTaskNotifyGive で wake-up を送る (段階5-x で復活)。
 *                task_manager_task はまだ v3 未移植のため通知対象外。
 *********************************************************************************************************************/
void gui_task( void * pvParameters )
{
    TASK_INFO * task_info = ( TASK_INFO * ) pvParameters;

    /* emWin / AppWizard 起動シーケンス (legacy 準拠) */
    APPW_X_Setup();
    APPW_Init( APPW_PROJECT_PATH );
    APPW_CreateRoot( APPW_INITIAL_SCREEN, WM_HBKWIN );

    /* GUI 初期化完了。legacy uart_string_printf() のブロック解除フラグ。 */
    task_info->gui_initialize_complete_flag = 1;

    /* GUI 初期化待ちタスクへ wake-up 通知 (legacy 準拠)。
     * task_manager_task は v3 未移植のため対象外。 */
    if( task_info->sdcard_task_handle != NULL )
    {
        xTaskNotifyGive( task_info->sdcard_task_handle );
    }
    if( task_info->serial_flash_task_handle != NULL )
    {
        xTaskNotifyGive( task_info->serial_flash_task_handle );
    }
    if( task_info->audio_task_handle != NULL )
    {
        xTaskNotifyGive( task_info->audio_task_handle );
    }

    /* 10ms 周期で AppWizard / emWin を駆動 (legacy main_10ms_display_update 準拠) */
    for( ; ; )
    {
        APPW_Exec();
        GUI_Exec();
        vTaskDelay( pdMS_TO_TICKS( 10 ) );
    }
}
/**********************************************************************************************************************
 End of function gui_task
 *********************************************************************************************************************/
