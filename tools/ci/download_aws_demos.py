#!/usr/bin/env python3
"""Convert aws_demos MOT to RSU and download it over UART."""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runner-handle"))
from runner_handle.rfp_cli import run_or_exit
from runner_handle.serial_port import resolve_port


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mot", required=True, help="Path to aws_demos.mot")
    parser.add_argument("--key", required=True, help="Path to ECDSA private key")
    parser.add_argument("--rsu-out", required=True, help="Output RSU path")
    parser.add_argument("--seq-no", default=os.environ.get("RSU_SEQ_NO", "1"))
    parser.add_argument("--uart-port", default=os.environ.get("UART_PORT"))
    parser.add_argument("--uart-baud", default=os.environ.get("UART_BAUD_RATE", "921600"))
    parser.add_argument("--timeout", default="300")
    parser.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = parser.parse_args()

    if not os.path.isfile(args.mot):
        print(f"ERROR: aws_demos.mot not found: {args.mot}", file=sys.stderr)
        return 1

    print("=== Convert .mot to .rsu ===", flush=True)
    print(f"  MOT: {args.mot}")
    print(f"  Key: {args.key}")
    print(f"  RSU: {args.rsu_out}")
    print(f"  Seq: {args.seq_no}")
    mot_to_rsu = os.path.join(args.project_dir, "tools", "mcu-tool-rx", "mot_to_rsu.py")
    run_or_exit(
        [
            sys.executable,
            mot_to_rsu,
            "--mot",
            args.mot,
            "--key",
            args.key,
            "-o",
            args.rsu_out,
            "--seq-no",
            str(args.seq_no),
        ]
    )

    uart_port = resolve_port(args.uart_port)
    print("=== UART Download ===", flush=True)
    print(f"  RSU:  {args.rsu_out}")
    print(f"  Port: {uart_port} @ {args.uart_baud}bps")
    download_script = os.path.join(args.project_dir, "tools", "runner-handle", "scripts", "uart_download.py")
    run_or_exit(
        [
            sys.executable,
            download_script,
            "--rsu",
            args.rsu_out,
            "--port",
            uart_port,
            "--baud",
            str(args.uart_baud),
            "--timeout",
            str(args.timeout),
            "--diag",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
