# -*- coding: utf-8 -*-
"""验证 disable_headless() 能完全还原，同进程内 headless → GUI 切换安全。"""
import importlib.util
import tkinter as tk

spec = importlib.util.spec_from_file_location("ws", r"E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

print("=== 1) 初始状态 ===")
print("  HEADLESS =", m.HEADLESS, "| tk.Canvas =", m.tk.Canvas.__name__)

print("\n=== 2) 开 headless ===")
m.enable_headless()
print("  HEADLESS =", m.HEADLESS, "| tk.Canvas =", m.tk.Canvas.__name__)
root1 = tk.Tk(); root1.withdraw()
app1 = m.CarlaCreatorWorkshop(root1)
print("  preview =", type(app1.preview).__name__, "（应 _StubWidget）")
app1.close()

print("\n=== 3) 关闭 headless 后必须完全还原 ===")
m.disable_headless()
print("  HEADLESS =", m.HEADLESS, "| tk.Canvas =", m.tk.Canvas.__name__)
print("  ttk.Button =", m.ttk.Button.__name__)
print("  messagebox.showwarning 模块 =", m.messagebox.showwarning.__module__)
root2 = tk.Tk(); root2.withdraw()
app2 = m.CarlaCreatorWorkshop(root2)
print("  preview =", type(app2.preview).__name__, "（应 Label）")
print("  record_button =", type(app2.record_button).__name__, "（应 Button）")
print("  map_combo =", type(app2.map_combo).__name__, "（应 Combobox）")
ok = (type(app2.preview).__name__ == "Label"
      and type(app2.record_button).__name__ == "Button"
      and type(app2.map_combo).__name__ == "Combobox"
      and m.HEADLESS is False)
app2.close()
print("\nRESULT:", "PASS 可逆切换安全" if ok else "FAIL 还原不完整")
