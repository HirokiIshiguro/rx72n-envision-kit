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

    # Skip the rfp-cli reset here: the preceding test_commands job (enforced via
    # needs:) already reset the MCU and left aws_demos idle at the `$ ` prompt
    # on SCI2/CN8. A second rfp-cli `-sig -run` within a few minutes is a known
    # intermittent trigger for the CN8 "MCU→PC 間欠受信障害" silent-state
    # documented in CLAUDE.md — pipeline #2901 observed prompt at 0.1s for
    # test_commands' reset but no prompt for 30s on the second reset in
    # test_screen_navigation. test_commands runs in default mode (no
    # --include-extended-probes) so it never touches the screen; Screen 00 /
    # VAR_01=0 is still intact when this job starts, no reset required.
    # (Codex c020598b dropped it on the same reasoning; f6dbae1a restored it
    # as a side-effect of a broader UART-path restore commit, not on its own
    # merit.)
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
