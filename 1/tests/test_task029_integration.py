# -*- coding: utf-8 -*-
"""
TASK-029 M09: 交通事件闭环系统集成自检脚本

依据 GPT §21 验证 7 个集成点：
  1) CircularFrameBuffer 基本功能
  2) TrafficEventEngine 事件创建 + 状态转换
  3) EvidenceChain 从事件构建
  4) CloudCollaborator.analyze_event 接口存在性
  5) RealtimeViolationDetector 集成检查
  6) API 路由注册检查
  7) 数据库 traffic_events 表存在检查

用法:
  py -3 tests\\test_task029_integration.py

退出码:
  0 = 全部通过
  1 = 至少一项失败
"""

import os
import sys
import json
import inspect
import traceback
from datetime import datetime

# 将 api 目录加入 sys.path
API_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api')
API_DIR = os.path.abspath(API_DIR)
sys.path.insert(0, API_DIR)


# ============== 测试结果汇总 ==============
RESULTS = []


def record(name, passed, detail="", error=""):
    RESULTS.append({
        "name": name,
        "passed": passed,
        "detail": detail,
        "error": error,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}")
    if detail:
        print(f"        详情: {detail}")
    if error:
        print(f"        错误: {error}")


# ============== 1. CircularFrameBuffer 基本功能 ==============
def test_circular_frame_buffer():
    """测试 1: CircularFrameBuffer 类与核心方法可用"""
    try:
        import numpy as np
        from circular_frame_buffer import CircularFrameBuffer
        buf = CircularFrameBuffer(duration_sec=5, fps=10)
        # 添加 3 帧（add() 在 frame is None 时会 graceful return，必须用真实 ndarray）
        import time
        dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        for i in range(3):
            buf.add(time.time(), dummy_frame, {"detections": [], "tracked_vehicles": {}})
        size = buf.size
        duration = round(buf.duration, 2)
        latest = buf.get_latest(n=1)
        record(
            "CircularFrameBuffer 基本功能",
            passed=(size == 3 and duration >= 0 and len(latest) == 1),
            detail=f"size={size}, duration={duration}s, latest_len={len(latest)}",
        )
    except Exception as e:
        record("CircularFrameBuffer 基本功能", False,
              error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ============== 2. TrafficEventEngine 事件创建+状态转换 ==============
def test_traffic_event_engine():
    """测试 2: TrafficEventEngine 8 状态枚举 + 事件创建 + 状态转换"""
    try:
        from traffic_event_engine import EventState, TrafficEvent, TrafficEventEngine

        # 状态数验证（GPT §7 要求 8 状态）
        states = list(EventState)
        state_ok = len(states) == 8
        state_names = [s.name for s in states]

        # 引擎实例化（不依赖 rule_plugins）
        engine = TrafficEventEngine(rule_plugins=[], frame_buffer=None)
        # 验证核心方法存在
        methods_ok = all(hasattr(engine, m) for m in [
            "process_frame", "get_active_events", "get_event",
            "submit_to_ai", "apply_ai_result", "manual_review",
        ])

        # 构造一个事件并验证状态转换
        event = TrafficEvent(
            event_id="test-evt-001",
            event_type="red_light",
            track_id=1,
            state=EventState.TRIGGERED,
            trigger_time=1234567890.0,
            created_at="2026-08-21T10:00:00",
            updated_at="2026-08-21T10:00:00",
            vehicle_info={}, scene_context={}, trajectory=[],
            key_frames=[], event_video_path="",
            rule_judgment={}, ai_judgment={},
            ai_confidence=0.0, ai_explanation="",
            state_history=[], cooldown_until=0.0,
        )
        # 将事件注入引擎（直接写入 _events 内部字典）
        if hasattr(engine, "_events"):
            engine._events[event.event_id] = event
        # 状态转换：TRIGGERED → RECORDING
        engine.transition_to_recording(event.event_id)
        new_event = engine.get_event(event.event_id)
        state_changed = new_event is not None and new_event.state == EventState.RECORDING

        record(
            "TrafficEventEngine 事件创建+状态转换",
            passed=(state_ok and methods_ok and state_changed),
            detail=f"states={state_names}, methods_ok={methods_ok}, state_changed={state_changed}",
        )
    except Exception as e:
        record("TrafficEventEngine 事件创建+状态转换", False,
              error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ============== 3. EvidenceChain 从事件构建 ==============
def test_evidence_chain():
    """测试 3: EvidenceChain.from_traffic_event 可用"""
    try:
        from evidence_chain import EvidenceChain
        from traffic_event_engine import TrafficEvent, EventState

        event = TrafficEvent(
            event_id="test-evt-002",
            event_type="wrong_way",
            track_id=2,
            state=EventState.CONFIRMED,
            trigger_time=1234567890.0,
            created_at="2026-08-21T11:00:00",
            updated_at="2026-08-21T11:05:00",
            vehicle_info={"plate_number": "京A12345", "vehicle_type": "car", "plate_color": "blue"},
            scene_context={"traffic_light_state": "red", "stop_line_relation": "after"},
            trajectory=[{"x": 100, "y": 200}, {"x": 150, "y": 220}],
            key_frames=["/tmp/k1.jpg", "/tmp/k2.jpg"],
            event_video_path="/tmp/test.mp4",
            rule_judgment={"rule": "wrong_way", "violated": True},
            ai_judgment={"version": "v3", "final": {"judgment": "confirmed"}},
            ai_confidence=0.92,
            ai_explanation="逆行已确认",
            state_history=[],
            cooldown_until=0.0,
        )
        evidence = EvidenceChain.from_traffic_event(event, camera_id="cam_0")
        d = evidence.to_dict()
        # 验证关键字段
        fields_ok = all(k in d for k in [
            "camera_id", "vehicle_id", "vehicle_type", "plate_number",
            "traffic_light_state", "stop_line_relation", "trajectory",
            "key_frames", "event_video_path", "rule_judgment", "ai_judgment",
            "ai_confidence", "ai_explanation", "final_status",
        ])
        summary_ok = bool(evidence.summary())
        json_ok = bool(evidence.to_json())

        record(
            "EvidenceChain 从事件构建",
            passed=(fields_ok and summary_ok and json_ok),
            detail=f"fields_ok={fields_ok}, summary_ok={summary_ok}, json_ok={json_ok}, "
                   f"plate={d.get('plate_number')}, final_status={d.get('final_status')}",
        )
    except Exception as e:
        record("EvidenceChain 从事件构建", False,
              error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ============== 4. CloudCollaborator.analyze_event 接口存在性 ==============
def test_cloud_collaborator_analyze_event():
    """测试 4: CloudCollaborator.analyze_event 方法存在且签名正确"""
    try:
        from cloud_collaborator import CloudCollaborator
        method = getattr(CloudCollaborator, "analyze_event", None)
        if method is None or not callable(method):
            record("CloudCollaborator.analyze_event 接口存在性", False,
                  error="analyze_event 方法不存在或不可调用")
            return

        # 检查方法签名（应包含 GPT §8 要求的全部入参）
        sig = inspect.signature(method)
        param_names = list(sig.parameters.keys())
        required_params = ["event_clip_frames", "key_frames", "vehicle_info",
                           "scene_context", "event_type", "trajectory"]
        missing = [p for p in required_params if p not in param_names]

        # 兼容旧方法 analyze_frame（不删除）
        has_old = hasattr(CloudCollaborator, "analyze_frame")

        record(
            "CloudCollaborator.analyze_event 接口存在性",
            passed=(len(missing) == 0),
            detail=f"params={param_names}, missing={missing}, analyze_frame_still_exists={has_old}",
        )
    except Exception as e:
        record("CloudCollaborator.analyze_event 接口存在性", False,
              error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ============== 5. RealtimeViolationDetector 集成检查 ==============
def test_realtime_detector_integration():
    """测试 5: RealtimeViolationDetector 集成 frame_buffer / event_engine / active_events"""
    try:
        from realtime_detector import RealtimeViolationDetector, realtime_detector
        # 实例级检查（realtime_detector 是模块级单例）
        has_frame_buffer = hasattr(realtime_detector, "frame_buffer")
        has_event_engine = hasattr(realtime_detector, "event_engine")
        has_active_events = hasattr(realtime_detector, "active_events")

        # 方法级检查
        methods_ok = all(hasattr(RealtimeViolationDetector, m) for m in [
            "_buffer_frame", "_process_event_engine", "_handle_event_lifecycle",
        ])

        # 单例属性类型验证（graceful：可能为 None 但字段必须存在）
        fb_type = type(realtime_detector.frame_buffer).__name__ if realtime_detector.frame_buffer else "None"
        ee_type = type(realtime_detector.event_engine).__name__ if realtime_detector.event_engine else "None"
        ae_type = type(realtime_detector.active_events).__name__

        record(
            "RealtimeViolationDetector 集成检查",
            passed=(has_frame_buffer and has_event_engine and has_active_events and methods_ok),
            detail=f"frame_buffer={fb_type}, event_engine={ee_type}, "
                   f"active_events={ae_type}, methods_ok={methods_ok}",
        )
    except Exception as e:
        record("RealtimeViolationDetector 集成检查", False,
              error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ============== 6. API 路由注册检查 ==============
def test_api_routes_registered():
    """测试 6: 6 个事件相关 API 路由全部注册到 realtime router"""
    try:
        from routers import realtime as realtime_router_module
        from fastapi import APIRouter

        # 拿到 router 实例
        router = getattr(realtime_router_module, "router", None)
        if router is None or not isinstance(router, APIRouter):
            record("API 路由注册检查", False,
                  error="realtime.router 不存在或不是 APIRouter 实例")
            return

        # 提取所有已注册路由的 path + methods
        registered_paths = set()
        for route in router.routes:
            if hasattr(route, "path"):
                registered_paths.add(route.path)

        # GPT §M07 要求的 6 个事件路由
        required_paths = [
            "/api/realtime/events",
            "/api/realtime/events/active",
            "/api/realtime/events/{event_id}",
            "/api/realtime/events/{event_id}/video",
            "/api/realtime/events/{event_id}/frames",
            "/api/realtime/events/{event_id}/review",
        ]
        missing = [p for p in required_paths if p not in registered_paths]

        record(
            "API 路由注册检查",
            passed=(len(missing) == 0),
            detail=f"total_routes={len(router.routes)}, "
                   f"required={len(required_paths)}, missing={missing}",
        )
    except Exception as e:
        record("API 路由注册检查", False,
              error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ============== 7. 数据库 traffic_events 表存在检查 ==============
def test_traffic_events_table_exists():
    """测试 7: traffic_events 表存在于数据库中"""
    try:
        import sqlite3
        from config import Config

        # 优先使用 Config.DB_PATH（生产配置），否则回退到默认
        db_path = getattr(Config, "DB_PATH", "") or ""
        if not db_path:
            db_path = os.path.join(API_DIR, "zhitong_violations.db")

        if not os.path.exists(db_path):
            record("traffic_events 表存在检查", False,
                  error=f"数据库文件不存在: {db_path}")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 查询 sqlite_master 看表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='traffic_events'"
        )
        row = cursor.fetchone()
        table_exists = row is not None

        # 查询表结构（验证列数 ≥ 15）
        column_count = 0
        columns = []
        if table_exists:
            cursor.execute("PRAGMA table_info(traffic_events)")
            columns = [r[1] for r in cursor.fetchall()]
            column_count = len(columns)

        # 查询索引数（≥ 5）
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='traffic_events'"
        )
        indexes = [r[0] for r in cursor.fetchall()]

        conn.close()

        record(
            "traffic_events 表存在检查",
            passed=(table_exists and column_count >= 15),
            detail=f"db_path={os.path.basename(db_path)}, table_exists={table_exists}, "
                   f"columns={column_count} ({', '.join(columns[:8])}...), indexes={len(indexes)}",
        )
    except Exception as e:
        record("traffic_events 表存在检查", False,
              error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ============== 主流程 ==============
def main():
    print("=" * 60)
    print("TASK-029 M09 集成自检开始")
    print(f"API_DIR: {API_DIR}")
    print(f"Python: {sys.version.split()[0]}")
    print("=" * 60)

    test_circular_frame_buffer()
    test_traffic_event_engine()
    test_evidence_chain()
    test_cloud_collaborator_analyze_event()
    test_realtime_detector_integration()
    test_api_routes_registered()
    test_traffic_events_table_exists()

    print("=" * 60)
    passed_count = sum(1 for r in RESULTS if r["passed"])
    total = len(RESULTS)
    print(f"集成自检结果: {passed_count}/{total} PASS")

    # 输出汇总 JSON（写入文件）
    summary = {
        "task": "TASK-029-M09-integration",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "all_passed": passed_count == total,
        "results": RESULTS,
    }

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '_TASK-029-M09_integration_selfcheck.json')
    output_path = os.path.abspath(output_path)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"自检报告已写入: {output_path}")
    except Exception as e:
        print(f"自检报告写入失败: {e}")

    print("=" * 60)
    if passed_count == total:
        print("✓ 全部通过")
        sys.exit(0)
    else:
        print(f"✗ 有 {total - passed_count} 项失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
