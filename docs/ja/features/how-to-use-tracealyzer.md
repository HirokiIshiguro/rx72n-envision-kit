# 準備する物
* 必須
    * RX72N Envision Kit × 1台
    * USBケーブル(USB Micro-B --- USB Type A) × 2 本
    * Windows PC × 1 台
        * Windows PC にインストールするツール
            * [Tracealyzer](https://percepio.com/downloadform/)
    * LANケーブル × 2 本
    * ルータ × 1 台 (DHCPサーバとして動作するもの)

# 前提条件
* ファームウェアバージョンv2.0.1以降がインストールされていること
    * 書き込み方法 = [SDカードを用いたファームアップデート方法](../../quick-start/update-firmware-from-sd-card.md)
* コマンドレスポンスの動作確認ができていること
    * 以下ページの シリアルターミナルデモ 参照
        * [初期ファームウェア動作確認方法](../../quick-start/confirm-factory-image-behavior.md)

# 動作解説
* TracealyzerはリアルタイムOSの内部情報をRAMに蓄積し、UARTやEthernet等の通信路経由で外部に出力しそれをPC上のソフトウェアで受信することで、その内部情報の可視化を行う
  * このため、TracealyzerはリアルタイムOSが搭載されるデバイス（今回の場合RX72N Envision Kit）に内部情報を収集するためのライブラリをインストールする必要がある
  * RX72N Envision Kitのファームウェアv2.0.0以降でTracealyzerのライブラリを実装した
  * RX72N Envision KitではEthernet経由でリアルタイムOSの内部情報を出力するように実装した
* RX72N Envision KitはTracealyzerデータの出力先のPCと通信するため、PCのIPアドレスとポート番号を知る必要がある
  * コマンドレスポンスによりこれらの設定値をRX72N Envision Kitに書き込むことができる

# 設定例(RX72N Envision Kit)
* dataflash write tracealyzerserveripaddress 192.168.1.210
* dataflash write tracealyzerserverportnumber 12000
* ![image](https://user-images.githubusercontent.com/37968119/190856509-adf63d75-8192-4ed9-9d32-3896893d85ab.png)

# 設定例(PC)
* ![image](https://user-images.githubusercontent.com/37968119/190856426-04e876d5-0030-4a14-a48f-4116cd94df31.png)

# 動作している様子
* 動画

https://github.com/renesas/rx72n-envision-kit/assets/37968119/26790de7-03f8-4235-94a4-0f3afd66e6d4

# 参考
* 本ページではRX72N Envision Kitのファームウェアに実装済のTracealyzerのライブラリ[Tracealyzer Recorder](https://github.com/percepio/TraceRecorderSource)の実装方法の説明を省略し、使用方法のみ解説している
* 実装方法については以下で解説を行っている
  * [Tracealyzer Recorderの実装方法](../../freertos/how-to-implement-tracealyzer-recorder.md)
