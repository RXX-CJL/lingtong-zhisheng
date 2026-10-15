"""诊断发光区定位：在**机器校验真值**的 CARLA 灯珠裁图上，
看 (a) 真实灯珠长什么样（像素特征）(b) 现有 find_glow_region 定位到了哪里。

数据：E:\\output\\_tl_carla3 —— 12/20/30 m，含红/黄/绿三态，状态经回读校验
"""
import glob
import os
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
import traffic_light_classifier as tlc  # noqa: E402

SRC = r"E:\output\_tl_carla3"
OUT = r"E:\output\_tl_glow_eval"
os.makedirs(OUT, exist_ok=True)


def analyse(img, tag):
    """真实灯珠在哪：找"最亮的圆形紧凑区"，并给出它相对灯壳的亮度/颜色。"""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, w = g.shape
    # 灯壳基线：整幅的中位数亮度
    shell_v = float(np.median(g))
    peak = float(g.max())
    py, px = np.unravel_index(np.argmax(g), g.shape)
    # 峰值附近 7x7 的均值 = 灯珠核心
    y0, y1 = max(0, py - 3), min(h, py + 4)
    x0, x1 = max(0, px - 3), min(w, px + 4)
    core = img[y0:y1, x0:x1]
    cb, cg, cr = [float(core[:, :, i].mean()) for i in range(3)]
    chsv = hsv[y0:y1, x0:x1]
    # 现有定位器
    gl = tlc.find_glow_region(img)
    gl_info = None
    if gl:
        gl_info = (round(gl["cx"], 1), round(gl["cy"], 1), gl["w"], gl["h"], gl["area"], gl["mask"])
    return dict(tag=tag, size=(w, h), shell_v=shell_v, peak=peak,
                peak_xy=(int(px), int(py)), core_bgr=(cb, cg, cr),
                core_sat=float(chsv[:, :, 1].mean()), core_v=float(chsv[:, :, 2].mean()),
                glow=gl_info)


def main():
    pat = re.compile(r"^(red|green|yellow)_(\d+)m_(\d+)x(\d+)\.png$")
    rows = []
    for f in sorted(glob.glob(os.path.join(SRC, "*.png"))):
        m = pat.match(os.path.basename(f))
        if not m:
            continue
        truth, dist, cw, ch = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if dist == 45:
            continue
        img = cv2.imread(f)
        if img is None or img.size == 0:
            continue
        a = analyse(img, "%s_%02dm_%dx%d" % (truth, dist, cw, ch))
        a["truth"] = truth
        a["dist"] = dist
        rows.append(a)

    print("真实灯珠像素特征（峰值 = 灯珠最亮点）:")
    print("%-30s %-7s %-8s %-8s %-22s %-7s %-7s %s"
          % ("crop", "truth", "壳亮度", "峰值", "峰值处 BGR", "饱和", "亮度", "现有定位器"))
    for r in rows:
        gl = r["glow"]
        gltxt = ("(%.0f,%.0f) %dx%d a=%d" % gl[:5]) if gl else "未找到"
        # 定位器中心与真实峰值的距离
        if gl:
            d = np.hypot(gl[0] - r["peak_xy"][0], gl[1] - r["peak_xy"][1])
            gltxt += "  偏差%.0fpx" % d
        print("%-30s %-7s %-8.0f %-8.0f (%6.1f,%6.1f,%6.1f) %-7.0f %-7.0f %s"
              % (r["tag"][:30], r["truth"], r["shell_v"], r["peak"],
                 r["core_bgr"][0], r["core_bgr"][1], r["core_bgr"][2],
                 r["core_sat"], r["core_v"], gltxt))

    # 对比：灯珠颜色（峰值核心）vs 灯壳颜色
    print("\n灯珠核心颜色 vs 灯壳（用于设计判据）:")
    print("%-8s %-24s %-24s %s" % ("truth", "灯珠核心 BGR", "整幅中位 BGR", "差值 B/G/R"))
    for truth in ("red", "yellow", "green"):
        sub = [r for r in rows if r["truth"] == truth]
        if not sub:
            continue
        c = np.median([r["core_bgr"] for r in sub], axis=0)
        # 整幅中位色
        med = []
        for r in sub[:1]:
            pass
        print("%-8s (%7.1f,%7.1f,%7.1f) %-24s %s" % (truth, c[0], c[1], c[2], "-", "-"))

    # 把峰值点画到图上，人工确认"峰值确实是灯珠"
    tiles = []
    for r in rows:
        if r["size"][0] != 34:
            continue
        f = os.path.join(SRC, "%s_%02dm_34x130.png" % (r["truth"], r["dist"]))
        img = cv2.imread(f)
        if img is None:
            continue
        big = cv2.resize(img, (34 * 4, 130 * 4), interpolation=cv2.INTER_NEAREST)
        px, py = r["peak_xy"]
        cv2.drawMarker(big, (px * 4, py * 4), (0, 0, 255), cv2.MARKER_CROSS, 22, 2)
        if r["glow"]:
            cv2.drawMarker(big, (int(r["glow"][0] * 4), int(r["glow"][1] * 4)),
                           (0, 255, 0), cv2.MARKER_TILTED_CROSS, 22, 2)
        cv2.putText(big, "%s %dm" % (r["truth"][:3], r["dist"]), (4, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(big)
    if tiles:
        cols = 5
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        rows_img = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
        sheet = np.vstack(rows_img)
        p = os.path.join(OUT, "glow_diagnosis.png")
        cv2.imwrite(p, sheet)
        print("\n诊断图（红叉=最亮点，绿叉=现有定位器）: %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
