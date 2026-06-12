# Panthera GUI

这是 Panthera-HT 的 PyQt6 本地控制界面，保留 Qt 主线代码和机器人控制相关逻辑。

## 安装

```bash
pip install -r panthera_gui/requirements_qt.txt
```

## 运行

```bash
python panthera_gui/run_qt.py
```

或：

```bash
./panthera_gui/launch_panthera_gui.sh
```

## 当前保留内容

- `app_qt.py`：Qt 主窗口和页面逻辑
- `run_qt.py`：Qt 入口
- `kinematic_preview_qt.py`：MuJoCo 预览组件
- `robot_backend.py`：机器人后端和 SDK 例程调度
- `requirements_qt.txt`：Qt 依赖

## 说明

- 默认读取 `panthera_python/robot_param/Follower.yaml`
- GUI 直接调用 `panthera_python/scripts/Panthera_lib/Panthera.py`
- 目标机器仍需要具备串口权限、OpenGL 和 MuJoCo 运行条件
