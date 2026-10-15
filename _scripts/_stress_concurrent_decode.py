# -*- coding: utf-8 -*-
"""cv2 解码**并发**压力测试（2026-10-10 由 DSH 编写）

背景：单线程顺序解码演示视频 1040 帧不崩（44 fps 稳定），
但后端 5 次原生崩溃都在 `opencv_videoio_ffmpeg500_64.dll` 同一偏移。
差异在于后端是**多线程并发**：检测主循环 + MJPEG 绘制 + 云端协作者 + 事件引擎。
-> 本脚本在**同一个进程内**开 N 个线程同时解码同一个 FFV1 视频（每个线程独立 VideoCapture，
   与后端一样），跑固定时长，看会不会崩。

用法：python _stress_concurrent_decode.py <video> <threads> <seconds>
输出纯 ASCII。
"""
import os
import sys
import threading
import time

os.environ.setdefault('OPENCV_LOG_LEVEL', 'ERROR')
import cv2  # noqa: E402

path = sys.argv[1] if len(sys.argv) > 1 else r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv'
nthreads = int(sys.argv[2]) if len(sys.argv) > 2 else 3
seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0

print('video   : %s' % path)
print('threads : %d   duration: %.0fs' % (nthreads, seconds))

stop = threading.Event()
stats = {}
lock = threading.Lock()


def worker(idx):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        with lock:
            stats[idx] = 'OPEN_FAIL'
        return
    n = 0
    loops = 0
    t0 = time.time()
    try:
        while not stop.is_set():
            ok, frame = cap.read()
            if not ok:
                loops += 1
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            n += 1
            if n % 200 == 0:
                with lock:
                    print('  t=%4.1fs  thread%d frames=%-6d loops=%d'
                          % (time.time() - t0, idx, n, loops))
    except Exception as e:
        with lock:
            print('  thread%d EXCEPTION %s: %s' % (idx, type(e).__name__, e))
    finally:
        cap.release()
        with lock:
            stats[idx] = 'frames=%d loops=%d (%.1fs)' % (n, loops, time.time() - t0)


threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(nthreads)]
t0 = time.time()
for t in threads:
    t.start()
time.sleep(seconds)
stop.set()
for t in threads:
    t.join(timeout=10)

print()
for k in sorted(stats):
    print('  thread%-2d %s' % (k, stats[k]))
total = sum(int(str(v).split('frames=')[1].split()[0]) for v in stats.values()
            if str(v).startswith('frames='))
print()
print('RESULT: SURVIVED  threads=%d  total_frames=%d  wall=%.1fs'
      % (nthreads, total, time.time() - t0))
