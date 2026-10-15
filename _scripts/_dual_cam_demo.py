"""双摄闯红灯演示（用户 2026-10-04 提出的方案）

  CAM-1 全景（监控视角）  ：用户机位后移 4 m，看车辆轨迹与路口
  CAM-2 灯头特写（近摄）  ：装在灯面法向一侧，13 m 正对信号灯，专判灯色

两者都是**纯视觉摄像头**，判色只靠图像 —— 不读取 CARLA 内部状态，
因此和现实"电子警察"（全景枪机 + 灯态特写）做法一致。

产出：双摄视频（画中画）、两路逐帧真值 CSV、代表帧
"""
import csv
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

# ---------------- 配置
HOST, PORT = "127.0.0.1", 2000
FPS = 20.0
DT = 1.0 / FPS
OUTDIR = r"E:\output\_dual_cam_demo"
os.makedirs(OUTDIR, exist_ok=True)

# CAM-1 全景
W1, H1, FOV1 = 1920, 1080, 90.0
CAM1_BACK = 4.0
# CAM-2 灯头特写：正对 light 9 的左侧灯头（已用像素搜索确认能看到灯面）
W2, H2, FOV2 = 1280, 720, 60.0
CAM2_POS = (-32.74, -64.26, 5.15)
CAM2_PITCH, CAM2_YAW = 0.0, 180.0

LIGHT_ID = 9                      # 旧实例的编号，仅作参考；实际按地理位置找
STOP_X = -25.61
LANE1_Y, LANE2_Y = -64.7, -68.2
START_X = 34.0
RECORD_SECONDS = 26.0
PHASE_FRAMES = int(5.0 * FPS)

# ★2026-10-04：CARLA 重启后红绿灯 ID 会重新分配（旧 9 -> 新 62），
# 且 spectator 会回到默认值。所以改为：
#   1) 按地理位置的停止线坐标找灯（对重启免疫）
#   2) CAM-1 机位不再从 spectator 动态取，改为硬编码用户机位
KNOWN_STOP = (-25.61, -64.76)     # 目标灯的停止线（road7 lane1/2 进口道）
SPEC_BASE = (-19.720, -63.145, 5.732)   # 用户手动调好的机位
SPEC_PITCH, SPEC_YAW = -23.445, 179.536


def find_target_light(world):
    """按停止线地理坐标找控制 road7 lane1/2 的那盏灯（对 CARLA 重启免疫）。"""
    best = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        d = 1e9
        try:
            for wp in a.get_stop_waypoints():
                sl = wp.transform.location
                d = min(d, math.dist((sl.x, sl.y), KNOWN_STOP))
        except Exception:
            pass
        if best is None or d < best[0]:
            best = (d, a)
    return best

G, Y, R = (carla.TrafficLightState.Green,
           carla.TrafficLightState.Yellow,
           carla.TrafficLightState.Red)
PHASE_PLAN = [R, R, R, G, Y, R]      # 前 15 秒红灯，之后 5 秒一换


def log(m):
    print(m, flush=True)


class Proj:
    def __init__(self, tf, w, h, fov):
        self.loc = np.array([tf.location.x, tf.location.y, tf.location.z])
        self.w, self.h = w, h
        self.f = w / (2 * math.tan(math.radians(fov) / 2))
        p, y = math.radians(tf.rotation.pitch), math.radians(tf.rotation.yaw)
        cp, sp, cy, sy = math.cos(p), math.sin(p), math.cos(y), math.sin(y)
        # 行向量 = 相机三轴（右、上、前）在世界系中的表示
        # ★2026-10-04 修正：up 原写 [sp*cy, sp*sy, cp]，符号错了 -> 所有投影的 v 跑到画面外。
        #   正确：up = [-sp*cy, -sp*sy, cp]
        #   验证：yaw=-90、pitch=0 时 fwd 应朝 -Y；错式会给 +Y（朝后）。
        self.right = np.array([-sy, cy, 0.0])
        self.up = np.array([-sp * cy, -sp * sy, cp])
        self.fwd = np.array([cp * cy, cp * sy, -sp])

    def project(self, p):
        d = np.asarray(p, float) - self.loc
        z = float(d @ self.fwd)
        if z <= 1e-6:
            return None
        x = float(d @ self.right)
        y = float(d @ self.up)
        return (self.w / 2 + self.f * x / z, self.h / 2 - self.f * y / z, z)


def rgb_arr(img):
    return np.frombuffer(img.raw_data, np.uint8).reshape(img.height, img.width, 4)[:, :, :3].copy()


def main():
    client = carla.Client(HOST, PORT)
    client.set_timeout(60.0)
    world = client.get_world()
    if len(world.get_actors().filter("traffic.traffic_light*")) == 0:
        log("交通灯为 0，重新加载地图 ...")
        world = client.load_world("Town10HD_Opt")
        time.sleep(3)
    m = world.get_map()

    for v in world.get_actors().filter("vehicle.*"):
        v.destroy()

    found = find_target_light(world)
    if found is None:
        log("找不到控制 %s 的灯" % (KNOWN_STOP,))
        return 1
    d_stop, tl = found
    log("按地理位置选中 light id=%d（距已知停止线 %.2f m）" % (tl.id, d_stop))

    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = DT
    world.apply_settings(settings)
    tm = client.get_trafficmanager(8000)
    tm.set_synchronous_mode(True)
    tm.set_global_distance_to_leading_vehicle(3.5)

    # ★ CAM-1 机位：硬编码用户机位（不再依赖 spectator，重启后会丢）
    cam1_tf = carla.Transform(
        carla.Location(x=SPEC_BASE[0] + CAM1_BACK, y=SPEC_BASE[1], z=SPEC_BASE[2]),
        carla.Rotation(pitch=SPEC_PITCH, yaw=SPEC_YAW, roll=0.0))
    cam2_tf = carla.Transform(carla.Location(*CAM2_POS),
                              carla.Rotation(pitch=CAM2_PITCH, yaw=CAM2_YAW, roll=0.0))
    log("CAM-1 全景  (%.2f,%.2f,%.2f) pitch=%.1f yaw=%.1f  %dx%d" %
        (cam1_tf.location.x, cam1_tf.location.y, cam1_tf.location.z,
         cam1_tf.rotation.pitch, cam1_tf.rotation.yaw, W1, H1))
    log("CAM-2 特写  (%.2f,%.2f,%.2f) pitch=%.1f yaw=%.1f  %dx%d" %
        (cam2_tf.location.x, cam2_tf.location.y, cam2_tf.location.z,
         cam2_tf.rotation.pitch, cam2_tf.rotation.yaw, W2, H2))

    bpl = world.get_blueprint_library()

    def mk_cam(tf, w, h, fov):
        bp = bpl.find("sensor.camera.rgb")
        bp.set_attribute("image_size_x", str(w))
        bp.set_attribute("image_size_y", str(h))
        bp.set_attribute("fov", str(fov))
        try:
            bp.set_attribute("exposure_compensation", "0.5")
        except Exception:
            pass
        c = world.spawn_actor(bp, tf)
        buf = []
        c.listen(lambda im: buf.append(im))
        return c, buf

    c1, buf1 = mk_cam(cam1_tf, W1, H1, FOV1)
    c2, buf2 = mk_cam(cam2_tf, W2, H2, FOV2)

    # 两车
    def spawn(bp_id, x, y, tag):
        bp = bpl.filter(bp_id)[0]
        if bp.has_attribute("role_name"):
            bp.set_attribute("role_name", tag)      # role_name 是**蓝图**属性
        wp = m.get_waypoint(carla.Location(x=x, y=y, z=2.0), project_to_road=True,
                            lane_type=carla.LaneType.Driving)
        tr = wp.transform
        tr.location.z += 0.4
        a = world.spawn_actor(bp, tr)
        log("  %-12s id=%-4d at (%.1f,%.1f)" % (tag, a.id, tr.location.x, tr.location.y))
        return a

    v_law = spawn("vehicle.audi.a2", START_X, LANE2_Y, "law_abiding")
    v_run = spawn("vehicle.tesla.model3", START_X, LANE1_Y, "red_runner")
    vehicles = {"law_abiding": v_law, "red_runner": v_run}
    for tag, a in vehicles.items():
        a.set_autopilot(True, tm.get_port())
        tm.auto_lane_change(a, False)
    tm.ignore_lights_percentage(v_run, 100.0)
    log("  red_runner 无视红灯 100%%，两车 autopilot")

    proj1 = Proj(cam1_tf, W1, H1, FOV1)
    proj2 = Proj(cam2_tf, W2, H2, FOV2)

    csv_path = os.path.join(OUTDIR, "ground_truth_dual.csv")
    fcsv = open(csv_path, "w", newline="", encoding="utf-8")
    wtr = csv.writer(fcsv)
    wtr.writerow(["frame", "t_sec", "commanded_state", "readback_state",
                  "tag", "x", "y", "speed_kmh", "dist_to_stop_m", "crossed_stop",
                  "cam1_in", "cam1_u", "cam1_v"])

    total = int(RECORD_SECONDS * FPS)
    t0 = world.get_snapshot().timestamp.elapsed_seconds
    stats = {t: {"max": 0.0, "sum": 0.0, "n": 0, "stop": 0, "cross": None} for t in vehicles}
    MARKERS = [0, 60, 120, 160, 180, 200, 220, 260, 300, 320, 360, 440, 500]
    shots = {}

    log("\n开始录制 %d 帧 / %.0f 秒 ..." % (total, RECORD_SECONDS))
    for i in range(total):
        pi = min(i // PHASE_FRAMES, len(PHASE_PLAN) - 1)
        cmd = PHASE_PLAN[pi]
        tl.set_state(cmd)                     # 每帧强制 5 秒相位
        world.tick()
        t = world.get_snapshot().timestamp.elapsed_seconds - t0
        rb = str(tl.get_state())
        for tag, a in vehicles.items():
            tfv = a.get_transform()
            v = a.get_velocity()
            spd = 3.6 * math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2)
            x, y = tfv.location.x, tfv.location.y
            pr = proj1.project([x, y, tfv.location.z + 0.8])
            inf = 1 if (pr and 0 <= pr[0] < W1 and 0 <= pr[1] < H1) else 0
            s = stats[tag]
            s["max"] = max(s["max"], spd)
            s["sum"] += spd
            s["n"] += 1
            if spd < 0.5:
                s["stop"] += 1
            crossed = 1 if x < STOP_X else 0
            if crossed and s["cross"] is None:
                s["cross"] = round(t, 2)
            wtr.writerow([i, round(t, 3), str(cmd), rb, tag,
                          round(x, 3), round(y, 3), round(spd, 2),
                          round(x - STOP_X, 3), crossed, inf,
                          round(pr[0], 1) if pr else "", round(pr[1], 1) if pr else ""])
        if i % 40 == 0:
            log("   %4d/%d t=%5.2fs %-6s law=%.1f@x%.0f run=%.1f@x%.0f" %
                (i, total, t, str(cmd)[-3:],
                 stats["law_abiding"]["sum"] / max(1, stats["law_abiding"]["n"]),
                 v_law.get_transform().location.x,
                 stats["red_runner"]["sum"] / max(1, stats["red_runner"]["n"]),
                 v_run.get_transform().location.x))
        if i in MARKERS:
            shots[i] = (len(buf1) - 1, len(buf2) - 1)

    fcsv.close()
    time.sleep(1.0)
    for c in (c1, c2):
        c.stop()
        c.destroy()
    log("\n共抓到 CAM-1 %d 帧 / CAM-2 %d 帧" % (len(buf1), len(buf2)))

    # ---------------- 写双摄视频（画中画：CAM-2 贴右下角）
    vid = os.path.join(OUTDIR, "dual_cam_demo_lossless.mkv")
    vw = cv2.VideoWriter(vid, cv2.VideoWriter_fourcc(*"FFV1"), FPS, (W1, H1))
    if not vw.isOpened():
        log("!! FFV1 不可用")
        return 1
    n = min(len(buf1), len(buf2))
    for k in range(n):
        base = rgb_arr(buf1[k])
        pip = rgb_arr(buf2[k])
        # 右下角画中画，宽度 26%
        pw = int(W1 * 0.26)
        ph = int(pw * H2 / W2)
        small = cv2.resize(pip, (pw, ph), interpolation=cv2.INTER_AREA)
        x0, y0 = W1 - pw - 18, H1 - ph - 18
        base[y0 - 2:y0 + ph + 2, x0 - 2:x0 + pw + 2] = (40, 40, 40)
        base[y0:y0 + ph, x0:x0 + pw] = small
        cv2.rectangle(base, (x0 - 2, y0 - 2), (x0 + pw + 2, y0 + ph + 2), (0, 255, 255), 2)
        cv2.putText(base, "CAM-2 SIGNAL HEAD", (x0, y0 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(base, "CAM-1 SURVEILLANCE", (18, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (0, 255, 255), 2, cv2.LINE_AA)
        vw.write(base)
    vw.release()
    log("双摄视频: %s (%.1f MB, %d 帧)" % (vid, os.path.getsize(vid) / 1e6, n))

    # ---------------- 代表帧
    for mark, (i1, i2) in sorted(shots.items()):
        if 0 <= i1 < len(buf1):
            cv2.imwrite(os.path.join(OUTDIR, "cam1_%03d.png" % mark), rgb_arr(buf1[i1]))
        if 0 <= i2 < len(buf2):
            cv2.imwrite(os.path.join(OUTDIR, "cam2_%03d.png" % mark), rgb_arr(buf2[i2]))

    log("\n================ 结果 ================")
    for tag, s in stats.items():
        log("  %-12s avg=%5.1f max=%5.1f km/h  停车帧=%d  越线@t=%s"
            % (tag, s["sum"] / max(1, s["n"]), s["max"], s["stop"], s["cross"]))
    for a in vehicles.values():
        a.destroy()
    tm.set_synchronous_mode(False)
    settings.synchronous_mode = False
    settings.fixed_delta_seconds = None
    world.apply_settings(settings)
    tl.freeze(False)
    log("\n真值: %s" % csv_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
