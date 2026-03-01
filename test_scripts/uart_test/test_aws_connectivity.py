#!/usr/bin/env python3
"""
AWS IoT Core Connectivity Test for aws_demos
RX72N Envision Kit の aws_demos が AWS IoT Core に接続できることを検証する

aws_demos は起動後に自動的に AWS IoT Core への MQTT 接続を試行する。
FreeRTOS ログは COM7 (SCI7, 921600bps) に出力される。
本スクリプトは COM7 のログを監視し、MQTT 接続成功を検出する。

検出パターン（aws_demos の FreeRTOS ログに含まれるメッセージ）:
  - TLS 接続関連のメッセージ
  - MQTT CONNECT / CONNACK
  - "Connected to" 等の接続成功メッセージ

注意:
  - AWS 認証情報がデータフラッシュにプロビジョニング済みであること
  - ネットワーク接続（Ethernet）が利用可能であること
  - DNS 解決ができること

環境変数:
  UART_PORT      : FreeRTOS ログ用ポート (デフォルト: COM7)
  UART_BAUD_RATE : ボーレート (デフォルト: 921600)
"""

import argparse
import os
import sys
import time

import serial

DEFAULT_PORT = os.environ.get("UART_PORT", "COM7")
DEFAULT_BAUD = int(os.environ.get("UART_BAUD_RATE", "921600"))
DEFAULT_TIMEOUT = 60

# 接続成功を示すパターン（大文字小文字区別なし）
SUCCESS_PATTERNS = [
    "mqtt connect",
    "connack",
    "connected to",
    "mqtt agent connected",
    "tls connection established",
    "mqtt_agent_connect",
]

# 接続失敗を示すパターン
FAILURE_PATTERNS = [
    "tls handshake failed",
    "connection refused",
    "dns resolution failed",
    "network down",
    "socket error",
    "mqtt connection failed",
]


def main():
    parser = argparse.ArgumentParser(
        description="Test AWS IoT Core connectivity via FreeRTOS log"
    )
    parser.add_argument("--port", default=DEFAULT_PORT,
                        help=f"FreeRTOS log port (default: {DEFAULT_PORT})")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD,
                        help=f"Baud rate (default: {DEFAULT_BAUD})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--reset-cmd",
                        help="Command to reset MCU before test (e.g., rfp-cli run)")
    args = parser.parse_args()

    print("=" * 60)
    print("[INFO] AWS IoT Core Connectivity Test")
    print(f"[INFO]   Port    : {args.port} @ {args.baud}bps")
    print(f"[INFO]   Timeout : {args.timeout}s")
    print("=" * 60)

    # MCU リセット（オプション）
    if args.reset_cmd:
        import subprocess
        print(f"[INFO] Resetting MCU: {args.reset_cmd}")
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", args.reset_cmd],
            timeout=30
        )
        time.sleep(3)

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0)
        ser.reset_input_buffer()
        print(f"[INFO] Listening on {args.port}...")

        buf = b""
        start = time.time()
        connected = False
        failed = False
        lines_seen = 0

        while (time.time() - start) < args.timeout:
            n = ser.in_waiting
            if n > 0:
                chunk = ser.read(n)
                buf += chunk
                while b"\n" in buf:
                    line_raw, buf = buf.split(b"\n", 1)
                    decoded = line_raw.decode("utf-8", errors="replace").strip()
                    if not decoded:
                        continue
                    lines_seen += 1
                    elapsed = time.time() - start

                    # ログ出力（最初の 50 行と、マッチした行を出力）
                    lower = decoded.lower()
                    is_match = any(p in lower for p in SUCCESS_PATTERNS + FAILURE_PATTERNS)
                    if lines_seen <= 50 or is_match:
                        print(f"[LOG] (t={elapsed:.1f}s) {decoded[:200]}")

                    # 成功パターン検出
                    for pat in SUCCESS_PATTERNS:
                        if pat in lower:
                            print(f"[MATCH] Success pattern: '{pat}'")
                            connected = True

                    # 失敗パターン検出
                    for pat in FAILURE_PATTERNS:
                        if pat in lower:
                            print(f"[MATCH] Failure pattern: '{pat}'")
                            failed = True

                    if connected:
                        break
            else:
                time.sleep(0.05)

            if connected:
                break

        ser.close()

        # 結果判定
        print()
        print("=" * 60)
        elapsed = time.time() - start
        print(f"[INFO] Total lines seen: {lines_seen}, elapsed: {elapsed:.1f}s")

        if connected and not failed:
            print("[PASS] AWS IoT Core connection detected")
            sys.exit(0)
        elif connected and failed:
            print("[WARN] Connection detected but errors also seen")
            sys.exit(0)
        elif failed:
            print("[FAIL] Connection failure detected")
            sys.exit(1)
        else:
            print(f"[FAIL] No connection detected within {args.timeout}s")
            if lines_seen == 0:
                print("[HINT] No log output received. Is aws_demos running?")
                print("[HINT] Are AWS credentials provisioned? (use provision_aws.py)")
            sys.exit(1)

    except serial.SerialException as e:
        print(f"[ERROR] Serial port error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted")
        sys.exit(130)


if __name__ == "__main__":
    main()
