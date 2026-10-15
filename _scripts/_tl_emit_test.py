"""检验用户质疑：CARLA 红绿灯是"灯头不发光"还是"太糊"？

我此前的结论建立在两点上：
  ① ROI 是从【缩放到 1280 宽】的帧上裁的（原帧 2560 宽）-> 已经糊了一半
  ② ROI 尺寸 50x129，我做了 HSV 统计

用户的质疑很合理："其实只是因为太糊了吧？"

本脚本要做的：
  · 在 CARLA 里把同一个红绿灯分别设为 Red / Green / Yellow
  · 每次都在【原生 2560x1440、不缩放】上裁剪灯框（并放大展示）
  · 比较三种状态下 ROI 的颜色分布是否**真的不同**
    - 若三种状态颜色分布几乎一样 -> 确实"不发光"（我的结论对）
    - 若红灯时红色显著增多     -> 是"太糊"（用户对）
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
m = world.get_map()

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)
out.append("同步模式已开")

# 找一个红绿灯，并在它附近架一台高分辨率相机（近距离拍灯，排除"太小"因素）
tls = list(world.get_actors().filter("traffic.traffic_light*"))
if not tls:
    out.append("未找到红绿灯，退出")
    io.open(r"E:\output\_tl_emit_test.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
    sys.exit(0)
tl = tls[0]
tl_loc = tl.get_location()
out.append(f"目标红绿灯 id={tl.id} 位置=({tl_loc.x:.1f},{tl_loc.y:.1f},{tl_loc.z:.1f})")

# 相机：架在灯的正前方 4 米、同高度附近，直视灯面（这样灯占画面比例很大）
cam_loc = carla.Location(x=tl_loc.x - 4.0, y=tl_loc.y, z=tl_loc.z + 0.3)
cam_rot = carla.Rotation(pitch=0.0, yaw=0.0, roll=0.0)
cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", "1280")
cam_bp.set_attribute("image_size_y", "720")
cam_bp.set_attribute("fov", "60")
cam = world.spawn_actor(cam_bp, carla.Transform(cam_loc, cam_rot))
q = queue.Queue()
cam.listen(q.put)
out.append(f"相机架在灯前 4m（画面 {1280}x{720}）")

import cv2
import numpy as np


def grab():
    world.tick()
    for _ in range(5):
        world.tick()
    try:
        img = q.get(timeout=15.0)
        return np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
            (img.height, img.width, 4))[:, :, :3].copy()
    except queue.Empty:
        return None


results = {}
for state_name, state_val in (("Red", carla.TrafficLightState.Red),
                              ("Green", carla.TrafficLightState.Green),
                              ("Yellow", carla.TrafficLightState.Yellow)):
    try:
        tl.set_state(state_val)
    except Exception as e:
        out.append(f"  set_state({state_name}) 失败: {str(e)[:60]}")
        continue
    frame = grab()
    if frame is None:
        out.append(f"  {state_name}: 取帧失败")
        continue
    results[state_name] = frame
    cv2.imwrite(os.path.join(OUT, f"tl_emit_{state_name}.png"), frame)

out.append("")
out.append("=" * 76)
out.append("三种灯态下的画面颜色统计（整幅画面，找出灯的位置）")
out.append("=" * 76)

if len(results) >= 2:
    # 先找"灯"在哪：用 Red 帧与其他帧的差异定位变化区域
    keys = list(results.keys())
    ref = results[keys[0]]
    changed = np.zeros(ref.shape[:2], dtype=np.uint8)
    for k in keys[1:]:
        d = cv2.absdiff(ref, results[k])
        g = cv2.cvtColor(d, cv2.COLOR_BGR2GRAY)
        changed = cv2.bitwise_or(changed, (g > 25).astype(np.uint8) * 255)

    n = int(cv2.countNonZero(changed))
    out.append(f"  三种灯态之间【画面发生变化】的像素: {n}")
    if n > 50:
        ys, xs = np.where(changed > 0)
        bx1, bx2, by1, by2 = xs.min(), xs.max(), ys.min(), ys.max()
        out.append(f"  变化区域 bbox = [{bx1},{by1},{bx2},{by2}]  "
                   f"尺寸 {bx2-bx1+1}x{by2-by1+1}")
        out.append("  -> ✅ 灯态切换确实改变了画面 -> 灯头是发光的（用户判断正确）")
    else:
        out.append("  -> ❌ 灯态切换【几乎没有改变画面】-> 灯头确实不发光")
        bx1, by1, bx2, by2 = 0, 0, ref.shape[1] - 1, ref.shape[0] - 1

    # 在变化区域内统计各灯态的颜色
    out.append("")
    out.append("  变化区域内各灯态的颜色占比:")
    out.append(f"     {'灯态':8} {'red%':>8} {'yellow%':>9} {'green%':>8} {'平均亮度V':>10}")
    for k, fr in results.items():
        roi = fr[by1:by2 + 1, bx1:bx2 + 1]
        if roi.size == 0:
            continue
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        tot = roi.shape[0] * roi.shape[1]
        mr = int(cv2.countNonZero(cv2.bitwise_or(
            cv2.inRange(hsv, (0, 70, 60), (10, 255, 255)),
            cv2.inRange(hsv, (170, 70, 60), (180, 255, 255)))))
        my = int(cv2.countNonZero(cv2.inRange(hsv, (15, 70, 70), (35, 255, 255))))
        mg = int(cv2.countNonZero(cv2.inRange(hsv, (40, 60, 60), (90, 255, 255))))
        vmean = float(hsv[:, :, 2].mean())
        out.append(f"     {k:8} {mr/tot*100:>7.1f}% {my/tot*100:>8.1f}% "
                   f"{mg/tot*100:>7.1f}% {vmean:>10.1f}")

    # 拼图：三态并排（放大变化区域）
    tiles = []
    pad = 30
    for k, fr in results.items():
        y1 = max(0, by1 - pad); y2 = min(fr.shape[0], by2 + pad)
        x1 = max(0, bx1 - pad); x2 = min(fr.shape[1], bx2 + pad)
        t = fr[y1:y2, x1:x2].copy()
        t = cv2.resize(t, (t.shape[1] * 3, t.shape[0] * 3), interpolation=cv2.INTER_NEAREST)
        cv2.putText(t, k, (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        tiles.append(t)
    hmax = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 0, 8,
                                cv2.BORDER_CONSTANT, value=(20, 20, 20)) for t in tiles]
    grid = np.hstack(tiles)
    p = os.path.join(OUT, "tl_emit_compare.png")
    cv2.imwrite(p, grid)
    out.append("")
    out.append(f"  三态对比图（放大变化区域 3 倍）: {p}")

try:
    cam.stop(); cam.destroy()
except Exception:
    pass
st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)

io.open(r"E:\output\_tl_emit_test.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
