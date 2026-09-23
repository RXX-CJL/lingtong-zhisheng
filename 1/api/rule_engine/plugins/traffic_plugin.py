# -*- coding: utf-8 -*-
"""
交通场景规则插件
将行为分析逻辑（behavior_engine.BehaviorEngine + vehicle_tracker.VehicleTracker）
封装为 BaseRulePlugin 插件，由 PluginLoader 动态加载

scenario_name = "traffic"
detectable_types = ["red_light", "wrong_way", "illegal_parking",
                    "no_helmet", "speeding"]
"""

import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..base_plugin import BaseRulePlugin, ViolationEvent

# 确保 api/ 目录在 sys.path 中，以便 import behavior_engine / vehicle_tracker
_API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

try:
    from behavior_engine import BehaviorEngine  # type: ignore
    from vehicle_tracker import VehicleTracker  # type: ignore
    _DEPS_AVAILABLE = True
except Exception as e:  # pragma: no cover - 仅当依赖缺失时触发
    BehaviorEngine = None  # type: ignore
    VehicleTracker = None  # type: ignore
    _DEPS_AVAILABLE = False
    logging.getLogger(__name__).warning(
        f"[TrafficPlugin] behavior_engine / vehicle_tracker 不可用: {e}"
    )

logger = logging.getLogger(__name__)


# 行为类型 -> 中文描述
TRAFFIC_TYPE_CN: Dict[str, str] = {
    "red_light": "闯红灯",
    "wrong_way": "逆行",
    "illegal_parking": "违规停车",
    "no_helmet": "未戴头盔",
    "speeding": "超速",
    # 兼容 behavior_engine 输出的扩展类型
    "lane_departure": "压线行驶",
    "running_yellow": "抢黄灯",
    "illegal_turn": "违规掉头",
    "pedestrian_crossing": "未礼让行人",
}

# 行为类型 -> 可视化颜色 (B, G, R)
TRAFFIC_TYPE_COLOR: Dict[str, Any] = {
    "red_light": (0, 0, 255),
    "wrong_way": (0, 165, 255),
    "illegal_parking": (0, 255, 255),
    "no_helmet": (255, 0, 255),
    "speeding": (0, 0, 200),
}


class TrafficPlugin(BaseRulePlugin):
    """交通场景违规检测插件"""

    scenario_name: str = "traffic"
    detectable_types: List[str] = [
        "red_light",
        "wrong_way",
        "illegal_parking",
        "no_helmet",
        "speeding",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config=config)
        self._behavior_engine: Optional["BehaviorEngine"] = None
        self._tracker: Optional["VehicleTracker"] = None

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        if not _DEPS_AVAILABLE:
            raise RuntimeError(
                "TrafficPlugin 依赖 behavior_engine / vehicle_tracker 不可用"
            )
        if self._behavior_engine is None:
            self._behavior_engine = BehaviorEngine(self.config)
        # 注意：VehicleTracker 通常由外层 realtime_detector 持有，
        # 这里仅作为兜底实例，用于独立调用 analyze 时的内部追踪。
        if self._tracker is None:
            self._tracker = VehicleTracker(use_bytetrack=False)
        self._initialized = True
        logger.info("[TrafficPlugin] 初始化完成")

    def shutdown(self) -> None:
        self._behavior_engine = None
        self._tracker = None
        self._initialized = False
        logger.info("[TrafficPlugin] 已关闭")

    # ------------------------------------------------------------------
    # 核心分析
    # ------------------------------------------------------------------
    def analyze(self, frame: Any, scene_context: Dict[str, Any],
                tracker: Any) -> List[ViolationEvent]:
        """对单帧执行交通违规分析

        简化实现：直接调用 behavior_engine.analyze_all，
        将 BehaviorResult 转换为 ViolationEvent 列表返回。

        Args:
            frame: 当前帧（本实现未直接使用，保留以符合接口契约）
            scene_context: 场景上下文，应包含可迭代的 vehicles 列表，
                           每个元素为 vehicle_tracker 输出的车辆 dict
            tracker: 外部追踪器实例（如 realtime_detector.vehicle_tracker）；
                     为 None 时使用插件内部兜底 tracker
        """
        if not self._initialized or self._behavior_engine is None:
            return []

        vehicles = self._extract_vehicles(scene_context, tracker)
        if not vehicles:
            return []

        # scene_context 透传给 BehaviorEngine.analyze_all
        behavior_scene_config = scene_context.get("scene_config", scene_context)

        events: List[ViolationEvent] = []
        for vehicle in vehicles:
            try:
                behaviors = self._behavior_engine.analyze_all(vehicle, behavior_scene_config)
            except Exception as e:
                logger.warning(
                    f"[TrafficPlugin] analyze_all 失败(车辆 {vehicle.get('id', -1)}): {e}"
                )
                continue
            for b in behaviors:
                if not getattr(b, "is_violation", False):
                    continue
                events.append(self._to_event(b))

        return events

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_vehicles(scene_context: Dict[str, Any], tracker: Any) -> List[Dict[str, Any]]:
        """从 scene_context 或 tracker 中提取车辆列表

        优先级：
          1. scene_context["vehicles"]（list[dict]）
          2. scene_context["tracked_vehicles"]（dict[id -> dict]）
          3. tracker.get_all_vehicles()（若提供 tracker 且有该方法）
        """
        if not isinstance(scene_context, dict):
            return []

        vehicles = scene_context.get("vehicles")
        if isinstance(vehicles, list) and vehicles:
            return vehicles

        tracked = scene_context.get("tracked_vehicles")
        if isinstance(tracked, dict) and tracked:
            return list(tracked.values())

        if tracker is not None and hasattr(tracker, "get_all_vehicles"):
            try:
                return list(tracker.get_all_vehicles())
            except Exception:
                return []

        return []

    @staticmethod
    def _to_event(behavior_result) -> ViolationEvent:
        """将 behavior_engine.BehaviorResult 转换为 ViolationEvent"""
        btype = getattr(behavior_result, "behavior_type", "") or ""
        return ViolationEvent(
            behavior_type=btype,
            behavior_type_cn=getattr(behavior_result, "behavior_type_cn", "")
            or TRAFFIC_TYPE_CN.get(btype, btype),
            confidence=float(getattr(behavior_result, "confidence", 0.0)),
            is_violation=bool(getattr(behavior_result, "is_violation", False)),
            evidence=dict(getattr(behavior_result, "evidence", {}) or {}),
            vehicle_id=int(getattr(behavior_result, "vehicle_id", -1)),
            timestamp=getattr(behavior_result, "timestamp", "")
            or datetime.now().isoformat(),
            color=TRAFFIC_TYPE_COLOR.get(btype, (0, 0, 255)),
        )


# 模块自检（仅当直接运行时）
if __name__ == "__main__":  # pragma: no cover
    import json

    plugin = TrafficPlugin()
    print(f"插件: {plugin}")
    print(f"可检测类型: {plugin.detectable_types}")

    if _DEPS_AVAILABLE:
        plugin.initialize()
        # 构造一个最小测试场景
        import time as _t
        test_vehicle = {
            "id": 1,
            "class_name": "car",
            "confidence": 0.95,
            "bbox": [200, 300, 400, 500],
            "center": (300, 400),
            "direction": "down",
            "speed": 25.0,
            "history": [
                {"center": (300, 100), "bbox": [200, 0, 400, 200], "timestamp": _t.time() - 2.0},
                {"center": (300, 200), "bbox": [200, 100, 400, 300], "timestamp": _t.time() - 1.5},
                {"center": (300, 300), "bbox": [200, 200, 400, 400], "timestamp": _t.time() - 1.0},
                {"center": (300, 400), "bbox": [200, 300, 400, 500], "timestamp": _t.time() - 0.5},
                {"center": (300, 500), "bbox": [200, 400, 400, 600], "timestamp": _t.time()},
            ],
            "first_seen": _t.time() - 2.0,
            "last_seen": _t.time(),
            "frame_count": 5,
        }
        ctx = {
            "vehicles": [test_vehicle],
            "traffic_light_state": "red",
            "stop_line_y": 350,
            "road_direction": "south",
            "speed_limit": 60,
            "pixel_per_meter": 10,
            "no_parking_zones": [],
            "lane_lines": [],
        }
        events = plugin.analyze(None, ctx, None)
        print(f"检测到 {len(events)} 个违规事件:")
        for ev in events:
            print(f"  - {ev.behavior_type_cn} (id={ev.vehicle_id}, "
                  f"conf={ev.confidence}, color={ev.color})")
        plugin.shutdown()
    else:
        print("依赖不可用，跳过运行时自检")
