# 準備する物
* 必須
    * RX72N Envision Kit × 1台
    * USBケーブル(USB Micro-B --- USB Type A) × 2 本
    * LANケーブル x 2 本
    * インターネット接続可能なルータ(Ethernet接続対応品) x 1台
    * Windows PC × 1 台
        * Windows PC にインストールするツール
            * [e2 studio 2020-07](https://www.renesas.com/products/software-tools/tools/ide/e2studio.html)
            * [CC-RX](https://www.renesas.com/products/software-tools/tools/compiler-assembler/compiler-package-for-rx-family.html) V3.02以降
            * [Tera Term](https://osdn.net/projects/ttssh2/) 4.105以降

# 前提条件
* [新規プロジェクト作成方法(ベアメタル)](../../bare-metal/generate-new-project.md) を完了すること
* [1+SCI](../../bare-metal/sci.md) を完了すること
    * 本稿では、[新規プロジェクト作成方法(ベアメタル)](../../bare-metal/generate-new-project.md)で作成したLED0.1秒周期点滅プログラムと[1+SCI](../../bare-metal/sci.md)で作成したログ表示機構に、TCP/IPスタック([組み込み用TCP/IP M3S-T4-Tiny](https://www.renesas.com/products/software-tools/software-os-middleware-driver/protocol-stack/m3s-t4-tiny-for-rx.html))を追加する形で実装する

# 組み込み用TCP/IP M3S-T4-Tiny の特性
* OSレス環境で動作する軽量のTCP/IPプロトコルスタック
    * 20KB程度のROM、数KB程度のRAM、タイマ1本で動作する
* [筆者](https://github.com/HirokiIshiguro) がスクラッチ開発
* 開発開始は2003年
* 通称T4 "ティーフォー" と呼ばれる
* 過去R8C、H8、M16C、SH2A等をサポートし、2020年時点ではRXをサポート
* ソースコードは以下に格納 (改築を繰り返しスパゲッティ状態のため作り直したいが機会に恵まれず)
    * https://github.com/renesas/rx-driver-package/tree/master/source/r_t4_rx/r_t4_rx_vx.xx/r_t4_rx/make_lib
* RXファミリを中心に多くの量産製品に搭載されている
* OS環境を利用する場合、[AWS社のFreeRTOS](https://aws.amazon.com/freertos/) 等のOSベンダが提供するTCP/IPスタックを利用することを推奨
    * FreeRTOSはリアルタイムOSのカーネル部分のみならず、AWS接続に必要なTCP/IPスタック、SSL、MQTTなど各種プロトコルも包含するようになった
    * 以下のように最新の脆弱性についても適宜パッチ提供される
        * https://aws.amazon.com/freertos/security-updates/
* 本TCP/IPも可能な限り脆弱性をトレースしパッチを提供するが、AWS程の規模感ではトレースができない
    * 従って、本TCP/IPを使用したシステムは、インターネットには接続せずLAN内通信に留めることを推奨

## セミナ資料
* 筆者が講師を担当したセミナ資料を掲載
* TCP/IPの歴史や最新の(といっても2019年当時の)組み込み業界におけるIoTのトレンド情報、RXマイコンのEtherコントローラの動作解説、T4の利用方法やT4内部のソースコードレベルデバッグ手法などを解説
  * ../../images/%E7%B5%84%E3%81%BF%E8%BE%BC%E3%81%BF%E7%94%A8TCPIP%E3%81%AE%E6%B4%BB%E7%94%A8%E6%B3%95.pptx

# 接続方法
```
RX72N ENvision Kit ----(LANケーブル)---インターネット接続可能なルータ
 |(USB(ECN1, CN8))                        |
PC---------------(LANケーブル)------------+
```

# 回路確認
* <a href="../../images/063_board_ether.png" target="_blank"><img src="../../images/063_board_ether.png" width="480px" target="_blank"></a>
    * EtherC/EDMACとは、上記回路のPC4/ET0_TX_CLK~PC3/ET-INTn のようにデータ信号線ET0_ETXD0-3(送信)、ET0_ERXD0-3(受信)の8本を使用、送信と受信それぞれにET0_TX_CLK、ET0_RX_CLKの2本の転送クロック、ET0_TX_ENなどの制御用信号を合わせた[Media Independ Interface(MII)](https://ja.wikipedia.org/wiki/Media-independent_interface#:~:text=media%2Dindependent%20interface%EF%BC%88MII%E3%80%81,%E3%81%9F%E6%A8%99%E6%BA%96%E3%82%A4%E3%83%B3%E3%82%BF%E3%83%95%E3%82%A7%E3%83%BC%E3%82%B9%E3%81%A7%E3%81%82%E3%82%8B%E3%80%82)で接続されている
    * MIIの信号はPHYチップ(KSZ8041NL)に接続されている
    * MIIで規定される信号以外に以下が接続されている
        * P56/CLKOUT25M: RX72NからPHYチップに供給するクロックであり25MHzが供給される
            * MIIではこの25MHzが転送クロックとなり、送信受信それぞれ4本ずつのデータラインにより1クロックあたり4ビットの転送、つまり100Mbpsを実現する
    * PHYチップとの通信は、MDC/MDIOの2本線によるクロック同期シリアル通信で行う
        * PHYチップはI2C通信のようにPHYアドレスを持つ
        * PHYアドレスはPHYチップリセット時の端子状態により確定する
        * 回路図上、PHYAD0="フローティング", PHYAD1="フローティング"、PHYAD2="フローティング"となっている
            * 回路図上プルアップ/プルダウンされているように見えるが（DNF）であり未接続
            * PHYチップ内部でデフォルト値が保持されており、PHYAD[2:0] = "001"となる
            * またPHYチップ内部でPHYAD3="L", PHYAD4="L"と固定されておりPHYAD[4:3] = "00"となる
                * つまりPHYアドレスは、PHYAD[4:0] = "00001" である
        * [PHYチップ(KSZ8041NL) datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/00002245B.pdf)
            * 2.2 STRAP-IN OPTION – KSZ8041NL 参照

# スマートコンフィグレータによるEtherC/EDMAC用ドライバソフトウェアおよびTCP/IPの設定
## コンポーネント追加
* <a href="../../images/064_e2_studio_sc.png" target="_blank"><img src="../../images/064_e2_studio_sc.png" width="480px" target="_blank"></a>
    * 上記のようにT4のコンポーネントを追加する
        * r_t4_rx (上記スクリーンショットで説明)
    * 依存関係にある以下コンポーネントが自動で登録される
        * r_ether_rx, r_sys_time_rx, r_t4_driver_rx
## コンポーネント設定
### r_t4_rx
* 特に設定は不要
    * 主要設定項目には以下のようなものがある
        * DHCPのON/OFF
        * DHCPがOFFの時の固定IPアドレス
        * 通信端点(ソケットという呼称のほうが通りが良い)の設定
            * デフォルトでTCPの通信端点が6個定義されている
            * 通信端点毎にデフォルト設定値は1460バイトの受信ウィンドウを抱える必要がありその分RAMが必要
            * 通信端点は同時に通信が必要な最低限の分を定義するとよい

### r_ether_rx
* <a href="../../images/065_e2_studio_sc.png" target="_blank"><img src="../../images/065_e2_studio_sc.png" width="480px" target="_blank"></a>
    * PHYアドレスを "0" から "1" に変更
    * "The register bus of PHY0/1 for ETHER0/1" を "Use ETHER1" から "Use ETHER0" に変更
    * "The link status is detected" を "Used" から "Unused" に変更
        * ET_LINKSTA端子とPHYチップのリンク状態出力信号を繋いである回路であれば、リンク状態の変化を割り込みとしてキャッチすることが可能
        * リンク状態の変化はLANケーブルの挿抜のことであり、直ちに処理が必要になるケースが少なく、ET_LINKSTA端子は使われないことが多い
        * この設定を"Unused"にすると、MDC/MIDOを使用して定期的にPHYチップにリンク状態を問いかけに行く実装(10ms周期のポーリング)に切り替わる
            * この10ms周期の制御はr_t4_driver.c の以下コードにより行われる
                * https://github.com/renesas/rx-driver-package/blob/ebfbb6d89e6d4229a5ce524128499c9fe6b41377/source/r_t4_driver_rx/r_t4_driver_rx_vx.xx/r_t4_driver_rx/src/t4_driver.c#L484

### r_sys_time_rx
* 特に設定は不要

### r_t4_driver_rx
* 特に設定は不要

### r_tsip_rx
* 特に設定は不要
  * r_t4_rx の v210以降を利用すると、TCPシーケンス番号等の乱数性が必要な処理に対し、RXマイコン内蔵のセキュリティIP「Trusted Secure IP(TSIP)」を利用して乱数生成を実行する
  * 輸出管理対象のデータの為ライブラリ配布になっているが、ルネサスのカスタマサポートセンタ経由でソースコードを入手可能
  * ライブラリ版の場合、全機能がリンクされる（将来改善予定）ので、ROMが大量に消費されるので、量産製品向けなどにROMの利用状況を最適化する等が必要な場合はソースコード版の利用を推奨する

## 端子設定
* <a href="../../images/066_e2_studio_sc.png" target="_blank"><img src="../../images/066_e2_studio_sc.png" width="480px" target="_blank"></a>
    * RX72N マイコンは、1個の端子に複数機能が割り当たっているため、どの機能を使用するかの設定をソフトウェアにより施す必要がある
    * 上記のようにスマートコンフィグレータ上で端子設定を行い、コード生成する
    * ボードコンフィグレーションファイル(BDF)を読み込むことで、スマートコンフィグレータ上の「端子設定」が自動化される

## TeraTermの設定
* [参照](https://github.com/renesas/rx72n-envision-kit/wiki/%E5%88%9D%E6%9C%9F%E3%83%95%E3%82%A1%E3%83%BC%E3%83%A0%E3%82%A6%E3%82%A7%E3%82%A2%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D%E6%96%B9%E6%B3%95#%E3%83%99%E3%83%B3%E3%83%81%E3%83%9E%E3%83%BC%E3%82%AF%E3%83%87%E3%83%A2%E8%B5%B7%E5%8B%95)
    * 「CN8(USB Micro-B)と通信相手となるUSBポート(PC等)をUSBケーブルを用いて接続」の項目参照
    * 「Windows PC上でTeratermを立ち上げ、COMポート(COMx: RSK USB Serial Port(COMx))を選択し接続」の項目参照

## セクション設定変更
* ビルドすると、Ether関連のセクション「B_ETHERNET_BUFFERS」等に他の変数が割りあたるBセクションがオーバーラップしてきている旨エラーがでる
* 以下3点のセクションを0x00800000にある拡張RAM領域に割り当てると良い
    * B_ETHERNET_BUFFERS_1
    * B_RX_DESC_1
    * B_TX_DESC_1
* e2 studio プロジェクトエクスプローラ上にて
* <a href="../../images/067_e2_studio_sc.png" target="_blank"><img src="../../images/067_e2_studio_sc.png" width="480px" target="_blank"></a>
* <a href="../../images/068_e2_studio_sc.png" target="_blank"><img src="../../images/068_e2_studio_sc.png" width="480px" target="_blank"></a>

## main()関数のコーディング
* 以下のように rx72n_envision_kit.c にコード追加を行う
* このコードではTCP/IPを起動するところまでを実現する
* 正常にTCP/IPが起動すると、TeraTerm側にDHCPで入手したIPアドレス等の情報が表示される
* PCからこのIPアドレスに対し コマンドプロンプトで ping 192.168.1.207 と入力すると応答があることが確認できる

```rx72n_envision_kit.c
#include <stdio.h>
#include <string.h> 

#include "r_smc_entry.h"
#include "platform.h"
#include "r_cmt_rx_if.h"
#include "r_sci_rx_if.h"
#include "r_t4_itcpip.h"
#include "r_t4_rx_config.h"

#include "Pin.h"
#include "r_sci_rx_pinset.h"
#include "r_ether_rx_pinset.h"
#include "r_sys_time_rx_if.h"

#if 1
/* Please turn off this section if you would use old r_t4_rx. */
#include "r_tsip_rx_if.h"
#endif

#define DEBUG_PRINT 1

void main(void);
void cmt_callback(void *arg);
void sci_callback(void *arg);
void my_sw_charput_function(char *data);
char my_sw_charget_function(void);

static sci_hdl_t sci_handle;
static UB guc_event[T4_CFG_SYSTEM_CHANNEL_NUMBER];
static DHCP* gpt_dhcp[T4_CFG_SYSTEM_CHANNEL_NUMBER];

static UW tcpudp_work[14800];

void main(void)
{
    uint32_t cmt_channel;
    R_CMT_CreatePeriodic(10, cmt_callback, &cmt_channel);
    sci_cfg_t   my_sci_config;
    int32_t size;

#if 1
    /* Please turn off this section if you would use old r_t4_rx. */
    R_TSIP_Open(NULL, NULL); 
#endif

    /* Set up the configuration data structure for asynchronous (UART) operation. */
    my_sci_config.async.baud_rate    = 115200;
    my_sci_config.async.clk_src      = SCI_CLK_INT;
    my_sci_config.async.data_size    = SCI_DATA_8BIT;
    my_sci_config.async.parity_en    = SCI_PARITY_OFF;
    my_sci_config.async.parity_type  = SCI_EVEN_PARITY;
    my_sci_config.async.stop_bits    = SCI_STOPBITS_1;
    my_sci_config.async.int_priority = 15; /* disable 0 - low 1 - 15 high */

    R_Pins_Create();
    R_SCI_Open(SCI_CH2, SCI_MODE_ASYNC, &my_sci_config, sci_callback, &sci_handle);
    R_SCI_PinSet_SCI2();
    R_ETHER_PinSet_ETHERC0_MII();

    printf("Hello World\n");

    R_SYS_TIME_Open();

    /* start LAN controller */
    lan_open();

    /* initialize TCP/IP */
    size = tcpudp_get_ramsize();
    if (size > (sizeof(tcpudp_work)))
    {
        while (1);
    }
    tcpudp_open(tcpudp_work);

    while(1);
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

void sci_callback(void *arg)
{

}

void my_sw_charput_function(char *data)
{
    uint32_t arg = 0;
    /* do not call printf()->charput in interrupt context */
    do
    {
        R_SCI_Control(sci_handle, SCI_CMD_TX_Q_BYTES_FREE, (void*)&arg);
    }
    while (SCI_CFG_CH2_TX_BUFSIZ != arg);
    R_SCI_Send(sci_handle, (uint8_t*)&data, 1);
}

char my_sw_charget_function(void)
{
	return 0;
}

ER system_callback(UB channel, UW eventid, VP param)
{
#if defined(DEBUG_PRINT)
    uint8_t*    ev_tbl[] =
    {
        "ETHER_EV_LINK_OFF",
        "ETHER_EV_LINK_ON",
        "ETHER_EV_COLLISION_IP",
        "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
        "DHCP_EV_LEASE_IP",
        "DHCP_EV_LEASE_OVER",
        "DHCP_EV_INIT",
        "DHCP_EV_INIT_REBOOT",
        "DHCP_EV_APIPA",
        "DHCP_EV_NAK",
        "DHCP_EV_FATAL_ERROR",
        "DHCP_EV_PLEASE_RESET"
    };
    printf("^^>>>user_cb<<< ch:%d,eventID = %s\n", channel, ev_tbl[eventid]);
#endif /*#if defined(DEBUG_PRINT)*/
    guc_event[channel] = eventid;
    switch(eventid)
    {
        case ETHER_EV_LINK_OFF:
        {
            /* Do Nothing. */
        }
        break;

        case ETHER_EV_LINK_ON:
        {
            /* Do Nothing. */
        }
        break;

        case ETHER_EV_COLLISION_IP:
        {
            /* Do Nothing. */
        }
        break;

        case DHCP_EV_LEASE_IP:
        {
            /* cast from VP to DHCP* */
            gpt_dhcp[channel] = (DHCP*)param;
#if defined(DEBUG_PRINT)
            printf("DHCP.ipaddr[4]   %d.%d.%d.%d\n",
                   gpt_dhcp[channel]->ipaddr[0], gpt_dhcp[channel]->ipaddr[1],
                   gpt_dhcp[channel]->ipaddr[2], gpt_dhcp[channel]->ipaddr[3]);
            printf("DHCP.maskaddr[4] %d.%d.%d.%d\n",
                   gpt_dhcp[channel]->maskaddr[0], gpt_dhcp[channel]->maskaddr[1],
                   gpt_dhcp[channel]->maskaddr[2], gpt_dhcp[channel]->maskaddr[3]);
            printf("DHCP.gwaddr[4]   %d.%d.%d.%d\n",
                   gpt_dhcp[channel]->gwaddr[0], gpt_dhcp[channel]->gwaddr[1],
                   gpt_dhcp[channel]->gwaddr[2], gpt_dhcp[channel]->gwaddr[3]);
            printf("DHCP.dnsaddr[4]  %d.%d.%d.%d\n",
                   gpt_dhcp[channel]->dnsaddr[0], gpt_dhcp[channel]->dnsaddr[1],
                   gpt_dhcp[channel]->dnsaddr[2], gpt_dhcp[channel]->dnsaddr[3]);
            printf("DHCP.dnsaddr2[4] %d.%d.%d.%d\n",
                   gpt_dhcp[channel]->dnsaddr2[0], gpt_dhcp[channel]->dnsaddr2[1],
                   gpt_dhcp[channel]->dnsaddr2[2], gpt_dhcp[channel]->dnsaddr2[3]);
            printf("DHCP.macaddr[6]  %02X:%02X:%02X:%02X:%02X:%02X\n",
                   gpt_dhcp[channel]->macaddr[0],  gpt_dhcp[channel]->macaddr[1],  gpt_dhcp[channel]->macaddr[2],
                   gpt_dhcp[channel]->macaddr[3],  gpt_dhcp[channel]->macaddr[4],  gpt_dhcp[channel]->macaddr[5]);
            printf("DHCP.domain[%d] %s\n", strlen(gpt_dhcp[channel]->domain), gpt_dhcp[channel]->domain);
            printf("\n");
#endif /*#if defined(DEBUG_PRINT)*/
        }
        break;

        case DHCP_EV_LEASE_OVER:
        {
            /* Do Nothing. */
        }
        break;

        case DHCP_EV_INIT:
        {
            /* Do Nothing. */
        }
        break;

        case DHCP_EV_INIT_REBOOT:
        {
            /* Do Nothing. */
        }
        break;

        case DHCP_EV_APIPA:
        {
            /* cast from VP to DHCP* */
            gpt_dhcp[channel] = (DHCP*)param;
#if defined(DEBUG_PRINT)
            printf("DHCP.ipaddr[4]   %d.%d.%d.%d\n",
                   gpt_dhcp[channel]->ipaddr[0], gpt_dhcp[channel]->ipaddr[1],
                   gpt_dhcp[channel]->ipaddr[2], gpt_dhcp[channel]->ipaddr[3]);
            printf("DHCP.maskaddr[4] %d.%d.%d.%d\n",
                   gpt_dhcp[channel]->maskaddr[0], gpt_dhcp[channel]->maskaddr[1],
                   gpt_dhcp[channel]->maskaddr[2], gpt_dhcp[channel]->maskaddr[3]);
            printf("DHCP.gwaddr[4]   %d.%d.%d.%d\n",
                   gpt_dhcp[channel]->gwaddr[0], gpt_dhcp[channel]->gwaddr[1],
                   gpt_dhcp[channel]->gwaddr[2], gpt_dhcp[channel]->gwaddr[3]);
            printf("DHCP.dnsaddr[4]  %d.%d.%d.%d\n",
                   gpt_dhcp[channel]->dnsaddr[0], gpt_dhcp[channel]->dnsaddr[1],
                   gpt_dhcp[channel]->dnsaddr[2], gpt_dhcp[channel]->dnsaddr[3]);
            printf("DHCP.dnsaddr2[4] %d.%d.%d.%d\n",
                   gpt_dhcp[channel]->dnsaddr2[0], gpt_dhcp[channel]->dnsaddr2[1],
                   gpt_dhcp[channel]->dnsaddr2[2], gpt_dhcp[channel]->dnsaddr2[3]);
            printf("DHCP.macaddr[6]  %02X:%02X:%02X:%02X:%02X:%02X\n",
                   gpt_dhcp[channel]->macaddr[0],  gpt_dhcp[channel]->macaddr[1],  gpt_dhcp[channel]->macaddr[2],
                   gpt_dhcp[channel]->macaddr[3],  gpt_dhcp[channel]->macaddr[4],  gpt_dhcp[channel]->macaddr[5]);
            printf("DHCP.domain[%d] %s\n", strlen(gpt_dhcp[channel]->domain), gpt_dhcp[channel]->domain);
            printf("\n");
#endif /*#if defined(DEBUG_PRINT)*/
        }
        break;

        case DHCP_EV_NAK:
        {
            /* Do Nothing. */
        }
        break;

        case DHCP_EV_FATAL_ERROR:
        {
            /* Do Nothing. */
        }
        break;

        case DHCP_EV_PLEASE_RESET:
        {
            /* Do Nothing. */
        }
        break;

        default:
        {
            /* Do Nothing. */
        }
        break;
    }
    return 0;
}
```
## 出力結果(TeraTerm)
```
Hello World
^^>>>user_cb<<< ch:0,eventID = ETHER_EV_LINK_ON
^^>>>user_cb<<< ch:0,eventID = DHCP_EV_INIT
^^>>>user_cb<<< ch:0,eventID = DHCP_EV_LEASE_IP
DHCP.ipaddr[4]   192.168.1.207
DHCP.maskaddr[4] 255.255.255.0
DHCP.gwaddr[4]   192.168.1.1
DHCP.dnsaddr[4]  192.168.1.1
DHCP.dnsaddr2[4] 0.0.0.0
DHCP.macaddr[6]  74:90:50:00:79:03
DHCP.domain[0]
```

## Ping応答(コマンドプロンプト)
```
C:\Users\Shelty>ping 192.168.1.207

192.168.1.207 に ping を送信しています 32 バイトのデータ:
192.168.1.207 からの応答: バイト数 =32 時間 <1ms TTL=80
192.168.1.207 からの応答: バイト数 =32 時間 <1ms TTL=80
192.168.1.207 からの応答: バイト数 =32 時間 <1ms TTL=80
192.168.1.207 からの応答: バイト数 =32 時間 <1ms TTL=80

192.168.1.207 の ping 統計:
    パケット数: 送信 = 4、受信 = 4、損失 = 0 (0% の損失)、
ラウンド トリップの概算時間 (ミリ秒):
    最小 = 0ms、最大 = 0ms、平均 = 0ms
```


