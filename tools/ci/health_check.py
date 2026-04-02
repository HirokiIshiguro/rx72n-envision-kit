#!/usr/bin/env python3
"""health_check: Run aws_demos startup health check.

Cross-platform (Windows / Linux) replacement for the inline bash script
that previously ran in the health_aws_demos_startup CI job.
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_serial_port import resolve_port


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--command-port", default=os.environ.get("COMMAND_PORT"))
    p.add_argument("--command-baud", default=os.environ.get("COMMAND_BAUD_RATE", "115200"))
    p.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    p.add_argument("--health-log", default=None,
                    help="Path to health log output")
    args = p.parse_args()

    health_log = args.health_log or os.path.join(args.project_dir, "aws_demos_health.log")

    print("=== aws_demos Startup Health Check ===", flush=True)

    command_port = resolve_port(args.command_port)
    health_script = os.path.join(
        args.project_dir, "test_scripts", "uart_test", "check_device_health.py")
    cmd = [
        sys.executable, health_script,
        "command-prompt",
        "--port", command_port,
        "--baud", args.command_baud,
        "--initial-wait", "3",
        "--prompt-timeout", "60",
        "--command-timeout", "10",
        "--probe-command", "version",
        "--probe-expect", "v",
    ]
    print(f"  > {' '.join(cmd)}", flush=True)

    with open(health_log, "w") as f:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            sys.stdout.write(line)
            f.write(line)
        proc.wait()

    if proc.returncode != 0:
        sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
