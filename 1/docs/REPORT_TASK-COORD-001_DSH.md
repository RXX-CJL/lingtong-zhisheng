# TASK-COORD-001 后端核心事件链只读审计报告

```text
任务编号：TASK-COORD-001
执行 Agent：DSH
状态：READY_FOR_REVIEW
读取过的基线/文件：
  E:\output\1\PROJECT_BASELINE.md
  E:\output\1\PROJECT_AUDIT_AND_BASELINE_REPORT.md
  E:\output\1\docs\AI_COORDINATION_PROTOCOL.md
  E:\output\1\api\realtime_detector.py
  E:\output\1\api\traffic_event_engine.py
  E:\output\1\api\circular_frame_buffer.py
  E:\output\1\api\evidence_chain.py
  E:\output\1\api\cloud_collaborator.py
  E:\output\1\api\routers\realtime.py
  E:\output\1\api\database.py, models.py, schemas.py, app.py, config.py
  E:\output\1\api\rule_engine\base_plugin.py, plugin_loader.py, plugins\traffic_plugin.py
  E:\output\1\api\behavior_engine.py, vehicle_tracker.py, migrate_db.py
  E:\output\1\tests\test_task029_integration.py, test_traffic_event_engine.py,
                   test_cloud_collaborator_event.py, test_evidence_chain.py,
                   test_circular_frame_buffer.py
实际改动：仅新增本文件（E:\output\1\docs\REPORT_TASK-COORD-001_DSH.md）。未修改任何业务代码、
          未改数据库、未改配置/启动脚本、未删除或重命名文件。
验证命令及结果：见 §9、§10
证据文件或日志：见 §9、§10（全部为命令输出，未新增证据文件）
风险与阻塞：见 §12
建议的下一步：见 §11 与 §13
```

---

## 0. 结论摘要（先看这里）

**后端事件链在"规则插件 → 事件引擎"这一环存在真实、可复现的调用契约不匹配，导致生产路径下事件触发数恒为 0。** 链路的其余环节（状态机、视频落盘、DB 同步、FastAPI 路由、静态资源）经只读探针验证**功能本身可用**，但因为上游永远不产出事件，从未被真实触发过。

| 环节 | 代码证据 | 运行/测试证据 | 判定 |
|---|---|---|---|
| 视频/摄像头 → YOLO | ✅ L660-671 | 未运行 | 未验证 |
| YOLO → tracking | ✅ L368 | 未运行 | 未验证 |
| tracking → 行为规则 | ✅ L386-403 | **探针实证可用** | 可用 |
| 行为规则 → TrafficEventEngine | ✅ 但**参数错位** | **探针实证触发数=0** | 🔴 **断链** |
| TrafficEventEngine 状态机 | ✅ | ✅ 单测 15 项通过 | 可用 |
| EventChain（EvidenceChain） | ✅ | ✅ 单测 8 项通过 | 可用（但未接入落库） |
| event_videos/*.mp4 | ✅ | ✅ 探针实证可写出 mp4 | 可用（生产目录为空） |
| traffic_events 表 | ✅ | ✅ 表存在（20 列/8 索引），**当前 0 行** | 建表成功、从未写入 |
| FastAPI 查询/资源接口 | ✅ 6 条路由已注册 | ✅ 路由注册检查通过 | 可用 |

---

## 1. 实际入口文件是什么？

**后端进程入口：`E:\output\1\api\app.py`**

- `app = FastAPI(..., lifespan=lifespan)` — `app.py:77-82`
- `lifespan()` — `app.py:55-74`，启动时执行 `init_db()`（`database.py:28`）+ `init_default_user()`
- 路由注册 — `app.py:122-131`，其中 `app.include_router(realtime.router)` 为事件链入口
- 静态挂载 — `app.py:137-146`：`/uploads` → `api/uploads`；`/event-videos` → `Config.EVENT_VIDEO_DIR`
- 启动方式（唯一被脚本使用的方式）：`api/start_api.bat` / `start-all.bat` → 工作目录 `E:\output\1\api`，`py -3 -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload`

**事件链的运行时入口（模块级单例）：`E:\output\1\api\realtime_detector.py:1098`**

```python
realtime_detector = RealtimeViolationDetector()
```

该单例在 `app.py` 导入路由时**立即实例化**（`routers/realtime.py:23` → `from realtime_detector import realtime_detector`），构造过程包含模型加载（`_init_all_models_safe`，L122-127）与事件引擎初始化（L72、L90-113）。

> 注意：`E:\output\1\api\main.py` 是**旧入口**（自带 User/ViolationRecord/SystemLog 模型与 JWT），`app.py` 未引用它，事件链与之无关。它不在本任务范围，但被 `PROJECT_AUDIT_AND_BASELINE_REPORT.md` 记为 P1-2 遗留项。

---

## 2. 关键函数和类是什么？

### 2.1 检测侧（`api/realtime_detector.py`，类 `RealtimeViolationDetector`）

| 函数 | 行号 | 作用 |
|---|---|---|
| `RealtimeViolationDetector.__init__` | 40-74 | 组装 tracker / behavior_engine / frame_buffer / event_engine |
| `_init_frame_buffer` | 76-88 | 按 `Config.FRAME_BUFFER_DURATION/FPS` 建 `CircularFrameBuffer`，失败降级为 `None` |
| `_init_event_engine` | 90-113 | 用 `rule_engine.plugin_loader.get_default_loader()` 取启用插件，构造 `TrafficEventEngine` |
| `start_camera` | 162-204 | 打开摄像头（DSHOW 优先）或 `cv2.VideoCapture(video_path)` |
| `set_source` | 206-248 | camera / video / carla 数据源切换 |
| `start_detection` | 250-271 | 置 `running=True`，清空 `frame_buffer` 与 `active_events`，起 `_detection_loop` 线程 |
| `_detection_loop` | 273-326 | 读帧 → `_buffer_frame(frame)` → 按 `Config.FRAME_RATE` 节流调用 `_process_frame_async` |
| `_process_frame_async` | 328-347 | 非阻塞 `process_lock` + 工作线程调用 `process_frame` |
| `process_frame` | 349-494 | 主流程：YOLO → tracker → behavior → 多帧确认 → 云端协作 → `_save_violation_evidence` → `_process_event_engine` |
| `_buffer_frame` | 496-513 | 把 `(time.time(), frame, {detections, tracked_vehicles, scene_config})` 写入循环缓存 |
| `_process_event_engine` | 515-545 | 调用引擎并异步启动事件生命周期线程 ← **断链点** |
| `_handle_event_lifecycle` | 547-627 | 事件视频 + 云端 AI + 状态流转 |
| `_pick_key_frame_paths` | 629-643 | 返回 `frame_{idx}` **占位字符串** |
| `get_status` / `_get_event_engine_status` | 909-982 | 暴露 `frame_buffer_size`、`active_events`、`event_engine` 统计 |
| `detect_external_frame` | 1012-1060 | 前端 getUserMedia 帧路径，同样进入 `process_frame` |

### 2.2 事件引擎（`api/traffic_event_engine.py`）

| 类/函数 | 行号 | 作用 |
|---|---|---|
| `EventState(Enum)` | 40-49 | 8 状态 |
| `VALID_TRANSITIONS` | 53-62 | 合法转换表 |
| `TERMINAL_STATES` | 65 | `{CONFIRMED, REJECTED}` |
| `TrafficEvent`（dataclass） | 72-145 | 事件载体，18 字段 |
| `TrafficEventEngine.__init__` | 162-181 | `rule_plugins` / `frame_buffer` / `cooldown_sec` / `_events` / `_cooldowns` |
| `process_frame` | 183-231 | 遍历插件 → 冷却检查 → `_trigger_event` |
| `_extract_vehicle_info` | 233-244 | 从 `tracked_vehicles[track_id]` 取 bbox/class/speed/direction/plate |
| `_trigger_event` | 246-287 | 建 `TrafficEvent`，state=`TRIGGERED`，写冷却 |
| `_extract_trajectory` | 289-296 | **只产出 1 个轨迹点** |
| `_update_event_state` | 298-329 | 校验转换合法性，非法抛 `ValueError`，记录 `state_history` |
| `_check_cooldown` | 331-345 | `(track_id, event_type)` 60s 冷却 |
| `submit_to_ai` | 362-409 | `RECORDING → PENDING_AI`，返回提交 dict（不真正调云端） |
| `apply_ai_result` | 411-460 | `PENDING_AI → AI_REVIEWED → CONFIRMED/REJECTED/MANUAL_REVIEW` |
| `manual_review` | 462-482 | `MANUAL_REVIEW → CONFIRMED/REJECTED` |
| `transition_to_recording` | 484-490 | `TRIGGERED → RECORDING` |
| `cleanup_old_events` | 492-508 | 超时清理（**生产路径从未调用**） |

### 2.3 其他

- `CircularFrameBuffer`（`circular_frame_buffer.py:26`）：`add` / `extract_event_clip` / `save_event_video` / `generate_event_video_path` / `get_latest` / `clear`
- `EvidenceChain`（`evidence_chain.py:26`）：dataclass + `to_dict` / `to_json` / `summary` / `from_traffic_event` / `from_dict`
- `CloudCollaborator.analyze_event`（`cloud_collaborator.py:588-688`）→ `_analyze_event_with_doubao(735)` / `_analyze_event_with_claude(765)` / `_analyze_event_with_deepseek(793)` / `_build_event_final_judgment` / `build_ai_trace(368)`
- `TrafficEventRecord`（`models.py:197-267`）→ 表 `traffic_events`
- `TrafficPlugin`（`rule_engine/plugins/traffic_plugin.py:64`）：`analyze(107)` / `_extract_vehicles(150)` / `_to_event(178)`
- `get_default_loader`（`rule_engine/plugin_loader.py:249-269`）：按 `Config.PLUGINS_ENABLED` 启用 `traffic,urban_management,public_security`

---

## 3. TrafficEventEngine 在什么条件下触发事件？

### 3.1 代码规定的条件（`traffic_event_engine.py:183-231`）

```python
def process_frame(self, frame, detections, tracked_vehicles, scene_context):
    if not self.rule_plugins:
        return []                                   # 条件0：无插件 → 不触发
    for plugin in self.rule_plugins:
        if hasattr(plugin, 'is_enabled') and not plugin.is_enabled: continue
        violations = plugin.analyze(frame, scene_context, tracked_vehicles)   # ← 唯一产出源
    for v in all_violations:
        track_id = getattr(v, 'vehicle_id', -1)
        event_type = getattr(v, 'behavior_type', 'unknown')
        if track_id < 0 or event_type == 'unknown': continue
        if not self._check_cooldown(track_id, event_type): continue
        event = self._trigger_event(...)            # TRIGGERED
```

即触发条件为四项全部成立：

1. `rule_plugins` 非空（`__init__:172`，由 `_init_event_engine` 注入）；
2. 插件 `analyze(frame, scene_context, tracked_vehicles)` 返回非空 `ViolationEvent` 列表；
3. 事件对象满足 `vehicle_id >= 0` 且 `behavior_type != 'unknown'`；
4. `(track_id, event_type)` 不在 60s 冷却窗口内（`cooldown_sec=60`，`realtime_detector.py:108`）。

### 3.2 真实插件侧的条件（`traffic_plugin.py:107-176`）

`TrafficPlugin.analyze` 的取数顺序是**唯一关键**：

```python
vehicles = self._extract_vehicles(scene_context, tracker)
# 1. scene_context["vehicles"]        list[dict]
# 2. scene_context["tracked_vehicles"] dict[id -> dict]
# 3. tracker.get_all_vehicles()        （tracker 必须是有该方法的对象）
if not vehicles: return []              # ← 到不了 BehaviorEngine
```

随后 `BehaviorEngine.analyze_all(vehicle, scene_config)`（`behavior_engine.py:477-523`）判 6 类行为：`red_light` / `wrong_way` / `illegal_parking` / `speeding` / `lane_departure` / `running_yellow`，只有 `is_violation=True` 才转成 `ViolationEvent`。

### 3.3 🔴 实际发生的条件（运行实证）

`realtime_detector.py:515-529` 的真实调用是：

```python
new_events = self.event_engine.process_frame(
    frame,
    detections or [],
    self.tracked_vehicles or {},   # → 引擎形参 tracked_vehicles
    self.scene_config or {},       # → 引擎形参 scene_context
)
```

而 `self.scene_config` 在 `process_frame:376-384` 构造，**键只有**：

```python
{'traffic_light_state', 'stop_line_y', 'road_direction', 'speed_limit',
 'pixel_per_meter', 'no_parking_zones', 'lane_lines'}
```

**没有 `vehicles`，也没有 `tracked_vehicles`。** 于是 `_extract_vehicles` 依次失败：
`scene_context["vehicles"]` → None；`scene_context["tracked_vehicles"]` → None；
`tracker` 实参是 `dict`，`hasattr(dict, "get_all_vehicles")` → False → **返回 `[]`** → `analyze` 返回 `[]` → 引擎 `new_events` 恒为 `[]`。

**探针实测（§9.3）**：同一辆车、同一场景，仅改变调用约定：

| 探针 | 调用约定 | 结果 |
|---|---|---|
| A | `plugin.analyze(frame, scene_config, tracked_vehicles_dict)`（**生产路径**） | `events: 0` |
| B | `plugin.analyze(frame, {**scene_config, "vehicles": [veh]}, None)` | `events: 2`（`red_light`, `speeding`） |
| C | `engine.process_frame(..., tracked_vehicles_dict, scene_config)`（**生产路径**） | `new_events: 0` |
| D | `engine.process_frame(..., {}, {**scene_config, "vehicles": [veh]})` | `new_events: 2`（state=`triggered`） |

**结论：事件触发条件在现网代码中不可能满足。这是链路唯一的第一断点，必须先由负责人授权修复或由验证脚本绕过，才可能产出任何事件、视频或 DB 记录。**

---

## 4. EvidenceChain 如何生成和保存证据？

### 4.1 生成（`evidence_chain.py:117-192`，`EvidenceChain.from_traffic_event(event, camera_id)`）

从 `TrafficEvent` 抽取 18 个字段：基础信息（`camera_id`/`timestamp`/`location`）、车辆信息（`vehicle_id`←`event.track_id`、`vehicle_type`←`vehicle_info['class_name']`、`plate_number`/`plate_color`、`lane_id`）、场景上下文（`traffic_light_state`、`stop_line_relation`、`trajectory`）、视觉证据（`key_frames`、`event_video_path`）、判断结果（`rule_judgment`、`ai_judgment`、`ai_confidence`、`ai_explanation`）、`final_status`（由 `state_map` 映射，`triggered/recording/pending_ai/ai_reviewed/detecting → 'pending'`）。

**保存能力**：`to_dict()` / `to_json()` / `summary()`，纯内存对象，不落盘。

### 4.2 生产路径中**唯一**的调用点

`routers/realtime.py:928-945`（`GET /api/realtime/events/{event_id}`）：

```python
event = realtime_detector.active_events.get(event_id)
if event is not None:
    evt_dict = event.to_dict()
    try:
        from evidence_chain import EvidenceChain
        evidence = EvidenceChain.from_traffic_event(event, camera_id=f"cam_{realtime_detector.camera_index}")
        evt_dict['evidence_chain'] = evidence.to_dict()
    except Exception as e:
        logger.warning(...)          # 静默降级
    return JSONResponse(...)
```

**关键事实：`evidence_chain` 只在"内存事件存在"时临时构造并随响应返回，从不写入数据库。** `_sync_active_events_to_db()` 的 `common_fields`（`routers/realtime.py:808-825`）**不包含 `evidence_chain` 列**，因此 `traffic_events.evidence_chain` 恒为 NULL。

**运行实证（§9.4 P2）**：向临时 DB 副本同步 1 条事件后查询，`evidence_chain` 返回 `None`。
**库内实证（§9.2）**：`SELECT COUNT(*) FROM traffic_events WHERE evidence_chain IS NOT NULL` = **0**。

### 4.3 字段取值缺陷（只记录，不修改）

- `stop_line_relation`（`evidence_chain.py:142-152`）读 `scene_context.get('stop_line')`，但生产 `scene_config` 的键是 **`stop_line_y`**；同理 `traffic_light_state` 读 `scene_context.get('traffic_light')`，生产键是 **`traffic_light_state`**。→ 证据链中这两项在现网恒为 `unknown`。
- `trajectory` 来自 `TrafficEvent.trajectory`，而该字段由 `_extract_trajectory`（`traffic_event_engine.py:289-296`）生成，**只返回 1 个点**，尽管 `VehicleTracker` 的车辆 dict 里带着完整 `history`（`vehicle_tracker.py:85/340`）。`_extract_vehicle_info`（L233-244）未透传 `history`。
- `key_frames` 是 `"frame_0" / "frame_5" / "frame_9"` 一类**占位字符串**（`realtime_detector.py:629-643`），不是文件路径，磁盘上没有对应 jpg。

---

## 5. event_videos/*.mp4 是否真实生成，保存位置是什么？

### 5.1 保存位置与命名规则（代码确定）

- 基目录：`Config.EVENT_VIDEO_DIR` = `os.path.join(BASE_DIR, 'output', 'event_videos')` → **`E:\output\1\api\output\event_videos`**（`config.py:47`）
- 命名：`{EVENT_VIDEO_DIR}/{YYYYMMDD}/{event_id}.mp4`（`circular_frame_buffer.py:183-201`）
- 编码：`cv2.VideoWriter_fourcc(*'mp4v')`，fps=`Config.FRAME_BUFFER_FPS`（10）（`circular_frame_buffer.py:118-119`、`realtime_detector.py:579`）
- 调用点：`realtime_detector.py:571-586`（`extract_event_clip` → `generate_event_video_path` → `save_event_video`），成功后写回 `event.event_video_path`
- 对外访问：`app.py:146` 挂载 `/event-videos` 静态目录；另有 `GET /api/realtime/events/{id}/video` 用 `FileResponse`（`routers/realtime.py:966-1001`）

### 5.2 是否真实生成

- **生产目录为空**：`E:\output\1\api\output\event_videos` 递归枚举 **0 个文件**（§9.1）。
- **写视频能力本身可用**：探针 P1 在内存构造 20 帧并调用 `save_event_video`，**成功产出 17,741 字节 mp4**；`generate_event_video_path` 返回 `E:\output\1\api\output\event_videos\20260925\evt_probe_001.mp4`（§9.4 P1）。探针写入的是系统临时目录，未污染项目目录。
- 现有单测亦覆盖：`test_circular_frame_buffer.test_save_event_video` 生成 3,217 字节视频（临时目录）。

**判定：机制可用，生产产物为零。** 根因同 §3.3 —— 没有事件，就没有 `_handle_event_lifecycle`，也就没有 mp4。

另注：`realtime_detector.py:802-819` 的 `_save_violation_evidence` 落盘的是**违规截图 jpg**（`api/uploads/`，当前 43 个文件），属于旧的"违规证据"链路，与事件视频链路是两套东西，不可混淆。

---

## 6. traffic_events 表由谁创建、谁写入、谁查询？

### 6.1 谁创建（两条独立路径）

| 路径 | 代码 | 说明 |
|---|---|---|
| ORM 自动建表 | `database.py:28-34` `init_db()` → `Base.metadata.create_all(bind=engine)` | `app.py:60` 在 lifespan 中调用；只要 `models.TrafficEventRecord` 已被导入即建表 |
| 显式迁移脚本 | `migrate_db.py:157-195` `create_traffic_events_table(cursor)` | 手工执行 `py -3 api/migrate_db.py` 时创建，含 5 个索引 |

**库内实测（§9.2）**：表存在，**20 列**，**8 个索引**（`event_id/event_type/state/camera_id/trigger_time/created_at/track_id/id`），**行数 = 0**。

### 6.2 谁写入

**唯一写入者：`routers/realtime.py:783-843` 的 `_sync_active_events_to_db()`**（"懒同步"设计）。

- 触发时机：`list_events`（L854）与 `review_event`（L1101）开头各调用一次；
- 数据源：`realtime_detector.active_events`（内存 dict，`realtime_detector.py:73/535/621`）；
- 行为：`existing` 存在则逐字段 `setattr` 更新，否则 `TrafficEventRecord(...)` 新增；
- 整段被 `try/except` 包裹，异常只 `logger.warning` 并返回 0（`L841-843`）——**失败不可见**。

**没有任何检测循环内的直接 ORM 写入。** 也就是说：事件只有在"有人查询 `/events` 或执行人工复核"时才可能落库。

**运行实证（§9.4 P2）**：把 `database.SessionLocal` 指向 DB **副本**，向 `active_events` 注入 1 条内存事件，调用 `_sync_active_events_to_db()` → 返回 `1`，副本 `traffic_events` 出现 1 行（`state='triggered'`，`event_video_path` 正确，`key_frames` 为 JSON 数组，`camera_id='cam_0'`，**`evidence_chain=None`**）。写入逻辑本身可用。

### 6.3 谁查询

| 接口 | 行号 | 数据来源 |
|---|---|---|
| `GET /api/realtime/events` | 846-885 | 先 `_sync_active_events_to_db()`，再查 `TrafficEventRecord`（支持 `state`/`camera_id`/分页） |
| `GET /api/realtime/events/active` | 888-925 | 优先内存 `active_events`，为空则查库（`state NOT IN (confirmed, rejected)`，limit 50） |
| `GET /api/realtime/events/{event_id}` | 928-963 | 先内存（并临时拼 `evidence_chain`），否则查库 `filter_by(event_id=...)` |
| `GET /api/realtime/events/{event_id}/video` | 966-1001 | 内存 `event.event_video_path` → 回退查库 |
| `GET /api/realtime/events/{event_id}/frames` | 1004-1037 | 内存 `key_frames` → 回退查库（JSON 解析） |
| `POST /api/realtime/events/{event_id}/review` | 1047-1118 | 内存则调 `event_engine.manual_review` 再同步；否则直接改库字段 |

---

## 7. FastAPI 是否提供对应查询或资源访问接口？

**是。** 运行验证：`test_task029_integration.test_api_routes_registered()` 实测 `total_routes=34`，6 条事件路由 `missing=[]`（§9.3 第 6 项）。

- 路由前缀：`router = APIRouter(prefix="/api/realtime", ...)`（`routers/realtime.py:27`）
- 挂载：`app.include_router(realtime.router)`（`app.py:131`）
- 6 条事件接口全部存在且路径与 `AI_COORDINATION_PROTOCOL.md` 主线一致
- 资源访问双通道：静态 `/event-videos/{YYYYMMDD}/{event_id}.mp4`（`app.py:146`）+ REST `GET /api/realtime/events/{id}/video`（`FileResponse`，不存在时 404 `{"success": false, "message": "事件视频不存在或尚未生成"}`）

**但"有接口"≠"有数据"**：因 §3.3 断链，以上接口当前一律返回空集；`traffic_events` 0 行，`event_videos` 0 文件。

**未在本次验证**：未启动 uvicorn（属 TASK-COORD-002/后续验证任务范围），因此路由的 HTTP 实际可达性与响应体未经联调验证。

---

## 8. 当前哪些环节有代码证据 / 测试证据 / 仍未验证

### 8.1 有代码证据的环节

| 环节 | 证据 |
|---|---|
| 数据源读取（camera/video/carla） | `realtime_detector.py:162-248`、`273-316` |
| YOLO 检测 | `realtime_detector.py:660-671` → `image_recognizer.multi_model_detect:781` |
| 跟踪 | `realtime_detector.py:368` → `vehicle_tracker.VehicleTracker.update:472` |
| 行为规则 | `realtime_detector.py:386-403` → `behavior_engine.analyze_all:477` |
| 多帧确认 | `realtime_detector.py:408-426`、`multi_frame_validator.py:97` |
| 循环缓存 | `circular_frame_buffer.py:54/67/90`；写入点 `realtime_detector.py:496-513` |
| 事件引擎 | `traffic_event_engine.py` 全文 |
| 证据链 | `evidence_chain.py` 全文 |
| 事件视频 | `circular_frame_buffer.py:90-142` + `realtime_detector.py:571-586` |
| DB 模型与同步 | `models.py:197-267`、`routers/realtime.py:783-843` |
| 路由 | `routers/realtime.py:846-1118`、`app.py:131/146` |

### 8.2 有测试证据的环节

命令与结果见 §9.3。

| 测试 | 覆盖内容 | 结果 |
|---|---|---|
| `unittest discover -s tests -t tests` | 37 个用例 | **36 通过 / 1 导入错误**（`test_core` 需 `pytest`，未安装） |
| `test_circular_frame_buffer` (9) | 缓存增删/清空/duration/片段提取/**视频写出**/路径生成/参数校验 | 全通过 |
| `test_traffic_event_engine` (15) | 8 状态枚举、转换表、dataclass 字段、触发、冷却、提交 AI、AI 结果三态、人工复核、状态历史、清理 | 全通过（**但用 `MockRulePlugin`，见 8.3**） |
| `test_evidence_chain` (8) | 18 字段、`from_traffic_event`、`from_dict`、`to_json`、`summary`、v3 嵌套 | 全通过 |
| `test_cloud_collaborator_event` (4) | B1/B2 修复回归：`autospec=True` 强制校验"调用点实参 ↔ 真实签名"，全程不联网 | 全通过 |
| `test_multi_frame_validator` (14) | 相似度/IOU/投票 | 通过 |
| `test_task029_integration`（脚本，非 unittest） | 7 项集成自检 | **6 PASS / 1 FAIL** |

`test_task029_integration` 逐项：

```
[PASS] CircularFrameBuffer 基本功能            size=3, duration=0.0s, latest_len=1
[PASS] TrafficEventEngine 事件创建+状态转换    8 状态齐全, state_changed=True
[PASS] EvidenceChain 从事件构建                18 字段, final_status=confirmed
[PASS] CloudCollaborator.analyze_event 接口存在性  params 齐全, missing=[]
[PASS] RealtimeViolationDetector 集成检查      frame_buffer=CircularFrameBuffer, event_engine=TrafficEventEngine
[PASS] API 路由注册检查                        total_routes=34, missing=[]
[FAIL] traffic_events 表存在检查               错误: 数据库文件不存在: E:\output\1\zhitong_violations.db
=== SUMMARY: PASS 6 / 7 ===
```

> 第 7 项失败**不是**表不存在，而是 `test_task029_integration.py:294` 取 `Config.DB_PATH`（`config.py:19` = `E:\output\1\zhitong_violations.db`）——该文件**不存在**；真实库在 `E:\output\1\api\zhitong_violations.db`（`database.py:7` 用相对路径 `sqlite:///./zhitong_violations.db`，随工作目录解析）。表本身存在且结构正确。

### 8.3 测试**不能**证明什么（关键）

1. **`test_traffic_event_engine` 全部 15 项使用的是自带的 `MockRulePlugin`**（`tests/test_traffic_event_engine.py:44-52`）：

   ```python
   def analyze(self, frame, scene_context, tracked_vehicles):
       return list(self._violations)     # 完全忽略入参，无条件返回预设违规
   ```

   → 引擎"能触发"被证明了，**"真实插件能被引擎正确驱动"从未被测试**。§3.3 的断链因此完全逃过测试网。
2. `test_task029_integration` 第 5 项只做 `hasattr` 属性/方法存在性检查（`:219-226`），**不调用** `_process_event_engine` / `_handle_event_lifecycle`；仓库内 `grep` 显示**没有任何测试调用这两个方法**，也没有任何测试调用 `_sync_active_events_to_db`。
3. `test_cloud_collaborator_event` 全程 mock 云端函数，证明的是**接口契约与降级行为**，不是真实网络/真实模型结果。
4. `test_circular_frame_buffer.test_generate_event_video_path` 只断言路径形状，不断言文件真的生成在该路径。
5. `api/test_*.py`（10 个）是手工脚本（需要摄像头/联网/交互），**未被 unittest 收集**，本次未运行。

### 8.4 仍未验证的环节

- 真实交通视频 → YOLO → tracking → 行为规则的**端到端真实触发**
- 事件视频在**生产目录**落盘
- `traffic_events` 的**首次真实写入**（当前 0 行）
- FastAPI 服务的**真实启动与 HTTP 联调**（端口 8001 未监听）
- 云端 AI 真实调用（`analyze_event` 的真实判定链路）
- 前端 EventCenter 展示（属 TASK-COORD-002）
- 真实性能指标（FPS / 延迟 / mAP）

---

## 9. 验证命令与原始结果

> 全部为只读或"只写系统临时目录"的探针；未触碰项目数据库、未启动长驻服务、未修改任何项目文件。
> 环境：`py -3` = Python 3.12（`C:\Users\ROG\AppData\Local\Programs\Python\Python312`），`PYTHONDONTWRITEBYTECODE=1`（不产生 `__pycache__`）。

### 9.1 产物与目录检查

```
E:\output\1\zhitong_violations.db           MISSING
E:\output\1\api\zhitong_violations.db       EXISTS  208896 B  2026/9/7 14:44:30
E:\output\1\api\zhitong.db                  EXISTS   49152 B  2026/7/24 9:04:31
E:\output\1\api\output\event_videos\        递归枚举 = 0 个文件
E:\output\1\api\uploads\                    43 个文件
```

### 9.2 数据库只读检查（`sqlite3 connect(file:...?mode=ro, uri=True)`）

```
== tables ==  api_logs, collaboration_sessions, sqlite_sequence, system_configs,
              system_statistics, traffic_events, users, violation_evidences
== traffic_events columns ==  count = 20
   ['id','event_id','event_type','track_id','state','trigger_time','vehicle_info',
    'scene_context','trajectory','key_frames','event_video_path','rule_judgment',
    'ai_judgment','ai_confidence','ai_explanation','evidence_chain','state_history',
    'camera_id','created_at','updated_at']
== traffic_events rows == 0
== indexes on traffic_events == 8 个
   ['ix_traffic_events_trigger_time','..._event_type','..._created_at','..._track_id',
    '..._id','..._camera_id','..._event_id','..._state']
== violation_evidences rows == 20
== evidence_chain non-null == 0
== Config.DB_PATH target exists? == False
```

### 9.3 测试执行

```
$ py -3 -m pytest tests/ -v
  → No module named pytest            （pytest 未安装）

$ py -3 -m unittest discover -s tests -t tests -v
  → Ran 37 tests in 0.018s
  → FAILED (errors=1)   ERROR: test_core → ModuleNotFoundError: No module named 'pytest'
  → 其余 36 个用例 ok

$ py -3（stdin 脚本）逐项调用 test_task029_integration 的 7 个检查函数
  → PASS 6 / 7，FAIL 项 = traffic_events 表存在检查（Config.DB_PATH 文件不存在）
```

### 9.4 三项定向探针（决定性证据）

**探针 A/B/C/D — 调用契约不匹配（§3.3 的实证来源）**

```
loaded: ['public_security', 'traffic', 'urban_management']
traffic plugin is_enabled attr? False | is_initialized: True
--- A) realtime_detector convention: plugin.analyze(frame, scene_config, tracked_vehicles_dict) ---
   events: 0 []
--- B) plugin documented convention: scene_context 含 'vehicles' ---
   events: 2 [('red_light', 1), ('speeding', 1)]
--- C) TrafficEventEngine.process_frame 用生产约定 ---
   new_events: 0
--- D) TrafficEventEngine.process_frame 用含 'vehicles' 的 scene_context ---
   new_events: 2 [('evt_..._1_3315b2','red_light','triggered'),
                  ('evt_..._1_b31f21','speeding','triggered')]
```

**探针 P1 — 事件视频能力（写入系统临时目录）**

```
[P1] frames in clip = 20
[P1] save_event_video returned = 'C:\Users\ROG\AppData\Local\Temp\audit_probe_event.mp4'
[P1] file exists = True size = 17741
[P1] Config.EVENT_VIDEO_DIR = E:\output\1\api\output\event_videos
[P1] generate_event_video_path (Config) = E:\output\1\api\output\event_videos\20260925\evt_probe_001.mp4
```

**探针 P2 — DB 同步能力（指向数据库副本，项目库未被写入）**

```
[P2] _sync_active_events_to_db returned = 1
[P2] rows in temp traffic_events = 1
      ('evt_audit_probe_001','red_light','triggered','...\Temp\audit_probe_event.mp4',
       '["frame_0", "frame_5", "frame_9"]', None, 'cam_0')
                                                          ↑ evidence_chain = NULL
```

（临时 mp4 与临时 DB 副本均已删除；副本删除时被 SQLAlchemy 连接短暂占用，进程退出后已清除，项目目录无残留。）

---

## 10. 与验收标准逐项对应

| # | 验收问题 | 结论 | 依据 |
|---|---|---|---|
| 1 | 实际入口文件 | `api/app.py`（uvicorn `app:app`，8001）；运行时单例 `api/realtime_detector.py:1098` | §1 |
| 2 | 关键函数和类 | `RealtimeViolationDetector`、`TrafficEventEngine`/`TrafficEvent`/`EventState`、`CircularFrameBuffer`、`EvidenceChain`、`CloudCollaborator.analyze_event`、`TrafficEventRecord`、`TrafficPlugin` | §2 |
| 3 | 引擎触发条件 | 需 4 条同时成立；**生产路径因 `scene_context` 缺 `vehicles`/`tracked_vehicles` 键，恒不触发（探针实测 0）** | §3、§9.4-A/C |
| 4 | EvidenceChain 生成与保存 | 生成：`from_traffic_event` 18 字段；保存：**仅内存/响应内临时构造，从不落库**（`evidence_chain` 列恒 NULL）；且 `stop_line`/`traffic_light` 键名不匹配、`trajectory` 仅 1 点、`key_frames` 为占位串 | §4、§9.2、§9.4-P2 |
| 5 | mp4 是否真实生成/位置 | 位置 `E:\output\1\api\output\event_videos\{YYYYMMDD}\{event_id}.mp4`（+ 静态 `/event-videos`）；**能力可用（探针写出 17,741 B），生产目录为空** | §5、§9.1、§9.4-P1 |
| 6 | 表由谁创建/写入/查询 | 创建：`init_db()` 的 `create_all` + `migrate_db.create_traffic_events_table`；写入：**仅** `routers/realtime.py:_sync_active_events_to_db()`（懒同步，仅查询/复核时触发）；查询：6 条 `/api/realtime/events*` 路由直查 ORM。当前 **0 行** | §6、§9.2 |
| 7 | FastAPI 是否提供对应接口 | 是，6 条事件路由全部注册（`total_routes=34, missing=[]`），+ `/event-videos` 静态挂载 + `FileResponse` 下载；但无数据可返回 | §7、§9.3 |
| 8 | 哪些环节有代码证据 | 见 §8.1 表（自数据源到路由全覆盖） | §8.1 |
| 9 | 哪些环节有测试证据 | 36/37 单测通过 + 集成自检 6/7；覆盖缓存、状态机、证据链、云端契约、多帧 | §8.2、§9.3 |
| 10 | 哪些环节仍未验证 | 真实视频端到端触发、生产目录 mp4、traffic_events 首次落库、服务启动与 HTTP 联调、真实云端调用、前端展示 | §8.4 |
| 11 | 最小真实视频验证方案 | 见 §11 | §11 |
| 12 | 阻塞问题与风险 | 见 §12 | §12 |

---

## 11. 最小真实视频闭环验证方案

### 11.1 必需输入

1. **一段真实交通视频**（.mp4/.avi，含车辆且画面中能形成轨迹；建议 ≥20s，便于覆盖 `EVENT_CLIP_BEFORE_SEC=5` + `AFTER_SEC=5`），放到 `E:\output\1\data\` 下，例如 `E:\output\1\data\audit_clip.mp4`。
2. **一个必然成立的违规判据**（否则事件仍不触发）。最省事的是 `speeding`：`analyze_speeding` 只看轨迹速度，不需要红绿灯模型；或 `red_light`：需要 `_detect_traffic_light_state` 返回 `'red'`（依赖红绿灯检测模型输出 `red_light` 类别）。
3. 可选：`api/config_runtime.json` 中的豆包/DeepSeek Key。**无 Key 不影响闭环成立**——`analyze_event` 会降级，`apply_ai_result` 得到 `uncertain` → `MANUAL_REVIEW`，仍是合法状态且会落库。

### 11.2 前置条件（按当前代码状态）

- Python 3.12 + 项目依赖（`ultralytics` / `opencv-python` / `fastapi` 等已可导入，见 §9.4 模型加载成功）。
- **必须先解决 §3.3 的调用契约不匹配**，否则生产路径事件数恒为 0，任何视频都验不出闭环。两种选择：
  - **(推荐，需授权)** 由后续 TASK 修复 `realtime_detector._process_event_engine` 与 `TrafficPlugin._extract_vehicles` 的契约（二选一改一侧即可，不要两侧同改）；
  - **(零代码改动)** 用 §11.3 方案 A 的 stdin 探针脚本，在**进程内**构造正确 `scene_context` 调用引擎，证明链路其余部分真实可用，把"改代码"留给有授权的 TASK。
- 后端如需走 HTTP 验证：工作目录必须是 `E:\output\1\api`（否则 `database.py:7` 的相对路径会让 DB 落到别处）。

### 11.3 验证步骤

**方案 A：零代码改动的进程内最小闭环（本轮即可执行，建议作为 TASK-COORD-003 的验收基线）**

1. `cd E:\output\1\api`；用 `py -3 -`（stdin，不落脚本文件）执行：
   1. `from realtime_detector import realtime_detector`（加载单例，其 `event_engine` 插件已就绪）；
   2. `realtime_detector.start_camera(0, r"E:\output\1\data\audit_clip.mp4")`；
   3. 循环 `cap.read()` → `realtime_detector.process_frame(frame)` 若干帧（≥10 帧以积累 `VehicleTracker.history`）；
   4. 取 `sd = realtime_detector.scene_config`，构造 `ctx = {**sd, "tracked_vehicles": realtime_detector.tracked_vehicles}`，调用 `realtime_detector.event_engine.process_frame(frame, [], realtime_detector.tracked_vehicles, ctx)`；
   5. 对每个新事件调用 `realtime_detector._handle_event_lifecycle(event)`（内部会 sleep 5s → RECORDING → 抽帧 → 写 mp4 → PENDING_AI → analyze_event → AI_REVIEWED → 终态）。
2. 断言：
   - `len(new_events) >= 1`；
   - `event.event_video_path` 非空且 `os.path.exists(...)` 为 True，位于 `api\output\event_videos\{YYYYMMDD}\`；
   - 事件终态 ∈ {`confirmed`,`rejected`,`manual_review`}（无 Key 时预期 `manual_review`）；
   - `event.state_history` 至少包含 `triggered→recording→pending_ai→ai_reviewed→…` 的完整轨迹。

**方案 B：HTTP 端到端（在 §3.3 修复获授权之后执行）**

1. `cd E:\output\1\api`；`py -3 -m uvicorn app:app --host 127.0.0.1 --port 8001`（后台作业，勿关窗口）。
2. `GET /health` → `db_exists` 应为 true（验证工作目录正确）。
3. `POST /api/realtime/source` `{"source_type":"video","video_path":"E:\\output\\1\\data\\audit_clip.mp4"}` → `success:true`。
4. `POST /api/realtime/start` `{"video_path":"E:\\output\\1\\data\\audit_clip.mp4"}`（注意：`/start` 直接调 `start_camera`，不重置 `source_type`，故第 3 步必须先做；见 §12-R9）。
5. 轮询 `GET /api/realtime/status`，观察 `frame_buffer_size`、`active_events`、`event_engine.total_events` 从 0 增长。
6. `GET /api/realtime/events/active` → 应看到事件；`GET /api/realtime/events` → 应出现 DB 行。
7. `GET /api/realtime/events/{id}` → 检查 `evidence_chain` 是否被临时拼装；`GET /api/realtime/events/{id}/video` → 应返回 `video/mp4`。
8. 只读核对 DB：`SELECT COUNT(*) FROM traffic_events` > 0；`SELECT event_video_path FROM traffic_events` 指向真实存在的文件。
9. 收尾：`POST /api/realtime/stop`。

**失败时的记录要求**（协议 §3：任一步失败都要记录确切证据）
逐帧记录 `result['detections']` 数量、`tracked_vehicles` 数量、`behavior_results` 列表、`new_events` 数量、`event.state`，并附 `api/output/logs/api.log` 中 `[RealtimeDetector]` / `[TrafficEventEngine]` / `[CircularFrameBuffer]` 前缀行。

### 11.4 成功判据（闭环成立的最小证据集）

```
1) E:\output\1\api\output\event_videos\<YYYYMMDD>\<event_id>.mp4 存在且 >0 字节
2) SELECT COUNT(*) FROM traffic_events  ≥ 1
3) 该行 event_video_path 指向 (1) 的文件，state ∈ 有效状态集合
4) GET /api/realtime/events/{id} 返回 success=true 且含 state_history
```

---

## 12. 阻塞问题与风险

### 12.1 阻塞项（阻断最小闭环）

| 编号 | 阻塞 | 文件位置 | 证据 | 是否阻塞本 TASK |
|---|---|---|---|---|
| **B-1** | `scene_context` 缺少 `vehicles`/`tracked_vehicles` 键，`TrafficPlugin._extract_vehicles` 恒返回 `[]`，事件触发数恒为 0 | `realtime_detector.py:515-529`（传参）／`traffic_plugin.py:150-176`（取数）／`base_plugin.py:72-84`（契约定义） | 探针 A/C = 0，B/D = 2（§9.4） | **是**（不修复则无事件、无视频、无落库） |
| **B-2** | `Config.DB_PATH` 指向 `E:\output\1\zhitong_violations.db`（不存在），而 `database.py:7` 用相对路径 `./zhitong_violations.db`，实际库在 `api\`。全项目自检第 7 项因此 FAIL | `config.py:19`、`database.py:7`、`tests/test_task029_integration.py:294` | 集成自检 6/7，FAIL 项报"数据库文件不存在" | 部分（不阻塞手写探针，但使官方自检恒红、且若从错误工作目录启动后端会写出第二个库） |

### 12.2 风险项（不阻塞本轮，但会影响闭环质量与可信度）

| 编号 | 风险 | 位置 | 说明 |
|---|---|---|---|
| R-1 | `evidence_chain` 从不落库 | `routers/realtime.py:808-825` | 列存在但恒 NULL（实测 0 条非空）；事件详情只在内存命中时才临时拼装，历史事件查库时无证据链 |
| R-2 | `key_frames` 是占位字符串 | `realtime_detector.py:629-643` | 返回 `frame_0/frame_5/frame_9`，磁盘无文件；`GET /events/{id}/frames` 返回不可加载的字符串 |
| R-3 | 证据链场景字段键名不匹配 | `evidence_chain.py:139-152` vs `realtime_detector.py:376-384` | 读 `traffic_light`/`stop_line`，生产写 `traffic_light_state`/`stop_line_y` → 恒 `unknown` |
| R-4 | 轨迹只有 1 个点 | `traffic_event_engine.py:289-296`、`_extract_vehicle_info:233-244` | 未透传 `VehicleTracker` 的 `history`，证据链 `trajectory` 退化，`stop_line_relation` 必然 `unknown` |
| R-5 | DB 同步是"懒同步"，只在被查询时写 | `routers/realtime.py:854/1101` | 若前端从不查 `/events`，事件永不落库；且写入失败只 `logger.warning`，静默丢失 |
| R-6 | `active_events` 无界增长、`cleanup_old_events` 从未被调用 | `realtime_detector.py:73`、`traffic_event_engine.py:492-508` | 长时间运行内存累积；卡在 PENDING_AI 的事件不会被清理 |
| R-7 | 视频文件读到结尾后检测循环不退出 | `realtime_detector.py:306-309` | `ret=False` → `sleep+continue` 死循环，必须人工 `/stop`；验证时易误判"还在跑" |
| R-8 | `/start` 绕过 `set_source` | `routers/realtime.py:41-48` | 直接调 `start_camera`，不更新 `source_type`；若上次为 `carla`，循环会走 CARLA 分支而忽略 `cap` |
| R-9 | 云端调用为真实外部依赖 | `cloud_collaborator.py:588-688` | 无 Key / 网络异常时整段走降级，只产出 `uncertain`；成本与限额未评估 |
| R-10 | pytest 缺失导致 `test_core` 恒为导入错误 | `tests/test_core.py:6` | 测试套件永远不是全绿，容易掩盖真实失败 |
| R-11 | `database.migrate_missing_columns` 只覆盖 `violation_evidences` | `database.py:36-75` | `traffic_events` 依赖 `create_all`；若表已存在但缺列，不会自动补列 |

---

## 【发现的额外问题】

> 均**不**在本 TASK 范围内，仅记录，未做任何修复。

| # | 文件或模块 | 问题描述 | 是否阻塞当前 TASK | 建议后续 TASK |
|---|---|---|---|---|
| E-1 | `E:\output\1\api\main.py` | 旧入口与 `app.py` 并存，自带 JWT Secret 与另一套 ORM 模型；`app.py` 未引用 | 否 | 独立 TASK：旧入口/旧 DB 边界清理（TASK-COORD-002/003 之后） |
| E-2 | `E:\output\1\api\output\event_videos` 与 `E:\output\1\api\uploads` | 两套产物目录并存（事件视频 vs 违规截图），命名与生命周期规则不同，README/PROJECT_FILE_INDEX 未描述 | 否 | 独立 TASK：产物目录规范 |
| E-3 | `E:\output\1\api\test_*.py`（10 个） | 手工脚本混在源码目录，需要摄像头/联网/交互，未被 unittest 收集；`PROJECT_AUDIT_AND_BASELINE_REPORT.md` P2-1 已记 | 否 | 独立 TASK：测试入口归类或标注 SKIP |
| E-4 | `E:\output\1\api\database.py:7` | `DATABASE_URL` 用相对路径，DB 落点随启动工作目录漂移（`start-all.bat` 用 `cd api`，手工 `py -3 -m uvicorn` 从别处启动会生成第二个库） | 部分（见 B-2） | 独立 TASK：DB 路径统一到 `Config.DB_PATH` |
| E-5 | `E:\output\1\api\routers\realtime.py:1070-1074` | 数据库分支人工复核的 `state_history` 写入 `old_state == new_state`（先改 `record.state` 再取值），历史记录语义错误 | 否 | 独立 TASK：复核状态历史修正 |
| E-6 | `E:\output\1\PROJECT_AUDIT_AND_BASELINE_REPORT.md` §6 P1-6 | 该报告仍把 B1/B2 列为未修复；实测 `test_cloud_collaborator_event`（4 项，`autospec=True` 强校验签名）全通过，`image_recognizer.analyze_with_claude` 已是 3 参签名 | 否 | 独立 TASK：文档与代码对齐（避免下一任重复修） |
| E-7 | `E:\output\1\tests\test_task029_integration.py:371-377` | 运行 `main()` 会写 `_TASK-029-M09_integration_selfcheck.json`；本轮为避免产生文件，只逐项调用其检查函数 | 否 | 记录即可 |

---

## 【本次任务模型信息】

- **实际使用模型**：当前环境无法可靠读取实际模型名称。
  （补充说明：本会话运行时上下文声明为 `deepseek-flash`，但该名称无法由当前环境独立校验，故不作为"实际模型"结论。）
- **任务复杂度**：**L3**
  （跨 12+ 文件追踪调用链、需同时给出代码证据与运行证据、涉及状态机/数据库/视频 IO/路由四类子系统；但所有结论均可由静态阅读 + 只读探针确定性验证，未涉及 L4 级别的多方案架构权衡或大规模重构。）
- **模型选择理由**：本任务的核心是"沿真实调用关系追断点"，需要长链路上下文保持与精细的实参/形参比对能力；L3 要求具备可靠代码理解与实验设计的模型。当前会话未提供可切换的更高能力模型入口，故以现有模型完成，并通过**外部可复现探针**（§9.4）弥补推理环节的可信度，而非依赖"代码看起来没问题"的判断。
- **是否发生模型切换**：否。
- **切换原因**：不适用。

---

*报告结束。本轮仅新增本文件；未修改任何业务代码、数据库、配置或启动脚本。*
