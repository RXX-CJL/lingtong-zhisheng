"""实测像素比例尺：用画面里已知尺寸的道路标线标定 pixel_per_meter。

依据（来自我们自己的场景脚本，均为已知真值）：
  * 两条车道的中心线间距 = 3.50 m（CARLA 世界坐标 y=-64.7 与 y=-68.2）
  * 斑马线条纹间距     = 0.60 m（CARLA 默认 crosswalk 条纹）
  * 停止线到斑马线距离 = 已知（STOP_X=-25.61 到斑马线 -63.2 世界 x）

做法：在图像里把车辆所在区域（车道 y 方向）的真实间距量出来，
      除以已知米数，得到 pixel_per_meter。
"""
import sys

import cv2
import numpy as np

VID = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"


def main():
    cap = cv2.VideoCapture(VID)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 240)
    ok, img = cap.read()
    cap.release()
    if not ok:
        print("取帧失败")
        return 1
    h, w = img.shape[:2]
    print("帧 %dx%d" % (w, h))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 白色标线：高亮 + 低饱和
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    white = ((hsv[:, :, 1] < 60) & (hsv[:, :, 2] > 150)).astype(np.uint8) * 255

    # ---- 方法1：量两条车道分界白线的横向(y方向)间距
    # 取画面下部一块（车辆所在车道，透视较小、标线接近水平）
    band = white[int(h * 0.80):int(h * 0.95), :]
    rows = band.sum(axis=1) / 255.0
    print("\n画面 y=80%%~95%% 区域里，每行的白线像素数（找车道分界线所在行）：")
    peaks = []
    for i, v in enumerate(rows):
        y = int(h * 0.80) + i
        if v > 40:
            peaks.append((y, int(v)))
    # 聚合成若干"线"
    lines = []
    for y, v in peaks:
        if lines and y - lines[-1][-1][0] <= 3:
            lines[-1].append((y, v))
        else:
            lines.append([(y, v)])
    centers = [int(np.mean([p[0] for p in grp])) for grp in lines]
    print("   检出白线所在的 y（画面行号）:", centers)

    # ---- 方法2：量斑马线条纹间距（在斑马线区域横向扫描）
    # 斑马线大约在画面 y=430~520（从之前的观测）
    print("\n斑马线区域条纹间距：")
    for y in (450, 470, 490, 510):
        row = white[y, :]
        # 找连续白段的起点
        starts = []
        run = 0
        for x in range(w):
            if row[x] > 0:
                run += 1
            else:
                if run > 6:
                    starts.append(x - run)
                run = 0
        if len(starts) >= 3:
            gaps = [starts[i + 1] - starts[i] for i in range(len(starts) - 1)]
            print("   y=%d 检出 %d 段，间距=%s  -> 中位间距 %.1f px"
                  % (y, len(starts), gaps[:8], float(np.median(gaps))))

    # ---- 方法3：结合世界真值给出结论
    print("\n=== 结论：像素比例尺 ===")
    # 两条车道中心线 y 世界坐标相差 3.5 m；在画面里它们的 v 坐标差即对应 3.5 m
    # 用检测到的白线（车道分界线）间距近似：分界线之间 = 一个车道宽 3.5 m
    if len(centers) >= 2:
        diffs = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
        print("   相邻白线行距 = %s px" % diffs)
        for d in diffs:
            if 20 < d < 200:
                print("   若这是 3.5 m 的车道宽 -> pixel_per_meter = %.1f px/m" % (d / 3.5))
    print("\n   当前代码里硬编码 pixel_per_meter = 10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
