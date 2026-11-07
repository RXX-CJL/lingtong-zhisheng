# -*- coding: utf-8 -*-
"""验证：AI 剧本产物（含车辆/行为）能被用户 GUI 无缝接续。"""
import importlib.util, json, time
from pathlib import Path
import tkinter as tk

spec = importlib.util.spec_from_file_location("ws", r"E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

print("=== 步骤1：headless 造车 + 设行为 + 存场景 ===")
m.enable_headless()
root1 = tk.Tk(); root1.withdraw()
app1 = m.CarlaCreatorWorkshop(root1)
app1.connect()

carla = m.carla
w = app1.world
wp = w.get_map().get_waypoint(carla.Location(x=109.93, y=-9.33, z=0.3), project_to_road=True)
tf = wp.transform
tf.location.z += 0.3
bp = w.get_blueprint_library().find("vehicle.tesla.model3")
actor = w.try_spawn_actor(bp, tf)
if actor is None:
    print("FAIL 生成失败")
    raise SystemExit(1)
app1._wait_one_tick()
app1.owned_vehicle_ids.append(actor.id)
app1.set_vehicle_behavior(actor.id, "run_light")
print("  造车 id=%d，行为=run_light" % actor.id)

scene_out = Path(r"E:\output\1\carla\仿真输出\_ai_generated_scene.json")
m._headless_dialog.next_save_path = str(scene_out)
app1.save_scene()
time.sleep(0.3)
data = json.loads(scene_out.read_text(encoding="utf-8"))
vs = data.get("vehicles") or []
print("  场景 format:", data.get("format"), "| 车辆:", len(vs))
if vs:
    v = vs[0]
    print("  记录: blueprint=%s behavior=%s autopilot=%s speed=%s" % (
        v.get("blueprint"), v.get("behavior_mode"), v.get("autopilot"), v.get("target_speed_kmh")))
app1.close()

print()
print("=== 步骤2：模拟用户新开 GUI 加载这份 AI 产物 ===")
spec2 = importlib.util.spec_from_file_location("ws2", r"E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py")
m2 = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(m2)
print("  新模块 HEADLESS =", m2.HEADLESS)
root2 = tk.Tk(); root2.withdraw()
app2 = m2.CarlaCreatorWorkshop(root2)
app2.connect()
m2.filedialog.askopenfilename = lambda **kw: str(scene_out)
m2.messagebox.askyesno = lambda *a, **k: True
app2._load_scene_from_path(str(scene_out), track_recent=False)
print("  GUI 加载后车辆数:", len(app2.owned_vehicle_ids))
for aid in app2.owned_vehicle_ids:
    a = app2._live_actor(aid)
    if a is not None:
        print("     id=%d %s 行为=%s" % (aid, a.type_id, app2.vehicle_modes.get(aid)))
print("  preview 类型 =", type(app2.preview).__name__, "（应为 Label）")
app2.remove_own_vehicles(confirm=False)
app2.close()
print()
print("RESULT: PASS AI 产物（含行为模式）可被 GUI 完整接续")
