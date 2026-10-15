# DSH 首轮任务提示词

你是“智瞳灵声”项目的分析与开发 Agent。本轮只做只读审计，不修改任何文件。

项目根目录：`E:\output\1`

请先阅读：

- `PROJECT_BASELINE.md`
- `PROJECT_AUDIT_AND_BASELINE_REPORT.md`
- `docs/AI_COORDINATION_PROTOCOL.md`

任务编号：`TASK-COORD-001`

请沿着这条真实链路检查当前代码，不要依据文档推测：

`视频/摄像头 → YOLO → tracking → 行为规则 → TrafficEventEngine → EvidenceChain → event_videos/*.mp4 → traffic_events → FastAPI`

重点回答：

1. 实际入口文件、关键函数和调用关系是什么？
2. `TrafficEventEngine` 在什么条件下触发事件？
3. 事件视频的生成、保存目录和命名规则是什么？
4. `traffic_events` 表由谁创建和写入？字段是否与 API 一致？
5. 当前有哪些测试能证明链路，哪些环节完全未验证？
6. 若要用真实视频做最小闭环验证，最小启动步骤和所需输入是什么？

输出文件：`docs/REPORT_TASK-COORD-001_DSH.md`。报告必须列出文件路径、函数/类名、证据和阻塞项。禁止修改业务代码、数据库和启动脚本。
