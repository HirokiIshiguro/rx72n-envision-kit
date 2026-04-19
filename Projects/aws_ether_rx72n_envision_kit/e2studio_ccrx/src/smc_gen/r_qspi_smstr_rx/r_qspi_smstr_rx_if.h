/***********************************************************************************************************************
* Copyright (c) 2014 - 2025 Renesas Electronics Corporation and/or its affiliates
*
* SPDX-License-Identifier: BSD-3-Clause
***********************************************************************************************************************/
/*******************************************************************************
* System Name  : QSPI single master driver
* File Name    : r_qspi_smstr_rx_if.h
* Version      : 1.30
* Device       : RX
* Abstract     : Interface file for QSPI single master driver
* Tool-Chain   : Renesas RXC Toolchain v3.07.00
* OS           : not use
* H/W Platform : not use
* Description  : Functions, typedefs and macros for QSPI single master driver
* Limitation   : none
*******************************************************************************/
/*******************************************************************************
* History      : DD.MM.YYYY Version  Description
*              : 24.06.2014 1.05     First Release
*              : 29.08.2014 1.06     Not change program due to changing r_qspi_smstr_private.h.
*              :                     Added demo source for DTC in this driver.
*              : 28.11.2014 1.07     Added R_QSPI_SMstr_1ms_Interval().
*              : 30.01.2015 1.08     Added RX71M.
*              : 30.09.2016 1.09     Added RX65N.
*              : 31.07.2017 1.10     Supported RX65N-2MB.
*              :                     Fixed to correspond to Renesas coding rule.
*              : 01.02.2019 1.11     Changed Minor version to 1.11.
*              : 20.05.2019 1.12     Added support for GNUC and ICCRX.
*              :                     Fixed coding style. 
*              : 30.07.2019 1.13     Added RX72M.
*              : 22.11.2019 1.14     Added RX72N and RX66N.
*              : 30.09.2021 1.15     Changed Minor version to 1.15
*              : 30.09.2022 1.20     Added new demo projects.
*              : 15.06.2023 1.21     Fixed typo in the file r_qspi_smstr_target_dev_port.c for all devices
*              : 15.03.2025 1.22     Updated disclaimer
*              : 30.10.2025 1.30     Removed doc folder and updated .rcpc file in FITDemos.
*              :                     Added support Nested Interrupt
*******************************************************************************/
#ifndef QSPI_SMSTR_IF_H_
#define QSPI_SMSTR_IF_H_

/*******************************************************************************
Includes <System Includes> , "Project Includes"
*******************************************************************************/
/* Includes board and MCU related header files. */
#include "platform.h"


/*******************************************************************************
Macro definitions
*******************************************************************************/
#if R_BSP_VERSION_MAJOR < 5
    #error "This module must use BSP module of Rev.5.00 or higher. Please use the BSP module of Rev.5.00 or higher."
#endif

#define QSPI_SMSTR_VERSION_MAJOR      (1)
#define QSPI_SMSTR_VERSION_MINOR      (30)


/*******************************************************************************
Typedef definitions
*******************************************************************************/
/* Enumeration for return values and values of channel state flag. */
typedef enum e_qspi_smstr_status
{
    QSPI_SMSTR_SUCCESS    = 0,            /* Successful operation                     */
    QSPI_SMSTR_ERR_PARAM  = -1,           /* Parameter error                          */
    QSPI_SMSTR_ERR_HARD   = -2,           /* Hardware error                           */
    QSPI_SMSTR_ERR_OTHER  = -7            /* Other error                              */
} qspi_smstr_status_t;


/* Enumeration for values of SPI operation mode. */
typedef enum e_qspi_smstr_opmode
{
    QSPI_SMSTR_SINGLE_SPI_WRITE = 0,      /* Single-SPI mode for writing              */
    QSPI_SMSTR_SINGLE_SPI_READ,           /* Single-SPI mode for reading              */
    QSPI_SMSTR_SINGLE_SPI_WRITEREAD,      /* Single-SPI mode for writing and reading  */
    QSPI_SMSTR_DUAL_SPI,                  /* Dual-SPI mode                            */
    QSPI_SMSTR_QUAD_SPI                   /* Quad-SPI mode                            */
} qspi_smstr_opmode_t;


/* Define for data transfer mode. */
typedef enum e_qspi_smstr_tranmode
{
    QSPI_SMSTR_SW         = 0,            /* Data transfer mode is software.          */
    QSPI_SMSTR_DMAC,                      /* Data transfer mode is DMAC.              */
    QSPI_SMSTR_DTC                        /* Data transfer mode is DTC.               */
} qspi_smstr_tranmode_t;

/* Define for QSPI Information structure type. */
typedef volatile struct
{
    uint32_t              data_cnt;       /* Number of data (byte unit)               */
    uint8_t             * p_tx_data;      /* Pointer to transmit data buffer          */
    uint8_t             * p_rx_data;      /* Pointer to receive data buffer           */
    qspi_smstr_opmode_t   op_mode;        /* SPI operating mode                       */
    qspi_smstr_tranmode_t tran_mode;      /* Data transfer mode                       */
} qspi_smstr_info_t;

/* DMAC/DTC transfer flag */
typedef enum e_qspi_smstr_trans_flg
{
    QSPI_SET_TRANS_STOP,
    QSPI_SET_TRANS_START
} qspi_smstr_trans_flg_t;


/*******************************************************************************
Exported global variables and functions (to be accessed by other files)
*******************************************************************************/
qspi_smstr_status_t R_QSPI_SMstr_Open(uint8_t channel, uint8_t spbr_data);
qspi_smstr_status_t R_QSPI_SMstr_Close(uint8_t channel);
qspi_smstr_status_t R_QSPI_SMstr_Control(uint8_t channel, uint8_t clk_mode, uint8_t spbr_data);
qspi_smstr_status_t R_QSPI_SMstr_Write(uint8_t channel, qspi_smstr_info_t * p_qspi_smstr_info);
qspi_smstr_status_t R_QSPI_SMstr_Read(uint8_t channel, qspi_smstr_info_t * p_qspi_smstr_info);
qspi_smstr_status_t R_QSPI_SMstr_Get_BuffRegAddress(uint8_t channel, uint32_t *p_spdr_adr);
void                R_QSPI_SMstr_Int_Spti_Ier_Clear(uint8_t channel);
void                R_QSPI_SMstr_Int_Spri_Ier_Clear(uint8_t channel);
qspi_smstr_status_t R_QSPI_SMstr_Int_Spti_Dmacdtc_Flag_Set(uint8_t channel, qspi_smstr_trans_flg_t flg);
qspi_smstr_status_t R_QSPI_SMstr_Int_Spri_Dmacdtc_Flag_Set(uint8_t channel, qspi_smstr_trans_flg_t flg);
uint32_t            R_QSPI_SMstr_GetVersion(void);
qspi_smstr_status_t R_QSPI_SMstr_Set_LogHdlAddress(uint32_t user_long_que);
uint32_t            R_QSPI_SMstr_Log(uint32_t flg, uint32_t fid, uint32_t line);
void                R_QSPI_SMstr_1ms_Interval(void);


/*******************************************************************************
Include specifics for chosen MCU
*******************************************************************************/


#endif /* _QSPI_SMSTR_IF_H_ */


/* End of File */
