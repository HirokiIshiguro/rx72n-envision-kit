#!/usr/bin/env bash
# Acquire a cross-project device lock on the Raspberry Pi runner.

set -euo pipefail

script_return_or_exit() {
  local code="$1"
  return "$code" 2>/dev/null || exit "$code"
}

if [[ "${DEVICE_LOCK_HELD:-0}" == "1" ]]; then
  script_return_or_exit 0
fi

device_id="${1:-${DEVICE_ID:-}}"
if [[ -z "$device_id" ]]; then
  echo "ERROR: device_id is required (arg1 or DEVICE_ID env var)." >&2
  script_return_or_exit 1
fi

lock_root="${DEVICE_LOCK_ROOT:-/tmp/gitlab-device-locks}"
mkdir -p "$lock_root"

lock_path="$lock_root/${device_id}.lock"
exec {DEVICE_LOCK_FD}>"$lock_path"

echo "[LOCK] Waiting for device lock: ${lock_path}"
flock "$DEVICE_LOCK_FD"

export DEVICE_LOCK_HELD=1
export DEVICE_LOCK_FD
export DEVICE_LOCK_PATH="$lock_path"

echo "[LOCK] Acquired device lock: ${lock_path}"
