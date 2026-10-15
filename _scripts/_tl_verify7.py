"""红绿灯判色验证（第 7 次，这次条件齐备）

前 6 次失败的原因（已全部定位）：
  1-4 次：机位/坐标错（bounding_box.location 是局部坐标；灯面法线是 ±X 不是 ±Y）
  5 次  ：录 v4 视频时相机拍到的是场景里的广告牌，我误判为"地图边缘"
  6 次  ：验证判色时真值与画面不匹配 —— 但本轮已证明**【其实匹配】**
          （检测框 center=(2062,58) <-> tl_id=17，距离 12px）

第 6 次真正的失败原因是：**灯太小**
  检测框 23x52 px，信号灯珠 ext=(0.032,0.050,0.101) 在 ~180m 外 -> 只占 1-2 像素
  CNN 只能看到黄色灯箱 -> 判 yellow 是信息不足的必然结果

本脚本（条件齐备）：
  ① 连 CARLA，锁定 tl_id=17（已建立对应关系）
  ② 相机架在它灯珠前 **8 米**、正对灯面 —— 灯珠将占几十像素
  ③ 分别置 Green / Red / Yellow，各拍一张
  ④ 对每张图跑项目判色链路（CNN + 发光灯珠法），与真值对照
  ⑤ 输出放大图供人工核对
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

# ---- 锁定 tl_id=17 ----
target = None
for tl in world.get_actors().filter("traffic.traffic_light*"):
    if tl.id == 17:
        target = tl
        break
if target is None:
    target = list(world.get_actors().filter("traffic.traffic_light*"))[0]
out.append(f"目标灯 id={target.id}（v4 视频中已建立对应关系）")

lbs = target.get_light_boxes()
lamp = sorted(lbs, key=lambda b: b.extent.x * b.extent.y * b.extent.z)[0]
head = sorted(lbs, key=lambda b: -(b.extent.x * b.extent.y * b.extent.z))[0]
L = lamp.location
Hd = head.location
out.append(f"  灯珠 loc=({L.x:.2f},{L.y:.2f},{L.z:.2f}) ext=({lamp.extent.x:.3f},{lamp.extent.y:.3f},{lamp.extent.z:.3f})")
out.append(f"  信号头 loc=({Hd.x:.2f},{Hd.y:.2f},{Hd.z:.2f}) ext=({head.extent.x:.3f},{head.extent.y:.3f},{head.extent.z:.3f})")

# ---- 灯面法线：信号头 ext 最薄的方向 ----
ext = (head.extent.x, head.extent.y, head.extent.z)
thin_axis = min(range(3), key=lambda i: ext[i])
out.append(f"  信号头最薄的轴 = {'xyz'[thin_axis]} (ext={ext[thin_axis]:.3f}) -> 灯面法线是 ±{'XYZ'[thin_axis]}")

# CARLA 相机默认朝向 +X；我们把相机放在 信号头 沿法线的两侧，取"能看到灯面"的一侧
# 判据：灯珠相对信号头中心的偏移方向 = 灯面朝向（灯珠在灯面上）
off = (L.x - Hd.x, L.y - Hd.y, L.z - Hd.z)
out.append(f"  灯珠相对信号头偏移 = ({off[0]:.3f},{off[1]:.3f},{off[2]:.3f})")

# 相机方向：沿 thin_axis 的两个方向各试，用"画面里红/绿发光像素数"判定
cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", "960")
cam_bp.set_attribute("image_size_y", "720")
cam_bp.set_attribute("fov", "45")

import cv2
import numpy as np


def shoot(direction, dist, state):
    """把相机放在 head 沿 direction 方向 dist 米处，朝灯拍一张"""
    tgt = carla.Location(x=Hd.x, y=Hd.y, z=Hd.z)
    cam_loc = carla.Location(x=Hd.x + direction[0] * dist,
                            y=Hd.y + direction[1] * dist,
                            z=Hd.z + direction[2] * dist)
    # 朝向灯：yaw/pitch 由向量算
    dx = tgt.x - cam_loc.x
    dy = tgt.y - cam_loc.y
    dz = tgt.z - cam_loc.z
    yaw = math.degrees(math.atan2(dy, dx))
    horiz = math.hypot(dx, dy)
    pitch = math.degrees(math.atan2(dz, horiz))
    cam = world.spawn_actor(cam_bp, carla.Transform(
        cam_loc, carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0)))
    q = queue.Queue()
    cam.listen(q.put)
    target.set_state(state)
    for _ in range(8):
        world.tick()
    frame = None
    try:
        img = q.get(timeout=15.0)
        frame = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
            (img.height, img.width, 4))[:, :, :3].copy()
    except queue.Empty:
        pass
    try:
        cam.stop(); cam.destroy()
    except Exception:
        pass
    return frame


# 两个候选方向
axes = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)]
out.append("")
out.append("=" * 78)
out.append("第一步：找出能拍到灯面的方向（用红灯时『红色发光像素数』判定）")
out.append("=" * 78)
best_dir, best_score, probe = None, -1, {}
for d in axes:
    f = shoot(d, 8.0, carla.TrafficLightState.Red)
    if f is None:
        out.append(f"  方向{d}: 取帧失败")
        continue
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    red_m = cv2.bitwise_or(cv2.inRange(hsv, (0, 120, 120), (10, 255, 255)),
                           cv2.inRange(hsv, (170, 120, 120), (180, 255, 255)))
    nred = int(cv2.countNonZero(red_m))
    probe[d] = f
    out.append(f"  方向{d}: 红色高饱和亮像素 = {nred}")
    if nred > best_score:
        best_score, best_dir = nred, d
out.append(f"  -> 最佳方向 = {best_dir}（{best_score} 个红色像素）")

if best_dir is None:
    out.append("未能找到灯面方向，退出")
else:
    out.append("")
    out.append("=" * 78)
    out.append(f"第二步：沿 {best_dir} 方向拍三种灯态，做真值对照")
    out.append("=" * 78)

    try:
        from traffic_light_classifier import classify_traffic_light, hsv_fallback_state
        have_cls = True
    except Exception as e:
        out.append(f"  分类器导入失败: {e}")
        have_cls = False

    frames = {}
    for name, val in (("Green", carla.TrafficLightState.Green),
                      ("Red", carla.TrafficLightState.Red),
                      ("Yellow", carla.TrafficLightState.Yellow)):
        f = shoot(best_dir, 8.0, val)
        if f is not None:
            frames[name] = f
            cv2.imwrite(os.path.join(OUT, f"v7_{name}.png"), f)

    out.append(f"  拍到 {len(frames)} 种灯态")

    if have_cls and frames:
        out.append("")
        out.append(f"  {'真值':8} {'CNN判定':>10} {'CNNconf':>8} "
                   f"{'红px':>7} {'黄px':>7} {'绿px':>7}")
        ok = 0
        tot = 0
        for name, f in frames.items():
            # 用整幅（灯占画面主体）
            cnn, conf = classify_traffic_light(f)
            hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
            mr = int(cv2.countNonZero(cv2.bitwise_or(
                cv2.inRange(hsv, (0, 110, 110), (10, 255, 255)),
                cv2.inRange(hsv, (170, 110, 110), (180, 255, 255)))))
            my = int(cv2.countNonZero(cv2.inRange(hsv, (15, 110, 130), (35, 255, 255))))
            mg = int(cv2.countNonZero(cv2.inRange(hsv, (40, 90, 90), (90, 255, 255))))
            truth = name.lower()
            tot += 1
            hit = (cnn == truth)
            ok += int(hit)
            out.append(f"  {name:8} {cnn:>10} {conf:>8} {mr:>7} {my:>7} {mg:>7}  "
                       f"{'✅' if hit else '❌'}")
        out.append("")
        out.append(f"  CNN 判对: {ok}/{tot} = {ok/tot*100:.0f}%")

        # 拼图
        tiles = []
        for name, f in frames.items():
            t = cv2.resize(f, (400, 300), interpolation=cv2.INTER_AREA)
            cv2.putText(t, name, (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            tiles.append(t)
        grid = np.hstack(tiles)
        p = os.path.join(OUT, "tl_v7_states.png")
        cv2.imwrite(p, grid)
        out.append(f"  三态对比图: {p}")

st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)

io.open(r"E:\output\_tl_verify7.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
