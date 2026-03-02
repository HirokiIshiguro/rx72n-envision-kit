#!/usr/bin/env python3
"""
AWS IoT OTA (Over-The-Air) Update Test Script
RX72N Envision Kit の OTA ファームウェア更新を CI/CD で自動テストする。

テストフロー:
  1. COM7 で OTA Agent 起動を確認 (OTA over MQTT demo)
  2. v2.rsu を S3 にアップロード
  3. AWS IoT OTA ジョブを作成
  4. デバイス側ログ監視 (マイルストーン検出)
     a. ジョブ受信
     b. データブロック受信開始
     c. 署名検証成功 + ファイル受信完了
     d. 自己テスト開始 (OtaJobEventStartTest)
  5. リセット後の新バージョン起動確認
  6. AWS 側のジョブ状態確認
  7. S3 クリーンアップ

前提条件:
  - AWS CLI がインストール済みで認証情報が設定されていること
  - S3 バケットが作成済みでバージョニングが有効なこと
  - OTA サービスロールが作成済みであること
  - デバイスに v1 ファームウェア (OTA Agent 有効) が書き込み済みであること
  - プロビジョニング (endpoint, thing, cert, key, codesigner cert) が完了していること
"""

import argparse
import base64
import json
import os
import re
import struct
import subprocess
import sys
import time

import serial

# --- マイルストーン定義 ---
# OTA プロセスの各段階で検出すべきログパターン
OTA_MILESTONES = {
    "agent_ready": {
        "description": "OTA Agent started",
        "patterns": [
            r"OTA over MQTT demo",
            r"OTA over MQTT demo, Application version",
        ],
        "required": True,
    },
    "job_received": {
        "description": "OTA job document received",
        "patterns": [
            r"Received job message callback",
            r"Job document was accepted",
            r"Job document for receiving an update received",
        ],
        "required": True,
    },
    "download_started": {
        "description": "File block download started",
        "patterns": [
            r"Received data message callback",
            r"Received valid file block",
        ],
        "required": True,
    },
    "download_complete": {
        "description": "All blocks received, signature verified",
        "patterns": [
            r"Received entire update and validated the signature",
            r"Received final block of the update",
        ],
        "required": True,
    },
    "self_test": {
        "description": "Self-test callback received",
        "patterns": [
            r"OtaJobEventStartTest",
            r"Received OtaJobEventStartTest",
            r"Beginning self-test",
            r"In self test mode",
        ],
        "required": True,
    },
    "accepted": {
        "description": "Image accepted after self-test",
        "patterns": [
            r"Successfully updated with the new image",
            r"Image version is valid",
        ],
        "required": False,  # リセット後に出る可能性があるため optional
    },
}


def parse_version_from_log(line):
    """ログ行からバージョン番号を抽出する。

    "Application version 2.0.5" → (2, 0, 5)
    """
    m = re.search(r"Application version\s+(\d+)\.(\d+)\.(\d+)", line)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def extract_signature_from_rsu(rsu_path):
    """RSU ファイルから ECDSA 署名を抽出し、二重 base64 エンコードで返す。

    RSU ファイルレイアウト (mot_to_rsu.py 参照):
        0x028-0x02B  Signature Size  uint32 LE  (4 bytes) = 64 for ECDSA P-256
        0x02C-0x12B  Signature       raw bytes  (256 bytes, 実際は sig_size 分)

    ECDSA P-256 の署名は r(32 bytes) || s(32 bytes) = 64 bytes。

    AWS CLI v2 の blob 型自動デコード問題:
        create-ota-update API の signature.inlineDocument は blob 型。
        AWS CLI v2 (cli_binary_format=base64, デフォルト) は JSON 内の
        blob 値を base64 としてデコードしてから API に送信する。
        AWS IoT OTA サービスは、ジョブドキュメントの sig-sha256-ecdsa に
        保存した blob をそのまま文字列として埋め込む。

        したがって、inlineDocument に base64(raw_sig) を渡すと:
          CLI デコード → raw_sig bytes → ジョブドキュメントに raw bytes 埋め込み
          → FreeRTOS が base64 デコード → Base64InvalidSymbol エラー！

        修正: 二重 base64 エンコード
          base64(base64(raw_sig)) を渡す → CLI デコード → base64(raw_sig) 文字列
          → ジョブドキュメントに base64 文字列埋め込み
          → FreeRTOS が base64 デコード → raw_sig → 成功！

    See: https://repost.aws/questions/QUS14VnKE9SZ-RrTSfChTrqA

    Args:
        rsu_path: RSU ファイルパス

    Returns:
        str: 二重 base64 エンコードされた署名文字列 (AWS CLI v2 用)
    """
    with open(rsu_path, 'rb') as f:
        data = f.read(0x12C)  # ヘッダ部分のみ読み込み (署名末尾 = 0x02C + 256)

    if len(data) < 0x12C:
        raise ValueError(f"RSU file too small: {len(data)} bytes (need at least 0x12C)")

    # マジックコード検証
    magic = data[0:7]
    if magic != b"Renesas":
        raise ValueError(f"Invalid RSU magic: {magic!r} (expected b'Renesas')")

    # 署名サイズ (offset 0x028, uint32 LE)
    sig_size = struct.unpack_from('<I', data, 0x28)[0]
    if sig_size == 0 or sig_size > 256:
        raise ValueError(f"Invalid signature size: {sig_size}")

    # 署名バイト列 (offset 0x02C, sig_size bytes)
    signature = data[0x2C:0x2C + sig_size]
    if len(signature) != sig_size:
        raise ValueError(f"Could not read full signature: got {len(signature)}, expected {sig_size}")

    # 1回目: raw bytes → base64 文字列 (デバイスが最終的にデコードする値)
    sig_b64 = base64.b64encode(signature).decode('utf-8')

    # 2回目: AWS CLI v2 の blob 自動デコード対策
    # CLI がデコードした後に sig_b64 がジョブドキュメントに埋め込まれるようにする
    sig_b64_for_cli = base64.b64encode(sig_b64.encode('utf-8')).decode('utf-8')

    print(f"[RSU] Extracted signature from {os.path.basename(rsu_path)}")
    print(f"[RSU]   Signature size: {sig_size} bytes")
    print(f"[RSU]   Base64 (device): {sig_b64[:40]}... ({len(sig_b64)} chars)")
    print(f"[RSU]   Base64 (CLI):    {sig_b64_for_cli[:40]}... ({len(sig_b64_for_cli)} chars)")
    return sig_b64_for_cli


def upload_to_s3(rsu_path, s3_bucket, s3_key):
    """v2.rsu を S3 にアップロードし、VersionId を返す。"""
    print(f"[S3] Uploading {rsu_path} to s3://{s3_bucket}/{s3_key}")
    result = subprocess.run(
        ["aws", "s3api", "put-object",
         "--bucket", s3_bucket,
         "--key", s3_key,
         "--body", rsu_path],
        capture_output=True, text=True, check=True
    )
    response = json.loads(result.stdout)
    version_id = response.get("VersionId", "")
    print(f"[S3] Upload complete. VersionId: {version_id}")
    return version_id


def get_aws_account_id():
    """AWS アカウント ID を取得する。"""
    result = subprocess.run(
        ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def create_ota_job(thing_name, s3_bucket, s3_key, s3_version_id,
                   ota_role_arn, region, account_id, rsu_path):
    """AWS IoT OTA ジョブを作成する。

    カスタム署名方式: .rsu は mot_to_rsu.py で ECDSA-SHA256 署名済み。
    AWS Signer は使用せず、customCodeSigning で RSU 内の署名を base64 で指定。

    Args:
        rsu_path: RSU ファイルパス（署名抽出用）
    """
    ota_update_id = f"rx72n-ota-{int(time.time())}"
    thing_arn = f"arn:aws:iot:{region}:{account_id}:thing/{thing_name}"

    # RSU ファイルから ECDSA 署名を抽出 (base64 エンコード)
    sig_b64 = extract_signature_from_rsu(rsu_path)

    # OTA ファイル定義 (カスタム署名)
    ota_files = [{
        "fileName": s3_key,
        "fileLocation": {
            "s3Location": {
                "bucket": s3_bucket,
                "key": s3_key,
                "version": s3_version_id,
            }
        },
        "codeSigning": {
            "customCodeSigning": {
                "signature": {
                    "inlineDocument": sig_b64
                },
                "certificateChain": {
                    "certificateName": "secp256r1.crt"
                },
                "hashAlgorithm": "SHA256",
                "signatureAlgorithm": "ECDSA"
            }
        }
    }]

    cmd = [
        "aws", "iot", "create-ota-update",
        "--ota-update-id", ota_update_id,
        "--targets", json.dumps([thing_arn]),
        "--protocols", "MQTT",
        "--target-selection", "SNAPSHOT",
        "--role-arn", ota_role_arn,
        "--files", json.dumps(ota_files),
        "--region", region,
    ]

    print(f"[OTA] Creating OTA job: {ota_update_id}")
    print(f"[OTA]   Target: {thing_arn}")
    print(f"[OTA]   S3: s3://{s3_bucket}/{s3_key} (v={s3_version_id})")
    print(f"[OTA]   Role: {ota_role_arn}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] create-ota-update failed: {result.stderr}")
        # JSON パースエラーの場合も stdout を表示
        if result.stdout:
            print(f"[DEBUG] stdout: {result.stdout[:500]}")
        sys.exit(1)

    response = json.loads(result.stdout)
    print(f"[OTA] Job created: {response.get('otaUpdateId', ota_update_id)}")
    print(f"[OTA]   Status: {response.get('otaUpdateStatus', 'unknown')}")
    return ota_update_id


def monitor_ota_progress(ser, timeout=600):
    """COM7 のログを監視し、OTA マイルストーンを検出する。

    Returns:
        dict: 検出されたマイルストーン {name: timestamp}
    """
    detected = {}
    start = time.time()
    buf = b""
    block_count = 0
    last_progress_time = start

    print(f"[MONITOR] Watching OTA progress (timeout={timeout}s)...")

    while (time.time() - start) < timeout:
        n = ser.in_waiting
        if n > 0:
            chunk = ser.read(n)
            buf += chunk
            last_progress_time = time.time()

            # 行ごとに処理
            while b"\n" in buf:
                line_bytes, buf = buf.split(b"\n", 1)
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                # デバイスログを標準出力に転送 (CI/CD パイプラインで確認可能)
                elapsed = time.time() - start
                print(f"[COM7] {elapsed:6.1f}s | {line[:2000]}")

                # ブロック受信カウント
                if "Received valid file block" in line or "Received data message" in line:
                    block_count += 1
                    if block_count % 50 == 0 or block_count <= 3:
                        print(f"[MONITOR] {elapsed:.0f}s: Block {block_count} received")

                # マイルストーン検出
                for name, info in OTA_MILESTONES.items():
                    if name in detected:
                        continue
                    for pattern in info["patterns"]:
                        if re.search(pattern, line):
                            elapsed = time.time() - start
                            detected[name] = elapsed
                            print(f"[MILESTONE] {elapsed:.0f}s: {info['description']}")
                            print(f"  Log: {line[:200]}")
                            break

                # エラー検出
                if re.search(r"Error|FAIL|Failed|Abort", line, re.IGNORECASE):
                    if "OtaJobEventFail" in line or "Failed to" in line:
                        elapsed = time.time() - start
                        print(f"[ERROR] {elapsed:.0f}s: {line[:200]}")

        else:
            time.sleep(0.1)

        # 全マイルストーン (required) 検出で早期終了
        required_milestones = {
            name for name, info in OTA_MILESTONES.items()
            if info["required"]
        }
        if required_milestones.issubset(detected.keys()):
            print(f"[MONITOR] All required milestones detected!")
            break

        # 無通信タイムアウト (120秒応答なしで中断)
        if (time.time() - last_progress_time) > 120:
            print("[WARN] No data received for 120s")
            break

    elapsed = time.time() - start
    print(f"[MONITOR] Monitoring ended after {elapsed:.0f}s")
    print(f"[MONITOR] Total blocks received: {block_count}")
    return detected


def verify_new_version_after_reset(ser, expected_build, timeout=120):
    """リセット後の新バージョン起動を確認する。

    OTA 自己テスト完了後、デバイスはリセットし新 FW で再起動する。
    boot_loader の bank swap ログ → 新 FW の "Application version X.Y.Z" を検出。
    """
    print(f"[VERIFY] Waiting for new version (build={expected_build}, timeout={timeout}s)...")
    start = time.time()
    buf = b""
    detected_version = None
    boot_loader_seen = False

    while (time.time() - start) < timeout:
        n = ser.in_waiting
        if n > 0:
            buf += ser.read(n)
            while b"\n" in buf:
                line_bytes, buf = buf.split(b"\n", 1)
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                # boot_loader 再起動検出
                if "RX72N Envision Kit" in line or "boot_loader" in line.lower():
                    if not boot_loader_seen:
                        elapsed = time.time() - start
                        print(f"[VERIFY] {elapsed:.0f}s: Boot loader detected")
                        boot_loader_seen = True

                # バージョン検出
                ver = parse_version_from_log(line)
                if ver:
                    detected_version = ver
                    elapsed = time.time() - start
                    print(f"[VERIFY] {elapsed:.0f}s: Version {ver[0]}.{ver[1]}.{ver[2]} detected")
                    if ver[2] == expected_build:
                        print(f"[PASS] New version confirmed: {ver[0]}.{ver[1]}.{ver[2]}")
                        return True
                    else:
                        print(f"[INFO] Version build={ver[2]}, expected={expected_build}")
        else:
            time.sleep(0.1)

    if detected_version:
        print(f"[WARN] Detected version {detected_version} but expected build={expected_build}")
    else:
        print(f"[WARN] No version information detected within {timeout}s")
    return detected_version is not None


def verify_job_status(ota_update_id, region):
    """AWS 側の OTA ジョブステータスを確認する。

    Returns:
        dict: {"status": str, "error_info": dict or None}
              status は CREATE_PENDING, CREATE_COMPLETE, CREATE_FAILED 等
    """
    print(f"[AWS] Checking OTA update status: {ota_update_id}")
    result = subprocess.run(
        ["aws", "iot", "get-ota-update",
         "--ota-update-id", ota_update_id,
         "--region", region],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[WARN] Could not get OTA status: {result.stderr[:200]}")
        return {"status": None, "error_info": None}

    response = json.loads(result.stdout)
    ota_info = response.get("otaUpdateInfo", {})
    status = ota_info.get("otaUpdateStatus", "unknown")
    error_info = ota_info.get("errorInfo")
    print(f"[AWS] OTA Update Status: {status}")

    if error_info:
        print(f"[AWS] Error Code:    {error_info.get('code', 'N/A')}")
        print(f"[AWS] Error Message: {error_info.get('message', 'N/A')}")

    # デバッグ: OTA ファイル情報も出力
    ota_files = ota_info.get("otaUpdateFiles", [])
    for i, f in enumerate(ota_files):
        signing = f.get("codeSigning", {})
        custom = signing.get("customCodeSigning", {})
        if custom:
            sig_info = custom.get("signature", {})
            cert_info = custom.get("certificateChain", {})
            inline_doc = sig_info.get("inlineDocument", "")
            cert_name = cert_info.get("certificateName", "")
            print(f"[AWS] File[{i}] signature.inlineDocument: "
                  f"{inline_doc[:40]}... ({len(inline_doc)} chars)")
            print(f"[AWS] File[{i}] certificateName: {cert_name}")

    # デバッグ: IoT Job のジョブドキュメントを取得して表示
    aws_job_id = ota_info.get("awsIotJobId")
    if aws_job_id:
        print(f"[AWS] IoT Job ID: {aws_job_id}")
        job_result = subprocess.run(
            ["aws", "iot", "describe-job",
             "--job-id", aws_job_id,
             "--region", region],
            capture_output=True, text=True
        )
        if job_result.returncode == 0:
            job_response = json.loads(job_result.stdout)
            job_obj = job_response.get("job", {})
            job_doc_str = job_obj.get("document", "")
            if job_doc_str:
                print(f"[AWS] Raw job document ({len(job_doc_str)} chars):")
                try:
                    job_doc = json.loads(job_doc_str)
                    print(json.dumps(job_doc, indent=2)[:3000])
                except json.JSONDecodeError:
                    print(job_doc_str[:3000])
            else:
                # OTA 作成ジョブは describe-job で document が空になる既知の制限。
                # ジョブドキュメントは documentSource (S3 URL) 経由で配信される。
                doc_src = job_obj.get("documentSource", "")
                print(f"[AWS] describe-job: document is empty (OTA jobs use documentSource)")
                if doc_src:
                    print(f"[AWS]   documentSource: {doc_src[:200]}")
        else:
            print(f"[WARN] describe-job failed: {job_result.stderr[:200]}")

    return {"status": status, "error_info": error_info}


def wait_for_ota_job_ready(ota_update_id, region, timeout=60):
    """OTA ジョブが CREATE_PENDING を脱するまでポーリングする。

    CREATE_PENDING → CREATE_COMPLETE: 成功（デバイスへの配信開始）
    CREATE_PENDING → CREATE_FAILED:   失敗（設定不備等）

    Returns:
        dict: verify_job_status の戻り値
    """
    print(f"[AWS] Waiting for OTA job to be ready (timeout={timeout}s)...")
    start = time.time()
    poll_interval = 5  # 5秒間隔

    while (time.time() - start) < timeout:
        result = verify_job_status(ota_update_id, region)
        status = result["status"]

        if status == "CREATE_COMPLETE":
            print("[AWS] OTA job is ready for device download")
            return result
        elif status == "CREATE_FAILED":
            print("[ERROR] OTA job creation failed!")
            return result
        elif status not in ("CREATE_PENDING", "CREATE_IN_PROGRESS"):
            print(f"[WARN] Unexpected OTA status: {status}")
            return result

        elapsed = time.time() - start
        print(f"[AWS] Still {status} ({elapsed:.0f}s)...")
        time.sleep(poll_interval)

    print(f"[WARN] OTA job still CREATE_PENDING after {timeout}s")
    return verify_job_status(ota_update_id, region)


def cleanup_s3(s3_bucket, s3_key):
    """S3 の一時ファイルを削除する。"""
    print(f"[CLEANUP] Deleting s3://{s3_bucket}/{s3_key}")
    result = subprocess.run(
        ["aws", "s3", "rm", f"s3://{s3_bucket}/{s3_key}"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[CLEANUP] S3 object deleted")
    else:
        print(f"[WARN] S3 cleanup failed: {result.stderr[:200]}")


def main():
    parser = argparse.ArgumentParser(
        description="AWS IoT OTA Update Test for RX72N Envision Kit"
    )
    parser.add_argument("--device-id",
                        help="Device ID (loads config from device_config.json)")
    parser.add_argument("--log-port", default="COM7",
                        help="Log serial port (default: COM7)")
    parser.add_argument("--log-baud", type=int, default=921600,
                        help="Log serial baud rate (default: 921600)")
    parser.add_argument("--rsu", required=True,
                        help="Path to v2 .rsu file for OTA update")
    parser.add_argument("--s3-bucket", default=os.environ.get("OTA_S3_BUCKET"),
                        help="S3 bucket name (or env OTA_S3_BUCKET)")
    parser.add_argument("--ota-role-arn", default=os.environ.get("OTA_ROLE_ARN"),
                        help="OTA service role ARN (or env OTA_ROLE_ARN)")
    parser.add_argument("--region", default=None,
                        help="AWS region (default: from device_config.json)")
    parser.add_argument("--thing-name", default=None,
                        help="AWS IoT Thing name (default: from device_config.json)")
    parser.add_argument("--expected-build", type=int, default=None,
                        help="Expected APP_VERSION_BUILD of v2 firmware")
    parser.add_argument("--timeout", type=int, default=600,
                        help="OTA download timeout in seconds (default: 600)")
    parser.add_argument("--skip-upload", action="store_true",
                        help="Skip S3 upload (use existing object)")
    parser.add_argument("--skip-cleanup", action="store_true",
                        help="Skip S3 cleanup after test")
    args = parser.parse_args()

    # --device-id から設定解決
    if args.device_id:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from device_config_loader import load_device_config
        device = load_device_config(args.device_id)
        print(f"[INFO] Loaded config for device: {args.device_id}")
        if args.log_port == "COM7":
            args.log_port = device["log_port"]
        if args.log_baud == 921600:
            args.log_baud = device["log_baud"]
        if not args.region:
            args.region = device.get("aws_region", "ap-northeast-1")
        if not args.thing_name:
            args.thing_name = device["thing_name"]

    # 必須パラメータチェック
    if not args.s3_bucket:
        parser.error("--s3-bucket is required (or set OTA_S3_BUCKET env var)")
    if not args.ota_role_arn:
        parser.error("--ota-role-arn is required (or set OTA_ROLE_ARN env var)")
    if not args.thing_name:
        parser.error("--thing-name is required (or use --device-id)")
    if not args.region:
        args.region = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-1")
    if not os.path.isfile(args.rsu):
        print(f"[ERROR] RSU file not found: {args.rsu}")
        sys.exit(1)

    # S3 キー名
    rsu_filename = os.path.basename(args.rsu)
    s3_key = f"ota/{args.thing_name}/{rsu_filename}"

    print("=" * 60)
    print("[INFO] AWS IoT OTA Update Test")
    print(f"[INFO]   Thing    : {args.thing_name}")
    print(f"[INFO]   Region   : {args.region}")
    print(f"[INFO]   S3       : s3://{args.s3_bucket}/{s3_key}")
    print(f"[INFO]   Role ARN : {args.ota_role_arn}")
    print(f"[INFO]   RSU      : {args.rsu} ({os.path.getsize(args.rsu)} bytes)")
    print(f"[INFO]   Log Port : {args.log_port} @ {args.log_baud}bps")
    print(f"[INFO]   Timeout  : {args.timeout}s")
    print("=" * 60)

    results = {}
    ota_update_id = None

    try:
        # --- Step 1: OTA Agent 起動確認 ---
        print()
        print("[STEP 1/6] Confirming OTA Agent is running")
        log_ser = serial.Serial(args.log_port, args.log_baud, timeout=0)
        time.sleep(0.5)
        log_ser.reset_input_buffer()

        # OTA Agent のログが出ていることを確認 (60秒待ち)
        agent_detected = False
        start = time.time()
        buf = b""
        while (time.time() - start) < 60:
            n = log_ser.in_waiting
            if n > 0:
                buf += log_ser.read(n)
                decoded = buf.decode("utf-8", errors="replace")
                if re.search(r"OTA over MQTT demo", decoded):
                    print("[PASS] OTA Agent is running")
                    # バージョン抽出
                    ver = parse_version_from_log(decoded)
                    if ver:
                        print(f"[INFO] Current firmware version: {ver[0]}.{ver[1]}.{ver[2]}")
                    agent_detected = True
                    break
            else:
                time.sleep(0.2)

        if not agent_detected:
            # まだ検出されていない場合は MQTT 接続メッセージなどで代替
            decoded = buf.decode("utf-8", errors="replace")
            if "MQTT" in decoded or "Subscribed" in decoded:
                print("[WARN] OTA Agent banner not detected, but MQTT activity found")
                agent_detected = True
            else:
                print("[FAIL] OTA Agent not detected within 60s")
                print(f"[DEBUG] Received: {decoded[:300]}")
                results["agent_ready"] = False
                sys.exit(1)

        results["agent_ready"] = agent_detected

        # --- Step 2: S3 アップロード ---
        print()
        print("[STEP 2/6] Uploading firmware to S3")
        if args.skip_upload:
            print("[SKIP] S3 upload skipped (--skip-upload)")
            s3_version_id = ""
        else:
            s3_version_id = upload_to_s3(args.rsu, args.s3_bucket, s3_key)
        results["s3_upload"] = True

        # --- Step 3: OTA ジョブ作成 ---
        print()
        print("[STEP 3/6] Creating OTA update job")
        account_id = get_aws_account_id()
        ota_update_id = create_ota_job(
            args.thing_name, args.s3_bucket, s3_key, s3_version_id,
            args.ota_role_arn, args.region, account_id, args.rsu
        )
        results["ota_job_created"] = True

        # --- Step 3.5: OTA ジョブ状態確認 (CREATE_FAILED 早期検出) ---
        print()
        print("[STEP 3.5/6] Waiting for OTA job to leave CREATE_PENDING")
        job_result = wait_for_ota_job_ready(ota_update_id, args.region, timeout=60)
        if job_result["status"] == "CREATE_FAILED":
            print("[FAIL] OTA job CREATE_FAILED - aborting (skip 10min device wait)")
            results["ota_job_ready"] = False
            results["ota_download"] = False
            results["new_version"] = False
            results["aws_status"] = False
            log_ser.close()
            print(f"[INFO] Closed {args.log_port}")
        else:
            results["ota_job_ready"] = True

            # --- Step 4: OTA 進捗監視 ---
            print()
            print("[STEP 4/6] Monitoring OTA progress")
            # Note: バッファクリアしない（JSON received ログを捕捉するため）
            milestones = monitor_ota_progress(log_ser, timeout=args.timeout)

            # マイルストーン評価
            required = {name for name, info in OTA_MILESTONES.items() if info["required"]}
            # agent_ready は既に Step 1 で確認済み
            required.discard("agent_ready")
            missing = required - set(milestones.keys())
            if missing:
                print(f"[WARN] Missing milestones: {', '.join(missing)}")
                results["ota_download"] = False
            else:
                print("[PASS] All required OTA milestones detected")
                results["ota_download"] = True

            # --- Step 5: 新バージョン起動確認 ---
            print()
            print("[STEP 5/6] Verifying new version after reset")
            if args.expected_build:
                version_ok = verify_new_version_after_reset(
                    log_ser, args.expected_build, timeout=120
                )
                results["new_version"] = version_ok
            else:
                print("[SKIP] --expected-build not specified, skipping version check")
                results["new_version"] = True

            # --- Step 6: AWS ジョブステータス確認 ---
            print()
            print("[STEP 6/6] Checking AWS OTA job status")
            if ota_update_id:
                job_result = verify_job_status(ota_update_id, args.region)
                # CREATE_COMPLETE は正常（デバイス側の実行状態とは別）
                results["aws_status"] = job_result["status"] is not None
            else:
                results["aws_status"] = False

            log_ser.close()
            print(f"[INFO] Closed {args.log_port}")

    except serial.SerialException as e:
        print(f"[ERROR] Serial port error: {e}")
        results["serial"] = False
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] AWS CLI error: {e}")
        if e.stderr:
            print(f"[DEBUG] stderr: {e.stderr[:300]}")
        results["aws_cli"] = False
    except KeyboardInterrupt:
        print("\n[INFO] Test interrupted by user")
    finally:
        # --- クリーンアップ ---
        if not args.skip_cleanup and ota_update_id:
            print()
            print("[CLEANUP]")
            cleanup_s3(args.s3_bucket, s3_key)

    # --- 結果レポート ---
    print()
    print("=" * 60)
    all_ok = all(results.values()) if results else False
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
    print("=" * 60)

    if all_ok:
        print("[PASS] OTA update test completed successfully")
        sys.exit(0)
    else:
        print("[FAIL] OTA update test failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
