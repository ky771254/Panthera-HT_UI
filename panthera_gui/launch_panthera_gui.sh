#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

GUI_ENTRY="./run_qt.py"

usage() {
  printf '%s\n' "Usage: ./panthera_gui/launch_panthera_gui.sh [--python PATH] [--] [gui args...]"
}

PYTHON_BIN="${PANTHERA_GUI_PYTHON:-}"
GUI_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      [[ $# -ge 2 ]] || { echo "Missing value for --python" >&2; exit 2; }
      PYTHON_BIN="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      GUI_ARGS+=("$@")
      break
      ;;
    *)
      GUI_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -n "${PYTHON_BIN}" ]]; then
  :
else
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    echo "python3 not found" >&2
    exit 1
  fi
fi

export PYTHONNOUSERSITE=1

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python runtime not found: ${PYTHON_BIN}" >&2
  echo "Pass --python PATH to select a Python runtime." >&2
  exit 1
fi

exec "${PYTHON_BIN}" "${GUI_ENTRY}" "${GUI_ARGS[@]}"
