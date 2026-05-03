/*
 * Reserve the board display frame buffer as a linker-visible section. The
 * fixed address in r_emwin_rx_config.h must match B_FRAME_BUFFER_1.
 */

#include <stdint.h>

#include "r_emwin_rx_private.h"

#pragma section _FRAME_BUFFER
uint8_t g_emwin_frame_buffer[EMWIN_NUM_BUFFERS * BYTES_PER_BUFFER];
#pragma section

void vApplicationEnsureEmwinFrameBufferReserved( void )
{
    volatile uint8_t * const p_frame_buffer = g_emwin_frame_buffer;

    p_frame_buffer[0] = p_frame_buffer[0];
}
