# -*- coding: utf-8 -*-
"""TASK-COORD-009A 契约测试：源时间轴 / 回放 sidecar 新字段 / 性能指标

覆盖任务书验收标准：
1. 固定源时间窗口 → 事件 clip 的媒体时长与窗口偏差 ≤5%
2. sidecar 含真实源帧序/源时间；frames[].time 与播放器时间一致；
   旧字段全部保留（旧 sidecar 仍可读取）
3. 沿用最近一次检测观测时保留真实观测年龄（stale/observed_age_sec），不伪造新检测
4. /status 指标：capture_fps / infer_fps / dropped_ticks / infer_duration_ms /
   frame_buffer_span_sec / last_infer_age_ms，缺值用 None
5. 缓存内存有界（帧数 + 时间窗双约束），且默认不改变旧行为

隔离性：全部写入 tempfile 目录，不触碰项目 DB / 事件视频 / JPG / sidecar。
"""

import os
import sys
import json
import glob
import time
import shutil
import tempfile
import unittest

import numpy as np

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api'))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

try:
    import cv2
    from circular_frame_buffer import CircularFrameBuffer
    from config import Config
    DEPS_OK = True
except ImportError as e:
    DEPS_OK = False
    _IMPORT_ERROR = e

PROJECT_EVENT_VIDEO_DIR = os.path.join(API_DIR, 'output', 'event_videos')
SRC_FPS = 25.0          # 模拟源视频帧率
BASE_CAPTURE_TS = 1_700_000_000.0


def _frame(w=64, h=48, fill=0):
    return np.full((h, w, 3), fill, dtype=np.uint8)


def _meta(source_time, source_frame_index, captured_at,
          observed_at=None, observed_source_time=None, track_id=7):
    """构造与 realtime_detector._buffer_frame 同构的元数据"""
    return {
        'tracked_vehicles': [{
            'id': track_id, 'class_name': 'car',
            'bbox': [10.0, 20.0, 60.0, 80.0], 'speed': 12.5, 'direction': 'right',
        }],
        'observed_at': observed_at,
        'observed_source_time': observed_source_time,
        'observed_source_frame_index': None,
        'observed_duration_ms': 120.0,
        'source_fps': SRC_FPS,
    }


@unittest.skipUnless(DEPS_OK, f'缺少依赖: {_IMPORT_ERROR if not DEPS_OK else ""}')
class TestSourceTimebaseAndSidecar(unittest.TestCase):
    """源时间轴提取 + sidecar 契约 + 时长一致性"""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix='timeline_contract_')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def _fill_buffer(self, buf, n=200, infer_every=None):
        """按 25fps 源时间轴灌入 n 帧；观测时刻模拟"每 infer_every 帧才有一次新推理"

        Returns:
            list[dict] 每帧的元数据（便于断言）
        """
        metas = []
        for i in range(n):
            src_t = i / SRC_FPS
            cap_t = BASE_CAPTURE_TS + src_t
            # 默认：整段只有第 0 帧发生过一次真实推理（模拟推理远慢于采集）
            if infer_every is None:
                observed_at = BASE_CAPTURE_TS if i == 0 else BASE_CAPTURE_TS
                observed_src = 0.0 if i == 0 else 0.0
            else:
                k = (i // infer_every) * infer_every
                observed_at = BASE_CAPTURE_TS + k / SRC_FPS
                observed_src = k / SRC_FPS
            m = _meta(src_t, i, cap_t,
                      observed_at=observed_at, observed_source_time=observed_src)
            metas.append(m)
            buf.add(cap_t, _frame(fill=i % 256), m,
                    source_time=src_t, source_frame_index=i,
                    captured_mono=1000.0 + src_t)
        return metas

    # ------------------------------------------------------------------
    def test_01_source_time_recorded_and_span(self):
        """源时间被记录；跨度按源时间计算"""
        buf = CircularFrameBuffer(duration_sec=30, fps=10, trim_to_window=True)
        self.assertFalse(buf.has_source_time)
        self._fill_buffer(buf, n=100)          # 100 帧 @25fps = 3.96s
        self.assertTrue(buf.has_source_time)
        self.assertAlmostEqual(buf.source_time_span(), 99 / SRC_FPS, places=4)
        # 采集墙钟跨度与源时间跨度一致（本测试中两者同源推进）
        self.assertAlmostEqual(buf.duration, 99 / SRC_FPS, places=3)
        print(f"[test_01] source_span={buf.source_time_span():.4f}s "
              f"capture_span={buf.duration:.4f}s size={buf.size}")

    def test_02_extract_by_source_timebase(self):
        """timebase='source' 精确选取源时间窗口；'capture' 行为不变"""
        buf = CircularFrameBuffer(duration_sec=30, fps=10, trim_to_window=True)
        self._fill_buffer(buf, n=200)          # 200 帧 @25fps = 7.96s
        # 窗口 [2.5, 5.5] @25fps → i=63..137 → 75 帧
        clip = buf.extract_event_clip_with_meta(4.0, before_sec=1.5, after_sec=1.5,
                                               timebase='source')
        self.assertEqual(len(clip), 75)
        srcs = [m['source_time'] for _, _, m in clip]
        self.assertAlmostEqual(srcs[0], 63 / SRC_FPS, places=6)
        self.assertAlmostEqual(srcs[-1], 137 / SRC_FPS, places=6)
        # 源时间单调递增，且都落在窗口内
        self.assertEqual(srcs, sorted(srcs))
        self.assertTrue(all(2.5 <= s <= 5.5 for s in srcs))
        # 2 元组接口仍保持旧形态
        clip2 = buf.extract_event_clip(4.0, before_sec=1.5, after_sec=1.5, timebase='source')
        self.assertEqual(len(clip2), 75)
        for item in clip2:
            self.assertEqual(len(item), 2)
        print(f"[test_02] source窗口取到 {len(clip)} 帧 "
              f"[{srcs[0]:.3f}, {srcs[-1]:.3f}]")

    def test_03_output_duration_matches_source_window(self):
        """★ 核心验收：媒体时长与所选源时间窗口偏差 ≤5%"""
        buf = CircularFrameBuffer(duration_sec=30, fps=10, trim_to_window=True)
        self._fill_buffer(buf, n=200)
        before, after = 1.5, 1.5
        window_sec = before + after
        clip = buf.extract_event_clip_with_meta(4.0, before_sec=before, after_sec=after,
                                               timebase='source')
        self.assertTrue(clip)
        # 通过被测代码自身推导 fps（与 realtime_detector._handle_event_lifecycle 同路径）
        from realtime_detector import RealtimeViolationDetector
        fps_out = RealtimeViolationDetector._derive_clip_fps(clip, 'source')
        self.assertIsNotNone(fps_out, '应从源时间跨度推导出输出 fps')

        out = os.path.join(self.tmpdir, 'evt_window.mp4')
        saved = buf.save_event_video(clip, out, fps=fps_out,
                                     sidecar_extra={'timebase': 'source'})
        self.assertEqual(saved, out)
        cap = cv2.VideoCapture(out)
        self.assertTrue(cap.isOpened())
        fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps_container = float(cap.get(cv2.CAP_PROP_FPS))
        cap.release()
        self.assertEqual(fc, len(clip))
        duration = fc / fps_container if fps_container else 0.0
        deviation = abs(duration - window_sec) / window_sec
        print(f"[test_03] window={window_sec:.3f}s frames={fc} "
              f"fps_container={fps_container:.4f} duration={duration:.3f}s "
              f"deviation={deviation * 100:.2f}%")
        self.assertLessEqual(deviation, 0.05,
                             f'媒体时长 {duration:.3f}s 与窗口 {window_sec:.3f}s '
                             f'偏差 {deviation * 100:.2f}% > 5%')

    def test_04_sidecar_schema_v2_and_old_fields(self):
        """sidecar 旧字段保留 + 新增 schema_version/source_fps/逐帧源时间"""
        buf = CircularFrameBuffer(duration_sec=30, fps=10, trim_to_window=True)
        self._fill_buffer(buf, n=60)
        clip = buf.extract_event_clip_with_meta(1.0, before_sec=0.5, after_sec=0.5,
                                               timebase='source')
        from realtime_detector import RealtimeViolationDetector
        fps_out = RealtimeViolationDetector._derive_clip_fps(clip, 'source')
        out = os.path.join(self.tmpdir, 'evt_schema.mp4')
        buf.save_event_video(clip, out, fps=fps_out, sidecar_extra={'timebase': 'source'})
        with open(out + '.replay.json', encoding='utf-8') as f:
            sc = json.load(f)

        # --- 旧字段（旧读取方兼容）---
        for k in ('version', 'event_id', 'source', 'video_width', 'video_height',
                  'fps', 'frame_count', 'generated_at', 'frames'):
            self.assertIn(k, sc, f'旧字段 {k} 丢失')
        self.assertEqual(sc['frame_count'], len(clip))
        self.assertEqual(len(sc['frames']), len(clip))
        for i, fr in enumerate(sc['frames']):
            for k in ('index', 'time', 'vehicles'):
                self.assertIn(k, fr, f'frames[{i}] 旧字段 {k} 丢失')
            self.assertEqual(fr['index'], i)
            # frames[].time 是回放媒体时间，与播放器 currentTime*fps 对齐
            self.assertAlmostEqual(fr['time'], i / sc['fps'], places=3)
        self.assertEqual(sc['frames'][0]['vehicles'][0]['track_id'], 7)

        # --- 新增字段 ---
        self.assertEqual(sc['schema_version'], 2)
        self.assertEqual(sc['timebase'], 'source')
        self.assertAlmostEqual(sc['source_fps'], SRC_FPS, places=2)
        for i, fr in enumerate(sc['frames']):
            self.assertIsNotNone(fr['source_time'], f'frames[{i}].source_time 缺失')
            self.assertIsNotNone(fr['source_frame_index'], f'frames[{i}].source_frame_index 缺失')
            self.assertIsNotNone(fr['captured_at'])
        # 源时间与源帧序自洽
        self.assertAlmostEqual(sc['frames'][0]['source_time'],
                               sc['frames'][0]['source_frame_index'] / SRC_FPS, places=6)
        # 媒体时长应与源时间跨度一致（±5%）
        media = sc['frame_count'] / sc['fps']
        src_span = sc['source_time_end'] - sc['source_time_start']
        self.assertLessEqual(abs(media - src_span) / src_span, 0.05,
                             f'media={media:.3f}s src_span={src_span:.3f}s')
        print(f"[test_04] schema={sc['schema_version']} fps_out={sc['fps']} "
              f"source_fps={sc['source_fps']} media={media:.3f}s src_span={src_span:.3f}s")

    def test_05_obsolescence_is_recorded_not_faked(self):
        """沿用旧观测时必须保留真实年龄；不谎称新检测"""
        buf = CircularFrameBuffer(duration_sec=30, fps=10, trim_to_window=True)
        self._fill_buffer(buf, n=50)   # 全程只有第 0 帧有一次真实推理
        clip = buf.extract_event_clip_with_meta(0.5, before_sec=0.4, after_sec=0.4,
                                               timebase='source')
        self.assertTrue(clip)
        ages = [m['observed_age_sec'] for _, _, m in clip]
        self.assertTrue(all(a is not None for a in ages), '观测年龄必须被记录')
        # 年龄随源时间推进单调不减（沿用同一观测）
        self.assertEqual(ages, sorted(ages))
        # 期望值 = 与第 0 帧的源时间差（采集墙钟与源时间同步推进）
        self.assertAlmostEqual(ages[0], (clip[0][2]['source_time'] - 0.0), places=2)
        self.assertGreater(ages[-1], ages[0], '沿用旧观测的年龄必须增长')
        threshold = float(getattr(Config, 'STALE_OBSERVATION_SEC', 0.3))
        for _, _, m in clip:
            self.assertEqual(m['stale'], m['observed_age_sec'] > threshold)
        # 观测源时间保持不变 → 证明是"沿用"而非伪造新观测
        src_refs = {m['observed_source_time'] for _, _, m in clip}
        self.assertEqual(src_refs, {0.0})
        self.assertTrue(any(m['stale'] for _, _, m in clip), '应出现 stale=True 的沿用帧')
        print(f"[test_05] observed_age_sec: 首={ages[0]:.3f} 末={ages[-1]:.3f} "
              f"stale帧={sum(1 for _, _, m in clip if m['stale'])}/{len(clip)}")

    def test_06_capture_timebase_unchanged(self):
        """未开启源时间时，旧行为（采集墙钟窗口/2元组）完全不变"""
        buf = CircularFrameBuffer(duration_sec=30, fps=10, trim_to_window=True)
        for i in range(50):
            buf.add(BASE_CAPTURE_TS + i * 0.04, _frame(), {'tracked_vehicles': []})
        self.assertFalse(buf.has_source_time)
        clip = buf.extract_event_clip_with_meta(BASE_CAPTURE_TS + 1.0,
                                               before_sec=0.2, after_sec=0.2)
        self.assertTrue(clip)
        for item in clip:
            self.assertEqual(len(item), 3)
        # 无源时间 → 逐帧 source_time 必须为 None（不合成）
        self.assertTrue(all(m['source_time'] is None for _, _, m in clip))
        self.assertIsNone(buf.source_time_for_timestamp(BASE_CAPTURE_TS + 1.0))
        print(f"[test_06] capture 时间轴 {len(clip)} 帧，source_time 全为 None")

    def test_07_memory_bounded_by_frames_and_window(self):
        """内存有界：帧数上限 + 时间窗淘汰（两种约束分别生效）"""
        # (a) 帧数约束：maxlen=10，先于时间窗生效
        buf = CircularFrameBuffer(duration_sec=1, fps=10, trim_to_window=True)  # maxlen=10
        for i in range(100):
            src_t = i / SRC_FPS
            buf.add(BASE_CAPTURE_TS + src_t, _frame(), {},
                    source_time=src_t, source_frame_index=i)
        self.assertLessEqual(buf.size, 10, '不得超过 maxlen')
        self.assertLessEqual(buf.source_time_span(), 1.0 + 1e-6, '不得超过时间窗')
        print(f"[test_07a] 帧数约束: size={buf.size} span={buf.source_time_span():.3f}s")

        # (b) 时间窗约束：maxlen 放大到 100，使 100 帧 @25fps(3.96s) 超过 1s 窗口
        buf2 = CircularFrameBuffer(duration_sec=1, fps=100, trim_to_window=True)  # maxlen=100
        for i in range(100):
            src_t = i / SRC_FPS
            buf2.add(BASE_CAPTURE_TS + src_t, _frame(), {},
                     source_time=src_t, source_frame_index=i)
        self.assertGreater(buf2.trimmed_count, 0, '超出时间窗的旧帧必须被淘汰')
        self.assertLessEqual(buf2.source_time_span(), 1.0 + 1e-6, '不得超过时间窗')
        self.assertLess(buf2.size, 100, '时间窗淘汰必须真正生效')
        print(f"[test_07b] 时间窗约束: size={buf2.size} "
              f"span={buf2.source_time_span():.3f}s trimmed={buf2.trimmed_count}")

    def test_08_default_trim_disabled_preserves_legacy_behavior(self):
        """默认构造（trim_to_window=False）不得改变旧的仅按帧数淘汰行为"""
        buf = CircularFrameBuffer(duration_sec=10, fps=10)
        for i in range(20):
            buf.add(BASE_CAPTURE_TS + i, _frame(), {'i': i})
        self.assertEqual(buf.size, 20, '未开启时间窗淘汰时，只受 maxlen 约束')
        self.assertEqual(buf.get_latest(20)[0][2]['i'], 0)
        print(f"[test_08] trim_to_window=False → size={buf.size}（旧行为保持）")


@unittest.skipUnless(DEPS_OK, f'缺少依赖: {_IMPORT_ERROR if not DEPS_OK else ""}')
class TestBackwardCompatibilityWithExistingSidecars(unittest.TestCase):
    """旧 sidecar（TASK-COORD-007 产物）仍可被读取 —— 只读，不修改任何文件"""

    def test_existing_v1_sidecars_still_readable(self):
        files = sorted(glob.glob(os.path.join(PROJECT_EVENT_VIDEO_DIR, '**', '*.replay.json'),
                                 recursive=True))
        if not files:
            self.skipTest('项目内无既有 sidecar，跳过兼容性检查')
        checked = 0
        for path in files:
            with open(path, encoding='utf-8') as f:
                sc = json.load(f)
            # 旧读取方依赖的字段必须存在
            for k in ('version', 'frame_count', 'fps', 'frames'):
                self.assertIn(k, sc, f'{os.path.basename(path)} 缺旧字段 {k}')
            self.assertIsInstance(sc['frames'], list)
            if sc['frames']:
                fr = sc['frames'][0]
                for k in ('index', 'time', 'vehicles'):
                    self.assertIn(k, fr, f'{os.path.basename(path)} frames[0] 缺 {k}')
            checked += 1
        print(f"[旧 sidecar 兼容] 只读校验 {checked} 个既有 v1 sidecar，旧字段齐全")


@unittest.skipUnless(DEPS_OK, f'缺少依赖: {_IMPORT_ERROR if not DEPS_OK else ""}')
class TestStreamMetricsContract(unittest.TestCase):
    """/status 新增指标的取值与缺值语义"""

    @classmethod
    def setUpClass(cls):
        # 需要 realtime_detector 模块（内含 StreamMetrics 与 _derive_clip_fps）
        import realtime_detector
        cls.mod = realtime_detector

    def test_01_all_contract_fields_present_and_null_when_unknown(self):
        m = self.mod.StreamMetrics(window_size=4)
        snap = m.snapshot()
        for k in ('capture_fps', 'infer_fps', 'dropped_ticks', 'infer_duration_ms',
                  'last_infer_age_ms', 'infer_ticks', 'process_duration_ms'):
            self.assertIn(k, snap, f'snapshot 缺字段 {k}')
        # 样本不足 → None（不得编造）
        self.assertIsNone(snap['capture_fps'])
        self.assertIsNone(snap['infer_fps'])
        self.assertIsNone(snap['infer_duration_ms'])
        self.assertIsNone(snap['last_infer_age_ms'])
        self.assertEqual(snap['dropped_ticks'], 0)
        print(f"[metrics] 初始快照 capture_fps={snap['capture_fps']} "
              f"infer_fps={snap['infer_fps']} dropped={snap['dropped_ticks']}")

    def test_02_rates_and_counters(self):
        m = self.mod.StreamMetrics(window_size=10)
        # 采集 10 帧：mono 0.0,0.1,...,0.9 → 10 fps
        for i in range(10):
            m.note_read(mono=i * 0.1)
        # 推理 3 次：mono 0.2,0.6,1.0 → 2.5 fps
        for mono, dur in ((0.2, 250.0), (0.6, 260.0), (1.0, 240.0)):
            m.note_infer(duration_ms=dur, process_duration_ms=dur + 30, mono=mono)
        m.note_tick_dropped()
        m.note_tick_dropped()
        snap = m.snapshot(now_mono=1.5)
        self.assertAlmostEqual(snap['capture_fps'], 10.0, places=2)
        self.assertAlmostEqual(snap['infer_fps'], 2.5, places=2)
        self.assertEqual(snap['dropped_ticks'], 2)
        self.assertEqual(snap['infer_ticks'], 3)
        self.assertEqual(snap['infer_duration_ms'], 240.0)
        self.assertEqual(snap['process_duration_ms'], 270.0)
        self.assertAlmostEqual(snap['last_infer_age_ms'], 500.0, places=1)
        print(f"[metrics] capture_fps={snap['capture_fps']} infer_fps={snap['infer_fps']} "
              f"dropped={snap['dropped_ticks']} infer_ms={snap['infer_duration_ms']} "
              f"age_ms={snap['last_infer_age_ms']}")

    def test_03_status_exposes_new_fields(self):
        """/status（get_status 返回体）必须含契约要求的字段"""
        rd = self.mod.realtime_detector
        status = rd.get_status()
        for k in ('capture_fps', 'infer_fps', 'dropped_ticks', 'infer_duration_ms',
                  'frame_buffer_span_sec', 'last_infer_age_ms'):
            self.assertIn(k, status, f'/status 缺契约字段 {k}')
        # 旧字段仍在
        for k in ('current_fps', 'avg_fps', 'total_frames', 'processed_frames',
                  'frame_buffer_size'):
            self.assertIn(k, status, f'/status 丢失旧字段 {k}')
        print(f"[status] capture_fps={status['capture_fps']} infer_fps={status['infer_fps']} "
              f"dropped={status['dropped_ticks']} infer_ms={status['infer_duration_ms']} "
              f"span={status['frame_buffer_span_sec']} age_ms={status['last_infer_age_ms']} "
              f"source_fps={status['source_fps']}")

    def test_04_derive_clip_fps_rejects_bad_input(self):
        D = self.mod.RealtimeViolationDetector._derive_clip_fps
        self.assertIsNone(D([], 'source'))
        self.assertIsNone(D([(0.0, None, {'source_time': 1.0})], 'source'))
        # 零跨度
        self.assertIsNone(D([(0.0, None, {'source_time': 1.0}),
                             (0.1, None, {'source_time': 1.0})], 'source'))
        # 正常：0..0.96 (25fps) → 24 帧 → (24-1)/0.92 = 25.0
        clip = [(i / 25.0, None, {'source_time': i / 25.0}) for i in range(24)]
        self.assertAlmostEqual(D(clip, 'source'), 25.0, places=3)
        print(f"[derive_fps] 正常输入 → {D(clip, 'source')}；非法输入 → None")


if __name__ == '__main__':
    unittest.main(verbosity=2)
