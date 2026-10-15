# -*- coding: utf-8 -*-
"""
交通事件引擎 + 事件状态机（GPT §6-7）

基于规则/状态机/轨迹/信号灯发现疑似交通事件，并为事件设计 8 状态生命周期。

核心设计：
- EventState 枚举 8 状态（GPT §7）
- TrafficEvent 数据类（GPT §10 证据字段）
- TrafficEventEngine 事件引擎（不直接调用云端 AI，只生成提交请求 dict）

状态转换规则（严格按 GPT §7）：
    DETECTING → TRIGGERED（规则满足触发条件）
    TRIGGERED → RECORDING（开始录制事件视频）
    RECORDING → PENDING_AI（录制完成提交云端）
    PENDING_AI → AI_REVIEWED（云端返回结果）
    AI_REVIEWED → CONFIRMED / REJECTED / MANUAL_REVIEW
    MANUAL_REVIEW → CONFIRMED / REJECTED

冷却机制：同一 track_id + event_type 在 60 秒内不重复触发（可配置）。
"""

import os
import time
import uuid
import logging
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("traffic_event_engine")


def wall_time_to_datetime(wall_time):
    """Convert a trusted Unix wall-clock timestamp; never pass source-video-relative time here."""
    if wall_time in (None, 0, "", False):
        return None
    try:
        return datetime.fromtimestamp(float(wall_time))
    except (TypeError, ValueError, OSError, OverflowError):
        return None


# ==========================================================================
# EventState 枚举（GPT §7 的 8 状态）
# ==========================================================================

class EventState(Enum):
    """交通事件 8 状态生命周期"""
    DETECTING = "detecting"          # 正在检测，规则引擎持续评估
    TRIGGERED = "triggered"          # 已触发疑似事件
    RECORDING = "recording"          # 正在等待事件结束并录制完整视频
    PENDING_AI = "pending_ai"        # 等待云端 AI 分析
    AI_REVIEWED = "ai_reviewed"      # 云端 AI 已分析
    CONFIRMED = "confirmed"          # 确认违法
    REJECTED = "rejected"            # 排除事件
    MANUAL_REVIEW = "manual_review"  # 需人工复核


# 合法的状态转换映射（严格按 GPT §7）
VALID_TRANSITIONS: Dict[EventState, List[EventState]] = {
    EventState.DETECTING: [EventState.TRIGGERED],
    EventState.TRIGGERED: [EventState.RECORDING, EventState.REJECTED],  # 允许直接排除（误触）
    EventState.RECORDING: [EventState.PENDING_AI, EventState.REJECTED],  # 录制中也可放弃
    # 云端请求失败时允许明确转人工复核，避免事件永久停留在 pending_ai。
    EventState.PENDING_AI: [EventState.AI_REVIEWED, EventState.MANUAL_REVIEW],
    EventState.AI_REVIEWED: [EventState.CONFIRMED, EventState.REJECTED, EventState.MANUAL_REVIEW],
    EventState.MANUAL_REVIEW: [EventState.CONFIRMED, EventState.REJECTED],
    EventState.CONFIRMED: [],   # 终态
    EventState.REJECTED: [],    # 终态
}

# 终态集合
TERMINAL_STATES = {EventState.CONFIRMED, EventState.REJECTED}


# ==========================================================================
# TrafficEvent 数据类（GPT §10 证据字段）
# ==========================================================================

@dataclass
class TrafficEvent:
    """交通事件对象 — 拥有完整生命周期

    字段对应 GPT §10 的证据链要求，比 ai_trace v3（单帧AI判断）更丰富。
    """
    # 基础标识
    event_id: str                     # 唯一 ID（uuid 或 timestamp+track_id）
    event_type: str                   # 事件类型（red_light / wrong_way / illegal_park / no_helmet）
    track_id: int                     # 关联车辆 track_id
    state: EventState = EventState.DETECTING  # 当前状态

    # 时间信息
    trigger_time: float = 0.0          # 触发时间戳
    # ★★2026-10-10 由 DSH 新增：**墙钟时间**（秒，time.time()），与 trigger_time 分开。
    #
    # 为什么必须分开：
    #   `trigger_time` 现在装的是**视频时间**（回放本地视频时由 realtime_detector._now()
    #   给出，(frame_count - 循环基准)/源fps），它的用途是"**在帧缓存里定位关键帧**"
    #   —— 必须和帧缓存的时间戳同源，这一点没错。
    #   但它**不是** Unix 时间戳，不能拿去当墙上时间用。
    #   原实现落库时直接 `datetime.fromtimestamp(trigger_time)`：
    #     · trigger_time=10.95（视频第 10.95 秒）-> **1970-01-01 08:00:10**
    #       （实测：本轮事件表里真的出现了这种 1970 行）
    #     · trigger_time 为负（基准脱节时）-> fromtimestamp 抛 OSError ->
    #       被 except 兜成 datetime.now() -> **看起来正常，其实是巧合**
    #   前端/小程序展示的是"违规发生时间"，必须是**真实墙上时间**。
    wall_time: float = 0.0             # 真实墙上时间（time.time()）
    created_at: str = ""               # 创建时间 ISO8601
    updated_at: str = ""               # 更新时间 ISO8601

    # 事件上下文
    vehicle_info: Dict[str, Any] = field(default_factory=dict)   # 车辆信息（type/bbox/plate）
    scene_context: Dict[str, Any] = field(default_factory=dict)  # 场景上下文（traffic_light/lane/stop_line）
    trajectory: List[Dict[str, Any]] = field(default_factory=list)  # 车辆轨迹点序列

    # 证据
    key_frames: List[str] = field(default_factory=list)   # 关键帧路径列表
    event_video_path: str = ""         # 事件视频路径
    rule_judgment: Dict[str, Any] = field(default_factory=dict)  # 本地规则判断结果
    ai_judgment: Dict[str, Any] = field(default_factory=dict)   # 云端 AI 判断结果（ai_trace v3）
    ai_confidence: float = 0.0          # AI 置信度
    ai_explanation: str = ""            # AI 分析说明

    # 生命周期管理
    state_history: List[Dict[str, Any]] = field(default_factory=list)  # 状态变更历史
    cooldown_until: float = 0.0         # 冷却到期时间（避免同一车辆重复触发）

    def __post_init__(self):
        """初始化后处理：补全时间戳"""
        if not self.event_id:
            self.event_id = f"evt_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        if not self.trigger_time:
            self.trigger_time = time.time()
        # ★2026-10-10：墙钟单独记一份（调用方通常已经显式传了本地视频时间给
        #   trigger_time，此时这里补的是"违规真实发生的那一刻"）
        if not self.wall_time:
            self.wall_time = time.time()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.state_history:
            self.state_history.append({
                'timestamp': self.trigger_time,
                'old_state': None,
                'new_state': self.state.value,
                'reason': '事件创建',
            })

    def to_dict(self) -> Dict[str, Any]:
        """输出字典（state 转为字符串，便于序列化）"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'track_id': self.track_id,
            'state': self.state.value,
            'trigger_time': self.trigger_time,
            'wall_time': self.wall_time,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'vehicle_info': self.vehicle_info,
            'scene_context': self.scene_context,
            'trajectory': self.trajectory,
            'key_frames': self.key_frames,
            'event_video_path': self.event_video_path,
            'rule_judgment': self.rule_judgment,
            'ai_judgment': self.ai_judgment,
            'ai_confidence': self.ai_confidence,
            'ai_explanation': self.ai_explanation,
            'state_history': self.state_history,
            'cooldown_until': self.cooldown_until,
        }


# ==========================================================================
# TrafficEventEngine 事件引擎
# ==========================================================================

class TrafficEventEngine:
    """交通事件引擎 — 基于规则+状态机发现和管理交通事件

    不直接调用云端 AI。只负责：
    1. 发现疑似事件（基于规则插件输出）
    2. 管理事件生命周期（状态转换）
    3. 触发视频缓存提取
    4. 触发云端 AI 分析请求（生成提交 dict，不实际发送）
    """

    def __init__(self, rule_plugins: Optional[List] = None,
                 frame_buffer=None,
                 cooldown_sec: int = 60,
                 clock=None):
        """初始化事件引擎

        Args:
            rule_plugins: 规则插件列表（从 PluginLoader 加载），None 表示无插件
            frame_buffer: CircularFrameBuffer 实例（用于事件视频提取）
            cooldown_sec: 同车同类型事件冷却秒数（默认 60s）
            clock: **可注入时钟**（返回秒数的无参可调用对象）。

                ★2026-10-06 由 DSH 新增。默认 None = 用墙钟 `time.time()`，
                **接真实摄像头时行为完全不变**。

                为什么要注入：**回放本地视频时，墙钟与视频时间不是一回事**。
                检测慢于视频（实测 2.66 fps vs 源 20 fps，慢 ~7.5 倍），
                于是一个"前后 5 秒"的事件片段窗口按墙钟取，实际会取到
                **视频里 80 秒之后**的帧 —— 证据里车早就开走了。
                实测 AI 复核因此判"画面中无任何车辆"，
                所有违规都被 REJECTED（trigger_time 与帧缓存时间戳不同源）。

                回放视频时应传入"视频时间"（帧号/源帧率），
                并且**每循环一圈把视频时间归零**，既保证窗口对齐，
                也让"同一违规每圈只报一次"成立。
        """
        self.rule_plugins = rule_plugins or []
        self.frame_buffer = frame_buffer
        self.cooldown_sec = cooldown_sec
        self._clock = clock
        # 事件存储：event_id → TrafficEvent
        self._events: Dict[str, TrafficEvent] = {}
        # 冷却记录：(track_id, event_type) → cooldown_until 时间戳
        self._cooldowns: Dict[tuple, float] = {}
        self._lock = threading.Lock()
        logger.info(f"[TrafficEventEngine] 初始化: plugins={len(self.rule_plugins)} "
                    f"frame_buffer={'有' if frame_buffer else '无'} cooldown={cooldown_sec}s "
                    f"clock={'注入' if clock else '墙钟'}")

    def set_clock(self, clock):
        """替换时钟（供 realtime_detector 按数据源类型注入）。

        传 None 恢复墙钟。
        """
        self._clock = clock
        logger.info(f"[TrafficEventEngine] 时钟已切换为 {'注入时钟' if clock else '墙钟'}")

    def _now(self) -> float:
        """当前时间（默认墙钟；注入了就用注入的）。

        **引擎内所有时间比较必须走这里**，否则会出现"用视频时间创建事件、
        却用墙钟判断冷却"的混用（曾因此导致冷却失效、事件重复触发）。
        """
        if self._clock is not None:
            try:
                return float(self._clock())
            except Exception:
                pass
        return time.time()

    def process_frame(self, frame, detections: List, tracked_vehicles: Dict,
                      scene_context: Dict) -> List[TrafficEvent]:
        """处理一帧 — 调用规则插件评估，发现疑似事件则创建/更新事件

        Args:
            frame: 当前视频帧
            detections: YOLO 检测结果列表
            tracked_vehicles: 跟踪车辆字典 {track_id: vehicle_info}
            scene_context: 场景上下文（traffic_light/lane/stop_line）

        Returns:
            新创建或更新状态的 TrafficEvent 列表
        """
        new_events = []
        if not self.rule_plugins:
            return new_events

        # 调用规则插件分析当前帧
        all_violations = []
        for plugin in self.rule_plugins:
            try:
                if hasattr(plugin, 'is_enabled') and not plugin.is_enabled:
                    continue
                violations = plugin.analyze(frame, scene_context, tracked_vehicles)
                if violations:
                    all_violations.extend(violations)
            except Exception as e:
                logger.warning(f"[TrafficEventEngine] 插件 {getattr(plugin, 'scenario_name', '?')} 分析异常: {e}")

        # 对每个违规触发事件
        for v in all_violations:
            track_id = getattr(v, 'vehicle_id', -1)
            event_type = getattr(v, 'behavior_type', 'unknown')
            if track_id < 0 or event_type == 'unknown':
                continue

            # 检查冷却
            if not self._check_cooldown(track_id, event_type):
                logger.debug(f"[TrafficEventEngine] {track_id}/{event_type} 冷却中，跳过")
                continue

            # 提取车辆信息和场景上下文
            vehicle_info = self._extract_vehicle_info(track_id, tracked_vehicles, v)
            # 触发新事件
            event = self._trigger_event(v, vehicle_info, scene_context, event_type)
            if event:
                new_events.append(event)

        return new_events

    def _extract_vehicle_info(self, track_id: int, tracked_vehicles: Dict,
                              violation) -> Dict[str, Any]:
        """从跟踪车辆字典提取车辆信息"""
        v_info = tracked_vehicles.get(track_id, {}) if isinstance(tracked_vehicles, dict) else {}

        # speed/direction 在上游可能是字符串（如 '85.6 km/h'），若原样传给下游的
        # f"{speed:.1f}" 会抛 ValueError: Unknown format code 'f' for object of type 'str'，
        # 导致事件级 AI 仲裁整体失效（事件长期停留在 pending_ai）。
        # 此处统一强制为数值类型（2026-10-02 由 DSH 修复）。
        def _num(val, default=0.0):
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                import re as _re
                m = _re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", val)
                if m:
                    try:
                        return float(m.group(0))
                    except ValueError:
                        pass
            return default

        return {
            'track_id': track_id,
            'bbox': v_info.get('bbox', getattr(violation, 'evidence', {}).get('bbox', [])),
            'class_name': v_info.get('class_name', 'unknown'),
            # 没有原始置信度时保留 None；不可伪造为 0.00 再交给云端审核。
            'confidence': _num(v_info.get('confidence', getattr(violation, 'confidence', None)), default=None),
            'speed': _num(v_info.get('speed', 0.0)),
            'direction': _num(v_info.get('direction', 0.0)),
            'plate_number': v_info.get('plate_number', ''),
        }

    def _trigger_event(self, violation, vehicle_info: Dict, scene_context: Dict,
                       event_type: str) -> Optional[TrafficEvent]:
        """触发新事件 — 创建 TrafficEvent 对象，状态 → TRIGGERED

        Args:
            violation: ViolationEvent 对象（来自规则插件）
            vehicle_info: 车辆信息字典
            scene_context: 场景上下文
            event_type: 事件类型

        Returns:
            新创建的 TrafficEvent，或 None（如果创建失败）
        """
        track_id = vehicle_info.get('track_id', -1)
        now = self._now()
        # ★2026-10-06 诊断日志（DSH 临时加入，用于坐实事件洪泛的根因）：
        # 打印每次触发事件时的 track_id / 类型 / 冷却键当前值。
        # 若同一辆车在一圈内打印出多个不同的 track_id -> 是追踪关联问题；
        # 若 track_id 始终相同却仍多次触发   -> 是冷却键/状态机问题。
        # 定位完即可删除（搜 DIAG-TRACK 可找到全部插入点）。
        try:
            _key = (track_id, event_type)
            _cd = self._cooldowns.get(_key)
            logger.info("[DIAG-TRACK] 触发事件 类型=%s track_id=%s 时间=%.2f "
                        "冷却键=%s 已有冷却=%s"
                        % (event_type, track_id, now, _key,
                           ("%.2f" % _cd) if _cd else "无"))
        except Exception:
            pass
        event = TrafficEvent(
            event_id=f"evt_{int(now*1000)}_{track_id}_{uuid.uuid4().hex[:6]}",
            event_type=event_type,
            track_id=track_id,
            state=EventState.TRIGGERED,
            trigger_time=now,
            vehicle_info=vehicle_info,
            scene_context=dict(scene_context) if scene_context else {},
            trajectory=self._extract_trajectory(vehicle_info),
            rule_judgment={
                'behavior_type': getattr(violation, 'behavior_type', event_type),
                'confidence': getattr(violation, 'confidence', 0.0),
                'is_violation': getattr(violation, 'is_violation', True),
                'evidence': getattr(violation, 'evidence', {}),
                'color': getattr(violation, 'color', '#FF0000'),
            },
        )
        # 设置冷却到期时间
        event.cooldown_until = now + self.cooldown_sec

        with self._lock:
            self._events[event.event_id] = event
            self._cooldowns[(track_id, event_type)] = event.cooldown_until

        # 创建即落库（2026-10-03 由 DSH 新增）
        # 初始状态 TRIGGERED 不经 _update_event_state，需在此显式插入，
        # 否则事件在库里不存在，后续证据链落库会找不到行。
        self._persist_event(event)

        logger.info(f"[TrafficEventEngine] 触发事件 {event.event_id} type={event_type} "
                    f"track={track_id} state=TRIGGERED")
        return event

    # ------------------------------------------------------------------
    # 事件持久化（2026-10-03 由 DSH 新增）
    # ⚠ 背景：本引擎原为**纯内存**实现，事件从不写入 traffic_events 表。
    # 实测证据：状态接口显示内存有 42 个事件，而数据库最新 created_at 停留在
    # 2026-10-02 19:13:29（541 行 created_at 全在同一秒 = 迁移脚本批量导入）。
    # 后果：① 重启即丢失（含终态）② evidence_chain 永远为空 ③ 前端事件中心
    # 只看到旧数据 ④ 违反"证据链可追溯"红线。
    # 详见 docs/EVENT_PERSISTENCE_AUDIT.md
    # ------------------------------------------------------------------
    def _persist_event(self, event: "TrafficEvent") -> bool:
        """把事件 upsert 到 traffic_events 表（存在则更新，不存在则插入）

        用 event_id 作为唯一键。任何状态流转都会调用（见 _update_event_state），
        因此事件一创建（TRIGGERED）就会落库，后续状态变化同步更新。
        """
        try:
            import json as _json

            from database import SessionLocal
            # 模型类名是 TrafficEventRecord（表 traffic_events）
            from models import TrafficEventRecord

            def _j(v):
                try:
                    return _json.dumps(v, ensure_ascii=False, default=str)
                except Exception:
                    return _json.dumps(str(v), ensure_ascii=False)

            # trigger_time: dataclass 用 float 时间戳，DB 用 DateTime
            #
            # ★★2026-10-10 由 DSH 修正：**落库必须用墙钟（wall_time），不能用 trigger_time**。
            #   trigger_time 是**视频时间**（用于在帧缓存里定位关键帧），不是 Unix 时间戳：
            #     · 用它当时间戳 -> 事件表出现 1970-01-01 08:00:10 这种行（本轮实测）；
            #     · 它为负时 fromtimestamp 抛 OSError -> 被 except 兜成 datetime.now()
            #       -> 表面正常，掩盖了这个错误（14 条负时间事件就是这么"混过去"的）。
            #   兼容：老事件对象没有 wall_time 字段时退回旧算法（保证不炸）。
            tt = getattr(event, 'wall_time', 0) or getattr(event, 'trigger_time', None)
            try:
                tt_dt = datetime.fromtimestamp(float(tt)) if tt else datetime.now()
            except (TypeError, ValueError, OSError, OverflowError):
                tt_dt = datetime.now()

            vals = {
                'event_type': event.event_type,
                'track_id': event.track_id,
                'state': (event.state.value if hasattr(event.state, 'value') else str(event.state)),
                'trigger_time': tt_dt,
                'vehicle_info': _j(event.vehicle_info),
                'scene_context': _j(event.scene_context),
                'trajectory': _j(event.trajectory),
                'key_frames': _j(event.key_frames),
                'event_video_path': event.event_video_path or '',
                'rule_judgment': _j(event.rule_judgment),
                'ai_judgment': _j(event.ai_judgment) if event.ai_judgment else None,
                'ai_confidence': float(event.ai_confidence or 0.0),
                'ai_explanation': event.ai_explanation or '',
                'state_history': _j(event.state_history),
            }

            db = SessionLocal()
            try:
                row = db.query(TrafficEventRecord).filter(
                    TrafficEventRecord.event_id == event.event_id).first()
                if row is None:
                    row = TrafficEventRecord(event_id=event.event_id, **vals)
                    db.add(row)
                    _action = 'INSERT'
                else:
                    for k, v in vals.items():
                        setattr(row, k, v)
                    _action = 'UPDATE'
                db.commit()
                logger.debug(f"[TrafficEventEngine] 事件落库 {_action} {event.event_id} "
                             f"state={vals['state']}")
                return True
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[TrafficEventEngine] 事件落库失败 {getattr(event,'event_id','?')}: "
                           f"{type(e).__name__}: {str(e)[:150]}")
            return False

    def _extract_trajectory(self, vehicle_info: Dict) -> List[Dict[str, Any]]:
        """从车辆信息提取轨迹点（简化版，真实场景从 tracker 获取）"""
        bbox = vehicle_info.get('bbox', [])
        if not bbox or len(bbox) < 4:
            return []
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        return [{'x': cx, 'y': cy, 'timestamp': time.time()}]

    def reject(self, event_id: str, reason: str = ""):
        """直接排除事件（2026-10-03 由 DSH 新增）

        用途：本地就能判定"无法验证"的事件（例如**未标定的超速** —— 云端视觉
        模型无法从图像测速，送审必然被判 rejected 且白烧 token）。
        与"AI 判否"的区别在于 reason 里会写明具体原因，可追溯。

        Args:
            event_id: 事件 ID
            reason: 排除原因（建议写明"为何不送 AI"）
        """
        with self._lock:
            event = self._events.get(event_id)
        if not event:
            raise KeyError(f"事件不存在: {event_id}")
        self._update_event_state(event, EventState.REJECTED,
                                 reason=reason or "本地判定排除")

    def _update_event_state(self, event: TrafficEvent, new_state: EventState,
                            reason: str = ""):
        """更新事件状态 — 记录状态历史

        Args:
            event: 事件对象
            new_state: 新状态
            reason: 变更原因

        Raises:
            ValueError: 如果状态转换非法
        """
        old_state = event.state
        if new_state == old_state:
            return  # 无变化

        # 校验转换合法性
        allowed = VALID_TRANSITIONS.get(old_state, [])
        if new_state not in allowed:
            raise ValueError(f"非法状态转换: {old_state.value} → {new_state.value} "
                            f"(允许: {[s.value for s in allowed]})")

        event.state = new_state
        event.updated_at = datetime.now().isoformat()
        event.state_history.append({
            'timestamp': time.time(),
            'old_state': old_state.value,
            'new_state': new_state.value,
            'reason': reason or f"{old_state.value} → {new_state.value}",
        })
        logger.info(f"[TrafficEventEngine] 事件 {event.event_id} 状态变更: "
                    f"{old_state.value} → {new_state.value} reason={reason}")

        # 状态变化 -> 同步落库（2026-10-03 由 DSH 新增）
        # 这是所有状态流转的唯一收口点，在此 upsert 可保证库里状态与内存一致。
        self._persist_event(event)

    def _check_cooldown(self, track_id: int, event_type: str) -> bool:
        """检查冷却期 — 避免同一车辆短时间内重复触发

        Returns:
            True 表示可以触发（不在冷却期），False 表示冷却中
        """
        key = (track_id, event_type)
        with self._lock:
            cooldown_until = self._cooldowns.get(key, 0)
            if cooldown_until and self._now() < cooldown_until:
                return False
            # 过期则清理
            if cooldown_until:
                self._cooldowns.pop(key, None)
            return True

    def get_active_events(self) -> List[TrafficEvent]:
        """获取所有未结束的事件（state 不是 CONFIRMED/REJECTED）"""
        with self._lock:
            return [e for e in self._events.values() if e.state not in TERMINAL_STATES]

    def get_event(self, event_id: str) -> Optional[TrafficEvent]:
        """获取指定事件"""
        with self._lock:
            return self._events.get(event_id)

    def get_all_events(self) -> List[TrafficEvent]:
        """获取所有事件（含已结束）"""
        with self._lock:
            return list(self._events.values())

    def submit_to_ai(self, event_id: str) -> Dict[str, Any]:
        """将事件提交给云端 AI 分析 — 状态 → PENDING_AI

        不实际调用云端，只生成提交请求 dict（含事件视频路径+关键帧+结构化上下文）。
        实际调用由 realtime_detector 或路由层完成。

        Args:
            event_id: 事件 ID

        Returns:
            提交信息字典：
            {
              'event_id': str,
              'event_video_path': str,
              'key_frames': list,
              'vehicle_info': dict,
              'scene_context': dict,
              'event_type': str,
              'trajectory': list,
              'rule_judgment': dict,
              'submit_time': str
            }

        Raises:
            KeyError: 事件不存在
            ValueError: 状态转换非法（当前状态不是 RECORDING）
        """
        with self._lock:
            event = self._events.get(event_id)
        if not event:
            raise KeyError(f"事件不存在: {event_id}")

        # 状态转换 RECORDING → PENDING_AI
        self._update_event_state(event, EventState.PENDING_AI, reason="提交云端 AI 分析")

        submit_info = {
            'event_id': event.event_id,
            'event_video_path': event.event_video_path,
            'key_frames': event.key_frames,
            'vehicle_info': event.vehicle_info,
            'scene_context': event.scene_context,
            'event_type': event.event_type,
            'trajectory': event.trajectory,
            'rule_judgment': event.rule_judgment,
            'submit_time': datetime.now().isoformat(),
        }
        logger.info(f"[TrafficEventEngine] 事件 {event_id} 已提交 AI 分析")
        return submit_info

    def apply_ai_result(self, event_id: str, ai_result: Dict[str, Any]):
        """应用云端 AI 分析结果 — 状态 → AI_REVIEWED

        根据 ai_result 更新事件状态：
        - AI 确认违法 → CONFIRMED
        - AI 排除 → REJECTED
        - AI 不确定 → MANUAL_REVIEW

        Args:
            event_id: 事件 ID
            ai_result: AI 分析结果 dict，期望含：
                - final.judgment: "confirmed"/"rejected"/"uncertain"
                - final.confidence: float
                - final.explanation: str
                - 完整 ai_trace v3 结构

        Raises:
            KeyError: 事件不存在
            ValueError: 状态转换非法（当前状态不是 PENDING_AI）
        """
        with self._lock:
            event = self._events.get(event_id)
        if not event:
            raise KeyError(f"事件不存在: {event_id}")

        # 状态转换 PENDING_AI → AI_REVIEWED
        self._update_event_state(event, EventState.AI_REVIEWED, reason="云端 AI 返回结果")

        # 解析 ai_trace v3 结构
        final = ai_result.get('final', {}) if isinstance(ai_result, dict) else {}
        judgment = final.get('judgment', 'uncertain').lower()
        confidence = float(final.get('confidence', 0.0))
        explanation = final.get('explanation', '')

        # 保存 AI 结果到事件
        event.ai_judgment = ai_result if isinstance(ai_result, dict) else {'raw': ai_result}
        event.ai_confidence = confidence
        event.ai_explanation = explanation

        # 根据 AI 判断更新终态
        if judgment == 'confirmed':
            self._update_event_state(event, EventState.CONFIRMED, reason=f"AI 确认违法 conf={confidence:.2f}")
        elif judgment == 'rejected':
            self._update_event_state(event, EventState.REJECTED, reason=f"AI 排除 conf={confidence:.2f}")
        else:  # uncertain 或其他
            self._update_event_state(event, EventState.MANUAL_REVIEW,
                                    reason=f"AI 不确定 conf={confidence:.2f} 需人工复核")

        logger.info(f"[TrafficEventEngine] 事件 {event_id} AI 结果: judgment={judgment} "
                    f"conf={confidence:.2f} → state={event.state.value}")

    def mark_manual_review(self, event_id: str, reason: str = "") -> None:
        """把事件转入"待人工复核" — PENDING_AI → MANUAL_REVIEW

        ★2026-10-06 由 DSH 新增，配合运行时开关 `cloud_review`（用户决策 C：
        关掉云端复核后转人工复核队列）。

        为什么不直接复用 apply_ai_result：
          那个方法会写入 ai_judgment/ai_confidence，并强制 PENDING_AI → AI_REVIEWED；
          而本路径**根本没有 AI 结果**，硬塞会把"没复核"记成"AI 已复核"。

        为什么经 PENDING_AI 中转：
          ① VALID_TRANSITIONS 里 RECORDING 只能去 PENDING_AI / REJECTED，
             而 REJECTED 是**终态**，进去就再也接不了人工复核；
          ② PENDING_AI 的语义本就是"等待复核"（提交给谁由开关决定），
             状态机因此**无需改动**，MANUAL_REVIEW → CONFIRMED/REJECTED 照旧合法。
        """
        with self._lock:
            event = self._events.get(event_id)
        if not event:
            raise KeyError(f"事件不存在: {event_id}")
        self._update_event_state(
            event, EventState.MANUAL_REVIEW,
            reason=reason or "转入人工复核队列")

    def manual_review(self, event_id: str, confirmed: bool, reviewer: str = "",
                      comment: str = ""):
        """人工复核 — MANUAL_REVIEW → CONFIRMED/REJECTED

        Args:
            event_id: 事件 ID
            confirmed: True=确认违法，False=排除
            reviewer: 复核人
            comment: 复核意见
        """
        with self._lock:
            event = self._events.get(event_id)
        if not event:
            raise KeyError(f"事件不存在: {event_id}")

        if confirmed:
            self._update_event_state(event, EventState.CONFIRMED,
                                    reason=f"人工复核确认 reviewer={reviewer} comment={comment}")
        else:
            self._update_event_state(event, EventState.REJECTED,
                                    reason=f"人工复核排除 reviewer={reviewer} comment={comment}")

    def transition_to_recording(self, event_id: str):
        """状态转换 TRIGGERED → RECORDING（开始录制事件视频）"""
        with self._lock:
            event = self._events.get(event_id)
        if not event:
            raise KeyError(f"事件不存在: {event_id}")
        self._update_event_state(event, EventState.RECORDING, reason="开始录制事件视频")

    def cleanup_old_events(self, max_age_sec: int = 3600):
        """清理超时的未结束事件（默认 1 小时）

        避免事件长期停留在 DETECTING/TRIGGERED/RECORDING 状态。
        """
        now = time.time()
        with self._lock:
            to_remove = []
            for eid, event in self._events.items():
                if event.state in TERMINAL_STATES:
                    continue
                if now - event.trigger_time > max_age_sec:
                    to_remove.append(eid)
            for eid in to_remove:
                event = self._events.pop(eid)
                logger.info(f"[TrafficEventEngine] 清理超时事件 {eid} state={event.state.value}")
            return len(to_remove)
