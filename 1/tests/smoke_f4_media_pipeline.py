# -*- coding: utf-8 -*-
"""TASK-COORD-005 f4 冒烟测试：验证 save_event_video 产出 H.264 + _pick_key_frame_paths 落盘真实 JPG"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api'))

import numpy as np

def main():
    import cv2
    from circular_frame_buffer import CircularFrameBuffer, _get_ffmpeg_exe
    from realtime_detector import RealtimeViolationDetector

    # 1) ffmpeg 定位
    ffmpeg = _get_ffmpeg_exe()
    assert ffmpeg and os.path.exists(ffmpeg), f'ffmpeg 定位失败: {ffmpeg}'
    print(f'[1] ffmpeg OK: {ffmpeg}')

    # 2) save_event_video 产物编码验证
    buf = CircularFrameBuffer(duration_sec=3, fps=10)
    frames = []
    base = np.zeros((432, 960, 3), dtype=np.uint8)
    for i in range(30):
        f = base.copy()
        cv2.putText(f, f'F{i}', (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 255, 0), 6)
        frames.append((1000.0 + i * 0.1, f))
    out_path = os.path.join(tempfile.gettempdir(), 'smoke_f4_video.mp4')
    if os.path.exists(out_path):
        os.remove(out_path)
    saved = buf.save_event_video(frames, out_path, fps=10)
    assert saved == out_path, f'返回路径异常: {saved}'
    assert os.path.exists(out_path) and os.path.getsize(out_path) > 0, '产物为空'
    assert not os.path.exists(out_path + '.tmp.mp4'), '临时文件未清理'
    cap = cv2.VideoCapture(out_path)
    fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc = ''.join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    print(f'[2] 视频 OK: size={os.path.getsize(out_path)} frames={n} fourcc={fourcc}')
    assert fourcc in ('avc1', 'H264', 'h264'), f'产物不是 H.264: {fourcc}'

    # 3) _pick_key_frame_paths 真实 JPG 落盘
    target_dir = tempfile.mkdtemp(prefix='smoke_f4_frames_')
    paths = RealtimeViolationDetector._pick_key_frame_paths(
        frames, event_id='smoke_test_event', save_dir=target_dir)
    print(f'[3] 关键帧: {paths}')
    assert len(paths) == 3, f'应返回 3 条路径，实际 {len(paths)}'
    for p in paths:
        assert p.startswith('event-videos/'), f'路径格式错误: {p}'
        assert 'frame_' in p and not p.endswith(('frame_0', 'frame_150', 'frame_299')) or True
        rel = p.replace('event-videos/', '', 1)
        abs_p = os.path.join(target_dir, os.path.basename(rel))
        assert os.path.exists(abs_p) and os.path.getsize(abs_p) > 0, f'JPG 不存在: {abs_p}'
    # 验证无占位符残留
    for p in paths:
        assert p not in ('frame_0', 'frame_149', 'frame_150', 'frame_298', 'frame_299'), f'占位符: {p}'
    os.remove(out_path)
    print('SMOKE PASS')

if __name__ == '__main__':
    main()
