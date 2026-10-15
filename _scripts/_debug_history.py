"""查明 history[].center 的真实数值序列（为何 vec 与 direction 矛盾）"""

import base64
import os
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402

from image_recognizer import multi_model_detect  # noqa: E402
from vehicle_tracker import VehicleTracker  # noqa: E402

VIDEO = r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"
cap = cv2.VideoCapture(VIDEO)
tracker = VehicleTracker()
tracked = {}
for i in range(60):
    ok, f = cap.read()
    if not ok:
        break
    if i % 3:
        continue
    _, buf = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 80])
    url = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
    r = multi_model_detect(url, conf_threshold=0.35)
    dets = r.get("all_detections", []) if r.get("success") else []
    h, w = f.shape[:2]
    tracked = tracker.update(dets, w, h)
cap.release()

print("=" * 78)
print("history 里 center 的完整序列")
print("=" * 78)
for tid, v in list(tracked.items())[:3]:
    hist = v.get("history") or []
    print(f"\nID{tid}  class={v.get('class_name')}  direction={v.get('direction')}")
    print(f"  bbox={[int(x) for x in (v.get('bbox') or [])]}  speed={v.get('speed')}")
    print(f"  history 长度={len(hist)}")
    for j, hh in enumerate(hist):
        c = hh.get("center")
        print(f"    [{j:>2}] center={c}  ts={round(float(hh.get('timestamp',0)),3)}  "
              f"dx={hh.get('dx')} dy={hh.get('dy')}")
    if hist:
        c0 = hist[0].get("center"); cN = hist[-1].get("center")
        print(f"  首尾位移: dx={cN[0]-c0[0]:.1f}  dy={cN[1]-c0[1]:.1f}")

print()
print("=" * 78)
print("VehicleTracker 的 _calculate_direction 实现")
print("=" * 78)
import inspect  # noqa: E402
from vehicle_tracker import VehicleTracker as VT  # noqa: E402
try:
    print(inspect.getsource(VT._calculate_direction))
except Exception as e:
    print("取源码失败:", e)
