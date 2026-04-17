/*
 * Copyright (c) 2025 Renesas Electronics Corporation and/or its affiliates
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */
/**********************************************************************************************************************
 * File Name    : LCDConf_sci_spi_if.c
 * Version      : 1.00
 * Description  : Display controller configuration (use SCI-SPI interface).
 *********************************************************************************************************************/
/**********************************************************************************************************************
 * History : DD.MM.YYYY Version        Description
 *         : 31.08.2022 6.26.c.1.00    First Release
 *         : 31.03.2023 6.32.a.1.00    Update emWin library to v6.32a.
 *                                     Added support for runtime orientation.
 *                                     Added support for DTC and DMAC in SPI interface.
 *         : 31.01.2024 6.34.g.1.00    Update emWin library to v6.34g.
 *                                     Removed interrupt control processing when using SCI and DTC.
 *                                     (Fixed by improving bugs in SCI FIT Rev4.60 and below)
 *                                     Moved SCI and RSPI pin setting process after the Open function.
 *                                     Fixed display On/Off processing of LCD_X_DisplayDriver function.
 *                                     Remove return operation from the dma_callback_w and dma_callback_r functions.
 *         : 20.03.2025 6.34.g.1.21    Changed the disclaimer.
 *         : 09.12.2025 6.52.  1.00    Update emWin library to v6.52.
 *                                     Copy and modify from LCDConf_spi_if.c
 *********************************************************************************************************************/

/**********************************************************************************************************************
 Includes   <System Includes> , "Project Includes"
 *********************************************************************************************************************/
#include "r_emwin_rx_if.h"

#if (EMWIN_LCD_IF == LCD_IF_SCI_SPI)

/* emWin library header */
#include "GUI.h"
#include "GUIDRV_FlexColor.h"

/* FIT module header */
#include "r_gpio_rx_if.h"

#include "r_sci_rx_if.h"
#include "r_sci_rx_pinset.h"

#if (EMWIN_SELECT_DMAC_DTC == 1)
#include "r_dtc_rx_if.h"
#elif (EMWIN_SELECT_DMAC_DTC == 2)
#include "r_dmaca_rx_if.h"
#endif

/*** Settings for each display controller  ***/

#if (EMWIN_LCD_DRIVER_IC == LCD_DRV_IC_ST7715)
#include "r_emwin_rx_lcd_driver_st7715.h"
#elif (EMWIN_LCD_DRIVER_IC == LCD_DRV_IC_ILI9341)
#include "r_emwin_rx_lcd_driver_ili9341.h"
#else /* (EMWIN_LCD_DRIVER_IC == LCD_DRV_IC_OTHER) */
#warning "Warning!! It is necessary to set definition of the display driver ic."
#endif /* EMWIN_LCD_DRIVER_IC */


/**********************************************************************************************************************
 Macro definitions
 *********************************************************************************************************************/

/* SCI_SPI pin setting */
#if (EMWIN_LCD_IF_NUMBER == 0)
#define SCI_PIN_SET     R_SCI_PinSet_SCI0
#elif (EMWIN_LCD_IF_NUMBER == 1)
#define SCI_PIN_SET     R_SCI_PinSet_SCI1
#elif (EMWIN_LCD_IF_NUMBER == 2)
#define SCI_PIN_SET     R_SCI_PinSet_SCI2
#elif (EMWIN_LCD_IF_NUMBER == 3)
#define SCI_PIN_SET     R_SCI_PinSet_SCI3
#elif (EMWIN_LCD_IF_NUMBER == 4)
#define SCI_PIN_SET     R_SCI_PinSet_SCI4
#elif (EMWIN_LCD_IF_NUMBER == 5)
#define SCI_PIN_SET     R_SCI_PinSet_SCI5
#elif (EMWIN_LCD_IF_NUMBER == 6)
#define SCI_PIN_SET     R_SCI_PinSet_SCI6
#elif (EMWIN_LCD_IF_NUMBER == 7)
#define SCI_PIN_SET     R_SCI_PinSet_SCI7
#elif (EMWIN_LCD_IF_NUMBER == 8)
#define SCI_PIN_SET     R_SCI_PinSet_SCI8
#elif (EMWIN_LCD_IF_NUMBER == 9)
#define SCI_PIN_SET     R_SCI_PinSet_SCI9
#elif (EMWIN_LCD_IF_NUMBER == 10)
#define SCI_PIN_SET     R_SCI_PinSet_SCI10
#elif (EMWIN_LCD_IF_NUMBER == 11)
#define SCI_PIN_SET     R_SCI_PinSet_SCI11
#elif (EMWIN_LCD_IF_NUMBER == 12)
#define SCI_PIN_SET     R_SCI_PinSet_SCI12
#endif

/* SCI FIT module version check */
#if ((SCI_VERSION_MAJOR == 4) && (SCI_VERSION_MINOR < 90)) || (SCI_VERSION_MAJOR < 4)
#error "Error!! Please use SCI FIT module Rev4.90 or higher."
#endif


/**********************************************************************************************************************
 Private (static) variables and functions
 *********************************************************************************************************************/

static sci_hdl_t s_lcd_sci_spi_handle;
static sci_err_t s_lcd_sci_spi_err;
static sci_cfg_t s_lcd_sci_spi_setting;

static volatile bool s_transfer_busy = false;

/**********************************************************************************************************************
 * Function Name: write_command
 * Description  : Command part transmission processing.
 * Arguments    : uint8_t * p_cmd     ; Source data address
 *              : int_t     num_bytes ; Source data length
 * Return Value : none
 *********************************************************************************************************************/
R_BSP_PRAGMA_STATIC_INLINE(write_command)
void write_command(uint8_t * p_cmd, int num_bytes)
{

#if (EMWIN_USE_DATA_CMD_PIN == 1)
    /* DATA/CMD pin is Low */
    R_GPIO_PinWrite(EMWIN_DATA_CMD_PIN, GPIO_LEVEL_LOW);
#endif

#if (EMWIN_USE_LCD_CS_PIN == 1)
    /* Chip select pin is Low */
    R_GPIO_PinWrite(EMWIN_LCD_CS_PIN, GPIO_LEVEL_LOW);
#endif

    s_transfer_busy = true;

    s_lcd_sci_spi_err = R_SCI_Send(s_lcd_sci_spi_handle, p_cmd, num_bytes);

    if (SCI_SUCCESS != s_lcd_sci_spi_err)
    {
        /* WAIT_LOOP */
        while (1)
        {
            R_BSP_NOP();  /* no operation */
        }
    }

    /* WAIT_LOOP */
    while (true == s_transfer_busy)
    {
        R_BSP_NOP(); /* no operation */
    }

#if (EMWIN_USE_LCD_CS_PIN == 1)
    /* Chip select pin is High */
    R_GPIO_PinWrite(EMWIN_LCD_CS_PIN, GPIO_LEVEL_HIGH);
#endif

#if (EMWIN_USE_DATA_CMD_PIN == 1)
    /* DATA/CMD pin is High */
    R_GPIO_PinWrite(EMWIN_DATA_CMD_PIN, GPIO_LEVEL_HIGH);
#endif

}
/**********************************************************************************************************************
 * End of function write_command
 *********************************************************************************************************************/


/**********************************************************************************************************************
 * Function Name: write_data
 * Description  : Data part transmission processing.
 * Arguments    : uint8_t * p_data    ; Source data address
 *              : int_t     num_bytes ; Source data length
 * Return Value : none
 *********************************************************************************************************************/
R_BSP_PRAGMA_STATIC_INLINE(write_data)
void write_data(uint8_t * p_data, int num_bytes)
{

#if (EMWIN_USE_DATA_CMD_PIN == 1)
    /* DATA/CMD pin is High */
    R_GPIO_PinWrite(EMWIN_DATA_CMD_PIN, GPIO_LEVEL_HIGH);
#endif

#if (EMWIN_USE_LCD_CS_PIN == 1)
    /* Chip select pin is Low */
    R_GPIO_PinWrite(EMWIN_LCD_CS_PIN, GPIO_LEVEL_LOW);
#endif

    s_transfer_busy = true;

    s_lcd_sci_spi_err = R_SCI_Send(s_lcd_sci_spi_handle, p_data, num_bytes);

    if (SCI_SUCCESS != s_lcd_sci_spi_err)
    {
        /* WAIT_LOOP */
        while (1)
        {
            R_BSP_NOP();  /* no operation */
        }
    }

    /* WAIT_LOOP */
    while (true == s_transfer_busy)
    {
        R_BSP_NOP(); /* no operation */
    }

#if (EMWIN_USE_LCD_CS_PIN == 1)
    /* Chip select pin is High */
    R_GPIO_PinWrite(EMWIN_LCD_CS_PIN, GPIO_LEVEL_HIGH);
#endif

}
/**********************************************************************************************************************
 * End of function write_data
 *********************************************************************************************************************/


/**********************************************************************************************************************
 * Function Name: write8_a0
 * Description  : .
 * Arguments    : .
 * Return Value : .
 *********************************************************************************************************************/
static void write8_a0(uint8_t cmd)
{
    write_command(&cmd, 1);
}
/**********************************************************************************************************************
 * End of function write8_a0
 *********************************************************************************************************************/


/**********************************************************************************************************************
 * Function Name: writem8_a0
 * Description  : .
 * Arguments    : .
 * Return Value : .
 *********************************************************************************************************************/
static void writem8_a0(uint8_t * p_cmd, int num_items)
{
    write_command(p_cmd, num_items);
}
/**********************************************************************************************************************
 * End of function writem8_a0
 *********************************************************************************************************************/


/**********************************************************************************************************************
 * Function Name: write8_a1
 * Description  : .
 * Arguments    : .
 * Return Value : .
 *********************************************************************************************************************/
static void write8_a1(uint8_t data)
{
    write_data(&data, 1);
}
/**********************************************************************************************************************
 * End of function write8_a1
 *********************************************************************************************************************/


/**********************************************************************************************************************
 * Function Name: writem8_a1
 * Description  : .
 * Arguments    : .
 * Return Value : .
 *********************************************************************************************************************/
static void writem8_a1(uint8_t * p_data, int num_items)
{
    write_data(p_data, num_items);
}
/**********************************************************************************************************************
 * End of function writem8_a1
 *********************************************************************************************************************/

#if (EMWIN_LCD_DRIVER_IC == LCD_DRV_IC_ST7715) || (EMWIN_LCD_DRIVER_IC == LCD_DRV_IC_ILI9341)
/**********************************************************************************************************************
 * Function Name: read8_a0
 * Description  : .
 * Arguments    : .
 * Return Value : .
 *********************************************************************************************************************/
static uint8_t read8_a0(void)
{
    return 0x00;  /* Dummy */
}
/**********************************************************************************************************************
 * End of function read8_a0
 *********************************************************************************************************************/


/**********************************************************************************************************************
 * Function Name: readm8_a0
 * Description  : .
 * Arguments    : .
 * Return Value : .
 *********************************************************************************************************************/
static void readm8_a0(uint8_t * p_data, int num_items)
{
    GUI_USE_PARA(p_data);
    GUI_USE_PARA(num_items);
}
/**********************************************************************************************************************
 * End of function readm8_a0
 *********************************************************************************************************************/


/**********************************************************************************************************************
 * Function Name: read8_a1
 * Description  : .
 * Arguments    : .
 * Return Value : .
 *********************************************************************************************************************/
static uint8_t read8_a1(void)
{
    return 0x00;  /* Dummy */
}
/**********************************************************************************************************************
 * End of function read8_a1
 *********************************************************************************************************************/


/**********************************************************************************************************************
 * Function Name: readm8_a1
 * Description  : .
 * Arguments    : .
 * Return Value : .
 *********************************************************************************************************************/
static void readm8_a1(uint8_t * p_data, int num_items)
{
    GUI_USE_PARA(p_data);
    GUI_USE_PARA(num_items);
}
/**********************************************************************************************************************
 * End of function readm8_a1
 *********************************************************************************************************************/
#else /* (EMWIN_LCD_DRIVER_IC == LCD_DRV_IC_OTHER) */

#warning "Warning!! It is necessary to set definition of the display driver ic."

#endif


/**********************************************************************************************************************
 * Function Name: init_display
 * Description  : Should initialize the display controller.
 * Arguments    : .
 * Return Value : .
 *********************************************************************************************************************/
static void init_display(void)
{
#if (EMWIN_LCD_DRIVER_IC == LCD_DRV_IC_ST7715) || (EMWIN_LCD_DRIVER_IC == LCD_DRV_IC_ILI9341)

    /*** Preset the output ports for i/o pins prior to setting as outputs ***/

#if (EMWIN_USE_DATA_CMD_PIN == 1)
    /* DATA/CMD pin is High */
    R_GPIO_PinWrite(EMWIN_DATA_CMD_PIN, GPIO_LEVEL_HIGH);
    R_GPIO_PinDirectionSet(EMWIN_DATA_CMD_PIN, GPIO_DIRECTION_OUTPUT);
#endif

#if (EMWIN_USE_LCD_CS_PIN == 1)
    /* Chip select pin is High */
    R_GPIO_PinWrite(EMWIN_LCD_CS_PIN, GPIO_LEVEL_HIGH);
    R_GPIO_PinDirectionSet(EMWIN_LCD_CS_PIN, GPIO_DIRECTION_OUTPUT);
#endif

#if (EMWIN_USE_DISP_SIGNAL_PIN == 1)
    /* Reset pin is High */
    R_GPIO_PinWrite(EMWIN_DISP_SIGNAL_PIN, GPIO_LEVEL_HIGH);
    R_GPIO_PinDirectionSet(EMWIN_DISP_SIGNAL_PIN, GPIO_DIRECTION_OUTPUT);
#endif

    /** Back-light off **/

#if (EMWIN_USE_BACKLIGHT_PIN == 1)
    /* Back-light pin is Low */
    R_GPIO_PinWrite(EMWIN_BACKLIGHT_PIN, GPIO_LEVEL_LOW);
    R_GPIO_PinDirectionSet(EMWIN_BACKLIGHT_PIN, GPIO_DIRECTION_OUTPUT);
#endif

    GUI_X_Delay(10); /* Wait 10ms */

    /** Clear reset line to reset display **/

#if (EMWIN_USE_DISP_SIGNAL_PIN == 1)
    /* Reset pin is Low */
    R_GPIO_PinDirectionSet(EMWIN_DISP_SIGNAL_PIN, GPIO_DIRECTION_OUTPUT);
    R_GPIO_PinWrite(EMWIN_DISP_SIGNAL_PIN, GPIO_LEVEL_LOW);
#endif

    GUI_X_Delay(10); /* Wait 10ms */

    /** Release reset **/

#if (EMWIN_USE_DISP_SIGNAL_PIN == 1)
    /* Reset pin is High */
    R_GPIO_PinDirectionSet(EMWIN_DISP_SIGNAL_PIN, GPIO_DIRECTION_OUTPUT);
    R_GPIO_PinWrite(EMWIN_DISP_SIGNAL_PIN, GPIO_LEVEL_HIGH);
#endif

    /** Software reset **/
    write8_a0(CONTROLLER_SWRESET);

    GUI_X_Delay(120); /* Wait 120ms */

    /** out of sleep mode **/
    write8_a0(CONTROLLER_SLPOUT);

    GUI_X_Delay(120); /* Wait 120ms */

    /** Set color mode **/
    write8_a0(CONTROLLER_COLMOD);

    write8_a1(COLMOD_COLOR); /* color format */

    GUI_X_Delay(10); /* Wait 10ms */

    /** Set Normal mode **/
    write8_a0(CONTROLLER_NORON);

    GUI_X_Delay(10); /* Wait 10ms */

    /* Display controller on, backlight is turned on later (LCD_X_DisplayDriver() with cmd LCD_X_ON) */
    write8_a0(CONTROLLER_DISPON);

    GUI_X_Delay(120); /* Wait 120ms */

#else /* (EMWIN_LCD_DRIVER_IC == LCD_DRV_IC_OTHER) */

#warning "Warning!! It is necessary to set definition of the display driver ic."

#endif /* EMWIN_LCD_DRIVER_IC */
}
/**********************************************************************************************************************
 * End of function init_display
 *********************************************************************************************************************/


/**********************************************************************************************************************
 * Function Name: com_end_callback
 * Description  : communication completion callback
 * Arguments    : .
 * Return Value : .
 *********************************************************************************************************************/
static void com_end_callback(void * p_data)
{
    GUI_USE_PARA(p_data);
    s_transfer_busy = false;
}
/**********************************************************************************************************************
 * End of function com_end_callback
 *********************************************************************************************************************/


/**********************************************************************************************************************
 * Function Name: init_controller
 * Description  : Should initialize the display controller.
 * Arguments    : .
 * Return Value : .
 *********************************************************************************************************************/
static void init_controller(void)
{

#if (EMWIN_SELECT_DMAC_DTC == 1) && (EMWIN_INIT_DMAC == 1)

    if (DTC_SUCCESS != R_DTC_Open())
    {
        /* WAIT_LOOP */
        while (1)
        {
            R_BSP_NOP(); /* no operation */
        }
    }

#elif (EMWIN_SELECT_DMAC_DTC == 2) && (EMWIN_INIT_DMAC == 1)

    R_DMACA_Init();

#else
    /* Transfer method is interrupt */
#endif


    /* Open the SSPI module */
    s_lcd_sci_spi_setting.sspi.bit_rate     = EMWIN_LCD_BAUDRATE;
    s_lcd_sci_spi_setting.sspi.int_priority = 5;
    s_lcd_sci_spi_setting.sspi.invert_data  = false;
    s_lcd_sci_spi_setting.sspi.msb_first    = true;
    s_lcd_sci_spi_setting.sspi.spi_mode     = SCI_SPI_MODE_0;

    /* Open the SSPI channel using the API function */
    s_lcd_sci_spi_err = R_SCI_Open( EMWIN_LCD_IF_NUMBER,        /* SSPI channel number */
            SCI_MODE_SSPI,             /* SCI mode                                     */
            &s_lcd_sci_spi_setting,    /* Address of the SSPI settings structure.      */
            &com_end_callback,         /* Address of user-defined callback function.   */
            &s_lcd_sci_spi_handle);    /* Address of where the handle is to be stored  */

    /* If there were an error this would demonstrate error detection of API calls. */
    if (SCI_SUCCESS != s_lcd_sci_spi_err)
    {
        /* WAIT_LOOP */
        while (1)
        {
            R_BSP_NOP(); /* no operation */
        }
    }

    /* Initialize SCI pins */
    SCI_PIN_SET();


    /* Initialize display */
    init_display();
}
/**********************************************************************************************************************
 * End of function init_controller
 *********************************************************************************************************************/

/**********************************************************************************************************************
 * Function Name: lcd_driver_setting
 * Description  : Called during configuration changes such as display rotation.
 * Arguments    : .
 * Return Value : .
 * Note         : This call back function is called from the emWin library.
 *********************************************************************************************************************/
void lcd_driver_setting(GUI_DEVICE * p_device, int rotateindex, int layerindex)
{
    GUI_PORT_API     port_api = { 0 };
    CONFIG_FLEXCOLOR config   = { 0 };
    int32_t          swap_xy_ex;
    int              temp;
    int              orientation[] = {
                         DISPLAY_ORIENTATION_0,
                         DISPLAY_ORIENTATION_1,
                         DISPLAY_ORIENTATION_2,
                         DISPLAY_ORIENTATION_3
                     };

    GUI_USE_PARA(layerindex);

    /* Display driver configuration */
    swap_xy_ex = LCD_GetSwapXYEx(0);
    if (swap_xy_ex)
    {
        LCD_SetSizeEx(0, EMWIN_YSIZE_PHYS, EMWIN_XSIZE_PHYS);
        LCD_SetVSizeEx(0, EMWIN_YSIZE_PHYS, EMWIN_XSIZE_PHYS);
    }
    else
    {
        LCD_SetSizeEx(0, EMWIN_XSIZE_PHYS, EMWIN_YSIZE_PHYS);
        LCD_SetVSizeEx(0, EMWIN_XSIZE_PHYS, EMWIN_YSIZE_PHYS);
    }

    /* Function selection, hardware routines (PortAPI) and operation mode (bus, bpp and cache) */
    port_api.pfWrite8_A0  = write8_a0;
    port_api.pfWrite8_A1  = write8_a1;
    port_api.pfWriteM8_A0 = writem8_a0;
    port_api.pfWriteM8_A1 = writem8_a1;
    port_api.pfRead8_A0   = read8_a0;
    port_api.pfRead8_A1   = read8_a1;
    port_api.pfReadM8_A0  = readm8_a0;
    port_api.pfReadM8_A1  = readm8_a1;

    /* Set controller and operation mode */
    GUIDRV_FlexColor_SetFunc(p_device, &port_api, DISPLAY_CONTROLLER, CONTROLLER_MODE);

    /* Orientation */
    config.Orientation   = orientation[rotateindex] ^ DISPLAY_ORIENTATION;
    config.NumDummyReads = 0;

    config.FirstCOM = FIRST_COM;
    config.FirstSEG = FIRST_SEG;

    if (config.Orientation & GUI_SWAP_XY)
    {
        temp            = config.FirstCOM;
        config.FirstCOM = config.FirstSEG;
        config.FirstSEG = temp;
    }

    GUIDRV_FlexColor_Config(p_device, &config);
}
/**********************************************************************************************************************
 * End of function lcd_driver_setting
 *********************************************************************************************************************/
/**********************************************************************************************************************
 * Function Name: LCD_X_Config
 * Description  : Called during the initialization process in order to set up the display driver configuration.
 * Arguments    : .
 * Return Value : .
 * Note         : This function is called from the emWin library.
 *********************************************************************************************************************/
void LCD_X_Config(void)
{
    GUI_DEVICE * p_device;

    /* Set display driver and color conversion for 1st layer */
    p_device = GUI_DEVICE_CreateAndLink(GUIDRV_FLEXCOLOR, COLOR_CONVERSION, 0, 0);

    /* Display size and frame buffer setting */
    lcd_driver_setting(p_device, 0, 0);

#if (EMWIN_USE_RUNTIME_ORIENTATION == 1)
    /* Create additional drivers and add them to the display rotation module */
    LCD_ROTATE_AddDriverExOrientation(GUIDRV_FLEXCOLOR, 0, GUI_ROTATION_CW);
    LCD_ROTATE_AddDriverExOrientation(GUIDRV_FLEXCOLOR, 0, GUI_ROTATION_180);
    LCD_ROTATE_AddDriverExOrientation(GUIDRV_FLEXCOLOR, 0, GUI_ROTATION_CCW);

    /* Set call back function */
    LCD_ROTATE_SetCallback(lcd_driver_setting, 0);
#endif
}
/**********************************************************************************************************************
 * End of function LCD_X_Config
 *********************************************************************************************************************/

/**********************************************************************************************************************
 * Function Name: LCD_X_DisplayDriver
 * Description  : This function is called by the display driver for several purposes.
 *                To support the according task the routine needs to be adapted to
 *                the display controller. Please note that the commands marked with
 *                'optional' are not cogently required and should only be adapted if
 *                the display controller supports these features.
 * Arguments    : layer_index - Index of layer to be configured
 *                cmd         - Please refer to the details in the switch statement below
 *                p_data      - Pointer to a LCD_X_DATA structure
 * Return Value : < -1 - Error
 *                  -1 - Command not handled
 *                   0 - Ok
 * Note         : This function is called from the emWin library.
 *********************************************************************************************************************/
int LCD_X_DisplayDriver(unsigned layer_index, unsigned cmd, void * p_data)
{
    int32_t r = 0;
    static bool init_f = false;

    GUI_USE_PARA(layer_index);
    GUI_USE_PARA(p_data);

    switch (cmd)
    {
        /* Required */
        case LCD_X_INITCONTROLLER:
        {
            /* Called during the initialization process in order to set up the
             * display controller and put it into operation. If the display
             * controller is not initialized by any external routine this needs
             * to be adapted by the customer... */
            if (false == init_f)
            {
                init_controller();
                init_f = true;
            }

            break;
        }

        /* Required if the display controller should support switching on and off. */
        case LCD_X_ON:
        {
#if (EMWIN_USE_BACKLIGHT_PIN == 1)
            /* Turn on back light */
            R_GPIO_PinDirectionSet(EMWIN_BACKLIGHT_PIN, GPIO_DIRECTION_OUTPUT);
            R_GPIO_PinWrite(EMWIN_BACKLIGHT_PIN, GPIO_LEVEL_HIGH);
#endif
            break;
        }

        /* Required if the display controller should support switching on and off. */
        case LCD_X_OFF:
        {
#if (EMWIN_USE_BACKLIGHT_PIN == 1)
            /* Turn off back light */
            R_GPIO_PinDirectionSet(EMWIN_BACKLIGHT_PIN, GPIO_DIRECTION_OUTPUT);
            R_GPIO_PinWrite(EMWIN_BACKLIGHT_PIN, GPIO_LEVEL_LOW);
#endif
            break;
        }

        default:
        {
            r = -1;
        }
    }

    return r;
}
/**********************************************************************************************************************
 * End of function LCD_X_DisplayDriver
 *********************************************************************************************************************/

#endif /* (EMWIN_LCD_IF == LCD_IF_SCI_SPI) */

