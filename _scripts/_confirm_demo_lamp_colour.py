"""确认演示视频里「信号灯」到底是红是绿 —— 用差分法（红态帧 vs 绿态帧）。

真值：帧 0-299 = 红灯，300-399 = 绿灯，400-499 = 黄灯，500+ = 红灯
做法：拿红灯相位的帧与绿灯相位的帧做差，差值区就是"被点亮的灯珠"，
      再看那块区域的绝对颜色。
"""
import sys

import cv2
import numpy as np

VID = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"


def grab(cap, i):
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ok, f = cap.read()
    return f if ok else None


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
    cap = cv2.VideoCapture(VID)
    if not cap.isOpened():
        print("打不开", VID)
        return 1
    print("视频 %dx%d 共 %d 帧" % (cap.get(3), cap.get(4),
                                   int(cap.get(cv2.CAP_PROP_FRAME_COUNT))))
    print("真值：0-299=红灯  300-399=绿灯  400-499=黄灯  500+=红灯\n")

    red_f = grab(cap, 150)      # 红灯相位代表帧
    grn_f = grab(cap, 350)      # 绿灯相位代表帧
    yel_f = grab(cap, 450)      # 黄灯相位代表帧
    cap.release()
    if red_f is None or grn_f is None:
        print("取帧失败")
        return 1

    d = cv2.absdiff(red_f, grn_f).max(axis=2)
    print("红态帧 vs 绿态帧：差 >25 的像素 = %d" % int((d > 25).sum()))
    m = cv2.morphologyEx((d > 25).astype(np.uint8) * 255, cv2.MORPH_CLOSE,
                         np.ones((3, 3), np.uint8))
    nc, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
    blobs = sorted([(int(st[i, cv2.CC_STAT_AREA]), int(ce[i][0]), int(ce[i][1]))
                    for i in range(1, nc)], reverse=True)[:8]
    print("\n%-6s %-14s %-34s %-34s %s" % ("面积", "位置", "红灯相位 实测", "绿灯相位 实测", "判定"))
    for a, cx, cy in blobs:
        sel = None
        for i in range(1, nc):
            if int(ce[i][0]) == cx and int(ce[i][1]) == cy and int(st[i, cv2.CC_STAT_AREA]) == a:
                sel = (lab == i)
                break
        if sel is None:
            continue
        out = []
        for f in (red_f, grn_f):
            b, g, r = [float(f[:, :, k][sel].mean()) for k in range(3)]
            hv = cv2.cvtColor(np.uint8([[[int(b), int(g), int(r)]]]), cv2.COLOR_BGR2HSV)[0, 0]
            out.append("BGR(%5.1f,%5.1f,%5.1f) h=%-3d %s" % (b, g, r, int(hv[0]) * 2,
                                                              cmp_color(int(hv[0]) * 2)))
        # 判定：红相位应 R 主导，绿相位应 G 主导
        rb, rg, rr = [f_ for f_ in (0, 0, 0)]
        rr_b = red_f[:, :, 2][sel].mean(); rr_g = red_f[:, :, 1][sel].mean()
        gr_b = grn_f[:, :, 2][sel].mean(); gr_g = grn_f[:, :, 1][sel].mean()
        verdict = []
        if rr_b > max(red_f[:, :, 0][sel].mean(), rr_g):
            verdict.append("红灯相位R主导 OK")
        else:
            verdict.append("红灯相位R不主导 X")
        if gr_g > max(grn_f[:, :, 0][sel].mean(), gr_b):
            verdict.append("绿灯相位G主导 OK")
        else:
            verdict.append("绿灯相位G不主导 X")
        print("%-6d (%4d,%4d)  %-34s %-34s %s" % (a, cx, cy, out[0], out[1], " / ".join(verdict)))

    print("\n=== 全图统计 ===")
    for tag, f in (("红灯相位", red_f), ("绿灯相位", grn_f), ("黄灯相位", yel_f)):
        if f is None:
            continue
        b, g, r = [f[:, :, i].astype(np.int16) for i in range(3)]
        bright = np.maximum(np.maximum(b, g), r)
        red = ((r > g + 40) & (r > b + 40) & (r > 120)).sum()
        grn = ((g > r + 40) & (g > b + 40) & (g > 120)).sum()
        blu = ((b > r + 40) & (b > g + 40) & (b > 120)).sum()
        print("  %-8s 亮红=%-6d 亮绿=%-6d 亮蓝=%-6d" % (tag, red, grn, blu))
    return 0


if __name__ == "__main__":
    sys.exit(main())
