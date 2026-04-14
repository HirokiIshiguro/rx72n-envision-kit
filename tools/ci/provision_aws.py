#!/usr/bin/env python3
"""Provision AWS IoT Core credentials to the device."""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runner-handle"))
from runner_handle.serial_port import resolve_port


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-id", default=os.environ.get("DEVICE_ID", "rx72n-03"))
    parser.add_argument("--codesigner-cert", default=None)
    parser.add_argument("--command-port", default=os.environ.get("COMMAND_PORT"))
    parser.add_argument("--uart-port", default=os.environ.get("UART_PORT"))
    parser.add_argument("--uart-baud", default=os.environ.get("UART_BAUD_RATE", "921600"))
    parser.add_argument("--mac-address", default=os.environ.get("MAC_ADDR"))
    parser.add_argument("--allow-missing-write-confirmation", action="store_true")
    parser.add_argument("--rfp-cli", default=os.environ.get("RFP_CLI", "rfp-cli"))
    parser.add_argument("--rfp-tool", default=os.environ.get("RFP_TOOL", "e2l"))
    parser.add_argument("--rfp-speed", default=os.environ.get("RFP_SPEED", "1500K"))
    parser.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = parser.parse_args()

    print("=== AWS IoT Core Provisioning ===", flush=True)
    print(f"  Device ID: {args.device_id}")

    provision_script = os.path.join(args.project_dir, "test_scripts", "uart_test", "provision_aws.py")
    reset_cmd = (
        f"\"{args.rfp_cli}\" -device RX72x -tool {args.rfp_tool}"
        f" -if fine -speed {args.rfp_speed}"
        f" -auth id FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        f" -sig -run -noquery"
    )
    cmd = [sys.executable, provision_script, "--device-id", args.device_id]
    if args.codesigner_cert:
        cmd += ["--codesigner-cert", args.codesigner_cert]
    if args.command_port:
        cmd += ["--port", resolve_port(args.command_port)]
    if args.uart_port:
        cmd += ["--log-port", resolve_port(args.uart_port), "--log-baud", str(args.uart_baud)]
    if args.mac_address:
        cmd += ["--mac-address", args.mac_address]
    if args.allow_missing_write_confirmation:
        cmd += ["--allow-missing-write-confirmation"]
    cmd += ["--reset-cmd", reset_cmd]

    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
