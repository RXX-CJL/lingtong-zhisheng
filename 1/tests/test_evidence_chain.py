# -*- coding: utf-8 -*-
"""
EvidenceChain 单元测试（TASK-029 M04）

覆盖 ≥5 测试用例：
- EvidenceChain 15 字段完整
- from_traffic_event 从 TrafficEvent 构建
- to_dict 输出字典
- to_json 输出 JSON 字符串
- summary 输出人类可读摘要
- ai_trace v3 嵌入 ai_judgment 字段
- from_dict 反序列化
"""

import os
import sys
import json
import unittest
from dataclasses import fields

# 让测试能导入 api 模块
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api'))

from evidence_chain import EvidenceChain
from traffic_event_engine import TrafficEvent, EventState


class TestEvidenceChain(unittest.TestCase):

    def _make_test_event(self):
        """创建测试用 TrafficEvent"""
        return TrafficEvent(
            event_id='test_evt_001',
            event_type='red_light',
            track_id=42,
            state=EventState.CONFIRMED,
            trigger_time=1700000000.0,
            created_at='2026-08-21T10:00:00',
            vehicle_info={
                'track_id': 42,
                'bbox': [100, 100, 200, 200],
                'class_name': 'car',
                'speed': 45.0,
                'direction': 90.0,
                'plate_number': '京A12345',
                'plate_color': 'blue',
            },
            scene_context={
                'traffic_light': 'red',
                'lane': 'main_lane_1',
                'stop_line': 300,
                'location': '北京市海淀区中关村大街',
            },
            trajectory=[
                {'x': 150, 'y': 250, 'timestamp': 1700000000.0},
                {'x': 155, 'y': 280, 'timestamp': 1700000000.5},
                {'x': 160, 'y': 310, 'timestamp': 1700000001.0},
            ],
            key_frames=['frame1.jpg', 'frame2.jpg', 'frame3.jpg'],
            event_video_path='/data/event_videos/20260821/test_evt_001.mp4',
            rule_judgment={
                'behavior_type': 'red_light',
                'confidence': 0.88,
                'is_violation': True,
                'evidence': {'bbox': [100, 100, 200, 200]},
            },
            ai_judgment={
                'version': 'v3',
                'yolo': {'confidence': 0.92},
                'claude': {'judgment': 'confirmed', 'confidence': 0.95},
                'doubao': {'confidence': 0.89},
                'deepseek': {'judgment': 'confirmed'},
                'final': {
                    'judgment': 'confirmed',
                    'confidence': 0.92,
                    'explanation': '车辆在红灯时越过停止线',
                }
            },
            ai_confidence=0.92,
            ai_explanation='车辆在红灯时越过停止线，确认闯红灯违规',
        )

    def test_fifteen_fields_exist(self):
        """测试 EvidenceChain 包含 GPT §10 要求的 15+ 字段"""
        expected = {
            'camera_id', 'timestamp', 'location',
            'vehicle_id', 'vehicle_type', 'plate_number', 'plate_color', 'lane_id',
            'traffic_light_state', 'stop_line_relation', 'trajectory',
            'key_frames', 'event_video_path',
            'rule_judgment', 'ai_judgment', 'ai_confidence', 'ai_explanation',
            'final_status'
        }
        actual = {f.name for f in fields(EvidenceChain)}
        missing = expected - actual
        self.assertEqual(missing, set(), f"缺少字段: {missing}")
        print(f"[test_fifteen_fields_exist] {len(actual)} 个字段全部存在")

    def test_from_traffic_event(self):
        """测试从 TrafficEvent 构建证据链"""
        event = self._make_test_event()
        chain = EvidenceChain.from_traffic_event(event, camera_id='cam_001')

        # 基础信息
        self.assertEqual(chain.camera_id, 'cam_001')
        self.assertEqual(chain.timestamp, '2026-08-21T10:00:00')
        self.assertEqual(chain.location, '北京市海淀区中关村大街')

        # 车辆信息
        self.assertEqual(chain.vehicle_id, 42)
        self.assertEqual(chain.vehicle_type, 'car')
        self.assertEqual(chain.plate_number, '京A12345')
        self.assertEqual(chain.plate_color, 'blue')
        self.assertEqual(chain.lane_id, 'main_lane_1')

        # 场景上下文
        self.assertEqual(chain.traffic_light_state, 'red')
        # 最后轨迹点 y=310 > stop_line=300 → after
        self.assertEqual(chain.stop_line_relation, 'after')
        self.assertEqual(len(chain.trajectory), 3)

        # 视觉证据
        self.assertEqual(len(chain.key_frames), 3)
        self.assertEqual(chain.event_video_path, '/data/event_videos/20260821/test_evt_001.mp4')

        # 判断结果
        self.assertEqual(chain.rule_judgment['behavior_type'], 'red_light')
        self.assertEqual(chain.ai_confidence, 0.92)
        self.assertIn('红灯', chain.ai_explanation)

        # 最终状态
        self.assertEqual(chain.final_status, 'confirmed')
        print(f"[test_from_traffic_event] 从 TrafficEvent 构建证据链成功 status={chain.final_status}")

    def test_to_dict(self):
        """测试 to_dict 输出字典"""
        event = self._make_test_event()
        chain = EvidenceChain.from_traffic_event(event, camera_id='cam_001')
        d = chain.to_dict()

        self.assertIsInstance(d, dict)
        self.assertEqual(d['camera_id'], 'cam_001')
        self.assertEqual(d['vehicle_id'], 42)
        self.assertEqual(d['plate_number'], '京A12345')
        self.assertEqual(d['final_status'], 'confirmed')
        self.assertEqual(len(d['key_frames']), 3)
        self.assertEqual(len(d['trajectory']), 3)
        print(f"[test_to_dict] 字典输出 {len(d)} 个字段")

    def test_to_json(self):
        """测试 to_json 输出 JSON 字符串"""
        event = self._make_test_event()
        chain = EvidenceChain.from_traffic_event(event, camera_id='cam_001')
        json_str = chain.to_json()

        self.assertIsInstance(json_str, str)
        # 解析回来验证
        parsed = json.loads(json_str)
        self.assertEqual(parsed['camera_id'], 'cam_001')
        self.assertEqual(parsed['vehicle_id'], 42)
        self.assertEqual(parsed['plate_number'], '京A12345')
        self.assertEqual(parsed['ai_judgment']['version'], 'v3')
        self.assertEqual(parsed['ai_judgment']['final']['judgment'], 'confirmed')
        print(f"[test_to_json] JSON 字符串长度 {len(json_str)} 字符，解析成功")

    def test_summary(self):
        """测试 summary 输出人类可读摘要"""
        event = self._make_test_event()
        chain = EvidenceChain.from_traffic_event(event, camera_id='cam_001')
        summary = chain.summary()

        self.assertIsInstance(summary, str)
        self.assertIn('事件证据链摘要', summary)
        self.assertIn('cam_001', summary)
        self.assertIn('京A12345', summary)
        self.assertIn('car', summary)
        self.assertIn('red', summary)
        self.assertIn('confirmed', summary)
        self.assertIn('v3', summary)
        # 应有多行
        self.assertGreater(summary.count('\n'), 10)
        print(f"[test_summary] 摘要 {len(summary)} 字符，{summary.count(chr(10))+1} 行")

    def test_ai_trace_v3_embedded(self):
        """测试 ai_trace v3 作为 ai_judgment 字段嵌入"""
        event = self._make_test_event()
        chain = EvidenceChain.from_traffic_event(event)

        # ai_judgment 应保持 ai_trace v3 嵌套结构
        ai = chain.ai_judgment
        self.assertEqual(ai.get('version'), 'v3')
        self.assertIn('yolo', ai)
        self.assertIn('claude', ai)
        self.assertIn('doubao', ai)
        self.assertIn('deepseek', ai)
        self.assertIn('final', ai)

        # 豆包置信度应为 0-1 之间（min(val/100.0, 1.0) 转换）
        doubao_conf = ai.get('doubao', {}).get('confidence', 0)
        self.assertGreaterEqual(doubao_conf, 0.0)
        self.assertLessEqual(doubao_conf, 1.0)

        # final.confidence 应与 ai_confidence 一致
        self.assertEqual(ai['final']['confidence'], chain.ai_confidence)
        print(f"[test_ai_trace_v3_embedded] ai_trace v3 嵌套结构完整，version={ai['version']}")

    def test_from_dict_deserialize(self):
        """测试 from_dict 反序列化"""
        event = self._make_test_event()
        chain = EvidenceChain.from_traffic_event(event, camera_id='cam_001')
        # 序列化为 dict
        d = chain.to_dict()
        # 反序列化回来
        chain2 = EvidenceChain.from_dict(d)

        self.assertEqual(chain2.camera_id, 'cam_001')
        self.assertEqual(chain2.vehicle_id, 42)
        self.assertEqual(chain2.plate_number, '京A12345')
        self.assertEqual(chain2.final_status, 'confirmed')
        self.assertEqual(chain2.ai_judgment['version'], 'v3')
        print(f"[test_from_dict_deserialize] 反序列化成功")

    def test_empty_event(self):
        """测试从空 TrafficEvent 构建（边界情况）"""
        event = TrafficEvent(
            event_id='empty_evt',
            event_type='unknown',
            track_id=-1,
            state=EventState.DETECTING,
        )
        chain = EvidenceChain.from_traffic_event(event, camera_id='default')
        self.assertEqual(chain.camera_id, 'default')
        self.assertEqual(chain.vehicle_id, -1)
        self.assertEqual(chain.vehicle_type, 'unknown')
        self.assertEqual(chain.plate_number, '')
        self.assertEqual(chain.traffic_light_state, 'unknown')
        self.assertEqual(chain.final_status, 'pending')
        print(f"[test_empty_event] 空 TrafficEvent 构建证据链成功 status=pending")


if __name__ == '__main__':
    unittest.main(verbosity=2)
