"""深挖 video 解码：为什么 app 里 cap.read() 会持续失败

对照实验：
  A. 顺序读全部 810 帧，记录第一次失败的位置
  B. 检查返回的 frame 是否为同一对象（OpenCV 复用缓冲区的已知行为）
  C. 大量帧连续处理后内存是否暴涨（判断缓冲/泄漏）
"""

import os
import sys
import time

import cv2
import numpy as np

VIDEO = r"E:\output\1\test_assets\traffic_videos\test1.mp4"

print("=" * 76)
print(f"OpenCV 版本: {cv2.__version__}")
print(f"文件: {VIDEO}  ({os.path.getsize(VIDEO)/1024/1024:.2f} MB)")
print("=" * 76)

cap = cv2.VideoCapture(VIDEO)
print("isOpened:", cap.isOpened())
print("FRAME_COUNT:", int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
print("FPS:", round(cap.get(cv2.CAP_PROP_FPS), 3))
print("WxH:", int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), "x", int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
print("FOURCC:", int(cap.get(cv2.CAP_PROP_FOURCC)), "BACKEND:", cap.getBackendName())

print()
print("--- A. 顺序读全部帧，找第一次失败位置 ---")
t0 = time.time()
ok = 0
first_fail = None
same_obj_count = 0
prev_id = None
max_mem = 0
for i in range(900):
    ret, frame = cap.read()
    if not ret:
        first_fail = i
        break
    ok += 1
    if prev_id is not None and id(frame) == prev_id:
        same_obj_count += 1
    prev_id = id(frame)
    if i % 200 == 0:
        import psutil
        mem = psutil.Process().memory_info().rss / 1024 / 1024
        max_mem = max(max_mem, mem)
        print(f"    frame {i:4d}: ok, rss={mem:.0f}MB")
elapsed = time.time() - t0
print(f"  成功帧数: {ok}   第一次失败于索引: {first_fail}   耗时 {elapsed:.1f}s")
print(f"  读取速率: {ok/elapsed:.1f} fps")
print(f"  相同对象引用次数: {same_obj_count}/{ok}  (OpenCV 复用缓冲区属正常)")
print(f"  峰值 RSS: {max_mem:.0f} MB")
cap.release()

print()
print("--- B. 失败后尝试 seek 回开头能否恢复 ---")
cap2 = cv2.VideoCapture(VIDEO)
for _ in range(15):
    cap2.read()
st_before = cap2.get(cv2.CAP_PROP_POS_FRAMES)
r1, _ = cap2.read()
print(f"  读到第 {st_before:.0f} 帧后继续读: ret={r1}")
cap2.set(cv2.CAP_PROP_POS_FRAMES, 0)
r2, f2 = cap2.read()
print(f"  seek 回 0 后再读: ret={r2}  shape={None if f2 is None else f2.shape}")
cap2.release()

print()
print("--- C. 结论 ---")
if first_fail is not None and first_fail < 100:
    print(f"  !! 解码在第 {first_fail} 帧后中断 —— 文件可能截断或编码异常")
else:
    print(f"  顺序读取完整（{ok} 帧），说明解码器本身可用")
    print("  => app 内失败原因需另找：可能是多次 VideoCapture 并发/资源竞争")
