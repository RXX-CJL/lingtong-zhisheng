"""对比三条链路的颜色保真度：
  A 截图基准   E:\\output\\_camera_verify\\reference_1080.png   （之前给你看过的图）
  B 本次 PNG 代表帧  frame_XXX.png                            （无损）
  C 本次视频   red_light_demo.mp4 同帧                        （有损编码）

如果 C 的饱和度明显低于 A/B，说明是视频编码（YUV 4:2:0）把颜色洗掉了，
而不是 CARLA 渲染问题 —— 那就该用无二次编码的方式出片。
"""
import os
import sys

import cv2
import numpy as np

SCENE = r"E:\output\_demo_scene"
REF = r"E:\output\_camera_verify\reference_1080.png"


def stats(img, tag):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s, v = hsv[:, :, 1].astype(np.float32), hsv[:, :, 2].astype(np.float32)
    # 只看"有颜色的像素"，避免大片灰路面把均值拉平
    colored = s > 60
    return {
        "tag": tag,
        "S_mean_all": float(s.mean()),
        "S_mean_colored": float(s[colored].mean()) if colored.sum() else 0.0,
        "S_p99": float(np.percentile(s, 99)),
        "colored_pct": 100.0 * float(colored.mean()),
        "V_mean": float(v.mean()),
        "max_S": float(s.max()),
    }


def main():
    rows = []
    if os.path.exists(REF):
        a = cv2.imread(REF)
        if a is not None:
            rows.append(stats(a, "A 截图基准 reference_1080.png (PNG)"))

    frames = sorted(f for f in os.listdir(SCENE) if f.startswith("frame_") and f.endswith(".png")
                    and "_marked" not in f)
    for fn in frames[:3]:
        img = cv2.imread(os.path.join(SCENE, fn))
        if img is not None:
            rows.append(stats(img, "B PNG 代表帧 %s" % fn))

    vid = os.path.join(SCENE, "red_light_demo.mp4")
    if os.path.exists(vid):
        cap = cv2.VideoCapture(vid)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        for f in (min(200, n - 1), min(260, n - 1), min(340, n - 1)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, img = cap.read()
            if ok:
                rows.append(stats(img, "C 视频帧 %d (mp4v 有损)" % f))
                cv2.imwrite(os.path.join(SCENE, "_vidcheck_%d.png" % f), img)
        cap.release()

    print("%-42s %-11s %-13s %-8s %-9s %-9s %s"
          % ("来源", "S均值(全部)", "S均值(有色)", "S_p99", "有色像素%", "V均值", "最大S"))
    for r in rows:
        print("%-42s %-11.1f %-13.1f %-8.1f %-9.1f %-9.1f %.0f"
              % (r["tag"], r["S_mean_all"], r["S_mean_colored"], r["S_p99"],
                 r["colored_pct"], r["V_mean"], r["max_S"]))

    # 同一内容（同帧序号）B vs C 直接比较
    print("\n同内容 PNG vs 视频帧 的逐像素差异（若有同帧号）：")
    for fn in frames:
        idx = int(fn.split("_")[1].split(".")[0])
        vf = os.path.join(SCENE, "_vidcheck_%d.png" % idx)
        if os.path.exists(vf):
            p = cv2.imread(os.path.join(SCENE, fn))
            v = cv2.imread(vf)
            if p is not None and v is not None and p.shape == v.shape:
                d = np.abs(p.astype(np.int16) - v.astype(np.int16))
                print("   frame %d : 平均绝对差=%.2f  最大差=%d  S差=%.1f"
                      % (idx, d.mean(), d.max(),
                         stats(p, "")["S_mean_all"] - stats(v, "")["S_mean_all"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
