# -*- coding: utf-8 -*-
"""验证：GUI 路径在 4,058 行版本下仍能正常开窗（headless 守卫没污染全局）。"""
import importlib.util
import tkinter as tk

spec = importlib.util.spec_from_file_location("ws", r"E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

print("导入后 HEADLESS =", m.HEADLESS, "（必须 False）")
print("tk.Canvas 是真类?", m.tk.Canvas.__name__ == "Canvas", "->", m.tk.Canvas.__name__)
print("ttk.Button 是真类?", m.ttk.Button.__name__ == "Button", "->", m.ttk.Button.__name__)
print("messagebox.showwarning 是真函数?", m.messagebox.showwarning.__module__, end=" -> ")
print(getattr(m.messagebox.showwarning, "__module__", "?"))

root = tk.Tk()
app = m.CarlaCreatorWorkshop(root)
root.update()
print("\nGUI 构造成功")
print("  preview 类型 =", type(app.preview).__name__, "（应为 Label）")
print("  record_button 类型 =", type(app.record_button).__name__, "（应为 Button）")
print("  map_combo 类型 =", type(app.map_combo).__name__, "（应为 Combobox）")
print("  窗口尺寸 =", root.winfo_width(), "x", root.winfo_height())
print("  status =", app.status_var.get()[:40])

# 关键：控件必须真的能查询尺寸（替身返回 0 会暴露）
print("  preview.winfo_width() =", app.preview.winfo_width(), "（真 Label 应 >= 1）")
app.close()
print("close 成功")
print("RESULT GUI OK")
