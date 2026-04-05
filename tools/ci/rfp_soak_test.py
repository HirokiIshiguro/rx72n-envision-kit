#!/usr/bin/env python3
"""Run rfp-cli soak tests for E2 Lite reliability diagnostics."""

import argparse
import datetime
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runner-handle"))
from runner_handle.rfp_cli import find_rfp_cli


def run_capture(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except Exception as exc:
        return -1, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--loops", type=int, default=25)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--mode", choices=["sig", "flash_boot"], default="sig")
    parser.add_argument("--device", default="RX72x")
    parser.add_argument("--tool", default=os.environ.get("RFP_TOOL", "e2l"))
    parser.add_argument("--speed", default=os.environ.get("RFP_SPEED", "1500K"))
    parser.add_argument("--auth-id", default="FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF")
    parser.add_argument("--rfp-cli", default=os.environ.get("RFP_CLI", "rfp-cli"))
    parser.add_argument("--mot", default=None)
    args = parser.parse_args()

    rfp = find_rfp_cli(args.rfp_cli)
    if args.mode == "flash_boot":
        if not args.mot:
            print("ERROR: --mot is required for flash_boot mode", file=sys.stderr)
            return 2
        if not os.path.isfile(args.mot):
            print(f"ERROR: MOT file not found: {args.mot}", file=sys.stderr)
            return 2

    os.makedirs(args.output_dir, exist_ok=True)
    summary_tsv = os.path.join(args.output_dir, "summary.tsv")
    summary_txt = os.path.join(args.output_dir, "summary.txt")

    with open(summary_txt, "w", encoding="utf-8") as output:
        output.write(f"timestamp_start={datetime.datetime.now().isoformat()}\n")
        output.write(f"mode={args.mode}\n")
        output.write(f"device={args.device}\n")
        output.write(f"tool={args.tool}\n")
        output.write(f"speed={args.speed}\n")
        output.write(f"loops={args.loops}\n")
        output.write(f"sleep_seconds={args.sleep_seconds}\n")
        if args.mot:
            output.write(f"mot={args.mot}\n")

    with open(summary_tsv, "w", encoding="utf-8") as output:
        output.write("iteration\ttimestamp\tlist_tools_status\tserial_present\trfp_status\n")

    for index in range(1, args.loops + 1):
        prefix = os.path.join(args.output_dir, f"iter_{index:03d}")
        timestamp = datetime.datetime.now().isoformat()

        list_status, list_output = run_capture([rfp, "-device", args.device, "-list-tools"])
        with open(f"{prefix}.list-tools.log", "w", encoding="utf-8") as output:
            output.write(list_output)
        serial_present = "yes" if re.search(r"^\s+[A-Za-z0-9:]+", list_output, re.MULTILINE) else "no"

        if args.mode == "sig":
            rfp_status, rfp_output = run_capture(
                [
                    rfp,
                    "-device",
                    args.device,
                    "-tool",
                    args.tool,
                    "-if",
                    "fine",
                    "-speed",
                    args.speed,
                    "-auth",
                    "id",
                    args.auth_id,
                    "-sig",
                    "-run",
                    "-noquery",
                ]
            )
        else:
            erase_status, erase_output = run_capture(
                [
                    rfp,
                    "-device",
                    args.device,
                    "-tool",
                    args.tool,
                    "-if",
                    "fine",
                    "-speed",
                    args.speed,
                    "-auth",
                    "id",
                    args.auth_id,
                    "-erase-chip",
                    "-noquery",
                ]
            )
            if erase_status != 0:
                rfp_status, rfp_output = erase_status, erase_output
            else:
                flash_status, flash_output = run_capture(
                    [
                        rfp,
                        "-device",
                        args.device,
                        "-tool",
                        args.tool,
                        "-if",
                        "fine",
                        "-speed",
                        args.speed,
                        "-auth",
                        "id",
                        args.auth_id,
                        "-p",
                        args.mot,
                        "-v",
                        "-run",
                        "-noquery",
                    ]
                )
                rfp_status = flash_status
                rfp_output = erase_output + "\n" + flash_output

        with open(f"{prefix}.rfp.log", "w", encoding="utf-8") as output:
            output.write(rfp_output)
        with open(summary_tsv, "a", encoding="utf-8") as output:
            output.write(f"{index}\t{timestamp}\t{list_status}\t{serial_present}\t{rfp_status}\n")
        with open(summary_txt, "a", encoding="utf-8") as output:
            output.write(
                f"iteration={index} list_tools_status={list_status} "
                f"serial_present={serial_present} rfp_status={rfp_status}\n"
            )

        print(
            f"iteration={index} list_tools_status={list_status} "
            f"serial_present={serial_present} rfp_status={rfp_status}",
            flush=True,
        )
        if rfp_status != 0:
            with open(summary_txt, "a", encoding="utf-8") as output:
                output.write(f"failure_iteration={index}\n")
            return rfp_status
        time.sleep(args.sleep_seconds)

    with open(summary_txt, "a", encoding="utf-8") as output:
        output.write("result=success\n")
    print("Soak test completed successfully.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
