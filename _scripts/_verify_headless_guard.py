# -*- coding: utf-8 -*-
"""验证 enable_headless 的误用保护。"""
import importlib.util
import tkinter as tk

spec = importlib.util.spec_from_file_location("ws", r"E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

root = tk.Tk(); root.withdraw()
app = m.CarlaCreatorWorkshop(root)
try:
    m.enable_headless()
    print("FAIL 保护未生效，headless 被误开启")
except RuntimeError as exc:
    print("PASS 保护生效:", str(exc)[:70])
app.close()

# 反向：没有实例时应能正常开启
import importlib
spec2 = importlib.util.spec_from_file_location("ws2", r"E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py")
m2 = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(m2)
m2.enable_headless()
print("PASS 无实例时可正常开启, HEADLESS =", m2.HEADLESS)
