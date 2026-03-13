#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

loops=20
sleep_seconds=1
mode="sig"
device="RX72x"
tool="e2l"
speed="1500K"
auth_id="FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
rfp_cli="${RFP_CLI:-rfp-cli}"
output_dir=""
mot=""
port_envs=()

usage() {
  cat <<'EOF'
Usage: run_rfp_soak_test.sh --output-dir DIR [options]

Options:
  --output-dir DIR       Directory to store per-iteration logs and snapshots
  --loops N             Number of iterations (default: 20)
  --sleep-seconds N     Delay between iterations (default: 1)
  --mode MODE           sig | flash_boot (default: sig)
  --device NAME         RFP device name (default: RX72x)
  --tool NAME           RFP tool spec (default: e2l)
  --speed VALUE         RFP speed (default: 1500K)
  --auth-id HEX         Authentication ID (default: all F)
  --rfp-cli PATH        RFP CLI executable (default: rfp-cli or $RFP_CLI)
  --mot PATH            Required for flash_boot mode
  --port-env NAME       Environment variable name to snapshot (repeatable)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      output_dir="$2"
      shift 2
      ;;
    --loops)
      loops="$2"
      shift 2
      ;;
    --sleep-seconds)
      sleep_seconds="$2"
      shift 2
      ;;
    --mode)
      mode="$2"
      shift 2
      ;;
    --device)
      device="$2"
      shift 2
      ;;
    --tool)
      tool="$2"
      shift 2
      ;;
    --speed)
      speed="$2"
      shift 2
      ;;
    --auth-id)
      auth_id="$2"
      shift 2
      ;;
    --rfp-cli)
      rfp_cli="$2"
      shift 2
      ;;
    --mot)
      mot="$2"
      shift 2
      ;;
    --port-env)
      port_envs+=("$2")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$output_dir" ]]; then
  echo "--output-dir is required" >&2
  usage >&2
  exit 2
fi

case "$mode" in
  sig)
    ;;
  flash_boot)
    if [[ -z "$mot" ]]; then
      echo "--mot is required for flash_boot mode" >&2
      exit 2
    fi
    if [[ ! -f "$mot" ]]; then
      echo "MOT file not found: $mot" >&2
      exit 2
    fi
    ;;
  *)
    echo "Unsupported mode: $mode" >&2
    exit 2
    ;;
esac

mkdir -p "$output_dir"
summary_tsv="$output_dir/summary.tsv"
summary_txt="$output_dir/summary.txt"

snapshot_state() {
  local name="$1"
  RFP_STATE_DEVICE="$device" bash "$script_dir/print_pi_hardware_state.sh" "${port_envs[@]}" \
    >"$output_dir/${name}.hardware_state.log" 2>&1 || true
}

run_list_tools() {
  "$rfp_cli" -device "$device" -list-tools
}

run_rfp_iteration() {
  case "$mode" in
    sig)
      "$rfp_cli" -device "$device" -tool "$tool" -if fine -speed "$speed" \
        -auth id "$auth_id" -sig -run -noquery
      ;;
    flash_boot)
      "$rfp_cli" -device "$device" -tool "$tool" -if fine -speed "$speed" \
        -auth id "$auth_id" -erase-chip -noquery
      "$rfp_cli" -device "$device" -tool "$tool" -if fine -speed "$speed" \
        -auth id "$auth_id" -p "$mot" -v -run -noquery
      ;;
  esac
}

{
  echo "timestamp_start=$(date -Is)"
  echo "mode=$mode"
  echo "device=$device"
  echo "tool=$tool"
  echo "speed=$speed"
  echo "loops=$loops"
  echo "sleep_seconds=$sleep_seconds"
  if [[ -n "$mot" ]]; then
    echo "mot=$mot"
  fi
} >"$summary_txt"

printf "iteration\ttimestamp\tlist_tools_status\tserial_present\trfp_status\n" >"$summary_tsv"
snapshot_state "initial"

for ((i = 1; i <= loops; i++)); do
  iteration_prefix="$output_dir/iter_$(printf '%03d' "$i")"
  list_log="${iteration_prefix}.list-tools.log"
  rfp_log="${iteration_prefix}.rfp.log"
  timestamp="$(date -Is)"

  set +e
  run_list_tools >"$list_log" 2>&1
  list_status=$?
  set -e

  serial_present="no"
  if grep -Eq '^[[:space:]]+[A-Za-z0-9:]+' "$list_log"; then
    serial_present="yes"
  fi

  set +e
  run_rfp_iteration >"$rfp_log" 2>&1
  rfp_status=$?
  set -e

  printf "%s\t%s\t%s\t%s\t%s\n" "$i" "$timestamp" "$list_status" "$serial_present" "$rfp_status" >>"$summary_tsv"
  echo "iteration=$i list_tools_status=$list_status serial_present=$serial_present rfp_status=$rfp_status" >>"$summary_txt"

  if [[ "$rfp_status" -ne 0 ]]; then
    echo "failure_iteration=$i" >>"$summary_txt"
    snapshot_state "failure_iter_$(printf '%03d' "$i")"
    exit "$rfp_status"
  fi

  sleep "$sleep_seconds"
done

snapshot_state "final"
echo "result=success" >>"$summary_txt"
