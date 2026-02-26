Welcome to the rx72n-envision-kit wiki!
* Following contents include Japanese only.
    * English page is here: [Home](../en/README.md)

----

# はじめに
* RX72N Envision Kit 初期ファームウェアの動作を確認することでRX72Nの性能面、機能面を確認することができます
* 性能面
    * SDHI(SD Host Interface)を用いたSDカードに対するR/W性能
    * SDカードに更新用ファームウェアを格納し、SDカードからファームウェアアップデートする際の実効性能
* 機能面
    * DRW2DやGLCDCを用いた画面表示機能
    * Segger社のemWinを用いた画面描画機能
* RX72N Envision Kitに書き込まれているファームウェアを更新することで以下性能面、機能面の確認用デモを追加することができます
    * アップデート用ファームウェア準備済
        * RX72N内蔵 Trusted Secure IPによる高度な鍵管理を有するセキュリティシステムの構築、およびその暗号実効性能
        * Amazon Web Services に更新用ファームウェアを格納し、OTAによりファームウェアアップデートする際の実効性能
        * D2 Audioチップ(ルネサス製)とMEMSマイクを用いたオーディオ活用ソリューション
    * 以下開発中
        * ESP32(Espressif製)を用いた無線LAN活用ソリューション
        * QSPI接続のシリアルフラッシュ(Macronix製)を用いた外部ストレージソリューション
* ルネサスのFreeRTOSに関する情報は以下も合わせて参照ください。
    * https://github.com/renesas/amazon-freertos

# クイックスタートガイド
1. [初期ファームウェア動作確認方法](../quick-start/confirm-factory-image-behavior.md)
1. [SDカードを用いたファームアップデート方法](../quick-start/update-firmware-from-sd-card.md)
1. [初期ファームウェアに戻す方法](../quick-start/revert-to-factory-image.md)
# 追加情報
1. [AWSとFreeRTOSを用いたOTAによるファームアップデート方法](../features/ota-via-aws-with-freertos.md)
1. [ネットワークベンチマーク](../features/network-benchmark.md)
1. [Tracealyzer使用方法](../features/how-to-use-tracealyzer.md)
1. [D2オーディオ活用](../features/d2-audio.md)
1. [MEMSマイク活用](../features/mems-mic.md)
1. [ESP32活用](../features/esp32.md)
1. [Trusted Secure IP(TSIP)によるSSLの加速](../features/ssl-acceleration-by-trusted-secure-ip-tsip.md)
1. [コマンドリスト](../features/command-list.md)
# 開発者向け
### 初期ファームウェアベース
1. [デバッグ方法](../developer/how-to-debug.md)
1. [ファームウェアをカスタムする方法](../developer/custom-firmware.md)
1. [設計メモ](../developer/design-memo.md) 
1. [トラブルシューティング](../developer/trouble-shooting.md)
### 新規プロジェクトベース(ベアメタル)
1. [新規プロジェクト作成方法(ベアメタル)](../bare-metal/generate-new-project.md)
1. [1+SCI](../bare-metal/sci.md)
1. [1+Trusted Secure IPドライバ](../bare-metal/trusted-secure-ip-driver.md)
1. [1+QSPI+シリアルフラッシュドライバ(Macronix用)](../bare-metal/qspi-serial-flash-driver.md)
1. [1+Ether+TCP/IP](../bare-metal/ether-tcp-ip.md)
1. [1+Ether+TCP/IP+Webサーバ](../bare-metal/ether-tcp-ip-web-server.md)
1. [1+SDHI+SDカードドライバ+ファイルシステム](../bare-metal/sdhi-sd-card-driver-filesystem.md)
1. [1+GLCDC+DRW2D+emWin(Segger GUIミドルウェア)](../bare-metal/glcdc-drw2d-emwin.md)
### 新規プロジェクトベース(FreeRTOS(Kernel Only))
1. [新規プロジェクト作成方法(FreeRTOS)](../freertos/generate-new-project-kernel-only.md)
1. [queueの活用 printデバッグのシリアライズ](../freertos/queue-serialization-of-print-debug.md)
### 新規プロジェクトベース(FreeRTOS(with IoT Libraries))
1. [新規プロジェクト作成方法(FreeRTOS(with IoT Libraries))](../freertos/generate-new-project-with-iot-libraries.md)

# アップデート用ファームウェア一覧
* 書き込み方法 = [SDカードを用いたファームアップデート方法](../quick-start/update-firmware-from-sd-card.md)

| ファームウェアバージョン | ダウンロード | 変更点 | ツールバージョン |
| ------------- | ------------- | ------------- | ------------- |
| v2.0.2 | <a href="https://raw.githubusercontent.com/renesas/rx72n-envision-kit/master/bin/updata/v202/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)FPSパフォーマンス表示を復活 | e2 studio 2023-01<br>cc-rx v3.04 |
| v2.0.1 | <a href="https://raw.githubusercontent.com/renesas/rx72n-envision-kit/master/bin/updata/v201/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)TracealyzerサーバのIPアドレスとポート番号登録の問題を修正 | |
| v2.0.0 | <a href="https://raw.githubusercontent.com/renesas/rx72n-envision-kit/master/bin/updata/v200/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)Amazon FreeRTOSのバージョンを202203.00に更新<br>(2)Tracealyzerのライブラリ追加<br>(3)SNTPクライアントをAWS製に交換<br>(4)emWinのライブラリを更新しAppWizardプロジェクト対応にした<br>本バージョンはファームウェアアップデート時に署名検証が失敗する場合があるため使用できません| |
| v1.0.6 | <a href="https://raw.githubusercontent.com/renesas/rx72n-envision-kit/master/bin/updata/v106/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)データフラッシュ操作の不具合を修正| |
| v1.0.5 | <a href="https://raw.githubusercontent.com/renesas/rx72n-envision-kit/master/bin/updata/v105/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)Amazon FreeRTOS system log 有効化| |
| v1.0.4 | <a href="https://raw.githubusercontent.com/renesas/rx72n-envision-kit/master/bin/updata/v104/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)TCP/IPのベンチマーク機能を追加 | |
| v1.0.3 | <a href="https://raw.githubusercontent.com/renesas/rx72n-envision-kit/master/bin/updata/v103/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)データフラッシュの全消去コマンドを追加 | |
| v1.0.2 | <a href="https://raw.githubusercontent.com/renesas/rx72n-envision-kit/master/bin/updata/v102/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)Amazon FreeRTOS OTA デモ関連の機能<br>(2)シリアルターミナル表示とシステムログ表示を削除 | |
| v1.0.1 | <a href="https://raw.githubusercontent.com/renesas/rx72n-envision-kit/master/bin/updata/v101/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)CPU負荷率表示を追加<br>(2)インターネット経由時計更新機能を追加 | |

* 右クリックでファイルを保存してください
* アップデート時にスポーツゲーム側のバンクは消去され、アップデート用ファームウェアのみインストールされます
* スポーツゲーム込みの初期ファームウェアに戻す場合は [初期ファームウェアに戻す方法](../quick-start/revert-to-factory-image.md) を参照ください

# 初期ファームウェア
* 書き込み方法 = [初期ファームウェアに戻す方法](../quick-start/revert-to-factory-image.md)

| ファームウェアバージョン | ダウンロード |
| ------------- | ------------- |
| v0.9.3 | <a href="https://raw.githubusercontent.com/renesas/rx72n-envision-kit/master/bin/factory_image/v100_20200214/userprog.mot" download="userprog.mot" >userprog.mot</a> |

* 右クリックでファイルを保存してください

# スタンドアロンのデモファームウェア
* 書き込み方法 = [初期ファームウェアに戻す方法](../quick-start/revert-to-factory-image.md)
  * 「初期ファームウェア」については、「スタンドアロンのデモファームウェア」に読み替えてください。

| デモファームウェアの名称 | ダウンロード | 解説書リンク | デモ動画 |
| ------------- | ------------- | ------------- | ------------- |
| RX72N Envision kit を用いた 音声認識・発話および LCD 表示ソリューション | <a href="https://raw.githubusercontent.com/renesas/rx72n-envision-kit/master/bin/standalone_demo_firmware_image/voice_recognition_and_lcd/rx72n_voice_demo.mot" download="rx72n_voice_demo.mot" >rx72n_voice_demo.mot</a> | [link](https://www.renesas.com/document/scd/voice-recognition-speech-and-lcd-solution-using-rx72n-envision-kit-rev100-sample-code?language=ja&r=1169186) | N/A |
| Quick-Connect IoT を活用して FreeRTOS を搭載した RX72N Envision Kit からセンサ情報を Amazon Web Services に送信する方法 | 右記リンクからサンプルコードのプロジェクトをダウンロードしビルドし生成されるMOTファイルを書き込んでください | [link](https://www.renesas.com/document/scd/rx72n-group-using-quick-connect-iot-send-sensor-information-amazon-web-services-rx72n-envision-kit?language=ja&r=1169186)  | 作成中 |

* 右クリックでファイルを保存してください
* その他、RX72N Envision Kitで動作するサンプルコードは以下製品ページの「ドキュメント」の欄にもあります
  * https://www.renesas.com/products/microcontrollers-microprocessors/rx-32-bit-performance-efficiency-mcus/rx72n-envision-kit-rx72n-envision-kit
