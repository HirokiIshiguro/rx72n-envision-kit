# 準備する物
* 必須
    * RX72N Envision Kit × 1台
    * USBケーブル(USB Micro-B --- USB Type A) × 2 本
    * Windows PC × 1 台
        * Windows PC にインストールするツール
            * [jperf-2.0.0](https://ja.osdn.net/projects/sfnet_iperf/downloads/jperf/jperf%202.0.0/jperf-2.0.0.zip/)
    * LANケーブル × 2 本
    * ルータ × 1 台 (DHCPサーバとして動作するもの)

# 前提条件
* ファームウェアバージョンv1.0.4以降がインストールされていること
    * 書き込み方法 = [SDカードを用いたファームアップデート方法](../quick-start/update-firmware-from-sd-card.md)
* コマンドレスポンスの動作確認ができていること
    * 以下ページの シリアルターミナルデモ 参照
        * [初期ファームウェア動作確認方法](../quick-start/confirm-factory-image-behavior.md)

# ベンチマーク実行方法
* RX72N Envision Kit を動作状態にしておく
* jperfを起動
* RX72N Envision Kitのタイトル画面の次の画面下部に表示されるIPアドレスを確認 (DHCPサーバから割り振られ、192.168.1.206等の値になる)

## TCP受信を計測する場合
* jperf の Choose iPerf Mode で Client を選択し、RX72N Envision KitのIPアドレスを入力、ポート番号は5001
* jperf 右上にある Run Iperf! ボタンを押す
## TCP送信を計測する場合
* jperf の Choose iPerf Mode で Server を選択する
* RX72N Envision Kit のコマンドレスポンスにて、PCのIPアドレスとポート番号を登録する
    * IPアドレスの登録 (PC の IPアドレスが 192.168.1.6の場合)
        * $ dataflash write tcpsendperformanceserveripaddress 192.168.1.6
    * ポート番号の登録 (PC の ポート番号が 5001の場合)
        * $ dataflash write tcpsendperformanceserverportnumber 5001
* jperf 右上にある Run Iperf! ボタンを押す
* RX72N Envision Kit のコマンドレスポンスにて、ソフトウェアリセットを発行する (jperfへの接続はシステム起動時に行われる)
  * $ reset

### TCP送信計測時の注意事項
* 2回目以降の接続時、jperf側の挙動が不正になり、RX72N Envision Kitからの接続を受け付けない場合がある
  * この場合、jperf側のポート番号を5002等に変更する
  * さらにRX72N Envision Kit のコマンドレスポンスにて、PCのポート番号を登録しなおす
    * $ dataflash write tcpsendperformanceserverportnumber 5002
* RX72N Envision Kit のコマンドレスポンスにて、ソフトウェアリセットを発行する (jperfへの接続はシステム起動時に行われる)
  * $ reset

# 性能評価
* TCP受信: 約76Mbps / CPU負荷率 40% 程度
    * <a href="../../images/040_tcp_receive_performance.png" target="_blank"><img src="../../images/040_tcp_receive_performance.png" width="480px" target="_blank"></a>
* TCP送信: 約57Mbps / CPU負荷率 90% 程度 <最適な状態になっていない様子。要チューニング>
    * <a href="../../images/041_tcp_send_performance.png" target="_blank"><img src="../../images/041_tcp_send_performance.png" width="480px" target="_blank"></a>

# ネットワーク設定値
* FreeRTOS+TCP
    * https://github.com/renesas/rx72n-envision-kit/blob/master/vendors/renesas/boards/rx72n-envision-kit/aws_demos/config_files/FreeRTOSIPConfig.h
* Ethernet Driver
    * https://github.com/renesas/rx72n-envision-kit/blob/master/vendors/renesas/boards/rx72n-envision-kit/aws_demos/src/smc_gen/r_config/r_ether_rx_config.h
