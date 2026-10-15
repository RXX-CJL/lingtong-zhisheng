"""直接回答「颜色差异会不会影响 YOLO」：用项目自带的 YOLO 跑三条链路的同一内容，
比较检出数量与置信度。
  A 项目在线画面（PNG 代表帧，无损、后处理开）
  B 视频帧（mp4v，有损）
  C 关掉后处理的画面（对照，看 YOLO 是否更差）
"""
import glob
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
SCENE = r"E:\output\_demo_scene"
PP = r"E:\output\_camera_check"


def run(model, img, tag):
    res = model.predict(img, verbose=False, conf=0.25)
    out = []
    for r in res:
        if r.boxes is None:
            continue
        for b in r.boxes:
            cls = int(b.cls[0])
            out.append((model.names.get(cls, str(cls)), float(b.conf[0]),
                        [round(float(v), 1) for v in b.xyxy[0].tolist()]))
    out.sort(key=lambda t: -t[1])
    return out


def main():
    from ultralytics import YOLO
    wpath = r"E:\output\1\zhitong\training\models\yolov8s.pt"
    model = YOLO(wpath)
    print("模型:", wpath)

    def show(tag, img):
        dets = run(model, img, tag)
        veh = [d for d in dets if d[0] in ("car", "truck", "bus", "motorcycle", "bicycle", "person")]
        print("\n%-46s 总检出=%d  车辆/人类=%d" % (tag, len(dets), len(veh)))
        for name, conf, box in veh[:6]:
            print("     %-10s conf=%.3f  box=%s" % (name, conf, box))
        return len(veh), max([d[1] for d in veh], default=0.0)

    # A: PNG 代表帧
    for fn in ("frame_220.png", "frame_260.png"):
        p = os.path.join(SCENE, fn)
        if os.path.exists(p):
            show("A PNG %s (无损/后处理开)" % fn, cv2.imread(p))

    # B: 视频同帧
    vid = os.path.join(SCENE, "red_light_demo.mp4")
    if os.path.exists(vid):
        cap = cv2.VideoCapture(vid)
        for f in (220, 260):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, img = cap.read()
            if ok:
                show("B 视频帧 %d (mp4v 有损)" % f, img)
        cap.release()

    # C: 后处理关闭的对照
    for fn in ("pp_pp_on.png", "pp_pp_off.png"):
        p = os.path.join(PP, fn)
        if os.path.exists(p):
            show("C %s" % fn, cv2.imread(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
