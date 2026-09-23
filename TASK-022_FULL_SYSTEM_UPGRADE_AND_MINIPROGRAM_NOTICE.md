# TASK-022 长时任务包：torch+CUDA、实时监控修复、数字孪生升级、小程序骨架、CARLA接入

> **指挥官交接说明**：用户已休息，执行者全权自主决策，无需等待用户同意即可执行任何操作（含高危操作如 pip/npm install、重启服务、删除自建文件等）。本任务包为长时任务，预计跨越多个工作周期。遇到阻塞可自主切换到其他子任务，不要卡住等待。

---

## 0. 协作规则（必读）

1. **Git 优先复用**：每个子任务开工前，先用 `gh-cli` Skill + GitHub MCP 搜索 GitHub 上是否有成熟的相关代码/框架/配置，合适则稍加修改直接用，禁止从零造轮子。在 `_OUTPUT.json` 的 `deviations` 字段记录查了哪些仓库、用了哪些、为什么没用。
2. **禁止降级方案**：遇到问题必须找更好的方法或报告指挥官，不允许换低质量方案。
3. **真实浏览器验证**：所有前端修复必须用 Chrome DevTools MCP 在用户真实 Chrome 环境验证，截图为证，**截图完整绝对路径必须报指挥官**（用户要查看）。
4. **能力报告单更新**：开工第一件事是更新 `e:\output\executor_capability_report.md`，补全所有 MCP 工具明细（Chrome DevTools 的 navigate_page/take_screenshot/click/evaluate_script 等，GitHub/Cloudflare/Tencent Docs 三个 MCP 服务器的工具列表）。
5. **自主决策权**：用户已休息，执行者可自主决定任务顺序、自主切换子任务、自主执行高危操作，无需请示。遇到无法解决的阻塞，写入 ERROR 文件并切换其他子任务。
6. **VPN 状态**：已开启。
7. **项目根目录**：`e:\output\1`
8. **结果输出**：每个子任务完成后写 `_TASK-022-MXX_OUTPUT.json`，失败写 `_TASK-022-MXX_ERROR.json`，路径 `e:\output\`。
9. **交接文档**：开工前必读 `e:\output\TASK-021_HANDOVER_FOR_EXECUTOR.md` 了解之前的问题和改动。

---

## 1. 任务清单

### 后台并行任务（不阻塞主线）

#### B1: 下载 CARLA 仿真软件（后台运行）
- **优先级**：低（下载完才接 M7）
- **操作**：
  1. 用 WebSearch 查 CARLA 最新 Windows release（GitHub releases）
  2. 用 RunCommand 后台下载 CARLA 压缩包（约 20GB）
  3. 用 CheckCommandStatus 监控下载进度，不要阻塞主线
  4. 下载完成后解压到 `e:\output\1\carla\`
- **必须 MCP/Skill**：RunCommand + WebSearch + CheckCommandStatus + gh-cli Skill

---

### 主线任务

#### M1: 更新能力报告单
- **优先级**：高（开工第一件事）
- **操作**：
  1. 读取 `e:\output\executor_capability_report.md`
  2. 用 LS 列出 `c:\Users\ROG\.trae-cn\mcps\s_output-17d1e943\solo_agent_lite\` 下所有 MCP 服务器目录
  3. 用 Read 读每个 MCP 服务器的工具 JSON 描述文件
  4. 补全报告单中缺失的 MCP 工具明细：
     - Chrome DevTools：navigate_page, take_screenshot, take_snapshot, click, evaluate_script, list_console_messages, list_network_requests, fill, fill_form, hover, press_key, wait_for, resize_page 等
     - GitHub：add_comment_to_pending_review, create_branch, create_pull_request, get_file_contents, list_issues, search_code, search_repositories 等
     - Cloudflare：docs, search, execute
     - Tencent Docs：所有 doc./slide./sheet./smartsheet. 工具
  5. 更新 Skill 清单（参考 `<available_skills>`）
  6. 在报告单末尾加"Git 复用能力"章节，说明如何用 gh-cli + GitHub MCP 查找复用代码
- **必须 MCP/Skill**：Read + Write + LS

#### M2: 安装 CUDA 版 torch（RTX 4060 适用）
- **优先级**：高（M3 依赖此任务）
- **背景**：当前 `yolo_available: false`，根因是 `ModuleNotFoundError: No module named 'torch'`，ultralytics 已装但 torch 缺失。
- **操作**：
  1. 用 WebSearch 查 PyTorch 官网最新 CUDA 版本安装命令（RTX 4060 支持 CUDA 11.8/12.1）
  2. 用 gh-cli Skill 查 pytorch/pytorch 仓库的 release 说明
  3. 用 RunCommand 执行安装（在 `e:\output\1\.venv` 虚拟环境中）：
     - 建议命令：`py -3 -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`
  4. 验证：`py -3 -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"`
  5. 验证：`py -3 -c "from ultralytics import YOLO; print('OK')"`
  6. 重启后端服务（lan-start.bat），访问 `http://127.0.0.1:8001/health`，确认 `yolo_available: true`
- **必须 MCP/Skill**：RunCommand + WebSearch + gh-cli Skill
- **验收标准**：`/health` 返回 `yolo_available: true`，`torch.cuda.is_available()` 返回 `True`，设备名包含 "RTX 4060"

#### M3: 修复管理端实时监控画面 + YOLO 识别框
- **优先级**：高
- **背景**：见交接文档。之前改过 3 个文件（realtime.py / realtime_detector.py / RealTimeMonitor.vue），中间状态曾出现画面但无识别框，完全改完反而没画面。
- **目标**：像 blind_yun 那样显示 AI 处理过的画面（带 YOLO 识别框、违规标注、FPS）。
- **操作**：
  1. 读交接文档 `TASK-021_HANDOVER_FOR_EXECUTOR.md` 了解之前的改动和问题
  2. 读当前代码：`e:\output\1\api\routers\realtime.py`、`e:\output\1\api\realtime_detector.py`、`e:\output\1\web-admin\src\views\RealTimeMonitor.vue`、`e:\output\1\web-admin\src\api\index.js`
  3. 用 gh-cli Skill 搜 GitHub 上 "vue3 webcam yolo realtime" 或 "fastapi opencv stream vue" 参考实现
  4. 确保 torch 装好后（M2 完成），YOLO 模型能正常加载
  5. 修复画面显示问题（当前用户看不到画面）
  6. 确保 YOLO 识别框叠加在画面上
  7. 用 Chrome DevTools MCP 真实浏览器验证：
     - navigate_page 到 `http://localhost:5173/realtime`
     - take_snapshot 查看 DOM
     - click "开始检测" 按钮
     - wait_for 等待 5 秒
     - take_screenshot 截图
     - **截图路径必须报指挥官**
  8. list_console_messages 检查无报错
- **必须 MCP/Skill**：Chrome DevTools MCP（navigate_page/take_screenshot/take_snapshot/click/evaluate_script/wait_for/list_console_messages）+ systematic-debugging Skill + gh-cli Skill + frontend-design Skill
- **验收标准**：
  1. Chrome DevTools 截图中能看到摄像头真实画面
  2. 画面上有 YOLO 识别框（绿色矩形+类别文字+置信度）
  3. 有 FPS 显示
  4. 截图完整路径已报告

#### M4: 修复数字孪生屏闪/连接不稳定
- **优先级**：中
- **操作**：
  1. 读 `e:\output\1\digital_twin\app.py` 和前端代码
  2. 用 Chrome DevTools MCP 打开数字孪生页面
  3. list_console_messages 查看 WebSocket 报错
  4. list_network_requests 查看重连情况
  5. 修复 WebSocket 重连逻辑、渲染优化
  6. take_screenshot 截图验证
- **必须 MCP/Skill**：Chrome DevTools MCP + systematic-debugging Skill
- **验收标准**：连续观察 30 秒无屏闪，WebSocket 稳定连接

#### M5: 数字孪生 4 场景演示（加分项，优先级低）
- **优先级**：低（加分项，时间不够可跳过）
- **目标**：数字孪生能演示 4 种违规场景，每个场景都有完整闭环。
- **场景规范**：

| 场景 | 触发条件 | 视觉效果 | 数据联动 |
|------|---------|---------|---------|
| 1. 逆行 | 一辆车逆方向行驶 | 车顶红色旋转跟随箭头 + 车牌号浮标 | 仪表盘"今日逆行数 +1" |
| 2. 未戴头盔 | 电动车驾驶员无头盔 | 同上 | 仪表盘"今日未戴头盔 +1" |
| 3. 闯红灯 | 红灯期间车辆越过停止线 | 同上 | 仪表盘"今日闯红灯 +1" |
| 4. 违规停车 | 车辆停在禁停区域 | 同上 | 仪表盘"今日违停 +1" |

- **其他车辆/行人**：正常行驶，不穿模，遵守红绿灯（红灯停、绿灯行）
- **道路规范**：
  - 严格按中国十字路口画（右行规则）
  - 4 个方向进口道，每个方向有左转、直行、右转车道
  - 斑马线、停止线、车道分隔线齐全
  - 红绿灯有数字倒计时（红/绿/黄都要有数字）
  - 红绿灯逻辑联动（南北绿 ↔ 东西红，黄灯过渡 3 秒）
- **技术要求**：
  - 用 Three.js（现有技术栈）
  - 红色箭头要旋转动画 + 跟随车辆移动
  - 车牌号用 sprite 或 HTML overlay 跟随
  - Git 优先：先搜 GitHub 上 "three.js traffic intersection"、"CARLA traffic simulation web"、"three.js vehicle tracking arrow" 等参考
- **操作**：
  1. 用 gh-cli Skill 搜 GitHub 参考项目
  2. 读现有数字孪生代码
  3. 重构 3D 场景（中国十字路口）
  4. 实现红绿灯倒计时+逻辑联动
  5. 实现 4 种违规场景
  6. 实现红色旋转跟随箭头
  7. 实现仪表盘数据联动
  8. 用 Chrome DevTools MCP 验证每个场景并截图
- **必须 MCP/Skill**：frontend-design Skill + SearchCodebase + gh-cli Skill + Chrome DevTools MCP + dynamic-ui Skill
- **验收标准**：4 个场景都能演示，红色箭头旋转跟随，仪表盘数据更新，截图为证

#### M6: 管理端 API Key 自动填充
- **优先级**：中
- **操作**：
  1. 读 `e:\output\1\web-admin\src\views\` 下管理端页面
  2. 用 SearchCodebase 查找 API Key 输入相关代码
  3. 实现自动填充：首次配置后保存到 localStorage，下次自动带出
  4. 用 Chrome DevTools MCP 验证
- **必须 MCP/Skill**：SearchCodebase + Read + Edit + Chrome DevTools MCP
- **验收标准**：API Key 配置一次后刷新页面自动带出

#### M7: 微信小程序开发（核心任务，优先级高）
- **优先级**：高（仅次于 M1/M2/M3）
- **目标**：搭建微信小程序完整骨架，实现"上传照片/视频举报 + 收到违规通知 + 申诉提交"功能。做不了的（需要用户操作的）写成详细用户操作清单。
- **用户最终目的**：
  1. 小程序能上传照片和视频举报他人违规
  2. 能收到自己车辆违规的通知
  3. 要和管理端的申诉接通
- **执行者能做的**：
  1. 用 gh-cli Skill 搜 GitHub 上 "wechat miniprogram traffic violation" 或 "微信小程序 交通违法举报" 参考项目
  2. 在 `e:\output\1\miniprogram\` 下搭建小程序骨架：
     - `pages/` 首页、举报页、通知页、申诉页、我的
     - `components/` 可复用组件
     - `utils/` 工具函数（API 请求封装、上传封装）
     - `app.js` / `app.json` / `app.wxss`
     - `project.config.json`
  3. 实现页面和逻辑：
     - 首页：违规统计、快捷举报入口、最新通知
     - 举报页：拍照/录像/相册上传、位置选择、违规类型选择、提交
     - 通知页：违规通知列表、详情查看
     - 申诉页：针对违规通知提交申诉（上传证据、填写理由）
     - 我的：个人信息、我的举报、我的违规、我的申诉
  4. 对接后端 API：
     - 用 `e:\output\1\api\routers\` 下现有接口
     - 举报：`/api/report` 相关接口
     - 通知：`/api/notifications` 相关接口
     - 申诉：`/api/appeals` 相关接口
     - 如果后端接口不全，自主补充后端接口
  5. UI 设计：
     - 用 frontend-design Skill 设计符合微信小程序规范的 UI
     - 参考 GitHub 上成熟的小程序 UI 模板
  6. 写详细用户操作清单（执行者做不了的部分）：
     - 如何注册微信小程序（获取 AppID/AppSecret）
     - 如何在小程序后台配置 request 合法域名
     - 如何配置服务器域名备案
     - 如何上传代码到微信开发者工具
     - 如何提交审核
- **做不了、必须用户操作的**：
  - 注册小程序账号（获取 AppID/AppSecret）
  - 配置合法域名
  - 域名备案
  - 提交审核
- **必须 MCP/Skill**：gh-cli Skill + frontend-design Skill + SearchCodebase + Read + Write + Edit + WebSearch
- **验收标准**：
  1. 小程序骨架完整，所有页面可跳转
  2. 举报/通知/申诉功能逻辑完整（可用 mock 数据演示）
  3. 后端 API 对接完成（接口不全则自主补充）
  4. 用户操作清单详细清晰
  5. 用 Chrome DevTools MCP 在微信开发者工具的 web 预览中截图验证（如果可能）

#### M8: CARLA 接入系统（B1 完成后）
- **优先级**：低（依赖 B1 下载完成）
- **操作**：
  1. 等 B1 下载完成
  2. 用 gh-cli Skill 搜 GitHub 上 "CARLA Python API traffic" 参考项目
  3. 启动 CARLA simulator
  4. 写 Python 客户端连接 CARLA
  5. 在系统里加"仿真视频源"选项（管理端可切换：本地摄像头 / 视频文件 / CARLA 仿真）
  6. 用 Chrome DevTools MCP 验证切换功能
- **必须 MCP/Skill**：RunCommand + WebSearch + WebFetch + Read + Edit + gh-cli Skill
- **验收标准**：管理端能切换到 CARLA 仿真源，画面显示正常

---

## 2. 统一要求

1. **每个子任务完成**：
   - 写 `_TASK-022-MXX_OUTPUT.json`（成功）或 `_TASK-022-MXX_ERROR.json`（失败）到 `e:\output\`
   - OUTPUT 格式包含：task, timestamp, status, details, deviations, screenshot_path
   - ERROR 格式包含：task, failed_at, error_text（完整 stack trace）, recommendation

2. **截图要求**：
   - 所有前端验证必须用 Chrome DevTools MCP take_screenshot
   - 截图保存到 `e:\output\screenshots\TASK-022-MXX-<描述>.png`
   - 截图完整绝对路径必须写入 OUTPUT 的 screenshot_path 字段
   - 截图本身就是一次自检

3. **任务顺序**：
   - 执行者可自主决定顺序，建议：M1 → M2 → M3 → M7 → M4 → M6 → M5 → M8
   - 遇到阻塞自主切换其他子任务，不要卡住等待

4. **高危操作**：用户已默认同意所有高危操作（pip/npm install、重启服务、删除自建文件等），无需请示

5. **报告指挥官**：每个子任务完成后报告 OUTPUT 文件路径 + 整体状态（PASS/FAIL/PARTIAL）

---

## 3. 验收标准（总）

- [ ] M1 能力报告单更新完成
- [ ] M2 torch 安装成功，`/health` 返回 `yolo_available: true`
- [ ] M3 管理端实时监控有画面 + YOLO 识别框（截图为证）
- [ ] M4 数字孪生无屏闪（截图为证）
- [ ] M5 数字孪生 4 场景演示完整（加分项，可跳过）
- [ ] M6 API Key 自动填充生效（截图为证）
- [ ] M7 小程序骨架完整 + 用户操作清单
- [ ] M8 CARLA 接入系统（B1 完成后）
- [ ] 所有截图路径已报告
- [ ] 所有 OUTPUT/ERROR 文件已写入

---

## 4. 关键文件路径

- 项目根：`e:\output\1`
- 后端：`e:\output\1\api\`
- 前端管理端：`e:\output\1\web-admin\`
- 数字孪生：`e:\output\1\digital_twin\`
- 小程序（新建）：`e:\output\1\miniprogram\`
- CARLA（新建）：`e:\output\1\carla\`
- 交接文档：`e:\output\TASK-021_HANDOVER_FOR_EXECUTOR.md`
- 能力报告单：`e:\output\executor_capability_report.md`
- 结果文件：`e:\output\_TASK-022-MXX_OUTPUT.json`
- 截图目录：`e:\output\screenshots\`

---

## 5. 提醒

- **开工前先读交接文档**：`e:\output\TASK-021_HANDOVER_FOR_EXECUTOR.md`
- **Git 优先复用**：每个子任务先搜 GitHub
- **禁止降级方案**
- **真实浏览器验证 + 截图**
- **用户已休息，自主决策，不要卡住等待**
- **遇到无法解决的阻塞，写 ERROR 文件并切换其他子任务**

---

**任务通知版本**：v1.0
**生成时间**：2026-07-23
**指挥官**：TRAE Assistant
**执行者**：TRAE Sub-agent
**用户状态**：已休息，全权委托执行者自主决策
