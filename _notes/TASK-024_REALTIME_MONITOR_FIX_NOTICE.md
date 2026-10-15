# TASK-024 实时监控画面修复（getUserMedia 方案）

> **指挥官交接说明**：多次尝试 MJPEG 流方案均失败（Chrome/Edge 兼容性问题），必须回到 getUserMedia 方案——这是唯一能保证用户看到画面的方案。执行者必须在用户真实 Edge 浏览器环境验证（用户常用 Edge），不能用 Playwright。借鉴 Vibe Coding 理念：优先验证效果，其次审查代码；一个方案不行快速换另一个，不纠结细节。

---

## 0. 协作规则

1. **Git 优先复用**：先搜 GitHub
2. **禁止降级方案**：必须用 getUserMedia，不允许改回 MJPEG
3. **真实浏览器验证**：必须用 Chrome DevTools MCP 在用户真实 Edge 浏览器环境验证，截图为证
4. **自主决策权**：用户已休息，无需请示
5. **VPN 已开启**
6. **项目根目录**：`e:\output\1`
7. **结果输出**：`_TASK-024_OUTPUT.json` / `_TASK-024_ERROR.json` 到 `e:\output\`

---

## 1. 问题根因

MJPEG 流方案在用户真实 Chrome/Edge 浏览器中不工作：
- Vite 代理缓冲破坏流式传输
- Chrome/Edge 对 `multipart/x-mixed-replace` 支持不完整
- Playwright 测试环境和用户真实浏览器不一致

**唯一可行方案**：getUserMedia 直接访问摄像头，画面由 `<video>` 直接渲染，后端只负责 YOLO 检测。

---

## 2. 任务清单

### M1: 修复实时监控画面（核心任务）
- **优先级**：最高
- **目标**：用户能在浏览器中看到摄像头实时画面 + YOLO 识别框
- **方案**：getUserMedia 方案（已验证能显示画面）

**操作步骤**：

**步骤 1：修改 RealTimeMonitor.vue**
1. 读 `e:\output\1\web-admin\src\views\RealTimeMonitor.vue` 当前内容
2. 将视频显示改为 getUserMedia 方案：
   - `<video>` 标签直接用 getUserMedia 取流
   - 添加 canvas 覆盖层绘制识别框
   - WebSocket 接收检测结果并绘制
3. 移除 MJPEG 流相关逻辑
4. 添加摄像头权限请求处理

**步骤 2：修改后端接口**
1. 读 `e:\output\1\api\routers\realtime.py`
2. 确认 `/detect-frame` POST 接口存在（接收前端发来的 base64 帧）
3. 如果不存在，添加该接口

**步骤 3：修改 realtime_detector.py**
1. 读 `e:\output\1\api\realtime_detector.py`
2. 确认 `detect_external_frame` 方法存在（接收外部帧做 YOLO 检测）
3. 如果不存在，添加该方法

**步骤 4：前端构建验证**
1. `cd e:\output\1\web-admin && npm run build`
2. 确保无构建错误

**步骤 5：真实浏览器验证（必须）**
1. 启动后端（`e:\output\1\lan-start.bat`）和前端（`cd web-admin && npm run dev`）
2. 用 Chrome DevTools MCP：
   - `navigate_page` 到 `http://localhost:5173/realtime`
   - `click` "开始检测" 按钮
   - `wait_for` 等待摄像头授权（如果弹出）
   - `wait_for` 等待 5 秒
   - `take_screenshot` 截图，保存到 `e:\output\screenshots\TASK-024-M1-realtime.png`
   - `list_console_messages` 检查无报错
   - `evaluate_script` 执行 `document.querySelector('video').readyState` 确认视频流就绪
3. **截图路径必须写入 OUTPUT**

**步骤 6：确认识别框显示**
1. 确保 YOLO 模型已加载（`/health` 返回 `yolo_available: true`）
2. 画面中应有绿色识别框（类别文字+置信度）
3. 如果识别框不显示：
   - 检查 `/detect-frame` 接口是否被调用
   - 检查 WebSocket 是否收到检测结果
   - 检查 canvas 绘制逻辑
4. **修复后重新截图**

- **必须 MCP/Skill**：Chrome DevTools MCP（navigate_page/take_screenshot/take_snapshot/click/wait_for/list_console_messages/evaluate_script）+ systematic-debugging Skill + frontend-design Skill + Read + Edit
- **验收标准**：
  1. 截图能清楚看到摄像头真实画面
  2. 画面上有 YOLO 识别框（绿色矩形+类别文字+置信度）
  3. 有 FPS 显示
  4. 截图完整路径已写入 OUTPUT
  5. 前端构建成功
  6. 后端 `/health` 返回 `yolo_available: true`

### M2: 验证小程序用户操作清单
- **优先级**：中
- **操作**：
  1. 检查 `e:\output\1\miniprogram\USER_GUIDE.md` 是否存在
  2. 如果不存在，创建用户操作清单：
     - 如何注册微信小程序
     - 如何获取 AppID/AppSecret
     - 如何配置合法域名
     - 如何上传代码到微信开发者工具
     - 如何提交审核
  3. 确保清单详细清晰，步骤完整
- **必须 MCP/Skill**：Read + Write + WebSearch
- **验收标准**：USER_GUIDE.md 存在且内容完整

### M3: 添加 Claude 3.5 Sonnet 到云端协作（替换/增强豆包）
- **优先级**：中
- **目标**：提升违规识别准确性，用更强的视觉模型替换或增强当前的豆包
- **背景**：豆包在交通违规识别上误判率较高，需要更强的 AI 模型
- **操作步骤**：

**步骤 1：添加 Claude API 配置**
1. 读 `e:\output\1\api\config.py`
2. 添加 `CLAUDE_API_KEY` 配置项
3. 读 `e:\output\1\api\config_runtime.json`（如果存在），确保 Claude API Key 可以从配置文件加载

**步骤 2：创建 Claude 分析模块**
1. 读 `e:\output\1\api\image_recognizer.py`，了解现有的 `analyze_with_doubao` 和 `analyze_with_deepseek_judge` 的接口格式
2. 创建 `analyze_with_claude` 函数：
   - 使用 Anthropic Claude 3.5 Sonnet API
   - 支持图片输入（base64）
   - 返回格式与现有函数一致（is_violation_confirmed, confidence_adjusted, result_text）
3. 参考 `analyze_with_doubao` 的实现

**步骤 3：修改云端协作逻辑**
1. 读 `e:\output\1\api\cloud_collaborator.py`
2. 在 `consult_cloud` 和 `consult_cloud_dual` 方法中，将豆包替换为 Claude，或添加 Claude 作为第三层验证
3. 更新 `build_ai_trace` 和 `build_ai_trace_v31` 方法，支持 Claude 结果
4. 修改 `process_cloud_response` 方法，支持 Claude 作为优先裁决者

**步骤 4：测试验证**
1. 用 WebSearch 查 Anthropic Claude API 最新调用方式
2. 写一个测试脚本测试 Claude 分析效果
3. 确保现有代码兼容（不破坏豆包/DeepSeek 的调用）

**步骤 5：更新 Settings 页面**
1. 读 `e:\output\1\web-admin\src\views\Settings.vue`
2. 添加 Claude API Key 输入框（与智谱/DeepSeek/Qwen 并列）

- **必须 MCP/Skill**：Read + Edit + Write + WebSearch + gh-cli Skill（查 anthropic-sdk Python 包用法）
- **验收标准**：
  1. Claude API Key 配置项已添加到 config.py
  2. `analyze_with_claude` 函数已创建，接口格式与现有函数一致
  3. cloud_collaborator.py 已支持 Claude 调用
  4. Settings 页面已添加 Claude API Key 输入框
  5. 测试脚本能成功调用 Claude API

---

## 3. 统一要求

1. **每个子任务完成**：
   - 写 `_TASK-024-MXX_OUTPUT.json` 或 `_TASK-024-MXX_ERROR.json`
   - OUTPUT 必须包含：task, timestamp, status, details, deviations, screenshot_path
   - ERROR 必须包含：task, failed_at, error_text（完整 stack trace）, recommendation

2. **截图要求**：
   - 所有前端验证用 Chrome DevTools MCP take_screenshot
   - 截图保存到 `e:\output\screenshots\TASK-024-MXX-<描述>.png`
   - 截图路径写入 OUTPUT 的 screenshot_path 字段

3. **任务顺序**：M1 → M2

4. **高危操作**：默认同意，无需请示

5. **报告指挥官**：每个子任务完成后报告 OUTPUT 文件路径 + 状态

---

## 4. 验收标准

- [ ] M1 实时监控画面显示 + YOLO 识别框（截图为证）
- [ ] M2 小程序用户操作清单完整
- [ ] M3 添加 Claude 3.5 Sonnet 到云端协作（替换/增强豆包）
- [ ] 所有截图路径已报告
- [ ] 所有 OUTPUT/ERROR 文件已写入

---

## 5. 关键文件路径

- 项目根：`e:\output\1`
- 前端管理端：`e:\output\1\web-admin\src\views\RealTimeMonitor.vue`
- 后端路由：`e:\output\1\api\routers\realtime.py`
- 后端检测器：`e:\output\1\api\realtime_detector.py`
- 小程序：`e:\output\1\miniprogram\`
- 截图目录：`e:\output\screenshots\`

---

**任务通知版本**：v1.0
**生成时间**：2026-07-24
**指挥官**：TRAE Assistant
**执行者**：TRAE Sub-agent
**用户状态**：已休息，全权委托执行者自主决策
