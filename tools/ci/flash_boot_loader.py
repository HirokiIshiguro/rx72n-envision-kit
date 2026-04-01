#!/usr/bin/env python3
"""flash_boot_loader: Flash boot_loader via rfp-cli and optionally run health check.

Cross-platform (Windows / Linux) replacement for the inline bash script
that previously ran in the flash_boot_loader CI job.
"""

import argparse
import os
import shutil
import subprocess
import sys

# Add tools/ci to path so we can import resolve_serial_port
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_serial_port import resolve_port


def find_rfp_cli(hint: str) -> str:
    """Resolve rfp-cli executable path."""
    found = shutil.which(hint)
    if found:
        return found
    if sys.platform == "win32":
        import glob
        # Search for rfp-cli in standard Renesas install locations
        for pattern in [
            r"C:\Program Files\Renesas Electronics\Programming Tools\Renesas Flash Programmer*\rfp-cli.exe",
            r"C:\Program Files (x86)\Renesas Electronics\Programming Tools\Renesas Flash Programmer*\rfp-cli.exe",
        ]:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
    return hint


def run(cmd, **kwargs):
    """Run a command and exit on failure."""
    print(f"  > {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"ERROR: command exited with {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rfp-cli", default=os.environ.get("RFP_CLI", "rfp-cli"))
    p.add_argument("--rfp-tool", default=os.environ.get("RFP_TOOL", "e2l"))
    p.add_argument("--rfp-speed", default=os.environ.get("RFP_SPEED", "1500K"))
    p.add_argument("--mot", required=True, help="Path to boot_loader .mot")
    p.add_argument("--uart-port", default=os.environ.get("UART_PORT"))
    p.add_argument("--uart-baud", default=os.environ.get("UART_BAUD_RATE", "921600"))
    p.add_argument("--run-healthcheck", default=os.environ.get("RUN_HW_HEALTHCHECK", "false"))
    p.add_argument("--project-dir", default=os.environ.get("CI_PROJECT_DIR", "."))
    p.add_argument("--snapshot-log", default=None)
    p.add_argument("--health-log", default=None)
    args = p.parse_args()

    rfp = find_rfp_cli(args.rfp_cli)

    snapshot_log = args.snapshot_log or os.path.join(args.project_dir, "boot_loader_hardware_state.log")
    health_log = args.health_log or os.path.join(args.project_dir, "boot_loader_health.log")

    # Create empty log files
    open(snapshot_log, "w").close()
    open(health_log, "w").close()

    if not os.path.isfile(args.mot):
        print(f"ERROR: {args.mot} not found", file=sys.stderr)
        sys.exit(1)

    print("=== Flash boot_loader ===", flush=True)
    print(f"  .mot:    {args.mot}")
    print(f"  Device:  RX72x")
    print(f"  Tool:    {args.rfp_tool}")
    print(f"  I/F:     FINE")

    run([rfp, "-device", "RX72x", "-tool", args.rfp_tool,
         "-if", "fine", "-speed", args.rfp_speed,
         "-auth", "id", "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
         "-erase-chip", "-noquery"])

    run([rfp, "-device", "RX72x", "-tool", args.rfp_tool,
         "-if", "fine", "-speed", args.rfp_speed,
         "-auth", "id", "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
         "-p", args.mot, "-v", "-run", "-noquery"])

    print("Flash completed successfully. Boot loader is running.", flush=True)

    if args.run_healthcheck.lower() == "true":
        uart_port = resolve_port(args.uart_port)
        health_script = os.path.join(
            args.project_dir, "test_scripts", "uart_test", "check_device_health.py")
        cmd = [
            sys.executable, health_script,
            "boot-banner",
            "--port", uart_port,
            "--baud", args.uart_baud,
            "--expect", "RX72N secure boot program",
            "--expect", 'send "userprog.rsu" via UART.',
            "--timeout", "20",
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
    else:
        print("  Boot loader health-check skipped (RUN_HW_HEALTHCHECK=false).")


if __name__ == "__main__":
    main()
