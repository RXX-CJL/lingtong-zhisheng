# -*- coding: utf-8 -*-
"""
行为理解规则引擎
基于轨迹分析判断车辆行为，支持复杂时空规则
集成了 signalwatch-traffic-detection 和 traffic-anomaly-detection 的核心思路
"""

import time
import math
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class BehaviorResult:
    behavior_type: str
    behavior_type_cn: str
    confidence: float
    is_violation: bool
    evidence: Dict
    vehicle_id: int
    timestamp: str


BEHAVIOR_TYPE_CN = {
    'red_light': '闯红灯',
    'wrong_way': '逆行',
    'illegal_parking': '违规停车',
    'lane_departure': '压线行驶',
    'speeding': '超速',
    'running_yellow': '抢黄灯',
    'illegal_turn': '违规掉头',
    'pedestrian_crossing': '未礼让行人'
}


class BehaviorEngine:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.default_config = {
            'speed_limit': 60,
            'pixel_per_meter': 10,
            'stop_line_y': 400,
            'red_light_duration_threshold': 0.5,
            'park_duration_threshold': 300,
            'lane_width': 200,
            'confidence_threshold': 0.6,
            'min_trajectory_length': 5,
            'speed_pixel_threshold': 2.0,
            'stationary_threshold': 1.5,
            'overlap_threshold': 0.1,
            'direction_consistency_threshold': 0.7
        }

    def _get_config(self, key: str, default=None):
        return self.config.get(key, self.default_config.get(key, default))

    def _bbox_overlap(self, bbox1, bbox2):
        x1, y1, x2, y2 = bbox1
        x3, y3, x4, y4 = bbox2
        overlap_x1 = max(x1, x3)
        overlap_y1 = max(y1, y3)
        overlap_x2 = min(x2, x4)
        overlap_y2 = min(y2, y4)

        if overlap_x2 <= overlap_x1 or overlap_y2 <= overlap_y1:
            return 0.0

        overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
        bbox1_area = (x2 - x1) * (y2 - y1)

        return overlap_area / bbox1_area if bbox1_area > 0 else 0.0

    def _extract_trajectory_features(self, history: List[Dict]) -> Dict:
        if len(history) < 2:
            return {}

        centers = [h['center'] for h in history]
        timestamps = [h['timestamp'] for h in history]

        dx_total = centers[-1][0] - centers[0][0]
        dy_total = centers[-1][1] - centers[0][1]
        total_distance = math.sqrt(dx_total ** 2 + dy_total ** 2)
        total_time = timestamps[-1] - timestamps[0]

        speeds = []
        for i in range(1, len(history)):
            dx = centers[i][0] - centers[i-1][0]
            dy = centers[i][1] - centers[i-1][1]
            dt = timestamps[i] - timestamps[i-1]
            if dt > 0:
                speeds.append(math.sqrt(dx ** 2 + dy ** 2) / dt)

        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
        max_speed = max(speeds) if speeds else 0.0

        x_coords = [c[0] for c in centers]
        y_coords = [c[1] for c in centers]
        x_std = math.sqrt(sum((x - sum(x_coords)/len(x_coords))**2 for x in x_coords) / len(x_coords)) if len(x_coords) > 1 else 0.0

        if len(centers) >= 3:
            path_curvature = 0.0
            for i in range(1, len(centers)-1):
                dx1 = centers[i][0] - centers[i-1][0]
                dy1 = centers[i][1] - centers[i-1][1]
                dx2 = centers[i+1][0] - centers[i][0]
                dy2 = centers[i+1][1] - centers[i][1]
                cross = dx1 * dy2 - dy1 * dx2
                mag1 = math.sqrt(dx1**2 + dy1**2)
                mag2 = math.sqrt(dx2**2 + dy2**2)
                if mag1 > 0 and mag2 > 0:
                    path_curvature += abs(cross) / (mag1 * mag2)
            path_curvature /= max(len(centers) - 2, 1)
        else:
            path_curvature = 0.0

        return {
            'avg_speed': avg_speed,
            'max_speed': max_speed,
            'total_distance': total_distance,
            'total_time': total_time,
            'x_std': x_std,
            'path_curvature': path_curvature,
            'direction_x': 'right' if dx_total > 0 else 'left' if dx_total < 0 else 'none',
            'direction_y': 'down' if dy_total > 0 else 'up' if dy_total < 0 else 'none',
            'trajectory_length': len(history)
        }

    def analyze_red_light(self, vehicle: Dict, traffic_light_state: str,
                          stop_line_y: int) -> BehaviorResult:
        history = vehicle.get('history', [])
        track_id = vehicle.get('id', vehicle.get('track_id', 0))

        if len(history) < self._get_config('min_trajectory_length', 5):
            return BehaviorResult(
                behavior_type='red_light',
                behavior_type_cn=BEHAVIOR_TYPE_CN['red_light'],
                confidence=0.0,
                is_violation=False,
                evidence={},
                vehicle_id=track_id,
                timestamp=datetime.now().isoformat()
            )

        centers = [h['center'] for h in history]
        below_stop_line = any(c[1] > stop_line_y for c in centers)
        above_stop_line = any(c[1] < stop_line_y for c in centers)

        if traffic_light_state == 'red' and below_stop_line and above_stop_line:
            first_below_idx = next(i for i, h in enumerate(history) if h['center'][1] > stop_line_y)
            speed_at_crossing = vehicle.get('speed', 0)

            features = self._extract_trajectory_features(history)
            avg_speed = features.get('avg_speed', 0)

            confidence = min(0.95, 0.6 + avg_speed / 200)

            return BehaviorResult(
                behavior_type='red_light',
                behavior_type_cn=BEHAVIOR_TYPE_CN['red_light'],
                confidence=round(confidence, 4),
                is_violation=True,
                evidence={
                    'crossed_stop_line': True,
                    'light_state': 'red',
                    'speed_at_crossing': speed_at_crossing,
                    'avg_speed': avg_speed,
                    'cross_frame': first_below_idx,
                    'trajectory_length': len(history)
                },
                vehicle_id=track_id,
                timestamp=datetime.now().isoformat()
            )

        return BehaviorResult(
            behavior_type='red_light',
            behavior_type_cn=BEHAVIOR_TYPE_CN['red_light'],
            confidence=0.0,
            is_violation=False,
            evidence={},
            vehicle_id=track_id,
            timestamp=datetime.now().isoformat()
        )

    def analyze_wrong_way(self, vehicle: Dict, road_direction: str) -> BehaviorResult:
        direction = vehicle.get('direction', 'unknown')
        history = vehicle.get('history', [])
        track_id = vehicle.get('id', vehicle.get('track_id', 0))

        if direction == 'unknown':
            return BehaviorResult(
                behavior_type='wrong_way',
                behavior_type_cn=BEHAVIOR_TYPE_CN['wrong_way'],
                confidence=0.0,
                is_violation=False,
                evidence={},
                vehicle_id=track_id,
                timestamp=datetime.now().isoformat()
            )

        wrong_direction_map = {
            'east': ['west'],
            'west': ['east'],
            'south': ['north'],
            'north': ['south'],
            'up': ['down'],
            'down': ['up'],
            'left': ['right'],
            'right': ['left']
        }

        is_wrong_direction = road_direction and direction in wrong_direction_map.get(road_direction, [])

        if not is_wrong_direction and len(history) >= 5:
            features = self._extract_trajectory_features(history)
            x_std = features.get('x_std', 0)
            frame_width = 1280

            if x_std < frame_width * 0.05:
                avg_x = sum(h['center'][0] for h in history) / len(history)
                if avg_x < frame_width * 0.3 and direction == 'right':
                    is_wrong_direction = True
                elif avg_x > frame_width * 0.7 and direction == 'left':
                    is_wrong_direction = True

        if is_wrong_direction:
            features = self._extract_trajectory_features(history)
            direction_consistency = features.get('trajectory_length', 0) >= 5
            avg_speed = features.get('avg_speed', 0)

            confidence = 0.6
            if direction_consistency and avg_speed > 5:
                confidence = min(0.9, 0.7 + avg_speed / 100)
            elif direction_consistency:
                confidence = 0.7

            return BehaviorResult(
                behavior_type='wrong_way',
                behavior_type_cn=BEHAVIOR_TYPE_CN['wrong_way'],
                confidence=round(confidence, 4),
                is_violation=True,
                evidence={
                    'vehicle_direction': direction,
                    'road_direction': road_direction,
                    'is_wrong_way': True,
                    'direction_consistency': direction_consistency,
                    'avg_speed': avg_speed,
                    'trajectory_length': len(history)
                },
                vehicle_id=track_id,
                timestamp=datetime.now().isoformat()
            )

        return BehaviorResult(
            behavior_type='wrong_way',
            behavior_type_cn=BEHAVIOR_TYPE_CN['wrong_way'],
            confidence=0.0,
            is_violation=False,
            evidence={},
            vehicle_id=track_id,
            timestamp=datetime.now().isoformat()
        )

    def analyze_illegal_parking(self, vehicle: Dict, no_parking_zones: List[Dict]) -> BehaviorResult:
        history = vehicle.get('history', [])
        track_id = vehicle.get('id', vehicle.get('track_id', 0))

        if len(history) < self._get_config('min_trajectory_length', 5):
            return BehaviorResult(
                behavior_type='illegal_parking',
                behavior_type_cn=BEHAVIOR_TYPE_CN['illegal_parking'],
                confidence=0.0,
                is_violation=False,
                evidence={},
                vehicle_id=track_id,
                timestamp=datetime.now().isoformat()
            )

        features = self._extract_trajectory_features(history)
        avg_speed = features.get('avg_speed', 0)
        total_time = features.get('total_time', 0)
        is_stationary = avg_speed < self._get_config('stationary_threshold', 1.5)

        if is_stationary:
            max_duration = self._get_config('park_duration_threshold', 300)

            in_no_parking_zone = False
            center = vehicle.get('center', (0, 0))
            for zone in no_parking_zones:
                if zone.get('x1', 0) < center[0] < zone.get('x2', float('inf')) and \
                   zone.get('y1', 0) < center[1] < zone.get('y2', float('inf')):
                    in_no_parking_zone = True
                    break

            exceeds_duration = total_time > max_duration
            is_violation = in_no_parking_zone or exceeds_duration

            confidence = 0.3
            if in_no_parking_zone and exceeds_duration:
                confidence = 0.95
            elif in_no_parking_zone:
                confidence = 0.7
            elif exceeds_duration:
                confidence = 0.6

            return BehaviorResult(
                behavior_type='illegal_parking',
                behavior_type_cn=BEHAVIOR_TYPE_CN['illegal_parking'],
                confidence=round(confidence, 4),
                is_violation=is_violation,
                evidence={
                    'is_stationary': is_stationary,
                    'avg_speed': avg_speed,
                    'duration': round(total_time, 2),
                    'max_duration': max_duration,
                    'in_no_parking_zone': in_no_parking_zone,
                    'exceeds_duration': exceeds_duration
                },
                vehicle_id=track_id,
                timestamp=datetime.now().isoformat()
            )

        return BehaviorResult(
            behavior_type='illegal_parking',
            behavior_type_cn=BEHAVIOR_TYPE_CN['illegal_parking'],
            confidence=0.0,
            is_violation=False,
            evidence={},
            vehicle_id=track_id,
            timestamp=datetime.now().isoformat()
        )

    def analyze_speeding(self, vehicle: Dict) -> BehaviorResult:
        speed = vehicle.get('speed', 0)
        history = vehicle.get('history', [])
        track_id = vehicle.get('id', vehicle.get('track_id', 0))

        speed_limit = self._get_config('speed_limit', 60)
        pixel_per_meter = self._get_config('pixel_per_meter', 10)

        features = self._extract_trajectory_features(history) if history else {}
        avg_speed = features.get('avg_speed', speed)
        max_speed = features.get('max_speed', speed)

        real_speed_pixels = max(avg_speed, max_speed)
        real_speed_kmh = real_speed_pixels * 3.6 / pixel_per_meter

        if real_speed_kmh > speed_limit:
            excess_ratio = (real_speed_kmh - speed_limit) / speed_limit
            confidence = min(0.95, 0.5 + excess_ratio * 0.8)

            return BehaviorResult(
                behavior_type='speeding',
                behavior_type_cn=BEHAVIOR_TYPE_CN['speeding'],
                confidence=round(confidence, 4),
                is_violation=True,
                evidence={
                    'pixel_speed': round(real_speed_pixels, 2),
                    'real_speed_kmh': round(real_speed_kmh, 2),
                    'speed_limit': speed_limit,
                    'excess_ratio': round(excess_ratio, 2),
                    'avg_speed': round(avg_speed, 2),
                    'max_speed': round(max_speed, 2)
                },
                vehicle_id=track_id,
                timestamp=datetime.now().isoformat()
            )

        return BehaviorResult(
            behavior_type='speeding',
            behavior_type_cn=BEHAVIOR_TYPE_CN['speeding'],
            confidence=0.0,
            is_violation=False,
            evidence={},
            vehicle_id=track_id,
            timestamp=datetime.now().isoformat()
        )

    def analyze_lane_departure(self, vehicle: Dict, lane_lines: List[Dict]) -> BehaviorResult:
        bbox = vehicle.get('bbox', [0, 0, 0, 0])
        track_id = vehicle.get('id', vehicle.get('track_id', 0))

        overlap_count = 0
        overlap_details = []
        for lane in lane_lines:
            lane_bbox = lane.get('bbox', [0, 0, 0, 0])
            overlap_ratio = self._bbox_overlap(bbox, lane_bbox)
            if overlap_ratio > self._get_config('overlap_threshold', 0.1):
                overlap_count += 1
                overlap_details.append({
                    'lane_type': lane.get('class_name', 'unknown'),
                    'overlap_ratio': round(overlap_ratio, 4),
                    'lane_bbox': lane_bbox
                })

        if overlap_count > 0:
            confidence = min(0.9, 0.5 + overlap_count * 0.15)

            return BehaviorResult(
                behavior_type='lane_departure',
                behavior_type_cn=BEHAVIOR_TYPE_CN['lane_departure'],
                confidence=round(confidence, 4),
                is_violation=True,
                evidence={
                    'overlap_count': overlap_count,
                    'lane_lines_count': len(lane_lines),
                    'overlap_details': overlap_details,
                    'vehicle_bbox': bbox
                },
                vehicle_id=track_id,
                timestamp=datetime.now().isoformat()
            )

        return BehaviorResult(
            behavior_type='lane_departure',
            behavior_type_cn=BEHAVIOR_TYPE_CN['lane_departure'],
            confidence=0.0,
            is_violation=False,
            evidence={},
            vehicle_id=track_id,
            timestamp=datetime.now().isoformat()
        )

    def analyze_running_yellow(self, vehicle: Dict, traffic_light_state: str,
                               stop_line_y: int) -> BehaviorResult:
        history = vehicle.get('history', [])
        track_id = vehicle.get('id', vehicle.get('track_id', 0))

        if len(history) < self._get_config('min_trajectory_length', 5):
            return BehaviorResult(
                behavior_type='running_yellow',
                behavior_type_cn=BEHAVIOR_TYPE_CN['running_yellow'],
                confidence=0.0,
                is_violation=False,
                evidence={},
                vehicle_id=track_id,
                timestamp=datetime.now().isoformat()
            )

        centers = [h['center'] for h in history]
        below_stop_line = any(c[1] > stop_line_y for c in centers)
        above_stop_line = any(c[1] < stop_line_y for c in centers)

        if traffic_light_state == 'yellow' and below_stop_line and above_stop_line:
            features = self._extract_trajectory_features(history)
            avg_speed = features.get('avg_speed', 0)

            if avg_speed > 15:
                confidence = min(0.85, 0.5 + avg_speed / 200)

                return BehaviorResult(
                    behavior_type='running_yellow',
                    behavior_type_cn=BEHAVIOR_TYPE_CN['running_yellow'],
                    confidence=round(confidence, 4),
                    is_violation=True,
                    evidence={
                        'crossed_stop_line': True,
                        'light_state': 'yellow',
                        'avg_speed': avg_speed,
                        'trajectory_length': len(history)
                    },
                    vehicle_id=track_id,
                    timestamp=datetime.now().isoformat()
                )

        return BehaviorResult(
            behavior_type='running_yellow',
            behavior_type_cn=BEHAVIOR_TYPE_CN['running_yellow'],
            confidence=0.0,
            is_violation=False,
            evidence={},
            vehicle_id=track_id,
            timestamp=datetime.now().isoformat()
        )

    def analyze_all(self, vehicle: Dict, scene_config: Optional[Dict] = None) -> List[BehaviorResult]:
        results = []

        scene_config = scene_config or {}

        red_light_result = self.analyze_red_light(
            vehicle,
            scene_config.get('traffic_light_state', ''),
            scene_config.get('stop_line_y', 400)
        )
        if red_light_result.is_violation:
            results.append(red_light_result)

        wrong_way_result = self.analyze_wrong_way(
            vehicle,
            scene_config.get('road_direction', '')
        )
        if wrong_way_result.is_violation:
            results.append(wrong_way_result)

        illegal_parking_result = self.analyze_illegal_parking(
            vehicle,
            scene_config.get('no_parking_zones', [])
        )
        if illegal_parking_result.is_violation:
            results.append(illegal_parking_result)

        speeding_result = self.analyze_speeding(vehicle)
        if speeding_result.is_violation:
            results.append(speeding_result)

        lane_departure_result = self.analyze_lane_departure(
            vehicle,
            scene_config.get('lane_lines', [])
        )
        if lane_departure_result.is_violation:
            results.append(lane_departure_result)

        running_yellow_result = self.analyze_running_yellow(
            vehicle,
            scene_config.get('traffic_light_state', ''),
            scene_config.get('stop_line_y', 400)
        )
        if running_yellow_result.is_violation:
            results.append(running_yellow_result)

        return results


def analyze_behavior(vehicle: Dict, scene_config: Optional[Dict] = None,
                     behavior_type: Optional[str] = None) -> Dict:
    engine = BehaviorEngine()

    if behavior_type:
        if behavior_type == 'red_light':
            result = engine.analyze_red_light(
                vehicle,
                scene_config.get('traffic_light_state', ''),
                scene_config.get('stop_line_y', 400)
            )
            return {
                'success': True,
                'behaviors': [result] if result.is_violation else [],
                'message': f'分析完成，检测到 {len([result] if result.is_violation else [])} 个违规行为'
            }
        elif behavior_type == 'wrong_way':
            result = engine.analyze_wrong_way(
                vehicle,
                scene_config.get('road_direction', '')
            )
            return {
                'success': True,
                'behaviors': [result] if result.is_violation else [],
                'message': f'分析完成，检测到 {len([result] if result.is_violation else [])} 个违规行为'
            }
        elif behavior_type == 'illegal_parking':
            result = engine.analyze_illegal_parking(
                vehicle,
                scene_config.get('no_parking_zones', [])
            )
            return {
                'success': True,
                'behaviors': [result] if result.is_violation else [],
                'message': f'分析完成，检测到 {len([result] if result.is_violation else [])} 个违规行为'
            }
        elif behavior_type == 'speeding':
            result = engine.analyze_speeding(vehicle)
            return {
                'success': True,
                'behaviors': [result] if result.is_violation else [],
                'message': f'分析完成，检测到 {len([result] if result.is_violation else [])} 个违规行为'
            }
        elif behavior_type == 'lane_departure':
            result = engine.analyze_lane_departure(
                vehicle,
                scene_config.get('lane_lines', [])
            )
            return {
                'success': True,
                'behaviors': [result] if result.is_violation else [],
                'message': f'分析完成，检测到 {len([result] if result.is_violation else [])} 个违规行为'
            }
        else:
            return {
                'success': False,
                'behaviors': [],
                'message': f'未知行为类型: {behavior_type}'
            }

    behaviors = engine.analyze_all(vehicle, scene_config)
    return {
        'success': True,
        'behaviors': behaviors,
        'count': len(behaviors),
        'message': f'行为分析完成，检测到 {len(behaviors)} 个违规行为'
    }


if __name__ == "__main__":
    test_vehicle = {
        'id': 1,
        'class_name': 'car',
        'confidence': 0.95,
        'bbox': [200, 300, 400, 500],
        'center': (300, 400),
        'direction': 'down',
        'speed': 25.0,
        'history': [
            {'center': (300, 100), 'bbox': [200, 0, 400, 200], 'timestamp': time.time() - 2.0},
            {'center': (300, 200), 'bbox': [200, 100, 400, 300], 'timestamp': time.time() - 1.5},
            {'center': (300, 300), 'bbox': [200, 200, 400, 400], 'timestamp': time.time() - 1.0},
            {'center': (300, 400), 'bbox': [200, 300, 400, 500], 'timestamp': time.time() - 0.5},
            {'center': (300, 500), 'bbox': [200, 400, 400, 600], 'timestamp': time.time()}
        ],
        'is_wrong_way': False,
        'first_seen': time.time() - 2.0,
        'last_seen': time.time(),
        'frame_count': 5
    }

    test_scene_config = {
        'traffic_light_state': 'red',
        'stop_line_y': 350,
        'road_direction': 'south',
        'speed_limit': 60,
        'pixel_per_meter': 10,
        'no_parking_zones': [{'x1': 0, 'y1': 400, 'x2': 1280, 'y2': 720}],
        'lane_lines': [{'class_name': 'white_line', 'bbox': [310, 0, 320, 720]}]
    }

    print("=== BehaviorEngine 测试 ===")

    engine = BehaviorEngine()

    print("\n1. 测试闯红灯检测（红灯+过线）")
    result = engine.analyze_red_light(test_vehicle, 'red', 350)
    print(f"   违规: {result.is_violation}, 置信度: {result.confidence}")

    print("\n2. 测试逆行检测（方向相反）")
    wrong_way_vehicle = test_vehicle.copy()
    wrong_way_vehicle['direction'] = 'up'
    result = engine.analyze_wrong_way(wrong_way_vehicle, 'south')
    print(f"   违规: {result.is_violation}, 置信度: {result.confidence}")

    print("\n3. 测试违规停车（禁停区域）")
    parked_vehicle = test_vehicle.copy()
    parked_vehicle['speed'] = 0.5
    parked_vehicle['direction'] = 'stationary'
    result = engine.analyze_illegal_parking(parked_vehicle, test_scene_config['no_parking_zones'])
    print(f"   违规: {result.is_violation}, 置信度: {result.confidence}")

    print("\n4. 测试超速检测")
    speeding_vehicle = test_vehicle.copy()
    speeding_vehicle['speed'] = 30.0
    result = engine.analyze_speeding(speeding_vehicle)
    print(f"   违规: {result.is_violation}, 置信度: {result.confidence}")

    print("\n5. 测试压线检测")
    lane_vehicle = test_vehicle.copy()
    lane_vehicle['bbox'] = [305, 300, 400, 500]
    result = engine.analyze_lane_departure(lane_vehicle, test_scene_config['lane_lines'])
    print(f"   违规: {result.is_violation}, 置信度: {result.confidence}")

    print("\n6. 测试抢黄灯检测")
    result = engine.analyze_running_yellow(test_vehicle, 'yellow', 350)
    print(f"   违规: {result.is_violation}, 置信度: {result.confidence}")

    print("\n7. 测试全行为分析")
    result = analyze_behavior(test_vehicle, test_scene_config)
    print(f"   检测到违规数: {result['count']}")
    for b in result['behaviors']:
        print(f"   - {b.behavior_type_cn}: 置信度 {b.confidence}")