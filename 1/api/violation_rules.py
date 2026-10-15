# -*- coding: utf-8 -*-
"""
规则引擎模块 - ViolationRuleEngine 类
基于检测结果判断违规行为，支持配置化规则
"""

import json
from datetime import datetime
from typing import List, Dict, Optional

VIOLATION_TYPE_CN = {
    'no_helmet': '未戴头盔',
    'illegal_parking': '违规停车',
    'lane_departure': '压线行驶',
    'wrong_way': '逆行',
    'red_light': '闯红灯',
    'speeding': '超速'
}

VEHICLE_CLASSES = {'car', 'motorcycle', 'truck', 'bus', 'bicycle'}
HELMET_CLASSES = {'helmet', 'head', 'hard_hat', 'safety_helmet', 'with_helmet'}
PERSON_CLASSES = {'person', 'rider', 'motorcyclist', 'cyclist'}
TRAFFIC_SIGNAL_CLASSES = {'traffic light', 'traffic_light'}
RED_LIGHT_CLASSES = {'red_light', 'red', 'traffic_light_red'}
YELLOW_LIGHT_CLASSES = {'yellow_light', 'yellow', 'traffic_light_yellow'}
GREEN_LIGHT_CLASSES = {'green_light', 'green', 'traffic_light_green'}
LANE_LINE_CLASSES = {'lane_line', 'road_line', 'white_line', 'yellow_line'}
NO_HELMET_CLASSES = {'no_helmet', 'no-helmet', 'without_helmet', 'Without Helmet'}
PEDESTRIAN_CLASSES = {'person', 'pedestrian'}
CROSSWALK_CLASSES = {'crosswalk', 'zebra_crossing', 'zebra'}
STOP_SIGN_CLASSES = {'stop sign', 'stop_sign'}
YIELD_SIGN_CLASSES = {'yield', 'yield_sign', 'give_way'}


class ViolationRuleEngine:
    """违规检测规则引擎"""

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化规则引擎
        
        参数:
            config: 规则配置字典，可覆盖默认配置
        """
        self.config = config or {}
        
        self.default_config = {
            # 2026-10-03 由 DSH 收紧：原值 0.5/0.3/0.4 过于宽松，导致几乎每帧都报违规
            # （实测 80 秒 519 条），演示时满屏红框。提高后显著降低误报。
            # 注意：这些是"本地规则判定"的置信度门槛，与云端咨询门槛（CONSULT_THRESHOLD）独立。
            'confidence_threshold': 0.65,
            'max_park_duration_seconds': 300,
            'helmet_confidence_threshold': 0.55,
            'vehicle_confidence_threshold': 0.6
        }
        
        self.rules = {
            'no_helmet': self._check_no_helmet,
            'red_light': self._check_red_light,
            'illegal_parking': self._check_illegal_parking,
            'lane_departure': self._check_lane_departure,
            'wrong_way': self._check_wrong_way,
            'speeding': self._check_speeding
        }

    def _get_config_value(self, key: str, default=None):
        """获取配置值，优先使用用户配置"""
        return self.config.get(key, self.default_config.get(key, default))

    def _get_detection_classes(self, detections: List[Dict]) -> set:
        """获取检测到的所有类别集合"""
        return {det.get('class_name', '') for det in detections if det.get('class_name')}

    def _has_detection(self, detections: List[Dict], class_name: str, 
                       min_confidence: float = 0.0) -> bool:
        """检查是否检测到指定类别"""
        for det in detections:
            if det.get('class_name') == class_name and det.get('confidence', 0.0) >= min_confidence:
                return True
        return False

    def _has_any_detection(self, detections: List[Dict], class_names: set,
                           min_confidence: float = 0.0) -> bool:
        """检查是否检测到指定类别中的任意一个"""
        for det in detections:
            if det.get('class_name') in class_names and det.get('confidence', 0.0) >= min_confidence:
                return True
        return False

    def _get_max_confidence(self, detections: List[Dict], class_name: str) -> float:
        """获取指定类别的最高置信度"""
        return max((det.get('confidence', 0.0) for det in detections 
                   if det.get('class_name') == class_name), default=0.0)

    def _get_max_confidence_for_classes(self, detections: List[Dict], class_names: set) -> float:
        """获取指定类别集合中的最高置信度"""
        return max((det.get('confidence', 0.0) for det in detections 
                   if det.get('class_name') in class_names), default=0.0)

    def _count_detections(self, detections: List[Dict], class_names: set,
                          min_confidence: float = 0.0) -> int:
        """统计指定类别的检测数量"""
        return sum(1 for det in detections 
                   if det.get('class_name') in class_names and det.get('confidence', 0.0) >= min_confidence)

    def _get_detection_by_class(self, detections: List[Dict], class_name: str,
                                min_confidence: float = 0.0) -> Optional[Dict]:
        """获取指定类别的最高置信度检测"""
        filtered = [d for d in detections if d.get('class_name') == class_name and d.get('confidence', 0.0) >= min_confidence]
        if not filtered:
            return None
        return max(filtered, key=lambda x: x.get('confidence', 0.0))

    def _get_detections_by_classes(self, detections: List[Dict], class_names: set,
                                   min_confidence: float = 0.0) -> List[Dict]:
        """获取指定类别集合的所有检测"""
        return [d for d in detections if d.get('class_name') in class_names and d.get('confidence', 0.0) >= min_confidence]

    def _get_bbox_center(self, bbox: List[float]) -> tuple:
        """获取bounding box中心点"""
        if len(bbox) >= 4:
            return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
        return (0, 0)

    def _bbox_distance(self, bbox1: List[float], bbox2: List[float]) -> float:
        """计算两个bounding box中心点的距离"""
        c1 = self._get_bbox_center(bbox1)
        c2 = self._get_bbox_center(bbox2)
        return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** 0.5

    # ------------------------------------------------------------------
    # 多边形区域判定（2026-10-03 由 DSH 新增）
    # 用于人工/自动标注的斑马线、禁停区等：不再依赖检测类，改用几何判定
    # ------------------------------------------------------------------
    @staticmethod
    def _point_in_polygon(px: float, py: float, polygon: List) -> bool:
        """射线法判断点是否在多边形内（支持任意凸/凹多边形）

        polygon: [[x1,y1],[x2,y2],...]  至少 3 个顶点
        """
        n = len(polygon)
        if n < 3:
            return False
        inside = False
        j = n - 1
        for i in range(n):
            try:
                xi, yi = float(polygon[i][0]), float(polygon[i][1])
                xj, yj = float(polygon[j][0]), float(polygon[j][1])
            except (TypeError, ValueError, IndexError):
                return False
            if ((yi > py) != (yj > py)) and \
                    (px < (xj - xi) * (py - yi) / ((yj - yi) or 1e-9) + xi):
                inside = not inside
            j = i
        return inside

    @staticmethod
    def _polygon_bbox(polygon: List) -> tuple:
        """多边形的轴对齐包围盒 (x1,y1,x2,y2)"""
        xs, ys = [], []
        for p in polygon or []:
            try:
                xs.append(float(p[0]))
                ys.append(float(p[1]))
            except (TypeError, ValueError, IndexError):
                continue
        if not xs:
            return (0.0, 0.0, 0.0, 0.0)
        return (min(xs), min(ys), max(xs), max(ys))

    def _bbox_in_any_polygon(self, bbox: List[float], polygons: List,
                             overlap_ratio: float = 0.25) -> bool:
        """车辆框是否落在任一多边形区域内

        判定（满足其一即算）：
          1. 车辆框中心点落在多边形内（最常用、最直观）
          2. 车辆框与多边形包围盒的重叠比例 >= overlap_ratio
        """
        if not polygons or len(bbox) < 4:
            return False
        cx, cy = self._get_bbox_center(bbox)
        for poly in polygons:
            if not poly:
                continue
            if self._point_in_polygon(cx, cy, poly):
                return True
            px1, py1, px2, py2 = self._polygon_bbox(poly)
            if px2 <= px1 or py2 <= py1:
                continue
            # 包围盒重叠比例（以车辆框面积为分母）
            ix1, iy1 = max(float(bbox[0]), px1), max(float(bbox[1]), py1)
            ix2, iy2 = min(float(bbox[2]), px2), min(float(bbox[3]), py2)
            if ix2 <= ix1 or iy2 <= iy1:
                continue
            inter = (ix2 - ix1) * (iy2 - iy1)
            area = max(1.0, (float(bbox[2]) - float(bbox[0])) *
                       (float(bbox[3]) - float(bbox[1])))
            if inter / area >= overlap_ratio:
                return True
        return False

    def _bbox_overlap_ratio(self, bbox1: List[float], bbox2: List[float]) -> float:
        """计算两个bounding box的重叠比例"""
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

    def _check_no_helmet(self, detections: List[Dict], scene_config: Optional[Dict] = None) -> Dict:
        """
        检查未戴头盔违规
        
        判断规则: 检测到motorcycle/bicycle但对应区域没有helmet，或直接检测到no_helmet
        """
        threshold = self._get_config_value('vehicle_confidence_threshold', 0.4)
        helmet_threshold = self._get_config_value('helmet_confidence_threshold', 0.3)
        
        has_vehicle = self._has_any_detection(detections, VEHICLE_CLASSES, threshold)
        has_two_wheeler = self._has_detection(detections, 'motorcycle', threshold) or \
                          self._has_detection(detections, 'bicycle', threshold)
        has_person = self._has_any_detection(detections, PERSON_CLASSES, threshold)
        has_helmet = self._has_any_detection(detections, HELMET_CLASSES, helmet_threshold)
        has_no_helmet = self._has_any_detection(detections, NO_HELMET_CLASSES, helmet_threshold)
        
        if has_no_helmet:
            no_helmet_conf = self._get_max_confidence_for_classes(detections, NO_HELMET_CLASSES)
            return {
                'violation_type': 'no_helmet',
                'violation_type_cn': VIOLATION_TYPE_CN['no_helmet'],
                'confidence': round(no_helmet_conf, 4),
                'is_violation': True,
                'evidence': {
                    'has_no_helmet': True,
                    'no_helmet_confidence': no_helmet_conf
                },
                'location': self._extract_location(detections),
                'timestamp': datetime.now().isoformat(),
                'message': '直接检测到未戴头盔'
            }
        
        if has_two_wheeler and has_person and not has_helmet:
            vehicle_conf = self._get_max_confidence_for_classes(detections, {'motorcycle', 'bicycle'})
            person_conf = self._get_max_confidence_for_classes(detections, PERSON_CLASSES)
            helmet_conf = self._get_max_confidence_for_classes(detections, HELMET_CLASSES)
            
            confidence = min(vehicle_conf, person_conf, 1.0 - helmet_conf)
            
            return {
                'violation_type': 'no_helmet',
                'violation_type_cn': VIOLATION_TYPE_CN['no_helmet'],
                'confidence': round(max(confidence, 0.5), 4),
                'is_violation': True,
                'evidence': {
                    'has_two_wheeler': has_two_wheeler,
                    'has_person': has_person,
                    'has_helmet': has_helmet,
                    'vehicle_confidence': vehicle_conf,
                    'person_confidence': person_conf,
                    'helmet_confidence': helmet_conf
                },
                'location': self._extract_location(detections),
                'timestamp': datetime.now().isoformat(),
                'message': '检测到两轮车和人员但未检测到头盔'
            }
        
        return {
            'violation_type': 'no_helmet',
            'violation_type_cn': VIOLATION_TYPE_CN['no_helmet'],
            'confidence': 0.0,
            'is_violation': False,
            'evidence': {},
            'location': None,
            'timestamp': datetime.now().isoformat(),
            'message': '未检测到未戴头盔违规'
        }

    def _check_red_light(self, detections: List[Dict], scene_config: Optional[Dict] = None) -> Dict:
        """
        检查闯红灯违规
        
        判断规则: 红灯状态下车辆越过停止线
        支持两种检测方式:
        1. 专用红绿灯模型检测到red_light
        2. 通用模型检测到traffic light + 灯色判断
        增强逻辑:
        - 检查车辆与停止线的位置关系
        - 检查车辆与红绿灯的相对位置（确保是同方向的红绿灯）
        """
        threshold = self._get_config_value('confidence_threshold', 0.5)
        
        has_vehicle = self._has_any_detection(detections, VEHICLE_CLASSES, threshold)
        has_traffic_light = self._has_any_detection(detections, TRAFFIC_SIGNAL_CLASSES, threshold)
        has_red_light = self._has_any_detection(detections, RED_LIGHT_CLASSES, threshold)
        
        vehicle_dets = self._get_detections_by_classes(detections, VEHICLE_CLASSES, threshold)
        red_light_dets = self._get_detections_by_classes(detections, RED_LIGHT_CLASSES, threshold)
        signal_dets = self._get_detections_by_classes(detections, TRAFFIC_SIGNAL_CLASSES, threshold)
        
        stop_line_y = scene_config.get('stop_line_y', 400) if scene_config else 400
        
        if has_vehicle and has_red_light:
            vehicle_conf = self._get_max_confidence_for_classes(detections, VEHICLE_CLASSES)
            red_light_conf = self._get_max_confidence_for_classes(detections, RED_LIGHT_CLASSES)
            
            vehicle_passed_stop_line = False
            for vehicle_det in vehicle_dets:
                bbox = vehicle_det.get('bbox', [0, 0, 0, 0])
                if len(bbox) >= 4:
                    vehicle_bottom = bbox[3]
                    if vehicle_bottom > stop_line_y:
                        vehicle_passed_stop_line = True
                        break
            
            same_direction = True
            if red_light_dets and vehicle_dets:
                light_center = self._get_bbox_center(red_light_dets[0].get('bbox', [0, 0, 0, 0]))
                vehicle_center = self._get_bbox_center(vehicle_dets[0].get('bbox', [0, 0, 0, 0]))
                if abs(light_center[0] - vehicle_center[0]) > 300:
                    same_direction = False
            
            confidence_factor = 0.7
            if vehicle_passed_stop_line:
                confidence_factor = 0.95
            if same_direction:
                confidence_factor = min(0.95, confidence_factor + 0.1)
            
            confidence = min(vehicle_conf, red_light_conf) * confidence_factor
            
            is_violation = vehicle_passed_stop_line and same_direction
            
            return {
                'violation_type': 'red_light',
                'violation_type_cn': VIOLATION_TYPE_CN['red_light'],
                'confidence': round(confidence, 4),
                'is_violation': is_violation,
                'evidence': {
                    'has_vehicle': has_vehicle,
                    'has_red_light': True,
                    'vehicle_confidence': vehicle_conf,
                    'red_light_confidence': red_light_conf,
                    'vehicle_passed_stop_line': vehicle_passed_stop_line,
                    'same_direction': same_direction,
                    'stop_line_y': stop_line_y,
                    'vehicle_count': len(vehicle_dets),
                    'red_light_count': len(red_light_dets)
                },
                'location': self._extract_location(detections),
                'timestamp': datetime.now().isoformat(),
                'message': '检测到红灯和车辆，判定为闯红灯' if is_violation else '检测到红灯但车辆未越过停止线'
            }
        
        if has_vehicle and has_traffic_light:
            vehicle_conf = self._get_max_confidence_for_classes(detections, VEHICLE_CLASSES)
            signal_conf = self._get_max_confidence_for_classes(detections, TRAFFIC_SIGNAL_CLASSES)
            
            confidence = min(vehicle_conf, signal_conf) * 0.5
            
            return {
                'violation_type': 'red_light',
                'violation_type_cn': VIOLATION_TYPE_CN['red_light'],
                'confidence': round(confidence, 4),
                'is_violation': True,
                'evidence': {
                    'has_vehicle': has_vehicle,
                    'has_traffic_light': has_traffic_light,
                    'vehicle_confidence': vehicle_conf,
                    'traffic_light_confidence': signal_conf,
                    'note': '通用模型检测到红绿灯，需结合灯色确认'
                },
                'location': self._extract_location(detections),
                'timestamp': datetime.now().isoformat(),
                'message': '检测到车辆和红绿灯，疑似闯红灯'
            }
        
        return {
            'violation_type': 'red_light',
            'violation_type_cn': VIOLATION_TYPE_CN['red_light'],
            'confidence': 0.0,
            'is_violation': False,
            'evidence': {},
            'location': None,
            'timestamp': datetime.now().isoformat(),
            'message': '未检测到闯红灯违规'
        }

    def _check_illegal_parking(self, detections: List[Dict], scene_config: Optional[Dict] = None) -> Dict:
        """
        检查违规停车
        
        判断规则: 车辆在禁停区域停留超过N秒
        增强逻辑:
        - 检查车辆是否在禁停区域（斑马线、消防通道、路口等）
        - 检测禁停标志
        - 结合车辆位置判断
        """
        threshold = self._get_config_value('confidence_threshold', 0.5)
        max_duration = self._get_config_value('max_park_duration_seconds', 300)
        
        vehicle_count = self._count_detections(detections, VEHICLE_CLASSES, threshold)
        vehicle_dets = self._get_detections_by_classes(detections, VEHICLE_CLASSES, threshold)
        
        has_stop_sign = self._has_any_detection(detections, STOP_SIGN_CLASSES, threshold)
        has_crosswalk = self._has_any_detection(detections, CROSSWALK_CLASSES, threshold)
        
        if vehicle_count > 0:
            vehicle_conf = self._get_max_confidence_for_classes(detections, VEHICLE_CLASSES)
            
            is_no_parking_zone = False
            in_special_area = False
            
            if scene_config:
                is_no_parking_zone = scene_config.get('is_no_parking_zone', False)
                
                no_parking_zones = scene_config.get('no_parking_zones', [])
                for vehicle_det in vehicle_dets:
                    bbox = vehicle_det.get('bbox', [0, 0, 0, 0])
                    center = self._get_bbox_center(bbox)
                    for zone in no_parking_zones:
                        if zone.get('x1', 0) < center[0] < zone.get('x2', float('inf')) and \
                           zone.get('y1', 0) < center[1] < zone.get('y2', float('inf')):
                            in_special_area = True
                            break
                    if in_special_area:
                        break
            
            if has_crosswalk:
                crosswalk_det = self._get_detection_by_class(detections, 'crosswalk', threshold)
                if crosswalk_det and vehicle_dets:
                    crosswalk_bbox = crosswalk_det.get('bbox', [0, 0, 0, 0])
                    for vehicle_det in vehicle_dets:
                        vehicle_bbox = vehicle_det.get('bbox', [0, 0, 0, 0])
                        if self._bbox_overlap_ratio(vehicle_bbox, crosswalk_bbox) > 0.1:
                            in_special_area = True
                            break

            # ---- 人工/自动标注的斑马线多边形（2026-10-03 由 DSH 新增）----------
            # 背景：原实现依赖 CROSSWALK_CLASSES 检测类，而 COCO 模型不输出该类
            # （实测 0 检出），导致"斑马线违停"规则永远不生效。
            # 方案（参考参考项目的"运行前人工标注"思路）：
            #   scene_config['crosswalk_zones'] 存多边形顶点，用几何判定替代检测类：
            #   - 车辆框中心落在多边形内            -> 违停
            #   - 或车辆框与多边形包围盒重叠比例超限 -> 违停
            if not in_special_area and scene_config:
                zones = scene_config.get('crosswalk_zones') or []
                for vehicle_det in vehicle_dets:
                    bbox = vehicle_det.get('bbox', [0, 0, 0, 0])
                    if self._bbox_in_any_polygon(bbox, zones, overlap_ratio=0.25):
                        in_special_area = True
                        break
            # ------------------------------------------------------------------
            
            duration = scene_config.get('park_duration_seconds', 0) if scene_config else 0
            exceeds_duration = duration > max_duration
            
            # ---- 违停判定（2026-10-04 由 DSH 修正）------------------------
            # 原实现：is_violation = in_special_area **or** is_no_parking_zone
            #                     **or** exceeds_duration
            #
            # 三个严重问题：
            #   ① 用 `or` -> 任一条件成立即判违规。而 is_no_parking_zone 是
            #      **场景级全局标志**（"这个路口有没有禁停区"），与"这辆车是否
            #      停在那里"无关 -> 只要场景配了禁停区，**路口所有车都被判违停**
            #   ② 完全没有"车辆是否静止"的信息 -> 单帧无法区分"违停"与"路过"
            #   ③ 默认 park_duration_seconds=0 时 exceeds_duration 恒 False，
            #      进一步让时长维度失效
            #
            # 用户口径：「在不可停车区域内，速度约 0，持续 >5 秒 -> 判违停」。
            # 静止判定在 behavior_engine.analyze_illegal_parking 里做（那里有轨迹），
            # 本函数只有单帧，因此**必须要求停放时长**才判违规 —— 宁可漏报不可误报。
            # ---------------------------------------------------------------
            is_violation = bool(in_special_area and exceeds_duration)

            if in_special_area and exceeds_duration:
                confidence = min(vehicle_conf * 0.9, 0.95)
            elif in_special_area:
                # 在禁停区但时长不够 -> 不算违规（可能只是经过）
                confidence = min(vehicle_conf * 0.4, 0.5)
            else:
                confidence = vehicle_conf * 0.3
            
            return {
                'violation_type': 'illegal_parking',
                'violation_type_cn': VIOLATION_TYPE_CN['illegal_parking'],
                'confidence': round(confidence, 4),
                'is_violation': is_violation,
                'evidence': {
                    'vehicle_count': vehicle_count,
                    'vehicle_confidence': vehicle_conf,
                    'is_no_parking_zone': is_no_parking_zone,
                    'in_special_area': in_special_area,
                    'has_stop_sign': has_stop_sign,
                    'has_crosswalk': has_crosswalk,
                    'park_duration_seconds': duration,
                    'max_allowed_duration': max_duration,
                    'exceeds_duration': exceeds_duration
                },
                'location': self._extract_location(detections),
                'timestamp': datetime.now().isoformat(),
                'message': f'检测到 {vehicle_count} 辆车辆{"，位于禁停区域" if in_special_area else ""}{"，位于禁停标志区域" if is_no_parking_zone else ""}{"，停留超时" if exceeds_duration else ""}'
            }
        
        return {
            'violation_type': 'illegal_parking',
            'violation_type_cn': VIOLATION_TYPE_CN['illegal_parking'],
            'confidence': 0.0,
            'is_violation': False,
            'evidence': {},
            'location': None,
            'timestamp': datetime.now().isoformat(),
            'message': '未检测到违规停车'
        }

    def _check_lane_departure(self, detections: List[Dict], scene_config: Optional[Dict] = None) -> Dict:
        """
        检查压线行驶
        
        判断规则: 车辆与车道线重叠
        支持两种检测方式:
        1. 专用车道线模型检测到lane_line
        2. 通过bounding box重叠判断车辆是否压线
        """
        threshold = self._get_config_value('confidence_threshold', 0.5)
        
        vehicle_count = self._count_detections(detections, VEHICLE_CLASSES, threshold)
        lane_line_count = self._count_detections(detections, LANE_LINE_CLASSES, threshold)
        
        vehicle_dets = [d for d in detections if d.get('class_name') in VEHICLE_CLASSES and d.get('confidence', 0.0) >= threshold]
        lane_dets = [d for d in detections if d.get('class_name') in LANE_LINE_CLASSES and d.get('confidence', 0.0) >= threshold]
        
        if vehicle_count > 0 and lane_line_count > 0:
            vehicle_conf = self._get_max_confidence_for_classes(detections, VEHICLE_CLASSES)
            lane_conf = self._get_max_confidence_for_classes(detections, LANE_LINE_CLASSES)
            
            overlap_count = 0
            for vehicle_det in vehicle_dets:
                v_bbox = vehicle_det.get('bbox', [0, 0, 0, 0])
                for lane_det in lane_dets:
                    l_bbox = lane_det.get('bbox', [0, 0, 0, 0])
                    if self._bbox_overlap(v_bbox, l_bbox) > 0:
                        overlap_count += 1
                        break
            
            has_overlap = overlap_count > 0
            
            confidence = vehicle_conf * 0.5
            if has_overlap:
                confidence = min(vehicle_conf * lane_conf * 0.8, 0.9)
            
            is_violation = has_overlap
            
            return {
                'violation_type': 'lane_departure',
                'violation_type_cn': VIOLATION_TYPE_CN['lane_departure'],
                'confidence': round(confidence, 4),
                'is_violation': is_violation,
                'evidence': {
                    'vehicle_count': vehicle_count,
                    'lane_line_count': lane_line_count,
                    'overlap_count': overlap_count,
                    'has_overlap': has_overlap,
                    'vehicle_confidence': vehicle_conf,
                    'lane_line_confidence': lane_conf
                },
                'location': self._extract_location(detections),
                'timestamp': datetime.now().isoformat(),
                'message': f'检测到 {vehicle_count} 辆车辆和 {lane_line_count} 条车道线{"，存在压线" if has_overlap else ""}'
            }
        
        elif vehicle_count > 0:
            vehicle_conf = self._get_max_confidence_for_classes(detections, VEHICLE_CLASSES)
            has_lane_line = scene_config.get('has_lane_line', False) if scene_config else False
            
            confidence = vehicle_conf * 0.5
            if has_lane_line:
                confidence = min(vehicle_conf * 0.7, 0.85)
            
            is_violation = has_lane_line
            
            return {
                'violation_type': 'lane_departure',
                'violation_type_cn': VIOLATION_TYPE_CN['lane_departure'],
                'confidence': round(confidence, 4),
                'is_violation': is_violation,
                'evidence': {
                    'vehicle_count': vehicle_count,
                    'vehicle_confidence': vehicle_conf,
                    'has_lane_line': has_lane_line
                },
                'location': self._extract_location(detections),
                'timestamp': datetime.now().isoformat(),
                'message': f'检测到 {vehicle_count} 辆车辆{"，疑似压线" if has_lane_line else ""}'
            }
        
        return {
            'violation_type': 'lane_departure',
            'violation_type_cn': VIOLATION_TYPE_CN['lane_departure'],
            'confidence': 0.0,
            'is_violation': False,
            'evidence': {},
            'location': None,
            'timestamp': datetime.now().isoformat(),
            'message': '未检测到压线行驶'
        }
    
    def _bbox_overlap(self, bbox1, bbox2):
        """计算两个bounding box的重叠面积比例"""
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
        
        if bbox1_area == 0:
            return 0.0
        
        return overlap_area / bbox1_area

    def _check_wrong_way(self, detections: List[Dict], scene_config: Optional[Dict] = None) -> Dict:
        """
        检查逆行
        
        判断规则:
        1. 通过车辆追踪器追踪车辆运动方向
        2. 结合车道线位置判断车辆是否在对向车道
        3. 连续帧对比确认运动方向一致性
        4. 判断车辆是否在对向车道行驶
        """
        threshold = self._get_config_value('confidence_threshold', 0.5)
        
        vehicle_count = self._count_detections(detections, VEHICLE_CLASSES, threshold)
        
        if vehicle_count == 0:
            return {
                'violation_type': 'wrong_way',
                'violation_type_cn': VIOLATION_TYPE_CN['wrong_way'],
                'confidence': 0.0,
                'is_violation': False,
                'evidence': {},
                'location': None,
                'timestamp': datetime.now().isoformat(),
                'message': '未检测到逆行'
            }
        
        try:
            from vehicle_tracker import vehicle_tracker
            # ★2026-10-06 由 DSH 修正：原来不传 frame_width，用的是 tracker 默认
            # **1280**，而本项目画面是 1920 -> 0.7*1280=896 的"对向车道"阈值严重偏左，
            # 车在画面中右侧（x≈1200）也会被判在对向车道。
            _fw = int((scene_config or {}).get('frame_width') or 0) or 1280
            _fh = int((scene_config or {}).get('frame_height') or 0) or 720
            tracked_vehicles = vehicle_tracker.update(detections, _fw, _fh)
            wrong_way_vehicles = vehicle_tracker.get_wrong_way_vehicles()
            
            vehicle_conf = self._get_max_confidence_for_classes(detections, VEHICLE_CLASSES)
            
            lane_line_count = self._count_detections(detections, LANE_LINE_CLASSES, threshold)
            
            has_wrong_way = len(wrong_way_vehicles) > 0
            wrong_way_count = len(wrong_way_vehicles)
            
            if has_wrong_way:
                confidence = min(vehicle_conf * 0.85, 0.95)
            elif lane_line_count > 0:
                confidence = vehicle_conf * 0.3
            else:
                confidence = vehicle_conf * 0.2
            
            is_violation = has_wrong_way and wrong_way_count > 0
            
            evidence = {
                'vehicle_count': vehicle_count,
                'vehicle_confidence': vehicle_conf,
                'wrong_way_count': wrong_way_count,
                'lane_line_count': lane_line_count,
                'tracked_vehicles': len(tracked_vehicles),
                'has_wrong_way': has_wrong_way,
            }
            
            if wrong_way_vehicles:
                evidence['wrong_way_details'] = [{
                    'vehicle_id': v['id'],
                    'class_name': v['class_name'],
                    'direction': v['direction'],
                    'speed': round(v['speed'], 2),
                    'frame_count': v['frame_count']
                } for v in wrong_way_vehicles]
            
            return {
                'violation_type': 'wrong_way',
                'violation_type_cn': VIOLATION_TYPE_CN['wrong_way'],
                'confidence': round(confidence, 4),
                'is_violation': is_violation,
                'evidence': evidence,
                'location': self._extract_location(detections),
                'timestamp': datetime.now().isoformat(),
                'message': f'检测到 {wrong_way_count} 辆逆行车辆' if has_wrong_way else f'检测到 {vehicle_count} 辆车辆，未发现逆行'
            }
        except Exception as e:
            vehicle_conf = self._get_max_confidence_for_classes(detections, VEHICLE_CLASSES)
            
            road_direction = scene_config.get('road_direction', '') if scene_config else ''
            vehicle_direction = scene_config.get('vehicle_direction', '') if scene_config else ''
            is_wrong_direction = road_direction and vehicle_direction and road_direction != vehicle_direction
            
            confidence = vehicle_conf * 0.4
            if is_wrong_direction:
                confidence = min(vehicle_conf * 0.8, 0.9)
            
            is_violation = is_wrong_direction
            
            return {
                'violation_type': 'wrong_way',
                'violation_type_cn': VIOLATION_TYPE_CN['wrong_way'],
                'confidence': round(confidence, 4),
                'is_violation': is_violation,
                'evidence': {
                    'vehicle_count': vehicle_count,
                    'vehicle_confidence': vehicle_conf,
                    'road_direction': road_direction,
                    'vehicle_direction': vehicle_direction,
                    'is_wrong_direction': is_wrong_direction,
                    'tracking_error': str(e)
                },
                'location': self._extract_location(detections),
                'timestamp': datetime.now().isoformat(),
                'message': f'检测到 {vehicle_count} 辆车辆{"，疑似逆行" if is_wrong_direction else ""}'
            }

    def _check_speeding(self, detections: List[Dict], scene_config: Optional[Dict] = None) -> Dict:
        """
        检查超速
        
        判断规则: 车辆行驶速度超过限速
        """
        threshold = self._get_config_value('confidence_threshold', 0.5)
        
        vehicle_count = self._count_detections(detections, VEHICLE_CLASSES, threshold)
        
        if vehicle_count > 0:
            vehicle_conf = self._get_max_confidence_for_classes(detections, VEHICLE_CLASSES)
            
            speed_limit = scene_config.get('speed_limit', 0) if scene_config else 0
            vehicle_speed = scene_config.get('vehicle_speed', 0) if scene_config else 0
            is_speeding = speed_limit > 0 and vehicle_speed > speed_limit
            
            confidence = vehicle_conf * 0.3
            if is_speeding:
                excess_ratio = (vehicle_speed - speed_limit) / speed_limit
                confidence = min(vehicle_conf * (0.5 + excess_ratio), 0.95)
            
            is_violation = is_speeding
            
            return {
                'violation_type': 'speeding',
                'violation_type_cn': VIOLATION_TYPE_CN['speeding'],
                'confidence': round(confidence, 4),
                'is_violation': is_violation,
                'evidence': {
                    'vehicle_count': vehicle_count,
                    'vehicle_confidence': vehicle_conf,
                    'speed_limit': speed_limit,
                    'vehicle_speed': vehicle_speed,
                    'is_speeding': is_speeding
                },
                'location': self._extract_location(detections),
                'timestamp': datetime.now().isoformat(),
                'message': f'检测到 {vehicle_count} 辆车辆{"，疑似超速" if is_speeding else "，超速判断需测速设备"}'
            }
        
        return {
            'violation_type': 'speeding',
            'violation_type_cn': VIOLATION_TYPE_CN['speeding'],
            'confidence': 0.0,
            'is_violation': False,
            'evidence': {},
            'location': None,
            'timestamp': datetime.now().isoformat(),
            'message': '未检测到超速'
        }

    def _extract_location(self, detections: List[Dict]) -> Optional[Dict]:
        """从检测结果中提取位置信息"""
        if not detections:
            return None
        
        vehicle_dets = [d for d in detections if d.get('class_name') in VEHICLE_CLASSES]
        if vehicle_dets:
            bbox = vehicle_dets[0].get('bbox', [])
            if len(bbox) == 4:
                return {
                    'bbox': bbox,
                    'center_x': (bbox[0] + bbox[2]) / 2,
                    'center_y': (bbox[1] + bbox[3]) / 2
                }
        
        return None

    def detect_violations(self, detections: List[Dict], scene_config: Optional[Dict] = None,
                          violation_type: Optional[str] = None) -> Dict:
        """
        检测违规行为
        
        参数:
            detections: 检测结果列表，每个元素包含 class_name, confidence, bbox 等
            scene_config: 场景配置，包含道路方向、禁停区域、限速等信息
            violation_type: 指定检查的违规类型，若为None则检查所有类型
        
        返回:
            结构化违规列表，含违规类型、置信度、位置、时间
        """
        if not detections:
            return {
                'success': True,
                'violations': [],
                'detection_summary': {'total_detections': 0, 'classes': []},
                'message': '无检测结果'
            }
        
        detection_classes = self._get_detection_classes(detections)
        detection_summary = {
            'total_detections': len(detections),
            'classes': list(detection_classes),
            'vehicle_count': self._count_detections(detections, VEHICLE_CLASSES),
            'helmet_count': self._count_detections(detections, HELMET_CLASSES),
            'person_count': self._count_detections(detections, PERSON_CLASSES),
            'traffic_signal_count': self._count_detections(detections, TRAFFIC_SIGNAL_CLASSES)
        }
        
        violations = []
        
        if violation_type:
            if violation_type in self.rules:
                result = self.rules[violation_type](detections, scene_config)
                if result['is_violation']:
                    violations.append(result)
            else:
                return {
                    'success': False,
                    'violations': [],
                    'detection_summary': detection_summary,
                    'message': f'未知违规类型: {violation_type}'
                }
        else:
            for vio_type, checker in self.rules.items():
                result = checker(detections, scene_config)
                if result['is_violation']:
                    violations.append(result)

        # 统一回填 vehicle_id（2026-10-03 由 DSH 新增）
        # 背景：规则引擎产生的违规原本**不带车辆 ID**，前端无法把违规与追踪
        # 车辆对应（"违规车辆"栏永远空）。检测框在追踪后已被回填 track_id
        # （见 realtime_detector._attach_track_ids），这里把该 ID 传进违规。
        try:
            self._attach_vehicle_ids(violations, detections)
        except Exception:
            pass

        return {
            'success': True,
            'violations': violations,
            'detection_summary': detection_summary,
            'message': f'规则引擎检查完成，检测到 {len(violations)} 个违规'
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _attach_vehicle_ids(violations: List[Dict], detections: List[Dict]):
        """给违规补充 vehicle_id / track_id（就近归属到车辆检测框）

        归属优先级：
          ① 违规自身已带 vehicle_id/track_id（如行为引擎产出）-> 保留
          ② 违规 evidence 里的 bbox 与车辆检测框做 IoU
          ③ 违规 location 点落在车辆框内
          ④ 退化：全场仅一辆车 -> 直接归属
        """
        if not violations or not detections:
            return
        vehs = []
        for d in detections:
            if d.get('class_name') not in VEHICLE_CLASSES:
                continue
            tid = d.get('track_id', d.get('vehicle_id'))
            bb = d.get('bbox') or []
            if tid is None or len(bb) < 4:
                continue
            try:
                vehs.append((int(tid), [float(v) for v in bb[:4]]))
            except (TypeError, ValueError):
                continue
        if not vehs:
            return
        _valid = {tid for tid, _t in vehs}

        for v in violations:
            # 2026-10-03 由 DSH 修正：已带 ID 也要校验是否**仍在当前车辆集合**，
            # 否则会保留失效旧 ID（实测行为引擎给的是上一批 track id，
            # 导致违规永远挂不到当前车辆上）。失效则重新做几何归属。
            _existing = v.get('vehicle_id', v.get('track_id'))
            if _existing is not None:
                try:
                    if int(_existing) in _valid:
                        continue
                except (TypeError, ValueError):
                    pass
                v.pop('vehicle_id', None)
                v.pop('track_id', None)
            assigned = None
            # ② evidence bbox IoU
            for src in (v.get('evidence') or {}, v):
                if not isinstance(src, dict):
                    continue
                bb = src.get('bbox') or src.get('target_bbox') or src.get('vehicle_bbox')
                if isinstance(bb, (list, tuple)) and len(bb) >= 4:
                    try:
                        ax1, ay1, ax2, ay2 = [float(x) for x in bb[:4]]
                    except (TypeError, ValueError):
                        continue
                    a_area = max(1.0, (ax2 - ax1) * (ay2 - ay1))
                    best, best_iou = None, 0.0
                    for tid, t in vehs:
                        ix1, iy1 = max(ax1, t[0]), max(ay1, t[1])
                        ix2, iy2 = min(ax2, t[2]), min(ay2, t[3])
                        if ix2 <= ix1 or iy2 <= iy1:
                            continue
                        inter = (ix2 - ix1) * (iy2 - iy1)
                        b_area = max(1.0, (t[2] - t[0]) * (t[3] - t[1]))
                        iou = inter / (a_area + b_area - inter)
                        if iou > best_iou:
                            best, best_iou = tid, iou
                    if best is not None and best_iou >= 0.2:
                        assigned = best
                        break
            # ③ location 点包含（兼容 {'x','y'} 与 {'bbox','center_x','center_y'}）
            if assigned is None:
                loc = v.get('location')
                if isinstance(loc, dict):
                    px = py = None
                    for kx, ky in (('x', 'y'), ('center_x', 'center_y'), ('cx', 'cy')):
                        try:
                            if loc.get(kx) is not None and loc.get(ky) is not None:
                                px, py = float(loc[kx]), float(loc[ky])
                                break
                        except (TypeError, ValueError):
                            continue
                    if px is None:
                        bb = loc.get('bbox') or loc.get('target_bbox')
                        if isinstance(bb, (list, tuple)) and len(bb) >= 4:
                            try:
                                px = (float(bb[0]) + float(bb[2])) / 2.0
                                py = (float(bb[1]) + float(bb[3])) / 2.0
                            except (TypeError, ValueError):
                                px = None
                    if px is not None:
                        for tid, t in vehs:
                            if t[0] <= px <= t[2] and t[1] <= py <= t[3]:
                                assigned = tid
                                break
            # ④ 不再"全场仅一辆车就归给它"（2026-10-03 由 DSH 修正）
            # 原因：这会把"没有几何依据"的违规硬塞给唯一在场的车辆。
            # 实测后果：红灯违规被归属到画面中央的卡车（它并未闯红灯），
            # 正是"框在空地上/归属错误"的来源。无匹配宁可**留空**
            # （前端会把它显示为"未归属告警"），也不编造归属。
            if assigned is not None:
                v['vehicle_id'] = assigned
                v['track_id'] = assigned
                # 同步更新 evidence 内的旧 ID（2026-10-03 由 DSH 修正）
                # 否则路由层递归提取时会优先拿到 evidence 里的**失效旧 ID**，
                # 把刚修好的归属又覆盖掉。
                ev = v.get('evidence')
                if isinstance(ev, dict):
                    for val in ev.values():
                        if isinstance(val, list):
                            for item in val:
                                if isinstance(item, dict):
                                    for k in ('vehicle_id', 'track_id'):
                                        if item.get(k) is not None:
                                            try:
                                                item[k] = assigned
                                            except Exception:
                                                pass

    def get_violation_types(self) -> List[Dict]:
        """获取所有支持的违规类型"""
        return [
            {'type': k, 'name': VIOLATION_TYPE_CN[k], 'description': self._get_description(k)}
            for k in self.rules
        ]

    def _get_description(self, violation_type: str) -> str:
        """获取违规类型描述"""
        descriptions = {
            'no_helmet': '驾驶或乘坐摩托车/电动车未佩戴安全头盔',
            'red_light': '红灯时车辆越过停止线',
            'illegal_parking': '车辆在禁止停车区域停留超过规定时间',
            'lane_departure': '车辆骑轧车道分界线行驶',
            'wrong_way': '车辆行驶方向与道路方向相反',
            'speeding': '车辆行驶速度超过限速'
        }
        return descriptions.get(violation_type, '')


def check_violations(detections: List[Dict], violation_type: Optional[str] = None,
                     scene_config: Optional[Dict] = None) -> Dict:
    """
    兼容旧接口的违规检查函数
    
    参数:
        detections: 检测结果列表
        violation_type: 违规类型
        scene_config: 场景配置
    
    返回:
        违规检查结果
    """
    engine = ViolationRuleEngine()
    return engine.detect_violations(detections, scene_config, violation_type)


if __name__ == "__main__":
    test_detections = [
        {'class_name': 'motorcycle', 'class_name_cn': '摩托车', 'confidence': 0.85, 'bbox': [100, 200, 300, 400]},
        {'class_name': 'person', 'class_name_cn': '行人', 'confidence': 0.78, 'bbox': [150, 180, 280, 380]},
        {'class_name': 'car', 'class_name_cn': '轿车', 'confidence': 0.92, 'bbox': [400, 250, 600, 450]},
        {'class_name': 'traffic light', 'class_name_cn': '红绿灯', 'confidence': 0.65, 'bbox': [500, 50, 550, 150]}
    ]
    
    test_scene_config = {
        'is_no_parking_zone': True,
        'park_duration_seconds': 600,
        'road_direction': 'east',
        'vehicle_direction': 'west',
        'speed_limit': 60,
        'vehicle_speed': 80
    }
    
    print("=== ViolationRuleEngine 测试 ===")
    
    engine = ViolationRuleEngine()
    
    print("\n1. 检查未戴头盔（无头盔检测）")
    result = engine.detect_violations(test_detections, test_scene_config, 'no_helmet')
    print(f"   检测到违规: {len(result['violations'])}")
    for v in result['violations']:
        print(f"   - {v['violation_type_cn']}: 置信度 {v['confidence']}")
    
    print("\n2. 检查违规停车（禁停区域+超时）")
    result = engine.detect_violations(test_detections, test_scene_config, 'illegal_parking')
    print(f"   检测到违规: {len(result['violations'])}")
    for v in result['violations']:
        print(f"   - {v['violation_type_cn']}: 置信度 {v['confidence']}")
    
    print("\n3. 检查所有违规类型")
    result = engine.detect_violations(test_detections, test_scene_config)
    print(f"   检测到违规: {len(result['violations'])}")
    for v in result['violations']:
        print(f"   - {v['violation_type_cn']}: 置信度 {v['confidence']}")
    
    print("\n4. 检测摘要")
    print(f"   总检测数: {result['detection_summary']['total_detections']}")
    print(f"   类别: {result['detection_summary']['classes']}")
    print(f"   车辆数: {result['detection_summary']['vehicle_count']}")
    
    print("\n5. 支持的违规类型")
    for vt in engine.get_violation_types():
        print(f"   - {vt['type']}: {vt['name']}")