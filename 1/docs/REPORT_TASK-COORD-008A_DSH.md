# TASK-COORD-008A 报告：后端视频采集、推理与事件回放时间轴 只读审计

```text
任务编号：TASK-COORD-008A
执行 Agent：DSH
状态：READY_FOR_REVIEW
复杂度：L3
性质：只读审计。唯一新增文件为本报告（经指挥官明确授权）。
        未修改任何源码、配置、数据库、视频、sidecar、测试、依赖或 Git 状态。
        未启动会写入事件数据的服务，未重跑真实视频，未安装依赖，未清理文件。
读取过的文件：
  E:\output\1\PROJECT_BASELINE.md
  E:\output\1\docs\PROJECT_OPTIMIZATION_DESIGN_2026-09.md
  E:\output\1\docs\REPORT_TASK-COORD-004_TRAE.md
  E:\output\1\docs\REPORT_TASK-COORD-007_TRAE.md
  E:\output\1\docs\REPORT_TASK-COORD-006A_DSH.md      （对照 006A 的结论是否仍成立）
  E:\output\1\api\config.py
  E:\output\1\api\realtime_detector.py                （当前含 003/005/007 改动）
  E:\output\1\api\circular_frame_buffer.py            （当前含 005/007 改动）
  E:\output\1\api\vehicle_tracker.py
  E:\output\1\api\traffic_event_engine.py
  E:\output\1\api\cloud_collaborator.py
  E:\output\1\api\routers\realtime.py                 （当前含 007 replay 路由）
  E:\output\1\api\image_recognizer.py                 （multi_model_detect 模型序列）
  E:\output\1\api\multi_frame_validator.py            （FPSMonitor）
  E:\output\1\web-admin\src\views\EventDetail.vue, RealTimeMonitor.vue（仅交叉核对刷新驱动）
只读探测对象：api/zhitong_violations.db、api/output/event_videos/**（9 sidecar + 23 mp4 + 48 jpg）、
              test_assets/traffic_videos/*.mp4、根目录 1/zhitong_violations.db
实际改动：仅新增 docs/REPORT_TASK-COORD-008A_DSH.md
验证命令及结果：见 §7、§9（全部只读；无服务启动、无写入）
风险与阻塞：见 §5、§10
建议的下一步：见 §9.4
```

---

## 0. 结论摘要

**"回放里检测框更新慢"不是渲染问题，是数据来源问题。**

`_buffer_frame`（`api/realtime_detector.py:496-513`）在**每一个被读取的帧**上写入元数据，而那份元数据是**共享的"最近一次推理结果"**（`self.last_detection_result`，`:502`；`self.tracked_vehicles`，`:508`）——这两者只在 `process_frame` 完成时更新（`:337` / `:368`），而 `process_frame` 被 `frame_interval = 1/Config.FRAME_RATE` 节流到 **≤3 次/秒**（`:274`、`:320-322`），并且在 `process_lock` 被占用时**整跳该 tick**（`:329-330`）。

磁盘实测（9 个真实 sidecar）：

- **6/9 个 sidecar 的 298–300 帧里只有 1 个不同检测状态**；
- 平均每 **72–300 帧**才发生一次框变化；
- 在 10 fps 回放时间轴上 = **每 7.2–30 秒才更新一次框**。

前端 `idx = round(video.currentTime * fps)` 的对齐是**精确的**，它忠实地渲染了一份**几乎不变的**数据。

另有两项确定性时间轴问题：

- **慢放 1.50×**：事件视频写死 `fps = Config.FRAME_BUFFER_FPS = 10`（`:580`），而当前事件的源视频是 **15 fps** → 299 帧回放 29.9 s，源画面真实只经过 19.93 s。（若换 24 fps 源则为 2.40×）
- **sidecar 无源时间戳**：`time = round(index/fps, 3)` 是纯合成时间轴，不含源帧号、墙钟、源 PTS、触发帧索引。

---

## 1. 生效参数表（`api/config.py`）

> `api/config.py` **不在本次 git diff 中** = 审计期间未被改动。

| 参数 | 行号 | 默认值 | 实际作用 | 仓库内是否有覆盖 |
|---|---|---|---|---|
| `FRAME_RATE` | 26 | **3** | 推理节流：`frame_interval = 1/3` → ≤3 次/秒 | 无 |
| `FRAME_BUFFER_FPS` | 43 | **10** | ① `CircularFrameBuffer.fps` ② **事件视频写入 fps** ③ sidecar `time = index/10` | 无 |
| `FRAME_BUFFER_DURATION` | 42 | **30** | 仅用于 `maxlen = 30×10 = 300`，单位是**帧**（非秒预算） | 无 |
| `FRAME_CACHE_SIZE` | 27 | 10 | 云端上下文帧 `frame_cache` deque 长度 | 无 |
| `EVENT_CLIP_BEFORE_SEC` | 44 | **5** | 事件片段起点 = `trigger_time − 5`（**墙钟秒**） | 无 |
| `EVENT_CLIP_AFTER_SEC` | 45 | **5** | ① 片段终点 ② `_handle_event_lifecycle` 先 `sleep(5)` | 无 |
| `CONFIDENCE_THRESHOLD` | 28 | 0.5 | 传入 `multi_model_detect` | 无 |
| `UPLOAD_DIR` / `EVENT_VIDEO_DIR` | 21 / 47 | api/uploads、api/output/event_videos | 证据截图 / 事件媒体 | 无 |

以上均为 `os.environ.get(...)` 的**默认值**；仓库内无 `.env` 加载，`config_runtime.json` 只存 API Key。**实际运行时生效值需测量确认**（本任务未启动服务）。

---

## 2. 调用链简图与各阶段节奏归属（验收第 1 条）

```
cap.read()  ──[无任何限速：文件源全速紧循环]───────────────────┐
   │  frame_count++ / current_frame = frame.copy()             │  ← 预览与缓存的"新画面"
   │  frame_cache.append(frame.copy())                         │
   ├─► _buffer_frame(frame)        【每个读取帧都写】            │
   │      meta = { detections: last_detection_result,          │  ← ★ 旧数据复制点
   │               tracked_vehicles: self.tracked_vehicles,     │
   │               scene_config }                               │
   │      frame_buffer.add(time.time(), frame, meta)  maxlen=300│
   │                                                            │
   └─► if elapsed >= 1/FRAME_RATE (=333ms):                     │
          _process_frame_async(frame)                           │
             process_lock.acquire(blocking=False) ─ 忙 ⇒ 【整跳该 tick，无计数】
             worker 线程: process_frame()                        │
                _yolo_detect → multi_model_detect 【5 个 YOLO 串联】
                vehicle_tracker.update()   ← 跟踪仅在此处推进     │
                behavior_engine.analyze_all()
                _process_event_engine → TrafficEventEngine        │
                last_detection_result = result  ← 唯一更新点       │
                                                  │              │
事件触发 ⇒ 每事件一个 daemon 线程 _handle_event_lifecycle:        │
   sleep(5s) → RECORDING → extract_event_clip_with_meta(±5s墙钟 ∩ 300帧)
        → save_event_video(fps=10) → mp4 + {video}.replay.json
        → submit_to_ai → CloudCollaborator.analyze_event (HTTP)
        → apply_ai_result        （独立线程，不占 process_lock）
```

### 2.1 节奏归属表

| 环节 | 由什么控制 | 现值得出方式 | 证据 |
|---|---|---|---|
| **采集（读取）** | `cap.read()` 紧循环，**文件源无限速/无 pacing**；摄像头源=设备帧率 | 文件源≈解码能力（**未实测**） | `realtime_detector.py:300-315`（无 sleep） |
| **缓存写入** | 每个成功读取帧 1 次 | == 采集 | `:315` `_buffer_frame(frame)` |
| **预览（MJPEG）** | 后端 `await asyncio.sleep(0.05)` → **≤20 fps 上限** | 20 | `routers/realtime.py:196` |
| 预览（snapshot 轮询） | 前端轮询 `detectParams.interval` | 由 008B（Trae）测量 | `RealTimeMonitor.vue:537-539` |
| **推理** | `elapsed >= 1/FRAME_RATE` 节流 **且** `process_lock` 非阻塞抢占 | ≤3 次/秒；实际 `min(3, 1/单帧耗时)` | `:274, :320-322, :329-330` |
| **跟踪** | 只在 `process_frame` 内 `vehicle_tracker.update()` | **== 推理 FPS** | `:368` |
| 轨迹历史 | 每次 `update()` 追加 1 点，`MAX_HISTORY=30` | 3 fps 时 30 点 ≈10 s | `vehicle_tracker.py:64-76` |
| **事件片段** | 墙钟 `[trigger−5, trigger+5]` **∩ deque 300 帧容量** | 实测 298–300 帧（**饱和**） | `circular_frame_buffer.py:131-137`、`:100` |
| **事件视频** | 写死 `fps=Config.FRAME_BUFFER_FPS`，与源 fps 无关 | **10 fps** | `realtime_detector.py:580` |
| **sidecar 框** | == 缓存写入那一刻的"最近推理结果" | **每 72–300 帧才变一次** | `_buffer_frame:502,508` + 9 sidecar 实测 |
| **回放显示** | `idx = round(currentTime*10)`，rAF 60 Hz 驱动 | 刷新很快，**内容受上一条限制** | `EventDetail.vue:663-668` |

### 2.2 为什么"实时识别页看起来流畅，但框更新慢"（机制解释）

`get_annotated_frame()`（`:771-830`）在**每次被预览请求时**取 `self.current_frame`（每读取帧都刷新，`:312`）并**即时重画** `self.last_detection_result` 的框（`:794-796`）。

→ 结果 = **新画面 + 旧框**。文件源全速读取时画面变化很快，MJPEG 以 20 fps 推送，视觉上非常流畅；而框的"内容"只在推理完成时变（≤3 次/秒，实际更低）。

这也是为什么**不能用"画面流畅"推断"推理帧率高"**——两者由完全不同的机制驱动。

---

## 3. 源时间戳 / frame_index / sidecar index / currentTime 的关联（验收第 2 条）

```
源视频帧号 N ──cap.read()──► 墙钟 T = time.time() ──► deque[(T, frame, meta)]
                                                          │  extract_event_clip_with_meta(trigger_time ±5s 墙钟过滤)
                                                          ▼
                                            clip[k] = (T_k, frame_k, meta_k)   k = 在 deque 内的存活序号
                                                          │
                              save_event_video: writer.write(frame_k)  → mp4 第 k 帧 @10fps
                              _write_replay_sidecar: frames[k] = {index:k, time:round(k/10,3)}
                                                          ▼
                                   前端: idx = round(video.currentTime * 10) → frames[idx]
```

| 关联项 | 结论 | 证据 |
|---|---|---|
| `sidecar.frames[i].index` ↔ mp4 帧序 | **一一对应且精确**（同一个 `written_metas` 顺序） | `circular_frame_buffer.py:211-225`、`:282-310` |
| `sidecar.frames[i].time` ↔ `currentTime` | **精确**：`time = round(i/fps,3)`，前端 `i = round(currentTime*fps)` | `:308` + `EventDetail.vue:663-668` |
| **源帧号 N** | ❌ **不记录、不可回溯** | sidecar 无该字段；文件名只有 `event_id` |
| **墙钟 T_k** | ❌ **不持久化**（仅存在于内存 tuple） | sidecar 顶层键实测：`version/event_id/source/video_width/video_height/fps/frame_count/generated_at/frames`，**无任何时间戳字段** |
| **源 PTS / 源 fps** | ❌ 不在 sidecar 中 | 同上 |
| **触发帧索引** | ❌ 不可得（clip 起点与 `trigger_time` 均未落盘） | 006A §Q5 已判定；本次复核**仍未修复** |

### 3.1 实测时间轴失真（新发现，确定性）

| 项 | 源视频 `3e9b3f65…` | 事件视频 `evt_…_79_64e07b` |
|---|---|---|
| 分辨率 | 960×432 | 960×432 |
| **fps** | **15.0** | **10.0**（由写入参数决定） |
| 帧数 | 11071（738.1 s） | 299 |
| fourcc | h264 | h264 |
| 回放时长 | — | 299 / 10 = **29.90 s** |
| 源画面真实时长 | — | 299 / 15 = **19.93 s** |
| **慢放倍数** | — | **1.50×** |

- 根因：`save_event_video(clip, video_path, fps=Config.FRAME_BUFFER_FPS)`（`realtime_detector.py:580`）**没有源 fps 的概念**，输出 fps 是常量。
- 放大效应：`test_assets` 中另外 4 个源视频均为 **24 fps**（1280×576）→ 若用它们触发，慢放将是 **2.40×**。
- 连带影响：sidecar 的 `time` 轴与 `currentTime` 自洽，但**两者都不等于源时间**；因此"第 10 秒发生了越线"这类结论无法从回放时间轴推回真实时间。

---

## 4. ★核心发现：sidecar 框刷新慢的根因（磁盘实测）

### 4.1 根因三方对齐

1. 缓存按**读取帧**打点：`_buffer_frame` 在每个成功读取帧上调用（`:315`）。
2. 元数据是**共享的"最近推理结果"**：`last_detection_result`（`:502`）与 `self.tracked_vehicles`（`:508`）只在 `process_frame` 完成时更新（`:337` / `:368`）。
3. 推理被节流且丢票：`≤3 次/秒`（`:274`、`:320`）+ `process_lock` 忙时整跳（`:329`）。

⇒ 两次推理之间的**全部**读取帧携带**完全相同**的框。

### 4.2 9 个真实 sidecar 的逐条测量

> 度量定义：`不同检测状态` = 逐帧 `(track_id, bbox)` 排序集合的 run 数（内容完全相同的连续帧合并为 1 个 run）。

| sidecar（尾号） | 帧数 | fps | **不同检测状态** | 平均每状态帧数 | 单状态最长帧数 | **折算回放更新间隔** | 平均车辆/帧 |
|---|---|---|---|---|---|---|---|
| `…_16_d2e727` | 298 | 10 | **1** | 298 | 298 | **29.8 s** | 8.00 |
| `…_15_f4f837` | 300 | 10 | **1** | 300 | 300 | **30.0 s** | 10.00 |
| `…_40_24f7a2` | 299 | 10 | 3 | 72 | 184 | 7.2 s | 9.25 |
| `…_42_24611c` | 300 | 10 | 3 | 73 | 184 | 7.3 s | 9.25 |
| `…_55_a86900` | 300 | 10 | **1** | 300 | 300 | **30.0 s** | 15.00 |
| `…_63_ec51e7` | 300 | 10 | **1** | 300 | 300 | **30.0 s** | 15.00 |
| `…_75_613c3b` | 299 | 10 | 2 | 233 | 233 | 23.3 s | 5.55 |
| `…_79_64e07b` | 299 | 10 | 2 | 193 | 193 | 19.3 s | 7.77 |
| `…_80_32d423` | 299 | 10 | 2 | 193 | 193 | 19.3 s | 7.77 |

**结论（置信度：高）**：
- 框是**真实的**（来自真实 YOLO/Tracker 的输出），但**不是"逐帧新鲜"的**——它是"**按推理节拍更新、然后被复制到每一帧**"的。
- 由此需要更正 TASK-COORD-007 报告 §1 的措辞："本地 YOLO/Tracking 逐帧识别框"应表述为"**真实但按推理节拍更新的逐帧回放数据**"。
- 007 §6 浏览器观察到的"帧号 167→218，侧栏条目 6→11"正是这**一次**状态切换，与本测量一致。

### 4.3 推算的采集/推理速率比（需实测确认）

单个状态持续 300 帧（整个 deque）⇒ 这 300 帧是在**一个推理间隔内**读入的 ⇒ `采集fps ≥ 300 × 推理fps`。

| 若推理 fps 为 | 则采集 fps ≥ | 300 帧覆盖的墙钟时间 ≈ |
|---|---|---|
| 3（`FRAME_RATE` 上限） | 900 | 0.33 s |
| 2 | 600 | 0.50 s |
| 1 | 300 | 1.00 s |

**这意味着配置的"触发前 5 秒"实际可能只有 0.3–1.0 秒。** 置信度：饱和事实=高；具体墙钟跨度=**推算**（因 sidecar 未持久化任何时间戳，无法直接测）。

---

## 5. 锁 / 队列 / 跳帧 / 全速读取 / 缓冲 / 云端阻塞（验收第 3 条）

| 机制 | 现状 | 影响 | 证据 |
|---|---|---|---|
| `self.lock` = **RLock** | 采集循环、worker、`get_annotated_frame`、`get_status` 共用；均为极短临界区 | 未见死锁风险；但**预览请求会与采集循环抢锁**（`current_frame.copy()` ≈1.24 MB 拷贝在锁内） | `:64`、`:310-313`、`:772-791` |
| `self.process_lock` = Lock（非阻塞抢占） | **不是队列，是"丢票"**：忙则整跳该 tick，**无丢帧计数** | 推理吞吐被单帧耗时锁死；**丢帧率不可观测** | `:65`、`:329-330` |
| 推理队列 | **不存在**（无"最新帧队列"）；只有 `current_frame`(1) + `frame_cache`(10) + `frame_buffer`(300) | 无背压、无优先级、无过载策略 | — |
| **文件源全速读取** | `cap.read()` 紧循环无 sleep；004 记录 11071 帧只处理 15 帧 | 短片（<1 min）在建立轨迹前读完；触发前"5 秒"严重缩水 | `:300-315`；`REPORT_TASK-COORD-004` §8.1 |
| deque 容量是**帧数**预算 | `maxlen=300` **帧**；窗口过滤用**墙钟秒** | 全速读取时 5+5 s 窗口被容量截断 → 实测片段 298–300 帧（**9/9 饱和**） | `circular_frame_buffer.py:100`、`:131-137` |
| 内存占用 | `frame_buffer` ≈ 300 × 960×432×3 B ≈ **373 MB**；`frame_cache` ≈12 MB；另加每事件线程 | 常驻内存放大（有界，非泄漏） | 由 `:508` + 分辨率实测计算 |
| **云端 AI 是否阻塞处理链** | **不阻塞检测循环**（每事件独立 daemon 线程，不占 `process_lock`） | 三个间接风险：① 每事件 1 线程，持有最多 300 帧 ≈**370 MB**；② 事件视频路径已取一次 clip（`:574`），云端路径**再取一次**（`:603`）；③ 无并发上限、无超时/重试可见性 | `:538-543`、`:560`、`:574`、`:603`、`:610` |
| 事件收尾 | `sleep(EVENT_CLIP_AFTER_SEC=5)` 后提取 | 文件读到 EOF 后 `cap.read()` 返回 False → **不再入缓存**，"后 5 秒"实为"文件末尾那 300 帧" | `:560` + `:307-309` |
| 孤儿同步缺口 | stop 时未同步的 active 事件不落 DB | 实测已产生 6 个孤儿 sidecar/视频（§7） | 007 §9.1 + 本次计数 |

---

## 6. 发现 / 证据 / 置信度总表（验收第 4 条）

| # | 发现 | 类型 | 证据 | 置信度 |
|---|---|---|---|---|
| F1 | 两次推理之间的所有缓存帧共享同一份框；6/9 sidecar 全程仅 1 个状态 | **当前代码 + 磁盘数据** | `_buffer_frame:502,508`；9 sidecar 实测 | **高** |
| F2 | 事件视频写死 10 fps，源 15 fps → 回放慢放 1.50× | **当前代码 + 实测** | `:580`；cv2 实测两侧 fps | **高** |
| F3 | sidecar 无源帧号、无墙钟、无源 PTS、无触发帧索引 | **磁盘数据 + 代码** | sidecar 顶层键实测；`:306-322` | **高** |
| F4 | 5+5 s 窗口被 300 帧容量截断，实际片段远短于 10 s | **代码 + 饱和事实** | 9/9 = 298–300 帧 | **高**（截断）/ 中高（具体跨度） |
| F5 | `current_fps = 1/(now − last_process_time)`，而 `last_process_time` **只在 `start_detection` 写一次**（`:258`）→ 单调衰减到 0；预览左下角的 `FPS:` 不可用 | **当前代码** | `:49`、`:258`、`:955-958`、`:827-828` | **高** |
| F6 | `multi_model_detect` 已算出 `duration_ms` 但**零消费** | **当前代码** | `image_recognizer.py:867`；`duration_ms\|inference_duration` 在 `realtime_detector.py`/`routers/realtime.py` **0 命中** | **高** |
| F7 | 每处理帧串联 **5 个 YOLO 模型**（vehicle→traffic_light→helmet→lane→license_plate），且每模型重复 base64 解码 | **当前代码** | `image_recognizer.py:837-846`；`:662-664` | **高**（成本量化需实测） |
| F8 | `process_lock` 忙时整跳 tick 且**无丢帧计数** | **当前代码** | `:329-330` | **高** |
| F9 | 云端复核不阻塞检测循环，但每事件 1 线程 + 同窗口 clip 取两次 | **当前代码** | `:538-543`、`:574`、`:603` | **中高**（内存峰值需实测） |
| F10 | 23 个 mp4 / 48 张 jpg / 9 个 sidecar 中，有 **6 个孤儿事件产物**（无 DB 行） | **磁盘实测 + DB 实查** | §7 | **高** |
| F11 | 根目录出现 **0 字节空 DB** `1/zhitong_violations.db` | **磁盘实测** | size=0；`no such table: traffic_events` | **高** |
| F12 | 004 记录的"11071 帧只处理 15 帧""读取 ~833 fps" | **仅历史报告** | `REPORT_TASK-COORD-004` §2/§4 | **中**（本次未复跑，按禁止项未重跑） |

---

## 7. 产物与数据库现状（只读实测）

```
api/output/event_videos/20260925/
  mp4 总 23 = 7 原始 FMP4 + 7 _h264 副本 + 3 新代(有 DB 行) + 6 新代(孤儿)
  jpg 总 48 = 21 迁移代 + 27 新代(9 事件 × 3 帧)
  sidecar  9 = 3 有 DB 行 + 6 孤儿          ← 与 007 §9.1 "stop 不同步" 一致

api/zhitong_violations.db : traffic_events = 10 行（7 迁移代 + 3 新代，state 全为 pending_ai）
1/zhitong_violations.db   : 存在，0 字节，无任何表（untracked）   ← F11 / E1

视频属性实测：
  新代   evt_…_79_64e07b.mp4        → 960×432 / 10.0 fps / 299 帧 / h264
  迁移代 evt_…_20_4ff131_h264.mp4   → 960×432 / 10.0 fps / 300 帧 / h264
源视频 test_assets/traffic_videos/：
  3e9b3f65… 960×432  15.0 fps 11071 帧 h264   ← 当前事件的源
  其余 4 个 1280×576 24.0 fps（168 / 479 / 248 / 196 帧）hevc
```

---

## 8. 仍需真实运行测量（不猜测，明确标记）

| # | 待测项 | 为什么现在测不了 | 建议测法 |
|---|---|---|---|
| M1 | **实际采集 FPS**（文件源 / 摄像头源） | 需启动服务读帧；sidecar 未持久化时间 | 加计数器后由 `/status` 暴露 `read_fps` |
| M2 | **实际推理 FPS** 与单帧 `duration_ms` (P50/P95) | 同上 | 消费已存在的 `duration_ms`；或读可信的 `avg_fps` |
| M3 | **丢帧数** | 无计数器（F8） | `process_lock` 失败处自增 |
| M4 | 300 帧在**墙钟**上覆盖多少秒 | sidecar 无时间戳（F3） | 在 `add()` 记 span，或 sidecar 记 `captured_at_first/last` |
| M5 | 事件片段相对**源视频**的真实位置与触发帧索引 | 未持久化（F3） | 记 `cap.get(cv2.CAP_PROP_POS_FRAMES)` |
| M6 | 云端复核对**线程/内存**的实际压力 | 未运行 | 多事件并发时采样线程数与 RSS |
| M7 | F5 的 `current_fps` 衰减曲线 | 需运行 | 连续读 `/status` 对比 `current_fps` vs `avg_fps` |
| M8 | 004 的"833 fps 读取 / 11071→15 帧" | 本次未复跑（禁止项） | 复跑同一源视频 + 新埋点 |

> 现有 `/status` 中**唯一可信的推理帧率指标是 `avg_fps`**（`FPSMonitor`，`process_frame:406` 每次推理完成 tick 一次，窗口 30，`multi_frame_validator.py:263-283`）；`current_fps` 因 F5 不可用。

---

## 9. 建议的最小实现边界、埋点与量化验收（本 TASK 不实现）

### 9.1 最小埋点位置（按性价比排序）

| # | 文件 : 位置 | 埋点 | 成本 |
|---|---|---|---|
| B1 | `realtime_detector.py:666-668`（`_yolo_detect`） | **消费已存在的** `result['duration_ms']` → `self.last_infer_duration_ms` | **零**（数据已算出） |
| B2 | `realtime_detector.py:329-330` | `acquire` 失败 → `self.dropped_ticks += 1` | 零 |
| B3 | `realtime_detector.py:955-958`（`get_status`） | 修 `last_process_time`（或在 worker `:337` 后写）；`current_fps` 改为真实值 | 极低 |
| B4 | `realtime_detector.py:306-315` | 记 `read_seq`、`cap.get(CAP_PROP_POS_FRAMES)`、`time.time()` → 聚合 `read_fps` | 低 |
| B5 | `realtime_detector.py:get_status` | 新增（只增不改）`read_fps / infer_fps / dropped_ticks / infer_duration_ms / frame_buffer_span_sec / last_infer_age_ms` | 低 |
| B6 | `circular_frame_buffer.py:106-117` | `add()` 记 `evicted_count`；新增 `span_seconds` 属性 | 低 |
| B7 | `circular_frame_buffer.py:_write_replay_sidecar:312-322` | sidecar 增 `schema_version / source_fps / captured_at_first / captured_at_last / trigger_index`（无法精确定位时写 `null`） | 低 |

### 9.2 最小文件边界（建议 TASK-COORD-009，对应设计稿阶段 A）

- **可改**：`api/realtime_detector.py`（采集节流开关 + B1–B5）、`api/circular_frame_buffer.py`（B6–B7）、`api/config.py`（**仅新增开关**，不改既有默认语义）、`api/routers/realtime.py`（`/status` **只增**字段）、`tests/`
- **禁改**：YOLO 模型序列与阈值、Tracking 算法、`TrafficEventEngine` / `EvidenceChain`、已有 23 mp4 / 48 jpg / 9 sidecar、DB 结构、前端（Trae 008B 负责）
- **需指挥官批准的**行为级决策（不应在 009 默认执行）：
  1. 是否给**文件源加节流**（按源 fps `sleep`）—— 改变采集语义
  2. 是否提高 `FRAME_RATE` 默认值 —— 受 F7（5 模型串联）限制，可能必须先削减模型串联数
  3. 是否给 sidecar 记 `trigger_index` —— 需先持久化 clip 起点

### 9.3 量化验收建议

用**同一固定片段**（建议 `3e9b3f65` 的固定 20 s 区间，或一个 <60 s 短片）前后各跑一次：

| # | 指标 | 当前（基线） | 建议目标 |
|---|---|---|---|
| 1 | `read_fps` / `infer_fps` / `dropped_ticks` | **不可观测** | 三项均可见 |
| 2 | `infer_duration_ms` P50/P95 | 不可观测（已算出却被丢） | 可见 |
| 3 | 事件片段**墙钟跨度** / 配置的 10 s | 推算 0.3–1.0 s，**未测** | 实测并说明差距 |
| 4 | **sidecar 状态数 / 帧数** | **1/300 … 3/300** | ≥ 与 `infer_fps × 片段墙钟秒数` 同量级 |
| 5 | 事件视频**慢放倍数** = (帧数/源fps) ÷ (帧数/写入fps) | **1.50×**（源 15）/ 2.40×（源 24） | ≤1.05×，或在 sidecar 显式记录源 fps + 采样率 |
| 6 | 短片（<60 s）`processed_frames` | 1（004 实测） | >1 且能建立轨迹并触发事件 |
| 7 | 孤儿产物数 | **6** | 0（stop 时同步 active 事件） |

**通过条件（建议）**：1–3、5、6 可读且达标；4 的比值较基线提升 ≥3×；7 归零。

### 9.4 建议的下一 TASK

- **`TASK-COORD-009`（阶段 A：后端可观测性与时间轴对齐）**：范围 = §9.1 的 B1–B7 + §9.3 验收表。与 Trae 的 **008B**（前端实时/回放体验与指标展示）按"后端 `realtime_detector.py`/`circular_frame_buffer.py` vs 前端 `.vue`"边界并行，互不同文件。
- 其后：阶段 B（证据与事件生命周期可靠性，含 E2 孤儿产物与 stop 同步）、阶段 C（场景配置 MVP）、阶段 D（统一车辆面板）、阶段 E（统计与模型评测）——见 `docs/PROJECT_OPTIMIZATION_DESIGN_2026-09.md` §6。

---

## 【发现的额外问题】（只记录，未修改）

| # | 文件/模块 | 问题 | 阻塞本 TASK | 建议后续 TASK |
|---|---|---|---|---|
| E1 | `1/zhitong_violations.db` | **0 字节空 DB 文件已出现**（untracked）。`Config.DB_PATH` 从"文件不存在"变成"存在但无表"→ 依赖它的检查（如 `tests/test_task029_integration.py` 第 7 项）状态改变，且会误导 DB 路径排查。006A 额外问题 1 的延续 | 否 | 明确唯一权威 DB 并清理空文件 |
| E2 | `api/output/event_videos/20260925/` | **6 个孤儿事件产物**（6 mp4 + 18 jpg + 6 sidecar 无 DB 行），根因是 stop 时未同步 active 事件（007 §9.1，本次已计数确认） | 否 | 阶段 B：stop 流程同步 + 孤儿/缺失文件诊断 |
| E3 | `api/realtime_detector.py:955-958` | `current_fps` 语义错误（`last_process_time` 永不更新）→ 预览上显示的 FPS 不能用于任何验收 | 否 | 并入 009 的 B3 |
| E4 | `api/image_recognizer.py:867` → `api/realtime_detector.py:666` | 推理耗时算出来即丢弃，零可观测性 | 否 | 并入 009 的 B1 |
| E5 | `api/realtime_detector.py:538-543, 603` | 每事件 1 线程 × 最多 300 帧（≈370 MB）+ 同窗口 clip 取两次；无并发上限 | 否 | 有界事件队列（设计稿 §4 的 CloudAI 独立队列） |
| E6 | `api/circular_frame_buffer.py:100, 131-137` | `duration_sec` 语义被 `maxlen=帧数` 偷换；窗口是秒、容量是帧，二者解耦导致"前 5 秒"不可信 | 否 | 阶段 A 核心（TASK-COORD-009） |
| E7 | `api/image_recognizer.py:837-846` | 单帧串联 5 个 YOLO；`multi_model_detect` 未提供"按需模型子集"，无法在不改算法的情况下降低推理成本 | 否 | 性能 TASK（需指挥官决策） |
| E8 | `web-admin` ↔ 设计稿 §4.2 | 界面用单一"FPS"混称采集/推理/预览/跟踪/回放 | 否 | 008B（Trae）+ 阶段 D |
| E9 | `docs/REPORT_TASK-COORD-007_TRAE.md` §1 | "逐帧识别框"措辞与实际"按推理节拍更新"不符（本次已实测证伪"逐帧新鲜"） | 否 | 文档更正（不改代码） |

---

## 【本次任务模型信息】

- **实际使用模型**：当前环境无法可靠读取实际模型名称。
- **任务复杂度**：**L3**
- **模型选择理由**：本任务要求跨"采集循环 → 推理节流/锁 → 跟踪 → 循环缓存 → 事件线程 → 视频与 sidecar 落盘 → 回放时间轴"整条链做**帧率与时间戳的根因归因**，并必须把「当前代码证实」「磁盘实测」「仅历史报告」「需运行测量」四类证据严格分开。难点不在实现量，而在于：① 识别"元数据是共享的最近推理结果"这一隐蔽数据来源；② 用磁盘上 9 个真实 sidecar 把"框更新慢"从主观感受量化为 72–300 帧/状态；③ 用两侧 fps 实测把"慢放 1.5×"从推断变成数字。按 L3 执行，未为节省成本降低所需能力。
- **是否发生模型切换**：否。
- **切换原因**：不适用。全程未遇能力瓶颈；唯一工具限制是 `modlens` 视觉桥在本机不可用（No vision provider），本任务不依赖图像判读，未因此降低结论强度。
- **边界遵守**：未启动任何服务、未重跑真实视频、未写 DB/sidecar/视频、未安装依赖、未执行任何 git 破坏性命令。全部结论来自只读代码定位 + 只读文件/DB/视频属性探测。

---

*报告结束。本任务唯一新增文件为本报告；其余工作区改动（含 TASK-COORD-003/005/006B/007 的未提交内容）均原样保留。*
