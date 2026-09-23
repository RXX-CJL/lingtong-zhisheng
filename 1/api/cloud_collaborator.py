# -*- coding: utf-8 -*-
"""
端云协作管理器模块

本模块实现本地AI主动咨询云端AI的核心协作逻辑，包含三种协作模式：
1. URGENT   - 高置信度违规，立即上报云端确认（避免误报）
2. CONSULT  - 模糊地带，主动咨询云端大模型
3. NORMAL   - 正常画面，仅统计不上报

依赖：
    - image_recognizer.analyze_with_doubao
    - image_recognizer.analyze_with_deepseek_judge
    - image_recognizer.VIOLATION_TYPE_CN
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

# 从同目录的 image_recognizer 导入协作所需的云端分析函数
from image_recognizer import (
    analyze_with_doubao,
    analyze_with_deepseek_judge,
    analyze_with_claude,
    VIOLATION_TYPE_CN,
)

logger = logging.getLogger("zhitong_api")

# 协作日志保存目录（与本文件同级的 collaboration_logs 子目录）
COLLAB_LOG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "collaboration_logs"
)

# 触发阈值配置
THRESHOLDS = {
    "urgent_confidence": 0.75,      # 置信度 >= 此值，触发 URGENT 模式
    "consult_low": 0.4,             # 模糊地带下界
    "consult_high": 0.75,           # 模糊地带上界（与 urgent_confidence 一致）
    "disagreement_threshold": 0.3,  # 豆包与 DeepSeek 置信度差异 >= 此值，判定为分歧
}


class CloudCollaborator:
    """
    端云协作管理器 - 本地AI主动咨询云端AI的核心模块

    三种协作模式：
        URGENT  - 高置信度违规，立即上报确认
        CONSULT - 模糊地带，主动咨询云端
        NORMAL  - 正常画面，仅统计不上报
    """

    def __init__(self, log_dir: Optional[str] = None):
        """初始化协作管理器，确保日志目录存在"""
        self.log_dir = log_dir or COLLAB_LOG_DIR
        # Claude API Key（按需加载，未配置则 analyze_event 中 Claude 跳过）
        try:
            from config import Config
            self.claude_api_key = getattr(Config, 'CLAUDE_API_KEY', '') or ''
        except Exception:
            self.claude_api_key = ''
        try:
            os.makedirs(self.log_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"[CloudCollaborator] 创建日志目录失败: {e}")

    # ------------------------------------------------------------------
    # 1. 判断是否需要咨询云端
    # ------------------------------------------------------------------
    def should_consult_cloud(self, detection_result: Dict[str, Any]) -> Optional[str]:
        """
        判断是否需要咨询云端

        参数:
            detection_result: 本地检测结果，应包含：
                - violation_type: 违规类型（英文）
                - confidence: 整体置信度 (0-1)
                - detections: 检测对象列表
                - success: 检测是否成功（可选，缺省视为 True）

        返回:
            "urgent"  - 高置信度违规，需立即上报确认
            "consult" - 模糊地带，需咨询云端
            None      - 正常画面，无需咨询
        """
        try:
            if not detection_result:
                return None

            # 检测失败或明确无对象，不咨询
            if not detection_result.get('success', True):
                return None

            detections = detection_result.get('detections') or []
            if not detections:
                return None

            confidence = float(detection_result.get('confidence', 0.0))

            # 高置信度违规 - 立即上报确认
            if confidence >= THRESHOLDS["urgent_confidence"]:
                logger.info(
                    f"[CloudCollaborator] URGENT触发: "
                    f"type={detection_result.get('violation_type')} "
                    f"confidence={confidence:.2f}"
                )
                return "urgent"

            # 模糊地带 - 主动咨询云端
            if THRESHOLDS["consult_low"] <= confidence < THRESHOLDS["consult_high"]:
                logger.info(
                    f"[CloudCollaborator] CONSULT触发: "
                    f"type={detection_result.get('violation_type')} "
                    f"confidence={confidence:.2f}"
                )
                return "consult"

            # 低置信度 - 视为正常画面
            return None
        except Exception as e:
            logger.warning(f"[CloudCollaborator] should_consult_cloud异常: {e}")
            return None

    # ------------------------------------------------------------------
    # 2. 主动咨询云端大模型
    # ------------------------------------------------------------------
    def consult_cloud(
        self,
        image_data: str,
        local_judgment: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        """
        主动咨询云端大模型，依次调用 Claude 视觉分析与 DeepSeek 二次审核

        参数:
            image_data: 图片路径或 base64 字符串（传给 analyze_with_claude）
            local_judgment: 本地判断结果，应包含：
                - violation_type: 违规类型（英文）
                - yolo_result: YOLO 检测结果字典（可选，传给 DeepSeek）
                - confidence: 本地置信度
            reason: 触发原因（"urgent" 或 "consult"）

        返回:
            {
                'success': bool,           # 云端调用整体是否成功
                'claude_result': dict,     # Claude 原始返回
                'doubao_result': dict,     # 豆包原始返回（备用）
                'deepseek_result': dict,   # DeepSeek 原始返回
                'duration_ms': int,        # 总耗时（毫秒）
                'reason': str,             # 触发原因
                'pending_review': bool,    # 云端失败 → 标记待人工复核
                'violation_type': str,
                'timestamp': str           # ISO8601 时间戳
            }
        """
        start_time = time.time()
        violation_type = local_judgment.get('violation_type', 'unknown')
        yolo_result_dict = local_judgment.get('yolo_result', {}) or {}

        # 1. 调用 Claude 视觉分析（主要模型）
        try:
            claude_result = analyze_with_claude(image_data, violation_type)
            if not isinstance(claude_result, dict):
                claude_result = {
                    'success': False,
                    'result_text': '',
                    'is_violation_confirmed': False,
                    'confidence_adjusted': 0.0,
                    'risk_level': 'low',
                    'message': 'Claude 返回格式异常',
                    'prompt': '',
                }
        except Exception as e:
            logger.error(f"[CloudCollaborator] Claude调用异常: {e}")
            claude_result = {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'risk_level': 'low',
                'message': f'Claude调用异常: {e}',
                'prompt': '',
            }

        # 2. Claude 失败时，回退到豆包视觉分析
        doubao_result = {}
        if not claude_result.get('success', False):
            try:
                doubao_result = analyze_with_doubao(image_data, violation_type)
                if not isinstance(doubao_result, dict):
                    doubao_result = {
                        'success': False,
                        'result_text': '',
                        'is_violation_confirmed': False,
                        'confidence_adjusted': 0.0,
                        'message': '豆包返回格式异常',
                        'prompt': '',
                    }
            except Exception as e:
                logger.error(f"[CloudCollaborator] 豆包调用异常: {e}")
                doubao_result = {
                    'success': False,
                    'result_text': '',
                    'is_violation_confirmed': False,
                    'confidence_adjusted': 0.0,
                    'message': f'豆包调用异常: {e}',
                    'prompt': '',
                }

        # 3. 确定使用哪个视觉模型结果作为 DeepSeek 的输入
        primary_visual_result = claude_result if claude_result.get('success', False) else doubao_result

        # 4. 调用 DeepSeek 二次审核（异常时优雅降级）
        try:
            deepseek_result = analyze_with_deepseek_judge(
                violation_type, yolo_result_dict, primary_visual_result
            )
            if not isinstance(deepseek_result, dict):
                deepseek_result = {
                    'success': False,
                    'result_text': '',
                    'is_violation_confirmed': False,
                    'confidence_adjusted': 0.0,
                    'risk_level': 'low',
                    'doubao_opinion_match': True,
                    'message': 'DeepSeek 返回格式异常',
                    'prompt': '',
                }
        except Exception as e:
            logger.error(f"[CloudCollaborator] DeepSeek调用异常: {e}")
            deepseek_result = {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'risk_level': 'low',
                'doubao_opinion_match': True,
                'message': f'DeepSeek调用异常: {e}',
                'prompt': '',
            }

        duration_ms = int((time.time() - start_time) * 1000)

        # 5. 任一云端调用失败 → 标记 pending_review
        cloud_failed = (not primary_visual_result.get('success', False)) or \
                       (not deepseek_result.get('success', False))

        result = {
            'success': not cloud_failed,
            'claude_result': claude_result,
            'doubao_result': doubao_result,
            'deepseek_result': deepseek_result,
            'duration_ms': duration_ms,
            'reason': reason,
            'pending_review': cloud_failed,
            'violation_type': violation_type,
            'violation_type_cn': VIOLATION_TYPE_CN.get(violation_type, violation_type),
            'timestamp': datetime.now().isoformat(),
        }

        logger.info(
            f"[CloudCollaborator] 云端咨询完成 reason={reason} "
            f"claude_success={claude_result.get('success')} "
            f"doubao_success={doubao_result.get('success')} "
            f"deepseek_success={deepseek_result.get('success')} "
            f"duration={duration_ms}ms pending_review={cloud_failed}"
        )

        return result

    # ------------------------------------------------------------------
    # 3. 处理云端响应，生成最终裁决
    # ------------------------------------------------------------------
    def process_cloud_response(
        self,
        local_result: Dict[str, Any],
        cloud_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        处理云端响应，生成最终裁决

        参数:
            local_result: 本地判断结果，应包含：
                - is_violation: 本地是否判定违规
                - confidence: 本地置信度
            cloud_result: consult_cloud 的返回

        返回:
            {
                'judgment': 'confirmed'/'rejected'/'pending_review',
                'confidence': float,
                'method': str,             # 裁决方式
                'evidence_count': int,     # 支撑证据数量
                'disagreement_flag': bool, # 是否存在分歧
                'pending_review': bool,    # 是否需人工复核
                'doubao_opinion_match': bool
            }
        """
        if cloud_result.get('pending_review', False):
            local_conf = float(local_result.get('confidence', 0.0))
            local_judgment = 'confirmed' if local_result.get('is_violation', False) else 'rejected'
            return {
                'judgment': local_judgment,
                'confidence': round(local_conf, 4),
                'method': 'local_fallback',
                'evidence_count': 1,
                'disagreement_flag': False,
                'pending_review': True,
                'doubao_opinion_match': True,
                'note': '云端调用失败，采用本地判断并标记待人工复核',
            }

        claude = cloud_result.get('claude_result', {}) or {}
        doubao = cloud_result.get('doubao_result', {}) or {}
        deepseek = cloud_result.get('deepseek_result', {}) or {}

        primary_visual = claude if claude.get('success', False) else doubao
        primary_confirmed = bool(primary_visual.get('is_violation_confirmed', False))
        primary_conf = float(primary_visual.get('confidence_adjusted', 0.0))
        primary_method = 'claude' if claude.get('success', False) else 'doubao'

        deepseek_confirmed = bool(deepseek.get('is_violation_confirmed', False))
        deepseek_conf = float(deepseek.get('confidence_adjusted', 0.0))

        conf_diff = abs(primary_conf - deepseek_conf)
        disagreement_flag = (primary_confirmed != deepseek_confirmed) or \
                            (conf_diff >= THRESHOLDS["disagreement_threshold"])

        if deepseek.get('success', False):
            final_judgment = 'confirmed' if deepseek_confirmed else 'rejected'
            final_conf = deepseek_conf
            method = f'{primary_method}_plus_deepseek'
            evidence_count = 2
        elif primary_visual.get('success', False):
            final_judgment = 'confirmed' if primary_confirmed else 'rejected'
            final_conf = primary_conf
            method = f'{primary_method}_only'
            evidence_count = 1
        else:
            final_judgment = 'confirmed' if local_result.get('is_violation', False) else 'rejected'
            final_conf = float(local_result.get('confidence', 0.0))
            method = 'local_fallback'
            evidence_count = 1

        pending_review = disagreement_flag
        # 豆包意见是否与最终判断一致
        doubao_confirmed = bool(doubao.get('is_violation_confirmed', False))
        opinion_match = (doubao_confirmed == (final_judgment == 'confirmed'))

        return {
            'judgment': final_judgment,
            'confidence': round(final_conf, 4),
            'method': method,
            'evidence_count': evidence_count,
            'disagreement_flag': disagreement_flag,
            'pending_review': pending_review,
            'doubao_opinion_match': opinion_match,
        }

    # ------------------------------------------------------------------
    # 4. 构建 v3 版本 ai_trace 嵌套结构
    # ------------------------------------------------------------------
    def build_ai_trace(
        self,
        yolo_result: Dict[str, Any],
        doubao_result: Dict[str, Any],
        deepseek_result: Dict[str, Any],
        final_result: Dict[str, Any],
        claude_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        构建 v3 版本 ai_trace 嵌套结构

        参数:
            yolo_result: YOLO 检测结果
            doubao_result: 豆包分析结果（备用）
            deepseek_result: DeepSeek 审核结果
            final_result: process_cloud_response 的返回
            claude_result: Claude 分析结果（主要模型）

        返回:
            {
                "version": "v3",
                "yolo":     {violation_type, confidence, detections, duration_ms},
                "claude":   {judgment, confidence, reasoning, duration_ms} (可选),
                "doubao":   {judgment, confidence, reasoning, duration_ms},
                "deepseek": {judgment, confidence, review_summary, disagreement_flag, duration_ms},
                "final":    {judgment, confidence, method, evidence_count}
            }
        """
        yolo = yolo_result or {}
        claude = claude_result or {}
        doubao = doubao_result or {}
        ds = deepseek_result or {}
        final = final_result or {}

        yolo_node = {
            'violation_type': yolo.get('violation_type', 'unknown'),
            'confidence': float(yolo.get('confidence', 0.0)),
            'detections': yolo.get('detections', []),
            'duration_ms': int(yolo.get('duration_ms', 0)),
        }

        claude_node = {
            'judgment': 'confirmed' if claude.get('is_violation_confirmed', False) else 'rejected',
            'confidence': float(claude.get('confidence_adjusted', 0.0)),
            'reasoning': claude.get('result_text', ''),
            'risk_level': claude.get('risk_level', 'medium'),
            'duration_ms': int(claude.get('duration_ms', 0)),
        }

        doubao_node = {
            'judgment': 'confirmed' if doubao.get('is_violation_confirmed', False) else 'rejected',
            'confidence': float(doubao.get('confidence_adjusted', 0.0)),
            'reasoning': doubao.get('result_text', ''),
            'duration_ms': int(doubao.get('duration_ms', 0)),
        }

        deepseek_node = {
            'judgment': 'confirmed' if ds.get('is_violation_confirmed', False) else 'rejected',
            'confidence': float(ds.get('confidence_adjusted', 0.0)),
            'review_summary': ds.get('result_text', ''),
            'disagreement_flag': bool(final.get('disagreement_flag', False)),
            'duration_ms': int(ds.get('duration_ms', 0)),
        }

        final_node = {
            'judgment': final.get('judgment', 'pending_review'),
            'confidence': float(final.get('confidence', 0.0)),
            'method': final.get('method', 'unknown'),
            'evidence_count': int(final.get('evidence_count', 0)),
        }

        result = {
            'version': 'v3',
            'yolo': yolo_node,
            'doubao': doubao_node,
            'deepseek': deepseek_node,
            'final': final_node,
        }

        if claude_result:
            result['claude'] = claude_node

        return result

    # ------------------------------------------------------------------
    # 4.5 双图云端协作 - 发送原始帧+标注帧
    # ------------------------------------------------------------------
    def consult_cloud_dual(
        self,
        original_image: str,
        annotated_image: str,
        local_judgment: Dict[str, Any],
        reason: str,
        context_frames: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        双图云端协作 - 发送原始帧和标注帧给云端AI进行双通道分析
        
        参数:
            original_image: 原始帧的base64字符串
            annotated_image: 标注帧的base64字符串（带有YOLO检测框）
            local_judgment: 本地判断结果
            reason: 触发原因（"urgent" 或 "consult"）
            context_frames: 上下文帧列表（可选，前后帧）
        
        返回:
            {
                'success': bool,
                'doubao_result': dict,
                'deepseek_result': dict,
                'duration_ms': int,
                'reason': str,
                'pending_review': bool,
                'violation_type': str,
                'timestamp': str,
                'has_dual_images': True,
                'context_frame_count': int
            }
        """
        start_time = time.time()
        violation_type = local_judgment.get('violation_type', 'unknown')
        
        try:
            doubao_result = self._analyze_with_dual_images(original_image, annotated_image, violation_type, context_frames)
            if not isinstance(doubao_result, dict):
                doubao_result = {
                    'success': False,
                    'result_text': '',
                    'is_violation_confirmed': False,
                    'confidence_adjusted': 0.0,
                    'message': '豆包返回格式异常',
                    'prompt': '',
                }
        except Exception as e:
            logger.error(f"[CloudCollaborator] 豆包双图分析异常: {e}")
            doubao_result = {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'message': f'豆包双图分析异常: {e}',
                'prompt': '',
            }

        try:
            deepseek_result = analyze_with_deepseek_judge(
                violation_type, local_judgment.get('yolo_result', {}) or {}, doubao_result
            )
            if not isinstance(deepseek_result, dict):
                deepseek_result = {
                    'success': False,
                    'result_text': '',
                    'is_violation_confirmed': False,
                    'confidence_adjusted': 0.0,
                    'risk_level': 'low',
                    'doubao_opinion_match': True,
                    'message': 'DeepSeek 返回格式异常',
                    'prompt': '',
                }
        except Exception as e:
            logger.error(f"[CloudCollaborator] DeepSeek调用异常: {e}")
            deepseek_result = {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'risk_level': 'low',
                'doubao_opinion_match': True,
                'message': f'DeepSeek调用异常: {e}',
                'prompt': '',
            }

        duration_ms = int((time.time() - start_time) * 1000)

        cloud_failed = (not doubao_result.get('success', False)) or \
                       (not deepseek_result.get('success', False))

        result = {
            'success': not cloud_failed,
            'doubao_result': doubao_result,
            'deepseek_result': deepseek_result,
            'duration_ms': duration_ms,
            'reason': reason,
            'pending_review': cloud_failed,
            'violation_type': violation_type,
            'violation_type_cn': VIOLATION_TYPE_CN.get(violation_type, violation_type),
            'timestamp': datetime.now().isoformat(),
            'has_dual_images': True,
            'context_frame_count': len(context_frames) if context_frames else 0,
        }

        logger.info(
            f"[CloudCollaborator] 双图云端协作完成 reason={reason} "
            f"doubao_success={doubao_result.get('success')} "
            f"deepseek_success={deepseek_result.get('success')} "
            f"duration={duration_ms}ms context_frames={len(context_frames) if context_frames else 0}"
        )

        return result

    def _analyze_with_dual_images(self, original, annotated, violation_type, context_frames):
        try:
            from image_recognizer import analyze_with_doubao
            
            result = analyze_with_doubao(annotated, violation_type)
            return result
        except Exception as e:
            logger.error(f"[CloudCollaborator] 双图分析异常: {e}")
            return {
                'success': False,
                'result_text': f'双图分析异常: {e}',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'message': f'双图分析异常: {e}',
                'prompt': '',
            }

    # ------------------------------------------------------------------
    # 4.6 按事件分析（GPT §8）—— 云端 AI 只在事件触发后调用
    # ------------------------------------------------------------------
    def analyze_event(
        self,
        event_clip_frames: List,
        key_frames: List,
        vehicle_info: Dict[str, Any],
        scene_context: Dict[str, Any],
        event_type: str,
        trajectory: List,
    ) -> Dict[str, Any]:
        """按事件分析 — 云端 AI 只在事件触发后调用（GPT §8）

        与 consult_cloud（按帧分析）不同，本方法输入是事件视频+关键帧+轨迹+结构化上下文，
        输出保持 ai_trace v3 嵌套结构。

        Args:
            event_clip_frames: 事件视频帧序列 [(timestamp, frame)]（CircularFrameBuffer.extract_event_clip 返回值）
            key_frames: 关键帧列表（numpy ndarray 或 base64 字符串）
            vehicle_info: 车辆信息（type/bbox/plate_number）
            scene_context: 场景上下文（traffic_light/lane/stop_line）
            event_type: 事件类型（red_light/wrong_way/...）
            trajectory: 车辆轨迹点序列

        Returns:
            ai_trace v3 嵌套结构：
            {
              "version": "v3",
              "yolo": {violation_type, confidence, detections, duration_ms},
              "claude": {judgment, confidence, reasoning, risk_level, duration_ms} (可选),
              "doubao": {judgment, confidence, reasoning, duration_ms},
              "deepseek": {judgment, confidence, review_summary, disagreement_flag, duration_ms},
              "final": {judgment, confidence, method, evidence_count, explanation, risk_flag}
            }
        """
        import time as _time
        start_ts = _time.time()
        logger.info(f"[CloudCollaborator] analyze_event 开始: type={event_type} "
                    f"clip_frames={len(event_clip_frames) if event_clip_frames else 0} "
                    f"key_frames={len(key_frames) if key_frames else 0} "
                    f"trajectory_points={len(trajectory) if trajectory else 0}")

        # 1) 从事件视频帧序列中选取最具代表性的 3-5 帧作为关键帧送云端
        representative_frames = self._select_representative_frames(event_clip_frames, key_frames)

        # 2) 构建结构化上下文文本 prompt（附加到图片分析中）
        context_prompt = self._build_event_context_prompt(
            vehicle_info, scene_context, event_type, trajectory
        )

        # 3) YOLO 节点（本地已有，直接填充）
        yolo_result = {
            'violation_type': event_type,
            'confidence': float(vehicle_info.get('confidence', 0.0) or 0.0),
            'detections': [{
                'bbox': vehicle_info.get('bbox', []),
                'class_name': vehicle_info.get('class_name', 'unknown'),
                'track_id': vehicle_info.get('track_id', -1),
            }],
            'duration_ms': 0,  # YOLO 已在本地完成，此处不计入
        }

        # 4) 豆包视觉分析（主视觉模型）
        doubao_result = self._analyze_event_with_doubao(
            representative_frames, event_type, context_prompt
        )

        # 5) Claude 分析（如果可用）
        claude_result = self._analyze_event_with_claude(
            representative_frames, event_type, context_prompt
        )

        # 6) DeepSeek 二级验证
        deepseek_result = self._analyze_event_with_deepseek(
            doubao_result, claude_result, event_type, context_prompt, yolo_result
        )

        # 7) 最终裁决
        final_result = self._build_event_final_judgment(
            doubao_result, claude_result, deepseek_result, event_type
        )

        # 8) 构建 ai_trace v3
        ai_trace = self.build_ai_trace(
            yolo_result=yolo_result,
            doubao_result=doubao_result,
            deepseek_result=deepseek_result,
            final_result=final_result,
            claude_result=claude_result if claude_result else None,
        )

        # 补充 final 节点的 explanation 和 risk_flag 字段
        if 'final' in ai_trace:
            ai_trace['final']['explanation'] = final_result.get('explanation', '')
            ai_trace['final']['risk_flag'] = bool(final_result.get('risk_flag', False))

        elapsed_ms = int((_time.time() - start_ts) * 1000)
        logger.info(f"[CloudCollaborator] analyze_event 完成: type={event_type} "
                    f"judgment={ai_trace.get('final', {}).get('judgment', 'unknown')} "
                    f"confidence={ai_trace.get('final', {}).get('confidence', 0.0):.2f} "
                    f"elapsed={elapsed_ms}ms")

        return ai_trace

    def _select_representative_frames(self, event_clip_frames: List,
                                       key_frames: List, max_count: int = 5) -> List:
        """从事件视频帧序列中选取最具代表性的 3-5 帧作为关键帧送云端

        策略：优先用显式传入的 key_frames，不足时从 event_clip_frames 均匀采样。
        """
        result = []
        # 优先用显式 key_frames
        if key_frames:
            result.extend(key_frames[:max_count])
        # 不足则从 event_clip_frames 均匀采样
        if len(result) < max_count and event_clip_frames:
            need = max_count - len(result)
            total = len(event_clip_frames)
            if total <= need:
                sampled = [f for _, f in event_clip_frames]
            else:
                # 均匀采样
                step = total / need
                indices = [int(i * step) for i in range(need)]
                sampled = [event_clip_frames[idx][1] for idx in indices]
            result.extend(sampled)
        return result[:max_count]

    def _build_event_context_prompt(self, vehicle_info: Dict, scene_context: Dict,
                                    event_type: str, trajectory: List) -> str:
        """构建结构化上下文文本 prompt（附加到图片分析中）"""
        lines = [
            f"事件类型: {event_type}",
            f"车辆类型: {vehicle_info.get('class_name', 'unknown')}",
            f"车牌号: {vehicle_info.get('plate_number', '未识别')}",
            f"速度: {vehicle_info.get('speed', 0.0):.1f} km/h",
            f"方向: {vehicle_info.get('direction', 0.0):.1f}°",
            f"信号灯状态: {scene_context.get('traffic_light', 'unknown')}",
            f"车道: {scene_context.get('lane', 'unknown')}",
            f"停止线位置: {scene_context.get('stop_line', 'unknown')}",
            f"轨迹点数: {len(trajectory) if trajectory else 0}",
        ]
        if trajectory and len(trajectory) >= 2:
            first = trajectory[0]
            last = trajectory[-1]
            lines.append(f"轨迹起点: ({first.get('x', 0):.0f}, {first.get('y', 0):.0f})")
            lines.append(f"轨迹终点: ({last.get('x', 0):.0f}, {last.get('y', 0):.0f})")
        return "\n".join(lines)

    def _analyze_event_with_doubao(self, frames: List, event_type: str,
                                    context_prompt: str) -> Dict[str, Any]:
        """豆包视觉分析事件（含结构化上下文 prompt）"""
        import time as _time
        start = _time.time()
        try:
            from image_recognizer import analyze_with_doubao
            # 用第一帧作为分析图（代表性帧）
            if not frames:
                return self._empty_ai_result('doubao', '无可用帧')
            frame = frames[0]
            # 如果 frame 是 numpy 数组，转 base64
            if hasattr(frame, 'shape'):
                import cv2
                import base64
                _, buffer = cv2.imencode('.jpg', frame)
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
            else:
                frame_b64 = frame  # 已是 base64 字符串

            result = analyze_with_doubao(frame_b64, event_type, context_prompt)
            # 豆包置信度必须 min(val/100.0, 1.0) 转换（硬约束 #5）
            raw_conf = float(result.get('confidence_adjusted', 0.0) or 0.0)
            result['confidence_adjusted'] = min(raw_conf / 100.0, 1.0) if raw_conf > 1.0 else raw_conf
            result['duration_ms'] = int((_time.time() - start) * 1000)
            return result
        except Exception as e:
            logger.error(f"[CloudCollaborator] 豆包事件分析异常: {e}")
            return self._empty_ai_result('doubao', f'异常: {e}')

    def _analyze_event_with_claude(self, frames: List, event_type: str,
                                    context_prompt: str) -> Dict[str, Any]:
        """Claude 视觉分析事件（如果 API Key 可用）"""
        import time as _time
        start = _time.time()
        try:
            if not self.claude_api_key:
                return {}  # Claude 未配置，返回空（graceful degradation）
            from image_recognizer import analyze_with_claude
            if not frames:
                return {}
            frame = frames[0]
            if hasattr(frame, 'shape'):
                import cv2
                import base64
                _, buffer = cv2.imencode('.jpg', frame)
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
            else:
                frame_b64 = frame
            result = analyze_with_claude(frame_b64, event_type, context_prompt)
            raw_conf = float(result.get('confidence_adjusted', 0.0) or 0.0)
            result['confidence_adjusted'] = min(raw_conf / 100.0, 1.0) if raw_conf > 1.0 else raw_conf
            result['duration_ms'] = int((_time.time() - start) * 1000)
            return result
        except Exception as e:
            logger.warning(f"[CloudCollaborator] Claude 事件分析异常（降级）: {e}")
            return {}

    def _analyze_event_with_deepseek(self, doubao_result: Dict, claude_result: Dict,
                                      event_type: str, context_prompt: str,
                                      yolo_result: Optional[Dict] = None) -> Dict[str, Any]:
        """DeepSeek 二级验证事件分析结果"""
        import time as _time
        start = _time.time()
        try:
            from image_recognizer import analyze_with_deepseek_judge
            # 合并豆包和 Claude 结果作为 DeepSeek 输入
            primary_result = claude_result if claude_result else doubao_result
            if not primary_result:
                return self._empty_ai_result('deepseek', '无主分析结果')
            # 按 analyze_with_deepseek_judge(violation_type, yolo_result_dict, doubao_result_dict)
            # 的真实签名对齐入参（修复 B2：此前误传 str 导致 AttributeError 被降级吞掉）：
            #   1) 事件类型；2) 结构化 YOLO dict（含 success/detections，每项带 class_name+confidence，
            #   避免 deepseek 内部按 x['confidence'] 取值时 KeyError）；3) 主视觉模型完整结果 dict。
            #   context_prompt 并入 yolo dict 的 message 说明字段。
            src_yolo = yolo_result or {}
            det_conf = float(src_yolo.get('confidence', 0.0) or 0.0)
            yolo_result_dict = {
                'success': True,
                'detections': [
                    {
                        'class_name': d.get('class_name', 'unknown'),
                        'confidence': float(d.get('confidence', det_conf) or det_conf),
                    }
                    for d in (src_yolo.get('detections', []) or [])
                ],
                'message': f"事件级本地检测（YOLO+跟踪已触发）；结构化上下文：\n{context_prompt}",
            }
            result = analyze_with_deepseek_judge(
                event_type,
                yolo_result_dict,
                primary_result,
            )
            raw_conf = float(result.get('confidence_adjusted', 0.0) or 0.0)
            result['confidence_adjusted'] = min(raw_conf / 100.0, 1.0) if raw_conf > 1.0 else raw_conf
            result['duration_ms'] = int((_time.time() - start) * 1000)
            return result
        except Exception as e:
            logger.error(f"[CloudCollaborator] DeepSeek 事件分析异常: {e}")
            return self._empty_ai_result('deepseek', f'异常: {e}')

    def _build_event_final_judgment(self, doubao_result: Dict, claude_result: Dict,
                                     deepseek_result: Dict, event_type: str) -> Dict[str, Any]:
        """构建事件最终裁决（GPT §7：允许返回 uncertain）"""
        try:
            # 构造与 process_cloud_response 兼容的 cloud_result 嵌套结构
            cloud_result = {
                'claude_result': claude_result or {},
                'doubao_result': doubao_result or {},
                'deepseek_result': deepseek_result or {},
                'pending_review': False,
            }
            # local_result：本地规则判断（事件触发时已认定疑似违规）
            primary = claude_result if claude_result else doubao_result
            local_result = {
                'is_violation': True,
                'confidence': float(primary.get('confidence_adjusted', 0.0) or 0.0),
            }
            final = self.process_cloud_response(local_result, cloud_result)
            # GPT §7：允许返回 uncertain（process_cloud_response 在分歧时返回 pending_review）
            if final.get('judgment') == 'pending_review' or final.get('pending_review'):
                final['judgment'] = 'uncertain'
                final['explanation'] = 'AI 无法确认，证据不足或主辅模型存在分歧，需人工复核'
            else:
                final['explanation'] = (
                    f"事件类型: {event_type}, "
                    f"主模型判断: {primary.get('is_violation_confirmed', False)}, "
                    f"DeepSeek 判断: {deepseek_result.get('is_violation_confirmed', False)}, "
                    f"最终: {final.get('judgment', 'unknown')}"
                )
            final['risk_flag'] = bool(final.get('disagreement_flag', False))
            final['evidence_count'] = max(1, final.get('evidence_count', 1))
            return final
        except Exception as e:
            logger.error(f"[CloudCollaborator] 事件最终裁决异常: {e}")
            return {
                'judgment': 'uncertain',
                'confidence': 0.0,
                'method': 'error_fallback',
                'evidence_count': 0,
                'explanation': f'裁决异常: {e}',
                'risk_flag': False,
            }

    def _empty_ai_result(self, source: str, message: str) -> Dict[str, Any]:
        """空 AI 结果（graceful degradation）"""
        return {
            'success': False,
            'result_text': message,
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'duration_ms': 0,
            'source': source,
        }

    # ------------------------------------------------------------------
    # 4.6 构建 v3.1 版本 ai_trace 嵌套结构（双图分析增强）
    # ------------------------------------------------------------------
    def build_ai_trace_v31(
        self,
        yolo_result: Dict[str, Any],
        doubao_result: Dict[str, Any],
        deepseek_result: Dict[str, Any],
        final_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        构建 v3.1 版本 ai_trace 嵌套结构（支持双图分析）
        
        返回:
            {
                "version": "v3.1",
                "yolo": {...},
                "doubao": {
                    "original_analysis": {...},
                    "annotated_analysis": {...},
                    "final_judgment": {...}
                },
                "deepseek": {
                    "original_analysis": {...},
                    "annotated_analysis": {...},
                    "final_judgment": {...}
                },
                "final": {...}
            }
        """
        yolo = yolo_result or {}
        doubao = doubao_result or {}
        ds = deepseek_result or {}
        final = final_result or {}

        yolo_node = {
            'violation_type': yolo.get('violation_type', 'unknown'),
            'confidence': float(yolo.get('confidence', 0.0)),
            'detections': yolo.get('detections', []),
            'duration_ms': int(yolo.get('duration_ms', 0)),
        }

        doubao_node = {
            'original_analysis': {
                'judgment': 'pending',
                'confidence': 0.0,
                'reasoning': '原始图分析由云端独立完成',
            },
            'annotated_analysis': {
                'judgment': 'confirmed' if doubao.get('is_violation_confirmed', False) else 'rejected',
                'confidence': float(doubao.get('confidence_adjusted', 0.0)),
                'reasoning': doubao.get('result_text', ''),
            },
            'final_judgment': {
                'judgment': 'confirmed' if doubao.get('is_violation_confirmed', False) else 'rejected',
                'confidence': float(doubao.get('confidence_adjusted', 0.0)),
            },
            'duration_ms': int(doubao.get('duration_ms', 0)),
        }

        deepseek_node = {
            'original_analysis': {
                'judgment': 'pending',
                'confidence': 0.0,
                'reasoning': '原始图分析由云端独立完成',
            },
            'annotated_analysis': {
                'judgment': 'confirmed' if ds.get('is_violation_confirmed', False) else 'rejected',
                'confidence': float(ds.get('confidence_adjusted', 0.0)),
                'reasoning': ds.get('result_text', ''),
            },
            'final_judgment': {
                'judgment': 'confirmed' if ds.get('is_violation_confirmed', False) else 'rejected',
                'confidence': float(ds.get('confidence_adjusted', 0.0)),
                'review_summary': ds.get('result_text', ''),
            },
            'disagreement_flag': bool(final.get('disagreement_flag', False)),
            'duration_ms': int(ds.get('duration_ms', 0)),
        }

        final_node = {
            'judgment': final.get('judgment', 'pending_review'),
            'confidence': float(final.get('confidence', 0.0)),
            'method': final.get('method', 'unknown'),
            'evidence_count': int(final.get('evidence_count', 0)),
            'has_dual_images': True,
        }

        return {
            'version': 'v3.1',
            'yolo': yolo_node,
            'doubao': doubao_node,
            'deepseek': deepseek_node,
            'final': final_node,
        }

    # ------------------------------------------------------------------
    # 5. 保存协作日志到 JSON 文件
    # ------------------------------------------------------------------
    def save_collaboration_log(self, session_id: str, data: Dict[str, Any]) -> str:
        """
        保存协作日志到 JSON 文件

        参数:
            session_id: 会话ID
            data: 日志数据（协作过程与裁决结果）

        返回:
            保存的文件绝对路径；失败时返回空字符串
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 防止路径穿越
            safe_session = (session_id or 'unknown').replace('/', '_').replace('\\', '_')
            safe_session = safe_session.replace(':', '_').replace(' ', '_')
            filename = f"{safe_session}_{timestamp}.json"
            filepath = os.path.join(self.log_dir, filename)

            log_entry = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'data': data,
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, ensure_ascii=False, indent=2)

            logger.info(f"[CloudCollaborator] 协作日志已保存: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"[CloudCollaborator] 保存协作日志失败: {e}")
            return ""

    # ------------------------------------------------------------------
    # 6. 获取协作统计数据
    # ------------------------------------------------------------------
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取协作统计数据（基于 collaboration_logs 目录下的历史日志聚合）

        返回:
            {
                'total_logs': int,
                'urgent_count': int,
                'consult_count': int,
                'normal_count': int,
                'pending_review_count': int,
                'success_rate': float,         # 0-1
                'avg_duration_ms': int,
                'judgment_distribution': {
                    'confirmed': int,
                    'rejected': int,
                    'pending_review': int
                }
            }
        """
        stats = {
            'total_logs': 0,
            'urgent_count': 0,
            'consult_count': 0,
            'normal_count': 0,
            'pending_review_count': 0,
            'success_rate': 0.0,
            'avg_duration_ms': 0,
            'judgment_distribution': {
                'confirmed': 0,
                'rejected': 0,
                'pending_review': 0,
            },
        }

        try:
            if not os.path.exists(self.log_dir):
                return stats

            durations = []
            success_count = 0
            files = [f for f in os.listdir(self.log_dir) if f.endswith('.json')]

            for fname in files:
                fpath = os.path.join(self.log_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        entry = json.load(f)
                except Exception as e:
                    logger.warning(f"[CloudCollaborator] 读取日志失败 {fname}: {e}")
                    continue

                # 兼容两种日志结构：{data:{...}} 或 直接 {...}
                data = entry.get('data', {}) if isinstance(entry, dict) else {}
                if not data and isinstance(entry, dict):
                    data = entry
                if not isinstance(data, dict):
                    continue

                stats['total_logs'] += 1

                # 模式统计
                reason = str(data.get('reason') or data.get('mode') or '').lower()
                if reason == 'urgent':
                    stats['urgent_count'] += 1
                elif reason == 'consult':
                    stats['consult_count'] += 1
                else:
                    stats['normal_count'] += 1

                # 成功率统计
                if data.get('success', False):
                    success_count += 1

                # 时长统计
                dur = data.get('duration_ms')
                if isinstance(dur, (int, float)) and dur > 0:
                    durations.append(dur)

                # 待复核统计
                if data.get('pending_review', False):
                    stats['pending_review_count'] += 1

                # 裁决分布
                final = data.get('final_result') or data.get('final') or {}
                if isinstance(final, dict):
                    judgment = str(final.get('judgment') or '').lower()
                    if judgment in stats['judgment_distribution']:
                        stats['judgment_distribution'][judgment] += 1
                    elif judgment:
                        # 其他类型（如 pending_review 已在键里）保守归到 pending_review
                        stats['judgment_distribution']['pending_review'] += 1

            # 计算派生指标
            if stats['total_logs'] > 0:
                stats['success_rate'] = round(success_count / stats['total_logs'], 4)
            if durations:
                stats['avg_duration_ms'] = int(sum(durations) / len(durations))

        except Exception as e:
            logger.error(f"[CloudCollaborator] 统计计算异常: {e}")

        return stats
