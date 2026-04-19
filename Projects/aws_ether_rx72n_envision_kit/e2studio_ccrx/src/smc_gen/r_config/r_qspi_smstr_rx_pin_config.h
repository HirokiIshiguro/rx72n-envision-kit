/***********************************************************************************************************************
* Copyright (c) 2014 - 2025 Renesas Electronics Corporation and/or its affiliates
*
* SPDX-License-Identifier: BSD-3-Clause
***********************************************************************************************************************/
/*******************************************************************************
* System Name  : QSPI single master driver
* File Name    : r_qspi_smstr_rx_pin_config.h
* Version      : 1.22
* Device       : RX
* Abstract     : Configuration file for QSPI single master driver
* Tool-Chain   : Renesas RXC Toolchain v3.01.00
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
*              : 30.09.2016 1.09     Changed Tool-Chain version.
*              :                     Changed pin name.
*              :                     Added RX65N.
*              : 31.07.2017 2.08     Supported RX65N-2MB.
*              :                     Fixed to correspond to Renesas coding rule.
*              : 30.07.2019 1.13     Added RX72M.
*              : 22.11.2019 1.14     Added RX72N and RX66N.
*              : 15.03.2025 1.22     Updated disclaimer
*******************************************************************************/
#ifndef QSPI_SMSTR_PIN_CONFIG_H
#define QSPI_SMSTR_PIN_CONFIG_H

/******************************************************************************
SPECIFY PORTS USED FOR QSPI
******************************************************************************/
/* The #defines specify the ports used for Clock, Data Output and Data Input
   of QSPI individually. */

#if   defined(BSP_MCU_RX64M)
    /* ==== QSPI channel 0 ==== */
    /* ---- Clock port ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QSPCLK_PORT   ('7')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QSPCLK_BIT    ('7')     /* Bit Number  */

    /* ---- Data Input/Output port 0 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO0_PORT     ('C')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO0_BIT      ('3')     /* Bit Number  */

    /* ---- Data Input/Output port 1 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO1_PORT     ('C')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO1_BIT      ('4')     /* Bit Number  */

    /* ---- Data Input/Output port 2 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO2_PORT     ('8')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO2_BIT      ('0')     /* Bit Number  */

    /* ---- Data Input/Output port 3 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO3_PORT     ('8')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO3_BIT      ('1')     /* Bit Number  */

#elif defined(BSP_MCU_RX65N)
    /* ==== QSPI channel 0 ==== */
    /* ---- Clock port ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QSPCLK_PORT   ('D')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QSPCLK_BIT    ('5')     /* Bit Number  */

    /* ---- Data Input/Output port 0 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO0_PORT     ('D')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO0_BIT      ('6')     /* Bit Number  */

    /* ---- Data Input/Output port 1 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO1_PORT     ('D')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO1_BIT      ('7')     /* Bit Number  */

    /* ---- Data Input/Output port 2 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO2_PORT     ('D')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO2_BIT      ('2')     /* Bit Number  */

    /* ---- Data Input/Output port 3 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO3_PORT     ('D')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO3_BIT      ('3')     /* Bit Number  */

#elif defined(BSP_MCU_RX66N)
    /* ==== QSPI channel 0 ==== */
    /* ---- Clock port ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QSPCLK_PORT   ('N')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QSPCLK_BIT    ('4')     /* Bit Number  */

    /* ---- Data Input/Output port 0 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO0_PORT     ('J')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO0_BIT      ('3')     /* Bit Number  */

    /* ---- Data Input/Output port 1 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO1_PORT     ('J')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO1_BIT      ('5')     /* Bit Number  */

    /* ---- Data Input/Output port 2 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO2_PORT     ('0')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO2_BIT      ('0')     /* Bit Number  */

    /* ---- Data Input/Output port 3 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO3_PORT     ('0')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO3_BIT      ('1')     /* Bit Number  */

#elif defined(BSP_MCU_RX71M)
    /* ==== QSPI channel 0 ==== */
    /* ---- Clock port ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QSPCLK_PORT   ('7')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QSPCLK_BIT    ('7')     /* Bit Number  */

    /* ---- Data Input/Output port 0 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO0_PORT     ('C')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO0_BIT      ('3')     /* Bit Number  */

    /* ---- Data Input/Output port 1 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO1_PORT     ('C')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO1_BIT      ('4')     /* Bit Number  */

    /* ---- Data Input/Output port 2 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO2_PORT     ('8')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO2_BIT      ('0')     /* Bit Number  */

    /* ---- Data Input/Output port 3 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO3_PORT     ('8')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO3_BIT      ('1')     /* Bit Number  */

#elif defined(BSP_MCU_RX72M)
    /* ==== QSPI channel 0 ==== */
    /* ---- Clock port ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QSPCLK_PORT   ('7')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QSPCLK_BIT    ('7')     /* Bit Number  */

    /* ---- Data Input/Output port 0 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO0_PORT     ('C')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO0_BIT      ('3')     /* Bit Number  */

    /* ---- Data Input/Output port 1 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO1_PORT     ('C')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO1_BIT      ('4')     /* Bit Number  */

    /* ---- Data Input/Output port 2 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO2_PORT     ('8')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO2_BIT      ('0')     /* Bit Number  */

    /* ---- Data Input/Output port 3 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO3_PORT     ('8')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO3_BIT      ('1')     /* Bit Number  */

#elif defined(BSP_MCU_RX72N)
    /* ==== QSPI channel 0 ==== */
    /* ---- Clock port ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QSPCLK_PORT   ('D')     /* Port Dumber */
    #define R_QSPI_SMSTR_CFG_QSPI_QSPCLK_BIT    ('5')     /* Bit Number  */

    /* ---- Data Input/Output port 0 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO0_PORT     ('D')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO0_BIT      ('6')     /* Bit Number  */

    /* ---- Data Input/Output port 1 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO1_PORT     ('D')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO1_BIT      ('7')     /* Bit Number  */

    /* ---- Data Input/Output port 2 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO2_PORT     ('D')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO2_BIT      ('2')     /* Bit Number  */

    /* ---- Data Input/Output port 3 ---- */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO3_PORT     ('D')     /* Port Number */
    #define R_QSPI_SMSTR_CFG_QSPI_QIO3_BIT      ('3')     /* Bit Number  */

#else
    #error "This MCU is not supported by the current r_qspi_smstr_rx module."
#endif  /* defined(BSP_MCU_RX64M) */

#endif /* _QSPI_API_PIN_CONFIG_H */


/* End of File */

