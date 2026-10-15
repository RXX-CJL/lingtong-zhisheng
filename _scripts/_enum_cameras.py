"""枚举本机可用摄像头（Windows/DirectShow + 默认后端）"""

import io
import os
import time

import cv2

out = []
out.append(f"OpenCV {cv2.__version__}")
out.append("")

# 方案1：DirectShow 枚举 0-5
out.append("=== DirectShow 后端 (CAP_DSHOW) ===")
found = []
for idx in range(5):
    t0 = time.time()
    cap = None
    try:
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None:
                h, w = frame.shape[:2]
                found.append((idx, "DSHOW", w, h))
                out.append(f"  [{idx}] 可用  {w}x{h}  读取耗时 {(time.time()-t0)*1000:.0f}ms")
            else:
                out.append(f"  [{idx}] 打开成功但读不到帧")
        else:
            out.append(f"  [{idx}] 不可用")
    except Exception as e:
        out.append(f"  [{idx}] 异常: {type(e).__name__}: {str(e)[:70]}")
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

out.append("")
out.append("=== 默认后端 (MSMF) ===")
for idx in range(3):
    cap = None
    try:
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None:
                h, w = frame.shape[:2]
                if not any(f[0] == idx for f in found):
                    found.append((idx, "MSMF", w, h))
                out.append(f"  [{idx}] 可用  {w}x{h}")
            else:
                out.append(f"  [{idx}] 打开成功但读不到帧")
        else:
            out.append(f"  [{idx}] 不可用")
    except Exception as e:
        out.append(f"  [{idx}] 异常: {type(e).__name__}")
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

out.append("")
out.append(f"结论: 发现 {len(found)} 个可用摄像头 {found}")
io.open(r"E:\output\_cameras.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
