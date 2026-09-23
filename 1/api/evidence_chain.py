# -*- coding: utf-8 -*-
"""
完整证据链模块（GPT §10）

GPT 要求每个事件保存完整证据链，不能只保存 AI 判断结果。
比 ai_trace v3（单帧 AI 判断）更丰富，包含事件全过程证据。

ai_trace v3 作为 ai_judgment 字段嵌入，不破坏现有结构。

证据链结构（GPT §10）：
    摄像头ID → 时间 → 地点 → 车辆ID → 车辆类型 → 车道 → 信号灯状态
    → 车辆轨迹 → 停止线关系 → 关键帧 → 事件视频
    → 本地规则判断结果 → 云端AI判断结果 → AI置信度 → AI分析说明 → 最终事件状态
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("evidence_chain")


@dataclass
class EvidenceChain:
    """完整证据链 — 事件级别的完整上下文

    比 ai_trace v3（单帧AI判断）更丰富，包含事件全过程证据。
    ai_trace v3 作为其中的 ai_judgment 字段嵌入。
    """

    # ===== 基础信息 =====
    camera_id: str = "default"                   # 摄像头 ID
    timestamp: str = ""                          # 事件时间 ISO8601
    location: str = ""                            # 事件地点

    # ===== 车辆信息 =====
    vehicle_id: int = -1                          # track_id
    vehicle_type: str = "unknown"                # 车辆类型（car/truck/bus/motorcycle）
    plate_number: str = ""                        # 车牌号
    plate_color: str = "unknown"                  # 车牌颜色
    lane_id: str = ""                             # 车道 ID（如有）

    # ===== 场景上下文 =====
    traffic_light_state: str = "unknown"         # 信号灯状态（red/green/yellow）
    stop_line_relation: str = "unknown"          # 停止线关系（before/after/crossing）
    trajectory: List[Dict[str, Any]] = field(default_factory=list)  # 轨迹点序列 [(x, y, timestamp)]

    # ===== 视觉证据 =====
    key_frames: List[str] = field(default_factory=list)  # 关键帧路径列表
    event_video_path: str = ""                    # 事件视频路径

    # ===== 判断结果 =====
    rule_judgment: Dict[str, Any] = field(default_factory=dict)  # 本地规则判断结果
    ai_judgment: Dict[str, Any] = field(default_factory=dict)   # 云端 AI 判断结果（嵌入 ai_trace v3）
    ai_confidence: float = 0.0                    # AI 置信度
    ai_explanation: str = ""                      # AI 分析说明

    # ===== 最终状态 =====
    final_status: str = "unknown"                 # 最终事件状态（confirmed/rejected/manual_review）

    def to_dict(self) -> Dict[str, Any]:
        """输出完整证据链字典"""
        return asdict(self)

    def to_json(self, ensure_ascii: bool = False, indent: int = 2) -> str:
        """输出 JSON 字符串

        Args:
            ensure_ascii: 是否转义非 ASCII 字符（默认 False，保留中文）
            indent: 缩进格数（默认 2）
        """
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, indent=indent,
                         default=str)

    def summary(self) -> str:
        """输出人类可读摘要（用于 Web 展示）

        返回多行字符串，包含关键字段。
        """
        lines = [
            f"=== 事件证据链摘要 ===",
            f"摄像头: {self.camera_id}",
            f"时间: {self.timestamp}",
            f"地点: {self.location or '未指定'}",
            f"",
            f"--- 车辆信息 ---",
            f"车辆ID: {self.vehicle_id}",
            f"车辆类型: {self.vehicle_type}",
            f"车牌号: {self.plate_number or '未识别'}",
            f"车牌颜色: {self.plate_color}",
            f"车道: {self.lane_id or '未指定'}",
            f"",
            f"--- 场景上下文 ---",
            f"信号灯状态: {self.traffic_light_state}",
            f"停止线关系: {self.stop_line_relation}",
            f"轨迹点数: {len(self.trajectory)}",
            f"",
            f"--- 视觉证据 ---",
            f"关键帧数量: {len(self.key_frames)}",
            f"事件视频: {self.event_video_path or '无'}",
            f"",
            f"--- 判断结果 ---",
            f"本地规则判断: {json.dumps(self.rule_judgment, ensure_ascii=False, default=str)[:200]}",
            f"AI 置信度: {self.ai_confidence:.2f}",
            f"AI 分析说明: {self.ai_explanation or '无'}",
            f"AI 判断结构版本: {self.ai_judgment.get('version', 'unknown') if self.ai_judgment else '无'}",
            f"",
            f"--- 最终状态 ---",
            f"最终状态: {self.final_status}",
            f"====================",
        ]
        return "\n".join(lines)

    @staticmethod
    def from_traffic_event(event, camera_id: str = "default") -> "EvidenceChain":
        """从 TrafficEvent 构建完整证据链

        Args:
            event: TrafficEvent 对象（来自 traffic_event_engine.py）
            camera_id: 摄像头 ID

        Returns:
            EvidenceChain 实例
        """
        # 从 vehicle_info 提取车辆信息
        vehicle_info = event.vehicle_info or {}
        # 从 scene_context 提取场景信息
        scene_context = event.scene_context or {}
        # 从 rule_judgment 提取规则判断信息
        rule_judgment = event.rule_judgment or {}

        # 解析车牌信息
        plate_number = vehicle_info.get('plate_number', '')
        plate_color = vehicle_info.get('plate_color', 'unknown')

        # 解析信号灯状态
        traffic_light = scene_context.get('traffic_light', 'unknown')

        # 解析停止线关系（基于轨迹和停止线位置推断）
        stop_line = scene_context.get('stop_line', 0)
        trajectory = event.trajectory or []
        stop_line_relation = "unknown"
        if trajectory and stop_line:
            last_y = trajectory[-1].get('y', 0) if trajectory else 0
            if last_y < stop_line:
                stop_line_relation = "before"
            elif last_y > stop_line:
                stop_line_relation = "after"
            else:
                stop_line_relation = "crossing"

        # 最终状态映射
        state_map = {
            'confirmed': 'confirmed',
            'rejected': 'rejected',
            'manual_review': 'manual_review',
            'triggered': 'pending',
            'recording': 'pending',
            'pending_ai': 'pending',
            'ai_reviewed': 'pending',
            'detecting': 'pending',
        }
        final_status = state_map.get(
            event.state.value if hasattr(event.state, 'value') else str(event.state),
            'unknown'
        )

        chain = EvidenceChain(
            camera_id=camera_id,
            timestamp=event.created_at or datetime.now().isoformat(),
            location=scene_context.get('location', ''),
            vehicle_id=event.track_id,
            vehicle_type=vehicle_info.get('class_name', 'unknown'),
            plate_number=plate_number,
            plate_color=plate_color,
            lane_id=scene_context.get('lane', ''),
            traffic_light_state=traffic_light,
            stop_line_relation=stop_line_relation,
            trajectory=trajectory,
            key_frames=list(event.key_frames or []),
            event_video_path=event.event_video_path or '',
            rule_judgment=dict(rule_judgment),
            ai_judgment=dict(event.ai_judgment or {}),
            ai_confidence=float(event.ai_confidence or 0.0),
            ai_explanation=event.ai_explanation or '',
            final_status=final_status,
        )
        logger.debug(f"[EvidenceChain] 从事件 {event.event_id} 构建证据链 "
                    f"vehicle={event.track_id} status={final_status}")
        return chain

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "EvidenceChain":
        """从字典构建证据链（用于从数据库反序列化）"""
        # 兼容字段名差异
        return EvidenceChain(
            camera_id=data.get('camera_id', 'default'),
            timestamp=data.get('timestamp', ''),
            location=data.get('location', ''),
            vehicle_id=data.get('vehicle_id', -1),
            vehicle_type=data.get('vehicle_type', 'unknown'),
            plate_number=data.get('plate_number', ''),
            plate_color=data.get('plate_color', 'unknown'),
            lane_id=data.get('lane_id', ''),
            traffic_light_state=data.get('traffic_light_state', 'unknown'),
            stop_line_relation=data.get('stop_line_relation', 'unknown'),
            trajectory=data.get('trajectory', []),
            key_frames=data.get('key_frames', []),
            event_video_path=data.get('event_video_path', ''),
            rule_judgment=data.get('rule_judgment', {}),
            ai_judgment=data.get('ai_judgment', {}),
            ai_confidence=float(data.get('ai_confidence', 0.0)),
            ai_explanation=data.get('ai_explanation', ''),
            final_status=data.get('final_status', 'unknown'),
        )
