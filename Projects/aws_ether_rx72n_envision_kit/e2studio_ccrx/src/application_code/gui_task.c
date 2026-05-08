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

#ifndef appmainENABLE_BOARD_GUI_STUB_TASK
    #define appmainENABLE_BOARD_GUI_STUB_TASK    ( 0 )
#endif

#ifndef appmainENABLE_BOARD_GUI_INIT_ONLY_TASK
    #define appmainENABLE_BOARD_GUI_INIT_ONLY_TASK    ( 0 )
#endif

#ifndef appmainENABLE_BOARD_GUI_SETUP_ONLY_TASK
    #define appmainENABLE_BOARD_GUI_SETUP_ONLY_TASK    ( 0 )
#endif

#ifndef appmainENABLE_BOARD_GUI_NO_ROOT_TASK
    #define appmainENABLE_BOARD_GUI_NO_ROOT_TASK    ( 0 )
#endif

#ifndef appmainENABLE_BOARD_GUI_CORE_INIT_ONLY_TASK
    #define appmainENABLE_BOARD_GUI_CORE_INIT_ONLY_TASK    ( 0 )
#endif

#ifndef appmainENABLE_BOARD_GUI_LCD_DIAGNOSTIC_TASK
    #define appmainENABLE_BOARD_GUI_LCD_DIAGNOSTIC_TASK    ( 0 )
#endif

#ifndef appmainENABLE_BOARD_GUI_CREATE_PERSISTENT_SCREENS
    #define appmainENABLE_BOARD_GUI_CREATE_PERSISTENT_SCREENS    ( 0 )
#endif

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

    configPRINT_STRING( ( "GUI task enter\r\n" ) );
    configPRINTF( ( "GUI task start: stub=%ld setup_only=%ld core_init_only=%ld no_root=%ld init_only=%ld persistent=%ld heap=%lu hwm=%lu\r\n",
                    ( long ) appmainENABLE_BOARD_GUI_STUB_TASK,
                    ( long ) appmainENABLE_BOARD_GUI_SETUP_ONLY_TASK,
                    ( long ) appmainENABLE_BOARD_GUI_CORE_INIT_ONLY_TASK,
                    ( long ) appmainENABLE_BOARD_GUI_NO_ROOT_TASK,
                    ( long ) appmainENABLE_BOARD_GUI_INIT_ONLY_TASK,
                    ( long ) appmainENABLE_BOARD_GUI_CREATE_PERSISTENT_SCREENS,
                    ( unsigned long ) xPortGetFreeHeapSize(),
                    ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );

#if ( appmainENABLE_BOARD_GUI_STUB_TASK != 0 )
    configPRINT_STRING( ( "GUI stub enter\r\n" ) );
    task_info->gui_initialize_complete_flag = 1;

    configPRINTF( ( "GUI stub ready: heap=%lu hwm=%lu\r\n",
                    ( unsigned long ) xPortGetFreeHeapSize(),
                    ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );

    for( ; ; )
    {
        vTaskDelay( pdMS_TO_TICKS( 1000 ) );
    }
#elif ( appmainENABLE_BOARD_GUI_LCD_DIAGNOSTIC_TASK != 0 )
    {
        static const GUI_COLOR xDiagColors[] =
        {
            GUI_RED,
            GUI_GREEN,
            GUI_BLUE,
            GUI_WHITE,
            GUI_BLACK
        };
        static const char * const pcDiagNames[] =
        {
            "RED",
            "GREEN",
            "BLUE",
            "WHITE",
            "BLACK"
        };
        size_t xIndex = 0;
        int gui_init_result;

        configPRINT_STRING( ( "GUI LCD diag GUI_Init enter\r\n" ) );
        gui_init_result = GUI_Init();
        configPRINTF( ( "GUI LCD diag GUI_Init done: result=%d heap=%lu hwm=%lu\r\n",
                        gui_init_result,
                        ( unsigned long ) xPortGetFreeHeapSize(),
                        ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );

        task_info->gui_initialize_complete_flag = 1;
        configPRINT_STRING( ( "GUI LCD diag ready\r\n" ) );

        for( ; ; )
        {
            GUI_SetBkColor( xDiagColors[ xIndex ] );
            GUI_Clear();
            GUI_SetColor( ( xDiagColors[ xIndex ] == GUI_WHITE ) ? GUI_BLACK : GUI_WHITE );
            GUI_DispStringAt( "RX72N LCD DIAG", 20, 20 );
            GUI_DispStringAt( pcDiagNames[ xIndex ], 20, 52 );
            GUI_Exec();

            xIndex++;
            if( xIndex >= ( sizeof( xDiagColors ) / sizeof( xDiagColors[ 0 ] ) ) )
            {
                xIndex = 0;
            }

            vTaskDelay( pdMS_TO_TICKS( 1000 ) );
        }
    }
#else
    /* emWin / AppWizard 起動シーケンス (legacy 準拠) */
    configPRINT_STRING( ( "GUI APPW_X_Setup enter\r\n" ) );
    configPRINTF( ( "GUI APPW_X_Setup start: heap=%lu hwm=%lu\r\n",
                    ( unsigned long ) xPortGetFreeHeapSize(),
                    ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
    APPW_X_Setup();
    configPRINT_STRING( ( "GUI APPW_X_Setup leave\r\n" ) );
    configPRINTF( ( "GUI APPW_X_Setup done: heap=%lu hwm=%lu\r\n",
                    ( unsigned long ) xPortGetFreeHeapSize(),
                    ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );

#if ( appmainENABLE_BOARD_GUI_SETUP_ONLY_TASK != 0 )
    task_info->gui_initialize_complete_flag = 1;
    configPRINT_STRING( ( "GUI setup-only ready\r\n" ) );

    for( ; ; )
    {
        vTaskDelay( pdMS_TO_TICKS( 1000 ) );
    }
#else
#if ( appmainENABLE_BOARD_GUI_CORE_INIT_ONLY_TASK != 0 )
    {
        int gui_init_result;

        configPRINT_STRING( ( "GUI core GUI_Init enter\r\n" ) );
        configPRINTF( ( "GUI core GUI_Init start: heap=%lu hwm=%lu\r\n",
                        ( unsigned long ) xPortGetFreeHeapSize(),
                        ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
        gui_init_result = GUI_Init();
        configPRINT_STRING( ( "GUI core GUI_Init leave\r\n" ) );
        configPRINTF( ( "GUI core GUI_Init done: result=%d heap=%lu hwm=%lu\r\n",
                        gui_init_result,
                        ( unsigned long ) xPortGetFreeHeapSize(),
                        ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );

        task_info->gui_initialize_complete_flag = 1;
        configPRINT_STRING( ( "GUI core-init-only ready\r\n" ) );

        for( ; ; )
        {
            vTaskDelay( pdMS_TO_TICKS( 1000 ) );
        }
    }
#else
    configPRINT_STRING( ( "GUI APPW_Init enter\r\n" ) );
    configPRINTF( ( "GUI APPW_Init start: heap=%lu hwm=%lu\r\n",
                    ( unsigned long ) xPortGetFreeHeapSize(),
                    ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
    APPW_Init( APPW_PROJECT_PATH );
    configPRINT_STRING( ( "GUI APPW_Init leave\r\n" ) );
    configPRINTF( ( "GUI APPW_Init done: heap=%lu hwm=%lu\r\n",
                    ( unsigned long ) xPortGetFreeHeapSize(),
                    ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );

#if ( appmainENABLE_BOARD_GUI_CREATE_PERSISTENT_SCREENS != 0 )
    configPRINT_STRING( ( "GUI APPW_CreatePersistentScreens enter\r\n" ) );
    configPRINTF( ( "GUI APPW_CreatePersistentScreens start: heap=%lu hwm=%lu\r\n",
                    ( unsigned long ) xPortGetFreeHeapSize(),
                    ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
    APPW_CreatePersistentScreens();
    configPRINT_STRING( ( "GUI APPW_CreatePersistentScreens leave\r\n" ) );
    configPRINTF( ( "GUI APPW_CreatePersistentScreens done: heap=%lu hwm=%lu\r\n",
                    ( unsigned long ) xPortGetFreeHeapSize(),
                    ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
#endif

#if ( appmainENABLE_BOARD_GUI_NO_ROOT_TASK != 0 )
    task_info->gui_initialize_complete_flag = 1;
    configPRINT_STRING( ( "GUI no-root ready\r\n" ) );

    for( ; ; )
    {
        vTaskDelay( pdMS_TO_TICKS( 1000 ) );
    }
#else
    configPRINT_STRING( ( "GUI APPW_CreateRoot enter\r\n" ) );
    configPRINTF( ( "GUI APPW_CreateRoot start: heap=%lu hwm=%lu\r\n",
                    ( unsigned long ) xPortGetFreeHeapSize(),
                    ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
    APPW_CreateRoot( APPW_INITIAL_SCREEN, WM_HBKWIN );
    configPRINT_STRING( ( "GUI APPW_CreateRoot leave\r\n" ) );
    configPRINTF( ( "GUI APPW_CreateRoot done: heap=%lu hwm=%lu\r\n",
                    ( unsigned long ) xPortGetFreeHeapSize(),
                    ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );

    /* GUI 初期化完了。legacy uart_string_printf() のブロック解除フラグ。 */
    task_info->gui_initialize_complete_flag = 1;
    configPRINT_STRING( ( "GUI ready sync\r\n" ) );
    configPRINTF( ( "GUI ready: heap=%lu hwm=%lu\r\n",
                    ( unsigned long ) xPortGetFreeHeapSize(),
                    ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );

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

#if ( appmainENABLE_BOARD_GUI_INIT_ONLY_TASK != 0 )
    configPRINT_STRING( ( "GUI init-only ready\r\n" ) );

    for( ; ; )
    {
        vTaskDelay( pdMS_TO_TICKS( 1000 ) );
    }
#else
    /* 10ms 周期で AppWizard / emWin を駆動 (legacy main_10ms_display_update 準拠) */
    for( ; ; )
    {
        static BaseType_t xFirstLoop = pdTRUE;

        if( xFirstLoop != pdFALSE )
        {
            configPRINT_STRING( ( "GUI loop APPW_Exec enter\r\n" ) );
        }
        APPW_Exec();
        if( xFirstLoop != pdFALSE )
        {
            configPRINT_STRING( ( "GUI loop APPW_Exec leave\r\n" ) );
            configPRINT_STRING( ( "GUI loop GUI_Exec enter\r\n" ) );
        }
        GUI_Exec();
        if( xFirstLoop != pdFALSE )
        {
            configPRINT_STRING( ( "GUI loop GUI_Exec leave\r\n" ) );
            xFirstLoop = pdFALSE;
        }
        vTaskDelay( pdMS_TO_TICKS( 10 ) );
    }
#endif
#endif
#endif
#endif
#endif
}
/**********************************************************************************************************************
 End of function gui_task
 *********************************************************************************************************************/
