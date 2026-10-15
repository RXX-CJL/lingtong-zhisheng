"""直接检查我录制的视频里红绿灯的真实样子（用户说"有亮灭区别"）

用户原话：
  "一共三个灯珠，最上面黄灯下面绿灯，中间红灯，而且有亮灭区别，为什么不能用？"

我录的 carla_simple_28s.mp4 有精确的灯态真值：
  t=0.00  Green    t=4.05  Red    t=15.45 Green -> 15.50 Red    t=25.45 Yellow -> 25.50 Red

本脚本：
  ① 在【Green 帧】和【Red 帧】各裁一张灯区域的高清放大图
  ② 逐像素比较两张图的差异
  ③ 输出并排对比图 —— 直接看"绿灯时是不是绿的、红灯时是不是红的"
"""

import glob
import io
import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

import cv2
import numpy as np
from ultralytics import YOLO

OUT = r"E:\output\_tl_review"
os.makedirs(OUT, exist_ok=True)
out = []

VIDEO = r"E:\output\_carla_video3\carla_simple_28s.mp4"
# 真值：第 10 帧(0.5s)=Green, 第 480 帧(24s)=Red（4.05s 后一直红，直到 15.45 短暂绿）
GREEN_FRAME = 10
RED_FRAME = 400      # 20s，处于 4.05~15.45 之外？-> 15.45~15.50 绿，之后红。20s 应为红
out.append(f"真值: 帧{GREEN_FRAME}(t={GREEN_FRAME/20:.2f}s)=Green   "
           f"帧{RED_FRAME}(t={RED_FRAME/20:.2f}s)=Red")

ws = glob.glob(r"E:\output\1\**\yolov8n.pt", recursive=True) or glob.glob(r"E:\output\*.pt")
model = YOLO(ws[0])
out.append(f"权重: {os.path.basename(ws[0])}")


def crop_lights(frame, label, save_prefix):
    """用 YOLO 找红绿灯框，裁出来放大"""
    r = model.predict(frame, conf=0.2, imgsz=1280, verbose=False)[0]
    names = r.names
    tiles = []
    infos = []
    for bx in r.boxes:
        if names[int(bx.cls)] != "traffic light":
            continue
        x1, y1, x2, y2 = [int(v) for v in bx.xyxy[0].tolist()]
        conf = float(bx.conf)
        # 扩边 40%（要把三颗灯都包进来）
        w, h = x2 - x1, y2 - y1
        px, py = int(w * 0.4) + 6, int(h * 0.4) + 6
        H, W = frame.shape[:2]
        cx1, cy1 = max(0, x1 - px), max(0, y1 - py)
        cx2, cy2 = min(W, x2 + px), min(H, y2 + py)
        roi = frame[cy1:cy2, cx1:cx2]
        if roi.size == 0:
            continue
        # 放大 6 倍（NEAREST 保留像素）
        big = cv2.resize(roi, (roi.shape[1] * 6, roi.shape[0] * 6),
                         interpolation=cv2.INTER_NEAREST)
        cv2.putText(big, f"{label} conf={conf:.2f}", (8, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        tiles.append(big)
        infos.append({"label": label, "bbox": [x1, y1, x2, y2], "conf": round(conf, 2),
                      "size": f"{w}x{h}", "roi": roi.copy()})
    return tiles, infos


cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, GREEN_FRAME)
ok1, fg = cap.read()
cap.set(cv2.CAP_PROP_POS_FRAMES, RED_FRAME)
ok2, fr_ = cap.read()
cap.release()
out.append(f"取帧: Green={ok1} {fg.shape if ok1 else ''}   Red={ok2} {fr_.shape if ok2 else ''}")

if ok1 and ok2:
    t1, i1 = crop_lights(fg, "GREEN", "g")
    t2, i2 = crop_lights(fr_, "RED", "r")
    out.append("")
    out.append(f"  绿灯帧检出灯框 {len(i1)} 个: {[x['bbox'] for x in i1]}")
    out.append(f"  红灯帧检出灯框 {len(i2)} 个: {[x['bbox'] for x in i2]}")

    # 并排：上排绿灯帧的灯，下排红灯帧的灯
    # 注意：不同灯框裁出来宽度不同，必须先统一宽度再 hstack（否则 numpy 报
    # "all the input array dimensions ... must match exactly"）
    n = max(len(t1), len(t2), 1)
    TILE_W = 320
    hmax = max([t.shape[0] for t in t1 + t2] + [1])

    def norm(t):
        # 等比例缩放到统一宽度，再补齐到统一高度
        sc = TILE_W / max(1, t.shape[1])
        r = cv2.resize(t, (TILE_W, max(1, int(t.shape[0] * sc))),
                       interpolation=cv2.INTER_NEAREST)
        if r.shape[0] < hmax:
            r = cv2.copyMakeBorder(r, 0, hmax - r.shape[0], 0, 0,
                                   cv2.BORDER_CONSTANT, value=(20, 20, 20))
        else:
            r = r[:hmax]
        return r

    def padrow(ts):
        row = [norm(t) for t in ts]
        while len(row) < n:
            row.append(np.zeros((hmax, TILE_W, 3), np.uint8))
        return np.hstack(row)

    grid = np.vstack([padrow(t1), padrow(t2)])
    p = os.path.join(OUT, "video_tl_green_vs_red.png")
    cv2.imwrite(p, grid)
    out.append("")
    out.append(f"  对比图（上=绿灯帧, 下=红灯帧, 放大6倍）: {p}  {grid.shape[1]}x{grid.shape[0]}")

    # 量化：同样位置的灯框，在两帧里的颜色差异
    out.append("")
    out.append("=" * 76)
    out.append("量化比较")
    out.append("=" * 76)
    if i1 and i2:
        b1 = i1[0]["bbox"]; b2 = i2[0]["bbox"]
        out.append(f"  绿灯帧灯框={b1}   红灯帧灯框={b2}")
        for nm, roi in (("GREEN帧", i1[0]["roi"]), ("RED帧", i2[0]["roi"])):
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            tot = max(1, roi.shape[0] * roi.shape[1])
            mr = int(cv2.countNonZero(cv2.bitwise_or(
                cv2.inRange(hsv, (0, 60, 50), (10, 255, 255)),
                cv2.inRange(hsv, (170, 60, 50), (180, 255, 255)))))
            my = int(cv2.countNonZero(cv2.inRange(hsv, (12, 60, 50), (36, 255, 255))))
            mg = int(cv2.countNonZero(cv2.inRange(hsv, (38, 40, 40), (95, 255, 255))))
            # 最亮像素的色相
            v = hsv[:, :, 2]
            thr = np.percentile(v, 92)
            mm = (v >= thr) & (hsv[:, :, 1] > 60)
            mh = float(np.median(hsv[:, :, 0][mm])) if mm.sum() else -1
            out.append(f"    {nm}: 红{mr/tot*100:5.1f}%  黄{my/tot*100:5.1f}%  "
                       f"绿{mg/tot*100:5.1f}%   最亮像素主色相 H={mh:.1f}")
        out.append("")
        out.append("  若两帧的『最亮像素主色相』不同 -> 灯确实随状态变色")

io.open(r"E:\output\_tl_video_check.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
