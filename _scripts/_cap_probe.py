"""对照实验：解释 app 内 cap.read() 持续失败的原因

实验：
  1. release() 之后 read() 是否永远返回 False（并确认 isOpened 状态）
  2. 同一个文件被两个 VideoCapture 同时打开，是否互相干扰
  3. set_source 持锁调用 start_camera 是否会死锁（Lock vs RLock）
"""

import threading
import time

import cv2

VIDEO = r"E:\output\1\test_assets\traffic_videos\test1.mp4"

print("=" * 76)
print("实验 1：release() 后 read() 的行为")
print("=" * 76)
cap = cv2.VideoCapture(VIDEO)
print("  打开后 isOpened:", cap.isOpened())
r, _ = cap.read()
print("  释放前 read:", r)
cap.release()
print("  释放后 isOpened:", cap.isOpened())
fails = 0
for _ in range(5):
    rr, _ = cap.read()
    if not rr:
        fails += 1
print(f"  释放后连续 5 次 read 失败次数: {fails}/5")
print("  => 结论:", "release 后 read 永久 False ✅ 与现象一致" if fails == 5 else "release 后仍可读")

print()
print("=" * 76)
print("实验 2：同文件双开是否互相干扰")
print("=" * 76)
a = cv2.VideoCapture(VIDEO)
n_a1 = sum(1 for _ in range(20) if a.read()[0])
print(f"  capA 先读 20 帧成功: {n_a1}")
b = cv2.VideoCapture(VIDEO)
n_b = sum(1 for _ in range(20) if b.read()[0])
print(f"  capB（第二个实例）读 20 帧成功: {n_b}")
n_a2 = sum(1 for _ in range(20) if a.read()[0])
print(f"  capB 打开后 capA 再读 20 帧成功: {n_a2}")
a.release()
b.release()
print("  => 结论:", "双开互不影响" if n_b == 20 and n_a2 == 20 else "!! 双开有干扰")

print()
print("=" * 76)
print("实验 3：Lock 是否可重入（决定 set_source -> start_camera 是否死锁）")
print("=" * 76)
lk = threading.Lock()
got = []


def try_reenter():
    with lk:
        got.append("outer")
        # 模拟 start_camera 再次 with self.lock
        acquired = lk.acquire(timeout=2.0)
        got.append(f"inner_acquired={acquired}")
        if acquired:
            lk.release()


t = threading.Thread(target=try_reenter, daemon=True)
t.start()
t.join(timeout=4)
print("  普通 Lock 重入结果:", got)
print("  => 结论:", "不可重入（会死锁）" if "inner_acquired=False" in got else "可重入")

print()
print("  --- 检查项目里 self.lock 的类型 ---")
src = open(r"E:\output\1\api\realtime_detector.py", encoding="utf-8").read()
import re
for m in re.finditer(r"self\.lock\s*=\s*[^\n]+", src):
    print("   ", m.group(0).strip())
for m in re.finditer(r"self\.process_lock\s*=\s*[^\n]+", src):
    print("   ", m.group(0).strip())
