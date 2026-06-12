#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# 移除 ROS 路径，避免版本冲突
_bad = [p for p in sys.path if "/opt/ros" in p or "ros/humble" in p]
for _p in _bad:
    sys.path.remove(_p)

if "PYTHONPATH" in os.environ:
    parts = [p for p in os.environ["PYTHONPATH"].split(":") if "/opt/ros" not in p]
    os.environ["PYTHONPATH"] = ":".join(parts)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from panthera_gui.app_qt import main

if __name__ == "__main__":
    main()
