# -*- coding: utf-8 -*-
"""TASK-COORD-005 聚焦契约测试：事件媒体（视频编码 + 关键帧路径）契约

覆盖任务书验收标准：
1. DB 中 key_frames 不再是占位符（frame_N 形式），且指向真实存在的 JPG
2. DB 中 event_video_path 指向 H.264 编码视频，可读取编码信息
3. 原始 FMP4 文件保留（_h264.mp4 旁必有同名原始 mp4）
4. 静态挂载路径可访问（与 app.py 相同的 /event-videos → Config.EVENT_VIDEO_DIR 挂载）
5. 未来事件路径：save_event_video 产出 H.264；_pick_key_frame_paths 产出真实 JPG 相对路径
"""
import os
import sys
import json
import glob
import shutil
import sqlite3
import tempfile
import unittest

import numpy as np

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api'))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

DB_PATH = os.path.join(API_DIR, 'zhitong_violations.db')
H264_FOURCCS = ('avc1', 'H264', 'h264')


def _fourcc_of(cap):
    v = int(cap.get(cv2.CAP_PROP_FOURCC))
    return ''.join(chr((v >> 8 * i) & 0xFF) for i in range(4))


try:
    import cv2
    import requests
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from starlette.testclient import TestClient
    from config import Config
    DEPS_OK = True
except ImportError as e:
    DEPS_OK = False
    _IMPORT_ERROR = e


@unittest.skipUnless(DEPS_OK, f'缺少依赖: {_IMPORT_ERROR if not DEPS_OK else ""}')
class TestEventMediaContract(unittest.TestCase):
    """现有 7 个事件 + 未来事件生成的媒体契约"""

    @classmethod
    def setUpClass(cls):
        cls.conn = sqlite3.connect(DB_PATH)
        cls.rows = cls.conn.execute(
            'SELECT event_id, event_video_path, key_frames FROM traffic_events ORDER BY created_at'
        ).fetchall()
        cls.event_video_dir = os.path.abspath(Config.EVENT_VIDEO_DIR)
        # 与 app.py 相同配置的最小静态挂载（避免加载 YOLO 模型）
        mini = FastAPI()
        mini.mount('/event-videos', StaticFiles(directory=cls.event_video_dir), name='event-videos')
        cls.client = TestClient(mini)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_01_there_are_events(self):
        self.assertGreaterEqual(len(self.rows), 7, f'事件数应≥7，实际 {len(self.rows)}')

    def test_02_key_frames_not_placeholder(self):
        for eid, vpath, kf in self.rows:
            with self.subTest(event=eid):
                frames = json.loads(kf) if kf else []
                self.assertIsInstance(frames, list, f'{eid}: key_frames 应为 JSON 数组')
                self.assertTrue(frames, f'{eid}: key_frames 不应为空')
                for p in frames:
                    self.assertIsInstance(p, str, f'{eid}: 关键帧路径应为字符串')
                    self.assertRegex(p, r'^event-videos/.+\.jpg$', f'{eid}: 路径格式异常 {p}')
                    self.assertIsNone(
                        __import__('re').fullmatch(r'frame_\d+', p),
                        f'{eid}: 存在占位符路径 {p}')

    def test_03_key_frame_files_exist(self):
        for eid, vpath, kf in self.rows:
            frames = json.loads(kf) if kf else []
            with self.subTest(event=eid):
                self.assertTrue(frames, f'{eid}: 无关键帧')
                for p in frames:
                    rel = p.replace('event-videos/', '', 1).replace('/', os.sep)
                    abs_path = os.path.join(self.event_video_dir, rel)
                    self.assertTrue(os.path.isfile(abs_path), f'{eid}: JPG 不存在 {abs_path}')
                    self.assertGreater(os.path.getsize(abs_path), 0, f'{eid}: JPG 为空 {abs_path}')

    def test_04_video_is_h264_and_original_preserved(self):
        for eid, vpath, kf in self.rows:
            with self.subTest(event=eid):
                self.assertTrue(vpath, f'{eid}: event_video_path 为空')
                abs_path = os.path.abspath(vpath)
                self.assertTrue(os.path.isfile(abs_path), f'{eid}: 视频不存在 {abs_path}')
                self.assertGreater(os.path.getsize(abs_path), 1024, f'{eid}: 视频过小')
                cap = cv2.VideoCapture(abs_path)
                self.assertTrue(cap.isOpened(), f'{eid}: VideoCapture 打不开 {abs_path}')
                fourcc = _fourcc_of(cap)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
                self.assertIn(fourcc, H264_FOURCCS, f'{eid}: 编码非 H.264（fourcc={fourcc}）')
                self.assertGreater(frame_count, 0, f'{eid}: 帧数为 0')
                # 两代事件约定：
                #  - 迁移代（005 生成）：DB 指向 *_h264.mp4，同名原始 FMP4 必须保留
                #  - 原生代（005 f4 之后的事件）：save_event_video 原地产出 H.264 单文件
                #    （test_save_event_video_produces_h264 契约：FMP4 临时文件必须清理）
                if '_h264.mp4' in abs_path:
                    orig = abs_path.replace('_h264.mp4', '.mp4')
                    self.assertNotEqual(orig, abs_path, f'{eid}: event_video_path 不应指向原始文件')
                    self.assertTrue(os.path.isfile(orig), f'{eid}: 原始 FMP4 被删除 {orig}')
                    self.assertGreater(os.path.getsize(orig), 1024, f'{eid}: 原始 FMP4 为空 {orig}')

    def test_05_static_mount_serves_frames_and_video(self):
        for eid, vpath, kf in self.rows:
            with self.subTest(event=eid):
                for p in json.loads(kf) if kf else []:
                    r = self.client.get(f'/{p}')
                    self.assertEqual(r.status_code, 200, f'{eid}: 静态关键帧 HTTP {r.status_code} {p}')
                    self.assertTrue(r.headers['content-type'].startswith('image/jpeg'),
                                    f'{eid}: content-type 异常 {r.headers["content-type"]}')
                    self.assertGreater(len(r.content), 0, f'{eid}: 关键帧响应体为空 {p}')

    def test_06_static_mount_serves_h264_video(self):
        eid, vpath, _ = self.rows[0]
        rel = 'event-videos/' + os.path.basename(os.path.dirname(os.path.abspath(vpath))) \
              + '/' + os.path.basename(os.path.abspath(vpath))
        r = self.client.get(f'/{rel}')
        self.assertEqual(r.status_code, 200, f'{eid}: 视频静态访问 HTTP {r.status_code} {rel}')


@unittest.skipUnless(DEPS_OK, f'缺少依赖: {_IMPORT_ERROR if not DEPS_OK else ""}')
class TestFutureEventMediaGeneration(unittest.TestCase):
    """未来事件生成路径（f4 修改的代码）"""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix='media_contract_')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def _synthetic_frames(self, n=12):
        import cv2
        base = np.zeros((108, 192, 3), dtype=np.uint8)
        frames = []
        for i in range(n):
            f = base.copy()
            cv2.putText(f, f'F{i}', (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
            frames.append((1000.0 + i * 0.1, f))
        return frames

    def test_save_event_video_produces_h264(self):
        import cv2
        from circular_frame_buffer import CircularFrameBuffer
        buf = CircularFrameBuffer(duration_sec=2, fps=10)
        out = os.path.join(self.tmpdir, 'future_event.mp4')
        saved = buf.save_event_video(self._synthetic_frames(), out, fps=10)
        self.assertEqual(saved, out)
        self.assertTrue(os.path.isfile(out))
        self.assertFalse(os.path.exists(out + '.tmp.mp4'), 'mp4v 临时文件未清理')
        cap = cv2.VideoCapture(out)
        self.assertTrue(cap.isOpened())
        fourcc = _fourcc_of(cap)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        self.assertIn(fourcc, H264_FOURCCS, f'新事件视频应为 H.264，实际 fourcc={fourcc}')
        self.assertEqual(frame_count, 12)

    def test_pick_key_frame_paths_real_jpg(self):
        from realtime_detector import RealtimeViolationDetector
        target = os.path.join(self.tmpdir, 'frames')
        paths = RealtimeViolationDetector._pick_key_frame_paths(
            self._synthetic_frames(30), event_id='unit_test_event', save_dir=target)
        self.assertEqual(len(paths), 3, f'应产出 3 个关键帧，实际 {len(paths)}: {paths}')
        for p in paths:
            self.assertRegex(p, r'^event-videos/.+_frame_\d+\.jpg$')
            self.assertIsNone(__import__('re').fullmatch(r'frame_\d+', p), f'占位符 {p}')
        # 文件真实落盘
        for p in paths:
            basename = os.path.basename(p.replace('\\', '/'))
            abs_path = os.path.join(target, basename)
            self.assertTrue(os.path.isfile(abs_path), f'JPG 未落盘 {abs_path}')
            self.assertGreater(os.path.getsize(abs_path), 0)

    def test_pick_key_frame_paths_empty_clip(self):
        from realtime_detector import RealtimeViolationDetector
        self.assertEqual(RealtimeViolationDetector._pick_key_frame_paths([]), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
