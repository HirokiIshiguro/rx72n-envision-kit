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

void gui_task( void * pvParameters );

/**********************************************************************************************************************
 * Function Name: gui_task
 * Description  : emWin の初期化と AppWizard 初期画面 (ID_SCREEN_00) を表示する。
 *                10ms 周期で APPW_Exec() + GUI_Exec() を呼び、AppWizard の状態更新と
 *                emWin ウィンドウマネージャを駆動する (legacy main_10ms_display_update 準拠)。
 *
 *                Legacy aws_demos の gui_task は GUI ready フラグと依存タスクへの xTaskNotifyGive
 *                を持つが、段階5-1 では sdcard / task_manager / serial_flash 等の依存タスクが
 *                v3 baseline に未移植のため省略する。段階5-2 以降で復活させる。
 *********************************************************************************************************************/
void gui_task( void * pvParameters )
{
    (void) pvParameters;

    /* emWin / AppWizard 起動シーケンス (legacy 準拠) */
    APPW_X_Setup();
    APPW_Init( APPW_PROJECT_PATH );
    APPW_CreateRoot( APPW_INITIAL_SCREEN, WM_HBKWIN );

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
