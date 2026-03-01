#!/usr/bin/env python3
"""
SD Card Firmware Update Integration Test for RX72N Envision Kit
UART 経由で SD カードに RSU ファイルを転送し、GUI 操作でファームウェア更新を検証する統合テスト。

テストフロー:
  Phase 1: COM6 で userprog.rsu を SD カードに転送 (sdcard write コマンド)
  Phase 2: COM6 で sdcard list により転送結果を検証
  Phase 3: COM6 で touch コマンドにより FW Update 画面を操作 (Update 実行)
  Phase 4: COM7 で boot_loader ログを監視 (integrity check -> jump to user program)
  Phase 5: COM6 で再起動確認後、SD カードから userprog.rsu を削除 (クリーンアップ)

転送プロトコル (sdcard write):
  Host -> MCU: sdcard write <filename> <size>\r\n
  MCU -> Host: READY <chunk_size>\r\n
  [Loop:]
    Host -> MCU: [raw binary, chunk_size bytes]
    MCU -> Host: W <received_total>\r\n
  MCU -> Host: DONE <received_total>\r\n

環境変数:
  DEVICE_ID : デバイス ID (デフォルト: rx72n-01)
"""

import argparse
import os
import sys
import time

import serial

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


def wait_for_prompt(ser, timeout=30):
    """プロンプトをポーリングで待つ"""
    print(f"[INFO] Polling for prompt on {ser.port} (timeout={timeout}s)...")
    start = time.time()
    attempt = 0
    while (time.time() - start) < timeout:
        attempt += 1
        ser.reset_input_buffer()
        ser.write(b"\r\n")
        ser.flush()
        poll_start = time.time()
        buf = b""
        while (time.time() - poll_start) < 1.0:
            n = ser.in_waiting
            if n > 0:
                buf += ser.read(n)
                decoded = buf.decode("utf-8", errors="replace")
                if "$" in decoded:
                    elapsed = time.time() - start
                    print(f"[INFO] Prompt detected after {attempt} attempts ({elapsed:.1f}s)")
                    return True
            else:
                time.sleep(0.05)
        if attempt <= 5 or attempt % 10 == 0:
            print(f"[INFO] Attempt {attempt}: no prompt yet...")
    return False


def send_command(ser, cmd, timeout=10):
    """コマンドを送信し応答を取得する"""
    ser.reset_input_buffer()
    time.sleep(0.1)
    ser.write((cmd + "\r\n").encode("utf-8"))
    ser.flush()

    buf = b""
    start = time.time()
    while (time.time() - start) < timeout:
        n = ser.in_waiting
        if n > 0:
            buf += ser.read(n)
            decoded = buf.decode("utf-8", errors="replace")
            if "$ " in decoded.split("\n")[-1] or decoded.rstrip().endswith("$"):
                return decoded
        else:
            time.sleep(0.05)
    if buf:
        return buf.decode("utf-8", errors="replace")
    return None


def wait_for_marker(ser, marker, timeout=30):
    """シリアルポートから特定のマーカー文字列を待つ"""
    buf = b""
    start = time.time()
    while (time.time() - start) < timeout:
        n = ser.in_waiting
        if n > 0:
            buf += ser.read(n)
            decoded = buf.decode("utf-8", errors="replace")
            if marker in decoded:
                return decoded
        else:
            time.sleep(0.02)
    return None


def upload_rsu_to_sdcard(ser, rsu_path, filename="userprog.rsu"):
    """Phase 1: RSU ファイルを UART 経由で SD カードに転送する"""
    file_size = os.path.getsize(rsu_path)
    print(f"[UPLOAD] Transferring {filename} ({file_size} bytes, ~{file_size/1024:.0f} KB)")

    # sdcard write コマンド送信
    cmd = f"sdcard write {filename} {file_size}"
    ser.reset_input_buffer()
    time.sleep(0.1)
    ser.write((cmd + "\r\n").encode("utf-8"))
    ser.flush()

    # READY 待ち (コマンドエコー + READY <chunk_size>)
    response = wait_for_marker(ser, "READY", timeout=10)
    if response is None:
        print("[FAIL] Timeout waiting for READY response")
        return False

    # chunk_size を解析
    chunk_size = 2048  # デフォルト
    for line in response.split("\n"):
        if "READY" in line:
            parts = line.strip().split()
            for part in parts:
                if part.isdigit():
                    chunk_size = int(part)
                    break
            break
    print(f"[UPLOAD] Chunk size: {chunk_size} bytes")

    # バイナリ転送ループ
    start_time = time.time()
    last_ack = None
    with open(rsu_path, "rb") as f:
        sent = 0
        chunk_count = 0
        while sent < file_size:
            remaining = file_size - sent
            to_send = min(chunk_size, remaining)
            chunk_data = f.read(to_send)
            if len(chunk_data) != to_send:
                print(f"\n[FAIL] File read error: expected {to_send}, got {len(chunk_data)}")
                return False

            # バイナリチャンク送信
            ser.write(chunk_data)
            ser.flush()

            # W ACK 待ち
            ack = wait_for_marker(ser, "W", timeout=60)
            if ack is None:
                print(f"\n[FAIL] Timeout waiting for ACK at {sent} bytes")
                return False

            last_ack = ack
            sent += len(chunk_data)
            chunk_count += 1
            pct = sent * 100 // file_size
            elapsed = time.time() - start_time
            speed = sent / elapsed / 1024 if elapsed > 0 else 0
            print(f"\r[UPLOAD] {sent}/{file_size} ({pct}%) [{speed:.1f} KB/s]", end="", flush=True)

    # DONE 待ち
    # 注意: MCU は最後のチャンクに対して W と DONE を連続送信するため、
    # 最後の W ACK のバッファに DONE が含まれている場合がある
    if last_ack and "DONE" in last_ack:
        done = last_ack
    else:
        done = wait_for_marker(ser, "DONE", timeout=30)
    elapsed = time.time() - start_time
    print()
    if done is None:
        print("[FAIL] Timeout waiting for DONE")
        return False

    print(f"[UPLOAD] Complete in {elapsed:.1f}s ({chunk_count} chunks, {file_size/elapsed/1024:.1f} KB/s)")

    # プロンプト復帰待ち
    time.sleep(0.5)
    ser.reset_input_buffer()
    ser.write(b"\r\n")
    ser.flush()
    time.sleep(0.5)
    if ser.in_waiting > 0:
        ser.read(ser.in_waiting)

    return True


def verify_sdcard_file(ser, filename="userprog.rsu"):
    """Phase 2: sdcard list でファイルの存在を確認する"""
    response = send_command(ser, "sdcard list", timeout=10)
    if response and filename in response:
        print(f"[VERIFY] {filename} found on SD card")
        # ファイルサイズも表示
        for line in response.split("\n"):
            if filename in line:
                print(f"  >> {line.strip()}")
        return True
    else:
        print(f"[FAIL] {filename} not found in sdcard list output")
        if response:
            print(f"[DEBUG] Response: {response[:300]}")
        return False


def trigger_fw_update_gui(ser):
    """Phase 3: touch コマンドで FW Update GUI を操作し更新を実行する"""
    print("[GUI] Switching to FW Update tab...")
    resp = send_command(ser, "touch 434 10", timeout=5)
    if resp and "OK" in resp:
        print("[GUI] FW Update tab: OK")
    else:
        print(f"[WARN] FW Update tab response: {resp[:100] if resp else 'None'}")

    # SD カードファイルスキャン待ち (sdcard_task の 1000ms ポーリング)
    time.sleep(2)

    print("[GUI] Selecting file in LISTBOX...")
    resp = send_command(ser, "touch 77 34", timeout=5)
    if resp and "OK" in resp:
        print("[GUI] File selection: OK")
    else:
        print(f"[WARN] File selection response: {resp[:100] if resp else 'None'}")
    time.sleep(0.5)

    print("[GUI] Pressing Update button...")
    resp = send_command(ser, "touch 346 238", timeout=5)
    if resp and "OK" in resp:
        print("[GUI] Update button: OK")
    else:
        print(f"[WARN] Update button response: {resp[:100] if resp else 'None'}")

    print("[GUI] Firmware update triggered. MCU will reset after completion.")
    return True


def monitor_bootloader(log_ser, timeout=180):
    """Phase 4: boot_loader ログを監視し、ファームウェア更新完了を検証する"""
    print(f"[MONITOR] Monitoring {log_ser.port} for boot_loader milestones (timeout={timeout}s)...")

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

    while (time.time() - start) < timeout:
        n = log_ser.in_waiting
        if n > 0:
            chunk = log_ser.read(n)
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
                    print(f"[MILESTONE] boot_loader started (t={elapsed:.1f}s)")
                    print(f"  >> {decoded}")
                elif MSG_UART_WAIT in decoded:
                    state["uart_wait"] = True
                    print(f"[WARN] boot_loader entered UART wait (SD card update skipped?)")
                    print(f"  >> {decoded}")
                elif MSG_COMPLETED_FW in decoded:
                    state["completed_fw"] = True
                    print(f"[MILESTONE] Firmware installation completed (t={elapsed:.1f}s)")
                    print(f"  >> {decoded}")
                elif MSG_INSTALL_FW in lower:
                    if not state["install_fw"]:
                        state["install_fw"] = True
                        print(f"[MILESTONE] Firmware installation started (t={elapsed:.1f}s)")
                        print(f"  >> {decoded}")
                    elif (time.time() - last_progress_time) > 5:
                        print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                        last_progress_time = time.time()
                elif MSG_INTEGRITY in lower:
                    state["integrity_check"] = True
                    print(f"[MILESTONE] Integrity check (t={elapsed:.1f}s)")
                    print(f"  >> {decoded}")
                elif MSG_CHECK_OK in decoded:
                    state["integrity_ok"] = True
                    print(f"[MILESTONE] Integrity check: OK (t={elapsed:.1f}s)")
                    print(f"  >> {decoded}")
                elif MSG_CHECK_NG in decoded:
                    state["integrity_ng"] = True
                    print(f"[MILESTONE] Integrity check: NG (t={elapsed:.1f}s)")
                    print(f"  >> {decoded}")
                elif MSG_COMPLETED_CONST in decoded:
                    state["completed_const"] = True
                    print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                elif MSG_INSTALL_CONST in lower:
                    if not state["install_const"]:
                        state["install_const"] = True
                        print(f"[LOG] (t={elapsed:.1f}s) {decoded}")
                elif MSG_SW_RESET in lower:
                    state["sw_reset"] = True
                    print(f"[MILESTONE] Software reset (t={elapsed:.1f}s)")
                    print(f"  >> {decoded}")
                elif MSG_JUMP_USER in lower:
                    state["jump_user"] = True
                    print(f"[MILESTONE] Jump to user program (t={elapsed:.1f}s)")
                    print(f"  >> {decoded}")

                if state["jump_user"]:
                    break
        else:
            time.sleep(0.05)

        if state["jump_user"]:
            break

    return state


def main():
    parser = argparse.ArgumentParser(
        description="SD card firmware update integration test for RX72N Envision Kit"
    )
    parser.add_argument("--device-id",
                        help="Device ID (loads config from device_config.json)")
    parser.add_argument("--rsu", required=True,
                        help="Path to userprog.rsu file")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Overall timeout in seconds (default: 300)")
    parser.add_argument("--cmd-port", default=None,
                        help="Command port (default: from device_config)")
    parser.add_argument("--cmd-baud", type=int, default=None,
                        help="Command baud rate (default: from device_config)")
    parser.add_argument("--log-port", default=None,
                        help="Log port (default: from device_config)")
    parser.add_argument("--log-baud", type=int, default=None,
                        help="Log baud rate (default: from device_config)")
    parser.add_argument("--skip-cleanup", action="store_true",
                        help="Skip SD card cleanup after test")
    args = parser.parse_args()

    # デバイスコンフィグ解決
    cmd_port = args.cmd_port or "COM6"
    cmd_baud = args.cmd_baud or 115200
    log_port = args.log_port or "COM7"
    log_baud = args.log_baud or 921600

    if args.device_id:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from device_config_loader import load_device_config
        device = load_device_config(args.device_id)
        print(f"[INFO] Loaded config for device: {args.device_id}")
        if not args.cmd_port:
            cmd_port = device["command_port"]
        if not args.cmd_baud:
            cmd_baud = device["command_baud"]
        if not args.log_port:
            log_port = device["log_port"]
        if not args.log_baud:
            log_baud = device["log_baud"]

    # RSU ファイル存在チェック
    if not os.path.isfile(args.rsu):
        print(f"[ERROR] RSU file not found: {args.rsu}")
        sys.exit(1)

    rsu_size = os.path.getsize(args.rsu)
    rsu_filename = os.path.basename(args.rsu)

    print("=" * 60)
    print("[INFO] SD Card Firmware Update Integration Test")
    print(f"[INFO]   Command Port : {cmd_port} @ {cmd_baud}bps")
    print(f"[INFO]   Log Port     : {log_port} @ {log_baud}bps")
    print(f"[INFO]   RSU File     : {args.rsu} ({rsu_size} bytes)")
    print(f"[INFO]   Timeout      : {args.timeout}s")
    print("=" * 60)

    overall_start = time.time()

    try:
        # ===== Phase 1: RSU ファイルを SD カードに転送 =====
        print()
        print("=" * 60)
        print("[PHASE 1/5] Uploading RSU to SD card via UART")
        print("=" * 60)

        cmd_ser = serial.Serial(cmd_port, cmd_baud, timeout=0)
        time.sleep(0.1)
        cmd_ser.reset_input_buffer()

        if not wait_for_prompt(cmd_ser, timeout=30):
            print("[FAIL] Could not detect prompt on command port")
            cmd_ser.close()
            sys.exit(1)

        if not upload_rsu_to_sdcard(cmd_ser, args.rsu, rsu_filename):
            print("[FAIL] RSU upload failed")
            cmd_ser.close()
            sys.exit(1)

        # ===== Phase 2: 転送結果を検証 =====
        print()
        print("=" * 60)
        print("[PHASE 2/5] Verifying uploaded file on SD card")
        print("=" * 60)

        if not verify_sdcard_file(cmd_ser, rsu_filename):
            print("[FAIL] File verification failed")
            cmd_ser.close()
            sys.exit(1)

        # ===== Phase 3: GUI 操作で FW Update を実行 =====
        print()
        print("=" * 60)
        print("[PHASE 3/5] Triggering firmware update via GUI")
        print("=" * 60)

        # COM7 をフォーム更新前に開いておく（boot_loader ログを逃さない）
        log_ser = serial.Serial(log_port, log_baud, timeout=0)
        log_ser.reset_input_buffer()

        trigger_fw_update_gui(cmd_ser)
        cmd_ser.close()
        print("[INFO] Command port closed. Waiting for MCU reset...")

        # ===== Phase 4: boot_loader ログ監視 =====
        print()
        print("=" * 60)
        print("[PHASE 4/5] Monitoring boot_loader for update verification")
        print("=" * 60)

        # FW 更新 (firm_update) + software_reset wait (5s) + boot_loader
        # 全体で 60-120 秒を見込む
        monitor_timeout = min(args.timeout - int(time.time() - overall_start), 180)
        if monitor_timeout < 30:
            monitor_timeout = 30

        state = monitor_bootloader(log_ser, timeout=monitor_timeout)
        log_ser.close()

        # ===== Phase 5: クリーンアップ =====
        print()
        print("=" * 60)
        print("[PHASE 5/5] Cleanup")
        print("=" * 60)

        if not args.skip_cleanup and state["jump_user"]:
            # aws_demos 再起動後にコマンドポート復帰を待つ
            print("[INFO] Waiting for aws_demos to restart...")
            time.sleep(10)  # DHCP + タスク初期化待ち

            try:
                cmd_ser = serial.Serial(cmd_port, cmd_baud, timeout=0)
                time.sleep(0.1)
                cmd_ser.reset_input_buffer()

                # Screen 00 通過 (touch any x 2)
                print("[INFO] Passing splash screen...")
                time.sleep(1)
                cmd_ser.write(b"\r\n")
                cmd_ser.flush()
                time.sleep(0.5)
                if cmd_ser.in_waiting > 0:
                    cmd_ser.read(cmd_ser.in_waiting)

                if wait_for_prompt(cmd_ser, timeout=30):
                    print("[CLEANUP] Deleting userprog.rsu from SD card...")
                    resp = send_command(cmd_ser, f"sdcard delete {rsu_filename}", timeout=10)
                    if resp and "deleted" in resp:
                        print(f"[CLEANUP] {rsu_filename} deleted successfully")
                    else:
                        print(f"[WARN] Could not confirm deletion: {resp[:200] if resp else 'None'}")
                else:
                    print("[WARN] Could not detect prompt for cleanup")
                cmd_ser.close()
            except serial.SerialException as e:
                print(f"[WARN] Cleanup failed (non-critical): {e}")
        elif args.skip_cleanup:
            print("[INFO] Cleanup skipped (--skip-cleanup)")
        else:
            print("[WARN] Cleanup skipped (MCU did not reach user program)")

        # ===== 結果レポート =====
        elapsed = time.time() - overall_start
        print()
        print("=" * 60)
        print(f"[INFO] Total elapsed: {elapsed:.1f}s")
        print("[INFO] Boot loader state transitions:")
        for key, val in state.items():
            status = "PASS" if val else "---"
            if key == "integrity_ng" and val:
                status = "FAIL"
            if key == "uart_wait" and val:
                status = "WARN"
            print(f"  {key:20s} : {status}")
        print("=" * 60)

        # 判定
        if state["integrity_ng"]:
            print("[FAIL] Integrity check failed (NG)")
            sys.exit(1)

        if state["jump_user"] and state["integrity_ok"]:
            print("[PASS] SD card firmware update completed successfully")
            sys.exit(0)

        if state["completed_fw"] and state["integrity_ok"] and state["sw_reset"]:
            print("[PASS] Update completed (jump_user not detected, but reset occurred)")
            sys.exit(0)

        if not state["boot"]:
            print("[FAIL] boot_loader did not start (MCU may not have reset)")
            print("[HINT] The firmware update may still be in progress or failed to trigger")
        elif not state["integrity_ok"]:
            print("[FAIL] Integrity check did not pass")
        else:
            print(f"[FAIL] Update sequence incomplete within timeout")

        sys.exit(1)

    except serial.SerialException as e:
        print(f"[ERROR] Serial port error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted")
        sys.exit(130)


if __name__ == "__main__":
    main()
