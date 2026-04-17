/*
 * Copyright (c) 2025 Renesas Electronics Corporation and/or its affiliates
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */
/**********************************************************************************************************************
 * File Name    : r_emwin_rx_lcd_driver_ili9341.h
 * Version      : 1.00
 * Description  : Header file of ILI9341 controller.
 *********************************************************************************************************************/
/**********************************************************************************************************************
 * History : DD.MM.YYYY Version        Description
 *         : 09.12.2025 6.52.  1.00    First Release (Separated from LCDConf_spi_if.c)
 *********************************************************************************************************************/
#ifndef EMWIN_RX_LCD_DRIVER_ILI9341_H
#define EMWIN_RX_LCD_DRIVER_ILI9341_H

/**********************************************************************************************************************
 Includes   <System Includes> , "Project Includes"
 *********************************************************************************************************************/

/**********************************************************************************************************************
 Macro definitions
 *********************************************************************************************************************/

/* Display controller class */
#define DISPLAY_CONTROLLER (GUIDRV_FLEXCOLOR_F66709)

/* Color Conversion Routine */
#if (EMWIN_BITS_PER_PIXEL == 24)

#define CONTROLLER_MODE  (GUIDRV_FLEXCOLOR_M24C0B8)
#define COLOR_CONVERSION (GUICC_888)
#define COLMOD_COLOR     (0x06)

#if (EMWIN_GUI_USE_CACHE == 1)
#error "Cache is not available with this setting!"
#endif

#elif (EMWIN_BITS_PER_PIXEL == 18)

#error "This controller does not support this color depth!"

#elif (EMWIN_BITS_PER_PIXEL == 16)

#if (EMWIN_GUI_USE_CACHE == 1)
#define CONTROLLER_MODE  (GUIDRV_FLEXCOLOR_M16C1B8)
#else
#define CONTROLLER_MODE  (GUIDRV_FLEXCOLOR_M16C0B8)
#endif

#define COLOR_CONVERSION (GUICC_565)
#define COLMOD_COLOR     (0x05)

#endif

/* Display orientation */
#if (EMWIN_DISPLAY_ORIENTATION == ORIENTATION_0)
#define DISPLAY_ORIENTATION_0 (GUI_ROTATION_0)
#define DISPLAY_ORIENTATION_1 (GUI_ROTATION_CW)
#define DISPLAY_ORIENTATION_2 (GUI_ROTATION_180)
#define DISPLAY_ORIENTATION_3 (GUI_ROTATION_CCW)
#elif (EMWIN_DISPLAY_ORIENTATION == ORIENTATION_CW)
#define DISPLAY_ORIENTATION_0 (GUI_ROTATION_CW)
#define DISPLAY_ORIENTATION_1 (GUI_ROTATION_180)
#define DISPLAY_ORIENTATION_2 (GUI_ROTATION_CCW)
#define DISPLAY_ORIENTATION_3 (GUI_ROTATION_0)
#elif (EMWIN_DISPLAY_ORIENTATION == ORIENTATION_180)
#define DISPLAY_ORIENTATION_0 (GUI_ROTATION_180)
#define DISPLAY_ORIENTATION_1 (GUI_ROTATION_CCW)
#define DISPLAY_ORIENTATION_2 (GUI_ROTATION_0)
#define DISPLAY_ORIENTATION_3 (GUI_ROTATION_CW)
#elif (EMWIN_DISPLAY_ORIENTATION == ORIENTATION_CCW)
#define DISPLAY_ORIENTATION_0 (GUI_ROTATION_CCW)
#define DISPLAY_ORIENTATION_1 (GUI_ROTATION_0)
#define DISPLAY_ORIENTATION_2 (GUI_ROTATION_CW)
#define DISPLAY_ORIENTATION_3 (GUI_ROTATION_180)
#else
#error "No display driver orientation defined!"
#endif

/* Setting the base point of the LCD */
#define DISPLAY_ORIENTATION (GUI_MIRROR_X)

/* LCD controller register addresses */
#define CONTROLLER_SWRESET  (0x01)
#define CONTROLLER_SLPOUT   (0x11)
#define CONTROLLER_NORON    (0x13)
#define CONTROLLER_DISPON   (0x29)
#define CONTROLLER_COLMOD   (0x3A)

/* Offset of the SEG- and COM-lines */
#define FIRST_COM        (0)
#define FIRST_SEG        (0)

#endif /* EMWIN_RX_LCD_DRIVER_ILI9341_H */
