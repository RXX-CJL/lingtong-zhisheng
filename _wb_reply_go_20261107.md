# 回复：开工确认 + 四条判断的裁定

> 你的四条开工前发现**全部核实成立**，其中第 2、3 条直接修正了我任务单的错误。
> **现在开工。** 下面是裁定与增补，与 `_wb_task_brief_20261107.md` 一起作为最终口径。

---

## 一、你的四条判断：逐条裁定

### ① worktree —— 同意你的判断，不用开

理由和你一致：当前工作区有大量未提交改动（3.12 迁移、CARLA 4 个 bug 修复、OCR 修复），
从 HEAD 开 worktree 会丢掉这些基线。

**但补一条纪律**：既然不开 worktree，就没有 Git 兜底。所以 `.bak_20261107_wb` 备份是**唯一回滚手段**，
一个都不能漏。新增文件在报告里标注「新增，无原文件可备份」（你已写了，照做）。

### ② 任务二现状被代码推翻 —— **你说得对，我的任务单写错了**

我核实过了，你是对的：

```
traffic_event_engine.py:402   self._persist_event(event)        ← 事件创建时（TRIGGERED）
traffic_event_engine.py:592   self._persist_event(event)        ← _update_event_state() 内部，每次状态流转
```

`_persist_event()` 用 `event_id` 做 upsert 键，**任何状态流转都直接写库**。
所以事件驱动**早就有了**，`routers/realtime.py:1359` 的 `_sync_active_events_to_db()`
只是**另一条兜底路径**（只在查 `/events` 时跑），不是唯一写库路径。

**我错在哪**：上一轮我查库的时机在事件还没确认之前，看到没数据就判定「不查列表就不写库」——
**是采样时机错，不是代码错**。这是我的问题。

**所以任务二改成**：

- **不要重写**。保持 `_persist_event()` 的现有链路。
- 你的做法（「以全程不调 /events、直接查 SQLite 为最终判据；发现缺口再修」）**就是正确做法**。
- 但要**额外验一件事**：`_persist_event()` 失败时会 `except` 吞掉吗？看它的返回值处理。
  如果它是静默失败，那「事件驱动」名义上有了、实际没落库——**这才是要查的真缺口**。
- 判据不变：全程不调 `/events`，直接查库必须有新记录。

### ③ 任务三不只是生成 JSON —— **这条是本次最有价值的发现**

我核实了，你说对了，而且比你说的更严重：

```
realtime_detector.py:797-880   CARLA 切源分支：没有 _scene_cfg_path 赋值，没有 load_scene()
realtime_detector.py:666,702   这两处 load_scene() 只在 start_camera() 的视频分支里
realtime_detector.py:943       _maybe_reload_scene_annotation() 每帧调，但 _scene_cfg_path=None -> 空转
```

**后果**：CARLA 模式下 `_scene_cfg_path` 永远是 `None`，
`_maybe_reload_scene_annotation()` 每帧被调用但什么都不做 →
**标定文件写出来了也永远不会被加载**，测速照样错。

**任务三范围因此扩大**（我任务单写窄了，以你这条为准）：

1. 给 CARLA 源一个**稳定的场景源标识**（不能每帧变，否则 `video_key()` 算出的路径会飘）
2. 让 `_path_for()` 生成的路径真正接到 `_scene_cfg_path`
3. 让 `_maybe_reload_scene_annotation()` 在 CARLA 模式下也能热重载
4. 标定文件本身（stop_line_y / crosswalk_zones / lane_lines / pixel_per_meter
   + 相机高度、俯角、偏航、FOV、画幅）
5. 全部接通后**重跑任务一 + 任务二的联合验收**

**源标识怎么定，我建议但你可以自己判**：
用固定字符串（如 `"carla:Town10HD_Opt:cam_A_handbook:1280x720"`）而不是随机/时间戳，
这样重启后同一个键、同一份标定。**别用 actor id 或 tick 数**——会飘。

### ④ 云端已关 —— 确认，保持关闭

`cloud_review=false` / `cloud_consult=false` 保持不变，验证期间不产生云端费用。
这不影响任何本地判据（数据库、灯态、轨迹、测速全部本地可验）。

---

## 二、开工放行

**现在开始执行。** 顺序按你的计划走：

```
环境基线 → 任务一 → 任务二（只验缺口，不重写）→ 任务三（含接通）→ 联合验收 → 写报告
```

---

## 三、增补：三条你没提但会绊住你的坑

### 坑 1：`tracked_vehicle_count` 可能是 0，那不是 bug

上一轮我查了三次，两次假设被自己推翻。**真因是画面里确实没车**：

- 相机在 `(-15.720, -63.145, 5.732)` 朝路口，视野里只覆盖 2-3 辆车
- `/carla/spawn` 生成 26 个 actor 后，**25 秒后只剩 2 个**，且无销毁日志（CARLA 侧行为）

**所以**：如果 `tracked_vehicle_count=0`，先看 `GET /carla/actors` 里车还在不在、在不在相机视野内，
**不要**去改追踪器代码。上一轮我就在这上面白花了两轮对照实验。

### 坑 2：`/start` 必须带 `video_path` 或保持 carla 源，否则会偷偷开摄像头

`routers/realtime.py` 的 `/start`：如果当前源不是 `carla`，它会无条件调 `start_camera()`，
而 `start_camera()` 内部把 `source_type` 强制写成 `camera` —— **会真的打开本机摄像头**。

上一轮实测踩过：`/source {carla}` → `/start` → `source_type` 变成 `camera`、录了 124 帧本机摄像头。

**所以**：切 CARLA 源之后，`/start` 传 `{}` 是安全的（因为 `cur_src == "carla"` 会跳过 `start_camera`），
但**每次 `/start` 后都要立刻查 `source_type` 确认还是 `carla`**。

### 坑 3：CARLA 可能自己消失

上一轮它跑着跑着进程没了（不是我停的，原因未查）。**每做完一个任务先 `netstat | grep 2000` 确认它还活着**，
否则你会以为是自己代码写错了。

---

## 四、FAIL 的处理（重申）

**任一判据没达到，如实记 FAIL + 你的实测证据，不要改判据。**

特别是任务一：如果 CARLA 本身做不到「让车朝红灯开过停止线」（比如红绿灯 state 无法在
车辆到达前稳定保持红色），**那就写 FAIL，并把你实测到的现象写清楚**。
这个 FAIL 本身是有价值的结论——它告诉下一个人「这条路走不通，别再试」。

---

## 五、报告位置

`E:\output\_wb_p1_report_20261107.md`（你已确认，照做）

写完就结束，不需要等我回复。
