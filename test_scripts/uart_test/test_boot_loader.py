#!/usr/bin/env python3
"""
UART Boot Loader Test Script
RX72N Envision Kit boot_loader の起動確認テスト

boot_loader は起動時に UART (SCI2, 115200bps) へ以下を出力する:
  -------------------------------------------------
  RX72N secure boot program
  -------------------------------------------------

このスクリプトは "RX72N secure boot program" の受信を確認する。

環境変数:
  UART_PORT        : シリアルポート (デフォルト: COM6)
  UART_BAUD_RATE   : ボーレート     (デフォルト: 115200)
  UART_TIMEOUT_SEC : 受信タイムアウト秒数 (デフォルト: 10)
"""

import os
import sys
import time

import serial

UART_PORT = os.environ.get("UART_PORT", "COM6")
UART_BAUD_RATE = int(os.environ.get("UART_BAUD_RATE", "115200"))
UART_TIMEOUT_SEC = int(os.environ.get("UART_TIMEOUT_SEC", "10"))
EXPECTED_STRING = "RX72N secure boot program"
MAX_LINES = 20


def main():
    print("=" * 60)
    print("[INFO] UART Boot Loader Test")
    print(f"[INFO]   Port    : {UART_PORT}")
    print(f"[INFO]   Baud    : {UART_BAUD_RATE}")
    print(f"[INFO]   Timeout : {UART_TIMEOUT_SEC}s")
    print(f"[INFO]   Expect  : '{EXPECTED_STRING}'")
    print("=" * 60)

    try:
        with serial.Serial(UART_PORT, UART_BAUD_RATE, timeout=UART_TIMEOUT_SEC) as ser:
            print(f"[INFO] Opened port: {UART_PORT}")
            # flash 直後のリセットで出力されるデータをフラッシュ
            ser.reset_input_buffer()
            print(f"[INFO] Waiting for boot_loader output... (max {MAX_LINES} lines)")

            for line_num in range(1, MAX_LINES + 1):
                raw = ser.readline()

                if not raw:
                    print(f"[WARN] Line {line_num}: no data received within {UART_TIMEOUT_SEC}s")
                    break

                decoded = raw.decode("utf-8", errors="replace").strip()
                print(f"[RECV] {line_num}: '{decoded}'")

                if EXPECTED_STRING in decoded:
                    print("-" * 60)
                    print(f"[PASS] '{EXPECTED_STRING}' received successfully")
                    print("-" * 60)
                    sys.exit(0)

            print("-" * 60)
            print(f"[FAIL] '{EXPECTED_STRING}' not found in {MAX_LINES} lines")
            print("-" * 60)
            sys.exit(1)

    except serial.SerialException as e:
        print(f"[ERROR] Serial port error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
