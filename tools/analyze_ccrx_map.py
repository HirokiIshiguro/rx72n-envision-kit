#!/usr/bin/env python3
"""Summarize ROM/RAM usage from Renesas CCRX linker map files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


MAPPING_ROW_RE = re.compile(
    r"^\s*([0-9a-fA-F]{8})\s+([0-9a-fA-F]{8})\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s*$"
)
FILE_RANGE_RE = re.compile(
    r"^\s*([0-9a-fA-F]{8})\s+([0-9a-fA-F]{8})\s+([0-9a-fA-F]+)\s*$"
)
TOTAL_SECTION_RE = re.compile(
    r"^(RAMDATA|ROMDATA|PROGRAM) SECTION:\s+([0-9a-fA-F]+) Byte\(s\)$"
)


def is_flash_like_address(address: int) -> bool:
    return 0x00100000 <= address < 0x00200000 or address >= 0xFE000000


def parse_mapping_sections(lines: list[str]) -> list[dict[str, int | str]]:
    sections: list[dict[str, int | str]] = []
    in_mapping_list = False
    pending_name: str | None = None

    for line in lines:
        if line.startswith("*** Mapping List ***"):
            in_mapping_list = True
            pending_name = None
            continue

        if not in_mapping_list:
            continue

        if line.startswith("*** Total Section Size ***"):
            break

        if not line.strip() or line.startswith("SECTION"):
            continue

        row_match = MAPPING_ROW_RE.match(line)
        if row_match and pending_name is not None:
            start = int(row_match.group(1), 16)
            end = int(row_match.group(2), 16)
            size = int(row_match.group(3), 16)
            align = int(row_match.group(4), 16)
            sections.append(
                {
                    "name": pending_name,
                    "start": start,
                    "end": end,
                    "size": size,
                    "align": align,
                    "region": "flash_like"
                    if is_flash_like_address(start)
                    else "ram_like",
                }
            )
            pending_name = None
            continue

        if not line.startswith(" "):
            pending_name = line.strip()

    return sections


def parse_total_sections(lines: list[str]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for line in lines:
        match = TOTAL_SECTION_RE.match(line.strip())
        if match:
            totals[match.group(1).lower()] = int(match.group(2), 16)
    return totals


def parse_file_contributions(
    lines: list[str], section_regions: dict[str, str]
) -> dict[str, dict[str, int]]:
    contributions: dict[str, dict[str, int]] = {}
    current_section: str | None = None

    for index, line in enumerate(lines):
        if line.startswith("SECTION="):
            current_section = line.split("=", 1)[1].strip()
            continue

        if not line.startswith("FILE="):
            continue

        if line.startswith("FILE=                               START"):
            continue

        file_path = line.split("=", 1)[1].strip()
        if not file_path or current_section is None:
            continue

        if index + 1 >= len(lines):
            continue

        range_match = FILE_RANGE_RE.match(lines[index + 1])
        if not range_match:
            continue

        size = int(range_match.group(3), 16)
        region = section_regions.get(current_section, "unknown")
        record = contributions.setdefault(
            file_path,
            {
                "flash_like": 0,
                "ram_like": 0,
                "unknown": 0,
                "total": 0,
            },
        )
        record[region] += size
        record["total"] += size

    return contributions


def parse_map(path: Path) -> dict[str, object]:
    lines = path.read_text(errors="ignore").splitlines()
    sections = parse_mapping_sections(lines)
    section_regions = {section["name"]: section["region"] for section in sections}
    totals = parse_total_sections(lines)
    file_contributions = parse_file_contributions(lines, section_regions)

    flash_like_total = totals.get("romdata", 0) + totals.get("program", 0)
    ram_like_total = totals.get("ramdata", 0)

    return {
        "path": str(path),
        "totals": {
            "ramdata": totals.get("ramdata", 0),
            "romdata": totals.get("romdata", 0),
            "program": totals.get("program", 0),
            "flash_like_total": flash_like_total,
            "ram_like_total": ram_like_total,
        },
        "sections": sections,
        "file_contributions": file_contributions,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate ROM/RAM usage from Renesas CCRX linker map files."
    )
    parser.add_argument("paths", nargs="+", help="Input .map file paths")
    parser.add_argument(
        "--budget",
        type=lambda value: int(value, 0),
        default=None,
        help="Optional flash-like budget in bytes for headroom calculation",
    )
    parser.add_argument(
        "--top-files",
        type=int,
        default=10,
        help="Number of top flash-like files to print in text mode",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    return parser


def enrich_report(report: dict[str, object], budget: int | None) -> dict[str, object]:
    if budget is None:
        return report

    totals = report["totals"]
    flash_like_total = int(totals["flash_like_total"])
    report["budget"] = {
        "flash_like_budget": budget,
        "headroom_bytes": budget - flash_like_total,
        "fits": flash_like_total <= budget,
    }
    return report


def summarize_top_files(report: dict[str, object], top_files: int) -> list[tuple[str, int]]:
    contributions = report["file_contributions"]
    ordered = sorted(
        (
            (file_path, int(values["flash_like"]))
            for file_path, values in contributions.items()
            if int(values["flash_like"]) > 0
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    return ordered[:top_files]


def main() -> int:
    args = build_parser().parse_args()
    reports = [enrich_report(parse_map(Path(path)), args.budget) for path in args.paths]

    if args.json:
        print(json.dumps(reports, ensure_ascii=True, indent=2))
        return 0

    for report in reports:
        totals = report["totals"]
        print(report["path"])
        print(f"  ramdata_bytes: {totals['ram_like_total']}")
        print(f"  romdata_bytes: {totals['romdata']}")
        print(f"  program_bytes: {totals['program']}")
        print(f"  flash_like_total_bytes: {totals['flash_like_total']}")
        if "budget" in report:
            budget = report["budget"]
            print(f"  flash_like_budget_bytes: {budget['flash_like_budget']}")
            print(f"  flash_like_headroom_bytes: {budget['headroom_bytes']}")
            print(f"  flash_like_fits: {budget['fits']}")
        for file_path, size in summarize_top_files(report, args.top_files):
            print(f"  top_flash_file: {size:8d} {file_path}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
