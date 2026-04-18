/*******************************************************************************
 * Trace Recorder Library for Tracealyzer v4.3.11
 * Stream port: FreeRTOS-Plus-TCP (rx72n-envision-kit Phase 8b 第3次 段階5-2 / #50)
 *
 * Adapted from `streamports/AFR_WIFI_LOCAL/include/trcStreamingPort.h`.
 * Replaces the legacy Amazon FreeRTOS `iot_secure_sockets.h` API with the
 * FreeRTOS-Plus-TCP socket API (`FreeRTOS_socket()` etc.) used by the
 * iot-reference-rx baseline.
 *
 * Use this stream port together with `vTraceEnable(TRC_START)` once the kernel
 * is running and the FreeRTOS-Plus-TCP stack is up. See `trcStreamingPort.c`
 * in the same directory for the runtime side and the per-target IP/port
 * configuration knobs.
 *
 * Tabs are used for indent in this file (1 tab = 4 spaces).
 ******************************************************************************/

#ifndef TRC_STREAMING_PORT_H
#define TRC_STREAMING_PORT_H

#ifdef __cplusplus
extern "C" {
#endif

void prvInitSocket(void);
int32_t prvReadFromSocket(void* ptrData, uint32_t size, int32_t* ptrBytesRead);
int32_t prvWriteToSocket(void* ptrData, uint32_t size, int32_t* ptrBytesWritten);

#define TRC_STREAM_PORT_INIT() \
	TRC_STREAM_PORT_MALLOC(); \
	prvInitSocket();

#define TRC_STREAM_PORT_USE_INTERNAL_BUFFER 1

#define TRC_STREAM_PORT_WRITE_DATA(_ptrData, _size, _ptrBytesWritten) prvWriteToSocket(_ptrData, _size, _ptrBytesWritten)

#define TRC_STREAM_PORT_READ_DATA(_ptrData, _size, _ptrBytesRead) prvReadFromSocket(_ptrData, _size, _ptrBytesRead)

#ifdef __cplusplus
}
#endif

#endif /* TRC_STREAMING_PORT_H */
