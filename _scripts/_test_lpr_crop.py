"""验证"车辆框裁剪后再识别车牌"（这是正确的接入方式）

思路：全图上远距离车牌只有几十像素 -> hyperlpr3 检不到；
      先把车辆框裁出来放大，再送识别，成功率应显著提高。
同时屏蔽 numpy 2.x 的 RuntimeWarning 干扰。
"""

import os
import sys
import time
import warnings

import numpy as np
warnings.filterwarnings("ignore")
np.seterr(all="ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402
import hyperlpr3 as lpr3  # noqa: E402
from ultralytics import YOLO  # noqa: E402

catcher = lpr3.LicensePlateCatcher()
m = YOLO(r"E:\output\1\zhitong\training\models\yolov8s.pt")

VIDEOS = [
    r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4",
    r"E:\output\1\test_assets\traffic_videos\701c5154f47975564a8039bb03bd3340.mp4",
]
print("=" * 74)
print("车辆框裁剪后识别车牌")
print("=" * 74)
hits = 0
tried = 0
for vp in VIDEOS:
    cap = cv2.VideoCapture(vp)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"\n{os.path.basename(vp)[:16]} ({n} 帧)")
    for fi in range(0, n, max(1, n // 5)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        r = m.predict(frame, imgsz=1280, conf=0.3, verbose=False, device=0)[0]
        vehs = []
        for b in (r.boxes or []):
            cn = r.names.get(int(b.cls[0])) if isinstance(r.names, dict) else r.names[int(b.cls[0])]
            if str(cn).lower() in ("car", "truck", "bus", "motorcycle"):
                x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
                if (x2 - x1) >= 60 and (y2 - y1) >= 50:
                    vehs.append((x1, y1, x2, y2, str(cn)))
        # 取最大的 3 辆车
        vehs.sort(key=lambda v: -(v[2] - v[0]) * (v[3] - v[1]))
        found_here = []
        for (x1, y1, x2, y2, cn) in vehs[:3]:
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue
            tried += 1
            # 放大 2 倍提高小字符可读性
            big = cv2.resize(crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            try:
                res = catcher(big)
                for it in (res or []):
                    try:
                        found_here.append(f"{it[0]}({float(it[1]):.2f})")
                    except Exception:
                        pass
            except Exception:
                pass
        if found_here:
            hits += len(found_here)
            print(f"  帧{fi:4d}: 车牌 {', '.join(found_here)}")
        else:
            print(f"  帧{fi:4d}: 车辆框 {len(vehs[:3])} 个，无车牌")
    cap.release()

print()
print("=" * 74)
print(f"尝试车辆框: {tried}   检出车牌: {hits}")
print("结论:", "✅ 裁剪放大后可识别" if hits else
      "⚠ 仍未检出：这批视频分辨率下车辆过小，车牌像素不足")
print("=" * 74)
