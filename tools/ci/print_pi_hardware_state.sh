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

  echo
  echo "--- lsusb -t ---"
  lsusb -t || true
fi

if command -v rfp-cli >/dev/null 2>&1; then
  echo
  echo "--- rfp-cli -list-tools ---"
  rfp_device="${RFP_STATE_DEVICE:-RX72x}"
  rfp-cli -device "$rfp_device" -list-tools || true
fi

if command -v journalctl >/dev/null 2>&1; then
  echo
  echo "--- journalctl -k -n 80 ---"
  if sudo -n true 2>/dev/null; then
    sudo -n journalctl -k -n 80 --no-pager || true
  else
    journalctl -k -n 80 --no-pager || true
  fi
fi

if command -v dmesg >/dev/null 2>&1; then
  echo
  echo "--- dmesg | tail -n 80 ---"
  if sudo -n true 2>/dev/null; then
    sudo -n dmesg | tail -n 80 || true
  else
    dmesg | tail -n 80 || true
  fi
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
