"""红绿灯判色验证（第 8 次）—— 裁紧 ROI，尺寸匹配训练分布

第 7 次的问题：
  方向(-1,0,0) 已找到灯面（红灯 650 红色像素，三态红px 676/1063/1066 有区别）
  但把【整幅 960x720】喂给 CNN -> 判 none（conf 0.9999）
  原因：CNN4 训练时用的是【紧贴灯头的裁剪图】，整幅图的尺寸/构图完全不符。

本次修正：
  ① 用相机投影把【信号头】的 8 个角点投到像素，得到紧贴灯头的 ROI
  ② 按训练时的习惯【外扩 25%】再喂 CNN
  ③ 三态各拍一张，对照真值
"""

import io
import math
import os
import queue
import sys

import carla

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

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

target = None
for tl in world.get_actors().filter("traffic.traffic_light*"):
    if tl.id == 17:
        target = tl
        break
if target is None:
    target = list(world.get_actors().filter("traffic.traffic_light*"))[0]
out.append(f"目标灯 id={target.id}")

lbs = target.get_light_boxes()
lamp = sorted(lbs, key=lambda b: b.extent.x * b.extent.y * b.extent.z)[0]
head = sorted(lbs, key=lambda b: -(b.extent.x * b.extent.y * b.extent.z))[0]
Hd = head.location
out.append(f"  信号头 loc=({Hd.x:.2f},{Hd.y:.2f},{Hd.z:.2f}) "
           f"ext=({head.extent.x:.3f},{head.extent.y:.3f},{head.extent.z:.3f})")

# 灯面方向 = (-1,0,0)（第 7 次实测）
DIR = (-1.0, 0.0, 0.0)
DIST = 6.0
cam_loc = carla.Location(x=Hd.x + DIR[0] * DIST, y=Hd.y + DIR[1] * DIST,
                         z=Hd.z + DIR[2] * DIST)
dx, dy, dz = Hd.x - cam_loc.x, Hd.y - cam_loc.y, Hd.z - cam_loc.z
yaw = math.degrees(math.atan2(dy, dx))
pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))

RES = (1280, 960)
FOV = 45.0
cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", str(RES[0]))
cam_bp.set_attribute("image_size_y", str(RES[1]))
cam_bp.set_attribute("fov", str(FOV))
cam_tf_obj = carla.Transform(cam_loc, carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0))
cam = world.spawn_actor(cam_bp, cam_tf_obj)
cam_tf = cam.get_transform()
q = queue.Queue()
cam.listen(q.put)
out.append(f"  相机=({cam_loc.x:.2f},{cam_loc.y:.2f},{cam_loc.z:.2f}) yaw={yaw:.1f} pitch={pitch:.1f} "
           f"距灯头 {DIST}m  {RES[0]}x{RES[1]} fov={FOV}")

f_px = RES[0] / (2.0 * math.tan(math.radians(FOV) / 2.0))


def _to_cam(P):
    inv = cam_tf.get_inverse_matrix()
    v = (P[0], P[1], P[2], 1.0)
    return tuple(sum(inv[i][j] * v[j] for j in range(4)) for i in range(4))


def project(P):
    p = _to_cam(P)
    if p[0] <= 0.1:
        return None
    return (RES[0] / 2.0 + f_px * (p[1] / p[0]), RES[1] / 2.0 - f_px * (p[2] / p[0]))


def head_px_bbox():
    """信号头 8 角点 -> 像素外接框"""
    us, vs = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                P = (Hd.x + sx * head.extent.x,
                     Hd.y + sy * head.extent.y,
                     Hd.z + sz * head.extent.z)
                pr = project(P)
                if pr:
                    us.append(pr[0]); vs.append(pr[1])
    if not us:
        return None
    return (min(us), min(vs), max(us), max(vs))


import cv2
import numpy as np

try:
    from traffic_light_classifier import classify_traffic_light
    have = True
except Exception as e:
    out.append(f"  分类器不可用: {e}")
    have = False


def grab_and_crop(state):
    target.set_state(state)
    for _ in range(8):
        world.tick()
    try:
        img = q.get(timeout=15.0)
        frame = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
            (img.height, img.width, 4))[:, :, :3].copy()
    except queue.Empty:
        return None, None
    bb = head_px_bbox()
    if bb is None:
        return frame, None
    x1, y1, x2, y2 = bb
    w, h = x2 - x1, y2 - y1
    px, py = int(w * 0.25), int(h * 0.25)
    cx1 = max(0, int(x1 - px)); cy1 = max(0, int(y1 - py))
    cx2 = min(RES[0], int(x2 + px)); cy2 = min(RES[1], int(y2 + py))
    roi = frame[cy1:cy2, cx1:cx2]
    return frame, (roi, (cx1, cy1, cx2, cy2))


out.append("")
out.append("=" * 80)
out.append("三态：投影定位灯头 -> 外扩25% 裁 ROI -> 喂 CNN")
out.append("=" * 80)

results = []
for name, val in (("Green", carla.TrafficLightState.Green),
                  ("Red", carla.TrafficLightState.Red),
                  ("Yellow", carla.TrafficLightState.Yellow)):
    frame, packed = grab_and_crop(val)
    if frame is None:
        out.append(f"  {name}: 取帧失败")
        continue
    cv2.imwrite(os.path.join(OUT, f"v8_{name}_full.png"), frame)
    if packed is None:
        out.append(f"  {name}: 灯头投影失败（可能不在画面内）")
        continue
    roi, bbox = packed
    cv2.imwrite(os.path.join(OUT, f"v8_{name}_roi.png"), roi)

    cnn, conf = ("n/a", 0.0)
    if have and roi.size > 0:
        cnn, conf = classify_traffic_light(roi)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mr = int(cv2.countNonZero(cv2.bitwise_or(
        cv2.inRange(hsv, (0, 110, 110), (10, 255, 255)),
        cv2.inRange(hsv, (170, 110, 110), (180, 255, 255)))))
    my = int(cv2.countNonZero(cv2.inRange(hsv, (15, 110, 130), (35, 255, 255))))
    mg = int(cv2.countNonZero(cv2.inRange(hsv, (40, 90, 90), (90, 255, 255))))
    results.append({"truth": name.lower(), "cnn": cnn, "conf": round(conf, 3),
                    "roi_shape": roi.shape, "bbox": bbox,
                    "mr": mr, "my": my, "mg": mg})
    out.append(f"  {name:7} ROI bbox={bbox} 尺寸={roi.shape[1]}x{roi.shape[0]}  "
               f"-> CNN={cnn} conf={conf:.3f}  红{mr} 黄{my} 绿{mg}")

out.append("")
out.append("=" * 80)
out.append("判色准确率")
out.append("=" * 80)
if results:
    tot = len(results)
    ok = sum(1 for r in results if r["cnn"] == r["truth"])
    out.append(f"  CNN 判对: {ok}/{tot} = {ok/tot*100:.0f}%")
    out.append("")
    out.append(f"  {'真值':8} {'CNN':>10} {'conf':>8}  说明")
    for r in results:
        note = "✅" if r["cnn"] == r["truth"] else "❌"
        out.append(f"  {r['truth']:8} {r['cnn']:>10} {r['conf']:>8}  {note}")
    # HSV 纯色法对照
    out.append("")
    out.append("  【对照】纯 HSV 最大占比法:")
    for r in results:
        m = max((r["mr"], "red"), (r["my"], "yellow"), (r["mg"], "green"))
        hit = "✅" if m[1] == r["truth"] else "❌"
        out.append(f"    真值={r['truth']:7} HSV法={m[1]:8} (红{r['mr']}/黄{r['my']}/绿{r['mg']}) {hit}")

    # 拼图
    tiles = []
    for name in ("Green", "Red", "Yellow"):
        p = os.path.join(OUT, f"v8_{name}_roi.png")
        if not os.path.exists(p):
            continue
        t = cv2.imread(p)
        sc = 300 / max(1, t.shape[0])
        t = cv2.resize(t, (max(1, int(t.shape[1] * sc)), 300), interpolation=cv2.INTER_NEAREST)
        cv2.putText(t, name, (6, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        tiles.append(t)
    if tiles:
        hmax = max(t.shape[0] for t in tiles)
        W_ = max(t.shape[1] for t in tiles)
        tiles = [cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 0, W_ - t.shape[1],
                                    cv2.BORDER_CONSTANT, value=(20, 20, 20)) for t in tiles]
        grid = np.hstack(tiles)
        p = os.path.join(OUT, "tl_v8_roi_compare.png")
        cv2.imwrite(p, grid)
        out.append("")
        out.append(f"  三态 ROI 对比: {p}")

try:
    cam.stop(); cam.destroy()
except Exception:
    pass
st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)

io.open(r"E:\output\_tl_verify8.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
