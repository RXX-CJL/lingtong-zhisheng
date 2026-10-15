"""坐实：触发时刻那一帧到底有没有车 + 车真正越线的时刻。

回答两个问题：
  1. 源视频 11.05 秒（帧 221）那一帧有没有车？
     - 有 -> 触发时刻没错，是 AI 看漏
     - 无 -> 触发时刻错了（规则在没车时误触发），要查几何参数
  2. 车真正越过停止线（x < -25.61）是视频第几秒？
"""
import sys

import cv2

sys.path.insert(0, r"E:\output\1\api")
SRC = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"


def main():
    from ultralytics import YOLO
    m = YOLO(r"E:\output\1\zhitong\training\models\yolov8s.pt")
    cap = cv2.VideoCapture(SRC)
    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0

    print("=== 1) 逐 10 帧找「首次出现车」的时刻 ===")
    first = None
    for f in range(0, 520, 10):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, fr = cap.read()
        if not ok:
            continue
        r = m.predict(fr, imgsz=960, conf=0.25, verbose=False, device=0)[0]
        cars = [b for b in (r.boxes or [])
                if m.names[int(b.cls[0])] in ("car", "truck", "bus")]
        if cars:
            if first is None:
                first = f
                print("   首次有车: 帧 %d = 视频 %.2f 秒" % (f, f / fps))
                for b in cars[:3]:
                    x1, y1, x2, y2 = [float(v) for v in b.xyxy[0].tolist()]
                    print("      车 bbox=(%.0f,%.0f,%.0f,%.0f) conf=%.2f"
                          % (x1, y1, x2, y2, float(b.conf[0])))
            break

    print("\n=== 2) 触发时刻附近逐帧看（视频 10.0~12.0 秒）===")
    print("   %-8s %-10s %-8s %s" % ("帧号", "视频秒", "车辆数", "备注"))
    for f in range(int(10.0 * fps), int(12.0 * fps) + 1, 4):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, fr = cap.read()
        if not ok:
            continue
        r = m.predict(fr, imgsz=960, conf=0.25, verbose=False, device=0)[0]
        cars = [b for b in (r.boxes or [])
                if m.names[int(b.cls[0])] in ("car", "truck", "bus")]
        note = ""
        if f == 221:
            note = "<== 事件 evt_11050 的触发帧"
        print("  %-8d %-10.2f %-8d %s" % (f, f / fps, len(cars), note))
        for b in cars[:2]:
            x1, y1, x2, y2 = [float(v) for v in b.xyxy[0].tolist()]
            print("        车 bbox=(%.0f,%.0f,%.0f,%.0f) conf=%.2f"
                  % (x1, y1, x2, y2, float(b.conf[0])))

    cap.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
