#!/usr/bin/env python3
"""
AWS IoT OTA (Over-The-Air) Update Test Script
RX72N Envision Kit の OTA ファームウェア更新を CI/CD で自動テストする。

実行モード:
  - full:       従来どおり単一ホストで OTA テスト全体を実行
  - create-job: Windows runner で S3 upload + OTA job 作成のみ実行
  - monitor:    Raspberry Pi runner で UART 監視 + 新バージョン確認のみ実行
  - finalize:   Windows runner で AWS 状態確認 + S3 cleanup を実行

前提条件:
  - create-job / finalize: AWS CLI がインストール済みで認証情報が設定されていること
  - monitor / full: pyserial がインストールされ、UART へアクセスできること
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

try:
    import serial
except ImportError as exc:
    serial = None
    SERIAL_IMPORT_ERROR = exc

    class SerialException(Exception):
        """Fallback exception used when pyserial is unavailable."""
else:
    SERIAL_IMPORT_ERROR = None
    SerialException = serial.SerialException

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
    "signature_verify_started": {
        "description": "Signature verification started",
        "patterns": [
            r"Started sig-sha256-ecdsa signature verification",
            r"Started .* signature verification",
        ],
        "required": False,
    },
    "self_test": {
        "description": "Self-test callback received",
        "patterns": [
            r"OtaJobEventStartTest",
            r"Received OtaJobEventStartTest",
            r"Beginning self-test",
            r"In self test mode",
            r"Created self test update",
            r'"self_test":"ready"',
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

LEGACY_RSU_MAGIC = b"Renesas"
FWUP_V2_RSU_MAGIC = b"RELFWV2"


def require_serial_support():
    """pyserial が必要なモードで import 可否を確認する。"""
    if serial is None:
        raise RuntimeError(
            "pyserial is required for this mode but is not installed: "
            f"{SERIAL_IMPORT_ERROR}"
        )


def env_int(name, default):
    """環境変数から int を読み取る。未設定/不正値なら default を返す。"""
    value = os.environ.get(name)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except ValueError:
        return default


def format_version(version):
    """(major, minor, build) を文字列化する。"""
    if not version:
        return None
    return f"{version[0]}.{version[1]}.{version[2]}"


def write_json(path, payload):
    """JSON ファイルを書き出す。"""
    if not path:
        return
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"[INFO] Wrote JSON metadata: {path}")


def read_json(path):
    """JSON ファイルを読み込む。"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_device_defaults(args):
    """device_config.json と環境変数から不足引数を補完する。"""
    device = {}
    if args.device_id:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from device_config_loader import load_device_config

        device = load_device_config(args.device_id)
        print(f"[INFO] Loaded config for device: {args.device_id}")

    if not args.log_port:
        args.log_port = device.get("log_port") or os.environ.get("UART_PORT") or "COM7"
    if not args.log_baud:
        args.log_baud = device.get("log_baud") or env_int("UART_BAUD_RATE", 921600)
    if not args.cmd_port:
        args.cmd_port = device.get("command_port") or os.environ.get("COMMAND_PORT")
    if not args.cmd_baud:
        args.cmd_baud = device.get("command_baud") or env_int("COMMAND_BAUD_RATE", 115200)
    if not args.region:
        args.region = device.get("aws_region") or os.environ.get("AWS_DEFAULT_REGION") or "ap-northeast-1"
    if not args.thing_name:
        args.thing_name = device.get("thing_name")

    return args


def build_s3_key(rsu_path, thing_name):
    """RSU パスから S3 key を決定する。"""
    return f"ota/{thing_name}/{os.path.basename(rsu_path)}"


def print_summary(results):
    """結果サマリーを表示する。"""
    print()
    print("=" * 60)
    all_ok = all(results.values()) if results else False
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
    print("=" * 60)
    return all_ok


def validate_serial_args(parser, args):
    """monitor/full 用のシリアル関連引数を検証する。"""
    if not args.log_port:
        parser.error("--log-port is required (or set UART_PORT / use --device-id)")


def validate_create_args(parser, args):
    """create-job/full 用の AWS 関連引数を検証する。"""
    if not args.rsu:
        parser.error("--rsu is required for this mode")
    if not args.s3_bucket:
        parser.error("--s3-bucket is required (or set OTA_S3_BUCKET env var)")
    if not args.ota_role_arn:
        parser.error("--ota-role-arn is required (or set OTA_ROLE_ARN env var)")
    if not args.thing_name:
        parser.error("--thing-name is required (or use --device-id)")
    if not os.path.isfile(args.rsu):
        parser.error(f"--rsu not found: {args.rsu}")


def validate_finalize_args(parser, args):
    """finalize 用の引数を検証する。"""
    if not args.metadata_in:
        parser.error("--metadata-in is required for finalize mode")
    if not os.path.isfile(args.metadata_in):
        parser.error(f"--metadata-in not found: {args.metadata_in}")


def parse_version_from_log(line):
    """ログ行からバージョン番号を抽出する。

    "Application version 2.0.5" → (2, 0, 5)
    """
    m = re.search(r"Application version\s+(\d+)\.(\d+)\.(\d+)", line)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def raw_rs_to_der(signature):
    """raw r||s (64 bytes) を DER エンコード ECDSA 署名に変換する。

    FreeRTOS OTA PAL は mbedtls_pk_verify() で署名検証するため、
    DER (ASN.1) フォーマットが必要。RSU ファイルの署名は raw r||s 形式。

    DER format:
        SEQUENCE {
            INTEGER r  (32 bytes, 先頭ビットが1なら 0x00 パディング)
            INTEGER s  (32 bytes, 先頭ビットが1なら 0x00 パディング)
        }

    Args:
        signature: 64 bytes (r: 32 bytes || s: 32 bytes)

    Returns:
        bytes: DER エンコードされた ECDSA 署名
    """
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

    r = int.from_bytes(signature[:32], 'big')
    s = int.from_bytes(signature[32:], 'big')
    return encode_dss_signature(r, s)


def extract_signature_from_rsu(rsu_path):
    """RSU ファイルから ECDSA 署名を抽出し、DER 変換 + 二重 base64 エンコードで返す。

    RSU ファイルレイアウト (mot_to_rsu.py 参照):
        0x028-0x02B  Signature Size  uint32 LE  (4 bytes) = 64 for ECDSA P-256
        0x02C-0x12B  Signature       raw bytes  (256 bytes, 実際は sig_size 分)

    ECDSA P-256 の署名は r(32 bytes) || s(32 bytes) = 64 bytes (raw r||s)。

    変換チェーン:
        1. raw r||s → DER (ASN.1) 変換
           FreeRTOS OTA PAL は mbedtls_pk_verify() を使用するため DER が必要。
           RSU には raw r||s が格納されているので変換する。

        2. DER → base64 エンコード
           ジョブドキュメントの sig-sha256-ecdsa は base64 文字列。

        3. base64 → 二重 base64 エンコード (AWS CLI v2 対策)
           create-ota-update API の inlineDocument は blob 型。
           CLI v2 は blob を自動 base64 デコードするため、二重エンコードが必要。
           See: https://repost.aws/questions/QUS14VnKE9SZ-RrTSfChTrqA

    Args:
        rsu_path: RSU ファイルパス

    Returns:
        str: 二重 base64 エンコードされた DER 署名文字列 (AWS CLI v2 用)
    """
    with open(rsu_path, 'rb') as f:
        data = f.read(0x12C)  # ヘッダ部分のみ読み込み (署名末尾 = 0x02C + 256)

    if len(data) < 0x12C:
        raise ValueError(f"RSU file too small: {len(data)} bytes (need at least 0x12C)")

    # マジックコード検証
    magic = data[0:7]
    if magic == LEGACY_RSU_MAGIC:
        rsu_format = "legacy"
    elif magic == FWUP_V2_RSU_MAGIC:
        rsu_format = "fwup-v2"
    else:
        raise ValueError(
            f"Invalid RSU magic: {magic!r} "
            f"(expected {LEGACY_RSU_MAGIC!r}* or {FWUP_V2_RSU_MAGIC!r})"
        )

    # 署名サイズ (offset 0x028, uint32 LE)
    sig_size = struct.unpack_from('<I', data, 0x28)[0]
    if sig_size == 0 or sig_size > 256:
        raise ValueError(f"Invalid signature size: {sig_size}")

    # 署名バイト列 (offset 0x02C, sig_size bytes)
    raw_sig = data[0x2C:0x2C + sig_size]
    if len(raw_sig) != sig_size:
        raise ValueError(f"Could not read full signature: got {len(raw_sig)}, expected {sig_size}")

    # Step 1: raw r||s → DER (ASN.1) 変換
    der_sig = raw_rs_to_der(raw_sig)

    # Step 2: DER → base64 (デバイスが最終的にデコードする値)
    sig_b64 = base64.b64encode(der_sig).decode('utf-8')

    # Step 3: AWS CLI v2 の blob 自動デコード対策 (二重 base64)
    sig_b64_for_cli = base64.b64encode(sig_b64.encode('utf-8')).decode('utf-8')

    print(f"[RSU] Extracted signature from {os.path.basename(rsu_path)} ({rsu_format})")
    print(f"[RSU]   Raw r||s: {sig_size} bytes")
    print(f"[RSU]   DER:      {len(der_sig)} bytes")
    print(f"[RSU]   Base64 (device): {sig_b64[:40]}... ({len(sig_b64)} chars)")
    print(f"[RSU]   Base64 (CLI):    {sig_b64_for_cli[:40]}... ({len(sig_b64_for_cli)} chars)")
    return sig_b64_for_cli


def extract_ota_payload(rsu_path):
    """RSU ファイルから OTA ペイロード (descriptor + code) を抽出する。

    OTA PAL は受信ファイルを TEMP_AREA + 0x200 から書き込み、
    total_image_length バイトをハッシュして署名検証する。
    mot_to_rsu.py は descriptor(256B) + code_flash のみ署名するため、
    RSU ヘッダ (0x200B) と data flash (末尾) を除いたペイロードを送る必要がある。

    RSU ファイルレイアウト:
        0x000-0x1FF  Header      (512B)  - NOT signed
        0x200-0x2FF  Descriptor  (256B)  - signed
        0x300+       Code flash  (N B)   - signed
        末尾         Data flash  (32KB)  - NOT signed

    Args:
        rsu_path: RSU ファイルパス

    Returns:
        bytes: OTA ペイロード (descriptor + code)
    """
    with open(rsu_path, 'rb') as f:
        rsu_data = f.read()

    descriptor_offset = 0x200
    descriptor_size = 256
    magic = rsu_data[0:7]

    if magic == FWUP_V2_RSU_MAGIC:
        file_size = struct.unpack_from('<I', rsu_data, 0x6C)[0]
        if file_size < descriptor_offset + descriptor_size:
            raise ValueError(
                f"Invalid FWUP v2 file size in RSU header: {file_size} "
                f"(need at least {descriptor_offset + descriptor_size})"
            )
        if len(rsu_data) < file_size:
            raise ValueError(
                f"RSU file too small: header says {file_size} bytes, "
                f"but only {len(rsu_data)} available"
            )

        payload = rsu_data[descriptor_offset:file_size]
        segment_count = struct.unpack_from('<I', rsu_data, descriptor_offset)[0]
        payload_size = len(payload)
        print(f"[RSU] Extracted OTA payload from {os.path.basename(rsu_path)} (fwup-v2)")
        print(f"[RSU]   RSU file size:    {len(rsu_data)} bytes")
        print(f"[RSU]   Header file size: {file_size} bytes")
        print(f"[RSU]   Segment count:     {segment_count}")
        print(f"[RSU]   Payload size:      {payload_size} bytes")
        print(f"[RSU]   Stripped:          header {descriptor_offset}B")
        return payload

    if magic != LEGACY_RSU_MAGIC:
        raise ValueError(
            f"Invalid RSU magic: {magic!r} "
            f"(expected {LEGACY_RSU_MAGIC!r}* or {FWUP_V2_RSU_MAGIC!r})"
        )

    # Legacy RSU の descriptor から code flash のアドレス範囲を読む
    # Descriptor は RSU offset 0x200:
    #   0x200-0x203: sequence_number (uint32 LE)
    #   0x204-0x207: start_address   (uint32 LE)
    #   0x208-0x20B: end_address     (uint32 LE)
    start_addr = struct.unpack_from('<I', rsu_data, descriptor_offset + 4)[0]
    end_addr = struct.unpack_from('<I', rsu_data, descriptor_offset + 8)[0]
    code_size = end_addr - start_addr + 1
    payload_size = descriptor_size + code_size

    payload = rsu_data[descriptor_offset:descriptor_offset + payload_size]

    if len(payload) != payload_size:
        raise ValueError(
            f"RSU file too small: expected {payload_size} payload bytes from offset 0x200, "
            f"but only {len(payload)} available"
        )

    print(f"[RSU] Extracted OTA payload from {os.path.basename(rsu_path)} (legacy)")
    print(f"[RSU]   RSU file size:    {len(rsu_data)} bytes")
    print(f"[RSU]   Code range:       0x{start_addr:08X}-0x{end_addr:08X} ({code_size} bytes)")
    print(f"[RSU]   Payload size:     {payload_size} bytes (descriptor {descriptor_size} + code {code_size})")
    print(f"[RSU]   Stripped:         header {descriptor_offset}B + data flash {len(rsu_data) - descriptor_offset - payload_size}B")

    return payload


def upload_to_s3(rsu_path, s3_bucket, s3_key):
    """RSU から OTA ペイロードを抽出して S3 にアップロードし、VersionId を返す。"""
    payload = extract_ota_payload(rsu_path)

    # ペイロードを一時ファイルに書き出して S3 にアップロード
    payload_path = rsu_path + ".ota_payload"
    with open(payload_path, 'wb') as f:
        f.write(payload)

    print(f"[S3] Uploading OTA payload ({len(payload)} bytes) to s3://{s3_bucket}/{s3_key}")
    result = subprocess.run(
        ["aws", "s3api", "put-object",
         "--bucket", s3_bucket,
         "--key", s3_key,
         "--body", payload_path],
        capture_output=True, text=True, check=True
    )
    response = json.loads(result.stdout)
    version_id = response.get("VersionId", "")
    print(f"[S3] Upload complete. VersionId: {version_id}")

    # 一時ファイル削除
    try:
        os.remove(payload_path)
    except OSError:
        pass

    return version_id


def get_aws_account_id():
    """AWS アカウント ID を取得する。"""
    result = subprocess.run(
        ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def run_aws_cli_json(cmd, error_label):
    """AWS CLI を実行し、JSON 応答を返す。"""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(f"{error_label}: {stderr[:300]}")
    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    return json.loads(stdout)


def iter_ota_update_summaries(region, max_pages=5):
    """list-ota-updates の結果をページングして列挙する。"""
    summaries = []
    next_token = None

    for _ in range(max_pages):
        cmd = [
            "aws", "iot", "list-ota-updates",
            "--region", region,
            "--max-results", "100",
        ]
        if next_token:
            cmd.extend(["--next-token", next_token])
        response = run_aws_cli_json(cmd, "list-ota-updates failed")
        summaries.extend(response.get("otaUpdates", []))
        next_token = response.get("nextToken")
        if not next_token:
            break

    return summaries


def get_ota_update_info(ota_update_id, region):
    """get-ota-update の otaUpdateInfo を返す。"""
    response = run_aws_cli_json(
        [
            "aws", "iot", "get-ota-update",
            "--ota-update-id", ota_update_id,
            "--region", region,
        ],
        f"get-ota-update failed for {ota_update_id}",
    )
    return response.get("otaUpdateInfo", {})


def matches_thing_target(targets, thing_name, region=None):
    """OTA update の target ARN 群に対象 Thing が含まれるか判定する。"""
    if not targets:
        return False

    expected_suffix = f":thing/{thing_name}"
    expected_slash = f"/thing/{thing_name}"

    for target in targets:
        if target == thing_name:
            return True
        if target.endswith(expected_suffix) or target.endswith(expected_slash):
            return True
        if region and f":{region}:" in target and expected_suffix in target:
            return True

    return False


def delete_ota_update(ota_update_id, region):
    """OTA update と対応する IoT Job/stream を削除する。"""
    print(f"[CLEANUP] Deleting OTA update: {ota_update_id}")
    subprocess.run(
        [
            "aws", "iot", "delete-ota-update",
            "--ota-update-id", ota_update_id,
            "--delete-stream",
            "--force-delete-aws-job",
            "--region", region,
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def cleanup_stale_ota_updates(thing_name, region, keep_ota_update_id=None):
    """対象 Thing 向けの古い OTA update を削除する。"""
    prefixes = ("rx72n-ota-",)
    summaries = iter_ota_update_summaries(region)
    matched = []
    deleted = []

    print(f"[CLEANUP] Looking for stale OTA updates for thing: {thing_name}")
    print(f"[CLEANUP]   Listed OTA updates: {len(summaries)}")

    for summary in summaries:
        ota_update_id = summary.get("otaUpdateId")
        if not ota_update_id:
            continue
        if keep_ota_update_id and ota_update_id == keep_ota_update_id:
            continue
        if not ota_update_id.startswith(prefixes):
            continue

        ota_info = get_ota_update_info(ota_update_id, region)
        targets = ota_info.get("targets", [])
        if not matches_thing_target(targets, thing_name, region):
            continue

        status = ota_info.get("otaUpdateStatus", "unknown")
        aws_job_id = ota_info.get("awsIotJobId")
        matched.append(
            {
                "ota_update_id": ota_update_id,
                "status": status,
                "aws_job_id": aws_job_id,
            }
        )
        print(f"[CLEANUP]   Match: {ota_update_id} (status={status}, job={aws_job_id})")
        delete_ota_update(ota_update_id, region)
        deleted.append(ota_update_id)

    print(f"[CLEANUP] Deleted stale OTA updates: {len(deleted)}")
    return {
        "listed_count": len(summaries),
        "matched": matched,
        "deleted": deleted,
    }


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


def monitor_ota_progress(ser, timeout=600, port_label="UART"):
    """ログ UART を監視し、OTA マイルストーンを検出する。

    Returns:
        tuple: (detected_milestones, last_version, stall_hint)
            - detected_milestones: dict {name: timestamp}
            - last_version: tuple (major, minor, build) or None
              モニタリング中に検出された最後のバージョン情報。
              self_test 後のリブートでバージョンが出力された場合にここに格納される。
            - stall_hint: 文字列 or None
              進行が止まった相を追加で推定できた場合に設定する。
    """
    detected = {}
    start = time.time()
    buf = b""
    block_count = 0
    last_progress_time = start
    last_version = None  # モニタリング中に検出したバージョン情報
    stall_hint = None

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
                print(f"[{port_label}] {elapsed:6.1f}s | {line[:2000]}")

                # ブロック受信カウント
                if "Received valid file block" in line or "Received data message" in line:
                    block_count += 1
                    if block_count % 50 == 0 or block_count <= 3:
                        print(f"[MONITOR] {elapsed:.0f}s: Block {block_count} received")
                    if "job_received" not in detected:
                        detected["job_received"] = elapsed
                        print(
                            f"[MILESTONE] {elapsed:.0f}s: OTA job document received"
                            " (inferred from file-block download activity)"
                        )

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

                # バージョン検出 (self_test 後のリブートで出力されるバージョンを記録)
                ver = parse_version_from_log(line)
                if ver:
                    last_version = ver
                    if "self_test" in detected:
                        elapsed = time.time() - start
                        print(f"[MONITOR] {elapsed:.0f}s: Post-reboot version {ver[0]}.{ver[1]}.{ver[2]} detected")

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

    if (
        "signature_verify_started" in detected
        and "self_test" not in detected
        and "download_complete" in detected
    ):
        stall_hint = "stalled_after_signature_verification"
        print("[WARN] OTA appears stalled after signature verification started")
    elif "download_complete" in detected and "self_test" not in detected:
        stall_hint = "stalled_after_download_complete"
        print("[WARN] OTA appears stalled after download completion")

    elapsed = time.time() - start
    print(f"[MONITOR] Monitoring ended after {elapsed:.0f}s")
    print(f"[MONITOR] Total blocks received: {block_count}")
    if last_version:
        print(f"[MONITOR] Last detected version: {last_version[0]}.{last_version[1]}.{last_version[2]}")
    return detected, last_version, stall_hint


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

    return {"status": status, "error_info": error_info, "aws_job_id": aws_job_id}


def describe_job_execution(job_id, thing_name, region):
    """Thing 向け IoT Job execution の状態を確認する。"""
    print(f"[AWS] Checking IoT Job execution: job={job_id}, thing={thing_name}")
    result = subprocess.run(
        [
            "aws", "iot", "describe-job-execution",
            "--job-id", job_id,
            "--thing-name", thing_name,
            "--region", region,
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[WARN] Could not get IoT Job execution status: {result.stderr[:200]}")
        return {"status": None, "status_details": None}

    response = json.loads(result.stdout)
    execution = response.get("execution", {})
    status = execution.get("status")
    status_details = execution.get("statusDetails")
    print(f"[AWS] IoT Job execution status: {status}")
    if status_details:
        print(f"[AWS] IoT Job execution details: {json.dumps(status_details, ensure_ascii=False)}")
    return {"status": status, "status_details": status_details}


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


def legacy_main():
    parser = argparse.ArgumentParser(
        description="AWS IoT OTA Update Test for RX72N Envision Kit"
    )
    parser.add_argument("--device-id",
                        help="Device ID (loads config from device_config.json)")
    parser.add_argument("--log-port", default="COM7",
                        help="Log serial port (default: COM7)")
    parser.add_argument("--log-baud", type=int, default=921600,
                        help="Log serial baud rate (default: 921600)")
    parser.add_argument("--cmd-port", default=None,
                        help="Command serial port for reset (default: from device_config)")
    parser.add_argument("--cmd-baud", type=int, default=115200,
                        help="Command serial baud rate (default: 115200)")
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
            args.log_port = device.get("log_port") or os.environ.get("UART_PORT") or "COM7"
        if args.log_baud == 921600:
            args.log_baud = int(device.get("log_baud") or os.environ.get("UART_BAUD_RATE") or 921600)
        if not args.cmd_port:
            args.cmd_port = device.get("command_port")
        if not args.cmd_port:
            args.cmd_port = os.environ.get("COMMAND_PORT")
        if args.cmd_baud == 115200:
            args.cmd_baud = int(device.get("command_baud") or os.environ.get("COMMAND_BAUD_RATE") or 115200)
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
    print(f"[INFO]   Cmd Port : {args.cmd_port} @ {args.cmd_baud}bps" if args.cmd_port else "[INFO]   Cmd Port : (none, no pre-reset)")
    print(f"[INFO]   Timeout  : {args.timeout}s")
    print("=" * 60)

    results = {}
    ota_update_id = None

    try:
        # --- Step 1: OTA Agent 起動確認 ---
        print()
        print("[STEP 1/8] Confirming OTA Agent is running")

        # ログポートを先に開いてからリセットすることで、起動メッセージを確実に捕捉する。
        # prepare_ota → test_ota の間にデバイスが起動完了しアイドル状態になると、
        # "OTA over MQTT demo" メッセージは既に出力済みで COM7 に新しいデータが来ない。
        log_ser = serial.Serial(args.log_port, args.log_baud, timeout=0)
        time.sleep(0.5)
        log_ser.reset_input_buffer()

        if args.cmd_port:
            print(f"[INFO] Sending reset via {args.cmd_port} to capture fresh startup messages")
            try:
                cmd_ser = serial.Serial(args.cmd_port, args.cmd_baud, timeout=1)
                cmd_ser.write(b"reset\r\n")
                time.sleep(1)
                cmd_ser.close()
                print("[INFO] Reset command sent, waiting for reboot...")
                time.sleep(3)
            except SerialException as e:
                print(f"[WARN] Could not send reset via {args.cmd_port}: {e}")
                print("[WARN] Continuing without reset (may fail if device is idle)")

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
            milestones, monitor_version = monitor_ota_progress(log_ser, timeout=args.timeout)

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
                # モニタリング中に既にバージョンが検出されている場合はそれを使用
                # (self_test 後のリブートでバージョンが出力され、monitor が消費済み)
                if monitor_version and monitor_version[2] == args.expected_build:
                    print(f"[PASS] New version already confirmed during monitoring: "
                          f"{monitor_version[0]}.{monitor_version[1]}.{monitor_version[2]}")
                    results["new_version"] = True
                else:
                    if monitor_version:
                        print(f"[INFO] Monitor saw version {monitor_version[0]}.{monitor_version[1]}.{monitor_version[2]}, "
                              f"expected build={args.expected_build}, waiting for correct version...")
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

    except SerialException as e:
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


def open_log_port(args):
    """ログ UART を開き、必要なら reset を送る。"""
    require_serial_support()

    log_ser = serial.Serial(args.log_port, args.log_baud, timeout=0)
    time.sleep(0.5)
    log_ser.reset_input_buffer()

    if args.cmd_port:
        print(f"[INFO] Sending reset via {args.cmd_port} to capture fresh startup messages")
        try:
            cmd_ser = serial.Serial(args.cmd_port, args.cmd_baud, timeout=1)
            cmd_ser.write(b"reset\r\n")
            time.sleep(1)
            cmd_ser.close()
            print("[INFO] Reset command sent, waiting for reboot...")
            time.sleep(3)
        except SerialException as exc:
            print(f"[WARN] Could not send reset via {args.cmd_port}: {exc}")
            print("[WARN] Continuing without reset (may fail if device is idle)")

    return log_ser


def confirm_ota_agent(log_ser):
    """OTA Agent 起動ログを待つ。"""
    agent_detected = False
    detected_version = None
    start = time.time()
    buf = b""

    while (time.time() - start) < 60:
        n = log_ser.in_waiting
        if n > 0:
            buf += log_ser.read(n)
            decoded = buf.decode("utf-8", errors="replace")
            if re.search(r"OTA over MQTT demo", decoded):
                print("[PASS] OTA Agent is running")
                detected_version = parse_version_from_log(decoded)
                if detected_version:
                    print(f"[INFO] Current firmware version: {format_version(detected_version)}")
                agent_detected = True
                break
        else:
            time.sleep(0.2)

    if not agent_detected:
        decoded = buf.decode("utf-8", errors="replace")
        if "MQTT" in decoded or "Subscribed" in decoded:
            print("[WARN] OTA Agent banner not detected, but MQTT activity found")
            agent_detected = True
        else:
            print("[FAIL] OTA Agent not detected within 60s")
            print(f"[DEBUG] Received: {decoded[:300]}")

    return agent_detected, detected_version


def run_create_job_mode(args):
    """S3 upload + OTA job 作成のみを実行する。"""
    results = {
        "stale_ota_cleanup": False,
        "s3_upload": False,
        "ota_job_created": False,
        "ota_job_ready": False,
    }
    s3_key = build_s3_key(args.rsu, args.thing_name)
    metadata = {
        "mode": args.mode,
        "device_id": args.device_id,
        "thing_name": args.thing_name,
        "region": args.region,
        "s3_bucket": args.s3_bucket,
        "s3_key": s3_key,
        "rsu_filename": os.path.basename(args.rsu),
        "skip_upload": args.skip_upload,
    }

    print("=" * 60)
    print("[INFO] AWS IoT OTA create-job phase")
    print(f"[INFO]   Thing    : {args.thing_name}")
    print(f"[INFO]   Region   : {args.region}")
    print(f"[INFO]   S3       : s3://{args.s3_bucket}/{s3_key}")
    print(f"[INFO]   Role ARN : {args.ota_role_arn}")
    print(f"[INFO]   RSU      : {args.rsu} ({os.path.getsize(args.rsu)} bytes)")
    print("=" * 60)

    try:
        if args.create_start_delay > 0:
            print()
            print(f"[INFO] Waiting {args.create_start_delay}s before AWS upload to let UART monitor attach")
            time.sleep(args.create_start_delay)

        print()
        print("[STEP 1/4] Cleaning stale OTA updates")
        if args.skip_ota_update_cleanup:
            print("[SKIP] OTA update cleanup skipped (--skip-ota-update-cleanup)")
            metadata["stale_ota_cleanup"] = {"skipped": True}
        else:
            metadata["stale_ota_cleanup"] = cleanup_stale_ota_updates(args.thing_name, args.region)
        results["stale_ota_cleanup"] = True

        print()
        print("[STEP 2/4] Uploading firmware to S3")
        if args.skip_upload:
            print("[SKIP] S3 upload skipped (--skip-upload)")
            s3_version_id = ""
        else:
            s3_version_id = upload_to_s3(args.rsu, args.s3_bucket, s3_key)
        metadata["s3_version_id"] = s3_version_id
        results["s3_upload"] = True

        print()
        print("[STEP 3/4] Creating OTA update job")
        account_id = get_aws_account_id()
        metadata["account_id"] = account_id
        ota_update_id = create_ota_job(
            args.thing_name, args.s3_bucket, s3_key, s3_version_id,
            args.ota_role_arn, args.region, account_id, args.rsu
        )
        metadata["ota_update_id"] = ota_update_id
        results["ota_job_created"] = True

        print()
        print("[STEP 4/4] Waiting for OTA job to leave CREATE_PENDING")
        job_result = wait_for_ota_job_ready(ota_update_id, args.region, timeout=60)
        metadata["job_ready_status"] = job_result["status"]
        metadata["job_ready_error_info"] = job_result["error_info"]
        metadata["job_ready_aws_job_id"] = job_result.get("aws_job_id")
        results["ota_job_ready"] = job_result["status"] != "CREATE_FAILED"
    except subprocess.CalledProcessError as exc:
        metadata["error"] = str(exc)
        if exc.stderr:
            metadata["stderr"] = exc.stderr[:300]
        print(f"[ERROR] AWS CLI error: {exc}")
        if exc.stderr:
            print(f"[DEBUG] stderr: {exc.stderr[:300]}")
    except Exception as exc:  # pragma: no cover - defensive for CI cleanup path
        metadata["error"] = str(exc)
        print(f"[ERROR] create-job phase failed: {exc}")
    finally:
        metadata["create_job_ok"] = all(results.values())
        write_json(args.metadata_out, metadata)
    if print_summary(results):
        print("[PASS] OTA create-job phase completed successfully")
        return 0
    print("[FAIL] OTA create-job phase failed")
    return 1


def run_monitor_mode(args):
    """UART 監視と新バージョン確認のみを実行する。"""
    results = {
        "agent_ready": False,
        "ota_download": False,
        "new_version": False,
    }
    monitor_payload = {
        "mode": args.mode,
        "device_id": args.device_id,
        "log_port": args.log_port,
        "log_baud": args.log_baud,
        "cmd_port": args.cmd_port,
        "cmd_baud": args.cmd_baud,
        "expected_build": args.expected_build,
        "timeout": args.timeout,
    }
    log_ser = None

    print("=" * 60)
    print("[INFO] AWS IoT OTA monitor phase")
    print(f"[INFO]   Log Port : {args.log_port} @ {args.log_baud}bps")
    print(f"[INFO]   Cmd Port : {args.cmd_port} @ {args.cmd_baud}bps" if args.cmd_port else "[INFO]   Cmd Port : (none, no pre-reset)")
    print(f"[INFO]   Timeout  : {args.timeout}s")
    print("=" * 60)

    try:
        print()
        print("[STEP 1/3] Confirming OTA Agent is running")
        log_ser = open_log_port(args)
        agent_detected, current_version = confirm_ota_agent(log_ser)
        results["agent_ready"] = agent_detected
        monitor_payload["current_version"] = format_version(current_version)
        if not agent_detected:
            raise RuntimeError("OTA Agent was not detected")

        print()
        print("[STEP 2/3] Monitoring OTA progress")
        milestones, monitor_version, stall_hint = monitor_ota_progress(
            log_ser, timeout=args.timeout, port_label=os.path.basename(args.log_port)
        )
        monitor_payload["milestones"] = milestones
        monitor_payload["monitor_version"] = format_version(monitor_version)
        if stall_hint:
            monitor_payload["stall_hint"] = stall_hint

        required = {name for name, info in OTA_MILESTONES.items() if info["required"]}
        required.discard("agent_ready")
        missing = sorted(required - set(milestones.keys()))
        if missing:
            print(f"[WARN] Missing milestones: {', '.join(missing)}")
            monitor_payload["missing_milestones"] = missing
        else:
            print("[PASS] All required OTA milestones detected")
            results["ota_download"] = True

        print()
        print("[STEP 3/3] Verifying new version after reset")
        if args.expected_build:
            if monitor_version and monitor_version[2] == args.expected_build:
                print(f"[PASS] New version already confirmed during monitoring: {format_version(monitor_version)}")
                results["new_version"] = True
            else:
                if monitor_version:
                    print(
                        f"[INFO] Monitor saw version {format_version(monitor_version)}, "
                        f"expected build={args.expected_build}, waiting for correct version..."
                    )
                results["new_version"] = verify_new_version_after_reset(
                    log_ser, args.expected_build, timeout=120
                )
        else:
            print("[SKIP] --expected-build not specified, skipping version check")
            results["new_version"] = True
    except (RuntimeError, SerialException) as exc:
        monitor_payload["error"] = str(exc)
        print(f"[ERROR] monitor phase failed: {exc}")
    except KeyboardInterrupt:
        monitor_payload["error"] = "Interrupted by user"
        print("\n[INFO] Test interrupted by user")
    finally:
        if log_ser:
            log_ser.close()
            print(f"[INFO] Closed {args.log_port}")
        monitor_payload["monitor_ok"] = all(results.values())
        write_json(args.monitor_results_out, monitor_payload)
    if print_summary(results):
        print("[PASS] OTA monitor phase completed successfully")
        return 0
    print("[FAIL] OTA monitor phase failed")
    return 1


def run_finalize_mode(args):
    """AWS 側のジョブ状態確認と cleanup を実行する。"""
    results = {
        "create_job": False,
        "aws_status": False,
    }
    metadata = read_json(args.metadata_in)
    monitor_results = None
    if args.monitor_results_in and os.path.isfile(args.monitor_results_in):
        monitor_results = read_json(args.monitor_results_in)

    s3_bucket = metadata.get("s3_bucket") or args.s3_bucket
    s3_key = metadata.get("s3_key")
    region = metadata.get("region") or args.region or os.environ.get("AWS_DEFAULT_REGION") or "ap-northeast-1"
    ota_update_id = metadata.get("ota_update_id")
    thing_name = metadata.get("thing_name")

    print("=" * 60)
    print("[INFO] AWS IoT OTA finalize phase")
    print(f"[INFO]   Thing    : {metadata.get('thing_name')}")
    print(f"[INFO]   Region   : {region}")
    print(f"[INFO]   S3       : s3://{s3_bucket}/{s3_key}" if s3_bucket and s3_key else "[INFO]   S3       : (not available)")
    print(f"[INFO]   OTA ID   : {ota_update_id}" if ota_update_id else "[INFO]   OTA ID   : (not available)")
    print("=" * 60)

    if monitor_results:
        print("[INFO] Monitor summary:")
        print(f"[INFO]   monitor_ok: {monitor_results.get('monitor_ok')}")
        if monitor_results.get("monitor_version"):
            print(f"[INFO]   version   : {monitor_results.get('monitor_version')}")

    try:
        results["create_job"] = bool(metadata.get("create_job_ok"))

        print()
        print("[STEP 1/2] Checking AWS OTA job status")
        if ota_update_id:
            job_result = verify_job_status(ota_update_id, region)
            results["aws_status"] = job_result["status"] is not None
            aws_job_id = job_result.get("aws_job_id") or metadata.get("job_ready_aws_job_id")
            if aws_job_id and thing_name:
                print()
                print("[STEP 1.5/2] Checking AWS IoT Job execution status")
                describe_job_execution(aws_job_id, thing_name, region)
        else:
            print("[WARN] ota_update_id not available; skipping AWS status lookup")
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] AWS CLI error during finalize: {exc}")
        if exc.stderr:
            print(f"[DEBUG] stderr: {exc.stderr[:300]}")
    finally:
        if ota_update_id and not args.skip_ota_update_cleanup:
            print()
            print("[CLEANUP] Deleting current OTA update")
            try:
                delete_ota_update(ota_update_id, region)
            except subprocess.CalledProcessError as exc:
                print(f"[WARN] OTA update cleanup failed: {exc}")
                if exc.stderr:
                    print(f"[DEBUG] stderr: {exc.stderr[:300]}")
            except Exception as exc:  # pragma: no cover - cleanup best effort
                print(f"[WARN] OTA update cleanup failed: {exc}")
        elif ota_update_id:
            print("[SKIP] OTA update cleanup skipped (--skip-ota-update-cleanup)")

        if not args.skip_cleanup and s3_bucket and s3_key:
            print()
            print("[STEP 2/2] Cleaning up S3 object")
            cleanup_s3(s3_bucket, s3_key)
        elif args.skip_cleanup:
            print("[SKIP] S3 cleanup skipped (--skip-cleanup)")
        else:
            print("[WARN] S3 cleanup skipped because bucket/key metadata is missing")
    if print_summary(results):
        print("[PASS] OTA finalize phase completed successfully")
        return 0
    print("[FAIL] OTA finalize phase failed")
    return 1


def run_full_mode(args):
    """従来どおり単一ホストで OTA テスト全体を順次実行する。"""
    results = {}
    ota_update_id = None
    s3_key = build_s3_key(args.rsu, args.thing_name)
    log_ser = None

    print("=" * 60)
    print("[INFO] AWS IoT OTA Update Test")
    print(f"[INFO]   Thing    : {args.thing_name}")
    print(f"[INFO]   Region   : {args.region}")
    print(f"[INFO]   S3       : s3://{args.s3_bucket}/{s3_key}")
    print(f"[INFO]   Role ARN : {args.ota_role_arn}")
    print(f"[INFO]   RSU      : {args.rsu} ({os.path.getsize(args.rsu)} bytes)")
    print(f"[INFO]   Log Port : {args.log_port} @ {args.log_baud}bps")
    print(f"[INFO]   Cmd Port : {args.cmd_port} @ {args.cmd_baud}bps" if args.cmd_port else "[INFO]   Cmd Port : (none, no pre-reset)")
    print(f"[INFO]   Timeout  : {args.timeout}s")
    print("=" * 60)

    try:
        print()
        print("[STEP 1/6] Confirming OTA Agent is running")
        log_ser = open_log_port(args)
        agent_detected, current_version = confirm_ota_agent(log_ser)
        results["agent_ready"] = agent_detected
        if not agent_detected:
            raise RuntimeError("OTA Agent was not detected")
        if current_version:
            print(f"[INFO] Current firmware version: {format_version(current_version)}")

        print()
        print("[STEP 2/8] Cleaning stale OTA updates")
        if args.skip_ota_update_cleanup:
            print("[SKIP] OTA update cleanup skipped (--skip-ota-update-cleanup)")
        else:
            cleanup_stale_ota_updates(args.thing_name, args.region)
        results["stale_ota_cleanup"] = True

        print()
        print("[STEP 3/8] Uploading firmware to S3")
        if args.skip_upload:
            print("[SKIP] S3 upload skipped (--skip-upload)")
            s3_version_id = ""
        else:
            s3_version_id = upload_to_s3(args.rsu, args.s3_bucket, s3_key)
        results["s3_upload"] = True

        print()
        print("[STEP 4/8] Creating OTA update job")
        account_id = get_aws_account_id()
        ota_update_id = create_ota_job(
            args.thing_name, args.s3_bucket, s3_key, s3_version_id,
            args.ota_role_arn, args.region, account_id, args.rsu
        )
        results["ota_job_created"] = True

        print()
        print("[STEP 5/8] Waiting for OTA job to leave CREATE_PENDING")
        job_result = wait_for_ota_job_ready(ota_update_id, args.region, timeout=60)
        if job_result["status"] == "CREATE_FAILED":
            print("[FAIL] OTA job CREATE_FAILED - aborting (skip device wait)")
            results["ota_job_ready"] = False
            results["ota_download"] = False
            results["new_version"] = False
            results["aws_status"] = False
            return 1
        results["ota_job_ready"] = True

        print()
        print("[STEP 6/8] Monitoring OTA progress")
        milestones, monitor_version = monitor_ota_progress(
            log_ser, timeout=args.timeout, port_label=os.path.basename(args.log_port)
        )
        required = {name for name, info in OTA_MILESTONES.items() if info["required"]}
        required.discard("agent_ready")
        missing = required - set(milestones.keys())
        if missing:
            print(f"[WARN] Missing milestones: {', '.join(sorted(missing))}")
            results["ota_download"] = False
        else:
            print("[PASS] All required OTA milestones detected")
            results["ota_download"] = True

        print()
        print("[STEP 7/8] Verifying new version after reset")
        if args.expected_build:
            if monitor_version and monitor_version[2] == args.expected_build:
                print(f"[PASS] New version already confirmed during monitoring: {format_version(monitor_version)}")
                results["new_version"] = True
            else:
                if monitor_version:
                    print(
                        f"[INFO] Monitor saw version {format_version(monitor_version)}, "
                        f"expected build={args.expected_build}, waiting for correct version..."
                    )
                results["new_version"] = verify_new_version_after_reset(
                    log_ser, args.expected_build, timeout=120
                )
        else:
            print("[SKIP] --expected-build not specified, skipping version check")
            results["new_version"] = True

        print()
        print("[STEP 8/8] Checking AWS OTA job status")
        if ota_update_id:
            job_result = verify_job_status(ota_update_id, args.region)
            results["aws_status"] = job_result["status"] is not None
        else:
            results["aws_status"] = False
    except (RuntimeError, SerialException) as exc:
        print(f"[ERROR] Serial/monitor error: {exc}")
        results["serial"] = False
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] AWS CLI error: {exc}")
        if exc.stderr:
            print(f"[DEBUG] stderr: {exc.stderr[:300]}")
        results["aws_cli"] = False
    except KeyboardInterrupt:
        print("\n[INFO] Test interrupted by user")
    finally:
        if log_ser:
            log_ser.close()
            print(f"[INFO] Closed {args.log_port}")
        if not args.skip_ota_update_cleanup and ota_update_id:
            print()
            print("[CLEANUP] Deleting current OTA update")
            try:
                delete_ota_update(ota_update_id, args.region)
            except subprocess.CalledProcessError as exc:
                print(f"[WARN] OTA update cleanup failed: {exc}")
                if exc.stderr:
                    print(f"[DEBUG] stderr: {exc.stderr[:300]}")
            except Exception as exc:  # pragma: no cover - cleanup best effort
                print(f"[WARN] OTA update cleanup failed: {exc}")
        if not args.skip_cleanup and ota_update_id:
            print()
            print("[CLEANUP]")
            cleanup_s3(args.s3_bucket, s3_key)

    if print_summary(results):
        print("[PASS] OTA update test completed successfully")
        return 0
    print("[FAIL] OTA update test failed")
    return 1


def main():
    parser = argparse.ArgumentParser(
        description="AWS IoT OTA Update Test for RX72N Envision Kit"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "create-job", "monitor", "finalize"],
        default="full",
        help="Execution mode (default: full)",
    )
    parser.add_argument("--device-id",
                        help="Device ID (loads config from device_config.json)")
    parser.add_argument("--log-port", default=None,
                        help="Log serial port (default: from device config or UART_PORT)")
    parser.add_argument("--log-baud", type=int, default=None,
                        help="Log serial baud rate (default: from device config or UART_BAUD_RATE)")
    parser.add_argument("--cmd-port", default=None,
                        help="Command serial port for reset (default: from device config or COMMAND_PORT)")
    parser.add_argument("--cmd-baud", type=int, default=None,
                        help="Command serial baud rate (default: from device config or COMMAND_BAUD_RATE)")
    parser.add_argument("--rsu",
                        help="Path to v2 .rsu file for OTA update")
    parser.add_argument("--s3-bucket", default=os.environ.get("OTA_S3_BUCKET"),
                        help="S3 bucket name (or env OTA_S3_BUCKET)")
    parser.add_argument("--ota-role-arn", default=os.environ.get("OTA_ROLE_ARN"),
                        help="OTA service role ARN (or env OTA_ROLE_ARN)")
    parser.add_argument("--region", default=None,
                        help="AWS region (default: from device_config.json or AWS_DEFAULT_REGION)")
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
    parser.add_argument("--skip-ota-update-cleanup", action="store_true",
                        help="Skip AWS IoT OTA update cleanup before/after the test")
    parser.add_argument("--metadata-out", default=None,
                        help="Write create-job metadata JSON to this path")
    parser.add_argument("--metadata-in", default=None,
                        help="Read create-job metadata JSON from this path")
    parser.add_argument("--monitor-results-out", default=None,
                        help="Write monitor results JSON to this path")
    parser.add_argument("--monitor-results-in", default=None,
                        help="Read monitor results JSON from this path")
    parser.add_argument("--create-start-delay", type=int, default=0,
                        help="Delay before create-job starts AWS upload (seconds)")
    args = parser.parse_args()

    args = load_device_defaults(args)

    if args.mode == "full":
        validate_serial_args(parser, args)
        validate_create_args(parser, args)
        return run_full_mode(args)
    if args.mode == "create-job":
        validate_create_args(parser, args)
        return run_create_job_mode(args)
    if args.mode == "monitor":
        validate_serial_args(parser, args)
        return run_monitor_mode(args)

    validate_finalize_args(parser, args)
    return run_finalize_mode(args)


if __name__ == "__main__":
    sys.exit(main())
