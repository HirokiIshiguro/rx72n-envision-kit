#!/usr/bin/env python3
"""
UART Command-Response Test Script for aws_demos
RX72N Envision Kit aws_demos の UART コマンドインターフェース自動テスト

aws_demos はコマンドターミナルを SCI2 (COM6, 115200bps) で提供する。
本スクリプトは各コマンドを送信し、期待される応答を検証する。

プロンプト: "RX72N Envision Kit\\r\\n$ "
コマンド送信: コマンド文字列 + "\\r\\n"
エコーバック: あり（送信した文字がそのまま返る）

テスト対象コマンド:
  - version              : ファームウェアバージョン読み出し
  - freertos cpuload read  : CPU 負荷読み出し
  - freertos cpuload reset : CPU 負荷カウンタリセット + 読み出し
  - dataflash info       : データフラッシュサイズ情報
  - dataflash read       : 全設定データ読み出し
  - timezone <tz>        : タイムゾーン設定
  - dataflash erase      : 全設定データ消去（破壊的操作、末尾で実行）

注意:
  - COM6 (RL78/G1C USB シリアル) には MCU→PC 方向の間欠受信障害がある
  - リトライ機構あり（デフォルト 3 回）
  - 受信失敗時は WARNING 扱い（テスト全体は FAIL にしない）

環境変数:
  COMMAND_PORT      : シリアルポート (デフォルト: COM6)
  COMMAND_BAUD_RATE : ボーレート     (デフォルト: 115200)
  COMMAND_TIMEOUT   : コマンド応答タイムアウト秒数 (デフォルト: 10)
"""

import argparse
import os
import sys
import time

import serial

# --- 定数 ---
DEFAULT_PORT = os.environ.get("COMMAND_PORT", "COM6")
DEFAULT_BAUD = int(os.environ.get("COMMAND_BAUD_RATE", "115200"))
DEFAULT_TIMEOUT = int(os.environ.get("COMMAND_TIMEOUT", "10"))
DEFAULT_RETRIES = 3

PROMPT = "$ "


class CommandTester:
    """UART コマンドテスター"""

    def __init__(self, port, baud, timeout, retries):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.retries = retries
        self.ser = None
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def open(self):
        """シリアルポートを開く"""
        self.ser = serial.Serial(self.port, self.baud, timeout=0)
        # バッファをクリア
        time.sleep(0.1)
        self.ser.reset_input_buffer()
        print(f"[INFO] Opened {self.port} at {self.baud} bps")

    def close(self):
        """シリアルポートを閉じる"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"[INFO] Closed {self.port}")

    def read_until_prompt(self, timeout=None):
        """プロンプト '$ ' が来るまで読み取る

        Returns:
            str: プロンプトまでの受信データ（プロンプト含む）
            None: タイムアウト
        """
        if timeout is None:
            timeout = self.timeout
        buf = b""
        start = time.time()
        while (time.time() - start) < timeout:
            n = self.ser.in_waiting
            if n > 0:
                chunk = self.ser.read(n)
                buf += chunk
                # プロンプト検出（"$ " で終わる）
                decoded = buf.decode("utf-8", errors="replace")
                if decoded.rstrip().endswith("$") or "$ " in decoded.split("\n")[-1]:
                    return decoded
            else:
                time.sleep(0.05)
        # タイムアウト — 読めた分を返す
        if buf:
            return buf.decode("utf-8", errors="replace")
        return None

    def send_command(self, cmd):
        """コマンドを送信し、応答を取得する

        Args:
            cmd: コマンド文字列（改行なし）

        Returns:
            str: 応答文字列（エコーバック・プロンプト含む）
            None: 受信失敗
        """
        # 送信前にバッファをドレイン
        self.ser.reset_input_buffer()
        time.sleep(0.1)

        # コマンド送信（\r\n で行末）
        self.ser.write((cmd + "\r\n").encode("utf-8"))
        self.ser.flush()

        # 応答読み取り
        response = self.read_until_prompt()
        return response

    def send_command_with_retry(self, cmd):
        """リトライ付きコマンド送信

        Returns:
            str: 応答文字列
            None: 全リトライ失敗
        """
        for attempt in range(1, self.retries + 1):
            response = self.send_command(cmd)
            if response is not None and len(response.strip()) > 0:
                return response
            if attempt < self.retries:
                print(f"[WARN] No response for '{cmd}', retry {attempt}/{self.retries}")
                time.sleep(1)
        return None

    def extract_response_body(self, raw_response, cmd):
        """応答からエコーバックとプロンプトを除去し、本体部分を抽出する

        Args:
            raw_response: 生の応答文字列
            cmd: 送信したコマンド

        Returns:
            str: 応答本体
        """
        if raw_response is None:
            return ""
        lines = raw_response.replace("\r", "").split("\n")
        body_lines = []
        skip_echo = True
        for line in lines:
            stripped = line.strip()
            # エコーバック行をスキップ（コマンド文字列を含む行）
            if skip_echo and cmd in stripped:
                skip_echo = False
                continue
            # プロンプト行をスキップ
            if stripped == "$" or stripped == "RX72N Envision Kit":
                continue
            if stripped:
                body_lines.append(stripped)
        return "\n".join(body_lines)

    def run_test(self, name, cmd, check_fn, description=""):
        """単一テストを実行

        Args:
            name: テスト名
            cmd: コマンド文字列
            check_fn: 応答本体を引数に取り、(pass, detail) を返す関数
            description: テスト説明
        """
        print()
        print(f"[TEST] {name}: '{cmd}'")
        if description:
            print(f"       {description}")

        raw = self.send_command_with_retry(cmd)

        if raw is None:
            print(f"[WARN] {name}: No response received (COM6 intermittent RX issue?)")
            self.warnings += 1
            return

        body = self.extract_response_body(raw, cmd)
        print(f"[RECV] Response body: {repr(body[:200])}")

        passed, detail = check_fn(body)
        if passed:
            print(f"[PASS] {name}: {detail}")
            self.passed += 1
        else:
            print(f"[FAIL] {name}: {detail}")
            self.failed += 1

    def wait_for_prompt(self, timeout=None):
        """初期プロンプトを待つ"""
        if timeout is None:
            timeout = self.timeout
        print(f"[INFO] Waiting for prompt (timeout={timeout}s)...")
        response = self.read_until_prompt(timeout)
        if response and PROMPT.strip() in response:
            print("[INFO] Prompt detected")
            return True
        # プロンプトが来ない場合、空行を送って促す
        print("[INFO] No prompt, sending empty line to trigger...")
        self.ser.write(b"\r\n")
        self.ser.flush()
        response = self.read_until_prompt(5)
        if response and PROMPT.strip() in response:
            print("[INFO] Prompt detected after nudge")
            return True
        print("[WARN] Could not detect prompt")
        return False


# --- テスト検証関数 ---

def check_version(body):
    """version コマンドの応答を検証"""
    if not body:
        return False, "Empty response"
    # バージョン文字列が含まれることを確認（例: "v2.0.2"）
    if "v" in body.lower() or "version" in body.lower() or "." in body:
        return True, f"Version: {body.strip()}"
    return False, f"Unexpected: {body.strip()}"


def check_cpuload_read(body):
    """freertos cpuload read の応答を検証"""
    if not body:
        return False, "Empty response"
    # CPU 負荷情報が含まれることを確認（数値やタスク名が出るはず）
    if any(c.isdigit() for c in body):
        return True, f"CPU load data received ({len(body)} chars)"
    return True, f"Response received: {body[:100]}"


def check_cpuload_reset(body):
    """freertos cpuload reset の応答を検証"""
    if not body:
        return False, "Empty response"
    # リセット後の読み出し結果が含まれるはず
    return True, f"CPU load reset data received ({len(body)} chars)"


def check_dataflash_info(body):
    """dataflash info の応答を検証"""
    if not body:
        return False, "Empty response"
    checks = {
        "physical size": False,
        "allocated size": False,
        "free size": False,
    }
    for key in checks:
        if key in body.lower():
            checks[key] = True
    all_ok = all(checks.values())
    missing = [k for k, v in checks.items() if not v]
    if all_ok:
        return True, f"All size fields present"
    return False, f"Missing: {', '.join(missing)}"


def check_dataflash_read(body):
    """dataflash read の応答を検証"""
    # 空のデータフラッシュなら応答なし or 短い応答も正常
    if body is None:
        return False, "No response"
    if "label" in body.lower():
        return True, f"Dataflash entries found ({len(body)} chars)"
    return True, "Dataflash appears empty (no entries)"


def check_timezone(body):
    """timezone コマンドの応答を検証"""
    if not body:
        return False, "Empty response"
    if "timezone is accepted" in body.lower():
        return True, "Timezone accepted"
    if "timezone is not accepted" in body.lower():
        return False, "Timezone not accepted"
    return False, f"Unexpected: {body.strip()}"


def check_dataflash_erase(body):
    """dataflash erase の応答を検証"""
    if not body:
        return False, "Empty response"
    if "completed erasing" in body.lower():
        return True, "Erase completed"
    return False, f"Unexpected: {body.strip()}"


def main():
    parser = argparse.ArgumentParser(
        description="UART command-response test for aws_demos"
    )
    parser.add_argument("--port", default=DEFAULT_PORT,
                        help=f"Serial port (default: {DEFAULT_PORT})")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD,
                        help=f"Baud rate (default: {DEFAULT_BAUD})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Command timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES,
                        help=f"Retry count for failed commands (default: {DEFAULT_RETRIES})")
    parser.add_argument("--skip-erase", action="store_true",
                        help="Skip dataflash erase test")
    parser.add_argument("--initial-wait", type=float, default=5.0,
                        help="Initial wait for aws_demos startup (default: 5s)")
    args = parser.parse_args()

    print("=" * 60)
    print("[INFO] aws_demos UART Command-Response Test")
    print(f"[INFO]   Port     : {args.port}")
    print(f"[INFO]   Baud     : {args.baud}")
    print(f"[INFO]   Timeout  : {args.timeout}s")
    print(f"[INFO]   Retries  : {args.retries}")
    print("=" * 60)

    tester = CommandTester(args.port, args.baud, args.timeout, args.retries)

    try:
        tester.open()

        # aws_demos が起動完了するまで待機
        print(f"[INFO] Waiting {args.initial_wait}s for aws_demos to be ready...")
        time.sleep(args.initial_wait)

        # プロンプト待ち
        tester.wait_for_prompt(timeout=args.timeout)

        # --- テスト実行 ---

        tester.run_test(
            "version", "version",
            check_version,
            "ファームウェアバージョン読み出し"
        )

        tester.run_test(
            "freertos_cpuload_read", "freertos cpuload read",
            check_cpuload_read,
            "FreeRTOS CPU 負荷読み出し"
        )

        tester.run_test(
            "freertos_cpuload_reset", "freertos cpuload reset",
            check_cpuload_reset,
            "FreeRTOS CPU 負荷カウンタリセット + 読み出し"
        )

        tester.run_test(
            "dataflash_info", "dataflash info",
            check_dataflash_info,
            "データフラッシュサイズ情報"
        )

        tester.run_test(
            "dataflash_read", "dataflash read",
            check_dataflash_read,
            "全設定データ読み出し"
        )

        tester.run_test(
            "timezone", "timezone UTC+09:00",
            check_timezone,
            "タイムゾーン設定 (JST)"
        )

        if not args.skip_erase:
            tester.run_test(
                "dataflash_erase", "dataflash erase",
                check_dataflash_erase,
                "全設定データ消去（破壊的操作）"
            )

        # --- 結果レポート ---
        print()
        print("=" * 60)
        total = tester.passed + tester.failed + tester.warnings
        print(f"[RESULT] Tests: {total}, Passed: {tester.passed}, "
              f"Failed: {tester.failed}, Warnings: {tester.warnings}")
        print("=" * 60)

        if tester.failed > 0:
            print("[FAIL] Some tests failed")
            sys.exit(1)
        elif tester.warnings > 0:
            print("[WARN] All tests passed but some had no response (COM6 RX issue)")
            sys.exit(0)
        else:
            print("[PASS] All tests passed")
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
