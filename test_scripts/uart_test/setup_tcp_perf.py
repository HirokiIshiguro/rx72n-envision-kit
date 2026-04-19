#!/usr/bin/env python3
"""
TCP perf 用 KVStore (tcpperfip / tcpperfport) を CLI 経由で設定する。

Phase 8b 第3次 段階5-7 B-3 (rx72n-envision-kit#62) で追加。
段階5-7 B-2 (#61 / MR !98) で導入された KVStore キー
KVS_TCP_PERF_SERVER_IP / KVS_TCP_PERF_SERVER_PORT に値を書き込み、
`conf commit` で LittleFS に保存、`reset` で再起動する。

iperf3 サーバ側 (RPi#2 想定) の起動 / 結果取得は本 script の対象外。
本 script は DUT (RPi#3 接続の RX72N) 側の CLI 操作のみ自動化する。

Usage:
  python setup_tcp_perf.py --device-id rx72n-01 \
      --server-ip 192.168.1.100 --server-port 5001

  # 値の読み戻し確認のみ (--verify-only)
  python setup_tcp_perf.py --device-id rx72n-01 --verify-only

依存:
  - pyserial
  - test_scripts/device_config_loader.py (UART_PORT 解決)
  - tools/provisioning/security.py (mask_sensitive_output)

CLI 設計 (v3 baseline):
  Demos/cli/CLIcommands.c の `conf` command が CLICMDKEYS で自動 dispatch。
  - conf set tcpperfip <value>
  - conf set tcpperfport <value>
  - conf commit
  - reset
"""

import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "provisioning"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

from provisioning.security import mask_sensitive_output
from device_config_loader import load_device_config

DEFAULT_PORT = os.environ.get("UART_PORT", "COM7")
DEFAULT_BAUD = int(os.environ.get("UART_BAUD_RATE", "921600"))
DEFAULT_CHAR_DELAY = 0.002
DEFAULT_LINE_DELAY = 0.5
DEFAULT_BOOT_WAIT = 3.0
DEFAULT_CLI_TIMEOUT = 15.0
CLI_READY_MARKERS = ("Going to FreeRTOS-CLI", ">")

IP_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")


def validate_ip(value):
    m = IP_RE.match(value)
    if not m:
        raise argparse.ArgumentTypeError(f"invalid IPv4 address: {value!r}")
    for octet in m.groups():
        if int(octet) > 255:
            raise argparse.ArgumentTypeError(f"IPv4 octet out of range: {value!r}")
    return value


def validate_port(value):
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"port must be integer: {value!r}")
    if not (1 <= port <= 65535):
        raise argparse.ArgumentTypeError(f"port out of range (1-65535): {port}")
    return port


def send_chars(ser, text, char_delay):
    for ch in text:
        ser.write(ch.encode("ascii"))
        time.sleep(char_delay)


def send_command(ser, command, char_delay, line_delay):
    ser.reset_input_buffer()
    send_chars(ser, command, char_delay)
    ser.write(b"\r\n")
    time.sleep(line_delay)
    response = ser.read(ser.in_waiting or 1024).decode("ascii", errors="replace")
    return response


def wait_for_cli_prompt(ser, timeout, reset_after_open):
    """Wait for FreeRTOS-CLI prompt. Optionally trigger reset to catch short-lived window."""
    if reset_after_open:
        print("  Sending CLI wake-up (Enter x2)...")
        ser.write(b"\r\n\r\n")
        time.sleep(0.3)

    deadline = time.monotonic() + timeout
    buffer = ""
    while time.monotonic() < deadline:
        chunk = ser.read(ser.in_waiting or 1).decode("ascii", errors="replace")
        if chunk:
            buffer += chunk
            for marker in CLI_READY_MARKERS:
                if marker in buffer:
                    print(f"  CLI ready marker '{marker}' detected")
                    return True
        else:
            time.sleep(0.1)
    print(f"  ERROR: CLI prompt not detected within {timeout}s")
    print(f"  Last received: {mask_sensitive_output(buffer[-512:]) if buffer else '(empty)'}")
    return False


def cmd_set(ser, key, value, char_delay, line_delay):
    print(f"  conf set {key} {mask_sensitive_output(str(value))}")
    response = send_command(ser, f"conf set {key} {value}", char_delay, line_delay)
    if "Error" in response or "error" in response:
        print(f"  ERROR: set {key} failed: {mask_sensitive_output(response.strip())}")
        return False
    return True


def cmd_get(ser, key, char_delay, line_delay):
    response = send_command(ser, f"conf get {key}", char_delay, line_delay)
    print(f"  conf get {key} -> {mask_sensitive_output(response.strip())}")
    return response


def cmd_commit(ser, char_delay, line_delay):
    print("  conf commit")
    response = send_command(ser, "conf commit", char_delay, line_delay)
    if "Error" in response or "error" in response:
        print(f"  ERROR: commit failed: {mask_sensitive_output(response.strip())}")
        return False
    return True


def cmd_reset(ser, char_delay):
    print("  reset")
    send_chars(ser, "reset", char_delay)
    ser.write(b"\r\n")
    time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device-id", help="device_config.json の device id (例: rx72n-01)")
    parser.add_argument("--port", default=DEFAULT_PORT, help=f"UART port (default: {DEFAULT_PORT})")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"UART baud (default: {DEFAULT_BAUD})")
    parser.add_argument("--server-ip", type=validate_ip, help="iperf3 server IPv4 address")
    parser.add_argument("--server-port", type=validate_port, default=5001, help="iperf3 server port (default: 5001)")
    parser.add_argument("--cli-timeout", type=float, default=DEFAULT_CLI_TIMEOUT, help="CLI prompt 待機 timeout (秒)")
    parser.add_argument("--reset-after-open", action="store_true", help="open 後に CR x2 で CLI window を起こす")
    parser.add_argument("--verify-only", action="store_true", help="読み戻し確認のみ実施 (set/commit/reset しない)")
    parser.add_argument("--no-reset", action="store_true", help="commit 後の reset を抑止")
    args = parser.parse_args()

    if not args.verify_only and args.server_ip is None:
        parser.error("--server-ip は --verify-only でない場合必須")

    port = args.port
    if args.device_id:
        try:
            config = load_device_config(args.device_id)
            port = config.get("log_port", port) or port
            print(f"device_config.json [{args.device_id}] -> UART port {port}")
        except Exception as e:
            print(f"WARNING: device_config.json 読み出し失敗 ({e})、CLI 引数 / env を使用")

    print(f"Opening {port} @ {args.baud}bps...")
    try:
        ser = serial.Serial(port, args.baud, timeout=1)
    except serial.SerialException as e:
        print(f"ERROR: serial open failed: {e}")
        return 1

    try:
        time.sleep(DEFAULT_BOOT_WAIT)
        if not wait_for_cli_prompt(ser, args.cli_timeout, args.reset_after_open):
            return 2

        if args.verify_only:
            print("\n--- Verify (read-only) ---")
            cmd_get(ser, "tcpperfip", DEFAULT_CHAR_DELAY, DEFAULT_LINE_DELAY)
            cmd_get(ser, "tcpperfport", DEFAULT_CHAR_DELAY, DEFAULT_LINE_DELAY)
            return 0

        print("\n--- Set TCP perf config ---")
        if not cmd_set(ser, "tcpperfip", args.server_ip, DEFAULT_CHAR_DELAY, DEFAULT_LINE_DELAY):
            return 3
        if not cmd_set(ser, "tcpperfport", args.server_port, DEFAULT_CHAR_DELAY, DEFAULT_LINE_DELAY):
            return 3

        print("\n--- Verify written values ---")
        cmd_get(ser, "tcpperfip", DEFAULT_CHAR_DELAY, DEFAULT_LINE_DELAY)
        cmd_get(ser, "tcpperfport", DEFAULT_CHAR_DELAY, DEFAULT_LINE_DELAY)

        print("\n--- Commit to LittleFS ---")
        if not cmd_commit(ser, DEFAULT_CHAR_DELAY, DEFAULT_LINE_DELAY):
            return 4

        if not args.no_reset:
            print("\n--- Reset device ---")
            cmd_reset(ser, DEFAULT_CHAR_DELAY)
        else:
            print("\n--no-reset 指定のため reset 抑止")

        print("\nDone.")
        return 0
    finally:
        ser.close()


if __name__ == "__main__":
    sys.exit(main())
