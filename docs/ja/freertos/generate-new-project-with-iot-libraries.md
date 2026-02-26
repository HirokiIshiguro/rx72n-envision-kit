# 準備する物
* 必須
    * RX72N Envision Kit × 1台
    * USBケーブル(USB Micro-B --- USB Type A) × 1 本
    * LANケーブル x 1 本
    * インターネット接続されたルータ(Ethernet接続対応品) x 1台
    * Windows PC × 1 台
        * Windows PC にインストールするツール
            * [e2 studio 2020-07](https://www.renesas.com/products/software-tools/tools/ide/e2studio.html)
            * [CC-RX](https://www.renesas.com/products/software-tools/tools/compiler-assembler/compiler-package-for-rx-family.html) V3.02以降

# e2 studio を起動し、新規プロジェクトを作成する
* ファイル -> 新規 -> プロジェクト
    * ウィザード -> C/C++ -> C/C++ プロジェクト -> 次へ
        * All -> Renesas CC-RX C/C++ Executable Project
            * プロジェクト名 = rx72n_envision_kit を入力 -> 次へ
                * Toolchain Settings
                    * RTOS -> FreeRTOS(Kernel IoT Libraries)
                    * RTOS Version に何も表示されない場合は "Manage RTOS Versions..." リンクからRTOSパッケージを入手
                    * RTOS Version には v202002.00-rx-1.0.1 より新しいものを選択
                * Device Settings 
                    * Target Board -> EnvisionRX72N
                        * EnvisionRX72Nが選択できる場合：ターゲット・デバイスが自動選択される
                        * EnvisionRX72Nが選択できない場合：ターゲット・デバイスが自動選択されない。
                            * この場合、Customを選びプロジェクト作成後に[RX72N Envision Kit の ボードコンフィグレーションファイル(BDF)をインストール](https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95(FreeRTOS)#rx72n-envision-kit-%E3%81%AE-%E3%83%9C%E3%83%BC%E3%83%89%E3%82%B3%E3%83%B3%E3%83%95%E3%82%A3%E3%82%B0%E3%83%AC%E3%83%BC%E3%82%B7%E3%83%A7%E3%83%B3%E3%83%95%E3%82%A1%E3%82%A4%E3%83%ABbdf%E3%82%92%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB)を実施

                            * Device Settings -> ターゲット・デバイス -> ...ボタン -> RX700 -> RX72N -> RX72N - 144pin -> R5F572NNHxFB (ファームウェアアップデートも試そうと考えている場合は、R5F572NNHxFB_DUALを選択)
                            * ★将来改善★ Amazon FreeRTOS OTAを試す場合は R5F572NNHxFB_DUAL 選択が必要だが、BDFにより固定化されている。
                            * ★将来改善★ プロジェクト新規作成時もBDFインストールができるようにする
                * Configuration -> Hardware Debug 構成を生成 -> E2 Lite (RX) -> 次へ
                    * スマート・コンフィグレータを使用する にチェック -> 終了
# 接続方法
```
RX72N ENvision Kit ----(LANケーブル)---インターネット接続可能なルータ
 |(USB(ECN1, CN8))
PC
```

# デバッガ設定
* [参照](https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95(%E3%83%99%E3%82%A2%E3%83%A1%E3%82%BF%E3%83%AB)#%E3%83%87%E3%83%90%E3%83%83%E3%82%AC%E8%A8%AD%E5%AE%9A)

# TeraTermの設定
* [参照](https://github.com/renesas/rx72n-envision-kit/wiki/%E5%88%9D%E6%9C%9F%E3%83%95%E3%82%A1%E3%83%BC%E3%83%A0%E3%82%A6%E3%82%A7%E3%82%A2%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D%E6%96%B9%E6%B3%95#%E3%83%99%E3%83%B3%E3%83%81%E3%83%9E%E3%83%BC%E3%82%AF%E3%83%87%E3%83%A2%E8%B5%B7%E5%8B%95)
    * 「CN8(USB Micro-B)と通信相手となるUSBポート(PC等)をUSBケーブルを用いて接続」の項目参照
    * 「Windows PC上でTeratermを立ち上げ、COMポート(COMx: RSK USB Serial Port(COMx))を選択し接続」の項目参照

# 動作確認(ネットワーク接続確認)
* TeraTerm上に以下ログが出力されれば成功
* "19 4924 [IP-task] IP Address: 192.168.1.209" のようにDHCPからIPアドレスが入手出来ていれば正しく起動できている

```
0 1 [ETHER_RECEI] Deferred Interrupt Handler Task started
1 1 [ETHER_RECEI] Network buffers: 8 lowest 8
2 1 [ETHER_RECEI] Heap: current 234144 lowest 234144
3 1 [ETHER_RECEI] Queue space: lowest 13
4 1 [IP-task] InitializeNetwork returns OK
5 1 [IP-task] xNetworkInterfaceInitialise returns 0
6 101 [ETHER_RECEI] R_ETHER_Read_ZC2: rc = -5
7 102 [ETHER_RECEI] prvLinkStatusChange( 1 )
8 102 [ETHER_RECEI] prvEMACHandlerTask: PHY LS now 1
9 102 [ETHER_RECEI] Heap: current 233944 lowest 233344
10 193 [ETHER_RECEI] Network buffers: 7 lowest 7
11 1194 [ETHER_RECEI] Network buffers: 6 lowest 6
12 2197 [ETHER_RECEI] Network buffers: 5 lowest 5
13 3001 [IP-task] xNetworkInterfaceInitialise returns 1
14 3097 [ETHER_RECEI] Heap: current 233776 lowest 233248
15 3097 [ETHER_RECEI] Queue space: lowest 10
16 4915 [IP-task] vDHCPProcess: offer c0a801d1ip
17 4924 [ETHER_RECEI] Heap: current 233408 lowest 233208
18 4924 [IP-task] vDHCPProcess: offer c0a801d1ip
19 4924 [IP-task] IP Address: 192.168.1.209
20 4924 [IP-task] Subnet Mask: 255.255.255.0
21 4924 [IP-task] Gateway Address: 192.168.1.1
22 4924 [IP-task] DNS Server Address: 192.168.1.1
23 5024 [ETHER_RECEI] Heap: current 233888 lowest 232576
24 5100 [Tmr Svc] The network is up and running
25 5124 [ETHER_RECEI] Heap: current 231720 lowest 231648
26 5194 [ETHER_RECEI] Heap: current 229848 lowest 228496
27 6892 [Tmr Svc] Warning: the client certificate should be updated. Please see https://aws.amazon.com/freertos/getting-started/.
28 6892 [Tmr Svc] Device public key, 91 bytes:
3059 3013 0607 2a86 48ce 3d02 0106 082a
8648 ce3d 0301 0703 4200 0468 9158 27d1
6fb0 a44e adbd a718 5798 1ab5 8a7c c1c8
ad07 ddf5 ae0d e92d d2af fc43 7be8 d049
706b 7c54 3933 0ed8 88c9 1af8 9741 5277
1b4f f383 f4d9 fade 48de 91
29 6893 [iot_thread] [INFO ][DEMO][6893] ---------STARTING DEMO---------

30 6894 [ETHER_RECEI] Heap: current 212080 lowest 212080
35 6953 [ETHER_RECEI] Heap: current 207944 lowest 206720
36 7016 [iot_thread] [ERROR][NET][7016] Failed to resolve .
37 7016 [iot_thread] [ERROR][MQTT][7016] Failed to establish new MQTT connection, error NETWORK ERROR.
38 7016 [iot_thread] [ERROR][DEMO][7016] MQTT CONNECT returned error NETWORK ERROR.
39 7016 [iot_thread] [INFO ][MQTT][7016] MQTT library cleanup done.
40 7016 [iot_thread] [ERROR][DEMO][7016] Error running demo.
41 7016 [iot_thread] [INFO ][INIT][7016] SDK cleanup done.
42 7016 [iot_thread] [INFO ][DEMO][7016] -------DEMO FINISHED-------
```

# 動作確認(AWS接続確認)
* AWSと接続確認するためには、ソースコード上にAWS接続情報を埋め込みAWS側も設定する必要がある
* 以下チュートリアルを参照
    * https://github.com/renesas/amazon-freertos/wiki/%E3%83%87%E3%83%90%E3%82%A4%E3%82%B9%E3%82%92AWS-IoT%E3%81%AB%E7%99%BB%E9%8C%B2%E3%81%99%E3%82%8B