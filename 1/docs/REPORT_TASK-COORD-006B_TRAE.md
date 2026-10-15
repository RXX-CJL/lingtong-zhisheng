# TASK-COORD-006B 报告：事件分析回放与中文车辆信息侧栏

```text
任务编号：TASK-COORD-006B
执行 Agent：Trae IDE
状态：PASS
复杂度：L4
前置依赖：TASK-COORD-006A（DSH 数据契约审计，已遵循）/ TASK-COORD-005（已验收）
Git 分支：main
修改文件：web-admin/src/views/EventDetail.vue（唯一改动文件）
未修改：web-admin/src/api/index.js（现有封装已齐备）、web-admin/src/utils/format.js（按授权约束未动）
验证事件：evt_1790324873606_20_4ff131（wrong_way 逆行）+ evt_1790324876514_39_ee9ac0（speeding 超速）
```

---

## 1. UI 结构和修改文件

### 布局（右侧栏重排，车辆面板置顶与视频联动）

```text
┌──────────────────────────────┬────────────────────────┐
│ 事件视频 [原始证据|分析回放]   │ 车辆信息  [已选中 ID 20] │
│  ┌────────────────────────┐ │ ┌────────────────────┐ │
│  │ ID 20 · 逆行（徽标）     │ │ │ ID 20      [逆行]   │ │
│  │                        │ │ │ 类型 轿车  速度 未采集│ │
│  │      H.264 视频         │ │ │ 车牌 未识别 方向 向右│ │
│  │                        │ │ │ 违规 逆行  置信度 90%│ │
│  │ 逐帧检测框数据未采集...   │ │ │ 状态 [待AI分析]     │ │
│  └────────────────────────┘ │ │ 像素速度: 29.6 px/s │ │
│ 关键帧画廊（3 张真实 JPG）     │ └────────────────────┘ │
│ 证据链时间线                  │ 事件信息 / 场景上下文      │
│                              │ AI 判定与人工复核（分区） │
│                              │ 本地规则判断 / 人工复核    │
└──────────────────────────────┴────────────────────────┘
```

### 具体改动（均在 `web-admin/src/views/EventDetail.vue`）

| 区块 | 改动内容 |
|---|---|
| 视频卡 header | 新增 `el-radio-group` 模式切换：`原始证据` / `分析回放`（`playMode` ref，默认 original） |
| 视频叠加层 | 分析回放模式下显示左上角事件级徽标 `ID xx · 违规中文`（左边框色 = 违规类型色，复用 `getTypeColor`）+ 左下角提示"逐帧检测框数据未采集 · 仅事件级标注"；`pointer-events: none` 不拦截视频控制条 |
| 车辆信息面板 | 从右栏第 2 位移至首位（与视频并排）；重构为可点击 `vehicle-item`：类型/速度/车牌/方向/违规/置信度/状态 7 字段 + 像素速度备注；选中态蓝框+浅蓝底+右上角"已选中 ID xx"标签 |
| 事件信息卡 | "AI 置信度"行改用 `aiConfidenceText` computed（0/缺失 → "待 AI 分析"，不再显示 `-`） |
| AI 卡 | 标题改为"AI 判定与人工复核"；新增 `ai-status-grid` 三格摘要：AI 判定 / AI 置信度 / 人工复核状态；`hasAiTrace` 做空对象判定，修复 `{}` truthy 渲染空面板问题；空状态文案"待 AI 分析" |
| 脚本 | 内联 `CLASS_CN`（7 类）/ `DIRECTION_CN`（5 向）/ `EXTRA_TYPE_CN`（4 个别名兜底）常量；新增 `playMode`/`selectedVehicleId` ref 与 `violationCN`/`vehicleClassCN`/`directionCN`/`realSpeedKmh`/`realSpeedText`/`pixelSpeedText`/`plateText`/`ruleConfidenceText`/`eventVehicle`/`selectedVehicle`/`hasAiTrace`/`aiVerdictText`/`aiConfidenceText` computed 与 `handleSelectVehicle` 方法 |
| 清理 | 删除已无人引用的 `getPlateColorClass`/`getPlateColorText` 及车牌色 CSS（plate_color 键在生产数据中不存在）；`formatConfidence` 保留（aiConfidenceText 复用） |
| 样式 | 新增 `.video-overlay`/`.overlay-badge`/`.overlay-note`/`.vehicle-panel`/`.vehicle-item`/`.ai-status-grid`/`.video-header-actions` |

`web-admin/src/api/index.js` 未改动：`getEventDetail`/`getEventFrames`/`getEventVideoUrl`/`getEventFrameUrl` 现有封装已满足全部数据需求。

## 2. 中文字段映射

| 字段 | 数据源（权威路径） | 映射方式 |
|---|---|---|
| 车辆类型 | `vehicle_info.class_name` | 内联 `CLASS_CN`：car→轿车、motorcycle→摩托车、truck→卡车、bus→公交车、bicycle→自行车、person→行人、unknown→未知 |
| 违规名称 | `detail.event_type` | 优先 `utils/format.js` `TYPE_MAP`（wrong_way→逆行、speeding→超速 等），未命中再走内联 `EXTRA_TYPE_CN`（illegal_park→违规停车、lane_departure→压线行驶、running_yellow→抢黄灯、illegal_turn→违规掉头），最后原样返回 |
| 行驶方向 | `vehicle_info.direction` | 内联 `DIRECTION_CN`：right→向右、left→向左、up→向上、down→向下、unknown→未知 |
| 车牌 | `vehicle_info.plate_number` | 空串 → "未识别"（7/7 事件实测为空） |
| 事件状态 | `detail.state` | 沿用既有 `stateLabelMap` 8 态中文 |
| AI 判定 | `ai_judgment` / `ai_confidence` | 空对象 `{}` 或置信度 ≤0 → "待 AI 分析" |

## 3. 真实数据与降级数据边界

| 展示项 | 级别 | 说明 |
|---|---|---|
| 原始证据视频 | **真实（L-C）** | H.264 副本（TASK-COORD-005 转码），接口 `GET /events/{id}/video`，浏览器实测可播 |
| 关键帧 3 张 | **真实（L-C）** | 真实 JPG 路径（TASK-COORD-005 修复） |
| ID / 类型 / 方向 / 违规 / 置信度 | **真实（L-C，事件级）** | `track_id`、`class_name`、`direction`、`event_type`、`rule_judgment.confidence` |
| 速度 km/h | **真实（L-C，事件级）** | 权威值 `rule_judgment.evidence.real_speed_kmh`；**仅 speeding 事件有该字段**（实测 evt_..._39_ee9ac0 = 64.28 → 显示 64.3 km/h）；wrong_way 事件无此字段 → 诚实显示"未采集"，**绝不把 px/s 标为 km/h** |
| 像素速度 | **真实（L-C，事件级）** | `vehicle_info.speed`，以"像素速度（非 km/h，仅供排查）"小字备注展示 |
| 视频叠加徽标 | **真实（事件级）** | 仅 ID + 违规中文；**无检测框**——`vehicle_info.bbox` 只是触发时刻单帧框，逐帧 bbox 从未持久化且不可恢复，画框即伪造 |
| 车牌颜色/车牌置信度/车辆置信度 | **未具备** | `vehicle_info` 中键不存在，已移除对应展示行（原先恒显示"未知/-"） |
| 逐帧轨迹/逐帧回放 | **未具备** | `trajectory` 恒为 1 点，轨迹图维持 `length>1` 才渲染（本来就不渲染）；叠加层显式提示"逐帧检测框数据未采集 · 仅事件级标注" |
| AI 判定/解释/ai_trace | **未具备（7/7 待分析）** | `ai_judgment={}`、`ai_explanation=null`、`state=pending_ai` → 三分区均显示"待 AI 分析" |

## 4. 现有事件验证截图/浏览器证据

验证环境：后端 `uvicorn app:app --port 8001`（/health → healthy），前端 `vite --port 5173`，Edge 浏览器自动化（browser_use 代理）。

**验证 1：evt_1790324873606_20_4ff131（wrong_way 逆行，置信度 0.90）**

DOM 断言（browser_evaluate 返回）：

```json
{"hasOriginal":true,"hasAnalysis":true,"vehicleCardText":"车辆信息","aiCardText":"AI 判定与人工复核","hasVideo":true,"videoSrc":"http://127.0.0.1:8001/api/realtime/events/evt_1790324873606_20_4ff131/video"}
```

截图证据（均已目视确认）：

- `eventdetail_original.png`（原始证据模式）：右栏车辆面板置顶，字段=类型 轿车 / 速度 未采集 / 车牌 未识别 / 方向 向右 / 违规 逆行 / 置信度 90% / 状态 待AI分析；像素速度 29.6 px/s；选中高亮+"已选中 ID 20"标签；视频正常出图。
- `eventdetail_analysis.png`（分析回放模式）：视频左上角徽标"ID 20 · 逆行"（紫色左边框 = wrong_way 色），左下角"逐帧检测框数据未采集 · 仅事件级标注"；无检测框。
- `eventdetail_selected.png`：点击车辆后选中态保持（蓝框高亮），面板与叠加层联动。

截图文件位于 `C:\Users\ROG\AppData\Local\Temp\trae\screenshots\`（浏览器沙箱路径，未写入仓库）。

**验证 2：evt_1790324876514_39_ee9ac0（speeding 超速）** —— 用于确认 km/h 权威速度路径

`.vehicle-field` 文本数组（browser_evaluate 实取）：

```json
["类型轿车","速度64.3 km/h","车牌未识别","方向未知","违规超速","置信度56%","状态待AI分析"]
```

截图 `eventdetail_speeding.png` 已存。速度 64.3 km/h 与接口 `rule_judgment.evidence.real_speed_kmh=64.28` 一致；方向 `unknown` → "未知"正确降级。

**验收标准对照**：

| # | 标准 | 结果 |
|---|---|---|
| 1 | 视频区域 + 右侧车辆信息面板 | ✅ 面板置顶右栏，与视频并排 |
| 2 | 画面文字明显减少 | ✅ 原始证据模式零叠加；分析模式仅 1 徽标 + 1 提示；删除 3 个不存在键的恒空行 |
| 3 | 中文字段正常显示 | ✅ ID/类型/速度/车牌/违规/置信度/状态 全中文（见验证 1/2 实测文本） |
| 4 | 点击车辆高亮反馈 | ✅ 事件级选中态（蓝框+"已选中"标签+叠加层联动）；未伪造逐帧框 |
| 5 | 原始证据视频仍可播放 | ✅ H.264 正常出图；媒体契约测试 9/9 绿 |
| 6 | AI 判定/置信度/解释/人工复核单独显示 | ✅ "AI 判定与人工复核"卡内三格摘要分区 |
| 7 | 至少 1 个真实事件非空验证 | ✅ 2 个真实事件（wrong_way + speeding） |
| 8 | 构建通过 + 报告区分数据边界 | ✅ 见 §3 与 §5 |

## 5. 测试和构建结果

| 项 | 命令 | 结果 |
|---|---|---|
| 前端构建 | `npx vite build`（cwd=web-admin） | ✅ 8.85s 成功；EventDetail chunk 22.83 kB；仅既有 chunk 体积警告 |
| 事件媒体契约（验收⑤守护） | `python -m unittest tests.test_event_media_contract -v`（cwd=E:\output\1） | ✅ Ran 9 tests，OK |
| 后端健康 | `curl http://127.0.0.1:8001/health` | ✅ `{"status":"healthy","overall":"ok"}` |
| 浏览器 DOM 断言 | 见 §4 | ✅ 全部通过 |

## 6. Git 状态与 diff 范围

```text
分支：main
本任务改动（git diff --stat 中归属本任务的唯一条目）：
  web-admin/src/views/EventDetail.vue | 477 +++++++++++++++++++++-------
既有未提交改动（005/DSH 遗留，保持原样未触碰）：
  api/circular_frame_buffer.py / api/realtime_detector.py /
  api/rule_engine/plugins/traffic_plugin.py / api/zhitong_violations.db /
  _TASK-029-M09_integration_selfcheck.json + 未跟踪 docs/tests/api/output 等
```

授权范围内：仅改了 `EventDetail.vue`；未改 `api/index.js`、`utils/format.js`；未触碰后端判定逻辑、原始证据视频、DB、AI 状态；未执行任何 git 还原/清理命令。

## 7. 尚未实现的逐帧能力（缺口声明）

1. **逐帧检测框回放**：7 个既有事件的逐帧 bbox/track 序列从未持久化（`extract_event_clip` 丢弃缓冲帧第 3 元素，进程退出即丢失），**不可恢复**。本任务按 DSH 方案 A 做事件级面板，叠加层已显式标注原因。未来事件需按 006A §5 建议落盘 sidecar + 新增只读 `/events/{id}/replay` 接口。
2. **轨迹折线/逐帧位置**：`trajectory` 恒 1 点，无法驱动任何轨迹可视化；需事件生成时持久化 `VehicleTracker.history`。
3. **AI 分析内容**：7/7 事件 `state=pending_ai`、`ai_judgment={}`，AI 面板当前只能显示"待 AI 分析"三格摘要；待云端 AI 链路跑通后自动充实。
4. **多车辆事件**：当前数据模型为单车辆（事件级 `track_id`），面板按单车辆渲染；`selectedVehicleId` 机制已预留多车辆扩展。

## 8. 发现额外问题（只记录，未扩大修复）

| 文件/位置 | 现象 | 是否阻塞本任务 | 建议 |
|---|---|---|---|
| api/evidence_chain.py:139-152 | 读 `traffic_light`/`stop_line` 键，生产写 `traffic_light_state`/`stop_line_y`，即使 EvidenceChain 可构造也恒 unknown | 否（本任务不依赖 evidence_chain） | 后续 TASK 统一键名 |
| traffic_events.evidence_chain 列 | 7/7 为 NULL，仅内存活跃事件才临时拼装 | 否 | 后续 TASK 落盘 |
| tests/ 环境 | pytest 未安装（沿用 unittest） | 否 | 指挥官决策是否固化依赖 |
| EventDetail 视频在窄窗口 | 右栏宽度 10/24 下字段两列网格在极窄时可能换行 | 否 | 后续响应式优化 |

---

【本次任务模型信息】

- 实际使用模型：当前环境无法可靠读取实际模型名称。
- 任务复杂度：L4
- 模型选择理由：任务涉及跨前后端字段契约、真实事件数据边界判断与 UI 重构，按任务书规则使用当前会话默认高能力模型完成。
- 是否发生模型切换：否（本次会话内未发生可感知的模型切换）
- 切换原因：无
