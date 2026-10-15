"""找出"我出的图 vs 用户 CARLA 窗口"颜色不一致的渲染侧原因。

CARLA 的 sensor.camera.rgb 有若干后处理属性会改变画面颜色/对比度，其中
enable_postprocess_effects 打开时会启用 UE4 的 Bloom / 色调映射 / 暗角（vignette）。
逐一渲染同一机位并量化差异。
"""
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_camera_check"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0

VARIANTS = [
    ("pp_on", {"enable_postprocess_effects": "True"}),
    ("pp_off", {"enable_postprocess_effects": "False"}),
    ("pp_off_bloom0", {"enable_postprocess_effects": "False", "bloom_intensity": "0.0"}),
    ("pp_on_bloom0", {"enable_postprocess_effects": "True", "bloom_intensity": "0.0"}),
    ("pp_off_gamma22", {"enable_postprocess_effects": "False", "gamma": "2.2"}),
    ("pp_off_shutter60", {"enable_postprocess_effects": "False", "shutter_speed": "60.0"}),
]


def stats(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s, v = hsv[:, :, 1].astype(np.float32), hsv[:, :, 2].astype(np.float32)
    col = s > 60
    return (float(s.mean()), float(s[col].mean()) if col.sum() else 0.0,
            float(np.percentile(s, 99)), float(v.mean()), 100.0 * float(col.mean()))


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    spec = world.get_spectator().get_transform()

    # 列出相机蓝图支持的滤镜相关属性
    bp0 = world.get_blueprint_library().find("sensor.camera.rgb")
    try:
        all_keys = list(bp0)
    except Exception:
        all_keys = []
    keys = [str(k) for k in all_keys
            if any(t in str(k) for t in ("postprocess", "bloom", "gamma", "shutter", "iso",
                                         "exposure", "fstop", "temp", "tone", "vignette", "motion"))]
    print("相机可变属性（与颜色/曝光相关）共 %d 项:" % len(keys))
    for k in sorted(keys):
        try:
            print("   %-32s 值=%s" % (k, bp0.get_attribute(k).recommended_values))
        except Exception as e:
            print("   %-32s (读取失败 %s)" % (k, e))
    print()

    print("%-20s %-11s %-13s %-8s %-9s %s" %
          ("变体", "S均值(全部)", "S均值(有色)", "S_p99", "V均值", "有色像素%"))
    imgs = {}
    for name, attrs in VARIANTS:
        bp = world.get_blueprint_library().find("sensor.camera.rgb")
        bp.set_attribute("image_size_x", str(W))
        bp.set_attribute("image_size_y", str(H))
        bp.set_attribute("fov", str(FOV))
        applied = []
        for k, v in attrs.items():
            try:
                bp.set_attribute(k, v)
                applied.append("%s=%s" % (k, v))
            except Exception as e:
                applied.append("%s FAILED(%s)" % (k, e))
        cam = world.spawn_actor(bp, spec)
        got = []
        cam.listen(lambda im: got.append(im))
        for _ in range(6):
            world.tick()
            time.sleep(0.05)
        time.sleep(0.6)
        cam.stop()
        cam.destroy()
        arr = np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
        imgs[name] = arr
        cv2.imwrite(os.path.join(OUT, "pp_%s.png" % name), arr)
        st = stats(arr)
        print("%-20s %-11.1f %-13.1f %-8.1f %-9.1f %.1f   [%s]"
              % (name, st[0], st[1], st[2], st[3], st[4], "; ".join(applied)))

    # 两两最大差异
    print("\n与 pp_on（默认，窗口所见）相比的差异:")
    base = imgs.get("pp_on")
    if base is not None:
        for name, arr in imgs.items():
            if name == "pp_on":
                continue
            d = np.abs(base.astype(np.int16) - arr.astype(np.int16))
            print("   %-20s 平均绝对差=%6.2f  最大差=%3d  S差=%+6.1f  V差=%+6.1f"
                  % (name, d.mean(), d.max(), stats(arr)[0] - stats(base)[0],
                     stats(arr)[3] - stats(base)[3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
