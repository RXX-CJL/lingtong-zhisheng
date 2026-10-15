# Trae 首轮任务提示词

你是“智瞳灵声”项目的工程执行 Agent。本轮只做只读审计，不修改任何文件。

项目根目录：`E:\output\1`

请先阅读：

- `PROJECT_BASELINE.md`
- `PROJECT_AUDIT_AND_BASELINE_REPORT.md`
- `docs/AI_COORDINATION_PROTOCOL.md`

任务编号：`TASK-COORD-002`

请核对管理端和后端接口的真实状态，重点检查：

1. `web-admin/` 的启动命令、构建命令和 EventCenter 页面入口；
2. EventCenter 调用了哪些 API，字段是否对应 `traffic_events` 或其他实际表；
3. FastAPI 的路由注册、事件查询接口、静态视频访问接口；
4. 当前 tests 的运行入口、通过/失败情况和未覆盖的闭环环节；
5. 启动后端、前端并进行最小健康检查需要哪些命令；
6. 真实视频闭环验证需要前端配合还是可直接通过后端/脚本完成。

只允许执行安全的读取、测试发现和不改变业务状态的检查。不得新增上传功能、修改 Vue、迁移数据库或改启动脚本。

输出文件：`docs/REPORT_TASK-COORD-002_TRAE.md`。报告必须列出实际文件路径、命令、结果、截图/日志位置（如有）和阻塞项。
