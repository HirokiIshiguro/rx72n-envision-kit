/**********************************************************************************************************************
 * DISCLAIMER
 * This software is supplied by Renesas Electronics Corporation and is only intended for use with Renesas products. No
 * other uses are authorized. This software is owned by Renesas Electronics Corporation and is protected under all
 * applicable laws, including copyright laws.
 * THIS SOFTWARE IS PROVIDED "AS IS" AND RENESAS MAKES NO WARRANTIES REGARDING
 * THIS SOFTWARE, WHETHER EXPRESS, IMPLIED OR STATUTORY, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. ALL SUCH WARRANTIES ARE EXPRESSLY DISCLAIMED. TO THE MAXIMUM
 * EXTENT PERMITTED NOT PROHIBITED BY LAW, NEITHER RENESAS ELECTRONICS CORPORATION NOR ANY OF ITS AFFILIATED COMPANIES
 * SHALL BE LIABLE FOR ANY DIRECT, INDIRECT, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES FOR ANY REASON RELATED TO
 * THIS SOFTWARE, EVEN IF RENESAS OR ITS AFFILIATES HAVE BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
 * Renesas reserves the right, without notice, to make changes to this software and to discontinue the availability of
 * this software. By using this software, you agree to the additional terms and conditions found by accessing the
 * following link:
 * http://www.renesas.com/disclaimer
 *
 * Copyright (C) 2020 Renesas Electronics Corporation. All rights reserved.
 *********************************************************************************************************************/
/**********************************************************************************************************************
 * File Name    : audio_task.c
 * Description  : Phase 8b 第3次 段階5-6 (rx72n-envision-kit#59) で legacy aws_demos の同名ファイル
 *                (vendors/.../renesas_code/audio_task.c, 108行) を v3 baseline に取り込んだ placeholder。
 *                legacy 本体は private_function() 内 vTaskDelay(0xffffffff) の永久 sleep のみで、
 *                実 audio 機能 (SSI codec / DMA driver) は legacy にも存在しない。本ファイルは
 *                main.c の xTaskCreate と TASK_INFO::audio_task_handle の wiring 一貫性のための
 *                placeholder。実機能は段階5-6b 以降で別途。
 *                FIT include (r_ssi_api_rx, r_dmaca_rx 等) は本体未使用かつ v3 baseline に
 *                未取り込みのため legacy から削除済。
 *********************************************************************************************************************/
/**********************************************************************************************************************
 * History : DD.MM.YYYY Version  Description
 *         : 20.11.2020 1.00     First Release (legacy aws_demos)
 *         : 19.04.2026 1.10     Phase 8b 段階5-6: v3 baseline 配置 (FIT include 整理)
 *********************************************************************************************************************/

#include "FreeRTOS.h"
#include "task.h"

void audio_task( void * pvParameters );

static void private_function( void );

void audio_task( void * pvParameters )
{
    ( void ) pvParameters;

    private_function();

    while( 1 )
    {
        vTaskDelay( 0xffffffff );
    }
}

static void private_function( void )
{
    while( 1 )
    {
        vTaskDelay( 100 );
    }
}
