# TASK-017 系统整合实测与摄像头接入验证

## 任务概述

本次任务目标：**让系统跑起来，让指挥官看到成果**。完成"智瞳灵声"系统的端到端整合实测，确保本地 YOLO 检测 + 云端大模型复核 + 前端展示 + 数字孪生 全链路可运行。同时验证 DroidCam 手机摄像头作为实时视频源接入系统。

**核心原则**：质量和稳定性优先，配置要求灵活处理。只要能稳定运行并展示效果，配置细节可以调整。

**项目根目录**：`e:\output\1`
**任务结果文件**：`e:\output\_TASK-017_OUTPUT.json`
**预计耗时**：可执行一个晚上的长任务

---

## 前置条件（已确认）

1. DroidCam Client v6.5.3 已安装在电脑端
2. 手机端需要安装 DroidCam App（Android: Google Play/酷安；iOS: App Store）
3. GPU 环境已验证：RTX 4060 + CUDA可用（`C:\miniconda\envs\zhitong-gpu\python.exe`）
4. YOLO 模型已全部就位：`e:\output\1\zhitong\training\models\` 下 7 个模型可正常加载到 GPU

---

## 执行步骤

### 步骤 1：检查并启动服务（灵活配置，能跑就好）

**目标**：确认后端、前端、数字孪生服务能正常启动并通信。**端口优先使用现有配置，只要不冲突能跑通即可**。

**涉及文件**：
- `e:\output\1\api\app.py`（检查端口配置，默认监听 8000/8001 均可）
- `e:\output\1\api\start_api.bat`（使用 zhitong-gpu 环境启动）
- `e:\output\1\web-admin\vite.config.js`（检查前端端口，默认 5173）
- `e:\output\1\web-admin\src\api\index.js`（检查后端 API 基础地址，确保能访问后端）
- `e:\output\1\digital_twin\app.py`（检查数字孪生服务端口，避免与后端/前端冲突）

**要求**：
- **必须使用 zhitong-gpu 环境启动 Python**：`C:\miniconda\envs\zhitong-gpu\python.exe`
- 后端服务启动命令：`cd /d e:\output\1\api && C:\miniconda\envs\zhitong-gpu\python.exe app.py`
- 前端服务启动命令：`cd /d e:\output\1\web-admin && npm run dev`
- 数字孪生启动命令：`cd /d e:\output\1\digital_twin && C:\miniconda\envs\zhitong-gpu\python.exe app.py`
- **端口冲突时自行调整**，确保三个服务都能启动且无冲突

---

### 步骤 2：启动后端服务并验证

**目标**：确认后端 API 正常启动，模型加载到 GPU，接口可访问。

**执行命令**：
```powershell
cd e:\output\1\api
C:\miniconda\envs\zhitong-gpu\python.exe app.py
```

**验证标准**：
- 服务监听端口 8001
- 浏览器访问 `http://127.0.0.1:8001/docs` 能看到 FastAPI 文档
- 运行 `python test_recognizer.py` 或类似测试脚本，确认模型加载和推理正常
- 检查控制台输出：所有 YOLO 模型成功移动到 GPU

**如遇依赖缺失**：自动安装 `requirements.txt` 中列出的依赖（使用 zhitong-gpu 环境的 pip）。

---

### 步骤 3：启动前端管理后台并验证

**目标**：确认前端页面能正常访问并与后端通信。

**执行命令**：
```powershell
cd e:\output\1\web-admin
npm install   # 如 node_modules 缺失
npm run dev
```

**验证标准**：
- 前端运行在 `http://127.0.0.1:5173`
- 浏览器能打开管理后台页面
- Dashboard 能显示后端健康状态、模型加载状态
- AI检测页面能上传图片并返回识别结果

---

### 步骤 4：启动数字孪生服务并验证

**目标**：确认 Three.js 数字孪生场景能正常显示，并接收后端数据。

**执行命令**：
```powershell
cd e:\output\1\digital_twin
C:\miniconda\envs\zhitong-gpu\python.exe app.py
```

**验证标准**：
- 服务成功启动
- 浏览器能打开数字孪生页面
- WebSocket 连接正常，能接收模拟或真实数据

---

### 步骤 5：接入 DroidCam 手机摄像头

**目标**：将手机摄像头作为系统视频源，替代电脑自带摄像头。

**操作流程**：
1. 在手机端打开 DroidCam App，记录显示的 IP 地址和端口（如 `192.168.x.x:4747`）
2. 在电脑端打开 DroidCam Client，输入手机 IP 和端口，点击 Start
3. 确认电脑出现 DroidCam 虚拟摄像头（在设备管理器中可见）
4. 测试 OpenCV 是否能读取到该摄像头：
   ```python
   import cv2
   for i in range(4):
       cap = cv2.VideoCapture(i)
       if cap.isOpened():
           ret, frame = cap.read()
           if ret:
               print(f"摄像头索引 {i} 可用，分辨率: {frame.shape}")
           cap.release()
   ```
5. 记录可用的摄像头索引，写入配置文件或在启动脚本中指定

**验证标准**：
- OpenCV 能成功读取 DroidCam 摄像头画面
- 画面稳定，无明显延迟或卡顿
- 记录最终使用的摄像头索引

---

### 步骤 6：端到端实时检测实测

**目标**：让系统通过手机摄像头捕获画面，完成实时检测并在前端展示。

**涉及文件**：
- `e:\output\1\api\realtime_detector.py`
- `e:\output\1\api\routers\realtime.py`
- `e:\output\1\api\image_recognizer.py`
- `e:\output\1\zhitong\blind_yun.py`（参考其摄像头接入方式）

**执行方式**：
1. 启动后端服务（已包含实时检测路由）
2. 打开前端 AI检测页面
3. 选择"实时摄像头"模式，选择 DroidCam 对应的摄像头索引
4. 观察前端是否能显示带检测框的视频流
5. 触发一些动作（如举起一个物体模拟车辆/行人），观察 YOLO 是否能检测到目标

**验证标准**：
- 前端能看到实时视频流
- 视频流上有 YOLO 检测框和类别标签
- 控制台无持续报错
- 检测帧率 > 5 FPS（在 RTX 4060 上应能达到更高）

---

### 步骤 7：云端复核链路实测

**目标**：验证本地 YOLO 检测到异常后，能主动联系云端 AI（豆包/DeepSeek）进行复核。

**涉及文件**：
- `e:\output\1\api\cloud_collaborator.py`
- `e:\output\1\api\cloud_collab.py` 或相关路由
- `e:\output\1\api\image_recognizer.py` 中的 `ai_trace` 生成逻辑

**执行方式**：
1. 确保 `config_manager` 中配置了可用的 DashScope / DeepSeek API Key
2. 在实时检测页面触发一次"云端复核"（手动点击或自动触发）
3. 检查后端是否生成了 `ai_trace` 结构（version 'v3'，包含 yolo/doubao/deepseek/final）
4. 检查前端 AI Trace 页面是否能正确显示 v3 结构

**验证标准**：
- 云端复核请求成功返回
- `ai_trace.v3` 结构完整
- DeepSeek 对 Doubao 结果进行了交叉验证
- 当差异较大时返回 "high risk of misjudgment, please administrator verify"
- 当 Doubao 失败时 DeepSeek 独立判断并标记 "pending_review"

---

### 步骤 8：生成实测报告

**目标**：记录所有实测结果、问题、截图。

**报告内容**：
1. 系统启动日志（后端/前端/数字孪生是否成功启动）
2. DroidCam 连接信息（IP、端口、摄像头索引）
3. 实时检测截图（至少 3 张）
4. ai_trace 输出示例
5. 遇到的问题和解决方案
6. 性能数据（FPS、GPU 占用、延迟）

**报告保存位置**：`e:\output\1\test_results\TASK-017_integration_test_report.md`

---

## 强制规则

1. **必须在 zhitong-gpu 环境下运行 Python 脚本**，禁止直接使用 base 环境的 python
2. **所有代码修改必须通过 old_string 精确匹配替换**，修改前必须先读取文件
3. **所有变更必须在 _TASK-017_OUTPUT.json 的 deviations 字段中列出**，否则任务视为未完成
4. **不得在代码中硬编码 API Key**
5. **每次启动服务前检查端口占用**：8001、5173、数字孪生端口
6. **如遇到无法解决的问题**，记录到 ERROR 文件并停止，不得自行绕过

---

## 验收标准（质量和稳定性优先）

**核心目标：能跑通、看到效果**。只要系统能稳定运行并展示检测效果，配置细节可以灵活处理。

必须全部满足才算 PASS：

- [ ] 后端服务成功启动（端口不限，能访问即可）
- [ ] 前端管理后台成功启动（端口不限，能访问即可）
- [ ] 数字孪生服务成功启动且无冲突
- [ ] 所有 YOLO 模型加载到 GPU（控制台有明确日志）
- [ ] DroidCam 手机摄像头被 OpenCV 识别并可用（或使用本地摄像头作为备选）
- [ ] 前端能看到带检测框的实时视频流
- [ ] 云端复核链路能生成 v3 结构 ai_trace（API Key 配置灵活处理）
- [ ] 生成实测报告 `e:\output\1\test_results\TASK-017_integration_test_report.md`
- [ ] 输出结果文件 `e:\output\_TASK-017_OUTPUT.json`

**弹性项（不强制，但尽量完成）**：
- [ ] 端口统一为 8001/5173（如无冲突则使用）
- [ ] ai_trace v3 完整包含 yolo/doubao/deepseek/final（如 API Key 不可用，可部分完成）
- [ ] 数字孪生 WebSocket 实时数据推送（模拟数据也可）

---

## 输出要求

成功时写入：`e:\output\_TASK-017_OUTPUT.json`
失败时写入：`e:\output\_TASK-017_ERROR.json`

JSON 格式参见项目规则。
