#!/usr/bin/env python3
"""Send a single command to a serial port."""

from __future__ import annotations

import argparse
import time

import serial


NEWLINES = {
    "crlf": b"\r\n",
    "lf": b"\n",
    "none": b"",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send one command to a serial port.")
    parser.add_argument("--port", required=True, help="Serial port path")
    parser.add_argument("--baud", type=int, required=True, help="Baud rate")
    parser.add_argument("--command", required=True, help="Command text to send")
    parser.add_argument(
        "--newline",
        choices=sorted(NEWLINES),
        default="crlf",
        help="Line ending to append (default: crlf)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Serial read/write timeout in seconds",
    )
    parser.add_argument(
        "--delay-after",
        type=float,
        default=0.0,
        help="Sleep after sending the command",
    )
    parser.add_argument(
        "--drain",
        type=float,
        default=0.0,
        help="Read and print incoming data for this many seconds after send",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = args.command.encode("utf-8") + NEWLINES[args.newline]

    with serial.Serial(
        port=args.port,
        baudrate=args.baud,
        timeout=args.timeout,
        write_timeout=args.timeout,
    ) as ser:
        ser.reset_input_buffer()
        ser.write(payload)
        ser.flush()

        if args.delay_after > 0:
            time.sleep(args.delay_after)

        if args.drain > 0:
            deadline = time.monotonic() + args.drain
            buffer = bytearray()
            while time.monotonic() < deadline:
                waiting = ser.in_waiting
                if waiting:
                    buffer.extend(ser.read(waiting))
                else:
                    time.sleep(0.05)
            if buffer:
                print(buffer.decode("utf-8", errors="replace"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
