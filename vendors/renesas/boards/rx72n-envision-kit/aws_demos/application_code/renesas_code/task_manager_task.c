
/**********************************************************************************************************************
 * DISCLAIMER
 * This software is supplied by Renesas Electronics Corporation and is only intended for use with Renesas products. No
 * other uses are authorized. This software is owned by Renesas Electronics Corporation and is protected under all
 * applicable laws, including copyright laws.
 * THIS SOFTWARE IS PROVIDED "AS IS" AND RENESAS MAKES NO WARRANTIES REGARDING
 * THIS SOFTWARE, WHETHER EXPRESS, IMPLIED OR STATUTORY, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. ALL SUCH WARRANTIES ARE EXPRESSLY DISCLAIMED. TO THE MAXIMUM
 * EXTENT PERMITTED NOT PROHIBITED BY LAW, NEITHER RENESAS ELECTRONICS CORPORATION NOR ANY OF ITS AFFILIATED COMPANIES
 * SHALL BE LIABLE FOR ANY DIRECT, INDIRECT, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES FOR ANY REASON RELATED TO THIS
 * SOFTWARE, EVEN IF RENESAS OR ITS AFFILIATES HAVE BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
 * Renesas reserves the right, without notice, to make changes to this software and to discontinue the availability of
 * this software. By using this software, you agree to the additional terms and conditions found by accessing the
 * following link:
 * http://www.renesas.com/disclaimer
 *
 * Copyright (C) 2014(2020) Renesas Electronics Corporation. All rights reserved.
 *********************************************************************************************************************/
/**********************************************************************************************************************
 * File Name    : task_manager_task.c
 * Description  : task_manager_task
 *********************************************************************************************************************/
/**********************************************************************************************************************
 * History : DD.MM.YYYY Version Description
 *         : 29.12.2019 1.00 First Release
 *********************************************************************************************************************/

/******************************************************************************
 Includes   <System Includes> , "Project Includes"
 ******************************************************************************/
/* for using C standard library */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* for using FIT Module */
#include "platform.h"
#include "r_sys_time_rx_if.h"

/* for using Segger emWin */
#include "GUI.h"
#include "DIALOG.h"

/* for using Amazon FreeRTOS */
#include "FreeRTOS.h"

/* FreeRTOS+TCP includes. */
#include "FreeRTOS_IP.h"

/* Key provisioning include. */
#include "aws_dev_mode_key_provisioning.h"

/* Includes for library initialization. */
#include "iot_demo_runner.h"
#include "aws_demo.h"

/* for RX72N Envision Kit system common header */
#include "rx72n_envision_kit_system.h"

/**********************************************************************************************************************
Typedef definitions
**********************************************************************************************************************/

/******************************************************************************
 External variables
 ******************************************************************************/

/******************************************************************************
 Private global variables
 ******************************************************************************/

/******************************************************************************
 External functions
 ******************************************************************************/

/*******************************************************************************
 global variables and functions
********************************************************************************/
void task_manager_task( void * pvParameters );
static BaseType_t prvHasRuntimeProvisioningInputs( void );

static BaseType_t prvHasRuntimeProvisioningInputs( void )
{
    const struct
    {
        const char * pcLabel;
        const char * pcDescription;
    } xRequiredObjects[] =
    {
        { client_private_key_label, "client private key" },
        { client_certificate_label, "client certificate" },
        { iot_thing_name_label, "IoT thing name" },
        { mqtt_broker_endpoint_label, "MQTT broker endpoint" },
    };
    size_t xIndex;

    for( xIndex = 0; xIndex < ( sizeof( xRequiredObjects ) / sizeof( xRequiredObjects[ 0 ] ) ); xIndex++ )
    {
        if( R_SFD_FindObject( ( uint8_t * ) xRequiredObjects[ xIndex ].pcLabel,
                              ( uint8_t ) strlen( xRequiredObjects[ xIndex ].pcLabel ) ) == SFD_HANDLE_INVALID )
        {
            FreeRTOS_printf( ( "task_manager_task: runtime credential missing: %s (%s)\r\n",
                               xRequiredObjects[ xIndex ].pcDescription,
                               xRequiredObjects[ xIndex ].pcLabel ) );
            return pdFALSE;
        }
    }

    return pdTRUE;
}

/******************************************************************************
 Function Name   : serial_terminal_task
 Description     : serial_terminal_task
 Arguments       : none
 Return value    : none
 ******************************************************************************/
void task_manager_task( void * pvParameters )
{
    TASK_INFO *task_info = (TASK_INFO *)pvParameters;

    /* wait completing gui initializing */
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

    /* We should wait for the network to be up before we run any demos. */
    while( FreeRTOS_IsNetworkUp() == pdFALSE )
    {
        vTaskDelay(300);
    }
	FreeRTOS_printf( ( "The network is up and running\n" ) );

    if( prvHasRuntimeProvisioningInputs() == pdFALSE )
    {
        FreeRTOS_printf( ( "task_manager_task: runtime provisioning inputs are incomplete; "
                           "skipping dev-mode key provisioning and demo start until next reset.\r\n" ) );

        while( 1 )
        {
            vTaskDelay( 1000 );
        }
    }

    /* start tracealyzer */
    vTraceEnable(TRC_INIT);
    vTraceEnable(TRC_START);

    /* Provision the device with AWS certificate and private key. */
    vDevModeKeyProvisioning();

    /* Run all demos. */
    DEMO_RUNNER_RunDemos();

    while(1)
    {
        vTaskDelay(1000);
    }
}
