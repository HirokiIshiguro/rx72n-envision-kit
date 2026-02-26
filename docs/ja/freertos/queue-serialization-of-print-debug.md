# 準備する物
* 必須
    * RX72N Envision Kit × 1台
    * USBケーブル(USB Micro-B --- USB Type A) × 2 本
    * Windows PC × 1 台
        * Windows PC にインストールするツール
            * [e2 studio 2020-07](https://www.renesas.com/products/software-tools/tools/ide/e2studio.html)
            * [CC-RX](https://www.renesas.com/products/software-tools/tools/compiler-assembler/compiler-package-for-rx-family.html) V3.02以降
            * [Tera Term](https://osdn.net/projects/ttssh2/) 4.105以降
                * [シリアル接続における高速なファイル転送](https://teratermproject.github.io/manual/5/ja/setup/teraterm-trans.html#FileSendHighSpeedMode) の FileSendHighSpeedMode を OFF にする
                    * Tera Term -> 設定 -> 設定の読み込み -> TERATERM.INI を テキストエディタで開く -> 設定を変更 -> 保存 -> Tera Term再起動

# 前提条件
* [新規プロジェクト作成方法(FreeRTOS)](../freertos/generate-new-project-kernel-only.md) を完了すること
    * 本稿では、[新規プロジェクト作成方法(FreeRTOS)](../freertos/generate-new-project-kernel-only.md)で作成したLED0.1秒周期点滅プログラムにSCI(Serial Communication Interface)のUARTモードを用いてPCと通信するためのコードを追加する形で実装する

# シリアライズとは
* シリアル(連続的)に要求を並べること
* その実装体として適切なデータ構造は キュー(queue) である
* ハードウェアが1個であるのに対し、そのハードウェアを使用するタスクが複数存在する場合に有効な手法
* 代表例として、printデバッグのシリアライズを説明する
    * 複数タスクからの文字列送信要求を キュー(queue) で受け、SCIの送信関数に流し込む
    * SCIの送信関数はノンブロッキングコールであるため関数終了時に処理自体は完了していない
    * 処理完了はコールバック関数で通知される形式である
    * SCIの送信関数終了後にセマフォ(semaphore)を取り(take)待ち状態とする
    * SCIの送信完了通知のコールバック時にセマフォ(semaphore)を与え(give)待ち状態を解除する

# 回路確認
* [参考](https://github.com/renesas/rx72n-envision-kit/wiki/1-SCI#%E5%9B%9E%E8%B7%AF%E7%A2%BA%E8%AA%8D)

# スマートコンフィグレータによるSCI用ドライバソフトウェアの設定
## コンポーネント追加
* [参考](https://github.com/renesas/rx72n-envision-kit/wiki/1-SCI#%E3%82%B3%E3%83%B3%E3%83%9D%E3%83%BC%E3%83%8D%E3%83%B3%E3%83%88%E8%BF%BD%E5%8A%A0)
## コンポーネント設定
* r_sci_rx
    * [参考](https://github.com/renesas/rx72n-envision-kit/wiki/1-SCI#r_sci_rx)
    * 上記参考に含まれていない設定として、「送信完了時に割り込みを発生させる設定」を有効にする
        * <a href="../../images/062_e2_studio_sc.png" target="_blank"><img src="../../images/062_e2_studio_sc.png" width="480px" target="_blank"></a>
* FreeRTOS_Object
    * タスク登録
        * <a href="../../images/059_e2_studio_sc.png" target="_blank"><img src="../../images/059_e2_studio_sc.png" width="480px" target="_blank"></a>
        * FreeRTOS_Object -> Taskを選択
        * Task CodeとTask Nameに task_2, task_3, print_task と入力
    * セマフォ登録
        * <a href="../../images/060_e2_studio_sc.png" target="_blank"><img src="../../images/060_e2_studio_sc.png" width="480px" target="_blank"></a>
        * FreeRTOS_Object -> Semaphores を選択
        * Semaphore Type に binaryを選択
    * キュー登録
        * <a href="../../images/061_e2_studio_sc.png" target="_blank"><img src="../../images/061_e2_studio_sc.png" width="480px" target="_blank"></a>
        * FreeRTOS_Object -> Queues を選択
        * Queue Length に 16 を入力
        * Item Size に 256 を入力
            * 256文字のデータを16個まで行列を作ることができる、という設定
# 端子設定
* [参考](https://github.com/renesas/rx72n-envision-kit/wiki/1-SCI#%E7%AB%AF%E5%AD%90%E8%A8%AD%E5%AE%9A)

# print_task.c のコーディング
```print_task.c
#include "task_function.h"
/* Start user code for import. Do not edit comment generated here */
#include "r_sci_rx_if.h"
#include "r_sci_rx_pinset.h"
#include "platform.h"
#include <string.h>

void sci_callback(void *arg);

static sci_hdl_t sci_handle;
static signed portBASE_TYPE xHigherPriorityTaskWoken;

extern QueueHandle_t queue_handle_1;
extern SemaphoreHandle_t semaphore_handle_1;

/* End user code. Do not edit comment generated here */

void print_task(void * pvParameters)
{
/* Start user code for function. Do not edit comment generated here */
	sci_cfg_t   my_sci_config;
	static char string[256];

    /* Set up the configuration data structure for asynchronous (UART) operation. */
    my_sci_config.async.baud_rate    = 115200;
    my_sci_config.async.clk_src      = SCI_CLK_INT;
    my_sci_config.async.data_size    = SCI_DATA_8BIT;
    my_sci_config.async.parity_en    = SCI_PARITY_OFF;
    my_sci_config.async.parity_type  = SCI_EVEN_PARITY;
    my_sci_config.async.stop_bits    = SCI_STOPBITS_1;
    my_sci_config.async.int_priority = 15; /* disable 0 - low 1 - 15 high */

    R_SCI_Open(SCI_CH2, SCI_MODE_ASYNC, &my_sci_config, sci_callback, &sci_handle);
    R_SCI_PinSet_SCI2();

    while(1)
    {
    	xQueueReceive(queue_handle_1, string, portMAX_DELAY);
    	R_SCI_Send(sci_handle, (uint8_t *)string, strlen(string));
    	xSemaphoreTake( semaphore_handle_1, portMAX_DELAY );
    }
/* End user code. Do not edit comment generated here */
}
/* Start user code for other. Do not edit comment generated here */
void sci_callback(void *arg)
{
	xHigherPriorityTaskWoken = pdFALSE;
	xSemaphoreGiveFromISR(semaphore_handle_1, &xHigherPriorityTaskWoken);
	portYIELD_FROM_ISR( xHigherPriorityTaskWoken );
}

/* End user code. Do not edit comment generated here */
```

# task_2.c のコーディング
```task_2.c
#include "task_function.h"
/* Start user code for import. Do not edit comment generated here */
#include "platform.h"

extern QueueHandle_t queue_handle_1;
/* End user code. Do not edit comment generated here */

void task_2(void * pvParameters)
{
/* Start user code for function. Do not edit comment generated here */
	char string[256];
	while(1)
	{
		vTaskDelay(1000);
		sprintf(string, "task_2: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n");
		xQueueSend(queue_handle_1, string, portMAX_DELAY);
	}
/* End user code. Do not edit comment generated here */
}
/* Start user code for other. Do not edit comment generated here */
/* End user code. Do not edit comment generated here */
```

# task_3.c のコーディング
```task_3.c
#include "task_function.h"
/* Start user code for import. Do not edit comment generated here */
#include "platform.h"

extern QueueHandle_t queue_handle_1;
/* End user code. Do not edit comment generated here */

void task_3(void * pvParameters)
{
/* Start user code for function. Do not edit comment generated here */
	char string[256];
	while(1)
	{
		vTaskDelay(1000);
		sprintf(string, "task_3: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n");
		xQueueSend(queue_handle_1, string, portMAX_DELAY);
	}
/* End user code. Do not edit comment generated here */
}
/* Start user code for other. Do not edit comment generated here */
/* End user code. Do not edit comment generated here */
```
# ヒープ容量を調整する
* [参考](https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95%28FreeRTOS%29#%E3%83%92%E3%83%BC%E3%83%97%E5%AE%B9%E9%87%8F%E3%82%92%E8%AA%BF%E6%95%B4%E3%81%99%E3%82%8B)

# 動作確認
* Windows PC上でTeratermを立ち上げ、COMポート(COMx: RSK USB Serial Port(COMx))を選択し接続
    * 設定 -> シリアルポート で以下設定を行う
        * ボーレート: 115200 bps
        * データ: 8 bit
        * パリティ: none
        * ストップ: 1 bit
        * フロー制御: none
    * 設定 -> 端末 で以下設定を行う
        * 改行コード
            * 受信: AUTO
            * 送信: CR+LF
        * ローカルエコー
            * チェックを外す
* 実行：[参考](https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95%28%E3%83%99%E3%82%A2%E3%83%A1%E3%82%BF%E3%83%AB%29#%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D)
* 1秒おきに、以下のようなログが出力されることを確認
```
task_2: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
task_3: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
task_2: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
task_3: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
task_2: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
task_3: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```
* task_2 および、task_3 からのprint出力が衝突せずに出力されていることを確認
* 仮に task_2 および、task_3 からxQueueSend()を使用せずに直接R_SCI_Send()を呼び出したとすると、task_2の送信中にtask_3の送信が混じり、上記のように衝突せず出力することができない