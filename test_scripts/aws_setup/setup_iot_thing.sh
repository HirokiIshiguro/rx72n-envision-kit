#!/usr/bin/env bash
#
# AWS IoT Core Setup Script for RX72N Envision Kit
#
# AWS IoT Core に Thing, 証明書, ポリシーを作成し、
# デバイスプロビジョニングに必要なファイルを出力する。
#
# 前提:
#   - AWS CLI v2 がインストール済み
#   - aws configure / aws sso login 等で認証済み
#   - jq がインストール済み（JSON パース用）
#
# 使い方:
#   bash setup_iot_thing.sh [--thing-name NAME] [--region REGION] [--output-dir DIR]
#
# 出力:
#   <output-dir>/certificate.pem.crt  — デバイス証明書
#   <output-dir>/private.pem.key      — 秘密鍵
#   <output-dir>/AmazonRootCA1.pem    — AWS ルート CA
#   <output-dir>/endpoint.txt         — MQTT ブローカーエンドポイント
#   <output-dir>/thing_info.json      — Thing/証明書/ポリシー情報

set -euo pipefail

# --- デフォルト値 ---
THING_NAME="rx72n-envision-kit"
REGION="${AWS_DEFAULT_REGION:-ap-northeast-1}"
OUTPUT_DIR="./certs"
POLICY_NAME="rx72n-envision-kit-policy"

# --- 引数パース ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --thing-name) THING_NAME="$2"; shift 2 ;;
        --region)     REGION="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--thing-name NAME] [--region REGION] [--output-dir DIR]"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "============================================================"
echo "[INFO] AWS IoT Core Setup for RX72N Envision Kit"
echo "[INFO]   Thing Name  : ${THING_NAME}"
echo "[INFO]   Region      : ${REGION}"
echo "[INFO]   Output Dir  : ${OUTPUT_DIR}"
echo "[INFO]   Policy Name : ${POLICY_NAME}"
echo "============================================================"

# --- 前提チェック ---
if ! command -v aws &> /dev/null; then
    echo "[ERROR] AWS CLI is not installed. Install it first."
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "[ERROR] jq is not installed. Install it first."
    echo "  Windows: winget install jqlang.jq"
    echo "  macOS:   brew install jq"
    exit 1
fi

# 認証チェック
if ! aws sts get-caller-identity --region "${REGION}" > /dev/null 2>&1; then
    echo "[ERROR] AWS CLI is not authenticated. Run 'aws configure' first."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region "${REGION}")
echo "[INFO] AWS Account: ${ACCOUNT_ID}"

# --- 出力ディレクトリ作成 ---
mkdir -p "${OUTPUT_DIR}"

# --- Step 1: Thing 作成 ---
echo ""
echo "[STEP 1] Creating IoT Thing: ${THING_NAME}"
if aws iot describe-thing --thing-name "${THING_NAME}" --region "${REGION}" > /dev/null 2>&1; then
    echo "[WARN] Thing '${THING_NAME}' already exists. Skipping creation."
else
    aws iot create-thing --thing-name "${THING_NAME}" --region "${REGION}"
    echo "[OK] Thing created: ${THING_NAME}"
fi

# --- Step 2: 証明書 + 秘密鍵の作成 ---
echo ""
echo "[STEP 2] Creating certificate and private key"
CERT_RESPONSE=$(aws iot create-keys-and-certificate \
    --set-as-active \
    --certificate-pem-outfile "${OUTPUT_DIR}/certificate.pem.crt" \
    --private-key-outfile "${OUTPUT_DIR}/private.pem.key" \
    --region "${REGION}" \
    --output json)

CERT_ARN=$(echo "${CERT_RESPONSE}" | jq -r '.certificateArn')
CERT_ID=$(echo "${CERT_RESPONSE}" | jq -r '.certificateId')
echo "[OK] Certificate created:"
echo "  ARN: ${CERT_ARN}"
echo "  ID:  ${CERT_ID}"
echo "  Cert: ${OUTPUT_DIR}/certificate.pem.crt"
echo "  Key:  ${OUTPUT_DIR}/private.pem.key"

# --- Step 3: IoT ポリシー作成 ---
echo ""
echo "[STEP 3] Creating IoT policy: ${POLICY_NAME}"

POLICY_DOC=$(cat <<POLICY_EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iot:Connect",
        "iot:Publish",
        "iot:Subscribe",
        "iot:Receive"
      ],
      "Resource": "arn:aws:iot:${REGION}:${ACCOUNT_ID}:*"
    }
  ]
}
POLICY_EOF
)

if aws iot get-policy --policy-name "${POLICY_NAME}" --region "${REGION}" > /dev/null 2>&1; then
    echo "[WARN] Policy '${POLICY_NAME}' already exists. Skipping creation."
else
    aws iot create-policy \
        --policy-name "${POLICY_NAME}" \
        --policy-document "${POLICY_DOC}" \
        --region "${REGION}" > /dev/null
    echo "[OK] Policy created: ${POLICY_NAME}"
fi

# --- Step 4: ポリシーを証明書にアタッチ ---
echo ""
echo "[STEP 4] Attaching policy to certificate"
aws iot attach-policy \
    --policy-name "${POLICY_NAME}" \
    --target "${CERT_ARN}" \
    --region "${REGION}" 2>/dev/null || true
echo "[OK] Policy '${POLICY_NAME}' attached to certificate"

# --- Step 5: 証明書を Thing にアタッチ ---
echo ""
echo "[STEP 5] Attaching certificate to Thing"
aws iot attach-thing-principal \
    --thing-name "${THING_NAME}" \
    --principal "${CERT_ARN}" \
    --region "${REGION}"
echo "[OK] Certificate attached to Thing '${THING_NAME}'"

# --- Step 6: エンドポイント取得 ---
echo ""
echo "[STEP 6] Getting MQTT broker endpoint"
ENDPOINT=$(aws iot describe-endpoint \
    --endpoint-type iot:Data-ATS \
    --query endpointAddress \
    --output text \
    --region "${REGION}")
echo "${ENDPOINT}" > "${OUTPUT_DIR}/endpoint.txt"
echo "[OK] Endpoint: ${ENDPOINT}"

# --- Step 7: Amazon Root CA ダウンロード ---
echo ""
echo "[STEP 7] Downloading Amazon Root CA"
if command -v curl &> /dev/null; then
    curl -s -o "${OUTPUT_DIR}/AmazonRootCA1.pem" \
        "https://www.amazontrust.com/repository/AmazonRootCA1.pem"
elif command -v wget &> /dev/null; then
    wget -q -O "${OUTPUT_DIR}/AmazonRootCA1.pem" \
        "https://www.amazontrust.com/repository/AmazonRootCA1.pem"
else
    echo "[WARN] Neither curl nor wget found. Download manually:"
    echo "  https://www.amazontrust.com/repository/AmazonRootCA1.pem"
fi
if [[ -f "${OUTPUT_DIR}/AmazonRootCA1.pem" ]]; then
    echo "[OK] Root CA saved: ${OUTPUT_DIR}/AmazonRootCA1.pem"
fi

# --- Step 8: 情報ファイル保存 ---
echo ""
echo "[STEP 8] Saving setup info"
cat > "${OUTPUT_DIR}/thing_info.json" <<INFO_EOF
{
  "thing_name": "${THING_NAME}",
  "certificate_arn": "${CERT_ARN}",
  "certificate_id": "${CERT_ID}",
  "policy_name": "${POLICY_NAME}",
  "endpoint": "${ENDPOINT}",
  "region": "${REGION}",
  "account_id": "${ACCOUNT_ID}"
}
INFO_EOF
echo "[OK] Info saved: ${OUTPUT_DIR}/thing_info.json"

# --- サマリ ---
echo ""
echo "============================================================"
echo "[DONE] AWS IoT Core setup complete!"
echo ""
echo "Next steps:"
echo "  1. Provision the device via UART:"
echo "     python provision_aws.py \\"
echo "       --endpoint ${ENDPOINT} \\"
echo "       --thing-name ${THING_NAME} \\"
echo "       --cert ${OUTPUT_DIR}/certificate.pem.crt \\"
echo "       --key ${OUTPUT_DIR}/private.pem.key"
echo ""
echo "  2. Reset the device and verify MQTT connection"
echo "============================================================"
