"""直接对比：旧视频（用户说颜色没问题）vs 本次录制（红灯呈青蓝）。

两张视频都是**同一个用户机位**、都含红灯期。
把同一位置的像素值并排测出来 —— 差异到底在哪一环，一眼可见。
"""
import os
import sys

import numpy as np
import cv2

OLD = r"E:\output\_carla_video4\carla_tl_face_28s.mp4"      # 上一会话产物（用户说颜色正常）
NEW = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"  # 本次产物
OUT = r"E:\output\_compare_old_new"
os.makedirs(OUT, exist_ok=True)


def probe(img, tag, boxes):
    print("  %-14s" % tag, end="")
    for (x0, y0, x1, y1) in boxes:
        roi = img[y0:y1, x0:x1]
        if roi.size == 0:
            print("   [empty]", end="")
            continue
        g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        y, x = np.unravel_index(int(np.argmax(g)), g.shape)
        b, gg, r = [int(roi[y, x, k]) for k in range(3)]
        hsv = cv2.cvtColor(np.uint8([[[b, gg, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
        hue, sat = int(hsv[0]) * 2, int(hsv[1])
        nm = ("RED" if (hue < 20 or hue >= 340) and sat >= 40 else
              "green" if 100 <= hue < 150 and sat >= 40 else
              "cyan/blue" if 180 <= hue < 260 and sat >= 40 else "grey")
        print("  (%3d,%3d,%3d)h%-3d %-9s" % (b, gg, r, hue, nm), end="")
    print()


def sample_video(path, frames, boxes, tag):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print("打不开:", path)
        return None
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print("\n=== %s ===" % tag)
    print("   %dx%d  %d 帧  %.1f fps" % (w, h, n, fps))
    got = None
    for f in frames:
        if f >= n:
            continue
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, img = cap.read()
        if not ok:
            continue
        print("  帧 %-4d (t=%.2fs):" % (f, f / fps))
        probe(img, "最亮像素", boxes)
        if got is None:
            got = img
    cap.release()
    return got


def main():
    # 旧视频的灯珠区域：先用色域扫描自动找（它的灯位置未知）
    print("先在两个视频里各自自动找『亮且带色』的紧凑块，再对比颜色。")
    for tag, path in (("旧视频 _carla_video4", OLD), ("本次 dual_cam", NEW)):
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            print("\n%s: 打不开" % tag)
            continue
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
        print("\n=== %s  (%d 帧, %.1f fps) ===" % (tag, n, fps))
        # 取若干帧扫描
        found = []
        for f in range(0, n, max(1, n // 12)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, img = cap.read()
            if not ok:
                continue
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            s = hsv[:, :, 1].astype(np.int16)
            v = hsv[:, :, 2].astype(np.int16)
            m = ((s > 100) & (v > 140)).astype(np.uint8) * 255
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            nc, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
            for i in range(1, nc):
                a = int(st[i, cv2.CC_STAT_AREA])
                bw, bh = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
                if a < 30 or a > 3000:
                    continue
                if max(bw, bh) / max(1, min(bw, bh)) > 4:
                    continue
                cx, cy = int(ce[i][0]), int(ce[i][1])
                b, gg, r = [int(img[cy, cx, k]) for k in range(3)]
                hv = cv2.cvtColor(np.uint8([[[b, gg, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
                hue, sat = int(hv[0]) * 2, int(hv[1])
                nm = ("RED" if (hue < 20 or hue >= 340) else
                      "green" if 100 <= hue < 150 else
                      "cyan/blue" if 180 <= hue < 260 else "other")
                found.append((f, cx, cy, b, gg, r, hue, sat, nm))
        cap.release()
        from collections import Counter
        cnt = Counter(x[8] for x in found)
        print("  亮色块类别统计: %s" % dict(cnt))
        for x in found[:10]:
            print("    f%-4d (%4d,%4d) BGR=(%3d,%3d,%3d) hue=%-3d sat=%-3d -> %s"
                  % (x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8]))
        if any(x[8] == "RED" for x in found):
            r = [x for x in found if x[8] == "RED"][0]
            print("  ★ 找到 RED 块: 帧 %d @(%d,%d) BGR=(%d,%d,%d) hue=%d sat=%d"
                  % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]))
        else:
            print("  ✗ 整个视频里没有找到任何 RED 块")
    return 0


if __name__ == "__main__":
    sys.exit(main())
