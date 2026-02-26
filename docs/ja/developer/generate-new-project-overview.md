# 準備する物
* 必須
    * RX72N Envision Kit × 1台
    * USBケーブル(USB Micro-B --- USB Type A) × 1 本
    * Windows PC × 1 台
        * Windows PC にインストールするツール
            * [e2 studio 2020-07](https://www.renesas.com/products/software-tools/tools/ide/e2studio.html)
            * [CC-RX](https://www.renesas.com/products/software-tools/tools/compiler-assembler/compiler-package-for-rx-family.html) V3.02以降

# e2 studio を起動し、新規プロジェクトを作成する
* ファイル -> 新規 -> プロジェクト
    * ウィザード -> C/C++ -> C/C++ プロジェクト -> 次へ
        * All -> Renesas CC-RX C/C++ Executable Project
            * プロジェクト名 = rx72n_envision_kit を入力 -> 次へ
                * Device Settings -> ターゲット・デバイス -> ...ボタン -> RX700 -> RX72N -> RX72N - 144pin -> R5F572NNHxFB (ファームウェアアップデートも試そうと考えている場合は、R5F572NNHxFB_DUALを選択)
                * Configuration -> Hardware Debug 構成を生成 -> E2 Lite (RX) -> 次へ
                    * スマート・コンフィグレータを使用する にチェック -> 終了
* ★将来改善★ プロジェクト新規作成時もBDFインストールができるようにする

# RX72N Envision Kit の ボードコンフィグレーションファイル(BDF)をインストール
* <a href="../../images/044_e2_studio_sc.png" target="_blank"><img src="../../images/044_e2_studio_sc.png" width="480px" target="_blank"></a>

# RX72N Envision Kit の ボードコンフィグレーションファイル(BDF)を読み込む
* <a href="../../images/045_e2_studio_sc.png" target="_blank"><img src="../../images/045_e2_studio_sc.png" width="480px" target="_blank"></a>

# RX72N Envision Kitに合わせてスマートコンフィグレータでクロック設定を施す 
* ★将来改善★ BDF連携により e2 studio 2020-xx (将来バージョン)で不要になる見込み。e2 studio 2020-07以前では必要
* <a href="../../images/022_e2_studio_sc1.png" target="_blank"><img src="../../images/022_e2_studio_sc1.png" width="480px" target="_blank"></a>
    * スマートコンフィグレータの下部、「クロック」タブを押す
        * メインクロック -> 周波数 -> 16 (MHz) に変更
        * PLL回路 -> 逓倍比 を x15.0 に変更
        * PPLL回路 -> 分周比を x1/2、逓倍比 を x25.0 に変更
            * FlashIFクロック、システムクロック等が上記変更に連動して、自動的に変更されることを確認
    * スマートコンフィグレータ右上の「コード生成」ボタンを押すとスマートコンフィグレータで設定した内容に応じたスケルトンプログラムが出力される
    * e2 studio画面上部のプロジェクト -> すべてをビルド を実行し、コンソールにエラー表示されないことを確認

# CMT(Compare Match Timer)を使用し0.1秒周期割り込みを発生させLEDを0.1秒周期で点滅させる
## スマートコンフィグレータでCMTのコンポーネントを登録する
* <a href="../../images/046_e2_studio_sc.png" target="_blank"><img src="../../images/046_e2_studio_sc.png" width="480px" target="_blank"></a>
    * スマートコンフィグレータの下部、「コンポーネント」タブを押す
    * 上記のようにr_cmt_rxコンポーネントを追加する
    * 表示されない場合は、以下を試す
        * ほかのソフトウェアコンポーネントをダウンロードする -> Region選択 -> 表示された RXファミリ RX Driver Package Ver.x.xx (最新版)を選択しダウンロードする
    * CMTのみ動作確認の場合は不要だが、SCI(Serial Communication Interface)やポート設定などを動的に行う場合は以下も実施しておくとよい
        * 基本設定 -> C/C++ -> Renesas -> スマート・コンフィグレータ -> コンポーネント -> すべてのFITモジュールを表示する
    * スマートコンフィグレータ右上の「コード生成」ボタンを押すとスマートコンフィグレータで設定した内容に応じたスケルトンプログラムが出力される
        * <a href="../../images/047_e2_studio_sc.png" target="_blank"><img src="../../images/047_e2_studio_sc.png" width="480px" target="_blank"></a>
    * e2 studio画面上部のプロジェクト -> すべてをビルド を実行し、コンソールにエラー表示されないことを確認

## CMTのコンポーネントのマニュアルを確認する
* <a href="../../images/024_e2_studio_sc3.png" target="_blank"><img src="../../images/024_e2_studio_sc3.png" width="480px" target="_blank"></a>
    * スマートコンフィグレータが生成するコードはすべて smc_gen フォルダに格納される
    * 様々な機能を持つコンポーネント、例えば今回使用する r_cmt_rx など、docフォルダを持つコンポーネントがある
    * docフォルダ内にはマニュアルが入っており、コンポーネントのAPI仕様およびその使用方法を確認できる
    * 今回は、r_cmt_rx の 周期起動API、R_CMT_CreatePeriodic()を使用する

## LEDに接続されたRX72Nのポート番号を確認する
* <a href="../../images/025_board_led.png" target="_blank"><img src="../../images/025_board_led.png" width="480px" target="_blank"></a>
    * P40がUSER LEDに繋がっている
        * P40 の電圧レベルをゼロにすることで、3.3V電源からUSER LEDを経由しP40に対し電流が流れ、USER LEDが点灯する仕組み

## スマートコンフィグレータでポートのコンポーネントを登録する
* <a href="../../images/026_e2_studio_sc4.png" target="_blank"><img src="../../images/026_e2_studio_sc4.png" width="480px" target="_blank"></a>
    * スマートコンフィグレータの下部、「コンポーネント」タブを押す
    * 上記のように ポート コンポーネントを追加する
    * さらに、追加された Config_PORT コンポーネントを選択し、以下設定を施す
        * ポート選択タブ -> PORT4
        * PORT4タブ
            * P40 -> 出力、CMOS出力、1を出力にチェック(初期状態でLED消灯)
    * スマートコンフィグレータ右上の「コード生成」ボタンを押すとスマートコンフィグレータで設定した内容に応じたスケルトンプログラムが出力される
    * e2 studio画面上部のプロジェクト -> すべてをビルド を実行し、コンソールにエラー表示されないことを確認

## main()関数を作成する
* スマートコンフィグレータが出力するコードは、ハードウェアの初期化が完了すると、main()を呼び出す
* ユーザはこのmain()にユーザコードを追加し、ユーザシステムの動作を定義していく
* 今回はここに、CMTとポートの機能を使用したコードを追加することで、「LEDを0.1秒周期で点滅させる」ことを実現する
* 以下コードを rx72n_envision_kit.c に書き込む
    * rx72n_envision_kit.c のソースコードはe2 studio画面上のプロジェクトエクスプローラにおいて、 rx72n_envision_kit -> src -> smc_gen に格納されている
```
#include "r_smc_entry.h"
#include "platform.h"
#include "r_cmt_rx_if.h"

void main(void);
void cmt_callback(void *arg);

void main(void)
{
	uint32_t channel;
	R_CMT_CreatePeriodic(10, cmt_callback, &channel);
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
```
## 動作確認
* RX72N Envision KitのSW1-2 をOFF(ボードの下側)にする
    * <a href="../../images/017_board_sw1.jpg" target="_blank"><img src="../../images/017_board_sw1.jpg" width="480px" target="_blank"></a>
* 次にビルドしたファームウェアをRX72Nにダウンロードし、実行する
    * e2 studio 画面上部の Configuration プルダウンで rx72n_envision_kit HardwareDebug が選択されていることを確認
    * その右隣りの歯車アイコンを押す
        * Debugger -> Debug hardware -> E2 Lite(RX) が選択されていることを確認
        * Debugger -> Connection Settings
            * メイン・クロック・ソース -> EXTAL に変更
            * EXTAL周波数[MHz] -> 16.0000 に変更
            * 動作周波数[MHz] -> 240 に変更
            * 接続タイプ -> Fine に変更
            * エミュレータから電源を供給する (MAX 200mA) -> いいえ に変更
    * e2 studio 画面上部の 虫アイコンを押してファームウェアをRX72Nにダウンロードする
    * e2 studio 画面上部の 再生ボタンのアイコンを押してファームウェアを実行する
        * main()で一度ブレークするのでもう一度再生ボタンのアイコンを押す
* ボード上の青色LED(ボード中央RX72Nの右下あたり)が0.1秒周期で点滅することを確認
* ★将来改善★ BDFに合わせてデバッガの設定を自動化する

# [スマートコンフィグレータ](https://www.renesas.com/products/software-tools/tools/solution-toolkit/smart-configurator.html)とは？
* RX72Nは汎用マイコンであるため、クロック源や内部PLL回路の逓倍/分周比を柔軟に設定することができる
* CMTに代表されるタイマ系や、SCIに代表される通信系においては、自身に配線されているクロック信号のクロック速度に応じて自身への設定値をソフトウェアにより調整する必要がある
* このソフトウェアのコーディングは本来、マイコンのマニュアルを参照しながらユーザが行う必要があるが、非常に設定項目が多岐に渡るためスマートコンフィグレータのようなツールでこれを支援する機構を用意した
* ユーザ（特にアプリ設計者）はクロック源が何MHzであるとか、内部PLLの設定がどうなっているかを意識することなく、APIレベルでたとえば「ボーレートは115200bps」といった形でソフトウェアからハードウェアに対して指示をすることが可能となり、ソフトウェア開発効率が改善する
* また、RXファミリ製品を熟知した設計者がCMT、SCI、Ether、USB、SDHI等のRXファミリ内蔵回路用のドライバソフトウェアを主要RXグループに対し同一API設計にて「FITモジュール」という形式で開発・メンテナンス(継続的な不具合修正)を実施し、FITモジュールを1個のパッケージに同梱したものを「RX Driver Package」として配布をしている
* 従ってユーザはRXファミリ間の詳細なハードウェア差異やハードウェアエラッタ情報を意識することなくアプリケーション開発に注力できる

# 画面処理系のFITモジュール
* 画面処理系のFITモジュールはまだ試作段階であり、RX Driver Packageに正式に組み込めていない
* 試作段階のFITモジュールはearly prototypeとして以下にあり、使用する場合は別途導入が必要
    * https://github.com/renesas/rx-driver-package
* 画像処理系以外にもSDIOドライバや各種WiFiドライバのearly prototype版のFITモジュールがいくつか存在する
* 以下フォルダに上記URLからダウンロードしたFITモジュール(FITModulesフォルダ内の*.zip, *.xml, *.mdf)をコピーすればスマートコンフィグレータがそれを読み込むことができる
    * e2 studio 2020-04以前
        * <a href="../../images/031_e2_studio_sc8.png" target="_blank"><img src="../../images/031_e2_studio_sc8.png" width="480px" target="_blank"></a>
    * e2 studio 2020-07以降
        * <a href="../../images/042_e2_studio_sc.png" target="_blank"><img src="../../images/042_e2_studio_sc.png" width="480px" target="_blank"></a>
        * <a href="../../images/043_e2_studio_sc.png" target="_blank"><img src="../../images/043_e2_studio_sc.png" width="480px" target="_blank"></a>

# ★今後改善する項目
* LEDのON/OFFだけでなく、RX72N Envision Kit に搭載されている全機能についてスマートコンフィグレータで簡単に設定ができるよう*.scfgファイルを整備できるよう、情報拡充する <工事中>
* BDF設定によりFITモジュールのMDF(Module Description File)が抱える初期設定値を更新できるようにすることで、ボード選択により全自動でFITモジュールの再設定が可能となる
* BDF設定によりPMODなどのボード上のマルチファンクションなコネクタに対するFITモジュール設定を柔軟に選択可能にする