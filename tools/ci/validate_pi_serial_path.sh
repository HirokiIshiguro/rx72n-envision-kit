#!/usr/bin/env bash

set -euo pipefail

list_serial_devices() {
  if [[ -d /dev/serial/by-id ]]; then
    echo "[INFO] Available /dev/serial/by-id entries:"
    ls -l /dev/serial/by-id
  else
    echo "[WARN] /dev/serial/by-id is not available on this runner."
  fi
}

validate_one() {
  local name="$1"
  local value="${!name:-}"

  if [[ -z "$value" ]]; then
    echo "[ERROR] ${name} is not set." >&2
    list_serial_devices
    return 1
  fi

  if [[ "$value" =~ ^COM[0-9]+$ ]]; then
    echo "[ERROR] ${name} is set to Windows-style serial port '${value}' on a Linux runner." >&2
    echo "[ERROR] Update the CI/CD variable to a Linux path such as /dev/serial/by-id/... ." >&2
    list_serial_devices
    return 1
  fi

  if [[ "$value" != /dev/* ]]; then
    echo "[WARN] ${name} does not start with /dev/: ${value}" >&2
  fi

  if [[ ! -e "$value" ]]; then
    echo "[ERROR] ${name} does not exist: ${value}" >&2
    list_serial_devices
    return 1
  fi

  echo "[INFO] ${name}=${value}"
}

if [[ "$#" -eq 0 ]]; then
  echo "usage: validate_pi_serial_path.sh <ENV_VAR_NAME> [<ENV_VAR_NAME> ...]" >&2
  exit 1
fi

for name in "$@"; do
  validate_one "$name"
done
