# -*- coding: utf-8 -*-
r"""场景 v2 离线验收：GUI 冒烟 + 自动存档 + 最近项目（不需要 CARLA 服务端）。

用法：py -3.12 E:\output\_scripts\_verify_workshop_scene_v2_offline.py
"""
import importlib.util
import json
import sys
import time
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
FAILED_NAMES = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        FAILED_NAMES.append(name)
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail) if detail else ""))


# 把落盘路径重定向到临时目录，避免污染真实 仿真输出
tmp = Path(__file__).resolve().parent / "_tmp_scene_v2_offline"
if tmp.exists():
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
tmp.mkdir(parents=True, exist_ok=True)
module.RECENTS_PATH = tmp / "_workshop_recents.json"
module.AUTO_SAVE_DIR = tmp / "场景快照"
module.AUTO_SAVE_PATH = module.AUTO_SAVE_DIR / "last_session.json"

dialog_log = []
module.filedialog.asksaveasfilename = lambda **kw: (dialog_log.append("save"), str(tmp / "a.json"))[1]
module.filedialog.askopenfilename = lambda **kw: (dialog_log.append("open"), str(tmp / "missing.json"))[1]
module.messagebox.askyesno = lambda *a, **kw: (dialog_log.append("askyesno"), True)[1]
module.messagebox.showwarning = lambda *a, **kw: dialog_log.append(("warn", a[0]))
module.messagebox.showerror = lambda *a, **kw: dialog_log.append(("error", a[0]))
module.messagebox.showinfo = lambda *a, **kw: dialog_log.append(("info", a[0]))

root = tk.Tk()
root.withdraw()
app = Workshop(root)
root.update()

# ---------- 1. 新增方法存在 ----------
for name in ("_scene_to_dict", "_weather_to_dict", "_traffic_lights_to_dict", "_camera_to_dict",
             "_hidden_env_to_dict", "_write_json_atomic", "_apply_scene_weather", "_restore_camera",
             "_restore_traffic_lights", "_apply_scene_session", "_load_scene_from_path",
             "_spawn_scene_vehicles", "_apply_vehicle_item", "_spawn_scene_props",
             "run_auto_save", "_auto_save_tick", "_schedule_auto_save", "restore_auto_save",
             "refresh_recents", "open_recent_scene", "_push_recent", "_load_recents", "_recent_label"):
    check("method " + name, hasattr(app, name))

# ---------- 2. 新增控件存在 & 默认值 ----------
check("recent combo exists", hasattr(app, "recent_combo") and app.recent_combo.winfo_exists())
check("recent combo readonly", str(app.recent_combo.cget("state")) == "readonly",
      app.recent_combo.cget("state"))
check("auto save label exists", hasattr(app, "auto_save_var"))
check("auto save label text", "自动存档" in app.auto_save_var.get(), app.auto_save_var.get())
check("auto save interval constant", module.AUTO_SAVE_INTERVAL_SECONDS == 180,
      module.AUTO_SAVE_INTERVAL_SECONDS)
check("auto save path", str(module.AUTO_SAVE_PATH).endswith(r"场景快照\last_session.json"),
      str(module.AUTO_SAVE_PATH))
check("recents max", module.MAX_RECENTS == 10, module.MAX_RECENTS)
check("recents path name", module.RECENTS_PATH.name == "_workshop_recents.json",
      module.RECENTS_PATH.name)
check("v2 format constant", module.SCENE_FORMAT_V2 == "carla_creator_workshop_scene_v2",
      module.SCENE_FORMAT_V2)
check("v1 still readable", module.SCENE_FORMAT_V1 in module.SCENE_FORMAT_READABLE)

# 场景与视频框里的按钮（按文本找）
def all_widgets(widget):
    yield widget
    for child in widget.winfo_children():
        yield from all_widgets(child)

texts = []
for widget in all_widgets(root):
    try:
        texts.append(str(widget.cget("text")))
    except Exception:
        continue
for wanted in ("打开最近项目", "刷新列表", "恢复上次自动存档", "保存场景配置…", "加载场景配置…"):
    check("button exists: " + wanted, wanted in texts)

# ---------- 3. 未连接时点击不崩 ----------
for label, fn in (("save_scene", app.save_scene), ("load_scene", app.load_scene),
                  ("restore_auto_save", app.restore_auto_save),
                  ("open_recent_scene", app.open_recent_scene),
                  ("refresh_recents", app.refresh_recents),
                  ("run_auto_save", app.run_auto_save)):
    try:
        fn()
        ok = True
    except Exception as exc:
        ok = False
        print("traceback:", label, exc)
    check("disconnected %s safe" % label, ok)

check("run_auto_save returns False when disconnected", app.run_auto_save() is False)
check("auto save skipped while disconnected", not module.AUTO_SAVE_PATH.exists())

# ---------- 4. 原子写 + 自动存档内容可被 load_scene 读取 ----------
fake_scene = {"format": module.SCENE_FORMAT_V2, "map": "Town10HD_Opt",
              "weather": {"cloudiness": 1.0}, "vehicles": [], "props": []}
app._write_json_atomic(module.AUTO_SAVE_PATH, fake_scene)
check("atomic write created file", module.AUTO_SAVE_PATH.is_file(), str(module.AUTO_SAVE_PATH))
check("atomic write left no .tmp",
      not any(p.name.endswith(".tmp") for p in module.AUTO_SAVE_DIR.iterdir()),
      [p.name for p in module.AUTO_SAVE_DIR.iterdir()])
check("auto save json parses",
      json.loads(module.AUTO_SAVE_PATH.read_text(encoding="utf-8"))["format"] == module.SCENE_FORMAT_V2)

# 模拟已连接但 world 为 None 不能崩
class _Boom:
    def __getattr__(self, item):
        raise RuntimeError("boom")


app.connected = True
app.world = _Boom()
try:
    result = app.run_auto_save()
    crashed = False
except Exception as exc:
    crashed = True
    result = exc
check("run_auto_save catches world errors", not crashed and result is False, result)
app.connected = False
app.world = None

# ---------- 5. 最近项目：推入顺序 / 灰掉丢失文件 / 打开不崩 ----------
(tmp / "scene_a.json").write_text("{}", encoding="utf-8")
(tmp / "scene_b.json").write_text("{}", encoding="utf-8")
app._push_recent(str(tmp / "scene_a.json"))
recents_one = json.loads(module.RECENTS_PATH.read_text(encoding="utf-8"))
check("first push recorded", len(recents_one) == 1, recents_one)
time.sleep(1.05)
app._push_recent(str(tmp / "scene_b.json"))
recents = json.loads(module.RECENTS_PATH.read_text(encoding="utf-8"))
check("recents has 2 entries", len(recents) == 2, len(recents))
check("newest first", Path(recents[0]["path"]).name == "scene_b.json", recents[0]["path"])
check("older second", Path(recents[1]["path"]).name == "scene_a.json", recents[1]["path"])
check("recents combo populated", len(app.recent_combo["values"]) == 2,
      list(app.recent_combo["values"]))
check("recents item has saved_at", bool(recents[0].get("saved_at")), recents[0])

# 重复推入不产生重复项
app._push_recent(str(tmp / "scene_a.json"))
recents = json.loads(module.RECENTS_PATH.read_text(encoding="utf-8"))
check("re-push dedups and moves to front",
      len(recents) == 2 and Path(recents[0]["path"]).name == "scene_a.json",
      [Path(r["path"]).name for r in recents])

# 超过 10 条要截断
for index in range(14):
    target = tmp / ("bulk_%02d.json" % index)
    target.write_text("{}", encoding="utf-8")
    app._push_recent(str(target))
recents = json.loads(module.RECENTS_PATH.read_text(encoding="utf-8"))
check("recents capped at 10", len(recents) == 10, len(recents))
check("capped list newest first", Path(recents[0]["path"]).name == "bulk_13.json",
      Path(recents[0]["path"]).name)

# 删掉一个文件后刷新列表：不崩 + 标记丢失
app.refresh_recents(announce=False)
app.recent_combo.current(0)
gone = Path(app.recent_items[0]["path"])
gone.unlink()
label = app._recent_label(app.recent_items[0])
check("missing file marked in label", "文件已丢失" in label, label)
app.refresh_recents(announce=False)
check("refresh after missing file OK", len(app.recent_combo["values"]) == 10)

dialog_log.clear()
app.connected = False
app.open_recent_scene()
check("open_recent_scene while disconnected warns",
      any(isinstance(item, tuple) and item[0] == "warn" for item in dialog_log), dialog_log)

# 已连接但文件丢失：应提示并从列表移除，不能崩
class _NilWorld:
    def get_map(self):
        return _Boom()

app.connected = True
app.world = _NilWorld()
app.recent_combo.current(0)
missing_entry = app.recent_items[0]["path"]
dialog_log.clear()
try:
    app.open_recent_scene()
    ok = True
except Exception as exc:
    ok = False
    print("traceback:", exc)
check("open missing recent does not crash", ok)
check("open missing recent warns",
      any(isinstance(item, tuple) and item[0] == "warn" for item in dialog_log), dialog_log)
recents_after = json.loads(module.RECENTS_PATH.read_text(encoding="utf-8"))
check("missing recent removed from file",
      missing_entry not in [r["path"] for r in recents_after],
      [Path(r["path"]).name for r in recents_after])
app.connected = False
app.world = None

# ---------- 6. 定时器：可调度可取消 ----------
app._schedule_auto_save()
check("auto save job scheduled", app.auto_save_job is not None)
first_job = app.auto_save_job
app._schedule_auto_save()
check("reschedule replaces job", app.auto_save_job is not None and app.auto_save_job != first_job,
      (first_job, app.auto_save_job))

try:
    app.close()
    closed = True
except Exception as exc:
    closed = False
    print("close traceback:", exc)
check("close clean", closed)

print()
print("RESULT PASS=%d FAIL=%d" % (PASS, FAIL))
if FAILED_NAMES:
    print("FAILED: " + ", ".join(FAILED_NAMES))
sys.exit(0 if FAIL == 0 else 1)
