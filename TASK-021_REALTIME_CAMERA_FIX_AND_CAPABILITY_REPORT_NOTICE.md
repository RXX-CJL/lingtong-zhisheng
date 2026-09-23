# TASK-021：实时监控摄像头画面彻底修复 + 执行者能力深度探索

## 任务背景
用户反馈实时监控页面"摄像头启动成功，但依旧没有画面"。
此问题已困扰多轮，TASK-018/019/020 都尝试过但未完全解决。
核心矛盾：blind_yun.py 几百行代码就能在桌面显示摄像头，网页方案却一直卡壳。

## 上一轮已完成的工作（指挥官已做）
1. **后端新增 detect_external_frame 方法**
   - 文件：`e:\output\1\api\realtime_detector.py`
   - 功能：接收前端 base64 帧做 YOLO 检测，返回检测结果
   - 状态：✅ 已完成，已验证接口可用（88帧处理成功）

2. **后端新增 /detect-frame 接口**
   - 文件：`e:\output\1\api\routers\realtime.py`
   - 路由：`POST /api/realtime/detect-frame`
   - 状态：✅ 已完成，curl 测试通过

3. **前端改用 getUserMedia 方案**
   - 文件：`e:\output\1\web-admin\src\views\RealTimeMonitor.vue`
   - 改动：用 `<video>` + `navigator.mediaDevices.getUserMedia` 直接显示摄像头画面
   - 检测逻辑：从 `<video>` 截图（canvas.toDataURL）发后端 `/detect-frame`
   - 状态：✅ 代码已改，前端构建通过

4. **DevTools 验证结果（在 Chrome DevTools MCP 中）**
   - `getUserMedia` API 可用，`navigator.mediaDevices.getUserMedia` 返回 OK
   - video 元素状态：videoWidth=1280, videoHeight=720, readyState=4, trackState=live
   - 后端处理帧计数持续增长（38→88）
   - **但用户实际看到的页面：没有画面**

## 可能的根因分析（待执行者排查）
1. **CSS 样式问题**：video 元素存在且有画面，但被 CSS 隐藏/遮挡/尺寸为0
   - 检查 `.video-feed` 的样式是否正确
   - 检查父容器 `.video-wrapper` 是否有尺寸
   - 检查 `v-show="isRunning"` 是否生效

2. **Vite 热更新未生效**：用户浏览器加载的还是旧代码
   - 需要硬刷新（Ctrl+Shift+R）或重启 dev server

3. **浏览器摄像头授权问题**：用户拒绝了授权或授权弹窗被拦截
   - 但代码中应该有 ElMessage.error 提示

4. **视频流已获取但渲染问题**：
   - `autoplay` 属性在某些浏览器需要用户交互才能播放
   - `muted` 属性是否正确设置（autoplay 需要 muted）
   - 检查 `playsinline` 属性（iOS 需要）

5. **对象赋值问题**：Vue3 的 ref 赋值后 DOM 未更新
   - `videoRef.value.srcObject = mediaStream` 是否触发了响应式更新

## 你的任务

### 第一部分：彻底修复实时监控画面显示问题

**执行步骤：**
1. 打开 `http://localhost:5173/realtime` 页面
2. 打开 Chrome DevTools，检查 Elements 面板中 video 元素的实际状态
3. 检查 Console 面板是否有报错
4. 检查 Network 面板，确认页面加载的是最新代码（看 RealTimeMonitor.vue 对应文件）
5. 点击"开始检测"，观察：
   - 浏览器是否弹出摄像头授权
   - video 元素的 srcObject 是否被设置
   - video 元素的 CSS 样式（display、visibility、width、height）
   - video.readyState 和 video.videoWidth/videoHeight
6. 定位问题并修复
7. 验证：画面正常显示，FPS 计数器在变化，检测目标列表有更新

**验收标准：**
- [ ] 点击"开始检测"后3秒内出现摄像头画面
- [ ] 画面流畅（至少 10fps 视觉流畅度）
- [ ] 右侧"检测状态"中处理帧数持续增长
- [ ] 检测到目标时右侧"检测目标"列表更新
- [ ] 停止检测后画面消失，状态变为"已停止"
- [ ] 刷新页面后功能正常（不依赖热更新）

### 第二部分：深度探索你的能力边界（MCP + Skills）

**背景**：用户要求你"全面发挥 MCP 和 skill 技能"，并生成能力剖析报告。
之前的任务提到过但可能不够深入。请系统性地探索：

**执行步骤：**
1. **MCP 能力盘点**
   - 列出你能调用的所有 MCP 服务器
   - 每个 MCP 服务器有哪些工具
   - 哪些工具是你之前没用过/没充分利用的

2. **Skill 能力盘点**
   - 列出所有可用的 Skill
   - 按类别分组（前端、后端、数据分析、可视化、文档等）
   - 标注哪些是高价值但未充分使用的

3. **工具组合探索**
   - 思考：哪些 MCP 工具 + Skill 的组合能产生 1+1>2 的效果
   - 例如：browser + frontend-design = 实时预览调试
   - 例如：search + data-analysis = 自动数据分析

4. **生成能力剖析报告**
   - 输出格式：Markdown
   - 保存到：`e:\output\executor_capability_report.md`
   - 内容包括：
     - MCP 服务器清单（每个服务器的工具列表、用途、使用场景）
     - Skill 清单（每个 Skill 的能力、适用场景、示例用法）
     - 能力矩阵（按任务类型推荐的工具组合）
     - 局限性说明（哪些做不到）
     - 最佳实践建议（如何高效使用你的能力）

**验收标准：**
- [ ] MCP 清单完整，每个工具都有一句话说明
- [ ] Skill 清单完整，按类别分组
- [ ] 能力矩阵至少覆盖 5 种常见任务类型
- [ ] 报告有实际参考价值，不是简单罗列

### 第三部分：数字孪生页面优化（如果时间充裕）

**背景**：用户之前反馈数字孪生演示模型问题多（红绿灯无倒计时、车辆穿模、无停车行为）。
如果前两部分完成得快，可以开始这部分。

**优先级**：低（前两部分必须完成）

## 技术栈
- 前端：Vue 3 + Element Plus + Vite
- 后端：FastAPI (Python) + OpenCV + YOLO
- 浏览器摄像头：`navigator.mediaDevices.getUserMedia`
- 后端端口：8001
- 前端端口：5173

## 关键文件路径
- 前端实时监控页：`e:\output\1\web-admin\src\views\RealTimeMonitor.vue`
- 前端 API 模块：`e:\output\1\web-admin\src\api\index.js`
- 后端实时检测路由：`e:\output\1\api\routers\realtime.py`
- 后端实时检测器：`e:\output\1\api\realtime_detector.py`
- 参考实现（桌面版）：`e:\output\1\beforeness\blind_yun.py`
- 前端 Vite 配置：`e:\output\1\web-admin\vite.config.js`

## 工具使用要求
- **必须**使用 Chrome DevTools MCP 进行前端调试
- **必须**使用 browser MCP 进行页面操作和截图验证
- **鼓励**使用 frontend-design skill 优化 UI
- **鼓励**使用 webapp-testing skill 进行自动化测试
- **鼓励**使用 search skill 查找最佳实践
- 遇到问题先搜索（web-search），不要盲目尝试

## 输出要求
1. 修复完成后写入 `_TASK-021_OUTPUT.json`
2. 能力报告保存到 `e:\output\executor_capability_report.md`
3. 报告指挥官：只说结果文件路径 + 整体状态

## 注意事项
- VPN 已开启，可正常访问网络
- 高危操作（npm install、重启服务等）用户已默认同意
- 禁止降级方案，遇到问题找更好的方法
- 信息获取和能力提升优先用 git 和官方文档
