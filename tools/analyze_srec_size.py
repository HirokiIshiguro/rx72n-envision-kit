#!/usr/bin/env python3
"""Summarize programmed bytes in Motorola S-record files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ADDRESS_LENGTH_HEX = {
    "1": 4,
    "2": 6,
    "3": 8,
}


def parse_srec(path: Path) -> dict[str, object]:
    total_data_bytes = 0
    buckets: dict[int, int] = {}

    for line in path.read_text().splitlines():
        if not line.startswith("S") or len(line) < 4:
            continue

        record_type = line[1]
        if record_type not in ADDRESS_LENGTH_HEX:
            continue

        address_hex_len = ADDRESS_LENGTH_HEX[record_type]
        address = int(line[4 : 4 + address_hex_len], 16)
        data_bytes = len(line[4 + address_hex_len : -2]) // 2

        total_data_bytes += data_bytes
        bucket = address & 0xFFF00000
        buckets[bucket] = buckets.get(bucket, 0) + data_bytes

    return {
        "path": str(path),
        "file_size_bytes": path.stat().st_size,
        "programmed_data_bytes": total_data_bytes,
        "address_buckets": [
            {
                "base": f"0x{bucket:08X}",
                "data_bytes": size,
            }
            for bucket, size in sorted(buckets.items())
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate programmed bytes in Motorola S-record files."
    )
    parser.add_argument("paths", nargs="+", help="Input .mot/.srec file paths")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    reports = [parse_srec(Path(path)) for path in args.paths]

    if args.json:
        print(json.dumps(reports, ensure_ascii=True, indent=2))
        return 0

    for report in reports:
        print(report["path"])
        print(f"  file_size_bytes: {report['file_size_bytes']}")
        print(f"  programmed_data_bytes: {report['programmed_data_bytes']}")
        for bucket in report["address_buckets"]:
            print(f"  {bucket['base']}: {bucket['data_bytes']}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
