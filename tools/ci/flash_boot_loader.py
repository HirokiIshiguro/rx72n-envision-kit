#!/usr/bin/env python3
"""Flash boot_loader and optionally run the boot banner health check."""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runner-handle"))
from runner_handle.rfp_cli import run_or_exit
from runner_handle.serial_port import resolve_port


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rfp-cli", default=os.environ.get("RFP_CLI", "rfp-cli"))
    parser.add_argument("--rfp-tool", default=os.environ.get("RFP_TOOL", "e2l"))
    parser.add_argument("--rfp-speed", default=os.environ.get("RFP_SPEED", "1500K"))
    parser.add_argument("--mot", required=True, help="Path to boot_loader MOT")
    parser.add_argument("--uart-port", default=os.environ.get("UART_PORT"))
    parser.add_argument("--uart-baud", default=os.environ.get("UART_BAUD_RATE", "921600"))
    parser.add_argument("--run-healthcheck", default=os.environ.get("RUN_HW_HEALTHCHECK", "false"))
    parser.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = parser.parse_args()

    snapshot_log = os.path.join(args.project_dir, "boot_loader_hardware_state.log")
    health_log = os.path.join(args.project_dir, "boot_loader_health.log")
    open(snapshot_log, "w").close()
    open(health_log, "w").close()

    if not os.path.isfile(args.mot):
        print(f"ERROR: {args.mot} not found", file=sys.stderr)
        return 1

    flash_script = os.path.join(args.project_dir, "tools", "runner-handle", "scripts", "flash_firmware.py")
    run_or_exit(
        [
            sys.executable,
            flash_script,
            "--device",
            "RX72x",
            "--rfp-cli",
            args.rfp_cli,
            "--rfp-tool",
            args.rfp_tool,
            "--rfp-speed",
            str(args.rfp_speed),
            "--mot",
            args.mot,
        ]
    )

    if args.run_healthcheck.lower() != "true":
        print("  Boot loader health-check skipped (RUN_HW_HEALTHCHECK=false).")
        return 0

    uart_port = resolve_port(args.uart_port)
    health_script = os.path.join(args.project_dir, "test_scripts", "uart_test", "check_device_health.py")
    cmd = [
        sys.executable,
        health_script,
        "boot-banner",
        "--port",
        uart_port,
        "--baud",
        str(args.uart_baud),
        "--expect",
        "RX72N secure boot program",
        "--expect",
        'send "userprog.rsu" via UART.',
        "--timeout",
        "20",
    ]
    print(f"  > {' '.join(cmd)}", flush=True)
    with open(health_log, "w", encoding="utf-8") as output:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            sys.stdout.write(line)
            output.write(line)
        proc.wait()
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
