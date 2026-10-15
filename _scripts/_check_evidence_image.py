"""测 AI 实际收到的证据图：里面有没有车？

对比：
  * 证据图（uploads/realtime_*.jpg）—— AI 看的就是它
  * 源视频同一时刻的帧 —— 应该有车
若源视频有车而证据图无车 -> 保存证据这一环出错（丢帧/取错帧）
"""
import glob
import os
import sys

import cv2

sys.path.insert(0, r"E:\output\1\api")
SRC = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"


def count_cars(m, img):
    r = m.predict(img, imgsz=960, conf=0.25, verbose=False, device=0)[0]
    out = []
    for b in (r.boxes or []):
        nm = m.names[int(b.cls[0])]
        if nm in ("car", "truck", "bus", "motorcycle"):
            x1, y1, x2, y2 = [float(v) for v in b.xyxy[0].tolist()]
            out.append((nm, round(float(b.conf[0]), 2), [round(x1), round(y1), round(x2), round(y2)]))
    return out


def main():
    from ultralytics import YOLO
    m = YOLO(r"E:\output\1\zhitong\training\models\yolov8s.pt")

    print("=== A) AI 收到的证据图 ===")
    fs = sorted(glob.glob(r"E:\output\1\api\uploads\realtime_*"),
                key=os.path.getmtime, reverse=True)[:3]
    for f in fs:
        im = cv2.imread(f)
        if im is None:
            continue
        h, w = im.shape[:2]
        print("\n%s  (%dx%d)" % (os.path.basename(f), w, h))
        # 整图
        cars = count_cars(m, im)
        print("   整图检测到车辆: %d 辆  %s" % (len(cars), cars[:3]))
        # 若为 3 联图，分栏看
        if w >= 1800:
            third = w // 3
            for k in range(3):
                sub = im[:, k * third:(k + 1) * third]
                c2 = count_cars(m, sub)
                print("   第%d栏 %dx%d -> 车辆 %d 辆 %s"
                      % (k + 1, sub.shape[1], sub.shape[0], len(c2), c2[:2]))

    print("\n=== B) 源视频 11.0 秒那一帧（应有车）===")
    cap = cv2.VideoCapture(SRC)
    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(11.0 * fps))
    ok, fr = cap.read()
    cap.release()
    if ok:
        cars = count_cars(m, fr)
        print("   源视频帧检测到车辆: %d 辆" % len(cars))
        for c in cars[:4]:
            print("      %s conf=%.2f bbox=%s" % c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
