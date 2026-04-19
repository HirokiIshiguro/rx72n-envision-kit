#!/usr/bin/env python3
"""SC コード生成後に必要な後処理パッチを当てる (Phase 8b 第3次 段階5-5 / #58 で導入)。

背景:
    e2 studio 2025-12 同梱の Smart Configurator が r_bsp 7.52 用に r_bsp_config.h を
    生成すると、BSP_CFG_MCU_PART_GROUP / BSP_CFG_MCU_PART_SERIES を文字列リテラル
    ("RX72N") / ("RX700") として書き出す。一方 BSP 本体 mcu/rx72n/mcu_info.h の
    判定は `#if BSP_CFG_MCU_PART_SERIES == 0x0` の整数比較のままで、これは
    legacy r_bsp 5.52 + 旧 SC では `(0x0)` 整数を出していた挙動を前提としている。
    Renesas 側 SC ツールのリグレッションが解消するまでの workaround として、
    SC 生成直後・ビルド直前に文字列を `(0x0)` に戻す。

使い方:
    python tools/ci/sc_postgen_patch.py            # 既知プロジェクトを全て処理
    python tools/ci/sc_postgen_patch.py <path>     # 特定 r_bsp_config.h を処理

冪等。既に (0x0) になっている場合は何もせず exit 0。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_TARGETS = [
    REPO_ROOT / "Projects" / "aws_ether_rx72n_envision_kit" / "e2studio_ccrx"
        / "src" / "smc_gen" / "r_config" / "r_bsp_config.h",
    REPO_ROOT / "Projects" / "boot_loader_rx72n_envision_kit" / "e2studio_ccrx"
        / "src" / "smc_gen" / "r_config" / "r_bsp_config.h",
]

PATCH_RULES = [
    (re.compile(r'(#define\s+BSP_CFG_MCU_PART_GROUP\s+)\("[^"]*"\)'),  r"\1(0x0)"),
    (re.compile(r'(#define\s+BSP_CFG_MCU_PART_SERIES\s+)\("[^"]*"\)'), r"\1(0x0)"),
]


def patch(path: Path) -> bool:
    if not path.is_file():
        print(f"[skip] not found: {path}")
        return False
    original = path.read_text(encoding="utf-8")
    patched = original
    for pattern, replacement in PATCH_RULES:
        patched = pattern.sub(replacement, patched)
    if patched == original:
        print(f"[ok]   already patched: {path}")
        return False
    path.write_text(patched, encoding="utf-8")
    print(f"[fix]  patched: {path}")
    return True


def main(argv: list[str]) -> int:
    targets = [Path(a).resolve() for a in argv[1:]] if len(argv) > 1 else DEFAULT_TARGETS
    changed = 0
    for t in targets:
        if patch(t):
            changed += 1
    print(f"--- sc_postgen_patch: {changed} file(s) modified ---")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
