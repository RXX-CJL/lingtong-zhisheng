# -*- coding: utf-8 -*-
"""
TASK-COORD-003 生产形态回归测试：TrafficPlugin ↔ TrafficEventEngine 车辆参数契约

背景（TASK-COORD-001 审计 §3.3 定位的断点）：
    realtime_detector._process_event_engine 以
        engine.process_frame(frame, detections, self.tracked_vehicles, self.scene_config)
    调用事件引擎；引擎再以
        plugin.analyze(frame, scene_context, tracked_vehicles)
    调用规则插件。即：
      - 第 3 个实参是 {track_id: vehicle_dict} 字典（生产形态）
      - scene_context 是检测器的 scene_config，其中**不含**任何车辆字段
    修复前 TrafficPlugin._extract_vehicles 只认 scene_context["vehicles"] /
    scene_context["tracked_vehicles"] / tracker.get_all_vehicles()，
    对"tracker 实参本身是 dict" 的情况返回 []，导致插件永远拿不到车辆、
    行为规则不执行、引擎收不到违规事件（实测事件数恒为 0）。

本测试用**生产参数形态**驱动「TrafficEventEngine → 真实 TrafficPlugin → BehaviorEngine」
完整路径，断言车辆进入行为分析并最终产生正确的 TrafficEvent。

隔离性（不依赖摄像头 / 网络 / 云端 / 真实模型）：
  - 不导入 realtime_detector（其模块级单例会加载 YOLO/CUDA 模型）
  - 不导入 image_recognizer / cloud_collaborator（避免任何云端调用）
  - 不打开摄像头、不读取视频文件、不写任何文件
  - 车辆字典与轨迹在测试内构造；BehaviorEngine 为纯 Python 规则（无模型/网络），
    输入固定 → 输出确定
  - 每个用例使用独立的 TrafficEventEngine（冷却表互不干扰）

运行：
    py -3 -m unittest tests.test_traffic_plugin_contract -v
"""

import os
import sys
import unittest

# 将 api 目录加入 sys.path（与仓库其他测试一致）
API_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api')
API_DIR = os.path.abspath(API_DIR)
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from rule_engine.plugin_loader import PluginLoader          # noqa: E402
from behavior_engine import BehaviorEngine                    # noqa: E402
from traffic_event_engine import TrafficEventEngine, EventState  # noqa: E402


# ======================================================================
# 生产形态固定装置
# ======================================================================

# 检测器 realtime_detector.process_frame 构造的 scene_config 键集合
# （realtime_detector.py:376-384）——注意：**没有** vehicles / tracked_vehicles
PRODUCTION_SCENE_CONFIG = {
    'traffic_light_state': 'red',
    'stop_line_y': 350,
    'road_direction': 'south',
    'speed_limit': 60,
    'pixel_per_meter': 10,
    'no_parking_zones': [],
    'lane_lines': [],
}

_FIXED_BASE_TS = 1700000000.0  # 固定时间戳，保证完全确定性


def make_vehicle(track_id: int = 7):
    """构造与 VehicleTracker.update 输出同构的车辆字典（dict 的 value）"""
    history = []
    for i, y in enumerate((100, 200, 300, 400, 500)):
        history.append({
            'center': (300, y),
            'bbox': [200, y - 100, 400, y + 100],
            'timestamp': _FIXED_BASE_TS + i * 0.5,
        })
    return {
        'id': track_id,
        'class_name': 'car',
        'confidence': 0.95,
        'bbox': [200, 400, 400, 600],
        'center': (300, 500),
        'direction': 'down',
        'speed': 200.0,
        'history': history,
        'first_seen': _FIXED_BASE_TS,
        'last_seen': _FIXED_BASE_TS + 2.0,
        'frame_count': 5,
        'plate_number': '宁A12345',
        'plate_color': 'blue',
    }


class _RecordingBehaviorEngine:
    """把 analyze_all 委派给真实 BehaviorEngine，同时记录收到的车辆

    用于证明"车辆确实进入了行为分析阶段"，而不仅仅是"被 _extract_vehicles 取出来了"。
    """

    def __init__(self, real_engine):
        self._real = real_engine
        self.seen_vehicles = []

    def analyze_all(self, vehicle, scene_config=None):
        self.seen_vehicles.append(vehicle)
        return self._real.analyze_all(vehicle, scene_config)


class _FakeTrackerObject:
    """模拟 VehicleTracker 实例（提供 get_all_vehicles 方法）"""

    def __init__(self, vehicles):
        self._vehicles = vehicles

    def get_all_vehicles(self):
        return list(self._vehicles)


# ======================================================================
# 测试
# ======================================================================

class TestTrafficPluginProductionContract(unittest.TestCase):
    """生产调用形态：tracked_vehicles 作为第 3 实参字典传入"""

    @classmethod
    def setUpClass(cls):
        # 走与 realtime_detector._init_event_engine 相同的加载路径
        cls.loader = PluginLoader(enabled_scenarios=["traffic"])
        cls.loader.discover()
        cls.loader.initialize_all()
        # 注意：PluginLoader.discover() 对已在 sys.modules 中的插件模块执行
        # importlib.reload()，会生成新的类对象；因此这里从 sys.modules 取
        # "加载器实际使用的那个类"，isinstance 校验才真实有效。
        cls.plugin_cls = sys.modules['rule_engine.plugins.traffic_plugin'].TrafficPlugin

    def setUp(self):
        self.plugin = self.loader.get("traffic")
        self.assertIsNotNone(self.plugin, "TrafficPlugin 未从 PluginLoader 加载成功")
        # 每个用例独立引擎 → 冷却表干净
        self.engine = TrafficEventEngine(
            rule_plugins=[self.plugin],
            frame_buffer=None,
            cooldown_sec=60,
        )
        self.vehicle = make_vehicle(track_id=7)
        # 生产形态：dict 在第三实参，scene_context 里没有车辆
        self.tracked_vehicles = {7: self.vehicle}

    # ------------------------------------------------------------------
    # 0. 前置断言：我们用的确实是生产形态
    # ------------------------------------------------------------------
    def test_production_shape_has_no_vehicle_in_scene_context(self):
        """确认测试装置符合生产形态：scene_context 不含车辆字段"""
        self.assertNotIn('vehicles', PRODUCTION_SCENE_CONFIG)
        self.assertNotIn('tracked_vehicles', PRODUCTION_SCENE_CONFIG)
        self.assertIsInstance(self.tracked_vehicles, dict)
        self.assertNotIsInstance(self.tracked_vehicles, list)
        # 被测插件必须是真实 TrafficPlugin（加载器实际使用的类）
        self.assertIsInstance(self.plugin, self.plugin_cls)
        self.assertEqual(type(self.plugin).__name__, 'TrafficPlugin')
        self.assertEqual(self.plugin.scenario_name, 'traffic')
        print("[test_production_shape] scene_context 无车辆字段，车辆仅在第三实参 dict 中")

    # ------------------------------------------------------------------
    # 1. 核心：生产形态能够创建事件，且 track_id / event_type 正确
    # ------------------------------------------------------------------
    def test_production_shape_creates_event_with_correct_track_and_type(self):
        """核心回归：engine.process_frame(frame, detections, tracked_dict, scene_context)"""
        events = self.engine.process_frame(
            None,                    # frame（行为分析不需要图像）
            [],                      # detections
            self.tracked_vehicles,   # ← 生产形态：dict[id -> vehicle]
            dict(PRODUCTION_SCENE_CONFIG),
        )

        self.assertGreaterEqual(
            len(events), 1,
            "生产形态下未创建任何 TrafficEvent —— 车辆参数契约仍然断裂"
        )

        event_types = {e.event_type for e in events}
        print(f"[test_production_shape_creates_event] 事件类型={sorted(event_types)} "
              f"track_ids={sorted({e.track_id for e in events})}")

        red_light_events = [e for e in events if e.event_type == 'red_light']
        self.assertEqual(
            len(red_light_events), 1,
            f"应恰好产生 1 个 red_light 事件，实际 {len(red_light_events)}；全部类型={sorted(event_types)}"
        )

        evt = red_light_events[0]
        self.assertEqual(evt.track_id, 7, "事件的 track_id 必须来自字典中的车辆")
        self.assertEqual(evt.state, EventState.TRIGGERED)
        self.assertEqual(evt.vehicle_info.get('class_name'), 'car')
        self.assertEqual(evt.vehicle_info.get('plate_number'), '宁A12345')
        self.assertTrue(evt.event_id.startswith('evt_'))
        self.assertGreater(evt.trigger_time, 0)
        # 规则判断结果来自真实 BehaviorEngine
        self.assertEqual(evt.rule_judgment.get('behavior_type'), 'red_light')
        self.assertGreater(evt.rule_judgment.get('confidence', 0.0), 0.0)
        self.assertTrue(evt.rule_judgment.get('is_violation'))
        # 状态历史初始为 TRIGGERED
        self.assertEqual(evt.state_history[0]['new_state'], 'triggered')

    # ------------------------------------------------------------------
    # 2. 证明车辆进入"行为分析"，而不只是被提取出来
    # ------------------------------------------------------------------
    def test_vehicle_reaches_behavior_analysis(self):
        """用记录型代理证明 BehaviorEngine.analyze_all 收到了字典里的车辆"""
        spy = _RecordingBehaviorEngine(BehaviorEngine())
        original = self.plugin._behavior_engine
        self.plugin._behavior_engine = spy
        self.addCleanup(setattr, self.plugin, '_behavior_engine', original)

        events = self.engine.process_frame(
            None, [], self.tracked_vehicles, dict(PRODUCTION_SCENE_CONFIG)
        )

        self.assertTrue(spy.seen_vehicles, "行为分析从未被调用 —— 车辆未到达规则分析阶段")
        seen_ids = [v.get('id') for v in spy.seen_vehicles]
        self.assertIn(7, seen_ids, f"行为分析收到的车辆 id 不含 7：{seen_ids}")
        # 车辆对象身份一致：确实是字典里那个 dict，而不是空壳
        self.assertIs(spy.seen_vehicles[0], self.vehicle)
        self.assertEqual(spy.seen_vehicles[0].get('history'), self.vehicle['history'])
        self.assertGreaterEqual(len(events), 1)
        print(f"[test_vehicle_reaches_behavior_analysis] 行为分析收到车辆 id={seen_ids}")

    # ------------------------------------------------------------------
    # 3. 冷却机制在生产形态下依然生效
    # ------------------------------------------------------------------
    def test_production_shape_cooldown_still_applies(self):
        """同一 dict 连续两次处理：第二次因 60s 冷却不再创建事件"""
        first = self.engine.process_frame(
            None, [], self.tracked_vehicles, dict(PRODUCTION_SCENE_CONFIG)
        )
        second = self.engine.process_frame(
            None, [], self.tracked_vehicles, dict(PRODUCTION_SCENE_CONFIG)
        )
        self.assertGreaterEqual(len(first), 1)
        self.assertEqual(second, [], "冷却期内不应重复触发")
        print(f"[test_production_shape_cooldown] 首次={len(first)} 事件，冷却期第二次=0")

    # ------------------------------------------------------------------
    # 4. 负向：空字典 / 非车辆值不得凭空造事件
    # ------------------------------------------------------------------
    def test_empty_tracked_vehicles_dict_creates_no_event(self):
        events = self.engine.process_frame(
            None, [], {}, dict(PRODUCTION_SCENE_CONFIG)
        )
        self.assertEqual(events, [], "空 tracked_vehicles 不应产生事件")

    def test_non_vehicle_dict_values_are_ignored(self):
        """字典里放非 dict 值不得抛异常，也不得产生事件"""
        events = self.engine.process_frame(
            None, [], {1: 'not-a-vehicle', 2: None, 3: 42}, dict(PRODUCTION_SCENE_CONFIG)
        )
        self.assertEqual(events, [], "非车辆值不应产生事件")
        print("[test_non_vehicle_dict_values_are_ignored] 非车辆值被安全忽略")

    # ------------------------------------------------------------------
    # 5. 向后兼容：原有两条取车路径不得回退
    # ------------------------------------------------------------------
    def test_legacy_scene_context_vehicles_still_works(self):
        ctx = dict(PRODUCTION_SCENE_CONFIG)
        ctx['vehicles'] = [self.vehicle]
        events = self.engine.process_frame(None, [], {}, ctx)
        self.assertGreaterEqual(len(events), 1)
        self.assertIn('red_light', {e.event_type for e in events})
        self.assertEqual({e.track_id for e in events}, {7})
        print("[test_legacy_scene_context_vehicles] scene_context['vehicles'] 路径仍可用")

    def test_legacy_scene_context_tracked_vehicles_still_works(self):
        ctx = dict(PRODUCTION_SCENE_CONFIG)
        ctx['tracked_vehicles'] = self.tracked_vehicles
        events = self.engine.process_frame(None, [], {}, ctx)
        self.assertGreaterEqual(len(events), 1)
        self.assertIn('red_light', {e.event_type for e in events})
        self.assertEqual({e.track_id for e in events}, {7})
        print("[test_legacy_scene_context_tracked_vehicles] scene_context['tracked_vehicles'] 路径仍可用")

    def test_tracker_object_with_get_all_vehicles_still_works(self):
        events = self.engine.process_frame(
            None, [], _FakeTrackerObject([self.vehicle]), dict(PRODUCTION_SCENE_CONFIG)
        )
        self.assertGreaterEqual(len(events), 1)
        self.assertIn('red_light', {e.event_type for e in events})
        self.assertEqual({e.track_id for e in events}, {7})
        print("[test_tracker_object] tracker.get_all_vehicles() 路径仍可用")

    # ------------------------------------------------------------------
    # 6. 插件层直接调用（不经引擎）同样成立
    # ------------------------------------------------------------------
    def test_plugin_analyze_directly_with_tracker_dict(self):
        """plugin.analyze(frame, scene_context, tracked_dict) 直接契约"""
        violations = self.plugin.analyze(None, dict(PRODUCTION_SCENE_CONFIG), self.tracked_vehicles)
        self.assertGreaterEqual(len(violations), 1, "插件直接调用仍拿不到车辆")
        self.assertEqual({v.vehicle_id for v in violations}, {7})
        self.assertIn('red_light', {v.behavior_type for v in violations})
        print(f"[test_plugin_analyze_directly] 插件直接返回 {len(violations)} 个违规 "
              f"{sorted({v.behavior_type for v in violations})}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
