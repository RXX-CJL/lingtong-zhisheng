# TASK-COORD-006A 报告：事件分析回放数据能力与接口契约只读设计审计

```text
任务编号：TASK-COORD-006A
执行 Agent：DSH
状态：READY_FOR_REVIEW
复杂度：L3
性质：只读设计审计。除本报告外未新增/修改任何文件。
读取过的文件：
  E:\output\1\docs\REPORT_TASK-COORD-004_TRAE.md
  E:\output\1\docs\REPORT_TASK-COORD-005_TRAE.md
  E:\output\1\docs\PROMPT_TRAE_TASK-COORD-006B.md   （用于确认 A/B 边界）
  E:\output\1\api\realtime_detector.py              （当前含 TASK-COORD-003/005 改动）
  E:\output\1\api\traffic_event_engine.py           （只读，未被 Trae 改动）
  E:\output\1\api\circular_frame_buffer.py          （当前含 TASK-COORD-005 改动）
  E:\output\1\api\evidence_chain.py
  E:\output\1\api\models.py
  E:\output\1\api\routers\realtime.py
  E:\output\1\api\behavior_engine.py, vehicle_tracker.py, image_recognizer.py(CLASS_CN_MAP)
  E:\output\1\web-admin\src\views\EventDetail.vue, EventCenter.vue
  E:\output\1\web-admin\src\api\index.js, utils\format.js, components\TypeTag.vue
  E:\output\1\tests\test_event_media_contract.py
  E:\output\1\api\zhitong_violations.db             （只读 mode=ro 实查）
  E:\output\1\api\output\event_videos\20260925\     （只读枚举 42 个文件 + 目视 1 张关键帧）
实际改动：仅新增本文件 docs/REPORT_TASK-COORD-006A_DSH.md
验证命令及结果：见 §10
证据文件或日志：见 §4、§10（均为命令输出与只读实查，未新增证据文件）
风险与阻塞：见 §9
建议的下一步：见 §8
```

**Git 起始状态（已保护，未触碰）**：分支 `main`，HEAD `4a67b5a`。既有未提交改动全部原样保留：`1/api/circular_frame_buffer.py`(M)、`1/api/realtime_detector.py`(M)、`1/api/rule_engine/plugins/traffic_plugin.py`(M，DSH TASK-COORD-003)、`1/api/zhitong_violations.db`(M)、`1/_TASK-029-M09_integration_selfcheck.json`(M)，以及 `1/api/output/`、`1/test_assets/`、`1/tests/{migrate_existing_events_f5,smoke_f4_media_pipeline,test_event_media_contract,test_traffic_plugin_contract}.py`、`docs/*` 等未跟踪项。未执行任何 git 清理/还原命令。

---

## 0. 结论速览

| 问题 | 结论 | 级别 |
|---|---|---|
| 事件视频是否保存原始帧 | ✅ 是。**逐帧目视确认无任何程序绘制的框/文字** | 代码+实物 |
| 是否保存检测框 / track_id | ❌ 否。事件路径**零调用** `_draw_detection_boxes` | 代码 |
| 是否保存逐帧车辆信息 | ❌ 否。每帧结果在内存 deque 中存在，但 `extract_event_clip` 用 `_` 丢弃，且从不持久化 | 代码 |
| trajectory 能否驱动逐帧回放 | ❌ **完全不能**。7/7 事件 trajectory 长度 = **1** | DB 实查 |
| 7 个真实事件能否做首批样本 | 🟡 **事件级面板可以**（字段齐全）；**逐帧框回放不可以**（数据不可恢复） | DB 实查 |
| 未来事件能否做逐帧回放 | ✅ 可以，需最小后端改动（落盘 sidecar），**不必重跑 YOLO** | 设计 |
| 是否必须新增回放接口 | 🟡 既有事件：不必要；未来事件：建议新增 1 个只读接口 | 设计 |
| 中文标签位置 | ✅ **前端 HTML/CSS 叠加层为主**；后端烧录仅限派生副本 | 设计 |
| 原始证据视频 | ✅ 现状已保留（`{event_id}.mp4` 与 `{event_id}_h264.mp4` 并存），回放不得覆盖 | 实物 |

**一句话**：**事件级数据齐全，逐帧数据不存在。** 006B 的视频叠加框若要对 7 个既有事件"真实"呈现，**做不到**——必须按降级方案做事件级面板，或先补 sidecar（只对未来事件生效）。

### 证据分级定义（本报告全文使用）

| 级别 | 含义 |
|---|---|
| **L-A 代码存在** | 源码可读、可定位，但未执行 |
| **L-B 接口可返回** | 存在可产出该字段的函数/路由签名 |
| **L-C 真实事件已有数据** | 7 行真实事件 DB 实查非空 |
| **L-D 逐帧数据可用** | 回放所需的**逐帧序列**真实存在且可取回 |

---

## 1. 逐项回答 006A 的 9 个问题

### Q1. 当前事件视频是否保存原始帧、检测框、track_id 和逐帧车辆信息？

| 子项 | 结论 | 证据 |
|---|---|---|
| 原始帧 | ✅ **是** | `circular_frame_buffer.py:177-187` 直接 `writer.write(frame)`，无绘制 |
| 检测框 | ❌ **否** | 事件路径（`realtime_detector.py:515-685`）**无任何** `_draw_detection_boxes` 调用 |
| track_id 叠加 | ❌ **否** | 同上；`_draw_detection_boxes` 的 label 逻辑（`realtime_detector.py:719-767`）只在实时预览/违规截图路径生效 |
| 逐帧车辆信息 | ❌ **否（但原始数据曾存在过）** | 见下 |

**逐帧数据的确切命运（三步丢失）**：

1. **采集到了**：`_buffer_frame`（`realtime_detector.py:496-513`）对每一读取帧写入
   `(time.time(), frame, {'detections': [...], 'tracked_vehicles': [...], 'scene_config': {...}})`
   —— `tracked_vehicles` 的值是 `VehicleTracker.update` 的完整车辆 dict，含 `id / class_name / bbox / center / history / direction / speed`（`vehicle_tracker.py:79-87`）。**这就是逐帧车辆信息与逐帧框的原料，且它已经存在。**
2. **提取时丢弃**：`extract_event_clip`（`circular_frame_buffer.py:118-139`）循环体是
   `for ts, frame, _ in self._buffer:` → **第 3 个元素（检测/跟踪结果）被 `_` 丢弃**，只返回 `[(timestamp, frame)]`。
3. **从不持久化**：`save_event_video` 与 `_pick_key_frame_paths` 都只接收 `(timestamp, frame)`，落盘内容只有像素；deque 为纯内存 `maxlen=300`，进程退出即永久丢失。

**目视实证（决定性）**：读 `evt_1790324873606_20_4ff131_frame_150.jpg`（960×432），画面为真实路口监控视角，**无任何检测框、ID 文字、速度文字或中文标签**；画面上的时间戳 `2022-09-09 16:14:52` 与"浙江 宁波 奉化 大成路与斗门路路口"为**源视频自带的摄像头 OSD 水印**，非本项目绘制。关键帧与事件视频同源（同一 `clip` 的帧），故事件视频同样无叠加。

> 附带结论：`realtime_detector.py:145-154` 的 `cv2.putText` 注释已自认"中文会显示问号"——后端烧录中文本来就不可行（见 Q6）。

### Q2. `TrafficEvent`、`TrafficEventRecord`、`EvidenceChain` 能提供哪些车辆字段？

**载体 A：`TrafficEvent`（`traffic_event_engine.py:72-145`，18 字段，内存对象）**

| 字段 | 生产实测值（以 evt_..._20_4ff131 为例） |
|---|---|
| `vehicle_info.track_id` | `20` |
| `vehicle_info.bbox` | `[231.67, 225.02, 306.72, 285.49]`（**仅触发时刻单帧框**，原图像素坐标） |
| `vehicle_info.class_name` | `"car"` |
| `vehicle_info.speed` | `29.618829991950886` —— **像素/秒，不是 km/h** |
| `vehicle_info.direction` | `"right"`（5/7 事件为 `"unknown"`） |
| `vehicle_info.plate_number` | `""`（**7/7 为空**） |
| `vehicle_info.plate_color` | **该键不存在** |
| `vehicle_info.confidence` | **该键不存在** |
| `trajectory` | `[{x,y,timestamp}]` —— **长度恒为 1** |
| `rule_judgment.evidence` | `{vehicle_direction, road_direction, is_wrong_way, direction_consistency, avg_speed, trajectory_length}`（wrong_way）/ `{pixel_speed, real_speed_kmh, speed_limit, excess_ratio, avg_speed, max_speed}`（speeding） |
| `key_frames` / `event_video_path` | 3 个真实相对路径 / H.264 绝对路径 |

**载体 B：`TrafficEventRecord`（`models.py:197-267`，表 `traffic_events`，20 列）**
与 `TrafficEvent.to_dict()` 一一对应，车辆信息在 `vehicle_info` / `scene_context` / `trajectory` / `rule_judgment` 四个 **JSON 文本列**里。**没有任何逐帧列**。

**载体 C：`EvidenceChain`（`evidence_chain.py:26-65`，18 字段）**
理论上比前两者多：`vehicle_type`、`plate_color`、`lane_id`、`traffic_light_state`、`stop_line_relation`、`final_status`。
**但生产不可得**：
- `traffic_events.evidence_chain` 列 **7/7 为 NULL**（DB 实查）；
- 唯一构造点是 `routers/realtime.py:939-944`，**仅当事件还在内存 `active_events` 中**才临时拼装并随响应返回；后端进程已退出，这 7 个事件只走 DB 分支（`routers/realtime.py:957`），直接返回 `record.to_dict()` → `evidence_chain: null`；
- 即使构造成功，`traffic_light_state` / `stop_line_relation` 也因**键名不匹配**（`evidence_chain.py:139-152` 读 `traffic_light`/`stop_line`，生产写 `traffic_light_state`/`stop_line_y`）恒为 `unknown`。

### Q3. 当前 `trajectory` 是否足以驱动视频回放中的车辆位置？

**❌ 完全不足以。** 三重证据：

1. **源码**：`_extract_trajectory`（`traffic_event_engine.py:289-296`）只返回**一个点**——`bbox` 中心 + `time.time()`：
   ```python
   return [{'x': cx, 'y': cy, 'timestamp': time.time()}]
   ```
   而 `_trigger_event` 只传了 `vehicle_info`（不含 `history`），所以拿不到 `VehicleTracker` 已积累的轨迹序列。
2. **DB 实查**：7/7 事件 `trajectory` 长度 = **1**（§4 逐事件列出）。
3. **前端现状**：`EventDetail.vue:503-504` 的 `trajectoryPointsArr` 要求 `trajectory.length >= 2`，否则返回 `[]` → 现有轨迹 SVG **本来就不渲染**（`v-if="trajectory.length > 1"`，第 245 行）。

**结论**：轨迹折线图与逐帧车辆位置回放**都必须判为"数据不具备"**。不要试图用单点 + 线性插值"补"出轨迹——那是伪造。

### Q4. EventDetail 现有接口和前端组件应如何扩展？

**现有可用接口（6 条，`routers/realtime.py` 全部已注册，路由前缀 `/api/realtime`）**

| 行号 | 接口 | 对本任务的价值 |
|---|---|---|
| 846 | `GET /events` | 列表 |
| 888 | `GET /events/active` | 内存活跃事件 |
| 928 | `GET /events/{id}` | **事件级全字段（回放面板主数据源）** |
| 966 | `GET /events/{id}/video` | `FileResponse`，DB 指向 H.264 副本，可播 |
| 1004 | `GET /events/{id}/frames` | 3 个真实 JPG 相对路径（`event-videos/...`） |
| 1047 | `POST /events/{id}/review` | 人工复核 |

前端封装齐备（`api/index.js:301-342`）：`getEventList / getActiveEvents / getEventDetail / getEventFrames / reviewEvent / getEventVideoUrl / getEventFrameUrl`。**回放面板不需要新接口即可拿到事件级数据。**

**EventDetail.vue 现状与缺口（实测）**

- 已有：视频区（42-63）+ 关键帧画廊（66-100）+ 证据链时间线（104-128）+ 事件信息（133-168）+ 车辆信息（172-206）+ 场景上下文（209-270）+ AI 结果（273-322）+ 规则判断（324-334）+ 人工复核（336-386）。
- **缺口 1（字段不存在）**：`190-199` 读 `vehicleInfo.plate_color` / `plate_confidence` / `confidence`，而 `vehicle_info` 里**这三个键都没有** → 恒显示 `未知` / `-` / `-`。
- **缺口 2（有值但没展示）**：`vehicleInfo.speed`（px/s）、`vehicleInfo.direction`、`rule_judgment.evidence.real_speed_kmh`（km/h）、`rule_judgment.confidence` **均未在页面上呈现** —— 而 006B 的右侧面板恰恰要显示"速度、置信度"，数据**已在响应里**。
- **缺口 3（无中文映射）**：`188-189` 直接把 `class_name` 输出为 `car`；`utils/format.js` 只有 `TYPE_MAP`（违规类型），**没有车辆类型映射**。
- **缺口 4（单位陷阱）**：`vehicle_info.speed=29.62`（px/s）若直接标 `km/h` 会把"逆行"误报成"29.6 km/h"，而真实速度在 `rule_judgment.evidence.real_speed_kmh=24.79`。**这是本任务最容易犯错的地方，必须在实现中显式区分。**
- **缺口 5（AI 面板空转）**：`ai_judgment` = `{}`（2 字符）在 JS 中为 **truthy**，`aiTraceData` 返回 `{}`，`v-if="aiTraceData"`（290）会渲染一个**空的可折叠面板**。

**扩展建议（事件级，零后端改动）**：左侧视频区加"原始证据 / 分析回放"模式切换 + 叠加层容器；右侧新增/改造车辆信息卡：事件车辆（ID、类型中文、速度 km/h、方向、车牌→未识别）、违规与置信度、状态与 AI 判定分区展示；车辆列表=当前事件车辆（单车辆事件时即 1 项），选中态用 CSS 高亮而非画框。

### Q5. 是否需要新增事件回放数据接口？推荐响应结构？

**分开回答，这是本审计最重要的判断：**

| 目标 | 是否需要新接口 | 理由 |
|---|---|---|
| **7 个既有事件**的**事件级**回放 | ❌ **不需要** | `/events/{id}` + `/frames` 已有全部所需字段（§4 实证） |
| **7 个既有事件**的**逐帧**回放 | ❌ **不可能**（加接口也没用） | 逐帧数据从未持久化，内存 deque 已随进程释放，**不可恢复** |
| **未来事件**的**逐帧**回放 | ✅ **建议新增 1 个只读接口** | 需先把逐帧结果落盘为 sidecar |

**推荐接口（未来事件方案，最小形态）**

```http
GET /api/realtime/events/{event_id}/replay
```
只读；**从 sidecar JSON 文件回读，不查库、不改库、不重跑检测**；文件不存在时返回 404 `{"success": false, "message": "该事件无逐帧回放数据"}`（对 7 个既有事件即此响应，前端据此自动降级为事件级面板——语义诚实且无需特判）。

推荐响应结构（字段均有真实来源，不引入新概念）：

```json
{
  "success": true,
  "event_id": "evt_...",
  "fps": 10,
  "frame_count": 300,
  "video": "event-videos/20260925/evt_..._h264.mp4",
  "trigger_frame_index": null,
  "track_ids": [20],
  "frames": [
    {
      "i": 0,
      "t": 0.0,
      "vehicles": [
        { "track_id": 20, "class_name": "car", "bbox": [x1, y1, x2, y2],
          "speed_px": 24.79, "direction": "right" }
      ]
    }
  ]
}
```

**必须写明的三条约束**：
1. `trigger_frame_index` 建议显式置 `null` 并**不要猜**——目前 clip 起始时间与触发帧索引均未持久化（§9 不可行项 3）。若将来要支持，需在事件生成时把 `trigger_time - clip_start_ts` 一并落盘。
2. `vehicles[].bbox` 来自 `clip[i]` 所在缓冲帧的 `tracked_vehicles`——其精度是"**该读取帧缓冲时最近一次 `process_frame` 的检测结果**"（`_buffer_frame` 读 `self.last_detection_result`），处理速率为 `Config.FRAME_RATE=3`，而缓冲按**读取帧**打点，因此**相邻若干帧会共享同一检测结果**。这是真实语义，必须在文档中说明，不得声称"严格逐帧检测"。
3. `speed_px` 是像素/秒；km/h 需按 `3.6 / pixel_per_meter` 换算，或直接沿用事件级 `rule_judgment.evidence.real_speed_kmh`（**不要**对每帧重新换算后当成新结论）。

### Q6. 中文标签应放在前端 HTML/CSS 叠加层、后端视频帧，还是两者组合？

**结论：以「前端 HTML/CSS 叠加层」为唯一主方案；后端烧录仅限**导出的派生副本**，且绝不允许作用于原始证据视频或当前 DB 指向的视频。**

理由（均以本仓库代码为依据）：

| 依据 | 内容 |
|---|---|
| OpenCV 无法渲染中文 | `realtime_detector.py:145-154` 自带注释："`cv2.FONT_HERSHEY_SIMPLEX` 中文会显示问号"。当前所有 `_draw_detection_boxes` 标签（`719-767`）全是英文/拼音（`ID:1`、`px/s`、`逆行` 会变问号） |
| 叠加层可交互 | 006B 要求"点击车辆后高亮对应车辆"——CSS 图层天然支持 hover/选中态/显隐；烧录进像素则完全不可交互 |
| 不污染证据 | 叠加层是渲染态，原始 mp4/JPG 保持只读；烧录会产生新的"已标注"文件，动摇证据链的原始性 |
| 前端已有基础 | `EventDetail.vue:41` 已有 `.video-container` 定位容器 + `<video class="event-video">`，加绝对定位覆盖层仅需 CSS |
| 坐标系可直接对齐 | `video_info.bbox` 与视频同为原图 960×432 像素域，`<video>` 用 `object-fit: contain` 时按缩放比换算即可（需处理 letterbox 偏移） |

**若确实需要烧录**（如对外材料导出）：写入**新文件**（如 `{event_id}_annotated.mp4`），中文用 `PIL`/`ffmpeg drawtext` + 中文字体（当前环境未验证存在中文字体，属未验证项），并在报告中标注该文件为**派生产物、非证据**。

### Q7. 如何保留原始证据视频，同时提供分析回放？

**现状（已实现，实物核实）**：目录内**双层文件并存**

```
20260925\evt_..._20_4ff131.mp4        3,720,815 B   ← 原始证据（FMP4，OpenCV mp4v）
20260925\evt_..._20_4ff131_h264.mp4   1,200,151 B   ← 浏览器可播副本（ffmpeg libx264）
20260925\evt_..._20_4ff131_frame_{0,150,299}.jpg      ← 3 张真实关键帧
```
- 全目录：**14 个 mp4**（7 原始 + 7 `_h264`）+ **21 张 JPG** = 35 个文件；
- DB `event_video_path` 指向 `_h264.mp4`（TASK-COORD-005 迁移结果）；
- `tests/test_event_media_contract.py:110-113` 已**断言原始 FMP4 必须保留** —— 这条契约是防线，006B 不得破坏。

**建议的三层命名契约（新增第 3 层，前两层不变）**：

| 层 | 文件 | 语义 | 谁写 | 可否被覆盖 |
|---|---|---|---|---|
| L1 证据原始 | `{event_id}.mp4` | 检测时原始录制帧，**只读** | 检测链路 | ❌ 永不 |
| L2 播放副本 | `{event_id}_h264.mp4` | 浏览器可播（可再生成） | 转码 | ✅ 可再生 |
| L3 回放数据 | `{event_id}_replay.json` | 逐帧框/车辆（可再生成） | 新增（仅未来事件） | ✅ 可再生 |

**前端呈现要求**：视频区必须**显式区分**「原始证据视频」与「分析回放」两种模式，并在回放模式显示提示语，例如"分析叠加层：显示系统判定信息，非证据原始画面"。二者共用同一个 `<video>` 源即可（当前 DB 指向 L2），**不要为回放再做一份带框视频**。

### Q8. 现有 7 个真实事件能否直接作为首批回放样本？

**分层回答（这是给 006B 的直接输入）：**

| 用途 | 可否 | 依据 |
|---|---|---|
| **事件级车辆信息面板** | ✅ **可以，7/7 全部可用** | 字段齐全，见下方逐事件表 |
| 视频播放 | ✅ 可以（H.264 副本，TASK-COORD-005 已浏览器实测） | `REPORT_TASK-COORD-005_TRAE.md` §4 |
| 关键帧展示 | ✅ 可以（3 张真实 JPG，静态挂载 200） | 同上 |
| **逐帧车辆框 / 位置回放** | ❌ **不可以** | trajectory=1 点；逐帧检测结果未持久化 |
| **逐帧速度变化** | ❌ 不可以 | 同上；仅事件级 `real_speed_kmh` |
| 轨迹折线 | ❌ 不可以 | trajectory 长度 1 < 前端要求的 2 |
| 车牌号 | ❌ 不可以 | 源头未产出（见额外问题 1） |
| AI 判定详情 | ❌ 当前不可（`ai_judgment={}`、`ai_confidence=0`、state 全 `pending_ai`） | TASK-COORD-004 §8.4 |

**7 个事件逐条实查（DB read-only）**

| event_id 后缀 | 类型 | track | state | speed(px/s) | real_speed_kmh | 方向 | 车牌 | 置信度 | 关键帧 | trajectory |
|---|---|---|---|---|---|---|---|---|---|---|
| `_2_baecaf` | speeding | 2 | pending_ai | 156.55 | **74.54** | right |  | 0.6938 | 3 | 1 点 |
| `_10_6a490c` | speeding | 10 | pending_ai | 174.64 | **62.87** | unknown |  | 0.5383 | 3 | 1 点 |
| `_16_6a49bc` | speeding | 16 | pending_ai | 182.36 | **65.65** | unknown |  | 0.5753 | 3 | 1 点 |
| `_19_fca8c3` | speeding | 19 | pending_ai | 186.56 | **67.16** | unknown |  | 0.5955 | 3 | 1 点 |
| `_20_4ff131` | **wrong_way** | 20 | pending_ai | 29.62 | 24.79（evidence.avg_speed） | right |  | **0.90** | 3 | 1 点 |
| `_39_ee9ac0` | speeding | 39 | pending_ai | 178.55 | **64.28** | unknown |  | 0.5570 | 3 | 1 点 |
| `_40_305b53` | speeding | 40 | pending_ai | 220.11 | **79.24** | unknown |  | 0.7565 | 3 | 1 点 |

- 全部 `class_name = "car"`；全部 `plate_number = ""`；全部 `camera_id = "cam_0"`；
- 全部 `evidence_chain = NULL`；`traffic_light_state = ""`；`stop_line_y = 237`；`speed_limit = 60`；`pixel_per_meter = 10`；
- **建议首批验证样本**：`evt_1790324873606_20_4ff131`（唯一 wrong_way、置信度最高 0.90、方向非 unknown），与 TASK-COORD-004/005 的验证样本一致，便于横向对比截图。

**注意**：`created_at = 2026-09-25 08:30:10`（UTC，`_sync_active_events_to_db` 用 `datetime.utcnow()`）而 `trigger_time = 2026-09-25 16:27:46`（本地时区），相差 8 小时——面板若同屏显示两个时间会造成"事件创建早于触发"的观感错误（见额外问题 6）。

### Q9. 最小实现需要修改哪些文件，哪些文件不应修改

#### 方案 A（推荐给 006B）：纯前端事件级回放 —— **零后端改动**

| 动作 | 文件 | 说明 |
|---|---|---|
| 修改（**必需**） | `web-admin/src/views/EventDetail.vue` | 视频区模式切换 + 叠加层容器（无框时显示"逐帧数据不可用"说明）+ 右侧车辆信息面板改造 + 中文字段映射 + 选中高亮 |
| 修改（**建议**） | `web-admin/src/utils/format.js` | 补车辆类型/方向中文映射、速度格式化为 km/h |
| 新增（可选） | `web-admin/src/components/EventVehiclePanel.vue` | 车辆面板独立组件（006B 明文允许"必要时新增前端组件或样式文件"） |
| 不改 | `web-admin/src/api/index.js` | 方案 A 不需要新接口 |
| 不改 | 全部后端、数据库、`models.py`、EventCenter、原始 mp4/JPG 产物、config、启动脚本 | — |

> ⚠ **授权边界提醒**：006B 的"允许修改"只列了 `EventDetail.vue` 与 `api/index.js`（+ 必要时新增组件/样式）。`utils/format.js` 是**既有共享文件**（EventCenter/其它页面也在用）。建议：**把映射常量写在 `EventDetail.vue` 内部**，暂不动 `format.js`；若确需改，请先向指挥官申请该文件所有权，避免越界与并行冲突。

#### 方案 B（未来事件逐帧回放）：需后端最小改动，**建议拆成 TASK-COORD-006C**

| 动作 | 文件 | 最小改动 |
|---|---|---|
| 修改 | `api/circular_frame_buffer.py` | 新增（不改既有签名）`extract_event_timeline(trigger_time, before, after)`，保留逐帧 `(ts, tracked_vehicles, detections)`；`extract_event_clip` 保持原样以不破坏既有契约 |
| 修改 | `api/realtime_detector.py` | `_handle_event_lifecycle` 中把 timeline 落盘为 `{event_id}_replay.json`（与 mp4 同目录），失败仅告警 |
| 修改 | `api/routers/realtime.py` | 新增 1 条只读路由 `GET /events/{event_id}/replay`（读 sidecar 文件） |
| 修改 | `web-admin/src/api/index.js` | 新增 `getEventReplayUrl/getEventReplay` |
| 新增 | `tests/` 契约测试 | sidecar 结构、404 降级、帧数与 fps 一致性 |
| **不改** | `models.py` / 数据库结构 / YOLO / Tracking / TrafficPlugin / TrafficEventEngine 判定 / EvidenceChain / CloudAI | sidecar 存**文件**，不建表不加列 |

#### 明确不应修改（006B 禁止清单的落地）

`api/traffic_event_engine.py`（判定与状态机）、`api/rule_engine/plugins/*`、YOLO/Tracking 相关、`api/models.py`、`api/zhitong_violations.db`（不得为回放改数据）、`api/output/event_videos/**`（不得覆盖/删除原始 mp4 与 21 张 JPG）、`api/evidence_chain.py`、`api/cloud_collaborator.py`、`EventCenter.vue`、`config.py`、启动脚本。

---

## 2. 字段流追踪：事件生成 → 视频保存 → 数据库存储 → EventDetail 展示

```
[1] 帧读取        realtime_detector._detection_loop:306  ret, frame = self.cap.read()
                              │
[2] 原始帧入缓存  _buffer_frame:496-513  buffer.add(t, frame,
                              │             {detections, tracked_vehicles, scene_config})   ← 逐帧数据在此"有"
                              ▼
[3] 逐帧处理      _process_frame_async → process_frame:349-494
                     YOLO:660 → tracker.update:368 → behavior_engine.analyze_all:386-403
                              │
[4] 事件触发      _process_event_engine:515-529 → engine.process_frame
                              │   → TrafficPlugin.analyze（TASK-COORD-003 已修契约）
                              → _trigger_event:246-287 建 TrafficEvent（TRIGGERED）
                              │      vehicle_info = _extract_vehicle_info:233-244（单帧 bbox/speed px/s）
                              │      trajectory   = _extract_trajectory:289-296（★ 仅 1 点）
                              ▼
[5] 事件视频      _handle_event_lifecycle:547-627
                     sleep(EVENT_CLIP_AFTER_SEC=5)
                     → transition_to_recording
                     → extract_event_clip:118-139   ★ for ts, frame, _ → 逐帧数据在此"丢"
                     → save_event_video:141-220     mp4v→ffmpeg H.264（只写像素，不画框）
                     → _pick_key_frame_paths:630-685  3 张 JPG（只 imencode，不画框）
                     → submit_to_ai → cloud_collaborator.analyze_event（当前无有效输出）
                     → apply_ai_result（当前 7/7 停在 pending_ai）
                              │
[6] 落库          routers/realtime._sync_active_events_to_db:783-843（懒同步）
                     event.to_dict() → TrafficEventRecord 20 列
                     ★ 不写 evidence_chain 列（恒 NULL）；逐帧无列可写
                              │
[7] 展示          GET /events/{id} → record.to_dict()
                     → EventDetail.vue:441-667 各 computed 解析
                     ★ 轨迹 SVG 因 length<2 不渲染；plate_color/confidence 键不存在；speed 未展示
```

**关键结论**：从 [2] 到 [5] 之间，逐帧车辆信息**只需要"不丢弃 + 落一个 JSON"**就能获得回放能力；当前断裂点精确位于 `circular_frame_buffer.py:134` 的 `_` 与 `models.py` 无逐帧列这两处。对既有 7 事件，这一步**过去没有发生，现在无法追补**。

---

## 3. 字段盘点总表（按 4 级证据标注）

| 回放所需字段 | L-A 代码存在 | L-B 接口可返回 | L-C 真实事件已有数据 | L-D 逐帧可用 | 来源 |
|---|---|---|---|---|---|
| 车辆 track_id | ✅ | ✅ | ✅ 7/7 | — | `detail.track_id` |
| 车辆类型 class_name | ✅ | ✅ | ✅ 7/7 (`car`) | — | `vehicle_info.class_name` |
| 触发时刻 bbox | ✅ | ✅ | ✅ 7/7 | ❌ | `vehicle_info.bbox` |
| 速度（px/s） | ✅ | ✅ | ✅ 7/7 | ❌ | `vehicle_info.speed` |
| 速度（km/h） | ✅ | ✅ | ✅ 7/7 | ❌ | `rule_judgment.evidence.real_speed_kmh` |
| 方向 direction | ✅ | ✅ | ✅ 7/7（5 个 unknown） | ❌ | `vehicle_info.direction` |
| 违规类型 | ✅ | ✅ | ✅ 7/7 | — | `event_type` + `TYPE_MAP` |
| 规则置信度 | ✅ | ✅ | ✅ 7/7 | — | `rule_judgment.confidence` |
| 事件状态 | ✅ | ✅ | ✅ 7/7 | — | `state` + `stateLabelMap` |
| 摄像头 / 时间 | ✅ | ✅ | ✅ 7/7 | — | `camera_id` / `trigger_time` |
| 关键帧 3 张 | ✅ | ✅ | ✅ 7/7 | — | `key_frames` |
| 可播视频 | ✅ | ✅ | ✅ 7/7 (H.264) | — | `event_video_path` |
| **逐帧 bbox** | ✅（曾存在于 buffer） | ❌ | ❌ | ❌ **丢失** | 需方案 B |
| **逐帧车辆状态** | ✅（同上） | ❌ | ❌ | ❌ **丢失** | 需方案 B |
| **逐帧速度** | 🟡（buffer 有 px/s） | ❌ | ❌ | ❌ | 需方案 B |
| **完整 trajectory** | 🟡（`history` 在 buffer 内） | ❌ | ❌（恒 1 点） | ❌ | 需方案 B |
| 车牌号 | ❌ 源头不产出 | ❌ | ❌ 7/7 空 | ❌ | 见额外问题 1 |
| plate_color | ❌ 键不存在 | ❌ | ❌ | ❌ | 见额外问题 2 |
| AI 判定 / 说明 | ✅ | ✅ | ❌（`{}` / `""`） | ❌ | 见额外问题 3 |
| evidence_chain | ✅ | 🟡 仅内存事件 | ❌ 列 NULL | ❌ | 见额外问题 4 |
| 触发帧索引 | ❌ 未持久化 | ❌ | ❌ | ❌ | 不可行项 3 |

---

## 4. 建议的前端显示字段与中文映射

### 4.1 车辆信息面板（006B 右侧栏）建议字段

| 面板项 | 数据来源（真实） | 缺失时显示 | 备注 |
|---|---|---|---|
| 车辆 ID | `detail.track_id` | `-` | 已有 |
| 车辆类型 | `vehicle_info.class_name` → 中文映射 | `未知` | 当前直接显示英文 `car` |
| 速度 | **`rule_judgment?.evidence?.real_speed_kmh`** | 回退 `vehicle_info.speed` 并标注 `px/s`；两者皆无 → `-` | ⚠ **绝对不要把 `vehicle_info.speed` 标成 km/h** |
| 方向 | `vehicle_info.direction` → 中文 | `未知` | |
| 车牌 | `vehicle_info.plate_number` | `未识别` | 7/7 为空 |
| 车牌颜色 | `vehicle_info.plate_color` | `未采集` | 键不存在 |
| 违规类型 | `detail.event_type` → `TYPE_MAP` | 原值 | 已有 |
| 置信度 | `rule_judgment.confidence` → `xx.x%` | `-` | 建议 `formatConfidence` 兼容 0–1 与 0–100 |
| AI 置信度 | `detail.ai_confidence` | `待 AI 分析` | 7/7 为 0，勿显示 `0.00%` 误导 |
| 事件状态 | `detail.state` → `stateLabelMap` | `-` | 已有 8 态中文 |
| 停止线关系 | `evidence_chain?.stop_line_relation` | `未采集` | 生产恒 unknown，建议不显示 |
| 信号灯状态 | `scene_context.traffic_light_state` | `未检测到` | 7/7 为 `""` |

### 4.2 中文映射建议（放进 `EventDetail.vue` 内部常量）

```js
// 车辆类型：与后端 image_recognizer.py:35 CLASS_CN_MAP 对齐
const CLASS_CN = {
  car: '轿车', motorcycle: '摩托车', truck: '卡车', bus: '公交车',
  bicycle: '自行车', person: '行人', unknown: '未知'
}

// 运动方向（VehicleTracker 取值：right/left/up/down/unknown）
const DIRECTION_CN = {
  right: '向右', left: '向左', up: '向上', down: '向下', unknown: '未知'
}

// 违规类型：复用 utils/format.js TYPE_MAP，另补以下别名/扩展
const EXTRA_TYPE_CN = {
  illegal_parking: '违规停车',      // 已存在
  illegal_park: '违规停车',         // 前端筛选用的旧值，别名兜底
  lane_departure: '压线行驶',
  running_yellow: '抢黄灯',
  illegal_turn: '违规掉头',
  pedestrian_crossing: '未礼让行人',
  street_stall: '占道经营',
  illegal_occupancy: '违规占用',
  crowd_gathering: '人员聚集',
  abnormal_assembly: '异常聚集'
}
```

> `utils/format.js:1-8` 现有 `TYPE_MAP` 缺 `running_yellow / illegal_turn / street_stall / crowd_gathering` 等（`behavior_engine.py:26-35` 与三个规则插件可产出），`getTypeName` 会回退成英文原值——若 006B 要求"中文字段正常显示"，需一并覆盖。

### 4.3 分析回放区的标注策略（基于真实数据能力）

| 元素 | 事件级模式（对 7 既有事件可用） | 逐帧模式（仅未来事件） |
|---|---|---|
| 车辆框 | ❌ **不画**（无逐帧框）。在视频区显式提示："逐帧检测框数据未采集，无法叠加" | ✅ 按 `frames[i].vehicles[].bbox` + `video.currentTime` 叠加 |
| 车辆 ID/违规文字 | ✅ 作为**事件级徽标**放在视频区固定角落（不随画面移动），如"ID 20 · 逆行" | ✅ 跟随框 |
| 选中高亮 | ✅ 事件级选中态（面板卡片高亮 + 角落徽标高亮） | ✅ 对应框描边高亮 |
| 速度 | ✅ 面板显示事件级 `real_speed_kmh` | ✅ 面板按当前帧更新；**不得**在无数据帧显示上一帧数值而不说明 |

---

## 5. 最小数据契约（建议写入 006B 实现说明）

```text
契约 1（既有，不可破坏）
  每个事件目录下：{event_id}.mp4（原始证据，只读）
                  {event_id}_h264.mp4（可播副本，DB event_video_path 指向它）
                  {event_id}_frame_*.jpg（真实关键帧，key_frames 为 event-videos/ 相对路径）
  由 tests/test_event_media_contract.py 的 test_01..test_06 守护。

契约 2（本报告新增建议，仅未来事件）
  同一目录追加：{event_id}_replay.json
  结构 = { fps, frame_count, video, trigger_frame_index:null, track_ids[], frames[{i, t, vehicles[{track_id, class_name, bbox, speed_px, direction}]}] }
  由 GET /api/realtime/events/{id}/replay 只读回传；文件缺失 → 404，前端降级为事件级面板。

契约 3（字段语义，防误用——必须在代码注释与报告中固定）
  vehicle_info.speed            = 像素/秒（不是 km/h）
  rule_judgment.evidence.real_speed_kmh = km/h（事件级唯一权威速度）
  vehicle_info.bbox             = 触发时刻单帧框（不是逐帧框）
  trajectory                    = 当前恒 1 个点，禁止用于插值/连线
  plate_number                  = 当前恒空（源头 VehicleTracker 不产该字段）
  时间戳单位：state_history[].timestamp = epoch 秒(float)；trigger_time/created_at = 字符串
```

---

## 6. 明确不可行部分（不得在 006B 中伪装实现）

| # | 不可行项 | 原因（证据） | 006B 应如何处理 |
|---|---|---|---|
| 1 | 7 个既有事件的**逐帧车辆框** | 逐帧结果未持久化；`extract_event_clip:134` 丢弃；deque 为内存对象且进程已退出 | 视频区显示"逐帧数据未采集"提示，只做事件级面板 |
| 2 | 7 个既有事件的**逐帧速度曲线** | 同上 | 面板只显示事件级 `real_speed_kmh`，并标注"事件级" |
| 3 | **触发帧精确定位** | clip 起始时间与触发帧索引从未落盘 | `trigger_frame_index: null`，不猜不插值 |
| 4 | 7 个既有事件的**完整轨迹** | trajectory 恒 1 点（DB 实查 7/7） | 不渲染轨迹图；面板只显示单点坐标或直接隐藏该卡 |
| 5 | **车牌号** | `VehicleTracker` 车辆 dict 无 `plate_number` 键（全文件 grep 0 命中） | 显示"未识别"，不得显示任何号码 |
| 6 | **逐帧车辆框与真实画面严格对齐**（未来事件） | 缓冲按读取帧打点、检测结果按 `FRAME_RATE=3` 更新，相邻帧共用同一结果 | 在 UI 与文档中说明"分析标注按检测节拍更新" |
| 7 | 后端烧录**中文**标注 | OpenCV `putText` 不支持中文（代码自带注释 `realtime_detector.py:145-154`）；环境未验证中文字体 | 中文一律走前端叠加层 |

> 唯一"能造出逐帧框"的路径是**对这 7 个 mp4 重跑 YOLO**（属于"重新分析"，产出**新**检测结果，不是原始证据）。006A 明确**不建议**在 006B 做：它耗时、且语义上必须标注为"重新分析结果"，否则等同伪造原始判定。若指挥官确实要，应单列 TASK，并要求 UI 显式标注"重新分析（非原始检测结果）"。

---

## 7. 给 Trae 的实现边界与验收标准（006B 落地建议）

**实现边界（在 006B 授权范围内）**

1. 只做**事件级**回放：`/events/{id}` + `/frames` 已有数据，`EventDetail.vue` 内完成，**零后端改动**；
2. 视频区新增"原始证据 / 分析回放"模式切换；**分析回放模式下若判定无逐帧数据，必须显式提示，不得画任何框**；
3. 右侧车辆信息面板按 §4.1 字段表实现，速度以 `real_speed_kmh` 为准并带单位 `km/h`；
4. 中文映射放在 `EventDetail.vue` 内部常量（避免改 `utils/format.js` 越界）；
5. 中文标签只用 HTML/CSS 叠加层，**不烧录**；
6. 不新增/改写 mp4、不删除 21 张 JPG、不改 DB、不改 `event_video_path` 与 `key_frames`；
7. 若决定做未来事件 sidecar（方案 B），**先回报并单列 TASK**，不并入 006B。

**006B 验收标准（建议指挥官采用）**

| # | 标准 | 判定方式 |
|---|---|---|
| 1 | EventDetail 存在视频区 + 右侧车辆信息面板，布局符合 006B 示意 | 浏览器截图 |
| 2 | 面板显示：车辆 ID、类型（中文）、速度（km/h）、车牌（未识别）、违规（中文）、置信度、状态 | 以 `evt_1790324873606_20_4ff131` 为例截图 |
| 3 | 速度值 = `real_speed_kmh`（逆行事件应为 ~24.8 km/h），**不是** `vehicle_info.speed`（29.62） | 对照 DB 值断言 |
| 4 | 视频区明确区分"原始证据 / 分析回放"，且回放模式**无伪造框**，有"逐帧数据未采集"说明 | 截图 + 代码审查 |
| 5 | 原始证据与播放副本文件均存在且未被修改（尺寸不变） | re-run `test_event_media_contract.py` 6 用例应仍全绿 |
| 6 | 面板显示"未识别/未采集"而非空白或虚构值（车牌、车牌颜色、AI 置信度） | 截图 |
| 7 | 前端构建通过 | `npm run build` EXIT=0 |
| 8 | 报告明确区分：逐帧真实数据（无）/ 事件级数据（全部）/ 仍未具备（轨迹、车牌、AI 判定） | 报告审查 |

---

## 8. 建议的下一步

1. **[P1] 交 Trae 执行 006B**：按 §7 边界做**事件级**回放（方案 A，零后端改动）。首要正确性风险是**速度单位**（§4.1）与**不得画假框**（§6 不可行项 1）。
2. **[P1] 若要逐帧回放**：单列 **TASK-COORD-006C（方案 B）**，最小改动见 §Q9 方案 B；预期只对**未来**事件生效，并在验收时明确"既有 7 事件仍为事件级"。
3. **[P2] 回放数据源修复（独立 TASK）**：把 `_extract_trajectory` 改为透传 `VehicleTracker.history`（`traffic_event_engine.py:289-296` + `_extract_vehicle_info:233-244`），使 trajectory 真正具备"多帧轨迹"——这是**唯一**能让轨迹图与逐帧位置在未来事件上真实可用的根本改动。
4. **[P2] 车牌链路**：`VehicleTracker` 不产 `plate_number`，导致事件 `plate_number` 恒空，而 `plate_number` 是 006B 面板要求字段之一（见额外问题 1）。
5. **[P3] 既有技术债**：`evidence_chain` 恒 NULL、AI 全停 `pending_ai`、时间戳秒/毫秒不一致、`vehicle_info` 缺 `plate_color/confidence`。

---

## 9. 风险与阻塞

| 级别 | 项 | 说明 |
|---|---|---|
| 🟡 中 | 006B 的 UI 示意与真实数据能力不匹配 | 示意要求"视频上简洁框线和状态颜色"，但 7 个既有事件**无逐帧框可画**。若照示意硬做，必然产生伪造框 → 必须在 006B 中显式降级（本报告 §6 已给出话术与处理方式） |
| 🟡 中 | 速度单位陷阱 | `vehicle_info.speed`（px/s）与 `real_speed_kmh` 同名近似、量级悬殊（174.64 vs 62.87）。误用会产生"174 km/h"这类虚假结论 |
| 🟡 中 | 授权边界 | 006B 允许清单未含 `utils/format.js`，而中文映射的"自然位置"在那里；建议内联到 `EventDetail.vue`（§Q9 提醒） |
| 🟢 低 | 叠加层坐标换算 | `<video>` 默认按比例缩放 + letterbox，需按 `videoWidth/videoHeight` 与实际渲染尺寸换算，否则框位偏移（仅方案 B 需要考虑） |
| 🟢 低 | 中文渲染字体 | 前端 HTML 中文无风险；若将来做烧录需验证中文字体存在（当前环境**未验证**） |
| 🟢 低 | 7 事件样本代表性 | 7/7 为 speeding(6)+wrong_way(1)，`class_name` 全为 car，无 red_light/no_helmet 样本；面板对其它类型的中文映射无法用真实数据验证 |

**无阻塞本审计报告的项。** 报告结论均来自只读实查与代码定位。

---

## 10. 执行的命令与结果

环境：`py -3` = Python 3.12（`C:\Users\ROG\AppData\Local\Programs\Python\Python312`），`PYTHONDONTWRITEBYTECODE=1`，全部只读。

```text
[A] Git 安全核查
    $ git status --porcelain            → 5 个 M + 27 个 ??（含 Trae 006A/005 产物），与任务开始时一致
    $ git branch --show-current         → main
    $ git log -n 3 --oneline            → 4a67b5a / 1eb430d / 5bac816
    $ git diff --stat                   → circular_frame_buffer.py +90、realtime_detector.py +54、
                                          traffic_plugin.py +10、zhitong_violations.db(Bin)、
                                          _TASK-029-M09_integration_selfcheck.json
    结论：目标文件（事件链、前端、models）中 realtime_detector/circular_frame_buffer 已含 Trae 改动，
          本次审计按"当前代码"为准，未做任何改动。

[B] 数据库只读实查（sqlite3 connect(file:...?mode=ro, uri=True)）
    traffic_events rows = 7
    → 逐行 dump：vehicle_info / scene_context / trajectory / key_frames /
                 rule_judgment / state_history / ai_judgment / evidence_chain /
                 ai_confidence / ai_explanation / event_video_path
    关键读数：trajectory 长度 7/7 = 1；evidence_chain 7/7 = NULL；
              ai_judgment 7/7 = "{}"；ai_confidence 7/7 = 0.0；
              plate_number 7/7 = ""；state 7/7 = pending_ai

[C] 产物只读枚举
    mp4 = 14（7 原始 + 7 _h264）；jpg = 21；event_videos 下共 35 文件
    原始/副本尺寸与 REPORT_TASK-COORD-005 §3 表格逐行一致（未被改动）

[D] 关键帧目视（read_image，只读）
    evt_1790324873606_20_4ff131_frame_150.jpg  960x432
    → 真实路口监控画面；无任何检测框 / ID / 速度 / 中文标签
    → 画面内时间戳与"浙江 宁波 奉化 大成路与斗门路路口"为源视频 OSD 水印
    （注：modlens 视觉桥不可用：No vision provider is set up on this machine）

[E] 代码定位（grep/select-string）
    _draw_detection_boxes 出现位置：719(def) / 795 / 857 / 913 / 1080
      → 均属实时预览、违规截图、强制咨询、外部帧检测；事件路径 515-685 内 0 次。
    vehicle_tracker.py 中 'plate' → 0 命中（车辆 dict 不含 plate 字段）
    api/routers/realtime.py 中 'bbox' → 仅 tracking/plugins 段（421-476），无逐帧事件数据接口
    事件路由 = 6 条（846/888/928/966/1004/1047），无 replay 路由

[F] 前端结构核对（grep EventDetail.vue）
    218 处结构命中：视频区(42-63)、关键帧画廊(66-100)、时间线(104-128)、
    车辆信息(172-206)、场景(209-270)、AI(273-322)、规则(324-334)、复核(336-386)
    computed：videoUrl(448) keyFramePreviewList(454) vehicleInfo(459) trajectory(487)
              ruleJudgment(533) aiJudgment(545) aiTraceData(556) evidenceTimeline(596)
    缺口实证：190-199 读不存在的 plate_color/plate_confidence/confidence；
              503-504 要求 trajectory>=2 才渲染（当前恒 1 → 永不渲染）
    utils/format.js：formatDate(31) 用 new Date(数值) → epoch 秒被当毫秒（1970 问题根因）
```

---

## 【发现的额外问题】

> 均为本任务范围外，**只记录，未修改**。

| # | 文件或模块 | 问题描述 | 是否阻塞本任务 | 建议后续 TASK |
|---|---|---|---|---|
| 1 | `api/vehicle_tracker.py`（全文）+ `api/traffic_event_engine.py:233-244` | `VehicleTracker` 产出的车辆 dict **不含 `plate_number` 键**（全文件 grep 0 命中），而 `_extract_vehicle_info` 用 `v_info.get('plate_number','')` 取值 → 事件 `plate_number` **恒为空字符串**，与车牌识别是否成功无关。这是 006B 面板"车牌"字段恒显示"未识别"的根因 | 否 | 独立 TASK：车牌结果回填到 tracker 车辆 dict 或事件层 |
| 2 | `api/realtime_detector.py:876-886`（frontend `vehicleInfo` 消费侧） | `vehicle_info` 缺 `plate_color` / `plate_confidence` / `confidence` 三键，但 `EventDetail.vue:190-199` 已在读取 → 车辆信息卡长期显示"未知/-/-" | 否 | 随问题 1 一并处理 |
| 3 | `api/cloud_collaborator.py` + `TrafficEventEngine.apply_ai_result` | 7 事件 `ai_judgment={}`、`ai_confidence=0`、state 全停 `pending_ai`（TASK-COORD-004 §8.4 已记）；导致 EventDetail 的 AI 面板与 `aiTraceData` 出现**空的可折叠面板**（`{}` 在 JS 中为 truthy，`v-if` 误判） | 否 | 独立 TASK：AI 链路 + 前端空对象判定 |
| 4 | `api/routers/realtime.py:808-825` | `_sync_active_events_to_db` 的 `common_fields` 无 `evidence_chain` 列 → 该列永为 NULL；`GET /events/{id}` 对历史事件拿不到证据链 | 否（但影响回放面板可展示字段） | 独立 TASK：证据链持久化 |
| 5 | `api/evidence_chain.py:139-152` | `stop_line_relation` / `traffic_light_state` 读 `scene_context['stop_line']`/`['traffic_light']`，生产写入键为 `stop_line_y`/`traffic_light_state` → 恒 `unknown` | 否 | 独立 TASK：键名对齐 |
| 6 | `api/routers/realtime.py:824/832` + `web-admin/src/utils/format.js:31` | `created_at` 用 `datetime.utcnow()`（UTC）而 `trigger_time` 由本地 epoch 转换 → 同屏相差 8 小时（实测 `08:30:10` vs `16:27:46`）；且 `state_history[].timestamp` 为 **epoch 秒**，`formatDate` 按毫秒解析 → 显示 1970-01-22 | 否（但 006B 面板若显示时间需注意） | 独立 TASK：时间戳单位与 UTC/本地统一 |
| 7 | `api/circular_frame_buffer.py:134` | `extract_event_clip` 丢弃每帧检测结果（`for ts, frame, _`），逐帧回放能力因此在源头被丢弃且不可恢复 | **是**（阻塞"逐帧回放"目标，不阻塞事件级面板） | TASK-COORD-006C（方案 B） |
| 8 | `api/traffic_event_engine.py:289-296` | `_extract_trajectory` 只产出 1 点，未透传 `VehicleTracker.history`（该 history 本已积累 ≥5 点，`wrong_way` 事件 evidence 里 `trajectory_length: 5` 可证） | 否 | 独立 TASK：轨迹透传（方案 B 的前置） |
| 9 | `api/realtime_detector.py:306-309` | 视频文件源全速读取，短样本（<1min）在处理链建立轨迹前读完（TASK-COORD-004 §8.1） | 否 | 独立 TASK：视频源节流 |
| 10 | `tests/test_core.py:6` | 依赖未安装的 `pytest`，全量 discover 恒 1 个收集错误 | 否 | 独立 TASK：测试运行器统一 |
| 11 | `docs/REPORT_TASK-COORD-006A_DSH.md`（本报告） | 报告必须落盘但不在 006A "允许修改"清单（清单仅要求新增本文件，故合规） | 否 | 无需处理 |

---

## 【本次任务模型信息】

- **实际使用模型**：当前环境无法可靠读取实际模型名称。
- **任务复杂度**：**L3**
- **模型选择理由**：本任务需跨"检测器 → 循环缓存 → 事件引擎 → 3 个数据载体 → 6 条 API → EventDetail 组件"核对字段级可达性，并对**既有 7 个真实事件**做数据库实查以区分"代码存在 / 接口可返回 / 真实事件已有数据 / 逐帧数据可用"四级证据；同时必须判断哪些 UI 需求在当前数据下**根本不可实现**并给出不伪造的降级方案。属多文件交叉分析 + 数据契约设计，不含大规模实现，L3 适配。未为节省成本降低能力（含一次关键帧目视核验与一次只读数据库全字段 dump）。
- **是否发生模型切换**：否。
- **切换原因**：不适用。全程未遇到能力瓶颈；唯一的环境限制是 `modlens` 视觉桥不可用（`No vision provider is set up on this machine`），已改用 harness 内置图像读取完成目视核验，未因此降低结论强度。

---

*报告结束。本任务仅新增本文件；未修改任何业务代码、数据库、前端、接口、配置或启动脚本；未生成或删除任何视频、关键帧或数据库记录。*
