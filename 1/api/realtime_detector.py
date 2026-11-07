# -*- coding: utf-8 -*-
"""
实时违规检测服务模块
- 摄像头采集
- 本地YOLO检测（每秒处理2-5帧）
- 违规规则引擎判断
- 触发端云协作
- 保存证据
- 推送数字孪生
- 帧缓存上下文分析
"""

import cv2
import time
import threading
import base64
import os
import json
import queue
import numpy as np
import asyncio
import logging
from datetime import datetime
from collections import deque
from typing import Optional, Dict, List, Any

from image_recognizer import (multi_model_detect, init_all_models, CLASS_CN_MAP,
                              TRAFFIC_CLASS_WHITELIST)
from violation_rules import check_violations, ViolationRuleEngine, VIOLATION_TYPE_CN
from cloud_collaborator import CloudCollaborator
from config import Config
from behavior_engine import BehaviorEngine, BEHAVIOR_TYPE_CN

# ★2026-10-09 由 DSH 新增：红绿灯类名的**唯一权威名单**。
# 历史 bug：检测侧（_collect_traffic_lights）与绘制侧（annotation_renderer
# 主循环跳过红绿灯的判断）各写了一份手写名单，且两份不一致 —— 绘制侧漏了
# 裸色名 red/green/yellow 与 COCO 原生带空格写法 "traffic light"，导致红绿灯
# 掉进车辆绘制分支、被画成灰框 + 英文标签，按灯色着色的配色同时失效。
# 现在两处共用 annotation_renderer.TRAFFIC_LIGHT_CLASS_NAMES 一个 frozenset。
try:
    from annotation_renderer import TRAFFIC_LIGHT_CLASS_NAMES as _TL_LIGHT_NAMES
except Exception:                                  # 渲染器不可用时退回等价集合
    _TL_LIGHT_NAMES = frozenset(
        ("traffic light", "traffic_light", "red_light", "green_light",
         "yellow_light", "red", "green", "yellow",
         "traffic_light_red", "traffic_light_green", "traffic_light_yellow"))

# ---------------------------------------------------------------------------
# 运行时设置（2026-10-03 由 DSH 新增）
# 供"直播页控制台"实时调整：检测类型开关 / 置信度门槛 / 冷却期
# 不重启即可生效；进程内共享，线程安全（dict 的读写在 GIL 下足够安全，
# 且这些值只做数值判断，无需强一致）
# ---------------------------------------------------------------------------
_ALL_VIOLATION_TYPES = ("wrong_way", "red_light", "illegal_parking",
                        "lane_departure", "no_helmet", "speeding")

RUNTIME_SETTINGS = {
    # 每类检测的开关（关掉后该类违规不再上报，用于车辆多时降低信息杂乱）
    "enabled_types": {t: True for t in _ALL_VIOLATION_TYPES},
    # 各类最低上报置信度（推条控制，避免误判过多）
    "min_confidence": {
        "illegal_parking": 0.60, "lane_departure": 0.65, "no_helmet": 0.60,
        "wrong_way": 0.65, "red_light": 0.60, "speeding": 0.60,
        "_default": 0.65,
    },
    # 时间维度（治理过报的关键参数）
    "hold_sec": float(os.environ.get("VIOLATION_HOLD_SEC", "1.5")),
    "cooldown_sec": float(os.environ.get("VIOLATION_COOLDOWN_SEC", "8")),
    # 云端咨询开关（关掉可省 token）
    #   ⚠ 只管"逐帧咨询"这条支路（process_frame 里的 consult_cloud_dual）。
    #   事件级复核请用下面的 cloud_review —— 两者是**不同的花钱入口**。
    "cloud_consult": True,
    # ★云端 AI 复核总开关（2026-10-06 由 DSH 新增，用户明确要求"别再花没必要的钱"）
    # ----------------------------------------------------------------
    # 背景（实测事实）：每条事件在 _process_event_engine 里**无条件**调用
    #   cloud_collaborator.analyze_event()，它一次会打 2~3 家云 API
    #   （豆包视觉 3~5 关键帧 + Claude（配了 key 才调）+ DeepSeek 二级验证）。
    #   原先**没有任何闸门**；库里 traffic_events 已积累 2552 行。
    # 关闭后的行为（用户 2026-10-06 决策 C：转人工复核队列）：
    #   RECORDING → PENDING_AI → MANUAL_REVIEW（"待人工复核"），
    #   不产生任何云端调用，事件进入事件中心等你点一下确认/排除。
    #   状态机未改动：MANUAL_REVIEW → CONFIRMED/REJECTED 本来就合法。
    "cloud_review": True,
    # 是否允许把"未标定的数值类违规（超速）"送去云端复核
    # 默认 False —— 云端视觉模型无法从图像测速（实测它自己也这么说），
    # 送审只会白烧 token 并产生 rejected。见 docs/AI_EVENT_REVIEW_AUDIT.md
    "cloud_review_uncalibrated": False,
    # ★跨圈重复取证抑制窗口（秒，2026-10-10 由 DSH 新增）
    # ----------------------------------------------------------------
    # 背景（用户反馈"重复的无意义的取证"）：演示视频循环播放，而"闯红灯"的车是
    #   固定那几辆；每回放一圈 tracker 就重新编号，于是**同一辆车、同一位置、
    #   同一个红灯，每圈都被重新上报一次**。实测 position 落在同一 40px 桶的
    #   记录有 141 条、间隔稳定 30/31 秒（= 一圈的墙钟时间）。
    # 语义：同一「违规类型 + 位置(40px 网格)」在 N 秒**墙钟**内只上报一次。
    #   设为 0 = 关闭该抑制（恢复"每圈都报"的旧行为）。
    #   用到的是墙钟而不是视频时间 —— 视频时间每圈归零，正是漏洞所在。
    "loop_dedup_sec": float(os.environ.get("LOOP_DEDUP_SEC", "300")),
    # 标注分级显示（2026-10-04 由 DSH 新增）
    #   minimal  画面只画 ID（默认，最清爽）
    #   standard ID + 速度
    #   full     ID + 速度 + 车牌 + 违规类型
    #   off      只画框与箭头
    "display_mode": os.environ.get("ANNOTATION_MODE", "minimal"),
}


def get_runtime_settings():
    """读取当前运行时设置（返回深拷贝，避免调用方误改）"""
    import copy
    return copy.deepcopy(RUNTIME_SETTINGS)


# ---------------------------------------------------------------------------
# ★★2026-10-10 由 DSH 新增：**运行时设置的持久化**（否则每次重启都会静默重置）
#
# 用户报的现象："两个云端开关有时候会自动打开"。
# 根因（本轮实测确认，比设计单 §8 的前端连带推送更根本）：
#   `RUNTIME_SETTINGS` 是**模块级内存字典**，`cloud_review` / `cloud_consult`
#   的默认值都是 **True**（保持原行为）。于是 ——
#     **每次重启后端，用户关掉的付费开关都会被重置回"开"**。
#   铁证：用户 2026-10-10 22:01 关掉两个开关 -> 22:13 我按流程重启后端
#         -> `/settings` 立刻变回 `cloud_review=true, cloud_consult=true`。
#   这解释了为什么用户觉得"有时候会自己打开"——重启（含双击 restart-backend.bat）
#   就会发生，而且**没有任何提示**。
#
# 修法：把"用户改过的"那部分设置落盘到 `api/output/runtime_settings.json`，
#   启动时读回。**只持久化可以安全恢复的字段**：
#     cloud_review / cloud_consult / cloud_review_uncalibrated /
#     display_mode / hold_sec / cooldown_sec / enabled_types / min_confidence
#   ⚠ 不持久化环境变量驱动的项（如 TUNE_*），避免"盘上的旧值"盖掉启动参数。
# ---------------------------------------------------------------------------
_RUNTIME_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "output", "runtime_settings.json")
_PERSIST_KEYS = ("cloud_review", "cloud_consult", "cloud_review_uncalibrated",
                 "display_mode", "hold_sec", "cooldown_sec", "loop_dedup_sec",
                 "enabled_types", "min_confidence")


def _load_persisted_runtime_settings():
    """启动时读回上次保存的运行时设置（失败一律静默沿用默认值，不影响启动）"""
    try:
        if not os.path.exists(_RUNTIME_SETTINGS_FILE):
            logger.info("[settings] 无历史运行时设置文件，使用默认值（cloud_review=%s）"
                        % RUNTIME_SETTINGS.get("cloud_review"))
            return
        with open(_RUNTIME_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return
        applied = []
        for k in _PERSIST_KEYS:
            if k not in data:
                continue
            v = data[k]
            if k in ("cloud_review", "cloud_consult", "cloud_review_uncalibrated"):
                if isinstance(v, bool):
                    RUNTIME_SETTINGS[k] = v
                    applied.append(k)
            elif k in ("hold_sec", "cooldown_sec"):
                try:
                    RUNTIME_SETTINGS[k] = max(0.0, float(v))
                    applied.append(k)
                except (TypeError, ValueError):
                    pass
            elif k == "display_mode":
                if str(v) in ("minimal", "standard", "full", "off"):
                    RUNTIME_SETTINGS[k] = str(v)
                    applied.append(k)
            elif k == "enabled_types" and isinstance(v, dict):
                for kk, vv in v.items():
                    if kk in _ALL_VIOLATION_TYPES:
                        RUNTIME_SETTINGS["enabled_types"][kk] = bool(vv)
                applied.append(k)
            elif k == "min_confidence" and isinstance(v, dict):
                for kk, vv in v.items():
                    if kk in RUNTIME_SETTINGS["min_confidence"] or kk == "_default":
                        try:
                            RUNTIME_SETTINGS["min_confidence"][kk] = max(
                                0.0, min(1.0, float(vv)))
                        except (TypeError, ValueError):
                            pass
                applied.append(k)
        logger.info("[settings] 已从 %s 恢复运行时设置: %s（cloud_review=%s, cloud_consult=%s）"
                    % (os.path.basename(_RUNTIME_SETTINGS_FILE), applied,
                       RUNTIME_SETTINGS.get("cloud_review"),
                       RUNTIME_SETTINGS.get("cloud_consult")))
    except Exception as e:
        logger.warning(f"[settings] 读取历史运行时设置失败（沿用默认值）: {e}")


def _persist_runtime_settings():
    """把当前运行时设置写盘（**任何失败都不影响主流程**）"""
    try:
        payload = {k: RUNTIME_SETTINGS[k] for k in _PERSIST_KEYS if k in RUNTIME_SETTINGS}
        payload["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs(os.path.dirname(_RUNTIME_SETTINGS_FILE), exist_ok=True)
        tmp = _RUNTIME_SETTINGS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _RUNTIME_SETTINGS_FILE)
    except Exception as e:
        logger.debug(f"[settings] 运行时设置落盘失败（不影响运行）: {e}")


def update_runtime_settings(patch: dict):
    """局部更新运行时设置，返回更新后的完整设置

    支持字段：
      enabled_types: {type: bool}
      min_confidence: {type: float}
      hold_sec / cooldown_sec: float
      cloud_consult: bool
    """
    if not isinstance(patch, dict):
        return get_runtime_settings()
    if isinstance(patch.get("enabled_types"), dict):
        for k, v in patch["enabled_types"].items():
            if k in _ALL_VIOLATION_TYPES:
                RUNTIME_SETTINGS["enabled_types"][k] = bool(v)
    if isinstance(patch.get("min_confidence"), dict):
        for k, v in patch["min_confidence"].items():
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if k in RUNTIME_SETTINGS["min_confidence"] or k == "_default":
                RUNTIME_SETTINGS["min_confidence"][k] = max(0.0, min(1.0, fv))
    for k in ("hold_sec", "cooldown_sec"):
        if k in patch:
            try:
                RUNTIME_SETTINGS[k] = max(0.0, float(patch[k]))
            except (TypeError, ValueError):
                pass
    if "cloud_consult" in patch:
        RUNTIME_SETTINGS["cloud_consult"] = bool(patch["cloud_consult"])
    if "cloud_review" in patch:
        # ★事件级云端 AI 复核总开关（2026-10-06 由 DSH 新增）
        RUNTIME_SETTINGS["cloud_review"] = bool(patch["cloud_review"])
    if "display_mode" in patch and str(patch["display_mode"]) in ("minimal", "standard", "full", "off"):
        RUNTIME_SETTINGS["display_mode"] = str(patch["display_mode"])
        try:
            from annotation_renderer import get_renderer
            get_renderer().mode = RUNTIME_SETTINGS["display_mode"]
        except Exception:
            pass
    if "cloud_review_uncalibrated" in patch:
        RUNTIME_SETTINGS["cloud_review_uncalibrated"] = bool(patch["cloud_review_uncalibrated"])
    if "loop_dedup_sec" in patch:
        try:
            RUNTIME_SETTINGS["loop_dedup_sec"] = max(0.0, float(patch["loop_dedup_sec"]))
        except (TypeError, ValueError):
            pass
    # ★2026-10-10：改完立刻落盘 —— 这样"用户关掉开关"能活过重启
    #   （原来只存在内存里，重启即回到默认 True，是"开关自己打开"的根本原因）
    _persist_runtime_settings()
    return get_runtime_settings()
from vehicle_tracker import VehicleTracker
from multi_frame_validator import MultiFrameValidator, FPSMonitor
# GPT 升级 M06: 循环缓存 + 事件引擎 + 证据链
from circular_frame_buffer import CircularFrameBuffer
from traffic_event_engine import TrafficEventEngine, TrafficEvent, EventState

logger = logging.getLogger("zhitong_api")

# ★2026-10-10：**启动时恢复上次保存的运行时设置**（必须在 logger 定义之后调用）。
# 不做这一步，用户关掉的 cloud_review 会在每次重启后静默变回 True。
_load_persisted_runtime_settings()

class RealtimeViolationDetector:
    def __init__(self):
        self.cap = None
        self.running = False
        self.processing = False
        self.cloud_collaborator = CloudCollaborator()
        self.violation_engine = ViolationRuleEngine()
        self.behavior_engine = BehaviorEngine()
        self.vehicle_tracker = VehicleTracker(use_bytetrack=True)   # 2026-10-03 由 DSH 启用 ByteTrack（原为 False，降级质心追踪）
        self.current_frame = None
        self.last_process_time = 0
        self.frame_count = 0
        # ★2026-10-06 由 DSH 新增：回放本地视频时的"本轮循环起始帧号"。
        # 视频会循环重播；每循环一圈把它设为当时的 frame_count，
        # 于是"视频时间"从 0 重新计时。作用有二：
        #   ① 事件片段窗口（触发时刻 ±5s）能对齐到视频内容，取到"车在路口"的帧；
        #   ② "同一违规每圈只报一次"自然成立（冷却按视频时间算，每圈重新开始）。
        # 接真实摄像头/CARLA 时该值恒为 0，且 _now() 直接用墙钟，行为不变。
        self._loop_frame_base = 0
        self.processed_count = 0
        self.violation_count = 0
        self.camera_index = 0
        # M17: 数据源类型（camera / video / carla）与 CARLA 实例
        self.source_type = "camera"
        self.carla_source = None
        # ★2026-11-07 由 DSH 新增：记住当前视频源路径。
        #
        # 为什么需要（实测事故）：
        #   `POST /source {source_type:video, video_path:X}` 会调 start_camera(video_path=X)
        #   把源打开，但**没有把 X 存下来**。随后 `POST /start` 时：
        #       cur_src = self.source_type  -> "video"
        #       而 routers/realtime.py 的 /start 只对 "carla" 做了跳过，
        #       video 落到 else 分支 -> start_camera(camera_index, video_path=None)
        #       -> classify_source(None) 判成 "camera" -> 转而打开本机摄像头。
        #   实测证据：/source{video} 返回 success=true，
        #             /status 却报 source_type=camera、tracked_vehicle_count=0。
        #   这和 2026-11-07 修的 BUG-3（carla 被 /start 覆盖成 camera）是**同一个病根**，
        #   当时只补了 carla 一个分支，video 漏了。
        self.video_path = None
        self.web_socket_clients = []
        self.digital_twin_clients = []
        self.last_detection_result = None
        self.frame_cache = deque(maxlen=Config.FRAME_CACHE_SIZE)
        self.event_loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()
        self.lock = threading.RLock()
        self.process_lock = threading.Lock()
        self.scene_config = {}
        self.tracked_vehicles = {}
        # 标注渲染所需数据（2026-10-02 由 DSH 新增）
        # _last_violations: 最近一帧违规列表（供画红框 + 显示违规类型）
        # _last_traffic_lights: 最近一帧红绿灯框+颜色（HSV 判定）
        # _plate_cache: {track_id: 车牌号}，后台异步填充，画框时零延迟读取
        self._last_violations = []
        # ★框预测的观测计数（2026-10-06 由 DSH 新增）：用来回答
        #   "预测到底跑没跑、为什么没跑"，而不是靠猜。见 /status 的 predicted_boxes。
        self._pred_stats = {}
        self._last_predicted = []
        # 带时效的"最近违规"缓存（2026-10-03 由 DSH 新增）
        # 背景：_last_violations 每帧被覆盖，且**无违规的帧会立刻清空**；
        # 而违规有确认时长(1.5s)+冷却期(8s)，绝大多数帧都没有违规 ->
        # 前端 /api/realtime/vehicles 几乎永远读到空列表（实测右栏恒为 0）。
        # 这里额外维护一份"最近 N 秒内出现过的违规"，供实时页面展示。
        self._recent_violations = []          # [{'v': 违规dict, 'ts': 时间戳}]
        self._recent_viol_ttl = float(os.environ.get('RECENT_VIOLATION_TTL', '10'))
        # ★2026-10-10 由 DSH 新增：跨圈重复取证抑制的指纹表
        #   {f"{类型}|{网格x}|{网格y}": 上次上报的墙钟时间}
        #   与 `_viol_last_report`（按类型、用视频时间、每圈归零）是**两套**机制：
        #   那一套管"一圈之内不重复"，这一套管"跨圈不重复"。
        self._viol_loop_dedup = {}
        self._last_traffic_lights = []
        # ★★2026-10-09 由 DSH 新增：**场景标注热重载**的可观测状态。
        #
        # 背景（用户实测，设计单 §12.5 根因 B）：
        #   全仓只有 start_camera() 一处 load_scene() -> 运行中保存的标定
        #   **要等「停止→开始」才生效**。铁证：后端进程 22:33:14 启动、
        #   用户 23:19:09 保存了 4 个 ROI，而那一轮跑的是 22:33 加载的旧标注
        #   （只有 1 个 ROI）；更糟的是 /status 仍报 scope=roi（旧标注里本来
        #   就有 1 个 ROI），所以**看起来"在用"，实际用的是旧值**。
        # 修法：detector 侧按场景配置文件的 mtime+size 做热重载（零耦合，
        #   任何写入方式——管理端接口 / 手工改文件——都能生效）。
        self._scene_annotation = getattr(self, '_scene_annotation', None) or {}
        self._scene_sig = None              # (mtime, size) 上次加载时的签名
        self._scene_reload_at = 0.0         # 节流用：上次检查的墙钟
        self._scene_reload_count = 0        # 累计热重载次数（供 /status 观测）
        self._scene_reload_last = None      # 最近一次热重载的时间字符串
        # ★2026-11-07 由 WorkBuddy 新增：CARLA 源的**稳定场景源标识**
        # （固定字符串，不用 actor id / tick —— 那些每次重启都会飘）。
        # 标定文件路径 = scene_annotation._path_for(self._scene_source_id)。
        self._scene_source_id = None
        # ★2026-11-07 由 WorkBuddy 新增：按车流方向的灯态（CARLA 仿真真值）
        #   {'away': 'red', 'toward': 'green'} —— 用于消除对向车流的误报。
        self._light_state_by_motion = {}
        # ★★2026-10-09 由 DSH 新增：**检测类白名单**过滤的观测计数。
        # 根因（设计单 §12.6 问题 2）：渲染器主循环只跳过红绿灯、其余照画，
        #   而 CLASS_CN_MAP 有 107 类、其中 83 类与交通无关 -> 用户看到"盆栽"被画成框。
        # 这里在检测出口按白名单裁掉，而不是只在绘制时跳过 —— 顺带让规则引擎/
        #   行为引擎/跟踪器也不再被垃圾框干扰。
        self._class_filter_stats = {'kept': 0, 'dropped': 0,
                                    'last_dropped_classes': {},
                                    'last_log_at': 0.0}
        self._plate_cache = {}
        self._plate_lock = threading.Lock()
        # ---- 云端咨询异步化（2026-10-03 由 DSH 实现：帧率三级解耦）----------
        # 背景：consult_cloud_dual 是 1-5 秒的同步网络调用，原先直接在 process_frame
        # 里执行，导致 process_lock 被长期占用 -> 大量帧被丢弃（实测 processed 仅
        # 0.7 fps，远低于配置的 3 fps）。
        # 方案：检测线程只做"本地判定 + 入队"，云端调用交给独立 worker 线程，
        # 使第 1 级（本地检测/画框）与第 3 级（云端）彻底解耦。
        self._cloud_queue = queue.Queue(maxsize=2)   # 有界队列，防止积压
        self._cloud_worker = None
        self.cloud_submitted = 0      # 累计入队
        self.cloud_dropped = 0        # 因队列满而丢弃
        self.cloud_completed = 0      # 完成数
        self.cloud_failed = 0         # 失败数
        self._last_cloud_result = None
        self.multi_validator = MultiFrameValidator(window_size=10, confirm_threshold=5)
        self.fps_monitor = FPSMonitor(window_size=30)
        # GPT 升级 M06: 循环缓存 + 事件引擎（叠加层，不影响现有逻辑）
        self.frame_buffer = self._init_frame_buffer()
        self.event_engine = self._init_event_engine(self.frame_buffer)
        self.active_events = {}  # event_id → TrafficEvent
        # 事件证据提取中的 event_id；停止/重启时不可提前清空帧缓存。
        self._event_evidence_condition = threading.Condition()
        self._pending_event_evidence = set()
        self._accept_new_events = False
        self._event_engine_process_lock = threading.Lock()
        self._accept_new_events = False
        self._init_all_models_safe()

    def _init_frame_buffer(self) -> Optional[CircularFrameBuffer]:
        """初始化视频循环缓存（graceful degradation：失败返回 None 不影响主流程）"""
        try:
            buf = CircularFrameBuffer(
                duration_sec=Config.FRAME_BUFFER_DURATION,
                fps=Config.FRAME_BUFFER_FPS,
            )
            logger.info(f"[RealtimeDetector] 循环缓存已就绪 duration={Config.FRAME_BUFFER_DURATION}s "
                        f"fps={Config.FRAME_BUFFER_FPS}")
            return buf
        except Exception as e:
            logger.warning(f"[RealtimeDetector] 初始化循环缓存失败（降级运行）: {e}")
            return None

    def _init_event_engine(self, frame_buffer: Optional[CircularFrameBuffer]) -> Optional[TrafficEventEngine]:
        """初始化交通事件引擎（graceful degradation：插件加载失败返回 None）"""
        try:
            plugins = []
            try:
                from rule_engine.plugin_loader import get_default_loader
                loader = get_default_loader()
                for scenario_name in loader.list_enabled():
                    plugin = loader.get(scenario_name)
                    if plugin is not None:
                        plugins.append(plugin)
                logger.info(f"[RealtimeDetector] 事件引擎加载 {len(plugins)} 个规则插件: {loader.list_enabled()}")
            except Exception as e:
                logger.warning(f"[RealtimeDetector] 规则插件加载失败（事件引擎将以空插件运行）: {e}")

            engine = TrafficEventEngine(
                rule_plugins=plugins,
                frame_buffer=frame_buffer,
                # ★2026-11-07 由 DSH 改：60 -> 300，并把「同车同类型只报一次」交给引擎的去重。
                #
                # 为什么改（实测事故）：
                #   原来 cooldown_sec=60，一辆**停在原地压线**的车每分钟被重报一次。
                #   实测库中 lane_departure 共 570 条，其中 track_id=5 一辆车占 278 条
                #   （时间间隔精确 60.1/60.2/60.5/60.3 秒，坐标固定 (727.5, 357.0)）。
                #   后果：演示时事件列表被同一辆车刷屏，看起来像假数据。
                #
                # 为什么不是无限期只报一次：
                #   track_id 会复用（CARLA 里车消失后新车可能撞上旧 id），
                #   永久去重会让新车被误判为「已报过」而漏报。
                #   300 秒（5 分钟）足够覆盖一次路口通行，又不会跨车辆生命周期。
                #
                # 可用 VIOLATION_EVENT_COOLDOWN_SEC 覆盖。
                cooldown_sec=float(os.environ.get("VIOLATION_EVENT_COOLDOWN_SEC", "300")),
                # ★2026-10-06 由 DSH 注入统一时钟：
                # 回放本地视频时用"视频时间"，摄像头/CARLA 时 _now() 内部自动回退墙钟。
                # 这样事件 trigger_time、冷却、证据帧窗口三者同源，
                # 证据帧才能取到"车在路口"的那几帧（原先取到空镜头，AI 全判驳回）。
                clock=self._now,
            )
            return engine
        except Exception as e:
            logger.warning(f"[RealtimeDetector] 初始化事件引擎失败（降级运行）: {e}")
            return None

    def _run_event_loop(self):
        asyncio.set_event_loop(self.event_loop)
        try:
            self.event_loop.run_forever()
        except Exception as e:
            logger.error(f"Event loop error: {e}")

    def _ensure_event_loop(self):
        """保证后台事件循环在跑（2026-10-23 由 DSH 新增）

        为什么需要它（用户报的"违规告警比画面标注慢"的真根因）：
          · `event_loop` 只在 `__init__` 里创建并启动**一次**；
          · `stop()` 会 `call_soon_threadsafe(event_loop.stop)` ——
            一旦 `run_forever()` 返回，该 loop 就处于 `_stopping` 状态，**不可复用**；
          · 而 `start_detection()` 原来**从不重启它** ->
            做过一次「开始→停止→再开始」之后，`event_loop.is_running()` 永远是 False，
            `_push_violation_event()` 每次都走 else 分支把推送**静默丢弃**。
          实测铁证（/api/realtime/status）：
            ws_clients=1（前端连上了）但 push_loop_alive=False、
            push_scheduled=2 且 push_failed=2（两次推送全失败、0 条送达）。
          后果：前端 WebSocket 收不到任何推送，只能退回 800ms 定时轮询
                （平均多等 400ms，最坏 800ms）。

        做法：loop 没在跑就**重建一个新 loop + 新线程**（旧 loop 已 stop 无法 run_forever）。
        幂等：已在跑时直接返回 True，不产生额外线程。
        """
        try:
            if self.event_loop is not None and self.event_loop.is_running():
                return True
            # 旧 loop 可能已 stop（不可复用），必须换新的
            old = getattr(self, 'event_loop', None)
            if old is not None and not old.is_closed():
                try:
                    old.close()
                except Exception:
                    pass
            self.event_loop = asyncio.new_event_loop()
            self.loop_thread = threading.Thread(
                target=self._run_event_loop, daemon=True, name="rt-ws-loop"
            )
            self.loop_thread.start()
            # 等待线程真正进入 run_forever（最多 1s），避免紧接着的推送又落空
            _deadline = time.time() + 1.0
            while time.time() < _deadline:
                if self.event_loop.is_running():
                    break
                time.sleep(0.01)
            _ok = self.event_loop.is_running()
            if _ok:
                logger.info("[RealtimeDetector] 后台事件循环已（重新）启动 —— WebSocket 推送恢复")
            else:
                logger.warning("[RealtimeDetector] 后台事件循环启动超时 —— 推送仍不可用（将退回轮询）")
            return _ok
        except Exception as e:
            logger.error(f"[RealtimeDetector] 启动后台事件循环失败: {e}")
            return False

    def _init_all_models_safe(self):
        try:
            init_all_models()
            logger.info("[RealtimeDetector] 模型初始化完成")
        except Exception as e:
            logger.error(f"[RealtimeDetector] 模型初始化失败: {e}")

    def _make_diagnostic_frame(self, title: str, lines: List[str],
                                bg_color: tuple = (30, 60, 120),
                                size: tuple = (720, 1280)) -> np.ndarray:
        """生成带中文提示的诊断占位帧（当摄像头/数据源不可用时使用，避免前端显示空白或橙色异常画面）

        Args:
            title: 大标题（首行）
            lines: 多行说明文字
            bg_color: BGR 背景色（默认深蓝）
            size: (高, 宽)
        """
        h, w = size
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :] = bg_color
        # 顶部横条（品牌色：智瞳灵声蓝 -> 亮蓝渐变效果）
        cv2.rectangle(frame, (0, 0), (w, 100), (255, 140, 0), -1)  # 橙蓝主题
        cv2.putText(frame, '智瞳灵声 / ZhiTong LingSheng', (24, 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(frame, title, (24, 88),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

        y = 160
        for line in lines:
            # 英文 + 数字可用 FONT_HERSHEY，中文会显示问号，尽量用简短中文并加拼音替代
            cv2.putText(frame, line, (40, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 200), 2)
            y += 34
        # 底部状态行
        now_s = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(frame, f'Time: {now_s}  |  Source: {self.source_type}  |  CamIdx: {self.camera_index}',
                    (24, h - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 220, 255), 2)
        return frame

    @staticmethod
    def classify_source(src):
        """判定数据源类型（2026-10-03 由 DSH 新增）

        统一抽象：让"导入视频"与"接入摄像头"走同一条代码路径。
          - 本地文件      -> ('file',  path)
          - 网络流/手机摄像头 -> ('stream', url)   如 http://192.168.1.5:8080/video
                                                  rtsp://user:pw@ip:554/stream
          - 摄像头索引    -> ('camera', idx)
        区别只在"结束行为"：文件会 EOF（可循环），流与摄像头永不 EOF。
        """
        if src is None:
            return ("camera", None)
        s = str(src).strip()
        if not s:
            return ("camera", None)
        low = s.lower()
        for scheme in ("http://", "https://", "rtsp://", "rtmp://",
                       "udp://", "tcp://", "rtp://"):
            if low.startswith(scheme):
                return ("stream", s)
        if s.isdigit():
            return ("camera", int(s))
        if os.path.exists(s):
            return ("file", s)
        return ("file", s)      # 交给 OpenCV 报错，错误信息更明确

    # ------------------------------------------------------------------
    # 场景标注**热重载**（2026-10-09 由 DSH 新增，设计单 §12.5 根因 B）
    # ------------------------------------------------------------------
    def _scene_config_path(self):
        """当前数据源对应的场景标注文件路径（与 scene_annotation 的命名规则同源）

        为什么不用 self._source_path / _source_url 重新推导：
          start_camera() 里用的是**归一化后的** `norm`，而 status 暴露的是
          `_source_path`（文件）/`_source_url`（流）—— 两者字符串必须完全一致，
          video_key() 是按**原始字符串**算 sha1 的，差一个字符就是另一个键。
          所以这里在源就绪时把路径**算一次存下来**，之后只 stat 它。
        """
        p = getattr(self, '_scene_cfg_path', None)
        if p:
            return p
        src = getattr(self, '_source_path', None) or getattr(self, '_source_url', None)
        if not src:
            return None
        try:
            from scene_annotation import _path_for
            return _path_for(src)
        except Exception:
            return None

    @staticmethod
    def _scene_sig_of(path):
        """(mtime, size) 签名；文件不存在返回 None"""
        if not path:
            return None
        try:
            st = os.stat(path)
            return (round(float(st.st_mtime), 3), int(st.st_size))
        except OSError:
            return None

    def _maybe_reload_scene_annotation(self, force=False):
        """标注文件一变就重载（节流 0.5s；返回 True 表示本次真的重载了）

        设计取舍（设计单 §12.5 修法对比）：
          · 方案1「保存接口通知 detector」—— 直接，但引入 routers→detector 耦合，
            且手工改文件、别的进程写文件都不生效；
          · 方案2（本实现）「按 mtime+size 比对」—— 零耦合，os.stat 开销微秒级，
            **任何写入方式都能生效**。
        调用点：_detection_loop() 的 while 顶部（保存后的**下一帧**即生效），
          以及 get_status()（让界面上刚点完保存就能看到新 scope）。
        """
        now = time.time()
        if not force and (now - float(getattr(self, '_scene_reload_at', 0.0) or 0.0)) < 0.5:
            return False
        self._scene_reload_at = now

        path = self._scene_config_path()
        if not path:
            return False
        sig = self._scene_sig_of(path)
        if sig == getattr(self, '_scene_sig', None):
            return False                       # 没变化：只花了一次 stat

        try:
            from scene_annotation import load_scene, video_key
            # ★★2026-11-07 由 WorkBuddy 修正（真 bug，标定会「挂载成功又消失」）：
            #   原来这里取 src = self._source_path or self._source_url。
            #   **CARLA 源这两个都是 None**（CARLA 不是文件/流源）->
            #   load_scene(None) 返回空 dict -> 刚挂载好的 CARLA 标定被**清空**。
            #   实测症状：/status 里 scene_annotation_reload_count=0（看似正常），
            #   但 /vehicles 的 speed_calibration.method 变成 assumed_lanes（无标定），
            #   测速精度直接掉到「±50% 仅供参考」。
            #   修法：源标识统一走 _scene_source_id（文件源/流源/CARLA 都有），
            #   优先用它，只有它为空时才回退到 _source_path/_source_url。
            src = (getattr(self, '_scene_source_id', None)
                   or getattr(self, '_source_path', None)
                   or getattr(self, '_source_url', None))
            new = load_scene(src) or {}
            if not new:
                # 查不到对应标注 -> **保留旧标注**，不要用空 dict 覆盖
                # （否则一次失败的查找就把正在生效的标定废掉了）
                logger.warning("[RealtimeDetector] 场景标注热重载未找到对应文件"
                               f"（src={src!r}），保留当前标注不变")
                self._scene_sig = sig
                return False
        except Exception as e:
            logger.warning(f"[RealtimeDetector] 场景标注热重载失败（沿用旧标注）: {e}")
            self._scene_sig = sig              # 记下签名，避免每 0.5s 重试吵闹
            return False

        old = getattr(self, '_scene_annotation', None) or {}
        with self.lock:
            self._scene_annotation = new
            self._scene_sig = sig
            self._scene_reload_count = int(getattr(self, '_scene_reload_count', 0)) + 1
            self._scene_reload_last = time.strftime('%Y-%m-%d %H:%M:%S')
        # 日志写清新旧 ROI 数量：热重载是否**真的换掉了判定依据**必须一眼可见，
        # 否则又是一次"看起来生效、其实用旧值"（这正是本 bug 的隐蔽之处）。
        logger.info(
            "[RealtimeDetector] ★场景标注已热重载（无需重启检测）: "
            f"ROI {len(old.get('traffic_light_roi') or [])} -> "
            f"{len(new.get('traffic_light_roi') or [])} 个，"
            f"停止线={new.get('stop_line_y')}，"
            f"来源={new.get('annotated_by')}@{new.get('annotated_at')}，"
            f"累计热重载={self._scene_reload_count} 次")
        return True

    def start_camera(self, camera_index=0, video_path=None):
        with self.lock:
            self.camera_index = camera_index
            kind, norm = self.classify_source(video_path) if video_path else ("camera", None)
            _video_like = video_path and kind in ("file", "stream")
            if _video_like:
                # 先释放旧句柄，避免重复调用时泄漏（2026-10-02 由 DSH 修复）
                if self.cap is not None:
                    try:
                        self.cap.release()
                    except Exception:
                        pass
                    self.cap = None
                # 流源用 FFMPEG 后端更稳（HTTP MJPEG / RTSP）
                if kind == "stream":
                    self.cap = cv2.VideoCapture(norm, cv2.CAP_FFMPEG)
                    if not self.cap.isOpened():
                        self.cap = cv2.VideoCapture(norm)      # 回退默认后端
                else:
                    self.cap = cv2.VideoCapture(norm)
                if not self.cap.isOpened():
                    self.cap = None
                    raise RuntimeError(f"无法打开{'网络流' if kind == 'stream' else '视频文件'}: {video_path}")
                # source_type 仍用 "video" 让限速/绘制路径统一；
                # 是否"播完回到开头"由 _source_is_file 决定（流不循环）
                self.source_type = "video"
                self._source_is_file = (kind == "file")
                self._source_url = norm if kind == "stream" else None
                self._source_path = norm if kind == "file" else None
                # ★2026-10-09 由 DSH 新增：记录该源的场景标注文件路径，
                # 供热重载比对 mtime（见 _scene_config_path / _maybe_reload_scene_annotation）。
                # 必须在**源就绪时**算一次：video_key() 用原始字符串算 sha1，
                # 之后再用 _source_path 重新推导可能因归一化差异得到另一个键。
                try:
                    from scene_annotation import _path_for
                    self._scene_cfg_path = _path_for(norm)
                except Exception:
                    self._scene_cfg_path = None
                self._scene_sig = self._scene_sig_of(self._scene_cfg_path)
                self._scene_reload_at = time.time()
                self._scene_reload_count = 0
                self._scene_reload_last = None
                logger.info(f"[RealtimeDetector] 数据源已就绪（{kind}）: {video_path}"
                            f"{' [循环播放]' if self._source_is_file else ' [持续流，不循环]'}")
                # ★2026-10-06 由 DSH 新增：按数据源**自动选择判色模型**
                #
                # 背景（子代理审计 U1/G3，是"唯一影响演示结果"的问题）：
                #   报告结论是"采用 CNN5"，但 traffic_light_classifier 默认是 cnn4，
                #   而 start-all.bat 不设 TL_COLOR_MODEL ->
                #   后端只要不带环境变量启动，就会用 CNN4
                #   -> CNN4 在 CARLA 演示上 lit 裁图 **0/14**（红灯召回 0.000）
                #   -> 红灯判不出来 -> 闯红灯永远不触发。
                #
                # 现在按源类型自动切：
                #   本地视频（多为 CARLA 录制）-> CNN5（CARLA 数据微调，演示 14/14）
                #   实时摄像头（真实画面）      -> CNN4（真实视频训练）
                # 环境变量 TL_COLOR_MODEL 仍可覆盖（优先级最高）。
                try:
                    from traffic_light_classifier import (model_file_for_source,
                                                          use_model)
                    _want = model_file_for_source(bool(self._source_is_file))
                    _ok = use_model(_want)
                    logger.info(f"[RealtimeDetector] 判色模型按数据源选择："
                                f"{os.path.basename(_want)}"
                                f"（{'文件源' if self._source_is_file else '摄像头/流源'}，"
                                f"{'加载成功' if _ok else '加载失败将回退'}）")
                except Exception as _e:
                    logger.warning(f"[RealtimeDetector] 判色模型按源切换失败（沿用当前）: {_e}")
                # 加载该源已保存的场景标注（人工/AI 描绘的斑马线、车道线等）
                # 2026-10-03 由 DSH 新增：让"导入视频/接入摄像头"共享同一套标注机制
                try:
                    from scene_annotation import load_scene
                    self._scene_annotation = load_scene(norm) or {}
                    if self._scene_annotation:
                        logger.info(f"[RealtimeDetector] 已加载场景标注: "
                                    f"斑马线={len(self._scene_annotation.get('crosswalk_zones') or [])} "
                                    f"车道线={len(self._scene_annotation.get('lane_lines') or [])} "
                                    f"停止线={self._scene_annotation.get('stop_line_y')} "
                                    f"来源={self._scene_annotation.get('annotated_by')}")
                    else:
                        logger.info("[RealtimeDetector] 该源无场景标注（可调用 "
                                    "/api/scene/auto-detect 或人工描绘）")
                except Exception as _e:
                    self._scene_annotation = {}
                    logger.debug(f"[RealtimeDetector] 加载场景标注失败: {_e}")
            else:
                # Windows 下优先使用 DirectShow 后端（CAP_DSHOW），大幅提高摄像头打开成功率
                # 某些笔记本自带摄像头用默认 MSMF 后端会打不开或报"can't grab frame"
                is_windows = os.name == 'nt'
                # 清掉上一次"文件源"的状态（2026-10-03 由 DSH 修复）
                # 否则切到摄像头后 status 里仍显示 source_kind=file、loop_playback=True，
                # 排查时会被误导（实测踩过）。
                self.source_type = "camera"
                self._source_is_file = False
                self._source_path = None
                self._source_url = None
                # ★2026-10-06 由 DSH 新增：切回摄像头时把判色模型换回 CNN4。
                # 原因：CNN5 是在 CARLA 渲染数据上微调的，真实画面应用 CNN4
                # （CNN4 用真实视频训练）。环境变量 TL_COLOR_MODEL 仍可覆盖。
                try:
                    from traffic_light_classifier import (model_file_for_source,
                                                          use_model)
                    _want = model_file_for_source(False)
                    use_model(_want)
                    logger.info(f"[RealtimeDetector] 判色模型切回摄像头用："
                                f"{os.path.basename(_want)}")
                except Exception as _e:
                    logger.debug(f"[RealtimeDetector] 判色模型切换（摄像头）跳过: {_e}")
                backend = cv2.CAP_DSHOW if is_windows else 0
                backends_to_try = [backend] if backend != 0 else [0]
                # Windows 下做一次双后端兜底：先 DSHOW，再默认
                if is_windows:
                    backends_to_try = [cv2.CAP_DSHOW, 0]
                camera_indexes = [camera_index] + [i for i in range(4) if i != camera_index]

                opened = False
                for be in backends_to_try:
                    if opened: break
                    for idx in camera_indexes:
                        self.cap = cv2.VideoCapture(idx, be) if be != 0 else cv2.VideoCapture(idx)
                        if self.cap.isOpened():
                            # 读一帧验证真正可用（有些摄像头 isOpened=True 但 read 失败）
                            ret_test, _ = self.cap.read()
                            if ret_test:
                                self.camera_index = idx
                                logger.info(
                                    f"[RealtimeDetector] 成功打开摄像头 idx={idx} "
                                    f"backend={'DSHOW' if be == cv2.CAP_DSHOW else 'default'}"
                                )
                                opened = True
                                break
                            else:
                                self.cap.release()
                                self.cap = None
                if not opened or not self.cap or not self.cap.isOpened():
                    # 最终仍未打开，抛出清晰错误，由调用方决定降级
                    raise RuntimeError(
                        f"无法打开摄像头（索引 {camera_indexes}，后端 {backends_to_try}）。"
                        f"可能原因：摄像头被其它程序占用 / 驱动异常 / 索引错误。"
                    )
            logger.info(f"[RealtimeDetector] 摄像头已启动，索引: {self.camera_index}")

    def set_source(self, source_type: str, video_path: str = None, camera_index: int = 0) -> bool:
        """M17: 切换数据源（camera / video / carla）

        - camera/video: 走原 start_camera 流程
        - carla: 懒加载 CarlaSource，连接成功后由 _detection_loop 调 get_frame()
        """
        source_type = (source_type or "camera").lower()
        # 2026-10-03 由 DSH 扩展：file/stream 与 video 等价（统一抽象，
        # 让"导入视频"与"接入摄像头/手机流"走同一条代码路径）
        if source_type in ("file", "stream"):
            source_type = "video"
        if source_type not in ("camera", "video", "carla"):
            logger.warning(f"[RealtimeDetector] 未知数据源类型: {source_type}")
            return False

        with self.lock:
            # 切换前先释放旧资源
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None

            if source_type == "carla":
                try:
                    # ★2026-11-07 由 DSH 修复（BUG-4，实测踩到）：
                    #   原来这里 new 了一个**独立**的 CarlaSource 实例，而
                    #   routers/realtime.py:1190 的 _carla_source_instance 是另一个实例。
                    #   两个实例各自 connect、各自 attach_camera、各自 tick()。
                    #   后果（实测，8002 端口）：
                    #     · /carla/connect + /carla/next-scene 作用在 A 实例上；
                    #     · 检测循环取帧走 B 实例 —— B 的相机挂在「自己 spawn 的第一辆车」
                    #       上，而 B 从未 spawn_vehicles -> 相机被 spawn 在
                    #       carla.Transform(x=1.5, z=2.4) 的相对坐标上，
                    #       即世界原点附近 —— 实测抓到的帧是被建筑挡住的墙。
                    #     · 双方各自 world.tick() -> 同步模式下互相抢步进。
                    #   修法：复用路由层那**同一个**实例（single source of truth）。
                    try:
                        from routers.realtime import _get_carla_source
                        self.carla_source = _get_carla_source()
                    except Exception as _e:
                        logger.debug(f"[RealtimeDetector] 复用路由层 CARLA 实例失败，回退自建: {_e}")
                        self.carla_source = None
                    if self.carla_source is None:
                        from carla_source import CarlaSource
                        self.carla_source = CarlaSource()
                    if not self.carla_source.is_connected():
                        ok = self.carla_source.connect(host="127.0.0.1", port=2000)
                        if not ok:
                            logger.warning("[RealtimeDetector] CARLA 连接失败，请确认 CarlaUE4.exe 已启动")
                            return False
                    # CARLA 模式下挂载摄像头传感器
                    # ★2026-11-07：分辨率/机位改为可配（原来是 640x480 fov90，
                    #   与现有 1920x1080 标定不匹配 -> 反投影/测速全错，项目手册 T88）。
                    #   默认取 CARLA_DEMO_WIDTH/HEIGHT/FOV 环境变量，缺省 1280x720 fov90：
                    #   比 640x480 更接近演示口径，又不至于吃满显存。
                    try:
                        _w = int(os.environ.get("CARLA_DEMO_WIDTH", "1280"))
                        _h = int(os.environ.get("CARLA_DEMO_HEIGHT", "720"))
                        _fov = int(os.environ.get("CARLA_DEMO_FOV", "90"))
                    except Exception:
                        _w, _h, _fov = 1280, 720, 90
                    self.carla_source.attach_camera(width=_w, height=_h, fov=_fov,
                                                   mount_on_vehicle=False)
                    self.source_type = "carla"

                    # ★★2026-11-07 由 WorkBuddy 新增（任务三：让 CARLA 分支**真正加载标定**）
                    #
                    # 改前的事实（用户与上一轮共同核实）：
                    #   CARLA 分支**没有**给 _scene_cfg_path 赋值，也**没有** load_scene()；
                    #   而 _maybe_reload_scene_annotation() 每帧都调用它 ->
                    #   _scene_config_path() 返回 None -> 热重载永远空转 ->
                    #   **标定文件写出来了也不会被加载**，测速/停止线全部用默认值。
                    #
                    # 修法（与文件/流源同源，只多一个稳定的 CARLA 源标识）：
                    #   源标识固定为 "carla:<地图>:<机位>:<画幅>"，
                    #   **不能**用 actor id 或 tick（会飘，每次重启都是新键）。
                    try:
                        _map_name = "unknown"
                        try:
                            _map_name = str(self.carla_source._world.get_map().name).split("/")[-1]
                        except Exception:
                            pass
                        self._scene_source_id = (f"carla:{_map_name}:cam_A_handbook:"
                                                f"{_w}x{_h}")
                        from scene_annotation import _path_for, load_scene
                        self._scene_cfg_path = _path_for(self._scene_source_id)
                        self._scene_annotation = load_scene(self._scene_source_id) or {}
                        self._scene_sig = self._scene_sig_of(self._scene_cfg_path)
                        self._scene_reload_at = time.time()
                        self._scene_reload_count = 0
                        self._scene_reload_last = None
                        logger.info(f"[RealtimeDetector] CARLA 场景标注已挂载: "
                                    f"source_id={self._scene_source_id} "
                                    f"path={self._scene_cfg_path} "
                                    f"停止线={self._scene_annotation.get('stop_line_y')} "
                                    f"斑马线={len(self._scene_annotation.get('crosswalk_zones') or [])}")
                    except Exception as _e:
                        logger.warning(f"[RealtimeDetector] CARLA 场景标注挂载失败: {_e}")
                        self._scene_source_id = None
                        self._scene_cfg_path = None

                    # ★2026-11-07 由 DSH 新增（P0 联调实测缺口）：
                    #   切到 carla 源后，原来**从不生成车流** —— CarlaSource 的
                    #   spawn_vehicles() 只有测试脚本会调，路由和检测器都不调。
                    #   结果画面是一个空路口，YOLO 只能检出红绿灯和盆栽，
                    #   tracked_vehicle_count 恒为 0，永远不可能判出任何违规。
                    #   现在按 CARLA_TRAFFIC_N 环境变量自动生成（缺省 20 辆，0 = 不生成）。
                    try:
                        _n = int(os.environ.get("CARLA_TRAFFIC_N", "20"))
                    except Exception:
                        _n = 20
                    if _n > 0:
                        try:
                            _existing = len(self.carla_source._world.get_actors()
                                            .filter('vehicle.*'))
                            # 只有场上车太少时才补，避免每次切源都堆一批
                            if _existing < _n:
                                _want = _n - _existing
                                _ids = self.carla_source.spawn_vehicles(_want)
                                logger.info(f"[RealtimeDetector] CARLA 车流已生成："
                                            f"请求 {_want} 辆，成功 {len(_ids)} 辆 "
                                            f"（场上共 {_existing + len(_ids)} 辆）")
                            else:
                                logger.info(f"[RealtimeDetector] CARLA 场上已有 "
                                            f"{_existing} 辆车，跳过车流生成")
                        except Exception as _e:
                            logger.warning(f"[RealtimeDetector] CARLA 车流生成失败: {_e}")

                    logger.info(f"[RealtimeDetector] 数据源已切换为 CARLA"
                                f"（复用路由层实例 id={id(self.carla_source)}，"
                                f"相机 {_w}x{_h} fov={_fov}）")
                    return True
                except Exception as e:
                    logger.error(f"[RealtimeDetector] 切换 CARLA 数据源失败: {e}")
                    return False
            else:
                # camera / video 走原逻辑
                self.source_type = source_type
                # ★2026-11-07 由 DSH 新增：video 源必须把路径存下来，
                # 否则后续 /start 再调 start_camera(video_path=None) 会退化成开摄像头。
                # （实测：/source{video} 成功但 /status 报 camera，就是这个原因）
                if source_type == "video":
                    self.video_path = video_path
                else:
                    self.video_path = None
                self.start_camera(camera_index=camera_index, video_path=video_path)
                return True

    def start_detection(self):
        with self.lock:
            if self.running:
                return {"success": False, "message": "检测已在运行中"}
            with self._event_evidence_condition:
                if self._pending_event_evidence:
                    return {"success": False, "message": "上一轮事件证据仍在保存，请稍后重试"}
            self.running = True
            self.frame_count = 0
            self.processed_count = 0
            self.violation_count = 0
            # ★★2026-10-10 由 DSH 修复（**离线取证不同步的真正根因之一**）：
            #   这里必须**同时**把视频时间基准归零。
            #
            #   背景：`_now()`（视频时间）= (frame_count - _loop_frame_base) / 源fps。
            #   `_loop_frame_base` 只在**视频循环回绕**时被设成当时的 frame_count。
            #   而本函数把 frame_count 归零、却**没有**归零 _loop_frame_base  ->
            #   新的一轮开始时 `frame_count - _loop_frame_base` 是个**很大的负数**。
            #
            #   实测铁证（数据库 traffic_events，最近 400 条里 **14 条**）：
            #     evt_-119350_37_…（-119.3s）/ evt_-231600 / evt_-327250 / evt_-37950 …
            #     最早可追溯到 2026-10-06（该时钟机制上线当天）。
            #   后果（用户报的"不同步"就是它）：
            #     · 事件 trigger_time 变成"违规之前 N 秒"，事件 ID 也带着负数；
            #     · 事件引擎按"trigger_time ± 窗口"去循环缓存里取**关键帧/事件视频**
            #       -> 取到的是**上一圈**甚至更早的帧 -> 证据里的车早已离场
            #       -> 云端复核看到空路口 -> 判 rejected（库里大量 rejected 就是这么来的）；
            #     · 与前端展示的时间也对不上。
            self._loop_frame_base = 0
            self._accept_new_events = True
            self.last_process_time = time.time()
            self.frame_cache.clear()
            # GPT 升级 M06: 重启时清空循环缓存和活跃事件
            if self.frame_buffer is not None:
                try:
                    self.frame_buffer.clear()
                except Exception:
                    pass
            self.active_events.clear()

        # ★★2026-10-23 由 DSH 修复：**每次启动都确保 WebSocket 推送的事件循环在跑**。
        #   stop() 会停掉 event_loop 且不可复用，原实现从不重启 ->
        #   「开始→停止→再开始」之后推送永久失效（实测 push_failed=2 / 送达 0 条），
        #   前端只能退回 800ms 轮询（平均多等 400ms）。
        #   放在起的线程之外调用：_ensure_event_loop 内部自己起线程并等就绪。
        self._ensure_event_loop()

        thread = threading.Thread(target=self._detection_loop, daemon=True)
        thread.start()
        logger.info("[RealtimeDetector] 检测循环已启动")
        return {"success": True, "message": "检测已启动"}

    def _detection_loop(self):
        frame_interval = 1.0 / Config.FRAME_RATE
        last_frame_time = time.time()

        while self.running:
            try:
                # ★★2026-10-09 由 DSH 新增：**每轮检查场景标注是否被改过**。
                # 放在这里（而不是 process_frame 里）的原因：本循环既覆盖文件源
                # 又覆盖摄像头/流源，且发生在读取帧**之前** —— 保存后的**下一帧**
                # 就用新标定，不必等「停止→开始」（设计单 §12.5 根因 B）。
                # 内部自带 0.5s 节流 + mtime/size 比对，无变化时只花一次 os.stat。
                try:
                    self._maybe_reload_scene_annotation()
                except Exception as _e:
                    logger.debug(f"[RealtimeDetector] 场景标注热重载检查失败: {_e}")

                # M17: 按 source_type 分支读取帧
                if self.source_type == "carla":
                    # CARLA 数据源
                    if self.carla_source is None or not self.carla_source.is_connected():
                        time.sleep(0.1)
                        continue
                    frame = self.carla_source.get_frame()
                    if frame is None:
                        # 同步模式下推进一帧
                        try:
                            self.carla_source.tick()
                        except Exception:
                            pass
                        time.sleep(0.05)
                        continue
                    with self.lock:
                        self.frame_count += 1
                        self.current_frame = frame.copy()
                        self.frame_cache.append(frame.copy())
                    # GPT 升级 M06: 写入循环缓存（携带最近检测结果）
                    self._buffer_frame(frame)
                else:
                    # camera / video 数据源
                    with self.lock:
                        if self.cap is None:
                            time.sleep(0.05)
                            continue
                        ret, frame = self.cap.read()
                        is_video = (self.source_type == "video")
                        # 视频文件：按源 FPS 限速并取回源帧率。
                        # 原因：文件可 1000+ fps 全速读完，而处理被 frame_interval(FRAME_RATE)
                        # 节流，导致 0.5 秒内 810 帧全被读完、只来得及处理 3 帧，
                        # 之后 cap.read() 永久返回 False，循环在下面空转（已实测）。
                        src_fps = self.cap.get(cv2.CAP_PROP_FPS) if is_video else 0.0
                        # 存为实例属性（2026-10-04 由 DSH 新增）：
                        # 追踪器需要【视频时间】来打轨迹点时间戳，否则测速会
                        # 按墙钟计算 —— 检测慢于视频时速度被低估数倍，且结果
                        # 随机器性能变化。见 vehicle_tracker.update(frame_ts=...)。
                        try:
                            if src_fps and src_fps > 0.1:
                                self._source_fps = float(src_fps)
                        except Exception:
                            pass
                    if not ret:
                        # EOF 处理（2026-10-03 由 DSH 统一抽象）：
                        #   本地文件  -> 回到开头循环播放（视频时长有限）
                        #   网络流/摄像头 -> 永不 EOF；若真读失败则短暂退避重试
                        if is_video and getattr(self, "_source_is_file", True):
                            # ★2026-10-06 由 DSH 新增：每循环一圈做"视频时间归零 + 去重状态清理"。
                            #
                            # 为什么：视频会反复重播（演示需要）。若不归零，
                            #   ① 视频时间会一直累加 -> 事件片段窗口越来越偏；
                            #   ② 违规冷却被上一圈占用 -> 本圈不再上报，或反过来重复上报。
                            # 归零后语义清晰：**每一圈 = 一个独立演示回合，
                            # 同一违规每圈只报一次**。
                            with self.lock:
                                self._loop_frame_base = self.frame_count
                                # 清空去重/确认状态，让本圈的违规可以重新上报
                                for _attr in ('_viol_hold', '_viol_last_report'):
                                    try:
                                        getattr(self, _attr).clear()
                                    except Exception:
                                        pass
                                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            logger.info(f"[RealtimeDetector] 视频回放循环 -> 视频时间归零"
                                        f"（帧号基准={self._loop_frame_base}，"
                                        f"违规去重状态已清理）")
                            continue
                        time.sleep(0.05)
                        continue
                    with self.lock:
                        self.frame_count += 1
                        self.current_frame = frame.copy()
                        self.frame_cache.append(frame.copy())
                    # GPT 升级 M06: 写入循环缓存（携带最近检测结果）
                    self._buffer_frame(frame)
                    if is_video:
                        # 在锁外限速：避免持锁 sleep 阻塞帧处理线程与状态查询
                        # （2026-10-02 由 DSH 修复：原实现无此限速，视频源只处理 0.4% 内容）
                        pace = 1.0 / src_fps if (src_fps and src_fps > 0.5) else 0.05
                        time.sleep(min(pace, 0.2))

                current_time = time.time()
                elapsed = current_time - last_frame_time

                if elapsed >= frame_interval:
                    last_frame_time = current_time
                    # ★2026-10-06 诊断日志（DSH 临时加入，用于坐实"同一辆车是否每帧换 track_id"）：
                    # 打印 帧号 / 视频时间 / 当前在跟踪的 track_id 列表。
                    # 目的：判断"一辆车开过去产生几十条重复事件"到底是因为
                    #   ① 追踪器每帧发新 ID（关联失败）  -> 要改采集/处理解耦
                    #   ② track_id 稳定而是冷却键/状态机问题 -> 改去重逻辑
                    # 定位完即可删除（搜 DIAG-TRACK 可找到全部插入点）。
                    try:
                        if self.frame_count % 10 == 1:
                            _ids = sorted((self.tracked_vehicles or {}).keys())
                            _vn = (self.frame_count - getattr(self, '_loop_frame_base', 0))
                            logger.info("[DIAG-TRACK] 帧=%d 视频时间=%.2fs track_ids=%s 车辆数=%d"
                                        % (self.frame_count, self._now(), _ids, len(_ids)))
                    except Exception:
                        pass
                    self._process_frame_async(frame)

            except Exception as e:
                logger.error(f"[RealtimeDetector] 检测循环异常: {e}")
                time.sleep(0.1)

    # ------------------------------------------------------------------
    # 云端咨询异步化（帧率三级解耦，2026-10-03 由 DSH 实现）
    # ------------------------------------------------------------------
    def _start_cloud_worker(self):
        """启动云端咨询后台线程（幂等）"""
        if self._cloud_worker is not None and self._cloud_worker.is_alive():
            return
        self._cloud_worker = threading.Thread(
            target=self._cloud_worker_loop, daemon=True, name="cloud-consult")
        self._cloud_worker.start()
        logger.info("[RealtimeDetector] 云端咨询后台线程已启动（与检测循环解耦）")

    def _cloud_worker_loop(self):
        """后台消费云端咨询任务（阻塞式网络调用集中在这里，不占用 process_lock）"""
        while True:
            try:
                job = self._cloud_queue.get()
            except Exception:
                time.sleep(0.1)
                continue
            if job is None:          # 退出哨兵
                break
            try:
                (frame_base64, annotated_base64, judgment,
                 consult_type, context_frames, detections) = job
                cloud_result = self.cloud_collaborator.consult_cloud_dual(
                    frame_base64, annotated_base64, judgment,
                    consult_type, context_frames)
                if cloud_result.get("success"):
                    process_result = self.cloud_collaborator.process_cloud_response(
                        {"violation_type": judgment.get("violation_type"),
                         "confidence": judgment.get("confidence")}, cloud_result)
                    ai_trace = self.cloud_collaborator.build_ai_trace_v31(
                        {"violation_type": judgment.get("violation_type"),
                         "confidence": judgment.get("confidence"),
                         "detections": detections},
                        cloud_result.get("doubao_result", {}),
                        cloud_result.get("deepseek_result", {}),
                        process_result)
                    with self.lock:
                        self._last_cloud_result = {
                            "ai_trace": ai_trace,
                            "cloud_result": cloud_result,
                            "violation_type": judgment.get("violation_type"),
                            "finished_at": time.time(),
                        }
                    self.cloud_completed += 1
                    logger.info(f"[RealtimeDetector] 云端咨询完成（异步）: "
                                f"{judgment.get('violation_type')} "
                                f"第{self.cloud_completed}次")
                else:
                    self.cloud_failed += 1
            except Exception as e:
                self.cloud_failed += 1
                logger.warning(f"[RealtimeDetector] 云端咨询异步任务失败: {e}")
            finally:
                try:
                    self._cloud_queue.task_done()
                except Exception:
                    pass

    def submit_cloud_consult(self, frame_base64, annotated_base64, judgment,
                             consult_type, context_frames, detections):
        """把云端咨询投递给后台线程；队列满则丢弃最旧任务（保证不阻塞主流程）"""
        self._start_cloud_worker()
        job = (frame_base64, annotated_base64, judgment,
               consult_type, context_frames, detections)
        try:
            self._cloud_queue.put_nowait(job)
            self.cloud_submitted += 1
            return True
        except queue.Full:
            # 丢弃一个最旧的，腾位给最新（最新画面更有价值）
            try:
                self._cloud_queue.get_nowait()
                self._cloud_queue.task_done()
            except Exception:
                pass
            try:
                self._cloud_queue.put_nowait(job)
                self.cloud_submitted += 1
                self.cloud_dropped += 1
                return True
            except queue.Full:
                self.cloud_dropped += 1
                return False

    def _process_frame_async(self, frame):
        if not self.process_lock.acquire(blocking=False):
            return
        
        def worker():
            try:
                result = self.process_frame(frame)
                with self.lock:
                    self.processed_count += 1
                    self.last_detection_result = result
                    if result.get('violation_detected'):
                        self.violation_count += 1
                        # ★2026-10-11：**不要再在这里推送** —— 已提前到
                        #   `process_frame` 内部"画完框、写好展示缓存"那一刻
                        #   （见那里的注释：为了消除"告警栏比画面标注慢半拍"）。
                        #   留此注释避免以后有人"补回来"造成重复推送。
            except Exception as e:
                logger.error(f"[RealtimeDetector] 帧处理异常: {e}")
            finally:
                self.process_lock.release()
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def process_frame(self, frame):
        result = {
            'violation_detected': False,
            'violations': [],
            'detections': [],
            'tracked_vehicles': [],
            'behaviors': [],
            'confidence': 0.0,
            'ai_trace': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            detections = self._yolo_detect(frame)
            # ★★2026-10-09 由 DSH 新增：**按交通类白名单过滤检测结果**。
            #
            # 用户原话："画面中甚至还识别了路旁的盆栽"。
            # 根因（设计单 §12.6 问题 2）：COCO 的 80 类里 83 个类名与交通无关
            #   （potted plant / fire hydrant / sports ball / chair / bench / dog …），
            #   而渲染器主循环**只跳过红绿灯、其余照画** -> 盆栽被画成了框。
            #
            # 为什么在**这里**过滤，而不是只在绘制时跳过：
            #   ① 垃圾框不再进入 all_detections -> 规则引擎/行为引擎/跟踪器/多帧
            #      确认器**同时**少受干扰（低置信度垃圾框会污染 IoU 匹配）；
            #   ② 一处生效，不管有几个调用方在画框（本项目踩过"改一处看不到效果"）；
            #   ③ 顺带兜住 T73 那类隐患：`license_plate` 模型文件不存在时静默回退
            #      COCO，每帧吐 12 个消防栓/盆栽/运动球。
            detections = self._filter_traffic_classes(detections)
            result['detections'] = detections

            # ★2026-10-06 由 DSH 新增：检测完成时间 + 检测间隔（供"框位置预测"用）
            #   预测需要一个"距上次检测过了多久"的基准，以及"一次检测大约多久"。
            #   用墙钟即可 —— 本地视频回放是按源 fps 节流读取的，墙钟与视频时间同步推进。
            try:
                _now_wall = time.time()
                _prev_wall = getattr(self, '_last_detect_wall_ts', 0) or 0
                if _prev_wall > 0:
                    _iv = _now_wall - _prev_wall
                    if 0.03 < _iv < 3.0:          # 过滤异常值（暂停/首帧/卡顿）
                        _ema = float(getattr(self, '_det_interval_ema', 0.0) or 0.0)
                        self._det_interval_ema = _iv if _ema <= 0 else (0.7 * _ema + 0.3 * _iv)
                self._last_detect_wall_ts = _now_wall
            except Exception:
                pass

            frame_height, frame_width = frame.shape[:2]
            
            try:
                # 传【视频时间】而不是让追踪器用墙钟（2026-10-04 由 DSH 修复）：
                # 轨迹点的时间差决定测速结果。若用墙钟，检测慢于视频时
                # 速度会被低估数倍，且同一视频在不同机器上结果不同。
                # 视频时间 = 已处理帧序号 / 源视频帧率。
                try:
                    _fps = float(getattr(self, '_source_fps', 0) or 0)
                    if _fps <= 0.1:
                        _fps = float(getattr(self, '_video_fps', 0) or 0)
                    _fts = (self.frame_count / _fps) if _fps > 0.1 else None
                except Exception:
                    _fts = None
                self.tracked_vehicles = self.vehicle_tracker.update(
                    detections, frame_width, frame_height, frame_ts=_fts)
                result['tracked_vehicles'] = list(self.tracked_vehicles.values())
                # 回填 track_id 到 detections（2026-10-03 由 DSH 新增）
                # 背景：规则引擎 check_violations(detections) 产生的违规**不带车辆 ID**
                # （仅 wrong_way 经行为引擎带了），导致前端"违规车辆"栏无法与追踪
                # 车辆对应（右栏永远空）。此处用 IoU 把 track_id 写回检测框，
                # 规则引擎即可在违规里带上 vehicle_id，前端即可左右分流。
                self._attach_track_ids(detections)
            except Exception as e:
                logger.warning(f"[RealtimeDetector] 车辆追踪失败: {e}")
            
            # ★2026-10-06 由 DSH 调整顺序 + 引入**车道级（受控方向）灯态**。
            #
            # 旧实现两个毛病：
            #   ① 顺序反了：先汇总灯态、后收集灯框 -> 用的是**上一帧**的判色结果；
            #   ② 汇总时取"画面里**任意一盏**灯"的最高优先级（红>绿>黄）。
            #      实测后果（演示视频每循环）：触发 5~6 次 red_light，其中
            #      t≈15.7~16.0s 那几次发生在**被拍方向明明是绿灯**的时候
            #      —— 横向车道的红灯被当成了本方向的（画面里同时有 6 盏灯）。
            #
            # 现改为：先把本帧灯框判色收齐，再按人工标注的 `traffic_light_roi`
            # （受控方向信号灯所在区域）**只统计 ROI 内那盏**。
            try:
                self._collect_traffic_lights(frame, detections)
            except Exception as e:
                logger.debug(f"[RealtimeDetector] 红绿灯颜色判定失败: {e}")

            _rois = (getattr(self, '_scene_annotation', None) or {}).get('traffic_light_roi')
            traffic_light_state = self._scene_light_state_from_cnn(rois=_rois)
            if not traffic_light_state:
                traffic_light_state = self._detect_traffic_light_state(detections)

            # ★★2026-11-07 由 WorkBuddy 新增（CARLA 源用**仿真真值**灯态）
            #
            # 为什么：画面里同时有 8~15 盏灯。图像判色（CNN）只能回答
            #   「画面里某一盏灯是什么颜色」，无法回答「**本车道**那盏是什么颜色」；
            #   旧逻辑在未标 ROI 时取「任意一盏灯的最高优先级」(红>绿>黄)，
            #   实测把横向车道的红灯当成本方向的 -> 每循环误报 5~7 次。
            # CARLA 仿真端**知道**每盏灯的真实状态，而且我们能确定
            #   「哪盏灯控制本机位看到的那条停止线」（按停止线地理坐标反查）。
            # 因此 CARLA 源下用仿真真值作为场景灯态 —— 准确、可复现、不依赖判色命中。
            # 图像判色结果仍保留在 _last_traffic_lights 里供绘制与对照。
            if self.source_type == "carla":
                try:
                    _sim_state = ""
                    _by_motion = {}
                    if self.carla_source is not None:
                        _sim_state = self.carla_source.get_controlled_light_state() or ""
                        _by_motion = self.carla_source.get_controlled_light_states() or {}
                    if _sim_state:
                        traffic_light_state = _sim_state
                        self._light_scope = "carla_sim"
                    # ★方向感知：对向进口的车流有自己的灯态。
                    #   少了这一步，实测会出现 4 条**假阳性**闯红灯
                    #   （对向车合法绿灯通过，却因为「受控进口是红灯」被误判）。
                    self._light_state_by_motion = dict(_by_motion or {})
                except Exception as _e:
                    logger.debug(f"[RealtimeDetector] 读取 CARLA 受控灯态失败: {_e}")

            self._light_scope_state = traffic_light_state      # 供 /status 观测
            lane_lines = self._extract_lane_lines(detections)
            
            self.scene_config = {
                'traffic_light_state': traffic_light_state,
                'traffic_light_scope': getattr(self, '_light_scope', 'frame'),
                # ★2026-11-07 新增：按车流方向的灯态（CARLA 源下由仿真真值给出）
                'traffic_light_state_by_motion': dict(
                    getattr(self, '_light_state_by_motion', None) or {}),
                'stop_line_y': int(frame_height * 0.55),
                'road_direction': 'south',
                'speed_limit': 60,
                'pixel_per_meter': 10,
                'no_parking_zones': [{'x1': 0, 'y1': int(frame_height * 0.6), 'x2': frame_width, 'y2': frame_height}],
                'lane_lines': lane_lines
            }

            # 合并"人工/AI 标注的场景要素"（2026-10-03 由 DSH 新增）
            # 标注（斑马线多边形/车道线/停止线/禁停区）优先于自动推断值，
            # 因为实测 COCO 不输出 crosswalk/lane_line 等类，自动推断不可靠。
            _ann = getattr(self, '_scene_annotation', None)
            if _ann:
                if _ann.get('crosswalk_zones'):
                    self.scene_config['crosswalk_zones'] = _ann['crosswalk_zones']
                if _ann.get('lane_lines'):
                    self.scene_config['lane_lines'] = _ann['lane_lines']
                if _ann.get('stop_line_y') is not None:
                    self.scene_config['stop_line_y'] = int(_ann['stop_line_y'])
                if _ann.get('no_parking_zones'):
                    self.scene_config['no_parking_zones'] = _ann['no_parking_zones']
                if _ann.get('road_direction'):
                    self.scene_config['road_direction'] = _ann['road_direction']
                if _ann.get('is_no_parking_zone') is not None:
                    self.scene_config['is_no_parking_zone'] = bool(_ann['is_no_parking_zone'])
                if _ann.get('pixel_per_meter'):
                    self.scene_config['pixel_per_meter'] = float(_ann['pixel_per_meter'])
                if _ann.get('speed_limit'):
                    self.scene_config['speed_limit'] = float(_ann['speed_limit'])
                # ★测速标定字段必须逐个带过来（2026-10-06 由 DSH 补）
                # 这里是**第二道静默丢弃**：scene_annotation._ALLOWED_KEYS 放行了
                # 这些字段，但本处手工 copy 漏了它们 -> SpeedCalibrator 永远看不到
                # 相机参数，超速换算永远落回 assumed（= 永远不判超速）。
                # 实测教训：契约要成组维护，新增标定字段时这两处都要加。
                for _k in ('camera_height_m', 'camera_pitch_deg', 'camera_yaw_deg',
                           'fov_deg', 'camera_world_x', 'camera_world_y',
                           'ppm_ref_y', 'lane_width_px', 'lane_ref_y',
                           'crosswalk_width_m', 'y_horizon_ratio',
                           'frame_width', 'frame_height', 'ground_points',
                           'traffic_light_roi', '_source'):
                    if _ann.get(_k) is not None:
                        self.scene_config[_k] = _ann[_k]
                self.scene_config['_annotated_by'] = _ann.get('annotated_by')

            # 红绿灯框 + CNN 颜色判定已上移到本函数开头（2026-10-06）：
            # 必须在汇总灯态**之前**完成，否则用的是上一帧的判色结果
            # （且避免同一帧重复跑两次 CNN 推理）。

            # 车牌识别（后台限流，结果进 _plate_cache 供画框零延迟读取）
            try:
                self._try_recognize_plates(frame)
            except Exception as e:
                logger.debug(f"[RealtimeDetector] 车牌识别调度失败: {e}")

            behavior_results = []
            for vehicle in self.tracked_vehicles.values():
                try:
                    behaviors = self.behavior_engine.analyze_all(vehicle, self.scene_config)
                    for behavior in behaviors:
                        behavior_results.append({
                            'behavior_type': behavior.behavior_type,
                            'behavior_type_cn': behavior.behavior_type_cn,
                            'confidence': behavior.confidence,
                            'is_violation': behavior.is_violation,
                            'evidence': behavior.evidence,
                            'vehicle_id': behavior.vehicle_id,
                            'timestamp': behavior.timestamp
                        })
                except Exception as e:
                    logger.warning(f"[RealtimeDetector] 行为分析失败(车辆{vehicle.get('id')}): {e}")
            
            result['behaviors'] = behavior_results

            # FPS 监控
            self.fps_monitor.tick()

            # 多帧确认：将行为分析结果送入验证器
            frame_validator_input = []
            for vehicle in self.tracked_vehicles.values():
                vid = vehicle.get('id', -1)
                v_bbox = vehicle.get('bbox', [0, 0, 0, 0])
                for behavior in behavior_results:
                    if behavior.get('vehicle_id') == vid and behavior.get('is_violation'):
                        frame_validator_input.append({
                            'track_id': vid,
                            'plate': vehicle.get('plate_number', ''),
                            'violation_type': behavior.get('behavior_type', ''),
                            'bbox': v_bbox
                        })
                        break
            if frame_validator_input:
                self.multi_validator.add_frame(frame_validator_input)
                confirmed = self.multi_validator.get_confirmed()
                if confirmed:
                    result['confirmed_violations'] = confirmed

            if detections:
                violation_result = check_violations(detections)
                violations = violation_result.get('violations', [])
                
                for behavior in behavior_results:
                    if behavior['is_violation']:
                        # 2026-10-03 由 DSH 修正两处：
                        #   ① 补 vehicle_id（行为引擎已在源头注入，之前在此丢失）
                        #   ② location 不再硬编码 (0,0) —— 假坐标会让几何归属
                        #      永远匹配不到车辆（这是"未归属"的直接原因）。
                        #      bbox 优先取行为证据，退化到该车的追踪框。
                        _vid = behavior.get('vehicle_id')
                        _bb = None
                        _ev = behavior.get('evidence')
                        if isinstance(_ev, dict):
                            for _k in ('bbox', 'target_bbox', 'vehicle_bbox'):
                                if isinstance(_ev.get(_k), (list, tuple)) and len(_ev[_k]) >= 4:
                                    _bb = [float(x) for x in _ev[_k][:4]]
                                    break
                        if _bb is None and _vid is not None:
                            try:
                                _tv = (self.tracked_vehicles or {}).get(int(_vid)) or {}
                                if len(_tv.get('bbox') or []) >= 4:
                                    _bb = [float(x) for x in _tv['bbox'][:4]]
                            except (TypeError, ValueError):
                                pass
                        if _bb is not None:
                            _loc = {'bbox': _bb,
                                    'center_x': (_bb[0] + _bb[2]) / 2.0,
                                    'center_y': (_bb[1] + _bb[3]) / 2.0}
                        else:
                            _loc = {}
                        violations.append({
                            'violation_type': behavior['behavior_type'],
                            'violation_type_cn': behavior['behavior_type_cn'],
                            'confidence': behavior['confidence'],
                            'is_violation': True,
                            'vehicle_id': _vid,
                            'track_id': _vid,
                            'evidence': behavior['evidence'],
                            'location': _loc,
                            'timestamp': behavior['timestamp'],
                            'source': 'behavior_engine'
                        })
                
                # ---- 运行时设置驱动的过滤（2026-10-03 由 DSH 升级）----------
                # 控制台可实时改：① 每类检测开关 ② 每类置信度门槛 ③ 冷却/确认时长
                # 目的：车辆多时关掉不关心的检测类型 -> 信息不乱；调门槛 -> 少误判
                _rs = RUNTIME_SETTINGS
                _enabled = _rs["enabled_types"]
                _min_report = _rs["min_confidence"]
                _def_thr = float(_min_report.get("_default", 0.65))

                if violations:
                    _before = len(violations)
                    violations = [
                        v for v in violations
                        if _enabled.get(v.get('violation_type') or v.get('behavior_type'), True)
                    ]
                    _after_switch = len(violations)
                    violations = [
                        v for v in violations
                        if float(v.get('confidence', 0) or 0)
                        >= float(_min_report.get(
                            v.get('violation_type') or v.get('behavior_type'), _def_thr))
                    ]
                    if _before != len(violations):
                        logger.debug(f"[RealtimeDetector] 违规过滤(开关+阈值): "
                                     f"{_before} -> {_after_switch} -> {len(violations)}")

                # ---- 违规确认 + 冷却（2026-10-03 由 DSH 新增）------------------
                # 现象：解耦后 15fps，规则引擎在"每一帧"都判违规（违停规则只要
                # 检测到车辆+区域条件即返回 True），实测违规率 96-99%；
                # 仅提高置信度阈值无效（仍 96%+），加"持续 1.5s 才确认"也只降到 89%。
                # 根因：缺少时间维度 —— 同一违规在每帧都被当成"新违规"。
                # 方案：① 需持续 N 秒才确认（去掉瞬时抖动）
                #       ② 确认后进入冷却期，期间不再重复上报（真实抓拍系统同做法）
                if violations:
                    _hold = float(_rs.get("hold_sec", 1.5))
                    _cooldown = float(_rs.get("cooldown_sec", 8))
                    # ★2026-10-06 修正：原先 time.time()（墙钟）。
                    # 回放视频时改用视频时间 -> 冷却按"视频秒"算，
                    # 于是同一违规在**一圈之内只报一次**（每圈视频时间归零，重新允许上报）。
                    _now = self._now()
                    if not hasattr(self, '_viol_hold'):
                        self._viol_hold = {}
                    if not hasattr(self, '_viol_last_report'):
                        self._viol_last_report = {}
                    _kept = []
                    _dup_skipped = 0
                    for v in violations:
                        vt = v.get('violation_type') or v.get('behavior_type') or 'unknown'
                        # ★★2026-10-23 由 DSH 修复：确认/冷却的**键从「类型」改成「类型+车辆」**。
                        #
                        # 病根（用户反馈：右栏比画面左上角慢很久、快车来不及抓拍）：
                        #   原来键只有 vt（违规类型）-> 同一类型的确认/冷却状态被**所有车共用**：
                        #     · A 车首次闯红灯开始 1.5s 确认计时 -> B 车此刻闯红灯，
                        #       读到的 first_seen 是 A 车的（不为 None 但还不够时长）-> B 车也被压住；
                        #     · A 车确认通过后进入 8s 冷却 -> 这 8 秒内**任何**车闯红灯都进不了右栏。
                        #   而画面左上角的【违规】文字读的是 behaviors（规则引擎原始判定，
                        #   见 get_annotated_frame），**从不经过这两道门** -> 所以它一直很快。
                        #   两者本质不是同一条链路，这就是左上角立刻有、右栏等很久的全部原因。
                        #
                        # 修法与依据：_push_recent_violations() 早就在用
                        #   (violation_type, vehicle_id/track_id) 做去重键，
                        #   说明按车归属本来就是本项目的既定口径，只是这两道门没跟上。
                        # 效果：误报控制逻辑（持续 N 秒才算数）完全不变，
                        #   只是**不再互相阻塞** —— B 车的确认计时从 B 车自己出现那一刻开始算。
                        _vid_key = v.get('vehicle_id')
                        if _vid_key is None:
                            _vid_key = v.get('track_id')
                        try:
                            _vid_key = int(_vid_key) if _vid_key is not None else None
                        except (TypeError, ValueError):
                            _vid_key = None
                        # 拿不到车辆 ID 时退回按类型（保底，不因缺 ID 而永不确认）
                        vk = (vt, _vid_key) if _vid_key is not None else (vt, None)
                        first_seen = self._viol_hold.get(vk)
                        if first_seen is None:
                            self._viol_hold[vk] = _now
                            continue                       # 该车该类型首次出现，等待确认
                        if (_now - first_seen) < _hold:
                            continue                       # 该车持续不足，继续等待
                        last = self._viol_last_report.get(vk, 0.0)
                        if (_now - last) < _cooldown:
                            continue                       # 该车冷却期内，不重复上报
                        # ★★2026-10-10 由 DSH 新增：**跨圈重复取证抑制**。
                        #
                        # 用户反馈："违规抓拍证据……存在不同步和重复的无意义的取证问题"。
                        # 实测根因（数据库 + trace 双重证据）：
                        #   演示视频是**循环播放**的，而视频里"闯红灯"的车是固定的那几辆。
                        #   每回放一圈，tracker 重新分配 track_id（实测 track=1 在
                        #   22:12:36 / 22:15:57 两次都由不同车辆占用），于是
                        #   ① `_viol_hold`（按类型）在**每一圈开头被清空**；
                        #   ② `_viol_last_report` 用的是**视频时间**，每圈归零；
                        #   -> 同一辆车、同一位置、同一个红灯，**每圈都重新上报一次**。
                        #   铁证：position bbox 左上角落在同一个 40px 桶里的记录有
                        #   **141 条**，间隔稳定在 30/31 秒（= 一圈的墙钟时间），
                        #   track_id 每次都不同（1,16,28,35,44,49,62…）。
                        #   后果：一段 26 秒的视频循环播 5 分钟，就产出约 **9 条**
                        #   内容几乎相同的"闯红灯"记录 —— 正是用户说的"重复且无意义"。
                        #
                        # 修法：按"**违规类型 + 位置**"记一个**跨圈**指纹，
                        #   在 `loop_dedup_sec`（默认 300 秒墙钟）内不再重复上报。
                        #   · 用**墙钟**而不是视频时间 —— 视频时间每圈归零，正是漏洞所在；
                        #   · 位置按 40px 网格分桶 —— 同一辆车在视频里的位置是固定的，
                        #     而 tracker 的框有几十像素抖动，精确坐标无法命中；
                        #   · 设 0 可完全关闭该抑制（保留旧行为）。
                        _dedup_sec = float(_rs.get("loop_dedup_sec", 300) or 0)
                        if _dedup_sec > 0:
                            _sig = self._viol_position_key(vt, v)
                            _now_wall = time.time()
                            # ★必须查**3×3 邻域**：只查本格的话，同一个位置只要
                            #   抖动跨过格子边界就会被当成"新违规"（实测踩到：
                            #   中心 (1034.4,327.2) 与 (1031.6,312.1) 落在不同格，
                            #   于是重复取证照样产生）。查邻域相当于一个**滑动窗口**，
                            #   边界抖动不再能绕过抑制。
                            _hit = False
                            for _k in self._viol_neighbor_keys(_sig):
                                _ts = self._viol_loop_dedup.get(_k, 0.0)
                                if _ts and (_now_wall - _ts) < _dedup_sec:
                                    _hit = True
                                    break
                            if _hit:
                                _dup_skipped += 1
                                # ★★2026-10-10 由 DSH 修正（用户反馈"违规告警窗口有时候
                                #   甚至就没有任何反应"）：
                                #   `loop_dedup_sec` 抑制的**只是"再存一条证据/再报一次事件"**，
                                #   不该把"告警栏的展示"一起掐掉。否则演示里会长时间挂着
                                #   "暂无违规"，而画面里车明明在闯红灯（实测右栏空 129 秒）。
                                #   这里把被抑制的违规**仍然喂给展示缓存**，并打上 repeat 标记，
                                #   前端据此显示为"重复出现"——既不让用户以为没反应，
                                #   也不会多存证据、不会重复扣云端费用。
                                try:
                                    self._push_repeat_alert(v)
                                except Exception:
                                    pass
                                continue
                            self._viol_loop_dedup[_sig] = _now_wall
                            # 顺手清理过期指纹，避免长期运行内存无界增长
                            if len(self._viol_loop_dedup) > 512:
                                _cut = _now_wall - _dedup_sec
                                for _k in [k for k, ts in self._viol_loop_dedup.items() if ts < _cut]:
                                    self._viol_loop_dedup.pop(_k, None)
                        self._viol_last_report[vk] = _now
                        # ★2026-10-23 由 DSH 补：_viol_last_report 现在按 (类型,车辆) 分键，
                        #   不再像旧代码那样天然只有 <=11 个键（按类型）。
                        #   长期运行（摄像头源 / track_id 持续增长）会无界膨胀，故按冷却期清理。
                        #   冷却期已过的条目留着也没用（下次进来 last 必然已超时）。
                        if len(self._viol_last_report) > 512:
                            _lr_cut = _now - max(_cooldown, 1.0)
                            for _lr_k in [k for k, ts in self._viol_last_report.items() if ts < _lr_cut]:
                                self._viol_last_report.pop(_lr_k, None)
                        _kept.append(v)
                    if _dup_skipped:
                        logger.info(f"[RealtimeDetector] 跨圈重复取证已抑制 {_dup_skipped} 条"
                                    f"（同一类型+同一位置，{int(_rs.get('loop_dedup_sec', 300))}s 内只报一次）")
                    # ★2026-10-23 由 DSH 同步修复：清理用的 _present 必须与 _viol_hold 同键型。
                    #   否则（旧的纯类型集合）每个元组键都 不 in _present -> 每帧被全删 ->
                    #   确认时长永远生效不了（首发永远 first_seen=None，永远 continue）。
                    #   这是改键型时**必须一起改**的隐藏依赖，漏了就等于把这个功能静默关掉。
                    _present = set()
                    for v in violations:
                        _pvt = v.get('violation_type') or v.get('behavior_type') or 'unknown'
                        _pvid = v.get('vehicle_id')
                        if _pvid is None:
                            _pvid = v.get('track_id')
                        try:
                            _pvid = int(_pvid) if _pvid is not None else None
                        except (TypeError, ValueError):
                            _pvid = None
                        _present.add((_pvt, _pvid) if _pvid is not None else (_pvt, None))
                    for k in list(self._viol_hold):
                        if k not in _present:
                            del self._viol_hold[k]
                    violations = _kept
                    if not _kept:
                        logger.debug(f"[RealtimeDetector] 违规被抑制(待确认/冷却): {sorted(_present)}")
                # --------------------------------------------------------------

                if violations:
                    result['violation_detected'] = True
                    result['violations'] = violations
                    # 统一回填 vehicle_id（2026-10-03 由 DSH 新增）
                    # 背景：规则引擎的违规在 violation_rules 内部已回填，但
                    # **行为引擎（behavior_engine）产生的违规没有**，实测
                    # speeding / illegal_parking 全部落入"未归属"（右栏恒空）。
                    # 这里在合并后的最终列表上再补一次，保证两类来源一致。
                    try:
                        from violation_rules import ViolationRuleEngine
                        ViolationRuleEngine._attach_vehicle_ids(violations, detections)
                    except Exception as _e:
                        logger.debug(f"[RealtimeDetector] vehicle_id 回填失败: {_e}")
                    # 保存给标注渲染用（违规→红框+违规类型）（2026-10-02 由 DSH 新增）
                    self._last_violations = violations
                    # 同时写入带时效的最近违规缓存（2026-10-03 由 DSH 新增）
                    self._push_recent_violations(violations)
                    highest_conf = max(v.get('confidence', 0.0) for v in violations)
                    result['confidence'] = highest_conf
                    # ★★2026-10-11 由 DSH 调整：**把 WebSocket 推送提前到"画完框"这一刻**。
                    #
                    # 用户反馈："右边栏违规告警比视频左上角的报告还差一些（虽然有所改进）"。
                    # 实测定位（三处都有数字，不再靠猜）：
                    #   · 前端埋点：WS 收到推送 -> DOM 出现卡片 = **152~277ms**（其中 150ms
                    #     是我加的去抖）—— 前端侧很快，不是瓶颈；
                    #   · 事件引擎耗时：**0~0.2ms**（峰值 10ms）—— 也不是它；
                    #   · 剩下的就是**后端这一帧的处理时长**：画面上的标注是在
                    #     `process_frame` **内部**画好的，而推送原先要等这个函数**跑完**
                    #     （`worker()` 里 `process_frame` 返回之后）才发 ——
                    #     于是"告警栏"比"画面标注"整整晚了后面半截处理时间
                    #     （实测单帧 ~0.4~0.5s）。
                    # 现在：画完框**立刻**推，事件引擎/落库/云端都排到推送之后
                    #   （它们本来就与"画面已显示的内容"无关）。
                    try:
                        self._push_violation_event(result)
                    except Exception as _e:
                        logger.debug(f"[RealtimeDetector] 提前推送失败（不影响主流程）: {_e}")
                    
                    frame_base64 = self._frame_to_base64(frame)
                    annotated_frame = self._draw_detection_boxes(
                        frame.copy(), detections, self.tracked_vehicles,
                        violations=violations)
                    annotated_base64 = self._frame_to_base64(annotated_frame)
                    
                    consult_type = self.cloud_collaborator.should_consult_cloud({
                        'violation_type': violations[0].get('violation_type'),
                        'confidence': highest_conf,
                        'detections': detections,
                        'success': True
                    })
                    
                    if consult_type and RUNTIME_SETTINGS.get("cloud_consult", True):
                        # 异步化（2026-10-03 由 DSH 改）：原先在此同步调用云端
                        # （1-5 秒）会长期占用 process_lock，导致大量帧被丢弃。
                        # 现在只入队，由独立 worker 线程执行，检测循环立即继续。
                        try:
                            context_frames = self.get_context_frames()
                            self.submit_cloud_consult(
                                frame_base64, annotated_base64,
                                {'violation_type': violations[0].get('violation_type'),
                                 'confidence': highest_conf},
                                consult_type, context_frames, detections)
                        except Exception as e:
                            logger.warning(f"[RealtimeDetector] 云端咨询入队失败: {e}")

                    self._save_violation_evidence(frame, violations)
                else:
                    # 本帧没有违规：清空，避免上一帧的红框残留（2026-10-02 由 DSH 新增）
                    self._last_violations = []
            else:
                self._last_violations = []

            # GPT 升级 M06: 调用交通事件引擎（叠加层，不影响现有违规流程）
            # ★2026-10-11 由 DSH 新增耗时观测：用户反馈"告警栏比画面标注慢"，
            #   而画面标注（`_last_violations`）在这一步**之前**就已经画好了 ——
            #   所以怀疑是事件引擎（写事件视频/落库/云端复核）把后面的环节拖住。
            #   这里的耗时直接暴露到 /status 的 `event_engine_ms`，用数据说话。
            _ee_t0 = time.perf_counter()
            try:
                self._process_event_engine(frame, detections, result)
            finally:
                _ee_ms = (time.perf_counter() - _ee_t0) * 1000.0
                self._event_engine_last_ms = round(_ee_ms, 1)
                if _ee_ms > float(getattr(self, '_event_engine_max_ms', 0.0) or 0.0):
                    self._event_engine_max_ms = round(_ee_ms, 1)
                # 只对"有违规的帧"提示：那些帧才是告警栏关心的
                if result.get('violation_detected') and _ee_ms > 200:
                    logger.warning(f"[RealtimeDetector] 事件引擎耗时 {_ee_ms:.0f}ms"
                                   f"（有违规帧；画面标注已完成，但推送/落库会被它拖后）")

            # ★逐帧 trace（2026-10-06 由 DSH 新增，默认关闭）
            self._trace_frame(result)

        except Exception as e:
            logger.error(f"[RealtimeDetector] 帧处理失败: {e}")

        return result

    # ------------------------------------------------------------------
    # ★逐帧 trace（2026-10-06 由 DSH 新增，默认关闭、关闭时零开销）
    #
    # 用途：把"识别成功率"从感觉变成可核对的数。评测脚本
    #   `_scripts\_evaluate_redlight.py` 用真值 CSV（灯态 readback_state /
    #   越线 crossed_stop）+ 本 trace 逐帧对齐，算：
    #     ① 判色准确率（受控方向灯 vs 真值灯态）
    #     ② 闯红灯检出率（真违规窗口内是否触发）
    #     ③ 误报率（非红灯期 / 无车越线时是否触发）
    # 开启：环境变量 RT_TRACE_JSONL=E:\output\_rt_trace.jsonl
    # ------------------------------------------------------------------
    def _trace_frame(self, result):
        path = getattr(self, '_trace_path', None)
        if path is None:
            path = str(os.environ.get('RT_TRACE_JSONL', '') or '')
            self._trace_path = path
        if not path:
            return
        try:
            import json as _json
            lights = [{"bbox": [round(float(v), 1) for v in (it.get("bbox") or [])[:4]],
                       "color": it.get("color"), "conf": it.get("confidence")}
                      for it in (getattr(self, '_last_traffic_lights', None) or [])]
            vehs = []
            for tid, v in (self.tracked_vehicles or {}).items():
                vehs.append({"id": tid,
                             "bbox": [round(float(t), 1) for t in (v.get('bbox') or [])[:4]],
                             "spx": round(float(v.get('speed') or 0.0), 2),
                             "n": len(v.get('history') or [])})
            rec = {
                "f": int(getattr(self, 'frame_count', 0)),
                "t": round(float(self._now()), 3),
                "scope": getattr(self, '_light_scope', 'frame'),
                "matched": int(getattr(self, '_light_matched', 0)),
                "state": getattr(self, '_light_scope_state', None),
                "lights": lights,
                "veh": vehs,
                "viol": [{"type": v.get("violation_type") or v.get("type"),
                          "conf": v.get("confidence"),
                          "vid": v.get("vehicle_id"),
                          # ★来源可诊断：规则引擎 / 行为引擎 / 插件（2026-10-06 加）
                          "src": v.get("source") or v.get("engine")}
                         for v in (result.get('violations') or [])],
                "stats": dict(getattr(self, 'traffic_light_stats', {}) or {}),
            }
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(_json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _tl_model_info(self) -> dict:
        """当前判色模型信息（失败时返回空 dict，不影响 /status 其它字段）。

        ★2026-10-06 由 DSH 新增，用于让外部（前端/运维）能核对
        "后端实际加载的是哪一版判色模型"——这是子代理审计的 U1 疑点。
        """
        try:
            from traffic_light_classifier import current_model_info
            info = current_model_info() or {}
            return {
                'file': info.get('file'),
                'loaded': info.get('loaded'),
                'load_failed': info.get('load_failed'),
                'env_override': info.get('env_override'),
            }
        except Exception:
            return {}

    def _now(self) -> float:
        """当前时间 —— **按数据源类型选择时钟**（★2026-10-06 由 DSH 新增）。

        * 回放本地视频（`_source_is_file`）-> **视频时间** = (frame_count - 本轮起点)/源帧率
        * 摄像头 / CARLA / 网络流        -> **墙钟**

        为什么必须这样：
          检测慢于视频（实测 2.66 fps vs 源 20 fps，慢约 7.5 倍）。
          若用墙钟，"事件触发时刻 ± 5 秒"的取帧窗口会落到**视频里约 80 秒之后**，
          导致证据帧里车早已离场 —— AI 复核看到空路口，判"无任何车辆"，
          违规全部被 REJECTED。同时帧缓存的时间戳也是墙钟，两边对不上。

          统一成视频时间后：
            ① 取帧窗口对齐 -> 证据里车在路口（本问题的主因）
            ② 测速正常（vehicle_tracker 已用同一套视频时间）
            ③ 违规冷却按视频时间算 -> "同一违规每圈只报一次"
        """
        try:
            if getattr(self, '_source_is_file', False):
                fps = float(getattr(self, '_source_fps', 0) or 0)
                if fps <= 0.1:
                    fps = float(getattr(self, '_video_fps', 0) or 0)
                if fps <= 0.1:
                    # 兜底：从 VideoCapture 直接取（前几帧 _source_fps 还没被赋值时）
                    try:
                        if self.cap is not None:
                            fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0)
                    except Exception:
                        fps = 0.0
                if fps > 0.1:
                    _vt = (self.frame_count - getattr(self, '_loop_frame_base', 0)) / fps
                    # ★2026-10-10 由 DSH 记录一个**踩过的坑**：
                    # 这里**不能**把负值兜成 time.time()。我一开始就是这么"修"的，
                    # 结果更糟 —— `_now()` 是**视频时间**，被拿去算"事件触发 ± 窗口"
                    # 来定位关键帧，同时又被落库当时间戳；混用墙钟后事件表里
                    # 出现了 **1970-01-01** 这种行（实测），比负数还糟。
                    # 正确做法：**让视频时间不要变负**（见 start_detection 里
                    # 归零 _loop_frame_base）+ **落库改用 wall_time**
                    # （见 traffic_event_engine 持久化处）。这里保持纯视频时间。
                    return _vt
        except Exception:
            pass
        return time.time()

    def _buffer_frame(self, frame):
        """将当前帧写入循环缓存（携带最近检测结果，graceful degradation）"""
        if self.frame_buffer is None or frame is None:
            return
        try:
            with self.lock:
                last_result = self.last_detection_result or {}
            self.frame_buffer.add(
                # ★2026-10-06 修正：原先写死 time.time()（墙钟），
                # 与 event.trigger_time（现已是视频时间）不同源 ->
                # extract_event_clip 的窗口取不到正确帧。统一走 self._now()。
                self._now(),
                frame,
                {
                    'detections': last_result.get('detections', []),
                    'tracked_vehicles': list(self.tracked_vehicles.values()),
                    'scene_config': self.scene_config,
                }
            )
        except Exception as e:
            logger.warning(f"[RealtimeDetector] 循环缓存写入失败: {e}")

    def _process_event_engine(self, frame, detections, result):
        # 与 stop() 使用同一把锁，保证停止标记与事件入队之间没有竞态。
        with self._event_engine_process_lock:
            if not getattr(self, '_accept_new_events', True):
                return
            self._process_event_engine_locked(frame, detections, result)

    def _process_event_engine_locked(self, frame, detections, result):
        """调用交通事件引擎处理当前帧（graceful degradation）

        - 触发新事件后异步提取视频+提交云端 AI（不阻塞检测循环）
        - 仅在 event_engine 可用时执行
        """
        if not getattr(self, '_accept_new_events', True):
            return
        if self.event_engine is None:
            return
        try:
            new_events = self.event_engine.process_frame(
                frame,
                detections or [],
                self.tracked_vehicles or {},
                self.scene_config or {},
            )
            if not new_events:
                return

            for event in new_events:
                with self.lock:
                    self.active_events[event.event_id] = event
                with self._event_evidence_condition:
                    self._pending_event_evidence.add(event.event_id)

                # 异步处理：先固定事件证据，再提交云端 AI 分析
                thread = threading.Thread(
                    target=self._handle_event_lifecycle,
                    args=(event,),
                    daemon=True,
                )
                try:
                    thread.start()
                except Exception:
                    self._mark_event_evidence_complete(event.event_id)
                    raise
        except Exception as e:
            logger.warning(f"[RealtimeDetector] 事件引擎处理异常: {e}")

    def _mark_event_evidence_complete(self, event_id: str):
        """标记事件片段已提取（或已明确失败），通知 stop/start 的缓存保护逻辑。"""
        condition = getattr(self, '_event_evidence_condition', None)
        if condition is None:
            return
        with condition:
            self._pending_event_evidence.discard(event_id)
            condition.notify_all()

    def _handle_event_lifecycle(self, event: TrafficEvent):
        """事件生命周期处理（在后台线程执行，避免阻塞检测循环）

        事件证据提取完成后即可释放缓存保护；云端复核使用已提取的本地帧副本。
        """
        try:
            self._handle_event_lifecycle_inner(event)
        finally:
            # 包括提前返回、编码失败和意外异常在内，均不能让 pending 标记永久残留。
            self._mark_event_evidence_complete(event.event_id)

    def _handle_event_lifecycle_inner(self, event: TrafficEvent):
        """事件生命周期处理（在后台线程执行，避免阻塞检测循环）

        流程：
        1. TRIGGERED → RECORDING（开始录制）
        2. 提取事件视频片段并保存为 mp4
        3. 提交云端 AI 分析（analyze_event）
        4. 应用 AI 结果，状态 → AI_REVIEWED → CONFIRMED/REJECTED/MANUAL_REVIEW
        """
        if self.event_engine is None:
            return
        try:
            # 等待 after_sec 秒，让缓存录到事件后段
            time.sleep(Config.EVENT_CLIP_AFTER_SEC)

            # 1) TRIGGERED → RECORDING
            try:
                self.event_engine.transition_to_recording(event.event_id)
            except Exception as e:
                logger.warning(f"[RealtimeDetector] 事件 {event.event_id} RECORDING 状态转换失败: {e}")
                return

            # 2) 提取事件视频片段并保存。保留帧副本供云端分析，避免停止/重启清缓存后丢失。
            video_path = ""
            event_clip_frames = []
            if self.frame_buffer is not None:
                try:
                    # TASK-COORD-007: 用含元数据版本提取，保留逐帧检测/跟踪数据写回放 sidecar
                    clip = self.frame_buffer.extract_event_clip_with_meta(
                        event.trigger_time,
                        before_sec=Config.EVENT_CLIP_BEFORE_SEC,
                        after_sec=Config.EVENT_CLIP_AFTER_SEC,
                    )
                    event_clip_frames = [(item[0], item[1]) for item in clip if len(item) >= 2]
                    video_path = self.frame_buffer.generate_event_video_path(event.event_id)
                    # ★★2026-10-06 由 DSH 修复「事件视频快一倍」的根因。
                    # 原实现写死 fps=Config.FRAME_BUFFER_FPS(10)，但源视频实际是
                    # 20 fps 采集的（采集循环按源 fps 节流）-> 188 帧的真实跨度是
                    # 9.4 秒，却被当成 18.8 秒写盘 -> **时间轴拉长一倍，播放看着快一倍**。
                    # 实测：现有 4855 个事件视频**全部是 2.0×**（抽查 12 个无一例外），
                    # 且 replay.json 的 time 字段同样偏移 -> 回放叠加框会逐渐错位。
                    # 用户报告："我说的太快的演示视频是 evt_11200_18_60c808"。
                    #
                    # config.py:80 本来就有 EVENT_VIDEO_FPS_FROM_SOURCE 这个开关，
                    # 但**全仓没有任何地方读它**（空壳）。这里把它真正接上：
                    #   fps = (帧数 - 1) / (首末帧时间跨度)，取整并夹在 [5,60]。
                    # 注意用 timestamp 求真实跨度，而不是假设采集帧率 —— 丢帧时也准。
                    _ev_fps = Config.FRAME_BUFFER_FPS
                    if getattr(Config, 'EVENT_VIDEO_FPS_FROM_SOURCE', True) and len(clip) >= 2:
                        try:
                            _span = float(clip[-1][0]) - float(clip[0][0])
                            if _span > 0.2:
                                _ev_fps = int(round((len(clip) - 1) / _span))
                                _ev_fps = max(5, min(60, _ev_fps))
                        except (TypeError, ValueError, IndexError):
                            _ev_fps = Config.FRAME_BUFFER_FPS
                    saved = self.frame_buffer.save_event_video(clip, video_path, fps=_ev_fps)
                    if saved:
                        event.event_video_path = saved
                        # 选取关键帧（用首/中/尾三帧）
                        event.key_frames = self._pick_key_frame_paths(
                            clip, event_id=event.event_id, save_dir=os.path.dirname(saved))
                        logger.info(f"[RealtimeDetector] 事件 {event.event_id} 视频已保存: {saved}"
                                    f"（fps={_ev_fps}，{len(clip)} 帧；"
                                    f"源帧率={getattr(self, '_source_fps', 0) or '未知'}）")
                        # 视频/关键帧就绪即落一次证据链（2026-10-03 由 DSH 新增）
                        # 原因：证据链原先只在 AI 复核后落库，导致 triggered /
                        # 早退 rejected 的事件没有证据链（实测覆盖率仅 28%，
                        # 而视频/关键帧覆盖 99%）。这里补一次，保证
                        # "只要录到了证据，就有证据链"。
                        try:
                            self._persist_evidence_chain(
                                event, ai_result=None, note="after_clip_saved")
                        except Exception as _e:
                            logger.debug(f"[RealtimeDetector] 证据链(录后)落库失败: {_e}")
                    else:
                        logger.warning(f"[RealtimeDetector] 事件 {event.event_id} 视频保存失败")
                except Exception as e:
                    logger.warning(f"[RealtimeDetector] 事件 {event.event_id} 视频提取失败: {e}")

            # 证据提取阶段已结束；此后云端分析使用 event_clip_frames 的局部副本。
            self._mark_event_evidence_complete(event.event_id)

            # ★★云端 AI 复核总开关（2026-10-06 由 DSH 新增，用户决策 C）
            # --------------------------------------------------------------
            # 用户原话："管理端的云端 ai 复核功能需要添加一个开关，
            #            不然现在会一直花没必要的钱。"
            # 关闭后：不调用 analyze_event（= 不打豆包/Claude/DeepSeek），
            #         事件走 RECORDING → PENDING_AI → MANUAL_REVIEW，
            #         在事件中心以"待人工复核"呈现，等你点确认/排除。
            # 放在最前面：它是**总闸**，优先于下面"数值类是否值得送审"的判断。
            # --------------------------------------------------------------
            try:
                _do_cloud_review = bool(RUNTIME_SETTINGS.get("cloud_review", True))
            except Exception:
                _do_cloud_review = True
            if not _do_cloud_review:
                try:
                    self.event_engine.submit_to_ai(event.event_id)
                    self.event_engine.mark_manual_review(
                        event.event_id,
                        reason="云端 AI 复核已关闭（运行时开关 cloud_review=False）")
                    logger.info(f"[RealtimeDetector] 事件 {event.event_id} "
                                f"云端复核已关闭 -> 转人工复核队列（未产生任何云调用）")
                except Exception as _e:
                    logger.warning(f"[RealtimeDetector] 事件 {event.event_id} 转人工复核失败: {_e}")
                try:
                    _ev = self.event_engine.get_event(event.event_id) or event
                    self._persist_evidence_chain(
                        _ev, ai_result=None, note="cloud_review_disabled_manual_review")
                except Exception as _e:
                    logger.debug(f"[RealtimeDetector] 证据链落库失败: {_e}")
                with self.lock:
                    self.active_events[event.event_id] = \
                        self.event_engine.get_event(event.event_id) or event
                return

            # 3) 判定是否需要云端 AI 复核（2026-10-03 由 DSH 新增门禁）
            # --------------------------------------------------------------
            # 背景（实测教训）：让云端视觉模型复核"超速"是**无效调用**。
            # 云端原话：「无雷达/激光测速读数或视频帧间位移计算数据，
            #            仅凭静态图像无法判定是否超速」—— 它说得对。
            # 后果：364 条事件因置信度 0.05 被判 rejected，同时白烧 token。
            #
            # 正确分工（见 docs/AI_EVENT_REVIEW_AUDIT.md §5）：
            #   数值类（超速）  -> 本地标定+轨迹计算负责，AI 不复核
            #   语义类（闯红灯/违停/压线/逆行/未戴头盔）-> 云端 AI 复核
            # 例外：**已标定**的超速可以送审（让 AI 核对画面与结论是否一致）。
            # --------------------------------------------------------------
            _needs_numeric = event.event_type in ("speeding",)
            _calib = None
            try:
                _vi = event.vehicle_info or {}
                _calib = _vi.get("calibration") or _vi.get("speed_method")
                if not _calib:
                    _ev = (_vi.get("evidence") or {}) if isinstance(_vi, dict) else {}
                    _calib = _ev.get("calibration") or _ev.get("calibration_confidence")
            except Exception:
                _calib = None
            _is_calibrated = bool(_calib) and not str(_calib).startswith("assumed")
            _skip_ai = _needs_numeric and not _is_calibrated
            try:
                _allow_uncal = bool(RUNTIME_SETTINGS.get("cloud_review_uncalibrated", False))
            except Exception:
                _allow_uncal = False

            if _skip_ai and not _allow_uncal:
                # 不进 AI 队列：直接排除，并写明原因（请求要可追溯）
                # 注意状态机：RECORDING 的合法去向只有 PENDING_AI / REJECTED，
                # 不能直接跳 MANUAL_REVIEW（VALID_TRANSITIONS 会拒绝）。因此这里走 REJECTED，
                # 理由写清"因未标定而无法验证"，与"AI 判否"在语义上可区分。
                _reason = (f"数值类违规（{event.event_type}）未经场景标定，"
                           f"无法由视觉模型验证；已跳过云端复核。"
                           f"校准方式={_calib or '无'}")
                try:
                    self.event_engine.reject(event.event_id, reason=_reason)
                    logger.info(f"[RealtimeDetector] 事件 {event.event_id} 跳过 AI 复核"
                                f"（{event.event_type} 未标定）-> 直接排除")
                except Exception as _e:
                    logger.warning(f"[RealtimeDetector] 跳过 AI 后置为排除失败: {_e}")
                # 写入证据链（见修复 2）
                try:
                    self._persist_evidence_chain(event, ai_result=None,
                                                 note="skipped_ai_uncalibrated_numeric")
                except Exception:
                    pass
                with self.lock:
                    self.active_events[event.event_id] = \
                        self.event_engine.get_event(event.event_id) or event
                return

            # 4) 提交云端 AI 分析（RECORDING → PENDING_AI → AI_REVIEWED）
            try:
                self.event_engine.submit_to_ai(event.event_id)
            except Exception as e:
                logger.warning(f"[RealtimeDetector] 事件 {event.event_id} 提交 AI 失败: {e}")
                return

            # 4) 实际调用云端 AI（按事件分析，GPT §8）
            try:
                # 使用证据提取阶段固定下来的帧副本；不要在重启/清缓存后重新查询循环缓存。
                # 不要把事件片段的前 5 帧伪装成"关键帧"：这会集中在时间窗口开头，
                # 而 CloudCollaborator 会优先使用它们，导致后续均匀采样逻辑失效。
                # 传空列表，让事件分析器从完整 clip 中按时间均匀抽样首/中/尾等代表帧。
                key_frames_nd = []

                ai_result = self.cloud_collaborator.analyze_event(
                    event_clip_frames=event_clip_frames,
                    key_frames=key_frames_nd,
                    vehicle_info=event.vehicle_info or {},
                    scene_context=event.scene_context or {},
                    event_type=event.event_type,
                    trajectory=event.trajectory or [],
                )

                # 5) 应用 AI 结果，状态自动流转到 CONFIRMED / REJECTED / MANUAL_REVIEW
                self.event_engine.apply_ai_result(event.event_id, ai_result)

                # 5.5) 证据链落库（2026-10-03 由 DSH 新增，修复"541 条全空"）
                try:
                    _ev = self.event_engine.get_event(event.event_id) or event
                    self._persist_evidence_chain(_ev, ai_result=ai_result,
                                                 note="normal_ai_review")
                except Exception as _e:
                    logger.debug(f"[RealtimeDetector] 证据链落库调用失败: {_e}")

                with self.lock:
                    self.active_events[event.event_id] = self.event_engine.get_event(event.event_id) or event

                logger.info(f"[RealtimeDetector] 事件 {event.event_id} AI 复核完成 state={self.event_engine.get_event(event.event_id).state.value if self.event_engine.get_event(event.event_id) else 'unknown'}")
            except Exception as e:
                logger.warning(f"[RealtimeDetector] 事件 {event.event_id} 云端 AI 分析失败: {e}")
                # 请求异常不等于违规成立/不成立；保留证据并明确交人工复核。
                try:
                    current = self.event_engine.get_event(event.event_id)
                    if current is not None and current.state.value == 'pending_ai':
                        self.event_engine.mark_manual_review(
                            event.event_id,
                            reason=f"云端复核调用失败，需人工复核或稍后重试：{type(e).__name__}: {str(e)[:180]}",
                        )
                        current = self.event_engine.get_event(event.event_id) or current
                    with self.lock:
                        self.active_events[event.event_id] = current or event
                except Exception as state_error:
                    logger.error(f"[RealtimeDetector] 事件 {event.event_id} 失败状态落库失败: {state_error}")
        except Exception as e:
            logger.error(f"[RealtimeDetector] 事件 {event.event_id} 生命周期处理异常: {e}")

    @staticmethod
    def _pick_key_frame_paths(clip, event_id: str = '', save_dir: str = '') -> List[str]:
        """从事件片段中选取首/中/尾三帧，写真实 JPG 到事件视频同目录

        返回 event-videos/ 相对路径（正斜杠），前端 getEventFrameUrl
        拼接 BACKEND_DIRECT_URL 后可直接命中后端 /event-videos 静态挂载。
        全部落盘失败时返回空列表（不返回占位符）。
        """
        if not clip:
            return []
        if len(clip) <= 3:
            indices = list(range(len(clip)))
        else:
            mid = len(clip) // 2
            indices = [0, mid, len(clip) - 1]

        try:
            import cv2
            from config import Config
            base_dir = Config.EVENT_VIDEO_DIR
        except Exception as e:
            logger.warning(f"[RealtimeDetector] 关键帧落盘失败（无法定位输出目录）: {e}")
            return []

        video_dir = save_dir or os.path.join(base_dir, datetime.now().strftime('%Y%m%d'))
        try:
            os.makedirs(video_dir, exist_ok=True)
        except OSError as e:
            logger.warning(f"[RealtimeDetector] 关键帧目录创建失败: {e}")
            return []

        safe_id = (event_id or datetime.now().strftime('%H%M%S%f')).replace('/', '_').replace('\\', '_')
        paths = []
        for idx in indices:
            frame = clip[idx][1]
            if frame is None:
                continue
            try:
                if frame.ndim == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                if not ok or buf is None:
                    continue
                filename = f'{safe_id}_frame_{idx}.jpg'
                abs_path = os.path.join(video_dir, filename)
                with open(abs_path, 'wb') as f:
                    f.write(buf.tobytes())
                try:
                    rel = os.path.relpath(abs_path, base_dir).replace('\\', '/')
                except ValueError:
                    # save_dir 不在 base_dir 之下（如跨盘符）：退化为按目录名拼接
                    rel = f'{os.path.basename(video_dir)}/{filename}'
                paths.append(f'event-videos/{rel}')
            except Exception as e:
                logger.warning(f"[RealtimeDetector] 关键帧 {idx} 落盘失败: {e}")
        return paths

    @staticmethod
    def _light_in_rois(bbox, rois):
        """灯框中心是否落在人工标注的灯态 ROI 内（2026-10-06 由 DSH 新增）"""
        try:
            x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
        except (TypeError, ValueError, IndexError):
            return False
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        for r in (rois or []):
            try:
                rx1, ry1, rx2, ry2 = [float(v) for v in r[:4]]
            except (TypeError, ValueError, IndexError):
                continue
            if min(rx1, rx2) <= cx <= max(rx1, rx2) and min(ry1, ry2) <= cy <= max(ry1, ry2):
                return True
        return False

    def _scene_light_state_from_cnn(self, rois=None):
        """用判色器（CNN）逐框结果汇总出「场景灯态」

        ★2026-10-04 由 DSH 新增：原来读的是上游专门红绿灯模型的裸色名，而它
          在本演示里**恒输出 'yellow'**（520/520 帧），导致 red_light 永不触发。

        ★★2026-10-06 由 DSH 修正为**车道级（受控方向）灯态**：
          旧实现取"画面里**任意一盏**灯"的最高优先级（红>绿>黄）。
          端到端实测后果（演示视频每个循环）：触发 5~6 次 red_light，
          其中多次发生在**被拍方向明明是绿灯**的时候 —— 画面里同时有 6 盏灯
          （含 CAM-2 小窗里那盏），横向车道的红灯被当成了本方向的。
          演示视频实测灯框：受控方向灯在 (1007,146) 判 red(0.998)，
          另有 (433,150)黄 / (823,139)红 / (1138,143)红 / (1337,185)红 / (1653,922)红。

        现支持人工标注 `traffic_light_roi`：只统计**中心落在 ROI 内**的灯框。
        未标注时退回旧行为，并把 `self._light_scope` 标成 'frame'
        （前端可据此提示"灯态未标定，闯红灯判定不可信"）。

        返回 '' 表示判色器无结论（调用方回退到 _detect_traffic_light_state）。
        """
        prio = {"red": 3, "green": 2, "yellow": 1}
        lights = list(getattr(self, "_last_traffic_lights", None) or [])
        scope = "frame"
        if rois:
            kept = [it for it in lights
                    if self._light_in_rois(it.get("bbox"), rois)]
            if kept:
                lights, scope = kept, "roi"
            else:
                # ROI 内这一帧没判出灯（远处小灯偶发漏检/被去误检丢弃）：
                # **不能**退回"全画面"——那正是误报来源。返回空，让调用方
                # 走回退路径，同时保留 scope 标记供观测。
                lights, scope = [], "roi_miss"
        best, best_p = "", 0
        for it in lights:
            st = str(it.get("color") or it.get("state") or "").lower()
            p = prio.get(st, 0)
            if p > best_p:
                best, best_p = st, p
        self._light_scope = scope
        self._light_matched = len(lights)
        return best

    def _detect_traffic_light_state(self, detections):
        for det in detections:
            class_name = det.get('class_name', '').lower()
            if class_name in ['red_light', 'red', 'traffic_light_red']:
                return 'red'
            elif class_name in ['yellow_light', 'yellow', 'traffic_light_yellow']:
                return 'yellow'
            elif class_name in ['green_light', 'green', 'traffic_light_green']:
                return 'green'
        return ''

    def _extract_lane_lines(self, detections):
        lane_classes = {'lane_line', 'road_line', 'white_line', 'yellow_line'}
        return [d for d in detections if d.get('class_name') in lane_classes]

    def _yolo_detect(self, frame):
        try:
            _, img_encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            img_base64 = base64.b64encode(img_encoded).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{img_base64}"
            
            result = multi_model_detect(data_url, conf_threshold=Config.CONFIDENCE_THRESHOLD)
            if result.get('success'):
                return result.get('all_detections', [])
        except Exception as e:
            logger.error(f"[RealtimeDetector] YOLO检测失败: {e}")
        return []

    def _filter_traffic_classes(self, detections):
        """按 TRAFFIC_CLASS_WHITELIST 裁掉与交通无关的检测（2026-10-09 由 DSH 新增）

        用户原话："画面中甚至还识别了路旁的盆栽"。

        白名单的**唯一权威定义**在 `image_recognizer.TRAFFIC_CLASS_WHITELIST`
        （那里写了维护须知：规则引擎新增类名分组时必须同步补上）。

        可观测性（**必须有**，否则又是一次"静默过滤"）：
          · `/status` 的 `class_filter_stats` 报告 kept/dropped 累计数与
            最近被挡掉的类名及次数 —— 先看它再决定要不要扩白名单；
          · 有新类名被挡时，最多每 5 秒打一条 info 日志（防止刷屏）。
        """
        if not detections:
            return []
        stats = getattr(self, '_class_filter_stats', None)
        if stats is None:
            stats = {'kept': 0, 'dropped': 0, 'last_dropped_classes': {},
                     'last_log_at': 0.0}
            self._class_filter_stats = stats

        kept, dropped = [], {}
        for det in detections or []:
            cls = str((det or {}).get('class_name') or '').strip().lower()
            if cls in TRAFFIC_CLASS_WHITELIST:
                kept.append(det)
            else:
                dropped[cls or '(空类名)'] = dropped.get(cls or '(空类名)', 0) + 1

        stats['kept'] = int(stats.get('kept', 0)) + len(kept)
        stats['dropped'] = int(stats.get('dropped', 0)) + sum(dropped.values())
        if dropped:
            hist = stats.setdefault('last_dropped_classes', {})
            for k, v in dropped.items():
                hist[k] = int(hist.get(k, 0)) + v
            # 只保留最近 20 个不同类名，避免无界增长
            if len(hist) > 20:
                for k in list(hist.keys())[:len(hist) - 20]:
                    hist.pop(k, None)
            now = time.time()
            if now - float(stats.get('last_log_at', 0.0) or 0.0) > 5.0:
                stats['last_log_at'] = now
                _top = sorted(dropped.items(), key=lambda kv: -kv[1])[:5]
                logger.info("[RealtimeDetector] 已挡掉非交通类检测 "
                            f"{sum(dropped.values())} 个（累计 {stats['dropped']}）: "
                            + "、".join(f"{k}×{v}" for k, v in _top))
        return kept

    @staticmethod
    def _viol_neighbor_keys(sig):
        """把指纹扩成 3×3 邻域（含自身），用于跨圈重复抑制的滑动窗口匹配

        指纹格式 `"{类型}|{gx}|{gy}"`；末两段是 40px 网格坐标。
        拿不到坐标（`{类型}|nobb`）时只返回自身。
        """
        parts = str(sig).split('|')
        if len(parts) != 3:
            return (sig,)
        try:
            gx, gy = int(parts[1]), int(parts[2])
        except (TypeError, ValueError):
            return (sig,)
        t = parts[0]
        return tuple(f"{t}|{gx + dx}|{gy + dy}" for dx in (-1, 0, 1) for dy in (-1, 0, 1))

    @staticmethod
    def _viol_position_key(vtype, v):
        """违规的"类型 + 位置"指纹（2026-10-10 由 DSH 新增，用于跨圈重复抑制）

        位置取 detection/evidence 里的 bbox 中心，按 **40px 网格**分桶：
          · 同一辆闯红灯的车在视频里位置**固定**（实测 bbox 左上角稳定在 (1000,280) 一带）
          · 但 tracker 的框有几十像素抖动，精确坐标无法命中同一桶
        拿不到 bbox 时退化为"只有类型"，仍然可用（只是粒度更粗）。
        """
        bb = None
        for src in (v, v.get('evidence') or {}, v.get('location') or {}):
            if isinstance(src, dict) and isinstance(src.get('bbox'), (list, tuple)) \
                    and len(src['bbox']) >= 4:
                bb = src['bbox']
                break
        if not bb:
            return f"{vtype}|nobb"
        try:
            cx = (float(bb[0]) + float(bb[2])) / 2.0
            cy = (float(bb[1]) + float(bb[3])) / 2.0
        except (TypeError, ValueError):
            return f"{vtype}|nobb"
        return f"{vtype}|{int(cx // 40)}|{int(cy // 40)}"

    def _box_draw_stats(self):
        """读取绘制侧的关联统计（2026-10-09 由 DSH 新增，供 /status 观测）

        单独包一层 try：渲染器可能因字体/依赖问题不可用，那也只应让这一个字段为空，
        不能让 /status 整个 500（本项目已有"辅助功能拖垮主链路"的教训）。
        """
        try:
            from annotation_renderer import get_box_draw_stats
            return get_box_draw_stats()
        except Exception as e:
            return {'error': f'{type(e).__name__}: {e}'[:120]}

    def _frame_to_base64(self, frame):
        _, img_encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return base64.b64encode(img_encoded).decode('utf-8')

    def _active_model_sequence(self):
        """当前多模型检测实际生效的序列（供 /status 观测）

        数据源是 image_recognizer.ACTIVE_MODEL_SEQUENCE（multi_model_detect 每次
        调用刷新）；若还没跑过任何一帧，则按环境变量推算，保证"启动即可观测"。
        """
        try:
            from image_recognizer import ACTIVE_MODEL_SEQUENCE as _seq
            if _seq:
                return list(_seq)
        except Exception:
            pass
        _want = (os.environ.get('YOLO_MODEL_SEQUENCE') or '').strip()
        if _want:
            return [k.strip() for k in _want.split(',') if k.strip()]
        return ['vehicle', 'traffic_light', 'helmet', 'lane', 'license_plate']

    def _predict_boxes(self, tracked_vehicles):
        """按「距上次检测过了多久」外推每辆车的框位置（**仅供显示**）

        ★★2026-10-06 由 DSH 重写 —— 第一版有两个致命错误，导致功能**从未生效**：
          ① 把 tracked_vehicles 当成 list 遍历，而它实际是
             `{track_id: {...}}` 的 **dict**（`vehicle_tracker` 返回 OrderedDict）
             -> 遍历出来的是字符串键 -> `v.get(...)` 抛 AttributeError
             -> 被我自己的 `except` 吞掉 -> 静默退回原框；
          ② 返回 list，而渲染器 `AnnotationRenderer.render(tracked_vehicles=...)`
             要求的是 **Dict**。
          教训：写"仅显示"的辅助函数也必须先核对**上游产出的真实类型**；
          并且"加了 try/except 兜底"会让类型错误彻底静默 —— 兜底要有可观测的计数。

        设计要点：
          · 只平移、不改尺寸（尺寸外推没有可靠依据，还会把框拉变形）；
          · 速度用**最近 4 个轨迹点**的位移中位数（对单帧抖动更稳），
            拿不到时退回 tracker 的 `speed`(px/s)；
          · 外推倍数 = min(距今 / 检测间隔, MAX_FACTOR=3.0)，防"检测卡住"时甩飞；
          · 平移量再夹在画面尺寸的 12% 以内，作为最后一道保险；
          · **输入输出同型**：dict 进、dict 出；且不修改传入对象。
        """
        try:
            if not tracked_vehicles:
                self._pred_stats['skip_empty'] = self._pred_stats.get('skip_empty', 0) + 1
                return tracked_vehicles

            # 兼容 list 与 dict 两种形态（上游现在是 dict，但不写死假设）
            if isinstance(tracked_vehicles, dict):
                items = list(tracked_vehicles.items())
            else:
                items = [(str(i), v) for i, v in enumerate(tracked_vehicles)]

            now = time.time()
            last_ok = getattr(self, '_last_detect_wall_ts', 0) or 0
            if not last_ok:
                self._pred_stats['skip_no_ts'] = self._pred_stats.get('skip_no_ts', 0) + 1
                return tracked_vehicles
            elapsed = now - last_ok
            if elapsed <= 0.02:                 # 刚检测完，无需预测
                self._pred_stats['skip_fresh'] = self._pred_stats.get('skip_fresh', 0) + 1
                return tracked_vehicles
            det_iv = float(getattr(self, '_det_interval_ema', 0.0) or 0.0)
            if det_iv <= 0.05:
                det_iv = max(0.05, min(1.0, elapsed))
            factor = min(elapsed / det_iv, 3.0)
            if factor <= 0.05:
                self._pred_stats['skip_small_factor'] = self._pred_stats.get('skip_small_factor', 0) + 1
                return tracked_vehicles

            self._pred_stats['ran'] = self._pred_stats.get('ran', 0) + 1
            self._pred_stats['last_elapsed_ms'] = round(elapsed * 1000)
            self._pred_stats['last_factor'] = round(factor, 2)
            self._pred_stats['last_det_iv_ms'] = round(det_iv * 1000)

            cf = getattr(self, 'current_frame', None)
            if cf is not None and getattr(cf, 'shape', None) is not None:
                fh, fw = int(cf.shape[0]), int(cf.shape[1])
            else:
                fh, fw = 1080, 1920
            max_shift = 0.12 * float(max(fw, fh))

            observed = []
            result = {}
            for key, v in items:
                if not isinstance(v, dict):
                    result[key] = v
                    continue
                bb = v.get('bbox')
                if not (isinstance(bb, (list, tuple)) and len(bb) >= 4):
                    result[key] = v
                    continue
                try:
                    x1, y1, x2, y2 = [float(t) for t in bb[:4]]
                    dx = dy = 0.0
                    got = False
                    hist = v.get('history') or []
                    if len(hist) >= 2:
                        pts = []
                        for h in hist[-4:]:
                            c = h.get('center') if isinstance(h, dict) else None
                            if c is not None and len(c) >= 2:
                                pts.append((float(c[0]), float(c[1])))
                        if len(pts) >= 2:
                            ddx = sorted(pts[i][0] - pts[i - 1][0] for i in range(1, len(pts)))
                            ddy = sorted(pts[i][1] - pts[i - 1][1] for i in range(1, len(pts)))
                            dx = ddx[len(ddx) // 2]          # 中位位移（px/采样）
                            dy = ddy[len(ddy) // 2]
                            got = True
                    if not got:
                        sp = float(v.get('speed') or 0.0)
                        if sp > 0 and det_iv > 0:
                            px = sp * det_iv
                            d = str(v.get('direction') or '').lower()
                            if d in ('left', 'right'):
                                dx = -px if d == 'left' else px
                            elif d in ('up', 'down'):
                                dy = -px if d == 'up' else px
                            else:
                                dx = px
                            got = True
                    if not got:
                        result[key] = v
                        continue
                    sx, sy = dx * factor, dy * factor
                    n = (sx * sx + sy * sy) ** 0.5
                    if n > max_shift:
                        sx *= max_shift / n
                        sy *= max_shift / n
                    nv = dict(v)
                    nv['bbox'] = [x1 + sx, y1 + sy, x2 + sx, y2 + sy]
                    nv['_predicted'] = True
                    result[key] = nv
                    observed.append({
                        'track_id': v.get('id', v.get('track_id', key)),
                        'bbox': [round(t, 1) for t in nv['bbox']],
                        'predicted': True,
                    })
                except Exception:
                    result[key] = v

            # 只读观测出口（/status 的 predicted_boxes）
            self._last_predicted = observed[:12]
            self._pred_stats['last_out_n'] = len(result)
            self._pred_stats['last_observed_n'] = len(observed)
            return result
        except Exception as e:
            self._pred_stats['error'] = str(e)[:120]
            return tracked_vehicles

    def _draw_detection_boxes(self, frame, detections, tracked_vehicles=None,
                              violations=None):
        """在帧上绘制识别框与中文标注

        2026-10-02 由 DSH 重写：改用 annotation_renderer.AnnotationRenderer
        原因：
          1. cv2.putText 不支持中文（原实现里的 "逆行" 实际渲染为乱码/空）
          2. 需要"违规→红框+违规类型，正常→绿框不显示类型"的区分
          3. 需要红绿灯框 + 颜色标注

        保持函数签名向后兼容（violations 为可选参数），6 处既有调用点无需改动；
        违规/红绿灯信息也可由实例属性 self._last_violations / self._last_traffic_lights
        提供（供实时显示线程使用）。
        """
        try:
            from annotation_renderer import get_renderer
            renderer = get_renderer()
        except Exception as e:
            logger.warning(f"[RealtimeDetector] 标注渲染器不可用，跳过画框: {e}")
            return frame

        if violations is None:
            violations = getattr(self, "_last_violations", None) or []
        traffic_lights = getattr(self, "_last_traffic_lights", None) or []

        # ★★2026-10-09 由 DSH 新增：**绘制侧 ROI 过滤**（设计单 §12.6 问题 1）
        #
        # 用户原话："左边不该识别的红绿灯还是识别了"。
        # 根因：灯态**判定**确实只认 ROI 内的灯（_scene_light_state_from_cnn），
        #   但**绘制**没有任何过滤 —— _collect_traffic_lights 会把画面里所有
        #   判出颜色的灯都塞进 _last_traffic_lights，渲染器把它们**全部画出来**。
        #   trace 铁证（_rt_trace_final.jsonl）：左侧横向车道的黄灯
        #   ('yellow',(419,120)) 出现 252+228 次、('red',(275,182)) 200 次。
        #
        # ★ 关键顺序约束（设计单里特别警告过）：
        #   灯态汇总 `_scene_light_state_from_cnn` 读的**就是** _last_traffic_lights，
        #   而且它自己已经按 ROI 过滤过。所以这里**绝不能**去改
        #   _last_traffic_lights 本身（那会把判色/判定链路一起裁掉）——
        #   只过滤**传给渲染器的这份副本**。判定语义 100% 不变。
        # 未标 ROI 时保持旧行为（全部画），否则用户第一次标定时根本找不到灯。
        _rois_draw = (getattr(self, '_scene_annotation', None) or {}).get('traffic_light_roi')
        self._lights_filtered_for_draw = len(traffic_lights)      # 供 /status 观测
        if _rois_draw:
            try:
                traffic_lights = [it for it in traffic_lights
                                  if self._light_in_rois(it.get("bbox"), _rois_draw)]
            except Exception as e:
                logger.debug(f"[RealtimeDetector] 灯框绘制过滤失败（改为全画）: {e}")
        self._lights_drawn = len(traffic_lights)
        # 车牌：优先用后台识别线程写入的缓存（2026-10-03 由 DSH 接入）
        plates = {}
        try:
            with self._plate_lock:
                plates = dict(getattr(self, "_plate_cache", {}) or {})
        except Exception:
            plates = getattr(self, "_plate_cache", {}) or {}

        # ★★2026-10-06 由 DSH 新增：**框位置预测**（解决"识别框跟不上车"）
        # ------------------------------------------------------------------
        # 实测事实：端到端真实吞吐只有 ~2 fps（单帧 480~560ms，其中模型只占 139ms），
        #   而每处理 1 帧画面时间就跳过 **0.3 秒**（= 6 帧画面没检测）。
        #   流接口是"每请求用当前帧 + 缓存检测结果重画" -> 画面流畅、但框每 0.3~0.56s
        #   才跳一次，看起来就是"框跟不上车"。
        # 修法：两次检测之间，用该车**最近几帧的位移**做线性外推，只平移框、不改尺寸。
        #   这样框跟着车连续滑动（流仍是 10~20fps），**不需要额外算力**。
        # 安全性：只改**显示用的副本**（display_vehicles），
        #   绝不回写 tracked_vehicles / detections —— 违规判定与测速用的仍是真实数据，
        #   所以"预测误差"不可能影响判罚结论。
        # 关闭方式：环境变量 BOX_PREDICTION=0
        if str(os.environ.get('BOX_PREDICTION', '1')).lower() not in ('0', 'false', 'off'):
            tracked_vehicles = self._predict_boxes(tracked_vehicles)

        try:
            cv2.putText  # noqa: B018  仅确认 cv2 可用
            return renderer.render(
                frame,
                detections=detections or [],
                tracked_vehicles=tracked_vehicles or {},
                violations=violations,
                traffic_lights=traffic_lights,
                plate_of_track=plates,
            )
        except Exception as e:
            logger.warning(f"[RealtimeDetector] 画框失败（回退原帧）: {e}")
            return frame

    # ------------------------------------------------------------------
    # 红绿灯颜色判定（HSV ROI 分析，参考 K230 red_light.py 的色块阈值法）
    # ------------------------------------------------------------------
    def _analyze_traffic_light_color(self, frame, bbox):
        """从红绿灯框内裁剪 ROI，用 HSV 统计判定颜色

        返回 'red' / 'yellow' / 'green' / 'unknown'
        """
        try:
            x1, y1, x2, y2 = [int(v) for v in bbox[:4]]
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 - x1 < 4 or y2 - y1 < 4:
                return "unknown"
            roi = frame[y1:y2, x1:x2]
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            # 红色跨 0 度，分两段
            masks = {
                "red": cv2.bitwise_or(
                    cv2.inRange(hsv, (0, 70, 60), (10, 255, 255)),
                    cv2.inRange(hsv, (170, 70, 60), (180, 255, 255))),
                "yellow": cv2.inRange(hsv, (15, 70, 70), (35, 255, 255)),
                "green": cv2.inRange(hsv, (40, 60, 60), (90, 255, 255)),
            }
            counts = {k: int(cv2.countNonZero(m)) for k, m in masks.items()}
            total = roi.shape[0] * roi.shape[1]
            best = max(counts, key=counts.get)
            # 占比过低认为无法判定（避免在无灯画面误判）
            if total <= 0 or counts[best] < max(6, int(total * 0.02)):
                return "unknown"
            return best
        except Exception:
            return "unknown"

    @staticmethod
    def _crop_lit_lens(roi):
        """从红绿灯框里裁出「被点亮的那颗镜片」（上=红位 / 中=黄位 / 下=绿位）。

        ★2026-10-04 由 DSH 新增。实测依据见调用点注释：
          不做这步时 CNN5 在演示视频上 11/14，做了之后 14/14=100%。
        做法：竖直三等分，按「最亮 10% 像素的均值」选最亮的一片。
        兜底：框太小（<3px/片）或三片亮度接近时，原样返回，不冒险。
        """
        try:
            import numpy as _np
            import cv2 as _cv2
            h, w = roi.shape[:2]
            if h < 9 or w < 3:
                return roi
            third = max(3, h // 3)
            g = _cv2.cvtColor(roi, _cv2.COLOR_BGR2GRAY).astype(_np.float32)
            scores, spans = [], []
            for k in range(3):
                y0 = k * third
                y1 = (k + 1) * third if k < 2 else h
                seg = g[y0:y1]
                spans.append((y0, y1))
                if seg.size == 0:
                    scores.append(-1.0)
                    continue
                thr = _np.percentile(seg, 90)
                sel = seg[seg >= thr]
                scores.append(float(sel.mean()) if sel.size else float(seg.mean()))
            bi = int(_np.argmax(scores))
            srt = sorted(scores, reverse=True)
            # 三片亮度太接近 -> 无法可靠判定是哪一颗被点亮，原样返回
            if len(srt) >= 2 and (srt[0] - srt[1]) < 2.0:
                return roi
            y0, y1 = spans[bi]
            out = roi[y0:y1, :]
            return out if out.size else roi
        except Exception:
            return roi

    def _collect_traffic_lights(self, frame, detections):
        """收集红绿灯框 + 颜色，写入 self._last_traffic_lights

        2026-10-03 由 DSH 升级为 CNN 判色：
          - 优先用自训 CNN4（green/red/yellow/none），交叉验证 0.997
          - 判为 none -> **丢弃该框**（模型明确认为"这不是红绿灯"，即去误检）
          - CNN 不可用/置信度不足 -> 回退 HSV（保证功能不中断）
          - 统计字段供 /status 观测
        """
        out = []
        stats = {"total": 0, "none_dropped": 0, "cnn": 0, "hsv": 0, "unknown": 0}
        try:
            from traffic_light_classifier import (classify_traffic_light,
                                                  hsv_fallback_state)
        except Exception:
            classify_traffic_light = None
            hsv_fallback_state = None

        for det in detections or []:
            cls = (det.get("class_name") or "").lower()
            # ★2026-10-04 由 DSH 修正：**补上裸色名**。
            #
            # 背景：项目里有一个专门的红绿灯颜色模型（image_recognizer.py:177
            #   'classes': ['red','yellow','green']），它输出的 class_name 就是
            #   **裸色名**（'red'/'yellow'/'green'），不是 'traffic light'。
            # 原白名单只认 'traffic light'/'red_light'/'green_light'/'yellow_light'，
            # 于是把该模型的**全部**检测都 continue 掉了 ->
            #   _collect_traffic_lights 恒返回 0、traffic_light_stats 恒为空、
            #   红绿灯框一个都画不出来（端到端实测：确认出红绿灯框 0/520 帧）。
            #
            # 现在同时接受三种写法；颜色一律由**本函数的判色器**重判
            # （不再信任上游模型的颜色，避免第三条判色路径与 CNN 冲突）。
            if cls not in _TL_LIGHT_NAMES:
                continue
            bb = det.get("bbox") or []
            if len(bb) < 4:
                continue
            stats["total"] += 1

            # ★ 2026-10-04 由 DSH 修正：**取消扩边**
            #
            # 原实现：把 YOLO 框四周扩 25% 再喂判色器（理由是"分类器需要灯壳上下文"）。
            # 实测（377 张真实样本：red54 green48 yellow15 none260）证明扩边有害：
            #
            #   输入处理            判色        拒识       假阳性   黄→红
            #   原样（不处理）      117/117=100%  260/260=100%   0      0   ← 最优
            #   扩边 10%           117/117=100%  260/260=100%   0      0
            #   扩边 25%（原实现）  109/117= 93%  259/260=100%   1      8
            #   扩边 40%           104/117= 89%  259/260=100%   1      -
            #
            # 被扩边害错的 9 例中，**8 例是"黄灯被判成红灯"** ——
            # 黄→红会误报闯红灯，属危险方向。
            # 原因：扩边把框外背景像素带进来，干扰分类器。
            #
            # 注意：x1/y1/x2/y2 必须在这里解包 —— 后面裁 ROI 要用
            #      （曾因删掉扩边块时连带删掉解包，导致 NameError 被外层
            #        except 静默吞掉，红绿灯判色 100% 失效，已修复）
            x1, y1, x2, y2 = [int(v) for v in bb[:4]]
            H, W = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(W, x2), min(H, y2)
            if x2 - x1 < 4 or y2 - y1 < 4:
                continue
            roi = frame[y1:y2, x1:x2]

            state, conf = ("unknown", 0.0)
            if classify_traffic_light is not None:
                # ★2026-10-04 新增：先裁出「被点亮的那颗镜片」再判色
                #
                # 实测依据（演示视频 14 帧，真值=钉死灯态）：
                #   裁图方式        CNN4(原)   CNN5(重训)
                #   原样(raw)        0/14      11/14
                #   lit(本次)        0/14      14/14 = 100%
                #   peak13           0/14      14/14
                #
                # 原因：**真实视频里灯珠填满 YOLO 框，而 CARLA 里灯珠只占框内一小块**
                # （灯头 15x41 px，点亮镜片仅约 10x12 px）。
                # 判色模型是在「灯珠填满框」的样本上学的，不裁就会判不准。
                # 裁法：框内三等分（上=红位/中=黄位/下=绿位），取亮度最高的一片。
                roi_c = self._crop_lit_lens(roi)
                state, conf = classify_traffic_light(roi_c)
                if state != "unknown":
                    stats["cnn"] += 1

            # ---- HSV 兜底（2026-10-04 由 DSH 收紧）------------------------
            # 实测问题：真实视频上 CNN 与 HSV 一致率仅 23%，且出现
            #   CNN=red(conf 0.97) 而 HSV=green  —— **红→绿方向错误**，
            #   这是最危险的方向（会把闯红灯漏掉）。
            # 原因：灯框常只有 6x16 像素，HSV 色相统计在小 ROI 上噪声极大。
            #
            # 因此收紧为：**仅在 CNN 完全不可用（模型加载失败）时才用 HSV**。
            # 默认行为 = CNN 说 unknown 就**不画框**（"宁可不画，不可误导"），
            # 与既有的 none/unknown 处理策略一致。
            # 如需恢复旧行为：设 TL_HSV_FALLBACK=always
            # ---------------------------------------------------------------
            _hsv_mode = str(os.environ.get('TL_HSV_FALLBACK', 'cnn_only')).lower()
            _use_hsv = (_hsv_mode in ('always', '1', 'true', 'on')
                        or classify_traffic_light is None)
            if state == "unknown" and _use_hsv and hsv_fallback_state is not None:
                hsv_state = hsv_fallback_state(roi)
                if hsv_state != "unknown":
                    state = hsv_state
                    conf = 0.0
                    stats["hsv"] += 1
            elif state == "unknown":
                stats["hsv_skipped"] = stats.get("hsv_skipped", 0) + 1

            if state == "none":
                stats["none_dropped"] += 1
                continue                      # 明确不是红绿灯：不画框
            if state == "unknown":
                stats["unknown"] += 1
                continue                      # 无法判定：宁可不画，避免误导

            out.append({"bbox": bb, "color": state, "confidence": round(conf, 3)})

        self._last_traffic_lights = out
        self.traffic_light_stats = stats
        return out

    def _try_recognize_plates(self, frame):
        """后台识别车牌（2026-10-03 由 DSH 新增）

        为什么放后台线程：
          hyperlpr3 对"裁剪+放大"后的车辆图识别约 5-150ms，
          直接放进检测循环会拖慢帧率。这里限流（每 PLATE_INTERVAL 秒一次），
          识别结果写入 self._plate_cache，供画框时零延迟读取。
        """
        interval = float(os.environ.get('PLATE_INTERVAL_SEC', '2.0'))
        now = time.time()
        if now - getattr(self, '_plate_last_try', 0.0) < interval:
            return
        if getattr(self, '_plate_busy', False):
            return
        self._plate_last_try = now
        self._plate_busy = True

        # 拷贝需要的车辆框（避免跨线程读取共享 dict）
        boxes, tids = [], []
        try:
            with self.lock:
                for tid, veh in (self.tracked_vehicles or {}).items():
                    bb = veh.get('bbox') or []
                    if len(bb) >= 4:
                        boxes.append(list(bb[:4]))
                        tids.append(tid)
        except Exception:
            self._plate_busy = False
            return
        if not boxes:
            self._plate_busy = False
            return
        frame_copy = frame.copy()

        def worker():
            try:
                from plate_recognizer import recognize_in_frame
                res = recognize_in_frame(frame_copy, boxes, tids)
                if res:
                    with self._plate_lock:
                        for item in res:
                            tid = item.get('track_id')
                            if tid is not None:
                                self._plate_cache[int(tid)] = item['plate']
                    logger.info(f"[RealtimeDetector] 车牌识别: " +
                                ", ".join(f"ID{i.get('track_id')}={i['plate']}"
                                          f"({i['confidence']:.2f})" for i in res[:4]))
            except Exception as e:
                logger.debug(f"[RealtimeDetector] 车牌识别失败: {e}")
            finally:
                self._plate_busy = False

        threading.Thread(target=worker, daemon=True, name="plate-ocr").start()

    def _push_recent_violations(self, violations):
        """把本帧违规写入"带时效的最近违规"缓存（2026-10-03 由 DSH 新增）

        为什么不直接用 _last_violations：它每帧被覆盖，且无违规的帧会立刻清空，
        而违规受"确认时长+冷却期"抑制，绝大多数帧都是空的 ->
        前端实时页面永远看不到违规（实测右栏恒为 0）。
        这里保留 TTL 秒内的违规，让页面有稳定的展示窗口；同类型+同车去重。
        """
        try:
            now = time.time()
            for v in violations or []:
                key = (v.get('violation_type'), v.get('vehicle_id') or v.get('track_id'))
                # 去重：同键只更新时间戳（避免列表膨胀/重复告警）
                for item in self._recent_violations:
                    if item.get('key') == key:
                        item['ts'] = now
                        item['v'] = v
                        break
                else:
                    self._recent_violations.append({'key': key, 'v': v, 'ts': now})
            # 清理过期
            self._recent_violations = [
                it for it in self._recent_violations
                if (now - it['ts']) <= self._recent_viol_ttl
            ][-50:]
        except Exception as e:
            logger.debug(f"[RealtimeDetector] 最近违规缓存写入失败: {e}")

    def _push_repeat_alert(self, v):
        """把"被跨圈抑制的重复违规"喂给展示缓存（2026-10-10 由 DSH 新增）

        与 `_push_recent_violations` 的区别：
          · 那条路走的是"**已确认并已上报**"的违规（会存证据、可能触发云端）；
          · 这条路走的是"**判定成立、但这轮不重复存证**"的重复出现
            （`loop_dedup_sec` 命中）——**只用于告警栏展示**，绝不落库、绝不触发云端。
        标记 `repeat=True`，前端显示为「重复出现」，避免与"新违规"混淆。
        """
        try:
            now = time.time()
            key = ('repeat', v.get('violation_type'), v.get('vehicle_id') or v.get('track_id'))
            item_v = dict(v)
            item_v['repeat'] = True
            for item in self._recent_violations:
                if item.get('key') == key:
                    item['ts'] = now
                    item['v'] = item_v
                    return
            self._recent_violations.append({'key': key, 'v': item_v, 'ts': now})
            # 与主路径一致：清理过期 + 限制条数
            self._recent_violations = [
                it for it in self._recent_violations
                if (now - it['ts']) <= self._recent_viol_ttl
            ][-50:]
        except Exception as e:
            logger.debug(f"[RealtimeDetector] 重复告警写入失败: {e}")

    def get_recent_violations(self):
        """读取 TTL 内的最近违规（含 age 秒数），供实时页面展示"""
        now = time.time()
        out = []
        for it in list(getattr(self, '_recent_violations', []) or []):
            age = now - it.get('ts', now)
            if age > self._recent_viol_ttl:
                continue
            v = dict(it.get('v') or {})
            v['_age_sec'] = round(age, 1)
            out.append(v)
        return out

    def _attach_track_ids(self, detections, iou_threshold: float = 0.12):
        """把追踪得到的 track_id 回填到检测框上（2026-10-03 由 DSH 新增）

        目的：让规则引擎产出的违规带上 `vehicle_id`，前端才能把违规与
        "哪辆车"对应起来（右侧违规车辆栏 / 拉近动画 / 证据归属都依赖它）。

        匹配门限说明：实测 ByteTrack 输出的 bbox 与原始检测框存在偏移
        （同一辆卡车：检测 [565,157,688,364] vs 追踪 [627,261,750,467]，
        IoU≈0.11），故 IoU 门限设为 0.12 并辅以"中心点包含"兜底。
        仍不匹配则**不写 ID**（宁可留空，不编造归属）。
        """
        try:
            tracked = self.tracked_vehicles or {}
            if not tracked or not detections:
                return
            boxes = []
            for tid, veh in tracked.items():
                bb = veh.get('bbox') or []
                if len(bb) >= 4:
                    try:
                        boxes.append((int(tid), [float(v) for v in bb[:4]]))
                    except (TypeError, ValueError):
                        continue
            if not boxes:
                return
            for det in detections:
                bb = det.get('bbox') or []
                if len(bb) < 4:
                    continue
                try:
                    ax1, ay1, ax2, ay2 = [float(v) for v in bb[:4]]
                except (TypeError, ValueError):
                    continue
                a_area = max(1.0, (ax2 - ax1) * (ay2 - ay1))
                cx, cy = (ax1 + ax2) / 2.0, (ay1 + ay2) / 2.0
                best_id, best_iou = None, 0.0
                for tid, t in boxes:
                    ix1, iy1 = max(ax1, t[0]), max(ay1, t[1])
                    ix2, iy2 = min(ax2, t[2]), min(ay2, t[3])
                    if ix2 <= ix1 or iy2 <= iy1:
                        continue
                    inter = (ix2 - ix1) * (iy2 - iy1)
                    b_area = max(1.0, (t[2] - t[0]) * (t[3] - t[1]))
                    iou = inter / (a_area + b_area - inter)
                    if iou > best_iou:
                        best_id, best_iou = tid, iou
                if best_iou < iou_threshold or best_id is None:
                    # 退化：中心点包含于车辆框
                    best_id = None
                    for tid, t in boxes:
                        if t[0] <= cx <= t[2] and t[1] <= cy <= t[3]:
                            best_id = tid
                            break
                if best_id is None:
                    # 再退化：车辆框中心点落在检测框内（应对 tracker 框偏移）
                    for tid, t in boxes:
                        tcx, tcy = (t[0] + t[2]) / 2.0, (t[1] + t[3]) / 2.0
                        if ax1 <= tcx <= ax2 and ay1 <= tcy <= ay2:
                            best_id = tid
                            break
                if best_id is not None:
                    det['track_id'] = best_id
                    det['vehicle_id'] = best_id
        except Exception as e:
            logger.debug(f"[RealtimeDetector] track_id 回填失败: {e}")

    def get_annotated_frame(self):
        with self.lock:
            if self.current_frame is None:
                # 关键修复：永不返回 None，避免 MJPEG 前端 img 元素显示橙色/空白异常画面
                status = "Not Started (Qing Dian Kai Shi Jian Ce)" if not self.running else "No Frame (She Xiang Tou Lian Zhong)"
                lines = [
                    f"[STATUS] {status}",
                    f"running={self.running}  frame_count={self.frame_count}",
                    "",
                    "Tip A (AI检测页 /ai-detect): call POST /api/realtime/start first",
                    "Tip B (实时监控页 /realtime): click '开始检测' button (not this stream)",
                    "Tip C: close apps using camera (WeChat / Teams / Zoom)",
                    "Tip D: on Windows the preferred backend is cv2.CAP_DSHOW",
                ]
                return self._make_diagnostic_frame(
                    title='NO VIDEO FRAME - SHE XIANG TOU WEI JIA ZAI',
                    lines=lines,
                    bg_color=(60, 30, 10),  # 深蓝灰（不会被误认为橙色）
                )

            frame = self.current_frame.copy()
            tracked_vehicles = self.tracked_vehicles
            
            if self.last_detection_result:
                detections = self.last_detection_result.get('detections', [])
                frame = self._draw_detection_boxes(frame, detections, tracked_vehicles)
                
                behaviors = self.last_detection_result.get('behaviors', [])
                violations = self.last_detection_result.get('violations', [])
                
                all_violations = []
                for behavior in behaviors:
                    if behavior.get('is_violation'):
                        all_violations.append({
                            'violation_type_cn': behavior.get('behavior_type_cn', behavior.get('behavior_type')),
                            'confidence': behavior.get('confidence', 0),
                            'vehicle_id': behavior.get('vehicle_id')
                        })
                
                for vio in violations:
                    if vio.get('source') != 'behavior_engine':
                        all_violations.append({
                            'violation_type_cn': vio.get('violation_type_cn', vio.get('violation_type')),
                            'confidence': vio.get('confidence', 0),
                            'vehicle_id': None
                        })
                
                if all_violations:
                    # 2026-10-02 由 DSH 修复：原先用 cv2.putText 画中文，
                    # OpenCV Hershey 字体无中文字形 -> 实际显示为 "?" 乱码。
                    # 改用 annotation_renderer（PIL + 中文字体）。
                    try:
                        from annotation_renderer import get_renderer
                        _r = get_renderer()
                        _items = []
                        for idx, vio in enumerate(all_violations[:3]):
                            y_offset = 25 + idx * 22
                            vehicle_info = f"(车{vio.get('vehicle_id')})" if vio.get('vehicle_id') else ""
                            # 注意：不使用 ⚠ 等 emoji（微软雅黑无该字形，会渲染成方框）
                            text = (f"【违规】{vio.get('violation_type_cn')}{vehicle_info} "
                                    f"{vio.get('confidence', 0):.2f}")
                            _items.append((text, 10, y_offset, (255, 255, 255),
                                           (60, 60, 235), 18))
                        frame = _r.draw_texts(frame, _items)
                    except Exception as e:
                        logger.debug(f"[RealtimeDetector] 违规告警文本绘制失败: {e}")
            
            status = self.get_status()
            fps_text = f"FPS: {status['current_fps']:.1f}"
            cv2.putText(frame, fps_text, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            return frame

    def get_context_frames(self):
        with self.lock:
            cache_list = list(self.frame_cache)
        
        frames = []
        if len(cache_list) >= 4:
            frames.append(cache_list[-4] if len(cache_list) >= 4 else None)
            frames.append(cache_list[-3] if len(cache_list) >= 3 else None)
            frames.append(cache_list[-2] if len(cache_list) >= 2 else None)
            frames.append(cache_list[-1] if len(cache_list) >= 1 else None)
        
        return [self._frame_to_base64(f) if f is not None else None for f in frames]

    def _save_violation_evidence(self, frame, violations):
        """保存违规证据：图片落盘 + **数据库落库（含车牌）** + 通知车主

        2026-10-03 由 DSH 重写。原实现**只写图片文件、不写数据库**，
        导致：
          · violation_evidences 长期只有早期 API 测试的少量记录（实测 20 行）
          · 违规记录里没有车牌 -> 小程序"我的违规"永远匹配 0 条
        现在补齐三件事：① 写库 ② 附上车牌（车牌识别已就绪）③ 按车牌反查
        绑定车主并发通知（未配置微信时自动退化为站内信）。
        """
        try:
            uploads_dir = Config.UPLOAD_DIR
            os.makedirs(uploads_dir, exist_ok=True)

            # ★2026-10-10 由 DSH 加固：文件名加**毫秒**。
            #   原实现只到"秒"（`%Y%m%d_%H%M%S`），而 `_persist_violation` 用的
            #   `image_path` 就是**这个文件名**（`os.path.basename`）。同一秒内如果
            #   出现两条同类型违规（多车同时闯红灯完全可能），后写入的会**覆盖**前一
            #   张图，而两条 DB 记录指向**同一张图** -> 其中一条的证据图内容不对
            #   （"证据不可追溯"是项目红线，这类静默错配必须堵掉）。
            #   list_realtime_evidence 的正则只匹配到秒，多余后缀不影响它（它按下划线切分）。
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 毫秒用 **`-`** 分隔（不是 `_`）：`list_realtime_evidence` 用
            # "最后一个下划线后是时间戳"的经验规则切分类型，
            # 若写成 `..._221353_123.jpg`，类型会变成 "red_light_221353"。
            # 写成 `..._221353-123.jpg` 则类型解析不受影响。
            _ms = datetime.now().strftime("%f")[:3]
            violation_types = '_'.join(v.get('violation_type', '') for v in violations)
            filename = f"realtime_{violation_types}_{timestamp}-{_ms}.jpg"
            filepath = os.path.join(uploads_dir, filename)

            with self.lock:
                detections = self.last_detection_result.get('detections', []) if self.last_detection_result else []
                plates = dict(getattr(self, '_plate_cache', {}) or {})

            annotated = self._draw_detection_boxes(frame.copy(), detections)
            cv2.imwrite(filepath, annotated)
            logger.info(f"[RealtimeDetector] 证据已保存: {filepath}")

            # ---- 逐条违规落库（含车牌）------------------------------------
            for v in violations or []:
                vtype = v.get('violation_type') or 'unknown'
                vid = v.get('vehicle_id', v.get('track_id'))
                plate = None
                try:
                    if vid is not None:
                        plate = plates.get(int(vid))
                except (TypeError, ValueError):
                    plate = None
                # 车牌可能挂在 evidence 里（上游不同来源）
                if not plate:
                    ev = v.get('evidence') or {}
                    if isinstance(ev, dict):
                        plate = ev.get('plate') or ev.get('plate_number')
                self._persist_violation(vtype, v, filepath, plate)
                if plate:
                    self._notify_owner(plate, vtype, v, filepath)
        except Exception as e:
            logger.error(f"[RealtimeDetector] 保存证据失败: {e}")

    def _persist_violation(self, vtype, v, image_path, plate):
        """把一条违规写入 violation_evidences（含 plate_number）"""
        try:
            from database import SessionLocal
            from models import ViolationEvidence
            db = SessionLocal()
            try:
                pos = v.get('location') or {}
                rec = ViolationEvidence(
                    violation_type=vtype,
                    track_id=(lambda x: int(x) if x is not None else None)(
                        v.get('vehicle_id', v.get('track_id'))),
                    confidence=float(v.get('confidence', 0) or 0),
                    position=json.dumps(pos, ensure_ascii=False, default=str),
                    timestamp=datetime.now(),
                    image_path=os.path.basename(image_path),
                    video_path=None,
                    additional_info=json.dumps({
                        'plate_number': plate,
                        'plate_source': 'realtime_ocr' if plate else None,
                        'violation_type_cn': v.get('violation_type_cn'),
                        'source': v.get('source', 'rule_engine'),
                        'evidence': v.get('evidence'),
                        'calibration': (v.get('evidence') or {}).get('calibration')
                        if isinstance(v.get('evidence'), dict) else None,
                    }, ensure_ascii=False, default=str),
                    cloud_validated=False,
                    status='pending',
                )
                db.add(rec)
                db.commit()
                logger.info(f"[RealtimeDetector] 违规已落库 id={rec.id} type={vtype} "
                            f"plate={plate or '未识别'} conf={rec.confidence:.2f}")
                return rec.id
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[RealtimeDetector] 违规落库失败({vtype}): "
                           f"{type(e).__name__}: {str(e)[:120]}")
            return None

    def _persist_evidence_chain(self, event, ai_result=None, note: str = ""):
        """写入事件证据链到数据库（2026-10-03 由 DSH 新增）

        ⚠ 背景：实测 `traffic_events.evidence_chain` **541 条全为空**
        （审计见 docs/AI_EVENT_REVIEW_AUDIT.md）。模型里该字段存在、
        EvidenceChain 类也已实现，但**从未有人调用并落库**。

        证据链是"事件全过程上下文"（车辆/场景/轨迹/关键帧/规则判断/AI判断），
        是本项目"证据可追溯"红线的载体，必须落库。
        """
        try:
            from evidence_chain import EvidenceChain
            from database import SessionLocal
            # 注意：模型类名是 TrafficEventRecord（表 traffic_events），
            # 不是 TrafficEvent（那是事件引擎里的 dataclass）。写错会 ImportError。
            from models import TrafficEventRecord

            vi = event.vehicle_info or {}
            sc = event.scene_context or {}
            # ★2026-11-05 修 B1：原先读 sc.get('traffic_light') / sc.get('lane') /
            # sc.get('location') —— 这三个键**在 scene_config 里根本不存在**，
            # 于是 2674/2674 条 evidence_chain 的灯态/停止线/车道/地点/车牌全是默认值。
            # 实测真实来源（两条都有，按优先级取）：
            #   ① rule_judgment.evidence.light_state / crossed_stop_line / vehicle_id
            #      —— 判定当刻的真实值（实测样例 "light_state":"red", "crossed_stop_line":true）
            #   ② scene_context.traffic_light_state / stop_line_y / road_direction
            #      —— 场景配置里的标定值
            # location / lane_id 在 scene_config 里没有对应字段（只有 road_direction /
            # road_zones / lane_lines），因此改为写可解释的语义值，不再伪装成"有但为空"。
            _ev = {}
            try:
                _rj = getattr(event, 'rule_judgment', None) or {}
                if isinstance(_rj, dict):
                    _ev = _rj.get('evidence') or {}
                    if not isinstance(_ev, dict):
                        _ev = {}
            except Exception:
                _ev = {}

            def _first(*vals):
                """取第一个"非空且非 unknown"的值"""
                for v in vals:
                    if v is None:
                        continue
                    s = str(v).strip()
                    if s and s.lower() not in ('unknown', 'none', 'null'):
                        return s
                return ''

            _light = _first(_ev.get('light_state'),
                            sc.get('traffic_light_state'),
                            sc.get('traffic_light'))
            _crossed = _ev.get('crossed_stop_line')
            if isinstance(_crossed, bool):
                _stop_rel = 'after' if _crossed else 'before'
            else:
                _stop_rel = _first(sc.get('stop_line_relation'))
            _road_dir = _first(sc.get('road_direction'))
            # ★2026-11-05 三次修正：`_source` 原本不在 scene_annotation._ALLOWED_KEYS，
            # load_scene 会把它过滤掉 → 运行时永远读不到。已把 `_source` 加进白名单
            # （只读元数据，前端不写，安全）。现在它才是可靠的地点来源。
            # 优先级：_source（视频/流路径，能指回具体点位）> location > camera_id。
            # 语义：location 是"哪个点位/哪路视频"，scene_config 无路名字段，不伪造路名。
            _loc = _first(sc.get('_source'),
                          sc.get('location'),
                          getattr(event, 'camera_id', None),
                          sc.get('camera_id'))
            # 车道号：scene_config 无 lane 编号字段（只有 lane_lines 折线 + road_direction），
            # 因此用 road_direction 写成"受控方向"标识，可追溯且不伪造车道编号。
            # 实测 vehicle_direction 在 rule_judgment.evidence 里，一并可用于逆行复核。
            _lane = _first(sc.get('lane'), sc.get('lane_id'),
                           sc.get('road_direction'), _ev.get('road_direction'))

            chain = EvidenceChain(
                camera_id=getattr(event, 'camera_id', None) or 'default',
                timestamp=str(getattr(event, 'trigger_time', '') or ''),
                location=_loc,
                vehicle_id=int(getattr(event, 'track_id', -1) or -1),
                vehicle_type=str(vi.get('class_name', 'unknown')),
                plate_number=str(vi.get('plate_number') or vi.get('plate') or ''),
                lane_id=_lane,
                traffic_light_state=_light or 'unknown',
                stop_line_relation=_stop_rel or 'unknown',
                trajectory=list(getattr(event, 'trajectory', None) or []),
                key_frames=list(getattr(event, 'key_frames', None) or []),
                event_video_path=str(getattr(event, 'event_video_path', '') or ''),
                rule_judgment=dict(getattr(event, 'rule_judgment', None) or {}),
                ai_judgment=dict(ai_result or {}),
                ai_confidence=float(getattr(event, 'ai_confidence', 0.0) or 0.0),
                ai_explanation=str(getattr(event, 'ai_explanation', '') or ''),
                final_status=(event.state.value if hasattr(event.state, 'value')
                              else str(event.state)),
            )
            payload = chain.to_json()
            if note:
                try:
                    import json as _json
                    d = _json.loads(payload)
                    d['_note'] = note
                    d['_persisted_at'] = datetime.now().isoformat()
                    payload = _json.dumps(d, ensure_ascii=False)
                except Exception:
                    pass

            db = SessionLocal()
            try:
                row = db.query(TrafficEventRecord).filter(
                    TrafficEventRecord.event_id == event.event_id).first()
                if row is None:
                    logger.debug(f"[RealtimeDetector] 证据链落库跳过：事件 {event.event_id} 不在库中")
                    return False
                row.evidence_chain = payload
                db.commit()
                logger.info(f"[RealtimeDetector] 证据链已落库 event={event.event_id} "
                            f"({len(payload)} 字节)")
                return True
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[RealtimeDetector] 证据链落库失败: {type(e).__name__}: {str(e)[:150]}")
            return False

    def _notify_owner(self, plate, vtype, v, image_path):
        """按车牌反查绑定车主并推送通知（未配置微信 -> 仅站内信）"""
        try:
            import wechat_miniapp as wx
            norm = wx.normalize_plate(plate)
            if not norm:
                return
            con = wx._conn()
            try:
                cur = con.cursor()
                cur.execute("SELECT openid FROM wx_vehicle_bindings WHERE plate_number=?",
                            (norm,))
                targets = [r['openid'] for r in cur.fetchall()]
            finally:
                con.close()
            if not targets:
                logger.debug(f"[RealtimeDetector] 车牌 {norm} 无绑定车主，跳过通知")
                return
            cn = v.get('violation_type_cn') or vtype
            for op in targets:
                wx.create_notification(
                    op, f"违规通知：{cn}",
                    f"你的车辆 {norm} 于 {datetime.now().strftime('%m-%d %H:%M')} "
                    f"被记录 {cn}（置信度 {float(v.get('confidence', 0) or 0):.2f}）",
                    plate_number=norm,
                    violation_id=None,
                    payload={'violation_type': vtype,
                             'image': os.path.basename(image_path),
                             'confidence': float(v.get('confidence', 0) or 0)},
                    push=True)
            logger.info(f"[RealtimeDetector] 已通知 {len(targets)} 位车主（车牌 {norm}）")
        except Exception as e:
            logger.debug(f"[RealtimeDetector] 通知车主失败: {type(e).__name__}: {e}")

    def _push_violation_event(self, result):
        event_data = {
            'event': 'violation_detected',
            'timestamp': result['timestamp'],
            # ★2026-10-11 由 DSH 新增：**服务端发出这一刻的墙钟**（epoch ms）。
            #   用途：把"告警比画面慢"拆成两半 ——
            #     端到端 = (浏览器收到 - pushed_at) + (DOM 出现 - 浏览器收到)
            #              └── 服务端/网络 ──┘   └──── 前端渲染 ────┘
            #   用户实测"将近 3 秒"，而前端侧我实测只有 152~277ms（含已删掉的 150ms 去抖），
            #   所以必须能量化"服务端这一侧"到底占了多少，不能再靠猜。
            'pushed_at': int(time.time() * 1000),
            'violations': result['violations'],
            'detections': result['detections'],
            'confidence': result['confidence'],
            'ai_trace': result.get('ai_trace')
        }
        
        async def send_to_clients():
            with self.lock:
                ws_clients = self.web_socket_clients[:]
                dt_clients = self.digital_twin_clients[:]
            
            for client in ws_clients:
                try:
                    await client.send_json(event_data)
                except Exception as e:
                    # ★2026-10-11 由 DSH 新增：**原来这里静默吞掉异常**（只把客户端移除）。
                    #   实测后果：`push_scheduled` 在涨、`push_failed=0`，看起来"推得好好的"，
                    #   但客户端**一条都收不到** —— 完全无从判断。
                    #   教训同 T75：异步/兜底路径必须留下可观测痕迹。
                    self._ws_push_failed = int(getattr(self, '_ws_push_failed', 0)) + 1
                    logger.warning(f"[RealtimeDetector] WebSocket 推送失败"
                                   f"（{type(e).__name__}: {str(e)[:160]}）-> 移除该客户端")
                    with self.lock:
                        if client in self.web_socket_clients:
                            self.web_socket_clients.remove(client)
            
            for client in dt_clients:
                try:
                    await client.send_json({
                        'type': 'violation',
                        'camera_id': f'cam_{self.camera_index}',
                        'violation_type': result['violations'][0].get('violation_type') if result['violations'] else 'unknown',
                        'confidence': result['confidence'],
                        'position': result['violations'][0].get('location', {}) if result['violations'] else {}
                    })
                except Exception:
                    with self.lock:
                        if client in self.digital_twin_clients:
                            self.digital_twin_clients.remove(client)
        
        if self.event_loop.is_running():
            asyncio.run_coroutine_threadsafe(send_to_clients(), self.event_loop)
            self._ws_push_scheduled = int(getattr(self, '_ws_push_scheduled', 0)) + 1
        else:
            # ★2026-10-11：循环没跑时原来**静默什么都不做**（前端因此永远收不到推送，
            #   而我只能靠"数不到推送"来推断，非常费时）。这里留一条可观测痕迹。
            self._ws_push_failed = int(getattr(self, '_ws_push_failed', 0)) + 1
            logger.warning(f"[RealtimeDetector] 违规事件无法推送：后台事件循环未运行"
                           f"（loop_alive={self.event_loop.is_running()}，"
                           f"clients={len(self.web_socket_clients)}）")

    def force_cloud_consult(self):
        with self.lock:
            if self.current_frame is None:
                return {"success": False, "message": "未获取到画面"}
            
            frame = self.current_frame.copy()
        
        frame_base64 = self._frame_to_base64(frame)
        
        detections = self._yolo_detect(frame)
        annotated_frame = self._draw_detection_boxes(frame.copy(), detections)
        annotated_base64 = self._frame_to_base64(annotated_frame)
        
        context_frames = self.get_context_frames()
        
        cloud_result = self.cloud_collaborator.consult_cloud_dual(
            frame_base64,
            annotated_base64,
            {'violation_type': 'manual_consult', 'confidence': 1.0},
            'consult',
            context_frames
        )
        
        return cloud_result

    def stop(self):
        # 先禁止新事件，但让采集循环继续运行，以便已触发事件录到 after_sec 的尾段。
        # 与事件引擎处理使用同一把锁，避免 stop 检查完 pending 后又出现新事件。
        with self._event_engine_process_lock:
            with self.lock:
                self._accept_new_events = False

        timeout = max(5.0, float(getattr(Config, 'EVENT_CLIP_AFTER_SEC', 5)) + 10.0)
        deadline = time.monotonic() + timeout
        timed_out = False
        with self._event_evidence_condition:
            while self._pending_event_evidence:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                self._event_evidence_condition.wait(min(remaining, 0.25))

        # 证据已固定（或超时）后再停采集。超时情况下保留缓存，防止后台线程取证时被清空。
        with self.lock:
            self.running = False
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            self.current_frame = None
            self.last_detection_result = None
            self.frame_cache.clear()

        if not timed_out and self.frame_buffer is not None:
            try:
                self.frame_buffer.clear()
            except Exception as e:
                logger.warning(f"[RealtimeDetector] 停止后清理循环缓存失败: {e}")

        if self.event_loop.is_running():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)

        if timed_out:
            logger.warning("[RealtimeDetector] 停止等待事件证据超时；为避免丢证据，保留循环缓存并阻止立即重启")
            return {"success": True, "message": "检测已停止，但事件证据仍在保存；请稍后再启动"}
        logger.info("[RealtimeDetector] 检测已停止")
        return {"success": True, "message": "检测已停止"}

    def get_status(self):
        # ★2026-10-09 由 DSH 新增：读状态前**先检查标注有没有被改过**。
        # 放在 with self.lock 之外（虽然 lock 是 RLock 可重入，但语义上这里是
        # "先把盘上的最新标定读进来，再报告"）。效果：管理端点了保存之后，
        # 下一个 1.5s 轮询就能看到 scene_annotation_reload_count +1、
        # roi_count 与 traffic_light_scope 已是新值 —— 这就是"标定不用重启"的证据。
        # 注：检测未运行时也生效，所以"先标定、再开始"同样立刻用上新值。
        if getattr(self, '_source_path', None) or getattr(self, '_source_url', None):
            try:
                self._maybe_reload_scene_annotation()
            except Exception as _e:
                logger.debug(f"[RealtimeDetector] status 前热重载检查失败: {_e}")
        with self.lock:
            fps = 0
            if self.last_process_time > 0:
                elapsed = time.time() - self.last_process_time
                if elapsed > 0:
                    fps = 1.0 / elapsed

            # GPT 升级 M06: 事件引擎状态
            event_engine_status = self._get_event_engine_status()

            return {
                'running': self.running,
                'camera_index': self.camera_index,
                # 数据源可观测性（2026-10-03 由 DSH 新增）
                # 之前 status 里没有这些字段，无法确认"当前到底在跑哪个源"，
                # 排查时只能靠猜（实测踩过：以为换了视频其实没换）。
                'source_type': getattr(self, 'source_type', None),
                'source_kind': ('file' if getattr(self, '_source_is_file', False)
                                else ('stream' if getattr(self, '_source_url', None) else 'camera')),
                'video_path': getattr(self, '_source_path', None),
                'source_url': getattr(self, '_source_url', None),
                'loop_playback': bool(getattr(self, '_source_is_file', False)),
                # ★2026-10-06 由 DSH 新增：暴露当前判色模型版本。
                # 原因（子代理审计 U1）：/status 原先不暴露模型，
                # 导致外部无法判定"实际加载的是 CNN4 还是 CNN5"——
                # 而这正是"演示时红灯判不出来"的隐蔽原因。
                'tl_color_model': self._tl_model_info(),
                'frame_rate': Config.FRAME_RATE,
                # ★2026-10-06 由 DSH 新增：**实际生效的模型序列与调优参数**。
                # 起因：核对"helmet/lane 到底在不在跑"时，用 `cmd /k` 起的后端
                # stdout 不落在日志文件里 -> 无法判定运行中实例的真实配置。
                # 配置必须可观测（同一教训见 U1/G3）。
                'model_sequence': self._active_model_sequence(),
                'yolo_imgsz': int(os.environ.get('YOLO_IMGSZ', '1280')),
                'box_prediction': str(os.environ.get('BOX_PREDICTION', '1')).lower()
                                  not in ('0', 'false', 'off'),
                # 最近一次预测后的框（仅供观测/调试；与 vehicles 的真实框不同）
                'predicted_boxes': getattr(self, '_last_predicted', []) or [],
                'prediction_stats': getattr(self, '_pred_stats', {}) or {},
                'current_fps': round(fps, 2),
                'avg_fps': round(self.fps_monitor.avg_fps, 2),
                'total_frames': self.frame_count,
                'processed_frames': self.processed_count,
                'violation_count': self.violation_count,
                'processing': self.process_lock.locked(),
                'cache_size': len(self.frame_cache),
                'tracked_vehicle_count': len(self.tracked_vehicles),
                # 红绿灯判色统计（2026-10-03 由 DSH 暴露）：
                #   total       本帧红绿灯检测框数
                #   none_dropped 被 CNN 判为"非红绿灯"而丢弃的数量（去误检）
                #   cnn / hsv   分别由 CNN / HSV 回退给出结论的数量
                #   unknown     无法判定而跳过的数量
                'traffic_light_stats': getattr(self, 'traffic_light_stats',
                                               {'total': 0, 'none_dropped': 0,
                                                'cnn': 0, 'hsv': 0, 'unknown': 0}),
                'traffic_light_confirmed': len(getattr(self, '_last_traffic_lights', []) or []),
                # ★2026-10-06 由 DSH 新增：灯态作用域可观测性
                #   roi      = 只取了人工标注 ROI 内的灯（车道级，可信）
                #   roi_miss = 标了 ROI 但本帧 ROI 内没判出灯（判色器漏检）
                #   frame    = **未标注 ROI**，取的是画面里任意一盏灯 -> 闯红灯不可信
                'traffic_light_state': getattr(self, '_light_scope_state', None),
                'traffic_light_scope': getattr(self, '_light_scope', 'frame'),
                'traffic_light_matched': getattr(self, '_light_matched', 0),
                # ★2026-10-09 由 DSH 新增：**绘制侧 ROI 过滤**的可观测性。
                #   lights_collected = 本帧**收集到的全部**判出颜色的灯（全画面，未过滤）
                #   lights_drawn     = 经 ROI 过滤后**交给渲染器**的灯（**IoU 去重前**）
                #   traffic_light_matched（上面）= ROI 过滤后的灯数（判定用的那份）
                #   traffic_lights_scope 的语义见 _scene_light_state_from_cnn
                #
                # ⚠⚠ 读这三个数时必须知道的三件事（实测 2026-10-10 全部踩过）：
                #   ① collected/drawn 是**绘制侧**才写的 —— 只有真有 MJPEG 流客户端
                #      （浏览器开着 /live 页）时 `_draw_detection_boxes` 才会跑。
                #      **没人看流时这两个值会"冻"在最后一次绘制的那一帧**
                #      （实测：无浏览器时 collected=12/drawn=6 恒定不变，而 matched
                #        在同一时刻已经变到 8）—— 那不是过滤失效，是没人请求画面。
                #   ② drawn 统计在 `_dedupe_traffic_lights` **之前**，所以
                #      drawn 可能大于"最终画出的框数"（去重后更少）。
                #   ③ matched 由**检测线程**每帧更新，与 ①② 不属于同一时刻的快照，
                #      因此 "matched == drawn" **不是**不变量（实测 8 vs 6 即此因）。
                # 可靠的不变量只有两条：
                #   · 标了 ROI 时 drawn <= collected（过滤只会变少）；
                #   · matched == 该帧 ROI 内的灯数（逐帧严格验证见
                #     `_scripts\_verify_trace_roi_filter.py`，2026-10-10 实测 73/73 帧）。
                'traffic_lights_collected': getattr(self, '_lights_filtered_for_draw', 0),
                'traffic_lights_drawn': getattr(self, '_lights_drawn', 0),
                # ★2026-10-09 由 DSH 新增：**场景标注热重载**状态（设计单 §12.5 根因 B）。
                # 用户当前的核心痛点："运行中保存的标定要等停止→开始才生效"。
                # 这里暴露"上次热重载时间 / 累计次数 / 当前生效的 ROI 数"，
                # 保存后刷新 /status 就能证明**不用重启**（三级证据）。
                'scene_annotation_reloaded_at': getattr(self, '_scene_reload_last', None),
                'scene_annotation_reload_count': int(getattr(self, '_scene_reload_count', 0) or 0),
                'scene_annotation_roi_count': len(
                    (getattr(self, '_scene_annotation', None) or {}).get('traffic_light_roi') or []),
                # ★2026-10-09 由 DSH 新增：**检测类白名单**过滤统计（设计单 §12.6 问题 2）。
                # 先看 dropped 与 last_dropped_classes，再决定要不要扩白名单 ——
                # 否则"盆栽不画了"会以"某条规则悄悄失效"为代价。
                'class_filter_stats': getattr(self, '_class_filter_stats', {}),
                # ★2026-10-09 由 DSH 新增：**绘制侧"每辆车几个框"的关联统计**。
                # 起因：用户的"每辆车两个框"是**不报错、不写日志**的回归，只能靠肉眼看出来。
                # 现在把渲染器每帧的关联结果暴露出来（见 annotation_renderer._BOX_STATS）：
                #   main_boxes          主循环（遍历 detections）画了几个框
                #   fallback_boxes      兜底循环（遍历 tracked_vehicles）补画了几个
                #   unmatched_dets      关联不到 track 的 detection 数（>0 就要留意）
                #   max_dets_per_track  **单个 track 被几条 detection 占用**（>1 = 会画重框）
                #   tracks_drawn        本帧登记进 drawn_tracks 的 track 数
                # ⚠ 与 traffic_lights_* 同理：**只有真有 MJPEG 客户端时才会更新**
                #   （绘制侧不跑就不刷新），`last_update` 可用于确认新鲜度。
                'box_draw_stats': self._box_draw_stats(),
                # ★2026-10-11 由 DSH 新增：**WebSocket 推送侧的可观测性**。
                # 起因：前端告警改用"收到推送即刷新"后，实测"一次推送都没到"，
                # 而 violation_count 明明在涨。这三个字段能立刻分清是哪种原因：
                #   ws_clients      —— 后端登记了几个 WebSocket 客户端（0 = 前端没连上/被移除）
                #   push_loop_alive —— 推送用的后台事件循环是否在跑（不在跑则推送被静默丢弃）
                #   push_scheduled / push_failed —— 累计调度次数 / 发送失败次数
                # 教训同 T75：任何"兜底/异步"路径都必须有可观测计数，否则等于埋雷。
                'ws_push': {
                    'ws_clients': len(getattr(self, 'web_socket_clients', []) or []),
                    'digital_twin_clients': len(getattr(self, 'digital_twin_clients', []) or []),
                    'push_loop_alive': bool(getattr(self, 'event_loop', None)
                                            and self.event_loop.is_running()),
                    'loop_thread_alive': bool(getattr(self, 'loop_thread', None)
                                              and self.loop_thread.is_alive()),
                    'push_scheduled': int(getattr(self, '_ws_push_scheduled', 0)),
                    'push_failed': int(getattr(self, '_ws_push_failed', 0)),
                },
                # ★2026-10-11 由 DSH 新增：**事件引擎耗时**（排查"告警栏比画面标注慢"）
                #   画面标注在事件引擎之前就画好了；若事件引擎耗时长，它后面的
                #   推送/落库/通知都会被拖后，用户就会觉得"画面已经报了、告警栏还没动"。
                'event_engine_ms': getattr(self, '_event_engine_last_ms', None),
                'event_engine_max_ms': getattr(self, '_event_engine_max_ms', None),
                'pending_count': self.multi_validator.pending_count,
                'confirmed_count': self.multi_validator.confirmed_count,
                # GPT 升级 M06: 事件引擎 + 循环缓存状态
                'frame_buffer_size': self.frame_buffer.size if self.frame_buffer else 0,
                'frame_buffer_duration': round(self.frame_buffer.duration, 2) if self.frame_buffer else 0.0,
                'active_events': len(self.active_events),
                'event_engine': event_engine_status,
            }

    def _get_event_engine_status(self) -> Dict[str, Any]:
        """获取事件引擎状态摘要（graceful degradation）"""
        if self.event_engine is None:
            return {
                'available': False,
                'total_events': 0,
                'pending_ai': 0,
                'confirmed': 0,
                'rejected': 0,
                'manual_review': 0,
            }
        try:
            all_events = self.event_engine.get_all_events()
            status_counts = {'pending_ai': 0, 'confirmed': 0, 'rejected': 0,
                             'manual_review': 0, 'triggered': 0, 'recording': 0,
                             'ai_reviewed': 0}
            for ev in all_events:
                state_val = ev.state.value if hasattr(ev.state, 'value') else str(ev.state)
                if state_val in status_counts:
                    status_counts[state_val] += 1
            return {
                'available': True,
                'total_events': len(all_events),
                'pending_ai': status_counts['pending_ai'],
                'confirmed': status_counts['confirmed'],
                'rejected': status_counts['rejected'],
                'manual_review': status_counts['manual_review'],
                'triggered': status_counts['triggered'],
                'recording': status_counts['recording'],
                'ai_reviewed': status_counts['ai_reviewed'],
                # ★2026-11-07 由 WorkBuddy 新增：落库成功/失败计数。
                #   事件驱动落库一旦失败，内存里有、库里没有 —— 这个计数
                #   让「静默失效」变成可观测项（不再只能翻日志）。
                'persist_success': int(getattr(self.event_engine, '_persist_success', 0) or 0),
                'persist_failures': int(getattr(self.event_engine, '_persist_failures', 0) or 0),
                'last_persist_error': str(getattr(self.event_engine, '_last_persist_error', '') or ''),
            }
        except Exception as e:
            logger.warning(f"[RealtimeDetector] 获取事件引擎状态失败: {e}")
            return {
                'available': True,
                'total_events': 0,
                'pending_ai': 0,
                'confirmed': 0,
                'rejected': 0,
                'manual_review': 0,
                'error': str(e),
            }

    def get_tracked_vehicles(self):
        with self.lock:
            return list(self.tracked_vehicles.values())

    def get_behavior_statistics(self):
        behaviors = []
        if self.last_detection_result:
            behaviors = self.last_detection_result.get('behaviors', [])
        
        behavior_counts = {}
        for b in behaviors:
            btype = b.get('behavior_type')
            if b.get('is_violation'):
                behavior_counts[btype] = behavior_counts.get(btype, 0) + 1
        
        return {
            'total_behaviors': len(behaviors),
            'violation_behaviors': len([b for b in behaviors if b.get('is_violation')]),
            'behavior_counts': behavior_counts,
            'tracked_vehicles': len(self.tracked_vehicles)
        }

    def get_snapshot(self):
        with self.lock:
            if self.current_frame is not None:
                return self._frame_to_base64(self.current_frame)
            return None

    def detect_external_frame(self, frame_base64):
        """接收前端 getUserMedia 采集的帧做检测（前端直接访问摄像头，后端只做检测）"""
        try:
            img_data = base64.b64decode(frame_base64)
            nparr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return {"success": False, "message": "帧解码失败"}

            with self.lock:
                self.current_frame = frame.copy()
                self.frame_count += 1
                self.frame_cache.append(frame.copy())

            # GPT 升级 M06: 外部帧也写入循环缓存
            self._buffer_frame(frame)

            result = self.process_frame(frame)

            with self.lock:
                self.processed_count += 1
                self.last_detection_result = result
                if result.get('violation_detected'):
                    self.violation_count += 1
                    self._push_violation_event(result)

            annotated_frame = self._draw_detection_boxes(frame.copy(), result.get('detections', []), self.tracked_vehicles)
            
            return {
                "success": True,
                "detections": result.get('detections', []),
                "violations": result.get('violations', []),
                "violation_detected": result.get('violation_detected', False),
                "confidence": result.get('confidence', 0.0),
                "frame_count": self.frame_count,
                "processed_count": self.processed_count,
                "violation_count": self.violation_count,
                "annotated_frame": self._frame_to_base64(annotated_frame),
                "tracked_vehicles": result.get('tracked_vehicles', []),
                "behaviors": result.get('behaviors', []),
                "tracked_vehicle_count": len(self.tracked_vehicles),
                # M10: 顶部统计条所需字段
                "avg_fps": round(self.fps_monitor.avg_fps, 2),
                "pending_count": self.multi_validator.pending_count,
                "confirmed_count": self.multi_validator.confirmed_count
            }
        except Exception as e:
            logger.error(f"[RealtimeDetector] 外部帧检测失败: {e}")
            return {"success": False, "message": str(e)}

    def register_websocket_client(self, client):
        with self.lock:
            if client not in self.web_socket_clients:
                self.web_socket_clients.append(client)

    def unregister_websocket_client(self, client):
        with self.lock:
            if client in self.web_socket_clients:
                self.web_socket_clients.remove(client)

    def register_digital_twin_client(self, client):
        with self.lock:
            if client not in self.digital_twin_clients:
                self.digital_twin_clients.append(client)

    def unregister_digital_twin_client(self, client):
        with self.lock:
            if client in self.digital_twin_clients:
                self.digital_twin_clients.remove(client)


COLOR_MAP = {
    'motorcycle': (255, 0, 0),
    'car': (255, 0, 0),
    'truck': (255, 0, 0),
    'bus': (255, 0, 0),
    'bicycle': (255, 0, 0),
    'person': (0, 255, 0),
    'helmet': (0, 255, 0),
    'no_helmet': (0, 0, 255),
    'red_light': (0, 0, 255),
    'yellow_light': (0, 255, 255),
    'green_light': (0, 255, 0),
    'lane_line': (0, 255, 255),
}

realtime_detector = RealtimeViolationDetector()
