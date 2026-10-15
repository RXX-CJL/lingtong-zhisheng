"""
量化"每帧 5 个模型"的开销 —— 给帧率方案提供数据（2026-10-06 由 DSH 编写）

只读：不启动检测、不改配置，只是加载模型跑几次推理计时。
用法：& 'C:\miniconda\envs\zhitong-gpu\python.exe' -B E:\output\_scripts\_bench_models.py
"""
import os
import sys
import time

sys.path.insert(0, r'E:\output\1\api')

import cv2
import numpy as np

FRAME = r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv'

# 取真实一帧（有车、有红绿灯、有车道线）
cap = cv2.VideoCapture(FRAME)
cap.set(cv2.CAP_PROP_POS_FRAMES, 260)
ok, frame = cap.read()
cap.release()
if not ok:
    raise SystemExit('取帧失败')
print(f'测试帧: {frame.shape[1]}x{frame.shape[0]}')

# ★ 必须传 base64 data URL：detect_with_yolo 内部会 input.startswith(...)，
#   直接传 np.ndarray 会报 "'numpy.ndarray' object has no attribute 'startswith'"
#   而它把异常吞成 success=False + 0 检出（我第一次就踩了，白测一轮）。
import base64 as _b64
_ok, _buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
DATA_URL = 'data:image/jpeg;base64,' + _b64.b64encode(_buf.tobytes()).decode('ascii')
print('输入形式: data URL, %d 字节' % len(DATA_URL))

import torch
print('CUDA:', torch.cuda.is_available(),
      '| 设备:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else '-')
if torch.cuda.is_available():
    print('显存: 已用 %.0f MB / 共 %.0f MB' % (
        torch.cuda.memory_allocated() / 1e6, torch.cuda.get_device_properties(0).total_memory / 1e6))

from image_recognizer import detect_with_yolo, init_all_models, yolo_models

print('\n=== 加载模型 ===')
t0 = time.time()
try:
    init_all_models()
except Exception as e:
    print('init_all_models 异常（不致命）:', e)
print('加载耗时 %.1fs' % (time.time() - t0))

SEQ = ['vehicle', 'traffic_light', 'helmet', 'lane', 'license_plate']
IMGSZ = int(os.environ.get('YOLO_IMGSZ', '1280'))
print(f'YOLO_IMGSZ = {IMGSZ}')

print('\n=== 单模型耗时（跑 3 次取中位，首次含预热不计）===')
totals = {}
for key in SEQ:
    ts = []
    for i in range(4):
        t = time.time()
        try:
            r = detect_with_yolo(DATA_URL, key, 0.25)
            n = len(r.get('detections') or [])
            if not r.get('success'):
                print(f'  {key:<15} success=False: {r.get("message")}')
                ts = []
                break
        except Exception as e:
            print(f'  {key:<15} 失败: {e}')
            ts = []
            break
        dt = (time.time() - t) * 1000
        if i > 0:                       # 丢掉第一次（预热）
            ts.append(dt)
        last_n = n
    if ts:
        med = sorted(ts)[len(ts) // 2]
        totals[key] = med
        print(f'  {key:<15} {med:6.0f} ms   检出 {last_n} 个')

if totals:
    per_frame = sum(totals.values())
    print(f'\n=== 结论 ===')
    print(f'  每处理 1 帧总耗时 ≈ {per_frame:.0f} ms  ->  理论上限 {1000/per_frame:.1f} fps')
    print(f'  当前 Config.FRAME_RATE = 3  ->  标注帧率被节流在 3 fps')
    print(f'\n  逐项占比：')
    for k, v in sorted(totals.items(), key=lambda x: -x[1]):
        print(f'    {k:<15} {v:6.0f} ms  {100*v/per_frame:5.1f}%')
    only_vehicle = totals.get('vehicle', 0)
    print(f'\n  只跑 vehicle     ≈ {only_vehicle:.0f} ms/帧 -> 上限 {1000/max(1,only_vehicle):.1f} fps')
    core = totals.get('vehicle', 0) + totals.get('traffic_light', 0)
    print(f'  vehicle+tl       ≈ {core:.0f} ms/帧 -> 上限 {1000/max(1,core):.1f} fps')

if torch.cuda.is_available():
    print('\n峰值显存: %.0f MB' % (torch.cuda.max_memory_allocated() / 1e6))
