# -*- coding: utf-8 -*-
"""
M08: 云台控制模块 (PTZ Controller)
====================================
提供统一的云台控制抽象层，支持 ONVIF 协议硬件控制和无硬件模拟模式。

特性:
    - PTZControllerBase 抽象基类，定义统一接口
    - ONVIFPTZController: 通过 ONVIF 协议控制支持 ONVIF 的摄像头
    - SimulatedPTZController: 无硬件时返回设定值，用于开发/演示
    - PTZFactory: 根据配置自动选择实现
    - 优雅降级 (graceful degradation): ONVIF 库缺失或连接失败时回退到模拟模式
    - 目标跟踪辅助: track_object() 根据目标在画面中的位置计算 PTZ 偏移量

依赖:
    - onvif-zeep (可选): 缺失时自动回退到 SimulatedPTZController
    - 不依赖任何其他第三方库

ONVIF 摄像头开启步骤详见: docs/onvif_setup.md
"""

from __future__ import annotations

import logging
import math
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# ONVIF 库可选导入 (graceful degradation)
# ----------------------------------------------------------------------------
# onvif-zeep 是 ONVIF 协议的 Python 实现，安装命令: pip install onvif-zeep
# 缺失时记录警告并回退到模拟控制器，保证系统可用性。
ONVIF_AVAILABLE = False
ONVIFCamera = None
try:
    from onvif import ONVIFCamera  # type: ignore
    ONVIF_AVAILABLE = True
    logger.info("onvif-zeep 已加载，ONVIF 硬件控制可用")
except ImportError:
    logger.warning(
        "onvif-zeep 未安装，将使用 SimulatedPTZController。"
        "如需硬件控制请执行: pip install onvif-zeep"
    )
except Exception as e:  # 兜底: onvif-zeep 在某些环境下可能依赖 zeep 报错
    logger.warning(
        "onvif-zeep 加载失败 (%s)，将使用 SimulatedPTZController。", e
    )


# ----------------------------------------------------------------------------
# 抽象基类
# ----------------------------------------------------------------------------
class PTZControllerBase(ABC):
    """云台控制器抽象基类。

    所有具体控制器（ONVIF、Simulated、自定义）必须实现以下方法:
        get_position, move_absolute, move_relative,
        zoom_in, zoom_out, track_object, goto_home
    """

    @abstractmethod
    def get_position(self) -> Dict[str, float]:
        """获取当前云台位置。

        Returns:
            Dict[str, float]: {'pan': float, 'tilt': float, 'zoom': float}
                pan/tilt 单位为度，zoom 为归一化倍率 (1.0 = 广角)
        """
        raise NotImplementedError

    @abstractmethod
    def move_absolute(self, pan: float, tilt: float, zoom: float, speed: float = 0.5) -> bool:
        """移动到绝对位置。

        Args:
            pan: 水平角度 (度)
            tilt: 俯仰角度 (度)
            zoom: 归一化变焦 (1.0~最大倍率)
            speed: 移动速度 0.0~1.0
        Returns:
            bool: 是否成功
        """
        raise NotImplementedError

    @abstractmethod
    def move_relative(self, dx: float, dy: float, dz: float = 0.0, speed: float = 0.5) -> bool:
        """相对移动。

        Args:
            dx: 水平相对偏移 (度)
            dy: 垂直相对偏移 (度)
            dz: 变焦相对变化
            speed: 移动速度 0.0~1.0
        Returns:
            bool: 是否成功
        """
        raise NotImplementedError

    @abstractmethod
    def zoom_in(self, level: float = 1.0) -> bool:
        """放大变焦。"""
        raise NotImplementedError

    @abstractmethod
    def zoom_out(self, level: float = 1.0) -> bool:
        """缩小变焦。"""
        raise NotImplementedError

    @abstractmethod
    def track_object(
        self,
        bbox_xyxy: List[int],
        frame_width: int,
        frame_height: int,
    ) -> Tuple[float, float, float]:
        """根据目标在画面中的位置计算 PTZ 偏移量。

        Args:
            bbox_xyxy: 目标边界框 [x1, y1, x2, y2]
            frame_width: 画面宽度
            frame_height: 画面高度
        Returns:
            Tuple[float, float, float]: (dx, dy, dz) 相对偏移量
        """
        raise NotImplementedError

    @abstractmethod
    def goto_home(self) -> bool:
        """回到 Home 位置。"""
        raise NotImplementedError

    # 非抽象的便捷方法
    def is_connected(self) -> bool:
        """是否连接到硬件。"""
        return False

    def stop(self) -> bool:
        """停止当前移动。基类默认实现为空操作。"""
        return True


# ----------------------------------------------------------------------------
# ONVIF 实现
# ----------------------------------------------------------------------------
class ONVIFPTZController(PTZControllerBase):
    """基于 ONVIF 协议的云台控制器。

    适用于支持 ONVIF Profile S/G 的大多数网络摄像头（海康、大华、宇视等）。

    优雅降级策略:
        - 初始化失败不抛异常，仅记录日志，标记为未连接
        - 所有控制方法在未连接状态下返回 False / 默认值
        - 调用方可通过 is_connected() 判断状态
    """

    # ONVIF 归一化空间为 -1.0 ~ 1.0，对应摄像头物理范围
    _NORMALIZED_RANGE = 1.0

    def __init__(
        self,
        camera_ip: str,
        port: int = 80,
        username: str = "admin",
        password: str = "admin",
        profile: str = "Profile_1",
    ) -> None:
        """初始化 ONVIF 控制器。

        Args:
            camera_ip: 摄像头 IP 地址
            port: ONVIF 服务端口 (通常 80 或 8000)
            username: 用户名
            password: 密码
            profile: 媒体 profile 名称
        """
        self.camera_ip = camera_ip
        self.port = port
        self.username = username
        self.password = password
        self.profile = profile

        self._cam = None
        self._ptz = None
        self._media = None
        self._profile_token: Optional[str] = None
        self._connected = False
        self._lock = threading.Lock()  # ONVIF 调用非线程安全
        # 缓存当前位置，避免频繁查询
        self._current_pos: Dict[str, float] = {"pan": 0.0, "tilt": 0.0, "zoom": 1.0}

        if not ONVIF_AVAILABLE:
            logger.warning(
                "ONVIFPTZController 创建于无 onvif-zeep 环境 (ip=%s)，将处于未连接状态",
                camera_ip,
            )
            return

        self._connect()

    # ---- 内部连接逻辑 ----
    def _connect(self) -> None:
        """建立 ONVIF 连接，失败时优雅降级。"""
        try:
            logger.info(
                "正在连接 ONVIF 摄像头 %s:%d (user=%s)",
                self.camera_ip, self.port, self.username,
            )
            self._cam = ONVIFCamera(  # type: ignore[misc]
                self.camera_ip, self.port, self.username, self.password
            )
            # 创建 PTZ 和 Media 服务
            self._ptz = self._cam.create_ptz_service()
            self._media = self._cam.create_media_service()

            # 获取媒体 profile token
            profiles = self._media.GetProfiles()
            if not profiles:
                logger.error("ONVIF 摄像头 %s 无可用 media profile", self.camera_ip)
                self._connected = False
                return

            # 优先匹配指定 profile，否则取第一个
            target_profile = None
            for p in profiles:
                token = getattr(p, "_token", None) or getattr(p, "token", None)
                name = getattr(p, "Name", "")
                if name == self.profile or token == self.profile:
                    target_profile = p
                    break
            if target_profile is None:
                target_profile = profiles[0]
                logger.info(
                    "未找到 profile=%s，使用第一个 profile: %s",
                    self.profile, getattr(target_profile, "Name", "unknown"),
                )

            self._profile_token = (
                getattr(target_profile, "_token", None)
                or getattr(target_profile, "token", None)
            )
            self._connected = True
            logger.info(
                "ONVIF 摄像头 %s 连接成功, profile_token=%s",
                self.camera_ip, self._profile_token,
            )
        except Exception as e:
            # 优雅降级: 不抛异常，仅记录
            logger.error(
                "ONVIF 连接失败 %s:%d: %s。已降级为未连接状态。",
                self.camera_ip, self.port, e,
            )
            self._connected = False
            self._cam = None
            self._ptz = None
            self._media = None

    def _ensure_connected(self) -> bool:
        """检查连接状态，未连接时尝试重连一次。"""
        if self._connected and self._ptz is not None:
            return True
        logger.debug("ONVIF 未连接，尝试重连...")
        if not ONVIF_AVAILABLE:
            return False
        self._connect()
        return self._connected

    # ---- 抽象方法实现 ----
    def is_connected(self) -> bool:
        return self._connected

    def get_position(self) -> Dict[str, float]:
        """获取当前云台位置。

        Returns:
            {'pan': float, 'tilt': float, 'zoom': float}
            未连接时返回缓存的 _current_pos
        """
        if not self._ensure_connected():
            return dict(self._current_pos)
        try:
            with self._lock:
                status = self._ptz.GetStatus(
                    {"ProfileToken": self._profile_token}
                )
                pan = float(status.Position.PanTilt.x) * 180.0  # 归一化转度
                tilt = float(status.Position.PanTilt.y) * 180.0
                zoom = float(status.Position.Zoom.x) + 1.0  # 归一化 0~1 -> 1~2
                self._current_pos = {"pan": pan, "tilt": tilt, "zoom": zoom}
                return dict(self._current_pos)
        except Exception as e:
            logger.warning("get_position 失败: %s，返回缓存值", e)
            return dict(self._current_pos)

    def move_absolute(self, pan: float, tilt: float, zoom: float, speed: float = 0.5) -> bool:
        """移动到绝对位置 (pan/tilt 单位度，zoom 归一化)。"""
        if not self._ensure_connected():
            logger.warning("move_absolute: 未连接，操作忽略")
            return False
        try:
            speed = max(0.0, min(1.0, speed))
            # 度 -> ONVIF 归一化 (-1.0 ~ 1.0)
            pan_n = max(-1.0, min(1.0, pan / 180.0))
            tilt_n = max(-1.0, min(1.0, tilt / 180.0))
            zoom_n = max(0.0, min(1.0, zoom - 1.0))
            with self._lock:
                self._ptz.AbsoluteMove(
                    {
                        "ProfileToken": self._profile_token,
                        "Position": {
                            "PanTilt": {"x": pan_n, "y": tilt_n},
                            "Zoom": {"x": zoom_n},
                        },
                        "Speed": {
                            "PanTilt": {"x": speed, "y": speed},
                            "Zoom": {"x": speed},
                        },
                    }
                )
            self._current_pos = {"pan": pan, "tilt": tilt, "zoom": zoom}
            logger.info("move_absolute -> pan=%.2f tilt=%.2f zoom=%.2f", pan, tilt, zoom)
            return True
        except Exception as e:
            logger.error("move_absolute 失败: %s", e)
            return False

    def move_relative(self, dx: float, dy: float, dz: float = 0.0, speed: float = 0.5) -> bool:
        """相对移动 (dx/dy 单位度)。"""
        if not self._ensure_connected():
            logger.warning("move_relative: 未连接，操作忽略")
            return False
        try:
            speed = max(0.0, min(1.0, speed))
            dx_n = max(-1.0, min(1.0, dx / 180.0))
            dy_n = max(-1.0, min(1.0, dy / 180.0))
            dz_n = max(-1.0, min(1.0, dz))
            with self._lock:
                self._ptz.RelativeMove(
                    {
                        "ProfileToken": self._profile_token,
                        "Translation": {
                            "PanTilt": {"x": dx_n, "y": dy_n},
                            "Zoom": {"x": dz_n},
                        },
                        "Speed": {
                            "PanTilt": {"x": speed, "y": speed},
                            "Zoom": {"x": speed},
                        },
                    }
                )
            # 更新缓存位置
            self._current_pos["pan"] += dx
            self._current_pos["tilt"] += dy
            self._current_pos["zoom"] = max(1.0, self._current_pos["zoom"] + dz)
            logger.info("move_relative -> dx=%.2f dy=%.2f dz=%.2f", dx, dy, dz)
            return True
        except Exception as e:
            logger.error("move_relative 失败: %s", e)
            return False

    def zoom_in(self, level: float = 1.0) -> bool:
        """放大变焦。level 控制相对变化幅度 (0~1)。"""
        level = max(0.0, min(1.0, level))
        return self.move_relative(0.0, 0.0, level * 0.1)

    def zoom_out(self, level: float = 1.0) -> bool:
        """缩小变焦。level 控制相对变化幅度 (0~1)。"""
        level = max(0.0, min(1.0, level))
        return self.move_relative(0.0, 0.0, -level * 0.1)

    def track_object(
        self,
        bbox_xyxy: List[int],
        frame_width: int,
        frame_height: int,
    ) -> Tuple[float, float, float]:
        """根据目标在画面中的位置计算 PTZ 相对偏移量。

        将目标中心相对画面中心的归一化偏移转换为 PTZ 角度偏移。
        偏移越大，PTZ 移动幅度越大（带死区防止抖动）。

        Args:
            bbox_xyxy: [x1, y1, x2, y2]
            frame_width: 画面宽度 (像素)
            frame_height: 画面高度 (像素)
        Returns:
            (dx, dy, dz) 相对偏移量 (度 / 归一化)
        """
        if len(bbox_xyxy) != 4:
            logger.warning("track_object: bbox 长度异常 %s", bbox_xyxy)
            return (0.0, 0.0, 0.0)

        x1, y1, x2, y2 = bbox_xyxy
        # 目标中心
        obj_cx = (x1 + x2) / 2.0
        obj_cy = (y1 + y2) / 2.0
        # 画面中心
        frame_cx = frame_width / 2.0
        frame_cy = frame_height / 2.0
        # 归一化偏移 (-1 ~ 1)
        norm_dx = (obj_cx - frame_cx) / (frame_width / 2.0)
        norm_dy = (obj_cy - frame_cy) / (frame_height / 2.0)

        # 死区: 偏移小于 5% 不移动，避免抖动
        dead_zone = 0.05
        if abs(norm_dx) < dead_zone:
            norm_dx = 0.0
        if abs(norm_dy) < dead_zone:
            norm_dy = 0.0

        # 转换为角度偏移 (假设画面水平 FOV ~60 度，垂直 FOV ~35 度)
        # 实际应根据摄像头参数调整
        horiz_fov_deg = 60.0
        vert_fov_deg = 35.0
        dx_deg = norm_dx * horiz_fov_deg * 0.5  # 半 FOV 范围
        dy_deg = norm_dy * vert_fov_deg * 0.5

        # 根据目标大小决定是否变焦 (目标小于画面 10% 时放大)
        target_size = max((x2 - x1), (y2 - y1))
        target_ratio = target_size / float(max(frame_width, frame_height))
        dz = 0.0
        if target_ratio < 0.10:
            dz = 0.05  # 缓慢放大
        elif target_ratio > 0.50:
            dz = -0.05  # 缩小

        logger.debug(
            "track_object: norm=(%.3f,%.3f) deg=(%.2f,%.2f) dz=%.3f",
            norm_dx, norm_dy, dx_deg, dy_deg, dz,
        )
        return (dx_deg, dy_deg, dz)

    def goto_home(self) -> bool:
        """回到 Home 位置 (pan=0, tilt=0, zoom=1)。"""
        return self.move_absolute(0.0, 0.0, 1.0, speed=0.8)

    def stop(self) -> bool:
        """停止当前 PTZ 移动。"""
        if not self._ensure_connected():
            return False
        try:
            with self._lock:
                self._ptz.Stop(
                    {
                        "ProfileToken": self._profile_token,
                        "PanTilt": True,
                        "Zoom": True,
                    }
                )
            return True
        except Exception as e:
            logger.error("stop 失败: %s", e)
            return False


# ----------------------------------------------------------------------------
# 模拟实现 (无硬件)
# ----------------------------------------------------------------------------
class SimulatedPTZController(PTZControllerBase):
    """无硬件模拟控制器。

    用于开发、测试、演示场景。所有方法返回设定值，不依赖任何硬件。
    内部维护虚拟位置状态，move 操作会更新状态。
    """

    def __init__(
        self,
        initial_pan: float = 0.0,
        initial_tilt: float = 0.0,
        initial_zoom: float = 1.0,
    ) -> None:
        self._pos: Dict[str, float] = {
            "pan": initial_pan,
            "tilt": initial_tilt,
            "zoom": initial_zoom,
        }
        self._lock = threading.Lock()
        logger.info(
            "SimulatedPTZController 初始化: pan=%.2f tilt=%.2f zoom=%.2f",
            initial_pan, initial_tilt, initial_zoom,
        )

    def is_connected(self) -> bool:
        """模拟器始终可用。"""
        return True

    def get_position(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._pos)

    def move_absolute(self, pan: float, tilt: float, zoom: float, speed: float = 0.5) -> bool:
        with self._lock:
            self._pos = {"pan": pan, "tilt": tilt, "zoom": zoom}
        logger.debug("[Sim] move_absolute -> %s", self._pos)
        return True

    def move_relative(self, dx: float, dy: float, dz: float = 0.0, speed: float = 0.5) -> bool:
        with self._lock:
            self._pos["pan"] += dx
            self._pos["tilt"] += dy
            self._pos["zoom"] = max(1.0, self._pos["zoom"] + dz)
        logger.debug("[Sim] move_relative -> %s", self._pos)
        return True

    def zoom_in(self, level: float = 1.0) -> bool:
        return self.move_relative(0.0, 0.0, level * 0.1)

    def zoom_out(self, level: float = 1.0) -> bool:
        return self.move_relative(0.0, 0.0, -level * 0.1)

    def track_object(
        self,
        bbox_xyxy: List[int],
        frame_width: int,
        frame_height: int,
    ) -> Tuple[float, float, float]:
        """模拟器复用 ONVIF 的偏移计算逻辑。"""
        # 复用相同算法，保持一致性
        if len(bbox_xyxy) != 4:
            return (0.0, 0.0, 0.0)
        x1, y1, x2, y2 = bbox_xyxy
        obj_cx = (x1 + x2) / 2.0
        obj_cy = (y1 + y2) / 2.0
        frame_cx = frame_width / 2.0
        frame_cy = frame_height / 2.0
        norm_dx = (obj_cx - frame_cx) / (frame_width / 2.0)
        norm_dy = (obj_cy - frame_cy) / (frame_height / 2.0)
        dead_zone = 0.05
        if abs(norm_dx) < dead_zone:
            norm_dx = 0.0
        if abs(norm_dy) < dead_zone:
            norm_dy = 0.0
        dx_deg = norm_dx * 60.0 * 0.5
        dy_deg = norm_dy * 35.0 * 0.5
        target_size = max((x2 - x1), (y2 - y1))
        target_ratio = target_size / float(max(frame_width, frame_height))
        dz = 0.0
        if target_ratio < 0.10:
            dz = 0.05
        elif target_ratio > 0.50:
            dz = -0.05
        return (dx_deg, dy_deg, dz)

    def goto_home(self) -> bool:
        return self.move_absolute(0.0, 0.0, 1.0, speed=0.8)


# ----------------------------------------------------------------------------
# 工厂方法
# ----------------------------------------------------------------------------
def PTZFactory(config: Optional[Dict[str, Any]] = None) -> PTZControllerBase:
    """根据配置创建 PTZ 控制器。

    配置示例::

        # ONVIF 硬件模式
        {
            "mode": "onvif",
            "camera_ip": "192.168.1.64",
            "port": 80,
            "username": "admin",
            "password": "your_password",
            "profile": "Profile_1"
        }

        # 模拟模式
        {"mode": "simulated"}
        # 或不传 config

    优雅降级规则:
        1. mode="onvif" 但 onvif-zeep 未安装 -> 回退到 Simulated
        2. mode="onvif" 但连接失败 -> 返回 ONVIF 实例 (is_connected=False)，
           控制方法会安全返回 False，调用方可通过 is_connected() 判断
        3. 未知 mode -> 默认 Simulated

    Args:
        config: 配置字典
    Returns:
        PTZControllerBase 实例
    """
    if config is None:
        config = {}

    mode = str(config.get("mode", "simulated")).lower().strip()
    logger.info("PTZFactory: mode=%s, config=%s", mode, config)

    if mode == "onvif":
        if not ONVIF_AVAILABLE:
            logger.warning(
                "配置为 onvif 模式但 onvif-zeep 未安装，回退到 SimulatedPTZController"
            )
            return SimulatedPTZController()

        controller = ONVIFPTZController(
            camera_ip=str(config.get("camera_ip", "192.168.1.64")),
            port=int(config.get("port", 80)),
            username=str(config.get("username", "admin")),
            password=str(config.get("password", "admin")),
            profile=str(config.get("profile", "Profile_1")),
        )
        # 连接失败时仍返回 ONVIF 实例，调用方可通过 is_connected() 判断
        # 这样后续重连逻辑可复用
        if not controller.is_connected():
            logger.warning(
                "ONVIF 连接失败，已降级。可调用 is_connected() 检查状态，"
                "后续调用会自动尝试重连。"
            )
        return controller

    # 默认 / simulated / 未知
    if mode not in ("simulated", "sim", "mock"):
        logger.warning("未知 PTZ mode=%s，使用 SimulatedPTZController", mode)
    return SimulatedPTZController(
        initial_pan=float(config.get("initial_pan", 0.0)),
        initial_tilt=float(config.get("initial_tilt", 0.0)),
        initial_zoom=float(config.get("initial_zoom", 1.0)),
    )


# ----------------------------------------------------------------------------
# 模块自检 (python -m api.ptz_controller)
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 60)
    print("PTZ Controller 自检")
    print("=" * 60)

    # 1. 模拟模式
    print("\n[1] SimulatedPTZController 测试")
    sim = PTZFactory({"mode": "simulated"})
    print(f"  is_connected: {sim.is_connected()}")
    print(f"  position: {sim.get_position()}")
    sim.move_absolute(30.0, -15.0, 2.0)
    print(f"  after move_absolute: {sim.get_position()}")
    sim.move_relative(-5.0, 5.0)
    print(f"  after move_relative: {sim.get_position()}")
    sim.zoom_in(0.5)
    print(f"  after zoom_in: {sim.get_position()}")
    dx, dy, dz = sim.track_object([400, 200, 600, 400], 1280, 720)
    print(f"  track_object offset: dx={dx:.2f} dy={dy:.2f} dz={dz:.2f}")
    sim.goto_home()
    print(f"  after goto_home: {sim.get_position()}")

    # 2. ONVIF 模式 (会优雅降级)
    print("\n[2] ONVIFPTZController 测试 (无硬件将优雅降级)")
    onvif = PTZFactory({
        "mode": "onvif",
        "camera_ip": "192.168.1.64",
        "port": 80,
        "username": "admin",
        "password": "admin",
    })
    print(f"  is_connected: {onvif.is_connected()}")
    print(f"  position: {onvif.get_position()}")
    print(f"  move_absolute result: {onvif.move_absolute(10, 5, 1.5)}")

    print("\n自检完成。")
