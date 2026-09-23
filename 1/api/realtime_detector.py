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
import numpy as np
import asyncio
import logging
from datetime import datetime
from collections import deque
from typing import Optional, Dict, List, Any

from image_recognizer import multi_model_detect, init_all_models, CLASS_CN_MAP
from violation_rules import check_violations, ViolationRuleEngine, VIOLATION_TYPE_CN
from cloud_collaborator import CloudCollaborator
from config import Config
from behavior_engine import BehaviorEngine, BEHAVIOR_TYPE_CN
from vehicle_tracker import VehicleTracker
from multi_frame_validator import MultiFrameValidator, FPSMonitor
# GPT 升级 M06: 循环缓存 + 事件引擎 + 证据链
from circular_frame_buffer import CircularFrameBuffer
from traffic_event_engine import TrafficEventEngine, TrafficEvent, EventState

logger = logging.getLogger("zhitong_api")

class RealtimeViolationDetector:
    def __init__(self):
        self.cap = None
        self.running = False
        self.processing = False
        self.cloud_collaborator = CloudCollaborator()
        self.violation_engine = ViolationRuleEngine()
        self.behavior_engine = BehaviorEngine()
        self.vehicle_tracker = VehicleTracker(use_bytetrack=False)
        self.current_frame = None
        self.last_process_time = 0
        self.frame_count = 0
        self.processed_count = 0
        self.violation_count = 0
        self.camera_index = 0
        # M17: 数据源类型（camera / video / carla）与 CARLA 实例
        self.source_type = "camera"
        self.carla_source = None
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
        self.multi_validator = MultiFrameValidator(window_size=10, confirm_threshold=5)
        self.fps_monitor = FPSMonitor(window_size=30)
        # GPT 升级 M06: 循环缓存 + 事件引擎（叠加层，不影响现有逻辑）
        self.frame_buffer = self._init_frame_buffer()
        self.event_engine = self._init_event_engine(self.frame_buffer)
        self.active_events = {}  # event_id → TrafficEvent
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
                cooldown_sec=60,
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

    def start_camera(self, camera_index=0, video_path=None):
        with self.lock:
            self.camera_index = camera_index
            if video_path and os.path.exists(video_path):
                self.cap = cv2.VideoCapture(video_path)
                logger.info(f"[RealtimeDetector] 使用视频文件: {video_path}")
            else:
                # Windows 下优先使用 DirectShow 后端（CAP_DSHOW），大幅提高摄像头打开成功率
                # 某些笔记本自带摄像头用默认 MSMF 后端会打不开或报"can't grab frame"
                is_windows = os.name == 'nt'
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
                    from carla_source import CarlaSource
                    if self.carla_source is None:
                        self.carla_source = CarlaSource()
                    if not self.carla_source.is_connected():
                        ok = self.carla_source.connect(host="127.0.0.1", port=2000)
                        if not ok:
                            logger.warning("[RealtimeDetector] CARLA 连接失败，请确认 CarlaUE4.exe 已启动")
                            return False
                    # CARLA 模式下挂载摄像头传感器
                    self.carla_source.attach_camera(width=640, height=480, fov=90)
                    self.source_type = "carla"
                    logger.info("[RealtimeDetector] 数据源已切换为 CARLA")
                    return True
                except Exception as e:
                    logger.error(f"[RealtimeDetector] 切换 CARLA 数据源失败: {e}")
                    return False
            else:
                # camera / video 走原逻辑
                self.source_type = source_type
                self.start_camera(camera_index=camera_index, video_path=video_path)
                return True

    def start_detection(self):
        with self.lock:
            if self.running:
                return {"success": False, "message": "检测已在运行中"}
            self.running = True
            self.frame_count = 0
            self.processed_count = 0
            self.violation_count = 0
            self.last_process_time = time.time()
            self.frame_cache.clear()
            # GPT 升级 M06: 重启时清空循环缓存和活跃事件
            if self.frame_buffer is not None:
                try:
                    self.frame_buffer.clear()
                except Exception:
                    pass
            self.active_events.clear()

        thread = threading.Thread(target=self._detection_loop, daemon=True)
        thread.start()
        logger.info("[RealtimeDetector] 检测循环已启动")
        return {"success": True, "message": "检测已启动"}

    def _detection_loop(self):
        frame_interval = 1.0 / Config.FRAME_RATE
        last_frame_time = time.time()

        while self.running:
            try:
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
                    if not ret:
                        time.sleep(0.05)
                        continue
                    with self.lock:
                        self.frame_count += 1
                        self.current_frame = frame.copy()
                        self.frame_cache.append(frame.copy())
                    # GPT 升级 M06: 写入循环缓存（携带最近检测结果）
                    self._buffer_frame(frame)

                current_time = time.time()
                elapsed = current_time - last_frame_time

                if elapsed >= frame_interval:
                    last_frame_time = current_time
                    self._process_frame_async(frame)

            except Exception as e:
                logger.error(f"[RealtimeDetector] 检测循环异常: {e}")
                time.sleep(0.1)

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
                        self._push_violation_event(result)
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
            result['detections'] = detections
            
            frame_height, frame_width = frame.shape[:2]
            
            try:
                self.tracked_vehicles = self.vehicle_tracker.update(detections, frame_width, frame_height)
                result['tracked_vehicles'] = list(self.tracked_vehicles.values())
            except Exception as e:
                logger.warning(f"[RealtimeDetector] 车辆追踪失败: {e}")
            
            traffic_light_state = self._detect_traffic_light_state(detections)
            lane_lines = self._extract_lane_lines(detections)
            
            self.scene_config = {
                'traffic_light_state': traffic_light_state,
                'stop_line_y': int(frame_height * 0.55),
                'road_direction': 'south',
                'speed_limit': 60,
                'pixel_per_meter': 10,
                'no_parking_zones': [{'x1': 0, 'y1': int(frame_height * 0.6), 'x2': frame_width, 'y2': frame_height}],
                'lane_lines': lane_lines
            }
            
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
                        violations.append({
                            'violation_type': behavior['behavior_type'],
                            'violation_type_cn': behavior['behavior_type_cn'],
                            'confidence': behavior['confidence'],
                            'is_violation': True,
                            'evidence': behavior['evidence'],
                            'location': {'x': 0, 'y': 0},
                            'timestamp': behavior['timestamp'],
                            'source': 'behavior_engine'
                        })
                
                if violations:
                    result['violation_detected'] = True
                    result['violations'] = violations
                    highest_conf = max(v.get('confidence', 0.0) for v in violations)
                    result['confidence'] = highest_conf
                    
                    frame_base64 = self._frame_to_base64(frame)
                    annotated_frame = self._draw_detection_boxes(frame.copy(), detections, self.tracked_vehicles)
                    annotated_base64 = self._frame_to_base64(annotated_frame)
                    
                    consult_type = self.cloud_collaborator.should_consult_cloud({
                        'violation_type': violations[0].get('violation_type'),
                        'confidence': highest_conf,
                        'detections': detections,
                        'success': True
                    })
                    
                    if consult_type:
                        context_frames = self.get_context_frames()
                        cloud_result = self.cloud_collaborator.consult_cloud_dual(
                            frame_base64,
                            annotated_base64,
                            {'violation_type': violations[0].get('violation_type'), 'confidence': highest_conf},
                            consult_type,
                            context_frames
                        )
                        
                        if cloud_result.get('success'):
                            process_result = self.cloud_collaborator.process_cloud_response(
                                violations[0], cloud_result
                            )
                            ai_trace = self.cloud_collaborator.build_ai_trace_v31(
                                {'violation_type': violations[0].get('violation_type'), 'confidence': highest_conf, 'detections': detections},
                                cloud_result.get('doubao_result', {}),
                                cloud_result.get('deepseek_result', {}),
                                process_result
                            )
                            result['ai_trace'] = ai_trace
                            result['cloud_consulation'] = True
                            result['cloud_result'] = cloud_result
                            
                    self._save_violation_evidence(frame, violations)

            # GPT 升级 M06: 调用交通事件引擎（叠加层，不影响现有违规流程）
            self._process_event_engine(frame, detections, result)

        except Exception as e:
            logger.error(f"[RealtimeDetector] 帧处理失败: {e}")

        return result

    def _buffer_frame(self, frame):
        """将当前帧写入循环缓存（携带最近检测结果，graceful degradation）"""
        if self.frame_buffer is None or frame is None:
            return
        try:
            with self.lock:
                last_result = self.last_detection_result or {}
            self.frame_buffer.add(
                time.time(),
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
        """调用交通事件引擎处理当前帧（graceful degradation）

        - 触发新事件后异步提取视频+提交云端 AI（不阻塞检测循环）
        - 仅在 event_engine 可用时执行
        """
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

                # 异步处理：提取事件视频 + 提交云端 AI 分析
                thread = threading.Thread(
                    target=self._handle_event_lifecycle,
                    args=(event,),
                    daemon=True,
                )
                thread.start()
        except Exception as e:
            logger.warning(f"[RealtimeDetector] 事件引擎处理异常: {e}")

    def _handle_event_lifecycle(self, event: TrafficEvent):
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

            # 2) 提取事件视频片段并保存
            video_path = ""
            if self.frame_buffer is not None:
                try:
                    clip = self.frame_buffer.extract_event_clip(
                        event.trigger_time,
                        before_sec=Config.EVENT_CLIP_BEFORE_SEC,
                        after_sec=Config.EVENT_CLIP_AFTER_SEC,
                    )
                    video_path = self.frame_buffer.generate_event_video_path(event.event_id)
                    saved = self.frame_buffer.save_event_video(clip, video_path, fps=Config.FRAME_BUFFER_FPS)
                    if saved:
                        event.event_video_path = saved
                        # 选取关键帧（用首/中/尾三帧）
                        event.key_frames = self._pick_key_frame_paths(clip)
                        logger.info(f"[RealtimeDetector] 事件 {event.event_id} 视频已保存: {saved}")
                    else:
                        logger.warning(f"[RealtimeDetector] 事件 {event.event_id} 视频保存失败")
                except Exception as e:
                    logger.warning(f"[RealtimeDetector] 事件 {event.event_id} 视频提取失败: {e}")

            # 3) 提交云端 AI 分析（RECORDING → PENDING_AI → AI_REVIEWED）
            try:
                self.event_engine.submit_to_ai(event.event_id)
            except Exception as e:
                logger.warning(f"[RealtimeDetector] 事件 {event.event_id} 提交 AI 失败: {e}")
                return

            # 4) 实际调用云端 AI（按事件分析，GPT §8）
            try:
                event_clip_frames = []
                if self.frame_buffer is not None:
                    event_clip_frames = self.frame_buffer.extract_event_clip(
                        event.trigger_time,
                        before_sec=Config.EVENT_CLIP_BEFORE_SEC,
                        after_sec=Config.EVENT_CLIP_AFTER_SEC,
                    )
                key_frames_nd = [f for _, f in event_clip_frames[:5]] or []

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

                with self.lock:
                    self.active_events[event.event_id] = self.event_engine.get_event(event.event_id) or event

                logger.info(f"[RealtimeDetector] 事件 {event.event_id} AI 复核完成 state={self.event_engine.get_event(event.event_id).state.value if self.event_engine.get_event(event.event_id) else 'unknown'}")
            except Exception as e:
                logger.warning(f"[RealtimeDetector] 事件 {event.event_id} 云端 AI 分析失败: {e}")
        except Exception as e:
            logger.error(f"[RealtimeDetector] 事件 {event.event_id} 生命周期处理异常: {e}")

    @staticmethod
    def _pick_key_frame_paths(clip) -> List[str]:
        """从事件片段中选取首/中/尾三帧作为关键帧（暂存到内存，路径用占位符）

        实际生产场景应保存为 jpg 文件并返回路径。此处先用占位符，M07 路由层会落盘。
        """
        if not clip:
            return []
        if len(clip) <= 3:
            indices = list(range(len(clip)))
        else:
            mid = len(clip) // 2
            indices = [0, mid, len(clip) - 1]
        # 返回帧索引字符串作为占位（后续可保存为 jpg）
        return [f"frame_{idx}" for idx in indices]

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

    def _frame_to_base64(self, frame):
        _, img_encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return base64.b64encode(img_encoded).decode('utf-8')

    def _draw_detection_boxes(self, frame, detections, tracked_vehicles=None):
        tracked_vehicles = tracked_vehicles or {}
        
        vehicle_bbox_to_track = {}
        for vid, vehicle in tracked_vehicles.items():
            bbox = vehicle.get('bbox', [0, 0, 0, 0])
            if len(bbox) >= 4:
                vehicle_bbox_to_track[(int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))] = vehicle
        
        for det in detections:
            bbox = det.get('bbox', [0, 0, 0, 0])
            class_name = det.get('class_name', '')
            class_name_cn = CLASS_CN_MAP.get(class_name, class_name)
            confidence = det.get('confidence', 0.0)
            
            x1, y1, x2, y2 = [int(v) for v in bbox]
            color = COLOR_MAP.get(class_name, (0, 255, 0))
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            bbox_key = (x1, y1, x2, y2)
            track_info = vehicle_bbox_to_track.get(bbox_key)
            
            labels = []
            if track_info:
                track_id = track_info.get('id', '')
                labels.append(f"ID:{track_id}")
                
                direction = track_info.get('direction', '')
                if direction and direction != 'unknown':
                    labels.append(direction)
                
                speed = track_info.get('speed', 0)
                if speed > 0:
                    labels.append(f"{speed:.1f}px/s")
            
            labels.append(f"{class_name_cn} {confidence:.2f}")
            
            full_label = " ".join(labels)
            label_size = cv2.getTextSize(full_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 5), (x1 + label_size[0], y1), color, -1)
            cv2.putText(frame, full_label, (x1, y1 - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            if track_info and track_info.get('is_wrong_way', False):
                wrong_label = "逆行"
                wrong_size = cv2.getTextSize(wrong_label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(frame, (x1, y2 + 5), (x1 + wrong_size[0], y2 + wrong_size[1] + 5), (0, 0, 255), -1)
                cv2.putText(frame, wrong_label, (x1, y2 + wrong_size[1] + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame

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
                    h, w = frame.shape[:2]
                    for idx, vio in enumerate(all_violations[:3]):
                        y_offset = 25 + idx * 22
                        vehicle_info = f"(车{vio.get('vehicle_id')})" if vio.get('vehicle_id') else ""
                        text = f"⚠ {vio.get('violation_type_cn')}{vehicle_info} {vio.get('confidence', 0):.2f}"
                        cv2.putText(frame, text, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
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
        try:
            uploads_dir = Config.UPLOAD_DIR
            os.makedirs(uploads_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            violation_types = '_'.join(v.get('violation_type', '') for v in violations)
            filename = f"realtime_{violation_types}_{timestamp}.jpg"
            filepath = os.path.join(uploads_dir, filename)
            
            with self.lock:
                detections = self.last_detection_result.get('detections', []) if self.last_detection_result else []
            
            annotated = self._draw_detection_boxes(frame.copy(), detections)
            cv2.imwrite(filepath, annotated)
            logger.info(f"[RealtimeDetector] 证据已保存: {filepath}")
        except Exception as e:
            logger.error(f"[RealtimeDetector] 保存证据失败: {e}")

    def _push_violation_event(self, result):
        event_data = {
            'event': 'violation_detected',
            'timestamp': result['timestamp'],
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
                except Exception:
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
        with self.lock:
            self.running = False
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            self.current_frame = None
            self.last_detection_result = None
            self.frame_cache.clear()
            # GPT 升级 M06: 清理循环缓存和活跃事件
            if self.frame_buffer is not None:
                try:
                    self.frame_buffer.clear()
                except Exception:
                    pass
            self.active_events.clear()

        if self.event_loop.is_running():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)

        logger.info("[RealtimeDetector] 检测已停止")
        return {"success": True, "message": "检测已停止"}

    def get_status(self):
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
                'frame_rate': Config.FRAME_RATE,
                'current_fps': round(fps, 2),
                'avg_fps': round(self.fps_monitor.avg_fps, 2),
                'total_frames': self.frame_count,
                'processed_frames': self.processed_count,
                'violation_count': self.violation_count,
                'processing': self.process_lock.locked(),
                'cache_size': len(self.frame_cache),
                'tracked_vehicle_count': len(self.tracked_vehicles),
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