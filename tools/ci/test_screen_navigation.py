#!/usr/bin/env python3
"""Run screen navigation tests via UART touch commands."""

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
    parser.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = parser.parse_args()

    command_port = resolve_port(args.command_port)
    test_script = os.path.join(args.project_dir, "test_scripts", "uart_test", "test_touch_navigation.py")
    cmd = [
        sys.executable,
        test_script,
        "--cmd-port",
        command_port,
        "--cmd-baud",
        str(args.command_baud),
        "--timeout",
        "30",
        "--prompt-timeout",
        "30",
        "--initial-wait",
        "1",
    ]
    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
