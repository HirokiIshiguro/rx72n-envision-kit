#!/usr/bin/env python3
"""
UART Boot Loader Flash + Test Script
RX72N Envision Kit boot_loader の書き込み＋起動確認テスト

boot_loader は起動時に一度だけ UART (SCI2, 115200bps) へ以下を出力する:
  -------------------------------------------------
  RX72N secure boot program
  -------------------------------------------------

このスクリプトは:
1. UART ポートを先に開く
2. rfp-cli で boot_loader を書き込み＋実行
3. UART から "RX72N secure boot program" の受信を確認

環境変数:
  UART_PORT        : シリアルポート (デフォルト: COM6)
  UART_BAUD_RATE   : ボーレート     (デフォルト: 115200)
  UART_TIMEOUT_SEC : 受信タイムアウト秒数 (デフォルト: 10)

引数:
  --flash-cmd CMD  : flash コマンド（rfp-cli 呼び出し）
                     省略時は flash をスキップし UART 読み取りのみ
"""

import argparse
import os
import subprocess
import sys
import threading

import serial

UART_PORT = os.environ.get("UART_PORT", "COM6")
UART_BAUD_RATE = int(os.environ.get("UART_BAUD_RATE", "115200"))
UART_TIMEOUT_SEC = int(os.environ.get("UART_TIMEOUT_SEC", "10"))
EXPECTED_STRING = "RX72N secure boot program"
MAX_LINES = 30


def run_flash(cmd):
    """Flash コマンドを実行（別スレッドで呼ばれる）"""
    print(f"[FLASH] Executing: {cmd}")
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True, text=True, timeout=120
    )
    print(f"[FLASH] Exit code: {result.returncode}")
    if result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            print(f"[FLASH] {line}")
    if result.returncode != 0 and result.stderr.strip():
        for line in result.stderr.strip().split("\n"):
            print(f"[FLASH:ERR] {line}")
    return result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--flash-cmd", help="Flash command (rfp-cli)")
    args = parser.parse_args()

    print("=" * 60)
    print("[INFO] UART Boot Loader Flash + Test")
    print(f"[INFO]   Port    : {UART_PORT}")
    print(f"[INFO]   Baud    : {UART_BAUD_RATE}")
    print(f"[INFO]   Timeout : {UART_TIMEOUT_SEC}s")
    print(f"[INFO]   Expect  : '{EXPECTED_STRING}'")
    print(f"[INFO]   Flash   : {'yes' if args.flash_cmd else 'skip'}")
    print("=" * 60)

    flash_returncode = [0]

    try:
        with serial.Serial(UART_PORT, UART_BAUD_RATE, timeout=UART_TIMEOUT_SEC) as ser:
            print(f"[INFO] Opened port: {UART_PORT}")
            ser.reset_input_buffer()

            if args.flash_cmd:
                # UART ポートを開いた状態で flash を実行（別スレッド）
                # flash 完了後に MCU がリセットされ起動メッセージが出る
                flash_thread = threading.Thread(
                    target=lambda: flash_returncode.__setitem__(0, run_flash(args.flash_cmd))
                )
                flash_thread.start()
                print("[INFO] Flash started in background, reading UART...")
            else:
                print("[INFO] No flash command, reading UART immediately...")

            for line_num in range(1, MAX_LINES + 1):
                raw = ser.readline()

                if not raw:
                    # Flash がまだ実行中なら読み取りを続ける
                    # （flash に ~15秒かかるため readline タイムアウトが先に来る）
                    if args.flash_cmd and flash_thread.is_alive():
                        print(f"[INFO] Line {line_num}: waiting for flash to complete...")
                        continue
                    print(f"[WARN] Line {line_num}: no data received within {UART_TIMEOUT_SEC}s")
                    break

                decoded = raw.decode("utf-8", errors="replace").strip()
                if decoded:
                    print(f"[RECV] {line_num}: '{decoded}'")

                if EXPECTED_STRING in decoded:
                    print("-" * 60)
                    print(f"[PASS] '{EXPECTED_STRING}' received successfully")
                    print("-" * 60)
                    if args.flash_cmd:
                        flash_thread.join(timeout=60)
                    sys.exit(0)

            # タイムアウトまたは MAX_LINES に達した
            if args.flash_cmd:
                flash_thread.join(timeout=60)
                if flash_returncode[0] != 0:
                    print(f"[ERROR] Flash command failed with exit code {flash_returncode[0]}")
                    sys.exit(1)

            print("-" * 60)
            print(f"[FAIL] '{EXPECTED_STRING}' not found")
            print("-" * 60)
            sys.exit(1)

    except serial.SerialException as e:
        print(f"[ERROR] Serial port error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
