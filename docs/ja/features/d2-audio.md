# 工事中

# 準備する物
* 必須
  * RX72N Envision Kit × 1台
  * USBケーブル(USB Micro-B --- USB Type A) × 1 本
  * Windows PC × 1 台
    * Windows PC にインストールするツール
      * e2 studio 2020-07以降
        * 初回起動時に時間がかかることがある
          * CC-RX V3.02以降
  * スピーカ、ヘッドフォン、イヤホンのいずれか × 1 個
    * アンプ付きを推奨（参考：[RX72N Envision Kit マニュアル](https://www.renesas.com/doc/products/mpumcu/doc/rx_family/001/r20ut4788jj0100-rx72n.pdf?key=c3e0927448cedaa6fa41636c92e39bac) 5.15.1章）
* 参考
  * [SSI モジュールを使用するPCM データ転送サンプルプログラム Firmware Integration Technology（R01AN2825）](https://www.renesas.com/software/D4800301.html)
    * 本稿は上記サンプルプログラム「rx72n_example_ssi_rx」のアレンジ版である
  * [RX72N Envision Kit マニュアル](https://www.renesas.com/doc/products/mpumcu/doc/rx_family/001/r20ut4788jj0100-rx72n.pdf?key=c3e0927448cedaa6fa41636c92e39bac)
  * D2 Audio マニュアル
    * データシート：[d2-41051-151.pdf](https://www.renesas.com/products/audio-video/audio/digital-sound-processors/device/D2-41051.html#documents)
    * APIレジスタ仕様書：[r32an0004eu-d2-4-d2-4p.pdf](https://www.renesas.com/products/audio-video/audio/digital-sound-processors/device/D2-41051.html#documents)
  * MEMSマイク マニュアル
    * データシート：[DS-000069-ICS-43434-v1.2.pdf](https://invensense.tdk.com/products/ics-43434/)

# 前提条件
* ファームウェアバージョンv1.0.4以降がインストールされていること
    * 書き込み方法 = [SDカードを用いたファームアップデート方法](../quick-start/update-firmware-from-sd-card.md)
* コマンドレスポンスの動作確認ができていること
    * 以下ページの シリアルターミナルデモ 参照
        * [初期ファームウェア動作確認方法](../quick-start/confirm-factory-image-behavior.md)

# 工事中

# SSI（シリアルサウンドインタフェース）について
* 音声データを転送するためにSSIを利用する
* RX72Nは2チャネルのSSIE（拡張シリアルサウンドインタフェース、SSIでないことに注意）を内蔵している
* SSIEのブロック図は下図のとおり
  * <a href="../../images/.png" target="_blank"><img src="../../images/.png" width="480px" target="_blank"></a>

  * AUDIO_CLK
    * クロックソース
    * RX72N Envision Kitではクロックジェネレータ(5X34023)から供給され、**_AUDIO_CLK = 24.576MHz_** である
  * MCK
    * マスタクロック
    * 厳密には異なるが、クロックソース（AUDIO_CLK）と捉えてOK
  * BCK
    * ビットクロック（Bit Clock）
    * BCKを基準にSSI通信が実施される
  * CKDV
    * ビットクロック分周比（以降の説明では、d と表現している）
    * レジスタはSSIE.SSICR.CKDV
    * BCKはAUDIO_CLKをd分周したものなので、**_BCK  = AUDIO_CLK / d_**

* SSIEは以下のフォーマット（転送する音声データの並びの型）に対応している
  * I2Sフォーマット
  * 左詰めフォーマット
  * 右詰めフォーマット
  * モノラルフォーマット
  * TDMフォーマット
* D2 AudioはI2Sフォーマットで音声データを転送する
  * I2Sのフォーマットは下図のとおり
    * <a href="../../images/.png" target="_blank"><img src="../../images/.png" width="480px" target="_blank"></a>
    * ワード長
      * BCKの1クロック分の周期が1ワード長の転送に必要な周期なので、以降の説明では1ワード長をBCKの1クロック分の周期として扱っている
    * システムワード長（以降の説明では、wSys と表現している）
      * レジスタはSSIE.SSICR.SWL
      * パディングビットのビット数は、システムワード長とデータワード長の差で求まる
    * LまたはRチャネルのワード長（以降の説明では、wLR と表現している）
      * 1サンプルにおけるLまたはRチャネルの音声データの区間
      * **I2Sフォーマットの場合**、1wLR = 1wSys
    * 1サンプル（フレーム）のワード長（以降の説明では、wSample と表現している）
      * 1サンプルにおける音声データの区間
      * I2Sフォーマットの場合、1wSample = 2wLR なので、**_1wSample = 2wSys_**

# SSI FITモジュール設定の解説
* 以下の3値をもとにSSI FITモジュールの設定を施す
  * クロックソース周波数（AUDIO_CLK）
  * サンプリング周波数（fs）
  * システムワード長（wSys）
* クロックの設定は、設定項目ごとに単位が異なり分かりにくいので注意
  * <a href="../../images/.png" target="_blank"><img src="../../images/.png" width="480px" target="_blank"></a>
* 以下は設定すべき内容である
  * Chx PCM data width
    * チャネルにおける1サンプルにおける量子化ビット数を指定する
      * データワード長（SSIE.SSICR.DWL）と考えてもOK
  * Chx Bit Clock
    * チャネルにおけるBit Clockの**周波数**を指定する（単位はHz）
    * **I2Sフォーマットの場合は、** **_2wSys * fs_** の値を指定する
      * Bit Clock周波数は下記のいずれかから導き出せる
        * クロックソースとビットクロック分周比
        * **システムワード長とサンプリング周波数**
          * 1サンプルにおいてBit Clockのクロック回数が何回あるか？と考えればイメージしやすい
            * I2Sフォーマットの図から、1つのサンプル周期内で2wSys回のクロックが存在することがわかる（1wSample = 2wSys）
            * 言い換えると、サンプリング周波数の2wSys倍がBit Clock周波数である（BCK = 2wSys * fs）
            * 上述のとおり、この設定項目はBCKなので、{Bit Clock} = BCK → {Bit Clock} = 2wSys * fs である
  * Master Clock
    * サンプリング周期(1サンプルの時間間隔)内の Master Clockの**クロック回数**を指定する（単位は、クロック回数）
    * **_AUDIO_CLK / fs_** の値を指定する
      * サンプリング周期内の Master Clockのクロック回数とは、<br>Master Clock(AUDIO_CLK)にサンプリング周期（1 / fs）を掛けた値なので、<br>{Master Clock} = AUDIO_CLK * (1 / fs) → {Master Clock} = AUDIO_CLK / fs である
        * fs = AUDIO_CLK / {Master Clock} とも式変形できる


