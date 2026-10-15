# TASK-019 前端实时摄像头画面显示修复

## 任务概述

修复前端管理后台 AIDetect.vue 实时摄像头画面不显示的问题，并优化摄像头列表显示。

**核心问题**：MJPEG 视频流通过 Vite 代理（http-proxy）传输时，由于 http-proxy 不支持 `multipart/x-mixed-replace` 流式响应，导致画面无法显示。摄像头灯亮是因为检测已启动在读帧，但 MJPEG 流到不了前端。

**修复方案**：MJPEG 流地址改为后端绝对地址，绕过 Vite 代理。后端已配置 CORS `allow_origins=["*"]`，跨域无问题。

**项目根目录**：`e:\output\1`
**任务结果文件**：`e:\output\_TASK-019_OUTPUT.json`

---

## 前置条件（已确认）

1. 后端运行在 `http://127.0.0.1:8001`，CORS 已配置 `allow_origins=["*"]`
2. 后端接口可用：
   - `GET /api/realtime/stream` — MJPEG 视频流（带 YOLO 检测框，已实现）
   - `GET /api/realtime/camera/list` — 摄像头列表
   - `POST /api/realtime/start` — 启动检测
   - `POST /api/realtime/stop` — 停止检测
   - `GET /api/realtime/status` — 检测状态
3. 前端运行在 `http://127.0.0.1:5173` 或 `5174`
4. Vite 代理配置了 `/api` → `http://127.0.0.1:8001`，但**不支持 MJPEG 流式响应**
5. 后端 `get_annotated_frame()` 已正确返回带 YOLO 检测框 + 违规标注 + FPS 的画面（无需修改后端）
6. DroidCam 手机摄像头或本地摄像头可用

---

## 执行步骤

### 步骤 1：修复 MJPEG 流地址 — 绕过 Vite 代理

**目标**：MJPEG 流地址改为后端绝对地址，绕过 Vite 代理。

**涉及文件**：
- `e:\output\1\web-admin\src\views\AIDetect.vue`

**当前问题代码**（约第 469 行）：
```javascript
videoStreamUrl.value = `/api/realtime/stream?t=${Date.now()}`
```

**修复要求**：
1. 在 AIDetect.vue 的 `<script setup>` 顶部定义后端地址常量：
   ```javascript
   // 后端API基础地址（MJPEG流需要直接访问后端，绕过Vite代理）
   const BACKEND_URL = window.location.protocol + '//' + window.location.hostname + ':8001'
   ```
2. 修改 `videoStreamUrl` 为绝对地址：
   ```javascript
   videoStreamUrl.value = `${BACKEND_URL}/api/realtime/stream?t=${Date.now()}`
   ```
3. 在 `<img>` 标签上添加 `@load` 和 `@error` 事件处理：
   - `@load`：设置 `videoLoaded.value = true`，隐藏加载提示
   - `@error`：显示错误提示"视频流连接失败，请检查后端服务"
4. 添加 `crossorigin="anonymous"` 属性到 `<img>` 标签（虽然 CORS 已配 `*`，但加上更保险）

**验证标准**：
- 点击"开始检测"后，视频区域显示带 YOLO 检测框的实时画面
- 画面流畅刷新（非静态图片）
- 加载提示在画面出现后消失

---

### 步骤 2：优化摄像头列表显示

**目标**：摄像头列表显示设备名称，而非仅"摄像头 X (可用)"。

**涉及文件**：
- `e:\output\1\web-admin\src\views\AIDetect.vue`

**当前问题代码**（约第 186 行）：
```html
<el-option
  v-for="cam in cameraList"
  :key="cam.index"
  :label="`摄像头 ${cam.index} (可用)`"
  :value="cam.index"
/>
```

**修复要求**：
1. 修改 `loadCameraList()` 函数，为每个摄像头添加设备名称：
   - 索引 0 通常是内置摄像头，显示"摄像头 0 - 内置摄像头"
   - 索引 1+ 可能是 DroidCam/USB 摄像头，显示"摄像头 N - 外接设备"
   - 可以通过尝试读取摄像头分辨率来区分（可选）
2. 修改 `<el-option>` 的 label，显示更友好的名称：
   ```html
   :label="cam.label || `摄像头 ${cam.index}`"
   ```
3. 摄像头列表为空时显示提示"未检测到可用摄像头，请检查摄像头连接"
4. 添加"刷新摄像头列表"按钮，点击后重新调用 `loadCameraList()`

**验证标准**：
- 进入实时摄像头标签页，自动加载摄像头列表
- 列表显示设备名称（如"摄像头 0 - 内置摄像头"）
- 列表为空时有明确提示
- 刷新按钮可重新检测

---

### 步骤 3：修复摄像头选择和启动逻辑

**目标**：确保用户必须选择摄像头后才能启动检测，且启动流程正确。

**涉及文件**：
- `e:\output\1\web-admin\src\views\AIDetect.vue`

**当前问题代码**（约第 197 行）：
```javascript
:disabled="!selectedCameraIndex !== undefined || isDetecting"
```
这段逻辑有误，`!selectedCameraIndex !== undefined` 永远为 false（因为 `!undefined !== undefined` → `true !== undefined` → `true`，实际上这个条件逻辑是错的）。

**修复要求**：
1. 修复"开始检测"按钮的 disabled 条件：
   ```javascript
   :disabled="selectedCameraIndex === null || isDetecting"
   ```
2. 将 `selectedCameraIndex` 初始值改为 `null`（而非 `0`），强制用户选择
3. 摄像头列表加载后，如果有可用摄像头，默认选中第一个
4. 启动检测时显示 loading 状态，启动成功后切换到视频流显示
5. 停止检测时清空 `videoStreamUrl`，避免请求堆积

**验证标准**：
- 进入页面时"开始检测"按钮禁用
- 选择摄像头后"开始检测"按钮启用
- 启动检测后按钮变为"停止检测"
- 停止检测后画面消失，可重新选择摄像头

---

### 步骤 4：添加错误处理和状态反馈

**目标**：提升用户体验，出错时有明确提示。

**涉及文件**：
- `e:\output\1\web-admin\src\views\AIDetect.vue`

**修复要求**：
1. MJPEG 流加载超时处理（10秒未显示画面则提示"连接超时，请检查后端服务是否正常运行"）
2. 检测状态轮询失败时显示警告
3. 摄像头启动失败时显示具体错误信息（从后端响应中提取）
4. 在视频画面下方添加"帧率: X FPS | 总帧数: X | 处理帧数: X"实时状态条
5. 添加"截图保存"按钮，调用 `GET /api/realtime/snapshot` 获取当前帧并下载

**验证标准**：
- 后端未运行时有明确错误提示
- 摄像头被占用时有明确错误提示
- 状态信息实时更新
- 截图按钮可保存当前画面

---

### 步骤 5：端到端验证

**目标**：确认实时摄像头功能完全正常。

**验证流程**：
1. 启动后端（8001）和前端（5173/5174）
2. 打开前端 → AI检测 → "实时摄像头"标签
3. 确认摄像头列表自动加载，显示设备名称
4. 选择摄像头，点击"开始检测"
5. 确认画面显示，带 YOLO 检测框
6. 确认状态信息实时更新（FPS、帧数等）
7. 点击"停止检测"，确认画面停止
8. 截图保存功能正常

---

## 强制规则

1. **所有代码修改必须通过 old_string 精确匹配替换**，修改前必须先读取文件
2. **所有变更必须在 _TASK-019_OUTPUT.json 的 deviations 字段中列出**
3. **不得在代码中硬编码 API Key**
4. **只修改前端 AIDetect.vue**，不修改后端代码（后端已正确实现）
5. **保留现有"文件上传"功能不变**
6. **BACKEND_URL 使用动态拼接**（`window.location.hostname + ':8001'`），不硬编码 IP

---

## 验收标准

必须全部满足才算 PASS：

- [ ] MJPEG 流地址改为后端绝对地址，绕过 Vite 代理
- [ ] 实时摄像头画面正常显示，带 YOLO 检测框
- [ ] 摄像头列表显示设备名称
- [ ] 摄像头列表为空时有提示
- [ ] "开始检测"按钮 disabled 逻辑修复
- [ ] 添加刷新摄像头列表按钮
- [ ] 添加截图保存按钮
- [ ] 错误处理和状态反馈完善
- [ ] 输出结果文件 `e:\output\_TASK-019_OUTPUT.json`

---

## 输出要求

成功时写入：`e:\output\_TASK-019_OUTPUT.json`
失败时写入：`e:\output\_TASK-019_ERROR.json`

JSON 格式参见项目规则。deviations 字段必须列出所有变更。
