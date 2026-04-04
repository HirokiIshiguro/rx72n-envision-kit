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
    parser.add_argument("--device-id", default=os.environ.get("DEVICE_ID", "rx72n-02"))
    parser.add_argument("--codesigner-cert", default=None)
    parser.add_argument("--command-port", default=os.environ.get("COMMAND_PORT"))
    parser.add_argument("--mac-address", default=os.environ.get("MAC_ADDR"))
    parser.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = parser.parse_args()

    print("=== AWS IoT Core Provisioning ===", flush=True)
    print(f"  Device ID: {args.device_id}")

    provision_script = os.path.join(args.project_dir, "test_scripts", "uart_test", "provision_aws.py")
    cmd = [sys.executable, provision_script, "--device-id", args.device_id]
    if args.codesigner_cert:
        cmd += ["--codesigner-cert", args.codesigner_cert]
    if args.command_port:
        cmd += ["--port", resolve_port(args.command_port)]
    if args.mac_address:
        cmd += ["--mac-address", args.mac_address]

    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
