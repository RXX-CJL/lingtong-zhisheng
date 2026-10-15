# TASK-COORD-007 执行报告（Trae IDE）

- 任务：实现真实逐帧检测框分析回放（P0）
- 执行日期：2026-09-25
- 执行者：Trae IDE（子代理）
- 最终判定：**ACCEPT**

---

## 1. 结论摘要

新事件已具备"本地 YOLO/Tracking 逐帧识别框"回放能力：事件视频落盘时同步生成 sidecar JSON（`{video_path}.replay.json`），新增 replay 接口下发，前端分析回放模式用 SVG 按视频原始坐标系叠加真实 bbox/track_id，右侧"当前帧车辆"列表随播放联动。旧事件无 sidecar 时诚实降级（不伪造框）。真实视频重跑产出 3 个带 sidecar 的新事件并全链路浏览器验证通过。

## 2. 修改文件与数据流

### 2.1 修改文件（均在授权清单内）

| 文件 | 改动 |
|---|---|
| api/circular_frame_buffer.py | 新增 `extract_event_clip_with_meta()`（返回 (timestamp, frame, meta) 三元组）；`save_event_video` 写循环收集 `written_metas`，落盘前调用新增 `_write_replay_sidecar()` 写 sidecar；全 None 元数据时跳过（诚实降级）；bbox 4 位浮点校验；写失败仅告警不阻断视频保存 |
| api/realtime_detector.py | L574 本地事件链路改调 `extract_event_clip_with_meta`；L603 云端咨询链路保持 `extract_event_clip` 不动 |
| api/routers/realtime.py | 新增 `GET /api/realtime/events/{event_id}/replay`：内存→DB 查 video_path；无视频 404；无 sidecar 返回 200+`success:false, code=no_frame_replay_data`；有则返回完整 sidecar |
| web-admin/src/api/index.js | 新增 `getEventReplay(eventId)`（realtimeRequest 直连后端） |
| web-admin/src/views/EventDetail.vue | 分析回放模式：SVG 叠加层（viewBox=视频原生宽高）、按 currentTime 选取最近帧（rAF 循环 + timeupdate/seeked）、letterbox 坐标对齐（updateVideoRect: contain 缩放 + offset 补偿）、右侧"当前帧车辆"列表（随帧更新、点击选中与 SVG 高亮联动、"本事件"标记）；原始证据模式无任何叠加；无 sidecar 保留 006B 事件级降级徽标 |
| tests/test_replay_sidecar_contract.py（新增） | 7 项回放契约测试 |
| tests/verify_replay_sidecar.py（新增） | 只读验证脚本（DB+视频+sidecar 三方一致性） |
| tests/test_event_media_contract.py | test_04 最小修正：区分"迁移代事件（*_h264.mp4+保留原始 FMP4）"与"原生代事件（原地 H.264 单文件，005 既有契约）"两代约定 |

### 2.2 数据流

```
_buffer_frame(存 timestamp+frame+{detections,tracked_vehicles,scene_config})
  → extract_event_clip_with_meta（保留第三元素，根因修复点）
  → save_event_video（mp4v 临时文件 → ffmpeg H.264 转码）
      → {id}.mp4（H.264）
      → {id}.mp4.replay.json（sidecar：frames[{index,time,vehicles[{track_id,class_name,bbox,speed_px,direction}]}]，source=local_yolo_tracker）
  → traffic_events 入库（同步逻辑未改动）
  → GET /replay → EventDetail SVG 叠加
```

## 3. sidecar 路径规则与接口响应示例

- 路径规则：`{event_video_path}.replay.json`（与视频一一对应）
- 新事件接口 `GET /api/realtime/events/evt_1790347063112_79_64e07b/replay`（HTTP 200）：

```json
{
  "success": true,
  "event_id": "evt_1790347063112_79_64e07b",
  "data": {
    "version": 1, "source": "local_yolo_tracker",
    "video_width": 960, "video_height": 432, "fps": 10, "frame_count": 299,
    "frames": [
      { "index": 0, "time": 0.0, "vehicles": [
        { "track_id": 101, "class_name": "car", "bbox": [463.1, 239.3, 541.6, 308.5], "speed_px": 0.0, "direction": "unknown" }
      ] }
    ]
  }
}
```

- 旧事件 `GET .../evt_1790324873606_20_4ff131/replay`（HTTP 200）：
  `{"success":false,"code":"no_frame_replay_data","message":"该事件无逐帧回放数据（历史事件未采集逐帧检测框）"}`

## 4. 新事件与 sidecar 数据样本

DB 新增 3 事件（均 speeding / pending_ai，视频位于 `api\output\event_videos\20260925\`）：

| event_id | 视频 | sidecar 一致性 |
|---|---|---|
| evt_1790347063112_79_64e07b | h264 299帧 960x432 | frame_count=299 一致；含车辆帧 299/299；去重 track_id 12 个 |
| evt_1790347063112_80_32d423 | h264 299帧 960x432 | frame_count=299 一致；含车辆帧 299/299；去重 track_id 12 个 |
| evt_1790347061580_75_613c3b | h264 299帧 960x432 | frame_count=299 一致；含车辆帧 299/299；去重 track_id 13 个 |

样本（frame[1], time=0.1，事件 79）：

```
track_id=79  class=car bbox=[210.9, 167.7, 265.3, 204.0] speed_px=42.37 dir=up
track_id=97  class=car bbox=[156.4, 205.9, 233.3, 260.9] speed_px=17.45 dir=unknown
track_id=99  class=car bbox=[234.3, 128.3, 274.5, 174.9] speed_px=0.0  dir=unknown
```

磁盘 sidecar 共 9 个：上述 3 个有 DB 行；另 6 个属两轮运行中未被 `_sync_active_events_to_db` 同步的事件（既有 stop 行为，不伪造补录，详见 §9 遗留）。

## 5. 坐标变换与帧同步验证

- sidecar bbox 为视频原生像素坐标；SVG `viewBox="0 0 960 432"` 与视频原生宽高一致，由 `updateVideoRect()` 计算 contain 缩放（`scale=min(ew/vw, eh/vh)`）+ 居中 offset，叠加层绝对定位到视频内容矩形（浏览器窗口与视频尺寸非 1:1 时亦对齐）。
- 帧同步：`idx = round(currentTime * fps)`，rAF 循环 + timeupdate/seeked 双驱动；seek 后立即刷新。
- 视觉验证（截图 t7_new_analysis.png）：ID 101 框贴合公交车、ID 79 · 超速 框贴合轿车、ID 97/104/109/110 框贴合各自车辆，无偏移；侧栏列表 6 条与 SVG 标签 ID 集合一致。

## 6. 浏览器验证结果（browser_use 代理，9/9 PASS）

| # | 验证项 | 结果 |
|---|---|---|
| 1 | 新事件原始证据模式无 SVG 叠加 | PASS |
| 2 | 分析回放 SVG 出现（6 rect，标签 ID 101 / ID 79 · 超速 / ID 104…） | PASS |
| 3 | SVG ID 集合 = 侧栏列表 ID 集合；note"本地 YOLO/Tracking 逐帧识别框 · 帧 167/299 · 云端 AI 结论见下方判定区" | PASS |
| 4 | 随帧更新：帧号 167→218，侧栏条目 6→11 | PASS |
| 5 | 点击侧栏"本事件"（ID 79）联动：条目高亮 + SVG rect selected 红框 | PASS |
| 6 | 切回原始证据：SVG 消失、无降级文案 | PASS |
| 7 | 旧事件分析回放：事件级徽标"ID 20 · 逆行"+ 诚实文案"逐帧检测框数据未采集 · 仅事件级标注"，无 SVG | PASS |
| 8 | console 无 [EventDetail] 回放/视频加载错误 | PASS |
| 9 | 截图落盘确认 | PASS |

截图证据（`C:\Users\ROG\AppData\Local\Temp\trae\screenshots\`）：
`t7_new_analysis.png`、`t7_frame_update.png`、`t7_linkage.png`、`t7_old_degraded.png`

## 7. 测试、构建、Git 状态

- 单元测试：`tests.test_replay_sidecar_contract` 7/7 OK；`tests.test_event_media_contract` 9/9 OK（含 test_04 两代约定修正后）
- 验证脚本：`tests/verify_replay_sidecar.py` 输出 RESULT: PASS（3 事件视频帧数=sidecar frame_count、track_id/bbox 样本齐全）
- 前端构建：`npx vite build` 成功（9.42s，EventDetail-CbL9ozaH.js 26.70 kB）
- Git：HEAD `4a67b5a` 未变动；本任务未做任何 commit/破坏性操作
- 工作区说明：`git diff` 为 TASK-COORD-003/005/006B 累计未提交改动 + 本任务改动；`api/rule_engine/plugins/traffic_plugin.py`（003 产物）、`_TASK-029-M09_integration_selfcheck.json` 等非本任务触碰文件保持原样，未清理他人改动
- 服务：验证完成后前端（5173）与后端（8001）均已停止，端口确认释放（PORTS_RELEASED）

## 8. 红线遵守声明

- 未修改 YOLO/Tracking/TrafficPlugin/TrafficEventEngine 判定逻辑（仅 realtime_detector.py 调用处换用带元数据版本）
- 未伪造/插值已有 7 事件数据；未做 bbox 线性插值
- 未覆盖现有视频与 DB 记录（7 旧事件原样，迁移代 FMP4 原件保留由 test_04 继续守护）
- 未改 DB 结构、未改启动脚本
- 云端 AI 判定区域保持"待 AI 分析"，未冒充

## 9. 遗留与建议（不阻塞本判定）

1. 既有 stop 行为：检测 stop 时未同步的 active 事件不落 DB（本轮 6 个 sidecar 无 DB 行）。建议后续任务将同步逻辑挂到 stop 流程。
2. `tests/test_event_media_contract.py` test_04 已按两代事件约定修正，若指挥官希望原生代事件也保留原始 FMP4，需另行决策并改 save_event_video。
3. 旧事件仅事件级标注（诚实降级），如需旧事件逐帧回放需重新跑检测，属产品决策。

---

## 【本次任务模型信息】

- 模型名称：GLM-5.3-Flash（由运行环境声明，Trae IDE 子代理无法从模型服务端进一步核实）
- 说明：以上为本任务对话进程所用模型标识；如与平台实际调度不符，以平台侧记录为准。
