#!/usr/bin/env python3
"""confirm_aws_mqtt: Test AWS IoT Core MQTT connectivity.

Cross-platform (Windows / Linux) replacement for the inline bash script
that previously ran in the confirm_aws_mqtt CI job.
"""

import argparse
import os
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--device-id", default=os.environ.get("DEVICE_ID", "rx72n-01"))
    p.add_argument("--timeout", default="120")
    p.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = p.parse_args()

    print("=== AWS IoT Core MQTT Connectivity Test ===", flush=True)
    print(f"  Device ID: {args.device_id}")

    test_script = os.path.join(
        args.project_dir, "test_scripts", "uart_test", "test_aws_connectivity.py")
    cmd = [
        sys.executable, test_script,
        "--device-id", args.device_id,
        "--timeout", args.timeout,
    ]
    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
