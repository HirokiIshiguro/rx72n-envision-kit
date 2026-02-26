# Things to prepare
* Indispensable
    * RX72N Envision Kit × 1 unit
    * USB cable (USB Micro-B --- USB Type A) × 2 
    * Windows PC × 1 unit
        * Tools to be installed in Windows PC 
            * [e2 studio 2020-04](https://www.renesas.com/products/software-tools/tools/ide/e2studio.html)
                * Initial boot sometimes takes time
            * [CC-RX](https://www.renesas.com/products/software-tools/tools/compiler-assembler/compiler-package-for-rx-family.html) V3.02 or later

# Prerequisite
* [Generate new project (bare metal)](../../bare-metal/generate-new-project.md) must be completed.
    * In this section, implement by adding the code of how to access Macronix serial flash to LED 0.1 second cycle blinking program which was generated in [Generate new project (bare metal)](../../bare-metal/generate-new-project.md)

# Check circuit
* <a href="../../images/027_board_serial_flash.png" target="_blank"><img src="../../images/027_board_serial_flash.png" width="480px" target="_blank"></a>
    * QSPI (Quad Serial Peripheral Interface) is an interface of 6 lines in total, including four data signal lines, one data synchronous clock signal line and one chip select signal line as shown in the above circuit SIO0-SIO3.
    * In general, SPI has one data signal line, on the other hand, QSPI has four.
    * Accordingly, the transfer efficiency of QSPI per one clock is four times better than that of SPI, thereby, high speed.

# Set QSPI driver software with Smart Configurator
## Add component
* <a href="../../images/028_e2_studio_sc5.png" target="_blank"><img src="../../images/028_e2_studio_sc5.png" width="480px" target="_blank"></a>
    * Add four components as shown above.
        * r_qspi_smstr_rx (Explained in the above screenshot)
        * r_flash_spi
        * r_memdrv_rx
        * r_sys_time_rx

## Set component
### r_qspi_smstr_rx
* Perform setting in which QSPI related pins are used
    * <a href="../../images/029_e2_studio_sc6.png" target="_blank"><img src="../../images/029_e2_studio_sc6.png" width="480px" target="_blank"></a>

### r_flash_spi
* None (Source code requires fine-tune later)

### r_memdrv_rx
* Connect memory driver to QSPI
* Change the transfer clock frequency of QSPI to 30MHz.
    * <a href="../../images/032_e2_studio_sc9.png" target="_blank"><img src="../../images/032_e2_studio_sc9.png" width="480px" target="_blank"></a>

### r_sys_time_rx
* None

## Pin setting
* <a href="../../images/030_e2_studio_sc7.png" target="_blank"><img src="../../images/030_e2_studio_sc7.png" width="480px" target="_blank"></a>
    * Since RX72N MCU assigns multiple functions to one pin, you need to perform setting of which function to be used with software.
    * In RX72N Envision Kit, QSPI serial flash is controlled by five pins of PD2, PD3, PD5, PD6 and PD7
    * Since PD4 is connected to #CS (chip select), and unlike other pins, this pin is not controlled by QSPI function but by general-purpose port function, the setting of PD4 is performed separately with the FIT module on r_flash_spi side. (Improvement is required)
    * Perform setting on Smart Configurator as shown in the above picture to generate code.
    * By reading Board Configuration File (BDF), "pin setting" on Smart Configurator is automated.

### r_flash_spi (Fine-tune of source code)
* /src/smc_gen/r_config/r_flash_spi_pin_config.h
```
#define FLASH_SPI_CS_DEV0_CFG_PORTNO    'D'     /* Device 0 Port Number : FLASH SS#    */
#define FLASH_SPI_CS_DEV0_CFG_BITNO     '4'     /* Device 0 Bit Number  : FLASH SS#    */
```

## Coding of main() function
* Add code to rx72n_envision_kit.c as shown below.
* In this code, write/read the repeated pattern of "0x12345678, 0x9abcdef0" into serial flash. And repeat this for 1MB.
* Overwriting can not be performed in serial flash, accordingly, you need to write after elimination. Perform elimination with SERIAL_FLASH_STATE_ERASE in main ().
```rx72n_envision_kit.c
#include "r_smc_entry.h"
#include "platform.h"
#include "r_cmt_rx_if.h"
#include "r_flash_spi_if.h"
#include "r_flash_spi_config.h"
#include "r_sys_time_rx_if.h"

/*******************************************************************************
Macro definitions
*******************************************************************************/
#define SERIAL_FLASH_TASK_DATA_SIZE (0x00100000)
#define SERIAL_FLASH_64KB_SIZE (0x00010000)
#define SERIAL_FLASH_PAGE_SIZE (256)

/*******************************************************************************
Typedef definitions
*******************************************************************************/
typedef enum e_serial_flash_state
{
    SERIAL_FLASH_STATE_ERASE,
    SERIAL_FLASH_STATE_ERASE_WAIT_COMPLETE,
    SERIAL_FLASH_STATE_WRITE,
    SERIAL_FLASH_STATE_WRITE_WAIT_COMPLETE,
    SERIAL_FLASH_STATE_READ,
    SERIAL_FLASH_STATE_FINISH,
    SERIAL_FLASH_STATE_ERROR
} serial_flash_state_t;

/*******************************************************************************
Imported global variables and functions (from other files)
*******************************************************************************/

/*******************************************************************************
Exported global variables and functions (to be accessed by other files)
*******************************************************************************/
const uint32_t cbuf1[SERIAL_FLASH_PAGE_SIZE/sizeof(uint32_t)] = {
        0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0,
        0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0,
        0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0,
        0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0,
        0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0,
        0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0,
        0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0,
        0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0, 0x12345678, 0x9abcdef0
};
static uint32_t cbuf2[SERIAL_FLASH_PAGE_SIZE/sizeof(uint32_t)];
static uint8_t  gDevNo;
static uint8_t  gStat;
static serial_flash_state_t g_serial_flash_state;

/*******************************************************************************
Private global variables and functions
*******************************************************************************/
void main(void);
void cmt_callback(void *arg);
static serial_flash_state_t serial_flash_update(void);

void main(void)
{
	uint32_t channel;
	R_CMT_CreatePeriodic(10, cmt_callback, &channel);

    serial_flash_state_t state;
    /* wait completing gui initializing */
    R_SYS_TIME_RegisterPeriodicCallback(R_FLASH_SPI_1ms_Interval, 1);
    gDevNo = FLASH_SPI_DEV0;
    R_FLASH_SPI_Open(gDevNo);
    R_FLASH_SPI_Set_4byte_Address_Mode(gDevNo);
    R_FLASH_SPI_Quad_Enable(gDevNo);
    R_FLASH_SPI_Read_Status(gDevNo, &gStat); // debug (gStat & 0x40) != 0x00
    R_FLASH_SPI_Set_Write_Protect(gDevNo, 0);
    R_FLASH_SPI_Read_Status(gDevNo, &gStat); // debug gStat & (0x0f << 2) !=0x00
    g_serial_flash_state = SERIAL_FLASH_STATE_ERASE;
    while(1)
    {
        serial_flash_update();
    }
}

void cmt_callback(void *arg)
{
	if(PORT4.PIDR.BIT.B0 == 1)
	{
		PORT4.PODR.BIT.B0 = 0;
	}
	else
	{
		PORT4.PODR.BIT.B0 = 1;
	}
}

static serial_flash_state_t serial_flash_update(void)
{
    static uint32_t serial_flash_address = 0;
    static flash_spi_info_t Flash_Info_W;
    static flash_spi_info_t Flash_Info_R;
    static flash_spi_erase_info_t Flash_Info_E;

    switch (g_serial_flash_state)
    {
        case SERIAL_FLASH_STATE_ERASE:
            Flash_Info_E.addr   = serial_flash_address;
            Flash_Info_E.mode   = FLASH_SPI_MODE_B64K_ERASE;
            if (R_FLASH_SPI_Erase(gDevNo, &Flash_Info_E) == FLASH_SPI_SUCCESS)
            {
                g_serial_flash_state = SERIAL_FLASH_STATE_ERASE_WAIT_COMPLETE;
            }
            else
            {
                g_serial_flash_state = SERIAL_FLASH_STATE_ERROR;
            }
            break;
        case SERIAL_FLASH_STATE_ERASE_WAIT_COMPLETE:
            if (R_FLASH_SPI_Polling(gDevNo, FLASH_SPI_MODE_ERASE_POLL) == FLASH_SPI_SUCCESS)
            {
				serial_flash_address += SERIAL_FLASH_64KB_SIZE;
				if (SERIAL_FLASH_TASK_DATA_SIZE == serial_flash_address)
				{
					serial_flash_address = 0;
					Flash_Info_W.cnt     = SERIAL_FLASH_TASK_DATA_SIZE;
					g_serial_flash_state = SERIAL_FLASH_STATE_WRITE;
				}
				else
				{
					g_serial_flash_state = SERIAL_FLASH_STATE_ERASE;
				}
            }
            break;
        case SERIAL_FLASH_STATE_WRITE:
            Flash_Info_W.addr    = serial_flash_address;
            Flash_Info_W.p_data  = (uint8_t *)cbuf1;
            Flash_Info_W.op_mode = FLASH_SPI_QUAD;
            if (R_FLASH_SPI_Write_Data_Page(gDevNo, &Flash_Info_W) == FLASH_SPI_SUCCESS)
            {
                g_serial_flash_state = SERIAL_FLASH_STATE_WRITE_WAIT_COMPLETE;
            }
            else
            {
                g_serial_flash_state = SERIAL_FLASH_STATE_ERROR;
            }
            break;
        case SERIAL_FLASH_STATE_WRITE_WAIT_COMPLETE:
            if (R_FLASH_SPI_Polling(gDevNo, FLASH_SPI_MODE_PROG_POLL) == FLASH_SPI_SUCCESS)
            {
				serial_flash_address += SERIAL_FLASH_PAGE_SIZE;
				if (SERIAL_FLASH_TASK_DATA_SIZE == serial_flash_address)
				{
					serial_flash_address = 0;
					g_serial_flash_state = SERIAL_FLASH_STATE_READ;
				}
				else
				{
					g_serial_flash_state = SERIAL_FLASH_STATE_WRITE;
				}
            }
            break;
        case SERIAL_FLASH_STATE_READ:
            Flash_Info_R.cnt     = SERIAL_FLASH_PAGE_SIZE;
            Flash_Info_R.addr    = serial_flash_address;
            Flash_Info_R.p_data  = (uint8_t *)cbuf2;
            Flash_Info_R.op_mode = FLASH_SPI_QUAD;
            if (R_FLASH_SPI_Read_Data(gDevNo, &Flash_Info_R) == FLASH_SPI_SUCCESS)
            {
				serial_flash_address += SERIAL_FLASH_PAGE_SIZE;
				if (SERIAL_FLASH_TASK_DATA_SIZE == serial_flash_address)
				{
                     serial_flash_address = 0;
                     g_serial_flash_state = SERIAL_FLASH_STATE_FINISH;
                }
            }
            else
            {
                g_serial_flash_state = SERIAL_FLASH_STATE_ERROR;
            }
            break;
        case SERIAL_FLASH_STATE_FINISH:
            /* If do not want to repeat SERIAL_FLASH_STATE_FINISH, update the state. */
            break;
        case SERIAL_FLASH_STATE_ERROR:
            R_FLASH_SPI_Write_Di(gDevNo);
            break;
        default:
            break;
    }
    return g_serial_flash_state;
}
```
