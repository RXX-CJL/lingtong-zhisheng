"""CARLA 红绿灯发光检验 v2 —— 修正机位错误

v1 的错误：把相机放在灯杆**背面**（拍到灰色杆身），根本没拍到灯头，
所以"三态颜色一样"的结论无效。

v2 做法：
  ① 用灯的朝向（get_transform().rotation.yaw）把相机放在**灯面正前方**
  ② 相机对准灯头（用 bbox 中心而非底座 location）
  ③ 分别置 Red / Green / Yellow，各拍一张
  ④ 用**像素差分**定位真正变化的区域，再比较该区域颜色
     —— 若红灯时变化区偏红、绿灯时偏绿，则灯头**确实发光**
"""

import io
import math
import os
import queue
import sys

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

tls = list(world.get_actors().filter("traffic.traffic_light*"))
if not tls:
    out.append("无红绿灯")
else:
    tl = tls[0]
    tf = tl.get_transform()
    # 灯头中心（用 bounding box，而不是底座 location）
    bb = tl.bounding_box
    head = tf.transform(bb.location)
    out.append(f"灯 id={tl.id}")
    out.append(f"  transform 位置=({tf.location.x:.1f},{tf.location.y:.1f},{tf.location.z:.1f}) "
               f"yaw={tf.rotation.yaw:.1f} pitch={tf.rotation.pitch:.1f}")
    out.append(f"  bbox 中心(世界)=({head.x:.1f},{head.y:.1f},{head.z:.1f}) "
               f"尺寸={bb.extent.x*2:.2f}x{bb.extent.y*2:.2f}x{bb.extent.z*2:.2f}")

    # 沿灯面法线正前方放相机：CARLA 中 actor 前方是 +X（经 yaw 旋转）
    yaw = math.radians(tf.rotation.yaw)
    fx, fy = math.cos(yaw), math.sin(yaw)
    dist = 3.5
    cam_loc = carla.Location(x=head.x + fx * dist, y=head.y + fy * dist, z=head.z)
    # 相机看向灯 -> 朝向要指向灯的 -法线方向
    look_yaw = tf.rotation.yaw + 180.0
    cam_rot = carla.Rotation(pitch=0.0, yaw=look_yaw, roll=0.0)
    out.append(f"  相机放灯面正前方 {dist}m: ({cam_loc.x:.1f},{cam_loc.y:.1f},{cam_loc.z:.1f}) "
               f"yaw={look_yaw:.1f}")

    cam_bp = bp.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", "800")
    cam_bp.set_attribute("image_size_y", "600")
    cam_bp.set_attribute("fov", "45")
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
            cv2.imwrite(os.path.join(OUT, f"v2_{name}.png"), f)

    out.append("")
    out.append("=" * 74)
    out.append(f"取到 {len(frames)} 种灯态")
    out.append("=" * 74)

    if len(frames) >= 2:
        keys = list(frames.keys())
        # 两两差分，定位真正变化的区域
        masks = []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                d = cv2.absdiff(frames[keys[i]], frames[keys[j]])
                g = cv2.cvtColor(d, cv2.COLOR_BGR2GRAY)
                masks.append((g > 30).astype(np.uint8))
        changed = masks[0]
        for mk in masks[1:]:
            changed = cv2.bitwise_or(changed, mk)
        n = int(cv2.countNonZero(changed))
        out.append(f"  两两差分后【真正变化】的像素: {n}")

        if n < 20:
            out.append("  -> ❌ 置不同灯态对画面几乎无影响 -> **灯头不发光**")
            by1 = by2 = bx1 = bx2 = 0
        else:
            ys, xs = np.where(changed > 0)
            bx1, bx2, by1, by2 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
            out.append(f"  变化区域 bbox=[{bx1},{by1},{bx2},{by2}] "
                       f"尺寸 {bx2-bx1+1}x{by2-by1+1}")
            out.append("  -> ✅ 灯态切换改变了画面 -> 灯头**确实发光**（用户判断正确）")

        if n >= 20:
            out.append("")
            out.append(f"  {'灯态':8} {'red%':>8} {'yellow%':>9} {'green%':>8} {'亮度V':>7}")
            for k, fr in frames.items():
                roi = fr[by1:by2 + 1, bx1:bx2 + 1]
                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                tot = max(1, roi.shape[0] * roi.shape[1])
                mr = int(cv2.countNonZero(cv2.bitwise_or(
                    cv2.inRange(hsv, (0, 70, 60), (10, 255, 255)),
                    cv2.inRange(hsv, (170, 70, 60), (180, 255, 255)))))
                my = int(cv2.countNonZero(cv2.inRange(hsv, (15, 70, 70), (35, 255, 255))))
                mg = int(cv2.countNonZero(cv2.inRange(hsv, (40, 60, 60), (90, 255, 255))))
                out.append(f"  {k:8} {mr/tot*100:>7.1f}% {my/tot*100:>8.1f}% "
                           f"{mg/tot*100:>7.1f}% {float(hsv[:,:,2].mean()):>7.1f}")

            # 放大变化区域并排展示
            pad = 18
            tiles = []
            for k, fr in frames.items():
                y1 = max(0, by1 - pad); y2 = min(fr.shape[0], by2 + pad)
                x1 = max(0, bx1 - pad); x2 = min(fr.shape[1], bx2 + pad)
                t = fr[y1:y2, x1:x2].copy()
                sc = max(1, int(300 / max(1, t.shape[0])))
                t = cv2.resize(t, (t.shape[1] * sc, t.shape[0] * sc),
                               interpolation=cv2.INTER_NEAREST)
                cv2.putText(t, k, (5, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                tiles.append(t)
            hmax = max(t.shape[0] for t in tiles)
            tiles = [cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 0, 10,
                                        cv2.BORDER_CONSTANT, value=(25, 25, 25)) for t in tiles]
            grid = np.hstack(tiles)
            p = os.path.join(OUT, "tl_v2_compare.png")
            cv2.imwrite(p, grid)
            out.append("")
            out.append(f"  三态对比（放大变化区域）: {p}")

    try:
        cam.stop(); cam.destroy()
    except Exception:
        pass

st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)

io.open(r"E:\output\_tl_emit_test2.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
