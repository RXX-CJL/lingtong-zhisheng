# TASK-COORD-009B 报告：实时帧率指标与事件回放时间轴前端适配

```text
任务编号：TASK-COORD-009B
执行 Agent：Trae IDE
状态：READY_FOR_REVIEW（PASS）
复杂度：L3
性质：前端实现任务。仅修改 2 个授权文件，未改后端/配置/DB/视频/sidecar/测试/依赖/Git 状态。
      未启动会写入事件数据的服务，未重跑真实视频，未安装依赖。
修改文件：
  web-admin/src/views/AIDetect.vue     采集 FPS / 推理 FPS 分离 + 推理年龄/丢弃 tick/推理耗时（缺失不显示）
  web-admin/src/views/EventDetail.vue  frames[].time 最近邻选帧 + 观测新鲜度透明化 + 媒体时间异常告警
新增文件：本报告（授权产出）
验证：
  1) VS Code 诊断：两文件 0 diagnostic
  2) npx vite build：✓ built in 8.84s（仅既有 chunk 体积告警，与本任务无关）
  3) Node 纯算法断言：20 万随机时刻选帧一致性 + 非均匀轴最近邻 + 新鲜度统计，全部 PASS
```

---

## 0. 结论摘要

- **实时页**：单一含义不清的「FPS」已拆为「采集 FPS / 推理 FPS」，并在后端提供时追加「推理年龄 / 丢弃 tick / 推理耗时」。所有 009A 字段缺失时**不显示虚构数值**（采集 FPS 显示"—（未上报）"，推理 FPS 回退旧字段 `avg_fps` 并明确标注"旧后端·窗口均值"；不回退 008A F5 判定不可用的 `current_fps`）。
- **回放页**：取帧从 `round(currentTime×fps)` 升级为 **`frames[].time` 最近邻查表（二分，无插值）**，旧 sidecar 无 `time` 字段时回退原算法；新增**检测状态更新 X/Y 帧**统计与逐帧「新观测/沿用」标识、`observed_age_sec/stale` 透传展示、源时间仅作诊断；**视频时长与 sidecar 跨度偏差 >10% 显式红色告警并列出两侧时长，不做静默归一化**；源时间跨度与媒体时长偏差 >10% 黄色慢放告警。
- **契约核对**：任务开始时 `docs/REPORT_TASK-COORD-009A_DSH.md` **不存在**；任务执行期间（00:31–00:32 文件时间戳）DSH 后端改动落地于工作区。本报告所有字段名均按**当前后端实际代码**核实，未依据猜测（见 §3）。
- 旧事件无 sidecar 的诚实降级、原始证据模式不叠框两条既有行为**原样保留**，未改动其分支。

---

## 1. 数据流简图（改后）

### 1.1 实时识别页

```
后端 /api/realtime/status（1s 轮询，AIDetect.vue startStatusPolling）
  ├─ capture_fps            → 「采集 FPS」（null → —（未上报））
  ├─ infer_fps              → 「推理 FPS」（null → 回退 avg_fps 并标注"旧后端·窗口均值"）
  ├─ last_infer_age_ms      → 「推理年龄」（≥1s 橙、≥2s 红；字段缺失整项不渲染）
  ├─ dropped_ticks          → 「丢弃 tick」（>0 红色；缺失不渲染）
  ├─ infer_duration_ms      → 「推理耗时 ms」（缺失不渲染）
  └─ total/processed_frames → 总帧数/处理帧数（旧字段，不变）

画面本身仍为后端画框 MJPEG 单流（<img src="/api/realtime/stream">），
前端不画框、不因本任务改变推流路径；画面帧率不由上述任一指标代表。
```

### 1.2 事件回放页

```
video.currentTime（播放器媒体时间，唯一选帧基准）
  └─ rAF(60Hz) / timeupdate / seeked 三路驱动 → syncReplayFrame(t)
       └─ selectFrameIndexByTime(t)
            ├─ 全部 frames 有数值型 time → 二分最近邻（等距取后帧，与旧 round 半程行为一致）
            └─ 否则（旧 sidecar）       → round(t × fps)
                 → currentFrameIndex（响应式）
                      ├─ SVG 框      = frames[idx].vehicles（007 既有，未改）
                      ├─ 右侧车辆列表 = 同一 computed 同源（007 既有）
                      ├─ 新观测/沿用  = 全片预算签名 flags[idx]（009B 新增）
                      ├─ observed_age_sec / stale / source_time = frames[idx]（009B 新增展示）
                      └─ currentMediaTime 同步刷新诊断文本（009B 新增）

loadedmetadata → mediaDuration（播放器实测）
sidecar.media_duration_sec ?? frame_count/fps → sidecarMediaDuration
  ├─ |media-sidecar|/max > 10% → 红色 el-alert（两侧时长 + 偏差%，不归一化）
  └─ source_duration_sec vs media 偏差 > 10% → 黄色慢放告警（v2 sidecar 专属）
```

---

## 2. 实时页：指标分离实现（验收：画面与检测框分别如何更新）

- 008B 已查明：画面与框同源于 MJPEG（后端在最新帧上现场画最近检测结果，≤20Hz 推流、检测节拍 ≤3Hz），因此"画面流畅"不代表推理速率。本任务把该差异在 UI 上**显式分开**。
- 新增 `metrics` computed（[AIDetect.vue](file:///E:/output/1/web-admin/src/views/AIDetect.vue) L429-461）做字段归一化：仅接受 `number && isFinite`，其余一律 null。
- 旧后端兼容矩阵：

| 展示项 | 009A 字段 | 旧后端回退 | 缺失时 |
|---|---|---|---|
| 采集 FPS | `capture_fps` | 无（不虚构） | 显示 —（未上报） |
| 推理 FPS | `infer_fps` | `avg_fps`（FPSMonitor 窗口均值，008A 认定唯一可信旧指标） | —（未上报） |
| 推理年龄 | `last_infer_age_ms` | 无 | 整项 `v-if` 不渲染 |
| 丢弃 tick | `dropped_ticks` | 无 | 整项不渲染 |
| 推理耗时 | `infer_duration_ms` | 无 | 整项不渲染 |

- 移除了两处旧的单一 `current_fps` 展示（视频状态条、检测状态 descriptions）。`current_fps` 仍在响应数据中但前端不再当作帧率权威（008A F5：其基准时间只在 start 时写一次）。
- 阈值（纯展示决策，可复核）：推理年龄 ≥1.0s 橙色、≥2.0s 红色；丢弃 tick>0 红色。

## 3. 009A 契约核对结果（代码实测，非报告转述）

任务开始时 `docs/REPORT_TASK-COORD-009A_DSH.md` 缺失；以下字段均在当前工作区代码中逐一核实：

| 契约 | 实际位置 | 前端使用 |
|---|---|---|
| `/status` 新增 `capture_fps / infer_fps / dropped_ticks / infer_ticks / infer_duration_ms / process_duration_ms / last_infer_age_ms / metrics_window / frame_buffer_span_sec / frame_buffer_source_span_sec / frame_buffer_trimmed / source_fps / source_timebase / capture_pacing_enabled` | [realtime_detector.py](file:///E:/output/1/api/realtime_detector.py) `get_status` L1264-1286；指标类 `CaptureInferMetrics` L47-113（样本不足返回 `null`，不编造） | 采集/推理/年龄/丢弃/耗时 |
| sidecar v2 顶层 `schema_version/source_fps/timebase/source_time_start/end/window_*/media_duration_sec/source_duration_sec` | [circular_frame_buffer.py](file:///E:/output/1/api/circular_frame_buffer.py) L526-548 | 媒体/源时长诊断 |
| 逐帧 `time(媒体时间)/source_time/source_frame_index/captured_at/observed_age_sec/observed_source_age_sec/stale` | 同文件 L507-517 | time 选帧 + 年龄/源时间展示 |
| replay 接口整体透传 sidecar | [realtime.py](file:///E:/output/1/api/routers/realtime.py) L1055-1060 | 无需改 api 封装 |

注意：磁盘上 9 个既有 sidecar 仍是 v1（无 `source_time/observed_age_sec`），这些事件会自动走"无 age/无源时间不显示、按 time 选帧（v1 有合成 time）"路径；慢放告警仅在 v2 产物出现。

## 4. 回放页：选帧、新鲜度与异常提示

### 4.1 时间映射（验收：回放时间如何映射 sidecar 帧）

- `replayFrameTimes` computed：仅当**所有**帧都带数值型 `time` 时启用时间轴，否则整体回退 `round(t×fps)`（[EventDetail.vue](file:///E:/output/1/web-admin/src/views/EventDetail.vue) L626-637, L777-810）。
- 最近邻二分：单调非减 `time` 上找首个 ≥t，比较左右取近；**无插值、无外推**，首尾钳制。
- 均匀轴等价性：20 万个随机时刻与旧 `round(t×10)` 对比，非半程点 0 分歧；半程边界仅存浮点级差异（≤1 帧、等距），实现选后帧以贴合旧行为。
- `source_time` **只**出现在诊断文本（"源时间 x.xxs（仅诊断）"、侧栏"源时间/媒体时间"双列），未传入任何取帧函数。

### 4.2 观测新鲜度（验收：不让静态框看起来像新检测）

- 帧签名 = 排序后的 `track_id@整数bbox` 集合（与 008A/008B 审计 run 口径一致）；`replayObservationStats` 在 sidecar 加载后响应式缓存：`updateCount`=相对前一帧状态真实变化的帧数（首帧计 1）。
- 叠加层与侧栏同步显示「检测状态更新 X/Y 帧（无插值）」；当前帧显示绿点「本帧为新观测」或灰点「本帧沿用上一观测」；v2 有 `observed_age_sec` 时追加"观测于 … 前"，`stale=true` 显示红色"检测已过期"。
- 框、侧栏、新鲜度标识全部由同一 `currentFrameIndex → frames[idx]` 派生，**严格同帧同源**，不存在三者使用不同帧的风险。

### 4.3 媒体时间异常（验收：>10% 明确提示，不掩盖）

- 红色告警：`|video.duration − sidecarMediaDuration| / max(…) > 0.10`，文案列出两侧秒值与偏差百分比，并声明"未做静默归一化"。
- 黄色告警（v2）：`source_duration_sec` 与媒体时长偏差 >10% 时给出回放倍率与源帧率，指明源时间仅诊断。
- 两条告警均仅在「分析回放 + replayReady」时出现；旧事件降级分支不出现。

### 4.4 既有行为保护

- `replayState='unavailable'` 旧事件分支、"逐帧检测框数据未采集 · 仅事件级标注"、原始证据模式无 overlay（`v-if="playMode==='analysis'"`）均未改动。
- rAF 循环、`timeupdate/seeked`、letterbox `updateVideoRect` 逻辑保留；本次仅在 `syncReplayFrame` 内替换选帧算法并同步 `currentMediaTime`，未新增定时器、未改变 1s/60Hz 节奏。

## 5. 前端风险复核（采样/节流/重复渲染/坐标）

| 项 | 结论 |
|---|---|
| 采样/节流 | 无新增。取帧由既有 rAF 驱动；签名统计为加载后一次性 computed，非逐帧重算 |
| 重复渲染 | 无新增重复订阅；状态轮询仍 1s；`currentMediaTime` 每 rAF 写入但仅诊断文本消费 |
| 坐标误差 | 未触碰 SVG viewBox/letterbox 换算（008B 已验证），新鲜度元素不参与坐标 |
| 算法性能 | 二分 O(log n)，300 帧量级 <10 步；实测构建与诊断无告警 |
| 空/坏数据 | 非有限 time/age、缺 bbox、空 frames 全部防御；无 sidecar 走原降级 |

## 6. 需浏览器实测 / DSH 确认项（不在静态可证范围）

1. 浏览器（只打开既有事件，不产生数据）：
   - 009A 新事件产生后，实时页采集/推理 FPS 两个数字都可见且与任务管理器负载直觉一致；推理年龄在检测运行中不为空。
   - v2 sidecar 事件回放：黄色慢放告警出现且倍率与 DSH 实测一致；红色告警在人为制造 duration 偏差时出现（当前 v1 事件 video.duration≈29.9s≈sidecar 跨度，预期**不**出现红色告警）。
   - 播放/拖动时绿点仅在签名变化帧亮起；现有 v1 事件预期全片基本灰点（updateCount=1~3），数字与 008A 表一致。
   - 全屏切换/窗口缩放后 SVG 贴合（沿用 008B 已验证路径，本次未改）。
2. DSH 侧确认：009A 无正式报告，建议补一份契约报告；`stale` 阈值 `_stale_threshold_sec()` 的取值需在报告中声明（前端只如实展示布尔值）。
3. 磁盘旧 v1 sidecar 不会被回填；若需要旧事件也显示观测年龄，属后端任务，前端不再为 v1 推导（避免伪造）。

## 7. 修改文件范围与量化验收

最小文件范围（实际）：
- [AIDetect.vue](file:///E:/output/1/web-admin/src/views/AIDetect.vue)
- [EventDetail.vue](file:///E:/output/1/web-admin/src/views/EventDetail.vue)
- `web-admin/src/api/index.js`：无需修改（`getRealtimeStatus` L246、`getEventReplay` L323 已存在且透传）。
- 前端测试：项目**无测试框架**（package.json 无 test 脚本、无 vitest/jest 配置），未新建测试入口；以 vite build + Node 算法断言替代验证并在此声明。

量化验收清单（建议浏览器逐条勾验）：
1. 旧后端/字段缺失：采集 FPS 显示"—（未上报）"，推理 FPS 显示数值+「旧后端·窗口均值」，年龄/丢弃/耗时三行不出现。
2. 009A 后端：采集 FPS、推理 FPS 均为有限数；停止检测后推理年龄增长并在 ≥1s/≥2s 变色；制造忙时丢弃后 tick 计数红色。
3. v1 既有事件：叠加层显示"检测状态更新 1~3/299 帧"量级，播放全程框/侧栏/标识同帧；无红色时长告警。
4. v2 慢放事件：黄色告警显示源/媒体两侧时长与倍率；逐帧"观测于 x 前"随播放增长，切到新观测帧时归零跳绿。
5. 人为替换 sidecar 使跨度与视频偏差 >10%：红色告警出现并显示两侧秒值；取帧仍按 sidecar time（可从帧计数观察未被拉伸/压缩）。

## 8. 发现的额外问题（只记录，未修改）

- E1：009A 后端在无契约报告情况下落地工作区（文件时间戳 2026-09-26 00:31–00:32），本任务已按实际代码兼容；建议 DSH 补交 `REPORT_TASK-COORD-009A_DSH.md`。
- E2：AIDetect.vue `onBeforeUnmount` 与 `onUnmounted` 重复调用停止/释放（008B E2），本次未在范围内处理，保持原样。
- E3：MJPEG 推流无帧序号去重（008B E3）依旧存在，本任务仅在文字上把"采集"与"推流"概念分开，未改推流。

## 9. 合规声明

- 未修改授权清单外任何文件（git 工作区其余改动为 003/005/007/009A 既有内容，原样保留；HEAD 仍为 4a67b5a，未提交）。
- 未构建部署、未启动后端、未重跑真实视频、未安装依赖、未创建前端测试框架。
- `npx vite build` 产物在 `web-admin/dist`，已被 .gitignore 忽略（git check-ignore 确认）。

## 【本次任务模型信息】

- **实际使用模型**：GLM-5.3-Flash（由运行环境声明，无法从服务端核实实际模型名称）。
- **任务复杂度**：**L3**。
- **模型选择理由**：任务要求在两份未通读的大型 SFC 中，跨"轮询状态 → 多版本字段契约 → 播放器时间轴 → sidecar 双版本 schema → SVG/侧栏同源"做兼容改造，且必须在 009A 报告缺失、后端代码任务期间落地的情况下以实际代码为准核对字段；同时满足不插值、不伪造、不归一化、保护两条降级分支等强约束。按 L3 执行，未为节省成本降低能力。
- **是否发生模型切换**：否。
- **切换原因**：不适用。

---

*报告结束。*
