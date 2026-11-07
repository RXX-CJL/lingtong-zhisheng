# -*- coding: utf-8 -*-
r"""离线 GUI 冒烟：不启动 CARLA，验证创造工坊窗口与鼠标摆放控件可用。

用法：py -3.12 E:\output\_scripts\_verify_workshop_gui.py
"""
import importlib.util
import sys
import types
from pathlib import Path

import tkinter as tk

TARGET = (Path(__file__).resolve().parents[1] / "1" / "carla" / "CARLA_0.9.16"
          / "PythonAPI" / "examples" / "carla_creator_workshop.py")

spec = importlib.util.spec_from_file_location("carla_creator_workshop", TARGET)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Workshop = module.CarlaCreatorWorkshop

PASS = 0
FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail) if detail else ""))


root = tk.Tk()
root.withdraw()
app = Workshop(root)
root.update()

for method in ("_ray_from_pixel", "_world_to_pixel", "_ground_point_from_ray", "_pick_vehicle",
               "_on_preview_press", "_on_preview_drag", "_on_preview_release", "_on_preview_right_click",
               "_spawn_vehicle_at", "_begin_drag", "delete_selected_vehicle", "undo_last_placement",
               "_show_vehicle_menu", "_show_ground_menu", "_set_vehicle_yaw", "_align_vehicle_to_lane",
               "_ask_vehicle_yaw", "_draw_selection", "_delete_vehicle_by_id"):
    check("method " + method, hasattr(app, method))

check("default place_on_click=False", not bool(app.place_on_click_var.get()))
check("default drag_vehicle=True", bool(app.drag_vehicle_var.get()))
check("default snap_lane=False", not bool(app.snap_lane_var.get()))
check("default restore_autopilot=False", not bool(app.restore_autopilot_var.get()))
check("preview bound Button-1", bool(app.preview.bind("<Button-1>")))
check("preview bound B1-Motion", bool(app.preview.bind("<B1-Motion>")))
check("preview bound ButtonRelease-1", bool(app.preview.bind("<ButtonRelease-1>")))
check("preview bound Button-3", bool(app.preview.bind("<Button-3>")))
check("undo stack starts empty", app.undo_stack == [])
check("drag state starts empty", app.drag_state is None)

scale = app._preview_scale_for(1920, 1080)
check("scale<=0.5 for 1920", 0.0 < scale <= 0.5 + 1e-9, round(scale, 4))

event = types.SimpleNamespace(x=10, y=10, widget=app.preview)
try:
    app._on_preview_press(event)
    safe_press = True
except Exception as exc:
    safe_press = False
    print("press traceback:", exc)
check("press while disconnected is safe", safe_press)

for fn in (lambda: app.undo_last_placement(), lambda: app.delete_selected_vehicle()):
    try:
        fn()
        ok = True
    except Exception as exc:
        ok = False
        print("traceback:", exc)
    check("empty-state command safe", ok)

app._on_preview_release(event)
check("release with no drag safe", app.drag_state is None)

try:
    app.close()
    closed = True
except Exception as exc:
    closed = False
    print("close traceback:", exc)
check("close clean", closed)

print()
print("RESULT PASS=%d FAIL=%d" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)

