# 準備する物
* 必須
    * RX72N Envision Kit × 1台
    * USBケーブル(USB Micro-B --- USB Type A) × 2 本
    * [USB-シリアル変換 PMODモジュール](https://store.digilentinc.com/pmod-usbuart-usb-to-uart-interface/) × 1 台
    * Windows PC × 1 台
        * Windows PC にインストールするツール
            * [e2 studio 2022-10](https://www.renesas.com/products/software-tools/tools/ide/e2studio.html)
            * [CC-RX](https://www.renesas.com/products/software-tools/tools/compiler-assembler/compiler-package-for-rx-family.html) V3.04以降
            * [Tracealyzer v4.6.6](https://percepio.com/tracealyzer/)
* ![image](https://user-images.githubusercontent.com/37968119/204113795-2aa37adf-519e-458f-8ac3-9853ab41afb2.png)

# 前提条件
* [Tracealyzer使用方法](../../features/how-to-use-tracealyzer.md) を完了すること
* [新規プロジェクト作成方法(FreeRTOS)](../../freertos/generate-new-project-kernel-only.md) を完了すること
    * 本稿では、[新規プロジェクト作成方法(FreeRTOS)](../../freertos/generate-new-project-kernel-only.md)で作成したLED0.1秒周期点滅プログラムに[Tracealyzer Recorder](https://github.com/percepio/TraceRecorderSource)を実装し[Tracealyzer](https://percepio.com/tracealyzer/)によるFreeRTOS内部動作状態のモニタを実現する
    * なお、本稿の内容はRX72N Envision Kitを題材に解説しているが、RXファミリ全般で応用可能であり、モニタデータを出力する機能の端子設定等のボード依存の設定を[スマートコンフィグレータで設定変更](https://github.com/renesas/rx72n-envision-kit/wiki/%E3%82%B9%E3%83%9E%E3%83%BC%E3%83%88%E3%83%BB%E3%82%B3%E3%83%B3%E3%83%95%E3%82%A3%E3%82%B0%E3%83%AC%E3%83%BC%E3%82%BF%E3%81%AE%E4%BD%BF%E7%94%A8%E6%96%B9%E6%B3%95)することで、任意のRXファミリのボードを題材とした解説としても利用可能である
    * 単にFreeRTOSやRXファミリの技術習得が目的の場合、RX72N Envision Kitより廉価に購入でき、かつ、マイコン機能を任意にボード外部に接続しやすい [RX-Family-Target-Board](https://www.renesas.com/products/microcontrollers-microprocessors/rx-32-bit-performance-efficiency-mcus/rx-family-target-board-target-board-rx-family) シリーズを推奨する

# 前提知識
* [Tracealyzer使用方法](../../features/how-to-use-tracealyzer.md)の[動作解説](https://github.com/renesas/rx72n-envision-kit/wiki/Tracealyzer%E4%BD%BF%E7%94%A8%E6%96%B9%E6%B3%95#%E5%8B%95%E4%BD%9C%E8%A7%A3%E8%AA%AC)で解説している内容を理解すること
* Tracealyzer for FreeRTOSのTracealyzer Recorder部分の詳細な解説は以下ページが参考になる
  * https://percepio.com/docs/FreeRTOS/manual%20old/Recorder.html
* いくつかのデータ取得方法があるが、本稿ではデバッグで最も強力なリアルタイムでFreeRTOS内部状態をモニタ出来る[Streaming mode](https://percepio.com/docs/FreeRTOS/manual%20old/Recorder.html#Trace_Recorder_Library_Streaming_Mode) を実装する
* モニタデータは 20-200 KB/s (160 - 1600 Kbps) のレートで生成されると記載がある
  * 実際にいくつかのケースでどのくらいのレートが必要になるかを例示する
    * [RX72N@240MHzでFreeRTOSで0.1秒周期でLEDを点滅させるプログラム](https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95%28FreeRTOS%29)を実行した場合: 28.9 KB/s = 231.2 Kbps
      * ![image](https://user-images.githubusercontent.com/37968119/204113698-6731326c-ef8b-4882-b25c-cb0c379f078c.png)
    * [RX72N@240MHzでFreeRTOSで20個程度のタスクを並列で実行し画面表示機能を含むIoT装置的なシステムを実現するプログラム](https://github.com/renesas/rx72n-envision-kit/releases/tag/v2.0.0) : 224.8 KB/s = 1798.4 Kbps
      * ![image](https://user-images.githubusercontent.com/37968119/204113298-c194cbe9-4599-4c30-ba1f-fb90ec2b0d05.png)
* 本稿で利用するモニタ用の通信路はUART(900 Kbps設定)なので、上記のうちこの数値を超える例の場合はモニタデータを出力しきれない
  * この場合、Tracealyzer画面上では `missed event` が検出され、モニタデータが欠落した状態となり、モニタ結果の正確さが損なわれる
  * よって、`missed event` が検出された際には、通信速度に余裕がある通信路に変更することを推奨する
    * ネットワークスタックと高速な通信路(例えばEthernet)を利用するシステムの場合(例: [新規プロジェクト作成方法(FreeRTOS(with IoT Libraries))](../../freertos/generate-new-project-with-iot-libraries.md)) はこの問題が解消される
      * このケースの場合、ネットワークスタックと高速な通信路(例えばEthernet)を利用した[複雑なシステムのTracealyzer Recorder実装方法](../../freertos/how-to-implement-tracealyzer-recorder-complex.md) 参照
* なお、RX72N Envision Kitに標準で搭載されるUSBシリアル変換チップはボーレート上限が 115200 bps であり、モニタデータの最小レートである20 KB/s (160 Kbps)を満たすことができないため、使えない
  * よって、高速な [USB-シリアル変換 PMODモジュール](https://store.digilentinc.com/pmod-usbuart-usb-to-uart-interface/) をボード上のPMODコネクタに増設して利用することとする

# プロジェクトを新規作成する
* [新規プロジェクト作成方法(FreeRTOS)](../../freertos/generate-new-project-kernel-only.md) を参考に e2 studio で新規プロジェクトを作成する
* 利用するFreeRTOSのバージョンは 10.4.3-rx-1.0.6 とする
  * ![image](https://user-images.githubusercontent.com/37968119/204114662-97e96be9-4e84-4a8a-abbf-0b900390b67a.png)
* [新規プロジェクト作成方法(FreeRTOS)](../../freertos/generate-new-project-kernel-only.md) の記事を作成した当時と比較し、ボードに依存する設定項目の多くが自動化されたため、[クロック設定](https://github.com/renesas/rx72n-envision-kit/wiki/%E3%82%B9%E3%83%9E%E3%83%BC%E3%83%88%E3%83%BB%E3%82%B3%E3%83%B3%E3%83%95%E3%82%A3%E3%82%B0%E3%83%AC%E3%83%BC%E3%82%BF%E3%81%AE%E4%BD%BF%E7%94%A8%E6%96%B9%E6%B3%95#%E3%82%AF%E3%83%AD%E3%83%83%E3%82%AF%E8%A8%AD%E5%AE%9A) は不要になった
  * が、システム開発上、クロック設定値によりCPUクロック(ICLK)や周辺クロック(PCLK)が何MHzで動作しているのか、また、クロック源が何MHzでPLL(逓倍回路)の設定で何逓倍されていて、どのような分配器を経て各機能のクロックソースとなっているかなどを理解するためには、マイコンのハードウェアマニュアルを参照し、[クロック設定](https://github.com/renesas/rx72n-envision-kit/wiki/%E3%82%B9%E3%83%9E%E3%83%BC%E3%83%88%E3%83%BB%E3%82%B3%E3%83%B3%E3%83%95%E3%82%A3%E3%82%B0%E3%83%AC%E3%83%BC%E3%82%BF%E3%81%AE%E4%BD%BF%E7%94%A8%E6%96%B9%E6%B3%95#%E3%82%AF%E3%83%AD%E3%83%83%E3%82%AF%E8%A8%AD%E5%AE%9A)の項目及び出力コードを改めて確認することを推奨する
* また、[新規プロジェクト作成方法(FreeRTOS)](../../freertos/generate-new-project-kernel-only.md) ではヒープサイズを 8KB で設定しているが、Tracealyzerの利用時は 128KB 以上を推奨する (32KBでもモニタ可能であることは確認済)
  * モニタするFreeRTOSのリソース(タスクやセマフォなど)の量やシステムコールを呼び出す頻度に依存して必要になるバッファ量を柔軟に調整するため、多めのサイズ設定としている
  * 必要に応じてヒープサイズは調整すること
    * ![image](https://user-images.githubusercontent.com/37968119/204114762-34e53536-c108-419a-83e9-6ff5e60aeaa2.png)

# デバッガ設定と動作確認
* [新規プロジェクト作成方法(FreeRTOS)](../../freertos/generate-new-project-kernel-only.md)の[デバッガ設定](https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95%28FreeRTOS%29#%E3%83%87%E3%83%90%E3%83%83%E3%82%AC%E8%A8%AD%E5%AE%9A)と[動作確認](https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95%28FreeRTOS%29#%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D)の項目を実行
  * なお、[デバッガ設定](https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95%28FreeRTOS%29#%E3%83%87%E3%83%90%E3%83%83%E3%82%AC%E8%A8%AD%E5%AE%9A)の項目において、デバッガの設定項目の多く(メイン・クロック・ソース -> EXTAL に変更等)は、最新のe2 studio 2022-10 では自動化されており不要
* 実機上の青色LEDが点滅することを確認する

# Tracealyzer Recorder を e2 studio のプロジェクトに登録する
* 大まかなメカニズム、データフローを理解する
  * https://percepio.com/tracealyzer/freertostrace/gettingstarted-freertos/
* TracealyzerのヘルプからTraceRecorderフォルダを開く
  * ![image](https://user-images.githubusercontent.com/37968119/204116983-fac0b180-8d0b-4595-b24b-02016d4b39e7.png)
    * e2 studio のプロジェクトエクスプローラ上で「src」フォルダを右クリックし、「system explorer」を選択
      * ![image](https://user-images.githubusercontent.com/37968119/204117100-49526c08-f2b7-4fe2-acf7-d8d6d6b9aaa8.png)
        * Tracealyzerのヘルプから開いたTraceRecorderフォルダをすべて「src」フォルダにコピーする
          * 補足:
            * TraceRecoderフォルダは以下Percepio社のGitHubで同一のものが公開されている
              * [Tracealyzer Recorder](https://github.com/percepio/TraceRecorderSource)
    * TraceRecorderフォルダは以下のようにプロジェクト登録される
      * エクスプローラ上でstreamports 以下はすべて消しておき、代わりに「Renesas_RX_UART」フォルダとその内部にconfigフォルダ、includeフォルダを作って、「trcStreamPort.c」「trcStreamPort.h」「trcStreamPortConfig.h」「Readme-Streamport.txt」をそれぞれ空のファイルを作って置いておく
        * ![image](https://user-images.githubusercontent.com/37968119/204117072-9a27f3ae-24c5-47f1-9f37-815add42f09b.png)
* trcStreamPort.c に以下をコピーペーストする

```c
#include <string.h>

#include "trcRecorder.h"
#include "r_sci_rx_if.h"
#include "r_sci_rx_pinset.h"

#if (TRC_CFG_RECORDER_MODE == TRC_RECORDER_MODE_STREAMING)
#if (TRC_USE_TRACEALYZER_RECORDER == 1)

static uint8_t string[1024];
static uint8_t sci_buffer[1024];
static uint32_t sci_current_received_size = 0;
static volatile uint32_t wait_sending = 0;

extern sci_hdl_t sci_handle_tracealyzer;

void sci_callback_tracealyzer(void *arg);

traceResult xTraceStreamPortInitialize(TraceStreamPortBuffer_t* pxBuffer)
{
	TRC_ASSERT_EQUAL_SIZE(TraceStreamPortBuffer_t, TraceStreamPortUSBBuffers_t);

	if (pxBuffer == 0)
	{
		return TRC_FAIL;
	}

	return xTraceInternalEventBufferInitialize(pxBuffer->buffer, sizeof(pxBuffer->buffer));
}

traceResult prvTraceUARTTransmit(void* pvData, uint32_t uiSize, int32_t* piBytesSent)
{
	int32_t error_code = -1;

	while(1)
	{
		if(wait_sending)
		{
			xTraceKernelPortDelay(1);
		}
		else
		{
			break;
		}
	}

	if(uiSize < sizeof(string))
	{
		memcpy(string, pvData, uiSize);
		if(SCI_SUCCESS == R_SCI_Send(sci_handle_tracealyzer, string, uiSize))
		{
			wait_sending = 1;
			*piBytesSent = uiSize;
			error_code = 0;
		}
	}
	return error_code;
}

traceResult prvTraceUARTReceive(void* data, uint32_t uiSize, int32_t* piBytesReceived)
{
	if(sci_current_received_size == uiSize)
	{
		memcpy(data, sci_buffer, sci_current_received_size);
		*piBytesReceived = sci_current_received_size;
		sci_current_received_size = 0;
	}
	return 0;
}

void sci_callback_tracealyzer(void *arg)
{
	sci_cb_args_t   *p_args;
	p_args = (sci_cb_args_t *)arg;

	if (SCI_EVT_RX_CHAR == p_args->event)
	{
		R_SCI_Receive(p_args->hdl, &sci_buffer[sci_current_received_size], 1);
		if(sci_current_received_size == (sizeof(sci_buffer) - 1)) /* -1 means string terminator after "\n" */
		{
			sci_current_received_size = 0;
		}
		else
		{
			sci_current_received_size++;
		}
	}
	else if(SCI_EVT_TEI == p_args->event)
	{
		wait_sending = 0;
	}
}
```

* trcStreamPortConfig.h に以下をコピーペーストする

```c
#ifndef TRC_STREAM_PORT_CONFIG_H
#define TRC_STREAM_PORT_CONFIG_H

#ifdef __cplusplus
extern "C" {
#endif

/*******************************************************************************
* Configuration Macro: TRC_CFG_STREAM_PORT_INTERNAL_BUFFER_SIZE
*
* Specifies the size of the internal buffer.
******************************************************************************/
#define TRC_CFG_STREAM_PORT_INTERNAL_BUFFER_SIZE 1024

#ifdef __cplusplus
}
#endif

#endif /* TRC_STREAM_PORT_CONFIG_H */
```

* trcStreamPort.h に以下をコピーペーストする

```c
#ifndef TRC_STREAM_PORT_H
#define TRC_STREAM_PORT_H

#include <trcTypes.h>
#include <trcStreamPortConfig.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct TraceStreamPortBuffer
{
	uint8_t buffer[(TRC_CFG_STREAM_PORT_INTERNAL_BUFFER_SIZE) + sizeof(TraceUnsignedBaseType_t)];
} TraceStreamPortBuffer_t;

traceResult prvTraceUARTReceive(void* data, uint32_t uiSize, int32_t* piBytesReceived);

traceResult prvTraceUARTTransmit(void* pvData, uint32_t uiSize, int32_t* piBytesSent);

/**
 * @internal Stream port initialize callback.
 *
 * This function is called by the recorder as part of its initialization phase.
 *
 * @param[in] pxBuffer Buffer
 *
 * @retval TRC_FAIL Initialization failed
 * @retval TRC_SUCCESS Success
 */
traceResult xTraceStreamPortInitialize(TraceStreamPortBuffer_t* pxBuffer);

/**
 * @brief Allocates data from the stream port.
 *
 * @param[in] uiSize Allocation size
 * @param[out] ppvData Allocation data pointer
 *
 * @retval TRC_FAIL Allocate failed
 * @retval TRC_SUCCESS Success
 */
#define xTraceStreamPortAllocate(uiSize, ppvData) ((void)uiSize, xTraceStaticBufferGet(ppvData))

/**
 * @brief Commits data to the stream port, depending on the implementation/configuration of the
 * stream port this data might be directly written to the stream port interface, buffered, or
 * something else.
 *
 * @param[in] pvData Data to commit
 * @param[in] uiSize Data to commit size
 * @param[out] piBytesCommitted Bytes committed
 *
 * @retval TRC_FAIL Commit failed
 * @retval TRC_SUCCESS Success
 */
#define xTraceStreamPortCommit xTraceInternalEventBufferPush

/**
 * @brief Writes data through the stream port interface.
 *
 * @param[in] pvData Data to write
 * @param[in] uiSize Data to write size
 * @param[out] piBytesWritten Bytes written
 *
 * @retval TRC_FAIL Write failed
 * @retval TRC_SUCCESS Success
 */
#define xTraceStreamPortWriteData prvTraceUARTTransmit

/**
 * @brief Reads data through the stream port interface.
 *
 * @param[in] pvData Destination data buffer
 * @param[in] uiSize Destination data buffer size
 * @param[out] piBytesRead Bytes read
 *
 * @retval TRC_FAIL Read failed
 * @retval TRC_SUCCESS Success
 */
#define xTraceStreamPortReadData prvTraceUARTReceive

#define xTraceStreamPortOnEnable(uiStartOption) ((void)(uiStartOption), TRC_SUCCESS)

#define xTraceStreamPortOnDisable() (TRC_SUCCESS)

#define xTraceStreamPortOnTraceBegin() (TRC_SUCCESS)

#define xTraceStreamPortOnTraceEnd() (TRC_SUCCESS)

#ifdef __cplusplus
}
#endif

#endif /* TRC_STREAM_PORT_H */
```

* Readme-Streamport.txt は空のままでよい
* FreeRTOSConfig.h の一番下に#include "trcRecorder.h" を追加
  * ![image](https://user-images.githubusercontent.com/37968119/204117285-b0caff92-ec22-439a-97f1-9d00a94219b4.png)
* trcConfig.h を以下のように変更する
  * #error ... の行をコメントアウト
  * TRC_CFG_HARDWARE_PORT に TRC_HARDWARE_PORT_Renesas_RX600 を指定
    * ![image](https://user-images.githubusercontent.com/37968119/204117311-d42a8320-58a3-4d75-a8fb-15b08eb01cd7.png)
* trcKernelPortConfig.h を以下のように変更する
  * TRC_CFG_RECORDER_MODEに TRC_RECORDER_MODE_STREAMING を指定
  * TRC_CFG_FREERTOS_VERSION に TRC_FREERTOS_VERSION_10_4_1を指定 ⇒使用するFreeRTOSのバージョンに拠るので自分が使っているFreeRTOSのバージョンを確認し一致させること
    * ![image](https://user-images.githubusercontent.com/37968119/204117327-7b20063f-0452-46e4-a527-dd51fbf7ff9c.png)
* Tracealyzerのモニタデータ出力用のUARTの設定を行う
  * スマートコンフィグレータでSCIのFITモジュールを追加/設定
    * ![image](https://user-images.githubusercontent.com/37968119/204117372-89293061-0fef-4cc0-a8e5-0521fc5f007a.png)
      * フィルタに「sci」を入力してもSCIのFITモジュールが表示されない場合は、「最新版のFITドライバとミドルウェアをダウンロードする」を選択する
    * コンポーネントタブでSCIチャネル7を設定する
      * RX72N Envision Kit のPMODのCN6を使用する
        * ![image](https://user-images.githubusercontent.com/37968119/204117405-af5f7557-34f7-46c9-8548-e105a04dec7b.png)
      * チャネル7の送信バッファの容量を80バイトから1024バイトに増やす
        * ![image](https://user-images.githubusercontent.com/37968119/204117426-f871017b-585f-4665-9cbe-b5ef220786d9.png)
      * チャネル7の送信バッファ空割り込みを使用する設定に変更する
        * ![image](https://user-images.githubusercontent.com/37968119/204117437-3156b68c-d469-44ef-9e81-efdd10eecc6a.png)
      * チャネル7をフロー制御無しUARTで利用するので、フロー制御用端子(RTS/CTS)を無効化し、送受信用端子(TxD/RxD)のみ有効にしておく
        * ![image](https://user-images.githubusercontent.com/37968119/204117461-13dfa74a-280c-4d6f-9651-19324ce978f7.png)
   * 端子タブでSCIチャネル7を設定する
     * ![image](https://user-images.githubusercontent.com/37968119/204117541-290abb56-4ff8-49cb-9bd5-9803eea3fc31.png)
* コンパイラ設定でTracealyzerに必要なインクルードパスを追加する
  * プロジェクトエクスプローラでプロジェクト名「rx72n_envision_kit」を右クリックし、プロパティを選択
    * ![image](https://user-images.githubusercontent.com/37968119/204117594-95fba065-a556-4cff-b8d8-f49296a3cb6e.png)
      * C/C++ビルド -> 設定 -> ツール設定 -> Compiler -> ソース -> 追加 ボタンを押す
        * ![image](https://user-images.githubusercontent.com/37968119/204117611-abdafb3c-7898-47e7-a5c7-90f4decc13c2.png)
          * 以下5種類のパスを追加
            * `"${workspace_loc:/${ProjName}/src/smc_gen/r_bsp/mcu/rx72n/register_access/ccrx}"`
            * `"${workspace_loc:/${ProjName}/src/TraceRecorder/config}"`
            * `"${workspace_loc:/${ProjName}/src/TraceRecorder/include}"`
            * `"${workspace_loc:/${ProjName}/src/TraceRecorder/streamports/Renesas_RX_UART/config}"`
            * `"${workspace_loc:/${ProjName}/src/TraceRecorder/streamports/Renesas_RX_UART/include}"`
          * 注意
            * `"${workspace_loc:/${ProjName}/src/smc_gen/r_bsp/mcu/rx72n/register_access/ccrx}"` は、スマートコンフィグレータによりコード生成が実行される度に削除されるため、都度復旧させる必要がある
              * これはTracealyzerが旧来のレジスタアクセスファイル iodefine.h を参照しているためであり、プラットフォーム化された後([FIT](https://www.renesas.com/software-tool/fit)が適用されたRXv2世代以降)の platform.h を参照していないためである
              * Tracealyzerを開発するPercepio社と協議し、プラットフォーム化された後の環境においては、 iodefine.h を読み込まないように大元のファイルを改良していただくよう交渉予定
* FreeRTOS-Kernel の portmacro.h の実装がTracealyzerの呼び出しに対し不完全なため、修正する
  * ![image](https://user-images.githubusercontent.com/37968119/204117844-48e52155-5b85-4a5a-8868-1156e10651fb.png)
    * こちらは、AWS社管轄の[FreeRTOS-Kernelリポジトリ](https://github.com/FreeRTOS/FreeRTOS-Kernel)にAWS社と協議の後、プルリクエストを実施する予定

```c
    /* As this port allows interrupt nesting... */
        static int32_t set_interrupt_mask_from_isr( void );
        static int32_t set_interrupt_mask_from_isr( void )
        {
        	int32_t tmp = __get_ipl();
        	__set_ipl( ( long ) configMAX_SYSCALL_INTERRUPT_PRIORITY );
        	return tmp;
        }
        #define portSET_INTERRUPT_MASK_FROM_ISR()                              set_interrupt_mask_from_isr()
        #define portCLEAR_INTERRUPT_MASK_FROM_ISR( uxSavedInterruptStatus )    set_ipl( ( long ) uxSavedInterruptStatus )
```

* FreeRTOSカーネル起動前のフック関数(freertos_start.cのProcessing_Before_Start_Kernel())にTracealyzerおよびSCIの初期化コードを仕込む
  * ![image](https://user-images.githubusercontent.com/37968119/204117938-364a4079-33eb-43e4-b058-e2101f0748c1.png)

```c
#include "r_sci_rx_if.h"
#include "r_sci_rx_pinset.h"

static sci_cfg_t my_sci_config;
sci_hdl_t sci_handle_tracealyzer;

extern void sci_callback_tracealyzer(void *arg);

void Processing_Before_Start_Kernel(void)
{
    BaseType_t ret;

    /* Create all other application tasks here */
    /* Set up the configuration data structure for asynchronous (UART) operation. */
    my_sci_config.async.baud_rate    = 921600;
    my_sci_config.async.clk_src      = SCI_CLK_INT;
    my_sci_config.async.data_size    = SCI_DATA_8BIT;
    my_sci_config.async.parity_en    = SCI_PARITY_OFF;
    my_sci_config.async.parity_type  = SCI_EVEN_PARITY;
    my_sci_config.async.stop_bits    = SCI_STOPBITS_1;
    my_sci_config.async.int_priority = 15; /* disable 0 - low 1 - 15 high */

    R_SCI_Open(SCI_CH7, SCI_MODE_ASYNC, &my_sci_config, sci_callback_tracealyzer, &sci_handle_tracealyzer);
    R_SCI_PinSet_SCI7();

    xTraceInitialize();
```

* mainタスク(rx72n_envision_kit.c)でTracealyzerの動作開始のコードを仕込む
  * ![image](https://user-images.githubusercontent.com/37968119/204118013-21ec3072-c4c4-419c-a9b2-f70edfc3b7c1.png)

```c
void main_task(void *pvParameters)
{
	xTraceEnable(TRC_START);
	/* Create all other application tasks here */
	while(1)
	{
		vTaskDelay(10);
	}
	vTaskDelete(NULL);
}
```

# Tracealyzer を起動し設定する
* Recording Settings を選択
  * ![image](https://user-images.githubusercontent.com/37968119/204118145-0fc12144-30a5-466c-8a63-5d4cbd0fa81e.png)
    * 以下のように設定する
      * ![image](https://user-images.githubusercontent.com/37968119/204118168-45eaca8f-9207-41d0-af5b-fcffe5fb3334.png)
        * COMポートの番号は、RX72N Envision KitのPMODに接続されたUSBシリアル変換チップと対応するものを設定する
* Record Streaming Trace を選択
  * ![image](https://user-images.githubusercontent.com/37968119/204118191-e5ac33da-b677-4d62-815d-5f47317d74e8.png)
    * Reconnect -> Start Session を選択し、Tracealyzer側を待ち状態にしておく
      * ![image](https://user-images.githubusercontent.com/37968119/204118232-f475fbab-15ab-4704-8273-082f6647241d.png)

# e2 studio でマイコンボード側のソフトウェアを動作状態にする
* [動作確認](https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95(%E3%83%99%E3%82%A2%E3%83%A1%E3%82%BF%E3%83%AB)#%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D)を参考に、ソフトウェアを動作状態にする
* RX72N Envision KitとPC(Tracealyzer)の通信が始まり、FreeRTOSの内部状態がTracealyzer上で可視化される
  * ![image](https://user-images.githubusercontent.com/37968119/204118353-e46cda67-05b0-4446-bb90-49bccf9261b2.png)
* たとえば、以下ウィンドウではタスクスイッチおよびシステムコールの発行状況を完全にモニタすることができている
  * ![image](https://user-images.githubusercontent.com/37968119/204118401-00301ac2-42cc-4dee-906c-29c0ac6e4b49.png)
    * 今回作成したシステムでは、led_taskが100msに1回、MAIN_TASKが10msに1回、TzCtrl(Tracealyzer用タスク)が2msに1回起動し、上記はこの3タスクが同時に起動されるタイミングをモニタしたものである
    * 優先度はMAIN_TASK(3) > led_task(1) == TzCtrl(1) となっており、システム起動時にled_taskの方が早く生成されたため、この順番の通りタスクスイッチしていることが分かる
    * なお、同一優先度のタスクがtimetick(通常1ms)の時間より処理が長引く場合、かつ、FreeRTOSConfig.h の `configUSE_PREEMPTION` がONの場合、timetick毎に同一優先度内で実行されるタスクが順繰りに切り替わる、いわゆる「ラウンドロビン」方式での実行となる

# 最後に
* 先述の通り、本稿での解説はSCIを1チャネルTracealyzerの為に占有してしまっている
* これは実システムで利用できるSCIチャネルが1チャネル減ってしまうことを意味するため、物理1チャネルに論理複数チャネルを重畳できるEthernet等をTracealyzer通信に利用することを推奨する
  * また、UARTの特性上1Mbps程度が通信速度の限界であるため、10タスク程度のモニタで限界となる可能性が高い
  * 複雑なシステムをモニタする場合もEthernet等をTracealyzer通信に利用することを推奨する
* EthernetをTracealyzer通信に用いる方法は [複雑なシステムのTracealyzer Recorder実装方法](../../freertos/how-to-implement-tracealyzer-recorder-complex.md) に記載するものとする <工事中>
* また、RAファミリの場合は、SeggerのJlinkのRTT機能を活用したTracealyzerモニタ方法が、以下アプリケーションノートにより解説されている(RXファミリでも適宜情報追加を行っていく)
  * https://www.renesas.com/document/apn/renesas-ra-family-tracealyzer-freertos-debugging-application-note
