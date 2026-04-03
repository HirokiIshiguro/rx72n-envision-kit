#!/usr/bin/env python3
"""download_aws_demos: Convert .mot to .rsu and UART download aws_demos.

Cross-platform (Windows / Linux) replacement for the inline bash script
that previously ran in the download_aws_demos CI job.
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_serial_port import resolve_port


def run(cmd, **kwargs):
    """Run a command and exit on failure."""
    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"ERROR: command exited with {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mot", required=True, help="Path to aws_demos.mot")
    p.add_argument("--key", required=True, help="Path to ECDSA private key")
    p.add_argument("--rsu-out", required=True, help="Output .rsu path")
    p.add_argument("--seq-no", default=os.environ.get("RSU_SEQ_NO", "1"))
    p.add_argument("--uart-port", default=os.environ.get("UART_PORT"))
    p.add_argument("--uart-baud", default=os.environ.get("UART_BAUD_RATE", "921600"))
    p.add_argument("--timeout", default="300")
    p.add_argument("--rfp-cli", default=os.environ.get("RFP_CLI", "rfp-cli"))
    p.add_argument("--rfp-tool", default=os.environ.get("RFP_TOOL", "e2l"))
    p.add_argument("--rfp-speed", default=os.environ.get("RFP_SPEED", "750K"))
    p.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = p.parse_args()

    if not os.path.isfile(args.mot):
        print(f"ERROR: aws_demos.mot not found: {args.mot}", file=sys.stderr)
        sys.exit(1)

    print("=== Convert .mot to .rsu ===", flush=True)
    print(f"  MOT: {args.mot}")
    print(f"  Key: {args.key}")
    print(f"  RSU: {args.rsu_out}")
    print(f"  Seq: {args.seq_no}")

    mot_to_rsu = os.path.join(args.project_dir, "tools", "mcu-tool-rx", "mot_to_rsu.py")
    run([sys.executable, mot_to_rsu,
         "--mot", args.mot, "--key", args.key,
         "-o", args.rsu_out, "--seq-no", args.seq_no])

    uart_port = resolve_port(args.uart_port)
    print("=== UART Download ===", flush=True)
    print(f"  RSU:  {args.rsu_out}")
    print(f"  Port: {uart_port} @ {args.uart_baud}bps")

    # Build reset command: rfp-cli -sig -run re-starts the MCU so the
    # boot_loader outputs the ready message on the already-opened UART.
    reset_cmd = (
        f"{args.rfp_cli} -device RX72x -tool {args.rfp_tool}"
        f" -if fine -speed {args.rfp_speed}"
        f" -auth id FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        f" -sig -run -noquery"
    )
    print(f"  Reset: {reset_cmd}")

    download_script = os.path.join(
        args.project_dir, "test_scripts", "uart_test", "test_uart_download.py")
    run([sys.executable, download_script,
         "--rsu", args.rsu_out, "--port", uart_port, "--baud", args.uart_baud,
         "--timeout", args.timeout, "--diag",
         "--wait-for-ready", "--ready-timeout", "60",
         "--reset-cmd", reset_cmd])


if __name__ == "__main__":
    main()
