/*********************************************************************
*                    SEGGER Microcontroller GmbH                     *
*        Solutions for real time microcontroller applications        *
**********************************************************************
*                                                                    *
*        (c) 1996 - 2025  SEGGER Microcontroller GmbH                *
*                                                                    *
*        Internet: www.segger.com    Support:  support@segger.com    *
*                                                                    *
**********************************************************************

** emWin V6.52 - Graphical user interface for embedded applications **
emWin is protected by international copyright laws.   Knowledge of the
source code may not be used to write a similar product.  This file may
only  be used  in accordance  with  a license  and should  not be  re-
distributed in any way. We appreciate your understanding and fairness.
----------------------------------------------------------------------
Licensing information
Licensor:                 SEGGER Software GmbH
Licensed to:              Renesas Electronics Europe GmbH, Arcadiastrasse 10, 40472 Duesseldorf, Germany
Licensed SEGGER software: emWin
License number:           GUI-00678
License model:            License and Service Agreement, signed December 16th, 2016, Amendment No. 1 signed May 16th, 2019 and Amendment No. 2, signed September 20th, 2021 by Carsten Jauch, Managing Director
License valid for:        RX (based on RX-V1, RX-V2 or RX-V3)
----------------------------------------------------------------------
Support and Update Agreement (SUA)
SUA period:               2016-12-22 - 2025-12-31
Contact to extend SUA:    sales@segger.com
----------------------------------------------------------------------
File        : GUI_FontIntern.h
Purpose     : Internal declarations used in font files
---------------------------END-OF-HEADER------------------------------
*/

#ifndef  GUI_FONTINTERN_H    /* Guard against multiple inclusion */
#define  GUI_FONTINTERN_H

#include "GUI.h"

#if defined(__cplusplus)
extern "C" {     /* Make sure we have C-declarations in C++ programs */
#endif

//
// Proportional fonts
//
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font8_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font10S_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font10_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font13_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font13B_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font13H_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font13HB_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font16_1_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font16_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_CHARINFO_EXT  GUI_Font16_HK_CharInfo[169];
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font16B_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font20_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font20B_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font24_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font24B_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font32_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font32B_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_FontComic18B_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_FontComic24B_ASCII_Prop1;

//
// Monospaced fonts
//
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font6x8_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font8x8_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font8x13_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font8x15B_ASCII_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font8x16_ASCII_Prop1;

//
// Proportional fonts, antialiased
//
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font12_ASCII_AA4_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font16_ASCII_AA4_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font24_ASCII_AA4_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font32_ASCII_AA4_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font48_ASCII_AA4_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font64_ASCII_AA4_Prop1;

//
// Monospaced fonts, antialiased
//
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font5x12_ASCII_AA4_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font8x16_ASCII_AA4_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font12x24_ASCII_AA4_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font16x32_ASCII_AA4_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font24x48_ASCII_AA4_Prop1;
extern GUI_CONST_STORAGE GUI_FONT_PROP_EXT GUI_Font32x64_ASCII_AA4_Prop1;

#if defined(__cplusplus)
  }
#endif


#endif   /* Guard against multiple inclusion */

/*************************** End of file ****************************/
