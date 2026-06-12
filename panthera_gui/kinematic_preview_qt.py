"""
MuJoCo 机械臂预览组件 - PyQt6 版本
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    import mujoco
    MUJOCO_ERROR: Optional[str] = None
except Exception as e:
    mujoco = None
    MUJOCO_ERROR = str(e)

try:
    from PIL import Image, ImageDraw
    PIL_ERROR: Optional[str] = None
except Exception as e:
    Image = ImageDraw = None
    PIL_ERROR = str(e)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENE = PROJECT_ROOT / "Panthera-HT_mujoco_DEMO" / "model" / "scene_arm_only.xml"
ARM_JOINT_NAMES = [f"joint{i}" for i in range(1, 7)]
LEFT_GRIPPER_JOINT  = "L_finger_joint"
RIGHT_GRIPPER_JOINT = "R_finger_joint"

BG           = "#0b1117"
TARGET_COLOR = "#59b4ff"
LIVE_COLOR   = "#f3be74"
TEXT_PRIMARY = "#eff5fb"
TEXT_MUTED   = "#9aabba"

# 固定渲染分辨率，不随窗口变化 —— 原版也是渲染固定尺寸再 resize
RENDER_W = 1280
RENDER_H = 720


class ArmPreviewWidget(QWidget):
    """MuJoCo 机械臂预览组件。"""

    def __init__(self, config_path: str, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(320)

        # ── MuJoCo 对象 ──────────────────────────────────────
        self.model = None
        self.data  = None
        self.renderer = None
        self.camera: Optional[any] = None
        self.camera_name = "overhead"
        self._use_named_camera = True
        self.arm_qpos_addrs: list[int] = []
        self.left_gripper_addr:  Optional[int] = None
        self.right_gripper_addr: Optional[int] = None
        self.gripper_body_id:    Optional[int] = None

        # ── 姿态数据 ─────────────────────────────────────────
        self.target_joints: list[float] = [0.0] * 6
        self.live_joints:   Optional[list[float]] = None
        self.target_gripper: float = 0.0
        self.live_gripper:   Optional[float] = None
        # 上一帧数据，用于去重避免无效重绘
        self._last_target: list[float] = []
        self._last_live: Optional[list[float]] = None
        self._last_tgt_grip: float = -999.0
        self._last_live_grip: Optional[float] = None

        # ── 鼠标交互 ─────────────────────────────────────────
        self._drag_mode: Optional[str] = None
        self._last_pos:  Optional[tuple[int, int]] = None

        # ── 渲染节流（idle 触发，同原版 after_idle）────────────
        self._render_pending = False
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(0)   # 下一个事件循环空闲时触发
        self._render_timer.timeout.connect(self._render_frame)

        # ── UI ───────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(f"background: {BG}; border-radius: 8px;")
        self.image_label.setMinimumHeight(280)
        layout.addWidget(self.image_label, 1)

        self.status_label = QLabel("MuJoCo 初始化中...")
        self.status_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px; font-weight: bold; padding: 6px 12px; background: {BG};")
        layout.addWidget(self.status_label)

        self.target_label = QLabel("")
        self.target_label.setStyleSheet(f"color: {TARGET_COLOR}; font-size: 11px; padding: 2px 12px; background: {BG};")
        layout.addWidget(self.target_label)

        self.live_label = QLabel("")
        self.live_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; padding: 2px 12px 8px; background: {BG};")
        layout.addWidget(self.live_label)

        # 鼠标事件绑定到 image_label
        self.image_label.setMouseTracking(True)
        self.image_label.mousePressEvent   = self._mouse_press
        self.image_label.mouseMoveEvent    = self._mouse_move
        self.image_label.mouseReleaseEvent = self._mouse_release
        self.image_label.wheelEvent        = self._wheel_event

        self._load_model()

    # ── 模型加载（对齐原版 _ensure_model）────────────────────

    def _load_model(self):
        err = self._dependency_error()
        if err:
            self.status_label.setText(err)
            return
        if not DEFAULT_SCENE.exists():
            self.status_label.setText(f"场景文件不存在: {DEFAULT_SCENE}")
            return
        try:
            self.model = mujoco.MjModel.from_xml_path(str(DEFAULT_SCENE))
            # 对齐原版：用 max 保证 framebuffer 足够大
            self.model.vis.global_.offwidth  = max(int(self.model.vis.global_.offwidth),  RENDER_W)
            self.model.vis.global_.offheight = max(int(self.model.vis.global_.offheight), RENDER_H)

            self.data = mujoco.MjData(self.model)

            # 对齐原版：默认用 named camera "overhead"，支持鼠标切换为 free
            self.camera_name = "overhead"
            self.camera = mujoco.MjvCamera()
            self.camera.type        = mujoco.mjtCamera.mjCAMERA_FREE
            self.camera.fixedcamid  = -1
            self.camera.trackbodyid = -1
            self.camera.lookat[:]   = np.array([0.02, 0.0, 0.28], dtype=float)
            self.camera.distance    = 0.98
            self.camera.azimuth     = 132.0
            self.camera.elevation   = -24.0
            self._use_named_camera  = True   # 初始用 named camera

            self.arm_qpos_addrs     = [self._joint_addr(n) for n in ARM_JOINT_NAMES]
            self.left_gripper_addr  = self._joint_addr(LEFT_GRIPPER_JOINT)
            self.right_gripper_addr = self._joint_addr(RIGHT_GRIPPER_JOINT)
            self.gripper_body_id    = mujoco.mj_name2id(
                self.model, mujoco.mjtObj.mjOBJ_BODY, "gripper_center")

            # 建立固定尺寸 renderer（不随窗口变化）
            self.renderer = mujoco.Renderer(self.model, height=RENDER_H, width=RENDER_W)

            self.status_label.setText("MuJoCo 已就绪  |  拖拽旋转  Shift+拖拽平移  滚轮缩放")
            self._schedule_refresh()
        except Exception as e:
            self.status_label.setText(f"模型加载失败: {e}")

    def _joint_addr(self, name: str) -> int:
        jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if jid < 0:
            raise RuntimeError(f"关节不存在: {name}")
        return int(self.model.jnt_qposadr[jid])

    def _dependency_error(self) -> Optional[str]:
        if MUJOCO_ERROR:
            return f"mujoco 未安装: {MUJOCO_ERROR}"
        if PIL_ERROR:
            return f"Pillow 未安装: {PIL_ERROR}"
        return None

    # ── 公开接口 ──────────────────────────────────────────────

    def update_state(
        self,
        *,
        target_joints: Sequence[float],
        live_joints: Optional[Sequence[float]],
        target_gripper: float = 0.0,
        live_gripper: Optional[float] = None,
    ):
        new_target  = list(target_joints)
        new_live    = None if live_joints is None else list(live_joints)
        new_tgt_g   = float(target_gripper)
        new_live_g  = None if live_gripper is None else float(live_gripper)

        # 数据没变就不触发重绘，避免抖动
        def _close(a, b):
            if a is None and b is None: return True
            if a is None or b is None: return False
            return all(abs(x - y) < 0.002 for x, y in zip(a, b))  # 放宽到 2mm 容差

        if (_close(new_target, self._last_target) and
                _close(new_live, self._last_live) and
                abs(new_tgt_g - self._last_tgt_grip) < 1e-4 and
                _close([new_live_g] if new_live_g is not None else None,
                       [self._last_live_grip] if self._last_live_grip is not None else None)):
            return

        self.target_joints  = new_target
        self.live_joints    = new_live
        self.target_gripper = new_tgt_g
        self.live_gripper   = new_live_g
        self._last_target   = new_target
        self._last_live     = new_live
        self._last_tgt_grip = new_tgt_g
        self._last_live_grip = new_live_g
        self._schedule_refresh()

    # ── 渲染调度（对齐原版 after_idle）───────────────────────

    def _schedule_refresh(self):
        if self._render_pending:
            return
        self._render_pending = True
        self._render_timer.start()

    def _render_frame(self):
        self._render_pending = False
        if self.model is None or self.data is None or self.renderer is None:
            return

        # 显示区域尺寸
        w = max(self.image_label.width(),  520)
        h = max(self.image_label.height(), 320)

        try:
            if self.live_joints is not None:
                image, target_tcp, live_tcp = self._render_dual_view(w, h)
                err_mm = np.linalg.norm(live_tcp - target_tcp) * 1000.0
                self.status_label.setText("MuJoCo 双视图: 左侧目标 / 右侧真机")
                self.target_label.setText(_fmt_pos("Target TCP", target_tcp))
                self.live_label.setText(
                    f"{_fmt_pos('Live TCP', live_tcp)}    Tracking Error: {err_mm:5.1f} mm")
                self.live_label.setStyleSheet(
                    f"color: {LIVE_COLOR}; font-size: 11px; padding: 2px 12px 8px; background: {BG};")
            else:
                image, target_tcp = self._render_single_view(w, h)
                self.status_label.setText("MuJoCo 目标预览: 当前未连接真机")
                self.target_label.setText(_fmt_pos("Target TCP", target_tcp))
                self.live_label.setText("Live TCP: 等待真机连接")
                self.live_label.setStyleSheet(
                    f"color: {TEXT_MUTED}; font-size: 11px; padding: 2px 12px 8px; background: {BG};")

            self.image_label.setPixmap(_pil_to_pixmap(image))

        except Exception as exc:
            self.status_label.setText(f"MuJoCo 渲染失败: {exc}")
            self.target_label.setText(f"Scene: {DEFAULT_SCENE}")
            self.live_label.setText(str(exc))
            self.live_label.setStyleSheet(
                f"color: #ff9f9f; font-size: 11px; padding: 2px 12px 8px; background: {BG};")

    # ── 渲染逻辑（直接对齐原版）──────────────────────────────

    def _render_single_view(self, width: int, height: int):
        frame = self._render_pose_image(self.target_joints, self.target_gripper, width, height)
        canvas = Image.new("RGB", (width, height), BG)
        canvas.paste(frame, (0, 0))
        draw = ImageDraw.Draw(canvas)
        self._draw_title(draw, 18, 16, "Target Preview", TARGET_COLOR)
        return canvas, self._capture_tcp(self.target_joints, self.target_gripper)

    def _render_dual_view(self, width: int, height: int):
        gap = 12
        pw = max(240, (width - gap) // 2)
        target_img = self._render_pose_image(self.target_joints, self.target_gripper, pw, height)
        live_img   = self._render_pose_image(
            self.live_joints or self.target_joints,
            self.live_gripper if self.live_gripper is not None else 0.0,
            pw, height)

        canvas = Image.new("RGB", (pw * 2 + gap, height), BG)
        canvas.paste(target_img, (0, 0))
        canvas.paste(live_img,   (pw + gap, 0))

        draw = ImageDraw.Draw(canvas)
        self._draw_title(draw, 18,          16, "Target",     TARGET_COLOR)
        self._draw_title(draw, pw + gap + 18, 16, "Live Robot", LIVE_COLOR)

        target_tcp = self._capture_tcp(self.target_joints, self.target_gripper)
        live_tcp   = self._capture_tcp(
            self.live_joints or self.target_joints,
            self.live_gripper if self.live_gripper is not None else 0.0)
        return canvas, target_tcp, live_tcp

    def _render_pose_image(self, joints: Sequence[float], gripper: float,
                           width: int, height: int) -> "Image.Image":
        """渲染固定分辨率后 resize 到目标尺寸"""
        self._apply_pose(joints, gripper)
        cam = self.camera_name if self._use_named_camera else self.camera
        self.renderer.update_scene(self.data, camera=cam)
        pixels = self.renderer.render()
        img = Image.fromarray(pixels)
        if img.size != (width, height):
            img = img.resize((width, height), Image.LANCZOS)
        return img

    def _capture_tcp(self, joints: Sequence[float], gripper: float) -> np.ndarray:
        self._apply_pose(joints, gripper)
        if self.gripper_body_id is None:
            return np.zeros(3)
        return self.data.xpos[self.gripper_body_id].copy()

    def _apply_pose(self, joints: Sequence[float], gripper: float):
        """设置关节角度，clamp 到 XML range 防止穿模"""
        self.data.qpos[:] = 0.0
        self.data.qvel[:] = 0.0
        for i, (addr, val) in enumerate(zip(self.arm_qpos_addrs, joints)):
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, ARM_JOINT_NAMES[i])
            lo = float(self.model.jnt_range[jid][0])
            hi = float(self.model.jnt_range[jid][1])
            self.data.qpos[addr] = float(np.clip(val, lo, hi))
        opening = float(np.clip(gripper / 2.0 * 0.04, 0.0, 0.04))
        if self.left_gripper_addr is not None:
            self.data.qpos[self.left_gripper_addr] = opening
        if self.right_gripper_addr is not None:
            self.data.qpos[self.right_gripper_addr] = -opening
        mujoco.mj_forward(self.model, self.data)

    def _draw_title(self, draw: "ImageDraw.ImageDraw",
                    x: int, y: int, title: str, accent: str):
        draw.rounded_rectangle((x, y, x + 124, y + 30),
                                radius=10, fill="#09121a", outline="#203241", width=1)
        draw.ellipse((x + 10, y + 10, x + 20, y + 20), fill=accent)
        draw.text((x + 30, y + 8), title, fill=TEXT_PRIMARY)

    # ── 鼠标交互（对齐原版）──────────────────────────────────

    def _mouse_press(self, event):
        self._last_pos = (event.position().x(), event.position().y())
        mods = event.modifiers()
        self._drag_mode = "pan" if (mods & Qt.KeyboardModifier.ShiftModifier) else "rotate"
        # 第一次拖动时从 named camera 同步到 free camera
        if self._use_named_camera and self.model is not None and self.data is not None:
            self._use_named_camera = False

    def _mouse_move(self, event):
        if self.camera is None or self._last_pos is None:
            return
        x, y = event.position().x(), event.position().y()
        dx = x - self._last_pos[0]
        dy = y - self._last_pos[1]
        self._last_pos = (x, y)

        if self._drag_mode == "rotate":
            self.camera.azimuth   -= dx * 0.5
            self.camera.elevation  = float(
                np.clip(self.camera.elevation - dy * 0.35, -89.0, 89.0))
        elif self._drag_mode == "pan":
            scale = max(float(self.camera.distance), 0.2) * 0.0015
            az    = np.deg2rad(float(self.camera.azimuth))
            right = np.array([np.cos(az), np.sin(az), 0.0])
            up    = np.array([0.0, 0.0, 1.0])
            self.camera.lookat[:] -= right * dx * scale - up * dy * scale

        self._schedule_refresh()

    def _mouse_release(self, event):
        self._drag_mode = None
        self._last_pos  = None

    def _wheel_event(self, event):
        if self.camera is None:
            return
        delta = event.angleDelta().y()
        factor = 0.9 if delta > 0 else 1.1
        self.camera.distance = float(
            np.clip(self.camera.distance * factor, 0.35, 4.5))
        self._schedule_refresh()

    def closeEvent(self, event):
        if self.renderer is not None:
            self.renderer.close()
        super().closeEvent(event)


# ── 工具函数 ──────────────────────────────────────────────────

def _pil_to_pixmap(img: "Image.Image") -> QPixmap:
    rgb = img.convert("RGB")
    w, h = rgb.size
    data = rgb.tobytes("raw", "RGB")
    qimg = QImage(data, w, h, w * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg)


def _fmt_pos(label: str, pos: np.ndarray) -> str:
    mm = np.asarray(pos) * 1000.0
    return f"{label}: x={mm[0]:6.1f} mm   y={mm[1]:6.1f} mm   z={mm[2]:6.1f} mm"
