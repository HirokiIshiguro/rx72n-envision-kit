#!/usr/bin/env python3
"""test_screen_navigation: Run screen navigation tests via UART touch commands.

Cross-platform (Windows / Linux) replacement for the inline bash script
that previously ran in the test_screen_navigation CI job.
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runner-handle"))
from runner_handle.serial_port import resolve_port


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--command-port", default=os.environ.get("COMMAND_PORT"))
    p.add_argument("--command-baud", default=os.environ.get("COMMAND_BAUD_RATE", "115200"))
    p.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = p.parse_args()

    command_port = resolve_port(args.command_port)
    print("=== Screen Navigation Test ===", flush=True)
    print(f"  Port: {command_port} @ {args.command_baud}bps")

    test_script = os.path.join(
        args.project_dir, "test_scripts", "uart_test", "test_touch_navigation.py")
    cmd = [
        sys.executable, test_script,
        "--cmd-port", command_port,
        "--cmd-baud", args.command_baud,
        "--timeout", "30",
        "--prompt-timeout", "30",
        "--initial-wait", "1",
    ]
    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
