# -*- coding: utf-8 -*-
"""cv2 解码压力测试：量化"读多少帧会崩"（2026-10-10 由 DSH 编写）

背景：后端 5 次原生崩溃都在 `opencv_videoio_ffmpeg500_64.dll` 的同一偏移
（`0xc000001d` 非法指令），而演示视频是 **FFV1 / BGRA / 373 Mbps** 这种很不寻常的编码。
本脚本用**独立进程**反复读同一个视频，崩溃时进程会被系统杀掉并留下事件日志，
所以"跑到多少帧"就是崩溃速度的量化值。

用法：python _stress_cv2_decode.py <video> [max_loops] [backend]
  backend: auto(默认) / ffmpeg / msmf
输出纯 ASCII（控制台是 GBK）。
"""
import os
import sys
import time

os.environ.setdefault('OPENCV_LOG_LEVEL', 'ERROR')
import cv2  # noqa: E402

path = sys.argv[1] if len(sys.argv) > 1 else r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv'
max_loops = int(sys.argv[2]) if len(sys.argv) > 2 else 6
backend = (sys.argv[3] if len(sys.argv) > 3 else 'auto').lower()

print('open: %s' % path)
print('backend: %s   max_loops: %d' % (backend, max_loops))

cap = None
if backend == 'ffmpeg':
    cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
elif backend == 'msmf':
    cap = cv2.VideoCapture(path, cv2.CAP_MSMF)
else:
    cap = cv2.VideoCapture(path)

if not cap or not cap.isOpened():
    print('RESULT: CANNOT OPEN (backend=%s)' % backend)
    sys.exit(3)

fps = cap.get(cv2.CAP_PROP_FPS)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print('opened: %dx%d @ %.1f fps' % (w, h, fps))

t0 = time.time()
frames = 0
try:
    for loop in range(1, max_loops + 1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        n = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            n += 1
            frames += 1
            if frames % 500 == 0:
                el = time.time() - t0
                print('  frames=%d  elapsed=%.1fs  fps=%.1f' % (frames, el, frames / max(el, 0.001)))
        print('loop %d done: %d frames (cumulative %d, %.1fs)'
              % (loop, n, frames, time.time() - t0))
except Exception as e:
    print('EXCEPTION: %s: %s' % (type(e).__name__, e))
finally:
    cap.release()

el = time.time() - t0
print('RESULT: SURVIVED %d frames in %.1fs (%.1f fps) with backend=%s'
      % (frames, el, frames / max(el, 0.001), backend))
