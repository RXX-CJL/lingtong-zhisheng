# -*- coding: utf-8 -*-
"""
治安场景规则插件 - 人员聚集检测

scenario_name = "public_security"
detectable_types = ["crowd_gathering", "abnormal_assembly"]

检测逻辑（简化版）：
1. 检测到 ≥6 个 person 在同一区域
2. 该状态持续 ≥10 秒（可配置，按帧率推算帧数）
3. 用 DBSCAN 聚类（基于 numpy 实现，避免引入 sklearn 重依赖）
   将人员按位置聚类，任一簇 ≥ min_crowd_size 即视为聚集
4. 颜色：黄色 (B,G,R) = (0, 255, 255) — 与 M05 颜色表统一

说明：
- 本插件仅依赖 numpy（不引入 sklearn），用网格化聚类近似 DBSCAN
- 真实场景应结合人员姿态/动作识别（GitHub: crowd counting CSRNet/MCNN），
  本插件仅演示"插件架构可扩展性"
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

# 确保 api/ 目录在 sys.path 中
_API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 配置常量
# ------------------------------------------------------------------

# 治安=黄色 (B, G, R)
SECURITY_COLOR = (0, 255, 255)

# 默认聚集判定阈值
DEFAULT_MIN_CROWD_SIZE = 6        # 单簇最少人数
DEFAULT_CLUSTER_RADIUS = 80.0     # 聚类半径（像素）
DEFAULT_DURATION_SECONDS = 10.0   # 持续时长（秒）
DEFAULT_COOLDOWN_SECONDS = 60.0   # 冷却时间（秒）


class PublicSecurityPlugin(BaseRulePlugin):
    """治安场景违规检测插件 - 人员聚集"""

    scenario_name: str = "public_security"
    detectable_types: List[str] = ["crowd_gathering", "abnormal_assembly"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config=config)
        self._min_crowd_size: int = int(self.config.get("min_crowd_size", DEFAULT_MIN_CROWD_SIZE))
        self._cluster_radius: float = float(self.config.get("cluster_radius", DEFAULT_CLUSTER_RADIUS))
        self._duration_seconds: float = float(self.config.get("duration_seconds", DEFAULT_DURATION_SECONDS))
        self._cooldown_seconds: float = float(self.config.get("cooldown_seconds", DEFAULT_COOLDOWN_SECONDS))

        # 簇历史记录：cluster_key -> (first_seen_ts, last_seen_ts, last_count)
        self._cluster_history: Dict[str, Dict[str, Any]] = {}
        # 已触发冷却：cluster_key -> last_trigger_ts
        self._triggered_clusters: Dict[str, float] = {}
        # 帧率估算（最近 N 帧时间戳）
        self._frame_ts: deque = deque(maxlen=30)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        self._initialized = True
        logger.info(
            f"[PublicSecurityPlugin] 初始化完成 min_crowd={self._min_crowd_size} "
            f"radius={self._cluster_radius} duration={self._duration_seconds}s"
        )

    def shutdown(self) -> None:
        self._cluster_history.clear()
        self._triggered_clusters.clear()
        self._frame_ts.clear()
        self._initialized = False
        logger.info("[PublicSecurityPlugin] 已关闭")

    # ------------------------------------------------------------------
    # 核心分析
    # ------------------------------------------------------------------
    def analyze(self, frame: Any, scene_context: Dict[str, Any],
                tracker: Any) -> List[ViolationEvent]:
        """对单帧执行人员聚集检测"""
        if not self._initialized:
            return []

        now = time.time()
        self._frame_ts.append(now)

        detections = self._extract_detections(scene_context)
        persons = [d for d in detections if d.get("class_name") == "person"]

        # 1. 当前帧人数 < min_crowd_size → 重置历史
        if len(persons) < self._min_crowd_size:
            self._cluster_history.clear()
            return []

        # 2. 提取人员中心点
        centers: List[Tuple[float, float]] = []
        for p in persons:
            c = self._bbox_center(p.get("bbox", [0, 0, 0, 0]))
            if c is not None:
                centers.append(c)

        if len(centers) < self._min_crowd_size:
            self._cluster_history.clear()
            return []

        # 3. 网格化 DBSCAN 聚类
        clusters = self._grid_dbscan(centers, self._cluster_radius)

        # 4. 处理每个簇
        events: List[ViolationEvent] = []
        active_cluster_keys: set = set()

        for cluster_idx, cluster_points in enumerate(clusters):
            if len(cluster_points) < self._min_crowd_size:
                continue

            cluster_key = self._cluster_key(cluster_points)
            active_cluster_keys.add(cluster_key)

            history = self._cluster_history.get(cluster_key)
            if history is None:
                history = {
                    "first_seen_ts": now,
                    "last_seen_ts": now,
                    "last_count": len(cluster_points),
                    "last_center": self._mean_point(cluster_points),
                }
                self._cluster_history[cluster_key] = history
            else:
                history["last_seen_ts"] = now
                history["last_count"] = len(cluster_points)
                history["last_center"] = self._mean_point(cluster_points)

            # 检查持续时长
            duration = history["last_seen_ts"] - history["first_seen_ts"]
            if duration >= self._duration_seconds:
                if self._should_trigger(cluster_key):
                    events.append(self._build_event(
                        cluster_points, cluster_key, history, duration
                    ))

        # 5. 清理失效簇（本帧未出现）
        for cluster_key in list(self._cluster_history.keys()):
            if cluster_key not in active_cluster_keys:
                del self._cluster_history[cluster_key]

        return events

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_detections(scene_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(scene_context, dict):
            return []
        dets = scene_context.get("detections")
        if isinstance(dets, list):
            return dets
        last_result = scene_context.get("last_detection_result")
        if isinstance(last_result, dict):
            dets = last_result.get("detections")
            if isinstance(dets, list):
                return dets
        return []

    @staticmethod
    def _bbox_center(bbox) -> Optional[Tuple[float, float]]:
        try:
            if not bbox or len(bbox) < 4:
                return None
            x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
            return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
        except Exception:
            return None

    @staticmethod
    def _mean_point(points: List[Tuple[float, float]]) -> Tuple[float, float]:
        if not points:
            return (0.0, 0.0)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return (float(np.mean(xs)), float(np.mean(ys)))

    @staticmethod
    def _cluster_key(points: List[Tuple[float, float]]) -> str:
        """生成簇 key（用 100px 网格中心）"""
        if not points:
            return "c_0_0"
        cx, cy = PublicSecurityPlugin._mean_point(points)
        return f"c_{int(cx // 100)}_{int(cy // 100)}"

    @staticmethod
    def _grid_dbscan(points: List[Tuple[float, float]],
                     radius: float) -> List[List[Tuple[float, float]]]:
        """简易网格化 DBSCAN 聚类（不引入 sklearn）

        算法：
        1. 以 radius 为网格大小划分 cells
        2. 相邻 cell（含对角）的点合并为一个簇
        3. 返回每个簇的点列表
        """
        if not points:
            return []

        cell_size = max(radius, 1.0)
        cells: Dict[Tuple[int, int], List[Tuple[float, float]]] = defaultdict(list)
        for p in points:
            cell = (int(p[0] // cell_size), int(p[1] // cell_size))
            cells[cell].append(p)

        # 并查集合并相邻 cell
        visited: set = set()
        clusters: List[List[Tuple[float, float]]] = []

        for cell in cells.keys():
            if cell in visited:
                continue
            # BFS 扩展相邻 8 个 cell
            queue = [cell]
            visited.add(cell)
            cluster_points: List[Tuple[float, float]] = []
            while queue:
                cur = queue.pop()
                cluster_points.extend(cells[cur])
                # 检查 8 邻域
                cx, cy = cur
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nb = (cx + dx, cy + dy)
                        if nb in cells and nb not in visited:
                            visited.add(nb)
                            queue.append(nb)
            if cluster_points:
                clusters.append(cluster_points)

        return clusters

    def _should_trigger(self, cluster_key: str) -> bool:
        """冷却机制"""
        now = time.time()
        last_ts = self._triggered_clusters.get(cluster_key, 0.0)
        if now - last_ts < self._cooldown_seconds:
            return False
        self._triggered_clusters[cluster_key] = now
        return True

    def _build_event(self, cluster_points: List[Tuple[float, float]],
                     cluster_key: str,
                     history: Dict[str, Any],
                     duration: float) -> ViolationEvent:
        """构建 ViolationEvent"""
        cx, cy = history.get("last_center", (0.0, 0.0))
        # 簇 bbox 估计：以中心点为中心，半径为 cluster_radius
        r = self._cluster_radius
        cluster_bbox = [int(cx - r), int(cy - r), int(cx + r), int(cy + r)]

        # 置信度：人数权重 + 持续时长权重
        count = history.get("last_count", len(cluster_points))
        count_score = min(1.0, count / 10.0)
        duration_score = min(1.0, duration / (self._duration_seconds * 2))
        confidence = round(min(0.98, 0.5 + 0.3 * count_score + 0.2 * duration_score), 3)

        return ViolationEvent(
            behavior_type="crowd_gathering",
            behavior_type_cn="人员聚集",
            confidence=confidence,
            is_violation=True,
            evidence={
                "cluster_key": cluster_key,
                "cluster_center": [float(cx), float(cy)],
                "cluster_bbox": cluster_bbox,
                "person_count": int(count),
                "duration_seconds": round(duration, 2),
                "min_crowd_size": self._min_crowd_size,
                "cluster_radius": self._cluster_radius,
                "scene": "public_security",
            },
            vehicle_id=-1,
            timestamp=datetime.now().isoformat(),
            color=SECURITY_COLOR,
        )


# 模块自检
if __name__ == "__main__":  # pragma: no cover
    plugin = PublicSecurityPlugin()
    print(f"插件: {plugin}")
    print(f"可检测类型: {plugin.detectable_types}")
    plugin.initialize()

    # 构造 8 人在同一区域的模拟场景
    fake_ctx = {
        "frame_width": 1280,
        "frame_height": 720,
        "detections": [
            {"class_name": "person", "confidence": 0.9,
             "bbox": [300 + i * 20, 300 + i * 15, 360 + i * 20, 480 + i * 15]}
            for i in range(8)
        ],
    }

    print(f"模拟 {len(fake_ctx['detections'])} 人聚集，duration={plugin._duration_seconds}s")
    events_total = 0
    # 模拟 12 秒，每 0.5s 一帧
    import time as _t
    start = _t.time()
    for i in range(30):
        events = plugin.analyze(None, fake_ctx, None)
        events_total += len(events)
        if events:
            ev = events[0]
            print(f"  帧{i}: 触发 {ev.behavior_type_cn} conf={ev.confidence} "
                  f"count={ev.evidence.get('person_count')} duration={ev.evidence.get('duration_seconds')}s")
        _t.sleep(0.5)
    elapsed = _t.time() - start
    print(f"总触发事件数: {events_total}, 耗时 {elapsed:.1f}s")
    assert events_total >= 1, "应至少触发一次人员聚集事件"
    print("✓ PublicSecurityPlugin 自检通过")
    plugin.shutdown()
