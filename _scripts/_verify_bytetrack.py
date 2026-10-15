"""验证 ByteTrack 追踪质量（对比之前的质心追踪乱轨迹）"""

import base64
import os
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402

from annotation_renderer import _direction_vector  # noqa: E402
from image_recognizer import multi_model_detect  # noqa: E402
from vehicle_tracker import VehicleTracker  # noqa: E402

VIDEO = r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"
OUT = r"E:\output\_screens"

tr = VehicleTracker(use_bytetrack=True)
print(f"使用追踪器: {type(tr.tracker).__name__}  available={getattr(tr.tracker,'available','?')}")

cap = cv2.VideoCapture(VIDEO)
tracked = {}
frame = None
frames_run = 0
jumps = []
for i in range(160):
    ok, f = cap.read()
    if not ok:
        break
    frames_run += 1
    # 每帧都检测（ByteTrack 需要连续帧才能发挥关联能力）
    _, buf = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 80])
    url = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
    r = multi_model_detect(url, conf_threshold=0.35)
    dets = r.get("all_detections", []) if r.get("success") else []
    h, w = f.shape[:2]
    prev = {k: list(v.get("center") or []) for k, v in tracked.items()}
    tracked = tr.update(dets, w, h)
    # 统计帧间跳变
    for tid, v in tracked.items():
        c = v.get("center")
        if tid in prev and prev[tid] and c:
            d = ((c[0] - prev[tid][0]) ** 2 + (c[1] - prev[tid][1]) ** 2) ** 0.5
            jumps.append(d)
    frame = f
cap.release()

print(f"跑了 {frames_run} 帧（每帧检测），最终追踪 {len(tracked)} 辆车")
print()
print("=" * 78)
print("追踪轨迹（真实数据）")
print("=" * 78)
for tid, v in sorted(tracked.items())[:10]:
    hist = v.get("history") or []
    vec = _direction_vector(v)
    c0 = hist[0].get("center") if hist else None
    cN = hist[-1].get("center") if hist else None
    print(f"  ID{tid:>3} {str(v.get('class_name')):10s} hist={len(hist):>3} "
          f"speed={float(v.get('speed') or 0):7.2f}px/s dir={str(v.get('direction')):11s}")
    print(f"        首={c0} 尾={cN}  vec={None if vec is None else tuple(round(x,2) for x in vec)}")

if jumps:
    jumps_sorted = sorted(jumps)
    n = len(jumps_sorted)
    print()
    print("=" * 78)
    print("帧间位移统计（衡量轨迹平滑度）")
    print("=" * 78)
    print(f"  样本数: {n}")
    print(f"  中位: {jumps_sorted[n//2]:.1f}px   均值: {sum(jumps)/n:.1f}px")
    print(f"  P90 : {jumps_sorted[int(n*0.9)]:.1f}px   P99: {jumps_sorted[int(n*0.99)]:.1f}px   最大: {jumps_sorted[-1]:.1f}px")
    big = sum(1 for j in jumps if j > 60)
    print(f"  >60px 的跳变: {big} 次 ({big/n*100:.1f}%)   ← 越低越稳（之前质心追踪大量 ±70px 跳变）")

if frame is not None:
    p = os.path.join(OUT, "bytetrack_real.png")
    cv2.imwrite(p, frame)
    print(f"\n  帧已存: {p}")
