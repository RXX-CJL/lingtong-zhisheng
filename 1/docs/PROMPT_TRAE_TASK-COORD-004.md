# Trae 执行提示词：TASK-COORD-004

【TASK-COORD-004】

任务名称：真实交通视频最小闭环验证

优先级：P0

复杂度：L4

负责人：Trae IDE

协作者：DSH 仅在核心链路分析受阻时提供只读分析，不得并行修改代码。

并行状态：🔴 P-RED，禁止并行

任务目标：

验证真实视频是否能够完成：

`真实视频 → YOLO → Tracking → TrafficPlugin → TrafficEventEngine → 事件视频 → traffic_events → FastAPI → EventCenter`

视频目录：

`E:\output\1\test_assets\traffic_videos`

当前已有视频：

- `E:\output\1\test_assets\traffic_videos\3a3f1dd6ee318c8a965d85a70e7520bf.mp4`
- `E:\output\1\test_assets\traffic_videos\3e9b3f659e257969d581993be3c9e59e.mp4`
- `E:\output\1\test_assets\traffic_videos\701c5154f47975564a8039bb03bd3340.mp4`
- `E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4`
- `E:\output\1\test_assets\traffic_videos\f640e913639b7beaed028111ee4039ce.mp4`

当前问题：

TASK-COORD-003 已修复生产形态下的车辆参数契约，并通过 46 项相关测试。但项目仍没有真实事件记录和事件视频产物，尚未完成 E 级真实闭环验证。

需要阅读的文件：

- `PROJECT_BASELINE.md`
- `PROJECT_AUDIT_AND_BASELINE_REPORT.md`
- `docs/AI_COORDINATION_PROTOCOL.md`
- `docs/REPORT_TASK-COORD-001_DSH.md`
- `docs/REPORT_TASK-COORD-002_TRAE.md`
- `docs/REPORT_TASK-COORD-003_DSH.md`
- `docs/REPORT_TASK-COORD-003R_TRAE.md`
- `api/realtime_detector.py`
- `api/traffic_event_engine.py`
- `api/circular_frame_buffer.py`
- `api/routers/realtime.py`
- `api/app.py`
- `api/config.py`
- `api/database.py`
- `api/models.py`
- `web-admin/src/views/EventCenter.vue`
- `web-admin/src/views/EventDetail.vue`
- `web-admin/src/api/index.js`

允许修改：

- 默认只允许运行验证，不修改业务代码。
- 可新增 `docs/REPORT_TASK-COORD-004_TRAE.md`。
- 可启动和停止本地后端、前端验证进程。
- 可让验证过程产生真实事件记录和 `event_videos` 产物，但报告必须列出新增数据和文件。

禁止修改：

- 禁止修改核心业务代码、数据库结构、配置、前端、API 路由、启动脚本和模型文件。
- 禁止降低规则阈值、伪造检测结果或用合成数据冒充真实视频验证。
- 禁止删除原有数据库记录或视频文件。
- 禁止覆盖、还原或清理其他 Agent 的未提交改动。
- 禁止执行 `git reset --hard`、`git checkout -- .`、`git clean -fd`。
- 发现其他问题只记录，不得扩大任务范围修复。

前置依赖：

- TASK-COORD-003 已通过验收。
- 当前目录已有 5 个 MP4，但必须先检查每个文件的可读性、时长、分辨率、帧率和画面内容。

执行步骤：

1. 判断任务复杂度。
2. 执行并记录 `git status`、`git branch`、`git log -n 5`，保护现有未提交文件。
3. 逐个检查上述 5 个视频的元信息和可读取性，选择适合验证的样本；如果没有真实交通视频，报告 BLOCKED，不得伪造替代品。
4. 使用已验证可用的 `zhitong-gpu` Python 环境启动后端，确认 `/health` 返回结果。
5. 使用项目已有的视频源和检测接口启动检测，不自行改写业务入口。
6. 记录视频读取、YOLO 检测、tracked vehicles、事件引擎事件数量和 active events。
7. 检查 `traffic_events` 新增记录、真实 MP4、事件详情和视频接口。
8. 启动前端并验证 EventCenter/EventDetail 是否能读取真实事件和视频。
9. 如任一步失败，保存准确命令、响应、日志和截图，停止扩大范围，不立即修改代码。
10. 停止本轮启动的服务，确认端口和进程状态。
11. 检查 Git 状态，确认没有业务代码被修改。
12. 输出完整报告。

验收标准：

必须区分 A/B/C/D/E 证据等级：

- A：代码存在；
- B：代码可运行；
- C：接口实际响应；
- D：真实数据写入并读回；
- E：真实视频到 EventCenter 的完整闭环。

完整 ACCEPT 至少要求：

- 真实视频被读取；
- 实际检测链路触发至少一个事件；
- `traffic_events` 新增至少一条记录；
- `event_videos/*.mp4` 生成真实文件且可读取；
- 事件列表、详情和视频接口返回正确结果；
- EventCenter 和 EventDetail 能展示该事件。

如果只能完成到 C 或 D，状态必须为 PARTIAL；如果没有合适视频，状态必须为 BLOCKED。单元测试和人工构造车辆不能替代真实视频证据。

失败处理：

- 视频不可读、YOLO 无检测、Tracking 无车辆、事件不触发、视频不落盘、数据库无记录或前端不显示时，分别记录准确证据。
- 不得在本任务中调整阈值、改动核心链路或修复数据库路径。
- 发现额外问题，写入“发现的额外问题”，交由后续 TASK 处理。
- 如果当前模型无法可靠分析 L4 核心链路，优先切换到更高能力模型；无法切换时停止扩大范围并报告能力瓶颈。

最终报告要求：

报告文件：`docs/REPORT_TASK-COORD-004_TRAE.md`

必须包含：视频路径和元信息、启动环境、命令、健康检查、检测状态、事件数量、数据库查询、MP4 路径和文件信息、API 响应、前端验证、服务停止结果、Git 状态、截图/日志路径和最终判定 `ACCEPT / PARTIAL / BLOCKED / REJECT`。

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
- 质量、正确性和项目安全优先于成本。
- 禁止为了节省 Token 或额度而降低 L4 任务所需模型能力。
- 本任务涉及 YOLO、Tracking、TrafficEventEngine、数据库、FastAPI 和 EventCenter，属于 L4，应优先使用当前可用的高能力模型。
- 使用完成任务所需要的最低合理模型；高能力模型能明显降低误判和重复验证风险时，允许并鼓励切换。
