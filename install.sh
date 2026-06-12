#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

LAUNCH_SCRIPT="./panthera_gui/launch_panthera_gui.sh"
INSTALL_LAUNCHER_SCRIPT="./panthera_gui/deploy/install_desktop_launcher.sh"
USE_CONDA_ENV_SCRIPT="./panthera_gui/deploy/use_conda_env.sh"

CONDA_ENV_NAME=""
PYTHON_BIN=""
RUN_SELF_CHECK=0
NO_LAUNCH=0

usage() {
  cat <<'EOF'
Usage: bash ./install.sh [--conda-env ENV] [--python PATH] [--self-check] [--no-launch]

Installs the local desktop launcher for this repository and opens Panthera GUI.
Recommended customer flow after launch:
  1. Choose the local conda environment
  2. Click "设为启动环境"
  3. Click "环境检查"
  4. Click "安装桌面图标"
EOF
}

find_conda_bin() {
  local candidates=()

  if [[ -n "${CONDA_EXE:-}" ]]; then
    candidates+=("${CONDA_EXE}")
  fi
  if command -v conda >/dev/null 2>&1; then
    candidates+=("$(command -v conda)")
  fi

  candidates+=(
    "${HOME}/anaconda3/bin/conda"
    "${HOME}/anaconda3/condabin/conda"
    "${HOME}/miniconda3/bin/conda"
    "${HOME}/miniconda3/condabin/conda"
    "/opt/conda/bin/conda"
    "/opt/conda/condabin/conda"
  )

  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --conda-env)
      [[ $# -ge 2 ]] || { echo "Missing value for --conda-env" >&2; exit 2; }
      CONDA_ENV_NAME="$2"
      shift 2
      ;;
    --python)
      [[ $# -ge 2 ]] || { echo "Missing value for --python" >&2; exit 2; }
      PYTHON_BIN="$2"
      shift 2
      ;;
    --self-check)
      RUN_SELF_CHECK=1
      shift
      ;;
    --no-launch)
      NO_LAUNCH=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ -x "${LAUNCH_SCRIPT}" ]] || { echo "Launcher script not found: ${LAUNCH_SCRIPT}" >&2; exit 1; }
[[ -x "${INSTALL_LAUNCHER_SCRIPT}" ]] || { echo "Desktop installer not found: ${INSTALL_LAUNCHER_SCRIPT}" >&2; exit 1; }

echo "Panthera Control Deck installer"
echo "Repo: ."

if CONDA_BIN="$(find_conda_bin)"; then
  echo "[OK] conda found: ${CONDA_BIN}"
else
  echo "[WARN] conda not found in PATH or common install locations"
  echo "[INFO] You can still open the GUI in guide mode and choose a Python runtime manually"
fi

if [[ -n "${CONDA_ENV_NAME}" ]]; then
  "${USE_CONDA_ENV_SCRIPT}" "${CONDA_ENV_NAME}"
  echo "[OK] preferred GUI startup env: ${CONDA_ENV_NAME}"
else
  echo "[INFO] If this is the first install, choose the target conda environment inside the GUI"
fi

"${INSTALL_LAUNCHER_SCRIPT}"

echo
echo "Recommended next steps in the GUI:"
echo "  1. 选择本机 conda 环境"
echo "  2. 点击 设为启动环境"
echo "  3. 点击 环境检查"
echo "  4. 点击 安装桌面图标"

if [[ ${NO_LAUNCH} -eq 1 ]]; then
  echo
  echo "Launcher installed. Start later with:"
  echo "  ./panthera_gui/launch_panthera_gui.sh"
  exit 0
fi

LAUNCH_ARGS=()
if [[ -n "${CONDA_ENV_NAME}" ]]; then
  LAUNCH_ARGS+=("--conda-env" "${CONDA_ENV_NAME}")
fi
if [[ -n "${PYTHON_BIN}" ]]; then
  LAUNCH_ARGS+=("--python" "${PYTHON_BIN}")
fi
if [[ ${RUN_SELF_CHECK} -eq 1 ]]; then
  LAUNCH_ARGS+=("--self-check")
fi

exec "${LAUNCH_SCRIPT}" "${LAUNCH_ARGS[@]}"
