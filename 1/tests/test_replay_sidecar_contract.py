# -*- coding: utf-8 -*-
"""TASK-COORD-007 回放数据契约测试：逐帧 sidecar + replay 接口

覆盖任务书验收标准：
1. extract_event_clip_with_meta 保留缓冲三元组第三个元素（检测/跟踪元数据），
   原 extract_event_clip 仍返回 2 元组（云端咨询链路兼容）
2. save_event_video 写出与视频一一对应的 .replay.json
   （frame_count 与视频实际帧数一致、宽高/fps 正确、bbox 来自传入元数据）
3. 混合 2/3 元组时按实际写入帧对齐；无元数据帧 vehicles 诚实留空
4. 全部帧无元数据时不写 sidecar（诚实降级，不伪造）
5. replay 接口：有 sidecar → success+data；无 sidecar → 404 + code=no_frame_replay_data
"""
import os
import sys
import json
import shutil
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api'))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

try:
    import cv2
    from fastapi import FastAPI
    from starlette.testclient import TestClient
    from circular_frame_buffer import CircularFrameBuffer
    DEPS_OK = True
except ImportError as e:
    DEPS_OK = False
    _IMPORT_ERROR = e


@unittest.skipUnless(DEPS_OK, f'缺少依赖: {_IMPORT_ERROR if not DEPS_OK else ""}')
class TestReplaySidecarContract(unittest.TestCase):
    """sidecar 落盘契约（未来事件生成路径）"""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix='replay_sidecar_')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def _meta(self, track_id=20, bbox=(100.0, 120.0, 220.0, 260.0)):
        return {
            'tracked_vehicles': [{
                'id': track_id,
                'class_name': 'car',
                'bbox': list(bbox),
                'speed': 28.42,
                'direction': 'right',
            }]
        }

    def _frames_with_meta(self, n=6):
        base = np.zeros((108, 192, 3), dtype=np.uint8)
        out = []
        for i in range(n):
            f = base.copy()
            cv2.putText(f, f'F{i}', (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
            meta = self._meta(track_id=20 + i,
                              bbox=(100.0 + i * 5, 120.0, 180.0 + i * 5, 200.0))
            out.append((1000.0 + i * 0.1, f, meta))
        return out

    def test_01_extract_with_meta_keeps_third_element(self):
        buf = CircularFrameBuffer(duration_sec=2, fps=10)
        for ts, f, meta in self._frames_with_meta(6):
            buf.add(ts, f, meta)
        clip = buf.extract_event_clip_with_meta(1000.3, before_sec=0.2, after_sec=0.2)
        self.assertTrue(clip, '含元数据提取不应为空')
        for ts, f, meta in clip:
            self.assertIsInstance(meta, dict)
            self.assertIn('tracked_vehicles', meta)
        # 原 extract_event_clip 仍返回 2 元组（云端咨询链路兼容）
        clip2 = buf.extract_event_clip(1000.3, before_sec=0.2, after_sec=0.2)
        self.assertTrue(clip2)
        for item in clip2:
            self.assertEqual(len(item), 2, '原 extract_event_clip 必须保持 2 元组')

    def test_02_save_event_video_writes_matching_sidecar(self):
        buf = CircularFrameBuffer(duration_sec=2, fps=10)
        frames = self._frames_with_meta(6)
        out = os.path.join(self.tmpdir, 'evt_unit.mp4')
        saved = buf.save_event_video(frames, out, fps=10)
        self.assertEqual(saved, out)
        sidecar_path = out + '.replay.json'
        self.assertTrue(os.path.isfile(sidecar_path), 'sidecar 未落盘')
        with open(sidecar_path, 'r', encoding='utf-8') as f:
            sidecar = json.load(f)
        self.assertEqual(sidecar['frame_count'], 6)
        self.assertEqual(sidecar['video_width'], 192)
        self.assertEqual(sidecar['video_height'], 108)
        self.assertEqual(sidecar['fps'], 10)
        self.assertEqual(len(sidecar['frames']), 6)
        # 帧索引与时间（time = index / fps）
        self.assertEqual(sidecar['frames'][0]['index'], 0)
        self.assertAlmostEqual(sidecar['frames'][3]['time'], 0.3)
        # bbox 来自传入的真实元数据，未被补造
        v0 = sidecar['frames'][0]['vehicles'][0]
        self.assertEqual(v0['track_id'], 20)
        self.assertEqual(v0['bbox'], [100.0, 120.0, 180.0, 200.0])
        self.assertEqual(v0['direction'], 'right')
        self.assertAlmostEqual(v0['speed_px'], 28.42, places=2)
        # 视频实际帧数与 sidecar frame_count 一致（一一对应）
        cap = cv2.VideoCapture(out)
        self.assertTrue(cap.isOpened())
        fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        self.assertEqual(fc, sidecar['frame_count'])

    def test_03_mixed_meta_frames_keep_alignment(self):
        buf = CircularFrameBuffer(duration_sec=2, fps=10)
        frames = self._frames_with_meta(4)
        frames.insert(2, (1000.2, frames[0][1]))  # 插入一个无元数据的 2 元组帧
        out = os.path.join(self.tmpdir, 'evt_mixed.mp4')
        saved = buf.save_event_video(frames, out, fps=10)
        self.assertEqual(saved, out)
        with open(out + '.replay.json', 'r', encoding='utf-8') as f:
            sidecar = json.load(f)
        self.assertEqual(sidecar['frame_count'], 5)
        # 无元数据帧诚实留空，不补造车辆
        self.assertEqual(sidecar['frames'][2]['vehicles'], [])
        self.assertEqual(sidecar['frames'][0]['vehicles'][0]['track_id'], 20)

    def test_04_no_meta_no_sidecar(self):
        buf = CircularFrameBuffer(duration_sec=2, fps=10)
        base = np.zeros((108, 192, 3), dtype=np.uint8)
        frames = [(1000.0 + i * 0.1, base.copy()) for i in range(4)]
        out = os.path.join(self.tmpdir, 'evt_nometa.mp4')
        saved = buf.save_event_video(frames, out, fps=10)
        self.assertEqual(saved, out)
        self.assertFalse(os.path.exists(out + '.replay.json'),
                         '全部帧无元数据时不应写 sidecar（诚实降级）')


@unittest.skipUnless(DEPS_OK, f'缺少依赖: {_IMPORT_ERROR if not DEPS_OK else ""}')
class TestReplayEndpoint(unittest.TestCase):
    """GET /api/realtime/events/{id}/replay 接口契约"""

    @classmethod
    def setUpClass(cls):
        from routers.realtime import router
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)
        cls.tmpdir = tempfile.mkdtemp(prefix='replay_endpoint_')

    @classmethod
    def tearDownClass(cls):
        import realtime_detector as rd
        rd.realtime_detector.active_events.pop('evt_unit_test_replay', None)
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_01_old_event_without_sidecar_degrades(self):
        r = self.client.get('/api/realtime/events/evt_definitely_not_exist_xyz/replay')
        self.assertEqual(r.status_code, 404)
        body = r.json()
        self.assertFalse(body['success'])
        self.assertEqual(body['code'], 'no_frame_replay_data')

    def test_02_event_with_sidecar_returns_frames(self):
        import realtime_detector as rd
        video_path = os.path.join(self.tmpdir, 'evt_unit_test_replay.mp4')
        w = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'mp4v'), 10, (192, 108))
        w.write(np.zeros((108, 192, 3), dtype=np.uint8))
        w.release()
        sidecar = {
            'version': 1, 'video_width': 192, 'video_height': 108, 'fps': 10,
            'frame_count': 1,
            'frames': [{'index': 0, 'time': 0.0, 'vehicles': [
                {'track_id': 7, 'class_name': 'car', 'bbox': [10, 20, 60, 80],
                 'speed_px': 12.5, 'direction': 'right'},
            ]}],
        }
        with open(video_path + '.replay.json', 'w', encoding='utf-8') as f:
            json.dump(sidecar, f, ensure_ascii=False)
        # 注入内存事件（接口优先读内存 event_video_path）
        rd.realtime_detector.active_events['evt_unit_test_replay'] = SimpleNamespace(
            event_video_path=video_path)
        r = self.client.get('/api/realtime/events/evt_unit_test_replay/replay')
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body['success'])
        self.assertEqual(body['data']['frame_count'], 1)
        self.assertEqual(body['data']['frames'][0]['vehicles'][0]['track_id'], 7)
        self.assertEqual(body['data']['frames'][0]['vehicles'][0]['bbox'], [10, 20, 60, 80])

    def test_03_video_without_sidecar_degrades(self):
        import realtime_detector as rd
        video_path = os.path.join(self.tmpdir, 'evt_no_sidecar.mp4')
        w = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'mp4v'), 10, (192, 108))
        w.write(np.zeros((108, 192, 3), dtype=np.uint8))
        w.release()
        rd.realtime_detector.active_events['evt_no_sidecar'] = SimpleNamespace(
            event_video_path=video_path)
        try:
            r = self.client.get('/api/realtime/events/evt_no_sidecar/replay')
            self.assertEqual(r.status_code, 200)
            body = r.json()
            self.assertFalse(body['success'])
            self.assertEqual(body['code'], 'no_frame_replay_data')
        finally:
            rd.realtime_detector.active_events.pop('evt_no_sidecar', None)


if __name__ == '__main__':
    unittest.main(verbosity=2)
