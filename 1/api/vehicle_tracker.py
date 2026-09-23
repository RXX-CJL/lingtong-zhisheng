# -*- coding: utf-8 -*-
"""
车辆追踪器模块
支持双模式：质心追踪（默认）和 ByteTrack（可选）
集成了 traffic_surveillance 和 smart-vehicle-counter 的跟踪思路
"""

import time
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

    def update(self, detections: List[Dict], frame_width: int = 1280, frame_height: int = 720) -> Dict[int, Dict]:
        self.frame_count += 1

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
                    'timestamp': time.time(),
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
                    'first_seen': vehicle.get('first_seen', time.time()),
                    'last_seen': time.time(),
                    'frame_count': vehicle.get('frame_count', 0) + 1
                }
            else:
                history = [{
                    'center': center,
                    'bbox': bbox,
                    'timestamp': time.time(),
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
                    'last_seen': time.time(),
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

        centers = [h['center'][0] for h in history]
        avg_x = sum(centers) / len(centers)

        if avg_x < frame_width * 0.3:
            if any(h['dx'] > 0 for h in history[-3:] if h['dx'] != 0):
                return 'opposite'
            return 'left_lane'
        elif avg_x > frame_width * 0.7:
            if any(h['dx'] < 0 for h in history[-3:] if h['dx'] != 0):
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


class ByteTrackWrapper:
    def __init__(self, frame_rate: int = 30, max_history: int = MAX_HISTORY):
        self.byte_tracker = None
        self.tracked_vehicles = {}
        self.trajectories = {}
        self.frame_rate = frame_rate
        self.max_history = max_history
        self.lane_config = None

        try:
            from yolox.tracker.byte_tracker import BYTETracker
            self.byte_tracker = BYTETracker(
                frame_rate=frame_rate,
                track_thresh=0.5,
                track_buffer=30,
                match_thresh=0.8
            )
            self.available = True
            print("ByteTrack 初始化成功")
        except ImportError:
            self.available = False
            print("ByteTrack 不可用，将使用质心追踪")

    def update(self, detections: List[Dict], frame_width: int = 1280, frame_height: int = 720) -> Dict[int, Dict]:
        if not self.available:
            return {}

        vehicle_detections = [
            d for d in detections
            if d.get('class_name') in VEHICLE_CLASSES and d.get('confidence', 0.0) >= 0.3
        ]

        dets = []
        for det in vehicle_detections:
            bbox = det.get('bbox', [0, 0, 0, 0])
            x1, y1, x2, y2 = bbox
            tlwh = [x1, y1, x2 - x1, y2 - y1]
            dets.append({
                'bbox': tlwh,
                'score': det.get('confidence', 0.0),
                'class': det.get('class_name', 0)
            })

        online_targets = self.byte_tracker.update(dets, (frame_height, frame_width))

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
                'timestamp': time.time()
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
                'last_seen': time.time(),
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

    def update(self, detections: List[Dict], frame_width: int = 1280, frame_height: int = 720) -> Dict[int, Dict]:
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