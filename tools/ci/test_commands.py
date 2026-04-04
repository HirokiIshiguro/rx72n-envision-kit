#!/usr/bin/env python3
"""Run aws_demos UART command-response tests."""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runner-handle"))
from runner_handle.serial_port import resolve_port


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command-port", default=os.environ.get("COMMAND_PORT"))
    parser.add_argument("--command-baud", default=os.environ.get("COMMAND_BAUD_RATE", "115200"))
    parser.add_argument("--command-timeout", default=os.environ.get("COMMAND_TIMEOUT", "10"))
    parser.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = parser.parse_args()

    command_port = resolve_port(args.command_port)
    test_script = os.path.join(args.project_dir, "test_scripts", "uart_test", "test_aws_demos_commands.py")
    cmd = [
        sys.executable,
        test_script,
        "--port",
        command_port,
        "--baud",
        str(args.command_baud),
        "--timeout",
        str(args.command_timeout),
        "--prompt-timeout",
        "60",
        "--initial-wait",
        "3",
        "--skip-erase",
    ]
    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
