"""
端到端验证「框预测」是否真的让框动起来（2026-10-06 由 DSH 编写）

思路：预测只作用于**绘制**（realtime_detector._draw_detection_boxes -> _predict_boxes），
      所以 /api/realtime/vehicles 看到的是追踪器真实框，验证不到预测。
      真正的证据只能来自**画面像素**。

做法：从 MJPEG 流里连续抓 N 帧（间隔 < 一个检测周期），
      在"车辆所在区域"统计**相邻帧的像素差**：
        · 若框静止，车辆区域内"框线"位置不变 -> 差异主要来自车辆纹理移动；
        · 若框跟随车辆平移，框线也在移动 -> 差异显著更大。
      同时取一个**画面静止区域**（天空/建筑）作为对照基线。

只读：不启动/停止检测（由调用方保证检测在跑）。
"""
import io
import sys
import time
import urllib.request

import numpy as np
import cv2

STREAM = 'http://127.0.0.1:8001/api/realtime/stream'
N = 10
GAP = 0.22          # 间隔 < 一个检测周期（当前约 378ms）


def grab_one(timeout=25):
    """从 MJPEG 流里读一帧（读到第一个 JPEG 结束标记即返回）"""
    req = urllib.request.Request(STREAM, headers={'User-Agent': 'dsh-probe'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        buf = b''
        while True:
            chunk = r.read(4096)
            if not chunk:
                break
            buf += chunk
            a = buf.find(b'\xff\xd8')          # JPEG SOI
            b = buf.find(b'\xff\xd9')          # JPEG EOI
            if a >= 0 and b > a:
                arr = np.frombuffer(buf[a:b + 2], np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                return img
    return None


frames = []
for i in range(N):
    t0 = time.time()
    f = grab_one()
    if f is None:
        print(f'第{i+1}帧抓取失败')
        break
    frames.append((time.time(), f))
    dt = time.time() - t0
    print(f'  帧{i+1}: {f.shape[1]}x{f.shape[0]}  抓取耗时 {dt*1000:.0f} ms')
    time.sleep(max(0.0, GAP - dt))

if len(frames) < 3:
    raise SystemExit('帧数不足，无法比较')

H, W = frames[0][1].shape[:2]
span = frames[-1][0] - frames[0][0]
print(f'\n共 {len(frames)} 帧，跨度 {span*1000:.0f} ms（平均间隔 {span/(len(frames)-1)*1000:.0f} ms）')
print('对比相邻帧的灰度绝对差（MAD）：')


def mad(a, b, roi=None):
    ga = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    if roi:
        x1, y1, x2, y2 = roi
        ga = ga[y1:y2, x1:x2]
        gb = gb[y1:y2, x1:x2]
    return float(np.mean(np.abs(ga.astype(np.int16) - gb.astype(np.int16))))


# 区域1：画面中部（车辆通行区，应含移动的车与框）
mid = (int(W * 0.35), int(H * 0.35), int(W * 0.75), int(H * 0.85))
# 区域2：画面上部（天空/远景，基本静止）作对照
top = (int(W * 0.35), 0, int(W * 0.75), int(H * 0.12))

mids, tops = [], []
for i in range(1, len(frames)):
    mids.append(mad(frames[i - 1][1], frames[i][1], mid))
    tops.append(mad(frames[i - 1][1], frames[i][1], top))

print(f'  车辆通行区 MAD: 均值 {np.mean(mids):6.2f}  中位 {np.median(mids):6.2f}  最大 {np.max(mids):6.2f}')
print(f'  静止对照区 MAD: 均值 {np.mean(tops):6.2f}  中位 {np.median(tops):6.2f}  最大 {np.max(tops):6.2f}')

print('\n判定：')
print(f'  · 画面在更新（帧间隔 {span/(len(frames)-1)*1000:.0f} ms < 检测周期 378 ms）'
      f' -> {"是" if span/(len(frames)-1) < 0.378 else "否"}')
ratio = np.mean(mids) / max(1e-6, np.mean(tops))
print(f'  · 通行区变化 / 静止区变化 = {ratio:.1f}x')
print(f'  · 通行区相邻帧确实在变 -> {"是" if np.mean(mids) > 1.0 else "否"}')
print('\n注：本判据证明"画面在两次检测之间持续变化"；')
print('    框跟随预测的**直接**证据见单元测试（6 个场景，box 平移量与预期一致）。')
