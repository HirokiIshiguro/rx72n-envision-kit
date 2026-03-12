#!/usr/bin/env python3
"""Primitive serial health checks for RX72N device bring-up."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import serial
import serial.tools.list_ports


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from test_aws_demos_commands import CommandTester  # noqa: E402


DEFAULT_UART_PORT = os.environ.get("UART_PORT", "COM7")
DEFAULT_UART_BAUD = int(os.environ.get("UART_BAUD_RATE", "921600"))
DEFAULT_COMMAND_PORT = os.environ.get("COMMAND_PORT", "COM6")
DEFAULT_COMMAND_BAUD = int(os.environ.get("COMMAND_BAUD_RATE", "115200"))


def list_ports() -> None:
    print("[INFO] Available serial ports:")
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("[INFO]   (none)")
        return
    for port in sorted(ports, key=lambda item: item.device):
        print(f"[INFO]   {port.device}: {port.description}")


def run_boot_banner(args: argparse.Namespace) -> int:
    expected_tokens = args.expect or ["RX72N secure boot program"]

    print("=" * 60)
    print("[INFO] Boot Loader Health Check")
    print(f"[INFO]   Port      : {args.port}")
    print(f"[INFO]   Baud      : {args.baud}")
    print(f"[INFO]   Timeout   : {args.timeout}s")
    print(f"[INFO]   Expect    : {expected_tokens}")
    print("=" * 60)

    list_ports()

    end_time = time.monotonic() + args.timeout
    received = bytearray()

    try:
        with serial.Serial(args.port, args.baud, timeout=0) as ser:
            print(f"[INFO] Opened {args.port}")
            if args.reset_input_buffer:
                ser.reset_input_buffer()
                print("[INFO] Cleared input buffer")

            while time.monotonic() < end_time:
                waiting = ser.in_waiting
                if waiting:
                    chunk = ser.read(waiting)
                    received.extend(chunk)
                    decoded = received.decode("utf-8", errors="replace")
                    text = chunk.decode("utf-8", errors="replace")
                    for line in text.replace("\r", "\n").split("\n"):
                        line = line.strip()
                        if line:
                            print(f"[RECV] {line}")
                    for token in expected_tokens:
                        if token in decoded:
                            print(f"[PASS] Found expected boot_loader output: {token}")
                            return 0
                else:
                    time.sleep(0.05)
    except serial.SerialException as exc:
        print(f"[ERROR] Serial error: {exc}")
        return 1

    print(f"[FAIL] Expected banner not observed within {args.timeout}s")
    if received:
        print("[INFO] Final captured text:")
        print(received.decode("utf-8", errors="replace"))
    return 1


def run_command_prompt(args: argparse.Namespace) -> int:
    print("=" * 60)
    print("[INFO] aws_demos Prompt Health Check")
    print(f"[INFO]   Port           : {args.port}")
    print(f"[INFO]   Baud           : {args.baud}")
    print(f"[INFO]   Prompt timeout : {args.prompt_timeout}s")
    print(f"[INFO]   Probe command  : {args.probe_command}")
    print("=" * 60)

    list_ports()

    tester = CommandTester(args.port, args.baud, args.command_timeout, retries=args.retries)

    try:
        tester.open()
        print(f"[INFO] Waiting {args.initial_wait}s before prompt polling...")
        time.sleep(args.initial_wait)

        if not tester.wait_for_prompt(timeout=args.prompt_timeout):
            print("[FAIL] Prompt not detected")
            return 1

        raw = tester.send_command_with_retry(args.probe_command)
        if raw is None:
            print(f"[FAIL] No response for probe command: {args.probe_command}")
            return 1

        body = tester.extract_response_body(raw, args.probe_command)
        print(f"[INFO] Probe response: {repr(body[:200])}")

        if args.probe_expect and args.probe_expect not in body:
            print(f"[FAIL] Probe response does not contain expected text: {args.probe_expect}")
            return 1

        if not body.strip():
            print("[FAIL] Probe response body is empty")
            return 1

        print("[PASS] Prompt and probe command response are healthy")
        return 0
    except serial.SerialException as exc:
        print(f"[ERROR] Serial error: {exc}")
        return 1
    finally:
        tester.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Primitive serial health checks for RX72N device.")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    banner = subparsers.add_parser("boot-banner", help="Check boot_loader UART banner")
    banner.add_argument("--port", default=DEFAULT_UART_PORT)
    banner.add_argument("--baud", type=int, default=DEFAULT_UART_BAUD)
    banner.add_argument("--timeout", type=int, default=20)
    banner.add_argument("--expect", action="append")
    banner.add_argument("--reset-input-buffer", action="store_true")

    prompt = subparsers.add_parser("command-prompt", help="Check aws_demos command prompt")
    prompt.add_argument("--port", default=DEFAULT_COMMAND_PORT)
    prompt.add_argument("--baud", type=int, default=DEFAULT_COMMAND_BAUD)
    prompt.add_argument("--initial-wait", type=float, default=3.0)
    prompt.add_argument("--prompt-timeout", type=int, default=60)
    prompt.add_argument("--command-timeout", type=int, default=10)
    prompt.add_argument("--retries", type=int, default=3)
    prompt.add_argument("--probe-command", default="version")
    prompt.add_argument("--probe-expect", default="v")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.mode == "boot-banner":
        return run_boot_banner(args)
    if args.mode == "command-prompt":
        return run_command_prompt(args)
    print(f"[ERROR] Unsupported mode: {args.mode}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
