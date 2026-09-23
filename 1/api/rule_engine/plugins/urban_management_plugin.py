# -*- coding: utf-8 -*-
"""
城管场景规则插件 - 占道经营检测

scenario_name = "urban_management"
detectable_types = ["street_stall", "illegal_occupancy"]

检测逻辑（简化版）：
1. 检测到 person + 摊位物品（backpack/handbag/suitcase/bottle/bowl 等）在道路边缘区域
2. 同一区域连续 N 帧（默认 8 帧）出现该组合 → 触发"疑似占道经营"
3. 颜色：蓝色 (B,G,R) = (255, 0, 0) — 与 M05 颜色表统一

说明：
- 本插件不依赖外部追踪器，仅基于 detections 列表做空间聚合
- 道路边缘区域通过 frame 尺寸估算（左右各 20% 宽度）
- 真实场景应使用专门训练的"摊位检测 YOLO 模型"，
  本插件仅演示"插件架构可扩展性"，详见 docs/plugin_development_guide.md
"""

import os
import sys
import logging
import time
from datetime import datetime
from collections import defaultdict, deque
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

from ..base_plugin import BaseRulePlugin, ViolationEvent

# 确保 api/ 目录在 sys.path 中（独立调用 analyze 时可用）
_API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 配置常量
# ------------------------------------------------------------------

# 摊位疑似物品 COCO 类别（person 在此仅作"人员存在"判断）
STALL_ITEM_CLASSES = {
    "backpack", "handbag", "suitcase", "bottle", "bowl",
    "cup", "vase", "backpacks", "bag", "table", "chair"
}

# 颜色：城管=蓝色 (B, G, R)
URBAN_COLOR = (255, 0, 0)

# 占道确认帧数（连续 N 帧组合出现才触发）
DEFAULT_CONFIRM_FRAMES = 8

# 道路边缘区域宽度比例（左右各 20%）
DEFAULT_EDGE_RATIO = 0.20

# 人员与摊位物品的最大距离（归一化到 [0,1]，按 bbox 中心点距离）
DEFAULT_PROXIMITY_THRESHOLD = 0.18


class UrbanManagementPlugin(BaseRulePlugin):
    """城管场景违规检测插件 - 占道经营"""

    scenario_name: str = "urban_management"
    detectable_types: List[str] = ["street_stall", "illegal_occupancy"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config=config)
        # 可配置项
        self._confirm_frames: int = int(self.config.get("confirm_frames", DEFAULT_CONFIRM_FRAMES))
        self._edge_ratio: float = float(self.config.get("edge_ratio", DEFAULT_EDGE_RATIO))
        self._proximity: float = float(self.config.get("proximity", DEFAULT_PROXIMITY_THRESHOLD))
        # 区域历史记录：region_key -> deque[bool]（True 表示该帧触发组合）
        self._region_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self._confirm_frames)
        )
        # 已触发事件去重：region_key -> last_trigger_ts
        self._triggered_regions: Dict[str, float] = {}
        # 冷却时间（秒），同一区域在冷却期内不重复触发
        self._cooldown_seconds: float = float(self.config.get("cooldown_seconds", 30.0))
        self._frame_counter: int = 0

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        self._initialized = True
        logger.info(
            f"[UrbanManagementPlugin] 初始化完成 confirm_frames={self._confirm_frames} "
            f"edge_ratio={self._edge_ratio} proximity={self._proximity}"
        )

    def shutdown(self) -> None:
        self._region_history.clear()
        self._triggered_regions.clear()
        self._initialized = False
        logger.info("[UrbanManagementPlugin] 已关闭")

    # ------------------------------------------------------------------
    # 核心分析
    # ------------------------------------------------------------------
    def analyze(self, frame: Any, scene_context: Dict[str, Any],
                tracker: Any) -> List[ViolationEvent]:
        """对单帧执行占道经营检测

        Args:
            frame: 视频帧（本实现未直接使用，仅用尺寸从 scene_context 获取）
            scene_context: 应包含 "detections" 列表与可选的 "frame_width" / "frame_height"
            tracker: 未使用

        Returns:
            ViolationEvent 列表
        """
        if not self._initialized:
            return []

        self._frame_counter += 1

        detections = self._extract_detections(scene_context)
        if not detections:
            # 清空历史，避免长期未检测导致 stale 触发
            self._region_history.clear()
            return []

        frame_width, frame_height = self._get_frame_size(scene_context, frame)
        if frame_width <= 0 or frame_height <= 0:
            return []

        # 1. 提取人员与摊位物品 bbox
        persons = [d for d in detections if d.get("class_name") == "person"]
        stall_items = [d for d in detections if d.get("class_name") in STALL_ITEM_CLASSES]

        if not persons or not stall_items:
            # 当前帧未形成组合，记录 False
            self._record_region_history("global", False)
            return []

        # 2. 判断是否在道路边缘区域（左右各 edge_ratio 宽度）
        edge_left_max = frame_width * self._edge_ratio
        edge_right_min = frame_width * (1.0 - self._edge_ratio)

        # 3. 按"人员-摊位物品"对计算距离，并划分区域
        events: List[ViolationEvent] = []
        triggered_regions_this_frame: set = set()

        for person in persons:
            p_center = self._bbox_center(person.get("bbox", [0, 0, 0, 0]))
            if p_center is None:
                continue
            # 是否在边缘区域
            in_edge = p_center[0] <= edge_left_max or p_center[0] >= edge_right_min
            if not in_edge:
                continue

            # 寻找最近的摊位物品
            for item in stall_items:
                i_center = self._bbox_center(item.get("bbox", [0, 0, 0, 0]))
                if i_center is None:
                    continue
                # 归一化距离
                norm_dist = self._normalized_distance(p_center, i_center, frame_width, frame_height)
                if norm_dist > self._proximity:
                    continue

                # 命中组合，划分区域（用 100px 网格）
                region_key = self._region_key(p_center, frame_width)
                triggered_regions_this_frame.add(region_key)

                # 记录该区域本帧命中
                self._record_region_history(region_key, True)

                # 检查是否满足连续 confirm_frames 帧
                if self._is_region_confirmed(region_key):
                    if self._should_trigger(region_key):
                        events.append(self._build_event(
                            person, item, region_key, frame_width, frame_height,
                            norm_dist
                        ))
                break  # 一个 person 只配一个 item

        # 对本帧未命中的区域记录 False（保持滑动窗口准确性）
        for region_key in list(self._region_history.keys()):
            if region_key not in triggered_regions_this_frame and region_key != "global":
                self._record_region_history(region_key, False)

        return events

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_detections(scene_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从 scene_context 提取 detections 列表"""
        if not isinstance(scene_context, dict):
            return []
        dets = scene_context.get("detections")
        if isinstance(dets, list):
            return dets
        # 兼容嵌套结构
        last_result = scene_context.get("last_detection_result")
        if isinstance(last_result, dict):
            dets = last_result.get("detections")
            if isinstance(dets, list):
                return dets
        return []

    @staticmethod
    def _get_frame_size(scene_context: Dict[str, Any], frame: Any) -> Tuple[int, int]:
        """获取帧尺寸 (width, height)"""
        w = int(scene_context.get("frame_width", 0) or 0)
        h = int(scene_context.get("frame_height", 0) or 0)
        if w <= 0 or h <= 0 and frame is not None:
            try:
                if hasattr(frame, "shape"):
                    h, w = int(frame.shape[0]), int(frame.shape[1])
            except Exception:
                pass
        return w, h

    @staticmethod
    def _bbox_center(bbox) -> Optional[Tuple[float, float]]:
        """计算 bbox 中心点"""
        try:
            if not bbox or len(bbox) < 4:
                return None
            x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
            return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
        except Exception:
            return None

    @staticmethod
    def _normalized_distance(p1, p2, frame_width, frame_height) -> float:
        """计算归一化欧氏距离"""
        dx = (p1[0] - p2[0]) / max(frame_width, 1)
        dy = (p1[1] - p2[1]) / max(frame_height, 1)
        return float((dx * dx + dy * dy) ** 0.5)

    @staticmethod
    def _region_key(center, frame_width) -> str:
        """将中心点映射到 100px 网格的 region key"""
        grid_x = int(center[0] // 100)
        grid_y = int(center[1] // 100)
        return f"r_{grid_x}_{grid_y}"

    def _record_region_history(self, region_key: str, hit: bool) -> None:
        self._region_history[region_key].append(hit)

    def _is_region_confirmed(self, region_key: str) -> bool:
        """判断该区域是否满足连续 confirm_frames 帧命中"""
        history = self._region_history.get(region_key)
        if not history or len(history) < self._confirm_frames:
            return False
        # 最近 confirm_frames 帧全部命中
        recent = list(history)[-self._confirm_frames:]
        return all(recent)

    def _should_trigger(self, region_key: str) -> bool:
        """冷却机制：同一区域在 cooldown_seconds 内不重复触发"""
        now = time.time()
        last_ts = self._triggered_regions.get(region_key, 0.0)
        if now - last_ts < self._cooldown_seconds:
            return False
        self._triggered_regions[region_key] = now
        return True

    def _build_event(self, person, item, region_key: str,
                     frame_width: int, frame_height: int,
                     norm_dist: float) -> ViolationEvent:
        """构建 ViolationEvent"""
        p_bbox = person.get("bbox", [0, 0, 0, 0])
        i_bbox = item.get("bbox", [0, 0, 0, 0])
        # 取人员与物品 bbox 的合并区域作为事件位置
        merged_bbox = [
            min(p_bbox[0], i_bbox[0]),
            min(p_bbox[1], i_bbox[1]),
            max(p_bbox[2], i_bbox[2]),
            max(p_bbox[3], i_bbox[3]),
        ]
        # 置信度：人员置信度 * 物品置信度 * 距离权重
        p_conf = float(person.get("confidence", 0.5))
        i_conf = float(item.get("confidence", 0.5))
        distance_weight = max(0.3, 1.0 - norm_dist)
        confidence = min(1.0, p_conf * i_conf * distance_weight + 0.2)

        return ViolationEvent(
            behavior_type="street_stall",
            behavior_type_cn="疑似占道经营",
            confidence=round(confidence, 3),
            is_violation=True,
            evidence={
                "region_key": region_key,
                "person_bbox": p_bbox,
                "stall_item_class": item.get("class_name", ""),
                "stall_item_bbox": i_bbox,
                "merged_bbox": merged_bbox,
                "normalized_distance": round(norm_dist, 4),
                "confirm_frames": self._confirm_frames,
                "scene": "urban_management",
            },
            vehicle_id=-1,
            timestamp=datetime.now().isoformat(),
            color=URBAN_COLOR,
        )


# 模块自检（直接运行时）
if __name__ == "__main__":  # pragma: no cover
    plugin = UrbanManagementPlugin()
    print(f"插件: {plugin}")
    print(f"可检测类型: {plugin.detectable_types}")
    plugin.initialize()

    # 构造模拟测试场景：frame 1280x720，左边缘有 person + backpack
    fake_frame = None
    fake_ctx = {
        "frame_width": 1280,
        "frame_height": 720,
        "detections": [
            {"class_name": "person", "confidence": 0.92, "bbox": [50, 300, 150, 600]},
            {"class_name": "backpack", "confidence": 0.78, "bbox": [120, 400, 220, 550]},
            {"class_name": "car", "confidence": 0.88, "bbox": [400, 300, 700, 500]},
        ],
    }

    # 连续 confirm_frames 帧命中
    events_total = 0
    for i in range(plugin._confirm_frames + 2):
        events = plugin.analyze(fake_frame, fake_ctx, None)
        events_total += len(events)
        if events:
            ev = events[0]
            print(f"  帧{i}: 触发 {ev.behavior_type_cn} conf={ev.confidence} color={ev.color}")

    print(f"总触发事件数: {events_total}")
    assert events_total >= 1, "应至少触发一次占道经营事件"
    print("✓ UrbanManagementPlugin 自检通过")
    plugin.shutdown()
