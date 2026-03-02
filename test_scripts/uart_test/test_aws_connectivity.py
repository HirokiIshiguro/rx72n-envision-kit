#!/usr/bin/env python3
"""
AWS IoT Core Connectivity Test for aws_demos
RX72N Envision Kit の aws_demos が AWS IoT Core に MQTT 接続できることを検証する。

処理フロー:
  1. COM7 でログ監視スレッドを開始
  2. COM6 で reset コマンドを送信（MCU リスタート）
  3. COM7 のログで接続マイルストーンを順次検出:
     - IP アドレス取得 (DHCP)
     - TLS 接続確立
     - MQTT 接続成功
  4. 全マイルストーン検出で PASS、タイムアウトで FAIL

環境変数:
  COMMAND_PORT      : コマンドポート (デフォルト: COM6)
  COMMAND_BAUD_RATE : コマンドボーレート (デフォルト: 115200)
  UART_PORT         : ログポート (デフォルト: COM7)
  UART_BAUD_RATE    : ログボーレート (デフォルト: 921600)
"""

import argparse
import os
import re
import sys
import threading
import time

import serial

# --- デフォルト値 ---
DEFAULT_CMD_PORT = os.environ.get("COMMAND_PORT", "COM6")
DEFAULT_CMD_BAUD = int(os.environ.get("COMMAND_BAUD_RATE", "115200"))
DEFAULT_LOG_PORT = os.environ.get("UART_PORT", "COM7")
DEFAULT_LOG_BAUD = int(os.environ.get("UART_BAUD_RATE", "921600"))
DEFAULT_TIMEOUT = 120


class MilestoneMonitor:
    """COM7 ログからマイルストーンを検出するモニター"""

    # 検出対象マイルストーン（順序は問わない）
    MILESTONES = {
        "ip_address": {
            "description": "IP address obtained (DHCP)",
            "patterns": [
                re.compile(r"IP\s*Address:\s*\d+\.\d+\.\d+\.\d+", re.IGNORECASE),
                re.compile(r"network is up", re.IGNORECASE),
            ],
        },
        "tls_connection": {
            "description": "TLS connection established",
            "patterns": [
                re.compile(r"TLS connection to", re.IGNORECASE),
                re.compile(r"Creating a TLS connection", re.IGNORECASE),
            ],
        },
        "mqtt_connection": {
            "description": "MQTT connection established",
            "patterns": [
                re.compile(r"MQTT connection is established", re.IGNORECASE),
                re.compile(r"MQTT.+CONNACK", re.IGNORECASE),
                re.compile(r"An MQTT connection is established", re.IGNORECASE),
            ],
        },
    }

    # エラーパターン
    ERROR_PATTERNS = [
        re.compile(r"Connection to the broker failed", re.IGNORECASE),
        re.compile(r"Failed to establish MQTT", re.IGNORECASE),
        re.compile(r"TLS.+failed", re.IGNORECASE),
        re.compile(r"Certificate verification failed", re.IGNORECASE),
    ]

    def __init__(self):
        self.detected = {}
        self.errors = []
        self.all_lines = []
        self.rx_bytes_total = 0  # COM7 受信バイト数（診断用）
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

    def check_line(self, line):
        """1行のログをチェックし、マイルストーンまたはエラーを検出"""
        with self.lock:
            self.all_lines.append(line)

            # マイルストーン検出
            for name, info in self.MILESTONES.items():
                if name not in self.detected:
                    for pattern in info["patterns"]:
                        if pattern.search(line):
                            self.detected[name] = {
                                "time": time.time(),
                                "line": line.strip(),
                            }
                            print(f"[MILESTONE] {info['description']}")
                            print(f"  >> {line.strip()}")
                            break

            # エラー検出
            for pattern in self.ERROR_PATTERNS:
                if pattern.search(line):
                    self.errors.append(line.strip())
                    print(f"[ERROR] {line.strip()}")

    def all_detected(self):
        """全マイルストーンが検出されたか"""
        with self.lock:
            return len(self.detected) == len(self.MILESTONES)

    def get_report(self):
        """検出結果レポート"""
        with self.lock:
            report = []
            for name, info in self.MILESTONES.items():
                if name in self.detected:
                    report.append((name, True, info["description"], self.detected[name]["line"]))
                else:
                    report.append((name, False, info["description"], ""))
            return report, self.errors


def log_monitor_thread(ser, monitor):
    """COM7 ログ監視スレッド"""
    buf = b""
    while not monitor.stop_event.is_set():
        try:
            n = ser.in_waiting
            if n > 0:
                chunk = ser.read(n)
                buf += chunk
                with monitor.lock:
                    monitor.rx_bytes_total += len(chunk)
                # 行単位で処理
                while b"\n" in buf:
                    line_bytes, buf = buf.split(b"\n", 1)
                    line = line_bytes.decode("utf-8", errors="replace")
                    monitor.check_line(line)
            else:
                time.sleep(0.05)
        except serial.SerialException:
            break


def send_reset(cmd_ser, timeout=10):
    """COM6 で reset コマンドを送信し、リセット実行を検証する

    検証ステップ:
      1. プロンプト確認 --COM6 に \\r\\n を送り "$" が返るか (最大3回)
      2. reset コマンド送信
      3. リセット確認 --MCU リスタートにより COM6 が無応答になるか

    Returns:
        True  --リセットが実行された（COM6 無応答を確認）
        False --リセット失敗の可能性あり
    """
    print("[INFO] Verifying COM6 prompt before reset...")

    # --- ステップ 1: プロンプト確認 ---
    prompt_detected = False
    for attempt in range(1, 4):
        cmd_ser.reset_input_buffer()
        cmd_ser.write(b"\r\n")
        cmd_ser.flush()

        buf = b""
        poll_start = time.time()
        while (time.time() - poll_start) < 2.0:
            n = cmd_ser.in_waiting
            if n > 0:
                buf += cmd_ser.read(n)
                decoded = buf.decode("utf-8", errors="replace")
                if "$" in decoded:
                    prompt_detected = True
                    break
            else:
                time.sleep(0.05)

        decoded = buf.decode("utf-8", errors="replace").strip()
        if prompt_detected:
            print(f"[INFO] Prompt detected on attempt {attempt}")
            print(f"[DEBUG] COM6 response: {decoded[:120]}")
            break
        else:
            print(f"[WARN] Attempt {attempt}: no prompt. "
                  f"RX bytes={len(buf)}, data={decoded[:80]!r}")

    if not prompt_detected:
        print("[ERROR] COM6 prompt NOT detected --MCU may not be responsive")
        print("[ERROR] Sending reset anyway, but it may not take effect")

    # --- ステップ 2: reset コマンド送信 ---
    cmd_ser.reset_input_buffer()
    time.sleep(0.1)
    cmd_ser.write(b"reset\r\n")
    cmd_ser.flush()
    print("[INFO] Reset command sent.")

    # --- ステップ 3: リセット確認 ---
    # MCU がリセットされると COM6 (SCI2 115200) は無応答になるはず
    # 注: RX72N は約3秒で起動完了するため、1秒後にチェックする。
    #      3秒待つと新しい aws_demos のプロンプトを拾って false negative になる。
    time.sleep(1.0)
    cmd_ser.reset_input_buffer()
    cmd_ser.write(b"\r\n")
    cmd_ser.flush()
    time.sleep(1.0)

    post_buf = b""
    if cmd_ser.in_waiting > 0:
        post_buf = cmd_ser.read(cmd_ser.in_waiting)
    post_decoded = post_buf.decode("utf-8", errors="replace").strip()

    if "$" in post_decoded:
        print("[WARN] Prompt STILL detected after reset --MCU may NOT have reset!")
        print(f"[DEBUG] Post-reset COM6: {post_decoded[:120]}")
        return False
    else:
        print("[INFO] No prompt after reset --MCU appears to be resetting (expected)")
        if post_decoded:
            print(f"[DEBUG] Post-reset COM6 data: {post_decoded[:120]}")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="AWS IoT Core connectivity test for aws_demos"
    )
    parser.add_argument("--device-id",
                        help="Device ID (loads config from device_config.json)")
    parser.add_argument("--cmd-port", default=DEFAULT_CMD_PORT,
                        help=f"Command serial port (default: {DEFAULT_CMD_PORT})")
    parser.add_argument("--cmd-baud", type=int, default=DEFAULT_CMD_BAUD,
                        help=f"Command baud rate (default: {DEFAULT_CMD_BAUD})")
    parser.add_argument("--log-port", default=DEFAULT_LOG_PORT,
                        help=f"Log serial port (default: {DEFAULT_LOG_PORT})")
    parser.add_argument("--log-baud", type=int, default=DEFAULT_LOG_BAUD,
                        help=f"Log baud rate (default: {DEFAULT_LOG_BAUD})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Overall timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--skip-reset", action="store_true",
                        help="Skip device reset (assume already running)")
    args = parser.parse_args()

    # --device-id が指定された場合、device_config.json からポート設定を解決
    if args.device_id:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from device_config_loader import load_device_config
        device = load_device_config(args.device_id)
        print(f"[INFO] Loaded config for device: {args.device_id}")

        if args.cmd_port == DEFAULT_CMD_PORT:
            args.cmd_port = device["command_port"]
        if args.cmd_baud == DEFAULT_CMD_BAUD:
            args.cmd_baud = device["command_baud"]
        if args.log_port == DEFAULT_LOG_PORT:
            args.log_port = device["log_port"]
        if args.log_baud == DEFAULT_LOG_BAUD:
            args.log_baud = device["log_baud"]

    print("=" * 60)
    print("[INFO] AWS IoT Core Connectivity Test")
    print(f"[INFO]   Command Port: {args.cmd_port} @ {args.cmd_baud}bps")
    print(f"[INFO]   Log Port    : {args.log_port} @ {args.log_baud}bps")
    print(f"[INFO]   Timeout     : {args.timeout}s")
    print(f"[INFO]   Skip Reset  : {args.skip_reset}")
    print("=" * 60)

    monitor = MilestoneMonitor()
    log_ser = None
    cmd_ser = None

    try:
        # COM7 ログポートを開く
        log_ser = serial.Serial(args.log_port, args.log_baud, timeout=0)
        time.sleep(0.1)
        log_ser.reset_input_buffer()
        print(f"[INFO] Opened log port: {args.log_port} at {args.log_baud} bps")

        # ログ監視スレッド開始
        thread = threading.Thread(target=log_monitor_thread, args=(log_ser, monitor), daemon=True)
        thread.start()

        reset_ok = True
        if not args.skip_reset:
            # COM6 コマンドポートを開く
            cmd_ser = serial.Serial(args.cmd_port, args.cmd_baud, timeout=0)
            time.sleep(0.1)
            cmd_ser.reset_input_buffer()
            print(f"[INFO] Opened cmd port: {args.cmd_port} at {args.cmd_baud} bps")

            # リセット送信（検証付き）
            reset_ok = send_reset(cmd_ser)

            # COM6 を閉じる
            cmd_ser.close()
            cmd_ser = None
            print("[INFO] Closed cmd port")

            if not reset_ok:
                print("[WARN] Reset verification failed --continuing to monitor, "
                      "but results may be unreliable")

        # マイルストーン監視
        print()
        print(f"[INFO] Monitoring COM7 for connection milestones (timeout={args.timeout}s)...")
        start = time.time()
        last_status = 0
        early_check_done = False

        while (time.time() - start) < args.timeout:
            if monitor.all_detected():
                elapsed = time.time() - start
                print(f"\n[INFO] All milestones detected in {elapsed:.1f}s")
                break

            elapsed = time.time() - start

            # 15秒経過時の診断チェック: COM7 から何かデータが来ているか？
            if not early_check_done and elapsed >= 15:
                early_check_done = True
                with monitor.lock:
                    rx_total = monitor.rx_bytes_total
                    line_count = len(monitor.all_lines)
                if rx_total == 0:
                    print(f"[DIAG] 15s elapsed: COM7 received 0 bytes --"
                          f"MCU may not have booted!")
                    if not reset_ok:
                        print(f"[DIAG] Combined with reset verification failure, "
                              f"reset likely did NOT work")
                else:
                    print(f"[DIAG] 15s elapsed: COM7 received {rx_total} bytes, "
                          f"{line_count} lines --MCU is outputting")

            # 30秒ごとにステータス表示
            if int(elapsed) // 30 > last_status:
                last_status = int(elapsed) // 30
                with monitor.lock:
                    rx_total = monitor.rx_bytes_total
                report, errors = monitor.get_report()
                detected = sum(1 for _, ok, _, _ in report if ok)
                print(f"[INFO] {elapsed:.0f}s elapsed: {detected}/{len(report)} milestones, "
                      f"COM7 RX={rx_total} bytes")

            time.sleep(0.5)

        # 監視終了
        monitor.stop_event.set()
        time.sleep(0.5)

    except serial.SerialException as e:
        print(f"[ERROR] Serial port error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        monitor.stop_event.set()
    finally:
        if log_ser and log_ser.is_open:
            log_ser.close()
            print(f"[INFO] Closed {args.log_port}")
        if cmd_ser and cmd_ser.is_open:
            cmd_ser.close()
            print(f"[INFO] Closed {args.cmd_port}")

    # --- 結果レポート ---
    print()
    print("=" * 60)
    report, errors = monitor.get_report()
    with monitor.lock:
        rx_total = monitor.rx_bytes_total
        line_count = len(monitor.all_lines)

    print(f"  [INFO] COM7 total: {rx_total} bytes, {line_count} lines received")
    print()

    for name, ok, description, line in report:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {description}")
        if line:
            print(f"         {line[:80]}")

    if errors:
        print()
        print(f"  Errors detected ({len(errors)}):")
        for err in errors[:5]:
            print(f"    - {err[:80]}")

    print("=" * 60)

    all_ok = monitor.all_detected()
    if all_ok:
        print("[PASS] AWS IoT Core connectivity verified")
        sys.exit(0)
    else:
        detected = sum(1 for _, ok, _, _ in report if ok)
        print(f"[FAIL] Only {detected}/{len(report)} milestones detected")

        # 診断ヒント
        if rx_total == 0:
            print("[DIAG] COM7 received 0 bytes during entire monitoring period")
            print("[DIAG] Possible causes:")
            print("  1. Reset command did not reach MCU (COM6 not responsive)")
            print("  2. MCU crashed at boot (before any UART output)")
            print("  3. COM7 port issue (wrong port, baud rate, or held by other process)")
            print("  4. Boot loader did not jump to user program")
            if not reset_ok:
                print("[DIAG] ** Reset verification FAILED --cause #1 is most likely **")
        elif not any(ok for _, ok, _, _ in report):
            print("[HINT] COM7 received data but no milestones matched:")
            print("  - Is the device provisioned? (run provision_aws.py)")
            print("  - Is Ethernet connected?")
            print("  - Is the MQTT broker endpoint correct?")
            # 受信した行の先頭数行を表示（デバッグ用）
            print("[DIAG] First lines received on COM7:")
            with monitor.lock:
                for i, line in enumerate(monitor.all_lines[:10]):
                    print(f"  [{i+1}] {line.strip()[:100]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
