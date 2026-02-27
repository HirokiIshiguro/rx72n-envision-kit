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

注意: rfp-cli -run による起動（デバッガ経由）では UART 出力を確認できる。
パワーオンリセットでの起動はオンボード E2 Lite (RL78/G1C) が RES# をホールド
するため、E2 Lite USB 給電のみでは動作しない（AC アダプタ給電が必要）。
CI では rfp-cli -run を使用するため、この制約の影響を受けない。

環境変数:
  UART_PORT        : シリアルポート (デフォルト: COM6)
  UART_BAUD_RATE   : ボーレート     (デフォルト: 115200)
  UART_TIMEOUT_SEC : 全体タイムアウト秒数 (デフォルト: 30)

引数:
  --flash-cmd CMD  : flash コマンド（rfp-cli 呼び出し）
                     省略時は flash をスキップし UART 読み取りのみ
  --diag           : 診断モード（全 COM ポートを同時監視）
"""

import argparse
import os
import subprocess
import sys
import threading
import time

import serial
import serial.tools.list_ports

UART_PORT = os.environ.get("UART_PORT", "COM6")
UART_BAUD_RATE = int(os.environ.get("UART_BAUD_RATE", "115200"))
UART_TIMEOUT_SEC = int(os.environ.get("UART_TIMEOUT_SEC", "30"))
EXPECTED_STRING = "RX72N secure boot program"


def list_com_ports():
    """利用可能な COM ポートを列挙"""
    ports = serial.tools.list_ports.comports()
    for p in sorted(ports, key=lambda x: x.device):
        print(f"[DIAG]   {p.device}: {p.description} (VID:PID={p.vid}:{p.pid})")
    return ports


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


def read_port(port_name, baud, timeout, results, expected):
    """ノンブロッキングで1ポートを読み取り"""
    try:
        with serial.Serial(port_name, baud, timeout=0) as ser:
            ser.reset_input_buffer()
            results[port_name] = {"open": True, "lines": [], "raw_bytes": 0}
            buf = b""
            start = time.time()
            while (time.time() - start) < timeout:
                n = ser.in_waiting
                if n > 0:
                    chunk = ser.read(n)
                    results[port_name]["raw_bytes"] += len(chunk)
                    buf += chunk
                    while b"\n" in buf:
                        line_raw, buf = buf.split(b"\n", 1)
                        decoded = line_raw.decode("utf-8", errors="replace").strip()
                        if decoded:
                            elapsed = time.time() - start
                            results[port_name]["lines"].append(decoded)
                            print(f"[RECV:{port_name}] '{decoded}' (t={elapsed:.1f}s)")
                            if expected in decoded:
                                results[port_name]["found"] = True
                                return
                else:
                    time.sleep(0.05)
            # 残りバッファ
            if buf:
                decoded = buf.decode("utf-8", errors="replace").strip()
                if decoded:
                    results[port_name]["lines"].append(decoded)
                    if expected in decoded:
                        results[port_name]["found"] = True
    except serial.SerialException as e:
        results[port_name] = {"open": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--flash-cmd", help="Flash command (rfp-cli)")
    parser.add_argument("--diag", action="store_true", help="Diagnostic mode: monitor all COM ports")
    args = parser.parse_args()

    print("=" * 60)
    print("[INFO] UART Boot Loader Flash + Test")
    print(f"[INFO]   Port         : {UART_PORT}")
    print(f"[INFO]   Baud         : {UART_BAUD_RATE}")
    print(f"[INFO]   Total timeout: {UART_TIMEOUT_SEC}s")
    print(f"[INFO]   Expect       : '{EXPECTED_STRING}'")
    print(f"[INFO]   Flash        : {'yes' if args.flash_cmd else 'skip'}")
    print(f"[INFO]   Diag mode    : {'yes' if args.diag else 'no'}")
    print("=" * 60)

    # 診断: 利用可能なポート一覧
    print("[DIAG] Available COM ports:")
    ports = list_com_ports()
    if not ports:
        print("[DIAG]   (none)")

    # 読み取り対象ポート
    port_names = [p.device for p in ports]
    if args.diag:
        read_ports = [p.device for p in ports if p.device != "COM1"]
    else:
        read_ports = [UART_PORT]

    flash_returncode = [0]
    flash_done = threading.Event()
    start_time = time.time()

    def flash_worker():
        try:
            flash_returncode[0] = run_flash(args.flash_cmd)
        finally:
            flash_done.set()
            print(f"[FLASH] Flash thread completed (t={time.time() - start_time:.1f}s)")

    # 全ポートを先に開く
    results = {}
    read_threads = []

    for port in read_ports:
        t = threading.Thread(
            target=read_port,
            args=(port, UART_BAUD_RATE, UART_TIMEOUT_SEC, results, EXPECTED_STRING),
        )
        read_threads.append(t)
        t.start()
        print(f"[INFO] Listening on {port}...")

    time.sleep(0.5)

    # Flash 開始
    if args.flash_cmd:
        flash_thread = threading.Thread(target=flash_worker)
        flash_thread.start()
        print("[INFO] Flash started in background")
    else:
        flash_done.set()

    # 全読み取りスレッド完了を待つ
    for t in read_threads:
        t.join(timeout=UART_TIMEOUT_SEC + 10)

    if args.flash_cmd:
        flash_thread.join(timeout=60)

    # 結果レポート
    print()
    print("=" * 60)
    print("[RESULT] Port diagnostics:")
    for port, info in sorted(results.items()):
        if not info.get("open"):
            print(f"  {port}: FAILED to open - {info.get('error', 'unknown')}")
        else:
            found = info.get("found", False)
            print(f"  {port}: raw_bytes={info['raw_bytes']}, lines={len(info['lines'])}, found={found}")
            for line in info["lines"]:
                print(f"    > '{line}'")
    print("=" * 60)

    if args.flash_cmd and flash_returncode[0] != 0:
        print(f"[ERROR] Flash command failed with exit code {flash_returncode[0]}")
        sys.exit(1)

    # 判定
    primary = results.get(UART_PORT, {})
    if primary.get("found"):
        print("-" * 60)
        print(f"[PASS] '{EXPECTED_STRING}' received on {UART_PORT}")
        print("-" * 60)
        sys.exit(0)

    # 他のポートで見つかった場合はヒント表示
    for port, info in results.items():
        if port != UART_PORT and info.get("found"):
            print("-" * 60)
            print(f"[FAIL] '{EXPECTED_STRING}' NOT found on {UART_PORT}")
            print(f"[HINT] But found on {port}! Consider changing UART_PORT.")
            print("-" * 60)
            sys.exit(1)

    print("-" * 60)
    print(f"[FAIL] '{EXPECTED_STRING}' not found within {UART_TIMEOUT_SEC}s")
    print("-" * 60)
    sys.exit(1)


if __name__ == "__main__":
    main()
