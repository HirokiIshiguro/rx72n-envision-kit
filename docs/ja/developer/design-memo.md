# はじめに

* 本稿ではRX72N Envision Kit 初期ファームウェアの設計思想など、ユーザが独自実験を行うため初期ファームウェアをカスタムする際に必要な情報をまとめます。
* 以降説明では「ですます調」でなくなります。

# メモを書いている人
*  hiroki.ishiguro.fv@renesas.com

# システム設計
* RX72N 基本情報
    * データシート、ハードウェアマニュアルへのリンク
* RX72N Envision Kit 基本情報
    * システムブロック図
    * 回路図へのリンク
* システム基幹部分となるブートローダ/ファームウェアアップデートの仕掛けについて
    * https://github.com/renesas/amazon-freertos/wiki/OTA%E3%81%AE%E6%B4%BB%E7%94%A8
* 画面表示系システム
    * emWinについてまとめる
* デバイスドライバ
    * RX Driver Packageについて紹介する

# メモリマップ
* データフラッシュ: RX72Nマイコンの仕様
```
 +---------------------------------+ 0x00100000 +
 |                                 |            |
 |       user area                 |   <32KB>   | 
 |                                 |            |
 +---------------------------------+ 0x00108000 +
```
* データフラッシュ: RX72N Envision Kit 初期ファームウェアでのメモリマップ定義
```
                                                                             (section name)
+---------------------+---------------------------------------+ 0x00100000 + C_BOOTLOADER_KEY_STORAGE
|  const data of      | root/integrity check keys             |   <1KB>    | 
|  boot loader        +---------------------------------------+ 0x00100400 + C_BOOTLOADER_KEY_STORAGE_MIRROR
|                     | root/integrity check keys mirror      |   <1KB>    | 
+---------------------+---------------------------------------+ 0x00100800 + C_PKCS11_STORAGE
|                     | Amazon FreeRTOS PKCS const data       |   <8KB>    | 
|  const data of      +---------------------------------------+ 0x00102800 + C_PKCS11_STORAGE_MIRROR
|  user application   | Amazon FreeRTOS PKCS const data mirror|   <8KB>    | 
|                     +---------------------------------------+ 0x00104800 + C_SYSTEM_CONFIG 
|                     | System Config Data                    |   <6KB>    | 
|                     +---------------------------------------+ 0x00106000 + C_SYSTEM_CONFIG_MIRROR
|                     | System Config Data mirror             |   <6KB>    | 
|                     +---------------------------------------+ 0x00107800 +
|                     | free area for user application        |   <2KB>    | 
|---------------------+---------------------------------------+ 0x00108000 +
```
* コードフラッシュ: RX72Nマイコンの仕様
```
 +---------------------------------+ 0xFFC00000 +
 |                                 |            |
 |       temporary area            |  <2048KB>  | bank1
 |                                 |            |
 +---------------------------------+ 0xFFE00000 +
 |                                 |            |
 |       execute area              |  <2048KB>  | bank0
 |                                 |            |
 +---------------------------------+ 0xFFFFFFFF +
```
* コードフラッシュ: RX72N Envision Kit 初期ファームウェアでのメモリマップ定義
```
 +----------------------+----------------------+----------------------+ 0xFFC00000+-------+
 |                      |                      |  header              | <768B>    |       |
 |                      |  buffer              +----------------------+ 0xFFC00300|       |
 |  temporary area      |                      |  contents            | <~1791KB> | bank1 |
 |                      +----------------------+----------------------+ 0xFFDC0000|       |
 |                      |  Bootloader(mirror)  |  contents            | <256KB>   |       |
 +----------------------+----------------------+----------------------+ 0xFFE00000+-------+
 |                      |                      |  header              | <768B>    |       |
 |                      |  user application    +----------------------+ 0xFFE00300|       |
 |  execute area        |                      |  contents            | <~1791KB> | bank0 |
 |                      +----------------------+----------------------+ 0xFFFC0000|       |
 |                      |  Bootloader          |  contents            | <256KB>   |       |
 +----------------------+----------------------+----------------------+ 0xFFFFFFFF+-------+
```

# 初期ファームウェアとアップデート後ファームウェアの動作の違い
* 初期ファームウェア
    * execute area に スポーツゲームがインストールされている
    * temporary area に ベンチマークがインストールされている
    * ベンチマークもスポーツゲームもバンクスワップ機能を持ち、どちらのareaも起動可能となっている
    * アップデート後のインテグリティチェック機構、不正ファームウェアインストール時の復旧および必要に応じたバンクスワップはBootloaderが担う
* アップデート後ファームウェア
    * execute area に 任意のバージョンのuser applicationがインストールされている
    * temporary area は ブランク状態である
    * 任意のバージョンのuser applicationはアップデート機能を持ち、アップデート時はtemporary area に 新user applicationをインストールする
    * アップデート後のインテグリティチェック機構、不正ファームウェアインストール時の復旧および必要に応じたバンクスワップはBootloaderが担う
