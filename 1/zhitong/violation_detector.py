import numpy as np
import cv2
from typing import List, Dict, Tuple
from config import Config
from tracker import TrackedObject
from language import Translation

class ViolationType:
    RED_LIGHT = "red_light"
    NO_HELMET = "no_helmet"
    WRONG_WAY = "wrong_way"
    ILLEGAL_PARKING = "illegal_parking"
    LANE_DEPARTURE = "lane_departure"
    SPEEDING = "speeding"

class Violation:
    def __init__(self, violation_type: str, track_id: int, frame: np.ndarray, 
                 confidence: float, position: Tuple[int, int, int, int], timestamp: float,
                 additional_info: dict = None):
        self.violation_type = violation_type
        self.track_id = track_id
        self.frame = frame.copy()
        self.confidence = confidence
        self.position = position
        self.timestamp = timestamp
        self.additional_info = additional_info if additional_info else {}
        self.evidence_saved = False
        self.cloud_validated = False
    
    def to_dict(self):
        return {
            'type': self.violation_type,
            'track_id': self.track_id,
            'confidence': self.confidence,
            'position': self.position,
            'timestamp': self.timestamp,
            'additional_info': self.additional_info
        }

class ConfidenceEvaluator:
    def __init__(self, config: Config):
        self.config = config
        self.violation_history = {}
    
    def calculate_combined_confidence(self, detection_conf: float, 
                                      track_stability: float, 
                                      environment_fitness: float) -> float:
        weights = [0.5, 0.3, 0.2]
        total_confidence = (
            weights[0] * detection_conf +
            weights[1] * track_stability +
            weights[2] * environment_fitness
        )
        return np.clip(total_confidence, 0, 1)
    
    def get_response_level(self, confidence: float) -> str:
        if confidence >= self.config.CONFIDENCE_THRESHOLD_HIGH:
            return "high"
        elif confidence >= self.config.CONFIDENCE_THRESHOLD_LOW:
            return "medium"
        return "low"
    
    def should_send_to_cloud(self, confidence: float) -> bool:
        return (self.config.USE_CLOUD_VALIDATION and 
                confidence >= self.config.CONFIDENCE_THRESHOLD_LOW and 
                confidence < self.config.CONFIDENCE_THRESHOLD_HIGH)

class LaneDetector:
    def __init__(self):
        self.lane_lines = []
        self.region_of_interest = None
    
    def set_roi(self, roi_points):
        self.region_of_interest = np.array(roi_points, np.int32)
    
    def detect_lane_lines(self, frame):
        if frame is None:
            return []
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        
        if self.region_of_interest is not None:
            mask = np.zeros_like(edges)
            cv2.fillPoly(mask, [self.region_of_interest], 255)
            edges = cv2.bitwise_and(edges, edges, mask=mask)
        
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                               minLineLength=100, maxLineGap=50)
        
        self.lane_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                slope = (y2 - y1) / (x2 - x1 + 1e-6)
                if abs(slope) < 0.3 or abs(slope) > 3:
                    continue
                
                self.lane_lines.append({
                    'start': (x1, y1),
                    'end': (x2, y2),
                    'slope': slope,
                    'center': ((x1 + x2) / 2, (y1 + y2) / 2)
                })
        
        return self.lane_lines
    
    def draw_lane_lines(self, frame):
        result = frame.copy()
        for line in self.lane_lines:
            cv2.line(result, line['start'], line['end'], (0, 255, 0), 2)
        return result

class SpeedEstimator:
    def __init__(self, config: Config):
        self.config = config
        self.pixel_to_meter = 0.05
        self.fps = config.VIDEO_FPS
        self.track_speeds = {}
        self.track_positions = {}
    
    def update(self, track_id, bbox, timestamp):
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        
        if track_id not in self.track_positions:
            self.track_positions[track_id] = []
        
        self.track_positions[track_id].append((timestamp, center_x, center_y))
        
        if len(self.track_positions[track_id]) > 30:
            self.track_positions[track_id].pop(0)
    
    def calculate_speed(self, track_id):
        if track_id not in self.track_positions:
            return 0.0
        
        positions = self.track_positions[track_id]
        if len(positions) < 10:
            return 0.0
        
        recent = positions[-10:]
        time_diff = recent[-1][0] - recent[0][0]
        if time_diff < 0.1:
            return 0.0
        
        pixel_distance = 0
        for i in range(1, len(recent)):
            dx = recent[i][1] - recent[i-1][1]
            dy = recent[i][2] - recent[i-1][2]
            pixel_distance += np.sqrt(dx**2 + dy**2)
        
        avg_pixel_per_second = pixel_distance / time_diff
        speed_m_per_s = avg_pixel_per_second * self.pixel_to_meter
        speed_km_per_h = speed_m_per_s * 3.6
        
        return speed_km_per_h
    
    def get_speed(self, track_id):
        return self.track_speeds.get(track_id, 0.0)

class ViolationDetector:
    def __init__(self, config: Config):
        self.config = config
        self.confidence_evaluator = ConfidenceEvaluator(config)
        self.lane_detector = LaneDetector()
        self.speed_estimator = SpeedEstimator(config)
        
        self.violation_frames = {}
        self.track_positions = {}
        self.stop_line = None
        self.lane_direction = None
        self.parking_zones = []
        self.speed_zones = []
        
        self.light_state = "unknown"
        self.last_light_update = 0
    
    def set_stop_line(self, points: List[Tuple[int, int]]):
        self.stop_line = np.array(points, np.int32)
    
    def set_parking_zones(self, zones: List[List[Tuple[int, int]]]):
        self.parking_zones = [np.array(zone, np.int32) for zone in zones]
    
    def set_speed_zones(self, zones: List[dict]):
        self.speed_zones = zones
    
    def detect_traffic_light(self, frame: np.ndarray, detections: List[Dict]) -> str:
        for det in detections:
            if det['class_name'] == 'traffic light':
                x1, y1, x2, y2 = map(int, det['bbox'])
                roi = frame[y1:y2, x1:x2]
                if roi.size == 0:
                    continue
                
                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                
                red_lower1 = np.array([0, 120, 70])
                red_upper1 = np.array([10, 255, 255])
                red_lower2 = np.array([170, 120, 70])
                red_upper2 = np.array([180, 255, 255])
                
                green_lower = np.array([35, 120, 70])
                green_upper = np.array([85, 255, 255])
                
                mask_red1 = cv2.inRange(hsv, red_lower1, red_upper1)
                mask_red2 = cv2.inRange(hsv, red_lower2, red_upper2)
                mask_red = cv2.bitwise_or(mask_red1, mask_red2)
                mask_green = cv2.inRange(hsv, green_lower, green_upper)
                
                red_pixels = cv2.countNonZero(mask_red)
                green_pixels = cv2.countNonZero(mask_green)
                
                if red_pixels > green_pixels and red_pixels > 50:
                    return "red"
                elif green_pixels > red_pixels and green_pixels > 50:
                    return "green"
        
        return "unknown"
    
    def detect_red_light_violation(self, tracked_objects: List[TrackedObject], 
                                  frame: np.ndarray, current_time: float) -> List[Violation]:
        violations = []
        
        self.light_state = self.detect_traffic_light(frame, [])
        
        if self.light_state != "red":
            return violations
        
        for obj in tracked_objects:
            if obj.class_name not in ['car', 'truck', 'bus', 'motorcycle', 'bicycle']:
                continue
            
            center_x = (obj.bbox[0] + obj.bbox[2]) / 2
            center_y = (obj.bbox[1] + obj.bbox[3]) / 2
            
            if self.stop_line is not None:
                if self._point_passed_line((center_x, center_y), self.stop_line):
                    track_id = obj.track_id
                    if track_id not in self.violation_frames:
                        self.violation_frames[track_id] = {'type': ViolationType.RED_LIGHT, 'count': 0}
                    self.violation_frames[track_id]['count'] += 1
                    
                    if self.violation_frames[track_id]['count'] >= self.config.VIOLATION_FRAMES_THRESHOLD:
                        combined_confidence = self.confidence_evaluator.calculate_combined_confidence(
                            detection_conf=obj.confidence,
                            track_stability=1.0 - obj.frames_since_update / self.config.MAX_AGE,
                            environment_fitness=0.8
                        )
                        
                        violation = Violation(
                            violation_type=ViolationType.RED_LIGHT,
                            track_id=track_id,
                            frame=frame,
                            confidence=combined_confidence,
                            position=tuple(map(int, obj.bbox)),
                            timestamp=current_time
                        )
                        violations.append(violation)
        
        return violations
    
    def detect_no_helmet(self, tracked_objects: List[TrackedObject], 
                        frame: np.ndarray, current_time: float) -> List[Violation]:
        violations = []
        
        for obj in tracked_objects:
            if obj.class_name not in ['person', 'bicycle', 'motorcycle']:
                continue
            
            if obj.confidence < 0.6:
                continue
            
            track_id = obj.track_id
            if track_id not in self.violation_frames:
                self.violation_frames[track_id] = {'type': ViolationType.NO_HELMET, 'count': 0}
            self.violation_frames[track_id]['count'] += 1
            
            if self.violation_frames[track_id]['count'] >= self.config.VIOLATION_FRAMES_THRESHOLD:
                combined_confidence = self.confidence_evaluator.calculate_combined_confidence(
                    detection_conf=obj.confidence,
                    track_stability=1.0 - obj.frames_since_update / self.config.MAX_AGE,
                    environment_fitness=0.7
                )
                
                violation = Violation(
                    violation_type=ViolationType.NO_HELMET,
                    track_id=track_id,
                    frame=frame,
                    confidence=combined_confidence,
                    position=tuple(map(int, obj.bbox)),
                    timestamp=current_time
                )
                violations.append(violation)
        
        return violations
    
    def detect_wrong_way(self, tracked_objects: List[TrackedObject], 
                        frame: np.ndarray, current_time: float) -> List[Violation]:
        violations = []
        
        for obj in tracked_objects:
            if obj.class_name not in ['car', 'truck', 'bus', 'motorcycle', 'bicycle']:
                continue
            
            track_id = obj.track_id
            if track_id not in self.track_positions:
                self.track_positions[track_id] = []
            self.track_positions[track_id].append((obj.bbox[0], obj.bbox[1]))
            
            if len(self.track_positions[track_id]) < 10:
                continue
            
            positions = self.track_positions[track_id][-10:]
            movement_x = positions[-1][0] - positions[0][0]
            
            if abs(movement_x) < 20:
                continue
            
            moving_right = movement_x > 0
            
            if (self.lane_direction == "right" and not moving_right) or \
               (self.lane_direction == "left" and moving_right):
                
                combined_confidence = self.confidence_evaluator.calculate_combined_confidence(
                    detection_conf=obj.confidence,
                    track_stability=1.0 - obj.frames_since_update / self.config.MAX_AGE,
                    environment_fitness=0.6
                )
                
                violation = Violation(
                    violation_type=ViolationType.WRONG_WAY,
                    track_id=track_id,
                    frame=frame,
                    confidence=combined_confidence,
                    position=tuple(map(int, obj.bbox)),
                    timestamp=current_time
                )
                violations.append(violation)
        
        return violations
    
    def detect_illegal_parking(self, tracked_objects: List[TrackedObject], 
                              frame: np.ndarray, current_time: float) -> List[Violation]:
        violations = []
        
        for obj in tracked_objects:
            if obj.class_name not in ['car', 'truck', 'bus', 'motorcycle']:
                continue
            
            track_id = obj.track_id
            if track_id not in self.track_positions:
                self.track_positions[track_id] = []
            self.track_positions[track_id].append((obj.bbox[0], obj.bbox[1]))
            
            if len(self.track_positions[track_id]) < 30:
                continue
            
            recent_positions = self.track_positions[track_id][-30:]
            movement = np.sqrt(
                (recent_positions[-1][0] - recent_positions[0][0]) ** 2 + 
                (recent_positions[-1][1] - recent_positions[0][1]) ** 2
            )
            
            if movement < 30:
                center_x = (obj.bbox[0] + obj.bbox[2]) / 2
                center_y = (obj.bbox[1] + obj.bbox[3]) / 2
                
                in_parking_zone = False
                for zone in self.parking_zones:
                    if cv2.pointPolygonTest(zone, (center_x, center_y), False) > 0:
                        in_parking_zone = True
                        break
                
                if in_parking_zone:
                    combined_confidence = self.confidence_evaluator.calculate_combined_confidence(
                        detection_conf=obj.confidence,
                        track_stability=1.0 - obj.frames_since_update / self.config.MAX_AGE,
                        environment_fitness=0.9
                    )
                    
                    violation = Violation(
                        violation_type=ViolationType.ILLEGAL_PARKING,
                        track_id=track_id,
                        frame=frame,
                        confidence=combined_confidence,
                        position=tuple(map(int, obj.bbox)),
                        timestamp=current_time
                    )
                    violations.append(violation)
        
        return violations
    
    def detect_lane_departure(self, tracked_objects: List[TrackedObject], 
                             frame: np.ndarray, current_time: float) -> List[Violation]:
        violations = []
        
        self.lane_detector.detect_lane_lines(frame)
        lane_lines = self.lane_detector.lane_lines
        
        if not lane_lines:
            return violations
        
        for obj in tracked_objects:
            if obj.class_name not in ['car', 'truck', 'bus', 'motorcycle']:
                continue
            
            x1, y1, x2, y2 = obj.bbox
            vehicle_width = x2 - x1
            
            vehicle_left_edge = x1
            vehicle_right_edge = x2
            
            has_crossed_line = False
            for line in lane_lines:
                line_x1, line_y1 = line['start']
                line_x2, line_y2 = line['end']
                
                if y1 < line_y1 or y2 > line_y2:
                    continue
                
                line_at_vehicle_y = line_x1 + (line_x2 - line_x1) * (y1 - line_y1) / (line_y2 - line_y1 + 1e-6)
                
                dist_to_left = abs(line_at_vehicle_y - vehicle_left_edge)
                dist_to_right = abs(line_at_vehicle_y - vehicle_right_edge)
                
                if dist_to_left < 15 or dist_to_right < 15:
                    has_crossed_line = True
                    break
            
            if has_crossed_line:
                track_id = obj.track_id
                if track_id not in self.violation_frames:
                    self.violation_frames[track_id] = {'type': ViolationType.LANE_DEPARTURE, 'count': 0}
                self.violation_frames[track_id]['count'] += 1
                
                if self.violation_frames[track_id]['count'] >= self.config.VIOLATION_FRAMES_THRESHOLD:
                    combined_confidence = self.confidence_evaluator.calculate_combined_confidence(
                        detection_conf=obj.confidence,
                        track_stability=1.0 - obj.frames_since_update / self.config.MAX_AGE,
                        environment_fitness=0.75
                    )
                    
                    violation = Violation(
                        violation_type=ViolationType.LANE_DEPARTURE,
                        track_id=track_id,
                        frame=frame,
                        confidence=combined_confidence,
                        position=tuple(map(int, obj.bbox)),
                        timestamp=current_time,
                        additional_info={'lane_lines_detected': len(lane_lines)}
                    )
                    violations.append(violation)
        
        return violations
    
    def detect_speeding(self, tracked_objects: List[TrackedObject], 
                       frame: np.ndarray, current_time: float) -> List[Violation]:
        violations = []
        
        for obj in tracked_objects:
            if obj.class_name not in ['car', 'truck', 'bus', 'motorcycle']:
                continue
            
            track_id = obj.track_id
            self.speed_estimator.update(track_id, obj.bbox, current_time)
            speed = self.speed_estimator.calculate_speed(track_id)
            
            if speed < 5:
                continue
            
            speed_limit = 60
            for zone in self.speed_zones:
                if zone.get('active', True):
                    speed_limit = zone.get('limit', 60)
                    break
            
            if speed > speed_limit * 1.1:
                track_id = obj.track_id
                if track_id not in self.violation_frames:
                    self.violation_frames[track_id] = {'type': ViolationType.SPEEDING, 'count': 0}
                self.violation_frames[track_id]['count'] += 1
                
                if self.violation_frames[track_id]['count'] >= self.config.VIOLATION_FRAMES_THRESHOLD:
                    combined_confidence = self.confidence_evaluator.calculate_combined_confidence(
                        detection_conf=obj.confidence,
                        track_stability=1.0 - obj.frames_since_update / self.config.MAX_AGE,
                        environment_fitness=0.7
                    )
                    
                    violation = Violation(
                        violation_type=ViolationType.SPEEDING,
                        track_id=track_id,
                        frame=frame,
                        confidence=combined_confidence,
                        position=tuple(map(int, obj.bbox)),
                        timestamp=current_time,
                        additional_info={'speed': speed, 'speed_limit': speed_limit}
                    )
                    violations.append(violation)
        
        return violations
    
    def detect_all(self, frame: np.ndarray, detections: List[Dict], 
                  tracked_objects: List[TrackedObject], current_time: float) -> List[Violation]:
        all_violations = []
        
        all_violations.extend(self.detect_red_light_violation(tracked_objects, frame, current_time))
        all_violations.extend(self.detect_no_helmet(tracked_objects, frame, current_time))
        all_violations.extend(self.detect_wrong_way(tracked_objects, frame, current_time))
        all_violations.extend(self.detect_illegal_parking(tracked_objects, frame, current_time))
        all_violations.extend(self.detect_lane_departure(tracked_objects, frame, current_time))
        all_violations.extend(self.detect_speeding(tracked_objects, frame, current_time))
        
        return all_violations
    
    def _point_passed_line(self, point: Tuple[float, float], line: np.ndarray) -> bool:
        if len(line) < 2:
            return False
        
        line_start = line[0]
        line_end = line[-1]
        
        line_vec = np.array([line_end[0] - line_start[0], line_end[1] - line_start[1]])
        point_vec = np.array([point[0] - line_start[0], point[1] - line_start[1]])
        
        cross = np.cross(line_vec, point_vec)
        return cross > 0
    
    def draw_violations(self, frame: np.ndarray, violations: List[Violation]) -> np.ndarray:
        for vio in violations:
            x1, y1, x2, y2 = vio.position
            color = (0, 0, 255)
            
            if vio.violation_type == ViolationType.LANE_DEPARTURE:
                color = (0, 255, 255)
            elif vio.violation_type == ViolationType.SPEEDING:
                color = (255, 0, 255)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
            
            vio_type_cn = Translation.translate_violation(vio.violation_type)
            label = f"{vio_type_cn} ID:{vio.track_id} {vio.confidence:.2f}"
            cv2.putText(frame, label, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return frame
    
    def draw_lane_lines(self, frame: np.ndarray) -> np.ndarray:
        return self.lane_detector.draw_lane_lines(frame)
