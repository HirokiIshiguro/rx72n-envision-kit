#!/usr/bin/env bash
set -euo pipefail

workspace=""
output_dir=""
mot=""
script_root=""
iterations=10
speed="1500K"
tool="e2l"
device="RX72x"
auth_id="FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"

usage() {
  cat <<'EOF'
Usage: run_rfp_batch.sh --workspace DIR --output-dir DIR --mot PATH [options]

Options:
  --workspace DIR     Repository workspace to execute from
  --script-root DIR   Directory containing run_rfp_soak_test.sh (default: <workspace>/tools/ci)
  --output-dir DIR    Base directory for per-run outputs
  --mot PATH          Path to boot loader MOT file
  --iterations N      Number of one-shot runs (default: 10)
  --speed VALUE       RFP speed (default: 1500K)
  --tool VALUE        RFP tool (default: e2l)
  --device VALUE      RFP device name (default: RX72x)
  --auth-id HEX       Authentication ID (default: all F)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace)
      workspace="$2"
      shift 2
      ;;
    --output-dir)
      output_dir="$2"
      shift 2
      ;;
    --script-root)
      script_root="$2"
      shift 2
      ;;
    --mot)
      mot="$2"
      shift 2
      ;;
    --iterations)
      iterations="$2"
      shift 2
      ;;
    --speed)
      speed="$2"
      shift 2
      ;;
    --tool)
      tool="$2"
      shift 2
      ;;
    --device)
      device="$2"
      shift 2
      ;;
    --auth-id)
      auth_id="$2"
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

if [[ -z "$workspace" || -z "$output_dir" || -z "$mot" ]]; then
  echo "--workspace, --output-dir, and --mot are required" >&2
  usage >&2
  exit 2
fi

if [[ ! -d "$workspace" ]]; then
  echo "Workspace not found: $workspace" >&2
  exit 2
fi

if [[ -z "$script_root" ]]; then
  script_root="$workspace/tools/ci"
fi

if [[ ! -f "$script_root/run_rfp_soak_test.sh" ]]; then
  echo "run_rfp_soak_test.sh not found under: $script_root" >&2
  exit 2
fi

if [[ ! -f "$mot" ]]; then
  echo "MOT file not found: $mot" >&2
  exit 2
fi

mkdir -p "$output_dir"
summary_file="$output_dir/batch_summary.txt"
: >"$summary_file"

for i in $(seq 1 "$iterations"); do
  echo "batch_run=$i" | tee -a "$summary_file"
  sudo -u gitlab-runner bash -lc "cd '$workspace' && bash '$script_root/run_rfp_soak_test.sh' --output-dir '$output_dir/run_$i' --loops 1 --sleep-seconds 1 --mode flash_boot --device '$device' --tool '$tool' --speed '$speed' --auth-id '$auth_id' --port-env UART_PORT --port-env COMMAND_PORT --mot '$mot'" || exit $?
done
