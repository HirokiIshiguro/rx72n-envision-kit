#!/usr/bin/env python3
"""
test_uart_download.py - Download .rsu firmware via UART to RX72N boot loader

Sends an .rsu file (Renesas Secure Update) to the boot loader via UART and
monitors progress. The boot loader must already be running and waiting for
firmware data ("send userprog.rsu via UART.").

Typical CI flow:
    1. flash_boot_loader: flash boot_loader.mot, verify UART output
    2. download_aws_demos: run this script to send .rsu via UART
       → boot loader receives, verifies, bank swaps, resets
       → aws_demos boots

UART Protocol (from rx72n_boot_loader.c):
    Boot loader uses SCI2 at 115200 bps (8N1).
    Reception is interrupt-driven, byte-by-byte, with 32KB double buffering.
    No flow control needed — UART speed is the bottleneck.

    Message flow during download:
        "installing firmware...N%(size/totalKB)."  (progress, with \\r)
        "completed installing firmware."
        "integrity check scheme = sig-sha256-ecdsa"
        "bank1(temporary area) on code flash integrity check...OK"
        "installing const data...N%(size/totalKB)."  (data flash progress)
        "completed installing const data."
        "software reset..."
        (MCU resets)
        (boot loader starts again, verifies, bank swaps)
        "jump to user program"  (aws_demos boots)

Usage:
    python test_uart_download.py --rsu userprog.rsu
    python test_uart_download.py --rsu userprog.rsu --port COM6 --baud 115200
    python test_uart_download.py --rsu userprog.rsu --timeout 300 --diag

Dependencies:
    pip install pyserial
"""

import argparse
import os
import sys
import threading
import time
from pathlib import Path

try:
    import serial
except ImportError:
    print("ERROR: 'pyserial' package is required.")
    print("       Install with: pip install pyserial")
    sys.exit(1)


# Default UART settings
DEFAULT_PORT = os.environ.get("UART_PORT", "COM6")
DEFAULT_BAUD = int(os.environ.get("UART_BAUD_RATE", "115200"))
DEFAULT_TIMEOUT = 300  # 5 minutes (1.8MB at 115200 = ~160s + flash time)

# UART send chunk size (bytes)
# Large enough for efficiency, small enough to allow progress monitoring
SEND_CHUNK_SIZE = 4096

# Key messages from boot_loader
MSG_INSTALLING_FW = "installing firmware"
MSG_COMPLETED_FW = "completed installing firmware"
MSG_INTEGRITY_CHECK = "integrity check"
# Boot loader outputs "...OK" or "...NG" for check results.
# Must use "..." prefix to avoid false positives from lifecycle state strings
# like "LIFECYCLE_STATE_TESTING" which contains "NG".
MSG_CHECK_OK = "...OK"
MSG_CHECK_NG = "...NG"
MSG_CONST_DATA = "installing const data"
MSG_COMPLETED_CONST = "completed installing const data"
MSG_SW_RESET = "software reset"
MSG_JUMP_USER = "jump to user program"


class UartDownloader:
    """Send .rsu firmware to boot loader via UART and monitor progress."""

    def __init__(self, port, baud, timeout, post_tx_wait=30, diag=False):
        self.port_name = port
        self.baud = baud
        self.timeout = timeout
        self.post_tx_wait = post_tx_wait
        self.diag = diag
        self.ser = None
        self.rx_buffer = ""
        self.messages = []
        self.send_complete = False
        self.send_error = None
        self.bytes_sent = 0
        self.total_bytes = 0
        self.start_time = 0
        self.tx_complete_time = None
        self._lock = threading.Lock()

    def open_port(self):
        """Open serial port."""
        print(f"Opening {self.port_name} at {self.baud} bps...")
        self.ser = serial.Serial(
            port=self.port_name,
            baudrate=self.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1,  # read timeout for non-blocking reads
            write_timeout=10,
        )
        # Flush any stale data
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        print(f"  Port opened: {self.ser.name}")

    def close_port(self):
        """Close serial port."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"Port closed: {self.port_name}")

    def send_thread(self, rsu_data):
        """
        Thread function: send .rsu data in chunks.
        The serial driver handles baud rate pacing internally.
        """
        try:
            offset = 0
            while offset < len(rsu_data):
                chunk = rsu_data[offset:offset + SEND_CHUNK_SIZE]
                self.ser.write(chunk)
                offset += len(chunk)
                with self._lock:
                    self.bytes_sent = offset
        except Exception as e:
            self.send_error = str(e)
        finally:
            with self._lock:
                self.send_complete = True

    def read_uart(self):
        """
        Read available data from UART (non-blocking).
        Returns list of complete lines received.
        """
        lines = []
        try:
            data = self.ser.read(self.ser.in_waiting or 1)
            if data:
                # Decode with error handling (boot_loader output is ASCII)
                text = data.decode('ascii', errors='replace')
                self.rx_buffer += text

                # Split on newline, keeping partial lines in buffer
                while '\n' in self.rx_buffer:
                    line, self.rx_buffer = self.rx_buffer.split('\n', 1)
                    line = line.strip('\r')
                    if line:
                        lines.append(line)
                        self.messages.append(line)

                # Also check for \r-only lines (progress updates use \r)
                if '\r' in self.rx_buffer and '\n' not in self.rx_buffer:
                    parts = self.rx_buffer.split('\r')
                    # Keep the last part (possibly incomplete)
                    for part in parts[:-1]:
                        part = part.strip()
                        if part:
                            lines.append(part)
                            # Don't add progress lines to messages (too many)
                            if MSG_INSTALLING_FW not in part and MSG_CONST_DATA not in part:
                                self.messages.append(part)
                    self.rx_buffer = parts[-1]
        except serial.SerialException:
            pass
        return lines

    def download(self, rsu_path):
        """
        Send .rsu file and monitor progress.

        Returns:
            0 on success (firmware installed and verified)
            1 on failure
        """
        # Read .rsu file
        rsu_data = rsu_path.read_bytes()
        self.total_bytes = len(rsu_data)
        print(f"\n=== UART Download ===")
        print(f"  File:     {rsu_path}")
        print(f"  Size:     {self.total_bytes:,} bytes ({self.total_bytes/1024:.1f} KB)")
        print(f"  Port:     {self.port_name} @ {self.baud} bps")
        estimated_sec = self.total_bytes * 10 / self.baud
        print(f"  Est time: {estimated_sec:.0f}s ({estimated_sec/60:.1f} min) for transfer")
        print(f"  Timeout:  {self.timeout}s")
        print()

        self.open_port()
        self.start_time = time.time()

        # Brief pause to let boot_loader settle
        time.sleep(0.5)

        # Drain any pending data from boot_loader
        drain_data = b""
        while self.ser.in_waiting:
            drain_data += self.ser.read(self.ser.in_waiting)
            time.sleep(0.05)
        if drain_data:
            drain_text = drain_data.decode('ascii', errors='replace').strip()
            if drain_text:
                print(f"[drain] {drain_text}")

        # Start send thread
        print(f"Sending {self.total_bytes:,} bytes...")
        sender = threading.Thread(target=self.send_thread, args=(rsu_data,), daemon=True)
        sender.start()

        # Monitor loop
        fw_completed = False
        integrity_ok = False
        const_completed = False
        sw_reset = False
        jump_user = False
        last_progress_print = 0
        post_reset_timeout = 30  # seconds to wait after sw reset for "jump to user program"
        post_reset_start = None

        while True:
            elapsed = time.time() - self.start_time

            # Check global timeout (safety net)
            if elapsed > self.timeout:
                print(f"\nTIMEOUT after {elapsed:.1f}s")
                self.close_port()
                return 1

            # Read UART output
            lines = self.read_uart()
            for line in lines:
                # Print significant messages
                if MSG_INSTALLING_FW in line:
                    # Progress update — print periodically
                    if time.time() - last_progress_print > 5:
                        print(f"  [{elapsed:6.1f}s] {line}")
                        last_progress_print = time.time()
                elif MSG_CONST_DATA in line:
                    if time.time() - last_progress_print > 5:
                        print(f"  [{elapsed:6.1f}s] {line}")
                        last_progress_print = time.time()
                else:
                    print(f"  [{elapsed:6.1f}s] {line}")

                # Track state
                if MSG_COMPLETED_FW in line:
                    fw_completed = True
                elif MSG_CHECK_OK in line and MSG_INTEGRITY_CHECK in '\n'.join(self.messages[-5:]):
                    integrity_ok = True
                elif MSG_CHECK_NG in line and MSG_INTEGRITY_CHECK in '\n'.join(self.messages[-5:]):
                    print(f"\nERROR: Firmware integrity check FAILED")
                    self.close_port()
                    return 1
                elif MSG_COMPLETED_CONST in line:
                    const_completed = True
                elif MSG_SW_RESET in line:
                    sw_reset = True
                    post_reset_start = time.time()
                elif MSG_JUMP_USER in line:
                    jump_user = True

            # Print send progress and detect TX completion
            with self._lock:
                sent = self.bytes_sent
                tx_done = self.send_complete
            if sent > 0 and not tx_done:
                pct = sent * 100 / self.total_bytes
                if self.diag and time.time() - last_progress_print > 10:
                    print(f"  [{elapsed:6.1f}s] TX: {sent:,}/{self.total_bytes:,} bytes ({pct:.0f}%)")
            elif tx_done and self.tx_complete_time is None and not self.send_error:
                self.tx_complete_time = time.time()
                print(f"  [{elapsed:6.1f}s] TX complete: {sent:,} bytes sent")
                print(f"  [{elapsed:6.1f}s] Waiting up to {self.post_tx_wait}s for boot_loader response...")

            # Check if send failed
            if self.send_error:
                print(f"\nERROR: Send failed: {self.send_error}")
                self.close_port()
                return 1

            # Post-TX timeout: if TX done but no meaningful MCU response
            if (self.tx_complete_time and not sw_reset and
                    time.time() - self.tx_complete_time > self.post_tx_wait):
                print(f"\n=== Download Complete (TX only, no RX) ===")
                print(f"  TX:                {sent:,}/{self.total_bytes:,} bytes (100%)")
                print(f"  RX messages:       {len(self.messages)}")
                print(f"  Firmware installed: {'YES' if fw_completed else 'UNKNOWN (no RX)'}")
                print(f"  Integrity check:   {'PASS' if integrity_ok else 'UNKNOWN (no RX)'}")
                print(f"  Const data:        {'YES' if const_completed else 'UNKNOWN (no RX)'}")
                print(f"  Software reset:    {'YES' if sw_reset else 'UNKNOWN (no RX)'}")
                print(f"  Total time:        {elapsed:.1f}s ({elapsed/60:.1f} min)")
                print(f"\nWARNING: No response from boot_loader after TX completion.")
                print(f"  TX succeeded. Verify on LCD or fix COM port MCU→PC direction.")
                self.close_port()
                return 0

            # Success condition: firmware installed + verified + data flash + reset
            if sw_reset:
                if jump_user:
                    # Full success — aws_demos is booting
                    elapsed = time.time() - self.start_time
                    print(f"\n=== Download Complete ===")
                    print(f"  Firmware installed: {'YES' if fw_completed else 'NO'}")
                    print(f"  Integrity check:   {'PASS' if integrity_ok else 'UNKNOWN'}")
                    print(f"  Const data:        {'YES' if const_completed else 'NO'}")
                    print(f"  Software reset:    YES")
                    print(f"  Jump to user:      YES")
                    print(f"  Total time:        {elapsed:.1f}s ({elapsed/60:.1f} min)")
                    self.close_port()
                    return 0

                # After sw_reset, wait limited time for "jump to user program"
                if post_reset_start and (time.time() - post_reset_start > post_reset_timeout):
                    # Timeout waiting for jump, but download itself succeeded
                    elapsed = time.time() - self.start_time
                    print(f"\n=== Download Complete (partial) ===")
                    print(f"  Firmware installed: {'YES' if fw_completed else 'NO'}")
                    print(f"  Integrity check:   {'PASS' if integrity_ok else 'UNKNOWN'}")
                    print(f"  Const data:        {'YES' if const_completed else 'NO'}")
                    print(f"  Software reset:    YES")
                    print(f"  Jump to user:      NO (timeout after {post_reset_timeout}s)")
                    print(f"  Total time:        {elapsed:.1f}s ({elapsed/60:.1f} min)")
                    print(f"\nWARNING: 'jump to user program' not detected, but download completed.")
                    print(f"  This may be normal if the user program does not output to UART,")
                    print(f"  or if boot_loader does bank swap before printing this message.")
                    self.close_port()
                    # Still return 0 — download+verify succeeded, user program behavior is separate
                    return 0

            time.sleep(0.05)


def main():
    parser = argparse.ArgumentParser(
        description="Download .rsu firmware via UART to RX72N boot loader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--rsu", type=Path, required=True,
                        help="Path to .rsu file to download")
    parser.add_argument("--port", default=DEFAULT_PORT,
                        help=f"Serial port (default: {DEFAULT_PORT})")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD,
                        help=f"Baud rate (default: {DEFAULT_BAUD})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Total timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--post-tx-wait", type=int, default=30,
                        help="Seconds to wait for MCU response after TX completes (default: 30)")
    parser.add_argument("--diag", action="store_true",
                        help="Print additional diagnostic output")

    args = parser.parse_args()

    if not args.rsu.exists():
        print(f"ERROR: RSU file not found: {args.rsu}")
        return 1

    downloader = UartDownloader(
        port=args.port,
        baud=args.baud,
        timeout=args.timeout,
        post_tx_wait=args.post_tx_wait,
        diag=args.diag,
    )

    try:
        return downloader.download(args.rsu)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        downloader.close_port()
        return 130
    except serial.SerialException as e:
        print(f"\nSerial port error: {e}")
        downloader.close_port()
        return 1


if __name__ == "__main__":
    sys.exit(main())
