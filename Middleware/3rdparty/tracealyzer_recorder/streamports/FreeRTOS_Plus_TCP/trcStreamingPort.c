/*******************************************************************************
 * Trace Recorder Library for Tracealyzer v4.3.11
 * Stream port: FreeRTOS-Plus-TCP (rx72n-envision-kit Phase 8b 第3次 段階5-2 / #50)
 *
 * Adapted from the upstream `streamports/AFR_WIFI_LOCAL/trcStreamingPort.c`
 * (Percepio AB, 2018).  The legacy port relied on the Amazon FreeRTOS
 * `iot_secure_sockets.h` abstraction, which is not provided by the
 * iot-reference-rx (v202406.04-LTS-rx-1.2.0) baseline used by v3 builds.
 * This variant calls the FreeRTOS-Plus-TCP socket API (`FreeRTOS_socket`,
 * `FreeRTOS_connect`, `FreeRTOS_send`) directly.
 *
 * Status (段階5-2): build-clean wiring only.  IP / port resolution is hard
 * coded via the macros below so that the project links and `vTraceEnable()`
 * compiles.  The CLI / dataflash / LittleFS based runtime configuration that
 * the legacy aws_demos used (`dataflash write tracealyzerserveripaddress`)
 * will be ported back in a follow-up step once the dependent SD / CLI tasks
 * land in 段階5-3 / 5-7.  Until then this port can still complete the TCP
 * handshake and stream PSF data when the user:
 *   1. Sets `TRACEALYZER_SERVER_IP_*` below to the host PC IP.
 *   2. Builds, flashes, and runs the firmware after starting recording in
 *      Tracealyzer (Target Connection: TCP, Target Initiated).
 *
 * Tabs are used for indent in this file (1 tab = 4 spaces).
 *
 * Original copyright: Percepio AB, 2018.  www.percepio.com
 ******************************************************************************/

#include "trcRecorder.h"

#if (TRC_USE_TRACEALYZER_RECORDER == 1)
#if (TRC_CFG_RECORDER_MODE == TRC_RECORDER_MODE_STREAMING)

#include "FreeRTOS.h"
#include "task.h"
#include "FreeRTOS_IP.h"
#include "FreeRTOS_Sockets.h"

#include "trcExtensions.h"

/* -------------------------------------------------------------------------
 * Configuration knobs (placeholder defaults).
 *
 * These are intentionally compile-time defaults so段階5-2 can build cleanly
 * without depending on the legacy dataflash configuration store
 * (R_SFD_FindObject() / DATAFLASH_LABEL_NAME_TRACEALYZER_*).
 *
 * Override via `-D TRACEALYZER_SERVER_IP_OCT0=...` etc. on the compiler
 * command line, or replace this section with a CLI / LittleFS based lookup
 * once段階5-7 / 5-3 introduces the equivalent infrastructure.
 * --------------------------------------------------------------------------*/
#ifndef TRACEALYZER_SERVER_IP_OCT0
#define TRACEALYZER_SERVER_IP_OCT0   ( 192U )
#endif
#ifndef TRACEALYZER_SERVER_IP_OCT1
#define TRACEALYZER_SERVER_IP_OCT1   ( 168U )
#endif
#ifndef TRACEALYZER_SERVER_IP_OCT2
#define TRACEALYZER_SERVER_IP_OCT2   ( 1U )
#endif
#ifndef TRACEALYZER_SERVER_IP_OCT3
#define TRACEALYZER_SERVER_IP_OCT3   ( 100U )
#endif
#ifndef TRACEALYZER_SERVER_PORT
#define TRACEALYZER_SERVER_PORT      ( 12000U )  /* legacy default */
#endif

/* TCP send / receive timeouts.  Streaming should not block forever; if the
 * host PC is gone we fall through and let the recorder's TzCtrl task retry
 * on the next batch. */
#ifndef TRACEALYZER_TX_TIMEOUT_MS
#define TRACEALYZER_TX_TIMEOUT_MS    ( 200U )
#endif
#ifndef TRACEALYZER_RX_TIMEOUT_MS
#define TRACEALYZER_RX_TIMEOUT_MS    ( 0U )      /* non-blocking, recorder polls */
#endif

/* -------------------------------------------------------------------------
 * Module state
 * --------------------------------------------------------------------------*/
static Socket_t s_trace_socket = FREERTOS_INVALID_SOCKET;

/* -------------------------------------------------------------------------
 * prvInitSocket
 *
 * Called once from TRC_STREAM_PORT_INIT() (i.e. inside vTraceEnable()).
 * Opens a TCP socket and connects to the Tracealyzer host.  Failures call
 * vTraceStop() to suppress further trace activity until the next reset.
 * --------------------------------------------------------------------------*/
void prvInitSocket(void)
{
	struct freertos_sockaddr xRemoteAddress;
	TickType_t xSendTimeout = pdMS_TO_TICKS( TRACEALYZER_TX_TIMEOUT_MS );
	TickType_t xRecvTimeout = pdMS_TO_TICKS( TRACEALYZER_RX_TIMEOUT_MS );
	BaseType_t xConnectResult;

	s_trace_socket = FreeRTOS_socket( FREERTOS_AF_INET,
	                                  FREERTOS_SOCK_STREAM,
	                                  FREERTOS_IPPROTO_TCP );

	if( ( s_trace_socket == FREERTOS_INVALID_SOCKET ) || ( s_trace_socket == NULL ) )
	{
		/* Out of sockets / out of memory.  Disable tracing for this boot. */
		s_trace_socket = FREERTOS_INVALID_SOCKET;
		vTraceStop();
		return;
	}

	( void ) FreeRTOS_setsockopt( s_trace_socket,
	                              0,
	                              FREERTOS_SO_SNDTIMEO,
	                              &xSendTimeout,
	                              sizeof( xSendTimeout ) );
	( void ) FreeRTOS_setsockopt( s_trace_socket,
	                              0,
	                              FREERTOS_SO_RCVTIMEO,
	                              &xRecvTimeout,
	                              sizeof( xRecvTimeout ) );

	xRemoteAddress.sin_family = FREERTOS_AF_INET;
	xRemoteAddress.sin_port   = FreeRTOS_htons( TRACEALYZER_SERVER_PORT );
	xRemoteAddress.sin_address.ulIP_IPv4 = FreeRTOS_inet_addr_quick( TRACEALYZER_SERVER_IP_OCT0,
	                                                                 TRACEALYZER_SERVER_IP_OCT1,
	                                                                 TRACEALYZER_SERVER_IP_OCT2,
	                                                                 TRACEALYZER_SERVER_IP_OCT3 );

	xConnectResult = FreeRTOS_connect( s_trace_socket,
	                                   &xRemoteAddress,
	                                   sizeof( xRemoteAddress ) );

	if( xConnectResult != 0 )
	{
		( void ) FreeRTOS_closesocket( s_trace_socket );
		s_trace_socket = FREERTOS_INVALID_SOCKET;
		vTraceStop();
	}
}

/* -------------------------------------------------------------------------
 * prvWriteToSocket
 *
 * Recorder calls this from the TzCtrl task to drain the trace buffer.
 * --------------------------------------------------------------------------*/
int32_t prvWriteToSocket(void* ptrData, uint32_t size, int32_t* ptrBytesWritten)
{
	BaseType_t xSent;

	if( ( s_trace_socket == FREERTOS_INVALID_SOCKET ) || ( s_trace_socket == NULL ) )
	{
		if( ptrBytesWritten != NULL )
		{
			*ptrBytesWritten = 0;
		}
		return -1;
	}

	xSent = FreeRTOS_send( s_trace_socket, ptrData, ( size_t ) size, 0 );

	if( ptrBytesWritten != NULL )
	{
		*ptrBytesWritten = ( xSent > 0 ) ? ( int32_t ) xSent : 0;
	}

	if( xSent != ( BaseType_t ) size )
	{
		return -1;
	}

	return 0;
}

/* -------------------------------------------------------------------------
 * prvReadFromSocket
 *
 * The streaming recorder occasionally polls for host commands (e.g. start /
 * stop).  Returning 0 / 0-bytes is acceptable when no inbound channel is
 * implemented, matching the upstream AFR_WIFI_LOCAL behaviour.
 * --------------------------------------------------------------------------*/
int32_t prvReadFromSocket(void* ptrData, uint32_t size, int32_t* ptrBytesRead)
{
	( void ) ptrData;
	( void ) size;

	if( ptrBytesRead != NULL )
	{
		*ptrBytesRead = 0;
	}
	return 0;
}

#endif /* TRC_CFG_RECORDER_MODE == TRC_RECORDER_MODE_STREAMING */
#endif /* TRC_USE_TRACEALYZER_RECORDER == 1 */
