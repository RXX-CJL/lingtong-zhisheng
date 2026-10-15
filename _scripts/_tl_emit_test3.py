"""CARLA 红绿灯发光检验 v3 —— 用 get_light_boxes() 的真实世界坐标

v1/v2 的错误（已定位）：
  把 `tl.bounding_box.location` 当**世界坐标**用，但它其实是**灯杆坐标系内的偏移**。
  结果相机架在离灯 36 米的地方，什么都没拍到 -> 结论无效。

v3 做法：
  ① 用 `get_light_boxes()` 取"点亮的那盏灯"的**真实世界坐标**
     （4 个 box 里最小的那个，extent≈0.03x0.05x0.10，就是信号灯珠）
  ② 相机架在该点正前方 2.5m，正对灯面
  ③ Red / Green / Yellow 三态各拍一张
  ④ 只在该灯珠的小邻域内比较颜色 —— 若红灯时偏红、绿灯时偏绿，
     则灯头**确实发光**（用户判断成立）
"""

import io
import math
import os
import queue

import carla

OUT = r"E:\output\_tl_review"
os.makedirs(OUT, exist_ok=True)
out = []

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
bp = world.get_blueprint_library()

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)

tl = list(world.get_actors().filter("traffic.traffic_light*"))[0]
tl_tf = tl.get_transform()
lbs = tl.get_light_boxes()
# 选"最小"的那个 box 当作信号灯珠（经验：extent 体积最小）
lbs_sorted = sorted(lbs, key=lambda b: b.extent.x * b.extent.y * b.extent.z)
lamp = lbs_sorted[0]
out.append(f"灯 id={tl.id}  杆 yaw={tl_tf.rotation.yaw:.1f}")
out.append(f"信号灯珠世界坐标 = ({lamp.location.x:.2f}, {lamp.location.y:.2f}, "
           f"{lamp.location.z:.2f})  extent={lamp.extent.x:.3f}x{lamp.extent.y:.3f}x{lamp.extent.z:.3f}")
out.append(f"（对比：tl.bounding_box.location = {tl.bounding_box.location} "
           f"<- 这是灯杆坐标系内偏移，不是世界坐标）")

# 相机：从灯珠出发，沿灯杆朝向的"正面"后退 2.5m
# CARLA 中 actor 的 +X 是前方；灯面朝向前方
yaw = math.radians(tl_tf.rotation.yaw)
fx, fy = math.cos(yaw), math.sin(yaw)
dist = 2.5
cam_loc = carla.Location(x=lamp.location.x + fx * dist,
                         y=lamp.location.y + fy * dist,
                         z=lamp.location.z)
cam_rot = carla.Rotation(pitch=0.0, yaw=tl_tf.rotation.yaw + 180.0, roll=0.0)
out.append(f"相机位置 = ({cam_loc.x:.2f}, {cam_loc.y:.2f}, {cam_loc.z:.2f})  "
           f"距灯珠 {dist}m  yaw={cam_rot.yaw:.1f}")

cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", "800")
cam_bp.set_attribute("image_size_y", "600")
cam_bp.set_attribute("fov", "50")
cam = world.spawn_actor(cam_bp, carla.Transform(cam_loc, cam_rot))
q = queue.Queue()
cam.listen(q.put)

import cv2
import numpy as np


def grab():
    for _ in range(6):
        world.tick()
    try:
        img = q.get(timeout=15.0)
        return np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
            (img.height, img.width, 4))[:, :, :3].copy()
    except queue.Empty:
        return None


frames = {}
for name, val in (("Red", carla.TrafficLightState.Red),
                  ("Green", carla.TrafficLightState.Green),
                  ("Yellow", carla.TrafficLightState.Yellow)):
    tl.set_state(val)
    f = grab()
    if f is not None:
        frames[name] = f
        cv2.imwrite(os.path.join(OUT, f"v3_{name}.png"), f)
out.append("")
out.append(f"取到 {len(frames)} 种灯态")

if len(frames) >= 2:
    keys = list(frames.keys())
    # 找整幅画面里各灯态之间的最大差异区域（灯珠应该就在那里）
    acc = None
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            d = cv2.absdiff(frames[keys[i]], frames[keys[j]])
            g = cv2.cvtColor(d, cv2.COLOR_BGR2GRAY)
            acc = g if acc is None else cv2.max(acc, g)
    out.append(f"  各灯态最大像素差: {int(acc.max())}")
    ys, xs = np.where(acc > 25)
    out.append(f"  差值 >25 的像素数: {len(xs)}")
    if len(xs) > 10:
        cx, cy = int(xs.mean()), int(ys.mean())
        bw, bh = int(xs.max() - xs.min()) + 1, int(ys.max() - ys.min()) + 1
        out.append(f"  差异集中区域: 中心=({cx},{cy})  范围 {bw}x{bh}")

        # 在该区域周围取窗（略放大以容纳灯壳）
        pad = max(bw, bh) // 2 + 12
        x1, x2 = max(0, cx - pad), min(frames[keys[0]].shape[1], cx + pad)
        y1, y2 = max(0, cy - pad), min(frames[keys[0]].shape[0], cy + pad)
        out.append(f"  采样窗 = [{x1},{y1},{x2},{y2}]")
        out.append("")
        out.append(f"  {'灯态':8} {'red%':>8} {'yellow%':>9} {'green%':>8} "
                   f"{'亮度V':>7} {'主色相H':>8}")
        main_hue = {}
        for k, fr in frames.items():
            roi = fr[y1:y2, x1:x2]
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            tot = max(1, roi.shape[0] * roi.shape[1])
            mr = int(cv2.countNonZero(cv2.bitwise_or(
                cv2.inRange(hsv, (0, 70, 60), (10, 255, 255)),
                cv2.inRange(hsv, (170, 70, 60), (180, 255, 255)))))
            my = int(cv2.countNonZero(cv2.inRange(hsv, (15, 70, 70), (35, 255, 255))))
            mg = int(cv2.countNonZero(cv2.inRange(hsv, (40, 60, 60), (90, 255, 255))))
            # 只看高饱和高亮像素的主色相（点亮的灯珠应该符合）
            m = (hsv[:, :, 1] > 90) & (hsv[:, :, 2] > 110)
            hh = hsv[:, :, 0][m]
            mh = float(np.median(hh)) if hh.size else -1
            main_hue[k] = mh
            out.append(f"  {k:8} {mr/tot*100:>7.1f}% {my/tot*100:>8.1f}% "
                       f"{mg/tot*100:>7.1f}% {float(hsv[:,:,2].mean()):>7.1f} {mh:>8.1f}")

        out.append("")
        out.append("  === 判定 ===")
        r_h, g_h, y_h = main_hue.get("Red", -1), main_hue.get("Green", -1), main_hue.get("Yellow", -1)
        out.append(f"  高饱和亮像素主色相: Red={r_h:.1f}  Green={g_h:.1f}  Yellow={y_h:.1f}")
        # 红灯主色相应接近 0/180；绿灯 40-90；黄灯 15-35
        def cls(h):
            if h < 0: return "无"
            if h < 12 or h > 168: return "红"
            if 14 <= h <= 36: return "黄"
            if 38 <= h <= 95: return "绿"
            return f"其他({h:.0f})"
        out.append(f"  三态主色相归类: Red->{cls(r_h)}  Green->{cls(g_h)}  Yellow->{cls(y_h)}")
        ok = (cls(r_h) == "红" and cls(g_h) == "绿")
        out.append(f"  -> {'✅ 灯头确实发光（用户判断成立）' if ok else '⚠ 未能证明发光，或色相判定需调参'}")

        # 放大展示
        tiles = []
        for k, fr in frames.items():
            t = fr[y1:y2, x1:x2].copy()
            sc = max(3, int(280 / max(1, t.shape[0])))
            t = cv2.resize(t, (t.shape[1] * sc, t.shape[0] * sc),
                           interpolation=cv2.INTER_NEAREST)
            cv2.putText(t, k, (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            tiles.append(t)
        hmax = max(t.shape[0] for t in tiles)
        tiles = [cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 0, 10,
                                    cv2.BORDER_CONSTANT, value=(25, 25, 25)) for t in tiles]
        grid = np.hstack(tiles)
        p = os.path.join(OUT, "tl_v3_compare.png")
        cv2.imwrite(p, grid)
        out.append("")
        out.append(f"  三态灯珠对比（放大）: {p}   尺寸 {grid.shape[1]}x{grid.shape[0]}")
    else:
        out.append("  -> ❌ 置不同灯态几乎不改变画面 -> 灯头不发光")

try:
    cam.stop(); cam.destroy()
except Exception:
    pass
st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)

io.open(r"E:\output\_tl_emit_test3.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
