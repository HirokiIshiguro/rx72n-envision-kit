/*********************************************************************
*                     SEGGER Microcontroller GmbH                    *
*        Solutions for real time microcontroller applications        *
**********************************************************************
*                                                                    *
*        (c) 1996 - 2022  SEGGER Microcontroller GmbH                *
*                                                                    *
*        Internet: www.segger.com    Support:  support@segger.com    *
*                                                                    *
**********************************************************************
----------------------------------------------------------------------
File        : Application.h
Purpose     : Content to be managed by customer
---------------------------END-OF-HEADER------------------------------
*/

#ifndef APPLICATION_H
#define APPLICATION_H

/* Phase 8b 第3次 段階5-1 (rx72n-envision-kit#49 / MR !86):
 * Legacy aws_demos の rx72n_envision_kit_system.h は r_usb_basic / r_tfat_lib /
 * firm_update / r_simple_filesystem_on_dataflash 等の FIT モジュールを束ねた
 * 便宜ヘッダだったが、段階5-1 では同 ヘッダの最小スタブ版 (CustomCode/同名) のみを
 * include する。AppWizard 自動生成 CustomCode (ID_SCREEN_*_Slots.c) が参照する
 * TASK_INFO / get_task_info() を提供する。FIT モジュール群の再 include は段階5-3
 * (SDHI/tfat) / 5-4 (firm_update) で必要になった時点で行う。 */
#include "rx72n_envision_kit_system.h"

#endif  // APPLICATION_H

/*************************** End of file ****************************/
