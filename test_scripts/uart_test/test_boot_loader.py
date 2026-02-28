#!/usr/bin/env python3
"""
UART Boot Loader Flash + Test Script
RX72N Envision Kit boot_loader の書き込み＋起動確認テスト

boot_loader は起動時に一度だけ UART (SCI7, 921600bps, COM7 PMOD FTDI) へ以下を出力する:
  -------------------------------------------------
  RX72N secure boot program
  -------------------------------------------------

このスクリプトは:
1. rfp-cli で boot_loader を書き込み＋実行（同期的に完了を待つ）
2. flash 完了後に UART ポートを開く
3. UART から "RX72N secure boot program" の受信を確認

アーキテクチャ:
  flash を同期実行してから COM ポートを開く。
  COM7 (PMOD FTDI) は E2 Lite と別の USB デバイスのため、rfp-cli の
  デバッガ切断時の USB バスリセットの影響を受けない（旧 COM6 では問題だった）。
  flash 完了 → USB 安定化待ち → COM open → read の順序で実行する。

  boot_loader の UART 出力はバナー + "send userprog.rsu via UART." まで
  数百バイト程度で、USB シリアルドライバの受信バッファ (4KB+) に収まる。
  2秒の安定化待ち後でもバッファからデータを読み取れる。

注意: rfp-cli -run による起動（デバッガ経由）では UART 出力を確認できる。
パワーオンリセットでの起動はオンボード E2 Lite (RL78/G1C) が RES# をホールド
するため、E2 Lite USB 給電のみでは動作しない（AC アダプタ給電が必要）。
CI では rfp-cli -run を使用するため、この制約の影響を受けない。

環境変数:
  UART_PORT        : シリアルポート (デフォルト: COM7)
  UART_BAUD_RATE   : ボーレート     (デフォルト: 921600)
  UART_TIMEOUT_SEC : 全体タイムアウト秒数 (デフォルト: 30)

引数:
  --flash-cmd CMD  : flash コマンド（rfp-cli 呼び出し）
                     省略時は flash をスキップし UART 読み取りのみ
  --diag           : 診断モード（全 COM ポートを同時監視）
  --post-flash-delay SEC : flash 後の USB 安定化待ち秒数 (デフォルト: 3)
"""

import argparse
import os
import subprocess
import sys
import threading
import time

import serial
import serial.tools.list_ports

UART_PORT = os.environ.get("UART_PORT", "COM7")
UART_BAUD_RATE = int(os.environ.get("UART_BAUD_RATE", "921600"))
UART_TIMEOUT_SEC = int(os.environ.get("UART_TIMEOUT_SEC", "30"))
EXPECTED_STRING = "RX72N secure boot program"


def list_com_ports():
    """利用可能な COM ポートを列挙"""
    ports = serial.tools.list_ports.comports()
    for p in sorted(ports, key=lambda x: x.device):
        print(f"[DIAG]   {p.device}: {p.description} (VID:PID={p.vid}:{p.pid})")
    return ports


def run_flash(cmd):
    """Flash コマンドを同期的に実行"""
    print(f"[FLASH] Executing: {cmd}")
    start = time.time()
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True, text=True, timeout=120
    )
    elapsed = time.time() - start
    print(f"[FLASH] Exit code: {result.returncode} (t={elapsed:.1f}s)")
    if result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            print(f"[FLASH] {line}")
    if result.returncode != 0 and result.stderr.strip():
        for line in result.stderr.strip().split("\n"):
            print(f"[FLASH:ERR] {line}")
    return result.returncode


def read_port(port_name, baud, timeout, results, expected, flush=False):
    """ノンブロッキングで1ポートを読み取り

    Args:
        flush: True の場合、開始時にバッファをクリアする。
               False の場合、既にバッファにあるデータも読み取る。
               flash 後の読み取りでは False にして、boot_loader の出力を
               USB シリアルドライバのバッファから取得する。
    """
    try:
        with serial.Serial(port_name, baud, timeout=0) as ser:
            if flush:
                ser.reset_input_buffer()
            # 開始時点でバッファにあるバイト数を記録（診断用）
            initial_waiting = ser.in_waiting
            if initial_waiting > 0:
                print(f"[DIAG:{port_name}] {initial_waiting} bytes already in buffer")
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
    parser.add_argument("--post-flash-delay", type=float, default=3.0,
                        help="Delay after flash for USB stabilization (default: 3s)")
    args = parser.parse_args()

    print("=" * 60)
    print("[INFO] UART Boot Loader Flash + Test")
    print(f"[INFO]   Port             : {UART_PORT}")
    print(f"[INFO]   Baud             : {UART_BAUD_RATE}")
    print(f"[INFO]   Total timeout    : {UART_TIMEOUT_SEC}s")
    print(f"[INFO]   Expect           : '{EXPECTED_STRING}'")
    print(f"[INFO]   Flash            : {'yes' if args.flash_cmd else 'skip'}")
    print(f"[INFO]   Post-flash delay : {args.post_flash_delay}s")
    print(f"[INFO]   Diag mode        : {'yes' if args.diag else 'no'}")
    print("=" * 60)

    # 診断: 利用可能なポート一覧
    print("[DIAG] Available COM ports (before flash):")
    ports = list_com_ports()
    if not ports:
        print("[DIAG]   (none)")

    start_time = time.time()

    # ===== Phase 1: Flash (同期実行) =====
    if args.flash_cmd:
        print()
        print("[INFO] Phase 1: Flash boot_loader")
        flash_rc = run_flash(args.flash_cmd)
        if flash_rc != 0:
            print(f"[ERROR] Flash command failed with exit code {flash_rc}")
            sys.exit(1)

        # USB 安定化待ち
        # COM7 (PMOD FTDI) は E2 Lite と別 USB デバイスだが、
        # rfp-cli のデバッガ切断後の安定化待ちは念のため残す
        print(f"[INFO] Waiting {args.post_flash_delay}s for USB stabilization...")
        time.sleep(args.post_flash_delay)

        # 診断: flash 後のポート一覧
        print("[DIAG] Available COM ports (after flash):")
        ports_after = list_com_ports()
        if not ports_after:
            print("[DIAG]   (none)")

    # ===== Phase 2: UART 読み取り =====
    print()
    print("[INFO] Phase 2: Read UART output")

    # 読み取り対象ポート
    if args.diag:
        read_ports = [p.device for p in (ports_after if args.flash_cmd else ports) if p.device != "COM1"]
    else:
        read_ports = [UART_PORT]

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

    # 全読み取りスレッド完了を待つ
    for t in read_threads:
        t.join(timeout=UART_TIMEOUT_SEC + 10)

    total_elapsed = time.time() - start_time

    # ===== 結果レポート =====
    print()
    print("=" * 60)
    print(f"[RESULT] Port diagnostics (total elapsed: {total_elapsed:.1f}s):")
    for port, info in sorted(results.items()):
        if not info.get("open"):
            print(f"  {port}: FAILED to open - {info.get('error', 'unknown')}")
        else:
            found = info.get("found", False)
            print(f"  {port}: raw_bytes={info['raw_bytes']}, lines={len(info['lines'])}, found={found}")
            for line in info["lines"]:
                print(f"    > '{line}'")
    print("=" * 60)

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
