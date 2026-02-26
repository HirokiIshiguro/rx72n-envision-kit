# 目的
* FATファイルシステム「[TFAT](https://www.renesas.com/products/software-tools/software-os-middleware-driver/file-system/m3s-tfat-tiny-for-rx.html)」を介し、SDHIを用いてSDモードmicro SDカードと通信する
* micro SDカード挿入時にはLEDを周期的に点滅させ、未挿入時にはLEDを消す
* micro SDカード挿入後、フォルダとファイルをmicro SDカードに自動作成する

# 準備するもの
* 必須
  * RX72N Envision Kit × 1台
  * USBケーブル(USB Micro-B --- USB Type A) × 1 本
  * Windows PC × 1 台
    * Windows PC にインストールするツール
      * e2 studio 2020-07以降
        * 初回起動時に時間がかかることがある
          * CC-RX V3.02以降
  * micro SDカード(SD、SDHI、SDXC規格のいずれか) × 1 個

# 前提条件
 * [新規プロジェクト作成方法(ベアメタル)](../../bare-metal/generate-new-project.md)を完了すること
   * 本稿では、[新規プロジェクト作成方法(ベアメタル)](../../bare-metal/generate-new-project.md)で作成したLED0.1秒周期点滅プログラムにFATファイルシステムTFATを介してmicro SDカードと通信するためのコードを追加する形で実装する
  * 最新の[RX Driver Package](https://www.renesas.com/products/software-tools/software-os-middleware-driver/software-package/rx-driver-package.html)(FITモジュール)を使用すること
  * 事前にmicro SDカードをFAT32でフォーマットしておくこと
* SDカードのSimplified Specについてその利用条件を把握しておくこと
  * https://www.sdcard.org/downloads/pls/

# <a name="circuit_SDHI"></a>回路確認
* micro SD スロットはSDHI インタフェースを介してMCU と接続される
* RX72N Envision Kitでは、micro SD スロットは以下の信号とポートが割り当てられている
  * <a href="../../images/067_circuit_sdhi.png" target="_blank"><img src="../../images/067_circuit_sdhi.png" width="480px" target="_blank"></a>
  * <a href="../../images/068_pin_assign_table_sd.png" target="_blank"><img src="../../images/068_pin_assign_table_sd.png" width="480px" target="_blank"></a>
* RX72N Envision Kitでは、電源管理回路を使用してMCU により電源出力を制御し、SDHI への3.3V 電源出力を過負荷および短絡から保護する
  * この回路における電源出力用の信号線は```P42_SD_ENABLE```(ポート42に割り当て)である

# スマート・コンフィグレータ(SC)によるドライバソフトウェア/ミドルソフトウェアの設定
## BDF確認
* プロジェクトにBDF```EnvisionRX72N```が適用されていることを確認する（[スマート・コンフィグレータの使い方#ボード設定](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#board_setting)を参照）
  * 適用されていない場合、[スマート・コンフィグレータの使い方#ボード設定](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#board_setting) を参照

## コンポーネント追加
* [スマート・コンフィグレータの使い方#コンポーネント組み込み](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#component_import)を参考に以下の5個のコンポーネントを追加する
  * r_sdhi_rx
  * r_sys_time_rx
  * r_sdc_sdmem_rx
  * r_tfat_driver_rx
  * r_tfat_rx
* <a href="../../images/069_setting_component.png" target="_blank"><img src="../../images/069_setting_component.png" width="480px" target="_blank"></a>

## コンポーネント設定
### r_sdhi_rx
* SDHI関連設定を施す
  * SDHIチャネル0を使用
  * <a href="../../images/070_setting_sdhi1.png" target="_blank"><img src="../../images/070_setting_sdhi1.png" width="480px" target="_blank"></a>
* SDHI関連の端子を使用する設定にする
  * CLK, CMD, CD, WP, D0, D1, D2, D3端子を使用
    * :point_right: [補足] RX72N Envision KIt にはWP端子が実装されていないが、使用する設定を行う
  
  * <a href="../../images/071_setting_sdhi2.png" target="_blank"><img src="../../images/071_setting_sdhi2.png" width="480px" target="_blank"></a>
### r_sys_time_rx
* 無し
### r_sdc_sdmem_rx
* SDモードSDカード制御関連の設定を施す
  * プロトコルステータス確認方法：Hardware 割り込み、データ転送方式：Software 転送
  * <a href="../../images/072_setting_sdc_sdmem.png" target="_blank"><img src="../../images/072_setting_sdc_sdmem.png" width="480px" target="_blank"></a>
### r_tfat_driver_rx
* TFAT driver I/F関連の設定を施す
  * SDカードに使用するドライブ数：1、SDカードに使用するドライブ：Drive 0
    * :point_right: [補足] TFATは、SDカード/USBメモリ/eMMCカード/Serial Flashメモリを最大10個まで同時接続できる（[参考](#TFAT_multi_connection)）
  * <a href="../../images/073_setting_tfat_driver_sdc.png" target="_blank"><img src="../../images/073_setting_tfat_driver_sdc.png" width="480px" target="_blank"></a>
### r_tfat_rx
* 無し
### r_bsp
  * デフォルトで問題なし
### r_cmt_rx
  * デフォルトで問題なし
## 端子設定
* RX72N マイコンは、1個の端子に複数機能が割り当たっているため、どの機能を使用するかの設定をソフトウェアにより施す必要がある
* RX72N Envision KitのBDFを使用している場合、すでに端子を設定済みであるため、作業不要
  * :point_right: [補足] ただし、RX72N Envision KIt にはWP端子が実装されていないが、使用する設定を行う

* <a href="../../images/074_setting_pin_sdhi.png" target="_blank"><img src="../../images/074_setting_pin_sdhi.png" width="480px" target="_blank"></a>
## コード生成
* 上記の設定をすべて完了後、SCの[コード生成](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#code_generation)を実行する

# ユーザアプリケーション部のコーディング
## ソースコード全体
* ```rx72n_envision_kit.c```のソースコード全体を以下に記載する（説明は後述）
```rx72n_envision_kit.c
#include "platform.h"
#include "r_smc_entry.h"
#include "r_sdhi_rx_pinset.h"
#include "r_cmt_rx_if.h"
#include "r_sys_time_rx_if.h"
#include "r_sdc_sd_rx_if.h"
#include "r_sdc_sd_rx_config.h"
#include "r_tfat_driver_rx_config.h"

#define PERFORMANCE_MESUREMENT_DATA_SIZE 1024 * 20 /* 20KB */

typedef enum{
    NO_INITIALIZED = 0,
    IDLE,
    ON_PROCESS, /* Prevent from processing another task */
    REQUEST_SDC_DETECTION_TASK,
    REQUEST_SDC_INSERTION_TASK,
    REQUEST_SDC_REMOVAL_TASK,
} app_status_t;

uint8_t g_drv_tbl[TFAT_SDMEM_DRIVE_NUM];
uint32_t g_sdc_sd_work[TFAT_SDMEM_DRIVE_NUM][50];
FATFS g_fatfs[TFAT_SDMEM_DRIVE_NUM];
FIL g_file[TFAT_SDMEM_DRIVE_NUM];
app_status_t g_app_status = NO_INITIALIZED;
uint8_t g_oneshot_timer_flg = 0;
const uint8_t data_to_write[PERFORMANCE_MESUREMENT_DATA_SIZE] =
{
    0x52, 0x65, 0x6E, 0x65, 0x73, 0x61, 0x73, 0x0a,
}; /* 8 bytes data: Renesas\n */
uint8_t data_to_read[PERFORMANCE_MESUREMENT_DATA_SIZE];

void main(void);
static void initialize_sdc_demo (void);
sdc_sd_status_t r_sdc_sd_cd_callback (int32_t cd);
void set_status_sdc_detection(void);
void card_detection(void);
void process_on_sdc_insertion (void);
void process_on_sdc_removal (void);
void initialize_sdc_on_insertion (uint32_t sdc_no);
void deinitialize_sdc_on_insertion (uint32_t sdc_no);
sdc_sd_status_t r_sdc_sd_callback (int32_t channel);
void tfat_sample (void);
sdc_sd_status_t r_sdc_sdmem_demo_power_init(uint32_t card_no);
sdc_sd_status_t r_sdc_sdmem_demo_power_on(uint32_t card_no);
sdc_sd_status_t r_sdc_sdmem_demo_power_off(uint32_t card_no);
sys_time_err_t wait_milliseconds (uint32_t interval_milliseconds);
void set_oneshot_timer_flg (void);
static void error_trap_r_sdc_sd (uint32_t sdc_sd_card_no);
void blink_LED(void);

void cmt_1us_callback(void *arg);
void _1us_timer_reset(void);
void _1us_timer_stop(void);
void _1us_timer_start(void);
uint32_t _1us_timer_get(void);

uint32_t _1us_timer;
volatile uint32_t _1us_timer_flag;

void main (void)
{
	uint32_t cmt_channel;

    /* Initialize for this demo program */
    initialize_sdc_demo();
    R_CMT_CreatePeriodic(1000000, cmt_1us_callback, &cmt_channel);

    /* Process tasks by a current status */
    while (1)
    {
        switch (g_app_status)
        {
        case NO_INITIALIZED:
            return;
        case IDLE:
            break;
        case ON_PROCESS:
            break;
        case REQUEST_SDC_DETECTION_TASK:
            card_detection();
            break;
        case REQUEST_SDC_INSERTION_TASK:
            process_on_sdc_insertion();
            break;
        case REQUEST_SDC_REMOVAL_TASK:
            process_on_sdc_removal();
            break;
        default:
            return;
        }
    }
}

static void initialize_sdc_demo (void)
{
    uint32_t cmt_channel;
    SYS_TIME sys_time;
    sdc_sd_status_t sdc_sd_status = SDC_SD_SUCCESS;

    /* Initialize global variables for this demo */
    g_app_status = NO_INITIALIZED;
    g_oneshot_timer_flg = 0;

    /* Initialize pin settings for SDHI.
     * This function is generated by SDHI FIT's pin settings of the Smart Configurator */
    R_SDHI_PinSetInit();

    /* System timer settings */
    R_SYS_TIME_Open();
    sys_time.year = 2020;
    sys_time.month = 1;
    sys_time.day = 1;
    sys_time.hour = 0;
    sys_time.min = 0;
    sys_time.sec = 0;
    R_SYS_TIME_SetCurrentTime( &sys_time);

    /* SD card driver Initialization */
    r_sdc_sdmem_demo_power_init(SDC_SD_CARD_NO0);
    sdc_sd_status = R_SDC_SD_Open(SDC_SD_CARD_NO0, SDHI_CH0, &g_sdc_sd_work[SDC_SD_CARD_NO0]);
    if (SDC_SD_SUCCESS != sdc_sd_status)
    {
        /* Function error_trap_r_sdc_sd() can not called because R_SDC_SD_GetErrCode initially needs R_SDC_SD_Open */
        printf("ERROR: R_SDC_SD_Open. Error code (sdc_sd_status_t) is %d.\n", sdc_sd_status);
        while (1)
        {
            R_BSP_NOP();
        }
    }

    /* Register callback when SD card is inserted/removed */
    sdc_sd_status = R_SDC_SD_CdInt(SDC_SD_CARD_NO0, SDC_SD_CD_INT_ENABLE, r_sdc_sd_cd_callback);
    if (SDC_SD_SUCCESS != sdc_sd_status)
    {
        error_trap_r_sdc_sd(SDC_SD_CARD_NO0);
    }

    /* Setting of internal timer of SD card driver */
    R_CMT_CreatePeriodic(1000, (void (*) (void *)) R_SDC_SD_1msInterval, &cmt_channel);

    /* Table between SD card number of SD card driver and dirve number of TFAT */
    g_drv_tbl[SDC_SD_CARD_NO0] = TFAT_DRIVE_NUM_0;

    /* Set status to check the SD card insertion/removal every 10 ms,
     * then process file system tasks when occurring SD card's insertion */
    if (SYS_TIME_SUCCESS == R_SYS_TIME_RegisterPeriodicCallback(set_status_sdc_detection, 1))
    {
        printf("!!! Ready for this demo. Attach SD card. !!!\n");
        g_app_status = IDLE;
    }
}

sdc_sd_status_t r_sdc_sd_cd_callback (int32_t cd)
{
    sdc_sd_status_t sdc_sd_status = SDC_SD_SUCCESS;

    sdc_sd_status = R_SDC_SD_CdInt(SDC_SD_CARD_NO0, SDC_SD_CD_INT_DISABLE, 0);
    if (SDC_SD_SUCCESS != sdc_sd_status)
    {
        error_trap_r_sdc_sd(SDC_SD_CARD_NO0);
    }
    return SDC_SD_SUCCESS;
}

void set_status_sdc_detection (void)
{
    if (IDLE == g_app_status)
    {
        g_app_status = REQUEST_SDC_DETECTION_TASK;
    }
}

void card_detection (void)
{
    static sdc_sd_status_t sdc_sd_card_detection = SDC_SD_ERR;
    static sdc_sd_status_t previous_sdc_sd_card_detection = SDC_SD_ERR;

    g_app_status = ON_PROCESS;

    sdc_sd_card_detection = R_SDC_SD_GetCardDetection(SDC_SD_CARD_NO0);
    if (previous_sdc_sd_card_detection != sdc_sd_card_detection)
    {
        previous_sdc_sd_card_detection = sdc_sd_card_detection;

        if (SDC_SD_SUCCESS == sdc_sd_card_detection)
        {
            /* Detected attached SD card */
            printf("Detected attached SD card.\n");
            g_app_status = REQUEST_SDC_INSERTION_TASK;
        }
        else
        {
            /* Detected detached SD card */
            printf("Detected detached SD card.\n");
            g_app_status = REQUEST_SDC_REMOVAL_TASK;

        }
    }
    else /* if (previous_sdc_sd_card_detection != sdc_sd_card_detection) */
    {
        g_app_status = IDLE;
    }
}

void process_on_sdc_insertion (void)
{
    g_app_status = ON_PROCESS;

    /* SD card initialization */
    initialize_sdc_on_insertion(SDC_SD_CARD_NO0);

    /* Start of blinking LED per 500 ms */
    R_SYS_TIME_RegisterPeriodicCallback(blink_LED, 50);

    /* Process file system tasks */
    if (TFAT_DRIVE_NUM_0 == g_drv_tbl[SDC_SD_CARD_NO0])
    {
        tfat_sample();
    }

    /* SD card de-initialization */
    deinitialize_sdc_on_insertion(SDC_SD_CARD_NO0);

    printf("!!! Detach SD card !!!.\n");
    g_app_status = IDLE;
}

void process_on_sdc_removal (void)
{
    g_app_status = ON_PROCESS;

    r_sdc_sdmem_demo_power_off(SDC_SD_CARD_NO0);

    /* End of blinking LED */
    R_SYS_TIME_UnregisterPeriodicCallback(blink_LED);
    PORT4.PODR.BIT.B0 = 1; /* LED off */

    g_app_status = IDLE;
}

void initialize_sdc_on_insertion (uint32_t sdc_no)
{
    sdc_sd_status_t sdc_sd_status = SDC_SD_SUCCESS;
    sdc_sd_cfg_t sdc_sd_config;

    r_sdc_sdmem_demo_power_on(sdc_no);
    R_SDHI_PinSetTransfer();
    R_SDC_SD_IntCallback(sdc_no, r_sdc_sd_callback);
    sdc_sd_config.mode = SDC_SD_CFG_DRIVER_MODE;
    sdc_sd_config.voltage = SDC_SD_VOLT_3_3;
    sdc_sd_status = R_SDC_SD_Initialize(sdc_no, &sdc_sd_config,
            SDC_SD_MODE_MEM);
    if (SDC_SD_SUCCESS != sdc_sd_status)
    {
        error_trap_r_sdc_sd(sdc_no);
    }
}

void deinitialize_sdc_on_insertion (uint32_t sdc_no)
{
    sdc_sd_status_t sdc_sd_status = SDC_SD_SUCCESS;

    sdc_sd_status = R_SDC_SD_End(sdc_no, SDC_SD_MODE_MEM);
    if (SDC_SD_SUCCESS != sdc_sd_status)
    {
        error_trap_r_sdc_sd(sdc_no);
    }
}

sdc_sd_status_t r_sdc_sd_callback (int32_t channel)
{
    return SDC_SD_SUCCESS;
}

void tfat_sample (void)
{
    const char *drv0 = "0:";
    const char *path_fld = "0:FLD";
    const char *path_txt = "0:FLD/TEXT.TXT";
    uint8_t drv_no = TFAT_DRIVE_NUM_0;
    FRESULT rst;
    UINT file_rw_cnt;

    printf("Start TFAT sample.\n");

    /* Mount the file system (Note delayed mounting) */
    rst = f_mount( &g_fatfs[drv_no], drv0, 0);
    if (FR_OK != rst)
    {
        printf("TFAT Error: Drive mount.\n");
    }

    /* Create the directory */
    rst = f_mkdir(path_fld);
    if (FR_EXIST == rst)
    {
        printf("TFAT Error: Directory \"FLD\" is already existing.\n");
    }
    else if (FR_OK != rst)
    {
        printf("TFAT Error: Directory creation.\n");
    }

    /* Create the file to be written */
    rst = f_open( &g_file[drv_no], path_txt, FA_CREATE_ALWAYS | FA_WRITE);
    if (FR_OK != rst)
    {
        printf("TFAT Error: File creation and open.\n");
    }
    /* Complete file open */

	_1us_timer_reset();
	_1us_timer_start();
    /* Copy the contents to the newly created file */
    rst = f_write( &g_file[drv_no], (void *) data_to_write, sizeof(data_to_write), &file_rw_cnt);
    if (rst != FR_OK || file_rw_cnt < sizeof(data_to_write))
    {
        printf("TFAT Error: File writing operation.\n");
    }
    /* file write complete */
	_1us_timer_stop();
	printf("file write %d bytes takes %d us, throughput = %f Mbps\n", sizeof(data_to_write), _1us_timer_get(), (float)((sizeof(data_to_write) * 8) / (float)((float)_1us_timer_get() / (1000000))/1000000));

    /* Close the file */
    rst = f_close( &g_file[drv_no]);
    if (FR_OK != rst)
    {
        printf("TFAT Error: File close.\n");
    }

    /* Create the file to be written */
    rst = f_open( &g_file[drv_no], path_txt, FA_READ);
    if (FR_OK != rst)
    {
        printf("TFAT Error: File creation and open.\n");
    }
    /* Complete file open */

	_1us_timer_reset();
	_1us_timer_start();
    /* Read the contents from the file */
    rst = f_read( &g_file[drv_no], (void *) data_to_read, sizeof(data_to_read), &file_rw_cnt);
    if (rst != FR_OK || file_rw_cnt < sizeof(data_to_read))
    {
        printf("TFAT Error: File reading operation.\n");
    }
    /* file write complete */
	_1us_timer_stop();
	printf("file read %d bytes takes %d us, throughput = %f Mbps\n", sizeof(data_to_write), _1us_timer_get(), (float)((sizeof(data_to_write) * 8) / (float)((float)_1us_timer_get() / (1000000))/1000000));

    /* Close the file */
    rst = f_close( &g_file[drv_no]);
    if (FR_OK != rst)
    {
        printf("TFAT Error: File close.\n");
    }

    printf("End TFAT sample.\n");
}

sdc_sd_status_t r_sdc_sdmem_demo_power_init (uint32_t card_no)
{
    if (SDC_SD_CARD_NO0 == card_no)
    {
        PORT4.PMR.BIT.B2 = 0x00;
        PORT4.PCR.BIT.B2 = 0x00;
        PORT4.PODR.BIT.B2 = 0x00;     /* SDHI_POWER off */
        PORT4.PDR.BIT.B2 = 0x01;
    }
    return SDC_SD_SUCCESS;
}

sdc_sd_status_t r_sdc_sdmem_demo_power_on (uint32_t card_no)
{
    /* ---- Power On ---- */
    if (SDC_SD_CARD_NO0 == card_no)
    {
        PORT4.PODR.BIT.B2 = 0x01;     /* SDHI_POWER on */
        if (1 == PORT4.PODR.BIT.B2)
        {
            /* Wait for the write completion */
            R_BSP_NOP();
        }
    }

    /* ---- Supplies the Power to the SD Card and waits for 100 ms ---- */
    if(SYS_TIME_SUCCESS != wait_milliseconds(100))
    {
        return SDC_SD_ERR;
    }

    return SDC_SD_SUCCESS;
}


sdc_sd_status_t r_sdc_sdmem_demo_power_off (uint32_t card_no)
{
    /* ---- Power Off ---- */
    if (SDC_SD_CARD_NO0 == card_no)
    {
        PORT4.PODR.BIT.B2 = 0x00;     /* SDHI_POWER off */
        if (1 == PORT4.PODR.BIT.B2)
        {
            /* Wait for the write completion */
            R_BSP_NOP();
        }
    }

    /* ---- Stops the Power to the SD Card and waits for 100 ms ---- */
    if(SYS_TIME_SUCCESS != wait_milliseconds(100))
    {
        return SDC_SD_ERR;
    }

    return SDC_SD_SUCCESS;
}

sys_time_err_t wait_milliseconds (uint32_t interval_milliseconds)
{
    sys_time_err_t sys_time_err = SYS_TIME_ERR_BAD_INTERVAL;
    uint32_t interval_10milliseconds;

    if (1 == g_oneshot_timer_flg)
    {
        return sys_time_err;
    }
    interval_10milliseconds = interval_milliseconds / 10;
    sys_time_err = R_SYS_TIME_RegisterPeriodicCallback(set_oneshot_timer_flg, interval_10milliseconds);
    if (SYS_TIME_SUCCESS != sys_time_err)
    {
        return sys_time_err;
    }
    while(0 == g_oneshot_timer_flg)
    {
        R_BSP_NOP();
    }
    sys_time_err = R_SYS_TIME_UnregisterPeriodicCallback(set_oneshot_timer_flg);
    g_oneshot_timer_flg = 0;
    return sys_time_err;
}

void set_oneshot_timer_flg (void)
{
    g_oneshot_timer_flg = 1;
}

static void error_trap_r_sdc_sd (uint32_t sdc_sd_card_no)
{
    sdc_sd_status_t err_code;

    err_code = R_SDC_SD_GetErrCode(sdc_sd_card_no);

    R_SDC_SD_Log(0x00000001, 0x0000003f, 0x0001ffff);

    printf("ERROR: error code (sdc_sd_status_t) is %d.\n", err_code);
    while (1)
    {
        R_BSP_NOP();
    }
}

void blink_LED(void)
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

void cmt_1us_callback(void *arg)
{
	if(_1us_timer_flag)
	{
		_1us_timer++;
	}
}

void _1us_timer_reset(void)
{
	_1us_timer = 0;
}

void _1us_timer_stop(void)
{
	_1us_timer_flag = 0;
}

void _1us_timer_start(void)
{
	_1us_timer_flag = 1;
}

uint32_t _1us_timer_get(void)
{
	return _1us_timer;
}
```
## 動作確認
* ビルドする
* ダウンロードする
    * https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95#%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D
* printf()の出力先となる e2 studio の Renesas Debug Virtual Console を開いておく
    * Renesas view -> デバッグ -> Renesas Debug Virtual Console
* 実行する
    * Renesas Debug Virtual Console に以下のように出力される
```
!!! Ready for this demo. Attach SD card. !!!
Detected attached SD card.
Start TFAT sample.
TFAT Error: Directory "FLD" is already existing.
file write 20480 bytes takes 5802 us, throughput = 28.238539 Mbps
file read 20480 bytes takes 3368 us, throughput = 48.646080 Mbps
End TFAT sample.
!!! Detach SD card !!!.
```

* マイコン内蔵のCRC演算器を使えばもっと速くなるのでは？　★要検討
    * SDHI内蔵のCRC演算器を使っていた
        * が、SDIOドライバ側はソフトウェア処理しているようだ。こちらは改善できるかもしれない。
            * https://github.com/renesas/rx-driver-package/blob/153ad8704a7b9b368f53546d006d763c83799664/source/r_sdc_sdio_rx/r_sdc_sdio_rx_vx.xx/r_sdc_sdio_rx/src/sdio/r_sdc_sdio_crc.c

## main()関数
* 以下の処理を実行する
  * デモプログラムの初期化```initialize_sdc_demo()```
  * アプリの状況に応じて実行する処理を切り分けるループ
## initialize_sdc_demo()関数
* 以下の処理を実行する
  * SDHI端子の初期化
  * r_sys_time_rxの初期化
  * SDHI電源供給用端子の初期化```r_sdc_sdmem_demo_power_init()```
  * r_sdc_sdmem_rxの初期化
  * SDカード挿抜状態確認要求のための関数```set_status_sdc_detection()```を<br>周期実行ハンドラに登録```R_SYS_TIME_RegisterPeriodicCallback()```
    * :point_right: [補足] ```R_SYS_TIME_RegisterPeriodicCallback()```には最大30個の関数ポインタを登録可能
  * その他の初期化処理
## card_detection()関数
* 以下の処理を実行する（ステータスが```REQUEST_SDC_DETECTION_TASK```時に実行される）
  * SDカード挿抜状態を確認
## process_on_sdc_insertion()関数
* 以下の処理を実行する（ステータスが```REQUEST_SDC_INSERTION_TASK```時に実行される）
  * SDカード挿入後のSDカード接続初期化```initialize_sdc_on_insertion()```
  * LEDの点滅開始
  * ファイルシステムの利用```tfat_sample()```
  * SDカードの接続終了処理```deinitialize_sdc_on_insertion()```
## initialize_sdc_on_insertion()関数
* 以下の処理を実行する
  * SDHI電源の供給ON```r_sdc_sdmem_demo_power_on()```
  * SDカード初期化```R_SDC_SD_Initialize()```
## tfat_sample()関数
* 以下の処理を実行する
  * ファイルシステムの利用
    * マウント```f_mount()```
    * フォルダ作成```f_mkdir()```
    * ファイルオープン```f_open()```
    * ファイル書き込み```f_write()```
    * ファイルクローズ```f_close()```
## deinitialize_sdc_on_insertion()関数
* 以下の処理を実行する
  * SDカードの接続終了処理```R_SDC_SD_End()```
## process_on_sdc_removal()関数
* 以下の処理を実行する（ステータスが```REQUEST_SDC_REMOVAL_TASK```時に実行される）
  * SDHI電源の供給OFF```r_sdc_sdmem_demo_power_off()```
  * LEDの点滅終了
## r_sdc_sdmem_demo_power_init()、r_sdc_sdmem_demo_power_on()、r_sdc_sdmem_demo_power_off()関数
* 以下の処理を実行する
  * SDHIに電源を供給するための初期化、電源ON、電源OFF処理
    * SDHI電源供給を制御するポートはP42（[SDHI回路図](#circuit_SDHI)）
## blink_LED()関数
* 以下の処理を実行する
  * LEDを点滅
    * LEDを制御するポートはP40（[LED回路図](https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95%28%E3%83%99%E3%82%A2%E3%83%A1%E3%82%BF%E3%83%AB%29)）
***

# 追加情報
## <a name="TFAT_multi_connection"></a>USBメモリ/eMMCカード/Serial Flashメモリを接続したい
* TFATはSDカードだけでなく以下の記憶メディアにも対応している
  * USBメモリ
  * eMMCカード
  * Serial Flashメモリ
* USBメモリを接続するためには以下を変更する
  * :point_right: [補足] デモプロジェクト（ターゲットボードはRenesas Starter Kit+ for RX72M）を以下からダウンロードできる<br>[オープンソースFAT ファイルシステム M3S-TFAT-Tiny モジュールFirmware Integration Technology](https://www.renesas.com/software-tool/fat-file-system-m3s-tfat-tiny-rx-family)
    * TFAT driver FITのコンポーネント設定
      * ```Number of USB drivers```：```1```以上```10```以下（同時接続したいUSBメモリの数）
      * ```Memory Drive x```：```USB```
      * <a href="../../images/075_setting_tfat_driver_usb.png" target="_blank"><img src="../../images/075_setting_tfat_driver_usb.png" width="480px" target="_blank"></a>
    * USB basic FITのコンポーネント設定
      * ```USB operating mode setting```：```USB Host mode```
      * ```Device class setting```：```Host Mass Storage Class```
      * ```USB0_VBUSEN端子```：```使用する```
      * ```USB0_OVRCURA端子```：```使用する```
      * <a href="../../images/076_setting_usb.png" target="_blank"><img src="../../images/076_setting_usb.png" width="480px" target="_blank"></a>
      * <a href="../../images/077_setting_usb2.png" target="_blank"><img src="../../images/077_setting_usb2.png" width="480px" target="_blank"></a>
    * USBの端子設定
      * ```USB0_OVRCURA```：```P14```
      * ```USB0_VBUSEN```：```P16```
      * <a href="../../images/078_setting_pin_usb.png" target="_blank"><img src="../../images/078_setting_pin_usb.png" width="480px" target="_blank"></a>
* eMMCカードを接続するためには以下を変更する
    * TFAT driver FITのコンポーネント設定
      * ```Number of MMC drivers```：```1```以上```10```以下（同時接続したいeMMCカードの数）
      * ```Memory Drive x```：```MMC```
  * (工事中)
* Serial Flashメモリを接続するためには以下を変更する
    * TFAT driver FITのコンポーネント設定
      * ```Number of Serial FLASH drivers```：```1```以上```10```以下（同時接続したいSerial Flashメモリの数）
      * ```Memory Drive x```：```Serial FLASH```
  * (工事中)
* TFATではSDカード、USBメモリ、及び、eMMCカードを1～10個（ソフトウェア仕様）同時接続できる
  * 同時接続するためには以下を変更する
    * TFAT FITの```ffconf.h```
      * ```FF_VOLUMES```：```1```以上```10```以下（同時接続したい数）
    * TFAT driver FITのコンポーネント設定
      * ```Number of xxx drivers```：```1```以上```10```以下（同時接続したい各記憶メディアの数）
      * ```Memory Drive x```：```USB```、```SD momoery card```、```MMC```、```USB mini```、または```Serial FLASH```
        （各ドライブに紐づける記憶メディア）
      * 以下はUSBを2個、SDカードを1個同時接続する時の設定例
        * <a href="../../images/079_setting_tfat_multi.png" target="_blank"><img src="../../images/079_setting_tfat_multi.png" width="480px" target="_blank"></a>
  * 将来的にはSerial Flashメモリも同時接続できる予定

## FATファイルシステムをリアルタイムOS(RTOS)と共に使いたい
* TFATはFreeRTOS及び[RI600V4](https://www.renesas.com/products/software-tools/software-os-middleware-driver/itron-os/ri600v4-for-rx-family.html)(Renesas製RXファミリ用μITRON)に対応している
* FreeRTOS及びRI600V4用のSC対応プロジェクトをe2 studioから簡単に作成することができる
  * プロジェクト生成時にプルダウンメニューから使用したいRTOSを選択する
  * <a href="../../images/080_rtos_selection.png" target="_blank"><img src="../../images/080_rtos_selection.png" width="480px" target="_blank"></a>
    * なお、RI600V4をインストール済みの場合のみRI600V4を選択できる
## FATファイルシステムのLong Filename形式(LFN)を使いたい
* TFATはデフォルトでShort Filename形式(SFN)、8.3形式とも呼ばれる、に設定されている
  * SFN(8.3形式)
    * ドットを除く拡張子以外に最大8バイト、拡張子に最大3バイト
    * 小文字は大文字に置換される
  * LFN
    * FATファイルシステムにおいてファイル名の最大長が250文字（パスの最大長は259文字）
    * 大文字/小文字の区別がある
* LFNを有効にするためには以下のソースコードを変更すればよい
  * TFAT FITの```ffconf.h```
    * ```FF_USE_LFN```：```1```、```2```、```3```のいずれか
    * ```FF_MAX_LFN``` ：```12```~```255```のいずれか（ただし、基本的にはデフォルトの```255```でよい）


## ファイルシステムの日時取得にはCMTではなくRTCを使いたい
* RX72N Envision KitではRTCが実装されていないが参考情報として紹介する
* SCを使用してRTC FITモジュールをプロジェクトに組み込むことで、CMTからRTCに簡単に変更できる
* ソースコードは以下の箇所を変更すればよい（動作未確認）
  * TFAT driver FITの```r_tfat_drv_if.c```の```get_fattime()```関数
    * システムタイマ FITモジュールの代わりにRTC FITモジュールのAPIを使用して日時取得するように変更
  * ```rx72n_envidion_kit.c```の```initialize_sdc_demo()```関数
    * システムタイマ FITモジュールの代わりにRTC FITモジュールの初期化を実施

## ネットワークを介して正確な日時を取得したい
* 正確な日時を取得する方法として、Simple Network Time Protocol(SNTP)が用いられる
* SNTPを用いて[NICT Time Server](https://jjy.nict.go.jp/tsp/PubNtp/index.html)から日時を受信する方法は [AWSプロジェクトのデモ](https://github.com/renesas/rx72n-envision-kit/blob/master/vendors/renesas/boards/rx72n-envision-kit/aws_demos/application_code/renesas_code/sntp_task.c)を参照
  * ```sntp_task.c```の```sntp_task()```

# 将来改善項目
* SDカード検出の関数(R_SDC_SD_GetCardDetection())の実装がユーザ任せになっているため、SDカードドライバ内部で完結したほうがよい
* 上記★にもあるが、CRC演算器を使えばもっと速くなるかもしれない
  * ピンポイントでCRC演算器を使った実装をする前にTracealyzerを利用して実行状態のプロファイルを取り適切に最適化を目指す

# 注意事項
* R_CMT_CreatePeriodic()の第1引数は単位がHzであるが、マイコンにより入力できる値の上限値が異なる
* よって、例えば本ページのサンプルコードをRX65Nに移植する場合は、値を1000000→100000に変更して分解能を1usから10usとした上で各種処理を調整するとよい