"""抓帧确认各摄像头内容（识别是否为虚拟摄像头/手机投屏）"""

import io
import os

import cv2
import numpy as np

OUT_DIR = r"E:\output\_screens"
os.makedirs(OUT_DIR, exist_ok=True)
out = []

TARGETS = [(0, "default"), (1, "DSHOW"), (2, "DSHOW"), (3, "DSHOW")]
for idx, be in TARGETS:
    cap = None
    try:
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW) if be == "DSHOW" else cv2.VideoCapture(idx)
        if not cap.isOpened():
            out.append(f"[{idx}/{be}] 打不开")
            continue
        # 丢几帧让曝光稳定
        for _ in range(5):
            cap.read()
        ok, frame = cap.read()
        if not ok or frame is None:
            out.append(f"[{idx}/{be}] 读帧失败")
            continue
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean = float(gray.mean())
        std = float(gray.std())
        # 纯黑/纯色通常表示虚拟设备未推流
        blank = std < 3.0
        p = os.path.join(OUT_DIR, f"cam_{idx}_{be}.jpg")
        cv2.imwrite(p, frame)
        out.append(f"[{idx}/{be}] {w}x{h}  灰度均值={mean:.1f} 标准差={std:.1f}  "
                   f"{'疑似空画面' if blank else '有内容'}  -> {os.path.basename(p)}")
    except Exception as e:
        out.append(f"[{idx}/{be}] 异常: {type(e).__name__}: {str(e)[:70]}")
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

io.open(r"E:\output\_camera_frames.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
