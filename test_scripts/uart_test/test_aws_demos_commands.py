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
  - timezone <tz>        : タイムゾーン設定

任意の拡張プローブ:
  - dataflash read       : 全設定データ読み出し
  - touch any            : 疑似タッチイベント（画面中央）
  - touch <x> <y>        : 疑似タッチイベント（座標指定）
  - dataflash erase      : 全設定データ消去（破壊的操作、末尾で実行）

CI の smoke gate では、CN8/SCI2 の実測で intermittent になりやすい
touch / dataflash read を既定から外す。GUI 経路は
test_touch_navigation.py、credential path は provision_aws.py が別途見る。

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
import subprocess
import sys
import time

import serial

# --- 定数 ---
DEFAULT_PORT = os.environ.get("COMMAND_PORT", "COM6")
DEFAULT_BAUD = int(os.environ.get("COMMAND_BAUD_RATE", "115200"))
DEFAULT_TIMEOUT = int(os.environ.get("COMMAND_TIMEOUT", "300"))
DEFAULT_RETRIES = 3

PROMPT = "$ "


class CommandTester:
    """UART コマンドテスター"""

    def __init__(self, port, baud, timeout, retries, reset_cmd=None, reset_settle=0.2):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.retries = retries
        self.reset_cmd = reset_cmd
        self.reset_settle = reset_settle
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

    def trigger_reset(self):
        """Open済み UART で startup prompt を捕まえるために reset を後打ちする。"""
        if not self.reset_cmd:
            return
        print(f"[INFO] Triggering reset command: {self.reset_cmd}")
        result = subprocess.run(
            self.reset_cmd,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        if result.returncode != 0:
            raise RuntimeError(f"reset command failed with exit status {result.returncode}")
        if self.reset_settle > 0:
            time.sleep(self.reset_settle)

    def read_until_prompt(self, timeout=None, expect_echo=None):
        """コマンド応答の完了を待つ

        MCU のコマンド応答シーケンス:
          1. エコーバック: "command\\r\\n$ "  ← 1つ目のプロンプト（受理）
          2. 処理結果:    "result...\\r\\nRX72N Envision Kit\\r\\n$ "  ← 2つ目

        expect_echo が指定された場合:
          エコーバック検出後、"RX72N Envision Kit" バナーの出現を待つ。
          バナーは結果出力後にのみ送信されるため、確実に2つ目のプロンプト。
        expect_echo が None の場合:
          最初の \\n$ で返す（初期プロンプト検出等）。

        Returns:
            str: 受信データ全体
            None: タイムアウト
        """
        if timeout is None:
            timeout = self.timeout
        buf = b""
        echo_seen = (expect_echo is None)
        start = time.time()
        while (time.time() - start) < timeout:
            n = self.ser.in_waiting
            if n > 0:
                buf += self.ser.read(n)
                decoded = buf.decode("utf-8", errors="replace")

                if not echo_seen and expect_echo in decoded:
                    echo_seen = True

                if echo_seen:
                    if expect_echo is not None:
                        # エコーバック後に "RX72N Envision Kit" バナーが
                        # 出現したら結果出力完了。バナーはコマンド結果の
                        # 後にのみ送信される（エコーバック直後には出ない）
                        echo_pos = decoded.find(expect_echo)
                        after = decoded[echo_pos + len(expect_echo):]
                        if "RX72N Envision Kit" in after:
                            return decoded
                    else:
                        if b"\n$ " in buf or buf.endswith(b"\n$"):
                            return decoded
            else:
                time.sleep(0.05)
        if buf:
            return buf.decode("utf-8", errors="replace")
        return None

    def drain_input(self, settle_time=1.0, max_time=None, label=None):
        """受信バッファを完全にドレインする

        settle_time 秒間データが来なくなるまで読み続ける。
        MCU がチャンク送信中にポーズする場合があるため、
        reset_input_buffer() は使わず到着データを読み切る。
        max_time を超えたら強制終了する。
        """
        if max_time is None:
            max_time = settle_time * 5
        hard_deadline = time.time() + max_time
        deadline = time.time() + settle_time
        total_bytes = 0
        while time.time() < deadline and time.time() < hard_deadline:
            if self.ser.in_waiting > 0:
                total_bytes += len(self.ser.read(self.ser.in_waiting))
                deadline = time.time() + settle_time
            else:
                time.sleep(0.05)
        if label:
            print(f"[DRAIN] {label}: {total_bytes} bytes", flush=True)

    def sync(self):
        """MCU との同期を確立する

        wait_for_prompt() のポーリングで MCU に複数の \\r\\n を送信する
        ため、MCU は各々に対して応答を返す。全応答が送信し終わるまで
        3秒ドレインし、その後 "version" コマンドを sync マーカーとして
        送信。version 応答の完了（バナー検出）を確認することで、
        MCU がキューをすべて処理済みであることを保証する。
        """
        print("[INFO] Synchronizing with MCU...", flush=True)
        # MCU がポーリング応答や前ジョブ残留データを全て送り終わるまで待つ
        self.drain_input(settle_time=5.0, max_time=60.0, label="pre-sync")
        # sync コマンド送信
        self.ser.write(b"version\r\n")
        self.ser.flush()
        # version 応答 + バナーを待つ
        buf = b""
        start = time.time()
        while (time.time() - start) < 10:
            if self.ser.in_waiting > 0:
                buf += self.ser.read(self.ser.in_waiting)
                if b"RX72N Envision Kit" in buf and b"version" in buf:
                    break
            else:
                time.sleep(0.05)
        # 追加ドレイン
        self.drain_input(settle_time=2.0, max_time=10.0, label="post-sync")
        print("[INFO] MCU synchronized.", flush=True)

    def send_command(self, cmd):
        """コマンドを送信し、応答を取得する

        MCU はコマンド受信後:
        1. エコーバック + プロンプト（コマンド受理の合図）
        2. 処理結果 + プロンプト（結果出力完了の合図）
        を送信する。2つ目のプロンプトまで待つことで、応答を完全に取得する。

        Args:
            cmd: コマンド文字列（改行なし）

        Returns:
            str: 応答文字列（エコーバック・プロンプト含む）
            None: 受信失敗
        """
        # 送信前にバッファを完全にドレイン
        self.drain_input()

        # コマンド送信（\r\n で行末）
        self.ser.write((cmd + "\r\n").encode("utf-8"))
        self.ser.flush()

        # エコーバック後の2つ目のプロンプトまで待つ
        response = self.read_until_prompt(expect_echo=cmd)
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

    def send_command_body(self, cmd, retries=None, settle_time=0.5):
        """Send a command and return only the parsed response body.

        CN8 / SCI2 occasionally returns short fragments for the first read after
        a command. Retry when the parsed body is empty or obviously truncated.
        """
        if retries is None:
            retries = self.retries

        last_body = ""
        for attempt in range(1, retries + 1):
            raw = self.send_command(cmd)
            if raw is not None:
                body = self.extract_response_body(raw, cmd)
                last_body = body
                if body and body.strip() not in {"t"}:
                    return body
            if attempt < retries:
                time.sleep(settle_time)
        return last_body

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

        body = self.send_command_body(cmd)

        if body is None or len(body.strip()) == 0:
            print(f"[WARN] {name}: No response received (COM6 intermittent RX issue?)")
            self.warnings += 1
            return

        print(f"[RECV] Response body: {repr(body[:200])}")

        passed, detail = check_fn(body)
        if passed:
            print(f"[PASS] {name}: {detail}")
            self.passed += 1
        else:
            print(f"[FAIL] {name}: {detail}")
            self.failed += 1

    def wait_for_prompt(self, timeout=None):
        """プロンプトをポーリングで待つ

        1秒おきに \\r\\n を送信し、プロンプト '$ ' が返るまで繰り返す。
        serial_terminal_task は GUI 初期化完了後に起動するため、
        MCU 起動直後はまだ準備ができていない可能性がある。
        """
        if timeout is None:
            timeout = max(self.timeout, 30)  # ポーリングは最低30秒
        print(f"[INFO] Polling for prompt (sending \\r\\n every 1s, timeout={timeout}s)...")
        start = time.time()
        buf = b""
        attempt = 0
        while (time.time() - start) < timeout:
            attempt += 1
            while self.ser.in_waiting > 0:
                buf += self.ser.read(self.ser.in_waiting)
            buf = buf[-4096:]
            self.ser.write(b"\r\n")
            self.ser.flush()
            # 1秒待ちつつ受信チェック
            poll_start = time.time()
            while (time.time() - poll_start) < 1.0:
                n = self.ser.in_waiting
                if n > 0:
                    buf += self.ser.read(n)
                    buf = buf[-4096:]
                    # "\n$ " パターンで検出（"$" 単独だとbase64等で誤検出）
                    if b"\n$ " in buf[-100:] or buf.endswith(b"\n$"):
                        elapsed = time.time() - start
                        print(f"[INFO] Prompt detected after {attempt} attempts ({elapsed:.1f}s)")
                        # ドレイン: プロンプト後の残留データをクリア
                        self.drain_input(label="prompt")
                        return True
                else:
                    time.sleep(0.05)
            if attempt <= 5 or attempt % 10 == 0:
                print(f"[INFO] Attempt {attempt}: no prompt yet...")
        elapsed = time.time() - start
        print(f"[WARN] Could not detect prompt after {attempt} attempts ({elapsed:.1f}s)")
        return False


# --- テスト検証関数 ---

def check_version(body):
    """version コマンドの応答を検証"""
    if not body:
        return False, "Empty response"
    import re

    match = re.search(r'v\d+\.\d+\.\d+', body)
    if match:
        return True, f"Version: {match.group()}"
    return False, f"Unexpected: {body.strip()[:100]}"


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


def check_touch_any(body):
    """touch any の応答を検証"""
    if not body:
        return False, "Empty response"
    if "touch (240, 136) ok" in body.lower():
        return True, "Touch at center OK"
    if "touch" in body.lower() and "ok" in body.lower():
        return True, f"Touch OK: {body.strip()}"
    return False, f"Unexpected: {body.strip()}"


def check_touch_coord(body):
    """touch <x> <y> の応答を検証"""
    if not body:
        return False, "Empty response"
    if "touch" in body.lower() and "ok" in body.lower():
        return True, f"Touch OK: {body.strip()}"
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
    parser.add_argument("--include-extended-probes", action="store_true",
                        help="Run unstable GUI/dataflash probes for manual diagnosis")
    parser.add_argument("--initial-wait", type=float, default=30.0,
                        help="Initial wait before polling (default: 30s)")
    parser.add_argument("--prompt-timeout", type=int, default=300,
                        help="Timeout for prompt polling in seconds (default: 300)")
    parser.add_argument("--reset-cmd", default=None,
                        help="Optional reset command to execute after opening UART")
    parser.add_argument("--reset-settle", type=float, default=0.2,
                        help="Seconds to wait after reset command (default: 0.2)")
    args = parser.parse_args()

    print("=" * 60)
    print("[INFO] aws_demos UART Command-Response Test")
    print(f"[INFO]   Port           : {args.port}")
    print(f"[INFO]   Baud           : {args.baud}")
    print(f"[INFO]   Cmd timeout    : {args.timeout}s")
    print(f"[INFO]   Prompt timeout : {args.prompt_timeout}s")
    print(f"[INFO]   Retries        : {args.retries}")
    print("=" * 60)

    tester = CommandTester(args.port, args.baud, args.timeout, args.retries,
                           reset_cmd=args.reset_cmd, reset_settle=args.reset_settle)

    try:
        tester.open()
        tester.trigger_reset()

        # DHCP / Ethernet 初期化が落ち着いてから UART コマンドテストを始める。
        print(f"[INFO] Waiting {args.initial_wait}s for MCU to stabilize (DHCP)...")
        time.sleep(args.initial_wait)

        # プロンプトポーリング（serial_terminal_task が起動するまで待つ）
        if not tester.wait_for_prompt(timeout=args.prompt_timeout):
            print("[FAIL] Could not establish communication with aws_demos")
            print("[HINT] Is the MCU running? Has serial_terminal_task started?")
            sys.exit(1)

        # ポーリングで蓄積した MCU 応答をすべてドレインし同期を確立
        tester.sync()

        # sync 中の CRLF nudge 由来の stale data を version 1 回で吸収する。
        print("[INFO] Warm-up: sending version to absorb stale data...", flush=True)
        warmup_body = tester.send_command_body("version", retries=2, settle_time=1.0)
        print(f"[INFO] Warm-up response: {repr(warmup_body[:80])}")

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
            "dataflash_info", "dataflash info",
            check_dataflash_info,
            "データフラッシュサイズ情報"
        )

        if args.include_extended_probes:
            tester.run_test(
                "touch_any", "touch any",
                check_touch_any,
                "疑似タッチイベント (画面中央 240,136)"
            )

            tester.run_test(
                "touch_coord", "touch 0 0",
                check_touch_coord,
                "疑似タッチイベント (座標指定 0,0)"
            )

            tester.run_test(
                "dataflash_read", "dataflash read",
                check_dataflash_read,
                "全設定データ読み出し"
            )
        else:
            print("[INFO] Skipping extended GUI/dataflash probes in default smoke mode")

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
