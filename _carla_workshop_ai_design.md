# CARLA 创造工坊 AI 化设计（--headless + JSON 剧本）

> 2026-10-24 设计稿。用户补充目标：**不只是给人用，AI 助手也要能便捷做视频**。
> 用户已拍板：① 加 `--headless` 命令行模式 ② 用 JSON 剧本文件 ③ 先补完 ② 实机验收再做 AI 化。

## 1. 为什么要做（现状的 AI 使用成本）

今天 AI 想用这个工坊产一段视频，实际做法是（见 `_verify_workshop_scene_v2.py` 第 57-67 行）：

```python
module.filedialog.asksaveasfilename = lambda **kw: ...   # 打桩
module.filedialog.askopenfilename  = lambda **kw: ...   # 打桩
module.messagebox.askyesno         = lambda *a, **kw: ... # 打桩
module.messagebox.showwarning      = lambda *a, **kw: ... # 打桩
module.messagebox.showerror        = lambda *a, **kw: ... # 打桩
root = tk.Tk(); root.withdraw()                        # 假窗口
app = Workshop(root)
```

**问题**：全文有 **60 处**模态调用（16 showerror / 35 showwarning / 3 askyesno / 2 askfloat / 3 文件对话框）。
任何一个没打桩，无人值守运行就会**永久阻塞在对话框**上。这不是可维护的 AI 通道。

## 2. 关键结论：不需要重构

实测统计（`grep` 全文）：**142 处 Tk widget 调用，其中 116 处是 `.pack()` 布局**。
业务方法（`_spawn_vehicle_at` / `set_vehicle_behavior` / `_scene_to_dict` / `_start_recording` /
`hide_env_label` / `hide_env_in_range` / `restore_all_env`）本身几乎不碰 Tk。

→ 所以采用**同一个文件加 headless 分支**，不抽库、不拆模块。

## 3. 设计

### 3.1 三条入口（互不影响）

| 入口 | 命令 | 谁用 |
|---|---|---|
| GUI（现状不变） | 双击 `启动CARLA创造工坊.bat` | 用户 |
| 剧本执行 | `py -3.12 <工坊.py> --recipe 剧本.json --out 输出.mp4` | **AI** |
| 自检 | `py -3.12 <工坊.py> --selftest` | AI/CI（不开 CARLA 也能验参数解析与剧本校验） |

### 3.2 headless 模式怎么实现

**不建 Tk 主窗口**，但保留 `CarlaCreatorWorkshop` 的实例状态。做法：

1. `main()` 里判断 `sys.argv`：有 `--recipe` / `--selftest` → 走 `run_headless()`，不创建 `tk.Tk()`
2. 实例化时传 `headless=True`：
   - 所有 Tk 变量换成**同名的普通对象**（`_HeadlessVar`，有 `get()/set()` 两个方法，接口与 `tk.StringVar` 一致）
   - `_build_ui()` 整体跳过（不建任何控件）
   - `set_status()` 改成写日志（`print` + 可选 append 到 `workshop_headless.log`）
3. **模态对话框统一拦截**：加一个 `self.dialog()` 分发器，headless 下**不弹窗**，改为
   - `showwarning/showerror` → 写日志 + 记入 `self.findings`
   - `askyesno` → headless 默认返回**剧本里声明的值**（默认 `True`，剧本可覆盖）
   - 文件对话框 → headless 直接用剧本里给的路径
   - 这一步**不逐个改 60 处调用**，而是在模块级把 `messagebox` / `filedialog` 替换成 headless 适配器（仅当 `--headless` 时）

> 关键设计：**不改 60 处业务代码**，只在 headless 启动时替换模块级符号。这样 GUI 路径零风险。

### 3.3 JSON 剧本格式（recipe v1）

```json
{
  "format": "carla_workshop_recipe_v1",
  "title": "路口闯红灯演示",
  "map": "Town10HD_Opt",
  "scene": "E:\\output\\1\\carla\\仿真输出\\场景快照\\last_session.json",
  "camera": { "fov": 90, "transform": { "location": {...}, "rotation": {...} } },
  "hide": [
    { "action": "label", "label": "Vegetation" },
    { "action": "range", "label": "Vegetation", "radius": 60, "mode": "球体" }
  ],
  "actions": [
    { "t": 0.0,  "do": "behavior", "vehicle": 0, "mode": "run_light" },
    { "t": 0.0,  "do": "tl_durations", "green": 12, "yellow": 2, "red": 15 },
    { "t": 2.0,  "do": "wait", "seconds": 8 },
    { "t": 10.0, "do": "log", "text": "闯红灯完成" }
  ],
  "record": { "seconds": 20, "fps": 20, "resolution": "1920x1080", "out": "闯红灯.mp4" },
  "cleanup": { "restore_hidden": true, "restore_traffic_lights": true }
}
```

设计要点：
- `scene` 复用 **v2 场景文件**（已支持 vehicles/props/红绿灯配时/相机/被隐藏物体），不重复造
- `actions` 用 `t`（相对开录的秒数）排序，`do` 是动作名，扩展新动作不影响旧剧本
- `cleanup` 强制收尾还原（**这是给 AI 用的关键**：AI 跑完必须让世界回到干净状态，否则下次跑不准）

### 3.4 首版支持的 `do` 动作（够造违规视频即可）

| do | 参数 | 复用现有函数 |
|---|---|---|
| `behavior` | `vehicle`(索引/蓝图) + `mode` | `set_vehicle_behavior()` |
| `speed` | `vehicle` + `kmh` | `target_speed_by_vehicle` + `_drive_forward()` |
| `tl_durations` | `green/yellow/red` | `start_custom_timing()` 同一套 |
| `hide` / `show` | `label` / `range` | `hide_env_label()` / `hide_env_in_range()` |
| `wait` | `seconds` | — |
| `log` | `text` | — |

> **明确不做**：不做任意 Python 注入（安全与可复现考虑），只支持白名单动作。

## 4. 验收标准（AI 化的验收必须是「AI 自己跑通」）

1. `--selftest` 不开 CARLA 也能跑：剧本解析、字段校验、错误剧本给出清晰中文报错 → exit code 非 0
2. **一条命令出一段真视频**：`py -3.12 <工坊.py> --recipe x.json` → 产出 mp4，且 `ffprobe` 能读出正确时长/分辨率/fps
3. **零交互**：全程无窗口、无弹窗、无 stdin 等待（用一个 120 秒超时跑，超时即失败）
4. **幂等收尾**：跑完断言 actor 数回到基线、红绿灯配时回到 10/3/2、隐藏装饰物全部恢复
5. **失败可诊断**：剧本写错时给出「哪个字段、期望什么、实际什么」的中文错误，不用看 traceback

## 5. 与既有工作的关系

- 不改 GUI 任何行为（GUI 路径的行为必须逐字节等价，用既有 `_verify_workshop_gui.py` 35 项回归守住）
- 复用 v2 场景格式，不新增场景格式版本
- 装饰物隐藏的三档 API 已经是「返回计数」的好接口，剧本可直接调

## 6. 排序

1. **先补 ② 实机验收**（用户拍板，只差实机验证就闭环）
2. 再做 `--headless` + recipe（本文件）
3. 最后车牌（`apply_color_texture_to_object`）