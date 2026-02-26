# <a name="purpose"></a>目的
* 液晶ディスプレイを介した対話的なGUIアプリケーションの作成方法を紹介する
  1. [QE for Display[RX]](https://www.renesas.com/products/software-tools/tools/solution-toolkit/qe-qe-for-display.html)を使用して下記のドライバやソフトウェアの組み込み/設定を行う
       > 組み込み/設定方法はQE for Display[RX]の[アプリケーションノート（R20AN0582xxxxxx）](https://www.renesas.com/jp/ja/software/D4800348.html)も参照のこと
  2. RX72Nマイコン周辺機能のグラフィックLCD コントローラ(GLCDC)や2D 描画エンジン(DRW2D)、
及び、SEGGER社の[emWin](https://www.segger.com/products/user-interface/emwin/)ソフトを使用し、液晶ディスプレイに文字や図形を表示する
  3. GUIデザインツール[AppWizard](https://www.segger.com/products/user-interface/emwin/tools/tools-overview/#AppWizard)を使用し、液晶ディスプレイに対話的なGUIを設置する
  4. 液晶ディスプレイへ表示させたボタンのタッチ操作によってLEDの点灯を制御する

# <a name="things_to_prepare"></a>準備するもの
* 必須
  * RX72N Envision Kit × 1台
  * USBケーブル(USB Micro-B --- USB Type A) × 1 本
  * Windows PC × 1 台
    * Windows PC にインストールするツール
      * e2 studio 2020-07以降
        * 初回起動時に時間がかかることがある
          * CC-RX V3.02以降

# <a name="prerequisites"></a>前提条件
 * [新規プロジェクト作成方法(ベアメタル)](../bare-metal/generate-new-project.md)を完了すること
   * 本稿では、[新規プロジェクト作成方法(ベアメタル)](../bare-metal/generate-new-project.md)で作成したLED0.1秒周期点滅プログラムに対し、以下の内容を追加する形で実装する
      1. QE for Displayを活用し、GLCDドライバ、DRW2Dドライバ、emWinを手軽に組み込み/設定
      2. AppWizardを使用してGUIを設置
      3. GUIを制御するコードを追加
  * 最新の[RX Driver Package](https://www.renesas.com/products/software-tools/software-os-middleware-driver/software-package/rx-driver-package.html)(FITモジュール)を使用すること


# <a name="preparation"></a>QE for Display使用のための事前準備
* 初回のみ実施
  * [インストール方法](https://www.renesas.com/software/D4001360.html)に従ってQE for Displayをダウンロード/インストールする
  * [DRW2D FITモジュール](https://github.com/renesas/rx-driver-package/tree/master/FITModules)、及び、[emWin FITモジュール](https://www.renesas.com/software/D4800346.html)をダウンロードし、[FITモジュールの保存先フォルダ](https://github.com/renesas/rx72n-envision-kit/wiki/%E3%82%B9%E3%83%9E%E3%83%BC%E3%83%88%E3%83%BB%E3%82%B3%E3%83%B3%E3%83%95%E3%82%A3%E3%82%B0%E3%83%AC%E3%83%BC%E3%82%BF%E3%81%AE%E4%BD%BF%E7%94%A8%E6%96%B9%E6%B3%95#stored_fit_folder)に配置する
    > DRW2D FITモジュール、及び、emWin FITモジュールはRX Driver Package V1.26時点には同梱されていないため

# <a name="circuit"></a>回路確認
* LCDに関連する回路を以下のとおり確認する
## LCDグラフィックLCDコントローラ(GLCDC)
* RX72N Envision Kitには4.3インチWQVGA TFT-LCDが実装されている
  * 出力データフォーマットはRGB565形式（パラレル16ビット）
    * RGB565とは、RとBがそれぞれ5bit、Gが6bitの計16bit（65,536色）で色を表現する形式
      * ちなみに、GがRやBに比べて1bit分大きい理由は、緑色が人間の目に最も反応しやすいため
  * RGB565の場合、LCDにデータを出力する端子（LCD信号出力端子）はLCD_DATA15～LCD_DATA0の16bitバス
    > RX72N [ハードウェアマニュアル（R01UH0824xxxxxx）](https://www.renesas.com/search/keyword-search.html#q=R01UH0824)の51.1.5章 (3)を参照
    * LCD信号出力端子のそれぞれが出力する色を事前確認することが必要
      * GLCDCのB/R入れ替え機能を使用することでピクセル配列順序を切り替えることができる
        > RX72N [ハードウェアマニュアル（R01UH0824xxxxxx）](https://www.renesas.com/document/man/rx72n-group-users-manual-hardware)の51.1.5章 (3) パラレルRGB(565) フォーマットにおけるLCD信号のビット配置 を参照のこと）

        | LCDのData端子 | R-G-Bのピクセル配列の場合 | B-G-Rのピクセル配列の場合 |
        | ---- | ---- | ---- |
        | LCD_DATA_11~LCD_DATA_15 | Rのカラーデータ出力端子 | Bのカラーデータ出力端子 |
        | LCD_DATA_0~LCD_DATA_4   | Bのカラーデータ出力端子 | Rのカラーデータ出力端子 |
      * B/R入れ替え機能を必要に応じて使用しない場合、本来意図どおりに発色されないので注意
        * 例えば、RX65N(2MB) RSK+の場合、RX65N [マニュアル](https://www.renesas.com/document/man/rx65n-group-rx651-group-users-manualhardware)と[RSK+ユーザズマニュアル](https://www.renesas.com/document/man/renesas-starter-kit-rx65n-2mb-users-manual)、[TFTの回路図](https://www.renesas.com/document/man/renesas-starter-kit-rx65n-2mb-cpu-board-schematics)の情報を総合すると、R用のLCD信号出力端子がB用のTFT（HX8257-A）端子に、B用のLCD信号出力端子がR用のTFT端子につながっている（RX72N Envision Kitとは逆）
          * この時、B/R入れ替え機能を使用しピクセル配列順序を切り替えて、発色を調整する必要がある
  * その他、パネルクロック出力端子（LCD_CLK）や同期信号出力端子（LCD_TCON3～LCD_TCON0）を使用
    > RX72N [ハードウェアマニュアル（R01UH0824xxxxxx）](https://www.renesas.com/search/keyword-search.html#q=R01UH0824)の51.1章 表51.2を参照
  * <a href="../../images/096_circuit_glcdc.png" target="_blank"><img src="../../images/096_circuit_glcdc.png" width="480px" target="_blank"></a>

## 静電容量方式タッチコントローラ
* 静電容量方式タッチコントローラ（FT5260）がRX72N Envision Kitに実装されている
* RX72NマイコンはI2Cシリアルインタフェースにて静電容量方式タッチコントローラとデータ通信を行い、<br>コントローラの動作を制御する
  * <a href="../../images/083_circuit_touch.png" target="_blank"><img src="../../images/083_circuit_touch.png" width="480px" target="_blank"></a>

# BDF確認
* プロジェクトにBDF`EnvisionRX72N`が適用されていることを確認する
  * [スマート・コンフィグレータの使い方#ボード設定](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#board_setting)を参照
  * 適用されていない場合、上記リンク先に対処法が記載

# QE for Displayによるドライバソフトウェア/ミドルソフトウェアの設定
## 適用先プロジェクトの設定
* `Renesas Views` -> `Renesas QE` -> `LCD メイン RX (QE)`を実行しQE for Displayを開く
* QE for Displayの`プロジェクトの選択`のプルダウンメニューからQE for Displayを適用するプロジェクト`rx72n_envision_kit`を選択する
* 選択後、`評価ボード`が`EnvisionRX72N (V.x.xx)`になることを確認する
  * プロジェクトにBDF`EnvisionRX72N`が適用されているため、`プロジェクトの選択`でプロジェクトを選択した際に`評価ボード`が自動で切り替わる
* `GUI描画ツールの選択`で`emWinを使用する`を選択する
* <a href="../../images/084_qe_main1.png" target="_blank"><img src="../../images/084_qe_main1.png" width="480px" target="_blank"></a>

## LCDコントローラの設定
* LCDコントローラの設定方法を以下に記載する
  * スマート・コンフィグレータ（SC）を使用してLCDコントローラ（GLCDC FITモジュール）をプロジェクトに導入する
    * SCを開き、`r_glcdc_rx`を[コンポーネント追加](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#add_component)する
      * FITモジュールの依存関係でエラーになる場合は、各種FITモジュールのバージョンが適切でない可能性がある
        * エラー内容に従って各種FITモジュールの[バージョンを変更](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#change_component_version)すること
    * SCの[コード生成](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#code_generation)を一旦実行する
  * `LCD メイン RX (QE)` -> `LCDコントローラの導入` -> `導入済み`になっていることを確認する
  * `LCD メイン RX (QE)` -> `LCDの表示調整` -> `表示タイミング調整`LCDコントローラの設定を実施する
    * デフォルトの`タイミング設定`ではエラーが発生しているので、エラーを解消する
      * <a href="../../images/093_qe_lcd_error.png" target="_blank"><img src="../../images/093_qe_lcd_error.png" width="480px" target="_blank"></a>
      
      * `リフレッシュレート[Hz]`と`水平周波数[kHz]`がそれぞれ設定可能な値を満たし、かつ、`差分`が`0.0`になるように設定する（以下は例）
        * `PLL回路周波数[MHz]`：`240`
          * PLL回路周波数をSCの[クロック設定](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#clock_setting)と同値に変更する
            * ★将来改善★ SCのクロック設定から値を自動的に取得するように改善する見込み
        * `パネルクロック周波数[MHz]`：`10.000000`
          * パネルクロック周波数はPCLKA未満の値に設定する
        * `HPW`：`30`
        * `HBP`：`54`
        * `HFP`：`20`
        * <a href="../../images/087_qe_lcd.png" target="_blank"><img src="../../images/087_qe_lcd.png" width="480px" target="_blank"></a>
    * QE for Displayを使用する場合、r_glcdc_rxに関するSCの[コンポーネント設定](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#component_setting)は**不要**
  * LCDコントローラの設定ファイルを**QE for Displayから**生成する
     * `LCD メイン RX (QE)` -> `LCDの表示調整` -> `ファイル出力`を実行
       * デフォルトの出力先は`.\rx72n_envision_kit\src`直下である
       * `フォルダ指定`をチェックして`ファイル出力`を実行すると、出力先を選択可能
       * ただし、`.\rx72n_envision_kit\src\smc_gen`配下は避ける
         * 出力されたファイルがSCの[コード生成](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#code_generation)によって削除される恐れがあるため
     * <a href="../../images/085_qe_main2.png" target="_blank"><img src="../../images/085_qe_main2.png" width="480px" target="_blank"></a>
* 導入方法の詳細は`LCD メイン RX (QE)` -> `LCDコントローラの導入` -> `導入方法`を参照

## GUI描画ツールの設定
* GUI描画ツールの設定方法を以下に記載する
  * SCを使用してGUI描画ツール（emWin FITモジュール）をプロジェクトに導入する
    * SCを開き、`r_emwin_rx`を[コンポーネント追加](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#add_component)する
      * SCの機能により、emWin FITと依存関係をもつ以下のFITモジュールも自動でプロジェクトに追加される
        * r_cmt_rx
        * r_dmaca_rx
        * r_drw2d_rx
        * r_glcdc_rx
        * r_gpio_rx
        * r_sci_iic_rx
      * FITモジュールの依存関係でエラーになる場合は、各種FITモジュールのバージョンが適切でない可能性がある
        * エラー内容に従って各種FITモジュールの[バージョンを変更](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#change_component_version)すること
    * SCの[コード生成](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#code_generation)を一旦実行する
  * `LCD メイン RX (QE)` -> `GUI描画ツールの導入` -> `導入済み`になっていることを確認する
  * emWinの設定を実施する
    * `フレームバッファ2アドレス`：`0x00840000`
        * 本稿では[新規プロジェクト作成方法](https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95)からセクション設定を変更しないので、上記の値でよい
        * ただし、このバッファアドレスがセクションのアドレスと重複している場合は、セクションのアドレスを変更する
    * `GUIで使用する最大メモリサイズ`：`81920`
    * `IICで使用するチャネル`：`6`
    * `DRW2Dの使用`：`使用する`
    * <a href="../../images/088_qe_emwin.png" target="_blank"><img src="../../images/088_qe_emwin.png" width="480px" target="_blank"></a>
    * QE for Displayを使用する場合、r_emwin_rxに関するSCの[コンポーネント設定](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#component_setting)は**不要**
  * emWinの設定ファイルを**QE for Displayから**生成する
     * `LCD メイン RX (QE)` -> `GUI描画ツールの初期設定` -> `ファイル出力`を実行
       * デフォルトの出力先は`.\rx72n_envision_kit\src`直下である
       * `フォルダ指定`をチェックして`ファイル出力`を実行すると、出力先を選択可能
       * ただし、`.\rx72n_envision_kit\src\smc_gen`配下は避ける
         * 出力されたファイルがSCの[コード生成](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#code_generation)によって削除される恐れがあるため
     * <a href="../../images/086_qe_main3.png" target="_blank"><img src="../../images/086_qe_main3.png" width="480px" target="_blank"></a>
* 導入方法の詳細は`LCD メイン RX (QE)` -> `GUI描画ツールの導入` -> `導入方法`を参照

# スマート・コンフィグレータ(SC)によるドライバソフトウェア/ミドルソフトウェアの設定
## コンポーネント追加
* QE for Displayにて必要なコンポーネントは追加済みなので、操作不要

## コンポーネント設定
* QE for Displayでの設定にてカバーされないコンポーネントに対し、設定を施す
### r_bsp
  * `Heap size`：`0x4000`
    * BSP FITモジュールで定義されているデフォルトの`Heap size`の値はGUI描画には不十分なサイズなので、サイズをより大きく取る
    * `Heap size`は`LCD メイン RX (QE)` -> `GUI描画ツールの設定` -> `GUIで使用する最大メモリサイズ`の値より大きく取る
    * <a href="../../images/089_emwin_bsp.png" target="_blank"><img src="../../images/089_emwin_bsp.png" width="480px" target="_blank"></a>
### r_cmt_rx
  * デフォルトで問題なし
### r_dmaca_rx
  * デフォルトで問題なし
### r_drw2d_rx
  * 無し
### r_glcdc_rx
  * QE for Displayにて設定するので操作不要
### r_gpio_rx
  * デフォルトで問題なし
### r_sci_iic_rx
  * `MCU supported channels for CH6`：`Supported`
  * `SCI6` -> `SSCL6端子`：`使用する`
  * `SCI6` -> `SSDA6端子`：`使用する`
  * <a href="../../images/090_emwin_iic1.png" target="_blank"><img src="../../images/090_emwin_iic1.png" width="480px" target="_blank"></a>
  * <a href="../../images/091_emwin_iic2.png" target="_blank"><img src="../../images/091_emwin_iic2.png" width="480px" target="_blank"></a>
### r_emwin_rx
  * QE for Displayにて設定するので操作不要

## 端子設定
* RX72N マイコンは、1個の端子に複数機能が割り当たっているため、どの機能を使用するかの設定をソフトウェアにより施す必要がある
* RX72N Envision KitのBDFを使用している場合、すでに端子を設定済みであるため、作業不要
* <a href="../../images/092_emwin_pin_iic.png" target="_blank"><img src="../../images/092_emwin_pin_iic.png" width="480px" target="_blank"></a>

## コード生成
* 上記の設定をすべて完了後、SCの[コード生成](https://github.com/renesas/rx72n-envision-kit/wiki/スマート・コンフィグレータの使用方法#code_generation)を実行する

# AppWizardによるGUIオブジェクトの設置
## <a name="appwizard_install"></a>AppWizardのインストール
* 初回のみ実施
* `LCD メイン RX (QE)` -> `GUIの作成` -> `設定`を押し、`AppWizardの設定`ウィンドウを表示する
* `AppWizardはインストールされていません`と表示されている場合、<br>`AppWizardインストールフォルダ`にインストールしたいファイルパスを入力 -> <br>`AppWizaradをインストールする`を押す
* <a href="../../images/094_appwizard_install.png" target="_blank"><img src="../../images/094_appwizard_install.png" width="480px" target="_blank"></a>
* インストールウィザードが表示されるので、画面内容に従ってAppWizardをインストールする
* `AppWizardの設定`ウィンドウを閉じる
## AppWizardの設定
* `LCD メイン RX (QE)` -> `GUIの作成` -> `設定`を押し、`AppWizardの設定`ウィンドウを表示する
* `AppWizardはインストールされています`と表示されている場合、`OK`を押す
  * <a href="../../images/095_appwizard_ok.png" target="_blank"><img src="../../images/095_appwizard_ok.png" width="480px" target="_blank"></a>
* `AppWizardはインストールされていません`と表示されている場合、以下のどちらかの対応を行う
  * `AppWizardインストールフォルダ`にAppWizardがインストールされているファイルパスを入力する -> <br>`AppWizardはインストールされています`に表示が変われば`OK`を押す
  * [AppWizardのインストール](#appwizard_install)を実施する
## GUIオブジェクトの設置
### AppWizardの起動
* `LCD メイン RX (QE)` -> `GUIの作成` -> `GUI描画ツール起動`を押し、AppWizardを起動する
* AppWizardの起動後、e2 studioのプロジェクトツリーから`./aw/Resource`と`./aw/Source`が作成されることを確認する
### 画面設計
* AppWizardの画面設計の基本的な流れは以下のとおり
  1. `Resource`(`Text`, `Fonts`, `Images`, `Variables`)を登録する
  2. GUIオブジェクトを配置/設定する
     1. `Add objects`ペインから配置したいオブジェクトを選択する
     2. `Hierarchic tree`ペインに選択したオブジェクトが追加されたことを確認する
     3. `Hierarchic tree`ペインでオブジェクトの階層を変更する
     4. `Hierarchic tree`ペインでオブジェクトの位置や大きさを変更する
     5. `Properties`ペインでオブジェクトのプロパティを変更する
  3. `Interactions`ペインでオブジェクトのイベント及びイベントハンドラ（Slot）を登録する
  4.  `File` -> `Export & Save`を実行し、ソースコードを出力する
     * <a href="../../images/097_appwizard_flow.png" target="_blank"><img src="../../images/097_appwizard_flow.png" width="480px" target="_blank"></a>
* `Hierarchic tree`のトップにはオブジェクト`Screen`を必ず配置すること

#### `Resource` 登録
##### <a name="text_definition"></a>`Text` リソース
* [Text リソースの登録方法](#text_resource)に従って`ID_TEXT_LED_SWITCH_TXT`と`ID_TEXT_OFF_TXT`を作成する
  * `Id`："ID_TEXT_LED_SWITCH_TXT"、`English`："LED Switch"
  * `Id`："ID_TEXT_OFF_TXT"、`English`："OFF"

#### GUIオブジェクト配置/設定
##### `Screen` オブジェクト
* まず最初にオブジェクト`Screen`を配置する
  * `Add objects` -> `Screen`を選択する
  * `Hierarchic tree`のトップにオブジェクト`Screen`が追加されたことを確認する
  * `Editor`にオブジェクト`Screen`が追加されたことを確認する
  * `Properties`を変更する
    * `Id`："ID_SCREEN_00"
  * <a href="../../images/098_appwizard_screen.png" target="_blank"><img src="../../images/098_appwizard_screen.png" width="480px" target="_blank"></a>

##### `Box` オブジェクト
* 背景用にオブジェクト`Box`を画面一杯に配置する
  * `Add objects` -> `Box`を選択する
  * `Hierarchic tree`で`ID_SCREEN_00`の下にオブジェクト`Box`が追加されたことを確認する
  * `Editor`にオブジェクト`Box`が追加されたことを確認する
    * サイズは変更しない（フルサイズとする）
  * `Properties`を変更する
    * `Id`："ID_BOX_00"
    * `Set color`で長方形のエリアを押し、色選択画面を表示する -> <br>背景にしたい色を選択する（RGBA = (75, 75, 75, 255)）-> `OK`
  * <a href="../../images/099_appwizard_box.png" target="_blank"><img src="../../images/099_appwizard_box.png" width="480px" target="_blank"></a>

##### `Switch` オブジェクト
* LEDのスイッチ用にオブジェクト`Switch`を配置する
  * `Add objects` -> `Switch`を選択する
  * `Hierarchic tree`で`ID_BOX_00`の下にオブジェクト`Switch`が追加されたことを確認する
  * `Editor`にオブジェクト`Switch`が追加されたことを確認する
  * `Editor`上のオブジェクト`Switch`の大きさを変更する
    * `Properties` -> `Size`：`150`, `50`
  * `Editor`上のオブジェクト`Switch`をドラッグアンドドロップし、画面の真ん中に移動させる
    * `Properties` -> `Position`：`165`, `111`
  * `Properties`を変更する
    * `Id`："ID_SWITCH_00"
    * `Set Bitmaps` -> `BG-Left`： `Left_80x30.png` -> `Select`
    * `Set Bitmaps` -> `BG-Right`： `Right_80x30.png` -> `Select`
    * `Set Bitmaps` -> `BG-Disabled`： `Disabled_80x30.png` -> `Select`
    * `Set Bitmaps` -> `Thumb-Left`： `ThumbLeft_80x30.png` -> `Select`
    * `Set Bitmaps` -> `Thumb-Right`： `ThumbRight_80x30.png` -> `Select`
    * `Set Bitmaps` -> `Thumb-Disabled`： `Disabled_80x30.png` -> `Select`
  * <a href="../../images/100_appwizard_switch.png" target="_blank"><img src="../../images/100_appwizard_switch.png" width="480px" target="_blank"></a>

##### `Text` オブジェクト
* スイッチの用途を示す文字用のオブジェクト`Text`を配置する
  * `Add objects` -> `Text`を選択する
  * `Hierarchic tree`で`ID_SWITCH_00`の下にオブジェクト`Text`が追加されたことを確認する
  * `Editor`にオブジェクト`Text`が追加されたことを確認する
  * `Editor`上のオブジェクト`Text`の大きさを変更する
    * `Properties` -> `Size`：`150`, `32`
  * `Editor`上のオブジェクト`Text`をドラッグアンドドロップし、<br>オブジェクト`ID_SWITCH_00`の真上に移動させる
    * `Properties` -> `Position`：`165`, `79`
  * `Properties`を変更する
    * `Id`："ID_TEXT_LED_SWITCH"
    * `Set text color`：RGBA = (255, 255, 255, 255) -> `OK`
    * `Set text alignment`：Center
    * `Set font`： `NettoOT_24_Normal_EXT_AA4` -> `Select`
  * <a href="../../images/101_appwizard_text1.png" target="_blank"><img src="../../images/101_appwizard_text1.png" width="480px" target="_blank"></a>
* スイッチ状態に合わせてLED状態を示す文字用のオブジェクト`Text`を配置する
  * `Add objects` -> `Text`を選択する
  * `Hierarchic tree`で`ID_TEXT_LED_SWITCH`の下にオブジェクト`Text`が追加されたことを確認する
  * `Editor`にオブジェクト`Text`が追加されたことを確認する
  * `Editor`上のオブジェクト`Text`の大きさを変更する
    * `Properties` -> `Size`：`150`, `32`
  * `Editor`上のオブジェクト`Text`をドラッグアンドドロップし、<br>オブジェクト`ID_SWITCH_00`の真下に移動させる
    * `Properties` -> `Position`：`165`, `159`
  * `Properties`を変更する
    * `Id`："ID_TEXT_LED_STATE"
    * `Set text alignment`：Center
    * `Set font`： `NettoOT_24_Normal_EXT_AA4` -> `Select`
  * <a href="../../images/102_appwizard_text2.png" target="_blank"><img src="../../images/102_appwizard_text2.png" width="480px" target="_blank"></a>
* LEDの初期状態を示す文字用のオブジェクト`Text`を配置する
  * `Hierarchic tree`の`ID_TEXT_LED_STATE`を右クリックし、`Copy`を選択する
  * `Hierarchic tree`で右クリックし、`Paste`を選択する
  * `Hierarchic tree`で`ID_TEXT_LED_STATE`の下にオブジェクト`ID_TEXT_LED_COPY`が追加されたことを確認する
  * `Properties`を変更する
    * `Id`："ID_TEXT_LED_STATE_INIT"
    * `Set text`：`ID_TEXT_OFF_TXT` -> `Select`
    * `Set text color`：RGBA = (80, 80, 80, 255) -> `OK`
    * `Set background color`：RGBA = (255, 255, 255, 255) -> `OK`
    * 他のプロパティは`ID_TEXT_LED_STATE`と同じ
  * <a href="../../images/103_appwizard_text3.png" target="_blank"><img src="../../images/103_appwizard_text3.png" width="480px" target="_blank"></a>

#### イベント登録
* スイッチ状態に合わせてLED状態の文字を表示させるためのイベントを登録する
  * `Interactions` -> `+`を押す
    * `Emitter`(イベント発生元)：`ID_SWITCH_00`
    * `Signal`(イベント種類)：`VALUE_CHANGED`(値の変化のイベント)
    * `Job`(イベント発生によって連動するタスク)：`SETVIS`(オブジェクトの表示/非表示を設定)
    * `Receiver`(連動するタスクの宛先)：`ID_TEXT_LED_STATE`
  * ポップアップされる`Set interaction parameters`ウィンドウ -> `Use custom defined value`を押す
    * `Set visibility`：`On`
    * `Slot`：`ID_SCREEN_00__ID_SWITCH_00__WM_NOTIFICATION_VALUE_CHANGED__ID_TEXT_LED_STATE__APPW_JOB_SETVIS`
    * `Edit code`：AppWizard設定と出力されるソースコードは連動できるため、AppWizardの[ソースコード出力](#code_generation_appwizard)後に[編集](#code)する
  * <a href="../../images/104_appwizard_interaction1.png" target="_blank"><img src="../../images/104_appwizard_interaction1.png" width="480px" target="_blank"></a>
* 初期値のスイッチ状態の文字を非表示させるためのイベントを登録する
  * `Interactions` -> `+`を押す
    * `Emitter`(イベント発生元)：`ID_SWITCH_00`
    * `Signal`(イベント種類)：`VALUE_CHANGED`(値の変化のイベント)
    * `Job`(イベント発生によって連動するタスク)：`SETVIS`(オブジェクトの表示/非表示を設定)
    * `Receiver`(連動するタスクの宛先)：`ID_TEXT_LED_STATE_INIT`
  * ポップアップされる`Set interaction parameters`ウィンドウ -> `Use custom defined value`を押す
    * `Set visibility`：`Off`
    * `Slot`：`ID_SCREEN_00__ID_SWITCH_00__WM_NOTIFICATION_VALUE_CHANGED__ID_TEXT_LED_STATE_INIT__APPW_JOB_SETVIS`
    * `Edit code`：編集しない
  * <a href="../../images/105_appwizard_interaction2.png" target="_blank"><img src="../../images/105_appwizard_interaction2.png" width="480px" target="_blank"></a>

#### GUIオブジェクトのプレビュー
* `Editor`ペインの再生マークを押し、配置したオブジェクトのプレビューができる
  * 本稿では以下の状況をプレビューできればよい
    * 初期状態で、画面真ん中にスイッチのトグルが左側にある
    * 初期状態で、スイッチの真上に白色で"LED Switch"の表示がある
    * 初期状態で、スイッチの真上に白色で"LED Switch"の文字表示がある
    * 初期状態で、スイッチの真下に白色の四角があり、その中に灰色で"OFF"の文字表示がある
    * スイッチをクリックすると、スイッチのトグルが右側に移動し、<br>スイッチ真下の四角と文字表示が消える
      * トグル移動後、スイッチ真下の四角と文字表示（`ID_TEXT_LED_STATE_INIT`）が消えるのは意図どおりの動作
      * トグル移動後、`ID_TEXT_LED_STATE`はスイッチ真下に表示されているはずだが、文字表示はユーザソースコードで変化させるため、見た目上は何もない
    * スイッチをさらにクリックすると、スイッチのトグルが左側に移動する
* <a href="../../images/106_appwizard_preview.png" target="_blank"><img src="../../images/106_appwizard_preview.png" width="480px" target="_blank"></a>

#### <a name="code_generation_appwizard"></a>GUIオブジェクトのソースコード出力
* `File` -> `Export & Save`を実行する
* `./aw/Source`配下にソースコード（特に注目すべきは以下）が出力されたことを確認する
  * Resource.h：AppWizardの`Resource`(Text, Fonts, Images, Variables)に関わる
  * ID_SCREEN_00.h：オブジェクト`ID_SCREEN_00`とその中に配置されたオブジェクトに関わる
  * ID_SCREEN_00_Slots.c：オブジェクト`ID_SCREEN_00`とその中に配置されたオブジェクトのSlotに関わる
  * APPW_MainTask.c：AppWizardで作成したGUIオブジェクトの初期化/実行に関わる

# <a name="code"></a>ユーザアプリケーション部のコーディング
## ソースコード全体
* `rx72n_envision_kit.c`のソースコード全体を以下に記載する（説明は後述）
```rx72n_envision_kit.c
#include "GUI.h"

void main(void);

void main (void)
{
    /* The follow function is generated by the AppWizard. */
    MainTask();
}
```
* `ID_SCREEN_00_Slots.c`のソースコード全体を以下に記載する（説明は後述）
```ID_SCREEN_00_Slots.c
#include "Application.h"
#include "../Generated/Resource.h"
#include "../Generated/ID_SCREEN_00.h"

/*********************************************************************
*
*       Public code
*
**********************************************************************
*/
/*********************************************************************
*
*       cbID_SCREEN_00
*/
void cbID_SCREEN_00(WM_MESSAGE * pMsg) {
  GUI_USE_PARA(pMsg);
}

/*********************************************************************
*
*       ID_SCREEN_00__ID_SWITCH_00__WM_NOTIFICATION_VALUE_CHANGED__ID_TEXT_LED_STATE__APPW_JOB_SETVIS
*/
void ID_SCREEN_00__ID_SWITCH_00__WM_NOTIFICATION_VALUE_CHANGED__ID_TEXT_LED_STATE__APPW_JOB_SETVIS(APPW_ACTION_ITEM * pAction, WM_HWIN hScreen, WM_MESSAGE * pMsg, int * pResult) {
    GUI_USE_PARA(pAction);
    GUI_USE_PARA(hScreen);
    GUI_USE_PARA(pMsg);
    GUI_USE_PARA(pResult);

    int result = 0;
    /* Returns the state of a SWITCH widget. */
    result = SWITCH_GetState(pMsg->hWinSrc);
    if(SWITCH_STATE_RIGHT == result)
    {
        process_switch_on(pMsg->hWin);
    }
    else if(SWITCH_STATE_LEFT == result)
    {
        process_switch_off(pMsg->hWin);
    }
    else
    {
        process_switch_error(pMsg->hWin);
    }
}

/*********************************************************************
*
*       ID_SCREEN_00__ID_SWITCH_00__WM_NOTIFICATION_VALUE_CHANGED__ID_TEXT_LED_STATE_INIT__APPW_JOB_SETVIS
*/
void ID_SCREEN_00__ID_SWITCH_00__WM_NOTIFICATION_VALUE_CHANGED__ID_TEXT_LED_STATE_INIT__APPW_JOB_SETVIS(APPW_ACTION_ITEM * pAction, WM_HWIN hScreen, WM_MESSAGE * pMsg, int * pResult) {
  GUI_USE_PARA(pAction);
  GUI_USE_PARA(hScreen);
  GUI_USE_PARA(pMsg);
  GUI_USE_PARA(pResult);
}
```

* `Application.h`のソースコード全体を以下に記載する（説明は後述）
```Application.h
#ifndef APPLICATION_H
#define APPLICATION_H
/* Custom code by Renesas */
#include "platform.h"
#include "AppWizard.h"

void process_switch_on(WM_HWIN hDisplayedText);
void process_switch_off(WM_HWIN hDisplayedText);
void process_switch_error(WM_HWIN hDisplayedText);
void led_on(void);
void led_off(void);
#endif  // RESOURCE_H
```

* `Application.c`のソースコード全体を以下に記載する（説明は後述）
```Application.c
#include "Application.h"

void process_switch_on(WM_HWIN hDisplayedText)
{
    TEXT_SetText(hDisplayedText, "ON");
    TEXT_SetBkColor(hDisplayedText, GUI_WHITE);
    TEXT_SetTextColor(hDisplayedText, GUI_BLUE);
    led_on();
}

void process_switch_off(WM_HWIN hDisplayedText)
{
    TEXT_SetText(hDisplayedText, "OFF");
    TEXT_SetBkColor(hDisplayedText, GUI_WHITE);
    TEXT_SetTextColor(hDisplayedText, GUI_GRAY);
    led_off();
}

void process_switch_error(WM_HWIN hDisplayedText)
{
    TEXT_SetText(hDisplayedText, "ERROR");
    TEXT_SetBkColor(hDisplayedText, GUI_WHITE);
    TEXT_SetTextColor(hDisplayedText, GUI_RED);
    led_off();
}

void led_on(void)
{
    PORT4.PODR.BIT.B0 = 0;
}

void led_off(void)
{
    PORT4.PODR.BIT.B0 = 1;
}
```
## main()関数
* `MainTask()`関数を実行する
  * `MainTask()`関数はemWinとAppWizardの初期化やメイン処理を実行する
  * `MainTask()`関数はAppWizardの[ソースコード出力](#code_generation_appwizard)によって自動生成される

## ID_SCREEN_00__ID_SWITCH_00__WM_NOTIFICATION_VALUE_CHANGED__ID_TEXT_LED_STATE__APPW_JOB_SETVIS()関数
* スイッチ`ID_SWITCH_00`のトグル切り替えをトリガとしてテキスト`ID_TEXT_LED_STATE`へ作用する時のイベントハンドラ
* 切り替えた時のトグル状態に応じて処理を振り分けている
  * トグルが右側に切り替わったときはスイッチオンとして処理をする
  * トグルが左側に切り替わったときはスイッチオフとして処理をする
  * 上記以外のトグル状態のときはエラーとして処理をする

## process_switch_on()関数
* テキスト`ID_TEXT_LED_STATE`の文字表示を"ON"に変更する（`TEXT_SetText()`）
* テキスト`ID_TEXT_LED_STATE`の背景色を白色に変更する（`TEXT_SetBkColor()`）
* テキスト`ID_TEXT_LED_STATE`の文字色を青色に変更する（`TEXT_SetTextColor()`）
* LEDを点灯する（`led_on()`）

## process_switch_off()関数
* テキスト`ID_TEXT_LED_STATE`の文字表示を"OFF"に変更する（`TEXT_SetText()`）
* テキスト`ID_TEXT_LED_STATE`の背景色を白色に変更する（`TEXT_SetBkColor()`）
* テキスト`ID_TEXT_LED_STATE`の文字色を灰色に変更する（`TEXT_SetTextColor()`）
* LEDを消灯する（`led_off()`）

## process_switch_error()関数
* テキスト`ID_TEXT_LED_STATE`の文字表示を"ERROR"に変更する（`TEXT_SetText()`）
* テキスト`ID_TEXT_LED_STATE`の背景色を白色に変更する（`TEXT_SetBkColor()`）
* テキスト`ID_TEXT_LED_STATE`の文字色を赤色に変更する（`TEXT_SetTextColor()`）
* LEDを消灯する（`led_off()`）

## led_on()、led_off()関数
* それぞれLEDを点灯/消灯する
* LEDを制御するポートはP40（[LED回路図](https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95%28%E3%83%99%E3%82%A2%E3%83%A1%E3%82%BF%E3%83%AB%29#led%E3%81%AB%E6%8E%A5%E7%B6%9A%E3%81%95%E3%82%8C%E3%81%9Frx72n%E3%81%AE%E3%83%9D%E3%83%BC%E3%83%88%E7%95%AA%E5%8F%B7%E3%82%92%E7%A2%BA%E8%AA%8D%E3%81%99%E3%82%8B)）

***



# <a name="additional"></a>追加情報

## AppWizardについて
* AppWizardを使用するにあたっての勘所を以下に記載する
### AppWizard概要
* AppWizardとは、emWinに搭載されているGUIオブジェクトのユーザ実装を支援するWindowsアプリケーション
* GUIオブジェクトの設置や設定、イベントの登録、動作のシミュレーション、さらにソースコード生成を画面を見ながら実施できる
### GUIオブジェクトについて
* AppWizard V1.06a_6.14aにて利用できるemWinのGUIオブジェクトは以下のとおり（括弧内は非公式な日本語説明）
  * Screen（全オブジェクトの親となるスクリーン）
  * Box（矩形）
  * Button（ボタン）
  * Image（画像）
  * Text（テキスト表示）
  * Slider（スライダーバー）
  * Rotary（丸型のコントロールノブ）
  * Switch（二値をもつトグルスイッチ）
  * Edit（テキスト入力欄）
  * Window（ウィンドウ画面）
  * QRCode（QRコード）
  * Gauge（半弧型の進捗ゲージ）
  * Keyboard（キーボード）
### AppWizard Tips
#### GUIオブジェクト同士の相対配置
* GUIオブジェクト同士は位置関係を記憶可能（Excelの図形グループ化機能に似ている）
* 方法は以下のとおり
  1. 関連付けたいGUIオブジェクトの一方を選択する
  2. GUIオブジェクトの四辺に現れる9つの□（サイズ調整用の印）のうち、いずれかを右クリックしたままドラッグし、赤線または緑線を表示させる
  3. 関連付けたいもう一方のGUIオブジェクト付近までドラッグし、緑線になったら右クリックを離す
  4. 関連付けを解除する場合は、配置オプション<a href="../../images/107_allign_option.png" target="_blank"><img src="../../images/107_allign_option.png" width="35px" target="_blank"></a>のいずれかを選択する

#### GUI_USE_PARAマクロ
* Slotルーチン関数のパラメータ未使用を原因とするコンパイラの警告を防ぐ目的で使用される
  * Slotルーチン内でSlotルーチン関数の全パラメータが常に使用されるとは限らないが、<br>このマクロを用いることで擬似的にパラメータを使用する

#### GUIオブジェクトのサイズ最適化
* GUIオブジェクトを右クリックし`Set size to content`を選択することで、オブジェクトの内容に応じてサイズを自動調整する

#### <a name="text_resource"></a>`Text` リソースの登録方法
* 初回のみ`language`（言語）を追加する
  * `New language` -> "English"を入力 -> `OK`
* Text定義を追加する
  * `Add text`を押すと、新規にText定義が追加される
  * 新規に追加されたText定義を押す -> `Id`を任意の識別文字に変更する -> <br>`English`項（`New language`で作成した項目）で定義したい文字列を入力する
* `Applay`でText定義を更新する

#### イベントハンドラ(Slot)と出力されたSlot関数の編集
* Slotと実際に出力されたソースファイル中のSlot関数は編集内容がリンクしている
* しかし、以下のケースでリンクが切れ、**編集内容が反映されない**ことがあるので注意が必要
  * Slotまたはソースファイル中のSlot関数のどちらか一方を削除する
  * AppWizardの`Interactions`ペインで`Receiver`などを変更する
  * その他のケースもありそう
