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
import math
import os
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


# --------------------------------------------------------------------------- #
# 世界坐标 -> 像素投影（2026-11-07 由 WorkBuddy 新增）
#
# 为什么需要：任务单要求「按**停止线地理坐标**找灯」，而不是硬编码 Actor ID
# （CARLA 重启后灯的 Actor ID 会变）。要判断「这条停止线在画面里的哪个像素」，
# 就必须有一个世界坐标 -> 像素的正向投影。
#
# 几何与 speed_calibration.make_unprojector() **完全同源**（同一套相机基），
# 只是方向相反（那边是像素 -> 地面，这里是地面 -> 像素），避免两套实现打架
# —— 历史上正是"两个几何实现不一致"造成过 2 倍误差。
# --------------------------------------------------------------------------- #
def project_world_to_pixel(point, cam: Dict[str, Any]):
    """世界坐标 -> (u, v, depth)；相机背后或无效时返回 None。

    Args:
        point: (x, y, z) 世界坐标（可带高度，用于把停止线抬到路面以上一点点）
        cam: 相机几何字典 {x, y, z, pitch, yaw, roll, width, height, fov}
    """
    try:
        px, py, pz = float(point[0]), float(point[1]), float(point[2])
        cx = float(cam['x'])
        cy = float(cam['y'])
        cz = float(cam['z'])
        pitch = math.radians(float(cam.get('pitch', 0.0)))
        yaw = math.radians(float(cam.get('yaw', 0.0)))
        roll = math.radians(float(cam.get('roll', 0.0)))
        w = int(cam.get('width') or 1280)
        h = int(cam.get('height') or 720)
        fov = float(cam.get('fov') or 90.0)
    except (TypeError, ValueError, KeyError, IndexError):
        return None

    cp, sp = math.cos(pitch), math.sin(pitch)
    cyaw, syaw = math.cos(yaw), math.sin(yaw)
    cr, sr = math.cos(roll), math.sin(roll)

    # 相机基（pitch 向下为负；yaw 0 = +X，逆时针为正，与 CARLA 约定一致）
    fwd = (cp * cyaw, cp * syaw, sp)
    right = (-syaw, cyaw, 0.0)
    up = (-sp * cyaw, -sp * syaw, cp)
    if abs(roll) > 1e-9:
        right = (right[0] * cr + up[0] * sr, right[1] * cr + up[1] * sr, right[2] * cr + up[2] * sr)
        up = (-right[0] * sr + up[0] * cr, -right[1] * sr + up[1] * cr, -right[2] * sr + up[2] * cr)

    d = (px - cx, py - cy, pz - cz)
    depth = sum(d[i] * fwd[i] for i in range(3))
    if depth <= 0.05:
        return None
    lat = sum(d[i] * right[i] for i in range(3))
    vert = sum(d[i] * up[i] for i in range(3))
    f = w / (2.0 * math.tan(math.radians(fov) / 2.0))
    return (w / 2.0 + f * lat / depth, h / 2.0 - f * vert / depth, depth)


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
        # 相机几何（2026-11-07 由 WorkBuddy 新增）
        # 记录 attach_camera 实际使用的机位与画幅，供「世界坐标 -> 像素」投影使用。
        # 不从 actor 反查：新建 actor 在下一次 tick 前 get_transform() 返回 (0,0,0)。
        # ------------------------------------------------------------------ #
        self._camera_geom: Optional[Dict[str, Any]] = None

        # ------------------------------------------------------------------ #
        # 闯红灯违规车会话（2026-11-07 由 WorkBuddy 新增）
        # ------------------------------------------------------------------ #
        self._violator_lock = threading.Lock()
        self._violator_actor: Any = None
        self._violator_light_id: Optional[int] = None
        self._violator_path: List[Any] = []          # 纯追踪用的下游路点
        self._violator_stop_point: Optional[tuple] = None
        # 违规车「压过停止线」的像素阈值（画面里那条白线的 y）
        self._violator_stop_pixel_v: float = 0.0
        self._violator_thread: Optional[threading.Thread] = None
        self._violator_stop_event = threading.Event()
        self._violator_session: Dict[str, Any] = {}   # 可观测状态（/carla/actors 暴露）
        self._controlled_approach: Optional[Dict[str, Any]] = None  # 受控红灯进口缓存

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

    def is_connected(self) -> bool:
        """是否已连接。

        2026-11-07 修：原为 @property，但 routers/realtime.py 与
        realtime_detector.py 共 8 处调用点都写成 src.is_connected()（带括号）。
        property 被调用会抛 TypeError: 'bool' object is not callable →
        所有 CARLA 路由（/carla/status、/carla/connect、/carla/next-scene、
        /carla/actors）一被访问就 500。改成普通方法，与全部调用点一致。
        """
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
                      attach_to: Any = None, mount_on_vehicle: bool = True) -> bool:
        """生成 RGB 摄像头传感器，回调将帧存入缓冲（BGR 格式）。

        attach_to: 指定挂载的 vehicle actor；为 None 时挂载到第一辆车，
                   若无车则挂载到**路侧固定机位**。

        2026-11-07 修（实测踩到，这是画面里看不到车的真因）：
            原实现在 ``parent is None`` 时直接
            ``carla.Transform(Location(x=1.5, z=2.4), Rotation(pitch=-15))``
            传给 ``spawn_actor(..., attach_to=None)``。
            attach_to=None 时这个 Transform 是**世界坐标**，即相机被放在
            世界原点 (1.5, 0, 2.4) —— Town10HD 里那是一栋建筑的内部/墙边。
            实测抓到的帧就是一堵墙，YOLO 当然 100% no detections。

            另外 ``x=1.5, z=2.4`` 这个偏移本来是**相对车辆**的「前挡风上方」，
            只有在 attach_to 真是一辆车时才有意义；没有父 actor 时复用它
            是把两套坐标系混用了。

            现在：有父车 -> 保持原「前挡风」相对偏移（自驾视角）；
                  无父车 -> 用路侧固定机位，坐标来自环境变量
                  CARLA_CAM_X / Y / Z / PITCH / YAW，缺省取项目手册记录的
                  机位 (-15.720, -63.145, 5.732, pitch=-23.445, yaw=179.536)。
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

            parent = attach_to
            if parent is None and self._vehicles and mount_on_vehicle:
                parent = self._vehicles[0]

            self._camera_geom = None
            if parent is not None:
                # 车载视角：沿用原「前挡风上方」相对偏移
                transform = carla.Transform(
                    carla.Location(x=1.5, z=2.4),
                    carla.Rotation(pitch=-15.0),
                )
                mode = f'vehicle(id={getattr(parent, "id", "?")})'
            else:
                # 路侧固定机位：世界坐标，可直接用于标定
                import os as _os

                def _f(name: str, default: float) -> float:
                    try:
                        return float(_os.environ.get(name, default))
                    except Exception:  # noqa: BLE001
                        return float(default)

                _x = _f('CARLA_CAM_X', -15.720)
                _y = _f('CARLA_CAM_Y', -63.145)
                _z = _f('CARLA_CAM_Z', 5.732)
                _pitch = _f('CARLA_CAM_PITCH', -23.445)
                _yaw = _f('CARLA_CAM_YAW', 179.536)
                _roll = _f('CARLA_CAM_ROLL', 0.0)
                transform = carla.Transform(
                    carla.Location(x=_x, y=_y, z=_z),
                    carla.Rotation(pitch=_pitch, yaw=_yaw, roll=_roll),
                )
                mode = f'roadside({_x:.1f},{_y:.1f},{_z:.1f} pitch={_pitch:.1f} yaw={_yaw:.1f})'
                # ★2026-11-07 由 WorkBuddy 新增：记录路侧机位几何，
                # 供 project_world_to_pixel() 用（找「画面里的停止线」）。
                self._camera_geom = {
                    'x': _x, 'y': _y, 'z': _z,
                    'pitch': _pitch, 'yaw': _yaw, 'roll': _roll,
                    'width': int(width), 'height': int(height), 'fov': float(fov),
                }

            # 重复调用时先销毁旧相机，避免同一个源堆多个 sensor
            if self._camera is not None:
                try:
                    self._camera.stop()
                    self._camera.destroy()
                except Exception:  # noqa: BLE001
                    pass
                try:
                    self._spawned_actors.remove(self._camera)
                except ValueError:
                    pass
                self._camera = None

            self._camera = self._world.spawn_actor(cam_bp, transform, attach_to=parent)
            self._camera.listen(self._on_camera_image)
            self._spawned_actors.append(self._camera)
            logger.info('[CarlaSource] 摄像头已挂载 %dx%d fov=%d 机位=%s',
                        width, height, fov, mode)
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
        # 违规车控制线程要先停，否则它会继续 apply_control 到已销毁的 actor
        try:
            self._violator_stop_event.set()
            if self._violator_thread is not None and self._violator_thread.is_alive():
                self._violator_thread.join(timeout=2.0)
        except Exception:  # noqa: BLE001
            pass
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
        self._camera_geom = None
        self._controlled_approach = None
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

    # ------------------------------------------------------------------ #
    # ★闯红灯（2026-11-07 由 WorkBuddy 重做）
    #
    # 旧实现的问题（任务单已实测确认）：
    #   只做 set_autopilot(False) + throttle=1.0，而车的朝向由**随机 spawn point**
    #   的 yaw 决定 —— 不一定朝着红灯，所以实测判出的是 running_yellow / speeding，
    #   从来没有 red_light。
    #
    # 新实现（全部基于实测事实，不做假设）：
    #   ① 按**停止线的地理坐标**找受控灯（CARLA 重启后灯的 Actor ID 会变，
    #      绝不能硬编码 ID）；停止线在画面中的像素位置由 project_world_to_pixel()
    #      算出 —— 这保证「这条停止线确实在本机位画面里」。
    #   ② 生成点取**该车道上游**（waypoint.previous()），且要求它同样落在画面内：
    #      违规车从出现到越线全程都在镜头里，才能被跟踪到足够多的帧
    #      （行为引擎要求 history >= 5 个采样点）。
    #   ③ 目标灯**逐 tick set_state(Red)**（CARLA 的 set_red_time() 等在本机无效）。
    #   ④ 纯追踪（pure pursuit）沿车道驾驶，越过停止线后自动刹停。
    # ------------------------------------------------------------------ #
    def find_red_light_approach(self, prefer_lower_half: bool = True):
        """按**本机位画面**挑选可拍到的受控红灯进口，并同时找出**对向进口**。

        ★2026-11-07 由 WorkBuddy 新增「对向进口」的原因（实测误报）：
          画面里同时有 8~15 盏灯。若把**一个**进口的灯态当作全场灯态，
          对向车流（自己的进口是绿灯、合法通过）会被判成闯红灯 ——
          实测数据库里出现了 4 条这种假阳性（轨迹首点 y≈160 = 对向停止线）。
          因此这里把画面内的进口按「车流方向」分成两类：
            away  —— 车流**远离**相机（受控进口，停止线在画面下半部）
            toward —— 车流**靠近**相机（对向进口，灯态必须另算）
          判定方法：车道行驶方向与相机前向的夹角点积（>0.3 远离 / <-0.3 靠近）。

        Returns:
            dict | None，含受控进口 light/waypoint/停止线像素/上游生成点，
            以及 'opposite'（对向进口）。
        """
        cam = getattr(self, '_camera_geom', None)
        if not cam or self._world is None:
            logger.warning('[CarlaSource] 未挂载路侧相机，无法确定受控红灯进口')
            return None
        w = int(cam['width'])
        h = int(cam['height'])
        # 相机水平前向（忽略俯仰）
        pitch = math.radians(float(cam.get('pitch', 0.0)))
        yaw = math.radians(float(cam.get('yaw', 0.0)))
        cam_fwd = (math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw))
        best_away = None
        best_toward = None
        try:
            tls = list(self._world.get_actors().filter('traffic.traffic_light*'))
        except Exception as exc:  # noqa: BLE001
            logger.error('[CarlaSource] 读取红绿灯列表失败: %s', exc)
            return None

        for tl in tls:
            try:
                stop_wps = list(tl.get_stop_waypoints())
            except Exception:  # noqa: BLE001
                continue
            for wp in stop_wps:
                sp = wp.transform.location
                px = project_world_to_pixel((sp.x, sp.y, sp.z + 0.05), cam)
                if px is None:
                    continue
                u, v, depth = px
                if not (-0.5 * w <= u <= 1.5 * w):
                    continue
                if not (0 <= v <= h):
                    continue      # 停止线纵向必须落在画面内
                # 车道行驶方向 vs 相机前向
                lane_yaw = math.radians(float(wp.transform.rotation.yaw))
                dot = (math.cos(lane_yaw) * cam_fwd[0] + math.sin(lane_yaw) * cam_fwd[1])
                if dot > 0.3:
                    motion = 'away'
                elif dot < -0.3:
                    motion = 'toward'
                else:
                    continue      # 与视线近乎垂直（横向路口），不参与
                # 上游可见点（越远越好：给跟踪器留够帧数）
                spawn_candidates = []
                for dist in (16.0, 14.0, 12.0, 10.0, 8.0, 6.0, 5.0, 4.0, 3.0, 2.0):
                    try:
                        prevs = wp.previous(dist)
                    except Exception:  # noqa: BLE001
                        prevs = None
                    if not prevs:
                        continue
                    q = prevs[0]
                    qloc = q.transform.location
                    qpx = project_world_to_pixel((qloc.x, qloc.y, qloc.z + 0.05), cam)
                    if qpx and -0.2 * w <= qpx[0] <= 1.2 * w and 0 <= qpx[1] <= h:
                        spawn_candidates.append((dist, q))
                if not spawn_candidates:
                    continue
                # 取**最远**的可见上游点（留出最长跑道），但保留全部候选：
                # 生成点可能被别的车占住（实测），spawn 时要能逐个回退。
                spawn_dist, spawn_wp = spawn_candidates[0]
                lower = 1 if (prefer_lower_half and v >= h * 0.5) else 0
                # 排序：① 停止线在画面下半部分优先 ② 上游可见距离越长越好
                #       ③ 停止线越靠近画面中线越好（车辆不会被画面边缘切掉）
                score = (lower, spawn_dist, -abs(u - w / 2.0))
                cand = {
                    'light': tl,
                    'light_id': int(tl.id),
                    'waypoint': wp,
                    'motion': motion,
                    'stop_point': (sp.x, sp.y, sp.z),
                    'stop_pixel': (round(u, 1), round(v, 1)),
                    'stop_depth_m': round(depth, 2),
                    'spawn_wp': spawn_wp,
                    'spawn_dist_m': spawn_dist,
                    'spawn_candidates': spawn_candidates,
                    'lane': (wp.road_id, wp.lane_id),
                    'score': score,
                }
                if motion == 'away':
                    if best_away is None or score > best_away['score']:
                        best_away = cand
                else:
                    if best_toward is None or score > best_toward['score']:
                        best_toward = cand

        best = best_away or best_toward
        if best is None:
            logger.warning('[CarlaSource] 本机位画面内找不到「停止线可见且上游可见」的受控红灯进口')
            return None
        best['opposite'] = best_toward if best_toward is not best else None
        logger.info(
            '[CarlaSource] 选定受控红灯进口: motion=%s light_id=%d lane=%s 停止线=%s '
            '像素=%s 距相机 %.1fm 上游可见 %.1fm；对向进口 light_id=%s',
            best['motion'], best['light_id'], best['lane'],
            tuple(round(v, 2) for v in best['stop_point']), best['stop_pixel'],
            best['stop_depth_m'], best['spawn_dist_m'],
            (best['opposite']['light_id'] if best.get('opposite') else None))
        return best

    def _light_state_str(self, tl: Any) -> str:
        try:
            state_map = {
                carla.TrafficLightState.Red: 'red',
                carla.TrafficLightState.Yellow: 'yellow',
                carla.TrafficLightState.Green: 'green',
                carla.TrafficLightState.Off: 'off',
            }
            return state_map.get(tl.state, 'unknown')
        except Exception:  # noqa: BLE001
            return 'unknown'

    def get_controlled_light_state(self) -> str:
        """受控方向的信号灯**权威灯态**（直接读 CARLA 仿真真值）。

        为什么需要它：画面里同时有 8~15 盏灯，图像判色无法可靠区分
        「哪一盏是本车道的」。旧逻辑取「画面里任意一盏灯的最高优先级」
        （红>绿>黄），横向车道的红灯会被当成本方向的 —— 实测每循环误报 5~7 次。
        CARLA 仿真端**知道**每盏灯的真实状态，因此 CARLA 源下用它作为场景灯态：
        既准确，又不依赖图像判色是否命中。

        返回 '' 表示尚未确定受控进口（调用方应回退到图像判色路径）。
        """
        approach = self.get_controlled_approach()
        if not approach:
            return ''
        tl = approach.get('light')
        if tl is None:
            return ''
        return self._light_state_str(tl)

    def get_controlled_light_states(self) -> Dict[str, str]:
        """按**车流方向**给出画面内各进口的权威灯态。

        Returns:
            {'away': 'red', 'toward': 'green'} —— 键缺失表示该方向没有可见进口。
        """
        out: Dict[str, str] = {}
        approach = self.get_controlled_approach()
        if not approach:
            return out
        try:
            motion = approach.get('motion') or 'away'
            tl = approach.get('light')
            if tl is not None:
                out[motion] = self._light_state_str(tl)
            opp = approach.get('opposite')
            if opp is not None and opp.get('light') is not None:
                out['toward' if motion != 'toward' else 'away'] = \
                    self._light_state_str(opp['light'])
        except Exception as exc:  # noqa: BLE001
            logger.debug('[CarlaSource] 读取对向进口灯态失败: %s', exc)
        return out

    def get_controlled_approach(self) -> Optional[Dict[str, Any]]:
        """受控进口（带缓存，避免每帧重算投影）。"""
        if getattr(self, '_controlled_approach', None) is not None:
            return self._controlled_approach
        self._controlled_approach = self.find_red_light_approach()
        return self._controlled_approach

    def get_violator_state(self) -> Dict[str, Any]:
        """违规车会话的可观测状态（供 /carla/actors 与报告取证）。"""
        with self._violator_lock:
            return dict(self._violator_session)

    def _violator_control_loop(self) -> None:
        """违规车控制线程（2026-11-07 新增）。

        每 50ms 做两件事：
          1. 把目标红绿灯逐 tick 置为红（CARLA 的 set_red_time() 等在本机无效，
             必须每 tick set_state()）
          2. 纯追踪驾驶：沿车道下游路点走，越过停止线后刹停
        """
        target_speed = float(self._violator_session.get('target_speed_mps') or 1.2)
        crossed_at = None
        start_ts = time.time()
        while not self._violator_stop_event.is_set():
            try:
                actor = self._violator_actor
                if actor is None:
                    break
                # ① 强制目标灯为红
                light_id = self._violator_light_id
                if light_id is not None:
                    try:
                        # ⚠ world.get_actor(id) 对已销毁 actor 仍返回 stale 代理，
                        #   所以用 get_actors().find(id) 判存活。
                        tl = self._world.get_actors().find(light_id)
                        if tl is not None:
                            tl.set_state(carla.TrafficLightState.Red)
                    except Exception:  # noqa: BLE001
                        pass

                # ② 驾驶
                tf = actor.get_transform()
                loc = tf.location
                vel = actor.get_velocity()
                speed = math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)

                # 纯追踪：取前方第一个距离 > lookahead 的路点
                lookahead = max(3.0, speed * 1.2)
                target = None
                for p in self._violator_path:
                    d = math.hypot(p.x - loc.x, p.y - loc.y)
                    if d > lookahead:
                        target = p
                        break
                if target is None and self._violator_path:
                    target = self._violator_path[-1]

                steer = 0.0
                if target is not None:
                    dx = target.x - loc.x
                    dy = target.y - loc.y
                    yaw = math.radians(tf.rotation.yaw)
                    ang = math.atan2(dy, dx) - yaw
                    while ang > math.pi:
                        ang -= 2 * math.pi
                    while ang < -math.pi:
                        ang += 2 * math.pi
                    steer = max(-0.8, min(0.8, ang * 1.4))

                # 越线检测：两个判据同时满足才算「压过停止线」
                #   ① 世界坐标：沿车头方向越过停止线（signed < 0）
                #   ② 像素：车的地面点投影**越过画出来的白色停止线**
                #      （实测 CARLA 的 stop waypoint 投影在 y≈433，而画面里
                #        那条白线在 y≈380，相差 53px≈1.9m —— 规则要判的是
                #        「压过白线」，所以用像素判据把关）
                stop_pt = self._violator_stop_point
                signed = None
                if stop_pt is not None:
                    sx, sy = stop_pt[0], stop_pt[1]
                    dx = sx - loc.x
                    dy = sy - loc.y
                    yaw = math.radians(tf.rotation.yaw)
                    # 沿车头方向的分量（>0 表示还在停止线之前）
                    signed = dx * math.cos(yaw) + dy * math.sin(yaw)

                px_v = None
                cam = getattr(self, '_camera_geom', None)
                if cam is not None:
                    _p = project_world_to_pixel((loc.x, loc.y, loc.z), cam)
                    if _p is not None:
                        px_v = _p[1]
                self._violator_session['pixel_v'] = round(px_v, 1) if px_v is not None else None

                crossed_world = signed is not None and signed < -1.0
                crossed_pixel = (px_v is not None and
                                 px_v <= float(self._violator_stop_pixel_v))
                if crossed_at is None and crossed_world and crossed_pixel:
                    crossed_at = time.time()
                    logger.info('[CarlaSource] 违规车已压过停止线 id=%s 耗时 %.1fs '
                                '(signed=%.2fm, 像素 y=%.0f <= 阈值 %.0f)',
                                getattr(actor, 'id', '?'), crossed_at - start_ts,
                                signed or 0.0, px_v or -1, self._violator_stop_pixel_v)

                if crossed_at is not None:
                    # 越线后刹停（留 1.5m 余量，方便证据帧里看到它已经过线）
                    control = carla.VehicleControl(throttle=0.0, steer=0.0, brake=1.0)
                else:
                    throttle = max(0.0, min(0.55, (target_speed - speed) * 0.45))
                    brake = 0.0
                    if speed > target_speed * 1.6:
                        brake = 0.4
                        throttle = 0.0
                    control = carla.VehicleControl(throttle=throttle, steer=steer, brake=brake)
                actor.apply_control(control)

                with self._violator_lock:
                    self._violator_session.update({
                        'speed_mps': round(speed, 2),
                        'location': (round(loc.x, 2), round(loc.y, 2)),
                        'signed_dist_to_stop_m': round(signed, 2) if signed is not None else None,
                        'crossed': crossed_at is not None,
                        'elapsed_s': round(time.time() - start_ts, 2),
                    })
                    self._violator_session.setdefault('samples', []).append(
                        (round(time.time() - start_ts, 2), round(loc.x, 2), round(loc.y, 2),
                         round(speed, 2)))
                    if len(self._violator_session['samples']) > 600:
                        del self._violator_session['samples'][:-600]

                # 越线后再跑 8 秒：让检测器有多帧证据（灯仍保持红色）
                if crossed_at is not None and (time.time() - crossed_at) > 8.0:
                    break
                if (time.time() - start_ts) > 45.0:
                    break
                time.sleep(0.05)
            except Exception as exc:  # noqa: BLE001
                logger.warning('[CarlaSource] 违规车控制线程异常: %s', exc)
                time.sleep(0.2)
        try:
            if self._violator_actor is not None:
                self._violator_actor.apply_control(
                    carla.VehicleControl(throttle=0.0, steer=0.0, brake=1.0))
        except Exception:  # noqa: BLE001
            pass
        with self._violator_lock:
            self._violator_session['active'] = False
            self._violator_session['finished_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        logger.info('[CarlaSource] 违规车控制线程结束（灯态恢复自动）')

    def spawn_red_light_violator(self, target_speed_mps: float = 1.2) -> Optional[int]:
        """生成一辆**真闯红灯**的车辆：驶向受控红灯的真实停止线并冲过它。

        返回 vehicle actor id，失败返回 None。

        2026-11-07 重做（WorkBuddy）。旧实现见方法上方注释：随机 spawn point +
        油门直行，车不一定朝红灯，实测从来判不出 red_light。
        """
        if not self._ensure_connected():
            return None
        try:
            approach = self.get_controlled_approach()
            if not approach:
                return None

            blueprint_lib = self._world.get_blueprint_library()
            vehicle_bps = blueprint_lib.filter('vehicle.*')
            if not vehicle_bps:
                logger.error('[CarlaSource] 无 vehicle 蓝图')
                return None

            bp = None
            for name in ('vehicle.tesla.model3', 'vehicle.audi.a2',
                         'vehicle.nissan.patrol', 'vehicle.ford.mustang'):
                try:
                    bp = blueprint_lib.find(name)
                    break
                except Exception:  # noqa: BLE001
                    continue
            if bp is None:
                import random
                bp = random.choice(vehicle_bps)
            if bp.has_attribute('role_name'):
                bp.set_attribute('role_name', 'violator')
            if bp.has_attribute('color'):
                try:
                    bp.set_attribute('color', '255,0,0')
                except Exception:  # noqa: BLE001
                    pass

            # ★逐个候选上游点尝试生成。
            #   实测教训（2026-11-07）：① 最远的候选点常被别的车占住；
            #   ② 更隐蔽的是**路面高度** —— Town10HD_Opt 车道 waypoint 的 z=0.000，
            #      而 try_spawn_actor 在 z 恰好等于路面高度时**静默返回 None**
            #      （z=0.0 -> None；z=0.3 -> 成功 id=69/70/71，实测三处皆同）。
            #      所以这里对每个候选点再按 +0.3/+0.6/+0.9 递增高度重试。
            actor = None
            used_loc = None
            used_yaw = 0.0
            ground_ok = None
            tried = 0
            for _dist, cand_wp in (approach.get('spawn_candidates') or
                                   [(approach['spawn_dist_m'], approach['spawn_wp'])]):
                cloc = cand_wp.transform.location
                cyaw = float(cand_wp.transform.rotation.yaw)
                for z_off in (0.3, 0.6, 0.9):
                    ctransform = carla.Transform(
                        carla.Location(x=cloc.x, y=cloc.y, z=cloc.z + z_off),
                        carla.Rotation(yaw=cyaw))
                    tried += 1
                    actor = self._world.try_spawn_actor(bp, ctransform)
                    if actor is not None:
                        used_loc = cloc
                        used_yaw = cyaw
                        break
                if actor is not None:
                    break
            if actor is None:
                logger.error('[CarlaSource] 违规车 spawn 失败：%d 次尝试（%d 个候选点 x 3 个高度）全失败',
                             tried, len(approach.get('spawn_candidates') or []))
                return None
            loc = used_loc
            yaw = used_yaw

            # 生成点是否真的在可行驶路面上（ground_projection 返回 LabelledPoint，
            # 不是 Location，必须用 getattr(x, 'location', x) 取坐标）
            try:
                gp = self._world.ground_projection(
                    carla.Location(x=loc.x, y=loc.y, z=loc.z + 1.0), 3.0)
                if gp is not None:
                    g = getattr(gp, 'location', gp)
                    ground_ok = (round(g.x, 2), round(g.y, 2), round(g.z, 2))
            except Exception:  # noqa: BLE001
                ground_ok = None

            actor.set_autopilot(False)
            self._vehicles.append(actor)
            self._spawned_actors.append(actor)

            # 下游路点（纯追踪用）
            path = []
            wp = approach['waypoint']
            for dist in (4.0, 8.0, 12.0, 16.0):
                try:
                    nxt = wp.next(dist)
                    if nxt:
                        path.append(nxt[0].transform.location)
                except Exception:  # noqa: BLE001
                    continue
            if not path:
                # 退化：沿停止线方向直行
                sp = approach['stop_point']
                yaw_rad = math.radians(yaw)
                path = [carla.Location(x=sp[0] + math.cos(yaw_rad) * d,
                                       y=sp[1] + math.sin(yaw_rad) * d, z=sp[2])
                        for d in (4.0, 8.0, 12.0)]

            with self._violator_lock:
                self._violator_actor = actor
                self._violator_light_id = approach['light_id']
                self._violator_path = path
                self._violator_stop_point = approach['stop_point']
                # 压线阈值：CARLA stop waypoint 的投影 y 减去「waypoint 到画出来的
                # 白线」的像素差（实测 53px）。默认 60px，可由环境变量覆盖。
                try:
                    _off = float(os.environ.get('CARLA_VIOLATOR_STOP_OFFSET_PX', '60'))
                except Exception:
                    _off = 60.0
                self._violator_stop_pixel_v = float(approach['stop_pixel'][1]) - _off
                self._violator_session = {
                    'active': True,
                    'actor_id': int(actor.id),
                    'light_id': approach['light_id'],
                    'lane': approach['lane'],
                    'stop_point_world': tuple(round(v, 2) for v in approach['stop_point']),
                    'stop_line_pixel': approach['stop_pixel'],
                    'stop_pixel_threshold_v': round(self._violator_stop_pixel_v, 1),
                    'stop_depth_m': approach['stop_depth_m'],
                    'spawn_point_world': (round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)),
                    'spawn_pixel': None,
                    'spawn_yaw_deg': round(yaw, 2),
                    'spawn_ground_projection': ground_ok,
                    'target_speed_mps': target_speed_mps,
                    'started_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'samples': [],
                }
                spawn_px = project_world_to_pixel((loc.x, loc.y, loc.z + 0.05),
                                                  self._camera_geom) if self._camera_geom else None
                if spawn_px:
                    self._violator_session['spawn_pixel'] = (round(spawn_px[0], 1),
                                                             round(spawn_px[1], 1))

            # 启动控制线程
            self._violator_stop_event.clear()
            self._violator_thread = threading.Thread(
                target=self._violator_control_loop, daemon=True, name='carla-violator')
            self._violator_thread.start()

            logger.info(
                '[CarlaSource] 闯红灯车辆已生成 id=%d：目标灯 id=%d（lane=%s），'
                '停止线像素=%s，生成点=%s 像素=%s',
                actor.id, approach['light_id'], approach['lane'],
                approach['stop_pixel'], self._violator_session['spawn_point_world'],
                self._violator_session['spawn_pixel'])
            return int(actor.id)
        except Exception as exc:  # noqa: BLE001
            logger.error('[CarlaSource] spawn_red_light_violator 失败: %s', exc)
            return None

    # 上下文管理协议，便于 with 使用
    def __enter__(self) -> 'CarlaSource':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()
