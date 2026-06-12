"""
Panthera Control Deck - PyQt6
多页面导航版本
"""
from __future__ import annotations

import importlib
import queue
import sys
import time
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QPushButton, QScrollArea, QSlider,
    QStackedWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget, QMessageBox,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "panthera_python" / "robot_param" / "Follower.yaml"
JOINT_LIMITS = [(-2.4, -0.1), (2.4, 3.2), (-0.1, 4.0), (-1.6, 1.6), (-1.7, 1.7), (-2.5, 2.5)]
JOINT_LABELS = [f"关节{i}" for i in range(1, 7)] + ["夹爪"]

STYLE = """
QWidget {{
    font-family: ".AppleSystemUIFont", "SF Pro Text", "Segoe UI", "PingFang SC", sans-serif;
    font-size: 13px;
    color: #1d1d1f;
}}
QMainWindow, QWidget#root {{
    background: {bg_start};
}}

QWidget#sidebar {{
    background: rgba(246, 246, 248, 0.92);
    border-right: 1px solid rgba(60, 60, 67, 0.12);
    border-radius: 0;
}}
QWidget#sidebarBorder {{
    background: transparent;
}}
QLabel#appName {{
    color: #1d1d1f;
    font-size: 21px;
    font-weight: 700;
    padding: 14px 16px;
}}
QPushButton#navBtn {{
    background: transparent;
    color: #3a3a3c;
    border: none;
    border-radius: 10px;
    padding: 10px 14px;
    text-align: left;
    font-size: 14px;
    font-weight: 600;
    margin: 2px 10px;
    min-width: 50px;
}}
QPushButton#navBtn:hover {{
    background: rgba(60, 60, 67, 0.08);
}}
QPushButton#navBtn:pressed {{
    background: rgba(60, 60, 67, 0.12);
}}
QPushButton#navBtn[active=true] {{
    background: rgba(0, 122, 255, 0.13);
    color: {accent};
}}

QFrame#card {{
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(60, 60, 67, 0.11);
    border-radius: 14px;
}}

QPushButton {{
    background: #ffffff;
    border: 1px solid rgba(60, 60, 67, 0.18);
    border-radius: 9px;
    padding: 8px 16px;
    font-weight: 600;
    color: #1d1d1f;
}}
QPushButton:hover {{
    background: #f5f5f7;
}}
QPushButton:pressed {{
    background: #e8e8ed;
}}
QPushButton:disabled {{
    background: rgba(242, 242, 247, 0.85);
    color: rgba(60, 60, 67, 0.35);
    border: 1px solid rgba(60, 60, 67, 0.08);
}}
QPushButton#primary {{
    background: {accent};
    border: 1px solid {accent};
    color: white;
    font-weight: 700;
}}
QPushButton#primary:hover {{
    background: {accent_hover};
    border: 1px solid {accent_hover};
}}
QPushButton#primary:pressed {{
    background: {accent_hover};
}}
QPushButton#primary:disabled {{
    background: rgba(0, 122, 255, 0.25);
    color: rgba(255, 255, 255, 0.72);
    border: none;
}}
QPushButton#danger {{
    background: #ff3b30;
    border: 1px solid #ff3b30;
    color: white;
    font-weight: 700;
}}
QPushButton#danger:hover {{
    background: #d70015;
    border: 1px solid #d70015;
}}
QPushButton#danger:pressed {{
    background: #c30010;
}}
QPushButton#success {{
    background: #34c759;
    border: 1px solid #34c759;
    color: white;
    font-weight: 700;
}}
QPushButton#success:hover {{
    background: #2fb34f;
    border: 1px solid #2fb34f;
}}
QPushButton#success:pressed {{
    background: #279845;
}}

QComboBox {{
    background: #ffffff;
    border: 1px solid rgba(60, 60, 67, 0.18);
    border-radius: 9px;
    padding: 8px 12px;
    font-weight: 500;
    color: #1d1d1f;
}}
QComboBox:hover {{
    background: #f9f9fb;
}}
QComboBox:focus {{
    border: 1px solid rgba(0, 122, 255, 0.55);
    background: #ffffff;
}}
QComboBox:disabled {{
    background: rgba(242, 242, 247, 0.85);
    color: rgba(60, 60, 67, 0.35);
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 10px;
}}

QSlider {{
    min-height: 30px;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: rgba(60, 60, 67, 0.16);
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: #ffffff;
    width: 18px;
    height: 18px;
    margin: -7px 0;
    border-radius: 9px;
    border: 1px solid rgba(60, 60, 67, 0.22);
}}
QSlider::handle:horizontal:hover {{
    background: #f5f5f7;
}}
QSlider::handle:horizontal:pressed {{
    background: #e8e8ed;
}}
QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 2px;
}}
QSlider::add-page:horizontal {{
    background: rgba(60, 60, 67, 0.16);
    border-radius: 2px;
}}
QWidget#speedPanel {{
    background: #f2f2f7;
    border: 1px solid rgba(60, 60, 67, 0.09);
    border-radius: 12px;
}}
QLabel#speedTitle {{
    color: #3a3a3c;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#speedValue {{
    color: #1d1d1f;
    background: #ffffff;
    border: 1px solid rgba(60, 60, 67, 0.09);
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 600;
}}
QSlider#speedSlider {{
    min-height: 24px;
}}
QSlider#speedSlider::groove:horizontal {{
    height: 3px;
    background: rgba(60, 60, 67, 0.18);
    border-radius: 1px;
}}
QSlider#speedSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 1px;
}}
QSlider#speedSlider::add-page:horizontal {{
    background: rgba(60, 60, 67, 0.18);
    border-radius: 1px;
}}
QSlider#speedSlider::handle:horizontal {{
    background: {accent};
    width: 12px;
    height: 12px;
    margin: -5px 0;
    border-radius: 6px;
    border: none;
}}
QSlider#speedSlider::handle:horizontal:hover {{
    background: {accent_hover};
}}
QSlider#speedSlider::handle:horizontal:pressed {{
    background: {accent_hover};
}}

QTableWidget {{
    background: #ffffff;
    border: 1px solid rgba(60, 60, 67, 0.11);
    border-radius: 12px;
    gridline-color: rgba(60, 60, 67, 0.08);
    color: #1d1d1f;
}}
QTableWidget::item {{
    padding: 6px;
}}
QHeaderView::section {{
    background: #f5f5f7;
    padding: 8px;
    border: none;
    font-weight: 700;
    color: #3a3a3c;
    border-bottom: 1px solid rgba(60, 60, 67, 0.12);
}}

QTextEdit {{
    background: #1c1c1e;
    color: #f5f5f7;
    border: 1px solid rgba(60, 60, 67, 0.22);
    border-radius: 12px;
    padding: 12px;
    font-family: "SF Mono", "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
}}

QScrollArea {{ border: none; }}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(60, 60, 67, 0.25);
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(60, 60, 67, 0.35);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QLabel#pageTitle {{
    font-size: 26px;
    font-weight: 700;
    color: #1d1d1f;
}}
QLabel#panelTitle {{
    font-size: 15px;
    font-weight: 700;
    color: #1d1d1f;
}}
QLabel#sectionTitle {{
    font-size: 14px;
    font-weight: 700;
    color: #1d1d1f;
    margin-bottom: 4px;
}}
QLabel#cardTitle {{
    font-size: 11px;
    color: #6e6e73;
    font-weight: 700;
    text-transform: uppercase;
}}
QLabel#cardValue {{
    font-size: 24px;
    font-weight: 700;
    color: #1d1d1f;
}}
QLabel#muted {{
    color: #6e6e73;
    font-size: 12px;
}}
QLabel#columnHead {{
    color: #86868b;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#sliderName {{
    color: #3a3a3c;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#sliderCurrent {{
    color: #6e6e73;
    background: #f2f2f7;
    border-radius: 8px;
    padding: 5px 8px;
    font-size: 12px;
}}
QLabel#sliderTarget {{
    color: #1d1d1f;
    background: #f2f2f7;
    border-radius: 8px;
    padding: 5px 8px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#statusOk {{
    color: #34c759;
    font-weight: 700;
}}
QLabel#statusErr {{
    color: #ff3b30;
    font-weight: 700;
}}
"""


# ── 共用小组件 ────────────────────────────────────────────────

class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")

    def layout_v(self, margins=(18, 18, 18, 18), spacing=14) -> QVBoxLayout:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(*margins)
        lay.setSpacing(spacing)
        return lay


class StatusCard(Card):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        lay = self.layout_v()
        self._title = QLabel(title)
        self._title.setObjectName("cardTitle")
        lay.addWidget(self._title)
        self._value = QLabel("-")
        self._value.setObjectName("cardValue")
        lay.addWidget(self._value)

    def set_value(self, v: str):
        self._value.setText(v)


class JointSlider(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(self, label: str, lo: float, hi: float, parent=None):
        super().__init__(parent)
        self.lo, self.hi = lo, hi
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(12)

        lbl = QLabel(label)
        lbl.setObjectName("sliderName")
        lbl.setMinimumWidth(68)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(lbl)

        self._cur = QLabel("—")
        self._cur.setObjectName("sliderCurrent")
        self._cur.setMinimumWidth(110)
        self._cur.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._cur)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(500)
        self._slider.valueChanged.connect(self._changed)
        lay.addWidget(self._slider, 1)

        self._tgt = QLabel("0.00")
        self._tgt.setObjectName("sliderTarget")
        self._tgt.setMinimumWidth(68)
        self._tgt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._tgt)

    def _changed(self, v: int):
        val = self.lo + (self.hi - self.lo) * v / 1000
        self._tgt.setText(f"{val:.2f}")
        self.valueChanged.emit(val)

    def get_value(self) -> float:
        return self.lo + (self.hi - self.lo) * self._slider.value() / 1000

    def set_value(self, v: float):
        """把滑块移到指定值"""
        normalized = int((v - self.lo) / (self.hi - self.lo) * 1000)
        self._slider.setValue(max(0, min(1000, normalized)))

    def set_range(self, lo: float, hi: float):
        self.lo, self.hi = lo, hi
        self._changed(self._slider.value())

    def set_current(self, v: float):
        self._cur.setText(f"实际 {v:.3f}")


class SpeedControl(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("speedPanel")
        self.lo = 0.05
        self.hi = 2.0

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(10)

        label = QLabel("统一关节速度")
        label.setObjectName("speedTitle")
        label.setMinimumWidth(92)
        lay.addWidget(label)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setObjectName("speedSlider")
        self._slider.setRange(0, 1000)
        self._slider.setValue(self._value_to_slider(0.5))
        self._slider.valueChanged.connect(self._changed)
        lay.addWidget(self._slider, 1)

        self._value = QLabel("0.50 rad/s")
        self._value.setObjectName("speedValue")
        self._value.setMinimumWidth(86)
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._value)

    def _slider_to_value(self, raw: int) -> float:
        return self.lo + (self.hi - self.lo) * raw / 1000

    def _value_to_slider(self, value: float) -> int:
        return int((value - self.lo) / (self.hi - self.lo) * 1000)

    def _changed(self, raw: int):
        self._value.setText(f"{self.get_value():.2f} rad/s")

    def get_value(self) -> float:
        return self._slider_to_value(self._slider.value())


# ── 页面基类 ──────────────────────────────────────────────────

class BasePage(QWidget):
    """所有页面的基类，持有对主窗口的引用"""
    def __init__(self, win: "PantheraMainWindow"):
        super().__init__()
        self.win = win


# ── 页面 1：连接 ──────────────────────────────────────────────

class ConnectPage(BasePage):
    def __init__(self, win: "PantheraMainWindow"):
        super().__init__(win)
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 32, 36, 32)
        root.setSpacing(18)

        title = QLabel("连接配置")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # 配置卡片
        cfg_card = Card()
        cfg_lay = cfg_card.layout_v()

        cfg_lay.addWidget(QLabel("机器人配置文件"))

        row = QHBoxLayout()
        self.config_input = QComboBox()
        self.config_input.setEditable(True)
        self.config_input.addItem(str(DEFAULT_CONFIG))
        row.addWidget(self.config_input, 1)

        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self._browse)
        row.addWidget(browse_btn)
        cfg_lay.addLayout(row)

        btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setObjectName("primary")
        self.connect_btn.clicked.connect(self._connect)
        btn_row.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("断开")
        self.disconnect_btn.clicked.connect(self._disconnect)
        self.disconnect_btn.setEnabled(False)
        btn_row.addWidget(self.disconnect_btn)
        btn_row.addStretch()
        cfg_lay.addLayout(btn_row)

        root.addWidget(cfg_card)

        # 主题选择卡片
        theme_card = Card()
        theme_lay = theme_card.layout_v()
        theme_lay.addWidget(QLabel("界面主题"))

        theme_row = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["蓝", "紫", "绿", "橙", "粉", "石墨"])
        self.theme_combo.currentTextChanged.connect(self._change_theme)
        theme_row.addWidget(self.theme_combo, 1)
        theme_lay.addLayout(theme_row)

        root.addWidget(theme_card)

        # 状态卡片行
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        for key in ["连接状态", "机器人", "限频", "最近更新"]:
            card = StatusCard(key)
            win.status_cards[key] = card
            cards_row.addWidget(card)
        root.addLayout(cards_row)

        root.addStretch()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", str(DEFAULT_CONFIG.parent), "YAML (*.yaml)")
        if path:
            self.config_input.setCurrentText(path)

    def _connect(self):
        if self.win.backend:
            self.win.backend.connect(self.config_input.currentText())

    def _disconnect(self):
        if self.win.backend:
            self.win.backend.disconnect()
            self.win._sliders_synced = False

    def set_connected_state(self, connected: bool):
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)

    def _change_theme(self, theme_name: str):
        """切换主题颜色"""
        themes = {
            "蓝": {
                "bg_start": "#f5f5f7",
                "bg_end": "#f5f5f7",
                "accent": "#007aff",
                "accent_hover": "#0066d6"
            },
            "紫": {
                "bg_start": "#f5f5f7",
                "bg_end": "#f5f5f7",
                "accent": "#af52de",
                "accent_hover": "#9447bd"
            },
            "绿": {
                "bg_start": "#f5f5f7",
                "bg_end": "#f5f5f7",
                "accent": "#34c759",
                "accent_hover": "#2fb34f"
            },
            "橙": {
                "bg_start": "#f5f5f7",
                "bg_end": "#f5f5f7",
                "accent": "#ff9500",
                "accent_hover": "#db8000"
            },
            "粉": {
                "bg_start": "#f5f5f7",
                "bg_end": "#f5f5f7",
                "accent": "#ff2d55",
                "accent_hover": "#d92648"
            },
            "石墨": {
                "bg_start": "#f5f5f7",
                "bg_end": "#f5f5f7",
                "accent": "#6e6e73",
                "accent_hover": "#545458"
            },
        }
        self.win.current_theme = themes.get(theme_name, themes["蓝"])
        self.win._apply_theme()


# ── 页面 2：控制 ──────────────────────────────────────────────

class ControlPage(BasePage):
    def __init__(self, win: "PantheraMainWindow"):
        super().__init__(win)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(0)

        # 上下固定分区：上=MuJoCo预览，下=关节控制
        split_layout = QVBoxLayout()
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(12)
        root.addLayout(split_layout, 1)

        # ── 上半：MuJoCo 预览 ──────────────────────────────
        preview_card = Card()
        preview_lay = preview_card.layout_v(margins=(16, 14, 16, 12), spacing=8)

        top_row = QHBoxLayout()
        preview_title = QLabel("机械臂预览")
        preview_title.setObjectName("panelTitle")
        top_row.addWidget(preview_title)
        top_row.addStretch()

        # 快速动作按钮放在预览标题右侧
        for text, obj, slot in [
            ("刷新", "", win._refresh),
            ("停止", "danger", win._stop),
            ("零位", "", win._go_zero),
            ("初始位", "primary", win._go_home),
        ]:
            b = QPushButton(text)
            if obj:
                b.setObjectName(obj)
            b.clicked.connect(slot)
            top_row.addWidget(b)

        preview_lay.addLayout(top_row)

        try:
            from panthera_gui.kinematic_preview_qt import ArmPreviewWidget
            win.preview = ArmPreviewWidget(str(DEFAULT_CONFIG))
            preview_lay.addWidget(win.preview, 1)
        except Exception as e:
            err = QLabel(f"预览不可用: {e}")
            err.setObjectName("muted")
            err.setWordWrap(True)
            preview_lay.addWidget(err)

        split_layout.addWidget(preview_card, 1)

        # ── 下半：关节滑块 ─────────────────────────────────
        joint_card = Card()
        joint_lay = joint_card.layout_v(margins=(16, 14, 16, 14), spacing=10)

        joint_header = QHBoxLayout()
        joint_header.addWidget(self._section("关节 & 夹爪控制"))
        joint_header.addStretch()
        send_btn = QPushButton("发送目标位置")
        send_btn.setObjectName("primary")
        send_btn.clicked.connect(win._send_targets)
        joint_header.addWidget(send_btn)
        joint_lay.addLayout(joint_header)

        win.joint_speed_control = SpeedControl()
        joint_lay.addWidget(win.joint_speed_control)
        joint_lay.addSpacing(2)

        columns = QHBoxLayout()
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(12)

        name_head = QLabel("轴")
        name_head.setObjectName("columnHead")
        name_head.setMinimumWidth(68)
        name_head.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        columns.addWidget(name_head)

        current_head = QLabel("当前位置")
        current_head.setObjectName("columnHead")
        current_head.setMinimumWidth(110)
        current_head.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columns.addWidget(current_head)

        target_head = QLabel("目标位置")
        target_head.setObjectName("columnHead")
        columns.addWidget(target_head, 1)

        value_head = QLabel("目标值")
        value_head.setObjectName("columnHead")
        value_head.setMinimumWidth(68)
        value_head.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columns.addWidget(value_head)
        joint_lay.addLayout(columns)

        slider_list = QVBoxLayout()
        slider_list.setContentsMargins(0, 0, 0, 0)
        slider_list.setSpacing(6)

        for i in range(6):
            s = JointSlider(f"关节 {i+1}", JOINT_LIMITS[i][0], JOINT_LIMITS[i][1])
            s.valueChanged.connect(win._on_slider_changed)
            win.joint_sliders.append(s)
            slider_list.addWidget(s)

        gripper = JointSlider("夹爪", 0.0, 2.0)
        gripper.valueChanged.connect(win._on_slider_changed)
        win.joint_sliders.append(gripper)
        slider_list.addWidget(gripper)

        joint_lay.addLayout(slider_list)
        split_layout.addWidget(joint_card, 1)

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("panelTitle")
        return lbl


# ── 页面 3：轨迹管理 ─────────────────────────────────────────

class TrajectoryPage(BasePage):
    def __init__(self, win: "PantheraMainWindow"):
        super().__init__(win)
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 32, 36, 32)
        root.setSpacing(18)

        title = QLabel("轨迹录制与播放")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # 状态检查卡片
        status_card = Card()
        status_lay = status_card.layout_v()
        status_lay.addWidget(self._section("服务状态"))

        status_row = QHBoxLayout()
        check_btn = QPushButton("检查连接状态")
        check_btn.clicked.connect(self._check_status)
        status_row.addWidget(check_btn)

        self.service_status = QLabel("状态: 未检查")
        self.service_status.setObjectName("muted")
        status_row.addWidget(self.service_status)
        status_row.addStretch()
        status_lay.addLayout(status_row)

        root.addWidget(status_card)

        # 录制控制卡片
        record_card = Card()
        record_lay = record_card.layout_v()
        record_lay.addWidget(self._section("录制控制"))

        # 重力补偿按钮
        gravity_row = QHBoxLayout()
        self.gravity_btn = QPushButton("开启重力补偿")
        self.gravity_btn.setObjectName("primary")
        self.gravity_btn.clicked.connect(self._toggle_gravity)
        gravity_row.addWidget(self.gravity_btn)

        self.gravity_status = QLabel("状态: 未开启")
        self.gravity_status.setObjectName("muted")
        gravity_row.addWidget(self.gravity_status)
        gravity_row.addStretch()
        record_lay.addLayout(gravity_row)

        # 录制按钮
        record_row = QHBoxLayout()
        self.record_btn = QPushButton("开始录制")
        self.record_btn.setObjectName("danger")
        self.record_btn.clicked.connect(self._toggle_recording)
        record_row.addWidget(self.record_btn)

        self.record_status = QLabel("状态: 未录制")
        self.record_status.setObjectName("muted")
        record_row.addWidget(self.record_status)
        record_row.addStretch()
        record_lay.addLayout(record_row)

        # 保存轨迹
        save_row = QHBoxLayout()
        save_row.addWidget(QLabel("轨迹名称:"))
        self.traj_name_input = QComboBox()
        self.traj_name_input.setEditable(True)
        self.traj_name_input.setPlaceholderText("输入新轨迹名称")
        save_row.addWidget(self.traj_name_input, 1)

        save_btn = QPushButton("保存轨迹")
        save_btn.setObjectName("success")
        save_btn.clicked.connect(self._save_trajectory)
        save_row.addWidget(save_btn)
        record_lay.addLayout(save_row)

        root.addWidget(record_card)

        # 轨迹列表卡片
        list_card = Card()
        list_lay = list_card.layout_v()

        list_header = QHBoxLayout()
        list_header.addWidget(self._section("已保存的轨迹"))
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._refresh_trajectories)
        list_header.addWidget(refresh_btn)
        list_lay.addLayout(list_header)

        # 轨迹列表
        self.traj_list = QComboBox()
        list_lay.addWidget(self.traj_list)

        # 播放和删除按钮
        action_row = QHBoxLayout()
        play_btn = QPushButton("播放轨迹")
        play_btn.setObjectName("primary")
        play_btn.clicked.connect(self._play_trajectory)
        action_row.addWidget(play_btn)

        delete_btn = QPushButton("删除轨迹")
        delete_btn.setObjectName("danger")
        delete_btn.clicked.connect(self._delete_trajectory)
        action_row.addWidget(delete_btn)
        action_row.addStretch()
        list_lay.addLayout(action_row)

        root.addWidget(list_card)
        root.addStretch()

        # 初始化时检查后端连接
        self._check_backend_connection()
        self._refresh_trajectories()

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sectionTitle")
        return lbl

    def _check_backend_connection(self):
        """检查后端连接状态"""
        if self.win.backend and self.win.snapshot and self.win.snapshot.connected:
            self.service_status.setText("状态: 机器人已连接 ✓")
            self.service_status.setStyleSheet("color: #37b24d; font-weight: 700;")
            self.win._log("轨迹页面: 使用 GUI 后端连接")
        else:
            self.service_status.setText("状态: 机器人未连接 ✗")
            self.service_status.setStyleSheet("color: #ee5a6f; font-weight: 700;")
            self.win._log("轨迹页面: 请先在连接页面连接机器人")

    def _check_status(self):
        """检查服务状态"""
        self._check_backend_connection()

    def _toggle_gravity(self):
        """切换重力补偿"""
        self.win._log("点击了重力补偿按钮")
        if not self.win.backend or not self.win.snapshot or not self.win.snapshot.connected:
            self.win._log("请先连接机器人")
            return
        try:
            if not hasattr(self, '_gravity_enabled'):
                self._gravity_enabled = False
                self._gravity_thread = None
                self._gravity_stop_event = None

            if self._gravity_enabled:
                # 关闭重力补偿
                self.win._log("正在关闭重力补偿...")
                if self._gravity_stop_event:
                    self._gravity_stop_event.set()
                if self._gravity_thread:
                    self._gravity_thread.join(timeout=1.0)
                self.gravity_btn.setText("开启重力补偿")
                self.gravity_status.setText("状态: 已关闭")
                self._gravity_enabled = False
                self.win._log("重力补偿已关闭")
            else:
                # 开启重力补偿
                self.win._log("正在开启重力补偿...")
                import threading
                self._gravity_stop_event = threading.Event()
                self._gravity_thread = threading.Thread(target=self._gravity_compensation_loop, daemon=True)
                self._gravity_thread.start()
                self.gravity_btn.setText("关闭重力补偿")
                self.gravity_status.setText("状态: 已开启")
                self._gravity_enabled = True
                self.win._log("重力补偿已开启，现在可以手动拖动机械臂")
        except Exception as e:
            self.win._log(f"重力补偿切换失败: {e}")
            import traceback
            self.win._log(traceback.format_exc())

    def _gravity_compensation_loop(self):
        """重力补偿循环"""
        import time
        import numpy as np

        robot = self.win.backend.robot
        if not robot:
            return

        # 力矩限幅
        tau_limit = np.array([15.0, 30.0, 30.0, 15.0, 5.0, 5.0])
        zero_pos = [0.0] * robot.motor_count
        zero_vel = [0.0] * robot.motor_count
        zero_kp = [0.0] * robot.motor_count
        zero_kd = [0.0] * robot.motor_count

        self.win._log("重力补偿循环已启动")

        while not self._gravity_stop_event.is_set():
            try:
                # 计算重力补偿力矩
                gravity_torque = robot.get_Gravity()
                gravity_torque = np.clip(gravity_torque, -tau_limit, tau_limit)

                # 应用重力补偿（零刚度零阻尼 + 重力补偿力矩）
                robot.pos_vel_tqe_kp_kd(zero_pos, zero_vel, list(gravity_torque), zero_kp, zero_kd)

                # 夹爪也进入零刚度零阻尼状态
                robot.gripper_control_MIT(0.0, 0.0, 0.0, 0.0, 0.0)

                time.sleep(0.01)  # 100Hz 控制频率
            except Exception as e:
                self.win._log(f"重力补偿循环出错: {e}")
                break

        self.win._log("重力补偿循环已停止")

    def _toggle_recording(self):
        """切换录制状态"""
        if not self.win.backend or not self.win.snapshot or not self.win.snapshot.connected:
            self.win._log("请先连接机器人")
            return
        try:
            if not hasattr(self, '_recording'):
                self._recording = False
                self._record_data = []
                self._record_start_time = None

            if self._recording:
                # 停止录制
                self._recording = False
                self.record_btn.setText("开始录制")
                self.record_status.setText(f"状态: 录制已停止 (共 {len(self._record_data)} 帧)")
                self.win._log(f"录制已停止，共记录 {len(self._record_data)} 帧数据")
            else:
                # 开始录制
                self._recording = True
                self._record_data = []
                self._record_start_time = time.time()
                self.record_btn.setText("停止录制")
                self.record_status.setText("状态: 正在录制...")
                self.win._log("开始录制轨迹")
                # 启动录制线程
                import threading
                self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
                self._record_thread.start()
        except Exception as e:
            self.win._log(f"录制切换失败: {e}")
            import traceback
            self.win._log(traceback.format_exc())

    def _record_loop(self):
        """录制循环"""
        import time
        while self._recording and self.win.backend and self.win.backend.robot:
            try:
                snapshot = self.win.snapshot
                if snapshot and snapshot.connected:
                    timestamp = time.time() - self._record_start_time
                    frame = {
                        "timestamp": timestamp,
                        "joint_pos": list(snapshot.joint_pos),
                        "gripper_pos": snapshot.gripper_pos
                    }
                    self._record_data.append(frame)
                time.sleep(0.005)  # 200Hz 录制频率（和重力补偿一致）
            except Exception as e:
                self.win._log(f"录制出错: {e}")
                break

    def _save_trajectory(self):
        """保存轨迹"""
        name = self.traj_name_input.currentText().strip()
        if not name:
            self.win._log("请输入轨迹名称")
            return
        if not hasattr(self, '_record_data') or not self._record_data:
            self.win._log("没有可保存的轨迹数据，请先录制")
            return
        try:
            import json
            traj_dir = PROJECT_ROOT / "trajectories"
            traj_dir.mkdir(exist_ok=True)

            filepath = traj_dir / f"{name}.jsonl"
            with open(filepath, 'w') as f:
                for frame in self._record_data:
                    f.write(json.dumps(frame) + '\n')

            self.win._log(f"轨迹已保存: {name} ({len(self._record_data)} 帧)")
            self._refresh_trajectories()
            self._record_data = []
        except Exception as e:
            self.win._log(f"保存轨迹失败: {e}")
            import traceback
            self.win._log(traceback.format_exc())

    def _refresh_trajectories(self):
        """刷新轨迹列表"""
        try:
            traj_dir = PROJECT_ROOT / "trajectories"
            if not traj_dir.exists():
                traj_dir.mkdir(exist_ok=True)

            trajectories = sorted([f.stem for f in traj_dir.glob("*.jsonl")])
            self.traj_list.clear()
            self.traj_list.addItems(trajectories)
            self.win._log(f"已加载 {len(trajectories)} 个轨迹")
        except Exception as e:
            self.win._log(f"刷新轨迹列表失败: {e}")

    def _play_trajectory(self):
        """播放轨迹"""
        if not self.win.backend or not self.win.snapshot or not self.win.snapshot.connected:
            self.win._log("请先连接机器人")
            return
        name = self.traj_list.currentText()
        if not name:
            self.win._log("请选择要播放的轨迹")
            return

        # 播放前强制关闭重力补偿
        if hasattr(self, '_gravity_enabled') and self._gravity_enabled:
            self.win._log("播放前自动关闭重力补偿")
            self._toggle_gravity()
            import time
            time.sleep(0.3)  # 等重力补偿线程完全停止

        try:
            import json
            traj_dir = PROJECT_ROOT / "trajectories"
            filepath = traj_dir / f"{name}.jsonl"

            if not filepath.exists():
                self.win._log(f"轨迹文件不存在: {name}")
                return

            # 读取轨迹数据
            frames = []
            with open(filepath, 'r') as f:
                for line in f:
                    frames.append(json.loads(line))

            if len(frames) < 2:
                self.win._log("轨迹数据太少，无法播放")
                return

            self.win._log(f"开始播放轨迹: {name} ({len(frames)} 帧)")

            # 在后台线程播放
            import threading
            def play_thread():
                import time

                backend = self.win.backend
                if not backend:
                    return

                start_time = time.time()

                for i, frame in enumerate(frames):
                    if not backend or not backend.robot:
                        break
                    try:
                        target_pos = frame["joint_pos"]
                        gripper_pos = frame["gripper_pos"]
                        target_time = frame["timestamp"]

                        # 通过命令队列发送
                        backend.send_joint_targets(target_pos, 0.5)
                        backend.send_gripper_target(gripper_pos, 0.5)

                        # 按录制时间戳播放，保持原始节奏
                        elapsed = time.time() - start_time
                        sleep_time = target_time - elapsed
                        if sleep_time > 0.002:
                            time.sleep(sleep_time)

                    except Exception as e:
                        self.win._log(f"播放帧 {i} 出错: {e}")
                        import traceback
                        self.win._log(traceback.format_exc())
                        break

                self.win._log(f"轨迹播放完成: {name}")

            threading.Thread(target=play_thread, daemon=True).start()

        except Exception as e:
            self.win._log(f"播放轨迹失败: {e}")
            import traceback
            self.win._log(traceback.format_exc())

    def _delete_trajectory(self):
        """删除轨迹"""
        name = self.traj_list.currentText()
        if not name:
            self.win._log("请选择要删除的轨迹")
            return
        try:
            traj_dir = PROJECT_ROOT / "trajectories"
            filepath = traj_dir / f"{name}.jsonl"

            if filepath.exists():
                filepath.unlink()
                self.win._log(f"已删除轨迹: {name}")
                self._refresh_trajectories()
            else:
                self.win._log(f"轨迹文件不存在: {name}")
        except Exception as e:
            self.win._log(f"删除轨迹失败: {e}")


# ── 页面 4：例程 & 日志 ───────────────────────────────────────

class ExamplePage(BasePage):
    def __init__(self, win: "PantheraMainWindow"):
        super().__init__(win)
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 32, 36, 32)
        root.setSpacing(18)

        title = QLabel("例程 & 日志")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # 例程卡片
        ex_card = Card()
        ex_lay = ex_card.layout_v()
        ex_lay.addWidget(self._section("SDK 例程"))

        row = QHBoxLayout()
        win.example_combo = QComboBox()
        win.example_combo.addItems(win.example_scripts)
        row.addWidget(win.example_combo, 1)

        self.start_btn = QPushButton("启动")
        self.start_btn.setObjectName("success")
        self.start_btn.clicked.connect(win._start_example)
        row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.clicked.connect(win._stop_example)
        self.stop_btn.setEnabled(False)
        row.addWidget(self.stop_btn)
        ex_lay.addLayout(row)
        root.addWidget(ex_card)

        # 状态表 + 日志 并排
        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        # 状态表
        state_card = Card()
        state_lay = state_card.layout_v()
        state_lay.addWidget(self._section("实时状态"))

        win.state_table = QTableWidget(7, 4)
        win.state_table.setHorizontalHeaderLabels(["轴", "位置", "速度", "力矩"])
        win.state_table.horizontalHeader().setStretchLastSection(True)
        win.state_table.verticalHeader().setVisible(False)
        win.state_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for i, lbl in enumerate(JOINT_LABELS):
            win.state_table.setItem(i, 0, QTableWidgetItem(lbl))
            for j in range(1, 4):
                win.state_table.setItem(i, j, QTableWidgetItem("-"))
        state_lay.addWidget(win.state_table)
        bottom.addWidget(state_card, 1)

        # 日志
        log_card = Card()
        log_lay = log_card.layout_v()
        log_lay.addWidget(self._section("运行日志"))
        win.log_text = QTextEdit()
        win.log_text.setReadOnly(True)
        log_lay.addWidget(win.log_text, 1)
        bottom.addWidget(log_card, 1)

        root.addLayout(bottom, 1)

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sectionTitle")
        return lbl

    def set_example_state(self, state: str):
        starting = state == "starting"
        running = state == "running"
        stopping = state == "stopping"
        busy = starting or running or stopping

        if self.win.example_combo:
            self.win.example_combo.setEnabled(not busy)

        self.start_btn.setEnabled(not busy)
        self.stop_btn.setEnabled(running)

        if starting:
            self.start_btn.setText("启动中")
            self.stop_btn.setText("停止")
        elif stopping:
            self.start_btn.setText("启动")
            self.stop_btn.setText("停止中")
        else:
            self.start_btn.setText("启动")
            self.stop_btn.setText("停止")


# ── 主窗口 ────────────────────────────────────────────────────

class PantheraMainWindow(QMainWindow):
    snapshot_signal = pyqtSignal(object)
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Panthera Control Deck")
        self.resize(1440, 900)
        self.setMinimumSize(1000, 640)

        # 共享状态
        self.event_queue: queue.Queue = queue.Queue()
        self.backend: Any = None
        self.snapshot = None
        self.example_scripts: list[str] = []

        # 共享控件（由各页面填充）
        self.status_cards: dict[str, StatusCard] = {}
        self.joint_sliders: list[JointSlider] = []
        self.joint_speed_control: Optional[SpeedControl] = None
        self.state_table: Optional[QTableWidget] = None
        self.log_text: Optional[QTextEdit] = None
        self.example_combo: Optional[QComboBox] = None
        self.preview = None
        self._sliders_synced = False

        # SDK 例程运行状态（后台自动断连/重连）
        self._example_running = False
        self._example_state = "idle"
        self._was_connected_before_example = False

        # 主题配置
        self.current_theme = {
            "bg_start": "#f5f5f7",
            "bg_end": "#f5f5f7",
            "accent": "#007aff",
            "accent_hover": "#0066d6"
        }

        self._load_backend()
        self._build_ui()
        self._apply_theme()

        self.snapshot_signal.connect(self._on_snapshot)
        self.log_signal.connect(self._on_log)

        self._timer = QTimer()
        self._timer.timeout.connect(self._drain)
        self._timer.start(100)

        self._log("GUI 已启动")

    # ── 后端 ──────────────────────────────────────────────────

    def _load_backend(self):
        try:
            mod = importlib.import_module("panthera_gui.robot_backend")
            self.backend = mod.RobotBackend(self.event_queue)
            self.backend.start()
            self.example_scripts = list(mod.EXAMPLE_SCRIPTS)
        except Exception as e:
            self._log(f"后端加载失败: {e}")

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # 侧边栏（固定展开）
        self._sidebar = QWidget()
        self._sidebar.setObjectName("sidebar")
        self._sidebar.setFixedWidth(188)
        self._sidebar.setContentsMargins(8, 8, 0, 8)

        # 侧边栏主布局
        sidebar_main = QHBoxLayout(self._sidebar)
        sidebar_main.setContentsMargins(0, 0, 0, 0)
        sidebar_main.setSpacing(0)

        # 内容区域
        sidebar_content = QWidget()
        sb_lay = QVBoxLayout(sidebar_content)
        sb_lay.setContentsMargins(0, 22, 0, 22)
        sb_lay.setSpacing(6)

        app_name = QLabel("Panthera")
        app_name.setObjectName("appName")
        app_name.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sb_lay.addWidget(app_name)

        # 添加空白间隔
        sb_lay.addSpacing(20)

        self._nav_btns: list[QPushButton] = []
        self._stack = QStackedWidget()
        self._pages: dict[str, BasePage] = {}

        pages = [
            ("连接", ConnectPage(self)),
            ("控制", ControlPage(self)),
            ("轨迹", TrajectoryPage(self)),
            ("例程", ExamplePage(self)),
        ]

        for i, (label, page) in enumerate(pages):
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._nav(idx))
            sb_lay.addWidget(btn)
            self._nav_btns.append(btn)
            self._stack.addWidget(page)
            self._pages[label] = page

        sb_lay.addStretch()

        sidebar_main.addWidget(sidebar_content, 1)

        main.addWidget(self._sidebar)
        main.addWidget(self._stack, 1)

        self._nav(0)

    def _nav(self, idx: int):
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_btns):
            btn.setProperty("active", i == idx)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ── 事件 ──────────────────────────────────────────────────

    def _drain(self):
        while True:
            try:
                kind, payload = self.event_queue.get_nowait()
                if kind == "snapshot":
                    self.snapshot_signal.emit(payload)
                elif kind == "log":
                    self.log_signal.emit(payload)
                elif kind == "example_status":
                    self._on_example_status(payload)
            except queue.Empty:
                break

    def _on_example_status(self, payload: dict):
        state = payload.get("state")
        if not state:
            state = "running" if payload.get("running", False) else "idle"
        name = payload.get("name", "")
        message = payload.get("message", "")
        was_busy = self._example_running
        busy = state in {"starting", "running", "stopping"}
        self._example_running = busy
        self._example_state = state

        example_page = self._pages.get("例程")
        if isinstance(example_page, ExamplePage):
            example_page.set_example_state(state)

        connect_page = self._pages.get("连接")
        if isinstance(connect_page, ConnectPage):
            if busy:
                connect_page.connect_btn.setEnabled(False)
                connect_page.disconnect_btn.setEnabled(False)
            elif self.snapshot is not None:
                connect_page.set_connected_state(bool(self.snapshot.connected))
            else:
                connect_page.set_connected_state(False)

        if state == "starting":
            self._log(f"例程启动中: {name}")
            return
        if state == "running":
            self._log(message or f"例程运行中: {name}")
            return
        if state == "stopping":
            self._log(f"例程停止中: {name}")
            return

        if was_busy:
            self._log(message or f"例程已停止: {name}")
            if self._was_connected_before_example:
                QTimer.singleShot(500, self._reconnect_after_example)

    @pyqtSlot(object)
    def _on_snapshot(self, snap):
        self.snapshot = snap
        connect_page = self._pages.get("连接")
        if isinstance(connect_page, ConnectPage):
            if self._example_running:
                connect_page.connect_btn.setEnabled(False)
                connect_page.disconnect_btn.setEnabled(False)
            else:
                connect_page.set_connected_state(bool(snap.connected))

        self.status_cards["连接状态"].set_value(snap.status)
        self.status_cards["机器人"].set_value(snap.robot_name)
        self.status_cards["限频"].set_value(f"{snap.rate_limit_hz} Hz" if snap.rate_limit_hz else "-")
        if snap.updated_at:
            self.status_cards["最近更新"].set_value(
                time.strftime("%H:%M:%S", time.localtime(snap.updated_at)))

        if snap.joint_limits_lower and snap.joint_limits_upper:
            for i, s in enumerate(self.joint_sliders[:6]):
                s.set_range(snap.joint_limits_lower[i], snap.joint_limits_upper[i])
            if len(self.joint_sliders) > 6:
                self.joint_sliders[6].set_range(*snap.gripper_limits)

        for i in range(min(6, len(snap.joint_pos))):
            self.joint_sliders[i].set_current(snap.joint_pos[i])
            # 首次连接时把滑块目标位置同步到实际关节角度
            if snap.connected and not self._sliders_synced:
                self.joint_sliders[i].set_value(snap.joint_pos[i])
            if self.state_table:
                self.state_table.setItem(i, 1, QTableWidgetItem(f"{snap.joint_pos[i]:.3f}"))
                self.state_table.setItem(i, 2, QTableWidgetItem(f"{snap.joint_vel[i]:.3f}"))
                self.state_table.setItem(i, 3, QTableWidgetItem(f"{snap.joint_torque[i]:.3f}"))

        if len(self.joint_sliders) > 6 and self.state_table:
            self.joint_sliders[6].set_current(snap.gripper_pos)
            if snap.connected and not self._sliders_synced:
                self.joint_sliders[6].set_value(snap.gripper_pos)
            self.state_table.setItem(6, 1, QTableWidgetItem(f"{snap.gripper_pos:.3f}"))
            self.state_table.setItem(6, 2, QTableWidgetItem(f"{snap.gripper_vel:.3f}"))
            self.state_table.setItem(6, 3, QTableWidgetItem(f"{snap.gripper_torque:.3f}"))

        if snap.connected and not self._sliders_synced and snap.joint_pos:
            self._sliders_synced = True

        if self.preview and snap.joint_pos:
            self.preview.update_state(
                target_joints=[s.get_value() for s in self.joint_sliders[:6]],
                live_joints=snap.joint_pos[:6] if snap.connected else None,
                target_gripper=self.joint_sliders[6].get_value() if len(self.joint_sliders) > 6 else 0.0,
                live_gripper=snap.gripper_pos if snap.connected else None,
            )

    @pyqtSlot(str)
    def _on_log(self, msg: str):
        self._log(msg)

    def _log(self, msg: str):
        if self.log_text:
            self.log_text.append(msg)

    def _apply_theme(self):
        """应用当前主题"""
        style = STYLE.format(**self.current_theme)
        self.setStyleSheet(style)

    # ── 控制动作 ──────────────────────────────────────────────

    def _on_slider_changed(self, _: float):
        if self.preview and len(self.joint_sliders) >= 7:
            # 保留当前 snapshot 的真机数据，不要覆盖成 None（否则会在单/双视图间闪烁）
            snap = self.snapshot
            live = snap.joint_pos[:6] if (snap and snap.connected and snap.joint_pos) else None
            live_gripper = snap.gripper_pos if (snap and snap.connected) else None
            self.preview.update_state(
                target_joints=[s.get_value() for s in self.joint_sliders[:6]],
                live_joints=live,
                target_gripper=self.joint_sliders[6].get_value(),
                live_gripper=live_gripper,
            )

    def _refresh(self):
        if self.backend: self.backend.refresh_state()

    def _stop(self):
        if self.backend: self.backend.stop_robot()

    def _go_zero(self):
        if self.backend:
            self.backend.go_zero_pose()
            # 重置所有滑块到零位
            for slider in self.joint_sliders[:6]:
                slider.set_value(0.0)
            if len(self.joint_sliders) > 6:
                self.joint_sliders[6].set_value(0.0)

    def _go_home(self):
        if self.backend: self.backend.go_home_pose()

    def _send_targets(self):
        if self.backend:
            velocity = self.joint_speed_control.get_value() if self.joint_speed_control else 0.5
            self.backend.send_joint_targets([s.get_value() for s in self.joint_sliders[:6]], velocity)
            if len(self.joint_sliders) > 6:
                self.backend.send_gripper_target(self.joint_sliders[6].get_value(), velocity)

    def _start_example(self):
        if self.backend and self.example_combo:
            if self._example_state != "idle":
                self._log(f"例程当前状态为 {self._example_state}，忽略启动请求")
                return
            script = self.example_combo.currentText()
            if script:
                # 记录当前连接状态
                self._was_connected_before_example = bool(self.snapshot and self.snapshot.connected)
                example_page = self._pages.get("例程")
                if isinstance(example_page, ExamplePage):
                    example_page.set_example_state("starting")
                self.backend.start_example(script)

    def _stop_example(self):
        if self.backend:
            if self._example_state not in {"running", "starting"}:
                self._log(f"例程当前状态为 {self._example_state}，忽略停止请求")
                return
            example_page = self._pages.get("例程")
            if isinstance(example_page, ExamplePage):
                example_page.set_example_state("stopping")
            self._example_state = "stopping"
            self._example_running = True
            self.backend.stop_example()

    def _reconnect_after_example(self):
        """例程结束后自动重连"""
        if self.backend and self._was_connected_before_example:
            # 获取之前的配置文件路径
            config_path = str(DEFAULT_CONFIG)
            # 尝试从连接页面获取用户选择的配置
            connect_page = self._pages.get("连接")
            if connect_page and hasattr(connect_page, 'config_input'):
                config_path = connect_page.config_input.currentText()
            self.backend.connect(config_path)
            self._was_connected_before_example = False

    def closeEvent(self, event):
        if self.backend: self.backend.shutdown()
        event.accept()


def main():
    app = QApplication(sys.argv)

    # 全局异常处理
    def exception_hook(exctype, value, tb):
        import traceback
        error_msg = ''.join(traceback.format_exception(exctype, value, tb))
        print(error_msg, file=sys.stderr)

        # 弹窗显示错误
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("程序错误")
        msg.setText("程序遇到未处理的异常")
        msg.setDetailedText(error_msg)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    sys.excepthook = exception_hook

    win = PantheraMainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
