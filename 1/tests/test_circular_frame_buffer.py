# -*- coding: utf-8 -*-
"""
CircularFrameBuffer 单元测试（TASK-029 M02）

覆盖 6+ 测试用例：
- 添加帧和缓存大小限制
- extract_event_clip 提取正确时间范围
- save_event_video 生成有效 mp4 文件
- duration 属性正确
- get_latest 获取最近 n 帧
- clear 清空缓存
- 循环溢出旧帧
"""

import os
import sys
import time
import tempfile
import unittest

# 让测试能导入 api 模块
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api'))

import numpy as np
from circular_frame_buffer import CircularFrameBuffer


class TestCircularFrameBuffer(unittest.TestCase):

    def _make_frame(self, w=64, h=48, color=(0, 0, 255)):
        """生成测试用 BGR 帧"""
        frame = np.full((h, w, 3), color, dtype=np.uint8)
        return frame

    def test_add_and_size(self):
        """测试添加帧和缓存大小限制"""
        buf = CircularFrameBuffer(duration_sec=2, fps=5)  # maxlen=10
        self.assertEqual(buf.size, 0)
        for i in range(15):
            buf.add(timestamp=time.time() + i * 0.1, frame=self._make_frame(),
                    detection_result={'i': i})
        # 不应超过 maxlen
        self.assertEqual(buf.size, 10)
        print(f"[test_add_and_size] 添加 15 帧，缓存大小={buf.size}（maxlen=10）")

    def test_extract_event_clip(self):
        """测试 extract_event_clip 提取正确时间范围"""
        buf = CircularFrameBuffer(duration_sec=10, fps=10)  # maxlen=100
        base_ts = 1000.0
        for i in range(100):
            buf.add(timestamp=base_ts + i * 0.1, frame=self._make_frame(),
                    detection_result={'i': i})
        # 触发时间 1005.0，提取前 3s 后 2s => [1002.0, 1007.0]
        clip = buf.extract_event_clip(trigger_time=1005.0, before_sec=3, after_sec=2)
        # 预期覆盖 [1002.0, 1007.0] 共 5s，约 50 帧（含边界）
        self.assertGreaterEqual(len(clip), 40)
        self.assertLessEqual(len(clip), 55)
        # 验证时间范围
        for ts, _ in clip:
            self.assertGreaterEqual(ts, 1002.0)
            self.assertLessEqual(ts, 1007.0)
        print(f"[test_extract_event_clip] trigger=1005.0 range=[1002,1007] 返回 {len(clip)} 帧")

    def test_save_event_video(self):
        """测试 save_event_video 生成有效 mp4 文件"""
        buf = CircularFrameBuffer(duration_sec=5, fps=10)
        for i in range(20):
            buf.add(timestamp=time.time() + i * 0.1, frame=self._make_frame(320, 240),
                    detection_result={'i': i})
        clip = buf.get_latest(15)
        # 转成 (ts, frame) 格式
        frames = [(ts, f) for ts, f, _ in clip]
        # 临时文件输出
        tmp_dir = tempfile.mkdtemp()
        out_path = os.path.join(tmp_dir, 'test_event.mp4')
        result = buf.save_event_video(frames, out_path, fps=10)
        self.assertTrue(result, "save_event_video 应返回非空路径")
        self.assertTrue(os.path.exists(out_path), "视频文件应存在")
        self.assertGreater(os.path.getsize(out_path), 0, "视频文件应非空")
        print(f"[test_save_event_video] 生成视频 {out_path} 大小={os.path.getsize(out_path)} bytes")

    def test_duration(self):
        """测试 duration 属性正确"""
        buf = CircularFrameBuffer(duration_sec=10, fps=10)
        # 空 buffer duration=0
        self.assertEqual(buf.duration, 0.0)
        # 添加 10 帧，间隔 0.1s，总时长 0.9s
        base_ts = 1000.0
        for i in range(10):
            buf.add(timestamp=base_ts + i * 0.1, frame=self._make_frame(),
                    detection_result={})
        self.assertAlmostEqual(buf.duration, 0.9, places=1)
        print(f"[test_duration] 10 帧间隔 0.1s，duration={buf.duration:.2f}s")

    def test_get_latest(self):
        """测试 get_latest 获取最近 n 帧"""
        buf = CircularFrameBuffer(duration_sec=10, fps=10)
        for i in range(20):
            buf.add(timestamp=time.time() + i, frame=self._make_frame(),
                    detection_result={'i': i})
        latest_3 = buf.get_latest(3)
        self.assertEqual(len(latest_3), 3)
        # 最近一帧 i=19
        self.assertEqual(latest_3[-1][2]['i'], 19)
        # 请求超过缓存大小
        latest_all = buf.get_latest(100)
        self.assertEqual(len(latest_all), 20)
        print(f"[test_get_latest] 最近 3 帧 i 值={[x[2]['i'] for x in latest_3]}")

    def test_clear(self):
        """测试 clear 清空缓存"""
        buf = CircularFrameBuffer(duration_sec=5, fps=10)
        for i in range(10):
            buf.add(timestamp=time.time(), frame=self._make_frame(),
                    detection_result={'i': i})
        self.assertGreater(buf.size, 0)
        buf.clear()
        self.assertEqual(buf.size, 0)
        self.assertEqual(buf.duration, 0.0)
        print(f"[test_clear] 清空后 size={buf.size} duration={buf.duration}")

    def test_circular_overflow(self):
        """测试循环溢出旧帧"""
        buf = CircularFrameBuffer(duration_sec=2, fps=5)  # maxlen=10
        base_ts = 1000.0
        for i in range(20):  # 添加超过 maxlen
            buf.add(timestamp=base_ts + i * 0.1, frame=self._make_frame(),
                    detection_result={'i': i})
        # 缓存只保留最后 10 帧（i=10..19）
        self.assertEqual(buf.size, 10)
        latest = buf.get_latest(10)
        self.assertEqual(latest[0][2]['i'], 10)
        self.assertEqual(latest[-1][2]['i'], 19)
        print(f"[test_circular_overflow] 添加 20 帧，保留 i=[{latest[0][2]['i']}..{latest[-1][2]['i']}]")

    def test_invalid_params(self):
        """测试无效参数抛出异常"""
        with self.assertRaises(ValueError):
            CircularFrameBuffer(duration_sec=0, fps=10)
        with self.assertRaises(ValueError):
            CircularFrameBuffer(duration_sec=10, fps=-1)
        print("[test_invalid_params] 无效参数已正确抛出 ValueError")

    def test_generate_event_video_path(self):
        """测试事件视频路径生成"""
        buf = CircularFrameBuffer(duration_sec=5, fps=10)
        path = buf.generate_event_video_path('evt_test_001')
        self.assertIn('evt_test_001.mp4', path)
        # 应包含日期目录
        import re
        self.assertRegex(path, r'\d{8}', "路径应包含 YYYYMMDD 日期目录")
        print(f"[test_generate_event_video_path] 生成路径 {path}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
