"""清理冗余 + 最终交付整理。

删：key_frames_lossless（PNG 序列，与无损 mkv 完全重复，省 1018 MB）
留：无损 mkv（YOLO 输入）
做：JPEG q95 全片（复核用，视觉无损）+ mp4v 速览（仅预览，不作检测输入）
"""
import glob
import os
import shutil
import sys

import cv2
import numpy as np

SCENE = r"E:\output\_demo_scene"
MASTER = os.path.join(SCENE, "red_light_demo_lossless.mkv")
FPS = 20.0


def main():
    # 1) 删冗余 PNG 序列
    dup = os.path.join(SCENE, "key_frames_lossless")
    if os.path.isdir(dup):
        n = len(glob.glob(dup + "/*.png"))
        shutil.rmtree(dup)
        print("已删除冗余 PNG 序列 %s (%d 张)" % (dup, n))

    old_jpg = os.path.join(SCENE, "frames_jpeg98")
    if os.path.isdir(old_jpg):
        shutil.rmtree(old_jpg)
        print("已删除旧 JPEG98 目录")

    # 2) 生成 JPEG q95 全片 + mp4v 速览
    cap = cv2.VideoCapture(MASTER)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    jq = os.path.join(SCENE, "frames_jpeg95")
    os.makedirs(jq, exist_ok=True)
    prev = os.path.join(SCENE, "red_light_demo_preview.mp4")
    vw = cv2.VideoWriter(prev, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (w, h))

    refs = {}
    tot = 0
    for i in range(n):
        ok, img = cap.read()
        if not ok:
            break
        cv2.imwrite(os.path.join(jq, "f%04d.jpg" % i), img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        vw.write(img)
        if i in (100, 200, 260, 340):
            refs[i] = img.copy()
        tot += 1
    cap.release()
    vw.release()

    # 3) 量测 q95 保真度
    print("\nJPEG q95 相对无损母版的差异:")
    print("%-8s %-11s %-9s %s" % ("帧", "平均绝对差", "最大差", "S均值差"))
    hs = lambda im: cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[:, :, 1].astype(np.float32).mean()
    for i, ref in refs.items():
        jp = cv2.imread(os.path.join(jq, "f%04d.jpg" % i))
        if jp is not None and jp.shape == ref.shape:
            d = np.abs(ref.astype(np.int16) - jp.astype(np.int16))
            print("%-8d %-11.2f %-9d %+.2f" % (i, d.mean(), d.max(), hs(jp) - hs(ref)))

    # 4) 汇总
    print("\n最终交付:")
    items = [
        ("red_light_demo_key_lossless.mkv", "无损关键窗口（YOLO 输入，逐像素无损）"),
        ("frames_jpeg95", "全片 JPEG q95（人眼复核）"),
        ("red_light_demo_preview.mp4", "速览 mp4（仅预览，勿作检测输入）"),
        ("ground_truth.csv", "逐帧真值"),
        ("SCENE_NOTES.md", "场景实现记录"),
    ]
    for name, desc in items:
        p = os.path.join(SCENE, name)
        if os.path.isdir(p):
            sz = sum(os.path.getsize(f) for f in glob.glob(p + "/*"))
            print("  %-38s %8.1f MB  %s" % (name + "/", sz / 1e6, desc))
        elif os.path.exists(p):
            print("  %-38s %8.1f MB  %s" % (name, os.path.getsize(p) / 1e6, desc))
        else:
            print("  %-38s %s  (缺失)" % (name, desc))

    d = sum(os.path.getsize(os.path.join(dp, f))
            for dp, dn, fn in os.walk(SCENE) for f in fn)
    print("\n_demo_scene 总计: %.0f MB" % (d / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
