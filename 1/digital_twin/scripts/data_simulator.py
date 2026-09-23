# -*- coding: utf-8 -*-
"""
数据模拟器 - 生成模拟交通数据和违规检测数据
"""
import json
import time
import random
import threading
from datetime import datetime
from typing import Dict, List

class TrafficDataSimulator:
    def __init__(self):
        self.vehicles = {}
        self.violations = []
        self.vehicle_id_counter = 0
        self.running = False
        self.update_interval = 0.5
        self.roads = [
            {'name': 'north', 'start': (0, -45), 'end': (0, 45), 'direction': (0, 1)},
            {'name': 'south', 'start': (0, 45), 'end': (0, -45), 'direction': (0, -1)},
            {'name': 'east', 'start': (-45, 0), 'end': (45, 0), 'direction': (1, 0)},
            {'name': 'west', 'start': (45, 0), 'end': (-45, 0), 'direction': (-1, 0)}
        ]
        self.traffic_light_state = 'red'
        self.traffic_light_timer = 0
        
    def generate_vehicle_id(self) -> str:
        self.vehicle_id_counter += 1
        return f'VEH{self.vehicle_id_counter:06d}'
    
    def generate_vehicle(self) -> Dict:
        road = random.choice(self.roads)
        x, z = road['start']
        dx, dz = road['direction']
        
        vehicle_types = ['car', 'motorcycle', 'truck']
        weights = [0.6, 0.3, 0.1]
        vehicle_type = random.choices(vehicle_types, weights=weights)[0]
        
        speed = random.uniform(20, 60)
        violation_probability = 0.15
        
        violation_type = None
        if random.random() < violation_probability:
            violations = ['red_light', 'no_helmet', 'speeding', 'illegal_parking']
            violation_type = random.choice(violations)
            if violation_type == 'speeding':
                speed = random.uniform(70, 100)
        
        return {
            'id': self.generate_vehicle_id(),
            'type': vehicle_type,
            'x': x,
            'z': z,
            'dx': dx,
            'dz': dz,
            'speed': speed,
            'violation_type': violation_type,
            'timestamp': datetime.now().isoformat(),
            'confidence': round(random.uniform(0.7, 0.98), 2)
        }
    
    def update_vehicle(self, vehicle: Dict) -> Dict:
        move_distance = vehicle['speed'] * 0.005
        vehicle['x'] += vehicle['dx'] * move_distance
        vehicle['z'] += vehicle['dz'] * move_distance
        
        if vehicle['violation_type'] == 'red_light' and self.traffic_light_state == 'red':
            if abs(vehicle['x']) < 5 and abs(vehicle['z']) < 5:
                vehicle['speed'] *= 0.9
        
        vehicle['timestamp'] = datetime.now().isoformat()
        
        return vehicle
    
    def check_boundary(self, vehicle: Dict) -> bool:
        return abs(vehicle['x']) < 50 and abs(vehicle['z']) < 50
    
    def update_traffic_light(self):
        self.traffic_light_timer += 1
        if self.traffic_light_timer >= 20:
            states = ['red', 'yellow', 'green', 'yellow']
            current_index = states.index(self.traffic_light_state)
            self.traffic_light_state = states[(current_index + 1) % 4]
            self.traffic_light_timer = 0
    
    def simulate_step(self) -> Dict:
        self.update_traffic_light()
        
        if random.random() < 0.1:
            new_vehicle = self.generate_vehicle()
            self.vehicles[new_vehicle['id']] = new_vehicle
        
        to_remove = []
        for vid, vehicle in self.vehicles.items():
            updated = self.update_vehicle(vehicle)
            self.vehicles[vid] = updated
            
            if not self.check_boundary(updated):
                to_remove.append(vid)
        
        for vid in to_remove:
            del self.vehicles[vid]
        
        return {
            'vehicles': list(self.vehicles.values()),
            'traffic_light': self.traffic_light_state,
            'timestamp': datetime.now().isoformat(),
            'total_vehicles': len(self.vehicles),
            'violating_vehicles': sum(1 for v in self.vehicles.values() if v['violation_type'])
        }
    
    def start(self):
        self.running = True
        while self.running:
            data = self.simulate_step()
            yield data
            time.sleep(self.update_interval)
    
    def stop(self):
        self.running = False

class ViolationDetector:
    def __init__(self):
        self.violation_rules = {
            'red_light': {
                'name': '闯红灯',
                'severity': 'high',
                'description': '车辆在红灯时通过路口'
            },
            'no_helmet': {
                'name': '未戴头盔',
                'severity': 'medium',
                'description': '骑乘人员未佩戴头盔'
            },
            'speeding': {
                'name': '超速行驶',
                'severity': 'high',
                'description': '车辆行驶速度超过限速'
            },
            'illegal_parking': {
                'name': '违规停车',
                'severity': 'low',
                'description': '车辆在禁停区域停留'
            },
            'lane_departure': {
                'name': '压线行驶',
                'severity': 'low',
                'description': '车辆越过车道线'
            },
            'wrong_way': {
                'name': '逆行',
                'severity': 'high',
                'description': '车辆逆向行驶'
            }
        }
    
    def detect_violations(self, vehicles: List[Dict], scene_config: Dict = None) -> List[Dict]:
        violations = []
        
        for vehicle in vehicles:
            if vehicle.get('violation_type'):
                rule = self.violation_rules.get(vehicle['violation_type'], {})
                violations.append({
                    'id': vehicle['id'],
                    'type': vehicle['violation_type'],
                    'name': rule.get('name', vehicle['violation_type']),
                    'severity': rule.get('severity', 'medium'),
                    'description': rule.get('description', ''),
                    'x': vehicle['x'],
                    'z': vehicle['z'],
                    'speed': vehicle['speed'],
                    'confidence': vehicle.get('confidence', 0.8),
                    'timestamp': vehicle['timestamp']
                })
        
        return violations

def main():
    simulator = TrafficDataSimulator()
    detector = ViolationDetector()
    
    print("=== 交通数据模拟器 ===")
    print("开始生成模拟数据...")
    
    for i, data in enumerate(simulator.start()):
        violations = detector.detect_violations(data['vehicles'])
        data['violations'] = violations
        
        if i % 4 == 0:
            print(f"\n[第 {i+1} 步]")
            print(f"  时间: {data['timestamp']}")
            print(f"  总车辆数: {data['total_vehicles']}")
            print(f"  违规车辆数: {data['violating_vehicles']}")
            print(f"  红绿灯状态: {data['traffic_light']}")
            
            if violations:
                print(f"  违规详情:")
                for v in violations[:3]:
                    print(f"    - {v['id']}: {v['name']} ({v['severity']})")
        
        if i >= 20:
            simulator.stop()
            break
    
    print("\n模拟结束")

if __name__ == "__main__":
    main()