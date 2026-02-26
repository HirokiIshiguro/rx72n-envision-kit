# 準備する物
* 必須
    * RX72N Envision Kit × 1台
    * USBケーブル(USB Micro-B --- USB Type A) × 1 本
* オプション
    * USBケーブル(USB Micro-B --- USB Type A) × 2 本 (必須の1本を加え、合計3本)
    * LANケーブル(インターネット接続可能なネットワークに接続されていること) × 1 本
    * マイクロSDカード × 1 枚
    * [USB-シリアル変換 PMODモジュール](https://store.digilentinc.com/pmod-usbuart-usb-to-uart-interface/) × 1 台
    * Windows PC × 1 台
        * Windows PCへのインストール
            * [Tera Term](https://osdn.net/projects/ttssh2/) 4.105で動作確認済み
                * [シリアル接続における高速なファイル転送](https://teratermproject.github.io/manual/5/ja/setup/teraterm-trans.html#FileSendHighSpeedMode) の FileSendHighSpeedMode を OFF にする
                    * Tera Term -> 設定 -> 設定の読み込み -> TERATERM.INI を テキストエディタで開く -> 設定を変更 -> 保存 -> Tera Term再起動

# SPORTS GAMESデモ起動
* ECN1(USB Micro-B)と電源となるUSBポート(PC等)をUSBケーブルを用いて接続
    * <a href="../../images/001_board_power_on.jpg" target="_blank"><img src="../../images/001_board_power_on.jpg" width="480px" target="_blank"></a>

* 液晶面にてSPORTS GAMESが起動することを確認
    * <a href="../../images/002_board_sports_games.jpg" target="_blank"><img src="../../images/002_board_sports_games.jpg" width="480px" target="_blank"></a>
    * タイトル画面を指で左右にスライドすると以下4種類のゲームが選択可能。「PLAY」ボタンでプレイ開始。
        * Archery
        * 400m Race
        * Weightlifting
        * Bicycle Race
    * 本ゲームはSegger社の[emWinミドルウェア](https://www.segger.com/products/user-interface/emwin/)およびRX72N内蔵のLCDコントローラ「GLCDC」機能および2Dグラフィックエンジン「DRW2D」を活用して作成したもの
    * 画面描画のためのシステム仕様は以下の通り
        * 画面解像度: 480x272(WQVGA)
        * 描画用フレームバッファサイズは(480x272)x16bit color = 2,088,960bit = 256KB
        * LCDコントローラ転送用フレームバッファと、更新用フレームバッファの2面を持たせる（画面チラつきを防止するため）
        * RX72Nの内蔵RAM 1MBのうち、512KBを画面描画用に占有
        * 画面更新は16.66msに1回以上(60fps以上)行う

# バンク切り替え
* バンク切り替えの概念
    * RX72N 内蔵メモリマップ
        * <a href="../../images/003_rx72n_memory_map.png" target="_blank"><img src="../../images/003_rx72n_memory_map.png" width="480px" target="_blank"></a>
        * ファームウェアアップデートの仕組みを1チップで実現する場合、デュアルモードを使用することが推奨
        * デュアルモードでは起動バンクをBank0またはBank1とで以下仕組みにより選択することが可能
            * <a href="../../images/004_rx72n_dual_mode.png" target="_blank"><img src="../../images/004_rx72n_dual_mode.png" width="480px" target="_blank"></a>
    * RX72N Envision Kit では、Bank 0にSPORTS GAMESデモ、Bank 1にベンチマークデモが格納されている
* RX72N Envision KitのSPORTS GAMESデモにおけるバンク切り替え方法
    * RX72N Envision Kit 上の SW2 を 3秒の間に3回押す
        * <a href="../../images/005_board_SW2.jpg" target="_blank"><img src="../../images/005_board_SW2.jpg" width="480px" target="_blank"></a>

# ベンチマークデモ起動
* タイトル画面
    * <a href="../../images/006_board_power_on2.jpg" target="_blank"><img src="../../images/006_board_power_on2.jpg" width="480px" target="_blank"></a>
        * 画面をタッチすると次画面に遷移
* SDカード経由ファームウェアアップデートデモ
    * <a href="../../images/007_board_sd_firmware_update.jpg" target="_blank"><img src="../../images/007_board_sd_firmware_update.jpg" width="480px" target="_blank"></a>
        * 詳細は [SDカードを用いたファームアップデート方法](../../quick-start/update-firmware-from-sd-card.md) 参照
        * ここでは「next」ボタンを押す
* シリアルターミナルデモ (以下オプション)
    * <a href="../../images/008_board_serial_terminal.jpg" target="_blank"><img src="../../images/008_board_serial_terminal.jpg" width="480px" target="_blank"></a>
        * CN8(USB Micro-B)と通信相手となるUSBポート(PC等)をUSBケーブルを用いて接続
            * <a href="../../images/009_board_serial_terminal2.jpg" target="_blank"><img src="../../images/009_board_serial_terminal2.jpg" width="480px" target="_blank"></a>
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
    * 初期ファームウェアにおいては以下コマンドに対応(順次拡張予定)
        * version : バージョン情報を読み出す
        * freertos cpuload read : FreeRTOSが保持するCPU負荷率情報を読み出す
        * freertos cpuload reset : FreeRTOSが保持するCPU負荷率情報をリセットする
    * コマンド・レスポンスの動作確認
        * <a href="../../images/011_pc_teraterm2.png" target="_blank"><img src="../../images/011_pc_teraterm2.png" width="480px" target="_blank"></a>
        * <a href="../../images/012_board_serial_terminal3.jpg" target="_blank"><img src="../../images/012_board_serial_terminal3.jpg" width="480px" target="_blank"></a>
            * 液晶にもターミナル表示と同じ内容が表示される
            * ここでは「next」ボタンを押す
* Amazon FreeRTOSデモ
    * <a href="../../images/013_board_network.jpg" target="_blank"><img src="../../images/013_board_network.jpg" width="480px" target="_blank"></a>
        * LANケーブル(インターネット接続可能なネットワークに接続されていること)をCN10(LANコネクタ)に挿しこむ
        * CN6に[USB-シリアル変換 PMODモジュール](https://store.digilentinc.com/pmod-usbuart-usb-to-uart-interface/)を接続
            * CN6は12ピン、[USB-シリアル変換 PMODモジュール](https://store.digilentinc.com/pmod-usbuart-usb-to-uart-interface/)は6ピンのため、挿し込む位置・向きに注意。CN6付近のボード上の印字の1と[USB-シリアル変換 PMODモジュール](https://store.digilentinc.com/pmod-usbuart-usb-to-uart-interface/)上の印字の1を合わせること
        * [USB-シリアル変換 PMODモジュール](https://store.digilentinc.com/pmod-usbuart-usb-to-uart-interface/)にUSBケーブルを接続し、通信相手となるUSBポート(PC等)をUSBケーブルを用いて接続 (ログ表示全文を確認したい場合)
            * Windows PC上でTeratermを立ち上げ、COMポート(COMx: USB Serial Port(COMx))を選択し接続
                * 設定 -> シリアルポート で以下設定を行う
                    * ボーレート: 912600bps
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
    * <a href="../../images/015_pc_network3.png" target="_blank"><img src="../../images/015_pc_network3.png" width="480px" target="_blank"></a>
    * <a href="../../images/014_board_network2.jpg" target="_blank"><img src="../../images/014_board_network2.jpg" width="480px" target="_blank"></a>
        * IPアドレスが取得できて、ネットワークが起動していることを確認する
        * AWS接続のためのアカウント情報がRX72N Envision Kitに記録されていないため、AWS接続不可でエラーになる
            * AWS接続実験を行うためには、ファームウェアバージョン x.x.x 以上にアップデートが必要 <開発中>
            * ファームウェアはマイクロSDカードを用いてアップデート可能
            * マイクロSDカードを用いたファームウェアアップデートの方法詳細は[SDカードを用いたファームアップデート方法](../../quick-start/update-firmware-from-sd-card.md)のページを参照
            * AWS接続実験の詳細は[AWSとFreeRTOSを用いたデモ](#)のページを参照
        * 「prev」ボタンを2回押して「SDカード経由ファームウェアアップデートデモ」に戻る
* RX72N Envision Kitのベンチマークデモにおけるバンク切り替え方法
    * RX72N Envision Kit 上の bankswap ボタンを押す
        * <a href="../../images/016_board_bankswap.jpg" target="_blank"><img src="../../images/016_board_bankswap.jpg" width="480px" target="_blank"></a>

