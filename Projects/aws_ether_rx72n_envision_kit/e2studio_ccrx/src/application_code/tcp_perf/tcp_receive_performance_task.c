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
 * Copyright (C) 2020 Renesas Electronics Corporation. All rights reserved.
 *********************************************************************************************************************/
/**********************************************************************************************************************
 * File Name    : tcp_receive_performance_task.c
 * Description  : Phase 8b 第3次 段階5-7 B-1 (rx72n-envision-kit#60) で legacy aws_demos の同名ファイル
 *                (vendors/.../renesas_code/tcp_receive_performance_task.c, 143行) を v3 baseline に取り込んだもの。
 *                iperf 互換の TCP throughput 測定 task (受信側、port 5001 listen)。
 *
 *                v3 移植時の主な置換:
 *                - iot_secure_sockets.h / platform/iot_network.h / GUI.h / DIALOG.h: 本体未使用のため削除
 *                - r_simple_filesystem_on_dataflash_if.h: 本 task は元から SFD 未使用、念のため削除
 *                - SocketsSockaddr_t: legacy iot_secure_sockets 型のため struct freertos_sockaddr に統一
 *                - SOCKETS_Shutdown: deprecated のため FreeRTOS_shutdown に置換
 *                - r_sys_time_rx_if.h: 本体未使用のため削除
 *********************************************************************************************************************/

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "FreeRTOS_IP.h"
#include "FreeRTOS_DNS.h"
#include "FreeRTOS_Sockets.h"

#include "rx72n_envision_kit_system.h"

#define RECEIVE_DATA_UNIT_LENGTH ( 1460 * 3 )

/* iperf default server port (legacy 同等) */
#define TCP_PERF_LISTEN_PORT     ( 5001 )

void tcp_receive_performance_task( void * pvParameters );

static uint8_t receive_buffer[ RECEIVE_DATA_UNIT_LENGTH ];

void tcp_receive_performance_task( void * pvParameters )
{
    Socket_t xListeningSocket, xConnectedSocket;
    struct freertos_sockaddr xClient, xBindAddress;
    const BaseType_t xBacklog = 20;
    socklen_t xSize = sizeof( xClient );
    static const TickType_t xReceiveTimeOut = portMAX_DELAY;
    BaseType_t return_value;

    ( void ) pvParameters;

    while( 1 )
    {
        /* We should wait for the network to be up before getting time. */
        while( FreeRTOS_IsNetworkUp() == pdFALSE )
        {
            vTaskDelay( 300 );
        }

        /* Network up 後も socket pool / IP task 初期化が settle するまで余裕を待つ
         * (tcp_send_performance_task と同じ race 対策)。 */
        vTaskDelay( pdMS_TO_TICKS( 2000 ) );

        /* Create the socket — retry on transient INVALID_SOCKET。 */
        {
            int retry;
            xListeningSocket = FREERTOS_INVALID_SOCKET;
            for( retry = 0; retry < 30; retry++ )
            {
                xListeningSocket = FreeRTOS_socket( FREERTOS_AF_INET,
                                                    FREERTOS_SOCK_STREAM,
                                                    FREERTOS_IPPROTO_TCP );
                if( xListeningSocket != FREERTOS_INVALID_SOCKET )
                {
                    break;
                }
                configPRINTF( ( "tcp_receive_perf: FreeRTOS_socket() returned INVALID_SOCKET, retry %d/30\r\n", retry + 1 ) );
                vTaskDelay( pdMS_TO_TICKS( 1000 ) );
            }
            if( xListeningSocket == FREERTOS_INVALID_SOCKET )
            {
                configPRINTF( ( "tcp_receive_perf: FreeRTOS_socket() failed permanently, sleep forever.\r\n" ) );
                while( 1 )
                {
                    vTaskDelay( 0xffffffff );
                }
            }
        }

        /* Set a time out so accept() will just wait for a connection. */
        FreeRTOS_setsockopt( xListeningSocket,
                             0,
                             FREERTOS_SO_RCVTIMEO,
                             &xReceiveTimeOut,
                             sizeof( xReceiveTimeOut ) );

        /* Wait connect from the iperf client. */
        xBindAddress.sin_port = FreeRTOS_htons( TCP_PERF_LISTEN_PORT );

        /* Bind the socket to the port that the client RTOS task will send to. */
        FreeRTOS_bind( xListeningSocket, &xBindAddress, sizeof( xBindAddress ) );

        /* Set the socket into a listening state so it can accept connections.
         * The maximum number of simultaneous connections is limited to 20. */
        FreeRTOS_listen( xListeningSocket, xBacklog );

        /* Wait for incoming connections. */
        xConnectedSocket = FreeRTOS_accept( xListeningSocket, &xClient, &xSize );

        configPRINTF( ( "Connected from iperf client: OK.\r\n" ) );

        while( 1 )
        {
            /* Receive the string from the socket. */
            return_value = FreeRTOS_recv( xConnectedSocket,             /* The socket being received to. */
                                          ( void * ) receive_buffer,    /* The data being received. */
                                          RECEIVE_DATA_UNIT_LENGTH,     /* The length of the data being received. */
                                          0 );                          /* No flags. */
            if( 0 > return_value )
            {
                break;
            }
        }
        configPRINTF( ( "Shutting down connection from iperf client.\r\n" ) );
        FreeRTOS_shutdown( xConnectedSocket, FREERTOS_SHUT_RDWR );

        /* finish */
        while( 1 )
        {
            vTaskDelay( 0xffffffff );
        }
    }
}
