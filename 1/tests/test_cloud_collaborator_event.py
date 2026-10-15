# -*- coding: utf-8 -*-
"""
P0-1 回归单测：事件级云端协作仲裁闭环（B1 / B2 修复验证）

对应问题：
- B1：`_analyze_event_with_claude` 曾用 3 个实参调用只有 2 个形参的
      `analyze_with_claude(image_input, violation_type)`，触发 TypeError 被 try/except
      吞掉 → 静默降级返回 {}，事件永远拿不到 Claude 真实仲裁结果。
- B2：`_analyze_event_with_deepseek` 曾把
      `(primary.result_text:str, event_type:str, context_prompt:str)` 传给需要
      `(violation_type, yolo_result_dict:dict, doubao_result_dict:dict)` 的
      `analyze_with_deepseek_judge` → 第 2/3 参本应是 dict 却传 str，内部 .get() 抛
      AttributeError 被吞 → 二审始终走降级默认值。

验证目标（全程不联网）：
1. analyze_event 走 Claude / DeepSeek 正常路径，返回的 ai_trace 中
   claude / deepseek / final 节点均来源于"真实云端结果"而非降级默认值。
2. DeepSeek 二审实参类型为 (str, dict, dict)。
3. 保留优雅降级：真实云端抛异常时不崩溃，仍产出结构完整的 ai_trace。

关键手法：
- 用 `autospec=True` patch `image_recognizer` 的三个云端函数，使 mock 强制校验
  "调用点实参"与"被调函数真实签名"一致：若 B1 回退（调用点 3 参、定义仅 2 参），
  autospec 会抛 TypeError → 被降级捕获 → ai_trace 缺少 claude 节点 → 断言失败。
- 三个事件方法内部是运行时 `from image_recognizer import ...`，故 patch
  `image_recognizer.*` 对事件路径生效（违规路径用的是模块级绑定名，不受影响）。
"""
import os
import sys
import unittest
from unittest.mock import patch

import numpy as np
from types import SimpleNamespace
from unittest.mock import Mock

# 将 api 目录加入 sys.path（与仓库其他测试一致）
API_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api')
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

import image_recognizer

from cloud_collaborator import CloudCollaborator  # noqa: E402


# ---- 可区分的"真实云端结果"：各带唯一 result_text 标记，用于断言非降级 ----
CLAUDE_REAL = {
    'success': True,
    'result_text': 'CLAUDE_REAL_REASONING',
    'is_violation_confirmed': True,
    'confidence_adjusted': 0.90,   # <1.0，避免触发 /100 归一化分支
    'risk_level': 'high',
    'message': 'ok',
    'prompt': 'p',
}
DOUBAO_REAL = {
    'success': True,
    'result_text': 'DOUBAO_REAL_REASONING',
    'is_violation_confirmed': True,
    'confidence_adjusted': 0.85,
    'message': 'ok',
    'prompt': 'p',
}
DEEPSEEK_REAL = {
    'success': True,
    'result_text': 'DEEPSEEK_REAL_REVIEW',
    'is_violation_confirmed': True,
    'confidence_adjusted': 0.88,
    'risk_level': 'high',
    'doubao_opinion_match': True,
    'message': 'ok',
    'prompt': 'p',
}


class TestEventCloudArbitration(unittest.TestCase):
    """事件级云端三级仲裁闭环（analyze_event）回归测试"""

    def setUp(self):
        self.collab = CloudCollaborator()
        # 让事件路径进入 Claude 分支：否则 self.claude_api_key 为空会直接 return {}
        self.collab.claude_api_key = 'test-key-not-real'
        # 代表性关键帧用 base64 字符串，避免依赖 cv2 编码（hasattr(frame,'shape') 为假）
        self.frames = ['ZmFrZWJhc2U2NA==']
        self.vehicle_info = {
            'class_name': 'car', 'confidence': 0.86,
            'bbox': [10, 10, 100, 100], 'track_id': 7,
            'plate_number': '京A12345', 'speed': 42.0, 'direction': 90.0,
        }
        self.scene_context = {'traffic_light': 'red', 'lane': 'straight', 'stop_line': 'crossed'}
        self.trajectory = [{'x': 0, 'y': 0}, {'x': 50, 'y': 10}]

    def _call_event(self):
        return self.collab.analyze_event(
            event_clip_frames=[], key_frames=self.frames,
            vehicle_info=self.vehicle_info, scene_context=self.scene_context,
            event_type='red_light', trajectory=self.trajectory,
        )

    def test_representative_frames_are_sampled_across_clip(self):
        """空的显式关键帧列表时，必须从整段事件视频均匀抽样，而非只取开头。"""
        clip = [(float(i), np.full((8, 12, 3), i, dtype=np.uint8)) for i in range(10)]
        selected = self.collab._select_representative_frames(clip, [], max_count=5)
        self.assertEqual([int(frame[0, 0, 0]) for frame in selected], [0, 2, 4, 6, 8])

    def test_doubao_uncertain_parse_is_not_negative(self):
        """豆包输出【不确定】时解析结果必须保留三态信息，且完全不联网。"""
        content = '\n'.join(['第二步·是否违规：【不确定】', '第四步·置信度评分：20'])
        response = SimpleNamespace(
            status_code=200,
            output=SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=[{'text': content}]))]))
        fake_sdk = SimpleNamespace(api_key='', MultiModalConversation=SimpleNamespace(
            call=Mock(return_value=response)))
        with (
            patch.object(image_recognizer, 'DASHSCOPE_AVAILABLE', True),
            patch.object(image_recognizer, 'dashscope', fake_sdk, create=True),
            patch.object(image_recognizer, '_get_dashscope_key', return_value='fake-key'),
        ):
            result = image_recognizer.analyze_with_doubao('a' * 40, 'red_light')
        self.assertTrue(result['success'])
        self.assertFalse(result['is_violation_confirmed'])
        self.assertTrue(result['is_uncertain'])

    def test_deepseek_uncertain_parse_is_not_negative(self):
        """DeepSeek 的“无法确定·需人工”不能被压成普通否定。"""
        content = '\n'.join(['第三步·你的独立判断：【无法确定·需人工】', '第四步·置信度：20', '第五步·风险评估：【中风险】'])
        response = SimpleNamespace(status_code=200, json=lambda: {
            'choices': [{'message': {'content': content}}]})
        with (
            patch.object(image_recognizer, '_get_deepseek_key', return_value='fake-key'),
            patch('requests.post', return_value=response),
        ):
            result = image_recognizer.analyze_with_deepseek_judge('red_light', {}, dict(DOUBAO_REAL))
        self.assertTrue(result['success'])
        self.assertFalse(result['is_violation_confirmed'])
        self.assertTrue(result['is_uncertain'])

    def test_contact_sheet_contains_multiple_frames_without_network(self):
        """多帧拼图在本地生成，不需要任何云端 API。"""
        frames = [np.full((90, 160, 3), i * 20, dtype=np.uint8) for i in range(5)]
        sheet = self.collab._compose_event_contact_sheet(frames)
        self.assertIsNotNone(sheet)
        self.assertEqual(tuple(sheet.shape), (1080, 1280, 3))

    def test_doubao_receives_contact_sheet_in_one_mocked_call(self):
        """事件视觉调用实际收到拼图，且本地验证不触发网络或额外调用。"""
        import base64
        import cv2

        frames = [np.full((90, 160, 3), i * 20, dtype=np.uint8) for i in range(5)]
        with patch('image_recognizer.analyze_with_doubao', autospec=True) as mock_doubao:
            mock_doubao.return_value = dict(DOUBAO_REAL)
            result = self.collab._analyze_event_with_doubao(frames, 'red_light', 'test context')

        self.assertTrue(result['success'])
        self.assertEqual(mock_doubao.call_count, 1)
        payload = mock_doubao.call_args.args[0]
        encoded = payload.split(',', 1)[1] if payload.startswith('data:image') else payload
        decoded = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), np.uint8), cv2.IMREAD_COLOR)
        self.assertIsNotNone(decoded)
        self.assertEqual(tuple(decoded.shape), (1080, 1280, 3))

    def test_failed_primary_visual_skips_paid_deepseek_call(self):
        """主视觉模型失败时跳过无效二审，避免对空内容再产生一次付费调用。"""
        failed = {'success': False, 'message': 'mock provider failure', 'result_text': ''}
        with patch('image_recognizer.analyze_with_deepseek_judge', autospec=True) as mock_judge:
            result = self.collab._analyze_event_with_deepseek(
                failed, {}, 'red_light', 'test context', {'confidence': 0.5}
            )
        self.assertFalse(result['success'])
        self.assertIn('mock provider failure', result['result_text'])
        mock_judge.assert_not_called()

    def test_ai_trace_preserves_provider_failure_reason(self):
        """前端应能看到视觉模型 unavailable 的原因，而不是只有空 reasoning。"""
        trace = self.collab.build_ai_trace(
            {'violation_type': 'red_light'},
            {'success': False, 'message': 'mock HTTP 401', 'confidence_adjusted': 0.0},
            {'success': False, 'message': 'skipped because primary failed', 'result_text': 'skipped'},
            {'judgment': 'uncertain', 'confidence': 0.0, 'method': 'local_fallback', 'evidence_count': 1},
        )
        self.assertFalse(trace['doubao']['success'])
        self.assertEqual(trace['doubao']['message'], 'mock HTTP 401')
        self.assertFalse(trace['deepseek']['success'])
        self.assertIn('skipped', trace['deepseek']['message'])
    def test_uncertain_visual_evidence_goes_to_manual_review(self):
        """模型明确表示不确定时，不得把 False 布尔值误当成已证实的“不违规”。"""
        doubao = dict(DOUBAO_REAL, is_violation_confirmed=False, is_uncertain=True,
                      confidence_adjusted=0.2)
        deepseek = dict(DEEPSEEK_REAL, is_violation_confirmed=False, is_uncertain=True,
                        confidence_adjusted=0.2)
        final = self.collab._build_event_final_judgment(doubao, {}, deepseek, 'red_light')
        self.assertEqual(final['judgment'], 'uncertain')
        self.assertTrue(final['pending_review'])

    def test_uncertain_second_opinion_does_not_auto_reject(self):
        """主视觉模型确认但二审无法确定时，应人工复核而不是直接排除。"""
        doubao = dict(DOUBAO_REAL, is_violation_confirmed=True, is_uncertain=False,
                      confidence_adjusted=0.9)
        deepseek = dict(DEEPSEEK_REAL, is_violation_confirmed=False, is_uncertain=True,
                        confidence_adjusted=0.2)
        final = self.collab._build_event_final_judgment(doubao, {}, deepseek, 'red_light')
        self.assertEqual(final['judgment'], 'uncertain')
        self.assertTrue(final['pending_review'])



    def _run_happy_path(self):
        """在三个云端函数被 autospec mock 的场景下跑一次 analyze_event"""
        with patch('image_recognizer.analyze_with_doubao', autospec=True) as m_doubao, \
             patch('image_recognizer.analyze_with_claude', autospec=True) as m_claude, \
             patch('image_recognizer.analyze_with_deepseek_judge', autospec=True) as m_deepseek:
            m_doubao.return_value = dict(DOUBAO_REAL)
            m_claude.return_value = dict(CLAUDE_REAL)
            m_deepseek.return_value = dict(DEEPSEEK_REAL)
            trace = self._call_event()
        return trace, m_doubao, m_claude, m_deepseek

    # ------------------------------------------------------------------
    def test_b1_claude_normal_path_not_degraded(self):
        """B1：Claude 事件路径按新签名正常调用，ai_trace.claude 来源于真实结果"""
        trace, _, m_claude, _ = self._run_happy_path()

        self.assertTrue(m_claude.called, 'Claude 事件路径未被调用（可能因签名不符被降级）')
        args, _kwargs = m_claude.call_args
        # 调用点实参与真实签名对齐：第 2 参=事件类型，第 3 参=结构化上下文
        self.assertEqual(args[1], 'red_light')
        self.assertIsInstance(args[2], str)
        self.assertIn('red_light', args[2])    # 上下文确已拼入并被送达
        self.assertIn('京A12345', args[2])

        # build_ai_trace 仅在 claude_result 非空时添加 claude 节点；
        # 若 B1 未修 → 降级 return {} → 无 claude 节点，此断言失败。
        self.assertIn('claude', trace, 'ai_trace 缺少 claude 节点 → Claude 走了降级 return {}')
        self.assertEqual(trace['claude']['reasoning'], 'CLAUDE_REAL_REASONING')
        self.assertEqual(trace['claude']['judgment'], 'confirmed')

    def test_b2_deepseek_receives_dict_args(self):
        """B2：DeepSeek 二审实参为 (str, dict, dict)，节点来源于真实结果"""
        trace, _, _, m_deepseek = self._run_happy_path()

        self.assertTrue(m_deepseek.called, 'DeepSeek 事件路径未被调用')
        args, _kwargs = m_deepseek.call_args
        self.assertEqual(args[0], 'red_light')     # violation_type / event_type
        self.assertIsInstance(args[1], dict)       # yolo_result_dict（修复前是 str）
        self.assertIsInstance(args[2], dict)       # primary/doubao_result_dict（修复前是 str）
        self.assertTrue(args[1].get('success'))

        # 降级会是 _empty_ai_result（result_text 含 '异常'/'无主分析结果'），此处应为真实审核文本
        self.assertEqual(trace['deepseek']['review_summary'], 'DEEPSEEK_REAL_REVIEW')
        self.assertEqual(trace['deepseek']['judgment'], 'confirmed')

    def test_final_judgment_from_real_cloud(self):
        """final.judgment 非空且来源于真实云端仲裁（非降级默认值）"""
        trace, _, _, _ = self._run_happy_path()
        final = trace.get('final', {})

        self.assertNotEqual(final.get('judgment', ''), '')
        self.assertEqual(final['judgment'], 'confirmed')
        # 降级默认值会是 local_fallback / error_fallback / uncertain；
        # 真实"主模型 + DeepSeek 二审"应为 claude_plus_deepseek，证据数=2
        self.assertEqual(final['method'], 'claude_plus_deepseek')
        self.assertEqual(final['evidence_count'], 2)

    def test_graceful_degradation_preserved(self):
        """保留优雅降级：真实云端抛异常时不崩溃，仍产出结构完整的 ai_trace"""
        with patch('image_recognizer.analyze_with_doubao', autospec=True) as m_doubao, \
             patch('image_recognizer.analyze_with_claude', autospec=True) as m_claude, \
             patch('image_recognizer.analyze_with_deepseek_judge', autospec=True) as m_deepseek:
            m_doubao.side_effect = RuntimeError('network down')
            m_claude.side_effect = RuntimeError('network down')
            m_deepseek.side_effect = RuntimeError('network down')
            trace = self._call_event()   # 不应抛出异常

        self.assertEqual(trace.get('version'), 'v3')
        self.assertIn('final', trace)
        self.assertNotEqual(trace['final'].get('judgment', ''), '')
        self.assertEqual(trace['final']['judgment'], 'uncertain',
                         '云端调用失败不能把本地疑似事件自动确认或排除')


if __name__ == '__main__':
    unittest.main()
