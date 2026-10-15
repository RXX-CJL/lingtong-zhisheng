"""CARLA 红绿灯发光检验 v4 —— 相机后撤，拍到整根灯杆

用户的纠正（正确）：
  "一共三个灯珠，最上面黄灯下面绿灯，中间红灯，而且有亮灭区别"
  从 v3 的对比图确实能看到：左侧灯红色亮 + 绿色亮，右侧灯杆顶部绿色亮。

v1~v3 的错误：
  把相机架在"信号灯珠正前方 2.5m"，结果**灯珠不在画面里**
  （画面里可见的是别的灯杆）-> 一直在统计背景颜色 -> 结论错误。

v4 做法：
  ① 相机从灯珠位置**后撤 12m**（远到能看全整根灯杆 + 灯头）
  ② 正对灯面
  ③ Red / Green / Yellow 三态各拍一张
  ④ 用 Otsu 找**最亮的若干连通域**，看它们的色相是否随灯态改变
     —— 这是判"发光"的正确方法（发光灯珠 = 高饱和 + 高亮度 + 小面积）
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
lamp = sorted(lbs, key=lambda b: b.extent.x * b.extent.y * b.extent.z)[0]
out.append(f"灯 id={tl.id}  杆位置=({tl_tf.location.x:.1f},{tl_tf.location.y:.1f},"
           f"{tl_tf.location.z:.1f})  yaw={tl_tf.rotation.yaw:.1f}")
out.append(f"信号灯珠=({lamp.location.x:.2f},{lamp.location.y:.2f},{lamp.location.z:.2f})")

yaw = math.radians(tl_tf.rotation.yaw)
fx, fy = math.cos(yaw), math.sin(yaw)
DIST = 12.0
# 相机高度取灯珠高度（平视灯头），并稍微抬高一点以看全三颗灯
cam_loc = carla.Location(x=lamp.location.x + fx * DIST,
                         y=lamp.location.y + fy * DIST,
                         z=lamp.location.z + 0.6)
cam_rot = carla.Rotation(pitch=0.0, yaw=tl_tf.rotation.yaw + 180.0, roll=0.0)
out.append(f"相机=({cam_loc.x:.2f},{cam_loc.y:.2f},{cam_loc.z:.2f})  距灯珠 {DIST}m")

cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", "1280")
cam_bp.set_attribute("image_size_y", "960")
cam_bp.set_attribute("fov", "55")
cam = world.spawn_actor(cam_bp, carla.Transform(cam_loc, cam_rot))
q = queue.Queue()
cam.listen(q.put)

import cv2
import numpy as np


def grab():
    for _ in range(8):
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
        cv2.imwrite(os.path.join(OUT, f"v4_{name}.png"), f)
out.append(f"取到 {len(frames)} 种灯态")


def bright_blobs(img, topn=6):
    """找高饱和+高亮的小连通域 = 候选发光灯珠"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # 发光灯珠特征：饱和度较高 + 亮度很高
    m = ((hsv[:, :, 1] > 110) & (hsv[:, :, 2] > 150)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, cents = cv2.connectedComponentsWithStats(m, 8)
    res = []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < 8:
            continue
        mm = (lab == i)
        hh = hsv[:, :, 0][mm]
        ss = hsv[:, :, 1][mm]
        vv = hsv[:, :, 2][mm]
        res.append({
            "area": int(area),
            "hue": float(np.median(hh)),
            "sat": float(ss.mean()),
            "val": float(vv.mean()),
            "cx": float(cents[i][0]), "cy": float(cents[i][1]),
        })
    res.sort(key=lambda d: -d["area"])
    return res[:topn]


out.append("")
out.append("=" * 80)
out.append("各灯态下「高饱和+高亮」连通域（= 候选发光灯珠）")
out.append("=" * 80)
allb = {}
for k, fr in frames.items():
    blobs = bright_blobs(fr)
    allb[k] = blobs
    out.append(f"  [{k}] 找到 {len(blobs)} 个:")
    for b in blobs:
        col = ("红" if (b["hue"] < 12 or b["hue"] > 168) else
               "黄" if 14 <= b["hue"] <= 36 else
               "绿" if 38 <= b["hue"] <= 95 else f"H{b['hue']:.0f}")
        out.append(f"      area={b['area']:>5}  pos=({b['cx']:>6.0f},{b['cy']:>6.0f})  "
                   f"H={b['hue']:>5.1f} S={b['sat']:>5.0f} V={b['val']:>5.0f}  -> {col}")

# 判定：三态的色相分布应有区别
out.append("")
out.append("=" * 80)
out.append("判定")
out.append("=" * 80)
if len(frames) == 3:
    def hue_set(k):
        return sorted(round(b["hue"]) for b in allb.get(k, []))
    hr, hg, hy = hue_set("Red"), hue_set("Green"), hue_set("Yellow")
    out.append(f"  Red    态灯珠色相: {hr}")
    out.append(f"  Green  态灯珠色相: {hg}")
    out.append(f"  Yellow 态灯珠色相: {hy}")
    same = (hr == hg == hy)
    out.append("")
    if same:
        out.append("  -> ❌ 三态灯珠色相完全相同 -> 灯珠**不随状态变色**")
    else:
        out.append("  -> ✅ 三态灯珠色相**不同** -> 灯珠确实随状态变色（发光）")
    # 看是否有红/绿出现
    has_red = any(h < 12 or h > 168 for h in hr)
    has_green = any(38 <= h <= 95 for h in hg)
    out.append(f"  Red 态出现红色灯珠: {has_red}   Green 态出现绿色灯珠: {has_green}")

    # 并排放大灯头区域（用三态中任一 blobs 的包围盒）
    pts = [(b["cx"], b["cy"]) for k in allb for b in allb[k]]
    if pts:
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        pad = 60
        x1 = max(0, int(min(xs)) - pad); x2 = min(frames["Red"].shape[1], int(max(xs)) + pad)
        y1 = max(0, int(min(ys)) - pad); y2 = min(frames["Red"].shape[0], int(max(ys)) + pad)
        tiles = []
        for k, fr in frames.items():
            t = fr[y1:y2, x1:x2].copy()
            sc = max(2, int(320 / max(1, t.shape[0])))
            t = cv2.resize(t, (t.shape[1] * sc, t.shape[0] * sc), interpolation=cv2.INTER_NEAREST)
            cv2.putText(t, k, (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            tiles.append(t)
        hmax = max(t.shape[0] for t in tiles)
        tiles = [cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 0, 12,
                                    cv2.BORDER_CONSTANT, value=(25, 25, 25)) for t in tiles]
        grid = np.hstack(tiles)
        p = os.path.join(OUT, "tl_v4_compare.png")
        cv2.imwrite(p, grid)
        out.append("")
        out.append(f"  灯头区域三态对比: {p}  尺寸 {grid.shape[1]}x{grid.shape[0]}")

try:
    cam.stop(); cam.destroy()
except Exception:
    pass
st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)

io.open(r"E:\output\_tl_emit_test4.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
