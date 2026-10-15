# -*- coding: utf-8 -*-
"""CARLA **物理级**测速标定验证：已知地面点 -> 真实渲染 -> 检测像素 -> 与模型对照

★为什么要这一层（2026-10-06 由 DSH 建立）
  上一层验证（`_validate_speed_calibration.py`）用的是 YOLO 检测框，
  框的中心/底边与"车辆真实三维中心"之间有**几十像素的定义差**
  （车长一半、车高、遮挡、阴影都会掺进来）。
  本脚本把这件事做到物理级：在 CARLA 世界里**画/摆已知世界坐标的标记点**，
  让真实相机渲染出来，再用像素检测去测它们在画面上的位置 ——
  于是"世界坐标 <-> 像素"的对应关系**完全独立于任何投影公式**。

  验证两件事：
    ① 正投影：模型算出的像素 vs 渲染中实测的像素（像素误差）
    ② 反投影：把实测像素喂给 `speed_calibration.make_unprojector`
       反解出地面坐标，与标记点真实世界坐标比（米误差）
  顺带对照"已知错误基"（`_dual_cam_demo.Proj` 的 fwd_z=-sin p），
  说明它为什么不可用。

用法（**需要先启动 CARLA**；用 Python 3.12，那里装了 carla 0.9.16）：
    # 1) 启动 CARLA（另开一个窗口，等它加载完）
    E:\\output\\1\\carla\\CARLA_0.9.16\\CarlaUE4\\Binaries\\Win64\\CarlaUE4-Win64-Shipping.exe -carla-rpc-port=2000 -quality-level=Epic -nosound
    # 2) 跑本脚本（默认就是双摄演示那台相机的机位）
    & 'C:\\Users\\ROG\\AppData\\Local\\Programs\\Python\\Python312\\python.exe' -B E:\\output\\_scripts\\_carla_calibration_markers.py

可选参数：
    --x --y --z --pitch --yaw --fov --width --height   改机位/内参
    --out 输出目录（默认 E:\\output\\_calib_markers）
    --no-cones 只用 debug 画点（默认两者都做，取检测到的并集）
"""
import argparse
import csv
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, r"E:\output\1\api")
import speed_calibration as SC  # noqa: E402

# 双摄演示的 CAM-1 机位（_scripts\_dual_cam_demo.py）
DEF = dict(x=-15.720, y=-63.145, z=5.732, pitch=-23.445, yaw=179.536,
           fov=90.0, width=1920, height=1080)
CONE_IDS = ("static.prop.constructioncone", "static.prop.trafficcone01",
            "static.prop.trafficcone02", "static.prop.streetbarrier")
# 标记点网格：沿相机朝向的距离 × 横向偏移（米）
FORWARD_M = (7.0, 10.0, 14.0, 19.0, 25.0, 33.0, 43.0)
LATERAL_M = (-6.0, -3.0, 0.0, 3.0, 6.0)


def log(m):
    print(m, flush=True)


def project(x, y, z, loc, pitch, yaw, w, h, fov, broken=False):
    """针孔正投影。broken=True 用已知错误基（fwd_z=-sin p）做对照。"""
    p, yy = math.radians(pitch), math.radians(yaw)
    cp, sp, cy, sy = math.cos(p), math.sin(p), math.cos(yy), math.sin(yy)
    if broken:
        fwd = np.array([cp * cy, cp * sy, -sp])
        up = np.array([-sp * cy, -sp * sy, cp])
    else:
        fwd = np.array([cp * cy, cp * sy, sp])
        up = np.array([-sp * cy, -sp * sy, cp])
    right = np.array([-sy, cy, 0.0])
    f = w / (2.0 * math.tan(math.radians(fov) / 2.0))
    d = np.array([x - loc[0], y - loc[1], z - loc[2]])
    zc = float(d @ fwd)
    if zc <= 1e-6:
        return None
    return (w / 2.0 + f * float(d @ right) / zc,
            h / 2.0 - f * float(d @ up) / zc)


def rgb_arr(img):
    """CARLA raw_data 是 BGRA，[:, :, :3] 就是 BGR —— 绝不能再加 [::-1]"""
    return np.frombuffer(img.raw_data, np.uint8).reshape(
        img.height, img.width, 4)[:, :, :3].copy()


def main():
    ap = argparse.ArgumentParser()
    for k, v in DEF.items():
        ap.add_argument("--" + k, type=float if k != "width" and k != "height" else int,
                        default=v)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=2000)
    ap.add_argument("--out", default=r"E:\output\_calib_markers")
    ap.add_argument("--no-cones", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    import carla
    import cv2

    client = carla.Client(a.host, a.port)
    client.set_timeout(60.0)
    world = client.get_world()
    carla_map = world.get_map()
    loc = (a.x, a.y, a.z)
    log("CARLA 已连接 地图=%s" % carla_map.name)
    log("相机  世界(%.3f,%.3f,%.3f) pitch=%.3f yaw=%.3f fov=%.1f %dx%d"
        % (a.x, a.y, a.z, a.pitch, a.yaw, a.fov, a.width, a.height))

    # ---- 地面平面高度：用引擎自己的射线投射取相机脚下的路面 ----------
    plane_z = None
    try:
        gp = world.ground_projection(carla.Location(x=a.x, y=a.y, z=a.z + 2.0), 20.0)
        if gp is not None and getattr(gp, "location", None) is not None:
            plane_z = float(gp.location.z)
            log("地面投射: 相机脚下路面 z=%.3f  -> 相机离路面高度 h=%.3f m"
                % (plane_z, a.z - plane_z))
    except Exception as e:
        log("ground_projection 不可用(%s)，改用地图 waypoint 求路面高度" % e)
    if plane_z is None:
        wp = carla_map.get_waypoint(carla.Location(x=a.x, y=a.y, z=a.z),
                                    project_to_road=True)
        plane_z = float(wp.transform.location.z)
        log("waypoint 路面 z=%.3f -> h=%.3f m" % (plane_z, a.z - plane_z))
    h_above = a.z - plane_z

    st = world.get_settings()
    old_sync, old_dt = st.synchronous_mode, st.fixed_delta_seconds
    st.synchronous_mode = True
    st.fixed_delta_seconds = 0.05
    world.apply_settings(st)

    bp_lib = world.get_blueprint_library()
    cam_bp = bp_lib.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", str(a.width))
    cam_bp.set_attribute("image_size_y", str(a.height))
    cam_bp.set_attribute("fov", str(a.fov))
    tf = carla.Transform(carla.Location(*loc),
                         carla.Rotation(pitch=a.pitch, yaw=a.yaw, roll=0.0))
    cam = world.spawn_actor(cam_bp, tf)
    buf = []
    cam.listen(lambda im: buf.append(im))

    cones, markers = [], []
    try:
        # ---- 选标记点：沿相机朝向铺网格，吸附到路面 ------------------
        yr = math.radians(a.yaw)
        f2 = np.array([math.cos(yr), math.sin(yr)])
        r2 = np.array([-math.sin(yr), math.cos(yr)])
        for fwd in FORWARD_M:
            for lat in LATERAL_M:
                px = np.array([a.x, a.y]) + fwd * f2 + lat * r2
                try:
                    wp = carla_map.get_waypoint(
                        carla.Location(x=float(px[0]), y=float(px[1]), z=plane_z + 1.0),
                        project_to_road=True, lane_type=carla.LaneType.Driving)
                    wz = float(wp.transform.location.z)
                    snap = math.dist((float(px[0]), float(px[1])),
                                     (float(wp.transform.location.x),
                                      float(wp.transform.location.y)))
                except Exception:
                    continue
                if snap > 2.0 or abs(wz - plane_z) > 0.15:
                    continue                     # 不在同一水平路面 -> 跳过
                m = dict(fx=fwd, fy=lat, x=float(px[0]), y=float(px[1]), z=wz)
                pr = project(m["x"], m["y"], wz, loc, a.pitch, a.yaw, a.width, a.height, a.fov)
                m["pred_u"], m["pred_v"] = (pr if pr else (None, None))
                m["pred_broken"] = project(m["x"], m["y"], wz, loc, a.pitch, a.yaw,
                                           a.width, a.height, a.fov, broken=True)
                markers.append(m)
        log("标记点候选 %d 个（吸附后仍在同一路面、且模型可投影）" % len(markers))

        # ---- 基线帧（无标记）------------------------------------------
        for _ in range(3):
            world.tick()
        time.sleep(0.3)
        base = rgb_arr(buf[-1]) if buf else None

        # ---- 摆标记：真实道具 + debug 画点 ----------------------------
        cone_bp = None
        for cid in CONE_IDS:
            try:
                found = bp_lib.filter(cid)
                if len(found):
                    cone_bp = found[0]
                    break
            except Exception:
                pass
        if cone_bp is not None and not a.no_cones:
            for m in markers:
                try:
                    c = world.spawn_actor(cone_bp, carla.Transform(
                        carla.Location(m["x"], m["y"], m["z"] + 0.03)))
                    cones.append(c)
                    m["cone"] = 1
                except Exception:
                    m["cone"] = 0
            log("已摆放 %d 个 %s" % (len(cones), cone_bp.id))
        else:
            log("!! 未找到锥桶蓝图（或 --no-cones）—— 只用 debug 画点；"
                "若下面检测数为 0 说明 debug 层不进 RGB 相机，请改用锥桶")
            for m in markers:
                m["cone"] = 0
        for m in markers:
            try:
                world.debug.draw_point(
                    carla.Location(m["x"], m["y"], m["z"] + 0.25), size=0.35,
                    color=carla.Color(255, 0, 255), life_time=30.0)
            except Exception:
                pass

        for _ in range(5):
            world.tick()
        time.sleep(0.5)
        frame = rgb_arr(buf[-1]) if buf else None
        if frame is None or base is None:
            log("!! 没抓到画面，退出"); return 1

        # ---- 检测标记像素：与基线帧做差分（相机静止、场景静止 -> 只留下标记）----
        diff = cv2.absdiff(frame, base).max(axis=2)
        mask = (diff > 28).astype(np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, lab, stats, cent = cv2.connectedComponentsWithStats(mask, 8)
        blobs = [(stats[i, 4], cent[i][0], cent[i][1],
                  stats[i, 0], stats[i, 1], stats[i, 2], stats[i, 3])
                 for i in range(1, n) if stats[i, 4] >= 25]
        log("差分检测到 %d 个标记像素块（面积>=25px）" % len(blobs))
        if not blobs:
            log("!! 一个标记都没检测到：debug 点可能不进 RGB 相机；"
                "确认锥桶蓝图是否存在（列一下含 cone 的 static.prop）")
            for b in bp_lib.filter("static.prop.*"):
                if "cone" in b.id.lower() or "barrier" in b.id.lower():
                    log("   可用道具: %s" % b.id)
            return 1

        # ---- 匹配：每个标记点取最近的未占用像素块 ----------------------
        used, hits = set(), []
        for m in markers:
            if m["pred_u"] is None:
                continue
            best, bd = None, 1e9
            for k, b in enumerate(blobs):
                if k in used:
                    continue
                cx, cy = b[3] + b[5] / 2.0, b[4] + b[6]      # 块底边中点
                dd = math.hypot(cx - m["pred_u"], cy - m["pred_v"])
                if dd < bd:
                    best, bd = k, dd
            if best is None or bd > 70.0:
                continue
            used.add(best)
            b = blobs[best]
            hits.append(dict(m, det_u=b[3] + b[5] / 2.0, det_v=b[4] + b[6],
                             match_px=bd, area=int(b[0])))
        log("成功配对 %d 组「标记世界坐标 <-> 渲染像素」" % len(hits))
        if not hits:
            return 1

        # ---- 指标 ------------------------------------------------------
        up = SC.make_unprojector(h_above, a.pitch, a.fov, a.width, a.height, a.yaw)
        if up is None:
            log("!! make_unprojector 构造失败"); return 1
        px_err, m_err, broken_ok = [], [], 0
        for m in hits:
            pr = project(m["x"], m["y"], m["z"], loc, a.pitch, a.yaw,
                         a.width, a.height, a.fov)
            if pr:
                px_err.append(math.dist(pr, (m["det_u"], m["det_v"])))
            if m["pred_broken"]:
                broken_ok += 1
            g = up(m["det_u"], m["det_v"])
            if g is None:
                continue
            dd = np.array([m["x"] - a.x, m["y"] - a.y])
            truth = (float(dd @ f2), float(dd @ r2))
            m_err.append(math.hypot(g[0] - truth[0], g[1] - truth[1]))

        out_csv = os.path.join(a.out, "marker_correspondences.csv")
        with open(out_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["fx_m", "fy_m", "world_x", "world_y", "world_z",
                        "pred_u", "pred_v", "det_u", "det_v", "px_err",
                        "cone", "area", "ground_x", "ground_y", "err_m"])
            for m in hits:
                pr = project(m["x"], m["y"], m["z"], loc, a.pitch, a.yaw,
                             a.width, a.height, a.fov)
                g = up(m["det_u"], m["det_v"])
                dd = np.array([m["x"] - a.x, m["y"] - a.y])
                truth = (float(dd @ f2), float(dd @ r2))
                w.writerow([m["fx"], m["fy"], round(m["x"], 3), round(m["y"], 3),
                            round(m["z"], 3),
                            None if not pr else round(pr[0], 1),
                            None if not pr else round(pr[1], 1),
                            round(m["det_u"], 1), round(m["det_v"], 1),
                            None if not pr else round(math.dist(pr, (m["det_u"], m["det_v"])), 2),
                            m.get("cone"), m["area"],
                            None if not g else round(g[0], 3),
                            None if not g else round(g[1], 3),
                            None if not g else round(math.hypot(g[0] - truth[0],
                                                                g[1] - truth[1]), 3)])
        cv2.imwrite(os.path.join(a.out, "markers_frame.png"), frame)
        cv2.imwrite(os.path.join(a.out, "markers_baseline.png"), base)
        cv2.imwrite(os.path.join(a.out, "markers_mask.png"), mask * 255)
        log("已写出: %s / markers_frame.png / markers_mask.png" % out_csv)

        px_err.sort()
        m_err.sort()
        log("\n================ 结果 ================")
        log("相机离路面高度 h=%.3f m（用于 make_unprojector）" % h_above)
        log("① 正投影 像素误差: 平均 %.2f px  中位 %.2f  p90 %.2f  (n=%d)"
            % (sum(px_err) / len(px_err), px_err[len(px_err) // 2],
               px_err[int(0.9 * len(px_err))], len(px_err)))
        if m_err:
            log("② 反投影 米制误差: 平均 %.3f m  中位 %.3f  p90 %.3f  (n=%d)"
                % (sum(m_err) / len(m_err), m_err[len(m_err) // 2],
                   m_err[int(0.9 * len(m_err))], len(m_err)))
        log("③ 对照：已知错误基(fwd_z=-sin p) 只有 %d/%d 个点还能投影"
            % (broken_ok, len(hits)))
        ok = (sum(px_err) / len(px_err) < 6.0) and (not m_err or
                                                   sum(m_err) / len(m_err) < 0.6)
        log("判定: 像素误差<6px 且 米制误差<0.6m -> %s" % ("PASS" if ok else "FAIL"))
        return 0 if ok else 1
    finally:
        for c in cones + [cam]:
            try:
                c.stop()
            except Exception:
                pass
            try:
                c.destroy()
            except Exception:
                pass
        try:
            world.debug.clear_debug_lines()
        except Exception:
            pass
        st.synchronous_mode, st.fixed_delta_seconds = old_sync, old_dt
        try:
            world.apply_settings(st)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
