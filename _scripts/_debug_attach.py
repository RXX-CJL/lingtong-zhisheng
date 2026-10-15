"""直接调试 _attach_track_ids，逐步打印决策"""

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
cap = cv2.VideoCapture(VIDEO)
out = []
logged = 0
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
    if tracked and logged < 2:
        logged += 1
        out.append(f"===== 帧 {i} =====")
        out.append(f"tracked_vehicles: {len(tracked)} 辆")
        for tid, v in tracked.items():
            out.append(f"   ID{tid} bbox={[round(x,1) for x in (v.get('bbox') or [])]}")
        out.append(f"detections 中的车辆: ")
        for d in dets:
            if d.get('class_name') in ('car', 'truck', 'bus', 'motorcycle', 'bicycle'):
                out.append(f"   {d.get('class_name')} bbox={[round(float(x),1) for x in (d.get('bbox') or [])]} track_id={d.get('track_id')}")
        det._attach_track_ids(dets)
        out.append(f"回填后:")
        for d in dets:
            if d.get('class_name') in ('car', 'truck', 'bus', 'motorcycle', 'bicycle'):
                out.append(f"   {d.get('class_name')} bbox={[round(float(x),1) for x in (d.get('bbox') or [])]} track_id={d.get('track_id')}")
        vr = check_violations(dets)
        for v in vr.get("violations", [])[:2]:
            out.append(f"违规 {v.get('violation_type')} vehicle_id={v.get('vehicle_id')} loc={v.get('location')}")
        out.append("")
cap.release()
io.open(r"E:\output\_attach_dbg.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
