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
 * File Name    : tcp_send_performance_task.c
 * Description  : Phase 8b 第3次 段階5-7 B-1 (rx72n-envision-kit#60) で legacy aws_demos の同名ファイル
 *                (vendors/.../renesas_code/tcp_send_performance_task.c, 168行) を v3 baseline に取り込んだもの。
 *                iperf 互換の TCP throughput 測定 task (送信側)。
 *
 *                v3 移植時の主な置換:
 *                - iot_secure_sockets.h / platform/iot_network.h / GUI.h / DIALOG.h: 本体未使用のため削除
 *                - r_simple_filesystem_on_dataflash (SFD): v3 では LittleFS 置換済のため SFD ベース config
 *                  読み出しブロックを削除。サーバ IP / port は #define で暫定 hardcode (B-2 で KVStore 化)
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

#define SEND_DATA_UNIT_LENGTH ( 1460 * 3 )

/* Phase 8b 第3次 段階5-7 B-1: SFD ベース config 読み出しの暫定置換。
 * server IP/port は B-2 で KVStore 化する。それまでは個別 build でユーザが
 * 値を変更する想定の placeholder default。 */
#define TCP_PERF_SERVER_IP_OCTET1   ( 192 )
#define TCP_PERF_SERVER_IP_OCTET2   ( 168 )
#define TCP_PERF_SERVER_IP_OCTET3   ( 1 )
#define TCP_PERF_SERVER_IP_OCTET4   ( 100 )
#define TCP_PERF_SERVER_PORT        ( 5001 )

void tcp_send_performance_task( void * pvParameters );

static uint8_t send_buffer[ SEND_DATA_UNIT_LENGTH ];

void tcp_send_performance_task( void * pvParameters )
{
    Socket_t xSocket;
    uint32_t tcp_send_performance_server_ip_address;
    struct freertos_sockaddr xIperfServerAddress;
    BaseType_t return_value;

    ( void ) pvParameters;

    configPRINTF( ( "tcp_send_performance_task: server %d.%d.%d.%d:%d (B-1 hardcoded)\r\n",
                    TCP_PERF_SERVER_IP_OCTET1, TCP_PERF_SERVER_IP_OCTET2,
                    TCP_PERF_SERVER_IP_OCTET3, TCP_PERF_SERVER_IP_OCTET4,
                    TCP_PERF_SERVER_PORT ) );

    /* We should wait for the network to be up before getting time. */
    while( FreeRTOS_IsNetworkUp() == pdFALSE )
    {
        vTaskDelay( 300 );
    }

    /* Create a socket. */
    xSocket = FreeRTOS_socket( FREERTOS_AF_INET,
                               FREERTOS_SOCK_STREAM, /* FREERTOS_SOCK_STREAM for TCP. */
                               FREERTOS_IPPROTO_TCP );
    configASSERT( xSocket != FREERTOS_INVALID_SOCKET );

    /* Connect to the iperf server. */
    tcp_send_performance_server_ip_address = FreeRTOS_inet_addr_quick( TCP_PERF_SERVER_IP_OCTET1,
                                                                       TCP_PERF_SERVER_IP_OCTET2,
                                                                       TCP_PERF_SERVER_IP_OCTET3,
                                                                       TCP_PERF_SERVER_IP_OCTET4 );
    xIperfServerAddress.sin_port = FreeRTOS_htons( TCP_PERF_SERVER_PORT );
    xIperfServerAddress.sin_addr = tcp_send_performance_server_ip_address;

    if( FreeRTOS_connect( xSocket, &xIperfServerAddress, sizeof( xIperfServerAddress ) ) == 0 )
    {
        configPRINTF( ( "Connecting iperf server: OK.\r\n" ) );

        while( 1 )
        {
            /* Send the string to the socket. */
            return_value = FreeRTOS_send( xSocket,                  /* The socket being sent to. */
                                          ( void * ) send_buffer,   /* The data being sent. */
                                          SEND_DATA_UNIT_LENGTH,    /* The length of the data being sent. */
                                          0 );                      /* No flags. */
            if( 0 > return_value )
            {
                break;
            }
        }
    }
    else
    {
        configPRINTF( ( "Connecting iperf server: NG.\r\n" ) );
    }
    configPRINTF( ( "Shutting down connection to iperf server.\r\n" ) );
    FreeRTOS_shutdown( xSocket, FREERTOS_SHUT_RDWR );

    /* finish */
    while( 1 )
    {
        vTaskDelay( 0xffffffff );
    }
}
