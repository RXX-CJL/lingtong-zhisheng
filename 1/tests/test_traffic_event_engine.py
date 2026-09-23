# -*- coding: utf-8 -*-
"""
TrafficEventEngine 单元测试（TASK-029 M03）

覆盖 ≥8 测试用例：
- EventState 枚举 8 状态
- TrafficEvent 数据类字段
- 事件创建和状态 TRIGGERED
- 合法状态转换
- 非法状态转换拒绝
- 冷却机制
- get_active_events
- submit_to_ai
- apply_ai_result (confirmed/rejected/uncertain)
- manual_review
"""

import os
import sys
import time
import unittest
from dataclasses import fields

# 让测试能导入 api 模块
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api'))

from traffic_event_engine import (
    EventState, TrafficEvent, TrafficEventEngine, VALID_TRANSITIONS, TERMINAL_STATES
)


class MockViolationEvent:
    """模拟规则插件返回的 ViolationEvent"""
    def __init__(self, behavior_type='red_light', confidence=0.85, vehicle_id=1,
                 is_violation=True, evidence=None, color='#FF0000'):
        self.behavior_type = behavior_type
        self.confidence = confidence
        self.vehicle_id = vehicle_id
        self.is_violation = is_violation
        self.evidence = evidence or {'bbox': [100, 100, 200, 200]}
        self.color = color


class MockRulePlugin:
    """模拟规则插件"""
    def __init__(self, violations=None, scenario_name='mock', enabled=True):
        self.scenario_name = scenario_name
        self.is_enabled = enabled
        self._violations = violations or []

    def analyze(self, frame, scene_context, tracked_vehicles):
        return list(self._violations)


class TestEventStateEnum(unittest.TestCase):

    def test_eight_states_exist(self):
        """测试 EventState 枚举包含 8 个状态"""
        expected = {'detecting', 'triggered', 'recording', 'pending_ai',
                    'ai_reviewed', 'confirmed', 'rejected', 'manual_review'}
        actual = {s.value for s in EventState}
        self.assertEqual(actual, expected)
        print(f"[test_eight_states_exist] 8 状态: {sorted(actual)}")

    def test_valid_transitions(self):
        """测试合法状态转换映射"""
        # DETECTING → TRIGGERED
        self.assertIn(EventState.TRIGGERED, VALID_TRANSITIONS[EventState.DETECTING])
        # TRIGGERED → RECORDING
        self.assertIn(EventState.RECORDING, VALID_TRANSITIONS[EventState.TRIGGERED])
        # RECORDING → PENDING_AI
        self.assertIn(EventState.PENDING_AI, VALID_TRANSITIONS[EventState.RECORDING])
        # PENDING_AI → AI_REVIEWED
        self.assertIn(EventState.AI_REVIEWED, VALID_TRANSITIONS[EventState.PENDING_AI])
        # AI_REVIEWED → CONFIRMED/REJECTED/MANUAL_REVIEW
        self.assertIn(EventState.CONFIRMED, VALID_TRANSITIONS[EventState.AI_REVIEWED])
        self.assertIn(EventState.REJECTED, VALID_TRANSITIONS[EventState.AI_REVIEWED])
        self.assertIn(EventState.MANUAL_REVIEW, VALID_TRANSITIONS[EventState.AI_REVIEWED])
        # MANUAL_REVIEW → CONFIRMED/REJECTED
        self.assertIn(EventState.CONFIRMED, VALID_TRANSITIONS[EventState.MANUAL_REVIEW])
        self.assertIn(EventState.REJECTED, VALID_TRANSITIONS[EventState.MANUAL_REVIEW])
        # 终态无后续转换
        self.assertEqual(VALID_TRANSITIONS[EventState.CONFIRMED], [])
        self.assertEqual(VALID_TRANSITIONS[EventState.REJECTED], [])
        print("[test_valid_transitions] 全部合法转换验证通过")


class TestTrafficEventDataclass(unittest.TestCase):

    def test_dataclass_fields(self):
        """测试 TrafficEvent 数据类包含 GPT §10 全部字段"""
        expected_fields = {
            'event_id', 'event_type', 'track_id', 'state',
            'trigger_time', 'created_at', 'updated_at',
            'vehicle_info', 'scene_context', 'trajectory',
            'key_frames', 'event_video_path', 'rule_judgment',
            'ai_judgment', 'ai_confidence', 'ai_explanation',
            'state_history', 'cooldown_until'
        }
        actual_fields = {f.name for f in fields(TrafficEvent)}
        missing = expected_fields - actual_fields
        self.assertEqual(missing, set(), f"缺少字段: {missing}")
        print(f"[test_dataclass_fields] {len(actual_fields)} 个字段全部存在")


class TestTrafficEventEngine(unittest.TestCase):

    def setUp(self):
        """每个测试前创建新引擎"""
        self.plugin = MockRulePlugin()
        self.engine = TrafficEventEngine(
            rule_plugins=[self.plugin],
            frame_buffer=None,
            cooldown_sec=60,
        )
        self.tracked_vehicles = {
            1: {'track_id': 1, 'bbox': [100, 100, 200, 200], 'class_name': 'car',
                'speed': 60.0, 'direction': 90.0, 'plate_number': '京A12345'}
        }
        self.scene_context = {'traffic_light': 'red', 'lane': 'main', 'stop_line': 300}

    def test_trigger_event(self):
        """测试事件创建和状态 TRIGGERED"""
        self.plugin._violations = [MockViolationEvent(vehicle_id=1, behavior_type='red_light')]
        events = self.engine.process_frame(None, [], self.tracked_vehicles, self.scene_context)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.state, EventState.TRIGGERED)
        self.assertEqual(event.event_type, 'red_light')
        self.assertEqual(event.track_id, 1)
        self.assertGreater(event.trigger_time, 0)
        self.assertEqual(event.vehicle_info['plate_number'], '京A12345')
        self.assertEqual(event.scene_context['traffic_light'], 'red')
        print(f"[test_trigger_event] 事件 {event.event_id} 已创建 state=TRIGGERED")

    def test_valid_state_transition(self):
        """测试合法状态转换"""
        event = TrafficEvent(event_id='test1', event_type='red_light', track_id=1,
                            state=EventState.TRIGGERED)
        self.engine._events['test1'] = event
        self.engine.transition_to_recording('test1')
        self.assertEqual(event.state, EventState.RECORDING)
        # 继续推进到 PENDING_AI
        submit_info = self.engine.submit_to_ai('test1')
        self.assertEqual(event.state, EventState.PENDING_AI)
        self.assertEqual(submit_info['event_id'], 'test1')
        print(f"[test_valid_state_transition] TRIGGERED→RECORDING→PENDING_AI 全部合法")

    def test_invalid_state_transition(self):
        """测试非法状态转换拒绝"""
        event = TrafficEvent(event_id='test2', event_type='red_light', track_id=1,
                            state=EventState.DETECTING)
        self.engine._events['test2'] = event
        # DETECTING → CONFIRMED 是非法的
        with self.assertRaises(ValueError) as ctx:
            self.engine._update_event_state(event, EventState.CONFIRMED, reason="非法跳转")
        self.assertIn('非法状态转换', str(ctx.exception))
        print(f"[test_invalid_state_transition] DETECTING→CONFIRMED 被拒绝: {ctx.exception}")

    def test_cooldown(self):
        """测试冷却机制"""
        self.plugin._violations = [MockViolationEvent(vehicle_id=1, behavior_type='red_light')]
        # 第一次触发
        events1 = self.engine.process_frame(None, [], self.tracked_vehicles, self.scene_context)
        self.assertEqual(len(events1), 1)
        # 立即再次触发，应被冷却
        events2 = self.engine.process_frame(None, [], self.tracked_vehicles, self.scene_context)
        self.assertEqual(len(events2), 0)
        # 不同 track_id 不受冷却影响
        self.plugin._violations = [MockViolationEvent(vehicle_id=2, behavior_type='red_light')]
        events3 = self.engine.process_frame(None, [], self.tracked_vehicles, self.scene_context)
        self.assertEqual(len(events3), 1)
        print(f"[test_cooldown] 同车同类型 60s 内第二次触发被冷却，不同车不受影响")

    def test_get_active_events(self):
        """测试 get_active_events"""
        # 创建 2 个活跃 + 1 个已确认
        e1 = TrafficEvent(event_id='a1', event_type='red_light', track_id=1, state=EventState.TRIGGERED)
        e2 = TrafficEvent(event_id='a2', event_type='wrong_way', track_id=2, state=EventState.RECORDING)
        e3 = TrafficEvent(event_id='a3', event_type='illegal_park', track_id=3, state=EventState.CONFIRMED)
        self.engine._events = {'a1': e1, 'a2': e2, 'a3': e3}
        active = self.engine.get_active_events()
        self.assertEqual(len(active), 2)
        active_ids = {e.event_id for e in active}
        self.assertEqual(active_ids, {'a1', 'a2'})
        print(f"[test_get_active_events] 3 事件中 2 个活跃（不含 CONFIRMED）")

    def test_submit_to_ai(self):
        """测试 submit_to_ai 生成提交 dict"""
        event = TrafficEvent(event_id='sub1', event_type='red_light', track_id=1,
                            state=EventState.RECORDING,
                            event_video_path='/tmp/test.mp4',
                            key_frames=['frame1.jpg', 'frame2.jpg'])
        self.engine._events['sub1'] = event
        submit_info = self.engine.submit_to_ai('sub1')
        self.assertEqual(submit_info['event_id'], 'sub1')
        self.assertEqual(submit_info['event_video_path'], '/tmp/test.mp4')
        self.assertEqual(len(submit_info['key_frames']), 2)
        self.assertEqual(submit_info['event_type'], 'red_light')
        self.assertIn('submit_time', submit_info)
        self.assertEqual(event.state, EventState.PENDING_AI)
        print(f"[test_submit_to_ai] 提交 dict 生成成功 state=PENDING_AI")

    def test_apply_ai_result_confirmed(self):
        """测试 AI 确认违法 → CONFIRMED"""
        event = TrafficEvent(event_id='ai1', event_type='red_light', track_id=1,
                            state=EventState.PENDING_AI)
        self.engine._events['ai1'] = event
        ai_result = {
            'version': 'v3',
            'final': {
                'judgment': 'confirmed',
                'confidence': 0.92,
                'explanation': '车辆在红灯时越过停止线',
            }
        }
        self.engine.apply_ai_result('ai1', ai_result)
        self.assertEqual(event.state, EventState.CONFIRMED)
        self.assertEqual(event.ai_confidence, 0.92)
        self.assertIn('红灯', event.ai_explanation)
        print(f"[test_apply_ai_result_confirmed] AI confirmed → CONFIRMED conf={event.ai_confidence}")

    def test_apply_ai_result_rejected(self):
        """测试 AI 排除 → REJECTED"""
        event = TrafficEvent(event_id='ai2', event_type='wrong_way', track_id=2,
                            state=EventState.PENDING_AI)
        self.engine._events['ai2'] = event
        ai_result = {
            'version': 'v3',
            'final': {
                'judgment': 'rejected',
                'confidence': 0.15,
                'explanation': '车辆方向正确，非逆行',
            }
        }
        self.engine.apply_ai_result('ai2', ai_result)
        self.assertEqual(event.state, EventState.REJECTED)
        print(f"[test_apply_ai_result_rejected] AI rejected → REJECTED")

    def test_apply_ai_result_uncertain(self):
        """测试 AI 不确定 → MANUAL_REVIEW"""
        event = TrafficEvent(event_id='ai3', event_type='illegal_park', track_id=3,
                            state=EventState.PENDING_AI)
        self.engine._events['ai3'] = event
        ai_result = {
            'version': 'v3',
            'final': {
                'judgment': 'uncertain',
                'confidence': 0.5,
                'explanation': '证据不足，无法确认',
            }
        }
        self.engine.apply_ai_result('ai3', ai_result)
        self.assertEqual(event.state, EventState.MANUAL_REVIEW)
        print(f"[test_apply_ai_result_uncertain] AI uncertain → MANUAL_REVIEW")

    def test_manual_review(self):
        """测试人工复核"""
        event = TrafficEvent(event_id='mr1', event_type='no_helmet', track_id=4,
                            state=EventState.MANUAL_REVIEW)
        self.engine._events['mr1'] = event
        # 人工确认
        self.engine.manual_review('mr1', confirmed=True, reviewer='admin', comment='确认违规')
        self.assertEqual(event.state, EventState.CONFIRMED)
        # 创建新事件测试排除
        event2 = TrafficEvent(event_id='mr2', event_type='no_helmet', track_id=5,
                             state=EventState.MANUAL_REVIEW)
        self.engine._events['mr2'] = event2
        self.engine.manual_review('mr2', confirmed=False, reviewer='admin', comment='排除')
        self.assertEqual(event2.state, EventState.REJECTED)
        print(f"[test_manual_review] 人工确认→CONFIRMED / 人工排除→REJECTED")

    def test_state_history_recorded(self):
        """测试状态历史记录"""
        event = TrafficEvent(event_id='sh1', event_type='red_light', track_id=1,
                            state=EventState.TRIGGERED)
        self.engine._events['sh1'] = event
        self.engine.transition_to_recording('sh1')
        self.engine.submit_to_ai('sh1')
        # 应有 3 条历史记录：创建 + RECORDING + PENDING_AI
        self.assertGreaterEqual(len(event.state_history), 3)
        last = event.state_history[-1]
        self.assertEqual(last['old_state'], 'recording')
        self.assertEqual(last['new_state'], 'pending_ai')
        print(f"[test_state_history_recorded] 状态历史 {len(event.state_history)} 条")

    def test_cleanup_old_events(self):
        """清理超时事件"""
        # 创建一个很老的事件
        old_event = TrafficEvent(event_id='old1', event_type='red_light', track_id=99,
                                state=EventState.TRIGGERED)
        old_event.trigger_time = time.time() - 7200  # 2 小时前
        self.engine._events['old1'] = old_event
        # 创建一个新事件
        new_event = TrafficEvent(event_id='new1', event_type='red_light', track_id=100,
                                 state=EventState.TRIGGERED)
        self.engine._events['new1'] = new_event
        removed = self.engine.cleanup_old_events(max_age_sec=3600)
        self.assertEqual(removed, 1)
        self.assertNotIn('old1', self.engine._events)
        self.assertIn('new1', self.engine._events)
        print(f"[test_cleanup_old_events] 清理 1 个超时事件，保留 1 个新事件")


if __name__ == '__main__':
    unittest.main(verbosity=2)
