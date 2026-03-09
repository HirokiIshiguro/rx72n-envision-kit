#!/usr/bin/env bash

# Source this helper from GitLab CI device jobs.
# It prefers a per-job virtual environment on Linux, and falls back to the
# system Python only when the required modules are already installed.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "source this file from a shell script instead of executing it directly" >&2
  exit 1
fi

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
venv_dir="${PI_VENV_DIR:-${repo_root}/.venv-pi}"

check_system_requirement() {
  case "$1" in
    pyserial)
      python3 -c "import serial" >/dev/null 2>&1
      ;;
    cryptography)
      python3 -c "import cryptography" >/dev/null 2>&1
      ;;
    pycryptodome)
      python3 -c "from Crypto.Hash import SHA256" >/dev/null 2>&1
      ;;
    awscli)
      command -v aws >/dev/null 2>&1
      ;;
    *)
      return 0
      ;;
  esac
}

install_user_requirements() {
  if ! python3 -m pip --version >/dev/null 2>&1; then
    echo "[ERROR] python3 -m pip is unavailable; cannot install missing dependencies." >&2
    return 1
  fi

  export PATH="${HOME}/.local/bin:${PATH}"
  python3 -m pip install --quiet --user "$@"
}

if [[ -d "${venv_dir}" ]] || python3 -m venv "${venv_dir}" >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  . "${venv_dir}/bin/activate"
  export PIP_DISABLE_PIP_VERSION_CHECK=1
  if [[ "$#" -gt 0 ]]; then
    python3 -m pip install --quiet "$@"
  fi
  return 0
fi

echo "[WARN] python3 -m venv is unavailable; falling back to system Python" >&2

missing=0
for requirement in "$@"; do
  if ! check_system_requirement "${requirement}"; then
    echo "[ERROR] Missing system dependency: ${requirement}" >&2
    missing=1
  fi
done

if [[ "${missing}" -ne 0 ]]; then
  echo "[WARN] Installing missing dependencies into the gitlab-runner user site-packages." >&2
  install_user_requirements "$@"
fi

export PIP_DISABLE_PIP_VERSION_CHECK=1
