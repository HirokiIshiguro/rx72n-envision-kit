/* Generated configuration header file - do not edit */
/***********************************************************************************************************************
* Copyright (c) 2014 - 2025 Renesas Electronics Corporation and/or its affiliates
*
* SPDX-License-Identifier: BSD-3-Clause
***********************************************************************************************************************/
/*******************************************************************************
* System Name  : QSPI single master driver
* File Name    : r_qspi_smstr_rx_config.h
* Version      : 1.30
* Device       : RX
* Abstract     : Configuration file for QSPI single master driver
* Tool-Chain   : Renesas RXC Toolchain v3.07.00
* OS           : not use
* H/W Platform : not use
* Description  : Configures the QSPI single master driver.
* Limitation   : none
*******************************************************************************/
/*******************************************************************************
* History      : DD.MM.YYYY Version  Description
*              : 24.06.2014 1.05     First Release
*              : 29.08.2014 1.06     Not change program due to changing r_qspi_smstr_private.h.
*              :                     Added demo source for DTC in this driver.
*              : 28.11.2014 1.07     Changed the waiting for transfer completion of DMAC or DTC
*              :                     from the software wait to the timer wait.
*              : 30.01.2015 1.08     Added RX71M.
*              : 31.07.2017 2.08     Supported RX65N-2MB.
*              :                     Fixed to correspond to Renesas coding rule.
*              : 15.03.2025 1.22     Updated disclaimer
*              : 30.10.2025 1.30     Added support Nested Interrupt
*******************************************************************************/
#ifndef QSPI_SMSTR_CONFIG_H
#define QSPI_SMSTR_CONFIG_H

/*******************************************************************************
Includes <System Includes> , "Project Includes"
*******************************************************************************/
#include "r_qspi_smstr_rx_pin_config.h"


/******************************************************************************
USE FIRMWARE INTEGRATION TECHNOLOGY
******************************************************************************/
#define QSPI_SMSTR_CFG_USE_FIT


/******************************************************************************
SPECIFY CHANNELS TO INCLUDE SOFTWARE SUPPORT
******************************************************************************/
/* If these are defined, then the code for the specified channel is valid.
   If the #define which channel is not supported on the MCU is uncommented,
   then the compile error occurs. */

/* #define for QSPI channel 0 to be valid. */
#define QSPI_SMSTR_CFG_CH0_INCLUDED

/* #define for QSPI channel 1 to be valid. */
/* #define QSPI_SMSTR_CFG_CH1_INCLUDED */


/******************************************************************************
ENABLE DEBUGGING INFORMATION
******************************************************************************/
/* Store error log information with LONGQ driver.*/
/* #define QSPI_SMSTR_CFG_LONGQ_ENABLE */


/******************************************************************************
SET INTERRUPT SOURCE PRIORITY LEVEL OF SPTI AND SPRI USING DMAC/DTC
******************************************************************************/
/* In the case of DMAC/DTC, set the interrupt source priority level of spti and spri. */
#define QSPI_SMSTR_CFG_CH0_INT_SPTI_LEVEL     (10)
#define QSPI_SMSTR_CFG_CH0_INT_SPRI_LEVEL     (10)
#define QSPI_SMSTR_CFG_CH1_INT_SPTI_LEVEL     
#define QSPI_SMSTR_CFG_CH1_INT_SPRI_LEVEL     

/* Specifies whether to include code for Nested Interrupt SPTI. */
#define QSPI_SMSTR_CFG_SPTI_EN_NESTED_INT (0)

/* Specifies whether to include code for Nested Interrupt SPRI. */
#define QSPI_SMSTR_CFG_SPRI_EN_NESTED_INT (0)

#endif /* _QSPI_API_CONFIG_H */

/* End of File */

