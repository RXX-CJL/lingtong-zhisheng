# TASK-023 CUDA torch 修复 + 未完成任务收尾

> **指挥官交接说明**：TASK-022 部分完成，M2（CUDA torch）失败、M3 缺截图验证、M8 未启动。本任务聚焦解决这些问题，数字孪生 4 场景（M5）暂不做。用户已休息，执行者全权自主决策。

---

## 0. 协作规则（继承 TASK-022）

1. **Git 优先复用**：每个子任务先搜 GitHub
2. **禁止降级方案**
3. **真实浏览器验证 + 截图**：截图完整绝对路径必须报指挥官
4. **自主决策权**：用户已休息，无需请示
5. **VPN 已开启**
6. **项目根目录**：`e:\output\1`
7. **结果输出**：`_TASK-023-MXX_OUTPUT.json` / `_TASK-023-MXX_ERROR.json` 到 `e:\output\`

---

## 1. TASK-022 遗留问题分析

### M2 失败根因（CUDA torch 安装）
- **错误**：`ProtocolError: IncompleteRead`，下载 2.6GB 文件在 418MB 处中断
- **根因**：pip 单线程下载不支持断点续传，跨国网络不稳定
- **当前状态**：已装 CPU 版 torch 2.12.1，`torch.cuda.is_available()` = False
- **硬件**：RTX 4060，驱动 566.07，支持 CUDA 12.7

### M3 问题
- 代码改了（改回 MJPEG 流方案，前端用 `<img>` 标签）
- 构建通过
- **但 screenshot_path 为空** —— 违反验证要求，没截图

### M8 状态
- B1 CARLA 下载状态未知（无输出文件）
- M8 未启动

---

## 2. 任务清单

### M1: 修复 CUDA 版 torch 安装（最高优先级）
- **优先级**：高
- **目标**：让 `torch.cuda.is_available()` = True，YOLO 用 GPU 推理
- **方案**（执行者自主选择，推荐 A）：

**方案 A：aria2 多线程断点续传（推荐）**
1. 用 RunCommand 安装 aria2：`winget install aria2` 或下载 aria2.exe
2. 用 WebSearch 查 PyTorch cu118 wheel URL：
   - `https://download.pytorch.org/whl/cu118/torch-2.x.x+cu118-cp3xx-cp3xx-win_amd64.whl`
   - 选 cu118（更稳定，清华镜像有缓存）
3. 用 aria2 多线程下载（16 线程+断点续传）：
   ```
   aria2c -x 16 -s 16 -c -o torch-cu118.whl "https://download.pytorch.org/whl/cu118/torch-2.x.x%2Bcu118-cp310-cp310-win_amd64.whl"
   ```
4. 本地安装：`py -3 -m pip install torch-cu118.whl`
5. 验证：`py -3 -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"`

**方案 B：清华镜像 cu118**
1. 用清华镜像安装：
   ```
   py -3 -m pip install torch torchvision --index-url https://mirrors.tuna.tsinghua.edu.cn/pytorch-wheels/cu118
   ```
2. 验证同上

**方案 C：PowerShell BITS 传输**
1. 用 BITS 下载（支持断点续传）：
   ```powershell
   Start-BitsTransfer -Source "https://download.pytorch.org/whl/cu118/torch-2.x.x%2Bcu118-cp310-cp310-win_amd64.whl" -Destination "torch-cu118.whl"
   ```
2. 本地安装

- **必须 MCP/Skill**：RunCommand + WebSearch + CheckCommandStatus + gh-cli Skill（查 pytorch 官方推荐安装方式）
- **验收标准**：
  1. `torch.cuda.is_available()` = True
  2. `torch.cuda.get_device_name(0)` 包含 "RTX 4060"
  3. `from ultralytics import YOLO` 成功
  4. 重启后端后 `/health` 返回 `yolo_available: true`
  5. 在 OUTPUT 的 details 里记录最终用的方案

### M2: 补做 M3 截图验证（实时监控画面）
- **优先级**：高（M1 完成后）
- **背景**：TASK-022 的 M3 改了代码但没截图验证，无法确认画面和识别框是否真的显示
- **操作**：
  1. 确认 M1 完成（torch CUDA 版装好，YOLO 能用 GPU）
  2. 启动后端（`e:\output\1\lan-start.bat`）和前端（`cd web-admin && npm run dev`）
  3. 用 Chrome DevTools MCP：
     - `navigate_page` 到 `http://localhost:5173/realtime`
     - `take_snapshot` 查看 DOM
     - `click` "开始检测" 按钮
     - `wait_for` 等待 5 秒
     - `take_screenshot` 截图，保存到 `e:\output\screenshots\TASK-023-M2-realtime.png`
     - `list_console_messages` 检查无报错
     - `evaluate_script` 执行 `document.querySelector('img').src` 确认 MJPEG 流 URL
  4. **如果画面不显示或无识别框**：
     - 用 `systematic-debugging` Skill 排查
     - 检查后端 `/realtime/stream` 是否返回 200
     - 检查 MJPEG 流 content-type 是否为 `multipart/x-mixed-replace`
     - 修复后重新截图
  5. **截图路径必须写入 OUTPUT**
- **必须 MCP/Skill**：Chrome DevTools MCP（navigate_page/take_screenshot/take_snapshot/click/wait_for/list_console_messages/evaluate_script）+ systematic-debugging Skill
- **验收标准**：
  1. 截图能清楚看到摄像头画面
  2. 画面上有 YOLO 识别框（绿色矩形+类别文字+置信度）
  3. 有 FPS 显示
  4. 截图完整路径已写入 OUTPUT
  5. 如果修复了问题，在 deviations 里说明改了什么

### M3: 验证 M4/M6/M7 的实际效果
- **优先级**：中
- **背景**：TASK-022 的 M4（数字孪生屏闪）、M6（API Key 自动填充）、M7（小程序）报告 PASS 但都没截图验证
- **操作**：
  1. 用 Chrome DevTools MCP 打开数字孪生页面，观察 30 秒，截图验证无屏闪
  2. 用 Chrome DevTools MCP 打开 Settings 页面，验证 API Key 自动填充，截图
  3. 检查小程序构建产物 `e:\output\1\miniprogram\dist\` 是否完整，列出文件清单
  4. 每个验证都截图，保存到 `e:\output\screenshots\TASK-023-M3-*.png`
- **必须 MCP/Skill**：Chrome DevTools MCP + LS + Read
- **验收标准**：3 个子项都有截图为证

### M4: 检查并完成 B1 CARLA 下载 + M8 接入
- **优先级**：中
- **操作**：
  1. 检查 CARLA 下载状态：
     - 用 LS 查看 `e:\output\1\carla\` 是否存在
     - 用 RunCommand 检查是否有下载进程在运行
     - 如果没下载，用 aria2 后台下载 CARLA（参考 M1 方案 A）
  2. 下载完成后解压 CARLA
  3. 用 gh-cli Skill 搜 GitHub 上 "CARLA Python API traffic detection" 参考项目
  4. 启动 CARLA simulator（`CarlaUE4.exe`）
  5. 写 Python 客户端连接 CARLA：
     - 用 `carla` Python 包
     - 获取仿真画面帧
     - 传给后端 YOLO 检测
  6. 在管理端添加"仿真视频源"选项：
     - 修改 `e:\output\1\web-admin\src\views\RealTimeMonitor.vue`
     - 摄像头选择下拉框增加 "CARLA 仿真" 选项
     - 后端 `e:\output\1\api\routers\realtime.py` 增加 CARLA 数据源支持
  7. 用 Chrome DevTools MCP 验证切换功能并截图
- **必须 MCP/Skill**：RunCommand + WebSearch + gh-cli Skill + Chrome DevTools MCP + Read + Edit + Write
- **验收标准**：
  1. CARLA 下载完成并解压
  2. Python 客户端能连接 CARLA 并获取画面
  3. 管理端能切换到 CARLA 仿真源
  4. 截图为证

### M5: 小程序功能完善
- **优先级**：中
- **背景**：TASK-022 的 M7 搭了骨架，但功能可能不完整
- **操作**：
  1. 读 `e:\output\1\miniprogram\` 下所有文件，评估完成度
  2. 用 gh-cli Skill 搜 GitHub 上 "微信小程序 交通违法举报" 参考项目
  3. 检查并完善以下功能：
     - 举报页：拍照/录像/相册上传、位置选择、违规类型选择、提交
     - 通知页：违规通知列表、详情查看、标记已读
     - 申诉页：针对违规通知提交申诉（上传证据、填写理由）
     - 我的：个人信息、我的举报、我的违规、我的申诉
  4. 检查后端 API 是否支持小程序调用：
     - 用 SearchCodebase 查 `e:\output\1\api\routers\` 下所有路由
     - 缺的接口自主补充
     - 确保小程序 API 请求路径和后端一致
  5. 写用户操作清单（执行者做不了的部分）：
     - 如何注册微信小程序
     - 如何配置 AppID/AppSecret
     - 如何配置合法域名
     - 如何上传代码到微信开发者工具
     - 如何提交审核
  6. 用户操作清单保存到 `e:\output\1\miniprogram\USER_GUIDE.md`
- **必须 MCP/Skill**：gh-cli Skill + frontend-design Skill + SearchCodebase + Read + Write + Edit
- **验收标准**：
  1. 所有页面功能完整
  2. 后端 API 对接完成
  3. 用户操作清单详细清晰

---

## 3. 统一要求

1. **每个子任务完成**：
   - 写 `_TASK-023-MXX_OUTPUT.json` 或 `_TASK-023-MXX_ERROR.json`
   - OUTPUT 必须包含：task, timestamp, status, details, deviations, screenshot_path
   - ERROR 必须包含：task, failed_at, error_text（完整 stack trace）, recommendation

2. **截图要求**：
   - 所有前端验证用 Chrome DevTools MCP take_screenshot
   - 截图保存到 `e:\output\screenshots\TASK-023-MXX-<描述>.png`
   - 截图路径写入 OUTPUT 的 screenshot_path 字段

3. **任务顺序**：M1 → M2 → M3 → M4 → M5（可自主调整）

4. **高危操作**：默认同意，无需请示

5. **报告指挥官**：每个子任务完成后报告 OUTPUT 文件路径 + 状态

---

## 4. 验收标准

- [ ] M1 CUDA torch 安装成功，`torch.cuda.is_available()` = True
- [ ] M2 实时监控画面+识别框截图为证
- [ ] M3 M4/M6/M7 效果截图验证
- [ ] M4 CARLA 下载+接入完成（或报告下载状态）
- [ ] M5 小程序功能完善 + 用户操作清单
- [ ] 所有截图路径已报告
- [ ] 所有 OUTPUT/ERROR 文件已写入

---

## 5. 关键文件路径

- 项目根：`e:\output\1`
- 后端：`e:\output\1\api\`
- 前端管理端：`e:\output\1\web-admin\`
- 小程序：`e:\output\1\miniprogram\`
- CARLA（新建）：`e:\output\1\carla\`
- 交接文档：`e:\output\TASK-021_HANDOVER_FOR_EXECUTOR.md`
- 能力报告单：`e:\output\executor_capability_report.md`
- 截图目录：`e:\output\screenshots\`

---

**任务通知版本**：v1.0
**生成时间**：2026-07-23
**指挥官**：TRAE Assistant
**执行者**：TRAE Sub-agent
**用户状态**：已休息，全权委托执行者自主决策
