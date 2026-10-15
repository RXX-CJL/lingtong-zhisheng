# TASK-COORD-002 审计报告：管理端 EventCenter、后端 API 与测试入口

> 执行 Agent：Trae IDE
> 日期：2026-09-25
> 性质：只读审计。未修改任何业务代码、数据库、启动脚本。唯一新增文件为本报告。
> Git 状态：分支 main；验证期间后端进程已停止，前端仅产生 `web-admin/dist/` 构建产物（.gitignore 范畴）。

## 0. 证据分级说明

本报告所有结论按以下 5 级区分：

- **A 代码存在**：源码可读但未执行
- **B 代码可运行**：语法/导入/构建通过
- **C 功能实际执行**：服务启动并实测接口
- **D 真实数据验证**：真实数据写入并读回
- **E 完整链路验证**：端到端闭环（视频→事件→落盘→前端展示）

## 1. 逐项验收结论（12 条）

### 1.1 EventCenter 的实际入口文件是什么？

| 项 | 值 | 证据级别 |
|---|---|---|
| 列表页 | `web-admin/src/views/EventCenter.vue` | B（已通过 vite build） |
| 详情页 | `web-admin/src/views/EventDetail.vue` | B |
| 路由注册 | `web-admin/src/router/index.js` L22-30：`/events` → EventCenter，`/events/:id` → EventDetail | B |
| 菜单入口 | `web-admin/src/App.vue` L62-66：`/events` 子路由映射到主菜单 `/violations` 分组下高亮（无独立顶级菜单项，入口依附"违规管理"分组） | A |
| API 封装 | `web-admin/src/api/index.js` L299-342（M08 交通事件中心段） | B |
| 依赖组件 | `web-admin/src/components/TypeTag.vue`、`web-admin/src/utils/format.js` | B |

页面跳转：列表行点击 → `router.push('/events/{event_id}')`（EventCenter.vue L341-347）。

### 1.2 EventCenter 调用了哪些 API？

前端 `api/index.js` 定义、且页面实际调用：

| 前端函数 | HTTP | 实际请求路径 | 调用方 | axios 实例 |
|---|---|---|---|---|
| getEventList | GET | `/api/realtime/events` | EventCenter.vue L359 | realtimeRequest（直连 `http://{hostname}:8001`，绕过 Vite 代理） |
| getActiveEvents | GET | `/api/realtime/events/active` | EventCenter.vue L381，每 5s 轮询 | realtimeRequest |
| getEventDetail | GET | `/api/realtime/events/{id}` | EventDetail.vue L833 | realtimeRequest |
| getEventFrames | GET | `/api/realtime/events/{id}/frames` | EventDetail.vue L853 | realtimeRequest |
| reviewEvent | POST | `/api/realtime/events/{id}/review` | EventDetail.vue L887 | realtimeRequest |
| getEventVideoUrl | — | `{direct}:8001/api/realtime/events/{id}/video` | EventDetail.vue `<video :src>`（L448-451） | 直拼 URL |
| getEventFrameUrl | — | `{direct}:8001/{归一化路径}` | EventDetail.vue 关键帧 `<el-image>` | 直拼 URL |

注意：事件类 API 全部走 `realtimeRequest` 直连 8001（`api/index.js` L62-69 注释：Vite 代理会阻塞 MJPEG 流）。普通 `request`（baseURL `/api`，走 Vite 代理）不用于事件页。

### 1.3 API 请求和响应字段是否与后端实际定义一致？

**逐字段核对结果：一致（列表/详情/frames/review 均一致）。**

请求参数：

| 前端发送 | 后端 `list_events`（realtime.py L846-848） | 结论 |
|---|---|---|
| page, size, state, camera_id | state, page, size, camera_id | ✓ 一致 |

响应字段（后端 `TrafficEventRecord.to_dict()`，models.py L246-267）vs 前端使用：

| to_dict 字段 | EventCenter 使用 | EventDetail 使用 | 结论 |
|---|---|---|---|
| event_id / event_type / track_id / state / camera_id | ✓ | ✓ | ✓ |
| trigger_time / created_at / updated_at（ISO 字符串） | ✓ | ✓ | ✓ |
| ai_confidence（float） | ✓ | ✓ | ✓ |
| vehicle_info / scene_context / trajectory（JSON 解析后为对象或 null） | ✓（getVehicleField 取 plate_number/plate_color） | ✓ | ✓ |
| rule_judgment / ai_judgment / ai_explanation | — | ✓ | ✓ |
| evidence_chain | — | ✓（内存路径由 realtime.py L939-944 现场构造；DB 路径用落库 JSON） | ✓ |
| state_history | — | ✓（时间线 L596-670） | ✓ |

- 响应包裹：列表 `{success, data, total, page, size}`；详情 `{success, data}`；frames `{success, event_id, key_frames, count}`（realtime.py L1032-1037）——与前端 `res.data/res.total/res.key_frames` 取法一致。
- review 请求体：前端 `{confirmed, reviewer, comment}` ↔ 后端 `EventReviewRequest`（realtime.py L1040-1044）：一致。
- 状态机值域：前端 stateLabelMap 8 状态（detecting/triggered/recording/pending_ai/ai_reviewed/confirmed/rejected/manual_review）= models.py L208 默认 + traffic_event_engine 8 状态（test 实测输出同一 8 状态列表）：一致。

**不一致点（仅 1 处，属筛选功能缺陷，见 §3 额外问题 2）**：EventCenter.vue 筛选下拉"违规停车"值为 `illegal_park`（L53），而后端 behavior_engine.py 实际产生 `illegal_parking`（L271/308/325）；且 `loadData` 未把 `event_type` 传给后端（L353-358），后端 `list_events` 也不支持 `event_type` 参数——该筛选 UI 当前整体无效。

### 1.4 后端事件查询路由是否真实注册并可调用？

**已实测可调用（C 级）。** 证据：

- 注册：`api/app.py` L131 `app.include_router(realtime.router)`；realtime.py L27 `APIRouter(prefix="/api/realtime")`。
- 实测（本机启动 uvicorn 后 HTTP 实调）：
  - `GET /api/realtime/events?page=1&size=3` → **200** `{"success":true,"data":[],"total":0,"page":1,"size":3}`
  - `GET /api/realtime/events/active` → **200** `{"success":true,"data":[],"count":0}`
  - `GET /api/realtime/events/nonexistent_id_123` → **404**（预期行为）
  - `GET /health` → **200** `{"status":"healthy","version":"2.0.0","yolo_available":true,"dashscope_available":true,"db_exists":true,"overall":"ok"}`
- test_task029_integration.py 第 6 项"API 路由注册检查"：PASS（total_routes=34, required=6, missing=[]）。
- **重要事实**：`traffic_events` 表当前 **0 条记录**（列表接口 total=0），即接口可运行但无任何真实事件数据。

### 1.5 event_videos/*.mp4 是否存在对应的静态访问路径？

**代码存在（A 级），但目录为空、无任何 mp4。**

- 挂载：`api/app.py` L139-146，`app.mount("/event-videos", StaticFiles(directory=Config.EVENT_VIDEO_DIR))`。
- 目录来源：`api/config.py` L47 `EVENT_VIDEO_DIR = env 或 api/output/event_videos`（BASE_DIR=api 目录，L10）。
- 实际检查：`E:\output\1\api\output\event_videos\` **存在但为空**（递归枚举 0 个文件）；全项目 Glob `**/event_videos/**/*.mp4` 0 命中。
- 实测 `GET /event-videos/xxx_not_exist.mp4` → 404（挂载存活、无文件）。
- 另有按事件 ID 的动态视频接口 `GET /api/realtime/events/{id}/video`（realtime.py L966-1001，FileResponse，路径取内存或 DB `event_video_path`；文件不存在时 404）。

### 1.6 前端能否展示事件详情、视频和状态？

**代码存在且构建通过（A+B 级）；因无真实事件数据，未做真实数据展示验证（D/E 级未达成）。**

- 详情：EventDetail.vue 完整实现（摘要横幅、事件信息、车辆信息、场景上下文+轨迹 SVG、AI 分析结果、规则判断 JSON、证据链时间线、人工复核表单）。
- 视频：`<video>` 直连 `{host}:8001/api/realtime/events/{id}/video`（L448-451），带加载失败兜底 UI；关键帧画廊 + 预览大图。
- 状态：8 状态标签/颜色/横幅映射完整（L674-694、L567-593）。
- 人工复核：确认违法/排除事件，POST review 后本地更新 + 重新拉取详情。
- 前提条件：需后端 8001 在运行且存在事件记录；当前数据库为空，页面将显示空列表（列表页可正常渲染"共 0 条"）。

### 1.7 前端启动和构建命令是什么？

`web-admin/package.json`：

- 开发：`npm run dev`（vite，端口 5173，host 0.0.0.0；predev 先执行 `node clean-vite-temp.cjs`）
- 构建：`npm run build`（prebuild 先执行 `node scripts/verify-icons.cjs`）
- 代理：`vite.config.js` L18-27，`/api` 与 `/uploads` → `http://127.0.0.1:8001`
- 一键启动：`start-all.bat`（后端 + 前端 + 打开浏览器）

### 1.8 后端启动和健康检查命令是什么？

- 脚本 1：`api/start_api.bat` L43 → cwd=api，`C:\miniconda\envs\zhitong-gpu\python.exe app.py`（app.py L191 内部 uvicorn 0.0.0.0:8001 reload=True）
- 脚本 2：`start-all.bat` L13 → `py -3 -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload`（**用 py -3 而非 conda env，两个入口环境不一致**，见 §3 额外问题 4）
- 本次审计实测等价命令：`C:\miniconda\envs\zhitong-gpu\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8001`（cwd=api）→ 启动成功
- 健康检查：`curl http://127.0.0.1:8001/health` → 200 healthy（overall=ok）

### 1.9 tests 如何运行，哪些测试通过或失败？

运行环境：`C:\miniconda\envs\zhitong-gpu\python.exe`（Python 3.11.15）。**该环境无 pytest。**

| 测试文件 | 运行方式 | 本次结果 |
|---|---|---|
| tests/test_circular_frame_buffer.py | `python -m unittest`（unittest 风格） | PASS（合并统计） |
| tests/test_cloud_collaborator_event.py | 同上 | PASS |
| tests/test_evidence_chain.py | 同上 | PASS |
| tests/test_traffic_event_engine.py | 同上 | PASS |
| **以上 4 文件合计** | `python -m unittest tests.test_circular_frame_buffer tests.test_cloud_collaborator_event tests.test_evidence_chain tests.test_traffic_event_engine` | **Ran 36 tests, OK（36/36 通过）** |
| tests/test_task029_integration.py | 独立脚本 `python tests\test_task029_integration.py`（退出码 0/1） | **6/7 PASS**；第 7 项"traffic_events 表存在检查" FAIL：脚本用 `Config.DB_PATH` = `E:\output\1\zhitong_violations.db`（config.py L19 指向项目根），而实际数据库在 `api\zhitong_violations.db`（database.py L7 用 CWD 相对路径）。从 api 目录重跑仍 FAIL（因 Config.DB_PATH 硬编码项目根，与 CWD 无关）。**根因是 config.py 与 database.py 路径定义互相矛盾** |
| tests/test_multi_frame_validator.py | 独立脚本 | **14/14 PASS** |
| tests/test_core.py | 需 `import pytest` | **无法运行**：conda 环境 ModuleNotFoundError: No module named 'pytest'（与 PROJECT_BASELINE §10 P1 记载一致） |

覆盖范围：循环帧缓存、事件状态机（8 状态+转换+冷却+清理）、证据链构建、云端仲裁 mock、多帧验证、实时检测器集成、API 路由注册、DB 表检查。**不覆盖**：真实视频→事件落盘→前端展示链路。

> 测试固有副作用声明：test_task029_integration.py 自身会在项目根写 `_TASK-029-M09_integration_selfcheck.json`（脚本内置行为，非本次审计新增的业务修改）。

### 1.10 当前哪些环节只是源码存在，哪些已实际运行？

| 环节 | 级别 | 说明 |
|---|---|---|
| EventCenter/EventDetail 组件、路由、API 封装 | B | vite build 通过（EventCenter chunk 8.53kB、EventDetail chunk 19.0kB 正常产出） |
| FastAPI 应用、事件路由、/health | C | 实际启动 + HTTP 实测 200/404 |
| traffic_events 表 + to_dict 序列化 | C（结构）/ D（数据）缺失 | 接口可查但 0 条记录；测试中引擎可创建内存事件并同步落库逻辑（单测覆盖） |
| event_videos 落盘 | A | 目录存在、挂载代码存在，**0 个 mp4** |
| 真实视频→检测→事件触发→视频落盘→DB→前端展示 | **E 未达成** | 整条闭环无任何产物（无事件记录、无事件视频） |

### 1.11 真实视频闭环验证需要哪些步骤？

按协议 §3 主线，最小闭环步骤建议（本 TASK 未执行，仅供下一任务参考）：

1. 准备一段固定真实交通视频（当前项目内未发现 event_videos 产物；需确认可用输入源）。
2. 启动后端（conda env，cwd=api，端口 8001），确认 /health overall=ok。
3. 通过 `realtime_detector` 的视频处理入口（或 /api/realtime/start + 视频源切换 `/api/realtime/source`）喂入视频，等待规则引擎触发事件。
4. 验证产物三件套：`traffic_events` 表新增记录（sqlite 查询）；`api/output/event_videos/{YYYYMMDD}/{event_id}.mp4` 落盘；`key_frames` JSON 有路径。
5. `GET /api/realtime/events` 返回 total ≥ 1；`GET /events/{id}/video` 返回 200 + video/mp4。
6. 启动前端（npm run dev），打开 `http://localhost:5173/events`，确认列表渲染、详情页视频可播放、关键帧可显示、人工复核可将状态置为 confirmed/rejected 并回读。
7. 若无真实摄像头/视频触发成功，需先排查 violation_rules 阈值与视频内容匹配度（此为下一任务范围）。

### 1.12 阻塞问题和风险是什么？

阻塞（针对"真实视频闭环验收"目标）：

- **B1 数据零产物**：traffic_events 0 条、event_videos 空。闭环从未在本环境真实跑通过，无法证明可触发。
- **B2 事件类型筛选失效**：前端筛选 UI 无效 + 值域不一致（见 §3.2），数据量增大后影响可用性，但不阻塞闭环本身。

风险（非阻塞但需记录）：

- **R1** config.py 与 database.py 数据库路径定义矛盾（§3.1），任何依赖 Config.DB_PATH 的代码/测试都会指向不存在的文件。
- **R2** 两个启动入口 Python 环境不一致（§3.4），`py -3` 路径未验证，可能因依赖缺失启动失败。
- **R3** YOLO 模型从 `zhitong\training\models\`（已 gitignore）加载，换机器会失效。
- **R4** test_core.py 因 pytest 缺失长期不可运行，测试套件非全绿。

## 2. 前后端一致性总表

| 核对项 | 前端 | 后端 | 一致 |
|---|---|---|---|
| 列表请求参数 | page/size/state/camera_id | 同（realtime.py L847-848） | ✓ |
| 列表响应包裹 | success/data/total | 同（L873-879） | ✓ |
| 详情响应 | res.data（to_dict 全字段） | 同（L957） | ✓ |
| frames 响应 | res.key_frames | 同（L1032-1037） | ✓ |
| review 请求体 | confirmed/reviewer/comment | EventReviewRequest（L1040-1044） | ✓ |
| 8 状态值域 | stateLabelMap | 引擎 8 状态（单测实测同一列表） | ✓ |
| 事件类型值域（展示） | format.js TYPE_MAP 用 illegal_parking | behavior_engine 产生 illegal_parking | ✓ |
| 事件类型值域（筛选） | EventCenter 下拉用 illegal_park | 后端无 event_type 参数 | ✗（§3.2） |
| 视频访问 | {host}:8001/api/realtime/events/{id}/video | FileResponse（L966-1001） | ✓ |
| 静态帧/视频目录 | getEventFrameUrl 拼 {host}:8001/ 路径 | /event-videos 挂载（app.py L146） | ✓（依赖 event_video_path 为绝对路径或可归一化路径） |

## 3. 【发现的额外问题】

1. **数据库路径定义自相矛盾**
   - 文件：`api/config.py` L19 vs `api/database.py` L7
   - 描述：Config.DB_PATH = `E:\output\1\zhitong_violations.db`（项目根，不存在）；database.py 实际用 `sqlite:///./zhitong_violations.db`（CWD 相对，实际落在 api/ 下）。两处各自为政。
   - 是否阻塞本 TASK：否（审计完成）。
   - 建议后续 TASK：统一为单一来源（建议 database.py 引用 Config 或都用 BASE_DIR），并修复 test_task029 第 7 项。

2. **EventCenter 事件类型筛选整体无效**
   - 文件：`web-admin/src/views/EventCenter.vue` L48-56、L353-358；`api/routers/realtime.py` L846-848
   - 描述：下拉值 `illegal_park` 与后端实际值 `illegal_parking` 不一致；且 loadData 未传 event_type，后端也不支持该参数。三重问题叠加使筛选 UI 完全不生效。
   - 是否阻塞本 TASK：否。
   - 建议后续 TASK：前端传参 + 后端支持 event_type 筛选 + 统一值域为 illegal_parking。

3. **traffic_events 表 0 条、event_videos 目录空**
   - 文件/模块：`api/output/event_videos/`、数据库 `api/zhitong_violations.db`
   - 描述：真实视频闭环从未留下任何产物（0 事件、0 视频）。
   - 是否阻塞本 TASK：否；阻塞协议 §3 定义的"首个闭环验收"。
   - 建议后续 TASK：执行 §1.11 的闭环验证任务。

4. **启动入口 Python 环境不统一**
   - 文件：`start-all.bat` L13（`py -3`） vs `api/start_api.bat` L43（conda env zhitong-gpu）
   - 描述：`py -3` 解释器的依赖未验证；start-all.bat 实际能否拉起带 ultralytics/cv2 的后端存疑。
   - 是否阻塞本 TASK：否。
   - 建议后续 TASK：统一启动脚本指向 `C:\miniconda\envs\zhitong-gpu\python.exe`。

5. **conda 环境缺 pytest**
   - 文件/模块：`tests/test_core.py`、conda env zhitong-gpu
   - 描述：test_core.py 无法运行（ModuleNotFoundError）。安装属环境变更，本 TASK 未执行。
   - 是否阻塞本 TASK：否。
   - 建议后续 TASK：向 zhitong-gpu 安装 pytest（需指挥官批准环境变更）后补跑 test_core.py。

6. **review 数据库分支 state_history 的 old_state 记录错误**
   - 文件：`api/routers/realtime.py` L1067-1074
   - 描述：先 `record.state = 新状态`，再写入 `old_state: record.state`，导致 old_state 与 new_state 恒相同（内存分支走引擎无此问题）。
   - 是否阻塞本 TASK：否。
   - 建议后续 TASK：小修（先取旧值再赋新值）。

7. **前端生产构建 chunk 体积警告**
   - 文件：`web-admin/dist`（index-BjtuyMK1.js 1.03MB、index-DBnAmNOF.js 1.19MB）
   - 描述：两个 chunk 超 500kB（element-plus/echarts 未拆分）。仅警告，构建成功。
   - 是否阻塞本 TASK：否。
   - 建议后续 TASK：manualChunks 拆包（低优先级）。

## 4. 本次实际执行的命令与结果汇总

| 命令 | 结果 |
|---|---|
| `python -m unittest tests.test_circular_frame_buffer tests.test_cloud_collaborator_event tests.test_evidence_chain tests.test_traffic_event_engine` | Ran 36 tests, OK |
| `python tests\test_task029_integration.py`（项目根 + api 目录各一次） | 6/7 PASS，EXIT 1（表检查 FAIL，根因 §3.1） |
| `python tests\test_multi_frame_validator.py` | 14/14 PASS，EXIT 0 |
| `python -m uvicorn app:app --host 127.0.0.1 --port 8001`（cwd=api，已停止） | 启动成功 |
| `GET /health` | 200 healthy overall=ok |
| `GET /api/realtime/events?page=1&size=3` | 200，total=0 |
| `GET /api/realtime/events/active` | 200，count=0 |
| `GET /api/realtime/events/nonexistent_id_123` | 404 |
| `GET /event-videos/xxx_not_exist.mp4` | 404 |
| `npm run build`（cwd=web-admin） | 成功，21.91s，EXIT 0 |
| 8001 端口检查/进程停止 | 验证后已停止，端口归还 |

---

【本次任务模型信息】

- 实际使用模型：GLM-5.3-Flash
- 任务复杂度：L3
- 模型选择理由：本任务为跨前后端只读审计，需要追踪 EventCenter→API 封装→FastAPI 路由→SQLAlchemy 模型的字段级一致性，并执行测试/启动/构建验证；属于多文件交叉核对但不含架构设计或大规模实现，L3 足够且未降低所需能力。
- 是否发生模型切换：否
- 切换原因：无（任务在全过程中未遇到能力瓶颈）。
