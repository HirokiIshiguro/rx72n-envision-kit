#!/usr/bin/env python3
"""provision_aws: Provision AWS IoT Core credentials to device via UART.

Cross-platform (Windows / Linux) replacement for the inline bash script
that previously ran in the provision_aws_credentials CI job.
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_serial_port import resolve_port


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--device-id", default=os.environ.get("DEVICE_ID", "rx72n-01"))
    p.add_argument("--codesigner-cert", default=None,
                    help="Path to code signer certificate")
    p.add_argument("--command-port", default=os.environ.get("COMMAND_PORT"))
    p.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = p.parse_args()

    print("=== AWS IoT Core Provisioning ===", flush=True)
    print(f"  Device ID: {args.device_id}")

    provision_script = os.path.join(
        args.project_dir, "test_scripts", "uart_test", "provision_aws.py")
    cmd = [
        sys.executable, provision_script,
        "--device-id", args.device_id,
    ]
    if args.codesigner_cert:
        cmd += ["--codesigner-cert", args.codesigner_cert]
    if args.command_port:
        cmd_port = resolve_port(args.command_port)
        cmd += ["--port", cmd_port]

    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
