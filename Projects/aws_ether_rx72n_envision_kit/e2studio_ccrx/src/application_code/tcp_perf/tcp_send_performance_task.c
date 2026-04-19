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
 * Description  : Phase 8b 第3次 段階5-7 (rx72n-envision-kit#60 / #61) で legacy aws_demos の同名ファイル
 *                (vendors/.../renesas_code/tcp_send_performance_task.c, 168行) を v3 baseline に取り込んだもの。
 *                iperf 互換の TCP throughput 測定 task (送信側)。
 *
 *                v3 移植時の主な置換:
 *                - iot_secure_sockets.h / platform/iot_network.h / GUI.h / DIALOG.h: 本体未使用のため削除
 *                - SOCKETS_Shutdown: deprecated のため FreeRTOS_shutdown に置換
 *                - r_sys_time_rx_if.h: 本体未使用のため削除
 *
 *                B-2 (#61) で SFD ベース config 読み出しの v3 相当として KVStore (store.h) を使用。
 *                CLI から `conf set tcpperfip 192.168.1.100` / `conf set tcpperfport 5001` で設定可能。
 *                KVStore に値が無い場合は configPRINTF で warn を出して永久 sleep
 *                (legacy SFD 不在時と同等の挙動)。
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
#include "store.h"

#define SEND_DATA_UNIT_LENGTH ( 1460 * 3 )

void tcp_send_performance_task( void * pvParameters );

static uint8_t send_buffer[ SEND_DATA_UNIT_LENGTH ];

void tcp_send_performance_task( void * pvParameters )
{
    Socket_t xSocket;
    uint32_t tcp_send_performance_server_ip_address;
    struct freertos_sockaddr xIperfServerAddress;
    BaseType_t return_value;
    char * ip_string = NULL;
    char * port_string = NULL;
    size_t ip_length;
    size_t port_length;
    unsigned int ip_octet1, ip_octet2, ip_octet3, ip_octet4;
    unsigned int port_value;

    ( void ) pvParameters;

    /* Read iperf server IP / port from KVStore (B-2 で SFD ベース読み出しを置換)。
     * CLI: `conf set tcpperfip 192.168.1.100` / `conf set tcpperfport 5001` で設定。 */
    ip_length = prvGetCacheEntryLength( KVS_TCP_PERF_SERVER_IP );
    port_length = prvGetCacheEntryLength( KVS_TCP_PERF_SERVER_PORT );

    if( ( ip_length == 0U ) || ( port_length == 0U ) )
    {
        configPRINTF( ( "tcp_send_performance_task: KVStore に tcpperfip / tcpperfport が未設定 (ip_len=%u, port_len=%u)。永久 sleep します。\r\n",
                        ( unsigned int ) ip_length, ( unsigned int ) port_length ) );
        while( 1 )
        {
            vTaskDelay( 0xffffffff );
        }
    }

    ip_string = GetStringValue( KVS_TCP_PERF_SERVER_IP, ip_length );
    port_string = GetStringValue( KVS_TCP_PERF_SERVER_PORT, port_length );

    if( ( ip_string == NULL ) || ( port_string == NULL ) )
    {
        configPRINTF( ( "tcp_send_performance_task: KVStore 読み出し失敗。永久 sleep します。\r\n" ) );
        if( ip_string != NULL ) { vPortFree( ip_string ); }
        if( port_string != NULL ) { vPortFree( port_string ); }
        while( 1 )
        {
            vTaskDelay( 0xffffffff );
        }
    }

    if( ( sscanf( ip_string, "%u.%u.%u.%u", &ip_octet1, &ip_octet2, &ip_octet3, &ip_octet4 ) != 4 ) ||
        ( sscanf( port_string, "%u", &port_value ) != 1 ) ||
        ( ip_octet1 > 255U ) || ( ip_octet2 > 255U ) || ( ip_octet3 > 255U ) || ( ip_octet4 > 255U ) ||
        ( port_value == 0U ) || ( port_value > 65535U ) )
    {
        configPRINTF( ( "tcp_send_performance_task: KVStore の値が不正 (ip=%s, port=%s)。永久 sleep します。\r\n",
                        ip_string, port_string ) );
        vPortFree( ip_string );
        vPortFree( port_string );
        while( 1 )
        {
            vTaskDelay( 0xffffffff );
        }
    }

    configPRINTF( ( "tcp_send_performance_task: server %u.%u.%u.%u:%u (KVStore)\r\n",
                    ip_octet1, ip_octet2, ip_octet3, ip_octet4, port_value ) );

    vPortFree( ip_string );
    vPortFree( port_string );

    /* We should wait for the network to be up before getting time. */
    while( FreeRTOS_IsNetworkUp() == pdFALSE )
    {
        vTaskDelay( 300 );
    }

    /* Network up 後も socket pool / IP task の初期化が settle するまで余裕を待つ。
     * legacy aws_demos では init 順序の偶然で問題化しなかったが、v3 baseline は
     * tcp_perf task が高 priority (configMAX_PRIORITIES - 1) のため main_task より
     * 先に走る。FreeRTOS_socket() が一時的に FREERTOS_INVALID_SOCKET を返す race
     * があり、configASSERT で system halt → CLI 不能になっていた。 */
    vTaskDelay( pdMS_TO_TICKS( 2000 ) );

    /* Create a socket — retry on transient INVALID_SOCKET (socket pool warm-up race)。 */
    {
        int retry;
        xSocket = FREERTOS_INVALID_SOCKET;
        for( retry = 0; retry < 30; retry++ )
        {
            xSocket = FreeRTOS_socket( FREERTOS_AF_INET,
                                       FREERTOS_SOCK_STREAM, /* FREERTOS_SOCK_STREAM for TCP. */
                                       FREERTOS_IPPROTO_TCP );
            if( xSocket != FREERTOS_INVALID_SOCKET )
            {
                break;
            }
            configPRINTF( ( "tcp_send_perf: FreeRTOS_socket() returned INVALID_SOCKET, retry %d/30\r\n", retry + 1 ) );
            vTaskDelay( pdMS_TO_TICKS( 1000 ) );
        }
        if( xSocket == FREERTOS_INVALID_SOCKET )
        {
            configPRINTF( ( "tcp_send_perf: FreeRTOS_socket() failed permanently, sleep forever.\r\n" ) );
            while( 1 )
            {
                vTaskDelay( 0xffffffff );
            }
        }
    }

    /* Connect to the iperf server. */
    tcp_send_performance_server_ip_address = FreeRTOS_inet_addr_quick( ( uint8_t ) ip_octet1,
                                                                       ( uint8_t ) ip_octet2,
                                                                       ( uint8_t ) ip_octet3,
                                                                       ( uint8_t ) ip_octet4 );
    xIperfServerAddress.sin_port = FreeRTOS_htons( ( uint16_t ) port_value );
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
