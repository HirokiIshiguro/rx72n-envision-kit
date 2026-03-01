#!/usr/bin/env python3
"""
AWS IoT Core Provisioning Script for aws_demos
RX72N Envision Kit の aws_demos に AWS 認証情報を UART 経由でプロビジョニングする

aws_demos のコマンドターミナル (SCI2, COM6, 115200bps) を通じて、
データフラッシュに以下の AWS 認証情報を書き込む:
  1. MQTT Broker Endpoint
  2. IoT Thing Name
  3. Client Certificate (PEM)
  4. Client Private Key (PEM)
  5. Code Signer Certificate (PEM) — OTA 用

PEM 入力モード:
  "dataflash write aws clientprivatekey" 等のコマンド実行後、
  MCU は PEM 入力待ち状態に遷移する。
  PEM テキスト全体を送信し、"-----END ..." 行を検出すると自動的に保存される。
  "exit" / "quit" でキャンセル可能。

使用例:
  python provision_aws.py \\
    --endpoint abcdefg1234567-ats.iot.ap-northeast-1.amazonaws.com \\
    --thing-name RX72N-EnvisionKit-01 \\
    --cert path/to/device-cert.pem \\
    --key path/to/private-key.pem \\
    [--code-signer-cert path/to/code-signer-cert.pem]

環境変数:
  COMMAND_PORT      : シリアルポート (デフォルト: COM6)
  COMMAND_BAUD_RATE : ボーレート     (デフォルト: 115200)
"""

import argparse
import os
import sys
import time

import serial

DEFAULT_PORT = os.environ.get("COMMAND_PORT", "COM6")
DEFAULT_BAUD = int(os.environ.get("COMMAND_BAUD_RATE", "115200"))
PROMPT = "$ "
STORE_SUCCESS = "stored data into dataflash correctly"
STORE_FAIL = "could not store data into dataflash"


class Provisioner:
    """AWS プロビジョニング実行クラス"""

    def __init__(self, port, baud, timeout=15):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None

    def open(self):
        self.ser = serial.Serial(self.port, self.baud, timeout=0)
        time.sleep(0.1)
        self.ser.reset_input_buffer()

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def read_until(self, patterns, timeout=None):
        """指定パターンのいずれかが現れるまで読み取る

        Returns:
            (data, matched_pattern): 受信データと一致したパターン
            (data, None): タイムアウト
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
                decoded = buf.decode("utf-8", errors="replace")
                for pat in patterns:
                    if pat in decoded:
                        return decoded, pat
            else:
                time.sleep(0.05)
        decoded = buf.decode("utf-8", errors="replace") if buf else ""
        return decoded, None

    def send_command(self, cmd):
        """コマンド送信 + プロンプト待ち"""
        self.ser.reset_input_buffer()
        time.sleep(0.1)
        self.ser.write((cmd + "\r\n").encode("utf-8"))
        self.ser.flush()
        data, _ = self.read_until([PROMPT], timeout=self.timeout)
        return data

    def send_simple_value(self, label, cmd):
        """単純な値書き込みコマンド（endpoint, thing name 等）"""
        print(f"[PROV] {label}: sending '{cmd}'")
        response = self.send_command(cmd)
        if response and STORE_SUCCESS in response.lower():
            print(f"[PASS] {label}: stored successfully")
            return True
        elif response and STORE_FAIL in response.lower():
            print(f"[FAIL] {label}: store failed")
            return False
        else:
            print(f"[WARN] {label}: unexpected response: {repr(response[:200])}")
            return False

    def send_pem(self, label, cmd, pem_path):
        """PEM ファイル書き込みコマンド

        コマンド送信後、MCU が PEM 入力待ちに遷移。
        PEM ファイルの内容を1行ずつ送信する。
        """
        print(f"[PROV] {label}: sending PEM from {pem_path}")

        with open(pem_path, "r") as f:
            pem_data = f.read()

        if not pem_data.strip():
            print(f"[FAIL] {label}: PEM file is empty")
            return False

        # コマンド送信（PEM 入力モードに遷移）
        self.ser.reset_input_buffer()
        time.sleep(0.1)
        self.ser.write((cmd + "\r\n").encode("utf-8"))
        self.ser.flush()
        time.sleep(0.5)

        # PEM テキストを1行ずつ送信
        # MCU はエコーバックするため、各行送信後に少し待つ
        for line in pem_data.split("\n"):
            if line.strip():
                self.ser.write((line.strip() + "\n").encode("utf-8"))
                self.ser.flush()
                time.sleep(0.05)  # 1行ごとに少し待つ（SCI バッファ溢れ防止）

        # 保存完了待ち
        data, matched = self.read_until(
            [STORE_SUCCESS, STORE_FAIL, PROMPT],
            timeout=self.timeout
        )

        if matched and STORE_SUCCESS in (matched or ""):
            print(f"[PASS] {label}: stored successfully")
            return True
        elif data and STORE_SUCCESS in data.lower():
            print(f"[PASS] {label}: stored successfully")
            return True
        elif data and STORE_FAIL in data.lower():
            print(f"[FAIL] {label}: store failed")
            return False
        else:
            print(f"[WARN] {label}: uncertain result: {repr(data[:200])}")
            return False

    def verify_dataflash(self):
        """dataflash read でプロビジョニング結果を確認"""
        print()
        print("[PROV] Verifying with 'dataflash read'...")
        response = self.send_command("dataflash read")
        if response:
            print("[INFO] Dataflash contents:")
            for line in response.replace("\r", "").split("\n"):
                line = line.strip()
                if line and line != "$" and "RX72N Envision Kit" not in line:
                    print(f"  {line}")
        return response


def main():
    parser = argparse.ArgumentParser(
        description="Provision AWS IoT credentials to RX72N Envision Kit"
    )
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--endpoint", required=True,
                        help="MQTT Broker Endpoint (e.g., xxx-ats.iot.region.amazonaws.com)")
    parser.add_argument("--thing-name", required=True,
                        help="IoT Thing Name")
    parser.add_argument("--cert", required=True,
                        help="Path to client certificate PEM file")
    parser.add_argument("--key", required=True,
                        help="Path to client private key PEM file")
    parser.add_argument("--code-signer-cert",
                        help="Path to code signer certificate PEM file (for OTA)")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--skip-verify", action="store_true",
                        help="Skip dataflash read verification")
    args = parser.parse_args()

    # 入力ファイルの存在確認
    for path, name in [(args.cert, "cert"), (args.key, "key")]:
        if not os.path.isfile(path):
            print(f"[ERROR] File not found: {path} ({name})")
            sys.exit(1)
    if args.code_signer_cert and not os.path.isfile(args.code_signer_cert):
        print(f"[ERROR] File not found: {args.code_signer_cert} (code-signer-cert)")
        sys.exit(1)

    print("=" * 60)
    print("[INFO] AWS IoT Core Provisioning")
    print(f"[INFO]   Port     : {args.port} @ {args.baud}bps")
    print(f"[INFO]   Endpoint : {args.endpoint}")
    print(f"[INFO]   Thing    : {args.thing_name}")
    print(f"[INFO]   Cert     : {args.cert}")
    print(f"[INFO]   Key      : {args.key}")
    if args.code_signer_cert:
        print(f"[INFO]   CodeSign : {args.code_signer_cert}")
    print("=" * 60)

    prov = Provisioner(args.port, args.baud, args.timeout)
    results = []

    try:
        prov.open()

        # 初期プロンプト待ち
        print("[INFO] Waiting for prompt...")
        time.sleep(2)
        prov.ser.write(b"\r\n")
        prov.ser.flush()
        prov.read_until([PROMPT], timeout=5)

        # 1. MQTT Broker Endpoint
        ok = prov.send_simple_value(
            "MQTT Endpoint",
            f"dataflash write aws mqttbrokerendpoint {args.endpoint}"
        )
        results.append(("MQTT Endpoint", ok))

        # 2. IoT Thing Name
        ok = prov.send_simple_value(
            "IoT Thing Name",
            f"dataflash write aws iotthingname {args.thing_name}"
        )
        results.append(("IoT Thing Name", ok))

        # 3. Client Certificate
        ok = prov.send_pem(
            "Client Certificate",
            "dataflash write aws clientcertificate",
            args.cert
        )
        results.append(("Client Certificate", ok))

        # 4. Client Private Key
        ok = prov.send_pem(
            "Client Private Key",
            "dataflash write aws clientprivatekey",
            args.key
        )
        results.append(("Client Private Key", ok))

        # 5. Code Signer Certificate (optional)
        if args.code_signer_cert:
            ok = prov.send_pem(
                "Code Signer Certificate",
                "dataflash write aws codesignercertificate",
                args.code_signer_cert
            )
            results.append(("Code Signer Certificate", ok))

        # 検証
        if not args.skip_verify:
            prov.verify_dataflash()

        # 結果サマリ
        print()
        print("=" * 60)
        all_ok = all(ok for _, ok in results)
        for name, ok in results:
            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {name}")

        if all_ok:
            print("[PASS] Provisioning completed successfully")
            sys.exit(0)
        else:
            print("[FAIL] Some provisioning steps failed")
            sys.exit(1)

    except serial.SerialException as e:
        print(f"[ERROR] Serial port error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted")
        sys.exit(130)
    finally:
        prov.close()


if __name__ == "__main__":
    main()
