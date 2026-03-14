#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <output-prefix> <command> [args...]" >&2
  exit 2
fi

output_prefix="$1"
shift

output_dir="$(dirname "$output_prefix")"
mkdir -p "$output_dir"

pcap_file="${output_prefix}.pcapng"
summary_file="${output_prefix}.summary.txt"
meta_file="${output_prefix}.meta.txt"
capture_log_file="${output_prefix}.capture.log"

iface="${PI_PACKET_CAPTURE_INTERFACE:-eth0}"
filter="${PI_PACKET_CAPTURE_FILTER:-arp or port 67 or port 68 or udp port 53 or tcp port 8883}"
capture_started=0
capture_pid=""

write_meta() {
  {
    echo "timestamp=$(date '+%F %T')"
    echo "interface=$iface"
    echo "filter=$filter"
    echo "capture_started=$capture_started"
    echo "capture_pid=${capture_pid:-}"
  } >>"$meta_file"
}

finalize_capture() {
  if [[ "$capture_started" -eq 1 && -n "${capture_pid:-}" ]]; then
    sudo -n kill -INT "$capture_pid" 2>/dev/null || true
    wait "$capture_pid" 2>/dev/null || true
    sudo -n chown "$(id -u):$(id -g)" "$pcap_file" "$capture_log_file" 2>/dev/null || true
  fi

  if [[ -f "$pcap_file" ]]; then
    {
      echo "=== capinfos ==="
      if command -v capinfos >/dev/null 2>&1; then
        capinfos "$pcap_file" || true
      else
        echo "capinfos not found"
      fi
      echo
      echo "=== tshark summary ==="
      if command -v tshark >/dev/null 2>&1; then
        tshark -r "$pcap_file" \
          -Y 'bootp || arp || dns || tcp.port == 8883' \
          -T fields \
          -e frame.number \
          -e frame.time_relative \
          -e _ws.col.Protocol \
          -e eth.src \
          -e eth.dst \
          -e ip.src \
          -e ip.dst \
          -e udp.srcport \
          -e udp.dstport \
          -e dns.qry.name \
          -e dns.flags.response \
          -e dns.a || true
      else
        echo "tshark not found"
      fi
    } >"$summary_file" 2>&1
  fi
}

trap finalize_capture EXIT

: >"$meta_file"
write_meta

if ! command -v tshark >/dev/null 2>&1; then
  echo "tshark_not_found=1" >>"$meta_file"
elif ! ip link show "$iface" >/dev/null 2>&1; then
  echo "interface_missing=1" >>"$meta_file"
elif ! sudo -n true 2>/dev/null; then
  echo "sudo_unavailable=1" >>"$meta_file"
else
  if sudo -n tshark -i "$iface" -f "$filter" -w "$pcap_file" >"$capture_log_file" 2>&1 & then
    capture_pid="$!"
    capture_started=1
    echo "capture_started=1" >>"$meta_file"
    sleep 1
  else
    echo "capture_start_failed=1" >>"$meta_file"
  fi
fi

set +e
"$@"
command_status=$?
set -e

echo "command_exit_status=$command_status" >>"$meta_file"
exit "$command_status"
