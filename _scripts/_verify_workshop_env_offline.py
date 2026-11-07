# -*- coding: utf-8 -*-
r"""装饰物隐藏 · 离线验收：新增控件 / 默认值 / 未连接时按钮不崩 / 纯逻辑自检。

用法：py -3.12 E:\output\_scripts\_verify_workshop_env_offline.py
不需要 CARLA 服务端。
"""
import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import tkinter as tk

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


def _detail_text(detail):
    if isinstance(detail, str):
        return detail
    if detail is None:
        return ""
    return repr(detail)


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        FAILED.append(name)
    text = _detail_text(detail)
    print(("PASS " if ok else "FAIL ") + name + (" | " + text if text else ""))


dialogs = []
module.messagebox.showwarning = lambda *a, **k: dialogs.append(("warn", a[0] if a else ""))
module.messagebox.showerror = lambda *a, **k: dialogs.append(("error", a[0] if a else ""))
module.messagebox.showinfo = lambda *a, **k: dialogs.append(("info", a[0] if a else ""))
module.messagebox.askyesno = lambda *a, **k: True

root = tk.Tk()
root.withdraw()
app = Workshop(root)
root.update()

print("\n--- 1. 新增方法 / 常量 ---")
for method in ("refresh_env_objects", "hide_env_label", "show_env_label", "hide_env_in_range",
               "show_env_in_range", "restore_all_env", "_env_pick", "_env_corners", "_env_hide",
               "_env_show", "_load_env_cache", "invalidate_env_cache", "hide_env_single",
               "show_env_picked", "_on_preview_middle_click", "_env_hide_at_pixel",
               "hide_env_at_pixel", "_restore_hidden_environment_objects"):
    check("method " + method, hasattr(app, method))
check("ENV_LABELS has 6 classes", len(module.ENV_LABELS) == 6, module.ENV_LABELS)
check("ENV_LABELS covers required classes",
      set(module.ENV_LABELS) == {"Vegetation", "Poles", "Fences", "Buildings", "Walls", "TrafficSigns"})
check("ENV_LABEL_CN complete", all(k in module.ENV_LABEL_CN for k in module.ENV_LABELS))

print("\n--- 2. 实例状态默认值 ---")
check("hidden_env_ids starts empty dict",
      isinstance(app.hidden_env_ids, dict) and app.hidden_env_ids == {}, app.hidden_env_ids)
check("env_cache starts empty", app.env_cache == {})
check("env_label_var default Vegetation", app.env_label_var.get() == "Vegetation", app.env_label_var.get())
check("env_radius_var default 50", app.env_radius_var.get() == "50", app.env_radius_var.get())
check("env_radius_mode_var default 球体", app.env_radius_mode_var.get() == "球体", app.env_radius_mode_var.get())
check("env_pick_var default True", bool(app.env_pick_var.get()))
check("env_summary_var not empty", bool(app.env_summary_var.get()))

print("\n--- 3. 新增 UI 控件 ---")
widgets = {
    "env_label_combo": "ttk.Combobox",
    "env_pick_var": "tk.BooleanVar",
}
check("env_label_combo exists", hasattr(app, "env_label_combo"))
check("env_label_combo values == ENV_LABELS",
      tuple(app.env_label_combo["values"]) == module.ENV_LABELS, app.env_label_combo["values"])
check("env_label_combo readonly", str(app.env_label_combo["state"]) == "readonly")
texts = []


def walk(widget):
    try:
        texts.append(str(widget.cget("text")))
    except Exception:
        pass
    for child in widget.winfo_children():
        walk(child)


walk(root)
required_texts = [
    "刷新列表", "隐藏该类别全部装饰物", "恢复该类别全部装饰物",
    "隐藏范围内该类别（档 C）", "恢复范围内该类别（档 C）",
    "恢复刚拾取的那个", "一键恢复全部已隐藏",
]
for t in required_texts:
    check("button text: " + t, t in texts)
hint = "隐藏装饰物会同时去掉它的碰撞，纯属视觉操作，不影响行车逻辑。"
check("collision hint shown", hint in texts)
check("label frame 装饰物（树/路灯）隐藏 present",
      any("装饰物（树/路灯）隐藏" in t for t in texts))
check("preview bound Button-2", bool(app.preview.bind("<Button-2>")))

print("\n--- 4. 未连接时点各按钮不崩 ---")
calls = [
    ("refresh_env_objects", lambda: app.refresh_env_objects()),
    ("hide_env_label", lambda: app.hide_env_label()),
    ("show_env_label", lambda: app.show_env_label()),
    ("hide_env_in_range", lambda: app.hide_env_in_range()),
    ("show_env_in_range", lambda: app.show_env_in_range()),
    ("restore_all_env", lambda: app.restore_all_env()),
    ("show_env_picked", lambda: app.show_env_picked()),
    ("_on_preview_middle_click", lambda: app._on_preview_middle_click(
        types.SimpleNamespace(x=10, y=10, widget=app.preview))),
    ("_on_preview_right_click", lambda: app._on_preview_right_click(
        types.SimpleNamespace(x=10, y=10, widget=app.preview, x_root=0, y_root=0))),
]
for name, fn in calls:
    try:
        fn()
        ok = True
        detail = ""
    except Exception as exc:
        ok = False
        detail = repr(exc)
    check("not-connected no crash: " + name, ok, detail)
check("warnings raised for unconnected", len(dialogs) >= 5, len(dialogs))

print("\n--- 5. 半径解析与容错 ---")
app.env_radius_var.set("  25.5 ")
check("radius parsed 25.5", abs(app._env_parse_radius() - 25.5) < 1e-9, app.env_radius_var.get())
app.env_radius_var.set("abc")
r = app._env_parse_radius()
check("radius non-numeric -> clamped >= 1", r >= 1.0, r)
app.env_radius_var.set("-5")
check("radius negative -> clamped", app._env_parse_radius() >= 1.0, app.env_radius_var.get())
app.env_radius_var.set("50")

print("\n--- 6. 几何：8 角点自算（假 bbox，绕 yaw=90，纯几何自检）---")
entry = {
    "map": "fake",
    "ids": [11],
    "names": ["fake_obj"],
    "centers": np.array([[0.0, 0.0, 1.0]]),
    "half": np.array([[2.0, 1.0, 0.5]]),
    "axes": np.array([module.CarlaCreatorWorkshop._env_rotation_axes(
        carla.Rotation(pitch=0.0, yaw=90.0, roll=0.0))]),
}
app.env_cache = {"Poles": entry}
corners = app._env_corners("Poles", 0)
check("8 corners", corners.shape == (8, 3), corners.shape)
# yaw=90 → 局部 x 轴映射到世界 +y，局部 y 轴映射到世界 -x
expect = {(2.0, 1.0, 0.5), (2.0, 1.0, 1.5), (2.0, -1.0, 0.5), (2.0, -1.0, 1.5),
          (-2.0, 1.0, 0.5), (-2.0, 1.0, 1.5), (-2.0, -1.0, 0.5), (-2.0, -1.0, 1.5)}
got = {tuple(np.round((p[1], -p[0], p[2]), 6)) for p in corners}
check("yaw=90 corner mapping", got == expect, sorted(got)[:3])
check("corners center z offset respected", abs(float(np.mean(corners[:, 2])) - 1.0) < 1e-9)

print("\n--- 7. 半径预筛逻辑（球体 vs 圆柱）---")
entry2 = {
    "map": "fake",
    "ids": [101, 102, 103],
    "names": ["a", "b", "c"],
    "centers": np.array([[0.0, 0.0, 0.0], [30.0, 0.0, 0.0], [0.0, 0.0, 60.0]]),
    "half": np.array([[1.0, 1.0, 1.0]] * 3),
    "axes": np.array([module.CarlaCreatorWorkshop._env_rotation_axes(
        carla.Rotation(pitch=0.0, yaw=0.0, roll=0.0))] * 3),
}
app.env_cache = {"Poles": entry2}
sphere_ids, _ = app._env_range_ids("Poles", (0.0, 0.0, 0.0), 35.0, "球体")
check("sphere r=35 hits 2 of 3", sorted(sphere_ids) == [101, 102], sphere_ids)
cyl_ids, _ = app._env_range_ids("Poles", (0.0, 0.0, 0.0), 35.0, "圆柱")
check("cylinder r=35 hits 3 of 3 (z ignored)", sorted(cyl_ids) == [101, 102, 103], cyl_ids)
app.hidden_env_ids = {"Poles": [101]}
skip_ids, _ = app._env_range_ids("Poles", (0.0, 0.0, 0.0), 35.0, "球体")
check("range skips already hidden", 101 not in skip_ids and 102 in skip_ids, skip_ids)
all_ids, _ = app._env_range_ids("Poles", (0.0, 0.0, 0.0), 35.0, "球体", skip_hidden=False)
check("range keep_hidden returns both", sorted(all_ids) == [101, 102], all_ids)

print("\n--- 8. 拾取预筛（向量化投影 / 视锥）---")
app.hidden_env_ids = {}
transform = carla.Transform(carla.Location(0.0, 0.0, 10.0), carla.Rotation(0.0, 0.0, 0.0))
fwd, right, up = module.CarlaCreatorWorkshop._camera_basis(transform)
origin = np.array([0.0, 0.0, 10.0])
pts = np.array([[20.0, 0.0, 10.0], [-20.0, 0.0, 10.0], [20.0, 0.0, 0.0]])
px = module.CarlaCreatorWorkshop._env_project(pts, origin, (fwd, right, up), 90.0, 960, 540)
front_only = np.array([[20.0, 0.0, 10.0], [20.0, 10.0, 10.0]])
px = module.CarlaCreatorWorkshop._env_project(front_only, origin, (fwd, right, up), 90.0, 960, 540)
check("project returns pixels for front points", px is not None and px.shape == (2, 2), None if px is None else px.shape)
check("front point lands at image centre",
      px is not None and abs(px[0][0] - 479.5) < 1e-6 and abs(px[0][1] - 269.5) < 1e-6, None if px is None else px[0])
check("right-offset point lands to the right of centre", px is not None and px[1][0] > 479.5,
      None if px is None else px[1])
behind = module.CarlaCreatorWorkshop._env_project(
    np.array([[-20.0, 0.0, 10.0]]), origin, (fwd, right, up), 90.0, 960, 540)
check("behind-camera point returns None (culled)", behind is None, behind)
mixed = module.CarlaCreatorWorkshop._env_project(
    np.array([[20.0, 0.0, 10.0], [-20.0, 0.0, 10.0]]), origin, (fwd, right, up), 90.0, 960, 540)
check("batch with any behind-camera point is culled", mixed is None, mixed)
app.env_cache = {}
pick = app._env_pick(480, 270)
check("pick with empty cache returns None", pick is None, pick)

print("\n--- 9. v2 序列化通道仍接得上（hidden_env_ids 非空时）---")


class FakeWorld:
    def get_map(self):
        return types.SimpleNamespace(name="Carla/Maps/Town10HD_Opt")


app.world = FakeWorld()
app.hidden_env_ids = {"Vegetation": [2**63 + 12345, 16740775638937321093], "Poles": [7]}
payload = app._hidden_env_to_dict()
check("payload has 2 labels", set(payload) == {"Vegetation", "Poles"}, payload)
check("payload ids are python ints",
      all(isinstance(x, int) for ids in payload.values() for x in ids))
check("payload keeps >int64 id", payload["Vegetation"][1] == 16740775638937321093)
scene = app._scene_to_dict()
check("scene carries hidden_environment_objects",
      scene.get("hidden_environment_objects") == payload, scene.get("hidden_environment_objects"))
app.hidden_env_ids = {}
check("empty hidden -> empty payload", app._hidden_env_to_dict() == {})

print("\n--- 10. 面板文字刷新（纯计算，不发 RPC）---")
app.env_cache = {"Vegetation": {
    "map": "fake", "ids": [1, 2, 3, 2**63 + 1], "names": ["v1", "v2", "v3", "v4"],
    "centers": np.zeros((4, 3)), "half": np.ones((4, 3)),
    "axes": np.array([module.CarlaCreatorWorkshop._env_rotation_axes(
        carla.Rotation(pitch=0.0, yaw=0.0, roll=0.0))] * 4),
}}
app.hidden_env_ids = {"Vegetation": [2**63 + 1]}
app.world = None
app.env_label_var.set("Vegetation")
app._refresh_env_panel()
check("summary reflects hidden count", "已隐藏 1 个" in app.env_summary_var.get(), app.env_summary_var.get()[:80])

try:
    app.destroy = None
    root.destroy()
except Exception:
    pass

print("\nRESULT PASS=%d FAIL=%d" % (PASS, FAIL))
if FAILED:
    print("FAILED:", FAILED)
sys.exit(1 if FAIL else 0)
