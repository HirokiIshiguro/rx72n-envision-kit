#!/usr/bin/env python3
"""prepare_ota: Flash boot_loader, UART download OTA v1, provision, reset.

Cross-platform (Windows / Linux) replacement for the inline bash script
that previously ran in the prepare_ota CI job.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_serial_port import resolve_port


def find_rfp_cli(hint: str) -> str:
    """Resolve rfp-cli executable path."""
    found = shutil.which(hint)
    if found:
        return found
    if sys.platform == "win32":
        import glob
        for pattern in [
            r"C:\Program Files\Renesas Electronics\Programming Tools\Renesas Flash Programmer*\rfp-cli.exe",
            r"C:\Program Files (x86)\Renesas Electronics\Programming Tools\Renesas Flash Programmer*\rfp-cli.exe",
        ]:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
    return hint


def run(cmd, **kwargs):
    """Run a command and exit on failure."""
    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"ERROR: command exited with {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rfp-cli", default=os.environ.get("RFP_CLI", "rfp-cli"))
    p.add_argument("--rfp-tool", default=os.environ.get("RFP_TOOL", "e2l"))
    p.add_argument("--rfp-speed", default=os.environ.get("RFP_SPEED", "1500K"))
    p.add_argument("--mot", required=True, help="Path to boot_loader .mot")
    p.add_argument("--rsu", required=True, help="Path to ota_v1.rsu")
    p.add_argument("--uart-port", default=os.environ.get("UART_PORT"))
    p.add_argument("--uart-baud", default=os.environ.get("UART_BAUD_RATE", "921600"))
    p.add_argument("--command-port", default=os.environ.get("COMMAND_PORT"))
    p.add_argument("--command-baud", default=os.environ.get("COMMAND_BAUD_RATE", "115200"))
    p.add_argument("--device-id", default=os.environ.get("DEVICE_ID", "rx72n-01"))
    p.add_argument("--codesigner-cert", default=None)
    p.add_argument("--stop-after", default=os.environ.get("PREPARE_OTA_STOP_AFTER", ""),
                    choices=["", "flash", "uart", "provision"])
    p.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = p.parse_args()

    rfp = find_rfp_cli(args.rfp_cli)

    # Resolve serial ports for current platform
    if args.uart_port:
        args.uart_port = resolve_port(args.uart_port)
    if args.command_port:
        args.command_port = resolve_port(args.command_port)

    # --- Step 1: Flash boot_loader ---
    if not os.path.isfile(args.mot):
        print(f"ERROR: boot_loader.mot not found: {args.mot}", file=sys.stderr)
        sys.exit(1)

    print("=== Flash boot_loader (OTA) ===", flush=True)
    run([rfp, "-device", "RX72x", "-tool", args.rfp_tool,
         "-if", "fine", "-speed", args.rfp_speed,
         "-auth", "id", "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
         "-erase-chip", "-noquery"])
    run([rfp, "-device", "RX72x", "-tool", args.rfp_tool,
         "-if", "fine", "-speed", args.rfp_speed,
         "-auth", "id", "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
         "-p", args.mot, "-v", "-run", "-noquery"])
    print("Boot loader flashed successfully.", flush=True)

    if args.stop_after == "flash":
        print("[INFO] stop-after=flash: stopping after boot_loader flash.")
        return

    # --- Step 2: UART Download v1 ---
    if not os.path.isfile(args.rsu):
        print(f"ERROR: ota_v1.rsu not found: {args.rsu}", file=sys.stderr)
        sys.exit(1)

    rsu_size = os.path.getsize(args.rsu)
    print("=== UART Download v1 (OTA firmware) ===", flush=True)
    print(f"  RSU:  {args.rsu} ({rsu_size} bytes)")
    print(f"  Port: {args.uart_port} @ {args.uart_baud}bps")
    run([sys.executable,
         os.path.join(args.project_dir, "test_scripts", "uart_test", "test_uart_download.py"),
         "--rsu", args.rsu, "--port", args.uart_port, "--baud", args.uart_baud,
         "--timeout", "300", "--diag", "--wait-for-ready", "--ready-timeout", "60"])

    if args.stop_after == "uart":
        print("[INFO] stop-after=uart: stopping after UART download.")
        return

    # --- Step 3: Provision ---
    print("=== AWS IoT Core Provisioning (with code signer cert) ===", flush=True)
    print(f"  Device ID: {args.device_id}")
    provision_cmd = [
        sys.executable,
        os.path.join(args.project_dir, "test_scripts", "uart_test", "provision_aws.py"),
        "--device-id", args.device_id,
        "--port", args.command_port,
    ]
    if args.codesigner_cert:
        provision_cmd += ["--codesigner-cert", args.codesigner_cert]
    run(provision_cmd)

    if args.stop_after == "provision":
        print("[INFO] stop-after=provision: stopping after provisioning.")
        return

    # --- Step 4: Reset ---
    print("=== Resetting device ===", flush=True)
    run([sys.executable,
         os.path.join(args.project_dir, "tools", "ci", "send_serial_command.py"),
         "--port", args.command_port, "--baud", args.command_baud,
         "--command", "reset", "--delay-after", "1"])
    print("Reset command sent. Waiting for OTA Agent startup...")
    time.sleep(10)


if __name__ == "__main__":
    main()
