"""确认新录视频里"信号灯区域的真实颜色" —— AI 复核拿到的就是这些帧。

对被 AI 判为"无车/黄灯"的那几个事件，读出它们的 event_video / 关键帧，
测信号灯区域的像素颜色，判断：
  * 红灯光珠是否为红（应为 R 主导）
  * 灯箱是否为青蓝（若是，AI 可能被灯箱误导）
"""
import glob
import json
import os
import sqlite3
import sys

import cv2
import numpy as np

DB = r"E:\output\1\api\zhitong_violations.db"


def cmp_color(hue):
    if hue < 20 or hue >= 340:
        return "红"
    if hue < 45:
        return "橙"
    if hue < 70:
        return "黄"
    if hue < 100:
        return "黄绿"
    if hue < 150:
        return "绿"
    if hue < 200:
        return "青"
    if hue < 260:
        return "蓝"
    return "紫"


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()
    cur.execute("""SELECT id, event_type, state, event_video_path
                   FROM traffic_events WHERE id > 2337 AND event_video_path != ''
                   ORDER BY id DESC LIMIT 3""")
    rows = cur.fetchall()
    print("=== 抽 3 个最新事件的事件视频，看它们的画面颜色 ===\n")
    for r in rows:
        p = r["event_video_path"]
        print("#%s %-12s %s" % (r["id"], r["event_type"], "存在" if os.path.exists(p) else "不存在"))
        if not os.path.exists(p):
            continue
        cap = cv2.VideoCapture(p)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print("   帧数 %d" % n)
        # 取首/中/尾三帧
        for fi in (0, n // 2, max(0, n - 1)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
            ok, fr = cap.read()
            if not ok:
                continue
            h, w = fr.shape[:2]
            b, g, rr = [fr[:, :, i].astype(np.int16) for i in range(3)]
            bright = np.maximum(np.maximum(b, g), rr)
            # 全图最亮的 300 个像素（通常是天空/高光，作参考）
            sel = fr.reshape(-1, 3)[np.argsort(bright.flatten())[-300:]]
            mb, mg, mr = [float(sel[:, i].mean()) for i in range(3)]
            # 找"亮且最像信号灯"的小块：高饱和 + 够亮 + 紧凑
            hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
            s = hsv[:, :, 1].astype(np.int32)
            v = hsv[:, :, 2].astype(np.int32)
            m = ((s > 110) & (v > 140)).astype(np.uint8) * 255
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            nc, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
            blobs = []
            for i in range(1, nc):
                a = int(st[i, cv2.CC_STAT_AREA])
                bw, bh = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
                if a < 20 or a > 4000:
                    continue
                if max(bw, bh) / max(1, min(bw, bh)) > 4:
                    continue
                blobs.append((a, int(ce[i][0]), int(ce[i][1])))
            blobs.sort(reverse=True)
            desc = []
            for a, cx, cy in blobs[:4]:
                pb, pg, pr = [int(fr[cy, cx, k]) for k in range(3)]
                hv = cv2.cvtColor(np.uint8([[[pb, pg, pr]]]), cv2.COLOR_BGR2HSV)[0, 0]
                desc.append("(%d,%d)BGR(%d,%d,%d)h%d=%s" % (
                    cx, cy, pb, pg, pr, int(hv[0]) * 2, cmp_color(int(hv[0]) * 2)))
            print("   帧%-4d 最亮300像素BGR=(%.0f,%.0f,%.0f) | 亮色块: %s"
                  % (fi, mb, mg, mr, "; ".join(desc) if desc else "(无)"))
        cap.release()
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
