#!/usr/bin/env python3
"""Run aws_demos startup health checks."""

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
    parser.add_argument("--health-log", default=None)
    args = parser.parse_args()

    health_log = args.health_log or os.path.join(args.project_dir, "aws_demos_health.log")
    command_port = resolve_port(args.command_port)
    health_script = os.path.join(args.project_dir, "test_scripts", "uart_test", "check_device_health.py")
    cmd = [
        sys.executable,
        health_script,
        "command-prompt",
        "--port",
        command_port,
        "--baud",
        str(args.command_baud),
        "--initial-wait",
        "3",
        "--prompt-timeout",
        "60",
        "--command-timeout",
        "10",
        "--probe-command",
        "version",
        "--probe-expect",
        "v",
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
