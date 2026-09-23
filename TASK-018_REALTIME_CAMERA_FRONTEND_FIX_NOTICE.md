# TASK-018 实时摄像头视频流前端修复

## 任务概述

修复"智瞳灵声"系统中两处实时摄像头画面不显示的问题，并改进数字孪生视频面板的交互体验。

**核心问题**：
1. 前端管理后台 AIDetect.vue 没有实时摄像头视频流组件（只有图片上传）
2. 数字孪生视频面板请求的接口路径 `/api/stream/mjpeg/{cameraId}` 在后端不存在（后端实际接口是 `/api/realtime/stream`）
3. 数字孪生视频面板遮挡 3D 场景，不可拖动

**项目根目录**：`e:\output\1`
**任务结果文件**：`e:\output\_TASK-018_OUTPUT.json`

---

## 前置条件（已确认）

1. 后端服务运行在 `http://127.0.0.1:8001`，以下接口可用：
   - `GET /api/realtime/stream` — MJPEG 视频流（multipart/x-mixed-replace）
   - `GET /api/realtime/camera/list` — 摄像头列表
   - `GET /api/realtime/status` — 检测状态
   - `GET /api/realtime/snapshot` — 单帧快照（base64）
   - `POST /api/realtime/start` — 启动检测（body: `{"camera_index": 0}`）
   - `POST /api/realtime/stop` — 停止检测
   - `POST /api/realtime/consult` — 强制云端复核
2. DroidCam 或本地摄像头可用（索引 0/1/2/3）
3. 前端管理后台运行在 `http://127.0.0.1:5173`
4. 数字孪生运行在 `http://127.0.0.1:5000`

---

## 参考实现

**参考文件**：`e:\output\1\zhitong\blind_yun.py`
- 该文件展示了如何用 OpenCV 读取摄像头并显示带 YOLO 检测框的画面
- 关键逻辑：`cv2.VideoCapture(cam_index)` → 读取帧 → `model(frame)` → `results[0].plot()` → `cv2.imshow()`
- 后端已实现等效逻辑：`realtime_detector.py` 读取帧 → `multi_model_detect()` 检测 → `get_annotated_frame()` 返回带框帧 → `/api/realtime/stream` 输出 MJPEG

**前端 MJPEG 显示方式**：直接用 `<img>` 标签的 `src` 指向 MJPEG 流地址即可，浏览器原生支持：
```html
<img src="http://127.0.0.1:8001/api/realtime/stream" />
```

---

## 执行步骤

### 步骤 1：修复前端管理后台 AIDetect.vue — 新增实时摄像头模式

**目标**：在 AIDetect.vue 中新增"实时摄像头"标签页，与现有"文件上传"模式并列。

**涉及文件**：
- `e:\output\1\web-admin\src\views\AIDetect.vue`
- `e:\output\1\web-admin\src\api\index.js`（如需新增 API 调用）

**要求**：
1. 在页面顶部添加 `el-tabs`，包含两个标签页：
   - **文件上传**（保留现有功能不变）
   - **实时摄像头**（新增）
2. "实时摄像头"标签页内容：
   - 摄像头选择下拉框（调用 `GET /api/realtime/camera/list` 获取列表）
   - "开始检测"按钮（调用 `POST /api/realtime/start`，body: `{"camera_index": 选中的索引}`）
   - "停止检测"按钮（调用 `POST /api/realtime/stop`）
   - 视频流显示区域：`<img>` 标签，`src` 指向 `http://127.0.0.1:8001/api/realtime/stream`
   - 状态信息区域：显示当前帧数、处理帧数、违规数（定时调用 `GET /api/realtime/status`，每 1 秒刷新）
   - "云端复核"按钮（调用 `POST /api/realtime/consult`）
3. MJPEG 流地址需要根据后端实际地址拼接（从环境变量或配置中读取，避免硬编码）
4. 停止检测时清空 `<img>` 的 src，避免请求堆积
5. 摄像头画面区域要有合理尺寸（建议宽度 100%，高度自适应，max-height 500px）

**验证标准**：
- 切换到"实时摄像头"标签页，选择摄像头索引，点击"开始检测"
- 视频流区域显示带 YOLO 检测框的实时画面
- 状态信息实时更新
- 点击"停止检测"后画面停止刷新

---

### 步骤 2：修复数字孪生视频面板 — 接口路径对齐

**目标**：数字孪生视频面板能正确请求后端实际接口，显示真实摄像头画面。

**涉及文件**：
- `e:\output\1\digital_twin\static\js\main.js`（`createVideoPanel`、`selectVideoCamera`、`startVideoStreamListener` 方法）
- `e:\output\1\digital_twin\templates\index.html`（如需调整摄像头选项）

**当前问题**：
- `selectVideoCamera()` 请求 `/api/stream/mjpeg/${cameraId}` — 后端无此接口
- `startVideoStreamListener()` 请求 `/api/stream/info/${cameraId}` — 后端无此接口

**要求**：
1. 修改摄像头选择下拉框，改为动态从后端获取真实摄像头列表：
   - 调用 `GET http://127.0.0.1:8001/api/realtime/camera/list`
   - 根据返回的 `cameras` 数组生成 `<option>`（value 为摄像头索引）
2. 修改 `selectVideoCamera(cameraIndex)`：
   - 视频流地址改为 `http://127.0.0.1:8001/api/realtime/stream`
   - 选择摄像头后先调用 `POST http://127.0.0.1:8001/api/realtime/start`，body: `{"camera_index": cameraIndex}`
   - 再将 `<img>` 的 `src` 设为 MJPEG 流地址
3. 修改 `startVideoStreamListener()`：
   - 改为调用 `GET http://127.0.0.1:8001/api/realtime/status`
   - 从返回数据中提取 FPS、总帧数等信息
4. 关闭视频面板时调用 `POST http://127.0.0.1:8001/api/realtime/stop`
5. 后端地址从配置读取或使用相对路径（数字孪生 5000 端口访问后端 8001，需处理跨域）

**验证标准**：
- 打开数字孪生页面，点击视频面板的摄像头选择
- 选择一个可用摄像头，视频面板显示实时画面（带 YOLO 检测框）
- FPS 信息正常更新
- 关闭视频面板后摄像头释放

---

### 步骤 3：数字孪生视频面板改为可拖动浮窗

**目标**：解决视频面板遮挡 3D 场景的问题，改为可拖动、可调整大小的浮窗。

**涉及文件**：
- `e:\output\1\digital_twin\static\css\style.css`（视频面板样式）
- `e:\output\1\digital_twin\static\js\main.js`（拖动逻辑）

**要求**：
1. 视频面板样式调整：
   - 默认位置改为右上角（避免遮挡 3D 场景中央）
   - 尺寸适中（宽度 320px，高度自适应）
   - 添加半透明背景（backdrop-filter: blur）让 3D 场景隐约可见
   - 添加 `cursor: move` 提示可拖动
2. 实现拖动功能：
   - 鼠标按住视频面板头部（`.video-panel-header`）可拖动整个面板
   - 拖动时面板跟随鼠标移动
   - 松开鼠标后面板停留在当前位置
   - 拖动边界限制在窗口范围内
3. 可选：实现调整大小功能（右下角拖拽手柄）
4. 添加最小化按钮（点击后只显示标题栏，再次点击恢复）

**验证标准**：
- 视频面板可以拖动到屏幕任意位置
- 拖动过程流畅，无卡顿
- 拖动后不遮挡 3D 场景关键区域
- 最小化/恢复正常工作

---

### 步骤 4：端到端验证

**目标**：确认两处修复都能正常工作。

**验证流程**：
1. 启动后端（8001）、前端（5173）、数字孪生（5000）
2. 打开前端 `http://127.0.0.1:5173`，进入 AI检测页面，切换到"实时摄像头"标签
3. 选择摄像头，开始检测，确认画面显示
4. 打开数字孪生 `http://127.0.0.1:5000`，打开视频面板
5. 选择摄像头，确认画面显示
6. 拖动视频面板，确认可拖动
7. 截图保存到 `e:\output\1\test_results\`

**截图要求**：
- `e:\output\1\test_results\task018_frontend_realtime.png` — 前端实时摄像头画面
- `e:\output\1\test_results\task018_digital_twin_video.png` — 数字孪生视频面板
- `e:\output\1\test_results\task018_digital_twin_dragged.png` — 拖动后的视频面板

---

## 强制规则

1. **所有代码修改必须通过 old_string 精确匹配替换**，修改前必须先读取文件
2. **所有变更必须在 _TASK-018_OUTPUT.json 的 deviations 字段中列出**
3. **不得在代码中硬编码 API Key**
4. **前端 MJPEG 流地址使用配置或环境变量**，避免硬编码 `http://127.0.0.1:8001`
5. **保留现有"文件上传"功能不变**，只新增"实时摄像头"标签页
6. **如遇到无法解决的问题**，记录到 ERROR 文件并停止

---

## 验收标准

必须全部满足才算 PASS：

- [ ] 前端 AIDetect.vue 新增"实时摄像头"标签页，能显示 MJPEG 视频流
- [ ] 前端能选择摄像头、开始/停止检测、显示状态信息
- [ ] 数字孪生视频面板能正确请求后端接口，显示真实摄像头画面
- [ ] 数字孪生视频面板可拖动，不遮挡 3D 场景
- [ ] 两处画面都有 YOLO 检测框
- [ ] 生成 3 张验证截图
- [ ] 输出结果文件 `e:\output\_TASK-018_OUTPUT.json`

---

## 输出要求

成功时写入：`e:\output\_TASK-018_OUTPUT.json`
失败时写入：`e:\output\_TASK-018_ERROR.json`

JSON 格式参见项目规则。
