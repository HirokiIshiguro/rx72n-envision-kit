/*******************************************************************************
* DISCLAIMER
* This software is supplied by Renesas Electronics Corporation and is only
* intended for use with Renesas products. No other uses are authorized. This
* software is owned by Renesas Electronics Corporation and is protected under
* all applicable laws, including copyright laws.
* THIS SOFTWARE IS PROVIDED "AS IS" AND RENESAS MAKES NO WARRANTIES REGARDING
* THIS SOFTWARE, WHETHER EXPRESS, IMPLIED OR STATUTORY, INCLUDING BUT NOT
* LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
* AND NON-INFRINGEMENT. ALL SUCH WARRANTIES ARE EXPRESSLY DISCLAIMED.
* TO THE MAXIMUM EXTENT PERMITTED NOT PROHIBITED BY LAW, NEITHER RENESAS
* ELECTRONICS CORPORATION NOR ANY OF ITS AFFILIATED COMPANIES SHALL BE LIABLE
* FOR ANY DIRECT, INDIRECT, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES FOR
* ANY REASON RELATED TO THIS SOFTWARE, EVEN IF RENESAS OR ITS AFFILIATES HAVE
* BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
* Renesas reserves the right, without notice, to make changes to this software
* and to discontinue the availability of this software. By using this software,
* you agree to the additional terms and conditions found by accessing the
* following link:
* http://www.renesas.com/disclaimer
*
* Copyright (C) 2018 Renesas Electronics Corporation. All rights reserved.
*******************************************************************************/
/**********************************************************************************************************************
* File Name    : rskrx65n_uart.c
* Device(s)    : RSKRX65-2M
* Tool-Chain   : Renesas RX
* Description  :
***********************************************************************************************************************/
/**********************************************************************************************************************
* History : DD.MM.YYYY Version  Description
***********************************************************************************************************************/

/*****************************************************************************
Includes   <System Includes> , "Project Includes"
******************************************************************************/
#include <string.h>             // For strlen
#include "serial_term_uart.h"   // Serial Transfer Demo interface file.
#include "platform.h"           // Located in the FIT BSP module
#include "r_sci_rx_if.h"        // The SCI module API interface file.
#include "r_pinset.h"
#include "FreeRTOS.h"
#include "queue.h"
#include "semphr.h"

/* for using Segger emWin */
#include "GUI.h"
#include "DIALOG.h"

#include "rx72n_envision_kit_system.h"

/*******************************************************************************
 Macro definitions
 *******************************************************************************/
#if !defined(MY_BSP_CFG_AFR_TERM_SCI)
#error "Error! Need to define MY_BSP_CFG_SERIAL_TERM_SCI in r_bsp_config.h"
#elif MY_BSP_CFG_AFR_TERM_SCI == (0)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI0()
#define SCI_CH_serial_term          SCI_CH0
#elif MY_BSP_CFG_AFR_TERM_SCI == (1)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI1()
#define SCI_CH_serial_term          SCI_CH1
#elif MY_BSP_CFG_AFR_TERM_SCI == (2)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI2()
#define SCI_CH_serial_term          SCI_CH2
#elif MY_BSP_CFG_AFR_TERM_SCI == (3)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI3()
#define SCI_CH_serial_term          SCI_CH3
#elif MY_BSP_CFG_AFR_TERM_SCI == (4)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI4()
#define SCI_CH_serial_term          SCI_CH4
#elif MY_BSP_CFG_AFR_TERM_SCI == (5)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI5()
#define SCI_CH_serial_term          SCI_CH5
#elif MY_BSP_CFG_AFR_TERM_SCI == (6)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI6()
#define SCI_CH_serial_term          SCI_CH6
#elif MY_BSP_CFG_AFR_TERM_SCI == (7)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI7()
#define SCI_CH_serial_term          SCI_CH7
#elif MY_BSP_CFG_AFR_TERM_SCI == (8)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI8()
#define SCI_CH_serial_term          SCI_CH8
#elif MY_BSP_CFG_AFR_TERM_SCI == (9)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI9()
#define SCI_CH_serial_term          SCI_CH9
#elif MY_BSP_CFG_AFR_TERM_SCI == (10)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI10()
#define SCI_CH_serial_term          SCI_CH10
#elif MY_BSP_CFG_AFR_TERM_SCI == (11)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI11()
#define SCI_CH_serial_term          SCI_CH11
#elif MY_BSP_CFG_AFR_TERM_SCI == (12)
#define R_SCI_PinSet_serial_term()  R_SCI_PinSet_SCI12()
#define SCI_CH_serial_term          SCI_CH12
#else
#error "Error! Invalid setting for MY_BSP_CFG_SERIAL_TERM_SCI in r_bsp_config.h"
#endif

/*******************************************************************************
 Exported global variables and functions (to be accessed by other files)
 *******************************************************************************/

/* SCI7 一本化: ログモード ↔ コマンドモードの状態管理 */
#define SERIAL_MODE_LOG     0
#define SERIAL_MODE_COMMAND 1
volatile int32_t serial_mode = SERIAL_MODE_LOG;

/* serial_terminal_task.c で作成されるコマンド受信キュー */
extern QueueHandle_t xSerialTermQueue;

/*******************************************************************************
 Private variables and functions
 *******************************************************************************/
extern void amazon_freertos_syslog_putstring(char *string);
extern volatile int32_t gui_initialize_complete_flag;

/*****************************************************************************
Private global variables and functions
******************************************************************************/
static void my_sci_callback(void *pArgs);

/* Handle storage. Shared with serial_terminal_task via uart_get_sci_handle(). */
sci_hdl_t     my_sci_handle;

/*****************************************************************************
* Function Name: uart_config
* Description  : prepares UART for operation
* Arguments    : none
* Return Value : none
******************************************************************************/
void uart_config(void)
{
    sci_cfg_t   my_sci_config;
    sci_err_t   my_sci_err;

    /* Initialize the I/O port pins for communication on this SCI channel.
    * This is specific to the MCU and ports chosen. For the RSKRX65-2M we will use the
    * SCI channel connected to the USB serial port emulation. */
    R_SCI_PinSet_serial_term();

    /* Set up the configuration data structure for asynchronous (UART) operation. */
    my_sci_config.async.baud_rate    = MY_BSP_CFG_AFR_TERM_SCI_BITRATE;
    my_sci_config.async.clk_src      = SCI_CLK_INT;
    my_sci_config.async.data_size    = SCI_DATA_8BIT;
    my_sci_config.async.parity_en    = SCI_PARITY_OFF;
    my_sci_config.async.parity_type  = SCI_EVEN_PARITY;
    my_sci_config.async.stop_bits    = SCI_STOPBITS_1;
    my_sci_config.async.int_priority = MY_BSP_CFG_AFR_TERM_SCI_INTERRUPT_PRIORITY;    // 1=lowest, 15=highest

    /* OPEN ASYNC CHANNEL
    *  Provide address of the configure structure,
    *  the callback function to be assigned,
    *  and the location for the handle to be stored.*/
    my_sci_err = R_SCI_Open(SCI_CH_serial_term, SCI_MODE_ASYNC, &my_sci_config, my_sci_callback, &my_sci_handle);

    /* If there were an error this would demonstrate error detection of API calls. */
    if (SCI_SUCCESS != my_sci_err)
    {
        R_BSP_NOP(); // Your error handling code would go here.
    }
} /* End of function uart_config() */


/*****************************************************************************
* Function Name: my_sci_callback
* Description  : This is a template for an SCI Async Mode callback function.
* Arguments    : pArgs -
*                pointer to sci_cb_p_args_t structure cast to a void. Structure
*                contains event and associated data.
* Return Value : none
******************************************************************************/
static void my_sci_callback(void *pArgs)
{
    sci_cb_args_t   *p_args;

    p_args = (sci_cb_args_t *)pArgs;

    if (SCI_EVT_RX_CHAR == p_args->event)
    {
        /* SCI7 一本化: 受信バイトをコマンドキューに投入。
         * ログモード中にバイト受信 → コマンドモードに自動切替。 */
        uint8_t byte = p_args->byte;
        if (serial_mode == SERIAL_MODE_LOG)
        {
            serial_mode = SERIAL_MODE_COMMAND;
        }
        if (xSerialTermQueue != NULL)
        {
            BaseType_t xHigherPriorityTaskWoken = pdFALSE;
            xQueueSendFromISR(xSerialTermQueue, &byte, &xHigherPriorityTaskWoken);
            portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
        }
    }
    else if (SCI_EVT_RXBUF_OVFL == p_args->event)
    {
        /* From RXI interrupt; rx queue is full; 'lost' data is in p_args->byte
           You will need to increase buffer size or reduce baud rate */
    	R_BSP_NOP();
    }
    else if (SCI_EVT_OVFL_ERR == p_args->event)
    {
        /* From receiver overflow error interrupt; error data is in p_args->byte
           Error condition is cleared in calling interrupt routine */
    	R_BSP_NOP();
    }
    else if (SCI_EVT_FRAMING_ERR == p_args->event)
    {
        /* From receiver framing error interrupt; error data is in p_args->byte
           Error condition is cleared in calling interrupt routine */
    	R_BSP_NOP();
    }
    else if (SCI_EVT_PARITY_ERR == p_args->event)
    {
        /* From receiver parity error interrupt; error data is in p_args->byte
           Error condition is cleared in calling interrupt routine */
    	R_BSP_NOP();
    }
    else if (SCI_EVT_TEI == p_args->event)
    {
        /* SCI7 一本化: 送信完了割り込み。
         * serial_terminal_task の serial_terminal_putstring() が
         * xSemaphore で送信完了を待っている。 */
        extern SemaphoreHandle_t xSerialTermTxSemaphore;
        if (xSerialTermTxSemaphore != NULL)
        {
            BaseType_t xHigherPriorityTaskWoken = pdFALSE;
            xSemaphoreGiveFromISR(xSerialTermTxSemaphore, &xHigherPriorityTaskWoken);
            portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
        }
    }
    else
    {
        /* Do nothing */
    }

} /* End of function my_sci_callback() */

void uart_string_printf(char *pString)
{
    uint16_t str_length = 0;
    uint16_t transmit_length = 0;
    sci_err_t sci_err;
    uint32_t retry = 0xFFFF;

    TASK_INFO *task_info = get_task_info();

    while(!task_info->gui_initialize_complete_flag)
    {
    	vTaskDelay(1);
    }

    /* コマンドモード中はログ出力を抑制。
     * コマンド応答とログが混在するのを防ぐ。 */
    if (serial_mode != SERIAL_MODE_LOG)
    {
        return;
    }

    str_length = (uint16_t)strlen(pString);
    amazon_freertos_syslog_putstring(pString);

    while ((retry > 0) && (str_length > 0))
    {

        R_SCI_Control(my_sci_handle, SCI_CMD_TX_Q_BYTES_FREE, &transmit_length);

        if(transmit_length > str_length)
        {
            transmit_length = str_length;
        }

        sci_err = R_SCI_Send(my_sci_handle, (uint8_t *) pString,
                             transmit_length);

        if ((sci_err == SCI_ERR_XCVR_BUSY) || (sci_err == SCI_ERR_INSUFFICIENT_SPACE))
        {
            retry--; // retry if previous transmission still in progress or tx buffer is insufficient.
            continue;
        }

        str_length -= transmit_length;
        pString += transmit_length;

    }

    if (SCI_SUCCESS != sci_err)
    {
    	R_BSP_NOP(); //TODO error handling code
    }
}

/*****************************************************************************
* Function Name: uart_get_sci_handle
* Description  : Returns the SCI handle opened by uart_config().
*                Used by serial_terminal_task to share the SCI7 port.
* Arguments    : none
* Return Value : sci_hdl_t handle
******************************************************************************/
sci_hdl_t uart_get_sci_handle(void)
{
    return my_sci_handle;
}
