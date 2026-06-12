#!/usr/bin/env bash
# Panthera Control Deck 启动脚本（自动生成）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 过滤掉 ROS 和 cmeel 路径，避免 pinocchio 版本冲突
CLEAN_PYTHONPATH=""
IFS=':' read -ra PARTS <<< "${PYTHONPATH:-}"
for part in "${PARTS[@]}"; do
    [[ "${part}" == *"/opt/ros"* ]] && continue
    [[ "${part}" == *"cmeel"* ]] && continue
    CLEAN_PYTHONPATH="${CLEAN_PYTHONPATH:+${CLEAN_PYTHONPATH}:}${part}"
done
export PYTHONPATH="${SCRIPT_DIR}:${CLEAN_PYTHONPATH}"
export PYTHONNOUSERSITE=1

exec "/home/hightorque/anaconda3/envs/panthera_gui/bin/python" "${SCRIPT_DIR}/panthera_gui/run_qt.py" "$@"
