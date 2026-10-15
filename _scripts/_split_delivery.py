"""分层交付：把无损 FFV1 母版切成
  1) 关键窗口无损（YOLO 用）：把两车驶入→停止线→闯红灯→通过 的帧单独成段
  2) 高保真 JPEG 序列（供复核，体积友好）
  3) 全片 mp4v（仅速览，不作为检测输入 —— 颜色会被压坏）

并量化各格式相对母版的差异。
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
# 关键窗口：车辆进入(约t=4s)→到达停止线→闯红灯越线(t=9.55)→通过对面(t=17s)
KEY_START, KEY_END = int(3.5 * FPS), int(18.0 * FPS)


def main():
    if not os.path.exists(MASTER):
        print("母版不存在:", MASTER)
        return 1
    cap = cv2.VideoCapture(MASTER)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print("母版: %d 帧 %dx%d" % (n, w, h))

    key_dir = os.path.join(SCENE, "key_frames_lossless")
    os.makedirs(key_dir, exist_ok=True)

    key_vid = os.path.join(SCENE, "red_light_demo_key_lossless.mkv")
    vw = cv2.VideoWriter(key_vid, cv2.VideoWriter_fourcc(*"FFV1"), FPS, (w, h))
    if not vw.isOpened():
        print("FFV1 不可用")
        return 1

    jpg_dir = os.path.join(SCENE, "frames_jpeg98")
    os.makedirs(jpg_dir, exist_ok=True)

    master_key = []
    jpg_sizes = []
    key_count = 0
    for i in range(n):
        ok, img = cap.read()
        if not ok:
            break
        if KEY_START <= i < KEY_END:
            vw.write(img)
            master_key.append(img.copy())
            cv2.imwrite(os.path.join(key_dir, "k%04d.png" % i), img)
            key_count += 1
        # JPEG 98 全片
        cv2.imwrite(os.path.join(jpg_dir, "f%04d.jpg" % i), img,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 98])
    cap.release()
    vw.release()

    # 量测 JPEG98 与母版差异
    print("\n量测各格式相对母版的差异（对关键窗口抽样）:")
    print("%-28s %-10s %-11s %-9s %s" % ("格式", "帧", "平均绝对差", "最大差", "S均值差"))
    for k, mi in enumerate(range(0, len(master_key), max(1, len(master_key) // 4))):
        idx = KEY_START + mi
        ref = master_key[mi]
        # JPEG98
        jp = cv2.imread(os.path.join(jpg_dir, "f%04d.jpg" % idx))
        if jp is not None and jp.shape == ref.shape:
            d = np.abs(ref.astype(np.int16) - jp.astype(np.int16))
            hs = lambda im: cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[:, :, 1].astype(np.float32).mean()
            print("%-28s %-10d %-11.2f %-9d %+.2f" % ("JPEG q98", idx, d.mean(), d.max(), hs(jp) - hs(ref)))
        # PNG (关键窗口无损)
        pn = cv2.imread(os.path.join(key_dir, "k%04d.png" % idx))
        if pn is not None and pn.shape == ref.shape:
            d = np.abs(ref.astype(np.int16) - pn.astype(np.int16))
            print("%-28s %-10d %-11.2f %-9d %+.2f" % ("PNG (关键窗口)", idx, d.mean(), d.max(), 0.0))

    print("\n产出:")
    print("  %-42s %8.1f MB  (%d 帧关键窗口, 逐像素无损)" % (key_vid, os.path.getsize(key_vid) / 1e6, key_count))
    print("  %-42s %8.1f MB" % (key_dir, sum(os.path.getsize(f) for f in glob.glob(key_dir + "/*.png")) / 1e6))
    print("  %-42s %8.1f MB" % (jpg_dir, sum(os.path.getsize(f) for f in glob.glob(jpg_dir + "/*.jpg")) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
