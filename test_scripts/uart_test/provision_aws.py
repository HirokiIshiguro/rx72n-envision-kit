#!/usr/bin/env python3
"""
AWS IoT Core Device Provisioning Script
RX72N Envision Kit のデータフラッシュに AWS 認証情報を UART 経由で書き込む。

プロビジョニング対象:
  - MQTT broker endpoint (dataflash write aws mqttbrokerendpoint <url>)
  - IoT Thing name        (dataflash write aws iotthingname <name>)
  - Client certificate     (dataflash write aws clientcertificate → PEM streaming)
  - Client private key     (dataflash write aws clientprivatekey → PEM streaming)

PEM ストリーミングプロトコル:
  ファームウェア (serial_terminal_task.c) は PEM コマンド受信後、
  文字単位で xQueueReceive で受信し sci_buffer (2048 bytes) に蓄積する。
  終了マーカー検出で保存:
    - 秘密鍵: "-----END RSA PRIVATE KEY-----\\n"
    - 証明書: "-----END CERTIFICATE-----\\n"
  重要: ラインエンディングは LF (\\n) のみ。CRLF だと終了マーカー不一致。

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
DEFAULT_TIMEOUT = 15

PROMPT = "$ "
STORE_SUCCESS = "stored data into dataflash correctly."
STORE_FAIL = "could not store data into dataflash."


def wait_for_prompt(ser, timeout=30):
    """プロンプトをポーリングで待つ"""
    print(f"[INFO] Polling for prompt (timeout={timeout}s)...")
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
            chunk = ser.read(n)
            buf += chunk
            decoded = buf.decode("utf-8", errors="replace")
            if "$ " in decoded.split("\n")[-1] or decoded.rstrip().endswith("$"):
                return decoded
        else:
            time.sleep(0.05)
    if buf:
        return buf.decode("utf-8", errors="replace")
    return None


def send_simple_value(ser, cmd, timeout=10):
    """単純な値コマンド (endpoint, thing name) を送信し成功を確認"""
    print(f"[SEND] {cmd}")
    response = send_command(ser, cmd, timeout)
    if response is None:
        print(f"[FAIL] No response")
        return False

    if STORE_SUCCESS in response:
        print(f"[OK] {STORE_SUCCESS}")
        return True
    elif STORE_FAIL in response:
        print(f"[FAIL] {STORE_FAIL}")
        return False
    else:
        print(f"[WARN] Unexpected response: {response[:200]}")
        return STORE_SUCCESS in response


def send_pem_streaming(ser, cmd, pem_content, timeout=30):
    """PEM ストリーミング入力でデータフラッシュに書き込む

    1. コマンドを送信 (改行付き)
    2. PEM 内容を 1 文字ずつ送信 (LF のみ)
    3. 成功メッセージを待つ
    """
    print(f"[SEND] {cmd}")
    print(f"[INFO] PEM size: {len(pem_content)} bytes")

    # コマンド送信
    ser.reset_input_buffer()
    time.sleep(0.1)
    ser.write((cmd + "\r\n").encode("utf-8"))
    ser.flush()
    time.sleep(0.5)  # コマンド処理待ち

    # エコーバックを読み捨て
    if ser.in_waiting > 0:
        ser.read(ser.in_waiting)

    # PEM 内容を正規化 (CRLF → LF)
    pem_normalized = pem_content.replace("\r\n", "\n")
    if not pem_normalized.endswith("\n"):
        pem_normalized += "\n"

    # 1 文字ずつ送信
    sent = 0
    for ch in pem_normalized:
        ser.write(ch.encode("utf-8"))
        ser.flush()
        sent += 1
        # エコーバック読み捨て（バッファ溢れ防止）
        if ser.in_waiting > 0:
            ser.read(ser.in_waiting)
        # 改行ごとに小さなディレイ
        if ch == "\n":
            time.sleep(0.01)

    print(f"[INFO] Sent {sent} characters")

    # 成功/失敗メッセージを待つ
    buf = b""
    start = time.time()
    while (time.time() - start) < timeout:
        n = ser.in_waiting
        if n > 0:
            buf += ser.read(n)
            decoded = buf.decode("utf-8", errors="replace")
            if STORE_SUCCESS in decoded:
                print(f"[OK] {STORE_SUCCESS}")
                return True
            if STORE_FAIL in decoded:
                print(f"[FAIL] {STORE_FAIL}")
                return False
        else:
            time.sleep(0.05)

    decoded = buf.decode("utf-8", errors="replace") if buf else ""
    print(f"[FAIL] Timeout waiting for store result")
    if decoded:
        print(f"[DEBUG] Received: {decoded[:300]}")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="AWS IoT Core device provisioning via UART"
    )
    parser.add_argument("--port", default=DEFAULT_PORT,
                        help=f"Serial port (default: {DEFAULT_PORT})")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD,
                        help=f"Baud rate (default: {DEFAULT_BAUD})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Command timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--endpoint", required=True,
                        help="AWS IoT MQTT broker endpoint")
    parser.add_argument("--thing-name", required=True,
                        help="AWS IoT Thing name")
    parser.add_argument("--cert", required=True,
                        help="Path to client certificate PEM file")
    parser.add_argument("--key", required=True,
                        help="Path to client private key PEM file")
    args = parser.parse_args()

    # ファイル存在チェック
    for path, desc in [(args.cert, "Certificate"), (args.key, "Private key")]:
        if not os.path.isfile(path):
            print(f"[ERROR] {desc} file not found: {path}")
            sys.exit(1)

    # PEM ファイル読み込み
    with open(args.cert, "r") as f:
        cert_pem = f.read()
    with open(args.key, "r") as f:
        key_pem = f.read()

    # PEM 内容の基本検証
    if "-----BEGIN CERTIFICATE-----" not in cert_pem:
        print("[ERROR] Certificate file does not contain PEM header")
        sys.exit(1)
    if "-----BEGIN RSA PRIVATE KEY-----" not in key_pem:
        # EC キーの場合もサポート（ただしファームウェアは RSA のみ対応）
        if "-----BEGIN EC PRIVATE KEY-----" in key_pem:
            print("[ERROR] EC private key detected. Firmware only supports RSA private keys.")
            print("[HINT] When creating IoT certificates, use RSA key type.")
            sys.exit(1)
        print("[ERROR] Private key file does not contain RSA PEM header")
        sys.exit(1)

    print("=" * 60)
    print("[INFO] AWS IoT Core Device Provisioning")
    print(f"[INFO]   Port      : {args.port} @ {args.baud}bps")
    print(f"[INFO]   Endpoint  : {args.endpoint}")
    print(f"[INFO]   Thing Name: {args.thing_name}")
    print(f"[INFO]   Cert      : {args.cert} ({len(cert_pem)} bytes)")
    print(f"[INFO]   Key       : {args.key} ({len(key_pem)} bytes)")
    print("=" * 60)

    results = {}

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0)
        time.sleep(0.1)
        ser.reset_input_buffer()
        print(f"[INFO] Opened {args.port} at {args.baud} bps")

        # プロンプト待ち
        if not wait_for_prompt(ser, timeout=30):
            print("[FAIL] Could not detect prompt")
            sys.exit(1)

        # --- プロビジョニング実行 ---

        print()
        print("[STEP 1/4] Setting MQTT broker endpoint")
        results["endpoint"] = send_simple_value(
            ser, f"dataflash write aws mqttbrokerendpoint {args.endpoint}", args.timeout
        )

        # プロンプト復帰待ち
        time.sleep(0.5)
        ser.reset_input_buffer()
        ser.write(b"\r\n")
        ser.flush()
        time.sleep(0.5)
        if ser.in_waiting > 0:
            ser.read(ser.in_waiting)

        print()
        print("[STEP 2/4] Setting IoT Thing name")
        results["thing_name"] = send_simple_value(
            ser, f"dataflash write aws iotthingname {args.thing_name}", args.timeout
        )

        time.sleep(0.5)
        ser.reset_input_buffer()
        ser.write(b"\r\n")
        ser.flush()
        time.sleep(0.5)
        if ser.in_waiting > 0:
            ser.read(ser.in_waiting)

        print()
        print("[STEP 3/4] Writing client certificate")
        results["certificate"] = send_pem_streaming(
            ser, "dataflash write aws clientcertificate", cert_pem, timeout=30
        )

        time.sleep(1.0)
        ser.reset_input_buffer()
        ser.write(b"\r\n")
        ser.flush()
        time.sleep(0.5)
        if ser.in_waiting > 0:
            ser.read(ser.in_waiting)

        print()
        print("[STEP 4/4] Writing client private key")
        results["private_key"] = send_pem_streaming(
            ser, "dataflash write aws clientprivatekey", key_pem, timeout=30
        )

        # --- 確認: dataflash read ---
        print()
        print("[VERIFY] Reading dataflash contents")
        time.sleep(1.0)
        ser.reset_input_buffer()
        ser.write(b"\r\n")
        ser.flush()
        time.sleep(0.5)
        if ser.in_waiting > 0:
            ser.read(ser.in_waiting)

        response = send_command(ser, "dataflash read", timeout=10)
        if response:
            lines = response.replace("\r", "").split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped and stripped != "$" and "dataflash read" not in stripped:
                    if "RX72N Envision Kit" not in stripped:
                        print(f"  {stripped}")

        ser.close()
        print(f"[INFO] Closed {args.port}")

    except serial.SerialException as e:
        print(f"[ERROR] Serial port error: {e}")
        sys.exit(1)

    # --- 結果レポート ---
    print()
    print("=" * 60)
    all_ok = all(results.values())
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
    print("=" * 60)

    if all_ok:
        print("[PASS] All provisioning steps completed successfully")
        print()
        print("Next: Reset the device to connect to AWS IoT Core")
        print("  python test_aws_connectivity.py --log-port COM7 --cmd-port COM6")
        sys.exit(0)
    else:
        print("[FAIL] Some provisioning steps failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
