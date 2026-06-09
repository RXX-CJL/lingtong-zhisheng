from typing import Dict, List, Optional
from datetime import datetime, timedelta
from config import Config
from violation_detector import Violation

class WarningLevel:
    LIGHT = 1
    FORMAL = 2
    SEVERE = 3

class VehicleViolationRecord:
    def __init__(self, track_id: int):
        self.track_id = track_id
        self.violations: List[Violation] = []
        self.last_warning_time = None
        self.current_level = WarningLevel.LIGHT
    
    @property
    def violation_count(self) -> int:
        return len(self.violations)
    
    def add_violation(self, violation: Violation):
        self.violations.append(violation)
        self.current_level = self._calculate_level()
    
    def _calculate_level(self) -> int:
        count = self.violation_count
        if count >= Config.VIOLATION_THRESHOLD_2:
            return WarningLevel.SEVERE
        elif count >= Config.VIOLATION_THRESHOLD_1:
            return WarningLevel.FORMAL
        return WarningLevel.LIGHT
    
    def should_warn(self) -> bool:
        if not self.violations:
            return False
        
        if self.last_warning_time is None:
            return True
        
        time_since_last_warning = datetime.now() - self.last_warning_time
        min_interval = timedelta(seconds=5)
        
        return time_since_last_warning >= min_interval
    
    def get_warning_message(self) -> str:
        level = self.current_level
        violation_type = self.violations[-1].violation_type if self.violations else ""
        count = self.violation_count
        
        messages = {
            WarningLevel.LIGHT: {
                'red_light': f'温馨提示：检测到闯红灯行为，请遵守交通规则',
                'no_helmet': f'温馨提示：检测到未佩戴头盔，请佩戴安全头盔',
                'wrong_way': f'温馨提示：检测到逆行行为，请按规定方向行驶',
                'illegal_parking': f'温馨提示：检测到违规停车，请驶离禁停区域',
                'lane_departure': f'温馨提示：检测到压线行为，请保持在车道内行驶',
                'speeding': f'温馨提示：检测到超速行为，请减速慢行',
                'default': f'温馨提示：检测到交通违规行为'
            },
            WarningLevel.FORMAL: {
                'red_light': f'警告！已累计 {count} 次闯红灯行为，请注意安全驾驶',
                'no_helmet': f'警告！已累计 {count} 次未佩戴头盔，请立即佩戴',
                'wrong_way': f'警告！已累计 {count} 次逆行行为，严重违反交通规则',
                'illegal_parking': f'警告！已累计 {count} 次违规停车，将进行处罚',
                'lane_departure': f'警告！已累计 {count} 次压线行为，请规范驾驶',
                'speeding': f'警告！已累计 {count} 次超速行为，危险驾驶',
                'default': f'警告！已累计 {count} 次违规行为'
            },
            WarningLevel.SEVERE: {
                'red_light': f'严重警告！已累计 {count} 次闯红灯，将采取强制措施，请立即停车接受检查',
                'no_helmet': f'严重警告！已累计 {count} 次未佩戴头盔，将依法处罚，请立即佩戴',
                'wrong_way': f'严重警告！已累计 {count} 次逆行，严重危险，立即纠正方向',
                'illegal_parking': f'严重警告！已累计 {count} 次违规停车，拖车处理，请立即驶离',
                'lane_departure': f'严重警告！已累计 {count} 次压线，涉嫌危险驾驶，请规范行驶',
                'speeding': f'严重警告！已累计 {count} 次超速，严重危险驾驶，请立即减速',
                'default': f'严重警告！已累计 {count} 次违规，将采取限制措施'
            }
        }
        
        return messages[level].get(violation_type, messages[level]['default'])
    
    def get_correction_guide(self) -> Optional[str]:
        if self.current_level < WarningLevel.SEVERE:
            return None
        
        violation_type = self.violations[-1].violation_type if self.violations else ""
        
        guides = {
            'red_light': '整改指引：请在停止线前停车等待，遵守红绿灯信号指示',
            'no_helmet': '整改指引：请立即佩戴安全头盔，确保骑行安全',
            'wrong_way': '整改指引：请立即掉头或靠边停车，按正确方向行驶',
            'illegal_parking': '整改指引：请立即驶离禁停区域，到指定停车场停车',
            'lane_departure': '整改指引：请保持车辆在车道内行驶，避免压线和变道',
            'speeding': '整改指引：请立即减速至规定速度，安全驾驶',
            'default': '整改指引：请遵守交通规则，文明驾驶'
        }
        
        return guides.get(violation_type, guides['default'])

class WarningManager:
    def __init__(self):
        self.records: Dict[int, VehicleViolationRecord] = {}
    
    def add_violation(self, violation: Violation) -> Optional[VehicleViolationRecord]:
        track_id = violation.track_id
        
        if track_id not in self.records:
            self.records[track_id] = VehicleViolationRecord(track_id)
        
        record = self.records[track_id]
        record.add_violation(violation)
        
        return record
    
    def get_record(self, track_id: int) -> Optional[VehicleViolationRecord]:
        return self.records.get(track_id)
    
    def get_all_records(self) -> List[VehicleViolationRecord]:
        return list(self.records.values())
    
    def has_severe_violations(self) -> bool:
        return any(record.current_level >= WarningLevel.SEVERE for record in self.records.values())
    
    def reset_record(self, track_id: int):
        if track_id in self.records:
            del self.records[track_id]
    
    def reset_all_records(self):
        self.records.clear()
    
    def cleanup_old_records(self, hours: int = 24):
        cutoff_time = datetime.now() - timedelta(hours=hours)
        old_ids = [
            track_id for track_id, record in self.records.items()
            if record.violations and record.violations[-1].timestamp < cutoff_time.timestamp()
        ]
        for track_id in old_ids:
            del self.records[track_id]
