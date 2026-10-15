"""直接检查事件视频：里面到底有没有车？车在第几帧？

针对 AI 说"画面中无任何车辆"的事件，把它的事件视频抽帧出来，
用 YOLO 检测每帧有几辆车，定位车出现的时间段。
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
VID = r"E:\output\1\api\output\event_videos\20261006\evt_11050_1_1cf14d.mp4"
SRC = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"


def main():
    from ultralytics import YOLO
    m = YOLO(r"E:\output\1\zhitong\training\models\yolov8s.pt")

    print("=== 源视频（全程 520 帧）里车出现的时段 ===")
    cap = cv2.VideoCapture(SRC)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    hits = []
    for f in range(0, n, 20):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, fr = cap.read()
        if not ok:
            continue
        r = m.predict(fr, imgsz=960, conf=0.25, verbose=False, device=0)[0]
        cars = sum(1 for b in (r.boxes or [])
                   if m.names[int(b.cls[0])] in ("car", "truck", "bus", "motorcycle"))
        hits.append((f, cars))
    cap.release()
    print("   帧号(每20帧抽样) -> 车辆数")
    line = []
    for f, c in hits:
        line.append("%d:%d" % (f, c))
    for i in range(0, len(line), 13):
        print("     " + "  ".join(line[i:i + 13]))

    print("\n=== 事件视频 %s ===" % os.path.basename(VID))
    if not os.path.exists(VID):
        print("   不存在")
        return 1
    cap = cv2.VideoCapture(VID)
    en = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print("   共 %d 帧" % en)
    res = []
    for f in range(0, en, 10):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, fr = cap.read()
        if not ok:
            continue
        r = m.predict(fr, imgsz=960, conf=0.25, verbose=False, device=0)[0]
        cars = sum(1 for b in (r.boxes or [])
                   if m.names[int(b.cls[0])] in ("car", "truck", "bus", "motorcycle"))
        res.append((f, cars))
    cap.release()
    for f, c in res:
        print("   帧 %-4d 车辆数=%d %s" % (f, c, "  <== 有车" if c else ""))
    total_with = sum(1 for _, c in res if c)
    print("\n   含车的抽样帧: %d / %d" % (total_with, len(res)))
    if total_with == 0:
        print("   !! 事件视频里确实没有车 -> 取帧窗口错了")
    else:
        print("   -> 事件视频里有车，AI 说\"无车\"是它自己没看出来")
    return 0


if __name__ == "__main__":
    sys.exit(main())
