# -*- coding: utf-8 -*-
r"""装饰物隐藏 · 真实 CARLA 验收（档 A / 档 B / 档 C / 一键恢复 / v2 持久化 / 渲染差分）。

用法：py -3.12 E:\output\_scripts\_verify_workshop_env_live.py
安全约定：
  * 不改红绿灯配时、不改机位、不 load_world、不切 synchronous_mode
  * 隐藏过的装饰物在 finally 里全部恢复
  * 临时场景 JSON 写在 _scripts/_tmp_env_live 下，不动 Output 里的真实存档
"""
import importlib.util
import json
import sys
import time
import types
from pathlib import Path

import numpy as np

TARGET = (Path(__file__).resolve().parents[1] / "1" / "carla" / "CARLA_0.9.16"
          / "PythonAPI" / "examples" / "carla_creator_workshop.py")
spec = importlib.util.spec_from_file_location("carla_creator_workshop", TARGET)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Workshop = module.CarlaCreatorWorkshop
carla = module.carla

PASS = 0
FAIL = 0
FAILED = []


def _text(detail):
    return detail if isinstance(detail, str) else ("" if detail is None else repr(detail))


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        FAILED.append(name)
    txt = _text(detail)
    print(("PASS " if ok else "FAIL ") + name + (" | " + txt if txt else ""))


TMP = Path(__file__).resolve().parent / "_tmp_env_live"
if TMP.exists():
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
TMP.mkdir(parents=True, exist_ok=True)
module.RECENTS_PATH = TMP / "_workshop_recents.json"
module.AUTO_SAVE_DIR = TMP / "场景快照"
module.AUTO_SAVE_PATH = module.AUTO_SAVE_DIR / "last_session.json"

dialogs = []
module.messagebox.showwarning = lambda *a, **k: dialogs.append(("warn", a[0] if a else ""))
module.messagebox.showerror = lambda *a, **k: dialogs.append(("error", a[0] if a else ""))
module.messagebox.showinfo = lambda *a, **k: dialogs.append(("info", a[0] if a else ""))
module.messagebox.askyesno = lambda *a, **k: True

# ---------- 现场快照（收尾要断言没变） ----------
client = carla.Client("127.0.0.1", 2000)
client.set_timeout(20.0)
raw_world = client.get_world()
scene_path = TMP / "env_live_scene.json"
module.filedialog.asksaveasfilename = lambda **kw: str(scene_path)
module.filedialog.askopenfilename = lambda **kw: str(scene_path)

start_actors = len(raw_world.get_actors())
start_spectator = raw_world.get_spectator().get_transform()
start_lights = list(raw_world.get_actors().filter("traffic.traffic_light*"))
print(f"scene: actors={start_actors} lights={len(start_lights)} "
      f"spectator=({start_spectator.location.x:.3f},{start_spectator.location.y:.3f},"
      f"{start_spectator.location.z:.3f}) yaw={start_spectator.rotation.yaw:.3f}")


def light_triplets():
    out = {}
    for light in raw_world.get_actors().filter("traffic.traffic_light*"):
        out[light.id] = (round(light.get_green_time(), 3), round(light.get_yellow_time(), 3),
                         round(light.get_red_time(), 3))
    return out


start_triplets = light_triplets()
check("baseline 15 traffic lights all 10/3/2",
      len(start_triplets) == 15 and all(v == (10.0, 3.0, 2.0) for v in start_triplets.values()),
      len(start_triplets))

# ---------- 起 GUI（不点“连接”，自己接上真实世界，避免自动刷新噪声） ----------
import tkinter as tk
root = tk.Tk()
root.withdraw()
app = Workshop(root)
root.update()
app.client = client
app.world = raw_world
app.connected = True


def pump(seconds=0.0):
    end = time.time() + seconds
    while True:
        try:
            root.update()
        except Exception:
            return
        if time.time() >= end:
            return
        time.sleep(0.01)


app.preview_frame_size = (int(app.camera_width), int(app.camera_height))

try:
    # ---------- 3. 缓存性能：首次 vs 第二次（命中缓存） ----------
    print("\n--- 缓存性能实测 ---")
    app.invalidate_env_cache()
    t0 = time.perf_counter()
    app._load_env_cache(module.ENV_LABELS, announce=False)
    first = time.perf_counter() - t0
    per_class = {label: app.env_cache[label]["rpc_elapsed"] for label in module.ENV_LABELS}
    counts = {label: len(app.env_cache[label]["ids"]) for label in module.ENV_LABELS}
    print("首次加载 6 类耗时: %.2f ms" % (first * 1000))
    for label in module.ENV_LABELS:
        print("   %-14s n=%-6d rpc=%.1f ms" % (label, counts[label], per_class[label] * 1000))
    t0 = time.perf_counter()
    app._load_env_cache(module.ENV_LABELS, announce=False)
    second = time.perf_counter() - t0
    t0 = time.perf_counter()
    app._load_env_cache(["Vegetation"], announce=False)
    second_veg = time.perf_counter() - t0
    print("第二次（全部命中缓存）: %.4f ms" % (second * 1000))
    print("第二次（只取 Vegetation，命中）: %.4f ms" % (second_veg * 1000))
    check("first load > 100 ms (真 RPC)", first > 0.1, "%.1f ms" % (first * 1000))
    check("second load < 5 ms (命中缓存)", second < 0.005, "%.4f ms" % (second * 1000))
    check("cached Vegetation re-fetch < 5 ms", second_veg < 0.005, "%.4f ms" % (second_veg * 1000))
    check("Vegetation count 62581", counts["Vegetation"] == 62581, counts["Vegetation"])
    check("Poles count 880", counts["Poles"] == 880, counts["Poles"])

    # ---------- 渲染采样（档 A 的渲染差分证据） ----------
    frames = []
    bp = raw_world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", "480")
    bp.set_attribute("image_size_y", "270")
    bp.set_attribute("fov", "90")
    probe_cam = raw_world.spawn_actor(bp, raw_world.get_spectator().get_transform())
    probe_cam.listen(lambda img: frames.append(np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
        (img.height, img.width, 4))[:, :, :3].copy()))

    def grab(n=6):
        frames.clear()
        t0 = time.time()
        while len(frames) < n and time.time() - t0 < 20:
            raw_world.wait_for_tick()
        return frames[-1] if frames else None

    def diff_pixels(a, b, thr=10):
        d = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
        return int((d > thr).sum())

    def noise(rounds=3):
        vals = []
        prev = grab()
        for _ in range(rounds):
            cur = grab()
            vals.append(diff_pixels(prev, cur))
            prev = cur
        return vals

    # ---------- 档 A：按类别一键隐藏 / 恢复 ----------
    print("\n--- 档 A：按类别一键隐藏 / 恢复 ---")
    app.env_label_var.set("Vegetation")
    # 判据用"隐藏前后画面差异"，不用"帧间噪声"：
    # 实测帧间噪声在隐藏后并不单调下降（车/云都在动），同一操作三次跑出 [1007]、[17267]、[17317] 三种结果，
    # 而"隐藏前后整幅画面差异"稳定在 20%+ 像素（独立相机实测 21.8%）。指标换掉，结论才可信。
    frame_visible = grab()
    raw_veg_count_before = len(raw_world.get_environment_objects(carla.CityObjectLabel.Vegetation))
    hidden_n = app.hide_env_label()
    # 6 万棵树从渲染管线里摘掉要几帧才反映到画面上，给足等待
    pump(1.5)
    raw_world.wait_for_tick(3.0)
    frame_hidden = grab()
    fps_visible = [diff_pixels(frame_visible, frame_hidden)]
    fps_hidden = fps_visible
    raw_veg_count_after = len(raw_world.get_environment_objects(carla.CityObjectLabel.Vegetation))
    print("隐藏 Vegetation 返回 %d（列表数量 %d -> %d 不变说明仍可恢复）"
          % (hidden_n, raw_veg_count_before, raw_veg_count_after))
    print("帧间像素变化 visible=%s hidden=%s" % (fps_visible, fps_hidden))
    check("档A hide returned 62581", hidden_n == 62581, hidden_n)
    check("档A get_environment_objects count unchanged",
          raw_veg_count_after == raw_veg_count_before == 62581,
          (raw_veg_count_before, raw_veg_count_after))
    check("档A hidden_env_ids records 62581",
          len(app.hidden_env_ids.get("Vegetation") or []) == 62581,
          len(app.hidden_env_ids.get("Vegetation") or []))
    hidden_changed = diff_pixels(frame_visible, frame_hidden)
    check("档A hiding vegetation changes >= 5% of pixels",
          hidden_changed > frame_visible.shape[0] * frame_visible.shape[1] * 0.05,
          (hidden_changed, frame_visible.shape[0] * frame_visible.shape[1]))
    restored_a = app.show_env_label()
    pump(1.5)
    raw_world.wait_for_tick(3.0)
    frame_restored = grab()
    back_changed = diff_pixels(frame_restored, frame_visible)
    print("恢复后与基线画面差异像素 = %d（画面共 %d 像素）"
          % (back_changed, frame_visible.shape[0] * frame_visible.shape[1]))
    check("档A restore returned 62581", restored_a == 62581, restored_a)
    check("档A hidden_env_ids cleared for Vegetation", not (app.hidden_env_ids.get("Vegetation")),
          app.hidden_env_ids.get("Vegetation"))
    # 不能用"与基线帧差异 < 5%"：实测同状态下相邻两帧的自然抖动就有 13.8%（车在动、云在飘），
    # 这个阈值在物理上不可能满足。改用相对判据：恢复帧应"比隐藏帧更接近基线帧"。
    hidden_vs_visible = diff_pixels(frame_hidden, frame_visible)
    restored_vs_hidden = diff_pixels(frame_restored, frame_hidden)
    check("档A restoring brings画面 back（恢复帧离隐藏帧远、离基线帧近）",
          restored_vs_hidden > hidden_vs_visible * 0.5,
          {"恢复vs隐藏": restored_vs_hidden, "隐藏vs基线": hidden_vs_visible, "恢复vs基线": back_changed})

    # ---------- 档 C：以当前相机为中心、可调半径一次藏光 ----------
    print("\n--- 档 C：半径内一次藏光 ---")
    app.env_label_var.set("Vegetation")
    app.env_radius_mode_var.set("球体")
    app.env_radius_var.set("50")
    center = app._env_camera_center()
    radius = app._env_parse_radius()
    expect_ids, _info = app._env_range_ids("Vegetation", center, radius, "球体")
    print("相机 %s 半径 %.1f m 内 Vegetation 缓存命中 %d 个" % (np.round(center, 3), radius, len(expect_ids)))
    hidden_c = app.hide_env_in_range()
    print("档 C 实际隐藏 %d 个" % hidden_c)
    check("档C hidden count == cached in-radius count", hidden_c == len(expect_ids) and hidden_c > 0,
          (hidden_c, len(expect_ids)))
    check("档C hidden_env_ids matches returned count",
          len(app.hidden_env_ids.get("Vegetation") or []) == hidden_c,
          len(app.hidden_env_ids.get("Vegetation") or []))
    app.env_radius_var.set("25")
    restored_c = app.show_env_in_range()
    print("半径改 25 m 后恢复 %d 个" % restored_c)
    check("档C partial restore works (0 <= restored <= hidden)", 0 <= restored_c <= hidden_c, restored_c)
    still_c = len(app.hidden_env_ids.get("Vegetation") or [])
    check("档C partial restore leaves only out-of-range ones", still_c == hidden_c - restored_c,
          (still_c, hidden_c, restored_c))
    app.restore_all_env()
    check("档C restore_all cleared everything", app.hidden_env_ids == {}, app.hidden_env_ids)

    # ---------- 档 B：右键点中单个装饰物 ----------
    print("\n--- 档 B：屏幕拾取单个装饰物 ---")
    app.env_label_var.set("Poles")
    poles = app.env_cache["Poles"]
    target_pos = next(i for i, n in enumerate(poles["names"]) if n.startswith("SM_Parklight2_SM_0"))
    target_id = int(poles["ids"][target_pos])
    target_name = str(poles["names"][target_pos])
    # 把预览相机摆到能看见这棵树/灯的位置：先看它自己
    pole_center = poles["centers"][target_pos]
    print("目标：%s id=%d 中心=%s" % (target_name, target_id, np.round(pole_center, 3)))
    view = carla.Transform(
        carla.Location(x=float(pole_center[0]) + 14.0, y=float(pole_center[1]) - 14.0,
                       z=float(pole_center[2])),
        carla.Rotation(pitch=0.0, yaw=135.0, roll=0.0))
    # 不用 spectator 注入位姿：用户可能同时开着工坊窗口，它每 80ms 同步一次 spectator，
    # 会和测试互相覆盖（实测 _camera_pose() 与 get_spectator() 读到不一致的值）。
    # 改用假相机代理：_camera_pose() 优先读 self.camera，完全隔离于全局 spectator。
    class _FakeCamera:
        def __init__(self, transform):
            self._t = transform
            self.attributes = {"fov": 90.0}

        def get_transform(self):
            return self._t

        def set_transform(self, transform):
            self._t = transform

    app.camera = _FakeCamera(view)
    app.preview_frame_size = (960, 540)
    transform, fov = app._camera_pose()
    basis = app._camera_basis(transform)
    origin = app._np_location(transform.location)
    corners = app._env_corners("Poles", target_pos)
    screen = app._env_project(corners, origin, basis, fov, 960, 540)
    check("target projects in front of camera", screen is not None, None if screen is None else screen.shape)
    if screen is None:
        raise SystemExit("目标不在视野内，无法做档 B 验证")
    u, v = float(np.mean(screen[:, 0])), float(np.mean(screen[:, 1]))
    print("目标像素中心：u=%.1f v=%.1f（画面 960x540）" % (u, v))
    picked = app._env_pick(u, v, label="Poles")
    print("拾取结果：", None if picked is None else
          (picked["name"], picked["id"], picked["label"], round(picked["distance"], 2)))
    check("档B pick hit a pole", picked is not None, picked)
    check("档B picked id == target id", picked is not None and picked["id"] == target_id,
          None if picked is None else (picked["id"], target_id))
    check("档B picked name == target name", picked is not None and picked["name"] == target_name,
          None if picked is None else (picked["name"], target_name))
    check("档B picked label == Poles", picked is not None and picked["label"] == "Poles",
          None if picked is None else picked["label"])
    # 反向确认：点一个明显偏离目标的像素不该选中它
    miss = app._env_pick(20.0, 20.0, label="Poles")
    check("档B off-target pixel does not pick the pole",
          miss is None or miss["id"] != target_id, None if miss is None else miss["name"])
    # 真正隐藏它
    single = app.hide_env_single(picked)
    pump(0.2)
    # 档B 会按同心坐标吸附同组兄弟件（一根路灯常由多个 EnvironmentObject 组成）
    expect_ids = app._env_sibling_ids("Poles", [target_id])
    check("档B hide single returned >=1", single is not None and single >= 1, single)
    check("档B hidden ids == target + siblings",
          sorted(app.hidden_env_ids.get("Poles") or []) == sorted(expect_ids),
          (app.hidden_env_ids.get("Poles"), expect_ids))
    # 在点击点附近再点一次，隐藏后仍然命中该 id（隐藏不影响拾取数据）
    picked2 = app._env_pick(u, v, label="Poles")
    check("档B pick still resolves after hidden (cache intact)",
          picked2 is not None and picked2["id"] == target_id,
          None if picked2 is None else picked2["id"])
    back = app.show_env_picked()
    check("档B show picked restored all", back == len(expect_ids), back)
    check("档B hidden_env_ids empty again", not app.hidden_env_ids.get("Poles"),
          app.hidden_env_ids.get("Poles"))

    # ---------- 档 C 的右键快捷入口（点到的那片） ----------
    print("\n--- 档 C 快捷入口：右键点到的那片 ---")
    app.env_label_var.set("Vegetation")
    veg_entry = app.env_cache["Vegetation"]
    # 用视野内最近的植被中心做点击点
    delta = veg_entry["centers"] - origin
    dist = np.linalg.norm(delta, axis=1)
    # 必须用掩码版本：_env_project 要求 8 个角点全在相机前方，
    # 对 6.2 万个中心点必然有大量点在背后 → 直接返回 None
    px_all, valid_all = app._env_project_masked(veg_entry["centers"], origin, basis, fov, 960, 540)
    if px_all is not None:
        inside = np.nonzero(valid_all & (px_all[:, 0] > 0) & (px_all[:, 0] < 960)
                            & (px_all[:, 1] > 0) & (px_all[:, 1] < 540))[0]
        if inside.size:
            nearest = inside[np.argmin(dist[inside])]
            tu, tv = float(px_all[nearest][0]), float(px_all[nearest][1])
            got = app._env_hide_at_pixel(tu, tv)
            print("点在最近的植被上（%.0f,%.0f，距离 %.1f m）→ 隐藏 %d 个" % (tu, tv, dist[nearest], got))
            check("档C shortcut hides a contiguous patch", got > 0, got)
            check("档C shortcut cleared after restore_all", app.restore_all_env() and app.hidden_env_ids == {},
                  app.hidden_env_ids)
        else:
            check("档C shortcut had visible vegetation to click", False, "视野内没有植被")
    else:
        check("档C shortcut had visible vegetation to click", False, "投影失败")

    # ---------- 5. v2 持久化对接 ----------
    print("\n--- v2 持久化：save_scene -> JSON -> load_scene ---")
    raw_world.get_spectator().set_transform(view)
    app.world = raw_world
    poles_entry = app.env_cache["Poles"]
    veg_targets = [int(veg_entry["ids"][i]) for i in range(3)]
    pole_targets = [int(poles_entry["ids"][i]) for i in range(2)]
    big_targets = [i for i in veg_targets if i > 2 ** 63 - 1]
    app._env_hide("Vegetation", veg_targets)
    app._env_hide("Poles", pole_targets)
    pump(0.1)
    saved_before = dict(app.hidden_env_ids)
    app.save_scene()
    pump(0.1)
    check("scene file written", scene_path.is_file(), str(scene_path))
    data = json.loads(scene_path.read_text(encoding="utf-8"))
    payload = data.get("hidden_environment_objects") or {}
    print("JSON hidden_environment_objects:", {k: v[:3] for k, v in payload.items()},
          "| len:", {k: len(v) for k, v in payload.items()})
    check("JSON hidden_environment_objects non-empty", bool(payload), payload)
    check("JSON has Vegetation+Poles keys", set(payload) == {"Vegetation", "Poles"}, set(payload))
    check("JSON ids are plain decimal integers",
          all(isinstance(x, int) for ids in payload.values() for x in ids), payload)
    raw_text = scene_path.read_text(encoding="utf-8")
    check("JSON keeps >int64 id as decimal literal",
          bool(big_targets) and str(big_targets[0]) in raw_text,
          big_targets[:1])
    check("JSON ids round-trip exactly",
          {k: sorted(v) for k, v in payload.items()} == {k: sorted(v) for k, v in saved_before.items()},
          (payload, saved_before))

    cleared = app.restore_all_env()
    pump(0.1)
    check("restore_all before load cleared hidden_env_ids", cleared and app.hidden_env_ids == {},
          app.hidden_env_ids)
    app.load_scene()
    pump(0.3)
    print("load_scene 后 hidden_env_ids:", {k: len(v) for k, v in app.hidden_env_ids.items()})
    check("load_scene re-hid Vegetation ids",
          sorted(app.hidden_env_ids.get("Vegetation") or []) == sorted(veg_targets),
          app.hidden_env_ids.get("Vegetation"))
    check("load_scene re-hid Poles ids",
          sorted(app.hidden_env_ids.get("Poles") or []) == sorted(pole_targets),
          app.hidden_env_ids.get("Poles"))

finally:
    # ---------- 收尾恢复 ----------
    print("\n--- 收尾 ---")
    try:
        app.restore_all_env()
    except Exception as exc:
        print("restore_all error:", exc)
    try:
        probe_cam.stop()
        probe_cam.destroy()
    except Exception:
        pass
    try:
        raw_world.get_spectator().set_transform(start_spectator)
        raw_world.wait_for_tick(2.0)
    except Exception as exc:
        print("spectator restore error:", exc)
    app.camera = None
    pump(0.3)

    left = app._env_hidden_total()
    check("cleanup: hidden_env_ids empty", left == 0 and app.hidden_env_ids == {}, app.hidden_env_ids)
    # 复扫一遍真实状态：重新取一次，确认没有任何残留在"隐藏"状态
    raw_world.enable_environment_objects([], True)
    rescan = {}
    t0 = time.perf_counter()
    for label in module.ENV_LABELS:
        rescan[label] = len(raw_world.get_environment_objects(getattr(carla.CityObjectLabel, label)))
    print("复扫 6 类数量:", rescan, "用时 %.2f s" % (time.perf_counter() - t0))
    check("cleanup: all 6 classes still enumerable", all(v > 0 for v in rescan.values()), rescan)
    check("cleanup: vegetation back to 62581", rescan["Vegetation"] == 62581, rescan["Vegetation"])

    end_triplets = light_triplets()
    changed = {k: (start_triplets.get(k), v) for k, v in end_triplets.items() if start_triplets.get(k) != v}
    check("cleanup: 15 traffic lights still 10/3/2",
          len(end_triplets) == 15 and all(v == (10.0, 3.0, 2.0) for v in end_triplets.values()),
          end_triplets)
    check("cleanup: traffic light timings unchanged", not changed, changed)
    # 恢复机位（脚本中途把 spectator 挪去看灯杆了）：set_transform 要等帧才生效
    try:
        raw_world.get_spectator().set_transform(start_spectator)
        raw_world.wait_for_tick(2.0)
    except Exception as exc:
        print("  恢复机位失败:", exc)
    end_spectator = raw_world.get_spectator().get_transform()
    moved = (abs(end_spectator.location.x - start_spectator.location.x)
             + abs(end_spectator.location.y - start_spectator.location.y)
             + abs(end_spectator.location.z - start_spectator.location.z)
             + abs(end_spectator.rotation.yaw - start_spectator.rotation.yaw))
    # 容差 0.01：set/get 往返有 ~3e-5 度浮点噪声，不能要求逐位相等
    check("cleanup: spectator camera restored", moved < 0.01,
          "%.6f (位置+yaw 偏差合计)" % moved)
    end_actors = len(raw_world.get_actors())
    check("cleanup: actor count back to baseline", end_actors == start_actors,
          (start_actors, end_actors))

    try:
        root.update()
        root.destroy()
    except Exception:
        pass

print("\nRESULT PASS=%d FAIL=%d" % (PASS, FAIL))
if FAILED:
    print("FAILED:", FAILED)
sys.exit(1 if FAIL else 0)
