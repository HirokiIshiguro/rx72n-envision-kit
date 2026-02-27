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
| 3 | Set up CI/CD pipeline | In progress (Phase 1 done) |
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
| 2 | flash（rfp-cli）+ UART テスト自動化 | In progress (flash done, UART 実装準備中) |
| 3 | FreeRTOS LTS 最新版適用（[iot-reference-rx](https://github.com/renesas/iot-reference-rx) 最新リリースタグ） | Planned |
| 4 | AWS 接続を含む OTA テスト | Planned |
| 5 | RX72N Envision Kit 複数台でのフリートプロビジョニング＋OTA 一斉実施の全自動テスト | Planned |

### Build environment / ビルド環境

- **IDE:** e2 studio 2025-12（`C:\Renesas\e2_studio_2025_12\eclipse\e2studioc.exe`）
- **Compiler:** CC-RX v3.07（3プロジェクト共通。元は v3.04/v3.01 だったが Runner 環境に合わせて統一）
- **Runner tag:** `run_ishiguro_machine`（Windows 11、RX72N Envision Kit 物理接続済み）
- **Workspace:** `C:\workspace_rx72n`（hello_world とは別ディレクトリ）

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
`libraries/coreSNTP` は Git サブモジュールのため、`GIT_SUBMODULE_STRATEGY: recursive` が必要。

**ビルド方式:**
hello_world_with_claude_on_cicd と同じ e2studio ヘッドレスビルドパターンを採用。
3プロジェクトを1回の e2studio 起動でまとめてインポート＆ビルドする。
ビルドログは 15MB+ になるため、`Tee-Object | Out-Null` でファイルに保存しつつ
job log への出力を抑制（GitLab の 4MB ジョブログ制限を回避）。

### Phase 1 troubleshooting log / Phase 1 トラブルシューティング記録

Phase 1 完了まで約20回のパイプライン実行を要した。以下は主要な問題と解決策の記録（Zenn 記事素材）。

**1. CC-RX コンパイラバージョン不一致（パイプライン #129）**
- 症状: `E0562005: Specified option "lang=cpp" is not valid`（boot_loader, segger_emwin_demos）
- 原因: `.cproject` に記載のツールチェーン v3.04.00/v3.01.00 が Runner マシンの v3.07.00 と不一致
- 対策: `.cproject` のツールチェーンバージョンを v3.07.00 に統一
- 備考: 元のバージョン (v3.04) でCLIビルドが通るかは今後検証予定（当時ベトナムチームが GitLab CI/CD で動かしていた実績あり）

**2. CC-RX F0520005: Cannot open source file（パイプライン #136-138）**
- 症状: `trcStreamingPort.c(137):F0520005:Could not open source file "rx72n_envision_kit_system.h"`
- 原因: SubCommand.tmp 内のインクルードパスが最長251文字 → ヘッダファイル名を加えると281文字 > 260 MAX_PATH
- 試行錯誤: SubCommand.tmp のパスを sed 的に置換する案 → make がコンパイル時に毎回再生成するため無効
- **解決策: NTFS ジャンクション `C:\rx72n-src` → `$CI_PROJECT_DIR` で68文字を削減**

**3. Git サブモジュール未初期化（パイプライン #139）**
- 症状: `No rule to make target 'C:/rx72n-src/libraries/coreSNTP/source/core_sntp_client.c'`
- 原因: `libraries/coreSNTP` が Git サブモジュールで、初期化されていなかった
- 解決策: `GIT_SUBMODULE_STRATEGY: recursive` を `.gitlab-ci.yml` の variables に追加

**4. Duplicate symbol（パイプライン #140）**
- 症状: `E0562300: Duplicate symbol "_d2_getframebuffer"` in `application_code/smc_gen/r_drw2d_rx/...`
- 原因: `src/smc_gen` 全体をジャンクション化 → `.project` の `application_code/smc_gen` リンクリソースと同じ物理ディレクトリを指すため、CDT が同じソースを2回コンパイル
- 解決策: `src/smc_gen` 全体ではなく `src/smc_gen/r_config` のみジャンクション化（インクルードパス解決のみ）

**5. r_bsp_config.h が見つからない（パイプライン #141）**
- 症状: `Could not open source file "r_bsp_config.h"`（6ターゲット失敗）
- 原因: `src/smc_gen` ジャンクションを除去したことで `${workspace_loc:/${ProjName}/src/smc_gen/r_config}` インクルードパスが解決不能に
- 解決策: `src/smc_gen/r_config` のみをジャンクション化する「ターゲット型ジャンクション戦略」

**6. Stale Makefile / HardwareDebug キャッシュ（パイプライン #131 等）**
- 症状: `make: *** No rule to make target 'clean'. Stop.`
- 原因: 前回ビルドの HardwareDebug ディレクトリに残った Makefile が現在のソース構造と不整合
- 解決策: ビルド前に各プロジェクトの `HardwareDebug/` ディレクトリを削除（`-cleanBuild` に変更）

**7. ジャンクション経由のコピーエラー（パイプライン #142）**
- 症状: e2studio exit code 0（ビルド成功）だがジョブ失敗
- 原因: `C:\rx72n-src\...\aws_demos.mot` と `$CI_PROJECT_DIR\...\aws_demos.mot` がジャンクション経由で同一物理パス → Copy-Item が失敗
- 解決策: 不要なコピー処理を削除。ビルド出力はソースディレクトリ直下の `HardwareDebug/` に生成されるため、artifacts パスで直接指定

**最終結果: パイプライン #143 で全3プロジェクトのビルド成功（.mot ファイル生成確認済み）**

### Phase 2 troubleshooting log / Phase 2 トラブルシューティング記録

Phase 2 では boot_loader の flash 書き込み（rfp-cli）と UART 起動確認テストを実装。
パイプライン #147〜#154 の8回の実行を通じて、RX72N デュアルバンクフラッシュの根本的な問題を発見した。

**1. UART readline タイムアウト vs flash 所要時間（パイプライン #150）**
- 症状: flash 成功（exit code 0）だが UART テスト失敗。`no data received within 10s`
- 原因: rfp-cli の flash 書き込みに約13秒かかるが、pyserial の readline timeout が10秒で先にタイムアウト
- 対策: flash スレッドが alive なら continue して読み取りを継続

**2. readline ポーリング回数不足（パイプライン #151）**
- 症状: 2回の readline（各10秒）で合計20秒待機するも受信なし
- 原因: flash 完了（t=12.5s）後に MCU が出力するはずのデータが readline #2 のウィンドウ内で取れない
- 対策: readline をやめ、ノンブロッキング（timeout=0）+ 50ms ポーリング + 30秒全体タイムアウトに書き換え

**3. COM6 で一切データ受信なし（パイプライン #152）**
- 症状: `in_waiting=0` が30秒間継続。raw_bytes=0
- 分析: タイミング問題ではなく、根本的にデータが来ていない
- 対策: COM6（オンボード RL78/G1C）と COM7（PMOD FTDI）を同時監視する診断モード追加

**4. 全ポートで受信なし — パワーオンリセット問題の発見（パイプライン #153）**
- 症状: COM6 (VID=1115/Renesas), COM7 (VID=1027/FTDI) いずれも raw_bytes=0
- 手動検証:
  - rfp-cli `-run` → LCD に "RX72N secure boot program" 表示 + COM6 で UART 出力受信成功
  - E2 Lite USB ケーブル抜去 → パワーオンリセット → LCD 真っ黒、boot_loader 起動せず
- **初期仮説（否定済み）: BANKSEL（デュアルバンク起動バンク選択）の問題**
  - rfp-cli `-rv` で OFSM 読み出し → BANKSEL = `FFFFFFFF` (BANKSWP=`111b` = バンク0 から起動) → 正常
  - MDE = `FFFFFF8F` → リトルエンディアン + デュアルモード → 正常
  - リセットベクタ (FFFFFFFC) = `FFFC443E` → boot_loader コード領域内 → 正常
  - **BANKSEL は原因ではないと確定**
- **根本原因: オンボード E2 Lite (RL78/G1C) によるリセットホールド**
  - E2 Lite 別冊マニュアル (R20UT0399JJ): 「デバッグ終了後にエミュレータを取り外してマイコン単体で動作させることは保証しておりません」「E2 Lite が接続されていない状態での最終評価を必ず実施してください」
  - RX72N Envision Kit はオンボード E2 Lite (RL78/G1C = U9) を搭載。E2 Lite USB (CN8) 給電時は RL78/G1C がパワーオンリセット時に RX72N の RES# をホールドすると推定
  - rfp-cli `-run` → E2 Lite 経由でリセット解除＋実行開始 → **動作する**
  - パワーオンリセット（USB 抜き差し）→ E2 Lite がリセットホールド → **動作しない**
  - **回路図確認:** CN7 (DC ジャック, 5V センタープラス) による E2 Lite USB 非依存の給電経路あり
- **対策:** CI/CD では rfp-cli `-run` で書き込み＋実行開始し、直後に UART 出力を捕捉する
- **未検証:** CN7 (AC アダプタ) 給電でのパワーオンリセット起動（5V アダプタ調達後に検証予定）

**BANKSEL / デュアルバンク HW マニュアル調査結果:**
- BANKSEL レジスタ (FE7F 5D20h): BANKSWP[2:0] で起動バンクを選択。`111b` = バンク0 から起動、`000b` = バンク1 から起動。ブランク品は `FFFF_FFFFh` (=`111b`)
- MDE レジスタ (FE7F 5D00h): BANKMD[6:4] でバンクモード選択。`000b` = デュアル、`111b` = リニア
- OFSM は物理的にバンク0 に紐づいていると推測される（[r_flash_type4.c](https://github.com/renesas/rx-driver-package/blob/b5227bc4601e83c0464bcdf1ef4104accb7fad51/source/r_flash_rx/r_flash_rx_vx.xx/r_flash_rx/src/flash_type_4/r_flash_type4.c#L507) 参照）
- 参考: [RX72N ハードウェアマニュアル](https://www.renesas.com/ja/document/mah/rx72n-group-users-manual-hardware) 62章（フラッシュメモリ）

**5. COM ポートの排他制御 — 人間と CI の共存問題**
- 症状: CI パイプラインと TeraTerm が同じ COM ポートを取り合う可能性
- 経緯: デバッグ中に石黒さんが TeraTerm で手動確認 → 閉じ忘れると CI がポートを開けない
- 教訓: 一人で開発していると絶対に体験しない「COM ポートの取り合い」が、Claude と人間の協業で発生
- 対策: CI 実行前に TeraTerm 等のシリアルモニタを閉じておくこと

### Hardware reference / ハードウェアリファレンス

**UART ポート構成:**

| SCI チャネル | ピン | コネクタ | 変換チップ | COM ポート | VID |
|---|---|---|---|---|---|
| SCI2 | P12 (TXD2) / P13 (RXD2) | CN8 (オンボード) | RL78/G1C (USB-シリアル) | COM6 | 045B (Renesas) |
| SCI7 | P90 (TXD7) / P92 (RXD7) | CN6 (PMOD) | FTDI (外付け拡張基板) | COM7 | 0403 (FTDI) |

- SW3-2: CN8 の接続先を RX72N / ESP32 で切り替え
- E2 Lite: オンボードチップ搭載（外付けハードウェアではない）
- boot_loader の UART 設定: `r_bsp_config.h` → `MY_BSP_CFG_SERIAL_TERM_SCI (2)`, 115200bps

**Flash ツール:**

```
rfp-cli -device RX72x -tool "e2l:<serial>" -if fine -speed 500K \
  -auth id FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF -auto <mot_file> -run -noquery
```

- Flash 所要時間: 約13秒（erase + write + verify + config area + disconnect）
- `-run`: プログラム書き込み後に MCU を実行開始（BANKSEL を無視して書き込んだバンクから起動）

## Changelog / 変更履歴

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
