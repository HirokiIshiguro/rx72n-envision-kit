#!/usr/bin/env python3
"""
Screen Navigation Test via UART Touch Command
RX72N Envision Kit の UART touch コマンドで画面遷移を検証

Screen 00 (タイトル画面) から Screen 01 (メイン画面) への遷移には
touch コマンド 2 回が必要:
  - 1回目: AppWizard VAR_01 が 0→1 (遷移条件未達)
  - 2回目: VAR_01 が 1→2 (VAR_00==1 && VAR_01==2 で遷移実行)

Screen 01 ボタン座標 (ID_SCREEN_01.c から計算):
  BUTTON_00 (System Info)   : center (346, 10)
  BUTTON_01 (FW Update tab) : center (434, 10)
  BUTTON_03 (FW Update exec): center (346, 238) ※WINDOW_01内
  BUTTON_04 (Reset)         : center (434, 238) ※WINDOW_01内

環境変数:
  COMMAND_PORT      : シリアルポート (デフォルト: COM6)
  COMMAND_BAUD_RATE : ボーレート     (デフォルト: 115200)
"""

import argparse
import os
import sys
import time

import serial

# --- 定数 ---
DEFAULT_PORT = os.environ.get("COMMAND_PORT", "COM6")
DEFAULT_BAUD = int(os.environ.get("COMMAND_BAUD_RATE", "115200"))
DEFAULT_TIMEOUT = 30

# CommandTester を再利用 (同ディレクトリの test_aws_demos_commands.py)
sys.path.insert(0, os.path.dirname(__file__))
from test_aws_demos_commands import CommandTester


def main():
    parser = argparse.ArgumentParser(
        description="Screen navigation test via UART touch command"
    )
    parser.add_argument("--cmd-port", default=DEFAULT_PORT,
                        help=f"Command serial port (default: {DEFAULT_PORT})")
    parser.add_argument("--cmd-baud", type=int, default=DEFAULT_BAUD,
                        help=f"Command baud rate (default: {DEFAULT_BAUD})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Overall timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--initial-wait", type=float, default=3.0,
                        help="Initial wait before polling (default: 3s)")
    parser.add_argument("--prompt-timeout", type=int, default=60,
                        help="Timeout for prompt polling in seconds (default: 60)")
    args = parser.parse_args()

    print("=" * 60)
    print("[INFO] Screen Navigation Test via UART Touch Command")
    print(f"[INFO]   Cmd Port : {args.cmd_port}")
    print(f"[INFO]   Cmd Baud : {args.cmd_baud}")
    print(f"[INFO]   Timeout  : {args.timeout}s")
    print("=" * 60)

    tester = CommandTester(args.cmd_port, args.cmd_baud, args.timeout, retries=3)

    try:
        tester.open()

        # MCU 起動直後のノイズ回避
        print(f"[INFO] Waiting {args.initial_wait}s for MCU to stabilize...")
        time.sleep(args.initial_wait)

        # プロンプトポーリング
        if not tester.wait_for_prompt(timeout=args.prompt_timeout):
            print("[FAIL] Could not establish communication with aws_demos")
            sys.exit(1)

        # --- Step 1: Screen 00 → Screen 01 遷移 (touch any × 2) ---
        print()
        print("[STEP] Screen 00 → Screen 01 navigation (touch any × 2)")

        for i in range(1, 3):
            print(f"[INFO] Sending touch any ({i}/2)...")
            raw = tester.send_command_with_retry("touch any")
            if raw is None:
                print(f"[FAIL] No response for touch any ({i}/2)")
                sys.exit(1)
            body = tester.extract_response_body(raw, "touch any")
            if "ok" not in body.lower():
                print(f"[FAIL] Unexpected response: {body}")
                sys.exit(1)
            print(f"[PASS] touch any ({i}/2): {body.strip()}")
            time.sleep(0.2)

        print("[PASS] Screen 00 → Screen 01 navigation complete")
        tester.passed += 1

        # --- Step 2: Screen 01 ボタンタッチ (BUTTON_00: System Info tab) ---
        print()
        print("[STEP] Touch BUTTON_00 (System Info tab) at (346, 10)")
        raw = tester.send_command_with_retry("touch 346 10")
        if raw is None:
            print("[FAIL] No response for touch 346 10")
            sys.exit(1)
        body = tester.extract_response_body(raw, "touch 346 10")
        if "ok" not in body.lower():
            print(f"[FAIL] Unexpected response: {body}")
            sys.exit(1)
        print(f"[PASS] BUTTON_00 touch: {body.strip()}")
        tester.passed += 1

        # --- Step 3: FW Update タブに切替 (BUTTON_01) ---
        print()
        print("[STEP] Touch BUTTON_01 (FW Update tab) at (434, 10)")
        raw = tester.send_command_with_retry("touch 434 10")
        if raw is None:
            print("[FAIL] No response for touch 434 10")
            sys.exit(1)
        body = tester.extract_response_body(raw, "touch 434 10")
        if "ok" not in body.lower():
            print(f"[FAIL] Unexpected response: {body}")
            sys.exit(1)
        print(f"[PASS] BUTTON_01 touch: {body.strip()}")
        tester.passed += 1

        # --- 結果レポート ---
        print()
        print("=" * 60)
        print(f"[RESULT] Tests: {tester.passed}, Passed: {tester.passed}, "
              f"Failed: {tester.failed}, Warnings: {tester.warnings}")
        print("=" * 60)

        if tester.failed > 0:
            print("[FAIL] Some tests failed")
            sys.exit(1)
        else:
            print("[PASS] All screen navigation tests passed")
            sys.exit(0)

    except serial.SerialException as e:
        print(f"[ERROR] Serial port error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        sys.exit(130)
    finally:
        tester.close()


if __name__ == "__main__":
    main()
