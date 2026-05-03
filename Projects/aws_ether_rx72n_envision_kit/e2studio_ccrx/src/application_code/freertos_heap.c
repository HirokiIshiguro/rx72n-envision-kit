/*
 * Place the FreeRTOS heap in the lower RX72N RAM block. The upper RAM block is
 * shared by Ethernet and display buffers, so keeping the heap out of it avoids
 * collisions when board display support is enabled.
 */

#include <stdint.h>

#include "FreeRTOS.h"

#pragma section _FREERTOS_HEAP
uint8_t ucHeap[configTOTAL_HEAP_SIZE];
#pragma section
