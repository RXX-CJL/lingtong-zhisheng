# -*- coding: utf-8 -*-
"""TASK-COORD-007 追加 _TASK_HISTORY.json（幂等：已有则跳过）"""
import io
import json

p = r'e:\output\_TASK_HISTORY.json'
with io.open(p, 'r', encoding='utf-8-sig') as f:
    h = json.load(f)

NEW = {
    "task": "TASK-COORD-007",
    "title": "真实逐帧检测框分析回放（sidecar + replay 接口 + SVG 叠加）",
    "finished": "2026-09-25",
    "status": "PASS",
    "files": [
        "api/circular_frame_buffer.py",
        "api/realtime_detector.py",
        "api/routers/realtime.py",
        "web-admin/src/api/index.js",
        "web-admin/src/views/EventDetail.vue",
        "tests/test_replay_sidecar_contract.py",
        "tests/verify_replay_sidecar.py",
        "tests/test_event_media_contract.py",
        "docs/REPORT_TASK-COORD-007_TRAE.md",
    ],
    "note": (
        "根因修复: extract_event_clip 丢弃元数据第三元素 → 新增 extract_event_clip_with_meta; "
        "save_event_video 落盘 sidecar({video_path}.replay.json, frames[{index,time,vehicles["
        "{track_id,class_name,bbox,speed_px,direction}]}], source=local_yolo_tracker); "
        "新增 GET /api/realtime/events/{id}/replay(旧事件 200+no_frame_replay_data 诚实降级); "
        "EventDetail 分析回放 SVG 按视频原生坐标叠加真实 bbox、rAF+timeupdate 帧同步、"
        "letterbox contain 对齐、右侧当前帧车辆列表联动; 真实视频重跑产出 3 个带 sidecar 新事件"
        "(evt_1790347063112_79_64e07b / evt_1790347063112_80_32d423 / evt_1790347061580_75_613c3b); "
        "浏览器验证 9/9 PASS; 测试 7+9=16 OK; vite build OK; 判定逻辑零改动、旧事件未伪造、HEAD 未变。"
        "遗留: stop 时 active 事件不同步 DB(6 个 sidecar 无 DB 行, 既有行为); "
        "test_event_media_contract.test_04 已区分迁移代(_h264.mp4+保留FMP4)与原生代(原地H.264)两代约定"
    ),
    "reusable_for": (
        "未来需要事件级逐帧可视化/检测数据旁路(sidecar)的任务: 复用 extract_event_clip_with_meta + "
        "_write_replay_sidecar 模式与 /replay 降级响应契约; EventDetail 的 replayState 状态机与 "
        "updateVideoRect letterbox 对齐逻辑可直接搬用"
    ),
}

already = any(isinstance(x, dict) and x.get('task') == 'TASK-COORD-007' for x in h)
if already:
    print('SKIP: TASK-COORD-007 already in history')
else:
    h.append(NEW)
    with io.open(p, 'w', encoding='utf-8-sig') as f:
        json.dump(h, f, ensure_ascii=False, indent=4)
    print('APPENDED OK, total_items=', len(h))
