# -*- coding: utf-8 -*-
"""
车辆追踪器模块
支持双模式：质心追踪（默认）和 ByteTrack（可选）
集成了 traffic_surveillance 和 smart-vehicle-counter 的跟踪思路
"""

import time
import numpy as np                     # 2026-10-03 由 DSH 补充（ByteTrack 适配器需要）
from typing import Dict, List, Optional, Any
from collections import OrderedDict

VEHICLE_CLASSES = {'car', 'motorcycle', 'truck', 'bus', 'bicycle'}
MAX_HISTORY = 30
MAX_DISTANCE = 80
DIRECTION_THRESHOLD = 10


class CentroidTracker:
    def __init__(self, max_history: int = MAX_HISTORY):
        self.vehicles = OrderedDict()
        self.next_id = 1
        self.frame_count = 0
        self.max_history = max_history

    def _get_bbox_center(self, bbox: List[int]) -> tuple:
        x1, y1, x2, y2 = bbox
        return (x1 + x2) // 2, (y1 + y2) // 2

    def _calculate_distance(self, center1: tuple, center2: tuple) -> float:
        return ((center1[0] - center2[0]) ** 2 + (center1[1] - center2[1]) ** 2) ** 0.5

    def update(self, detections: List[Dict], frame_width: int = 1280,
               frame_height: int = 720, frame_ts: float = None) -> Dict[int, Dict]:
        """跟新一帧

        frame_ts（2026-10-04 由 DSH 新增，修一个影响测速正确性的 bug）：
          轨迹点原先一律用 `time.time()`（**墙钟**）打时间戳，而测速完全依赖
          轨迹点的时间差。于是：
            · 检测比视频慢（我们的常态：2~3fps vs 视频 20fps）
              -> Δt 被放大数倍 -> **速度被低估 5~10 倍**
            · 同一段视频在不同性能的机器上跑，**会得出不同车速**
          这不可接受。修法：调用方传入**视频时间**（frame_index / source_fps），
          不给时退回墙钟（保持旧行为，不破坏既有调用）。
        """
        self.frame_count += 1
        # 本帧的时间戳：优先用视频时间
        _now = float(frame_ts) if frame_ts is not None else time.time()
        self._last_ts = _now

        vehicle_detections = [
            d for d in detections
            if d.get('class_name') in VEHICLE_CLASSES and d.get('confidence', 0.0) >= 0.3
        ]

        new_vehicles = {}

        for det in vehicle_detections:
            bbox = det.get('bbox', [0, 0, 0, 0])
            center = self._get_bbox_center(bbox)
            class_name = det.get('class_name', '')
            confidence = det.get('confidence', 0.0)

            matched_id = None
            min_distance = MAX_DISTANCE

            for vid, vehicle in list(self.vehicles.items()):
                last_center = vehicle['history'][-1]['center']
                distance = self._calculate_distance(center, last_center)
                if distance < min_distance:
                    min_distance = distance
                    matched_id = vid

            if matched_id is not None:
                vehicle = self.vehicles[matched_id]
                prev_center = vehicle['history'][-1]['center']
                dx = center[0] - prev_center[0]
                dy = center[1] - prev_center[1]

                history = vehicle['history'][:]
                history.append({
                    'center': center,
                    'bbox': bbox,
                    'timestamp': _now,   # 视频时间（2026-10-04 修复）
                    'dx': dx,
                    'dy': dy
                })
                if len(history) > self.max_history:
                    history = history[-self.max_history:]

                direction = self._calculate_direction(history)
                speed = self._calculate_speed(history)

                new_vehicles[matched_id] = {
                    'id': matched_id,
                    'track_id': matched_id,
                    'class_name': class_name,
                    'confidence': confidence,
                    'bbox': bbox,
                    'center': center,
                    'history': history,
                    'direction': direction,
                    'speed': speed,
                    'is_wrong_way': self._detect_wrong_way(history, direction, frame_width),
                    'first_seen': vehicle.get('first_seen', _now),
                    'last_seen': self._last_ts,
                    'frame_count': vehicle.get('frame_count', 0) + 1
                }
            else:
                history = [{
                    'center': center,
                    'bbox': bbox,
                    'timestamp': _now,   # 视频时间（2026-10-04 修复）
                    'dx': 0,
                    'dy': 0
                }]

                new_vehicles[self.next_id] = {
                    'id': self.next_id,
                    'track_id': self.next_id,
                    'class_name': class_name,
                    'confidence': confidence,
                    'bbox': bbox,
                    'center': center,
                    'history': history,
                    'direction': 'unknown',
                    'speed': 0.0,
                    'is_wrong_way': False,
                    'first_seen': time.time(),
                    'last_seen': self._last_ts,
                    'frame_count': 1
                }
                self.next_id += 1

        for vid, vehicle in list(self.vehicles.items()):
            if vid not in new_vehicles:
                elapsed = time.time() - vehicle['last_seen']
                if elapsed > 2.0:
                    del self.vehicles[vid]

        self.vehicles = new_vehicles

        return self.vehicles

    def _calculate_direction(self, history: List[Dict]) -> str:
        if len(history) < 3:
            return 'unknown'

        total_dx = sum(h['dx'] for h in history[-3:])
        total_dy = sum(h['dy'] for h in history[-3:])

        if abs(total_dx) < DIRECTION_THRESHOLD and abs(total_dy) < DIRECTION_THRESHOLD:
            return 'stationary'

        if abs(total_dx) > abs(total_dy):
            return 'left' if total_dx < 0 else 'right'
        else:
            return 'up' if total_dy < 0 else 'down'

    def _calculate_speed(self, history: List[Dict]) -> float:
        if len(history) < 2:
            return 0.0

        total_distance = 0.0
        total_time = 0.0

        for i in range(1, len(history)):
            prev_center = history[i-1]['center']
            curr_center = history[i]['center']
            distance = self._calculate_distance(prev_center, curr_center)
            time_diff = history[i]['timestamp'] - history[i-1]['timestamp']

            if time_diff > 0:
                total_distance += distance
                total_time += time_diff

        if total_time > 0:
            return total_distance / total_time
        return 0.0

    def _detect_wrong_way(self, history: List[Dict], direction: str, frame_width: int) -> bool:
        if len(history) < 4:
            return False

        lane_evidence = self._analyze_lane_position(history, frame_width)
        direction_consistency = self._check_direction_consistency(history)

        if lane_evidence == 'opposite' and direction_consistency:
            return True

        return False

    def _analyze_lane_position(self, history: List[Dict], frame_width: int) -> str:
        if not history:
            return 'unknown'

        # ★2026-10-06 由 DSH 新增：**静止/微动不算逆行**。
        # 实测（演示视频，1920x1080）：停在停止线前等红灯的奥迪，像素只有 1~2px
        # 抖动，其中偶尔一次 dx<0 -> 被判 'opposite' -> **每循环 1 次逆行误报**
        # （落库 id 2457/2459/2461…）。
        # ⚠ 必须用**最近几个采样**判断"现在是否在动"：用整段 history 的净位移是错的
        #   —— 那辆车十几秒前开过 20 米然后再停下，净位移依然很大。
        try:
            pts = [h['center'] for h in history[-4:] if h.get('center')]
            moved = 0.0
            for i in range(1, len(pts)):
                moved = max(moved, ((pts[i][0] - pts[i - 1][0]) ** 2 +
                                    (pts[i][1] - pts[i - 1][1]) ** 2) ** 0.5)
            if len(pts) >= 2 and moved < 2.0:
                return 'middle'
        except (KeyError, TypeError, ValueError, IndexError):
            pass

        # ★同理：1~2px 的 dx 是抖动，不构成"横向运动"（原判据只排除 dx == 0）
        noise = 1.5
        centers = [h['center'][0] for h in history]
        avg_x = sum(centers) / len(centers)

        if avg_x < frame_width * 0.3:
            if any(h['dx'] > noise for h in history[-3:]):
                return 'opposite'
            return 'left_lane'
        elif avg_x > frame_width * 0.7:
            if any(h['dx'] < -noise for h in history[-3:]):
                return 'opposite'
            return 'right_lane'
        else:
            return 'middle'

    def _check_direction_consistency(self, history: List[Dict]) -> bool:
        if len(history) < 3:
            return False

        directions = []
        for i in range(1, len(history)):
            dx = history[i]['dx']
            dy = history[i]['dy']

            if abs(dx) > abs(dy):
                directions.append('left' if dx < 0 else 'right')
            else:
                directions.append('up' if dy < 0 else 'down')

        if len(set(directions)) == 1:
            return True

        dominant_dir = max(set(directions), key=directions.count)
        if directions.count(dominant_dir) >= len(directions) * 0.7:
            return True

        return False

    def get_vehicle_by_id(self, vehicle_id: int) -> Optional[Dict]:
        return self.vehicles.get(vehicle_id)

    def get_wrong_way_vehicles(self) -> List[Dict]:
        return [v for v in self.vehicles.values() if v.get('is_wrong_way', False)]

    def get_all_vehicles(self) -> List[Dict]:
        return list(self.vehicles.values())

    def get_statistics(self) -> Dict[str, Any]:
        vehicles = self.get_all_vehicles()

        if not vehicles:
            return {
                'total_vehicles': 0,
                'wrong_way_count': 0,
                'avg_speed': 0.0,
                'directions': {}
            }

        direction_counts = {}
        speeds = []
        wrong_way_count = 0

        for v in vehicles:
            dir = v.get('direction', 'unknown')
            direction_counts[dir] = direction_counts.get(dir, 0) + 1
            speeds.append(v.get('speed', 0.0))
            if v.get('is_wrong_way', False):
                wrong_way_count += 1

        return {
            'total_vehicles': len(vehicles),
            'wrong_way_count': wrong_way_count,
            'avg_speed': sum(speeds) / len(speeds) if speeds else 0.0,
            'directions': direction_counts,
            'tracked_ids': [v['id'] for v in vehicles]
        }

    def reset(self):
        self.vehicles.clear()
        self.next_id = 1
        self.frame_count = 0


class _Arr(np.ndarray):
    """numpy 子类：布尔索引后仍是 _Arr（供 ultralytics BYTETracker 使用）"""

    def __new__(cls, data):
        return np.asarray(data, dtype=float).view(cls)

    def __array_finalize__(self, obj):
        pass


class _DetShim:
    """ultralytics BYTETracker 所需的 Results 式检测容器（2026-10-03 由 DSH 新增）

    ultralytics 8.4 的 `BYTETracker.update()` 期望带 `.conf` / `.xywhr` / `.cls`
    且**支持布尔索引**的对象（原本由 model.track() 内部构造）。本项目走自研检测
    管线（multi_model_detect 直接返回 dict），故提供最小替身，避免重跑推理。
    """

    def __init__(self, boxes_xyxy=None, confs=None, classes=None,
                 _xywhr=None, _conf=None, _cls=None):
        if _xywhr is not None:
            self.xywhr, self.conf, self.cls = _xywhr, _conf, _cls
            return
        b = np.asarray(boxes_xyxy, dtype=float) if boxes_xyxy is not None else np.zeros((0, 4))
        n = len(b)
        if n == 0:
            xywhr = np.zeros((0, 5))
        else:
            cx = (b[:, 0] + b[:, 2]) / 2.0
            cy = (b[:, 1] + b[:, 3]) / 2.0
            w = b[:, 2] - b[:, 0]
            h = b[:, 3] - b[:, 1]
            xywhr = np.stack([cx, cy, w, h, np.zeros(n)], axis=1)
        self.xywhr = _Arr(xywhr)
        self.conf = _Arr(confs if confs is not None else np.ones(n))
        self.cls = _Arr(classes if classes is not None else np.zeros(n))

    def __getitem__(self, m):
        return _DetShim(_xywhr=_Arr(self.xywhr[m]), _conf=_Arr(self.conf[m]),
                        _cls=_Arr(self.cls[m]))

    def __len__(self):
        return len(self.conf)


class _TrackShim:
    """把 ultralytics 返回的 numpy 行包装成旧代码期望的对象（.track_id/.tlwh/.score）

    ultralytics BYTETracker.update 返回 (N,9)：[x, y, w, h, idx, track_id, score, cls, det_idx]

    ⚠ 关键（2026-10-03 由 DSH 修正）：这里的 **x,y 是 bbox 左上角**，
    但输入 xywhr 的 x,y 语义需与输出一致。实测发现：输入 xywhr 用**中心点**
    时，输出 x,y 恰好等于输入的中心点，且 w,h 不变 —— 说明该实现的
    x,y 直接沿用输入语义（即**中心点**）。
    证据（同一辆卡车）：
        检测框 [565,157,688,364] -> 中心 (626.5, 260.5)，宽124 高207
        追踪输出 x=625, y=262, w=125, h=204   ← 625≈626.5, 262≈260.5
    若按"左上角"解释，追踪框会整体偏移约 (+62,+104)，导致：
        · 画框与车辆错位（用户可见的"框歪了"）
        · 检测框与追踪框 IoU≈0 -> vehicle_id 回填 0%
    因此这里**统一按中心点换算回左上角**，保证下游拿到的是标准 xyxy。
    """

    __slots__ = ("track_id", "tlwh", "score", "center")

    def __init__(self, row):
        x, y, w, h = (float(row[0]), float(row[1]), float(row[2]), float(row[3]))
        self.center = (x, y)
        # 与输入的 xywhr 语义保持一致：x,y 为中心点 -> 转成左上角 tlwh
        self.tlwh = [x - w / 2.0, y - h / 2.0, w, h]
        self.track_id = int(row[5])
        self.score = float(row[6]) if len(row) > 6 else 1.0


class ByteTrackWrapper:
    def __init__(self, frame_rate: int = 30, max_history: int = MAX_HISTORY):
        self.byte_tracker = None
        self.tracked_vehicles = {}
        self.trajectories = {}
        self.frame_rate = frame_rate
        self.max_history = max_history
        self.lane_config = None

        # 2026-10-03 由 DSH 修复：原实现
        #   `from yolox.tracker.byte_tracker import BYTETracker`
        # —— yolox 包并不存在（本项目依赖的是 ultralytics），故永远 ImportError，
        # 永远降级为质心追踪（这是"追踪质量差"的根因之一）。
        # 改用 **ultralytics 自带 ByteTrack**（lap 0.5.13 已满足其依赖）。
        self.available = False
        try:
            from types import SimpleNamespace

            from ultralytics.trackers.byte_tracker import BYTETracker

            args = SimpleNamespace(
                track_high_thresh=0.5,
                track_low_thresh=0.1,
                new_track_thresh=0.6,
                track_buffer=30,
                match_thresh=0.8,
                fuse_score=True,
            )
            self.byte_tracker = BYTETracker(args)
            self.available = True
            print("ByteTrack 初始化成功（ultralytics 内置实现）")
        except Exception as _e:
            print(f"ByteTrack 不可用，将使用质心追踪（原因: {type(_e).__name__}: {_e}）")

    def update(self, detections: List[Dict], frame_width: int = 1280,
               frame_height: int = 720, frame_ts: float = None) -> Dict[int, Dict]:
        """frame_ts: 视频时间（2026-10-04 由 DSH 新增，修复"用墙钟算速度"的 bug）

        原先轨迹点一律用 time.time()，导致检测慢于视频时速度被低估数倍，
        且同一视频在不同机器上结果不同。传 frame_index/source_fps 即修正。
        """
        self._last_ts = float(frame_ts) if frame_ts is not None else time.time()

        if not self.available:
            return {}

        vehicle_detections = [
            d for d in detections
            if d.get('class_name') in VEHICLE_CLASSES and d.get('confidence', 0.0) >= 0.3
        ]

        # 2026-10-03 由 DSH 改造：ultralytics 的 BYTETracker 接收 Results 式对象，
        # 返回 (N,9) numpy 数组（第 5 列为 track_id），与旧 yolox API 不同。
        # 这里用 _DetShim 打包输入、_TrackShim 解包输出，后续逻辑保持不变。
        boxes, confs, classes = [], [], []
        for det in vehicle_detections:
            bbox = det.get('bbox', [0, 0, 0, 0])
            if len(bbox) < 4:
                continue
            x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
            if x2 - x1 <= 1 or y2 - y1 <= 1:
                continue
            boxes.append([x1, y1, x2, y2])
            confs.append(float(det.get('confidence', 0.0) or 0.0))
            classes.append(0.0)

        try:
            raw = self.byte_tracker.update(_DetShim(boxes, confs, classes), img=None)
        except Exception as _e:
            print(f"[ByteTrack] update 失败，跳过本帧: {type(_e).__name__}: {_e}")
            return self.tracked_vehicles

        online_targets = [_TrackShim(row) for row in (raw if raw is not None else [])]

        results = {}
        for t in online_targets:
            track_id = int(t.track_id)
            tlwh = t.tlwh
            x1, y1, w, h = tlwh
            center = (x1 + w / 2, y1 + h / 2)
            bbox = [x1, y1, x1 + w, y1 + h]
            class_name = t.class_name if hasattr(t, 'class_name') else 'car'

            if track_id not in self.trajectories:
                self.trajectories[track_id] = []

            self.trajectories[track_id].append({
                'center': center,
                'bbox': bbox,
                'timestamp': self._last_ts   # 视频时间（2026-10-04 修复）
            })

            if len(self.trajectories[track_id]) > self.max_history:
                self.trajectories[track_id] = self.trajectories[track_id][-self.max_history:]

            direction = self._calculate_direction(track_id)
            speed = self._calculate_speed(track_id)
            is_wrong_way = self._detect_wrong_way(track_id, direction, frame_width)

            vehicle = {
                'id': track_id,
                'track_id': track_id,
                'class_name': class_name,
                'confidence': t.score,
                'bbox': bbox,
                'center': center,
                'history': self.trajectories[track_id],
                'direction': direction,
                'speed': speed,
                'is_wrong_way': is_wrong_way,
                'first_seen': self.trajectories[track_id][0]['timestamp'],
                'last_seen': self._last_ts,   # 视频时间（2026-10-04 修复：原为 time.time()）
                'frame_count': len(self.trajectories[track_id])
            }

            self.tracked_vehicles[track_id] = vehicle
            results[track_id] = vehicle

        for vid in list(self.tracked_vehicles.keys()):
            if vid not in results:
                elapsed = time.time() - self.tracked_vehicles[vid]['last_seen']
                if elapsed > 2.0:
                    del self.tracked_vehicles[vid]
                    del self.trajectories[vid]

        return results

    def _calculate_direction(self, track_id: int) -> str:
        trajectory = self.trajectories.get(track_id, [])
        if len(trajectory) < 3:
            return 'unknown'

        recent = trajectory[-3:]
        dx = sum(r['center'][0] - trajectory[i-1]['center'][0]
                 for i, r in enumerate(recent) if i > 0)
        dy = sum(r['center'][1] - trajectory[i-1]['center'][1]
                 for i, r in enumerate(recent) if i > 0)

        if abs(dx) > abs(dy):
            return 'left' if dx < 0 else 'right'
        else:
            return 'up' if dy < 0 else 'down'

    def _calculate_speed(self, track_id: int) -> float:
        trajectory = self.trajectories.get(track_id, [])
        if len(trajectory) < 2:
            return 0.0

        total_dist = 0.0
        total_time = 0.0

        for i in range(1, len(trajectory)):
            dist = ((trajectory[i]['center'][0] - trajectory[i-1]['center'][0])**2 +
                    (trajectory[i]['center'][1] - trajectory[i-1]['center'][1])**2)**0.5
            time_diff = trajectory[i]['timestamp'] - trajectory[i-1]['timestamp']
            total_dist += dist
            total_time += time_diff

        return total_dist / total_time if total_time > 0 else 0.0

    def _detect_wrong_way(self, track_id: int, direction: str, frame_width: int) -> bool:
        if direction == 'unknown':
            return False

        trajectory = self.trajectories.get(track_id, [])
        if len(trajectory) < 5:
            return False

        centers = [t['center'][0] for t in trajectory]
        avg_x = sum(centers) / len(centers)

        if avg_x < frame_width * 0.3 and direction == 'right':
            return True
        elif avg_x > frame_width * 0.7 and direction == 'left':
            return True

        return False

    def get_vehicle_by_id(self, vehicle_id: int) -> Optional[Dict]:
        return self.tracked_vehicles.get(vehicle_id)

    def get_wrong_way_vehicles(self) -> List[Dict]:
        return [v for v in self.tracked_vehicles.values() if v.get('is_wrong_way', False)]

    def get_all_vehicles(self) -> List[Dict]:
        return list(self.tracked_vehicles.values())

    def get_statistics(self) -> Dict[str, Any]:
        vehicles = self.get_all_vehicles()

        if not vehicles:
            return {
                'total_vehicles': 0,
                'wrong_way_count': 0,
                'avg_speed': 0.0,
                'directions': {}
            }

        direction_counts = {}
        speeds = []
        wrong_way_count = 0

        for v in vehicles:
            dir = v.get('direction', 'unknown')
            direction_counts[dir] = direction_counts.get(dir, 0) + 1
            speeds.append(v.get('speed', 0.0))
            if v.get('is_wrong_way', False):
                wrong_way_count += 1

        return {
            'total_vehicles': len(vehicles),
            'wrong_way_count': wrong_way_count,
            'avg_speed': sum(speeds) / len(speeds) if speeds else 0.0,
            'directions': direction_counts,
            'tracked_ids': [v['id'] for v in vehicles]
        }

    def reset(self):
        self.tracked_vehicles.clear()
        self.trajectories.clear()


class VehicleTracker:
    def __init__(self, use_bytetrack: bool = False):
        self.use_bytetrack = use_bytetrack

        if use_bytetrack:
            self.byte_tracker = ByteTrackWrapper()
            if self.byte_tracker.available:
                self.tracker = self.byte_tracker
                print("使用 ByteTrack 跟踪器")
            else:
                self.tracker = CentroidTracker()
                print("ByteTrack 不可用，降级为质心追踪")
        else:
            self.tracker = CentroidTracker()
            print("使用质心追踪器")

    def update(self, detections: List[Dict], frame_width: int = 1280,
               frame_height: int = 720, frame_ts: float = None) -> Dict[int, Dict]:
        """frame_ts: 视频时间（2026-10-04 由 DSH 新增，修复"用墙钟算速度"的 bug）

        原先轨迹点一律用 time.time()，导致检测慢于视频时速度被低估数倍，
        且同一视频在不同机器上结果不同。传 frame_index/source_fps 即修正。
        """
        self._last_ts = float(frame_ts) if frame_ts is not None else time.time()

        return self.tracker.update(detections, frame_width, frame_height)

    def get_vehicle_by_id(self, vehicle_id: int) -> Optional[Dict]:
        return self.tracker.get_vehicle_by_id(vehicle_id)

    def get_wrong_way_vehicles(self) -> List[Dict]:
        return self.tracker.get_wrong_way_vehicles()

    def get_all_vehicles(self) -> List[Dict]:
        return self.tracker.get_all_vehicles()

    def get_statistics(self) -> Dict[str, Any]:
        return self.tracker.get_statistics()

    def reset(self):
        self.tracker.reset()

    @property
    def frame_count(self):
        return self.tracker.frame_count if hasattr(self.tracker, 'frame_count') else 0

    @property
    def available(self):
        if hasattr(self, 'byte_tracker'):
            return self.byte_tracker.available
        return False


vehicle_tracker = VehicleTracker(use_bytetrack=False)
byte_tracker_instance = ByteTrackWrapper()