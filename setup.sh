#!/usr/bin/env bash
# Panthera Control Deck - 一键安装/卸载脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

CONDA_ENV_NAME="panthera_gui"
WHEEL_DIR="${SCRIPT_DIR}/panthera_python/motor_whl"
DESKTOP_DIR="${HOME}/Desktop"
if [[ ! -d "${DESKTOP_DIR}" ]]; then
    DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "${HOME}/Desktop")"
fi
DESKTOP_FILE="${DESKTOP_DIR}/PantheraControlDeck.desktop"
LAUNCHER="${SCRIPT_DIR}/launch.sh"

# ── 颜色输出 ──────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── 卸载模式 ──────────────────────────────────────────────────
if [[ "${1:-}" == "--uninstall" ]]; then
    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║     Panthera Control Deck  卸载程序      ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""

    [[ -f "${DESKTOP_FILE}" ]] && rm -f "${DESKTOP_FILE}" && info "桌面图标已删除" || warn "桌面图标不存在"
    [[ -f "${LAUNCHER}" ]]     && rm -f "${LAUNCHER}"     && info "启动脚本已删除" || warn "启动脚本不存在"

    echo ""
    read -rp "是否同时删除 conda 环境 '${CONDA_ENV_NAME}'？[y/N] " confirm
    if [[ "${confirm,,}" == "y" ]]; then
        CONDA_BIN=""
        for candidate in \
            "${CONDA_EXE:-}" \
            "$(command -v conda 2>/dev/null || true)" \
            "${HOME}/anaconda3/bin/conda" \
            "${HOME}/miniconda3/bin/conda"; do
            if [[ -n "${candidate}" && -x "${candidate}" ]]; then
                CONDA_BIN="${candidate}"; break
            fi
        done
        if [[ -n "${CONDA_BIN}" ]]; then
            "${CONDA_BIN}" env remove -n "${CONDA_ENV_NAME}" -y && info "conda 环境已删除"
        else
            warn "未找到 conda，请手动运行: conda env remove -n ${CONDA_ENV_NAME}"
        fi
    fi

    echo ""
    info "卸载完成"
    exit 0
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     Panthera Control Deck  安装程序      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. 查找 conda ─────────────────────────────────────────────
info "查找 conda..."
CONDA_BIN=""
for candidate in \
    "${CONDA_EXE:-}" \
    "$(command -v conda 2>/dev/null || true)" \
    "${HOME}/anaconda3/bin/conda" \
    "${HOME}/miniconda3/bin/conda" \
    "/opt/conda/bin/conda"; do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
        CONDA_BIN="${candidate}"
        break
    fi
done

[[ -n "${CONDA_BIN}" ]] || error "未找到 conda，请先安装 Anaconda 或 Miniconda"
info "conda: ${CONDA_BIN}"

# ── 切换到中科大源（避免清华源 403 问题）────────────────────
info "配置 conda 镜像源（中科大）..."
"${CONDA_BIN}" config --remove-key channels 2>/dev/null || true
"${CONDA_BIN}" config --add channels defaults
"${CONDA_BIN}" config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/conda-forge/
"${CONDA_BIN}" config --set channel_priority flexible

# ── 辅助函数：自动选择匹配的 wheel 安装 ──────────────────────
_install_wheel() {
    local env_name="$1"
    local py_bin="$2"
    local arch; arch="$(uname -m)"
    local pyver; pyver="$("${py_bin}" -c 'import sys; print(f"cp{sys.version_info.major}{sys.version_info.minor}")')"
    local whl; whl="$(ls "${WHEEL_DIR}/hightorque_robot-"*"-${pyver}-${pyver}-linux_${arch}.whl" 2>/dev/null | sort -V | tail -1)"
    if [[ -n "${whl}" ]]; then
        info "安装 hightorque_robot: $(basename "${whl}")..."
        "${CONDA_BIN}" run -n "${env_name}" pip install "${whl}" --quiet
        info "hightorque_robot 安装完成"
    else
        warn "未找到匹配的 wheel（arch=${arch}, python=${pyver}），请手动安装"
        warn "可用 wheel: $(ls "${WHEEL_DIR}/" 2>/dev/null | tr '\n' ' ')"
    fi
}

# ── 2. 询问创建新环境还是使用已有环境 ───────────────────────
echo ""
echo "请选择安装方式："
echo "  1) 创建新的 conda 环境 (panthera_gui)"
echo "  2) 使用已有的 conda 环境"
echo ""
read -rp "请输入选项 [1/2]: " INSTALL_MODE

if [[ "${INSTALL_MODE}" == "1" ]]; then
    # 创建新环境
    CONDA_ENV_NAME="panthera_gui"

    if "${CONDA_BIN}" env list | grep -q "^${CONDA_ENV_NAME} "; then
        info "conda 环境 '${CONDA_ENV_NAME}' 已存在，将使用现有环境"
    else
        info "创建 conda 环境: ${CONDA_ENV_NAME} (Python 3.10)..."
        "${CONDA_BIN}" create -n "${CONDA_ENV_NAME}" python=3.10 pip numpy pinocchio scipy -c conda-forge -y
        info "conda 环境创建完成"
    fi

    PYTHON_BIN="$("${CONDA_BIN}" run -n "${CONDA_ENV_NAME}" which python)"
    info "Python: ${PYTHON_BIN}"

    # 安装 hightorque_robot wheel
    _install_wheel "${CONDA_ENV_NAME}" "${PYTHON_BIN}"

    # 安装所有依赖（--ignore-installed 确保装进 conda 环境而非 ~/.local）
    info "安装依赖（pin/scipy/mujoco/PyQt6 等）..."
    PYTHONNOUSERSITE=1 "${CONDA_BIN}" run -n "${CONDA_ENV_NAME}" pip install \
        -r "${SCRIPT_DIR}/panthera_python/requirements.txt" \
        "mujoco>=3.0.0" \
        "PyQt6>=6.6.0" \
        "Pillow>=10.0.0" \
        --ignore-installed --quiet
    info "依赖安装完成"

elif [[ "${INSTALL_MODE}" == "2" ]]; then
    # 使用已有环境
    echo ""
    echo "当前可用的 conda 环境："
    "${CONDA_BIN}" env list | grep -v "^#"
    echo ""
    read -rp "请输入要使用的 conda 环境名称（已安装 hightorque_robot 的环境）: " SELECTED_ENV
    [[ -n "${SELECTED_ENV}" ]] || error "未输入环境名称"

    # 验证环境存在
    "${CONDA_BIN}" env list | grep -q "^${SELECTED_ENV} " || error "环境 '${SELECTED_ENV}' 不存在"
    info "使用环境: ${SELECTED_ENV}"

    PYTHON_BIN="$("${CONDA_BIN}" run -n "${SELECTED_ENV}" which python)"
    info "Python: ${PYTHON_BIN}"

    # 安装 hightorque_robot wheel
    _install_wheel "${SELECTED_ENV}" "${PYTHON_BIN}"

    # 安装所有依赖（--ignore-installed 确保装进 conda 环境而非 ~/.local）
    info "安装依赖（pin/scipy/mujoco/PyQt6 等）..."
    PYTHONNOUSERSITE=1 "${CONDA_BIN}" run -n "${SELECTED_ENV}" pip install \
        -r "${SCRIPT_DIR}/panthera_python/requirements.txt" \
        "mujoco>=3.0.0" \
        "PyQt6>=6.6.0" \
        "Pillow>=10.0.0" \
        --ignore-installed --quiet
    info "依赖安装完成"

else
    error "无效的选项，请输入 1 或 2"
fi

# ── 6. 创建桌面启动脚本 ───────────────────────────────────────
LAUNCHER="${SCRIPT_DIR}/launch.sh"
cat > "${LAUNCHER}" << EOF
#!/usr/bin/env bash
# Panthera Control Deck 启动脚本（自动生成）
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"

# 过滤掉 ROS 和 cmeel 路径，避免 pinocchio 版本冲突
CLEAN_PYTHONPATH=""
IFS=':' read -ra PARTS <<< "\${PYTHONPATH:-}"
for part in "\${PARTS[@]}"; do
    [[ "\${part}" == *"/opt/ros"* ]] && continue
    [[ "\${part}" == *"cmeel"* ]] && continue
    CLEAN_PYTHONPATH="\${CLEAN_PYTHONPATH:+\${CLEAN_PYTHONPATH}:}\${part}"
done
export PYTHONPATH="\${SCRIPT_DIR}:\${CLEAN_PYTHONPATH}"
export PYTHONNOUSERSITE=1

exec "${PYTHON_BIN}" "\${SCRIPT_DIR}/panthera_gui/run_qt.py" "\$@"
EOF
chmod +x "${LAUNCHER}"
info "启动脚本已创建: ${LAUNCHER}"

# ── 7. 创建桌面图标 ───────────────────────────────────────────
ICON_PATH="${SCRIPT_DIR}/panthera_gui/assets/panthera-control-deck.svg"
[[ -f "${ICON_PATH}" ]] || ICON_PATH="applications-science"

# 查找桌面目录
DESKTOP_DIR="${HOME}/Desktop"
if [[ ! -d "${DESKTOP_DIR}" ]]; then
    DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "${HOME}/Desktop")"
fi
if [[ ! -d "${DESKTOP_DIR}" ]]; then
    mkdir -p "${DESKTOP_DIR}"
fi

DESKTOP_FILE="${DESKTOP_DIR}/PantheraControlDeck.desktop"

cat > "${DESKTOP_FILE}" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Panthera Control Deck
Comment=Panthera-HT 机械臂控制界面
Exec=${LAUNCHER}
Icon=${ICON_PATH}
Terminal=false
Categories=Science;Robotics;
StartupNotify=true
EOF
chmod +x "${DESKTOP_FILE}"

# 标记为可信任（Ubuntu）
if command -v gio >/dev/null 2>&1; then
    gio set "${DESKTOP_FILE}" metadata::trusted true 2>/dev/null || true
fi

info "桌面图标已创建: ${DESKTOP_FILE}"

# ── 8. 配置串口权限（udev 规则）────────────────────────────────
UDEV_RULE_FILE="/etc/udev/rules.d/99-panthera-serial.rules"
UDEV_RULE='KERNEL=="ttyACM*", MODE="0777"'

echo ""
info "配置串口权限（ttyACM*）..."
if [[ -f "${UDEV_RULE_FILE}" ]] && grep -q 'ttyACM' "${UDEV_RULE_FILE}" 2>/dev/null; then
    info "串口 udev 规则已存在，跳过"
else
    echo "${UDEV_RULE}" | sudo tee "${UDEV_RULE_FILE}" > /dev/null
    sudo udevadm control --reload-rules
    info "串口权限规则已写入: ${UDEV_RULE_FILE}"
    info "重新插拔 USB 后生效（或运行: sudo udevadm trigger）"
fi

# ── 完成 ──────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║           安装完成！                     ║"
echo "║                                          ║"
echo "║  双击桌面图标启动，或运行：              ║"
echo "║    bash launch.sh                        ║"
echo "║                                          ║"
echo "║  串口权限已配置，重插 USB 后生效         ║"
echo "╚══════════════════════════════════════════╝"
echo ""
