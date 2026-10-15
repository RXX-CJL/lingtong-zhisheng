"""端到端验证：真实检测 -> ByteTrack 追踪 -> 违规是否带 vehicle_id"""

import base64
import io
import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

import cv2  # noqa: E402

from image_recognizer import multi_model_detect  # noqa: E402
from realtime_detector import realtime_detector as det  # noqa: E402
from vehicle_tracker import VehicleTracker  # noqa: E402
from violation_rules import check_violations  # noqa: E402

VIDEO = r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"

tr = VehicleTracker(use_bytetrack=True)
out = []
cap = cv2.VideoCapture(VIDEO)
n_with_id = n_total = 0
last = []
tracked = {}
for i in range(150):
    ok, f = cap.read()
    if not ok:
        break
    _, buf = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 80])
    url = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
    r = multi_model_detect(url, conf_threshold=0.35)
    dets = r.get("all_detections", []) if r.get("success") else []
    h, w = f.shape[:2]
    tracked = tr.update(dets, w, h)
    det.tracked_vehicles = tracked
    det._attach_track_ids(dets)
    vr = check_violations(dets)
    vs = vr.get("violations", [])
    n_total += len(vs)
    n_with_id += len([v for v in vs if v.get("vehicle_id") is not None])
    if vs:
        last = [(v.get("violation_type"), v.get("vehicle_id"),
                 round(float(v.get("confidence", 0) or 0), 2)) for v in vs]
cap.release()

out.append(f"跑了 150 帧，累计违规 {n_total} 条，其中带 vehicle_id {n_with_id} 条")
if n_total:
    out.append(f"带 ID 比例: {n_with_id / n_total * 100:.0f}%")
out.append(f"最后一批违规 (类型, vehicle_id, 置信度): {last[:8]}")
out.append(f"最终追踪车辆数: {len(tracked)}")
for tid, v in list(tracked.items())[:5]:
    out.append(f"   ID{tid} {v.get('class_name')} bbox={[int(x) for x in (v.get('bbox') or [])]}")
io.open(r"E:\output\_vid_check.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
