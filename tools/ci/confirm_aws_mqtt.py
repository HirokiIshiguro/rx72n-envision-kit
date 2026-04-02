#!/usr/bin/env python3
"""confirm_aws_mqtt: Test AWS IoT Core MQTT connectivity.

Cross-platform (Windows / Linux) replacement for the inline bash script
that previously ran in the confirm_aws_mqtt CI job.
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
    p.add_argument("--timeout", default="120")
    p.add_argument("--uart-port", default=os.environ.get("UART_PORT"))
    p.add_argument("--uart-baud", default=os.environ.get("UART_BAUD_RATE", "921600"))
    p.add_argument("--command-port", default=os.environ.get("COMMAND_PORT"))
    p.add_argument("--command-baud", default=os.environ.get("COMMAND_BAUD_RATE", "115200"))
    p.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = p.parse_args()

    print("=== AWS IoT Core MQTT Connectivity Test ===", flush=True)
    print(f"  Device ID: {args.device_id}")

    cmd_port = resolve_port(args.command_port) if args.command_port else None
    log_port = resolve_port(args.uart_port) if args.uart_port else None

    test_script = os.path.join(
        args.project_dir, "test_scripts", "uart_test", "test_aws_connectivity.py")
    cmd = [
        sys.executable, test_script,
        "--device-id", args.device_id,
        "--timeout", args.timeout,
    ]
    if cmd_port:
        cmd += ["--cmd-port", cmd_port]
    if log_port:
        cmd += ["--log-port", log_port]

    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
