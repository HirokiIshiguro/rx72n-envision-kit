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
| 1 | Documentation cleanup: migrate Wiki to `docs/` | In progress |
| 2 | Set up Claude-assisted development environment | In progress |
| 3 | Set up CI/CD pipeline | Planned |
| 4 | Replace FreeRTOS with latest Renesas IoT reference implementation ([iot-reference-rx](https://github.com/renesas/iot-reference-rx)) | Planned |

## Repository Locations / リポジトリ

| Location | URL |
|---|---|
| Primary (GitLab) | https://shelty2.servegame.com/oss/import/github/renesas/rx72n-envision-kit |
| Mirror (GitHub fork) | https://github.com/HirokiIshiguro/rx72n-envision-kit |
| Upstream (GitHub) | https://github.com/renesas/rx72n-envision-kit |

## Changelog / 変更履歴

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

## Git Conventions / Git ルール

- Commits by Claude Code must use: `--author="Claude Code <claude-code@noreply.anthropic.com>"`
- Commits by the human owner use the default git config author
