#!/usr/bin/env python3
"""
AWS IoT Core Device Provisioning Script
RX72N Envision Kit のデータフラッシュに AWS 認証情報を UART 経由で書き込む。

プロビジョニング対象:
  - MQTT broker endpoint (dataflash write aws mqttbrokerendpoint <url>)
  - IoT Thing name        (dataflash write aws iotthingname <name>)
  - Client certificate     (dataflash write aws clientcertificate → PEM streaming)
  - Client private key     (dataflash write aws clientprivatekey → PEM streaming)
  - Code signer certificate (dataflash write aws codesignercertificate → PEM streaming) [OTA用、オプション]

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
  MAC_ADDR          : dataflash に書き込む MAC アドレス (任意)
"""

import argparse
import os
import re
import sys
import time

# provisioning submodule (tools/provisioning) をパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'provisioning'))

import serial
from provisioning.security import mask_sensitive_output

# --- 定数 ---
DEFAULT_PORT = os.environ.get("COMMAND_PORT", "COM6")
DEFAULT_BAUD = int(os.environ.get("COMMAND_BAUD_RATE", "115200"))
DEFAULT_TIMEOUT = 15

PROMPT = "$ "
STORE_SUCCESS = "stored data into dataflash correctly."
STORE_FAIL = "could not store data into dataflash."
MAC_ADDRESS_PATTERN = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")


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
                # "\n$ " パターンで検出
                if b"\n$ " in buf or buf.endswith(b"\n$"):
                    elapsed = time.time() - start
                    print(f"[INFO] Prompt detected after {attempt} attempts ({elapsed:.1f}s)")
                    drain_input(ser)
                    return True
            else:
                time.sleep(0.05)
        if attempt <= 5 or attempt % 10 == 0:
            print(f"[INFO] Attempt {attempt}: no prompt yet...")
    return False


def drain_input(ser, settle_time=1.0):
    """受信バッファを完全にドレインする

    MCU のバースト送信が断続的に来る場合があるため、settle_time は
    十分な長さ (1.0s) を確保する。
    """
    ser.reset_input_buffer()
    deadline = time.time() + settle_time
    while time.time() < deadline:
        if ser.in_waiting > 0:
            ser.read(ser.in_waiting)
            deadline = time.time() + settle_time
        else:
            time.sleep(0.05)


def sync_uart(ser):
    """MCU との同期を確立する

    wait_for_prompt() のポーリングで MCU に送った複数の \\r\\n に対する
    応答をすべてドレインし、version コマンドで同期を確認する。
    """
    print("[INFO] Synchronizing with MCU...", flush=True)
    drain_input(ser, settle_time=3.0)
    ser.write(b"version\r\n")
    ser.flush()
    buf = b""
    start = time.time()
    while (time.time() - start) < 10:
        if ser.in_waiting > 0:
            buf += ser.read(ser.in_waiting)
            if b"RX72N Envision Kit" in buf and b"version" in buf:
                break
        else:
            time.sleep(0.05)
    drain_input(ser, settle_time=1.0)
    # 同期後にダミーコマンドで残留応答を完全排出する。
    # wait_for_prompt() のポーリングで蓄積した応答が version 応答に
    # 混じると、後続の最初のコマンド（STEP 1）でエコーバックしか
    # 返らない問題が起きるため、ここで確実にフラッシュする。
    ser.write(b"version\r\n")
    ser.flush()
    drain_input(ser, settle_time=2.0)
    print("[INFO] MCU synchronized.", flush=True)


def send_command(ser, cmd, timeout=15):
    """コマンドを送信し、結果出力完了を待つ

    エコーバック検出後、2つ目のプロンプト "\\n$ " を待つ。
    MCU はコマンド受理時にエコー + プロンプトを返し、処理完了後に
    結果 + プロンプトを返す。エコー検出位置以降に新しいプロンプトが
    現れたら結果出力完了と判断する。
    """
    drain_input(ser)
    ser.write((cmd + "\r\n").encode("utf-8"))
    ser.flush()

    buf = b""
    echo_seen = False
    echo_end_pos = 0
    start = time.time()
    while (time.time() - start) < timeout:
        n = ser.in_waiting
        if n > 0:
            buf += ser.read(n)
            if not echo_seen:
                decoded = buf.decode("utf-8", errors="replace")
                if cmd[:20] in decoded:
                    echo_seen = True
                    echo_end_pos = len(buf)
            if echo_seen:
                after_echo = buf[echo_end_pos:]
                if b"\n$ " in after_echo or after_echo.endswith(b"\n$"):
                    return buf.decode("utf-8", errors="replace")
        else:
            time.sleep(0.02)
    if buf:
        return buf.decode("utf-8", errors="replace")
    return None


def send_simple_value(ser, cmd, timeout=15):
    """単純な値コマンド (endpoint, thing name) を送信し成功を確認

    send_command() のバナー/プロンプト検出を経由せず、成功・失敗マーカーを
    直接待つ。MCU の応答タイミングが不安定でもマーカーさえ届けば判定できる。
    """
    print(f"[SEND] {cmd}")
    drain_input(ser)
    ser.write((cmd + "\r\n").encode("utf-8"))
    ser.flush()

    buf = b""
    start = time.time()
    while (time.time() - start) < timeout:
        if ser.in_waiting > 0:
            buf += ser.read(ser.in_waiting)
            decoded = buf.decode("utf-8", errors="replace")
            if STORE_SUCCESS in decoded:
                print(f"[OK] {STORE_SUCCESS}")
                drain_input(ser, settle_time=1.0)
                return True
            if STORE_FAIL in decoded:
                print(f"[FAIL] {STORE_FAIL}")
                drain_input(ser, settle_time=1.0)
                return False
        else:
            time.sleep(0.05)

    decoded = buf.decode("utf-8", errors="replace") if buf else ""
    print(f"[FAIL] Timeout waiting for store result")
    if decoded:
        print(f"[DEBUG] Received ({len(decoded)} chars): {decoded[-200:]}")
    return False


def send_pem_streaming(ser, cmd, pem_content, timeout=90):
    """PEM ストリーミング入力でデータフラッシュに書き込む

    1. コマンドを送信 (改行付き)
    2. PEM 内容を行単位で送信 (LF のみ、行間にディレイ)
    3. 成功メッセージを待つ

    MCU 側の serial_terminal_task は xQueueReceive で 1 文字ずつ受信し
    sci_buffer (2048B) に蓄積する。終端マーカー検出後に dataflash へ書き込む。
    送信速度が速すぎると SCI キューが溢れるため、行単位でペーシングする。
    """
    print(f"[SEND] {cmd}")
    print(f"[INFO] PEM size: {len(pem_content)} bytes")

    # 前コマンドの残留応答を確実に排出
    drain_input(ser, settle_time=1.0)

    # コマンド送信
    ser.write((cmd + "\r\n").encode("utf-8"))
    ser.flush()

    # MCU が PEM 受信モードに入るまで待つ。
    # コマンドのエコーバック + プロンプト "\n$ " が返るのを待つ。
    # プロンプト検出後、MCU は次の入力として PEM データを待っている。
    echo_buf = b""
    cmd_short = cmd[:20]
    echo_start = time.time()
    prompt_detected = False
    while (time.time() - echo_start) < 5.0:
        if ser.in_waiting > 0:
            echo_buf += ser.read(ser.in_waiting)
            decoded = echo_buf.decode("utf-8", errors="replace")
            # コマンドエコーとプロンプトの両方を確認
            if cmd_short in decoded and ("\n$ " in decoded or decoded.endswith("\n$")):
                prompt_detected = True
                # プロンプト後の短い安定待ち
                time.sleep(0.2)
                # 追加データがあれば読み捨て
                if ser.in_waiting > 0:
                    echo_buf += ser.read(ser.in_waiting)
                break
        else:
            time.sleep(0.05)
    if echo_buf:
        print(f"[INFO] Echo drained: {len(echo_buf)} bytes")
    if not prompt_detected:
        print(f"[WARN] Prompt not detected after command, proceeding anyway")

    # PEM 内容を正規化 (CRLF → LF)
    pem_normalized = pem_content.replace("\r\n", "\n")
    if not pem_normalized.endswith("\n"):
        pem_normalized += "\n"

    # 行単位で送信（MCU の SCI キュー溢れ防止）
    #
    # MCU の serial_terminal_task は xQueueReceive で 1 文字ずつ受信し
    # sci_buffer (2048B) に蓄積する。PEM 受信モード中はエコーバックなし。
    # 終端マーカー検出後に dataflash 書き込み → 結果メッセージを送信。
    #
    # 送信中はエコーバック読み捨てを行わない（OS の serial buffer に任せる）。
    # Linux の serial buffer は通常 4096 bytes で、PEM (最大 ~1700 bytes)
    # には十分。
    # split("\n") で行分割すると、末尾が "\n" の場合は最終要素が空文字列になる。
    # 旧ロジックでは最終要素に "\n" を付与しなかったため、PEM 末尾が
    # "-----END CERTIFICATE-----" で終わり最終 "\n" が欠落する可能性があった。
    # MCU の終端マーカー検出は "-----END CERTIFICATE-----\n" (LF 含む) なので、
    # 全行に "\n" を付与し、末尾空文字列はスキップする方式に変更する。
    lines = pem_normalized.split("\n")
    sent = 0
    for line in lines:
        if line == "" and sent > 0:
            # split による末尾空文字列 → スキップ（LF は前行で送信済み）
            continue
        data = line + "\n"
        ser.write(data.encode("utf-8"))
        ser.flush()
        sent += len(data)
        # 行間ディレイ: MCU の xQueueReceive 処理に余裕を持たせる
        time.sleep(0.1)

    print(f"[INFO] Sent {sent} characters")

    # 送信完了後、MCU が終端マーカーを検出し dataflash に書き込み、
    # 結果メッセージを送信するまで待つ。
    # OS buffer に溜まったデータ（もしあれば）も含めて全て読み取り、
    # STORE_SUCCESS / STORE_FAIL を探す。
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
            time.sleep(0.1)

    decoded = buf.decode("utf-8", errors="replace") if buf else ""
    print(f"[FAIL] Timeout waiting for store result")
    if decoded:
        print(f"[DEBUG] Received ({len(decoded)} chars): {decoded[-300:]}")
    return False


def normalize_mac_address(mac_address):
    """Normalize a MAC address into uppercase colon-separated form."""
    if not mac_address:
        return None

    if not MAC_ADDRESS_PATTERN.match(mac_address):
        raise ValueError(
            f"Invalid MAC address: {mac_address} "
            "(expected AA:BB:CC:DD:EE:FF or AA-BB-CC-DD-EE-FF)"
        )

    return mac_address.replace("-", ":").upper()


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
    parser.add_argument("--device-id",
                        help="Device ID (loads config from device_config.json)")
    parser.add_argument("--endpoint", default=None,
                        help="AWS IoT MQTT broker endpoint")
    parser.add_argument("--thing-name", default=None,
                        help="AWS IoT Thing name")
    parser.add_argument("--cert", default=None,
                        help="Path to client certificate PEM file")
    parser.add_argument("--key", default=None,
                        help="Path to client private key PEM file")
    parser.add_argument("--codesigner-cert", default=None,
                        help="Path to code signer certificate PEM file (OTA)")
    parser.add_argument("--mac-address", default=None,
                        help="Ethernet MAC address to store in dataflash")
    args = parser.parse_args()

    # --device-id が指定された場合、device_config.json から設定を解決
    if args.device_id:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from device_config_loader import (
            load_device_config, get_cert_env_var_name, get_key_env_var_name
        )
        device = load_device_config(args.device_id)
        print(f"[INFO] Loaded config for device: {args.device_id}")

        # CLI 引数が未指定ならコンフィグの値を使用
        if args.port == DEFAULT_PORT:
            args.port = device.get("command_port") or os.environ.get("COMMAND_PORT") or DEFAULT_PORT
        if args.baud == DEFAULT_BAUD:
            args.baud = int(device.get("command_baud") or os.environ.get("COMMAND_BAUD_RATE") or DEFAULT_BAUD)
        if not args.endpoint:
            args.endpoint = device["aws_endpoint"]
        if not args.thing_name:
            args.thing_name = device["thing_name"]
        if not args.cert:
            cert_var = get_cert_env_var_name(args.device_id)
            args.cert = os.environ.get(cert_var)
            if not args.cert:
                print(f"[ERROR] Environment variable {cert_var} not set")
                sys.exit(1)
            print(f"[INFO] Certificate path from ${cert_var}")
        if not args.key:
            key_var = get_key_env_var_name(args.device_id)
            args.key = os.environ.get(key_var)
            if not args.key:
                print(f"[ERROR] Environment variable {key_var} not set")
                sys.exit(1)
            print(f"[INFO] Private key path from ${key_var}")
        # コード署名証明書 (OTA 用、オプション)
        if not args.codesigner_cert and device.get("codesigner_cert"):
            # device_config.json にリポジトリ相対パスが定義されている場合
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            candidate = os.path.join(repo_root, device["codesigner_cert"])
            if os.path.isfile(candidate):
                args.codesigner_cert = candidate
                print(f"[INFO] Code signer cert from device_config: {candidate}")
        if not args.mac_address:
            args.mac_address = device.get("mac_address") or os.environ.get("MAC_ADDR")

    if args.mac_address:
        try:
            args.mac_address = normalize_mac_address(args.mac_address)
        except ValueError as exc:
            print(f"[ERROR] {exc}")
            sys.exit(1)

    # --device-id なしの場合、必須引数をチェック
    if not args.endpoint:
        parser.error("--endpoint is required (or use --device-id)")
    if not args.thing_name:
        parser.error("--thing-name is required (or use --device-id)")
    if not args.cert:
        parser.error("--cert is required (or use --device-id)")
    if not args.key:
        parser.error("--key is required (or use --device-id)")

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
    codesigner_pem = None
    if args.codesigner_cert:
        if not os.path.isfile(args.codesigner_cert):
            print(f"[ERROR] Code signer certificate file not found: {args.codesigner_cert}")
            sys.exit(1)
        with open(args.codesigner_cert, "r") as f:
            codesigner_pem = f.read()
        if "-----BEGIN CERTIFICATE-----" not in codesigner_pem:
            print("[ERROR] Code signer certificate does not contain PEM header")
            sys.exit(1)

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

    total_steps = 4
    if args.mac_address:
        total_steps += 1
    if codesigner_pem:
        total_steps += 1
    print("=" * 60)
    print("[INFO] AWS IoT Core Device Provisioning")
    print(f"[INFO]   Port      : {args.port} @ {args.baud}bps")
    print(f"[INFO]   Endpoint  : {args.endpoint}")
    print(f"[INFO]   Thing Name: {args.thing_name}")
    if args.mac_address:
        print(f"[INFO]   MAC       : {args.mac_address}")
    print(f"[INFO]   Cert      : {args.cert} ({len(cert_pem)} bytes)")
    print(f"[INFO]   Key       : {args.key} ({len(key_pem)} bytes)")
    if codesigner_pem:
        print(f"[INFO]   CodeSigner: {args.codesigner_cert} ({len(codesigner_pem)} bytes)")
    print(f"[INFO]   Steps     : {total_steps}")
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

        # ポーリングで蓄積した MCU 応答をすべてドレインし同期確立
        sync_uart(ser)

        # --- プロビジョニング実行 ---

        print()
        print(f"[STEP 1/{total_steps}] Setting MQTT broker endpoint")
        results["endpoint"] = send_simple_value(
            ser, f"dataflash write aws mqttbrokerendpoint {args.endpoint}", args.timeout
        )

        print()
        print(f"[STEP 2/{total_steps}] Setting IoT Thing name")
        results["thing_name"] = send_simple_value(
            ser, f"dataflash write aws iotthingname {args.thing_name}", args.timeout
        )

        step_index = 3

        if args.mac_address:
            print()
            print(f"[STEP {step_index}/{total_steps}] Setting Ethernet MAC address")
            results["mac_address"] = send_simple_value(
                ser, f"dataflash write aws macaddress {args.mac_address}", args.timeout
            )
            step_index += 1

        print()
        print(f"[STEP {step_index}/{total_steps}] Writing client certificate")
        results["certificate"] = send_pem_streaming(
            ser, "dataflash write aws clientcertificate", cert_pem
        )
        step_index += 1

        print()
        print(f"[STEP {step_index}/{total_steps}] Writing client private key")
        results["private_key"] = send_pem_streaming(
            ser, "dataflash write aws clientprivatekey", key_pem
        )
        step_index += 1

        # Step 5 (OTA): コード署名証明書
        if codesigner_pem:
            print()
            print(f"[STEP {step_index}/{total_steps}] Writing code signer certificate (OTA)")
            results["codesigner_cert"] = send_pem_streaming(
                ser, "dataflash write aws codesignercertificate",
                codesigner_pem
            )

        # --- 確認: dataflash read ---
        print()
        print("[VERIFY] Reading dataflash contents")
        drain_input(ser, settle_time=2.0)

        response = send_command(ser, "dataflash read", timeout=10)
        if response:
            # PRIVATE KEY の本体をマスクしてから表示
            masked_response = mask_sensitive_output(response)
            lines = masked_response.replace("\r", "").split("\n")
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
        print(f"  python test_aws_connectivity.py --device-id {args.device_id}" if args.device_id else "  python test_aws_connectivity.py --log-port <LOG_PORT> --cmd-port <CMD_PORT>")
        sys.exit(0)
    else:
        print("[FAIL] Some provisioning steps failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
