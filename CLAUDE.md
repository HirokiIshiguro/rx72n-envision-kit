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
| 4 | Replace FreeRTOS with latest Renesas IoT reference implementation ([iot-reference-rx](https://github.com/renesas/iot-reference-rx)) | In progress (Phase 8b-4 OTA revalidation, Issue #10) |

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
| 4 | boot_loader の UART ダウンロードを COM6 (SCI2, 115200bps) から COM7 (SCI7 PMOD FTDI, 921600bps) に変更（要ファームウェア SCI ポート変更。ダウンロード時間短縮でデバッグ効率改善） | Done |
| 5 | e2studio 2024-01 / CC-RX v3.04 環境で既存機能の動作検証（AWS 接続、SD カードによるファームウェアアップデート、各種コマンドレスポンス） | Done (MR !20) |
| 6 | e2studio 2025-12 / CC-RX v3.07 ツールチェーン更新 + 既存機能の動作検証 | Done (MR !21) |
| 7 | AWS IoT OTA テスト自動化（S3 + OTA ジョブ → MQTT ダウンロード → 署名検証 → バンクスワップ → 自己テスト）（1台） | Done (MR !23) |
| 8 | FreeRTOS LTS 最新版適用（[iot-reference-rx](https://github.com/renesas/iot-reference-rx) 最新リリースタグ）。作業リポジトリ: [iot-reference-rx (GitLab)](https://shelty2.servegame.com/oss/import/github/renesas/iot-reference-rx)。CK-RX65N V1 で先行構築（Phase 8a）→ RX72N に移植（Phase 8b）の2段階アプローチ。詳細計画は [iot-reference-rx の CLAUDE.md](https://shelty2.servegame.com/oss/import/github/renesas/iot-reference-rx/-/blob/main/CLAUDE.md) を参照 | In progress (Phase 8b-4 OTA revalidation, Issue #10) |
| 9 | AWS 接続を含む OTA テスト（1台、新 FW で再検証） | Planned |
| 10 | AWS 接続を含むフリートプロビジョニング テスト（1台。iot-reference-rx の FP デモを活用） | Planned |
| 11 | AWS 接続を含むセカンダリ MCU ファームウェアアップデート テスト（RX72N → FPB-RX140） | Planned |
| 12 | OTA × 3 一斉テスト | Planned |
| 13 | フリートプロビジョニング × 3 + 一斉 OTA テスト | Planned |
| 14 | フリートプロビジョニング × 3 + セカンダリ MCU アップデート × 2 + 一斉 OTA テスト（フル構成） | Planned |
| - | UART テストスクリプトの共通ライブラリ化（[mcu-test/uart](https://shelty2.servegame.com/oss/experiment/generic/scripts/python/mcu-test) へ切り出し、git submodule で各プロジェクトから参照） | Planned |
| - | mot_to_rsu コンバータの共通部品化（git submodule で各プロジェクトから参照） | Done (MR !12) |
| - | AWS CLI / IoT Core ノウハウを `oss/experiment/cloud/aws/iot-core/claude` に export | Done (MR !1 on iot-core/claude) |
| - | SD カード更新の CI/CD 完全自動化: UART ファイル転送コマンド (`sdcard write`) + GUI ボタン操作コマンド (`touch`) の実装（ファームウェア変更） | Done (MR !20) |
| - | パイプライン条件分岐（`RUN_AWS_TESTS` / `RUN_SD_UPDATE_TEST` / `RUN_OTA_TEST` 変数で各テストを選択実行） | Done (MR !23) |
| - | BUTTON_03 タッチ問題: J-Link 実機デバッグで WM_NOTIFICATION_CLICKED 発火確認 | Planned |
| - | Runner 分離: ビルド専用 (Windows) / 実機操作専用 (Raspberry Pi) に分けて並列度向上 | Done (MR !32) |

**OTA monitor 調査の引継ぎ先:**
- 旧 FreeRTOS ベースの OTA monitor 調査ログと、最新 FreeRTOS 置換前の引継ぎは [MR !41](https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit/-/merge_requests/41) を参照
- 本件の深掘りは、可能であれば最新 FreeRTOS / `iot-reference-rx` 置換ブランチ側を優先する

### Phase 8b Migration Plan / 移行計画

Phase 8b is tracked under the parent issue [#11](https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit/-/issues/11).
The work is intentionally split so that FreeRTOS migration, OTA recovery, and GUI reintegration do not
fail at the same time.

Phase 8b は親 issue [#11](https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit/-/issues/11)
で管理する。FreeRTOS 移行、OTA 再接続、GUI 再統合を同時に壊さないため、作業は分割して進める。

| Step | Issue | Goal |
|------|-------|------|
| 8b-1 | [#7](https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit/-/issues/7) | `phase8b/` に upstream baseline と seed project を取り込み、RX72N port の着地点を固定 |
| 8b-2 | [#8](https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit/-/issues/8) | RX72N boot loader を新 baseline 上で build 可能にする |
| 8b-3 | [#9](https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit/-/issues/9) | RX72N app を新 baseline へ移植し MQTT baseline を回復 |
| 8b-3b | [#13](https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit/-/issues/13) | `phase8b/` の `build -> flash -> provision -> MQTT` を CI へ接続 |
| 8b-4 | [#10](https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit/-/issues/10) | OTA を新 baseline 上で再検証 |
| 8b-5 | [#12](https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit/-/issues/12) | GUI / SD update / Envision Kit 独自 UX を再統合 |

**Execution order / 実行順:**
- First target is a headless baseline: `build -> flash -> provision -> MQTT -> OTA`.
- GUI (`emWin` / AppWizard), SD update UX, and other Envision Kit specific functions come later.
- MCUboot migration is a separate track and must not be mixed into the initial FreeRTOS baseline port.

**Repo layout target / 目標構成:**
- Current repo still uses the legacy lower-case tree (`projects/`, `vendors/`, `libraries/`, `freertos_kernel/`).
- Target layout follows `iot-reference-rx`: `Common/`, `Configuration/`, `Demos/`, `Middleware/`, `Projects/`, `Test/`.
- Initial RX72N project names are expected to be `aws_ether_rx72n_envision_kit` and `boot_loader_rx72n_envision_kit`.
- Phase 8b-1 uses `phase8b/` as a staging root so the new layout can be prepared without breaking the current tree on Windows.

**Windows filesystem constraint / Windows ファイルシステム制約:**
- This repository currently runs with `core.ignorecase=true` on Windows.
- Case-only rename steps such as `projects` -> `Projects` or `vendors` -> `Middleware` staging must be done carefully,
  typically via temporary names or in a case-sensitive environment.
- Therefore Phase 8b-1 documents and prepares the migration first; it does not attempt a destructive top-level rename yet.

Detailed notes are tracked in [`docs/phase8b-migration-plan.md`](docs/phase8b-migration-plan.md).

**Current status / 現在の進捗:**
- 8b-1 は完了。`phase8b/` staging root に `iot-reference-rx` baseline を取り込み済み。
- 8b-2 は headless build gate を通過。`boot_loader_rx72n_envision_kit` は e2studio 2025-12 + CC-RX で `.mot` 生成まで確認。
- 8b-2 の残課題は runtime 妥当性確認。`R_BSP_ClockReset_Bootloader()` は RX72N 側でまだ暫定 no-op のため、flash 実機確認前に本実装へ置き換える。
- 8b-3 は headless build gate を通過。`aws_ether_rx72n_envision_kit` は e2studio 2025-12 + CC-RX で `.abs` / `.mot` / `.x` 生成まで確認。
- 8b-3 では `build_phase8b` job と `RUN_PHASE8B_BUILD_ONLY` モードを追加し、`phase8b/` のみを対象にした Windows build-only gate を CI へ接続済み。
- 8b-3b は完了。Issue [#13](https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit/-/issues/13) を閉じ、`RUN_PHASE8B_BASELINE` と phase8b 専用 helper / job により `build_phase8b -> flash/download -> provision -> MQTT` の hardware baseline を CI へ再接続した。
- 8b-4 は Issue [#10](https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit/-/issues/10) で進める。次段の主タスクは `RUN_PHASE8B_OTA` による phase8b 専用 OTA pipeline（`build_phase8b_ota -> prepare_phase8b_ota -> phase8b_ota_create_job/monitor/finalize`）の導線整備。
- 2026-03-11 の pipeline `#588` で `build_phase8b_ota` は成功し v1/v2 RSU 生成まで確認した。一方 `prepare_phase8b_ota` は Raspberry Pi runner `ef-saffti-001-rpi-003-rx72nek` 上で `E3000201: Cannot find the specified tool.` により失敗し、現行 CI 変数束（`DEVICE_ID=rx72n-01`, `E2LITE_SERIAL/UART_PORT/COMMAND_PORT` の単一セット）が 3 セット構成をまだ表現できていないことが分かった。
- 2026-03-11 の pipeline `#590` では `prepare_phase8b_ota` が `rpi-001` で成功した一方、`phase8b_ota_monitor` は `rpi-002` にスケジュールされて `UART_PORT` mismatch で失敗した。generic tag のみでは OTA prepare/run が同じ実機に stick せず、runner/device affinity の導入が必要。
- 同じ `#590` で `phase8b_ota_create_job` は旧 RSU parser が `RELFWV2` を理解できず失敗したため、`test_ota.py` を legacy `Renesas` / phase8b `RELFWV2` の両形式対応へ更新した。ローカル再現で phase8b RSU の payload/signature 抽出までは確認済み。
- 2026-03-11 の pipeline `#592` では `prepare_phase8b_ota` / `phase8b_ota_monitor` が同じ `rpi-001` で実行され、`phase8b_ota_create_job` も成功した。残る失敗は OTA monitor のみだが、trace を追うと `prepare_phase8b_ota` が実際には flash 後で止まっており、`UART download -> provisioning -> reset` まで到達していなかった。
- 原因は `tools/ci/acquire_pi_device_lock.sh` を同一 job 内で再度 `source` したとき、`DEVICE_LOCK_HELD=1` 分岐で `exit 0` し outer shell ごと終了していたこと。helper を `return` 優先に修正し、同一 job 内で lock helper を再利用しても後続 step が継続するようにした。
- 2026-03-11 の pipeline `#594` では、`prepare_phase8b_ota` が今度は 1 block 目を越えたものの、2 block 目開始時に `/tmp/gitlab-device-locks/rx72n-01.lock` の再取得待ちで停滞した。GitLab shell 実行形態では block 間で lock 状態を素直に引き回せない前提と見なし、`prepare_phase8b_ota` は `flash -> UART download -> provisioning -> reset` を 1 つの script block に統合した。
- `.pi_device_job` の `resource_group` は現状 `rx72n-device` 固定で、3 セット runner を導入しても job は device 全体で直列化される。並列度を上げるには、hardware-config 側で runner ごとの device 変数束と lock/resource の分離が必要。
- 2026-03-11 時点で repo 側は `DEVICE_RUNNER_TAG` / `DEVICE_RESOURCE_GROUP` override と `rx72n-02` / `rx72n-03` の `device_id` を受けられる形へ更新した。つまり CI 側は set 固定実行の受け皿を持ったが、実運用には runner 側の set 別 tag 付与と、hardware-config / CI Variables への set #2 / #3 個体値登録がまだ必要。
- さらに `rfp-cli -d RX72x -lt` が接続中 E2 Lite の serial を返さず tool 種別一覧だけを返すことが分かったため、repo 側は `RFP_TOOL=e2l` を既定にして serial 未指定でも 1 Pi = 1 E2 Lite 構成で書き込みできるように更新した。これで phase8b OTA の残 blocker はほぼ `runner tag / UART path / MAC 設定` へ絞り込めた。
- 8b-3/8b-4 共通の残課題は warning cleanup と OTA 実行安定化。`r_tsip_rx` の RX72N 正式化、`C_LITTLEFS_*` / `C_USER_APPLICATION_AREA` section warning の整理、phase8b 上での OTA monitor 再現性確認を次段で進める。

### Phase 8b precheck: ROM budget for MCUboot + latest FreeRTOS

Issue: `#5`

MCUboot 移行に関する OTA 観点の整理は、OTA プロジェクトの
[CLAUDE.md](https://shelty2.servegame.com/oss/experiment/embedded/mcu/elemental/ota/-/blob/main/CLAUDE.md)
へ集約する。本節は RX72N Envision Kit 側の project-local な sizing
メモと判断根拠を残す位置づけとする。

- RX72N は code flash 4MB を持つが、dual-bank 前提では片系の実行イメージとして
  使える容量を **2MB/bank** とみなして評価する
- `iot-reference-rx` 由来の最新 FreeRTOS 基盤を RX72N に移植するだけでなく、
  将来的な boot loader は Renesas オリジナル実装から **MCUboot** へ置き換える前提で
  容量検証を行う

2026-03-08 時点の rough sizing（Motorola S-record の data byte 合計）:

| Image | Source | Rough size |
|------|--------|-----------:|
| 現行 RX72N boot_loader | `rx72n-envision-kit` build artifact (`#380` / job `#1631`) | 54,235 B |
| 現行 RX72N aws_demos | `rx72n-envision-kit` build artifact (`#380` / job `#1631`) | 1,078,627 B |
| CK-RX65N boot loader | `iot-reference-rx` build artifact (`#423` / job `#1755`) | 32,057 B |
| CK-RX65N userprog | `iot-reference-rx` build artifact (`#423` / job `#1755`) | 472,254 B |

アドレス帯の rough 観測:

- 現行 RX72N `aws_demos.mot` は主に `0xFFE00000` 帯へ約 1.00 MiB、
  `0x00100000` 帯へ約 28 KiB を配置
- 現行 RX72N `rx72n_boot_loader.mot` は主に `0xFFF00000` 帯へ約 51 KiB を配置
- `iot-reference-rx` の `userprog.mot` は主に `0xFFF00000` 帯へ約 430 KiB、
  `0xFFE00000` 帯へ約 31 KiB を配置

MCUboot package の初期確認:

- 公式 RX package: `rx-driver-package/source/rm_mcuboot`
- `rm_mcuboot` v1.01 は RX72N Group を support 対象に含む
- `rm_mcuboot_vx.xx_extend.mdf` の RX72N/RX72M 既定値は以下
  - `RM_MCUBOOT_CFG_MCUBOOT_AREA_SIZE = 0x10000`
  - `RM_MCUBOOT_CFG_APPLICATION_AREA_SIZE = 0x1F0000`
  - `RM_MCUBOOT_CFG_SCRATCH_AREA_SIZE = 0x10000`（swap mode 時）
- 既定 config は `overwrite only` + `validate primary slot` 有効 +
  `ECDSA P-256` 署名検証 + encryption 無効
- この設定から、Renesas の公式 package 自体は
  **RX72N dual-bank を前提に MCUboot + 約 0x1F0000 の application slot**
  を想定していると読める

2026-03-08 ローカル headless build の `.map` 実測
（`tools/analyze_ccrx_map.py` で再現可能）:

| Image | ROMDATA | PROGRAM | Flash-like total | Budget | Headroom |
|------|--------:|--------:|-----------------:|-------:|---------:|
| 現行 RX72N boot_loader | 10,367 B | 43,868 B | 54,235 B | `0x10000` (65,536 B) | 11,301 B |
| 現行 RX72N aws_demos | 352,493 B | 727,062 B | 1,079,555 B | `0x1F0000` (2,031,616 B) | 952,061 B |
| RX72N MCUboot lower-bound scratch build | 4,526 B | 25,883 B | 30,409 B | `0x10000` (65,536 B) | 35,127 B |

2026-03-11 追記: MCUboot lower-bound scratch build の前提

- isolated scratch project で RX72N BSP/flash driver + MCUboot `bootutil` / `flash_map` / `tlv` / `swap_scratch`
  だけを組み合わせ、headless build で `.map` を採取
- build 前提は `overwrite only`、unsigned、logging off、`tinycrypt` SHA-256 のみ
- `abort()` / SCI low-level char I/O は stub 実装
- 現行 boot_loader 固有の GUI / UART command / key storage / magic code section、
  および `rm_mcuboot` の TSIP/RSIP・署名検証・encryption は未含有
- したがって 30,409 B は production 相当サイズではなく、
  **RX72N 上で MCUboot core がどの程度の下限で収まるか** を見るための lower-bound

補足:

- app slot 側は、現行 `aws_demos` 基準でも **約 952 KiB の headroom**
  があり、2MB/bank 全体では現時点で逼迫していない
- 一方、boot area `0x10000` は現行 Renesas boot loader 基準で
  **余白が 11,301 B** しかないため、
  MCUboot fit 判定は boot side の実ビルドで取るべき
- 仮に MCUboot 導入で boot area を `0x20000` (128 KiB) に増やしても、
  app slot は `0x1E0000` となり、現行 `aws_demos` 比で
  **886,525 B の headroom** が残る
- 現行 `aws_demos` の flash-heavy 要素は主に
  emWin 画像/フォント資産、PKCS11/mbedTLS、OTA/coreMQTT であり、
  FreeRTOS kernel 自体は主に RAM (`heap_4`) 側に効いている
- `RM_MCUBOOT_CFG_SIGN = RSA 2048` や image encryption 有効化は
  boot size を押し上げる候補なので、worst-case 別計測が必要
- 2026-03-11 の lower-bound scratch build では
  **MCUboot core 単体は `0x10000` に対して約 35 KiB の headroom**
  を残しており、issue `#5` の主不確実性は
  「MCUboot core が入るか」よりも
  「RX72N 向け実構成差分がどこまで headroom を削るか」に移っている

暫定判断:

- **application slot 容量は現時点で no-go には見えない**
- ただし `rm_mcuboot` は FIT module であり、実サイズ確認には
  **RX72N 向け最小組み込みビルド** が必要
- 2026-03-11 の lower-bound では
  **MCUboot core は boot area `0x10000` に収まる**
- 残る最優先の不確実性は、
  **RX72N 向け `rm_mcuboot` 実構成（ECDSA/TSIP/RSIP/metadata/section 配置込み）でも
  `0x10000` を維持できるか** である
- go/no-go は issue `#5` で
  `MCUboot + latest FreeRTOS app + OTA metadata` の実測を取ってから判定する

### パイプライン変数 / Pipeline Variables

GitLab UI の「Run Pipeline」画面でオーバーライド可能。

**ハードウェア依存変数（hardware-config リポジトリで一元管理）:**

Windows の COM ポート番号や Raspberry Pi の `/dev/serial/by-id/...` パス、E2 Lite シリアル番号は
接続先や USB 列挙順で変わるため、`.gitlab-ci.yml` にはハードコードせず `/oss` グループの CI/CD
Variables から取得する。変更時は hardware-config リポジトリの CLAUDE.md を更新し、GitLab の
CI/CD Variables を変更すること。

| CI/CD Variable | .gitlab-ci.yml 変数 | 説明 |
|---|---|---|
| `E2L_SERIAL_ENVISION_KIT_RX72N_ECN1` | `E2LITE_SERIAL` | E2 Lite シリアル番号 (ECN1) |
| `UART_PORT_ENVISION_KIT_RX72N_CN6` | `UART_PORT` | SCI7 ログ/ダウンロード (CN6 PMOD, 921600bps)。Pi では `/dev/serial/by-id/...` を設定 |
| `UART_PORT_ENVISION_KIT_RX72N_CN8` | `COMMAND_PORT` | SCI2 コマンド (CN8 USB Serial, 115200bps)。Pi では `/dev/serial/by-id/...` を設定 |

`device_config_loader.py` も `COMMAND_PORT` / `UART_PORT` / `E2LITE_SERIAL` 環境変数を検出すると
`device_config.json` の値をオーバーライドする。

**テスト制御変数:**

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `RUN_AWS_TESTS` | `"true"` | AWS 接続テスト（provision, MQTT）を実行するか |
| `RUN_HW_HEALTHCHECK` | `"true"` | 実機の段階的ヘルスチェック（USB/serial 列挙、boot_loader バナー、aws_demos プロンプト）を実行するか |
| `RUN_SD_UPDATE_TEST` | `"false"` | SD カードファームウェア更新テストを実行するか |
| `RUN_OTA_TEST` | `"true"` | OTA テスト（build_ota, prepare_ota, ota_create_job, ota_monitor, ota_finalize）を実行するか |
| `RUN_PHASE8B_BUILD_ONLY` | `"false"` | `phase8b/` の build-only gate (`build_phase8b`) のみを実行するか |
| `RUN_PHASE8B_BASELINE` | `"false"` | `phase8b/` の hardware baseline (`build_phase8b -> flash/download -> provision -> MQTT`) のみを実行するか |
| `RUN_PHASE8B_OTA` | `"false"` | `phase8b/` の OTA 再検証 (`build_phase8b_ota -> prepare_phase8b_ota -> phase8b_ota_create_job/monitor/finalize`) のみを実行するか |
| `DEVICE_ID` | `"rx72n-01"` | `device_config.json` / AWS 証明書変数名に対応する論理デバイス ID。3 セット運用時は `rx72n-02` / `rx72n-03` へ切り替える |
| `RFP_TOOL` | `"e2l"` | `rfp-cli -tool` に渡す値。1 Pi = 1 E2 Lite 構成では generic `e2l` を使い、必要時のみ `e2l:<serial>` へ override する |
| `DEVICE_RUNNER_TAG` | `"dev-rx72n"` | Raspberry Pi runner 固定用 tag。set 固定実行時は `dev-rx72n-01` / `-02` / `-03` のような個別 tag を指定する |
| `DEVICE_RESOURCE_GROUP` | `"rx72n-device"` | GitLab 内の device 直列化単位。set 固定実行時は `rx72n-device-01` / `-02` / `-03` のように分ける |
| `DEVICE_LOCK_ROOT` | `"/tmp/gitlab-device-locks"` | Raspberry Pi runner 上で `DEVICE_ID` 単位のクロスプロジェクト排他ロックを置くディレクトリ |

3 セットを安全に使い分けるときは、`DEVICE_ID` / `DEVICE_RUNNER_TAG` / `DEVICE_RESOURCE_GROUP` / `RFP_TOOL` / `UART_PORT` / `COMMAND_PORT` / `MAC_ADDR` を同じ set の値へまとめて切り替える。

**実行パターン:**

デフォルトは SD カード更新テストを除く通常テスト。
SD カード更新を含むフルテストを実施したい場合は `RUN_SD_UPDATE_TEST=true` を指定する。

| シナリオ | RUN_AWS_TESTS | RUN_SD_UPDATE_TEST | RUN_OTA_TEST |
|----------|:---:|:---:|:---:|
| 通常テスト（デフォルト） | true | false | true |
| フルテスト | true | true | true |
| AWS 接続テスト | true | **false** | **false** |
| ビルド+起動テスト | **false** | **false** | **false** |
| SD カード更新テスト | true | true | **false** |
| OTA テスト | true | **false** | true |

`RUN_PHASE8B_BUILD_ONLY=true` を指定すると、legacy `aws_demos` / OTA / 実機ジョブをすべて止め、
Windows runner 上の `build_phase8b` だけを実行する。`phase8b/` 配下の retarget 作業を
scarce な実機資源を消費せずに回すためのモード。

`RUN_PHASE8B_BASELINE=true` を指定すると、legacy `aws_demos` / OTA / GUI 系 job を止め、
`build_phase8b -> flash_phase8b_boot_loader -> download_phase8b_app`
だけを実行する。phase8b の `flash -> provision -> MQTT` を独立して詰めるためのモード。

`RUN_PHASE8B_OTA=true` を指定すると、legacy `aws_demos` 系 job と legacy OTA job を止め、
`build_phase8b_ota -> prepare_phase8b_ota -> phase8b_ota_create_job -> phase8b_ota_monitor -> phase8b_ota_finalize`
だけを実行する。最新 FreeRTOS baseline 上で OTA pipeline を再検証するためのモード。

**注意:**
- `RUN_SD_UPDATE_TEST` は `RUN_AWS_TESTS == "true"` の場合のみ有効（AWS 接続が前提）
- `RUN_HW_HEALTHCHECK=true` の場合、`flash_boot_loader` で boot_loader バナー確認、`download_aws_demos` 後に aws_demos の prompt/probe 確認を実行する
- `RUN_OTA_TEST` は独立した OTA パイプライン（build_ota → prepare_ota → ota_create_job/ota_monitor → ota_finalize）を制御。`RUN_AWS_TESTS=false` でも OTA テスト可（`prepare_ota` 内で再プロビジョニング）
- `RUN_PHASE8B_OTA` は phase8b app の OTA demo を前提とした別系統の OTA パイプライン。v1/v2 RSU は `tools/ci/build_phase8b_ota.ps1` で生成し、初回 provisioning は `tools/provision_phase8b.py` を使って短時間 CLI window 内で完了させる
- AWS credentials は Windows 側の `ota-aws-control` environment に scope できる。Pi runner 側 job は `awscli` 非依存とし、UART 監視のみに限定する。
- デバイスアクセスジョブには `resource_group: rx72n-device` を設定。同一ブランチへの連続 push で複数パイプラインが起動した際、先行パイプラインのデバイスジョブが完了するまで後続パイプラインのデバイスジョブは待機する（FIFO）。`build` / `build_ota` はデバイス非依存のため `resource_group` 不要。
- `resource_group` は同一プロジェクト内の直列化にしか効かない。別プロジェクトと Raspberry Pi runner を共有する場合は、Pi 上の `tools/ci/acquire_pi_device_lock.sh` により `/tmp/gitlab-device-locks/<DEVICE_ID>.lock` を `flock` してクロスプロジェクト排他を行う。

### テストファーム構想 / Test Farm Architecture

**目標:** RX72N Envision Kit 3台 + セカンダリ MCU (FPB-RX140) 6台によるフリートプロビジョニング＋マルチ MCU OTA の全自動テスト

**ハードウェア構成:**

```
[ビルド Runner (Windows)]           [実機 Runner (Raspberry Pi × 3台)]
  e2studio + CC-RX                    ├─ Pi #1 ── RX72N #1 ─┬─ FPB-RX140 (A)
  .mot/.rsu 生成                      │                      └─ FPB-RX140 (B)
  artifacts で受け渡し                 ├─ Pi #2 ── RX72N #2 ─┬─ FPB-RX140 (C)
                                      │                      └─ FPB-RX140 (D)
                                      └─ Pi #3 ── RX72N #3 ─┬─ FPB-RX140 (E)
                                                             └─ FPB-RX140 (F)
```

**調達済みハードウェア:**
- Raspberry Pi 4 Model B × 3台（RX72N Envision Kit 各セットに 1:1 対応）
- RX72N Envision Kit × 3台（3セット運用中）
- FPB-RX140 × 6台（セカンダリ MCU、各 RX72N に2台ずつ接続）
- USB ハブ + USB ケーブル多数
- 個別 runner / board の識別子は `hardware-config` リポジトリの台帳を正本とする

**Runner 分離方針:**
- **ビルド専用 Runner (Windows):** e2studio ヘッドレスビルド。実機不要、重い処理を分離
- **実機操作専用 Runner (Raspberry Pi):** flash (rfp-cli) + UART テスト + SD カード転送。RX72N 物理接続。Python スクリプト実行

**テストシナリオ（Phase 12-14）:**
- AWS IoT Core フリートプロビジョニングで3台同時にデバイス登録・証明書発行
- OTA ジョブで3台一斉にファームウェア更新
- RX72N → FPB-RX140 へのセカンダリ MCU カスケード更新
- 各デバイスの更新完了・正常動作を並列監視

### Build environment / ビルド環境

- **IDE:** e2 studio 2025-12（`C:\Renesas\e2_studio_2025_12\eclipse\e2studioc.exe`）
  - **重要:** CI と GUI で必ず同じ e2 studio バージョンを使うこと（SMC 生成物・Makefile テンプレートが異なり、バイナリ互換性が壊れる）
  - e2 studio バージョン変更時は smc_gen 再生成 → コミット → MOT 比較 → 実機検証 が必須
  - Phase 5 まで: e2 studio 2024-01 / CC-RX v3.04（MR !20）
  - Phase 6 (MR !21) で e2 studio 2024-01 → 2025-12 / CC-RX v3.04 → v3.07 へ移行完了
- **Compiler:** CC-RX v3.07.00（e2 studio 2025-12 同梱。v3.04 → v3.07 移行完了、LCD 消灯バグは Phase 5 の修正で解消確認済み）
- **Build runner tag:** `run_ishiguro_machine`（Windows 11、e2 studio/CC-RX ビルド専用）
- **Device runner tags:** `exec-shell`, `os-linux`, `hw-raspi`, `dev-rx72n`
  - flash ジョブは追加で `cap-flash` を要求
  - `UART_PORT` / `COMMAND_PORT` は Linux device path を設定する
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
- boot_loader の UART 設定: `r_bsp_config.h` → `MY_BSP_CFG_SERIAL_TERM_SCI (7)`, 921600bps（Phase 4 で SCI2/COM6 から SCI7/COM7 に変更）
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
COM6 が完全に応答しなくなった場合は、RX72N Envision Kit の電源 ON/OFF で RL78/G1C がリセットされ復旧する。
TeraTerm が異常に重くなる症状が出た場合も電源 ON/OFF が有効。

**LCD タッチ依存の完全解消 (Phase 5 で解消):**

元のコードでは `ID_SCREEN_00_Slots.c` の LCD タッチイベント (`PIDPRESSED`) で以下を実行していた:
1. `gui_initialize_complete_flag = 1` — `uart_string_printf()` のブロック解除（COM7 ログ出力に必須）
2. 4タスク（`serial_terminal_task`, `task_manager_task`, `sdcard_task`, `serial_flash_task`）への `xTaskNotifyGive`

つまり LCD 画面を 1 回タッチするまで:
- UART コマンドターミナルが動作しない（`serial_terminal_task` がブロック）
- AWS デモが起動しない（`task_manager_task` がブロック）
- COM7 のログ出力が一切出ない（`uart_string_printf()` が `gui_initialize_complete_flag` を待ってブロック）

CI/CD 自動テストではタッチ操作が不可能なため、`gui_task.c` の `APPW_CreateRoot()` 直後に
`gui_initialize_complete_flag = 1` と全4タスクへの `xTaskNotifyGive` を追加し、LCD タッチなしで
全機能が起動するように変更した。

**CI/CD でのシリアルポートロック問題:**

CI/CD ジョブ停止時に Python プロセスが正常終了せずシリアルポートを掴んだまま残留することがある。
次回ジョブで PermissionError になる。対策: `before_script` で残留 Python プロセスを強制終了する。

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

- `-range-exclude <start>,<end>`: 指定アドレス範囲を消去対象から除外。データフラッシュ保護に使用可能
  - RX72N データフラッシュ: `0x00100000` - `0x00107FFF` (32KB)
  - 例: `-erase-chip -range-exclude 00100000,00107FFF` でデータフラッシュを保持したまま全消去（未検証）
- **`-erase-chip` はデータフラッシュも消去する**: プロビジョニング済みの AWS 証明書・エンドポイント等が失われる。CI/CD でフラッシュ後に再プロビジョニングが必要か、`-range-exclude` でデータフラッシュを保護する
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
| `touch any` | 画面中央 (240, 136) をタッチ（疑似 PID イベント注入） |
| `touch <x> <y>` | 指定座標をタッチ（範囲: 0-479, 0-271） |
| `sdcard list` | SD カード内のファイル一覧（ファイル名とサイズ）を表示 |
| `sdcard write <filename> <size>` | UART 経由でバイナリデータを受信し SD カードにファイルを書き込み（ハンドシェイクプロトコル） |
| `sdcard delete <filename>` | SD カードからファイルを削除 |
| `reset` | ソフトウェアリセット |

データフラッシュはデュアルプレーン＋故障時復旧機構を備え、書き込み中の電源断に耐える設計。

**SD カード UART ファイル転送プロトコル (`sdcard write`):**

`sdcard write <filename> <size>` コマンドで UART 経由のバイナリデータを SD カードに書き込む。
SCI キュー溢れを防止するハンドシェイク方式:

```
Host → MCU: sdcard write userprog.rsu 1650000\r\n
MCU → Host: READY 2048\r\n                       ← chunk_size 通知
[Loop:]
  Host → MCU: [min(2048, remaining) bytes]        ← raw binary
  MCU:        sci_buffer に受信 → SD カードに書き込み
  MCU → Host: W <received_total>\r\n              ← ACK + 進捗
[End:]
MCU → Host: DONE <received_total>\r\n$            ← 完了
```

- chunk_size = `SCI_BUFFER_SIZE` (2048B)
- バイナリ転送中はエコーなし（ACK のみ送信）
- Host 側は `W` レスポンスを待ってから次チャンク送信 → キュー溢れ回避
- SD カード書き込みは `R_tfat_f_write()` + `R_tfat_f_sync()` で確実にフラッシュ
- 転送時間見積もり (userprog.rsu ≈ 1.6MB, 115200bps): 約3分

**UART 疑似タッチイベント注入 (Phase 5-D で追加):**

`touch` コマンドは emWin の `GUI_TOUCH_StoreStateEx()` API を使い、UART 経由で PID (Pointer Input Device) イベントを注入する。
gui_task のメインループ (`GUI_Exec()`, 10ms 周期) がイベントバッファを処理するため、50ms の press/release 間隔で確実に検出される。

- `GUI_TOUCH_StoreStateEx()` は ISR コンテキストから呼ばれる設計（PIDConf.c の I2C コールバックから呼出）→ serial_terminal_task からの呼び出しもスレッドセーフ
- 座標バリデーション: ディスプレイ解像度 480x272 の範囲外は `invalid coordinates` エラー
- レスポンス形式: `touch (240, 136) OK\n$ `

**Screen 00 → Screen 01 遷移条件 (AppWizard):**

`ID_SCREEN_00.c` の `_aAction` テーブルより:
1. `INITDIALOG` で `VAR_00 = 1`（自動）
2. `PIDPRESSED` ごとに `VAR_01 += 1`
3. **`VAR_00==1 && VAR_01==2` で `SHOWSCREEN(ID_SCREEN_01)` + `CLOSESCREEN(ID_SCREEN_00)`**

→ **`touch any` × 2 回で Screen 00 → Screen 01 遷移**

**Screen 01 ボタン座標 (`ID_SCREEN_01.c` `_aCreate` テーブルから計算):**

| ボタン | 用途 | 中心座標 | サイズ |
|--------|------|----------|--------|
| BUTTON_00 | タブ切替 (System Info) | (346, 10) | 80x16 |
| BUTTON_01 | タブ切替 (FW Update) | (434, 10) | 80x16 |
| BUTTON_03 | FW Update 実行 | (346, 238) | 80x16 (WINDOW_01 子要素, y offset +20) |
| BUTTON_04 | ソフトリセット | (434, 238) | 80x16 (WINDOW_01 子要素, y offset +20) |

### AWS IoT Core 接続 (Phase 5-C で検証済み)

**アーキテクチャ:**
- coreMQTT + Mutual TLS (クライアント証明書認証)
- PKCS#11 でデータフラッシュに証明書・秘密鍵を格納
- エンドポイント・Thing 名もデータフラッシュに格納

**起動シーケンス（COM7 ログで確認済み）:**
1. Secure boot → integrity check → jump to user program (~2s)
2. FreeRTOS 起動 → Ethernet 初期化 → DHCP (~3s)
3. `task_manager_task`: ネットワーク待ち → `vDevModeKeyProvisioning()` → データフラッシュ読み書き (~5s)
4. `DEMO_RUNNER_RunDemos()` → TLS 接続 → DNS 解決 → MQTT CONNECT (~2s)
5. Subscribe → Publish × 5 ("Hello World!") → Unsubscribe → Disconnect
6. 3 iteration 成功で DEMO FINISHED（起動から約80秒で完了）

**プロビジョニング方法:**
```bash
python test_scripts/uart_test/provision_aws.py \
  --port COM6 \
  --endpoint <endpoint>.iot.<region>.amazonaws.com \
  --thing-name rx72n-envision-kit \
  --cert certs/certificate.pem.crt \
  --key certs/private.pem.key
```

**PEM ストリーミングプロトコル（serial_terminal_task）:**
- `dataflash write aws clientcertificate` / `clientprivatekey` コマンド後、文字単位で PEM データを受信
- `xQueueReceive` で 1 文字ずつ `sci_buffer` (2048B) に蓄積
- 終端マーカー `-----END CERTIFICATE-----\n` or `-----END RSA PRIVATE KEY-----\n` で書き込み完了
- **改行は LF のみ**（CRLF を送ると終端検出に失敗する）

**AWS IoT Core リソース（テスト用）:**
- Region: `ap-northeast-1`
- Thing: `rx72n-envision-kit`
- Policy: `rx72n-envision-kit-policy` (Connect/Publish/Subscribe/Receive)
- 証明書・秘密鍵: `certs/` ディレクトリ（.gitignore で除外、秘密情報）

**COM7 ログ出力のボーレート:**
- `r_bsp_config.h` の `MY_BSP_CFG_AFR_TERM_SCI_BITRATE` = `921600`（boot_loader と統一）
- テストスクリプトも 921600bps で接続

## Changelog / 変更履歴

### 2026-03-11: phase8b provisioning を `reset-after-open` 化し、boot_loader 誤捕捉を可視化

Pipeline `#633` showed that `prepare_phase8b_ota` can finish the UART RSU transfer with `verify install area buffer ... OK` and `activating image ... OK`, but still hand off to provisioning without any observed `software reset` or app boot log. In that state, `provision_phase8b.py --no-reset` was racing a 10-second CLI window with no reliable proof that the phase8b app had actually started.

To isolate the state further, direct-flash diag pipeline `#634` was run with only `build_phase8b` and `diag_phase8b_direct_flash_cli`. Its trace showed the `CLI\r\n` wake-up bytes being consumed by the UART boot loader and eventually triggering `sample_write_image failed: FWUP_ERR_FAILURE (4)`, which made the wrong-state failure explicit: at least some "provisioning failed" cases were not app CLI failures but boot_loader still owning SCI7.

Repo-side mitigation is now to open the FTDI port first and then issue an explicit external reset before attempting CLI entry. `tools/provision_phase8b.py` gained `--reset-after-open` plus an early boot_loader marker check, and the phase8b provisioning call sites now use `rfp-cli ... -reset -noquery` with that mode enabled so the short CLI window can be recaptured more deterministically.

pipeline `#633` で、`prepare_phase8b_ota` は `verify install area buffer ... OK` と `activating image ... OK` まで進む一方、`software reset` や app 起動 log を観測しないまま provisioning へ移っていることが分かった。この状態で `provision_phase8b.py --no-reset` を呼ぶと、「phase8b app が本当に起動したか不明なまま」10 秒 CLI window を取りにいく形になっていた。

状態をさらに切り分けるため、`build_phase8b` と `diag_phase8b_direct_flash_cli` だけを流す direct-flash diag pipeline `#634` を実行した。trace では `CLI\r\n` の wake-up bytes が UART boot_loader に食われ、最終的に `sample_write_image failed: FWUP_ERR_FAILURE (4)` を返した。つまり少なくとも一部の「provisioning 失敗」は app CLI 自体の不具合ではなく、SCI7 をまだ boot_loader が握っている wrong-state failure だった。

repo 側の対策として、FTDI port を先に open してから明示 reset を掛け、その直後の CLI window を取り直す方式へ寄せた。`tools/provision_phase8b.py` には `--reset-after-open` と boot_loader marker の早期検出を追加し、phase8b provisioning 呼び出し側は `rfp-cli ... -reset -noquery` をそのモードで使うよう更新した。これで short-lived CLI window をより確実に再捕捉できる。

### 2026-03-11: `RFP_TOOL=e2l` を既定化し、E2 Lite serial 依存を外した

Follow-up probing on `ef-saffti-001-rpi-002-rx72nek` / `003` showed that `rfp-cli -d RX72x -lt` only reports supported tool classes (`e2`, `e2l`) and does not enumerate the attached E2 Lite serial. Because the runner topology is 1 Raspberry Pi to 1 RX72N set, pinning by runner tag is already enough to identify the programmer.

Updated `.gitlab-ci.yml` so Raspberry Pi jobs now use `RFP_TOOL=e2l` by default and only need an explicit serial when a future runner hosts multiple E2 Lite devices. This removes `E2LITE_SERIAL` as a mandatory blocker for phase8b OTA reruns and keeps the remaining work focused on per-set runner tags plus UART/MAC variables.

`ef-saffti-001-rpi-002-rx72nek` / `003` での追加確認から、`rfp-cli -d RX72x -lt` は接続中 E2 Lite の serial を列挙せず、対応 tool class (`e2`, `e2l`) だけを返すことが分かった。runner 構成は 1 Raspberry Pi : 1 RX72N set なので、programmer の識別は runner tag 固定だけで十分である。

このため `.gitlab-ci.yml` は Raspberry Pi job の既定を `RFP_TOOL=e2l` へ変更し、将来 1 runner に複数 E2 Lite を挿す場合だけ明示 serial を override する設計へ寄せた。これで phase8b OTA rerun における必須 blocker から `E2LITE_SERIAL` を外し、残作業を set 別 runner tag と UART/MAC 変数へ集中できるようにした。

### 2026-03-11: 3-set runner affinity 用の device 固定変数と multi-device config を追加

To make the remaining phase8b OTA blocker actionable, the repo now accepts set-specific runner and lock selection without breaking the current single-bundle defaults. `.gitlab-ci.yml` gained `DEVICE_RUNNER_TAG` and `DEVICE_RESOURCE_GROUP`, both consumed by Raspberry Pi jobs via variable expansion, so OTA prepare / monitor can be pinned to the same RX72N set once runner-side tags are in place.

Also extended `test_scripts/device_config.json` with `rx72n-02` / `rx72n-03` entries and relaxed the UART/AWS helper scripts to prefer environment overrides when a device entry omits local port fields. This keeps `device_id`-driven Thing/certificate naming usable for multi-set CI even before the new boards are fully documented in `hardware-config`.

phase8b OTA の残 blocker を具体的に潰せるよう、repo 側に set 固定実行の受け皿を追加した。`.gitlab-ci.yml` へ `DEVICE_RUNNER_TAG` と `DEVICE_RESOURCE_GROUP` を導入し、Raspberry Pi job が変数展開経由で runner tag / GitLab lock を選べるようにした。runner 側に set 別 tag が付けば、OTA prepare / monitor を同じ RX72N set に pin できる。

あわせて `test_scripts/device_config.json` に `rx72n-02` / `rx72n-03` を追加し、UART/AWS helper script 群は device entry にローカル port がなくても環境変数 override を優先して動くように緩めた。これで `hardware-config` に set #2 / #3 の個体値が揃う前でも、multi-set CI に必要な `device_id` ベースの Thing/cert 命名は先に使える。

### 2026-03-11: `prepare_phase8b_ota` を single-block 化して block 間 lock 再取得待ちを回避

Pipeline `#594` confirmed that fixing the lock helper alone was not enough: when `prepare_phase8b_ota` advanced into its next script item, it stalled waiting on `/tmp/gitlab-device-locks/rx72n-01.lock` again. The practical issue is that the OTA prepare sequence needs device exclusivity across flash, UART download, provisioning, and reset, but GitLab's per-item execution model made the multi-block structure fragile.

Collapsed `prepare_phase8b_ota` into a single script block so the full sequence now runs under one lock acquisition and one shell context. This removes the inter-block lock hand-off entirely and makes the next rerun focus on the real phase8b OTA runtime behavior.

pipeline `#594` で、lock helper 修正だけでは不十分なことが分かった。`prepare_phase8b_ota` は次の script item へ進んだ時点で `/tmp/gitlab-device-locks/rx72n-01.lock` の再取得待ちに入り、停滞した。phase8b OTA の prepare は flash / UART download / provisioning / reset を通しで同一実機占有する必要があるが、GitLab の item ごとの実行形態では multi-block 構成が脆かった。

このため `prepare_phase8b_ota` を single script block に畳み、全シーケンスを 1 回の lock 取得・1 つの shell context で実行する形へ変更した。これで block 間の lock 引き継ぎ問題を消し、次の rerun では phase8b OTA の実ランタイム挙動そのものに集中できる。

### 2026-03-11: `acquire_pi_device_lock.sh` の `source` 再利用バグを修正

Pipeline `#592` showed that `phase8b_ota_create_job` now succeeds, but `phase8b_ota_monitor` still failed because `prepare_phase8b_ota` never actually progressed past the initial flash step. Root cause was the lock helper: `tools/ci/acquire_pi_device_lock.sh` was sourced multiple times inside the same job, and its `DEVICE_LOCK_HELD=1` fast path used `exit 0`, which terminated the outer shell before UART download / provisioning / reset steps could run.

Updated the helper so it returns when sourced and only exits when executed as a standalone script. This keeps the device lock reusable across multiple script blocks in the same GitLab job while preserving existing failure behavior.

pipeline `#592` では `phase8b_ota_create_job` が成功した一方、`phase8b_ota_monitor` は失敗した。trace を確認すると、`prepare_phase8b_ota` が初回 flash の後で実際には進んでおらず、`UART download / provisioning / reset` に到達していなかった。原因は lock helper にあり、`tools/ci/acquire_pi_device_lock.sh` を同一 job 内で複数回 `source` した際、`DEVICE_LOCK_HELD=1` の fast path が `exit 0` を実行して outer shell ごと終了させていた。

helper は「source されたときは return、単独実行時のみ exit」するよう修正した。これで同一 GitLab job 内の複数 script block から device lock を再利用しても、後続 step が継続する。

### 2026-03-11: Phase 8b OTA pipeline #590 で runner affinity 問題を特定し、RELFWV2 parser を追加

Ran branch pipeline `#590` after hardening diagnostics. `prepare_phase8b_ota` succeeded on `ef-saffti-001-rpi-001-rx72nek`, but `phase8b_ota_monitor` was scheduled onto `ef-saffti-001-rpi-002-rx72nek` and failed because the shared `UART_PORT` variable pointed at a different FTDI device. This confirmed that the current generic runner tags do not preserve device affinity across OTA stages.

In the same run, `phase8b_ota_create_job` exposed a second issue: the OTA helper still assumed the legacy `Renesas` RSU layout and could not parse phase8b `RELFWV2` images. Updated `test_ota.py` to recognize both legacy and FWUP v2 RSU formats, and verified locally that phase8b payload/signature extraction now succeeds. Monitor jobs were also updated to pre-create placeholder artifacts so failure logs remain available without secondary artifact-upload noise.

診断強化後の branch pipeline `#590` を実行した。`prepare_phase8b_ota` は `ef-saffti-001-rpi-001-rx72nek` で成功したが、`phase8b_ota_monitor` は `ef-saffti-001-rpi-002-rx72nek` にスケジュールされ、共有 `UART_PORT` 変数が別の FTDI device を指していたため失敗した。これにより、現行の generic runner tag だけでは OTA の前後 stage で device affinity を維持できないことが確認できた。

同じ run では `phase8b_ota_create_job` から、OTA helper がまだ旧 `Renesas` RSU layout 前提で、phase8b の `RELFWV2` image を解釈できないことも判明した。`test_ota.py` を legacy / FWUP v2 の両 RSU 形式対応へ更新し、ローカルで phase8b payload/signature 抽出が成功することを確認した。あわせて monitor job は placeholder artifact を先に作るようにし、失敗時も artifact upload ノイズなしで log を残せるようにした。

### 2026-03-11: Phase 8b OTA pipeline #588 で 3-set hardware mismatch を確認

Ran branch pipeline `#588` with `RUN_PHASE8B_OTA=true`. `build_phase8b_ota` succeeded and produced phase8b OTA v1/v2 RSU artifacts, but `prepare_phase8b_ota` failed on Raspberry Pi runner `ef-saffti-001-rpi-003-rx72nek` with `E3000201: Cannot find the specified tool.` The log also showed the runner still locking `rx72n-01`, indicating that the current CI variable bundle and device lock/resource settings still assume a single hardware set.

To reduce noisy secondary failures while this hardware mapping is being corrected, OTA finalize jobs now no-op with placeholder artifacts when create/monitor metadata is absent instead of failing on missing files.

branch pipeline `#588` を `RUN_PHASE8B_OTA=true` で実行した。`build_phase8b_ota` は成功し、phase8b OTA v1/v2 RSU artifact を生成できたが、`prepare_phase8b_ota` は Raspberry Pi runner `ef-saffti-001-rpi-003-rx72nek` 上で `E3000201: Cannot find the specified tool.` により失敗した。log 上は runner が依然として `rx72n-01` の lock を取得しており、現行 CI 変数束と device lock/resource 設定がまだ単一ハードウェア前提であることが確認できた。

hardware mapping 修正中の二次障害を減らすため、OTA finalize job は create/monitor metadata が無い場合に missing file で失敗せず、placeholder artifact を残して no-op 終了するようにした。

### 2026-03-11: Phase 8b-4 OTA revalidation の CI 導線に着手

Started Issue #10 work to revalidate OTA on the latest FreeRTOS baseline. Added a dedicated `RUN_PHASE8B_OTA` mode, a `build_phase8b_ota` path for generating phase8b v1/v2 RSU images, and phase8b-specific OTA pipeline jobs intended to reuse the existing AWS IoT OTA create/monitor/finalize flow.

Issue #10 として、最新 FreeRTOS baseline 上の OTA 再検証に着手。`RUN_PHASE8B_OTA` モード、phase8b 向け v1/v2 RSU 生成の `build_phase8b_ota` 経路、および既存 AWS IoT OTA create/monitor/finalize フローを再利用する phase8b 専用 OTA pipeline job 群を追加した。

### 2026-03-11: MCUboot ROM budget note を OTA knowledge base に集約

Moved the OTA-facing MCUboot sizing summary to the OTA knowledge base and left a reference here. This CLAUDE.md keeps the RX72N Envision Kit-specific measurements and go/no-go notes for Phase 8b.

MCUboot の OTA 観点サマリを OTA knowledge base 側へ集約し、この CLAUDE.md には参照を追加した。こちらには引き続き、Phase 8b の RX72N Envision Kit 固有の実測値と go/no-go 判断メモを残す。

### 2026-03-09: Phase 8b-1 seed import into `phase8b/`

Imported the shared `iot-reference-rx` baseline into `phase8b/` so RX72N porting
can start from the same `Common/`, `Configuration/`, `Middleware/`, and `Test/`
software stack that already passed Phase 8a. Also copied seed `e2studio_ccrx`
projects for the RX72N app and boot loader under the target directory names.

`phase8b/UPSTREAM_BASELINE.md` now records the exact upstream source commit and
the imported directory inventory. The imported projects are still RX65N-oriented
seeds and are not yet claimed to build on RX72N; the next step is Issue `#8`
for boot loader porting.

`iot-reference-rx` の共通基盤を `phase8b/` に取り込み、RX72N 移植を
Phase 8a で実績のある `Common/` / `Configuration/` / `Middleware/` / `Test/`
構成から開始できる状態にした。あわせて、RX72N アプリと boot loader の
seed `e2studio_ccrx` project を目標ディレクトリ名で配置した。

`phase8b/UPSTREAM_BASELINE.md` に upstream commit と取り込み対象一覧を記録。
この段階の project はまだ RX65N 指向の seed であり、RX72N build 通過は未主張。
次の作業は Issue `#8` の boot loader port。

### 2026-03-09: Phase 8b-3 RX72N app が headless build を通過

`aws_ether_rx72n_envision_kit` seed project を RX72N 向けに retarget し、
project metadata, BSP/ETHERNET/FLASH/S12AD/SCI target, pin config, `r_fwup`
設定、clock/PPLL 設定、expansion RAM 定義を移植した。

あわせて littlefs 側に不足していた FSP compatibility include を補い、
RX72N の DPFPU 前提に合わせて linker の `D_8/R_8` と
`DEXRAM_8/REXRAM_8` section を有効化した。

e2studio 2025-12 + CC-RX の headless build で
`aws_ether_rx72n_envision_kit/HardwareDebug` が `0 errors, 55 warnings`
で完走し、`.abs` / `.mot` / `.x` の生成を確認した。

残課題は build blocker ではない warning の整理と CI 配線。
特に `r_tsip_rx` の RX72N target 正式化、`C_LITTLEFS_*` /
`C_USER_APPLICATION_AREA` linker warning の扱い、phase8b build-only
job の追加を次に進める。

### 2026-03-09: Phase 8b build-only CI を追加

Added `tools/ci/build_phase8b_headless.ps1` and wired a new `build_phase8b`
job into `.gitlab-ci.yml`. The new job imports
`boot_loader_rx72n_envision_kit` and `aws_ether_rx72n_envision_kit` directly
from `phase8b/Projects/`, runs a clean headless e2studio build, and publishes
the resulting `.mot` / `.abs` / `.x` artifacts.

Also introduced `RUN_PHASE8B_BUILD_ONLY=true`, which suppresses the legacy
`aws_demos` / hardware / OTA jobs and leaves only the phase8b Windows build
gate active. This keeps scarce RX72N/Pi resources free while the FreeRTOS
migration is still in build-only mode.

`tools/ci/build_phase8b_headless.ps1` を追加し、`.gitlab-ci.yml` に
`build_phase8b` job を配線した。新 job は `phase8b/Projects/` 配下の
`boot_loader_rx72n_envision_kit` / `aws_ether_rx72n_envision_kit` を直接
import し、e2studio headless clean build を実行して `.mot` / `.abs` / `.x`
artifact を保存する。

あわせて `RUN_PHASE8B_BUILD_ONLY=true` を導入し、legacy `aws_demos` /
実機 / OTA job を止めて、phase8b 向けの Windows build gate だけを残せる
ようにした。これにより、FreeRTOS 移行が build-only 段階にある間は scarce
な RX72N/Pi 実機資源を消費せずに反復できる。

### 2026-03-09: Phase 8b started — skeleton import planning and issue split

Started Phase 8b of the `iot-reference-rx` migration on the RX72N Envision Kit side.
Created a parent issue plus split execution issues so the work can proceed in a controlled
order: skeleton import, boot loader port, application port, OTA recovery, and GUI/SD
reintegration. Also documented the Windows case-insensitive filesystem constraint
(`core.ignorecase=true`) that affects top-level directory migration from the legacy
lower-case tree to the `iot-reference-rx` style layout.

RX72N Envision Kit 側で `iot-reference-rx` 移行の Phase 8b に着手。親 issue と
実行順に沿った分割 issue（skeleton import、boot loader port、application port、
OTA 再接続、GUI/SD 再統合）を作成した。あわせて、legacy の lower-case tree から
`iot-reference-rx` 風の構成へ移行する際に影響する Windows の
case-insensitive filesystem 制約（`core.ignorecase=true`）を文書化した。

### 2026-03-09: Issue #6 OTA AWS 制御を Windows runner へ分離

Split OTA execution into three jobs: `ota_create_job` (Windows), `ota_monitor` (Raspberry Pi),
and `ota_finalize` (Windows). This removes the `awscli` dependency from the Pi runner and allows
AWS credential variables to be scoped to the `ota-aws-control` environment on the Windows runner
only. `test_scripts/uart_test/test_ota.py` now supports `create-job`, `monitor`, and `finalize`
modes in addition to the original full mode.

Issue #6 として、OTA 実行を `ota_create_job`（Windows）、`ota_monitor`（Raspberry Pi）、
`ota_finalize`（Windows）の3ジョブに分割。Pi runner から `awscli` 依存を外し、
AWS credential variables を Windows runner 側の `ota-aws-control` environment に
scope できる構成にした。`test_scripts/uart_test/test_ota.py` には `create-job`、
`monitor`、`finalize` mode を追加し、従来の full mode も維持。

### 2026-03-08: Issue #4 Raspberry Pi Runner への device stage 移植着手

Started porting pipeline device stages (`flash`, UART test, AWS provisioning, SD update, OTA prep/test)
from the Windows runner to Raspberry Pi shell runners. Build jobs remain on Windows (`run_ishiguro_machine`),
while device jobs move to Linux tags (`exec-shell`, `os-linux`, `hw-raspi`, `dev-rx72n`; flash also requires
`cap-flash`). The pipeline now expects Linux serial device paths via CI/CD variables for `UART_PORT` and
`COMMAND_PORT`.

Issue #4 として、パイプラインの device stage（`flash`、UART テスト、AWS プロビジョニング、
SD update、OTA 準備/試験）の Raspberry Pi shell runner への移植を開始。ビルドジョブは
Windows (`run_ishiguro_machine`) に残し、device ジョブは Linux tag
(`exec-shell`, `os-linux`, `hw-raspi`, `dev-rx72n`、flash は `cap-flash` 追加) に移行する。
`UART_PORT` / `COMMAND_PORT` は CI/CD Variables 経由で Linux serial device path を受け取る前提。

**Implementation notes / 実装メモ:**
- `.gitlab-ci.yml` の device jobs を PowerShell から bash + `python3` 呼び出しへ置換
- `tools/ci/activate_pi_python.sh` を追加し、Pi runner で `pyserial` / `cryptography` / `awscli` を venv 経由で供給
- `tools/ci/send_serial_command.py` を追加し、`prepare_ota` の reset 送信を `System.IO.Ports.SerialPort` 依存から分離
- GitLab CI lint: valid（2026-03-08）

### 2026-03-03: Phase 8-14 順序変更 — iot-reference-rx 移行を先行

Reordered CI/CD phases 8-14. Moved iot-reference-rx migration (formerly Phase 9) to Phase 8, and consolidated fleet provisioning tests (formerly Phase 8 + 11) into a single Phase 10 on the new firmware. Total phases reduced from 15 to 14.

CI/CD フェーズ 8-14 の順序を変更。iot-reference-rx 移行（旧 Phase 9）を Phase 8 に前倒しし、フリートプロビジョニングテスト（旧 Phase 8 + 11）を新 FW 上の Phase 10 に一本化。全フェーズ数を 15 → 14 に削減。

**変更理由:**
- Phase 8 計画立案の調査で、現行ファームウェアに Fleet Provisioning デモが含まれていない可能性が判明
- iot-reference-rx には coreMQTT Agent + Fleet Provisioning デモが統合済みであり、移行後に FP テストを行う方が効率的
- 旧 Phase 8（現行 FW で FP テスト）と旧 Phase 11（新 FW で FP 再検証）を統合し、重複を排除

**変更前 → 変更後:**

| 旧 Phase | 旧内容 | 新 Phase | 新内容 |
|-----------|--------|-----------|--------|
| 8 | FP テスト（現行 FW） | 8 | iot-reference-rx 移行 |
| 9 | iot-reference-rx 移行 | 9 | OTA テスト（新 FW 再検証） |
| 10 | OTA テスト（新 FW 再検証） | 10 | FP テスト（新 FW、旧 8+11 統合） |
| 11 | FP テスト（新 FW 再検証） | 11 | セカンダリ MCU テスト |
| 12 | セカンダリ MCU テスト | 12 | OTA × 3 |
| 13 | OTA × 3 | 13 | FP × 3 + OTA |
| 14 | FP × 3 + OTA | 14 | フル構成 |
| 15 | フル構成 | - | (統合により削除) |

**Phase 8 作業リポジトリ:** [iot-reference-rx (GitLab)](https://shelty2.servegame.com/oss/import/github/renesas/iot-reference-rx) — CK-RX65N V1 で先行構築（8a）→ RX72N に移植（8b）。詳細は [iot-reference-rx の CLAUDE.md](https://shelty2.servegame.com/oss/import/github/renesas/iot-reference-rx/-/blob/main/CLAUDE.md) を参照。

### 2026-03-03: Phase 8 作業リポジトリ追加

Added iot-reference-rx repository link to Phase 8 description. Phase 8 uses a two-stage approach: build CI/CD on CK-RX65N V1 first (8a), then port to RX72N (8b). Detailed plan is in iot-reference-rx CLAUDE.md.

Phase 8 の説明に iot-reference-rx 作業リポジトリへのリンクを追加。2段階アプローチ（CK-RX65N V1 で先行構築 → RX72N に移植）の記載と、iot-reference-rx リポジトリの CLAUDE.md への参照を追加。

### 2026-03-02: Phase 7 — AWS IoT OTA テスト自動化 + パイプライン条件分岐

Added OTA (Over-The-Air) firmware update test automation via AWS IoT Core. Also introduced pipeline conditional execution variables (`RUN_AWS_TESTS`, `RUN_OTA_TEST`) for faster pipeline runs.

AWS IoT Core 経由の OTA ファームウェア更新テストの自動化を追加。パイプライン実行の高速化のため、条件分岐変数 (`RUN_AWS_TESTS`, `RUN_OTA_TEST`) を導入。

**OTA テストフロー:**
1. `build_ota`: `aws_demo_config.h` を OTA モードに切り替え、v1/v2 の2バージョンをビルド
2. `prepare_ota`: 通常テスト完了後に erase-chip → boot_loader 再書き込み → ota_v1.rsu UART DL → 再プロビジョニング
3. `test_ota`: v2 を S3 にアップロード → OTA ジョブ作成 → ログ監視（ジョブ受信→ダウンロード→署名検証→自己テスト→受理）

**パイプライン条件分岐:**
- `RUN_AWS_TESTS`: `"true"`(デフォルト) / `"false"` — AWS 接続テスト (provision, MQTT, SD update) の実行制御
- `RUN_OTA_TEST`: `"true"`(デフォルト) / `"false"` — OTA テストの実行制御
- GitLab UI の「Run Pipeline」画面で変数をオーバーライド可能

**New files / 新規ファイル:**
- `test_scripts/uart_test/test_ota.py` — OTA テストスクリプト（S3 アップロード、OTA ジョブ作成、マイルストーン監視、バージョン検証）

**Modified files / 変更ファイル:**
- `.gitlab-ci.yml`: `build_ota`, `prepare_ota`, `test_ota` ジョブ追加 + `rules:` による条件分岐
- `test_scripts/uart_test/provision_aws.py`: `--codesigner-cert` オプション追加（OTA 用コード署名証明書）
- `test_scripts/device_config.json`: `aws_region`, `codesigner_cert` フィールド追加
- `test_scripts/device_config_loader.py`: `aws_region` フィールドサポート追加

**AWS 側の前提条件（手動設定、1回限り）:**
- S3 バケット作成（バージョニング有効）
- OTA サービスロール作成
- IoT ポリシー更新（OTA 関連トピックのアクセス権限）
- GitLab CI/CD Variables: `OTA_S3_BUCKET`, `OTA_ROLE_ARN`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

**参照ナレッジベース:** [AWS IoT Core OTA](https://shelty2.servegame.com/oss/experiment/cloud/aws/iot-core/claude/-/blob/main/CLAUDE.md), [MCU OTA](https://shelty2.servegame.com/oss/experiment/embedded/mcu/elemental/ota/-/blob/main/CLAUDE.md)

**OTA テスト自動化で解決した5つの問題 (Pipeline #259-#293):**

| # | 症状 | 根本原因 | 修正 |
|---|------|---------|------|
| 1 | OTA ジョブ作成時 `Base64InvalidSymbol` | AWS CLI v2 が `inlineDocument` (blob 型) を自動 base64 デコード | 署名データを二重 base64 エンコード |
| 2 | `OtaPalSignatureCheckFailed` (ペイロード) | フル RSU を S3 にアップロード。OTA PAL の署名範囲は descriptor+code のみ | `extract_signed_payload()` で署名対象のみ抽出して S3 にアップロード |
| 3 | `OtaPalSignatureCheckFailed` (署名形式) | RSU は raw r\|\|s (64B) だが `mbedtls_pk_verify()` は DER 形式を期待 | `encode_dss_signature()` で DER に変換 |
| 4 | `build_ota` リンカエラー `E0562320` | `MAX_NUM_BLOCKS_REQUEST` 増加で RAM 超過 | `MAX_NUM_BLOCKS_REQUEST=1` に維持、`FILE_REQUEST_WAIT_MS=1000` で速度改善 |
| 5 | `test_ota` の `new_version` タイムアウト | `monitor_ota_progress()` がシリアルデータを消費し、STEP 5 でバージョン文字列を読めない | モニタリング中にバージョンを追跡し、STEP 5 で再利用 |

**OTA テスト通過確認:**
- Pipeline #293 (OTA テスト): 8/8 チェック PASS（agent_ready → s3_upload → ota_job_created → ota_job_ready → ota_download → new_version → aws_status）
- Pipeline #294 (フルテスト): 全11ジョブ PASS

### OTA + アプリケーション MQTT 並列動作（製品化に向けた設計指針）

現在のデモフレームワーク (`iot_demo_runner.h`) は **1デモ = 1バイナリ** の設計であり、
`CONFIG_OTA_MQTT_UPDATE_DEMO_ENABLED` と `CONFIG_CORE_MQTT_MUTUAL_AUTH_DEMO_ENABLED` は排他的。
製品では OTA バックグラウンド更新とアプリケーション MQTT 通信を並列動作させる必要がある。

**解決策: coreMQTT Agent パターン**

```
MQTT Agent Task（単一 MQTT 接続を管理、コマンドキュー経由で API 受付）
    ├── OTA Agent Task（バックグラウンドで OTA トピックを subscribe）
    ├── App Task 1（センサーデータ Pub/Sub）
    └── App Task N（その他アプリケーション）
```

- **MQTT 接続は1本だけ**（メモリ節約、スレッドセーフはキューで保証）
- OTA Agent は独立タスクとして稼働し、アプリケーションのパフォーマンスに影響しない
- 全タスクが `MQTTAgent_Publish()` / `MQTTAgent_Subscribe()` でコマンドキューに投入

**実装パス:**

| 方式 | 説明 | 工数 |
|------|------|------|
| **iot-reference-rx に移行** (Phase 4) | coreMQTT Agent + OTA Agent が最初から統合済み。推奨 | 大 |
| **カスタム結合デモを作成** | 現フレームワーク内でカスタムエントリ関数を作り複数タスク生成 | 中 |
| **現状維持（テスト用）** | OTA デモと MQTT デモは別バイナリで排他実行（CI/CD テスト方式） | 小 |

**参照実装:**
- [iot-reference-rx](https://github.com/renesas/iot-reference-rx) — Renesas RX 向け、coreMQTT-Agent で MQTT Pub/Sub + OTA を並列動作
- [coreMQTT-Agent-Demos](https://github.com/FreeRTOS/coreMQTT-Agent-Demos) — 公式デモ
- `demos/coreMQTT_Agent/mqtt_agent_task.c` — 本リポジトリ内の Agent パターン参考実装
- `demos/coreMQTT_Agent/simple_sub_pub_demo.c` — 共有 `xGlobalMqttAgentContext` の使用例

**現在のテスト戦略（2バイナリ方式）はテスト自動化として正しく、変更不要。**
Phase 4 の iot-reference-rx 移行で OTA + アプリ MQTT の並列動作は自然に実現される。

### 2026-03-01: Phase 5 — 既存機能の動作検証 + AWS IoT Core 接続 + UART touch コマンド

Added automated test scripts and CI/CD test stage for Phase 5 feature validation.
Completely removed LCD touch dependency from gui_task.c (all 4 tasks + gui_initialize_complete_flag).
Successfully verified AWS IoT Core MQTT connectivity (3/3 demo iterations PASS).
Added UART `touch` command for virtual touch event injection via GUI_TOUCH_StoreStateEx().
Automated screen navigation (Screen 00 → Screen 01) and button touch in CI/CD pipeline.

Phase 5 の動作検証のためのテストスクリプトと CI/CD テストステージを追加。
gui_task.c の LCD タッチ依存を完全解消（全4タスク通知 + gui_initialize_complete_flag 設定）。
AWS IoT Core への MQTT 接続を検証成功（3/3 デモイテレーション PASS）。
UART `touch` コマンドで emWin GUI_TOUCH_StoreStateEx() 経由の疑似タッチイベント注入を追加。
CI/CD パイプラインで画面遷移（Screen 00→01）とボタンタッチを自動検証。

**Firmware changes / ファームウェア変更:**
- `gui_task.c`: `APPW_CreateRoot()` 直後に以下を追加（LCD タッチ依存の完全解消）
  - `gui_initialize_complete_flag = 1` — COM7 ログ出力ブロック解除（`uart_string_printf()` の待ちを解消）
  - `xTaskNotifyGive` × 4タスク（serial_terminal, task_manager, sdcard, serial_flash）
  - 元の LCD タッチハンドラ (`ID_SCREEN_00_Slots.c:PIDPRESSED`) と同等の動作を実現
- `serial_terminal_task.c`: `touch` コマンド追加
  - `GUI_TOUCH_StoreStateEx()` で PID press/release イベントを注入（50ms 間隔）
  - `touch any` = 画面中央 (240, 136)、`touch <x> <y>` = 任意座標
  - 座標バリデーション（0-479, 0-271）、`GUI.h` は既にインクルード済み

**New files / 新規ファイル:**
- `test_scripts/uart_test/test_aws_demos_commands.py` — UART コマンドレスポンス自動テスト（COM6, 115200bps）
  - version, freertos cpuload, dataflash info/read/erase, timezone をテスト
  - COM6 間欠受信障害へのリトライ機構付き
  - プロンプトポーリング方式（1秒おきに `\r\n` 送信、応答を待つ）
- `test_scripts/uart_test/provision_aws.py` — AWS IoT Core プロビジョニング（UART 経由で証明書・エンドポイント書き込み）
- `test_scripts/uart_test/test_aws_connectivity.py` — AWS IoT Core 接続検証（COM7 FreeRTOS ログ監視）
- `test_scripts/uart_test/test_touch_navigation.py` — UART touch コマンドで画面遷移テスト（Screen 00→01 + ボタン操作）
- `test_scripts/uart_test/test_sd_update.py` — SD カードファームウェアアップデート検証
- `test_scripts/aws_setup/setup_iot_thing.sh` — AWS IoT Core リソース作成スクリプト

**CI/CD changes / CI/CD 変更:**
- `.gitlab-ci.yml`: `test` ステージ追加、`test_commands` ジョブ（download_aws_demos 後に実行）
  - ジョブタイムアウト 5 分に設定（ハング防止）
  - `before_script` で残留 Python プロセスの強制終了（ポートロック対策）
- `.gitlab-ci.yml`: `test_screen_navigation` ジョブ追加（test_commands 後に実行）
  - touch any × 2 で Screen 00→01 遷移、BUTTON_00/BUTTON_01 タッチ操作を検証
- `.gitlab-ci.yml`: `provision_aws_credentials` ジョブ追加（flash stage, download_aws_demos 後に実行）
  - `provision_aws.py --device-id --codesigner-cert` で証明書・エンドポイント・Thing名 + OTA 署名検証証明書を MCU に書き込み
- `.gitlab-ci.yml`: `confirm_aws_mqtt` ジョブ追加（test_screen_navigation 後に実行）
  - `test_aws_connectivity.py --device-id "$env:DEVICE_ID" --timeout 120` で DHCP/TLS/MQTT CONNACK を監視
  - ジョブタイムアウト 5 分
- `.gitlab-ci.yml`: グローバル変数 `DEVICE_ID: "rx72n-01"` 追加

**デバイス ID 方式 (Phase 5-E):**
- `test_scripts/device_config.json`: デバイスごとのハードウェア構成（COM ポート、E2 Lite シリアル、Thing 名等）
- `test_scripts/device_config_loader.py`: コンフィグローダーユーティリティ
  - `device_id_to_env_suffix()`: "rx72n-01" → "RX72N_01"（ハイフン→アンダースコア、大文字）
  - 証明書環境変数名: `AWS_CLIENT_CERT_{SUFFIX}` / `AWS_PRIVATE_KEY_{SUFFIX}`
- 証明書は GitLab CI/CD Variables (File 型) で管理
  - **Visibility は Visible を使用**（Masked/Masked and hidden は PEM の空白文字でエラー）
  - **Protected は No**（フィーチャーブランチで使用するため。本番鍵は Protected にすること）
- `provision_aws.py`, `test_aws_connectivity.py`: `--device-id` 引数追加（後方互換あり）
- 将来の複数デバイス同時運用（フリートプロビジョニング）を見据えた設計

**AWS IoT Core 接続検証結果:**
- DHCP → SNTP → TLS (port 8883) → MQTT CONNECT → Subscribe/Publish/Unsubscribe → 3/3 iterations PASS
- 起動から MQTT 接続まで約13秒、デモ完了まで約80秒
- `rfp-cli -erase-chip` でデータフラッシュも消去されるため、フラッシュ後に再プロビジョニングが必要
  - `rfp-cli -range-exclude 00100000,00107FFF` でデータフラッシュ保護が可能（未検証）

**Windows GitLab Runner での注意点:**
- `open()` に `encoding="utf-8"` を明示指定すること（デフォルト cp932 で日本語含む JSON が UnicodeDecodeError）
- GitLab CI/CD File 型変数: 環境変数の値は一時ファイルのパス（内容ではない）
- 初回 provision → confirm 実行時、二重リセットでタイミング問題が発生する可能性あり（リトライで解決）

**アクションアイテム:**
- device_config.json を共通プロジェクト（git submodule）に移行（他プロジェクトからも参照可能にする）
- AWS ノウハウ集 (oss/experiment/cloud/aws) に CI/CD Variables 知見・cp932 問題を追記

**CLAUDE.md changes / CLAUDE.md 変更:**
- Phase 5 ステータス更新
- LCD タッチ依存の完全解消（gui_initialize_complete_flag + 全4タスク通知）の知見を追記
- AWS IoT Core 接続アーキテクチャ・プロビジョニング方法・PEM プロトコルの知見を追記
- rfp-cli `-range-exclude` によるデータフラッシュ保護オプションを追記
- デバイス ID 方式、CI/CD Variables 管理、Windows Runner 注意点を追記
- アクションアイテム追加: AWS ノウハウ export、SD カード更新の完全自動化、device_config 共通化

### 2026-03-01: Phase 4 — boot_loader UART を COM7 (SCI7, 921600bps) に変更

Changed boot_loader UART download from COM6 (SCI2, 115200bps, on-board RL78/G1C) to COM7 (SCI7, 921600bps, PMOD FTDI). This provides ~8x faster download speed, significantly improving debug turnaround time.

boot_loader の UART ダウンロードを COM6 (SCI2, 115200bps, オンボード RL78/G1C) から COM7 (SCI7, 921600bps, PMOD FTDI) に変更。ダウンロード速度が約 8 倍に向上し、デバッグの効率が大幅に改善される。

**Changes / 変更点:**
- `r_bsp_config.h`: `MY_BSP_CFG_SERIAL_TERM_SCI` = 2→7, `MY_BSP_CFG_SERIAL_TERM_SCI_BITRATE` = 115200→921600
- `.gitlab-ci.yml`: `UART_PORT` = COM6→COM7, `UART_BAUD_RATE` = 115200→921600
- `test_boot_loader.py`, `test_uart_download.py`: デフォルト値・コメント更新
- CLAUDE.md: Phase 4 ステータス・ドキュメント更新

**Notes / 備考:**
- boot_loader コードは `rx72n_boot_loader.c` の `#elif` チェーンで全 SCI チャネル対応済み — コード変更不要
- `.scfg` は SCI7 のピン (P90/P92) とチャネルが既に有効化済み — 変更不要
- `MY_BSP_CFG_*` はこの BSP バージョン (v5.52) では SMC 管轄外のユーザー追加マクロ
- COM7 (PMOD FTDI) は E2 Lite と別の USB デバイスのため、rfp-cli デバッガ切断時の USB バスリセットの影響を受けない（旧 COM6 では問題だった）

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

## Zenn 記事ネタ

Claude Code との組み込み開発協業で得た知見・エピソードのメモ。

**計画モードの破壊力:**
- Claude Code の「計画モード」は Opus モデルになりトークン消費は激しいが、複雑なデバッグやコード分析にはうってつけ
- 難しい分析を依頼する際に「〇〇の分析計画を考えて」と「計画」を依頼すると計画モードが発動し分析精度が飛躍的に上がる
- 「計画」と言わなくても Claude が自発的に計画モードに入ることもある

**GUI 疑似操作の無茶振りに対する応答:**
- 「画面タッチを自分でやるのめんどくさいから、CI/CD で疑似操作できるよう、コード改造計画考えて」のような無茶振りに対し、計画モードの後余裕で「emWin のイベント発行 API を呼べば疑似タッチ操作が可能。コードを埋め込みビルドし実機で動作させます」と応答

**Claude の得意分野:**
- AWS CLI の操作、GitLab CI/CD や Linux の設定、Python ツールの作成力は抜群。人間など足元にも及ばない
- 今回 GUI 環境（人間の環境）をベースに CUI 環境（Claude の環境）を構築。トラブル発生時に Claude は環境全体を一瞬で比較検証できるのは流石

**マイコンデバッグでの課題:**
- マイコンデバッグにおいてはまだおかしなことを言うことがある
- なるべく実機デバッグをしない方向で指揮を執ったが、1回だけ実機デバッグが必要になった

**環境バージョン見落とし事件:**
- Claude は計画書に指定した環境バージョン指定を見落とした（指定: e2studio 2024-01、Claude: e2studio 2025-12）
- Claude と人間とで環境バージョンの違いに関する感度が異なった。Claude は汎用 PC の世界観、人間は組み込みシステムの世界観
- 組み込みの場合はツールがデリケートなのでバージョン違いがすぐにコードに影響する
- ただ、このデメリットを補って余りあるメリットが Claude と組むことにはある。間違いない
- しばらくはベテランと Claude の組み合わせが必要。今は素人と Claude を組ませるのはまだ危険
- CLAUDE.md の充実を急がねばならない

**「ひらめき」の比較:**
- 20年分の組み込み経験値からくる「ひらめき」は、ゼロコンテキストから開始され CLAUDE.md しか情報を持たない Claude の「ひらめき」にまだ勝っているようだ
- 不具合に直面して進めなくなったときに、ヒントを先に思い付くのは人間のほうが多かったかもしれない

**MOT 比較今昔物語（Claude が雑談中に発言）:**

昔:
```
後輩: 「なんか違いますね？」
石黒さん: 「どこが？」
後輩: 「わかんないです。なんか違います。」
石黒さん: 「...（WinMerge 起動）」
後輩: 「すみません」
```

今:
```
Claude: 「104,279行差分あります。SCI2の割り込み優先度がLevel 15になってます。
         SMCバージョン1.0.111と1.0.130の違いで、CIのheadless buildでは
         SMCが再生成しないためです」
石黒さん: 「...CLAUDE.mdにe2 studio 2024-01使えって書いてあるのに
           なんで2025-12使ってんの」
Claude: 「すみません」
```
