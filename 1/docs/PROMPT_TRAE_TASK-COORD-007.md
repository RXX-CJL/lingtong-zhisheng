# Trae 执行提示词：TASK-COORD-007

【TASK-COORD-007】

任务名称：实现真实逐帧检测框分析回放

优先级：P0

复杂度：L4

负责人：Trae IDE

协作者：DSH 仅在核心数据链路设计或实现复核出现阻塞时提供只读分析。

并行状态：🔴 P-RED，禁止并行

任务目标：

解决当前 EventDetail 左侧视频仍然没有识别框的问题。

当前根因已经确认：

- 事件视频保存的是原始帧；
- `_buffer_frame` 中曾经存在检测/跟踪数据，但 `extract_event_clip` 提取时丢弃了第三个元数据元素；
- 现有 7 个事件的 `trajectory` 都只有 1 个点，无法恢复逐帧 bbox；
- 006B 只显示事件级徽标，是为了避免伪造逐帧框。

本任务必须让未来新生成的事件具备真实逐帧回放数据，并在前端分析回放模式中显示真实识别框。

注意：

- 识别框和 ID 来自本地 YOLO/Tracking 数据；
- 云端 AI 判定是另一层能力，当前可以继续显示“待 AI 分析”；
- 不得把“本地识别框”冒充“云端 AI 结论”。

需要实现的效果：

```text
┌──────────────────────────────┬────────────────────────┐
│ 视频 + 真实检测框/ID/状态       │ 当前帧车辆信息列表       │
│                                │ ID 2  速度 64.3 km/h   │
│  [ID 2 · 超速]                 │ 类型：轿车              │
│  [ID 10]                       │ 车牌：未识别            │
│                                │ 违规：超速              │
└──────────────────────────────┴────────────────────────┘
```

需要阅读的文件：

- `docs/REPORT_TASK-COORD-006A_DSH.md`
- `docs/REPORT_TASK-COORD-006B_TRAE.md`
- `docs/REPORT_TASK-COORD-005_TRAE.md`
- `api/circular_frame_buffer.py`
- `api/realtime_detector.py`
- `api/traffic_event_engine.py`
- `api/routers/realtime.py`
- `api/models.py`
- `web-admin/src/views/EventDetail.vue`
- `web-admin/src/api/index.js`
- 相关测试文件

允许修改：

- `api/circular_frame_buffer.py`
- `api/realtime_detector.py`
- `api/routers/realtime.py`
- `web-admin/src/views/EventDetail.vue`
- `web-admin/src/api/index.js`
- `tests/` 中直接覆盖回放数据契约和渲染数据的测试
- 可新增回放数据迁移/验证脚本

禁止修改：

- 禁止修改 YOLO 模型、Tracking 算法、TrafficPlugin 和 TrafficEventEngine 的判定逻辑。
- 禁止伪造已有 7 个事件的逐帧数据。
- 禁止用线性插值补出不存在的 bbox、速度或轨迹。
- 禁止覆盖或删除现有原始 MP4、H.264 视频、关键帧和数据库记录。
- 禁止把云端 AI 结果写成已经完成，当前没有有效 AI 结果时继续显示“待 AI 分析”。
- 禁止大规模重构前端或后端。
- 禁止修改数据库结构、数据库路径、启动脚本和无关问题。
- 禁止执行 `git reset --hard`、`git checkout -- .`、`git clean -fd`。
- 禁止清理、覆盖或还原其他 Agent 的未提交改动。
- 发现额外问题只记录，不擅自扩大范围。

前置依赖：

- TASK-COORD-005 已验收通过。
- TASK-COORD-006A 和 TASK-COORD-006B 已完成。
- 当前工作区有多个未提交文件，必须先检查并保护。
- 现有 7 个事件只能作为历史事件级样本；本任务必须通过重新运行真实交通视频生成至少一个带逐帧回放数据的新事件。

推荐的最小回放数据结构：

```json
{
  "success": true,
  "event_id": "evt_...",
  "video_width": 960,
  "video_height": 432,
  "fps": 10,
  "frame_count": 300,
  "frames": [
    {
      "index": 0,
      "time": 0.0,
      "vehicles": [
        {
          "track_id": 20,
          "class_name": "car",
          "bbox": [100, 120, 220, 260],
          "speed_px": 28.4,
          "direction": "right"
        }
      ]
    }
  ]
}
```

可以使用等价结构，但必须满足：

- bbox 来自检测时真实缓冲元数据；
- track_id 来自真实 VehicleTracker；
- 不存在数据时返回空数组，不补造数据；
- 明确记录坐标尺寸和时间/FPS；
- sidecar 文件与事件视频一一对应；
- 进程结束后仍可通过接口读取。

建议新增只读接口：

```text
GET /api/realtime/events/{event_id}/replay
```

没有 sidecar 的旧事件必须返回明确的“无逐帧回放数据”，前端继续显示事件级降级提示。

执行步骤：

1. 判断任务复杂度。
2. 执行并记录 `git status`、`git branch`、`git log -n 5`。
3. 核对 `_buffer_frame` 当前保存的元数据和 `extract_event_clip` 的丢失点。
4. 用最小改动保留事件片段对应的逐帧检测/跟踪元数据，并写出 sidecar JSON。
5. 增加回放接口，返回真实 sidecar 内容；旧事件无 sidecar 时返回明确降级响应。
6. 在 EventDetail 的“分析回放”模式中增加真实 HTML/CSS/SVG 叠加层：
   - 按视频当前播放时间选择最近帧；
   - 按视频实际显示尺寸处理缩放和 letterbox；
   - 绘制真实 bbox、track_id 和简短中文状态；
   - 分析回放模式显示框，原始证据模式不显示框；
   - 右侧车辆列表随当前帧更新；
   - 当前选中车辆高亮，其他车辆保持可读。
7. 中文文字使用前端 DOM/SVG/CSS，不使用 OpenCV `putText` 烧录中文。
8. 使用项目已有真实视频重新运行检测，至少生成一个带 sidecar 的新事件。
9. 启动后端和前端，打开新事件的 EventDetail，确认：
   - 视频正常播放；
   - 分析回放模式确实显示识别框；
   - 框上的 ID 与侧栏 ID 一致；
   - 播放进度变化时框和车辆列表随帧变化；
   - 原始证据模式没有叠加层。
10. 运行相关测试、前端构建和接口验证。
11. 停止服务，检查端口释放和 Git diff。
12. 输出报告。

验收标准：

- 至少一个由真实视频新生成的事件拥有可读取的 replay sidecar。
- sidecar 中至少存在真实 frame、track_id 和 bbox 数据；报告列出来源和样本。
- `/events/{id}/replay` 返回 200 和真实逐帧数据。
- EventDetail 分析回放模式在浏览器中实际显示识别框和 ID。
- 识别框会随视频时间变化；不能只是固定一张事件级框。
- 右侧车辆信息列表来自当前回放帧的真实车辆数据。
- 原始证据模式保持无叠加，原始视频和旧事件不被覆盖。
- 没有 sidecar 的旧事件诚实降级，不显示伪造框。
- 前端构建、相关测试和浏览器验证通过。
- 报告明确区分本地 YOLO/Tracking 结果和云端 AI 判定结果。

如果真实视频重新运行后仍无法生成逐帧数据，任务状态必须为 PARTIAL 或 BLOCKED，报告准确断点，不得用人工构造 JSON 作为成功证据。

失败处理：

- sidecar 写入失败：记录路径、权限和异常，不改变数据库结构。
- bbox 坐标与视频显示错位：记录视频原始尺寸、显示尺寸、缩放和偏移，修复坐标变换。
- 只有单帧框：不能宣称逐帧回放完成，应报告实际 frame 数。
- 云端 AI 仍为 pending：不阻塞本地识别框验收，但必须在报告中明确。
- 发现速度单位、车牌识别或事件状态问题，只记录为额外问题。
- 如果当前模型无法可靠完成 L4 跨模块修改，优先切换到更高能力模型；无法切换时停止扩大修改并报告能力瓶颈。

最终报告要求：

报告文件：`docs/REPORT_TASK-COORD-007_TRAE.md`

必须包含：

- 修改文件和数据流变化；
- sidecar 的实际路径和响应示例；
- 新生成事件 ID；
- 实际 frame 数、track_id 数量和 bbox 样本；
- 视频尺寸、显示尺寸和坐标变换验证；
- 浏览器截图或 DOM/播放验证证据；
- 原始事件文件保留证据；
- 测试、构建和 Git 状态；
- 最终判定：`ACCEPT / PARTIAL / BLOCKED / REJECT`。

报告末尾必须包含：

【本次任务模型信息】

- 实际使用模型：
- 任务复杂度：L1 / L2 / L3 / L4
- 模型选择理由：
- 是否发生模型切换：
- 切换原因：

不得猜测模型名称。无法可靠读取时填写：“当前环境无法可靠读取实际模型名称。”

模型选择规则：

- 你拥有当前任务的模型自主选择权。
- 任务质量、代码正确性、项目安全性和运行验证能力优先于成本。
- 禁止为了节省 Token 或额度而降低 L4 任务所需的模型能力。
- 本任务涉及核心检测元数据持久化、回放接口、视频坐标变换和 EventDetail，属于 L4，应优先使用当前可用的高能力模型。
- 使用完成任务所需的最低合理模型；高能力模型能明显降低跨模块数据丢失和画框错位风险时，允许并鼓励切换。
