# CARLA 创造工坊 AI 化 —— 交付结论

> 2026-10-24。用户补充目标：**创意工坊的最终目标是让用户和 AI 都能便捷地制作视频**。
> 本文是该目标的实施结论。文件 `carla_creator_workshop.py` **3,500 → 4,058 行**。

## 1. 一句话结论

**已实现：AI 一条命令就能出片，全程零交互。验收 PASS=21 FAIL=0。**

```powershell
py -3.12 E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py `
    --recipe E:\output\recipes\闯红灯演示.json
```

实测：命令 → 7.8 秒 → 4.05 秒 H.264 视频（960x540 / 20fps / 81 帧 / 1.59 MB），世界自动还原干净。

## 2. 三条入口（互不影响）

| 入口 | 命令 | 谁用 |
|---|---|---|
| GUI（行为完全不变） | 双击 `启动CARLA创造工坊.bat` | 用户 |
| **剧本执行** | `--recipe 剧本.json [--out 输出.mp4]` | **AI** |
| **剧本自检** | `--selftest --recipe 剧本.json` | AI/CI（不开 CARLA） |
| 格式自描述 | `--print-schema` | AI 读文档 |

退出码：`0` 成功 ／ `1` 剧本校验失败 ／ `2` 文件/JSON 错误 ／ `3` 连不上 CARLA ／ `4` 收尾有问题 ／ `5` 运行异常。

## 3. 技术方案（为什么不是重构）

**侦察事实**：全文 142 处 Tk widget 调用里 **116 处只是 `.pack()` 布局**，业务方法（`_spawn_vehicle_at` /
`set_vehicle_behavior` / `_scene_to_dict` / `_start_recording` / `hide_env_label`）几乎不碰 Tk。

**所以用最小侵入方案，不改任何业务代码**：

1. headless 下仍创建**隐藏的 `tk.Tk()`**，让 32 个 `tk.StringVar/BooleanVar` 保持真实可用
2. 把 **17 种控件构造器**换成 `_StubWidget`（吞掉 pack/grid/configure/bind）
3. 把 **60 处模态调用**（`messagebox` / `filedialog` / `simpledialog`）换成无交互适配器

→ 116 处 `.pack()`、68 处 widget 调用**一行都不用改**，GUI 路径零风险。

## 4. 剧本格式（recipe v1）

见 `--print-schema` 与 `E:\output\recipes\闯红灯演示.json`。核心结构：

```json
{
  "format": "carla_workshop_recipe_v1",
  "scene": "可选，复用 v2 场景文件",
  "hide":  [{"action": "range", "label": "Vegetation", "radius": 80, "mode": "球体"}],
  "camera": {"fov": 90, "transform": {...}},
  "actions": [
    {"t": 0.0, "do": "behavior", "vehicle": 0, "mode": "run_light"},
    {"t": 0.0, "do": "tl_durations", "green": 12, "yellow": 2, "red": 15},
    {"t": 2.0, "do": "wait", "seconds": 5}
  ],
  "record": {"seconds": 6, "fps": 20, "resolution": "1280x720", "out": "输出.mp4"},
  "cleanup": {"restore_hidden": true, "destroy_vehicles": true}
}
```

**可用动作**（白名单，不做任意 Python 注入）：
`behavior` / `speed` / `tl_durations` / `hide` / `show` / `show_all` / `wait` / `log` / `camera` / `record_start` / `record_stop`

**设计要点**：
- `scene` 复用已交付的 v2 场景格式，不新增格式
- `cleanup` **强制收尾还原**——AI 跑完必须让世界回到干净状态，否则下次跑不准
- `--selftest` 不开 CARLA 就能查出剧本问题，错误信息是中文且指明字段

## 5. 本轮修掉的两个真实产品缺陷

### bug A · 录制视频**播放慢一倍**（既有缺陷，影响所有录制）

**现象**：剧本要求 5 秒，产出 10.65 秒视频。

**根因**：CARLA 异步模式下相机实测 **43.4 fps** 推送，而 ffmpeg 用 `-r 20` 封装。
205 帧 ÷ 20fps = **10.25 秒**，实际只录了 5 秒 → 慢一倍。

**修法**：新增 `_emit_record_frame` + 时间戳门控（`_write_record_frame`）：
按「目标 fps」算出每帧应落在第几个帧位，多余的相机帧丢弃、缺口重复上一帧补齐（上限 4 帧）。

**验证**：5 秒剧本 → **101 帧 / 5.05 秒**（修复前 205 帧 / 10.25 秒）。

> ⚠ 这与智瞳项目 2026-10 那次的「事件视频播放快一倍」是**同类根因**（采集帧率 ≠ 写死帧率）。

### bug B · 录制起点错误：预置阶段被录进视频

**现象**：`hide` 段（藏树）与相机设置发生在 `_start_recording` 之前，但这段时间被录进去了。

**修法**：所有准备动作（`hide` / 相机 / 分辨率）做完后**才**启动录制，并用 `start_wall` 作为时间轴基准。

## 6. 被推翻的结论（本轮新增）

### 6.1 「AI 打桩就能用」不成立

之前的验证脚本靠 `importlib` + 替换 6 个对话框函数来驱动工坊。但全文有 **60 处**模态调用
（16 `showerror` / 35 `showwarning` / 3 `askyesno` / 2 `askfloat` / 3 文件对话框）。
**任何一个没打桩，无人值守运行就会永久阻塞在对话框上。** 这不是可维护的 AI 通道。

### 6.2 不要用 ffprobe 验证视频（本机环境陷阱）

本机 `ffprobe` 是 `C:\Users\ROG\.local\bin\ffprobe.cmd` 包装脚本。
**Windows 下 Python `subprocess` 不能直接执行 `.cmd`**（`WinError 2`），且异常被 `try/except` 吞掉后
表现为「文件存在 1.5MB 但元信息全 None」——**极难定位**。
改用 `cv2.VideoCapture` 读元信息，零外部依赖。

### 6.3 spectator 是全局可变状态，headless 必须隔离

用户开着工坊窗口时它每 80ms 同步一次 spectator，任何外部脚本的 `set_transform` 都会被覆盖。
剧本执行器因此不依赖 spectator 注入位姿，改用 `self.camera.set_transform`。

## 7. 验收证据

`E:\output\_scripts\_verify_workshop_ai.py` → **PASS=21 FAIL=0，exit 0**

| 组 | 项 | 结果 |
|---|---|---|
| A 自描述 | `--print-schema` exit 0、含格式名、含动作清单 | 3/3 |
| B 校验 | 坏 JSON / 未知动作 / 非法模式 / 缺字段 / 非法 label / 版本错 **全部被拒且给中文错误** | 6/6 |
| C 端到端 | exit 0、未超时（7.8s）、**无弹窗**、文件生成、h264、960x540、4.05s、81 帧、1.59MB | 9/9 |
| D 幂等收尾 | actor 23、无车/道具/相机残留、红绿灯全 10/3/2 | 3/3 |

**回归（证明没破坏既有功能）**：GUI 35/0、场景 v2 离线 68/0、序列化 mock 103/0、装饰物离线 73/0、编译 exit 0。

## 8. 现场状态

| 项 | 值 |
|---|---|
| 总 actor | **23** |
| 车辆 / 道具 / 相机 | 0 / 0 / 0（脚本删掉了自己的探针残留） |
| 红绿灯 | 15 盏全 **10/3/2** |
| 用户机位 | `(-172.196579, 183.859116, 27.638052) yaw=-45.592213` |

## 9. 回滚

AI 化改动在 `.bak_20261023_after_v2` **之后**。当前无独立备份，
如需只回滚 AI 化部分，需从 `.bak_20261023_after_v2` 恢复后再补 ② 的改动；
**建议回滚点仍是 `.bak_20261023_after_v2`（放弃 ② 与 AI 化两者）**。

## 10. 遗留

1. 剧本 `camera.preset`（预设机位名）尚未实现，只支持显式 transform
2. 车牌 `apply_color_texture_to_object` 未开始
3. 红绿灯配时的崩溃场景残留风险（进程崩溃时 stop 跑不到）