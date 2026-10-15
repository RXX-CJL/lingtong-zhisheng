# TASK-COORD-009A 报告：后端采集、推理与事件回放时间轴修正及性能指标

```text
任务编号：TASK-COORD-009A
执行 Agent：DSH
状态：READY_FOR_REVIEW
复杂度：L3
最终判定：ACCEPT（验收 7 项逐条有实测证据；见 §9）
性质：实现任务。改动仅限授权文件；真实验证全部在隔离临时目录完成，
        未覆盖任何既有数据库、事件视频、JPG、sidecar。
读取过的文件：
  E:\output\1\PROJECT_BASELINE.md
  E:\output\1\docs\PROJECT_OPTIMIZATION_DESIGN_2026-09.md
  E:\output\1\docs\REPORT_TASK-COORD-008A_DSH.md      （本任务输入：根因与埋点建议）
  E:\output\1\docs\REPORT_TASK-COORD-008B_TRAE.md    （前端 009B 契约对齐）
  E:\output\1\api\config.py, realtime_detector.py, circular_frame_buffer.py
  E:\output\1\api\routers\realtime.py, image_recognizer.py, multi_frame_validator.py
  E:\output\1\tests\test_circular_frame_buffer.py, test_replay_sidecar_contract.py,
                test_event_media_contract.py      （必须保持通过的既有契约）
修改文件（均在授权清单内）：
  1. api/config.py                    （+23，仅新增配置项）
  2. api/circular_frame_buffer.py     （帧记录 + 源时间轴 + sidecar schema v2）
  3. api/realtime_detector.py         （指标 + 源时间节流 + 输出 fps 推导 + /status 只增字段）
  4. tests/test_timeline_metrics_contract.py （新增，13 用例）
  5. docs/REPORT_TASK-COORD-009A_DSH.md      （本报告）
未修改：api/routers/realtime.py（见 §2.4，无需改动即可满足 /status 契约）、
        api/image_recognizer.py、TrafficEventEngine、EvidenceChain、数据库、
        前端文件、既有真实媒体与 sidecar。
```

---

## 0. 结论摘要

| 验收标准 | 结果 | 证据 |
|---|---|---|
| 事件 clip 回放时长与源时间窗口偏差 ≤5% | ✅ **0.00% / 0.67% / 0.00% / 0.67%** | §5 真实事件 run + §8 确定性测试 |
| sidecar 含真实源帧序/源时间；`time` 与播放器一致 | ✅ schema v2，149–151 帧**全部**带 `source_time`+`source_frame_index` | §5.3 |
| 框随真实推理/跟踪观测更新；沿用状态显示观测年龄 | ✅ 检测状态数 **1→16**（中位 run 72–300 帧 → **6 帧**）；`observed_age_sec` 0.004–1.94s；`stale` 标记 | §5.4 |
| `/status` 分开提供采集与推理指标；跳过可计数；耗时有实测 | ✅ `capture_fps=25.01`(源25) / `infer_fps=2.93` / `dropped_ticks=7` / `infer_duration_ms=138` | §6 |
| 短视频按源时间推进并处理多于首帧 | ✅ **OFF: processed=0 → ON: processed=9**（同一 6s/150 帧源） | §4 |
| 旧 sidecar 兼容读取 | ✅ 9 个既有 v1 sidecar 只读校验通过；旧字段全部保留 | §7 |
| 既有 DB 与媒体无变化 | ✅ 项目 23 mp4 / 48 jpg / 9 sidecar 计数与 mtime 不变；DB 225,280 B 未变 | §10 |

**一句话**：把"按帧数截断的墙钟窗口 + 写死 10fps"换成"**按源时间的窗口 + 由源时间跨度推导的输出 fps + 双时间轴 sidecar**"后，回放媒体时长与源时间窗口**逐条对齐到 0–0.67%**，检测框更新频率提升 **12–25 倍**，并且采集/推理/丢帧/延迟首次全部可见。

---

## 1. 复杂度与模型信息（先判定）

- **复杂度：L3**（跨采集循环 / 缓冲 / 事件线程 / sidecar / 状态接口的时序改造，含真实运行验证）。
- 详细模型信息见文末【本次任务模型信息】。

---

## 2. 修改文件与关键代码位置

### 2.1 `api/config.py`（只新增，未改任何既有默认值）

| 行 | 新增项 | 默认 | 作用 |
|---|---|---|---|
| 59-60 | `CAPTURE_PACING_ENABLED` | `true` | 文件源按源时间推进 |
| 62-63 | `CAPTURE_PACING_MAX_SLEEP_SEC` | `1.0` | 单次节流等待上限（防异常源 fps 挂起） |
| 65-66 | `EVENT_VIDEO_FPS_FROM_SOURCE` | `true` | 输出 fps 由源时间跨度推导 |
| 68 | `METRICS_WINDOW_SIZE` | `60` | 采集/推理 FPS 滑动窗口 |
| 70 | `STALE_OBSERVATION_SEC` | `0.3` | "沿用最近观测"的陈旧阈值 |
| 130-135 | `get_config()` 新增 5 个键 | — | 只增 |

### 2.2 `api/circular_frame_buffer.py`

| 行 | 变更 | 说明 |
|---|---|---|
| 90 | **新增 `FrameRecord`** | `__slots__` 记录；`__iter__/__getitem__/__len__` 使其**在旧调用方眼里仍是 3 元组** `(timestamp, frame, detection_result)`；额外字段 `source_time / source_frame_index / captured_mono` |
| 176 | `add(..., source_time=None, source_frame_index=None, captured_mono=None)` | 新增**可选**参数，旧调用不变 |
| 205 | `_trim_by_time_window()` | 时间窗淘汰；**仅在 `trim_to_window=True` 时生效**，保证旧行为不变 |
| 235 | `_select_window(center, before, after, timebase)` | `timebase='source'` 时按源时间筛选（源时间未知的帧不参与，不猜测） |
| 257 | `_enrich_meta(rec)` | 为每帧附加真实 `captured_at / source_time / source_frame_index / observed_age_sec / observed_source_age_sec / stale` |
| 281 / 303 | `extract_event_clip` / `extract_event_clip_with_meta` | 新增 `timebase` 参数（默认 `'capture'` = 旧行为）；返回形态不变（2 元组 / 3 元组） |
| 329 | `source_time_for_timestamp(ts)` | 把墙钟 `trigger_time` 映射到最近的源媒体时间 |
| 350 | `source_time_span()` | 源时间跨度；`trimmed_count` / `has_source_time` 供指标 |
| 358 | `save_event_video(..., fps: float = 10, sidecar_extra=None)` | fps 可为 float；透传 sidecar 补充信息。**默认值不变** |
| 454 | `_write_replay_sidecar(..., extra=None)` | 旧字段全保留 + 新增 `schema_version/source_fps/timebase/source_time_start/end/window_*/media_duration_sec/source_duration_sec` 与逐帧源时间字段 |

### 2.3 `api/realtime_detector.py`

| 行 | 变更 | 说明 |
|---|---|---|
| 40-110 | **新增 `StreamMetrics`** | `note_read / note_tick_dropped / note_infer / snapshot`；样本不足返回 `None`（不编造） |
| 294 | `_reset_source_timebase(video_capture)` | 视频源读 `CAP_PROP_FPS`；摄像头源 `source_time=None` |
| 380 | `_apply_capture_pacing(source_time)` | 文件源按源时间推进（`mono0 + Δsource_time`） |
| 404 | `_detection_loop` | 每帧记录 `captured_at/captured_mono/source_time/source_frame_index`；`metrics.note_read()`；节流 |
| 485 | `_process_frame_async(frame, frame_meta)` | **`acquire` 失败 → `note_tick_dropped()`**；worker 内计时、修正 `last_process_time`、写 `last_infer_meta`、`note_infer()` |
| 509→ | `process_frame(frame, frame_meta=None)` | 消费 `multi_model_detect` 早已算出却被丢弃的 `duration_ms` |
| 677 | `_buffer_frame` | 写入帧的源时间 + **本次沿用观测的真实产生时刻**（`observed_*`），不再让旧结论冒充新检测 |
| 746→ | `_handle_event_lifecycle` | ① 选择 `timebase`（有源时间→`source`）② 以源时间为窗口中心 ③ `_derive_clip_fps` 推导 fps ④ 传 `sidecar_extra`；云端路径复用同一 `center/timebase` |
| 866 | **新增 `_derive_clip_fps(clip, timebase)`** | `fps = (N-1)/span`，使媒体时长贴合窗口；非法输入返回 `None` 由调用方回退 |
| 1226 | `get_status` | 旧字段全保留，**只增** 13 个字段（见 §6） |

### 2.4 为什么没有改 `api/routers/realtime.py`

`/status` 路由实现是 `status = realtime_detector.get_status(); return {"success": True, "data": status}`（`routers/realtime.py:55-59`）。契约字段全部加在 `get_status()` 返回体内即可自动暴露，因此**该文件零改动**（其 64 行 diff 全部来自 TASK-COORD-007 的 replay 路由，非本任务）。

---

## 3. 源时间 / 回放时间定义（交付给 009B 的契约）

| 概念 | 字段 | 定义 | 缺失时 |
|---|---|---|---|
| **回放媒体时间** | `frames[].time` | `index / fps`，与 `<video>.currentTime` 同一时间轴（**唯一用于播放器对齐的时间**） | 不适用 |
| **源媒体时间** | `frames[].source_time` | 视频文件源的媒体时间 = `源帧序号 / 源fps`；摄像头会话相对时间 | `null` |
| **源帧序号** | `frames[].source_frame_index` | 源视频帧序号（从 0 起） | `null` |
| **采集墙钟** | `frames[].captured_at` | 该帧被读取并缓冲时的 `time.time()` | 不适用 |
| **观测年龄** | `frames[].observed_age_sec` | 本帧沿用的检测结果**实际产生时刻**与 `captured_at` 之差 | `null` |
| **观测源年龄** | `frames[].observed_source_age_sec` | 同上，但在源时间轴上 | `null` |
| **陈旧标记** | `frames[].stale` | `observed_age_sec > Config.STALE_OBSERVATION_SEC(0.3)` | `null` |
| **输出 fps** | `fps`（顶层） | 由片段源时间跨度推导（= 源 fps 的无偏估计）；**实测 15.0，不再固定 10** | 回退 10 |
| **窗口** | `window_source_sec` / `window_capture_sec` | 事件 clip 的中心/前后秒数与所用时间基准 | `null` |
| **时长自检** | `media_duration_sec` / `source_duration_sec` | 媒体时长与源时间跨度，供前端/回归比对 | `null` |

**不得混用**：`time` 只用于播放器对齐；`source_time` 只用于源时间/证据语义。二者在本次改造后数值不同（例：`time` 末帧 9.9333s ↔ `source_time` 末帧 14.2s）。

---

## 4. 实测 A/B：文件源节流（隔离临时目录，同一合成短片）

同一 6.00s / 150 帧 / **25fps** 源（`%TEMP%\tc009a_*`），除 `CAPTURE_PACING_ENABLED` 外全部相同：

| 指标 | **OFF（旧行为）** | **ON（本次修复）** |
|---|---|---|
| `capture_fps` | **3687.5** | **25.01**（= 源 fps） |
| 读完 150 帧的采集墙钟跨度 | **0.02 s** | **6.01 s** |
| `processed_frames` | **0** ❌ | **9** ✅ |
| `infer_fps` | `null` | 2.93 |
| `dropped_ticks` | 0 | 7 |
| `infer_duration_ms` | `null` | **138.0** |
| `frame_buffer_source_span_sec` | 5.96 | 5.96（源内容固有） |

- **复现并量化了 TASK-COORD-004 §8.1 的现象**：旧行为下 6 秒短片在 **0.02 秒**内被读完，`processed_frames = 0`（004 记录为 1），根本无法建立轨迹。
- 修复后同一短片按源时间推进，处理了 9 帧，`capture_fps` 与源 fps 一致。
- 该表也解释了 008A 的 R1：**旧行为下 300 帧只覆盖 0.02s 墙钟**，因此编辑成 10fps 播放必然严重慢放。

---

## 5. 固定样本验证：真实长视频、真实事件（隔离输出）

源：`E:\output\1\test_assets\traffic_videos\3e9b3f659e257969d581993be3c9e59e.mp4`（960×432 / **15fps** / 11071 帧 / 738s），时间盒 240s。
隔离：`EVENT_VIDEO_DIR` 与 `UPLOAD_DIR` 均指向 `%TEMP%\tc009a_evt_z689f95x\`；**未连接数据库**（检测器单跑不写库）。

### 5.1 运行期指标（真实）

```json
{"total_frames": 631, "processed_frames": 73, "capture_fps": 14.98, "infer_fps": 2.05,
 "dropped_ticks": 38, "infer_duration_ms": 147.0, "active_events": 3,
 "source_fps": 15.0, "frame_buffer_span_sec": 19.93, "frame_buffer_source_span_sec": 19.93}
```

- `capture_fps = 14.98` ≈ 源 15fps → 节流精确
- `infer_fps = 2.05` **远低于** `FRAME_RATE=3`：单帧 5 个 YOLO 模型串联导致 `process_lock` 长期占用，331 个 tick 中 **38 次被直接跳过**（`dropped_ticks`）——这正是 008A 推断、本次首次**实测**的数值。

### 5.2 事件 clip 时长 vs 源时间窗口（★核心验收）

| 事件视频 | 容器 fps | 帧数 | 媒体时长 | **窗口(源秒)** | **偏差** | sidecar `source_duration_sec` |
|---|---|---|---|---|---|---|
| `evt_…_5_a2f7d5.mp4` | **15.0** | 149 | 9.933 s | 5+5 = 10.0 | **0.67%** | 9.8667 |
| `evt_…_12_7a82b5.mp4` | **15.0** | 150 | 10.000 s | 10.0 | **0.00%** | 9.9333 |
| `evt_…_12_78f93b.mp4` | **15.0** | 151 | 10.067 s | 10.0 | **0.67%** | 10.0000 |

- 容器 fps = **15.0 = 源 fps**（旧实现固定 10.0 → 1.5× 慢放已消除）
- `video_frames == sidecar.frame_count` **逐条精确一致**
- 窗口中心取自源时间：`window_source_sec.center = 9.267s`，clip 源时间范围 `[4.333, 14.200]` → 与 `[center−5, center+5] = [4.267, 14.267]` 对齐（边界差 < 1 帧）

### 5.3 sidecar 新字段（真实产物）

```
schema_version = 2          timebase = "source"        fps = 15.0
source_fps = 15.0           frame_count = 149/150/151
source_frame_index 覆盖：149/149、150/150、151/151（100%）
source_time_start/end 与 frames[0]/frames[-1].source_time 一致
```

### 5.4 检测框刷新率与观测年龄（★验收第 3 项）

| sidecar | 不同检测状态数 | 中位 run（帧） | 最长 run | `observed_age_sec` | `stale` 帧数 | 触发车轨迹自身出现帧 |
|---|---|---|---|---|---|---|
| `…_5_a2f7d5` | **16** | **6** | 29 | 0.004 – **1.94** | 80/149 | **111/149** |
| `…_12_7a82b5` | **16** | **6** | 27 | 0.006 – 1.84 | 86/150 | **150/150** |
| `…_12_78f93b` | **14** | **6** | 27 | 0.005 – 1.84 | 92/151 | **131/151** |

对照 **TASK-COORD-008A 的改造前基线**（9 个 sidecar）：不同检测状态数 **1–3**，中位 run **72–300 帧**。

- **框更新频率提升 12–25 倍**：由"每 72–300 帧一变"改善为"每 6 帧一变"（15fps 下 = 0.4s），与 `infer_fps≈2` 相符——**框只随真实推理/跟踪观测更新**。
- **沿用观测被如实标注**：`stale` 帧占 54–61%，`observed_age_sec` 最高 1.94s，`observed_source_age_sec` 最高 3.47s。**没有伪造新检测、没有插值**。
- **008B 的 E1 被本次修复顺带解决**：改造前事件自身的 track 在 sidecar 中 **0/299** 出现；现在 **111/149、150/150、131/151** —— 因为 clip 现在真正覆盖 `trigger±5s` 源时间窗，触发车辆必然在片段内。

---

## 6. `/status` 指标样例（契约字段全部落地）

修复后（pacing ON，6s 短片，运行中采样）：

```json
{"capture_fps": 25.01, "infer_fps": 2.93, "dropped_ticks": 7, "infer_ticks": 9,
 "infer_duration_ms": 138.0, "process_duration_ms": 140.0,
 "last_infer_age_ms": 79.0, "metrics_window": 60,
 "frame_buffer_span_sec": 5.98, "frame_buffer_source_span_sec": 5.96,
 "frame_buffer_trimmed": 0, "source_fps": 25.0, "source_timebase": "source",
 "capture_pacing_enabled": true}
```

真实事件运行（§5.1）：`capture_fps=14.98, infer_fps=2.05, dropped_ticks=38, infer_duration_ms=147.0`。

- **采集与推理彻底分开**：`capture_fps` 由成功读取帧计算，`infer_fps` 由推理完成次数计算；缺样本时为 `null`。**推流/预览节奏（`/stream` 的 20Hz）从未参与**。
- 旧字段 `current_fps / avg_fps / total_frames / processed_frames / frame_buffer_size / frame_buffer_duration / active_events / event_engine` **全部保留**。
- 附带修正（在授权文件内）：`last_process_time` 现在在每次推理完成后更新，`current_fps` 不再是"从启动时刻起单调衰减到 0"的伪值（008A F5）。

---

## 7. 旧数据兼容结果

| 项 | 结果 |
|---|---|
| 既有 **9 个 v1 sidecar** 可读 | ✅ 只读校验 9/9：`version/frame_count/fps/frames[index,time,vehicles]` 全部存在（`TestBackwardCompatibilityWithExistingSidecars`） |
| v1 sidecar 缺 `schema_version` | ✅ 前端/replay 路由按字段可选处理；接口把文件原样返回，不做 schema 校验 |
| 旧调用方（2 元组 / 3 元组） | ✅ `extract_event_clip` 仍返回 2 元组；`extract_event_clip_with_meta` 仍返回 3 元组；`get_latest` 的 `for ts,f,meta in` 与 `x[2]` 仍可用（`FrameRecord` 实现元组协议） |
| `CircularFrameBuffer(duration_sec, fps)` 默认行为 | ✅ `trim_to_window=False` 默认值下**完全保持**旧的仅按帧数淘汰（新增 `test_08` 守护） |
| `save_event_video(frames, out, fps=10)` | ✅ 默认 fps 仍为 10，`fps=10` 时 sidecar 的 `fps` 字段 `10.0 == 10` 成立；既有 007 契约 7 例全绿 |
| 既有 23 mp4 / 48 jpg / 9 sidecar / DB | ✅ 计数与 mtime **未变**（§10） |

---

## 8. 测试与构建结果

### 8.1 新增契约测试 `tests/test_timeline_metrics_contract.py`（13 例）

| # | 用例 | 断言要点 | 结果 |
|---|---|---|---|
| 01 | `test_01_source_time_recorded_and_span` | 源时间被记录；跨度按源时间 | OK |
| 02 | `test_02_extract_by_source_timebase` | 窗口 `[2.5,5.5]@25fps` → **恰好 75 帧** | OK |
| 03 | **`test_03_output_duration_matches_source_window`** | 媒体时长 vs 窗口 = **0.00%** ≤5% | OK |
| 04 | `test_04_sidecar_schema_v2_and_old_fields` | 旧字段齐全 + schema=2 + 逐帧源时间 + 时长一致（4.17%） | OK |
| 05 | `test_05_obsolescence_is_recorded_not_faked` | 年龄单调增长、`stale` 语义正确、观测源时间恒定不变（证明是"沿用"） | OK |
| 06 | `test_06_capture_timebase_unchanged` | 无源时间时 3 元组/`source_time=None`（不合成） | OK |
| 07 | `test_07_memory_bounded_by_frames_and_window` | 帧数约束 size≤10；时间窗约束 trimmed=74、span≤1.0s | OK |
| 08 | `test_08_default_trim_disabled_preserves_legacy_behavior` | 默认构造旧行为不变 | OK |
| 09 | 旧 sidecar 兼容（只读 9 个） | 旧字段齐全 | OK |
| 10-12 | `StreamMetrics` 三例 | 缺值 `null`、速率/计数/年龄、`/status` 契约字段 | OK |
| 13 | `_derive_clip_fps` 非法输入 | 空/单帧/零跨度 → `None` | OK |

运行时自述（节选）：
```
[test_03] window=3.000s frames=75 fps_container=25.0000 duration=3.000s deviation=0.00%
[test_04] schema=2 fps_out=25.0 source_fps=25.0 media=1.000s src_span=0.960s
[test_05] observed_age_sec: 首=0.120 末=0.880 stale帧=15/20
[test_07b] 时间窗约束: size=26 span=1.000s trimmed=74
[旧 sidecar 兼容] 只读校验 9 个既有 v1 sidecar，旧字段齐全
[status] capture_fps=None infer_fps=None dropped=0 infer_ms=None span=0.0 age_ms=None source_fps=None
```

### 8.2 回归（项目既有环境 `C:\miniconda\envs\zhitong-gpu\python.exe`，Python 3.11.15）

```text
$ python -m unittest tests.test_timeline_metrics_contract tests.test_circular_frame_buffer \
    tests.test_replay_sidecar_contract tests.test_event_media_contract \
    tests.test_traffic_plugin_contract tests.test_traffic_event_engine \
    tests.test_evidence_chain tests.test_cloud_collaborator_event tests.test_multi_frame_validator
Ran 75 tests in 2.111s
OK                                    ← EXIT 0

$ python -m unittest discover -s tests -t tests
Ran 76 tests in 1.438s
FAILED (errors=1)                     ← 唯一错误 = test_core 缺 pytest（既有环境问题，与本任务无关）
```

### 8.3 环境差异声明（重要）

- `py -3`（Python 3.12）**未安装 `imageio_ffmpeg`** → `_get_ffmpeg_exe()` 返回 `''` → H.264 转码回退 mp4v → `test_event_media_contract.test_save_event_video_produces_h264` 在该解释器下**失败（fourcc=FMP4）**。
- 该失败**与本任务无关**：`_get_ffmpeg_exe` / `_transcode_to_h264` 是 TASK-COORD-005 引入、本次未触碰的函数；同一测试在项目既有环境（conda，含 ffmpeg 7.1）**通过**（§8.2 的 75/75 OK）。
- 本任务新增的测试在**两个解释器下都通过**（它们用 fallback mp4v 亦能校验 fps/帧数/时长一致性）。
- **未安装任何依赖**（遵守禁止项），仅报告该环境差异。

### 8.4 前端构建

本任务未改任何前端文件，**未执行** `vite build`（009B 的职责范围）。

---

## 9. 验收标准逐条核对

| # | 标准 | 结果 | 证据 |
|---|---|---|---|
| 1 | clip 回放时长与源时间窗口偏差 ≤5% | ✅ 0.00% / 0.67% / 0.67%（真实事件）；0.00%（确定性） | §5.2、§8.1 |
| 2 | sidecar 含真实可验证源帧序/源时间；`time` 与播放器一致 | ✅ 100% 帧带 `source_frame_index/source_time`；`time=index/fps` | §5.3 |
| 3 | 框随真实推理/跟踪观测更新；沿用状态显示年龄；不伪造 | ✅ 状态数 1→16、中位 run 6 帧；`observed_age_sec`+`stale` 如实标注 | §5.4 |
| 4 | `/status` 分开采集与推理指标；跳过可计数；耗时有实测 | ✅ 6 个契约字段 + 3 个附加字段全部非空且有真值 | §6 |
| 5 | 短视频按源时间推进并处理多于首帧 | ✅ OFF=0 → ON=9（同一短片） | §4 |
| 6 | 旧 sidecar 兼容读取 | ✅ 9/9 只读校验 + 007 契约 7 例全绿 | §7 |
| 7 | 指定测试/构建/隔离真实样本结果完整；既有 DB 与媒体无变化 | ✅ §8 全部命令与退出码；§10 隔离与无变化证明 | §8、§10 |

**未声称通过的部分**：§11 列出的 R1–R6 不属于本任务验收项，未实现。

---

## 10. 隔离措施与"未触碰"证明

| 措施 | 做法 |
|---|---|
| 视频/关键帧/sidecar 输出隔离 | `EVENT_VIDEO_DIR` → `%TEMP%\tc009a_*\event_videos` |
| 违规证据 JPG 隔离 | `UPLOAD_DIR` → `%TEMP%\tc009a_*\uploads` |
| **数据库** | 真实验证只跑检测器单例（不 import `database`/`routers`），**全程无任何 DB 连接** |
| 服务 | 未启动 uvicorn、未启动前端 |
| 依赖 | 未安装任何包 |
| 合成源 | 在 `%TEMP%` 生成，不入库不入项目 |
| 既有改动 | 受保护：001/003/005/006B/007 的未提交内容原样保留 |

任务结束时核验：

```
项目 api/output/event_videos/     mp4=23  _h264=7  jpg=48  sidecar=9     ← 与任务开始时完全一致
项目 api/zhitong_violations.db    225,280 B   mtime 2026/9/25 22:47:27  ← 未变
git status                        本任务仅新增：api/config.py(M)、api/circular_frame_buffer.py(M)、
                                  api/realtime_detector.py(M)、tests/test_timeline_metrics_contract.py(??)、
                                  docs/REPORT_TASK-COORD-009A_DSH.md(??)
git diff --stat                   三者合计 +715 行；未 commit / reset / clean
```

临时证据（可随时删除，均在 `%TEMP%` 内）：
- `C:\Users\ROG\AppData\Local\Temp\tc009a_evt_z689f95x\`（3 个真实事件视频 + 3 sidecar + 9 关键帧）
- `C:\Users\ROG\AppData\Local\Temp\tc009a_7a041j9z\`（pacing ON）、`…\tc009a_base_4dqzk_k6\`（pacing OFF 合成源）

---

## 11. 风险与未解决项

| # | 项 | 说明 | 影响 |
|---|---|---|---|
| R1 | **推理仍然远慢于采集** | `infer_fps≈2` vs `capture_fps=15`；中位 run 仍是 6 帧（0.4s）。根因是单帧串联 5 个 YOLO 模型（008A F7） | 框的**物理刷新上限**由推理决定；本次只是让数据**如实反映**，未提升推理速度。属额外问题（禁止项） |
| R2 | `stale` 帧占比高（54–61%） | 这是真实行为的诚实呈现，不是缺陷 | 前端需在 UI 上说明"沿用最近观测"，不得显示为实时 |
| R3 | 偏差公式的上界 | `fps=(N-1)/span` ⇒ 时长偏差 ≈ `1/(N-1)`：N=300 时 0.33%、N=25 时 4.17%、**N≤20 时 >5%** | 极短片段（<20 帧）可能超出 5%；真实事件片段为 149–151 帧。已在 `_derive_clip_fps` 中限制 0.5–240fps，越界回退默认 10 |
| R4 | 文件源现在按真实时长运行 | pacing ON 后 738s 视频需 ~738s 墙钟读完 | 复现 TASK-COORD-004 的长视频验证将显著变慢；如需快速跑批需显式 `CAPTURE_PACING_ENABLED=false`（会在 status 中如实体现） |
| R5 | 摄像头/CARLA 无源时间 | `source_time=None`、`source_frame_index=None`，`timebase='capture'` | 语义正确且已显式标记为未知；不会用合成时间冒充源时间 |
| R6 | 未做 stop 时的孤儿同步 | 007 §9.1 遗留，本任务禁止处理 | 时间盒运行产生的事件若未触发 `/events` 查询，仍可能不落库（本次运行未连库，故无孤儿产生） |
| R7 | `current_fps` 语义修正 | 属授权文件内的修正；`avg_fps`（推理率）语义未变 | 前端若把 `current_fps` 当"推理帧率"显示，现在数值更接近真实推理率；建议 009B 改用 `infer_fps`/`capture_fps` 并分开展示 |

---

## 【发现的额外问题】（只记录，未修改）

| # | 文件/模块 | 问题 | 阻塞本任务 | 建议后续 TASK |
|---|---|---|---|---|
| E1 | `api/image_recognizer.py:837-846` | 单帧串联 5 个 YOLO 模型 → `infer_fps` 实测仅 2.05（`FRAME_RATE=3` 都达不到） | 否（已量化） | 模型子集/批处理优化（需 commander 决策） |
| E2 | `api/realtime_detector.py` `_handle_event_lifecycle` | 同一事件对 buffer 取两次 clip（带 meta + 不带），且每事件一个线程、最多持有 300 帧 | 否 | 事件证据有界队列（设计稿 §4） |
| E3 | `api/routers/realtime.py:196` | `/stream` 每 50ms 无条件 JPEG 编码+推帧，无帧序号去重 | 否 | 008B E3 的同一问题，属前端/推流优化 |
| E4 | 根目录 `1/zhitong_violations.db` | 0 字节空库导致 `routers.realtime` 回放路由报 `no such table: traffic_events`（测试日志可见） | 否 | DB 路径统一（006A/008A 已连续记录） |
| E5 | `tests/test_core.py:6` | 依赖未安装的 `pytest`，全量 discover 恒 1 error | 否 | 测试运行器统一 |
| E6 | `start-all.bat` vs `api/start_api.bat` | 两个启动入口 Python 环境不同（`py -3` 无 imageio_ffmpeg，conda 有）；H.264 事件视频只在 conda 下可产出 | 否 | 统一启动脚本环境（008B 额外问题 4） |

---

## 【本次任务模型信息】

- **实际使用模型**：当前环境无法可靠读取实际模型名称。
- **任务复杂度**：**L3**
- **模型选择理由**：本任务要求同时完成三件互相牵连的事：① 在不破坏 16 项既有契约测试（缓冲 9 + 回放 sidecar 7）的前提下改造帧记录结构与缓冲语义；② 引入源时间轴并保证"缺失即显式未知"；③ 用**真实运行**而不是推断来交付验收证据（A/B 节流对照、真实事件 sidecar 的时长/状态数/观测年龄）。这需要跨 4 个模块的连贯修改 + 对时间一致性偏差的量化判断，属 L3；未为节省成本降低能力。
- **是否发生模型切换**：否。
- **切换原因**：不适用。全程未遇能力瓶颈。唯一需要判别的是环境差异（`py -3` 缺 ffmpeg 导致 H.264 用例失败），已通过"同一测试在项目既有 conda 环境 75/75 通过 + `_get_ffmpeg_exe()` 实测返回空"两条独立证据确认为环境问题而非回归。
- **未做**：未启动服务、未改前端、未改 YOLO/Tracking/判定规则/EvidenceChain/DB 结构、未安装依赖、未 commit/reset/clean、未覆盖或删除任何既有真实媒体与 DB 数据。

---

*报告结束。*
