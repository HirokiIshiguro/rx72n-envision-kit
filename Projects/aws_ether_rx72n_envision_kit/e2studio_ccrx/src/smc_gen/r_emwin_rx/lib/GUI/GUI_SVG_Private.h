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
File        : GUI_SVG_Private.h
Purpose     : Private header for SVG support
---------------------------END-OF-HEADER------------------------------
*/

#ifndef GUI_SVG_PRIVATE_H
#define GUI_SVG_PRIVATE_H

#include "GUI_Private.h"
#include "GUI_VG.h"

/*********************************************************************
*
*       Include drivers based on compile-time selection
*
**********************************************************************
*/
#if   defined(GUI_GPU_HAS_OPENVG) || defined(GUI_SVG_HAS_OPENVG)
  #include "GUI_GPU.h"
  #include "GUI_GPU_Private.h"
  #include "GUI_GPU_OpenVG.h"
#elif defined(GUI_GPU_HAS_VGLITE) || defined(GUI_SVG_HAS_VGLITE)
  #include "GUI_GPU.h"
  #include "GUI_GPU_Private.h"
  #include "GUI_GPU_VGLite.h"
#elif defined(GUI_GPU_HAS_NEMAVG) || defined(GUI_SVG_HAS_NEMAVG)
  #include "GUI_GPU.h"
  #include "GUI_GPU_Private.h"
  #include "GUI_GPU_NemaVG.h"
#elif defined(GUI_GPU_HAS_NANOVG) || defined(GUI_SVG_HAS_NANOVG)
  //
  // Don't include GUI_GPU_NanoVG.h here, as we want to have it in GUI_GPU_NanoVG.c
  // (because of implementation define switch).
  //
  #include "GUI_GPU.h"
  #include "GUI_GPU_Private.h"
#endif

/*********************************************************************
*
*       Availability of ShivaVG as DLL or source.
*
**********************************************************************
*/
//
// Define may be overriden in GUIConf.h
// This allows for easier switching between OpenVG implementations.
//
#ifndef GUI_GPU_HAS_SHIVAVG
  #if defined(GUI_GPU_HAS_OPENVG) && defined(__SHIVA_VG__)
    #define GUI_GPU_HAS_SHIVAVG       1    // Can be ShivaVG source or DLL.
    #define GUI_GPU_HAS_SHIVAVG_DLL   0
  #else
    #if defined(_WINDOWS) && !defined(GUI_GPU_HAS_OPENVG)  // Simulation always uses ShivaVG DLL by default.
      #define GUI_GPU_HAS_SHIVAVG       1
      #define GUI_GPU_HAS_SHIVAVG_DLL   1
    #else
      #define GUI_GPU_HAS_SHIVAVG       0
      #define GUI_GPU_HAS_SHIVAVG_DLL   0
    #endif
  #endif
#endif

/*********************************************************************
*
*       Prepare interface from GPU module to SVG
*
**********************************************************************
*/
#if   defined(GUI_GPU_HAS_OPENVG)
  #define GPU_RENDER_BACKEND  (&GUI_SVG__Renderer)
#elif defined(GUI_GPU_HAS_VGLITE)
  #define GPU_RENDER_BACKEND  (&GUI_SVG__Renderer)
#elif        (GUI_GPU_HAS_SHIVAVG)   // Always defined, either as 0 or 1.
  #define GPU_RENDER_BACKEND  (&GUI_SVG__Renderer)
#elif defined(GUI_GPU_HAS_NEMAVG)
  #define GPU_RENDER_BACKEND  (&GUI_SVG__Renderer)
#elif defined(GUI_GPU_HAS_NANOVG)
  #define GPU_RENDER_BACKEND  (&GUI_SVG__Renderer)
#else
  #define GPU_RENDER_BACKEND  NULL
#endif

#if defined(__cplusplus)
extern "C" {     /* Make sure we have C-declarations in C++ programs */
#endif

/*********************************************************************
*
*       XML parsing module (not published for now)
*
**********************************************************************
*/
typedef GUI_HMEM   GUI_XML_Handle;

#define MAKE_STRUCT(NAME)  typedef struct NAME NAME; \
                           struct NAME 

// Keep structure the same as XML_ATTRIBUTE (private)
MAKE_STRUCT(GUI_XML_ATTRIBUTE) {
  const GUI_XML_ATTRIBUTE * pNext;
  const char              * sAttrib;
  const char              * sValue;
};

typedef void GUI_XML_DOCUMENT_CALLBACK(GUI_XML_Handle hXML, void * pUser);
typedef void GUI_XML_ELEMENT_CALLBACK (GUI_XML_Handle hXML, void * pUser, const char * sElement, const GUI_XML_ATTRIBUTE * pFirstAttrib);
typedef void GUI_XML_STRING_CALLBACK  (GUI_XML_Handle hXML, void * pUser, const char * s);
typedef void GUI_XML_ERROR_CALLBACK   (GUI_XML_Handle hXML, void * pUser, const char * sError, U32 Offset);

typedef struct {
  GUI_XML_DOCUMENT_CALLBACK * cbDocumentOpen;   // Called when XML doc opened.
  GUI_XML_DOCUMENT_CALLBACK * cbDocumentClose;  // Called when XML doc closed.
  GUI_XML_ELEMENT_CALLBACK  * cbElementOpen;    // Called when XML element was opened, e.g. <elem>
  GUI_XML_STRING_CALLBACK   * cbElementClose;   // Called when XML element was closed, e.g. </elem>
  GUI_XML_STRING_CALLBACK   * cbCharacter;      // Called when characters within an element were read.
  GUI_XML_STRING_CALLBACK   * cbCharData;       // Called when CDATA was read.
  GUI_XML_ERROR_CALLBACK    * cbError;          // Called when an error occured due to a malformed XML doc.
} GUI_XML_CALLBACKS;

typedef enum {
  GUI_XML_WHITELIST_ELEMENT = 0,
  GUI_XML_WHITELIST_ATTRIBUTE,
} GUI_XML_WHITELIST;

typedef struct {
  const GUI_XML_ATTRIBUTE * pAttrib;
  const char              * sAttrib;
  const char              * sValue;
} GUI_XML_ITERATOR;

GUI_XML_Handle            GUI_XML_Create          (const void * pFile, U32 FileSize);
GUI_XML_Handle            GUI_XML_CreateEx        (GUI_SVG_GET_DATA_FUNC * pfGetData, void * p);
U32                       GUI_XML_GetOffset       (GUI_XML_Handle hXML);
void                      GUI_XML_SetBufferSize   (GUI_XML_Handle hXML, U32 NumBytes);
void                      GUI_XML_SetCallbacks    (GUI_XML_Handle hXML, const GUI_XML_CALLBACKS * pCallbacks);
void                      GUI_XML_SetUserData     (GUI_XML_Handle hXML, void * p);
void                      GUI_XML_SetWhitelist    (GUI_XML_Handle hXML, GUI_XML_WHITELIST Id, const char ** paWhitelist, unsigned NumItems);
void                      GUI_XML_Delete          (GUI_XML_Handle hXML);
int                       GUI_XML_Parse           (GUI_XML_Handle hXML);
void                      GUI_XML_BeginIterator   (GUI_XML_ITERATOR * pIterator);
const GUI_XML_ATTRIBUTE * GUI_XML_GetNextAttribute(GUI_XML_ITERATOR * pIterator);

//
// TBD: replace this with new XML iterator functions
//
#define GUI_XML_BEGIN_ITERATE_ATTRIBS(ATTRIBUTE_PTR)   \
  {                                                    \
    const GUI_XML_ATTRIBUTE * pAttrib = (const GUI_XML_ATTRIBUTE *)ATTRIBUTE_PTR; \
    const char              * sValue;                  \
    if (pAttrib) {                                     \
      do {                                             \
        sValue = pAttrib->sValue;                      \
        GUI_USE_PARA(sValue);
#define GUI_XML_END_ITERATE_ATTRIBS()            \
        pAttrib = pAttrib->pNext;                \
      } while (pAttrib);                         \
    }                                            \
  }

/*********************************************************************
*
*       CSS parsing module
* 
*  CSS parsing is as primitive as it needs to be, not intended for
*  publishing.
*
**********************************************************************
*/
typedef enum {
  GUI_CSS_SELECTOR_INVALID, // any other selectors that aren't supported
  GUI_CSS_SELECTOR_ALL,     // * { ... }
  GUI_CSS_SELECTOR_ID,      // #someId { ... }
  GUI_CSS_SELECTOR_CLASS,   // .someClass { ... }
} GUI_CSS_SELECTOR_TYPE;
//
// Keep structure the same as (GUI_)XML_ATTRIBUTE
// The structs should all be convertible.
//
MAKE_STRUCT(GUI_CSS_ATTRIBUTE) {
  const GUI_CSS_ATTRIBUTE * pNext;
  char                    * sAttrib;
  char                    * sValue;
};

//
// Keep structure the same as CSS_SELECTOR
// The structs should all be convertible.
//
MAKE_STRUCT(GUI_CSS_SELECTOR) {
  /* const GUI_CSS_SELECTOR * pNextSelector; */
  GUI_CSS_SELECTOR_TYPE    Type;
  const char             * sTarget;
};

//
// One CSS rule, this means the declaraction block {}
// with the selector(s).
//
MAKE_STRUCT(GUI_CSS_RULE) {
  GUI_CSS_SELECTOR          Selector;
  const GUI_CSS_ATTRIBUTE * pFirstAttrib;
};

GUI_ARRAY GUI_CSS__Parse              (const char * sCSS);
void      GUI_CSS__Delete             (GUI_ARRAY haCss);
GUI_ARRAY GUI_CSS__GetMatchingRules   (GUI_ARRAY haCss, const char * sElement, const GUI_XML_ATTRIBUTE * pFirstAttrib);
void      GUI_CSS__ReadAttribValuePair(const char ** psCSS, char ** ppAttrib, char ** ppValue);

#define GUI_CSS_BEGIN_ITERATE_ATTRIBS   GUI_XML_BEGIN_ITERATE_ATTRIBS
#define GUI_CSS_END_ITERATE_ATTRIBS     GUI_XML_END_ITERATE_ATTRIBS

/*********************************************************************
*
*       Defines
*
**********************************************************************
*/
//
// Type aliases
//
#define F32  float
#define F64  double
//
// Physical display size.
//
#define LCD_XSIZE     ((LCD_GetSwapXY()) ? LCD_GetYSize() : LCD_GetXSize())
#define LCD_YSIZE     ((LCD_GetSwapXY()) ? LCD_GetXSize() : LCD_GetYSize())
#define LCD_XSIZE_F   ((F32)LCD_XSIZE)
#define LCD_YSIZE_F   ((F32)LCD_YSIZE)

#define LOCK_ABSTRACT(TYPE, HANDLE_VAR, PTR_VAR)    {                     \
                            TYPE * PTR_VAR;                               \
                            if (HANDLE_VAR) {                             \
                              PTR_VAR = (TYPE *)GUI_LOCK_H((GUI_HMEM)HANDLE_VAR);   \
                              if (PTR_VAR) {
#define UNLOCK_ABSTRACT(PTR_VAR) GUI_UNLOCK_H(PTR_VAR);                   \
                              }                                           \
                            }                                             \
                          }

#define SVG_LOCK(h)        GUI_LOCK(); LOCK_ABSTRACT(GUI_SVG_Obj, h, pObj)
#define SVG_UNLOCK()       UNLOCK_ABSTRACT(pObj); GUI_UNLOCK()
#define GUI_ARRAY_ADD_ITEM(ARR, VAR)   GUI_ARRAY_AddItem(ARR, &VAR, sizeof(VAR))

/*********************************************************************
*
*       Defines, configurable
*
**********************************************************************
*/
#ifndef   GUI_SVG_MAX_NUM_DASH_ITEMS
  #define GUI_SVG_MAX_NUM_DASH_ITEMS    10
#endif

/*********************************************************************
*
*       Enum types
*
**********************************************************************
*/
typedef enum {
  GUI_SVG_PARSE_INIT,
  GUI_SVG_PARSE_DRAW,
} GUI_SVG_PARSING_STRATEGY;

/*********************************************************************
*
*       Structure types
*
**********************************************************************
*/
//
// Internal flags
//
#define GUI_SVG_FLAG_CACHEMODE    (1 << 0)    // Caching enabled.
#define GUI_SVG_FLAG_INVALID      (1 << 1)    // Cache invalid.

//
// Aliases for common matrices and parameters
//
#define MAT_SVG(pSVG)    (&pSVG->BaseData.Mat)  // Current result of all loaded matrices and affine transformations.
#define MAT_TR(pSVG)     (&pSVG->Transform.aMatrix[GUI_SVG_MATRIX_TRANSLATE])
#define MAT_SC(pSVG)     (&pSVG->Transform.aMatrix[GUI_SVG_MATRIX_SCALE])
#define MAT_RO(pSVG)     (&pSVG->Transform.aMatrix[GUI_SVG_MATRIX_ROTATE])
#define VEC_RO(pSVG)     (&pSVG->Transform.aMatrix[GUI_SVG_VECTOR_ROTATE])
#define MAT_CUST(pSVG)   ((GUI_MATRIX *)GUI_ALLOC_h2p(pSVG->Transform.hMatrix)) // Custom matrix set by user.

typedef enum {
  GUI_SVG_MATRIX_TRANSLATE,   // Translation set by GUI_SVG_Translate().
  GUI_SVG_MATRIX_SCALE,       // Scale set by GUI_SVG_Scale().
  GUI_SVG_MATRIX_ROTATE,      // Rotation set by GUI_SVG_Rotate().
  GUI_SVG_VECTOR_ROTATE,
  //
  GUI_SVG_MATRIX_COUNT,       // LEAVE UNCHANGED!
} GUI_SVG_MATRIX_ID;

typedef struct {
  GUI_MATRIX aMatrix[GUI_SVG_MATRIX_COUNT];
  GUI_HMEM   hMatrix;     // Custom transformation matrix supplied with GUI_SVG_Transform()
} GUI_SVG_TRANSFORM_CONTEXT;

typedef struct {
  GUI_VG_GRADIENT * pCurrentGrad;
  U8                AcceptCss; // Flag to accept the next CDATA read as CSS data.
} GUI_SVG_PARSER_CONTEXT;

//
// The data that is saved for every indendation level.
// For each indentation level, a new instance of below struct is added.
// If the level decreases the previous one is restored.
// 
// This behavior was previously achieved with recursion and stack memory, but the new parsing
// strategy requires us to do this with a list of heap allocated items,
// because there is no more recursion.
//
typedef struct {
  GUI_VG_STYLE Style;
  GUI_MATRIX   Mat;
} GUI_SVG_INDENT_DATA;

//
// Any raster image within <image> tag
//
typedef struct {
  U32               Off;    // Offset in file, this serves as the identifier because an id attribute is not required.
  GUI_MEMDEV_Handle hImage; // Prerendered image data.
} GUI_SVG_IMAGE;

typedef struct {
  GUI_XML_Handle            hXML;        // SVG file loaded into XML module.
  GUI_SVG_INDENT_DATA       BaseData;    // Matrix and style for top most level <svg>.
  GUI_ARRAY                 haIndent;    // GUI_SVG_INDENT_DATA for each indent level. Index 0 is topmost draw tag. <svg> level not included here.
  GUI_SVG_INFO              Info;        // Public info struct, data is used internally by object, when user retrieves info this will be copied.
  GUI_ARRAY                 haCssRules;  // Array of GUI_CSS_RULEs
  GUI_ARRAY                 haGradients; // Array of GUI_SVG_GRADIENTs, optional.
  GUI_ARRAY                 haImages;    // Array of GUI_SVG_IMAGE, optional.
  GUI_SVG_TRANSFORM_CONTEXT Transform;   // Parameters used for transformations.
  GUI_SVG_PARSER_CONTEXT    ParserCtx;   // Context for parser module.
  GUI_MEMDEV_Handle         hMemDev;     // Memdev used for caching the SVG.
  GUI_COLOR                 BkColor;     // Background color used for filling internal memory device.
  U8                        Flags;       // See GUI_SVG_FLAG...
} GUI_SVG_Obj;

typedef int (DRAW_IMAGE_FILE_FUNC)(const void * pFileData, int FileSize, int x0, int y0);
typedef int (DRAW_GIF_FILE_FUNC)  (const void * pFileData, U32 FileSize, int x0, int y0);
typedef int (DRAW_BMP_FILE_FUNC)  (const void * pFileData,               int x0, int y0);

//
// Abstraction of a GPU for the SVG module.
//
typedef struct {
  int                      (* pfBeginDraw)      (void);
  void                     (* pfEndDraw)        (void);
  int                      (* pfLoadExtension)  (void);
  const GUI_VG_API       * (* pfGetVectorAPI)   (void);
  const GUI_RENDERBUFFER * (* pfGetRenderTarget)(void);
  void                     (* pfGetOutputMatrix)(GUI_MATRIX * pMat, float x, float y, U8 IgnoreMemdev);
  GUI_GPU_DRIVER         * (* pfGetRenderer)    (void);
} GUI_SVG_RENDERER;

//
// Global context
//
typedef struct {
  DRAW_IMAGE_FILE_FUNC     * pfDrawPNG;          // Optional pointer to GUI_PNG_Draw()
  DRAW_IMAGE_FILE_FUNC     * pfDrawJPEG;         // Optional pointer to GUI_JPEG_Draw()
  DRAW_GIF_FILE_FUNC       * pfDrawGIF;          // Optional pointer to GUI_GIF_Draw()
  DRAW_BMP_FILE_FUNC       * pfDrawBMP;          // Optional pointer to GUI_BMP_Draw()
  unsigned                   NumBytesBuffer;     // Size of the buffer that will be used for buffering externally read files.
  GUI_HMEM                   hBase64DecodeTable; // Decoding table for Base64.
  int                        NumDotsPerInch;     // Configured DPI for display, used for real life units like cm.
} GUI_SVG_CONTEXT;

//
// Shorter aliases
//
#define SVG_CONTEXT  (&GUI_SVG__Context)
#define SVG_DRIVER   (GUI__pRendererSVG->pfGetVectorAPI())

//
// Parameters used by draw functions
//
typedef struct {
  float x, y, w, h, rx, ry;
} GUI_SVG_RECT_PARAMETERS;

typedef struct {
  float x1, y1, x2, y2;
} GUI_SVG_LINE_PARAMETERS;

typedef struct {
  float cx, cy, r;
} GUI_SVG_CIRCLE_PARAMETERS;

typedef struct {
  float cx, cy, rx, ry;
} GUI_SVG_ELLIPSE_PARAMETERS;

/*********************************************************************
*
*       Private code
*
**********************************************************************
*/
GUI_VG_GRADIENT * GUI_SVG__GetGradientLocked(GUI_SVG_Obj * pObj, const char * sId);
void              GUI_SVG__Parse            (GUI_SVG_Obj * pObj, GUI_SVG_PARSING_STRATEGY Strategy);
//
// Basic draw routines.
//
void                  GUI_SVG__DrawPath    (const GUI_VG_PATH_Handle         * phPath, const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat);
void                  GUI_SVG__DrawRect    (const GUI_SVG_RECT_PARAMETERS    * p,      const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat);
void                  GUI_SVG__DrawCircle  (const GUI_SVG_CIRCLE_PARAMETERS  * p,      const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat);
void                  GUI_SVG__DrawEllipse (const GUI_SVG_ELLIPSE_PARAMETERS * p,      const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat);
void                  GUI_SVG__DrawLine    (const GUI_SVG_LINE_PARAMETERS    * p,      const GUI_VG_STYLE * pStyle, const GUI_MATRIX * pMat);
void                  GUI_SVG__DrawImage   (GUI_SVG_Obj * pObj, U32 TagOffset, float x, float y, float w, float h);
//
// Management of indentation level data.
//
GUI_SVG_INDENT_DATA * GUI_SVG__IncIndent       (GUI_SVG_Obj * pObj);
void                  GUI_SVG__DecIndent       (GUI_SVG_Obj * pObj);
GUI_SVG_INDENT_DATA * GUI_SVG__GetCurrentIndent(GUI_SVG_Obj * pObj);
void                  GUI_SVG__UnlockIndent    (GUI_SVG_Obj * pObj, GUI_SVG_INDENT_DATA ** ppData);
//
// Constructors for objects
//
void GUI_SVG__InitObj(GUI_SVG_Obj * p);
//
// Private string functions
//
char * GUI__ReadStringUntil (const char * sDelim, const char ** pp);
int    GUI__EqualsIgnoreCase(const char * s0, const char * s1);
int    GUI__BeginsWith      (const char * s0, const char * s1);
//
// Aliases for string functions
//
#define STR_EQUALS(s0, s1)        GUI__EqualsIgnoreCase(s0, s1)
#define STR_BEGINS_WITH(s0, s1)   GUI__BeginsWith(s0, s1)

/*********************************************************************
*
*       Externals
*
**********************************************************************
*/
//
// Global SVG context
//
extern GUI_SVG_CONTEXT GUI_SVG__Context;
//
// Interface to GPU module
//
extern const GUI_SVG_RENDERER * GUI__pRendererSVG;
extern const GUI_SVG_RENDERER   GUI_SVG__Renderer;

#if defined(__cplusplus)
}
#endif

#endif /* GUI_SVG_PRIVATE_H */

/*************************** End of file ****************************/
