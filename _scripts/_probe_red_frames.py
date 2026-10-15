"""查红灯期：YOLO 报的红绿灯框交给判色器后为什么全被丢成 none。

取演示视频红灯期（帧 0-299）的若干帧，列出每个 traffic light 框的
bbox / 尺寸 / CNN4 判定 / 发光区定位结果。
"""
import sys
import traceback

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
from realtime_detector import RealtimeViolationDetector  # noqa: E402
from traffic_light_classifier import (classify_traffic_light, find_glow_region,
                                      classify_with_glow)  # noqa: E402

VIDEO = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"
PROBE = [10, 100, 180, 200, 250, 290, 320, 350, 420, 480]


def main():
    det = RealtimeViolationDetector()
    cap = cv2.VideoCapture(VIDEO)
    print("真值相位: 0-299=Red  300-399=Green  400-499=Yellow  500+=Red\n")
    for i in PROBE:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, frame = cap.read()
        if not ok:
            continue
        dets = det._yolo_detect(frame)
        tls = [d for d in dets if (d.get("class_name") or "").lower() in
               ("traffic light", "traffic_light")]
        print("帧 %-4d  traffic light 框数=%d" % (i, len(tls)))
        for k, d in enumerate(tls):
            x1, y1, x2, y2 = [int(v) for v in d["bbox"][:4]]
            H, W = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(W, x2), min(H, y2)
            if x2 - x1 < 4 or y2 - y1 < 4:
                print("     #%d 框太小 (%d,%d,%d,%d)" % (k, x1, y1, x2, y2))
                continue
            roi = frame[y1:y2, x1:x2]
            cnn, conf = classify_traffic_light(roi)
            gl = find_glow_region(roi)
            st2, c2, info = classify_with_glow(roi)
            # ROI 的亮度/色度概况
            g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            b, gg, r = [float(roi[:, :, c].mean()) for c in range(3)]
            print("     #%d bbox=(%4d,%4d,%4d,%4d) %2dx%-3d conf=%.2f | CNN=%-8s %.2f | glow=%s | %s"
                  % (k, x1, y1, x2, y2, x2 - x1, y2 - y1, d["confidence"], cnn, conf,
                     "无" if gl is None else "%dx%d peak=%.0f" % (gl["w"], gl["h"], gl["peak"]),
                     st2))
            print("         ROI 均值 BGR=(%.0f,%.0f,%.0f)  灰度峰值=%d" % (b, gg, r, int(g.max())))
        print()
    cap.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
