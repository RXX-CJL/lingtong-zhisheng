"""真实验证：用实际检测结果渲染，不造任何数据

流程：
  1. 从视频取一帧
  2. 跑真实 YOLO 检测（imgsz=1280）
  3. 跑真实追踪（vehicle_tracker）
  4. 跑真实违规判定（check_violations）
  5. 用真实结果渲染（箭头方向来自真实轨迹）
  6. 输出：检出框数 / 轨迹点数 / 方向向量 / 违规项
"""

import os
import sys
import time

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import base64  # noqa: E402

import cv2  # noqa: E402

from annotation_renderer import AnnotationRenderer, _direction_vector  # noqa: E402
from image_recognizer import multi_model_detect  # noqa: E402
from vehicle_tracker import VehicleTracker  # noqa: E402
from violation_rules import check_violations  # noqa: E402

VIDEO = r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"
OUT = r"E:\output\_screens"

cap = cv2.VideoCapture(VIDEO)
frame = None
# 取一段连续帧，让追踪器积累轨迹（这样方向才有依据）
tracker = VehicleTracker()
detections = []
frame_idx = 0
for i in range(60):
    ok, f = cap.read()
    if not ok:
        break
    frame_idx = i
    if i % 3 != 0:      # 每 3 帧检测一次（模拟实时节流）
        continue
    _, buf = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 80])
    data_url = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
    r = multi_model_detect(data_url, conf_threshold=0.35)
    dets = r.get("all_detections", []) if r.get("success") else []
    h, w = f.shape[:2]
    tracked = tracker.update(dets, w, h)
    detections = dets
    frame = f

cap.release()
print(f"取到帧序号 {frame_idx}，尺寸 {frame.shape if frame is not None else None}")
print(f"最终检测框数: {len(detections)}")
print(f"追踪车辆数: {len(tracked)}")

print()
print("=" * 78)
print("真实追踪车辆（含轨迹与方向）")
print("=" * 78)
for tid, v in list(tracked.items())[:10]:
    hist = v.get("history") or []
    vec = _direction_vector(v)
    print(f"  ID{tid:>3} {str(v.get('class_name')):10s} bbox={[int(x) for x in (v.get('bbox') or [])]} "
          f"hist={len(hist):>2} speed={float(v.get('speed') or 0):6.2f}px/s "
          f"dir={str(v.get('direction')):11s} vec={None if vec is None else tuple(round(x,2) for x in vec)}")

print()
print("=" * 78)
print("真实违规判定")
print("=" * 78)
vr = check_violations(detections)
violations = vr.get("violations", [])
print(f"  违规数: {len(violations)}")
for v in violations[:6]:
    print(f"    type={v.get('violation_type')} cn={v.get('violation_type_cn')} "
          f"conf={v.get('confidence')} vehicle_id={v.get('vehicle_id')} "
          f"loc={v.get('location')}")

# 渲染
r = AnnotationRenderer(font_size=18)
out = r.render(frame.copy(), detections, tracked, violations, [], {})
p = os.path.join(OUT, "real_detection.png")
cv2.imwrite(p, out)
print()
print(f"真实渲染输出: {p}")
print(f"渲染耗时: {r.last_render_ms:.1f}ms")
