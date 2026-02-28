# CLAUDE.md - Development Notes / 開発メモ

## Background / 背景

This project was originally created at Renesas Electronics for the RX72N Envision Kit evaluation board. The original owner (Hiroki Ishiguro / @HirokiIshiguro) left Renesas and now continues development as a personal open-source project on a self-hosted GitLab instance.

本プロジェクトは、ルネサスエレクトロニクスにて RX72N Envision Kit 評価ボード向けに立ち上げられました。オリジナルオーナー (石黒 裕紀 / @HirokiIshiguro) がルネサスを退職後、個人の OSS 活動として自前の GitLab サーバ上でメンテナンスを継続しています。

- The upstream repository https://github.com/renesas/rx72n-envision-kit has not been actively maintained since 2024.
- This repository is mirrored to a GitHub fork for visibility to existing users who may be waiting for firmware updates.

## Goals / 目標

### Long-term goal / 最終目標

Enable users to try all features of the RX72N Envision Kit.

RX72N Envision Kit の全機能を試せるようにする。

### Near-term objectives / 直近の目標

| # | Objective | Status |
|---|---|---|
| 1 | Documentation cleanup: migrate Wiki to `docs/` | Done |
| 2 | Set up Claude-assisted development environment | In progress |
| 3 | Set up CI/CD pipeline | In progress (Phase 1-2 done) |
| 4 | Replace FreeRTOS with latest Renesas IoT reference implementation ([iot-reference-rx](https://github.com/renesas/iot-reference-rx)) | Planned |

## Repository Locations / リポジトリ

| Location | URL |
|---|---|
| Primary (GitLab) | https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit |
| Mirror (GitHub fork) | https://github.com/HirokiIshiguro/rx72n-envision-kit |
| Upstream (GitHub) | https://github.com/renesas/rx72n-envision-kit |

## CI/CD Pipeline

### Goals / 目標

| Phase | Goal | Status |
|-------|------|--------|
| 1 | e2studio ヘッドレスビルド（3プロジェクト） | Done |
| 2 | flash（rfp-cli）+ UART テスト自動化 | Done (MR !9) |
| 3 | UART ダウンロード後のフリーズ現象の解析・修正（原因: BANKSEL 未リセット、修正: `-erase-chip`） | Done |
| 4 | boot_loader の UART ダウンロードを COM6 (SCI2, 115200bps) から COM7 (SCI7 PMOD FTDI, 921600bps) に変更（要ファームウェア SCI ポート変更。ダウンロード時間短縮でデバッグ効率改善） | Planned |
| 5 | e2studio 2024-01 / CC-RX v3.04 環境で既存機能の動作検証（AWS 接続、SD カードによるファームウェアアップデート、各種コマンドレスポンス） | Planned |
| 6 | e2studio 2025-12 / CC-RX v3.07 に変更し、既存機能の動作検証（AWS 接続、SD カードによるファームウェアアップデート、各種コマンドレスポンス） | Planned |
| 7 | FreeRTOS LTS 最新版適用（[iot-reference-rx](https://github.com/renesas/iot-reference-rx) 最新リリースタグ） | Planned |
| 8 | AWS 接続を含む OTA テスト | Planned |
| 9 | RX72N Envision Kit 複数台でのフリートプロビジョニング＋OTA 一斉実施の全自動テスト | Planned |
| - | UART テストスクリプトの共通ライブラリ化（[mcu-test/uart](https://shelty2.servegame.com/oss/experiment/generic/scripts/python/mcu-test) へ切り出し、git submodule で各プロジェクトから参照） | Planned |
| - | mot_to_rsu コンバータの共通部品化（git submodule で各プロジェクトから参照） | Done (MR !12) |

### Build environment / ビルド環境

- **IDE:** e2 studio 2025-12（`C:\Renesas\e2_studio_2025_12\eclipse\e2studioc.exe`）
  - e2 studio 2024-01 でもビルド確認済み（upstream v2.0.2 タグ当時の推定バージョン）
- **Compiler:** CC-RX v3.04.00（3プロジェクト共通。v3.07.00 は LCD 消灯バグあり、MR !11 で戻し）
- **Runner tag:** `run_ishiguro_machine`（Windows 11、RX72N Envision Kit 物理接続済み）
- **Workspace:** `C:\workspace_rx72n`（hello_world とは別ディレクトリ）

**FIT モジュール管理 (Smart Configurator 依存):**

SMC（Smart Configurator）は `.scfg` ファイルに記録された FIT モジュールバージョンをローカルの
`~/.eclipse/com.renesas.platform_download/FITModules/` フォルダから取得する。
**必要なバージョンがローカルにない場合、SMC はエラーを出さずにコード生成をスキップする（サイレントスキップ）。**
結果として `smc_gen/` 配下のソースが生成されず、ビルドエラーとなる。

- `.scfg` の `<component display="..." version="...">` タグから必要モジュール一覧を取得可能
- aws_demos: 27 モジュール、boot_loader: 11 モジュール（計30ユニーク）
- ローカルに不足するモジュールは https://github.com/renesas/rx-driver-package/blob/master/versions.xml で URL を解決し、ダウンロード可能
- **自動化スクリプト:** `tools/mcu-tool-rx/resolve_fit_modules.py` — `.scfg` パース → ローカルチェック → 不足分ダウンロード

```bash
# 使用例
python tools/mcu-tool-rx/resolve_fit_modules.py <scfg_file_or_dir> [--fit-dir <path>] [--dry-run]
```

**e2studio ヘッドレスビルドでの AWS_IOT_MCU_ROOT パス変数:**

aws_demos の `.project` は `AWS_IOT_MCU_ROOT` パス変数を使った linkedResources を含む。
ヘッドレスビルドでは以下のワークスペース設定ファイルでパス変数を事前定義する:

```
# <workspace>/.metadata/.plugins/org.eclipse.core.runtime/.settings/org.eclipse.core.resources.prefs
eclipse.preferences.version=1
pathvariable.AWS_IOT_MCU_ROOT=C\:/rx72n-local
```

注意: `-import` オプションのパスは `file:///C:/...` URI 形式を使用すること（`C:/...` はスキームエラーになる）。

### Build targets / ビルド対象

| Project | Path | Output |
|---------|------|--------|
| aws_demos | `projects/renesas/rx72n_envision_kit/e2studio/aws_demos` | `aws_demos.mot` |
| boot_loader | `projects/renesas/rx72n_envision_kit/e2studio/boot_loader` | `rx72n_boot.mot` |
| segger_emwin_demos | `projects/renesas/rx72n_envision_kit/e2studio/segger_emwin_demos` | `segger_emwin_demos.mot` |

### Design decisions / 設計判断

**パス長対策（NTFS ジャンクション方式）:**
e2studio の CDT managed build は `.cproject` 内のインクルードパスを `${ProjDirPath}/../../../../../vendors/...` パターンで生成する。
GitLab Runner のチェックアウトパス（約80文字）+ `${ProjDirPath}`（約137文字）+ 相対パス + ヘッダファイル名を合計すると
260文字を超え、CC-RX が `F0520005 (Cannot open source file)` エラーを出す。

解決策: `CI_PROJECT_DIR` への短い NTFS ジャンクション `C:\rx72n-src` を作成し、
そこからプロジェクトをインポートすることで `${ProjDirPath}` を約65文字に短縮（68文字の削減）。

**aws_demos リンクリソースのジャンクション化:**
aws_demos は AWS FreeRTOS のポーティング構造に従い、`.project` の `linkedResources`（type=2）で
`vendors/` 配下のソースファイルを参照している。e2studio ヘッドレスビルドでは一部のリンクリソースが
解決されないため、以下のジャンクションを作成してリンクリソースを物理化:
- `src/smc_gen/r_config` → インクルードパス解決のみ（`src/smc_gen` 全体をジャンクション化すると二重コンパイルで `E0562300 Duplicate symbol` になる）
- `application_code/{renesas_code,aws_code,smc_gen}` → ソースファイル参照
- `config_files` → FreeRTOS/AWS 設定ヘッダ群

**Git サブモジュール:**
`GIT_SUBMODULE_STRATEGY: recursive` が必要。`.gitmodules` の URL は **HTTPS** にすること（SSH URL だと CI の job token 認証でクローン失敗する）。

| Submodule | Path | URL |
|-----------|------|-----|
| coreSNTP | `libraries/coreSNTP` | https://github.com/FreeRTOS/coreSNTP.git |
| mcu-tool-rx | `tools/mcu-tool-rx` | https://shelty2.servegame.com/oss/experiment/generic/scripts/python/mcu-tool/renesas/rx.git |

mcu-tool-rx は RX マイコン共通ツール（`resolve_fit_modules.py`, `mot_to_rsu.py`）を集約した共有リポジトリ。

**mot_to_rsu.py の機能:**
- **RSU 変換モード**（デフォルト）: `.mot` → `.rsu` 変換（OTA 用、C# ツール Update タブ相当）
- **Factory MOT 生成モード** (`--factory`): boot_loader + bank0 アプリ + bank1 アプリを結合した書き込み用 MOT を生成（C# ツール Initial タブ相当）
- **検証モード** (`--verify`): 既存 `.rsu` ファイルの構造解析・署名検証

> **C# "Renesas Secure Flash Programmer" は廃止予定。**
> CUI モードにバグがあり（`sig-sha256-ecdsa` Update モードで秘密鍵パス未設定）、ビルドに Visual Studio が必要なため、
> 全機能を `mot_to_rsu.py` で代替済み。`tools/Renesas Secure Flash Programmer/` は今後削除予定。

**e2studio ヘッドレスビルドの注意点:**
- `-cleanBuild all` を使うこと（`-build all` だとキャッシュで「変更なし→ビルド不要」と判断されスキップされる）
- ワークスペース (`C:\workspace_rx72n`) は毎回全削除が必要（`.metadata` だけの削除では不十分）
- rfp-cli で書き込みなし実行のみ: `rfp-cli -device RX72x -tool "e2l:<serial>" -if fine -run -noquery`（デバッグ・復旧用）

**ビルド方式:**
hello_world_with_claude_on_cicd と同じ e2studio ヘッドレスビルドパターンを採用。
3プロジェクトを1回の e2studio 起動でまとめてインポート＆ビルドする。
ビルドログは 15MB+ になるため、`Tee-Object | Out-Null` でファイルに保存しつつ
job log への出力を抑制（GitLab の 4MB ジョブログ制限を回避）。

**CLI ビルド（make + CC-RX 直接実行）:**
e2studio なしで GNU Make + CC-RX ツールチェーンのみでビルドする方法。
Makefile は e2studio ヘッドレスビルドで一度生成し、以後は `make` で直接ビルドする。

前提条件:
- e2studio headless build を1回実行し `HardwareDebug/` に Makefile を生成済み
- `C:\rx72n-local` ジャンクション（e2studio workspace 生成時に使用したパス）
- aws_demos の linked resource ジャンクション（application_code, config_files 等）
- `libraries/coreSNTP` サブモジュールの初期化済み

ビルドコマンド（PowerShell）:
```powershell
$ccrxBin = "C:\Program Files (x86)\Renesas\RX\3_4_0\bin"
$makeExe = "C:\Renesas\e2_studio_2025_12\eclipse\plugins\com.renesas.ide.exttools.gnumake.win32.x86_64_4.3.1.v20240909-0854\mk\make.exe"
$env:PATH = "$ccrxBin;$env:PATH"

# boot_loader
& $makeExe -C boot_loader\HardwareDebug rx72n_boot_loader.mot

# segger_emwin_demos
& $makeExe -C segger_emwin_demos\HardwareDebug segger_emwin_demos.mot

# aws_demos
& $makeExe -C aws_demos\HardwareDebug aws_demos.mot
```

検証結果（CC-RX v3.04.00、2026-03-01）:
| Project | CLI .mot | CI .mot | 比較結果 |
|---------|----------|---------|---------|
| boot_loader | 162,680 B | 162,680 B | 完全一致 |
| segger_emwin_demos | 5,214,160 B | 5,214,160 B | タイムスタンプのみ差異 |
| aws_demos | 3,223,714 B | 3,223,570 B | タイムスタンプ + リンク順序差（144B） |

注意: Makefile 内の `.ud` パス等は e2studio workspace 生成時のパスがハードコードされるが、.mot 生成には影響しない。

**CC-RX バージョン変更時の CLI ビルド追従:**
Makefile 再生成なしで CC-RX バージョンを切り替え可能。以下のファイルのパスを書き換える:
1. `makefile.init` — `INC_RX`, `RXC_LIB`, `BIN_RX` の CC-RX インストールパス
2. 全 `cSubCommand.tmp` — `-include` の CC-RX ヘッダパス
3. `LibraryGenerator*.tmp` — ライブラリ生成時のパス

検証結果（v3.04.00 → v3.07.00 パス書き換え、boot_loader）:
- v3.04.00: 162,680 B / v3.07.00: 162,372 B（308B 差、最適化差異）
- `-tfu=intrinsic` オプションは v3.04.00/v3.07.00 両方で有効（パス不一致時に `F0520571:Invalid option: --tfu_version=v1` エラー）
- ただし v3.07.00 は LCD 消灯バグがあるため運用では v3.04.00 を使用（MR !11 で戻し）
- **LCD 消灯バグの根本原因仮説（DPFPU レジスタ退避問題）:** CC-RX v3.07 が ISR パスで DPFPU 命令を生成 → FreeRTOS の割り込みハンドラが DPFPU レジスタを退避しない → タスクの浮動小数点レジスタが破壊 → 約10分後に描画崩壊。FreeRTOS port.c に `#warning Testing for DFPU support in this port is not yet complete` がある。v2.0.2 以前にも同根の R14 レジスタ退避問題が存在していた

### Hardware reference / ハードウェアリファレンス

**UART ポート構成:**

| SCI チャネル | ピン | コネクタ | 変換チップ | COM ポート | VID |
|---|---|---|---|---|---|
| SCI2 | P12 (TXD2) / P13 (RXD2) | CN8 (オンボード) | RL78/G1C (USB-シリアル) | COM6 | 045B (Renesas) |
| SCI7 | P90 (TXD7) / P92 (RXD7) | CN6 (PMOD) | FTDI (外付け拡張基板) | COM7 | 0403 (FTDI) |

- SW1-2: E2 OB 有効/無効（OFF=有効）。ON にしても E2 OB がリセット解除に関与するため RX72N は起動しない
- SW3-2: CN8 の接続先を RX72N / ESP32 で切り替え
- E2 Lite: オンボード搭載（デバッグマイコン = RX231、USB シリアル変換 = RL78/G1C、別チップ）
- RL78/G1C ファームウェア制限で COM6 ボーレート上限は 115200bps
- boot_loader の UART 設定: `r_bsp_config.h` → `MY_BSP_CFG_SERIAL_TERM_SCI (2)`, 115200bps
- aws_demos は COM7 (SCI7, PMOD FTDI, 921600bps) で FreeRTOS ログを出力する。CI での aws_demos 起動確認に利用可能
- CN7 (DC ジャック): KLDX-SMT2-0202-A、センタープラス 5V 2A。E2 Lite USB 非依存の給電経路（AC アダプタ給電でリセットホールド回避の可能性あり、未検証）

**E2 Lite パワーオンリセット問題:**

E2 Lite 別冊マニュアル (R20UT0399JJ): 「デバッグ終了後にエミュレータを取り外してマイコン単体で動作させることは保証しておりません」。
RX72N Envision Kit はオンボード E2 Lite (RL78/G1C = U9) を搭載しており、USB (CN8) 給電時はパワーオンリセットで RL78/G1C が RX72N の RES# をホールドするため MCU が起動しない。
CI/CD では rfp-cli `-run` で書き込み後に MCU 実行開始することで回避している。

**COM6 MCU→PC 間欠受信障害:**

COM6 (RL78/G1C USB シリアル) の MCU→PC 方向で受信データが 0 bytes になる現象が間欠的に発生する。
原因未特定（USB 抜き差しで改善する場合あり）。download_aws_demos の成功判定は TX 完了のみで判断し、
MCU 応答を受信できた場合は integrity check 結果で判定する TX-only 方式で回避中。

**Flash ツール (rfp-cli):**

```bash
# boot_loader 書き込み（CI/CD 標準 — -erase-chip で BANKSEL リセット）
# 注意: -erase-chip は他の操作 (-p, -v 等) と併用不可。2コマンドに分ける必要がある
rfp-cli -d RX72x -t "e2l:<serial>" -if fine -s 1500K \
  -auth id FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF -erase-chip -noquery
rfp-cli -d RX72x -t "e2l:<serial>" -if fine -s 1500K \
  -auth id FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF -p <boot_loader.mot> -v -run -noquery

# 開発用（Verify 省略で高速化）
rfp-cli -d RX72x -t "e2l:<serial>" -if fine -s 1500K \
  -auth id FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF -erase-chip -noquery
rfp-cli -d RX72x -t "e2l:<serial>" -if fine -s 1500K \
  -auth id FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF -p <mot_file> -run -noquery -nocheck-range
```

- サポート速度: 250K / 500K / 750K / 1000K / **1500K**（最大）
- `-auto` = `-e -p -v`（erase + program + verify）。開発時は `-e -p`（verify 省略）で高速化可能
- `-run`: **全操作で必須。** rfp-cli 接続時に E2 Lite が MCU をリセット・停止させるため、`-run` なしで切断すると MCU がホールド状態のまま停止する（LCD 消灯、UART 無応答）。読み取り専用操作（`-rv`, `-sig` 等）でも末尾に `-run` を付けること
- `-erase-chip` vs `-e`: 後述の BANKSEL 問題を参照。**boot_loader 書き込み時は `-erase-chip` 必須**

| モード | 速度 | 所要時間 | 備考 |
|--------|------|----------|------|
| boot_loader 単体 `-erase-chip -p -v` | 1500K | 約16秒 | CI/CD パイプライン標準 |
| factory MOT `-auto` | 500K | 約396秒 | Verify あり（3.7MB） |
| factory MOT `-e -p` | 1500K | **約122秒** | Verify 省略（推奨） |

**BANKSEL（起動バンク選択）と `-erase-chip` の必要性:**

> **これは Phase 3 フリーズ現象の根本原因であり、CI/CD パイプラインの安定稼働に不可欠な知見。**

RX72N のデュアルバンクフラッシュでは、BANKSEL レジスタ（Config Area `0xFE7F5D20`）が
物理バンクと論理アドレスのマッピングを制御する:

| BANKSEL 値 | 起動バンク | 0xFFE00000-0xFFFFFFFF（実行側） | 0xFFC00000-0xFFDFFFFF（ミラー側） |
|---|---|---|---|
| 0xFFFFFFFF（デフォルト） | bank0 | 物理 bank0 | 物理 bank1 |
| 0xFFFFFFF8（swap 後） | bank1 | 物理 bank1 | 物理 bank0 |

boot_loader が UART ダウンロード完了後に `flash_toggle_banksel_reg()` で bank swap を実行すると、
BANKSEL が `0xFFFFFFFF` → `0xFFFFFFF8` に反転する。

**問題のメカニズム:**

1. boot_loader の .mot ファイルは `BSP_CFG_CODE_FLASH_START_BANK=0`（bank0 起動）でビルドされており、
   Config Area (`0xFE7F5D20`) に `__BANKSELreg = 0xFFFFFFFF` を含む（`vecttbl.c` で定義）
2. rfp-cli の `-e`（通常 erase）は **Code Flash + Data Flash のみ消去** し、Config Area は消去しない
3. Config Area はフラッシュの性質上 **ビット 1→0 書き換えのみ可能**（0→1 への書き戻しは不可）
4. BANKSEL=`0xFFFFFFF8` の状態で .mot 内の `0xFFFFFFFF` を上書きしても **`0xFFFFFFF8` のまま変わらない**
5. → verify で不一致（.mot は `0xFFFFFFFF`、デバイス上は `0xFFFFFFF8`）→ **rfp-cli exit code=1**

**Phase 3 フリーズの再現シナリオ（CI/CD パイプライン）:**

1. 1回目のパイプライン: rfp-cli で boot_loader フラッシュ（BANKSEL=0xFF）→ UART ダウンロード → bank swap → **BANKSEL=0xF8 に反転** → aws_demos 正常起動
2. 次のプッシュで 2回目のパイプライン起動: rfp-cli `-auto`（= `-e -p -v`）で boot_loader フラッシュ → `-e` では Config Area 未消去のため **BANKSEL=0xF8 のまま** → verify 失敗 or バンクマッピング不整合 → **フリーズ**

**修正:** `-e` の代わりに **`-erase-chip`** を使用する。`-erase-chip` は Config Area も消去（全ビット 1 に戻す）するため、
BANKSEL が確実に `0xFFFFFFFF` に戻り、.mot 内の値が正しく書き込まれる。

**BSP による BANKSEL 値の埋め込み:**

boot_loader 本体のコードでは BANKSEL を**読み取るだけ**で書き込みは行わない。
BANKSEL の初期値は BSP（`smc_gen/r_bsp/mcu/rx72n/vecttbl.c`）が .mot ファイルに埋め込む:

```c
// vecttbl.c (BSP)
#if BSP_CFG_CODE_FLASH_START_BANK == 0
    #define BSP_PRV_START_BANK_VALUE (0xffffffff)   // bank0 起動
#else
    #define BSP_PRV_START_BANK_VALUE (0xfffffff8)   // bank1 起動
#endif
#pragma address __BANKSELreg = 0xFE7F5D20
const uint32_t __BANKSELreg = BSP_PRV_START_BANK_VALUE;
```

設定値は `r_bsp_config.h` の `BSP_CFG_CODE_FLASH_START_BANK` で制御（デフォルト=0）。

**BANKSEL 状態の確認方法:**

```bash
rfp-cli -d RX72x -t "e2l:<serial>" -if fine -s 1500K \
  -auth id FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF \
  -rv FE7F5D00 128 -run -noquery
# FE7F5D20 の値を確認:
#   FF FF FF FF = bank0 起動（デフォルト）
#   F8 FF FF FF = bank1 起動（bank swap 後）
```

**factory MOT による1コマンドフラッシュ（推奨）:**

`mot_to_rsu.py --factory` で boot_loader + bank0 アプリ + bank1 アプリ + RSU ヘッダ + データフラッシュを
1つの MOT に結合。Config Area 衝突がなく、1コマンドで書き込み可能:

```bash
# 1. factory MOT 生成
python tools/mcu-tool-rx/mot_to_rsu.py --factory \
  --bootloader boot_loader/HardwareDebug/rx72n_boot_loader.mot \
  --mot aws_demos/HardwareDebug/aws_demos.mot \
  --key ../../sample_keys/secp256r1.privatekey \
  -o factory.mot --image-flag valid

# 2. 書き込み（最速設定: 1.5M, Verify 省略）
rfp-cli -d RX72x -t "e2l:<serial>" -if fine -s 1500K \
  -auth id FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF \
  -e -p factory.mot -run -noquery -nocheck-range
```

`--image-flag` オプション:
- `valid` (0xFC): boot_loader が即座に aws_demos にジャンプ（通常運用）
- `testing` (0xFE): boot_loader が integrity check → bank swap を実行（OTA テスト用）

注意: factory MOT は bank0/bank1 両方にアプリを書き込むため、boot_loader の mirror copy パス（フリーズ発生箇所）をスキップする。
フリーズ再現テストには factory MOT ではなく、boot_loader flash → UART .rsu ダウンロードの手順を使用すること。

**boot_loader + aws_demos の2段階フラッシュ（レガシー）:**

aws_demos のリセットベクタは `0xFFFBFFFC`（boot_loader 用のジャンプ先）であり、
ハードウェアリセットベクタ `0xFFFFFFFC` は boot_loader 側にある。
そのため aws_demos 単体では起動できず、boot_loader + aws_demos の両方が必要。

両者の Config Area (0xFE7F5D00) が衝突するため、1コマンドでの同時書き込みは不可（`E3000101: The data already exist and cannot be overwritten`）。2段階で書き込む:

```bash
# Step 1: boot_loader（Config Area 含む全消去 + 書き込み）
# -erase-chip は他の操作と併用不可のため2コマンドに分割
rfp-cli -d RX72x -t "e2l:<serial>" -if fine -s 1500K \
  -auth id FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF -erase-chip -noquery
rfp-cli -d RX72x -t "e2l:<serial>" -if fine -s 1500K \
  -auth id FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF \
  -p boot_loader.mot -v -run -noquery -nocheck-range

# Step 2: aws_demos（消去なし、書き込みのみ — boot_loader 領域を保持）
rfp-cli -d RX72x -t "e2l:<serial>" -if fine -s 1500K \
  -auth id FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF \
  -file aws_demos.mot -auto -noerase -run -noquery -nocheck-range
```

注意: 正規の運用では boot_loader → UART ダウンロード（`.rsu` ファイル）で aws_demos を転送する。
2段階フラッシュは開発・デバッグ用の代替手段。factory MOT 方式の方が高速かつシンプル。

**RSU (Renesas Secure Update) ファイルフォーマット:**

仕様書: [ルネサス MCU におけるファームウェアアップデートの設計方針](https://www.renesas.com/ja/document/apn/renesas-mcu-firmware-update-design-policy-rev100)

Microchip OTA Image 互換フォーマット（将来の MCU ベンダ間標準化を見据えた設計）。

| Offset | Component | Size |
|--------|-----------|------|
| 0x000 | Header (Magic Code, Image Flags, FW Verification Type) | 512B |
| 0x008 | Signature (ECDSA P-256) | 256B + size field |
| 0x10c | Option (Dataflash Flag, DF Start/End Address, Image Size) | |
| 0x200 | Descriptor (Sequence Number, Start/End/Exec Address, HW ID) | 256B |
| 0x300 | Application Binary (Code Flash) | N bytes |
| 0x300+N | Dataflash Binary (32KB padded) | 32KB |

- SCI ダブルバッファ: 32KB × 2（A/B 交互使用、割り込み駆動バイト単位受信）
- `dataflash_flag`: ヘッダに定義済みだが boot_loader コードでは未チェック（常にデータフラッシュ受信を行う）
- Dataflash Binary は SCI バッファサイズ（32KB）に合わせてパディングが必要

**aws_demos UART コマンド（COM6 経由、115200bps）:**

| Command | Function |
|---------|----------|
| `version` | ファームウェアバージョン読み出し |
| `freertos cpuload read` | FreeRTOS CPU 負荷確認 |
| `freertos cpuload reset` | CPU 負荷カウンタリセット |
| `dataflash info` | データフラッシュ情報（物理サイズ、割当サイズ、空き） |
| `dataflash read` | 全設定データ読み出し |
| `dataflash erase` | 全設定データ消去 |
| `dataflash write aws clientprivatekey` | AWS クライアント秘密鍵（PEM 入力モード） |
| `dataflash write aws clientcertificate` | AWS クライアント証明書（PEM 入力モード） |
| `dataflash write aws codesignercertificate` | OTA コード署名証明書（PEM 入力モード） |
| `dataflash write aws mqttbrokerendpoint <endpoint>` | MQTT ブローカーエンドポイント |
| `dataflash write aws iotthingname <name>` | IoT Thing 名 |
| `timezone <tz>` | タイムゾーン設定（例: `UTC+09:00`） |
| `reset` | ソフトウェアリセット |

データフラッシュはデュアルプレーン＋故障時復旧機構を備え、書き込み中の電源断に耐える設計。

## Changelog / 変更履歴

### 2026-03-01: fix: Phase 3 フリーズ — BANKSEL 未リセット問題の修正

**Root cause:** After a successful UART download, boot_loader executes `flash_toggle_banksel_reg()` to swap banks, changing BANKSEL from `0xFFFFFFFF` (bank0) to `0xFFFFFFF8` (bank1). On the next CI pipeline run, `rfp-cli -auto` (which uses `-e` = erase Code Flash + Data Flash only) does NOT erase Config Area. Since flash memory can only change bits from 1→0, writing `0xFFFFFFFF` over `0xFFFFFFF8` has no effect — BANKSEL stays at `0xFFFFFFF8`. This causes verify failure (exit code 1) and/or boot from wrong bank.

**根本原因:** UART ダウンロード成功後、boot_loader が `flash_toggle_banksel_reg()` で bank swap を実行し、BANKSEL が `0xFFFFFFFF`（bank0）→ `0xFFFFFFF8`（bank1）に反転する。次の CI パイプラインで `rfp-cli -auto`（内部的に `-e` = Code Flash + Data Flash のみ消去）を実行しても Config Area は消去されない。フラッシュの性質上ビット 1→0 のみ書き換え可能なため、`0xFFFFFFF8` の上に `0xFFFFFFFF` を上書きしても値は変わらない。結果として verify 失敗（exit code 1）やバンクマッピング不整合が発生する。

**Fix:** Changed `flash_boot_loader` job in `.gitlab-ci.yml` from `-auto` (`-e -p -v`) to `-erase-chip -p -v`. `-erase-chip` erases Config Area (including BANKSEL), resetting all bits to 1, so BANKSEL=`0xFFFFFFFF` is correctly written.

**修正:** `.gitlab-ci.yml` の `flash_boot_loader` ジョブで `-auto`（`-e -p -v`）→ `-erase-chip -p -v` に変更。`-erase-chip` は Config Area（BANKSEL 含む）も消去し全ビットを 1 に戻すため、BANKSEL=`0xFFFFFFFF` が正しく書き込まれる。

**Additional changes / その他の変更:**
- rfp-cli speed: 500K → 1500K（最大対応速度）
- Pipeline resumed: `workflow: rules: - when: never` を削除
- CLAUDE.md: BANKSEL の詳細解説、`-erase-chip` vs `-e` の違い、BSP による BANKSEL 埋め込みの仕組み、Phase 3 フリーズの再現シナリオ、BANKSEL 確認方法、factory MOT 手順、速度比較テーブルを追加
- CLAUDE.md: rfp-cli `-run` 必須の注意事項を追記
- CLAUDE.md: e2studio j24 レースコンディション、CLI ビルド手順を追記

### 2026-03-01: C# "Renesas Secure Flash Programmer" 廃止予定を明記

Documented deprecation of C# "Renesas Secure Flash Programmer" tool. All functionality (Initial tab = factory MOT generation, Update tab = RSU conversion) has been replaced by `mot_to_rsu.py` in mcu-tool-rx. The C# tool has a CUI bug and requires Visual Studio to build.

C# "Renesas Secure Flash Programmer" の廃止予定を CLAUDE.md に明記。全機能（Initial タブ = factory MOT 生成、Update タブ = RSU 変換）は mcu-tool-rx の `mot_to_rsu.py` で代替済み。C# ツールは CUI バグあり・VS 必須のため今後削除予定。

### 2026-03-01: RX 共通ツールを mcu-tool-rx サブモジュールに移行（MR !12）

Migrated `resolve_fit_modules.py` and `mot_to_rsu.py` to shared mcu-tool-rx repository as git submodule. Updated CI pipeline and CLAUDE.md references. Removed Phase 1/2 troubleshooting logs (root cause was missing FIT modules, now resolved).

`resolve_fit_modules.py` と `mot_to_rsu.py` を mcu-tool-rx 共有リポジトリに移行し、git submodule 化。CI パイプラインと CLAUDE.md のパス参照を更新。Phase 1/2 トラブルシューティングログは FIT モジュール未インストールが根本原因であり解消済みのため削除。

### 2026-03-01: FIT モジュール自動解決 + e2studio ヘッドレスビルド SMC 検証

Identified root cause of build failures on fresh machines: FIT module versions required by .scfg files were missing from local FITModules folder. Created `tools/mcu-tool-rx/resolve_fit_modules.py` to automate detection and download of missing modules from rx-driver-package versions.xml. Verified e2studio 2024-01 headless build with SMC code generation (0 errors, 103 warnings, 29s). Confirmed CC-RX v3.04 baseline: LCD stable after boot_loader + aws_demos flash via rfp-cli 2-step method.

ビルドマシンに .scfg が要求する FIT モジュールバージョンがインストールされていないことがビルドエラーの根本原因と判明。`tools/mcu-tool-rx/resolve_fit_modules.py` で不足モジュールの検出・ダウンロードを自動化。e2studio 2024-01 でヘッドレスビルド + SMC コード生成を検証成功。CC-RX v3.04 ベースラインで LCD 安定動作を確認（rfp-cli 2段階フラッシュ方式）。

**Key findings / 主な知見:**
- SMC は必要な FIT モジュールがローカルにない場合、エラーなしにコード生成をスキップする（サイレントスキップ）
- aws_demos は 27 FIT モジュール、boot_loader は 11 モジュールに依存（計30ユニーク）
- versions.xml (https://github.com/renesas/rx-driver-package/blob/master/versions.xml) に全697モジュールの URL が集約
- e2studio ヘッドレスビルドでは `AWS_IOT_MCU_ROOT` パス変数をワークスペース `.metadata` に事前定義が必要
- `-import` のパスは `file:///C:/...` URI 形式（`C:/...` はスキームエラー）
- boot_loader + aws_demos は Config Area 衝突により1コマンドで同時書き込み不可 → 2段階フラッシュ

### 2026-03-01: CLI ビルド（make + CC-RX）検証

Verified that all 3 projects can be built using GNU Make + CC-RX v3.04.00 directly, without e2studio. Makefiles are generated once by e2studio headless build, then `make` drives CC-RX (ccrx, lbgrx, rlink) to produce identical .mot files. boot_loader .mot was byte-for-byte identical to CI build output.

e2studio なしで GNU Make + CC-RX v3.04.00 による CLI ビルドを全3プロジェクトで検証成功。Makefile は e2studio ヘッドレスビルドで1回生成し、以後は make が CC-RX (ccrx, lbgrx, rlink) を直接呼び出して .mot を生成。boot_loader は CI ビルドとバイト単位で一致。

**Key findings / 主な知見:**
- PATH にスペース含むディレクトリ追加時は PowerShell 経由が安定（bash では短縮パス `PROGRA~2` が必要）
- `renesas_cc_converter` は e2studio CDT 内部ツールで CLI 環境には存在しない → .mot ターゲットのみビルドで回避
- aws_demos のサイズ差（144B）はリンク順序差によるもので機能的に同等

### 2026-03-01: fix: CC-RX toolchain v3.04.00 に戻す

Reverted CC-RX toolchain from v3.07.00 to v3.04.00 across all 3 projects. v3.07.00 caused aws_demos LCD to go dark after ~10 minutes on dashboard screen (hard fault suspected). v3.04.00 confirmed stable via Pipeline #177 + manual 10-minute soak test.

CC-RX ツールチェーンを v3.07.00 から v3.04.00 に全3プロジェクトで戻した。v3.07.00 では aws_demos のダッシュボード画面で約10分後に LCD が消灯する問題が発生（ハードフォルト推定）。v3.04.00 で Pipeline #177 + 10分放置テストにより安定動作を確認。

**MR:** !11 (branch: `fix/toolchain-v304`)

### 2026-02-28: CI/CD Phase 2 — UART test integration + mot→rsu converter + download step

Extended flash stage with UART boot test, .mot→.rsu converter, and firmware download step. Python mot_to_rsu.py was created as CUI replacement for C# "Renesas Secure Flash Programmer" (which had a CUI bug: missing private key arg for sig-sha256-ecdsa Update mode, and requires VS to build). Completed full build → flash → UART download pipeline after 11 pipeline iterations (#162-#172).

flash ステージに UART 起動テスト統合、.mot→.rsu Python コンバータ、ファームウェアダウンロードステップを追加。C# "Renesas Secure Flash Programmer" の CUI モードにバグ（`sig-sha256-ecdsa` Update モードで `textBoxUserPrivateKeyPath.Text` が空のまま署名処理に入る）があり、ビルドに VS が必要なため、Python で CUI を再実装。11回のパイプライン実行（#162-#172）を経て完全パイプラインを完成。

**Key changes / 主な変更:**
- `flash_boot_loader` ジョブ: `test_boot_loader.py --flash-cmd --diag` で flash + UART 起動確認を一括実行
- `tools/mcu-tool-rx/mot_to_rsu.py` — .mot→.rsu コンバータ（ECDSA P-256 署名対応）
  - C# FormMain.cs をリバースエンジニアリングして .rsu フォーマットを完全再現
  - 既存 `bin/updata/v202/userprog.rsu` の署名検証に成功（PASS）
  - `--verify` モードで既存 .rsu ファイルの解析・検証が可能
- `test_scripts/uart_test/test_uart_download.py` — UART バイナリダウンロード + 進捗モニタ
  - TX-only 成功判定（COM6 MCU→PC 間欠受信障害の回避策）
  - `"...OK"` / `"...NG"` パターンマッチ（`LIFECYCLE_STATE_TESTING` 内の `NG` 誤検出防止）
  - データフラッシュ（28KB）を 32KB にパディングして RSU に含有（SCI バッファサイズに合わせる）
- `download_aws_demos` ジョブ: aws_demos.mot → userprog.rsu 変換 → UART 送信 → boot_loader 経由で書き込み
- Pipeline #170: 初の全ステージ PASS（build 60s + flash 26s + download 207s）
- Pipeline #172: ALL PASS（3回連続実行で BANKSEL 問題なし確認）

**MR:** !9 (branch: `feature/cicd-flash-test`)

### 2026-02-27: CI/CD Phase 2 — flash boot_loader

Added flash stage to CI/CD pipeline using rfp-cli. Investigated power-on reset failure: initially suspected BANKSEL (dual-bank), but rfp-cli read verified BANKSEL=111b (correct). Root cause identified as on-board E2 Lite (RL78/G1C) holding RES# during USB power-on. Workaround: use rfp-cli `-run` to start MCU execution after flash. AC adapter (CN7) power-on reset test pending.

rfp-cli による flash ステージを CI/CD パイプラインに追加。パワーオンリセット問題を調査: 当初 BANKSEL（デュアルバンク）を疑ったが rfp-cli 読み出しで BANKSEL=111b（正常）を確認。根本原因はオンボード E2 Lite (RL78/G1C) が USB パワーオン時に RES# をホールドすることと判明。対策: rfp-cli `-run` で flash 後に MCU を実行開始。AC アダプタ (CN7) 給電でのパワーオンリセットテストは保留中。

**Key changes / 主な変更:**
- `.gitlab-ci.yml` に flash ステージ追加（`flash_boot_loader` ジョブ）
- `test_scripts/uart_test/test_boot_loader.py` — 診断モード付き UART テストスクリプト（将来用）
- rfp-cli 終了コードによる flash 成功検証

**MR:** !8 (branch: `feature/cicd-flash-test`)

### 2026-02-27: CI/CD Phase 1 — e2studio headless build

Set up GitLab CI/CD pipeline for headless build of all 3 e2studio projects (aws_demos, boot_loader, segger_emwin_demos). Approximately 20 pipeline iterations were needed to resolve path length issues, linked resource resolution, and build configuration problems.

e2studio ヘッドレスビルドによる CI/CD パイプライン Phase 1 を構築。3プロジェクト（aws_demos, boot_loader, segger_emwin_demos）全てのビルドに成功。パス長問題・リンクリソース解決・ビルド設定の問題解決に約20回のパイプライン実行を要した。

**Key changes / 主な変更:**
- `.gitlab-ci.yml` 新規作成（build ステージ）
- `.cproject` ツールチェーンバージョンを v3.07.00 に統一（aws_demos, boot_loader, segger_emwin_demos）
- NTFS ジャンクション戦略で Windows 260文字パス長制限を回避
- aws_demos のリンクリソースをジャンクションで物理化

**MR:** !7 (branch: `feature/cicd-build-stage`)

### 2026-02-27: Wiki migration to docs/

Migrated all GitHub Wiki pages (58 pages, English + Japanese) into the `docs/` directory within the repository.

GitHub Wiki の全ページ (58ページ、日英両方) をリポジトリ内の `docs/` ディレクトリに移行しました。

**Structure / 構成:**
```
docs/
├── README.md          # Top-level index (links to en/ja)
├── en/                # English documentation
│   ├── README.md      # English index (from Wiki Home)
│   ├── quick-start/
│   ├── features/
│   ├── developer/
│   ├── bare-metal/
│   ├── freertos/
│   └── tools/
├── ja/                # Japanese documentation
│   ├── README.md      # 日本語目次 (Wiki ホームから)
│   ├── quick-start/
│   ├── features/
│   ├── developer/
│   ├── bare-metal/
│   ├── freertos/
│   └── tools/
└── images/            # All images from Wiki
```

**Reasons for migration / 移行理由:**
- Wiki is not included when importing a GitHub project to GitLab
- `docs/` in the repository is version-controlled alongside code
- Enables PR-based review workflow for documentation changes
- Works with CI/CD pipelines (link checking, static site generation, etc.)

移行理由:
- GitHub → GitLab インポート時に Wiki は引き継がれない
- `docs/` はコードと同一リポジトリでバージョン管理される
- ドキュメント変更に対して MR ベースのレビューワークフローが使える
- CI/CD パイプライン（リンクチェック、静的サイト生成等）と連携できる

#### Migration details / 移行の詳細

**Approach / 方針:**

GitHub Wiki は独立した Git リポジトリ（`.wiki.git`）として管理されている。
GitLab の「GitHub からインポート」機能では Wiki は引き継がれないため、
Wiki リポジトリを直接 clone し、Python スクリプトで一括変換・配置した。

GitHub Wiki is stored as a separate Git repository (`.wiki.git`).
GitLab's "Import from GitHub" feature does not include the Wiki,
so we cloned the Wiki repo directly and used a Python script for batch conversion.

```bash
git clone https://github.com/renesas/rx72n-envision-kit.wiki.git
```

**Scale / 規模:**

| Item | Count |
|---|---|
| Total Wiki pages | 58 |
| English pages | 26 |
| Japanese pages | 30 |
| Skipped (stubs/meta) | 4 (`Quick-Start-Guide.md`=dummy, `1-Ether-TCP-IP-Web-Server_.md`=Now Editing, `_Footer.md`, `_Sidebar.md`) |
| Dead links (English pages that never existed) | 3 (`D2-audio.md`, `MEMS-mic.md`, `ESP32.md`) |
| Image/data files | 117 files in `data/` directory |
| Target categories | 6 (`quick-start`, `features`, `developer`, `bare-metal`, `freertos`, `tools`) |

**Migration script: `migrate_wiki.py` / 移行スクリプト:**

Python スクリプト（約330行）で以下を自動処理:

1. **PAGE_MAP**: Wiki ファイル名 → `(言語, カテゴリ, 新ファイル名)` の全量マッピング辞書
2. **言語判定**: ファイル名に日本語文字を含むか、`_` サフィックスの有無で英語/日本語を識別
   - `1-SCI_.md` → 英語（`_` サフィックス付き）
   - `1-SCI.md` → 日本語（サフィックスなし）
   - `ホーム.md` → 日本語（日本語ファイル名）
3. **`[[Wiki Link]]` → 相対リンク変換**: 正規表現で `[[ページ名]]` を検出し、WIKI_LINK_MAP 辞書で対応する相対パスに変換
4. **画像パス変換**: GitHub Wiki の画像 URL を `docs/images/` への相対パスに書き換え
   - `https://github.com/renesas/rx72n-envision-kit/wiki/data/xxx.png` → `../../images/xxx.png`
   - `https://raw.githubusercontent.com/wiki/renesas/rx72n-envision-kit/data/xxx.png` → `../../images/xxx.png`
5. **ファイル名正規化**: `Generate-new-project-(bare-metal).md` → `generate-new-project.md` のように kebab-case に統一

**Issues encountered / 遭遇した問題:**

1. **Windows パス問題**: Python の `/tmp/` パスが Windows 上で解決できなかった。
   `r"C:\Users\ishig\AppData\Local\Temp\..."` に書き換えて対応。

2. **GitLab protected branch**: `master` ブランチが保護されていたため直接 push 不可。
   feature ブランチ + MR ワークフローに切り替え。

3. **HTTPS → SSH 認証**: GitLab clone 時の HTTPS URL では push 時に認証失敗。
   remote を SSH (`git@shelty2.servegame.com:...`) に変更して対応。

4. **相対パス計算バグ（`get_relative_path()`）**: 初版では `en/README.md` からのリンクが
   `docs/` レベルまで上がってしまい、リンク切れが発生（33ファイルに影響）。
   原因は言語ディレクトリを超えて `..` を余分に付与していたこと。
   ```python
   # Bug: 常に docs/ レベルまで上がっていた
   parts_up.append("..")  # up to docs/
   parts_up.append("..")  # up to lang dir (これだけでよかった)

   # Fix: 言語ディレクトリ内に留まるよう修正
   if from_cat:
       parts_up.append("..")  # up from category dir to lang dir (のみ)
   ```
   画像パスは `docs/images/` にあるため `..` がもう1段必要で、そちらは正しかった。
   「同じ言語内のリンク」と「言語をまたぐ画像パス」で必要な `..` の段数が異なることが混乱の原因。

5. **日英間クロスリンク**: Wiki の Home ページ冒頭にある「日本語ページはこちら: [[ホーム]]」は
   Wiki 内リンク書き換え辞書（同一言語内）では処理できない。
   手動で `[ホーム](../ja/README.md)` に修正。

6. **bare-metal リンク表示名の `1+` プレフィックス**: Wiki 原文の `[[1+SCI_]]` が
   そのまま `[1+SCI_](bare-metal/sci.md)` に変換されてしまう。
   `1+` は Wiki 内でのソート用プレフィックスのため、手動で `[SCI](bare-metal/sci.md)` に整理。

7. **GitHub user-images CDN 画像**: `https://user-images.githubusercontent.com/...` 形式の
   画像は認証なしではダウンロード困難。現状は外部 URL のまま残している（要対応）。

**MR history / MR 履歴:**

| MR | Content | Files changed |
|---|---|---|
| !1 | Initial wiki migration (58 pages + 117 images) | ~180 files |
| !2 | Fix GitHub account name, add project goals to CLAUDE.md | 2 files |
| !3 | Fix broken relative links (33 files), CLAUDE.md status update | 33 files |
| !7 | CI/CD Phase 1: e2studio headless build pipeline | .gitlab-ci.yml + 3 .cproject + CLAUDE.md |
