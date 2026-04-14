#!/usr/bin/env python3
"""Flash boot_loader, UART download OTA v1, provision, and reset."""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runner-handle"))
from runner_handle.rfp_cli import run_or_exit
from runner_handle.serial_port import resolve_port


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rfp-cli", default=os.environ.get("RFP_CLI", "rfp-cli"))
    parser.add_argument("--rfp-tool", default=os.environ.get("RFP_TOOL", "e2l"))
    parser.add_argument("--rfp-speed", default=os.environ.get("RFP_SPEED", "1500K"))
    parser.add_argument("--mot", required=True, help="Path to boot_loader MOT")
    parser.add_argument("--rsu", required=True, help="Path to OTA v1 RSU")
    parser.add_argument("--uart-port", default=os.environ.get("UART_PORT"))
    parser.add_argument("--uart-baud", default=os.environ.get("UART_BAUD_RATE", "921600"))
    parser.add_argument("--command-port", default=os.environ.get("COMMAND_PORT"))
    parser.add_argument("--command-baud", default=os.environ.get("COMMAND_BAUD_RATE", "115200"))
    parser.add_argument("--device-id", default=os.environ.get("DEVICE_ID", "rx72n-03"))
    parser.add_argument("--codesigner-cert", default=None)
    parser.add_argument("--mac-address", default=os.environ.get("MAC_ADDR"))
    parser.add_argument(
        "--stop-after",
        default=os.environ.get("PREPARE_OTA_STOP_AFTER", ""),
        choices=["", "flash", "uart", "provision"],
    )
    parser.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = parser.parse_args()

    snapshot_log = os.path.join(args.project_dir, "prepare_ota_hardware_state.log")
    open(snapshot_log, "w").close()

    if not os.path.isfile(args.mot):
        print(f"ERROR: boot_loader.mot not found: {args.mot}", file=sys.stderr)
        return 1
    if not os.path.isfile(args.rsu):
        print(f"ERROR: ota_v1.rsu not found: {args.rsu}", file=sys.stderr)
        return 1

    uart_port = resolve_port(args.uart_port) if args.uart_port else None
    command_port = resolve_port(args.command_port) if args.command_port else None
    flash_script = os.path.join(args.project_dir, "tools", "runner-handle", "scripts", "flash_firmware.py")
    download_script = os.path.join(args.project_dir, "tools", "runner-handle", "scripts", "uart_download.py")
    serial_command_script = os.path.join(
        args.project_dir, "tools", "runner-handle", "scripts", "send_serial_command.py"
    )
    provision_script = os.path.join(args.project_dir, "tools", "ci", "provision_aws.py")

    print("=== Flash boot_loader (OTA) ===", flush=True)
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
    if args.stop_after == "flash":
        print("[INFO] stop-after=flash: stopping after boot_loader flash.")
        return 0

    print("=== UART Download v1 (OTA firmware) ===", flush=True)
    print(f"  RSU:  {args.rsu} ({os.path.getsize(args.rsu)} bytes)")
    print(f"  Port: {uart_port} @ {args.uart_baud}bps")
    run_or_exit(
        [
            sys.executable,
            download_script,
            "--rsu",
            args.rsu,
            "--port",
            uart_port,
            "--baud",
            str(args.uart_baud),
            "--timeout",
            "300",
            "--diag",
            "--wait-for-ready",
            "--ready-timeout",
            "60",
        ]
    )
    if args.stop_after == "uart":
        print("[INFO] stop-after=uart: stopping after UART download.")
        return 0

    print("=== AWS IoT Core Provisioning (with code signer cert) ===", flush=True)
    print(f"  Device ID: {args.device_id}")
    provision_cmd = [sys.executable, provision_script, "--device-id", args.device_id]
    if command_port:
        provision_cmd += ["--command-port", command_port]
    if uart_port:
        provision_cmd += ["--uart-port", uart_port, "--uart-baud", str(args.uart_baud)]
    if args.codesigner_cert:
        provision_cmd += ["--codesigner-cert", args.codesigner_cert]
    if args.mac_address:
        provision_cmd += ["--mac-address", args.mac_address]
    provision_cmd += ["--allow-missing-write-confirmation"]
    provision_cmd += ["--rfp-cli", args.rfp_cli, "--rfp-tool", args.rfp_tool, "--rfp-speed", str(args.rfp_speed)]
    provision_cmd += ["--project-dir", args.project_dir]
    run_or_exit(provision_cmd)
    if args.stop_after == "provision":
        print("[INFO] stop-after=provision: stopping after provisioning.")
        return 0

    print("=== Resetting device ===", flush=True)
    run_or_exit(
        [
            sys.executable,
            serial_command_script,
            "--port",
            command_port,
            "--baud",
            str(args.command_baud),
            "--command",
            "reset",
            "--delay-after",
            "1",
        ]
    )
    print("Reset command sent. Waiting for OTA Agent startup...")
    time.sleep(10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
