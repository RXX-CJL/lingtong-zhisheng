"""查明违规对象里到底有什么可用于归属的几何信息"""

import base64
import io
import json
import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

import cv2  # noqa: E402

from image_recognizer import multi_model_detect  # noqa: E402
from vehicle_tracker import VehicleTracker  # noqa: E402
from violation_rules import check_violations  # noqa: E402

VIDEO = r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"
tr = VehicleTracker(use_bytetrack=True)
cap = cv2.VideoCapture(VIDEO)
out = []
samples = 0
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
    vr = check_violations(dets)
    vs = vr.get("violations", [])
    if vs and samples < 2:
        samples += 1
        out.append(f"===== 第 {i} 帧违规样本 =====")
        out.append(f"车辆检测框（带 track_id 的）:")
        for d in dets:
            if d.get('class_name') in ('car', 'truck', 'bus', 'motorcycle', 'bicycle'):
                out.append(f"   class={d.get('class_name')} track_id={d.get('track_id')} "
                           f"bbox={[int(x) for x in (d.get('bbox') or [])]}")
        out.append(f"追踪车辆:")
        for tid, v in tracked.items():
            out.append(f"   ID{tid} {v.get('class_name')} bbox={[int(x) for x in (v.get('bbox') or [])]}")
        for v in vs[:3]:
            out.append(f"违规对象完整内容:")
            out.append("   " + json.dumps(v, ensure_ascii=False, default=str)[:700])
        out.append("")
cap.release()
if not out:
    out.append("150 帧内未产生违规")
io.open(r"E:\output\_viol_struct.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
