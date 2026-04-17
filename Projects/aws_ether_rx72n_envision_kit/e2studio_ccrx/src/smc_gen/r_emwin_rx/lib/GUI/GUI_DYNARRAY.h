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
File        : GUI_DYNARRAY.h
Purpose     : Dynamic array of items with the same size.
---------------------------END-OF-HEADER------------------------------
*/

#ifndef GUI_DYNARRAY_H
#define GUI_DYNARRAY_H

#include "GUI.h"

typedef GUI_HMEM GUI_DYNARRAY_Handle;

typedef struct {
  void             ** ppItem;
  unsigned            i;
  GUI_DYNARRAY_Handle hArray;
} GUI_DYNARRAY_ITERATOR;

typedef int (GUI_DYNARRAY_EXPAND_FUNC)(int NumNewItems, int MaxItems);
typedef int (GUI_DYNARRAY_COMPARE_FUNC)(void * pItem0, void * pItem1);

void                GUI_DYNARRAY_Append       (GUI_DYNARRAY_Handle hArray, const void * pNewData, unsigned NumNewItems);
void                GUI_DYNARRAY_Prepend      (GUI_DYNARRAY_Handle hArray, const void * pNewData, unsigned NumNewItems);
GUI_DYNARRAY_Handle GUI_DYNARRAY_Create       (unsigned SizeOfItem, unsigned NumItems);
GUI_DYNARRAY_Handle GUI_DYNARRAY_CreateEx     (unsigned SizeOfItem, unsigned NumItems, GUI_DYNARRAY_EXPAND_FUNC * pfExpand);
void                GUI_DYNARRAY_Clear        (GUI_DYNARRAY_Handle hArray);
void                GUI_DYNARRAY_Delete       (GUI_DYNARRAY_Handle hArray);
int                 GUI_DYNARRAY_FindItem     (GUI_DYNARRAY_Handle hArray, const void * pItem);
void                GUI_DYNARRAY_Resize       (GUI_DYNARRAY_Handle hArray, unsigned NumBytesNew);
void                GUI_DYNARRAY_RemoveItemAt (GUI_DYNARRAY_Handle hArray, unsigned Index);
void                GUI_DYNARRAY_RemoveItem   (GUI_DYNARRAY_Handle hArray, const void * pItem);
void              * GUI_DYNARRAY_GetItemAt    (GUI_DYNARRAY_Handle hArray, unsigned Index);
void              * GUI_DYNARRAY_GetDataPtr   (GUI_DYNARRAY_Handle hArray);
unsigned            GUI_DYNARRAY_GetNumItems  (GUI_DYNARRAY_Handle hArray);
unsigned            GUI_DYNARRAY_GetNumBytes  (GUI_DYNARRAY_Handle hArray);
unsigned            GUI_DYNARRAY_GetSize      (GUI_DYNARRAY_Handle hArray);
unsigned            GUI_DYNARRAY_GetSizeOfItem(GUI_DYNARRAY_Handle hArray);
void                GUI_DYNARRAY_MoveData     (GUI_DYNARRAY_Handle hArray, unsigned IndexFrom, unsigned IndexTo);
void                GUI_DYNARRAY_BeginIterator(GUI_DYNARRAY_Handle hArray, void ** ppItem, GUI_DYNARRAY_ITERATOR * pIterator);
void              * GUI_DYNARRAY_GetNextItem  (GUI_DYNARRAY_ITERATOR * pIterator);
void                GUI_DYNARRAY_Sort         (GUI_DYNARRAY_Handle hArray, GUI_DYNARRAY_COMPARE_FUNC * pfCompare);
//
// Expand strategies
//
int GUI_DYNARRAY_EXPAND_Double(int NumNewItems, int MaxItems);
int GUI_DYNARRAY_EXPAND_Add   (int NumNewItems, int MaxItems);

#endif /* GUI_DYNARRAY_H */

/*************************** End of file ****************************/
