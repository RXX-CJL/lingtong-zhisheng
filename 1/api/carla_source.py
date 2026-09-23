# -*- coding: utf-8 -*-
"""
CARLA 仿真环境数据源抽象。

CarlaSource 与摄像头(VideoCapture)/视频文件同级，作为统一的数据源接入
交通检测管线。设计目标：
    1. 接口与现有 VideoCapture 保持一致（get_frame 返回 BGR np.ndarray）
    2. 优雅降级：CARLA 未安装 / 未启动时，connect() 返回 False，
       其余方法返回空值，不抛异常，保证主程序可继续运行
    3. CARLA 模块采用 try/except 导入，不强制安装 carla 包
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

import numpy as np

# 尝试导入 carla 模块，失败时降级为 None，所有方法将走优雅降级路径
try:
    import carla  # type: ignore
    _CARLA_AVAILABLE = True
except ImportError:  # pragma: no cover - 环境相关
    carla = None  # type: ignore
    _CARLA_AVAILABLE = False

logger = logging.getLogger(__name__)


class CarlaSource:
    """CARLA 仿真数据源。

    用法示例::

        src = CarlaSource()
        if not src.connect('localhost', 2000):
            print('CARLA 未启动，降级运行')
        src.set_synchronous_mode(0.05)
        src.spawn_vehicles(20)
        src.spawn_walkers(10)
        src.attach_camera(640, 480, 90)
        frame = src.get_frame()        # BGR np.ndarray，兼容 OpenCV
        states = src.get_actors_state()
    """

    def __init__(self) -> None:
        self._connected: bool = False
        self._client: Any = None
        self._world: Any = None
        self._tm: Any = None  # TrafficManager
        self._tm_port: int = 8000

        # actor 池
        self._vehicles: List[Any] = []
        self._walkers: List[Any] = []
        self._walker_controllers: List[Any] = []
        self._camera: Any = None
        self._spawned_actors: List[Any] = []  # 全部生成的 actor，便于清理

        # 帧缓冲（线程安全）
        self._frame_lock = threading.Lock()
        self._current_frame: Optional[np.ndarray] = None

        # 同步模式标记
        self._synchronous: bool = False
        self._fixed_delta: float = 0.05

    # ------------------------------------------------------------------ #
    # 连接 / 生命周期
    # ------------------------------------------------------------------ #
    def connect(self, host: str = 'localhost', port: int = 2000) -> bool:
        """连接 CARLA 服务器。

        成功返回 True；若 carla 未安装或服务器未启动，返回 False（不抛异常）。
        """
        if not _CARLA_AVAILABLE:
            logger.warning('[CarlaSource] carla 模块未安装，connect() 降级返回 False')
            return False

        try:
            self._client = carla.Client(host, port)
            self._client.set_timeout(10.0)
            # 触发一次真实通信以验证服务器在线
            self._world = self._client.get_world()
            self._connected = True
            logger.info('[CarlaSource] 已连接 CARLA %s:%d', host, port)
            return True
        except Exception as exc:  # noqa: BLE001 - 优雅降级，需捕获所有异常
            logger.warning('[CarlaSource] 连接 CARLA 失败: %s', exc)
            self._connected = False
            self._client = None
            self._world = None
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------ #
    # 交通生成
    # ------------------------------------------------------------------ #
    def spawn_vehicles(self, n: int = 20) -> List[int]:
        """生成 n 辆自动驾驶车辆，返回 actor id 列表。"""
        if not self._ensure_connected():
            return []
        try:
            blueprint_lib = self._world.get_blueprint_library()
            vehicle_bps = blueprint_lib.filter('vehicle.*')
            spawn_points = self._world.get_map().get_spawn_points()
            if not spawn_points:
                logger.warning('[CarlaSource] 地图无可用生成点')
                return []

            # TrafficManager（同步模式需要同步 TM）
            if self._tm is None:
                self._tm = self._client.get_trafficmanager(self._tm_port)
                if self._synchronous:
                    try:
                        self._tm.set_synchronous_mode(True)
                    except Exception as exc:  # noqa: BLE001
                        logger.debug('[CarlaSource] TM 同步设置失败: %s', exc)

            import random
            ids: List[int] = []
            for i in range(min(n, len(spawn_points))):
                bp = random.choice(vehicle_bps)
                if bp.has_attribute('color'):
                    color = random.choice(bp.get_attribute('color').recommended_values)
                    bp.set_attribute('color', color)
                bp.set_attribute('role_name', 'autopilot')
                point = spawn_points[i % len(spawn_points)]
                actor = self._world.try_spawn_actor(bp, point)
                if actor is None:
                    continue
                actor.set_autopilot(True)
                try:
                    self._tm.set_vehicle_target_speed(actor, 30.0)
                except Exception:  # noqa: BLE001
                    pass
                self._vehicles.append(actor)
                self._spawned_actors.append(actor)
                ids.append(actor.id)
            logger.info('[CarlaSource] 生成 %d 辆车辆', len(ids))
            return ids
        except Exception as exc:  # noqa: BLE001
            logger.error('[CarlaSource] spawn_vehicles 失败: %s', exc)
            return []

    def spawn_walkers(self, n: int = 10) -> List[int]:
        """生成 n 个行人，返回 actor id 列表。"""
        if not self._ensure_connected():
            return []
        try:
            blueprint_lib = self._world.get_blueprint_library()
            walker_bps = blueprint_lib.filter('walker.pedestrian.*')
            controller_bp = blueprint_lib.find('controller.ai.walker')
            if not walker_bps:
                return []

            import random
            spawn_points = []
            for _ in range(n):
                loc = self._world.get_random_location_from_navigation()
                if loc is None:
                    continue
                spawn_points.append(carla.Transform(loc))
            ids: List[int] = []
            for sp in spawn_points:
                bp = random.choice(walker_bps)
                walker = self._world.try_spawn_actor(bp, sp)
                if walker is None:
                    continue
                controller = self._world.try_spawn_actor(controller_bp, carla.Transform(), walker)
                if controller is None:
                    walker.destroy()
                    continue
                # 随机终点
                dest = self._world.get_random_location_from_navigation()
                if dest is not None:
                    controller.start()
                    controller.go_to_location(dest)
                    controller.set_max_speed(1.4)
                self._walkers.append(walker)
                self._walker_controllers.append(controller)
                self._spawned_actors.extend([walker, controller])
                ids.append(walker.id)
            logger.info('[CarlaSource] 生成 %d 个行人', len(ids))
            return ids
        except Exception as exc:  # noqa: BLE001
            logger.error('[CarlaSource] spawn_walkers 失败: %s', exc)
            return []

    # ------------------------------------------------------------------ #
    # 摄像头传感器
    # ------------------------------------------------------------------ #
    def attach_camera(self, width: int = 640, height: int = 480, fov: int = 90,
                      attach_to: Any = None) -> bool:
        """生成 RGB 摄像头传感器，回调将帧存入缓冲（BGR 格式）。

        attach_to: 指定挂载的 vehicle actor；为 None 时挂载到第一辆车，
                   若无车则挂载到一个 spectator 跟随的静态点上。
        """
        if not self._ensure_connected():
            return False
        try:
            blueprint_lib = self._world.get_blueprint_library()
            cam_bp = blueprint_lib.find('sensor.camera.rgb')
            cam_bp.set_attribute('image_size_x', str(width))
            cam_bp.set_attribute('image_size_y', str(height))
            cam_bp.set_attribute('fov', str(fov))
            cam_bp.set_attribute('sensor_tick', '0.0')

            # 挂载点：前挡风上方
            transform = carla.Transform(
                carla.Location(x=1.5, z=2.4),
                carla.Rotation(pitch=-15.0),
            )
            parent = attach_to
            if parent is None and self._vehicles:
                parent = self._vehicles[0]
            self._camera = self._world.spawn_actor(cam_bp, transform, attach_to=parent)
            self._camera.listen(self._on_camera_image)
            self._spawned_actors.append(self._camera)
            logger.info('[CarlaSource] 摄像头已挂载 %dx%d fov=%d', width, height, fov)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error('[CarlaSource] attach_camera 失败: %s', exc)
            return False

    def _on_camera_image(self, image: Any) -> None:
        """CARLA 摄像头回调：raw_data 为 BGRA，取前 3 通道即 BGR，兼容 OpenCV。"""
        try:
            arr = np.frombuffer(image.raw_data, dtype=np.uint8)
            arr = arr.reshape((image.height, image.width, 4))
            bgr = arr[:, :, :3].copy()  # BGR
            with self._frame_lock:
                self._current_frame = bgr
        except Exception as exc:  # noqa: BLE001
            logger.debug('[CarlaSource] 帧转换失败: %s', exc)

    def get_frame(self) -> Optional[np.ndarray]:
        """获取最新帧（BGR np.ndarray，兼容 OpenCV）；无帧时返回 None。"""
        with self._frame_lock:
            if self._current_frame is None:
                return None
            return self._current_frame.copy()

    # ------------------------------------------------------------------ #
    # 状态查询
    # ------------------------------------------------------------------ #
    def get_actors_state(self) -> List[Dict[str, Any]]:
        """获取所有车辆/行人的状态列表。

        每项结构：{id, type, location, rotation, velocity}
        - type: 'vehicle' | 'walker'
        - location/rotation: {x, y, z} / {pitch, yaw, roll}
        - velocity: m/s 标量
        """
        if not self._ensure_connected():
            return []
        states: List[Dict[str, Any]] = []
        try:
            for actor in self._vehicles:
                states.append(self._actor_state(actor, 'vehicle'))
            for actor in self._walkers:
                states.append(self._actor_state(actor, 'walker'))
        except Exception as exc:  # noqa: BLE001
            logger.error('[CarlaSource] get_actors_state 失败: %s', exc)
        return states

    def _actor_state(self, actor: Any, atype: str) -> Dict[str, Any]:
        tf = actor.get_transform()
        loc = tf.location
        rot = tf.rotation
        vel = actor.get_velocity()
        speed = float((vel.x ** 2 + vel.y ** 2 + vel.z ** 2) ** 0.5)
        return {
            'id': int(actor.id),
            'type': atype,
            'location': {'x': float(loc.x), 'y': float(loc.y), 'z': float(loc.z)},
            'rotation': {'pitch': float(rot.pitch), 'yaw': float(rot.yaw), 'roll': float(rot.roll)},
            'velocity': speed,
        }

    def get_traffic_lights(self) -> List[Dict[str, Any]]:
        """获取所有红绿灯状态：{id, location, state}。

        state 取值：'red' | 'yellow' | 'green' | 'off' | 'unknown'
        """
        if not self._ensure_connected():
            return []
        lights: List[Dict[str, Any]] = []
        try:
            tls = self._world.get_actors().filter('traffic.traffic_light*')
            for tl in tls:
                state_map = {
                    carla.TrafficLightState.Red: 'red',
                    carla.TrafficLightState.Yellow: 'yellow',
                    carla.TrafficLightState.Green: 'green',
                    carla.TrafficLightState.Off: 'off',
                }
                loc = tl.get_transform().location
                lights.append({
                    'id': int(tl.id),
                    'location': {'x': float(loc.x), 'y': float(loc.y), 'z': float(loc.z)},
                    'state': state_map.get(tl.state, 'unknown'),
                })
        except Exception as exc:  # noqa: BLE001
            logger.error('[CarlaSource] get_traffic_lights 失败: %s', exc)
        return lights

    # ------------------------------------------------------------------ #
    # 同步模式
    # ------------------------------------------------------------------ #
    def set_synchronous_mode(self, dt: float = 0.05) -> bool:
        """开启同步模式，固定步长 dt 秒。"""
        if not self._ensure_connected():
            return False
        try:
            settings = self._world.get_settings()
            settings.synchronous_mode = True
            settings.fixed_delta_seconds = dt
            self._world.apply_settings(settings)
            self._synchronous = True
            self._fixed_delta = dt
            if self._tm is not None:
                try:
                    self._tm.set_synchronous_mode(True)
                except Exception:  # noqa: BLE001
                    pass
            logger.info('[CarlaSource] 同步模式已开启 dt=%.3f', dt)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error('[CarlaSource] set_synchronous_mode 失败: %s', exc)
            return False

    def set_asynchronous_mode(self) -> bool:
        """切回异步模式。"""
        if not self._ensure_connected():
            return False
        try:
            settings = self._world.get_settings()
            settings.synchronous_mode = False
            settings.fixed_delta_seconds = None
            self._world.apply_settings(settings)
            self._synchronous = False
            if self._tm is not None:
                try:
                    self._tm.set_synchronous_mode(False)
                except Exception:  # noqa: BLE001
                    pass
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error('[CarlaSource] set_asynchronous_mode 失败: %s', exc)
            return False

    def tick(self) -> bool:
        """同步模式下推进一帧；异步模式下等待服务器 tick。"""
        if not self._ensure_connected():
            return False
        try:
            if self._synchronous:
                self._world.tick()
            else:
                self._world.wait_for_tick()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error('[CarlaSource] tick 失败: %s', exc)
            return False

    # ------------------------------------------------------------------ #
    # 清理
    # ------------------------------------------------------------------ #
    def disconnect(self) -> None:
        """清理所有 actor 并断开连接（幂等）。"""
        if not _CARLA_AVAILABLE:
            self._reset_state()
            return
        # 异步模式先切回，避免服务器卡在同步等待
        try:
            if self._world is not None:
                settings = self._world.get_settings()
                if settings.synchronous_mode:
                    settings.synchronous_mode = False
                    settings.fixed_delta_seconds = None
                    self._world.apply_settings(settings)
        except Exception:  # noqa: BLE001
            pass

        # 销毁 actor（逆序：先传感器再车/人）
        for actor in reversed(self._spawned_actors):
            try:
                if actor.is_alive:
                    actor.stop() if hasattr(actor, 'stop') else None
                    actor.destroy()
            except Exception:  # noqa: BLE001
                pass
        self._reset_state()
        logger.info('[CarlaSource] 已断开并清理所有 actor')

    def _reset_state(self) -> None:
        self._vehicles.clear()
        self._walkers.clear()
        self._walker_controllers.clear()
        self._spawned_actors.clear()
        self._camera = None
        self._tm = None
        self._world = None
        self._client = None
        self._connected = False
        self._synchronous = False
        with self._frame_lock:
            self._current_frame = None

    # ------------------------------------------------------------------ #
    # 辅助
    # ------------------------------------------------------------------ #
    def _ensure_connected(self) -> bool:
        """检查连接状态；未连接时记录一次降级提示。"""
        if not self._connected or self._world is None:
            logger.debug('[CarlaSource] 未连接 CARLA，方法降级返回空值')
            return False
        return True

    def load_town(self, town: str = 'Town01') -> bool:
        """加载指定城镇地图（如 Town01 / Town03）。"""
        if not self._ensure_connected():
            return False
        try:
            self._world = self._client.load_world(town)
            logger.info('[CarlaSource] 已加载地图 %s', town)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error('[CarlaSource] load_town(%s) 失败: %s', town, exc)
            return False

    def spawn_red_light_violator(self) -> Optional[int]:
        """生成一辆闯红灯车辆：关闭 autopilot，硬编码冲过路口。

        返回 vehicle actor id，失败返回 None。
        """
        if not self._ensure_connected():
            return None
        try:
            blueprint_lib = self._world.get_blueprint_library()
            vehicle_bps = blueprint_lib.filter('vehicle.*')
            spawn_points = self._world.get_map().get_spawn_points()
            if not spawn_points:
                return None
            import random
            bp = random.choice(vehicle_bps)
            bp.set_attribute('role_name', 'violator')
            actor = self._world.try_spawn_actor(bp, spawn_points[0])
            if actor is None:
                return None
            # 关闭 autopilot，手动控制全速直行
            actor.set_autopilot(False)
            self._vehicles.append(actor)
            self._spawned_actors.append(actor)
            control = carla.VehicleControl(throttle=1.0, steer=0.0, brake=0.0)
            actor.apply_control(control)
            logger.info('[CarlaSource] 闯红灯车辆已生成 id=%d', actor.id)
            return int(actor.id)
        except Exception as exc:  # noqa: BLE001
            logger.error('[CarlaSource] spawn_red_light_violator 失败: %s', exc)
            return None

    # 上下文管理协议，便于 with 使用
    def __enter__(self) -> 'CarlaSource':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()
