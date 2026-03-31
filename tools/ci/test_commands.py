#!/usr/bin/env python3
"""test_commands: Run UART command-response tests.

Cross-platform (Windows / Linux) replacement for the inline bash script
that previously ran in the test_commands CI job.
"""

import argparse
import os
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--command-port", default=os.environ.get("COMMAND_PORT"))
    p.add_argument("--command-baud", default=os.environ.get("COMMAND_BAUD_RATE", "115200"))
    p.add_argument("--command-timeout", default=os.environ.get("COMMAND_TIMEOUT", "10"))
    p.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = p.parse_args()

    print("=== UART Command-Response Test ===", flush=True)
    print(f"  Port: {args.command_port} @ {args.command_baud}bps")

    test_script = os.path.join(
        args.project_dir, "test_scripts", "uart_test", "test_aws_demos_commands.py")
    cmd = [
        sys.executable, test_script,
        "--port", args.command_port,
        "--baud", args.command_baud,
        "--timeout", args.command_timeout,
        "--prompt-timeout", "60",
        "--initial-wait", "3",
        "--skip-erase",
    ]
    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
