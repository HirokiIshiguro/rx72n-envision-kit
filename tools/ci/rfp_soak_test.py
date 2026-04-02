#!/usr/bin/env python3
"""rfp_soak_test: Run rfp-cli soak test for E2 Lite reliability diagnostics.

Cross-platform (Windows / Linux) replacement for run_rfp_soak_test.sh.
"""

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
    """Run command and return (exit_code, stdout_text)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except Exception as e:
        return -1, str(e)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--loops", type=int, default=25)
    p.add_argument("--sleep-seconds", type=float, default=1.0)
    p.add_argument("--mode", choices=["sig", "flash_boot"], default="sig")
    p.add_argument("--device", default="RX72x")
    p.add_argument("--tool", default=os.environ.get("RFP_TOOL", "e2l"))
    p.add_argument("--speed", default=os.environ.get("RFP_SPEED", "1500K"))
    p.add_argument("--auth-id", default="FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF")
    p.add_argument("--rfp-cli", default=os.environ.get("RFP_CLI", "rfp-cli"))
    p.add_argument("--mot", default=None)
    args = p.parse_args()

    rfp = find_rfp_cli(args.rfp_cli)

    if args.mode == "flash_boot":
        if not args.mot:
            print("ERROR: --mot is required for flash_boot mode", file=sys.stderr)
            sys.exit(2)
        if not os.path.isfile(args.mot):
            print(f"ERROR: MOT file not found: {args.mot}", file=sys.stderr)
            sys.exit(2)

    os.makedirs(args.output_dir, exist_ok=True)
    summary_tsv = os.path.join(args.output_dir, "summary.tsv")
    summary_txt = os.path.join(args.output_dir, "summary.txt")

    with open(summary_txt, "w") as f:
        f.write(f"timestamp_start={datetime.datetime.now().isoformat()}\n")
        f.write(f"mode={args.mode}\n")
        f.write(f"device={args.device}\n")
        f.write(f"tool={args.tool}\n")
        f.write(f"speed={args.speed}\n")
        f.write(f"loops={args.loops}\n")
        f.write(f"sleep_seconds={args.sleep_seconds}\n")
        if args.mot:
            f.write(f"mot={args.mot}\n")

    with open(summary_tsv, "w") as f:
        f.write("iteration\ttimestamp\tlist_tools_status\tserial_present\trfp_status\n")

    for i in range(1, args.loops + 1):
        prefix = os.path.join(args.output_dir, f"iter_{i:03d}")
        timestamp = datetime.datetime.now().isoformat()

        # List tools
        list_status, list_output = run_capture([rfp, "-device", args.device, "-list-tools"])
        with open(f"{prefix}.list-tools.log", "w") as f:
            f.write(list_output)

        serial_present = "yes" if re.search(r'^\s+[A-Za-z0-9:]+', list_output, re.MULTILINE) else "no"

        # RFP operation
        if args.mode == "sig":
            rfp_status, rfp_output = run_capture([
                rfp, "-device", args.device, "-tool", args.tool,
                "-if", "fine", "-speed", args.speed,
                "-auth", "id", args.auth_id, "-sig", "-run", "-noquery"])
        else:  # flash_boot
            s1, o1 = run_capture([
                rfp, "-device", args.device, "-tool", args.tool,
                "-if", "fine", "-speed", args.speed,
                "-auth", "id", args.auth_id, "-erase-chip", "-noquery"])
            if s1 != 0:
                rfp_status, rfp_output = s1, o1
            else:
                s2, o2 = run_capture([
                    rfp, "-device", args.device, "-tool", args.tool,
                    "-if", "fine", "-speed", args.speed,
                    "-auth", "id", args.auth_id,
                    "-p", args.mot, "-v", "-run", "-noquery"])
                rfp_status = s2
                rfp_output = o1 + "\n" + o2

        with open(f"{prefix}.rfp.log", "w") as f:
            f.write(rfp_output)

        with open(summary_tsv, "a") as f:
            f.write(f"{i}\t{timestamp}\t{list_status}\t{serial_present}\t{rfp_status}\n")
        with open(summary_txt, "a") as f:
            f.write(f"iteration={i} list_tools_status={list_status} serial_present={serial_present} rfp_status={rfp_status}\n")

        print(f"iteration={i} list_tools_status={list_status} serial_present={serial_present} rfp_status={rfp_status}", flush=True)

        if rfp_status != 0:
            with open(summary_txt, "a") as f:
                f.write(f"failure_iteration={i}\n")
            sys.exit(rfp_status)

        time.sleep(args.sleep_seconds)

    with open(summary_txt, "a") as f:
        f.write("result=success\n")
    print("Soak test completed successfully.", flush=True)


if __name__ == "__main__":
    main()
