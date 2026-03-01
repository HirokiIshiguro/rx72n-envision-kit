#!/usr/bin/env python3
"""
SD Card Firmware Update Test for RX72N Envision Kit
SD カードからのファームウェアアップデートを検証するテストスクリプト

テスト前提:
  1. SD カードに userprog.rsu が書き込まれている
  2. SD カードが RX72N Envision Kit に挿入されている
  3. boot_loader が書き込み済み

テストフロー:
  1. rfp-cli で MCU をリセット (-run)
  2. COM7 で boot_loader のログを監視
  3. SD カードからの RSU 検出・検証・bank swap を確認
  4. aws_demos 起動を確認
  5. (オプション) COM6 で version コマンドを実行し更新後バージョンを確認

boot_loader のログパターン（COM7, SCI7, 921600bps）:
  - "RX72N secure boot program"          : boot_loader 起動
  - "send userprog.rsu via UART."        : UART 待ち（SD カード未検出時）
  - "installing firmware..."              : SD カードからの書き込み中
  - "completed installing firmware"       : 書き込み完了
  - "integrity check scheme = ..."        : 署名検証方式
  - "...OK" / "...NG"                    : 検証結果
  - "software reset..."                   : リセット
  - "jump to user program"               : aws_demos 起動

環境変数:
  UART_PORT      : boot_loader ログ用ポート (デフォルト: COM7)
  UART_BAUD_RATE : ボーレート (デフォルト: 921600)
"""

import argparse
import os
import subprocess
import sys
import time

import serial

DEFAULT_PORT = os.environ.get("UART_PORT", "COM7")
DEFAULT_BAUD = int(os.environ.get("UART_BAUD_RATE", "921600"))
DEFAULT_TIMEOUT = 120  # SD カード更新は時間がかかる

# boot_loader ログの期待パターン
MSG_BOOT = "RX72N secure boot program"
MSG_INSTALL_FW = "installing firmware"
MSG_COMPLETED_FW = "completed installing firmware"
MSG_INTEGRITY = "integrity check"
MSG_CHECK_OK = "...OK"
MSG_CHECK_NG = "...NG"
MSG_INSTALL_CONST = "installing const data"
MSG_COMPLETED_CONST = "completed installing const data"
MSG_SW_RESET = "software reset"
MSG_JUMP_USER = "jump to user program"
MSG_UART_WAIT = "send userprog.rsu via UART"


def main():
    parser = argparse.ArgumentParser(
        description="Test SD card firmware update on RX72N Envision Kit"
    )
    parser.add_argument("--port", default=DEFAULT_PORT,
                        help=f"Boot loader log port (default: {DEFAULT_PORT})")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD,
                        help=f"Baud rate (default: {DEFAULT_BAUD})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--reset-cmd",
                        help="rfp-cli command to reset MCU (PowerShell)")
    parser.add_argument("--skip-reset", action="store_true",
                        help="Skip MCU reset (assume already running)")
    args = parser.parse_args()

    print("=" * 60)
    print("[INFO] SD Card Firmware Update Test")
    print(f"[INFO]   Port    : {args.port} @ {args.baud}bps")
    print(f"[INFO]   Timeout : {args.timeout}s")
    print("=" * 60)

    # MCU リセット
    if not args.skip_reset:
        if args.reset_cmd:
            print(f"[INFO] Resetting MCU: {args.reset_cmd}")
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", args.reset_cmd],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                print(f"[ERROR] Reset failed: {result.stderr}")
                sys.exit(1)
            time.sleep(3)
        else:
            print("[WARN] No --reset-cmd provided. Assuming MCU is about to boot.")

    # ログ監視
    try:
        ser = serial.Serial(args.port, args.baud, timeout=0)
        ser.reset_input_buffer()
        print(f"[INFO] Listening on {args.port}...")

        # 状態追跡
        state = {
            "boot": False,
            "uart_wait": False,
            "install_fw": False,
            "completed_fw": False,
            "integrity_check": False,
            "integrity_ok": False,
            "integrity_ng": False,
            "install_const": False,
            "completed_const": False,
            "sw_reset": False,
            "jump_user": False,
        }

        buf = b""
        start = time.time()
        last_progress_time = start

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

                    elapsed = time.time() - start
                    lower = decoded.lower()

                    # 状態遷移検出
                    if MSG_BOOT in decoded:
                        state["boot"] = True
                        print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                    elif MSG_UART_WAIT in decoded:
                        state["uart_wait"] = True
                        print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                        print("[WARN] boot_loader is waiting for UART, not SD card")
                        print("[HINT] Is the SD card inserted with userprog.rsu?")
                    elif MSG_COMPLETED_FW in decoded:
                        state["completed_fw"] = True
                        print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                    elif MSG_INSTALL_FW in lower:
                        if not state["install_fw"]:
                            state["install_fw"] = True
                            print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                        # 進捗行は間引く
                        elif (time.time() - last_progress_time) > 5:
                            print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                            last_progress_time = time.time()
                    elif MSG_INTEGRITY in lower:
                        state["integrity_check"] = True
                        print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                    elif MSG_CHECK_OK in decoded:
                        state["integrity_ok"] = True
                        print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                    elif MSG_CHECK_NG in decoded:
                        state["integrity_ng"] = True
                        print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                    elif MSG_COMPLETED_CONST in decoded:
                        state["completed_const"] = True
                        print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                    elif MSG_INSTALL_CONST in lower:
                        if not state["install_const"]:
                            state["install_const"] = True
                            print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                    elif MSG_SW_RESET in lower:
                        state["sw_reset"] = True
                        print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                    elif MSG_JUMP_USER in lower:
                        state["jump_user"] = True
                        print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                    else:
                        # その他のログ（最初の 30 秒間は全出力、以降は間引き）
                        if elapsed < 30:
                            print(f"[LOG] (t={elapsed:.1f}s) {decoded[:200]}")

                    # 完了判定: aws_demos 起動確認
                    if state["jump_user"]:
                        break

            else:
                time.sleep(0.05)

            if state["jump_user"]:
                break

        ser.close()

        # 結果レポート
        elapsed = time.time() - start
        print()
        print("=" * 60)
        print(f"[INFO] Elapsed: {elapsed:.1f}s")
        print("[INFO] State transitions:")
        for key, val in state.items():
            status = "YES" if val else "no"
            print(f"  {key:20s} : {status}")
        print("=" * 60)

        # 判定
        if state["integrity_ng"]:
            print("[FAIL] Integrity check failed (NG)")
            sys.exit(1)

        if state["uart_wait"] and not state["install_fw"]:
            print("[FAIL] boot_loader entered UART wait mode (SD card not detected)")
            sys.exit(1)

        if state["jump_user"] and state["integrity_ok"]:
            print("[PASS] SD card firmware update completed successfully")
            sys.exit(0)

        if state["completed_fw"] and state["integrity_ok"] and state["sw_reset"]:
            print("[PASS] Update completed (jump_user not detected, but reset occurred)")
            sys.exit(0)

        if not state["boot"]:
            print("[FAIL] boot_loader did not start")
        elif not state["install_fw"]:
            print("[FAIL] Firmware installation did not start")
        elif not state["completed_fw"]:
            print(f"[FAIL] Firmware installation did not complete within {args.timeout}s")
        elif not state["integrity_ok"]:
            print("[FAIL] Integrity check did not pass")
        else:
            print(f"[FAIL] Update sequence incomplete within {args.timeout}s")

        sys.exit(1)

    except serial.SerialException as e:
        print(f"[ERROR] Serial port error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted")
        sys.exit(130)


if __name__ == "__main__":
    main()
