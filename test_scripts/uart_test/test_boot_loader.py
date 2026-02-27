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
  UART_TIMEOUT_SEC : 全体タイムアウト秒数 (デフォルト: 30)

引数:
  --flash-cmd CMD  : flash コマンド（rfp-cli 呼び出し）
                     省略時は flash をスキップし UART 読み取りのみ
"""

import argparse
import os
import subprocess
import sys
import threading
import time

import serial

UART_PORT = os.environ.get("UART_PORT", "COM6")
UART_BAUD_RATE = int(os.environ.get("UART_BAUD_RATE", "115200"))
UART_TIMEOUT_SEC = int(os.environ.get("UART_TIMEOUT_SEC", "30"))
EXPECTED_STRING = "RX72N secure boot program"
POLL_INTERVAL = 1  # readline timeout per poll (seconds)


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
    print(f"[INFO]   Port         : {UART_PORT}")
    print(f"[INFO]   Baud         : {UART_BAUD_RATE}")
    print(f"[INFO]   Total timeout: {UART_TIMEOUT_SEC}s")
    print(f"[INFO]   Poll interval: {POLL_INTERVAL}s")
    print(f"[INFO]   Expect       : '{EXPECTED_STRING}'")
    print(f"[INFO]   Flash        : {'yes' if args.flash_cmd else 'skip'}")
    print("=" * 60)

    flash_returncode = [0]
    flash_done = threading.Event()

    def flash_worker():
        try:
            flash_returncode[0] = run_flash(args.flash_cmd)
        finally:
            flash_done.set()

    try:
        # 短い polling interval で頻繁にチェック
        with serial.Serial(UART_PORT, UART_BAUD_RATE, timeout=POLL_INTERVAL) as ser:
            print(f"[INFO] Opened port: {UART_PORT}")
            ser.reset_input_buffer()

            if args.flash_cmd:
                flash_thread = threading.Thread(target=flash_worker)
                flash_thread.start()
                print("[INFO] Flash started in background, reading UART...")
            else:
                flash_done.set()
                print("[INFO] No flash command, reading UART immediately...")

            start_time = time.time()
            line_count = 0
            received_bytes = b""

            while (time.time() - start_time) < UART_TIMEOUT_SEC:
                elapsed = time.time() - start_time
                # バイト単位で読み取り（readline がタイムアウトで空を返す問題の回避）
                chunk = ser.read(ser.in_waiting or 1)

                if chunk:
                    received_bytes += chunk
                    # 改行で分割して処理
                    while b"\n" in received_bytes:
                        line_raw, received_bytes = received_bytes.split(b"\n", 1)
                        decoded = line_raw.decode("utf-8", errors="replace").strip()
                        if decoded:
                            line_count += 1
                            print(f"[RECV] {line_count}: '{decoded}' (t={elapsed:.1f}s)")

                            if EXPECTED_STRING in decoded:
                                print("-" * 60)
                                print(f"[PASS] '{EXPECTED_STRING}' received at t={elapsed:.1f}s")
                                print("-" * 60)
                                if args.flash_cmd:
                                    flash_thread.join(timeout=60)
                                sys.exit(0)
                else:
                    # データなし — 状況を報告（5秒ごと）
                    if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                        status = "flash running" if not flash_done.is_set() else "flash done, waiting for MCU"
                        if int(elapsed * 10) % 50 == 0:
                            print(f"[INFO] t={elapsed:.0f}s: {status}, in_waiting={ser.in_waiting}")

            # 残りのバッファもチェック
            if received_bytes:
                decoded = received_bytes.decode("utf-8", errors="replace").strip()
                if decoded:
                    line_count += 1
                    print(f"[RECV] {line_count}: '{decoded}' (final)")
                    if EXPECTED_STRING in decoded:
                        print("-" * 60)
                        print(f"[PASS] '{EXPECTED_STRING}' received (final buffer)")
                        print("-" * 60)
                        if args.flash_cmd:
                            flash_thread.join(timeout=60)
                        sys.exit(0)

            # タイムアウト
            if args.flash_cmd:
                flash_thread.join(timeout=60)
                if flash_returncode[0] != 0:
                    print(f"[ERROR] Flash command failed with exit code {flash_returncode[0]}")
                    sys.exit(1)

            print("-" * 60)
            print(f"[FAIL] '{EXPECTED_STRING}' not found within {UART_TIMEOUT_SEC}s")
            print(f"[FAIL] Total lines received: {line_count}")
            print(f"[FAIL] Flash done: {flash_done.is_set()}")
            print("-" * 60)
            sys.exit(1)

    except serial.SerialException as e:
        print(f"[ERROR] Serial port error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
