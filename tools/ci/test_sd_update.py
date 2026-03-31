#!/usr/bin/env python3
"""test_sd_update: Test SD card firmware update.

Cross-platform (Windows / Linux) replacement for the inline bash script
that previously ran in the test_sd_update CI job.
"""

import argparse
import os
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--device-id", default=os.environ.get("DEVICE_ID", "rx72n-01"))
    p.add_argument("--rsu", required=True, help="Path to .rsu file")
    p.add_argument("--timeout", default="300")
    p.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    args = p.parse_args()

    print("=== SD Card Firmware Update Test ===", flush=True)
    print(f"  Device ID: {args.device_id}")
    print(f"  RSU file:  {args.rsu}")

    test_script = os.path.join(
        args.project_dir, "test_scripts", "uart_test", "test_sd_update.py")
    cmd = [
        sys.executable, test_script,
        "--device-id", args.device_id,
        "--rsu", args.rsu,
        "--timeout", args.timeout,
    ]
    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
