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
File        : GUI_VG.h
Purpose     : 
---------------------------END-OF-HEADER------------------------------
*/

#ifndef GUI_VG_H
#define GUI_VG_H

#include "GUI.h"
#include "GUI_ARRAY.h"
#include "GUI_DYNARRAY.h"

/*********************************************************************
*
*       Defines, configurable
*
**********************************************************************
*/
#ifndef   GUI_VG_MAX_NUM_DASH_ITEMS
  #define GUI_VG_MAX_NUM_DASH_ITEMS    10
#endif

/*********************************************************************
*
*       Types
*
**********************************************************************
*/
typedef enum {
  GUI_VG_CAP_BUTT   = 0x1700,
  GUI_VG_CAP_ROUND  = 0x1701,
  GUI_VG_CAP_SQUARE = 0x1702,
} GUI_VG_CAP_STYLE;

typedef enum {
  GUI_VG_JOIN_MITER = 0x1800,
  GUI_VG_JOIN_ROUND = 0x1801,
  GUI_VG_JOIN_BEVEL = 0x1802,
} GUI_VG_JOIN_STYLE;

typedef enum {
  GUI_VG_INVALID_PAINT  = (0),
  GUI_VG_STROKE_PATH    = (1 << 0),
  GUI_VG_FILL_PATH      = (1 << 1),
  GUI_VG_AA_PATH        = (1 << 2),
  GUI_VG_STROKE_AA_PATH = (GUI_VG_STROKE_PATH | GUI_VG_AA_PATH),
  GUI_VG_FILL_AA_PATH   = (GUI_VG_FILL_PATH   | GUI_VG_AA_PATH),
} GUI_VG_PAINT_MODE;

typedef enum {
  GUI_VG_CLOSE_PATH  = ( 0 << 1),
  GUI_VG_MOVE_TO     = ( 1 << 1),
  GUI_VG_LINE_TO     = ( 2 << 1),
  GUI_VG_HLINE_TO    = ( 3 << 1),
  GUI_VG_VLINE_TO    = ( 4 << 1),
  GUI_VG_QUAD_TO     = ( 5 << 1),
  GUI_VG_CUBIC_TO    = ( 6 << 1),
  GUI_VG_SQUAD_TO    = ( 7 << 1),
  GUI_VG_SCUBIC_TO   = ( 8 << 1),
  GUI_VG_SCCWARC_TO  = ( 9 << 1),
  GUI_VG_SCWARC_TO   = (10 << 1),
  GUI_VG_LCCWARC_TO  = (11 << 1),
  GUI_VG_LCWARC_TO   = (12 << 1),
} GUI_VG_PATH_SEGMENT;

typedef enum {
  GUI_VG_ABSOLUTE = 0,
  GUI_VG_RELATIVE = 1,
} GUI_VG_PATH_ABSREL;

typedef enum {
  GUI_VG_CLOSE          = GUI_VG_CLOSE_PATH,
  GUI_VG_MOVE_TO_ABS    = GUI_VG_MOVE_TO    | GUI_VG_ABSOLUTE,
  GUI_VG_MOVE_TO_REL    = GUI_VG_MOVE_TO    | GUI_VG_RELATIVE,
  GUI_VG_LINE_TO_ABS    = GUI_VG_LINE_TO    | GUI_VG_ABSOLUTE,
  GUI_VG_LINE_TO_REL    = GUI_VG_LINE_TO    | GUI_VG_RELATIVE,
  GUI_VG_HLINE_TO_ABS   = GUI_VG_HLINE_TO   | GUI_VG_ABSOLUTE,
  GUI_VG_HLINE_TO_REL   = GUI_VG_HLINE_TO   | GUI_VG_RELATIVE,
  GUI_VG_VLINE_TO_ABS   = GUI_VG_VLINE_TO   | GUI_VG_ABSOLUTE,
  GUI_VG_VLINE_TO_REL   = GUI_VG_VLINE_TO   | GUI_VG_RELATIVE,
  GUI_VG_QUAD_TO_ABS    = GUI_VG_QUAD_TO    | GUI_VG_ABSOLUTE,
  GUI_VG_QUAD_TO_REL    = GUI_VG_QUAD_TO    | GUI_VG_RELATIVE,
  GUI_VG_CUBIC_TO_ABS   = GUI_VG_CUBIC_TO   | GUI_VG_ABSOLUTE,
  GUI_VG_CUBIC_TO_REL   = GUI_VG_CUBIC_TO   | GUI_VG_RELATIVE,
  GUI_VG_SQUAD_TO_ABS   = GUI_VG_SQUAD_TO   | GUI_VG_ABSOLUTE,
  GUI_VG_SQUAD_TO_REL   = GUI_VG_SQUAD_TO   | GUI_VG_RELATIVE,
  GUI_VG_SCUBIC_TO_ABS  = GUI_VG_SCUBIC_TO  | GUI_VG_ABSOLUTE,
  GUI_VG_SCUBIC_TO_REL  = GUI_VG_SCUBIC_TO  | GUI_VG_RELATIVE,
  GUI_VG_SCCWARC_TO_ABS = GUI_VG_SCCWARC_TO | GUI_VG_ABSOLUTE,
  GUI_VG_SCCWARC_TO_REL = GUI_VG_SCCWARC_TO | GUI_VG_RELATIVE,
  GUI_VG_SCWARC_TO_ABS  = GUI_VG_SCWARC_TO  | GUI_VG_ABSOLUTE,
  GUI_VG_SCWARC_TO_REL  = GUI_VG_SCWARC_TO  | GUI_VG_RELATIVE,
  GUI_VG_LCCWARC_TO_ABS = GUI_VG_LCCWARC_TO | GUI_VG_ABSOLUTE,
  GUI_VG_LCCWARC_TO_REL = GUI_VG_LCCWARC_TO | GUI_VG_RELATIVE,
  GUI_VG_LCWARC_TO_ABS  = GUI_VG_LCWARC_TO  | GUI_VG_ABSOLUTE,
  GUI_VG_LCWARC_TO_REL  = GUI_VG_LCWARC_TO  | GUI_VG_RELATIVE,
} GUI_VG_PATH_COMMAND;

typedef enum {
  GUI_VG_FILL_EVEN_ODD = 0x1900,
  GUI_VG_FILL_NON_ZERO = 0x1901,
} GUI_VG_FILL_RULE;

typedef enum {
  GUI_VG_GRADIENT_OBJ_BOUND_BOX,
  GUI_VG_GRADIENT_USER_SPACE_ON_USE,
} GUI_VG_GRADIENT_UNITS;

typedef enum {
  GUI_VG_GRADIENT_PAD     = 0x1C00,
  GUI_VG_GRADIENT_REPEAT  = 0x1C01,
  GUI_VG_GRADIENT_REFLECT = 0x1C02,
} GUI_VG_GRADIENT_SPREAD;

typedef enum {
  GUI_VG_LINEAR_GRADIENT,
  GUI_VG_RADIAL_GRADIENT,
} GUI_VG_GRADIENT_TYPE;

typedef enum {
  GUI_VG_GRADIENT_REF_STOP_ARRAY = (1 << 0), // If true than haStops array is referenced, not owned.
} GUI_VG_GRADIENT_FLAGS;

typedef enum {
  GUI_VG_PATH_FLAG_NATIVE_FORMAT = 0x1,
  GUI_VG_PATH_FLAG_SHARED_BUFFER = 0x2, // Data and segments are stored in one buffer.
} GUI_VG_PATH_FLAGS;

typedef struct {
  GUI_HMEM hId;
  U32      StopColor;
  float    StopOpacity;
  float    Offset;
} GUI_VG_GRADIENT_STOP;

typedef struct {
  GUI_VG_GRADIENT_TYPE   Type;
  GUI_HMEM               hLink;
  GUI_HMEM               hId;
  GUI_VG_GRADIENT_UNITS  Unit;
  GUI_VG_GRADIENT_SPREAD Spread;
  GUI_MATRIX             Mat;
  GUI_ARRAY              haStops; // Array of GUI_VG_GRADIENT_STOP
  U8                     Flags;   // Combination of GUI_VG_GRADIENT_FLAGS
} GUI_VG_GRADIENT;

typedef struct {
  GUI_VG_GRADIENT Base;
  float           x1, y1, x2, y2;
} GUI_VG_GRADIENT_LINEAR;

typedef struct {
  GUI_VG_GRADIENT Base;
  float cx, cy; // Center point
  float r;      // Radius
  float fx, fy; // Focal point
} GUI_VG_GRADIENT_RADIAL;

typedef struct {
  GUI_COLOR         ColorFill;
  GUI_COLOR         ColorStroke;
  float             aDashArray[GUI_VG_MAX_NUM_DASH_ITEMS];
  int               NumDash;
  float             StrokeWidth;
  float             MiterLimit;
  GUI_VG_CAP_STYLE  LineCap;
  GUI_VG_JOIN_STYLE LineJoin;
  GUI_VG_FILL_RULE  FillRule;
  GUI_VG_GRADIENT * pGradientFill;
  GUI_VG_GRADIENT * pGradientStroke;
  float             FillOpacity;
  float             StrokeOpacity;
  float             Opacity;
  float             StrokeDashoffset;
} GUI_VG_STYLE;

typedef PTR_ADDR GUI_VG_PATH_Handle;        // Global path object
typedef PTR_ADDR GUI_VG_DRIVER_PATH_Handle; // Driver-dependent path object

typedef struct {
  U8 HasNoArcSegments : 1;
} GUI_VG_API_FLAGS;

//
// Abstract buffer type
//
typedef enum {
  GUI_RENDERBUFFER_TYPE_INVALID = 0,
  GUI_RENDERBUFFER_TYPE_FRAMEBUFFER,
  GUI_RENDERBUFFER_TYPE_MEMDEV,
  GUI_RENDERBUFFER_TYPE_BITMAP,
} GUI_RENDERBUFFER_TYPE;

typedef struct {
  void                     * pData;
  int	                       Width, Height;
  int                        x, y; // Position of buffer on the screen (memory device)
  int	                       Stride;
  int                        Bpp;
  const LCD_API_COLOR_CONV * pColorConv;
  int                        Orientation;
  GUI_RENDERBUFFER_TYPE      BufferType;
} GUI_RENDERBUFFER;

typedef struct {
  void (* pfInitDraw)          (GUI_VG_DRIVER_PATH_Handle hPath, GUI_VG_PAINT_MODE Mode, const GUI_MATRIX * pMat);
  void (* pfFillPath)          (GUI_VG_DRIVER_PATH_Handle hPath, const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat);
  void (* pfStrokePath)        (GUI_VG_DRIVER_PATH_Handle hPath, const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat);
  void (* pfFillGradientPath)  (GUI_VG_DRIVER_PATH_Handle hPath, const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat);
  void (* pfStrokeGradientPath)(GUI_VG_DRIVER_PATH_Handle hPath, const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat);
} GUI_VG_DRAWPATH_API;

typedef struct {
  GUI_VG_DRIVER_PATH_Handle  (* pfCreatePath)     (void);
  void                       (* pfAppendPath)     (GUI_VG_DRIVER_PATH_Handle hPath, int NumSegments, const U8 * pSegments, int NumData, const float * pCoordinates);
  void                       (* pfFinalizePath)   (GUI_VG_DRIVER_PATH_Handle hPath);
  void                       (* pfDestroyPath)    (GUI_VG_DRIVER_PATH_Handle hPath);
  void                       (* pfClearPath)      (GUI_VG_DRIVER_PATH_Handle hPath);
  const GUI_VG_DRAWPATH_API   * pDrawPathAPI;
  void                       (* pfDrawPath)(GUI_VG_DRIVER_PATH_Handle hPath, const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat);
  void                       (* pfDrawImage)      (const GUI_RENDERBUFFER * pRT, const GUI_MATRIX * pMat);
  U8                         (* pfMapPathCommand) (GUI_VG_PATH_COMMAND Cmd);
  void                       (* pfEnableClipping) (int x, int y, int w, int h);
  void                       (* pfDisableClipping)(void);
  U8                         (* pfBeginDraw)      (void);
  void                       (* pfEndDraw)        (void);
  void                       (* pfModifyImageSize)(U32 * pWidth, U32 * pHeight);
  const LCD_API_COLOR_CONV * (* pfGetColorConv)   (void);
  GUI_VG_API_FLAGS              Flags;
} GUI_VG_API;

//
// Can be used in path objects for casting data array.
//
typedef struct {
  float rx, ry;   // Radii
  float Angle;    // Rotation angle
  GUI_POINTF End; // End point of arc
} GUI_VG_ARC_PARAMETERS;

typedef struct {
  GUI_POINTF Control;
  GUI_POINTF End;
} GUI_VG_QUAD_PARAMETERS;

typedef struct {
  GUI_POINTF Control1, Control2;
  GUI_POINTF End;
} GUI_VG_BEZIER_PARAMETERS;

typedef struct {
  GUI_DYNARRAY_Handle hSegments;
  GUI_DYNARRAY_Handle hData;
  U32                 Flags;
} GUI_VG_PATH_BUFFER_OBJ;

/*********************************************************************
*
*       Public code
*
**********************************************************************
*/
void               GUI_VG_InitializeGradient       (GUI_VG_GRADIENT * pGradient);
void               GUI_VG_InitializeGradientStop   (GUI_VG_GRADIENT_STOP * pStop);
void               GUI_VG_FreeGradient             (GUI_VG_GRADIENT * pGradient);
void               GUI_VG_GetDefaultStyleAttributes(GUI_VG_STYLE * pStyle);
void               GUI_VG_GetStyleAttributes       (GUI_VG_PAINT_MODE Mode, GUI_VG_STYLE * pStyle);
int                GUI_VG_GetNumCoords             (GUI_VG_PATH_COMMAND Segment);
GUI_VG_PATH_Handle GUI_VG_CreatePath               (const GUI_VG_API * pAPI);
void               GUI_VG_DeletePath               (GUI_VG_PATH_Handle hPath, const GUI_VG_API * pAPI);
void               GUI_VG_AppendPath               (GUI_VG_PATH_Handle hPath, U8 Segment, float * pData, const GUI_VG_API * pAPI);
void               GUI_VG_FinalizePath             (GUI_VG_PATH_Handle hPath, const GUI_VG_API * pAPI);
void               GUI_VG_ClearPath                (GUI_VG_PATH_Handle hPath, const GUI_VG_API * pAPI);
//
// Setting up paths
//
void GUI_VG_SetupRectPath   (GUI_VG_DRIVER_PATH_Handle hPath, float x, float y, float w, float h, float rx, float ry, const GUI_VG_API * pAPI);
void GUI_VG_SetupCirclePath (GUI_VG_DRIVER_PATH_Handle hPath, float cx, float cy, float r, const GUI_VG_API * pAPI);
void GUI_VG_SetupEllipsePath(GUI_VG_DRIVER_PATH_Handle hPath, float cx, float cy, float rx, float ry, const GUI_VG_API * pAPI);
void GUI_VG_SetupLinePath   (GUI_VG_DRIVER_PATH_Handle hPath, float x0, float y0, float x1, float y1, const GUI_VG_API * pAPI);
void GUI_VG_SetupPolygonPath(GUI_VG_DRIVER_PATH_Handle hPath, const GUI_POINTF * pPoints, unsigned NumPoints, const GUI_VG_API * pAPI);
void GUI_VG_SetupArcPath    (GUI_VG_DRIVER_PATH_Handle hPath, float x0, float y0, float rx, float ry, float a, U8 LargeArg, U8 ClockwiseArc, float x1, float y1, const GUI_VG_API * pAPI);
void GUI_VG_SetupQuadPath   (GUI_VG_DRIVER_PATH_Handle hPath, float x0, float y0, float cx, float cy, float ex, float ey, const GUI_VG_API * pAPI);
void GUI_VG_SetupCubicPath  (GUI_VG_DRIVER_PATH_Handle hPath, float x0, float y0, float cx0, float cy0, float cx1, float cy1, float ex, float ey, const GUI_VG_API * pAPI);
//
// Direct rendering
//
void GUI_VG_DrawDriverPath(GUI_VG_DRIVER_PATH_Handle hPath, const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat, const GUI_VG_API * pAPI);
void GUI_VG_DrawPath   (GUI_VG_PATH_Handle hPath, const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat, const GUI_VG_API * pAPI);
void GUI_VG_DrawRect   (float x, float y, float w, float h, float rx, float ry, const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat, const GUI_VG_API * pAPI);
void GUI_VG_DrawCircle (float cx, float cy, float r, const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat, const GUI_VG_API * pAPI);
void GUI_VG_DrawEllipse(float cx, float cy, float rx, float ry, const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat, const GUI_VG_API * pAPI);
void GUI_VG_DrawLine   (float x0, float y0, float x1, float y1, const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat, const GUI_VG_API * pAPI);
//
// Path buffers, used if the third-party API does not have path objects.
//
GUI_VG_DRIVER_PATH_Handle  GUI_VG_PATH_Create        (U32 Flags, U32 NumInitalData, U32 NumInitialSegments, U32 NumAdditionalBytes);
void                       GUI_VG_PATH_Clear         (GUI_VG_DRIVER_PATH_Handle hPath);
void                       GUI_VG_PATH_Append        (GUI_VG_DRIVER_PATH_Handle hPath, const U8 * pSegments, int NumSegments, const float * pData, const GUI_VG_API * pAPI);
GUI_VG_PATH_COMMAND        GUI_VG_PATH_GetSegmentAt  (GUI_VG_DRIVER_PATH_Handle hPath, U32 Index);
const float              * GUI_VG_PATH_GetDataAt     (GUI_VG_DRIVER_PATH_Handle hPath, U32 Index);
unsigned                   GUI_VG_PATH_GetNumSegments(GUI_VG_DRIVER_PATH_Handle hPath);
void                       GUI_VG_PATH_Delete        (GUI_VG_DRIVER_PATH_Handle hPath);

#endif /* GUI_VG_H */

/*************************** End of file ****************************/
