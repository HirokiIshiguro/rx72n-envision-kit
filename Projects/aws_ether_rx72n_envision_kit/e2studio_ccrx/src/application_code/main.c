/*
FreeRTOS
Copyright (C) 2020 Amazon.com, Inc. or its affiliates.  All Rights Reserved.
Modifications Copyright (C) 2023-2025 Renesas Electronics Corporation or its affiliates.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

 http://aws.amazon.com/freertos
 http://www.FreeRTOS.org
*/

/* C runtime includes. */
#include <stdio.h>
#include <string.h>

/* FreeRTOS includes. */
#include "FreeRTOS.h"
#include "task.h"
#include "event_groups.h"

/* Renesas includes. */
#include "platform.h"

/* Logging includes. */
#include "iot_logging_task.h"

/* Key provisioning includes. */
#include "aws_dev_mode_key_provisioning.h"

/* FreeRTOS+TCP includes. */
#include "FreeRTOS_IP.h"

/* Demo includes */
#include "aws_clientcredential.h"
#include "demo_config.h"
#include "store.h"
#include "mqtt_agent_task.h"

/* Phase 8b 第3次 段階5-x: get_task_info() / TASK_INFO アクセス用。
 * gui_task からの xTaskNotifyGive で参照するタスクハンドル群を共有 singleton に
 * 集約し、legacy aws_demos と同じ task_info ベース wiring を復活させる。 */
#include "rx72n_envision_kit_system.h"
/* r_simple_glcdc_config_rx / r_simple_graphic_rx removed in Phase 8b 第3次
 * 段階5-1 first checkpoint (MR !85). LCD output now goes through emWin via
 * gui_task (legacy-aligned APPW_X_Setup → APPW_Init → APPW_CreateRoot
 * sequence). vApplicationLcdLogString() remains a stub until 段階5-2 wires
 * a logging window. */
extern void gui_task( void * pvParameters );

#define appmainGUI_TASK_STACK_SIZE                ( 4096 )
#define appmainGUI_TASK_PRIORITY                  ( tskIDLE_PRIORITY + 1 )
#define appmainGUI_INIT_WAIT_TIMEOUT_MS           ( 10000UL )
#define appmainGUI_INIT_WAIT_LOG_INTERVAL_MS      ( 1000UL )

/* Phase 8b 第3次 段階5-4c-3 (rx72n-envision-kit#57): SD update task. */
extern void sdcard_task( void * pvParameters );

#define appmainSDCARD_TASK_STACK_SIZE             ( 4096 )
#define appmainSDCARD_TASK_PRIORITY               ( tskIDLE_PRIORITY + 1 )

/* Phase 8b 第3次 段階5-5 (rx72n-envision-kit#58): serial flash (Quad SPI) task.
 * legacy aws_demos main_task は xTaskCreate(serial_flash_task, "serial_flash",
 * RX72N_ENVISION_KIT_TASKS_STACK, &task_info, tskIDLE_PRIORITY, ...) で起動していた。
 * v3 baseline では task_info 共有と gui_task からの xTaskNotifyGive が未復活のため、
 * sdcard_task と同じローカル static handle / NULL pvParameters / +1 priority に揃える。
 * notify wiring の復活は段階5-x で gui_task と一括で行う想定。 */
extern void serial_flash_task( void * pvParameters );

#define appmainSERIAL_FLASH_TASK_STACK_SIZE       ( 4096 )
#define appmainSERIAL_FLASH_TASK_PRIORITY         ( tskIDLE_PRIORITY + 1 )

/* Phase 8b 第3次 段階5-6 (rx72n-envision-kit#59): audio task placeholder.
 * legacy aws_demos の audio_task.c も実装は永久 sleep のみで、実 audio 機能
 * (SSI codec / DMA driver) は無かった。本 wiring は将来の audio 機能実装に
 * 備えた main_task / TASK_INFO::audio_task_handle の placeholder。
 * sdcard / serial_flash と同じローカル static handle / get_task_info() pattern。 */
extern void audio_task( void * pvParameters );

#define appmainAUDIO_TASK_STACK_SIZE              ( 4096 )
#define appmainAUDIO_TASK_PRIORITY                ( tskIDLE_PRIORITY + 1 )

#ifndef appmainENABLE_BOARD_APPLICATION_TASKS
    #define appmainENABLE_BOARD_APPLICATION_TASKS ( 0 )
#endif

#ifndef appmainENABLE_BOARD_GUI_TASK
    #define appmainENABLE_BOARD_GUI_TASK appmainENABLE_BOARD_APPLICATION_TASKS
#endif

#ifndef appmainENABLE_BOARD_SDCARD_TASK
    #define appmainENABLE_BOARD_SDCARD_TASK appmainENABLE_BOARD_APPLICATION_TASKS
#endif

#ifndef appmainENABLE_BOARD_SERIAL_FLASH_TASK
    #define appmainENABLE_BOARD_SERIAL_FLASH_TASK appmainENABLE_BOARD_APPLICATION_TASKS
#endif

#ifndef appmainENABLE_BOARD_AUDIO_TASK
    #define appmainENABLE_BOARD_AUDIO_TASK appmainENABLE_BOARD_APPLICATION_TASKS
#endif

#define appmainENABLE_ANY_BOARD_APPLICATION_TASK    ( ( appmainENABLE_BOARD_GUI_TASK != 0 ) || \
                                                      ( appmainENABLE_BOARD_SDCARD_TASK != 0 ) || \
                                                      ( appmainENABLE_BOARD_SERIAL_FLASH_TASK != 0 ) || \
                                                      ( appmainENABLE_BOARD_AUDIO_TASK != 0 ) )

#define appmainENABLE_BOARD_GUI_DEPENDENCY         ( ( appmainENABLE_BOARD_GUI_TASK != 0 ) || \
                                                      ( appmainENABLE_BOARD_SDCARD_TASK != 0 ) || \
                                                      ( appmainENABLE_BOARD_SERIAL_FLASH_TASK != 0 ) || \
                                                      ( appmainENABLE_BOARD_AUDIO_TASK != 0 ) )

#ifndef appmainENABLE_NETWORK_WAIT_DIAGNOSTICS
    #define appmainENABLE_NETWORK_WAIT_DIAGNOSTICS appmainENABLE_ANY_BOARD_APPLICATION_TASK
#endif

#ifndef appmainENABLE_TRACEALYZER
    #define appmainENABLE_TRACEALYZER ( 1 )
#endif

#define appmainNETWORK_WAIT_LOG_INTERVAL_MS        ( 5000UL )

/* Phase 8b 第3次 段階5-7 B-1 (rx72n-envision-kit#60): TCP performance tasks.
 * iperf 互換 TCP throughput 測定。legacy aws_demos と同じ priority
 * configMAX_PRIORITIES (network throughput 優先)。両 task とも自走で
 * gui_task からの notify 不要。サーバ IP/port は B-1 では #define hardcode、
 * B-2 で KVStore 化予定。 */
extern void tcp_send_performance_task( void * pvParameters );
extern void tcp_receive_performance_task( void * pvParameters );

#define appmainTCP_PERF_TASK_STACK_SIZE           ( 4096 )
#define appmainTCP_PERF_TASK_PRIORITY             ( configMAX_PRIORITIES - 1 )

EventGroupHandle_t xStartDemoEventGroup = NULL;

bool ApplicationCounter (uint32_t xWaitTime);
signed char vISR_Routine (void);
extern void vStartSimplePubSubDemo (void);
BaseType_t OtaSelfTest(void);

BaseType_t vAssignCredentials(void);
extern int32_t xprvWriteCacheEntry(size_t KeyLength,
        char * Key,
        size_t ValueLength,
        char * pvNewValue );
extern BaseType_t KVStore_xCommitChanges(void);

#if (ENABLE_OTA_UPDATE_DEMO == 1)
    extern void vStartOtaDemo(void);
#endif

#if (ENABLE_FLEET_PROVISIONING_DEMO == 1)
    extern void vStartFleetProvisioningDemo(void);
#endif

/**
 * @brief Flag which enables OTA update task in background along with other demo tasks.
 * OTA update task polls regularly for firmware update jobs or acts on a new firmware update
 * available notification from OTA service.
 */
#define appmainINCLUDE_OTA_UPDATE_TASK            ( 1 )

/**
 * @brief Stack size and priority for OTA Update task.
 */
#define appmainMQTT_OTA_UPDATE_TASK_STACK_SIZE    ( 4096 )
#define appmainMQTT_OTA_UPDATE_TASK_PRIORITY      ( tskIDLE_PRIORITY )

/**
 * @brief Stack size and priority for MQTT agent task.
 * Stack size is capped to an adequate value based on requirements from MbedTLS stack
 * for establishing a TLS connection. Task priority of MQTT agent is set to a priority
 * higher than other MQTT application tasks, so that the agent can drain the queue
 * as work is being produced.
 */
#define appmainMQTT_AGENT_TASK_STACK_SIZE         ( 6144 )
#define appmainMQTT_AGENT_TASK_PRIORITY           ( tskIDLE_PRIORITY + 2 )

/**
 * @brief Stack size and priority for CLI task.
 */
#define appmainCLI_TASK_STACK_SIZE                ( 6144 )
#define appmainCLI_TASK_PRIORITY                  ( tskIDLE_PRIORITY + 1 )

#define mainLOGGING_TASK_STACK_SIZE               ( configMINIMAL_STACK_SIZE * 6 )
#define mainLOGGING_MESSAGE_QUEUE_LENGTH          ( 15 )
#define mainTEST_RUNNER_TASK_STACK_SIZE           ( configMINIMAL_STACK_SIZE * 8 )
#define UNSIGNED_SHORT_RANDOM_NUMBER_MASK         (0xFFFFUL)

#define mainUART_COMMAND_CONSOLE_STACK_SIZE ( configMINIMAL_STACK_SIZE * 6UL )
/* The priority used by the UART command console task. */
#define mainUART_COMMAND_CONSOLE_TASK_PRIORITY  ( 1 )

/* The MAC address array is not declared const as the MAC address will
normally be read from an EEPROM and not hard coded (in real deployed
applications).*/
static uint8_t ucMACAddress[6] =
{
    configMAC_ADDR0,
    configMAC_ADDR1,
    configMAC_ADDR2,
    configMAC_ADDR3,
    configMAC_ADDR4,
    configMAC_ADDR5
}; //XXX

/* Define the network addressing.  These parameters will be used if either
ipconfigUDE_DHCP is 0 or if ipconfigUSE_DHCP is 1 but DHCP auto configuration
failed. */
static const uint8_t ucIPAddress[4] =
{
    configIP_ADDR0,
    configIP_ADDR1,
    configIP_ADDR2,
    configIP_ADDR3
};
static const uint8_t ucNetMask[4] =
{
    configNET_MASK0,
    configNET_MASK1,
    configNET_MASK2,
    configNET_MASK3
};
static const uint8_t ucGatewayAddress[4] =
{
    configGATEWAY_ADDR0,
    configGATEWAY_ADDR1,
    configGATEWAY_ADDR2,
    configGATEWAY_ADDR3
};

/* The following is the address of an OpenDNS server. */
static const uint8_t ucDNSServerAddress[4] =
{
    configDNS_SERVER_ADDR0,
    configDNS_SERVER_ADDR1,
    configDNS_SERVER_ADDR2,
    configDNS_SERVER_ADDR3
};

extern int32_t littlFs_init (void);
extern void vSerialPutString(const signed char * pcString, unsigned short usStringLength);

/**
 * @brief Application task startup hook.
 */
void vApplicationDaemonTaskStartupHook (void);

/**
 * @brief Initializes the board.
 */
void prvMiscInitialization (void);
static BaseType_t prvShouldAutoProvisionFromClientCredentials( void );
static void prvDisplayInitialize( void );
static void prvWaitForGuiInitialization( void );
static void prvStartBoardApplicationTasks( void );
static void prvDisplayWriteBanner( void );
static void prvDisplayWrite( const char * pcMessage );

extern void vApplicationEnsureEmwinFrameBufferReserved( void );
extern void UserInitialization (void);
extern void CLI_Support_Settings (void);
extern void vUARTCommandConsoleStart (uint16_t usStackSize, UBaseType_t uxPriority);
extern void vRegisterSampleCLICommands (void);

static BaseType_t xDisplayInitialized = pdFALSE;

/*-----------------------------------------------------------*/

/**********************************************************************************************************************
 * Function Name: main_task
 * Description  : The application entry point from a power on reset is PowerON_Reset_PC()
 *                in resetprg.c.
 * Return Value : .
 *********************************************************************************************************************/
void main_task(void *pvParameters)
{
    int32_t xResults;
    int32_t xCacheInitResult = LFS_ERR_OK;
    int32_t Time2Wait = 10000;
    BaseType_t xProceedToDemo = pdTRUE;
    extern void vRegisterSampleCLICommands (void);
    extern void vUARTCommandConsoleStart (uint16_t usStackSize, UBaseType_t uxPriority);
    extern TaskHandle_t xCLIHandle;

    (void) pvParameters;

    prvMiscInitialization();
    UserInitialization();

    /* Phase 8b 第3次 段階5-4c-3 (#57): code flash 排他制御用 semaphore を初期化。
     * sdcard_task / firm_update.c が xSemaphoreTake/Give する。
     * legacy aws_demos の main.c L164-165 と同じパターン。 */
    {
        extern SemaphoreHandle_t xSemaphoreCodeFlashAccess;
        xSemaphoreCodeFlashAccess = xSemaphoreCreateBinary();
        xSemaphoreGive( xSemaphoreCodeFlashAccess );
    }

    /* Keep LCD/SD/serial flash/audio out of the v3 baseline path.
     * Re-enable them from a dedicated app-layer job once MQTT is stable. */
#if (ENABLE_CREDENTIAL_BY_CLI == 1)
    {
        /* Register the standard CLI commands. */
        extern void vRegisterSdcardCLICommands(void); /* Phase 8b 第3次 段階5-4a (#53) */
        vRegisterSampleCLICommands();
        vRegisterSdcardCLICommands();
        vUARTCommandConsoleStart(mainUART_COMMAND_CONSOLE_STACK_SIZE, mainUART_COMMAND_CONSOLE_TASK_PRIORITY);
    }
#endif

    xResults = littlFs_init();
    prvDisplayWrite((LFS_ERR_OK == xResults) ? "LittleFS OK\r\n" : "LittleFS ERROR\r\n");

    xMQTTAgentInit();
    prvDisplayWrite("MQTT agent init\r\n");

    if (LFS_ERR_OK == xResults)
    {
        xCacheInitResult = vprvCacheInit();
    }

#if (ENABLE_CREDENTIAL_BY_CLI == 1)
    if( ( LFS_ERR_OK == xResults ) &&
        ( LFS_ERR_OK == xCacheInitResult ) &&
        ( pdTRUE == prvShouldAutoProvisionFromClientCredentials() ) )
    {
        vAssignCredentials();
    }
#endif

#if (ENABLE_CREDENTIAL_BY_CLI == 0)
    vAssignCredentials();
#else
    xProceedToDemo = ApplicationCounter(Time2Wait);
#endif

    if (pdTRUE == xProceedToDemo)
    {
    #if (ENABLE_CREDENTIAL_BY_CLI == 1)
        /* Remove CLI task before going to demo. */
        /* CLI and Log tasks use common resources but are not exclusively controlled. */
        /* For this reason, the CLI task must be deleted before executing the Demo. */
        if( xCLIHandle != NULL )
        {
            TaskHandle_t xCurrentTaskHandle = xTaskGetCurrentTaskHandle();

#if ( appmainENABLE_NETWORK_WAIT_DIAGNOSTICS != 0 )
            configPRINTF( ( "CLI delete check: cli=%08lx current=%08lx heap=%lu main_hwm=%lu\r\n",
                            ( unsigned long ) xCLIHandle,
                            ( unsigned long ) xCurrentTaskHandle,
                            ( unsigned long ) xPortGetFreeHeapSize(),
                            ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
#endif

            if( xCLIHandle != xCurrentTaskHandle )
            {
                vTaskDelete(xCLIHandle);
                xCLIHandle = NULL;

#if ( appmainENABLE_NETWORK_WAIT_DIAGNOSTICS != 0 )
                configPRINTF( ( "CLI delete done: heap=%lu main_hwm=%lu\r\n",
                                ( unsigned long ) xPortGetFreeHeapSize(),
                                ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
#endif
            }
#if ( appmainENABLE_NETWORK_WAIT_DIAGNOSTICS != 0 )
            else
            {
                configPRINTF( ( "CLI delete skipped current task handle\r\n" ) );
            }
#endif
        }
    #endif

        /* Initialise the RTOS's TCP/IP stack.  The tasks that use the network
            are created in the vApplicationIPNetworkEventHook() hook function
            below.  The hook function is called when the network connects. */
        prvDisplayWrite("Network init\r\n");

#if ( appmainENABLE_NETWORK_WAIT_DIAGNOSTICS != 0 )
        configPRINTF( ( "Network init start: heap=%lu main_hwm=%lu\r\n",
                        ( unsigned long ) xPortGetFreeHeapSize(),
                        ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
#endif

        FreeRTOS_IPInit(ucIPAddress,
                        ucNetMask,
                        ucGatewayAddress,
                        ucDNSServerAddress,
                        ucMACAddress );

#if ( appmainENABLE_NETWORK_WAIT_DIAGNOSTICS != 0 )
        configPRINTF( ( "Network init returned: heap=%lu main_hwm=%lu\r\n",
                        ( unsigned long ) xPortGetFreeHeapSize(),
                        ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
#endif

        /* We should wait for the network to be up before we run any demos. */
#if ( appmainENABLE_NETWORK_WAIT_DIAGNOSTICS != 0 )
        {
            const TickType_t xNetworkWaitStartTick = xTaskGetTickCount();
            TickType_t xNetworkWaitLastLogTick = xNetworkWaitStartTick;
#endif
            while (FreeRTOS_IsNetworkUp() == pdFALSE)
            {
                vTaskDelay(pdMS_TO_TICKS(300));

#if ( appmainENABLE_NETWORK_WAIT_DIAGNOSTICS != 0 )
                {
                    const TickType_t xNetworkWaitNowTick = xTaskGetTickCount();

                    if( ( xNetworkWaitNowTick - xNetworkWaitLastLogTick ) >= pdMS_TO_TICKS( appmainNETWORK_WAIT_LOG_INTERVAL_MS ) )
                    {
                        xNetworkWaitLastLogTick = xNetworkWaitNowTick;
                        configPRINTF( ( "Network wait: up=%ld waited=%lu heap=%lu main_hwm=%lu\r\n",
                                        ( long ) FreeRTOS_IsNetworkUp(),
                                        ( unsigned long ) ( ( xNetworkWaitNowTick - xNetworkWaitStartTick ) * portTICK_PERIOD_MS ),
                                        ( unsigned long ) xPortGetFreeHeapSize(),
                                        ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
                    }
                }
#endif
            }

#if ( appmainENABLE_NETWORK_WAIT_DIAGNOSTICS != 0 )
            {
                const TickType_t xNetworkWaitEndTick = xTaskGetTickCount();

                configPRINTF( ( "Network wait done: waited=%lu heap=%lu main_hwm=%lu\r\n",
                                ( unsigned long ) ( ( xNetworkWaitEndTick - xNetworkWaitStartTick ) * portTICK_PERIOD_MS ),
                                ( unsigned long ) xPortGetFreeHeapSize(),
                                ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
            }
        }
#endif

        FreeRTOS_printf(("Initialise the RTOS's TCP/IP stack\n"));
        prvDisplayWrite("Network up\r\n");

        if( appmainENABLE_ANY_BOARD_APPLICATION_TASK != 0 )
        {
            prvStartBoardApplicationTasks();
            configPRINTF( ( "Board app tasks init done: heap=%lu main_hwm=%lu\r\n",
                            ( unsigned long ) xPortGetFreeHeapSize(),
                            ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
            prvDisplayWrite("Board app tasks init\r\n");
        }

        /* Phase 8b 第3次 段階5-7 B-1 (#60): TCP performance tasks (iperf 互換) を起動。
         * CLI provisioning window を潰さないよう、demo 継続判定と network up 後に起動する。 */
        {
            static TaskHandle_t s_tcp_send_perf_task_handle = NULL;
            if( s_tcp_send_perf_task_handle == NULL )
            {
                ( void ) xTaskCreate( tcp_send_performance_task,
                                      "tcp_send_perf",
                                      appmainTCP_PERF_TASK_STACK_SIZE,
                                      get_task_info(),
                                      appmainTCP_PERF_TASK_PRIORITY,
                                      &s_tcp_send_perf_task_handle );
                get_task_info()->tcp_send_performance_task_handle = s_tcp_send_perf_task_handle;
            }
        }
        {
            static TaskHandle_t s_tcp_recv_perf_task_handle = NULL;
            if( s_tcp_recv_perf_task_handle == NULL )
            {
                ( void ) xTaskCreate( tcp_receive_performance_task,
                                      "tcp_recv_perf",
                                      appmainTCP_PERF_TASK_STACK_SIZE,
                                      get_task_info(),
                                      appmainTCP_PERF_TASK_PRIORITY,
                                      &s_tcp_recv_perf_task_handle );
                get_task_info()->tcp_receive_performance_task_handle = s_tcp_recv_perf_task_handle;
            }
        }

        /* Phase 8b 第3次 段階5-2 (rx72n-envision-kit#50): Tracealyzer recorder
         * の起動。FreeRTOS-Plus-TCP streamport (Middleware/3rdparty/
         * tracealyzer_recorder/streamports/FreeRTOS_Plus_TCP/) が socket を開いて
         * 初期接続するため、本タイミング (network up 確認後、demo task 起動前) に
         * vTraceEnable() を呼ぶ。Tracealyzer host 接続失敗時は port 内で
         * vTraceStop() が呼ばれ trace 出力は無効化される (boot は継続)。 */
#if ( appmainENABLE_TRACEALYZER != 0 )
        {
            configPRINTF( ( "Tracealyzer init start: heap=%lu main_hwm=%lu\r\n",
                            ( unsigned long ) xPortGetFreeHeapSize(),
                            ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
            vTraceEnable( TRC_INIT );
            configPRINTF( ( "Tracealyzer start: heap=%lu main_hwm=%lu\r\n",
                            ( unsigned long ) xPortGetFreeHeapSize(),
                            ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
            vTraceEnable( TRC_START );
            configPRINTF( ( "Tracealyzer done: heap=%lu main_hwm=%lu\r\n",
                            ( unsigned long ) xPortGetFreeHeapSize(),
                            ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
            prvDisplayWrite("Tracealyzer init\r\n");
        }
#else
        configPRINTF( ( "Tracealyzer skipped: heap=%lu main_hwm=%lu\r\n",
                        ( unsigned long ) xPortGetFreeHeapSize(),
                        ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
#endif

        FreeRTOS_printf(("---------STARTING DEMO---------\r\n"));
        configPRINTF( ( "Demo start marker: heap=%lu main_hwm=%lu\r\n",
                        ( unsigned long ) xPortGetFreeHeapSize(),
                        ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
        prvDisplayWrite("Starting demo\r\n");

            #if (ENABLE_FLEET_PROVISIONING_DEMO == 1)
                vStartFleetProvisioningDemo();
            #else
                xSetMQTTAgentState(MQTT_AGENT_STATE_INITIALIZED);
            #endif

            configPRINTF( ( "MQTT agent start call: heap=%lu main_hwm=%lu\r\n",
                            ( unsigned long ) xPortGetFreeHeapSize(),
                            ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
            vStartMQTTAgent (appmainMQTT_AGENT_TASK_STACK_SIZE, appmainMQTT_AGENT_TASK_PRIORITY);
            configPRINTF( ( "MQTT agent start returned: heap=%lu main_hwm=%lu\r\n",
                            ( unsigned long ) xPortGetFreeHeapSize(),
                            ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
            prvDisplayWrite("MQTT task start\r\n");

            configPRINTF( ( "Simple PubSub start call: heap=%lu main_hwm=%lu\r\n",
                            ( unsigned long ) xPortGetFreeHeapSize(),
                            ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
            vStartSimplePubSubDemo ();
            configPRINTF( ( "Simple PubSub start returned: heap=%lu main_hwm=%lu\r\n",
                            ( unsigned long ) xPortGetFreeHeapSize(),
                            ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
            prvDisplayWrite("PubSub task start\r\n");

            #if (ENABLE_OTA_UPDATE_DEMO == 1)
                        vStartOtaDemo();
                        prvDisplayWrite("OTA task start\r\n");
            #endif
    }
    else
    {
        prvDisplayWrite("CLI mode active\r\n");
    }

    while (1)
    {
        vTaskSuspend(NULL);
    }
}
/*****************************************************************************************
End of function main_task
****************************************************************************************/
/*-----------------------------------------------------------*/

/**********************************************************************************************************************
 * Function Name: prvMiscInitialization
 * Description  : .
 * Return Value : .
 *********************************************************************************************************************/
void prvMiscInitialization(void)
{
    /* Initialize UART for serial terminal. */
    CLI_Support_Settings();

    xStartDemoEventGroup = xEventGroupCreate();

    /* Start logging task. */
    xLoggingTaskInitialize(mainLOGGING_TASK_STACK_SIZE,
                            tskIDLE_PRIORITY + 2,
                            mainLOGGING_MESSAGE_QUEUE_LENGTH);

}
/*****************************************************************************************
End of function prvMiscInitialization
****************************************************************************************/
/*-----------------------------------------------------------*/

static void prvDisplayInitialize( void )
{
    static TaskHandle_t s_gui_task_handle = NULL;

    if( s_gui_task_handle == NULL )
    {
        BaseType_t xCreateResult;

        vApplicationEnsureEmwinFrameBufferReserved();

        configPRINTF( ( "GUI task create call: heap=%lu main_hwm=%lu\r\n",
                        ( unsigned long ) xPortGetFreeHeapSize(),
                        ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
        xCreateResult = xTaskCreate( gui_task,
                                     "gui",
                                     appmainGUI_TASK_STACK_SIZE,
                                     get_task_info(),
                                     appmainGUI_TASK_PRIORITY,
                                     &s_gui_task_handle );
        configPRINTF( ( "GUI task create returned: result=%ld handle=%08lx heap=%lu main_hwm=%lu\r\n",
                        ( long ) xCreateResult,
                        ( unsigned long ) s_gui_task_handle,
                        ( unsigned long ) xPortGetFreeHeapSize(),
                        ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );

        if( xCreateResult == pdPASS )
        {
            get_task_info()->gui_task_handle = s_gui_task_handle;
        }
    }
}
/*-----------------------------------------------------------*/

static void prvWaitForGuiInitialization( void )
{
    const TickType_t xStartTick = xTaskGetTickCount();
    TickType_t xLastLogTick = xStartTick;
    const TickType_t xTimeoutTicks = pdMS_TO_TICKS( appmainGUI_INIT_WAIT_TIMEOUT_MS );
    const TickType_t xLogIntervalTicks = pdMS_TO_TICKS( appmainGUI_INIT_WAIT_LOG_INTERVAL_MS );

    while( get_task_info()->gui_initialize_complete_flag == 0UL )
    {
        const TickType_t xNowTick = xTaskGetTickCount();
        const TickType_t xWaitedTicks = xNowTick - xStartTick;

        if( xWaitedTicks >= xTimeoutTicks )
        {
            configPRINTF( ( "GUI init wait timeout: waited=%lu heap=%lu main_hwm=%lu\r\n",
                            ( unsigned long ) ( xWaitedTicks * portTICK_PERIOD_MS ),
                            ( unsigned long ) xPortGetFreeHeapSize(),
                            ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
            break;
        }

        if( ( xNowTick - xLastLogTick ) >= xLogIntervalTicks )
        {
            configPRINTF( ( "GUI init wait: waited=%lu heap=%lu main_hwm=%lu\r\n",
                            ( unsigned long ) ( xWaitedTicks * portTICK_PERIOD_MS ),
                            ( unsigned long ) xPortGetFreeHeapSize(),
                            ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
            xLastLogTick = xNowTick;
        }

        vTaskDelay( pdMS_TO_TICKS( 100UL ) );
    }

    configPRINTF( ( "GUI init wait done: ready=%lu waited=%lu heap=%lu main_hwm=%lu\r\n",
                    ( unsigned long ) get_task_info()->gui_initialize_complete_flag,
                    ( unsigned long ) ( ( xTaskGetTickCount() - xStartTick ) * portTICK_PERIOD_MS ),
                    ( unsigned long ) xPortGetFreeHeapSize(),
                    ( unsigned long ) uxTaskGetStackHighWaterMark( NULL ) ) );
}
/*-----------------------------------------------------------*/

static void prvStartBoardApplicationTasks( void )
{
    if( appmainENABLE_BOARD_GUI_DEPENDENCY != 0 )
    {
        prvDisplayInitialize();
        prvWaitForGuiInitialization();
    }

    /* Phase 8b 第3次 段階5-4c-3 (#57): SD update task を起動。
     * sdcard_task は SD カード挿抜検出 + 自動 mount + firm_update 進捗監視 +
     * GUI 連動を行う。gui_task の完了通知を待ってから動き始める設計。 */
    if( appmainENABLE_BOARD_SDCARD_TASK != 0 )
    {
        static TaskHandle_t s_sdcard_task_handle = NULL;
        if( s_sdcard_task_handle == NULL )
        {
            ( void ) xTaskCreate( sdcard_task,
                                  "sdcard",
                                  appmainSDCARD_TASK_STACK_SIZE,
                                  get_task_info(),
                                  appmainSDCARD_TASK_PRIORITY,
                                  &s_sdcard_task_handle );
            get_task_info()->sdcard_task_handle = s_sdcard_task_handle;
        }
    }

    /* Phase 8b 第3次 段階5-5 (#58): serial flash (Quad SPI) task を起動。
     * Macronix MX25L 32Mbit に対する erase/write/read テスト harness。
     * gui_task からの xTaskNotifyGive で wake-up される (段階5-x で復活)。 */
    if( appmainENABLE_BOARD_SERIAL_FLASH_TASK != 0 )
    {
        static TaskHandle_t s_serial_flash_task_handle = NULL;
        if( s_serial_flash_task_handle == NULL )
        {
            ( void ) xTaskCreate( serial_flash_task,
                                  "serial_flash",
                                  appmainSERIAL_FLASH_TASK_STACK_SIZE,
                                  get_task_info(),
                                  appmainSERIAL_FLASH_TASK_PRIORITY,
                                  &s_serial_flash_task_handle );
            get_task_info()->serial_flash_task_handle = s_serial_flash_task_handle;
        }
    }

    /* Phase 8b 第3次 段階5-6 (#59): audio task placeholder を起動。
     * legacy aws_demos と同じく実装は永久 sleep のみで、実 audio 機能は無い。
     * 段階5-6b 以降で SSI/DMA を取り込んだ際に本実装に差し替える。 */
    if( appmainENABLE_BOARD_AUDIO_TASK != 0 )
    {
        static TaskHandle_t s_audio_task_handle = NULL;
        if( s_audio_task_handle == NULL )
        {
            ( void ) xTaskCreate( audio_task,
                                  "audio",
                                  appmainAUDIO_TASK_STACK_SIZE,
                                  get_task_info(),
                                  appmainAUDIO_TASK_PRIORITY,
                                  &s_audio_task_handle );
            get_task_info()->audio_task_handle = s_audio_task_handle;
        }
    }
}
/*-----------------------------------------------------------*/

static void prvDisplayWriteBanner( void )
{
    char cVersionLine[96];

    prvDisplayWrite("\r\n");
    prvDisplayWrite("RX72N Envision Kit\r\n");
    prvDisplayWrite("AWS FreeRTOS IoT Reference\r\n");
    prvDisplayWrite("Implementation Demo\r\n");
    prvDisplayWrite("----------------------------------------\r\n");

    (void) sprintf(cVersionLine,
                   "Firmware: %u.%u.%u\r\n",
                   (unsigned int) APP_VERSION_MAJOR,
                   (unsigned int) APP_VERSION_MINOR,
                   (unsigned int) APP_VERSION_BUILD);
    prvDisplayWrite(cVersionLine);

    prvDisplayWrite("OS: " democonfigOS_NAME " " democonfigOS_VERSION "\r\n");
    prvDisplayWrite("MQTT: " democonfigMQTT_LIB "\r\n");

    (void) sprintf(cVersionLine,
                   "BSP: %u.%u\r\n",
                   (unsigned int) R_BSP_VERSION_MAJOR,
                   (unsigned int) R_BSP_VERSION_MINOR);
    prvDisplayWrite(cVersionLine);

    prvDisplayWrite("Built: " __DATE__ " " __TIME__ "\r\n");
    prvDisplayWrite("----------------------------------------\r\n");
}
/*-----------------------------------------------------------*/

static void prvDisplayWrite( const char * pcMessage )
{
    if( ( pdFALSE != xDisplayInitialized ) && ( NULL != pcMessage ) )
    {
        vApplicationLcdLogString(pcMessage, (unsigned short) strlen(pcMessage));
    }
}
/*-----------------------------------------------------------*/

void vApplicationLcdLogString( const char * pcMessage, unsigned short usStringLength )
{
    /* Stub: r_simple_graphic_rx removed.
     * Will be replaced with emWin GUI_DispString() in 段階5-2.
     * UART logging continues unaffected. */
    (void) pcMessage;
    (void) usStringLength;
}
/*-----------------------------------------------------------*/

/**********************************************************************************************************************
 * Function Name: vApplicationDaemonTaskStartupHook
 * Description  : .
 * Return Value : .
 *********************************************************************************************************************/
void vApplicationDaemonTaskStartupHook(void)
{
}
/*****************************************************************************************
End of function vApplicationDaemonTaskStartupHook
****************************************************************************************/

/*-----------------------------------------------------------*/

/**********************************************************************************************************************
 * Function Name: vApplicationGetIdleTaskMemory
 * Description  : configUSE_STATIC_ALLOCATION is set to 1, so the application must provide an
 *                implementation of vApplicationGetIdleTaskMemory() to provide the memory that is
 *                used by the Idle task.
 * Arguments    : ppxIdleTaskTCBBuffer
 *              : ppxIdleTaskStackBuffer
 *              : pulIdleTaskStackSize
 * Return Value : .
 *********************************************************************************************************************/
void vApplicationGetIdleTaskMemory(StaticTask_t ** ppxIdleTaskTCBBuffer,
                                    StackType_t ** ppxIdleTaskStackBuffer,
                                    uint32_t * pulIdleTaskStackSize)
{
    /* If the buffers to be provided to the Idle task are declared inside this
     * function then they must be declared static - otherwise they will be allocated on
     * the stack and so not exists after this function exits. */
    static StaticTask_t xIdleTaskTCB;
    static StackType_t uxIdleTaskStack[configMINIMAL_STACK_SIZE];

    /* Pass out a pointer to the StaticTask_t structure in which the Idle
     * task's state will be stored. */
    *ppxIdleTaskTCBBuffer = &xIdleTaskTCB;

    /* Pass out the array that will be used as the Idle task's stack. */
    *ppxIdleTaskStackBuffer = uxIdleTaskStack;

    /* Pass out the size of the array pointed to by *ppxIdleTaskStackBuffer.
     * Note that, as the array is necessarily of type StackType_t,
     * configMINIMAL_STACK_SIZE is specified in words, not bytes. */
    *pulIdleTaskStackSize = configMINIMAL_STACK_SIZE;
}
/*****************************************************************************************
End of function vApplicationGetIdleTaskMemory
****************************************************************************************/
/*-----------------------------------------------------------*/

/**********************************************************************************************************************
 * Function Name: vApplicationGetTimerTaskMemory
 * Description  : This is to provide the memory that is used by the RTOS daemon/time task.
 *
 *                If configUSE_STATIC_ALLOCATION is set to 1, so the application must provide an
 *                implementation of vApplicationGetTimerTaskMemory() to provide the memory that is
 *                used by the RTOS daemon/time task.
 * Arguments    : ppxTimerTaskTCBBuffer
 *              : ppxTimerTaskStackBuffer
 *              : pulTimerTaskStackSize
 * Return Value : .
 *********************************************************************************************************************/
void vApplicationGetTimerTaskMemory(StaticTask_t ** ppxTimerTaskTCBBuffer,
                                    StackType_t ** ppxTimerTaskStackBuffer,
                                    uint32_t * pulTimerTaskStackSize)
{
    /* If the buffers to be provided to the Timer task are declared inside this
     * function then they must be declared static - otherwise they will be allocated on
     * the stack and so not exists after this function exits. */
    static StaticTask_t xTimerTaskTCB;
    static StackType_t uxTimerTaskStack[configTIMER_TASK_STACK_DEPTH];

    /* Pass out a pointer to the StaticTask_t structure in which the Idle
     * task's state will be stored. */
    *ppxTimerTaskTCBBuffer = &xTimerTaskTCB;

    /* Pass out the array that will be used as the Timer task's stack. */
    *ppxTimerTaskStackBuffer = uxTimerTaskStack;

    /* Pass out the size of the array pointed to by *ppxTimerTaskStackBuffer.
     * Note that, as the array is necessarily of type StackType_t,
     * configMINIMAL_STACK_SIZE is specified in words, not bytes. */
    *pulTimerTaskStackSize = configTIMER_TASK_STACK_DEPTH;
}
/*****************************************************************************************
End of function vApplicationGetTimerTaskMemory
****************************************************************************************/
/*-----------------------------------------------------------*/

#ifndef iotconfigUSE_PORT_SPECIFIC_HOOKS

/**********************************************************************************************************************
 * Function Name: vApplicationMallocFailedHook
 * Description  : Warn user if pvPortMalloc fails.
 *
 *                Called if a call to pvPortMalloc() fails because there is insufficient
 *                free memory available in the FreeRTOS heap.  pvPortMalloc() is called
 *                internally by FreeRTOS API functions that create tasks, queues, software
 *                timers, and semaphores.  The size of the FreeRTOS heap is set by the
 *                configTOTAL_HEAP_SIZE configuration constant in FreeRTOSConfig.h.
 * Argument     :
 * Return Value : .
 *********************************************************************************************************************/
void vApplicationMallocFailedHook( void )
    {
        configPRINT_STRING(("ERROR: Malloc failed to allocate memory\r\n"));
        taskDISABLE_INTERRUPTS();

        for (;;)
        {
            /* Loop forever */
        }
    }
/*****************************************************************************************
End of function vApplicationMallocFailedHook
****************************************************************************************/

/*-----------------------------------------------------------*/

/**********************************************************************************************************************
 * Function Name: vApplicationStackOverflowHook
 * Description  : Loop forever if stack overflow is detected.
 *                If configCHECK_FOR_STACK_OVERFLOW is set to 1,
 *                this hook provides a location for applications to
 *                define a response to a stack overflow.
 *
 *                Use this hook to help identify that a stack overflow
 *                has occurred.
 * Arguments    : xTask
 *              : pcTaskName
 * Return Value : .
 *********************************************************************************************************************/
void vApplicationStackOverflowHook(TaskHandle_t xTask,
                                        char * pcTaskName)
    {
        configPRINT_STRING(("ERROR: stack overflow\r\n"));
        portDISABLE_INTERRUPTS();

        /* Unused Parameters */
        (void) xTask;
        (void) pcTaskName;

        for (;;)
        {
            /* Loop forever */
        }
    }
/*****************************************************************************************
End of function vApplicationStackOverflowHook
****************************************************************************************/

#endif /* iotconfigUSE_PORT_SPECIFIC_HOOKS */
/*-----------------------------------------------------------*/

#if ( ipconfigUSE_LLMNR != 0 ) || ( ipconfigUSE_NBNS != 0 ) || ( ipconfigDHCP_REGISTER_HOSTNAME == 1 )

/**********************************************************************************************************************
 * Function Name: pcApplicationHostnameHook
 * Description  : This function will be called during the DHCP: the machine will be registered
 *                 with an IP address plus this name.
 *                 Note: Please make sure vprvCacheInit() is called before this function, because
 *                 it retrieves thingname value from KeyValue table.
 * Return Value : .
 *********************************************************************************************************************/
const char * pcApplicationHostnameHook(void)
    {
#if defined(__TEST__)
        return clientcredentialIOT_THING_NAME;
#else
    {
        /* The string returned by this API is stipulated to be a maximum of 32 characters. */
        static char s_buff[32];
        memset (s_buff, 0x00, sizeof(s_buff));

        size_t valueLength = prvGetCacheEntryLength(KVS_CORE_THING_NAME);

        /* Process for thing name input by CLI. */
        if (valueLength > 0)
        {
            if (valueLength > 31)
            {
                configPRINT_STRING(("Warning: thing name with null-terminate string is longer than 32 characters.\r\n"));
                valueLength = 31;
            }
            size_t xLength = xReadEntry(KVS_CORE_THING_NAME, s_buff, valueLength);
            if (0 != xLength)
            {
                s_buff[valueLength] = '\0';
                return s_buff;
            }
            else
            {
                valueLength = strlen(clientcredentialIOT_THING_NAME);
                if (valueLength > 31)
                {
                    configPRINT_STRING(("Warning: thing name with null-terminate string is longer than 32 characters.\r\n"));
                    valueLength = 31;
                }
                strncpy(s_buff, clientcredentialIOT_THING_NAME, valueLength);
                s_buff[valueLength] = '\0';
                return s_buff;
            }
        }
        /* Process for thing name in aws_clientcredential.h. */
        else
        {
            valueLength = strlen(clientcredentialIOT_THING_NAME);
            if (valueLength > 31)
            {
                configPRINT_STRING(("Warning: thing name with null-terminate string is longer than 32 characters.\r\n"));
                valueLength = 31;
            }
            strncpy(s_buff, clientcredentialIOT_THING_NAME, valueLength);
            s_buff[valueLength] = '\0';
            return s_buff;
        }
    }
#endif
    }
#endif
/*****************************************************************************************
 End of function pcApplicationHostnameHook
 ****************************************************************************************/

/**********************************************************************************************************************
 * Function Name: ApplicationCounter
 * Description  : .
 * Argument     : xWaitTime
 * Return Value : .
 *********************************************************************************************************************/
bool ApplicationCounter(uint32_t xWaitTime)
{
    TickType_t xStart;
    TickType_t xCurrent;
    bool DEMO_TEST = pdTRUE;
    const TickType_t xWaitTicks = pdMS_TO_TICKS(xWaitTime);
    signed char cRxChar;
    xStart = xTaskGetTickCount();
    configPRINTF(("Press CLI and enter to switch to CLI mode\r\n"));
    do
    {
        vTaskDelay(1);
        xCurrent = xTaskGetTickCount();

        cRxChar = vISR_Routine();
        if ((0 != cRxChar))
        {
            configPRINTF(("Going to FreeRTOS-CLI\r\n"));
            DEMO_TEST = pdFALSE;
            break;
        }
    }
    while ((xCurrent - xStart) < xWaitTicks);
    return DEMO_TEST;
}
/*****************************************************************************************
 End of function ApplicationCounter
 ****************************************************************************************/

/**********************************************************************************************************************
 * Function Name: vISR_Routine
 * Description  : .
 * Return Value : .
 *********************************************************************************************************************/
signed char vISR_Routine(void)
{
    BaseType_t xTaskWokenByReceive = pdFALSE;
    extern signed char cRxedChar;
    return cRxedChar;
}
/*****************************************************************************************
 End of function vISR_Routine
 ****************************************************************************************/

static BaseType_t prvShouldAutoProvisionFromClientCredentials( void )
{
    if( clientcredentialMQTT_BROKER_ENDPOINT[ 0 ] == '\0' )
    {
        return pdFALSE;
    }

    if( strcmp( clientcredentialIOT_THING_NAME, "dummy" ) == 0 )
    {
        return pdFALSE;
    }

    if( ( keyCLIENT_CERTIFICATE_PEM == NULL ) || ( keyCLIENT_PRIVATE_KEY_PEM == NULL ) )
    {
        return pdFALSE;
    }

    if( ( prvGetCacheEntryLength( KVS_CORE_THING_NAME ) > 0U ) &&
        ( prvGetCacheEntryLength( KVS_CORE_MQTT_ENDPOINT ) > 0U ) )
    {
        return pdFALSE;
    }

    return pdTRUE;
}
/**********************************************************************************************************************
 * Function Name: vAssignCredentials
 * Description  : Handle pre-provisioning.
 * Return Value : .
 *********************************************************************************************************************/
BaseType_t vAssignCredentials(void)
{
    BaseType_t xCommitResult;
    int32_t xStoreResult;

    /* Write thing name */
    char *pValue = democonfigCLIENT_IDENTIFIER;
    xStoreResult = xprvWriteCacheEntry(strlen("thingname"), "thingname", strlen(pValue), pValue);
    if( xStoreResult < 0 )
    {
        return pdFALSE;
    }

    /* Write endpoint */
    pValue = democonfigMQTT_BROKER_ENDPOINT;
    xStoreResult = xprvWriteCacheEntry(strlen("endpoint"), "endpoint", strlen(pValue), pValue);
    if( xStoreResult < 0 )
    {
        return pdFALSE;
    }

    /* Write certificate */
    pValue = keyCLIENT_CERTIFICATE_PEM;
    xStoreResult = xprvWriteCacheEntry(strlen("cert"), "cert", strlen(pValue), pValue);
    if( xStoreResult < 0 )
    {
        return pdFALSE;
    }

    /* Write private key */
    pValue = keyCLIENT_PRIVATE_KEY_PEM;
    xStoreResult = xprvWriteCacheEntry(strlen("key"), "key", strlen(pValue), pValue);
    if( xStoreResult < 0 )
    {
        return pdFALSE;
    }

    /* Write code signing certificate */
    pValue = otapalconfigCODE_SIGNING_CERTIFICATE;
    xStoreResult = xprvWriteCacheEntry(strlen("codesigncert"), "codesigncert", strlen(pValue), pValue);
    if( xStoreResult < 0 )
    {
        return pdFALSE;
    }

    /* Write root CA */
    pValue = democonfigROOT_CA_PEM;
    xStoreResult = xprvWriteCacheEntry(strlen("rootca"), "rootca", strlen(pValue), pValue);
    if( xStoreResult < 0 )
    {
        return pdFALSE;
    }

    /* Write cache to DF */
    xCommitResult = KVStore_xCommitChanges();

    return xCommitResult;
}
/**********************************************************************************************************************
 End of function vAssignCredentials
 *********************************************************************************************************************/
/**********************************************************************************************************************
 * Function Name: OtaSelfTest
 * Description  : The test function executed during the self-check process during an OTA update
 * Return Value : pdTRUE (if the self-test was successful)
 *                pdFALSE (if the self-test was failed)
 *                Always return pdTRUE since the initial firmware was evaluated during the manufacturing process.
 *********************************************************************************************************************/
BaseType_t OtaSelfTest(void)
{
	return pdTRUE;
}
