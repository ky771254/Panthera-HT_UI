from __future__ import annotations

import os
import queue
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "panthera_python" / "scripts"
DEFAULT_CONFIG = PROJECT_ROOT / "panthera_python" / "robot_param" / "Follower.yaml"


def discover_example_scripts() -> list[str]:
    if not SCRIPTS_DIR.exists():
        return []

    return sorted(
        path.name
        for path in SCRIPTS_DIR.glob("*.py")
        if path.is_file() and not path.name.startswith("_")
    )


EXAMPLE_SCRIPTS = discover_example_scripts()


@dataclass
class RobotSnapshot:
    connected: bool = False
    status: str = "未连接"
    robot_name: str = "-"
    config_path: str = ""
    motor_count: int = 0
    gripper_id: int = 0
    rate_limit_hz: int = 0
    updated_at: float = 0.0
    joint_pos: list[float] = field(default_factory=list)
    joint_vel: list[float] = field(default_factory=list)
    joint_torque: list[float] = field(default_factory=list)
    gripper_pos: float = 0.0
    gripper_vel: float = 0.0
    gripper_torque: float = 0.0
    joint_limits_lower: list[float] = field(default_factory=list)
    joint_limits_upper: list[float] = field(default_factory=list)
    gripper_limits: tuple[float, float] = (0.0, 2.0)


class RobotBackend:
    def __init__(self, event_queue: queue.Queue):
        self.event_queue = event_queue
        self.command_queue: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.robot = None
        self.snapshot = RobotSnapshot(config_path=str(DEFAULT_CONFIG))
        self.poll_interval = 0.1
        self.example_process: Optional[subprocess.Popen] = None
        self.example_name: str = ""
        self.example_state: str = "idle"

    def start(self) -> None:
        self.thread.start()

    def shutdown(self) -> None:
        self.command_queue.put(("shutdown", {}))
        self.thread.join(timeout=2.0)

    def connect(self, config_path: str) -> None:
        self.command_queue.put(("connect", {"config_path": config_path}))

    def disconnect(self) -> None:
        self.command_queue.put(("disconnect", {}))

    def refresh_state(self) -> None:
        self.command_queue.put(("refresh_state", {}))

    def stop_robot(self) -> None:
        self.command_queue.put(("stop_robot", {}))

    def send_joint_targets(self, positions: list[float], velocity: float) -> None:
        self.command_queue.put(
            ("send_joint_targets", {"positions": positions, "velocity": velocity})
        )

    def go_zero_pose(self) -> None:
        self.command_queue.put(("go_zero_pose", {}))

    def go_home_pose(self) -> None:
        self.command_queue.put(("go_home_pose", {}))

    def open_gripper(self) -> None:
        self.command_queue.put(("open_gripper", {}))

    def close_gripper(self) -> None:
        self.command_queue.put(("close_gripper", {}))

    def send_gripper_target(self, position: float, velocity: float) -> None:
        self.command_queue.put(
            ("send_gripper_target", {"position": position, "velocity": velocity})
        )

    def start_example(self, script_name: str) -> None:
        self.command_queue.put(("start_example", {"script_name": script_name}))

    def stop_example(self) -> None:
        self.command_queue.put(("stop_example", {}))

    def _run(self) -> None:
        next_poll = time.monotonic()
        while not self.stop_event.is_set():
            try:
                # 不等待，直接取命令，有就处理，没有就继续
                name, payload = self.command_queue.get_nowait()
                if name == "shutdown":
                    self._handle_disconnect()
                    self.stop_event.set()
                    break
                self._handle_command(name, payload)
            except queue.Empty:
                time.sleep(0.001)  # 队列空时短暂休眠，避免 CPU 空转

            if self.robot is not None and time.monotonic() >= next_poll:
                self._poll_state()
                next_poll = time.monotonic() + self.poll_interval

    def _handle_command(self, name: str, payload: dict) -> None:
        try:
            if name == "connect":
                self._handle_connect(payload["config_path"])
            elif name == "disconnect":
                self._handle_disconnect()
            elif name == "refresh_state":
                self._poll_state(force=True)
            elif name == "stop_robot":
                self._require_robot()
                self.robot.set_stop()
                self._log("已发送停止命令")
            elif name == "send_joint_targets":
                self._handle_send_joint_targets(payload["positions"], payload["velocity"])
            elif name == "go_zero_pose":
                self._handle_send_joint_targets([0.0] * self.robot.motor_count, 0.5)
            elif name == "go_home_pose":
                home_pose = [-0.3, 1.1, 1.1, 0.8, -0.3, 0.3]
                self._handle_send_joint_targets(home_pose, 0.5)
            elif name == "open_gripper":
                self._require_robot()
                self.robot.gripper_open()
                self._log("已发送夹爪打开命令")
            elif name == "close_gripper":
                self._require_robot()
                self.robot.gripper_close()
                self._log("已发送夹爪闭合命令")
            elif name == "send_gripper_target":
                self._require_robot()
                self.robot.gripper_control(payload["position"], payload["velocity"], 0.5)
                self._log(f"已发送夹爪目标: {payload['position']:.3f}")
            elif name == "start_example":
                self._handle_start_example(payload["script_name"])
            elif name == "stop_example":
                self._handle_stop_example()
        except Exception as exc:
            self._log(f"命令执行失败: {exc}", level="ERROR")
            self._publish_snapshot(status=f"错误: {exc}")

    def _handle_connect(self, config_path: str) -> None:
        if self.example_process is not None and self.example_process.poll() is None:
            raise RuntimeError("例程运行中，请先停止例程再连接机械臂")

        self._handle_disconnect()
        self._log(f"连接机械臂: {config_path}")

        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))

        from Panthera_lib import Panthera  # pylint: disable=import-outside-toplevel

        self.robot = Panthera(config_path)
        robot_name = self._resolve_robot_name()
        self.snapshot = RobotSnapshot(
            connected=True,
            status="已连接",
            robot_name=robot_name,
            config_path=config_path,
            motor_count=self.robot.motor_count,
            gripper_id=self.robot.gripper_id,
            rate_limit_hz=int(getattr(self.robot.robot_params, "motor_cmd_rate_limit_hz", 0)),
            joint_limits_lower=self.robot.joint_limits["lower"].astype(float).tolist(),
            joint_limits_upper=self.robot.joint_limits["upper"].astype(float).tolist(),
            gripper_limits=(
                float(self.robot.gripper_limits["lower"]),
                float(self.robot.gripper_limits["upper"]),
            ),
        )
        self._poll_state(force=True)
        self._log("机械臂连接成功")

    def _handle_disconnect(self) -> None:
        self._handle_stop_example()
        if self.robot is not None:
            try:
                self.robot.set_stop()
            except Exception:
                pass
            self.robot = None
        self.snapshot = RobotSnapshot(config_path=self.snapshot.config_path)
        self._publish_snapshot(status="未连接")

    def _handle_send_joint_targets(self, positions: list[float], velocity: float) -> None:
        self._require_robot()
        velocity = max(0.05, float(velocity))
        velocities = [velocity] * self.robot.motor_count
        max_torque = self.robot.max_torque.astype(float).tolist()
        ok = self.robot.Joint_Pos_Vel(positions, velocities, max_torque, iswait=False)
        if ok is False:
            raise RuntimeError("目标位置被限位保护拒绝")
        self._log(f"已发送关节目标: {np.round(np.asarray(positions), 3).tolist()}")

    def _poll_state(self, force: bool = False) -> None:
        self._require_robot()
        if force:
            self._log("刷新状态")

        self.robot.send_get_motor_state_cmd()
        joint_pos = self.robot.get_current_pos().astype(float).tolist()
        joint_vel = self.robot.get_current_vel().astype(float).tolist()
        joint_torque = self.robot.get_current_torque().astype(float).tolist()
        gripper_pos = float(self.robot.get_current_pos_gripper())
        gripper_vel = float(self.robot.get_current_vel_gripper())
        gripper_torque = float(self.robot.get_current_torque_gripper())

        self.snapshot.connected = True
        self.snapshot.status = "在线"
        self.snapshot.updated_at = time.time()
        self.snapshot.joint_pos = joint_pos
        self.snapshot.joint_vel = joint_vel
        self.snapshot.joint_torque = joint_torque
        self.snapshot.gripper_pos = gripper_pos
        self.snapshot.gripper_vel = gripper_vel
        self.snapshot.gripper_torque = gripper_torque
        self._publish_snapshot()

    def _publish_snapshot(self, status: Optional[str] = None) -> None:
        if status is not None:
            self.snapshot.status = status
        self.event_queue.put(("snapshot", self.snapshot))

    def _log(self, message: str, level: str = "INFO") -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.event_queue.put(("log", f"[{timestamp}] [{level}] {message}"))

    def _publish_example_status(self, state: str, name: str = "", message: str = "") -> None:
        self.example_state = state
        self.event_queue.put(
            (
                "example_status",
                {
                    "state": state,
                    "running": state == "running",
                    "name": name,
                    "message": message,
                },
            )
        )

    def _require_robot(self) -> None:
        if self.robot is None:
            raise RuntimeError("机械臂未连接")

    def _handle_start_example(self, script_name: str) -> None:
        if script_name not in EXAMPLE_SCRIPTS:
            self._publish_example_status("idle", script_name)
            raise RuntimeError(f"未知例程: {script_name}")
        if self.example_state in {"starting", "running", "stopping"}:
            self._publish_example_status(self.example_state, self.example_name or script_name, "例程状态忙，忽略启动请求")
            return
        if self.example_process is not None and self.example_process.poll() is None:
            self._publish_example_status("running", self.example_name, "例程已在运行")
            return

        self._publish_example_status("starting", script_name, "正在启动例程")

        if self.robot is not None:
            self._log("启动 SDK 例程前先断开 GUI 当前连接，避免串口设备冲突")
            self._handle_disconnect()

        script_path = SCRIPTS_DIR / script_name
        if not script_path.exists():
            self._publish_example_status("idle", script_name)
            raise RuntimeError(f"例程文件不存在: {script_path}")

        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONNOUSERSITE"] = "1"

        self._log(f"启动例程: {script_name}")
        self.example_name = script_name
        try:
            self.example_process = subprocess.Popen(
                [sys.executable, script_name],
                cwd=str(SCRIPTS_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                start_new_session=True,
            )
        except Exception:
            self.example_name = ""
            self.example_process = None
            self._publish_example_status("idle", script_name)
            raise

        self._publish_example_status("running", script_name, "例程已启动")

        output_thread = threading.Thread(
            target=self._stream_example_output,
            args=(self.example_process, script_name),
            daemon=True,
        )
        output_thread.start()

    def _handle_stop_example(self) -> None:
        if self.example_state == "stopping":
            self._publish_example_status("stopping", self.example_name, "例程正在停止")
            return
        if self.example_process is None or self.example_process.poll() is not None:
            self.example_process = None
            if self.example_name:
                self._publish_example_status("idle", self.example_name)
            self.example_name = ""
            return

        process = self.example_process
        script_name = self.example_name
        self._log(f"停止例程: {script_name}")
        self._publish_example_status("stopping", script_name, "正在停止例程")
        self._stop_process_tree(process)

        if self.example_process is process:
            self.example_process = None
            self.example_name = ""
            self._publish_example_status("idle", script_name, "例程已停止")

    def _stop_process_tree(self, process: subprocess.Popen) -> None:
        try:
            pgid = os.getpgid(process.pid)
        except ProcessLookupError:
            return

        for sig, timeout in (
            (signal.SIGINT, 1.0),
            (signal.SIGTERM, 1.5),
            (signal.SIGKILL, 1.0),
        ):
            if process.poll() is not None:
                return
            try:
                os.killpg(pgid, sig)
            except ProcessLookupError:
                return
            try:
                process.wait(timeout=timeout)
                return
            except subprocess.TimeoutExpired:
                continue

    def _stream_example_output(self, process: subprocess.Popen, script_name: str) -> None:
        try:
            if process.stdout is not None:
                for line in process.stdout:
                    line = line.rstrip()
                    if line:
                        self._log(f"[{script_name}] {line}")
            return_code = process.wait()
            level = "INFO" if return_code == 0 else "ERROR"
            self._log(f"例程结束: {script_name} (code={return_code})", level=level)
        except Exception as exc:
            self._log(f"例程输出线程异常: {exc}", level="ERROR")
        finally:
            if self.example_process is process:
                self.example_process = None
                self.example_name = ""
                self._publish_example_status("idle", script_name, "例程已结束")

    def _resolve_robot_name(self) -> str:
        if self.robot is None:
            return "-"

        robot_params = getattr(self.robot, "robot_params", None)
        if robot_params is not None:
            name = getattr(robot_params, "robot_name", "")
            if name:
                return str(name)

        if isinstance(self.robot.config, dict):
            robot_cfg = self.robot.config.get("robot", {})
            for key in ("robot_name", "name"):
                value = robot_cfg.get(key)
                if value:
                    return str(value)

        return "-"
