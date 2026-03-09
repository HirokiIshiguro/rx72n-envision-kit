#!/usr/bin/env bash
set -euo pipefail

echo "=== Hardware State Snapshot ==="
echo "Timestamp: $(date -Is)"
echo "Host: $(hostname)"
echo "Kernel: $(uname -a)"

if command -v lsusb >/dev/null 2>&1; then
  echo
  echo "--- lsusb ---"
  lsusb
fi

echo
echo "--- /dev/serial/by-id ---"
if [[ -d /dev/serial/by-id ]]; then
  ls -l /dev/serial/by-id
else
  echo "/dev/serial/by-id not found"
fi

for env_name in "$@"; do
  echo
  echo "--- ${env_name} ---"
  port_path="${!env_name:-}"
  if [[ -z "${port_path}" ]]; then
    echo "${env_name} is not set"
    continue
  fi

  echo "configured path: ${port_path}"
  if [[ -e "${port_path}" ]]; then
    echo "exists: yes"
    readlink -f "${port_path}" || true
    ls -l "${port_path}" || true
  else
    echo "exists: no"
  fi
done
