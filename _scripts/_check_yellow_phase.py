"""查"红->绿之间到底有没有黄灯"——测演示视频三颗镜片的亮度变化。

用户观察：灯从最上面（红）直接变到最下面（绿），中间那颗（黄）没亮过。
真值相位计划：红15s / 绿5s / 黄5s / 红6s
逐帧测三颗镜片的亮度，看黄灯相位时"中间那颗"到底亮没亮。
"""
import sys

import cv2
import numpy as np

VID = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"
# CAM-1 里信号灯头的三颗镜片位置（画面坐标，前几轮实测过）
HEADS = [(1007, 131, 1006, 157, 1006, 198),     # 灯头1: 上/中/下
         (1139, 131, 1138, 158, 1139, 198)]     # 灯头2


def main():
    cap = cv2.VideoCapture(VID)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    print("视频 %d 帧 / %.1f fps" % (n, fps))
    print("真值相位: 0-299 红 | 300-399 绿 | 400-499 黄 | 500+ 红\n")

    def lum(img, cx, cy, hw=9, hh=7):
        r = img[max(0, cy - hh):cy + hh, max(0, cx - hw):cx + hw]
        if r.size == 0:
            return 0.0
        return float(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY).mean())

    print("%-6s %-7s | %-22s | %-22s" % ("帧", "真值", "灯头1 上/中/下 亮度", "灯头2 上/中/下 亮度"))
    rows = []
    for f in range(0, n, 20):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, img = cap.read()
        if not ok:
            continue
        truth = "红" if (f < 300 or f >= 500) else ("绿" if f < 400 else "黄")
        cells = []
        for (ux, uy, mx, my, dx, dy) in HEADS:
            cells.append((lum(img, ux, uy), lum(img, mx, my), lum(img, dx, dy)))
        rows.append((f, truth, cells))
        print("%-6d %-7s | %5.1f %5.1f %5.1f      | %5.1f %5.1f %5.1f"
              % (f, truth, cells[0][0], cells[0][1], cells[0][2],
                 cells[1][0], cells[1][1], cells[1][2]))
    cap.release()

    print("\n=== 关键结论 ===")
    # 只看灯头1
    for label, lo, hi in (("红灯相位", 0, 300), ("绿灯相位", 300, 400), ("黄灯相位", 400, 500)):
        sel = [r for r in rows if lo <= r[0] < hi]
        if not sel:
            continue
        upper = np.mean([r[2][0][0] for r in sel])
        mid = np.mean([r[2][0][1] for r in sel])
        lower = np.mean([r[2][0][2] for r in sel])
        lit = ["上", "中", "下"][int(np.argmax([upper, mid, lower]))]
        print("  %-8s 上=%.1f 中=%.1f 下=%.1f  -> 最亮的是「%s」那颗" % (label, upper, mid, lower, lit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
