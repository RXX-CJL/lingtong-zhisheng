"""把已录好的 PNG 帧序列重新编码，对比三种交付格式的颜色保真度与体积。

为什么：mp4v (MPEG-4 Part 2) 会把颜色压坏 —— 实测在饱和内容上平均差 44/255，
并导致 YOLO 对远处车辆的置信度从 0.676 掉到 0.418。演示素材必须保色。
"""
import glob
import os
import subprocess
import sys

import cv2
import numpy as np

SCENE = r"E:\output\_demo_scene"
FRAMES = sorted(glob.glob(os.path.join(SCENE, "frame_*.png")))
FRAMES = [f for f in FRAMES if "_marked" not in f]
FPS = 20.0


def encode(fourcc, out, fps=FPS):
    first = cv2.imread(FRAMES[0])
    h, w = first.shape[:2]
    vw = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*fourcc), fps, (w, h))
    if not vw.isOpened():
        return None
    for f in FRAMES:
        img = cv2.imread(f)
        if img is not None:
            vw.write(img)
    vw.release()
    return out


def compare(png_path, vid_path, idx):
    cap = cv2.VideoCapture(vid_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, back = cap.read()
    cap.release()
    if not ok:
        return None
    a = cv2.imread(png_path)
    if a is None or back is None or a.shape != back.shape:
        return None
    d = np.abs(a.astype(np.int16) - back.astype(np.int16))
    hs = lambda im: cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[:, :, 1].astype(np.float32).mean()
    return d.mean(), d.max(), hs(a) - hs(back)


def main():
    print("PNG 帧数:", len(FRAMES))
    idx_map = {}
    for i, f in enumerate(FRAMES):
        n = int(os.path.basename(f).split("_")[1].split(".")[0])
        idx_map[n] = i

    results = []
    for fourcc, ext, label in (("FFV1", ".mkv", "FFV1 无损"), ("HFYU", ".avi", "HuffYUV 无损"),
                               ("mp4v", ".mp4", "mp4v 有损（旧）")):
        out = os.path.join(SCENE, "red_light_demo_%s%s" % (fourcc.lower(), ext))
        # 只取代表帧编码以省时间？不 —— 需要完整视频，用 PNG 全序列
        r = encode(fourcc, out)
        if r is None:
            print("%-16s 编码器不可用" % label)
            continue
        size = os.path.getsize(out)
        results.append((label, out, size))
        print("%-16s %s  %.2f MB" % (label, os.path.basename(out), size / 1e6))

    print("\n与 PNG 原帧的差异（代表性帧号）:")
    print("%-26s %-10s %-10s %-9s %s" % ("格式", "帧号", "平均绝对差", "最大差", "S均值差"))
    for label, path, _ in results:
        for mark in (220, 260, 340):
            if mark not in idx_map:
                continue
            res = compare(FRAMES[idx_map[mark]], path, idx_map[mark])
            if res:
                print("%-26s %-10d %-10.2f %-9d %+.2f" % (label, mark, res[0], res[1], res[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
