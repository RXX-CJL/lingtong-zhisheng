"""探查：违规对象与追踪车辆的真实字段形态（用于设计映射逻辑）"""

import json
import os
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8001"
VIDEO = r"E:\output\1\test_assets\traffic_videos\test1.mp4"


def call(method, path, body=None, timeout=60):
    req = urllib.request.Request(BASE + path,
                                 data=json.dumps(body).encode() if body else None,
                                 method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


print("启动检测...")
print(call("POST", "/api/realtime/start", {"video_path": VIDEO}))
time.sleep(20)

print()
print("=" * 74)
print("追踪车辆字段（前 3 辆）")
print("=" * 74)
st = call("GET", "/api/realtime/tracked-vehicles")
vehicles = st.get("data") or st
if isinstance(vehicles, dict):
    vehicles = vehicles.get("vehicles") or list(vehicles.values())
print(f"  车辆数: {len(vehicles) if vehicles else 0}")
for v in (vehicles or [])[:3]:
    if isinstance(v, dict):
        keys = {k: (str(val)[:30] if not isinstance(val, (list, dict)) else type(val).__name__)
                for k, val in v.items()}
        print(f"  {json.dumps(keys, ensure_ascii=False)}")

print()
print("=" * 74)
print("最新检测结果里的违规对象结构")
print("=" * 74)
# 通过 status 拿不到违规详情，改从 uploads 里的证据图存在性推断；
# 用 detect-frame 主动推一帧，观察返回结构
import base64  # noqa: E402

import cv2  # noqa: E402

cap = cv2.VideoCapture(VIDEO)
ok, frame = False, None
for _ in range(40):
    ok, frame = cap.read()
    if ok:
        break
cap.release()
if ok:
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    b64 = base64.b64encode(buf.tobytes()).decode()
    r = call("POST", "/api/realtime/detect-frame", {"frame": b64}, timeout=120)
    d = r.get("data", r)
    print("  返回顶层字段:", list(d.keys())[:20] if isinstance(d, dict) else type(d))
    for k in ("detections", "violations", "behaviors", "tracked_vehicles"):
        v = d.get(k) if isinstance(d, dict) else None
        if v:
            print(f"\n  --- {k}: {len(v)} 项，首项字段 ---")
            first = v[0] if isinstance(v, list) else list(v.values())[0]
            if isinstance(first, dict):
                print("     ", json.dumps({kk: (str(vv)[:40] if not isinstance(vv, (list, dict))
                                              else type(vv).__name__)
                                           for kk, vv in first.items()}, ensure_ascii=False))

print()
print(call("POST", "/api/realtime/stop"))
