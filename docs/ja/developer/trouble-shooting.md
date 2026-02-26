# プロジェクトインポートは出来たがビルドができない
## 原因
* インポートしたプロジェクトで使用していたコンパイラバージョン(V301)と、ユーザがインストールしているコンパイラバージョン(V302以降)が一致していない

## 対策1
* e2 studio上でプロジェクト「aws_demos」のプロパティを開く
* 「C/C++ビルド」>「設定」>「Toolchain」タブを選択し、さらに「バージョン」>「v3.02.00」を選択 (空欄になっている場合)
* 「C/C++ビルド」>「設定」>「ツール設定」タブを選択し、さらに「Compiler」>「ソース」を選択
* 「コンパイル単位の先頭にインクルードするファイル」内の「"implicitlyinclude.h"」をダブルクリック
* 「ファイル・パスの編集」ウインドウが開くので、「ファイル・システム」をクリックし、「${base_folder}/vendors/renesas/amazon_freertos_common/compiler_support/ccrx」内の「implicitlyinclude.h」を選択
* 「OK」、「Apply and Close」を選択してウインドウを閉じる

## 対策2
* ユーザがインストールしているコンパイラバージョンをV301にする

# ブートローダからユーザアプリをダウンロードすると検証結果NGになる
## 原因
* TeraTermのバージョンが合っていない
* TeraTermの設定が足りていない

## 対策
* 以下設定をもう一度確認する
    * [Tera Term](https://osdn.net/projects/ttssh2/) 4.105以降
        * [シリアル接続における高速なファイル転送](https://teratermproject.github.io/manual/5/ja/setup/teraterm-trans.html#FileSendHighSpeedMode) の FileSendHighSpeedMode を OFF にする
            * Tera Term -> 設定 -> 設定の読み込み -> TERATERM.INI を テキストエディタで開く -> 設定を変更 -> 保存 -> Tera Term再起動