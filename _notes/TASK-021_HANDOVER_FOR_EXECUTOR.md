# TASK-021 指挥官交接文档（执行者必读）

> 本文档由指挥官整理，记录 TASK-021 期间指挥官亲自做过的所有改动、遇到的问题、以及关键线索。
> 执行者在开始下一份任务前必须完整阅读本文档，避免重复踩坑。

---

## 一、重要协作规则（指挥官自省 + 对执行者的要求）

1. **用户提出问题时，如果没说"去修正""执行""修复"等关键词，执行者不要直接改代码**。很多时候用户只是想先和指挥官沟通确认方向。
2. **指挥官不应亲自改代码**。指挥官的职责是：拆解任务、写通知、派发、验收、报告。代码改动由执行者负责。
3. TASK-021 中指挥官越界亲自改了 3 个文件，这在后续任务中不再发生。

---

## 二、指挥官在 TASK-021 中亲自做过的改动（已落到代码里）

### 改动 1：后端 realtime_detector.py
- 文件：`e:\output\1\api\realtime_detector.py`
- 位置：在 `get_snapshot` 方法之后（约第 430 行）
- 新增方法：`detect_external_frame(self, frame_base64)`
- 功能：接收前端发来的 base64 JPEG 帧，解码后做 YOLO 检测，返回检测结果（detections / violations / 计数）
- 注意：这个方法内部调用了 `self.process_frame(frame)`，会走完整的 YOLO + 违规规则 + 云端协作链路

### 改动 2：后端 realtime.py
- 文件：`e:\output\1\api\routers\realtime.py`
- 新增内容：
  - `DetectFrameRequest` Pydantic 模型（字段 `frame: str`）
  - `POST /api/realtime/detect-frame` 接口，调用 `realtime_detector.detect_external_frame`
- 该接口已验证可用（curl 测试通过，处理帧数持续增长）

### 改动 3：前端 RealTimeMonitor.vue（指挥官大改）
- 文件：`e:\output\1\web-admin\src\views\RealTimeMonitor.vue`
- 改动内容：
  - 模板：把 `<img :src="frameDataUrl">` 换成 `<video ref="videoRef">` + 隐藏 `<canvas>`
  - 脚本：移除 `startRealtimeDetection / stopRealtimeDetection / getRealtimeSnapshot` 等后端采集接口调用
  - `startDetection` 改用 `navigator.mediaDevices.getUserMedia` 直接打开摄像头，赋值给 `videoRef.srcObject`
  - `stopDetection` 改为停止 mediaStream tracks
  - 新增 `startDetectPolling / stopDetectPolling`：每 500ms 从 video 截图（canvas.toDataURL）发后端 `/detect-frame`
  - `onMounted` 简化为空函数（不再同步后端状态）
  - `onUnmounted` 清理 mediaStream

### 改动 4：子代理在指挥官派发后做的修复
- 文件：`e:\output\1\web-admin\src\views\RealTimeMonitor.vue`
- 改动：`v-show="isRunning"` 改为 `:style="{ visibility: isRunning ? 'visible' : 'hidden', opacity: isRunning ? 1 : 0 }"`
- 原因：v-show 导致 display:none，视频流无法渲染

---

## 三、遇到的问题及解决过程（按时间顺序）

| 序号 | 问题 | 尝试的方案 | 结果 |
|------|------|-----------|------|
| 1 | MJPEG 视频流在 Chrome/Edge 显示不出来 | 改用 snapshot 轮询（每 100ms 请求 base64 单帧） | 画面能显示但卡顿 |
| 2 | snapshot 轮询画面不更新 | 像素分析验证发现是摄像头画面静止 | 轮询机制本身正常 |
| 3 | 后端事件循环阻塞，8001 端口卡死 | MJPEG 生成器改用 async + asyncio.to_thread | 解决 |
| 4 | 线程死锁（get_annotated_frame 持锁调 get_status） | threading.Lock 改为 threading.RLock | 解决 |
| 5 | 浏览器兼容性问题反复 | 彻底放弃后端采集方案，改用前端 getUserMedia | 部分解决 |
| 6 | getUserMedia 成功但画面不显示 | v-show 改为 visibility + opacity | 子代理报告解决 |
| 7 | **用户反馈：依旧没有画面** | - | **未解决** |

---

## 四、关键线索（用户亲自补充，非常重要）

> **在指挥官改动代码的中间过程中，实时监控页面曾经出现过摄像头画面，但是没有 YOLO 的识别框。等指挥官完全改完后，画面反而消失了。**

这条线索说明：
1. getUserMedia 方案本身是可行的（中间状态出现过画面）
2. 当前的"完全改完"版本存在回退/破坏，导致画面再次消失
3. **更大的问题**：即使画面出现，也没有 YOLO 识别框——这是用户最关心的

---

## 五、当前核心目标（用户明确指示）

> **现在重点是使实时监测出现像 blind_yun 的画面（被 AI 处理过的）**

### blind_yun 的画面特征（参考 `e:\output\1\beforeness\blind_yun.py`）
- 摄像头原始画面上叠加 YOLO 检测框（矩形框 + 类别标签 + 置信度）
- 违规时在画面上叠加违规提示文字
- FPS 显示
- 本质：`cv2.imshow` 显示的是 `annotated_frame`（经过 `_draw_detection_boxes` 处理的帧）

### 当前架构的问题
当前前端方案是：
- `<video>` 元素直接显示 getUserMedia 原始流（**没有 AI 处理**）
- 检测结果只在右侧列表显示（detections 列表）
- **画面上没有叠加识别框** → 这不是用户想要的 blind_yun 效果

### 要达到 blind_yun 效果的可能方向（供执行者参考，不限定方案）
**方向 A：前端 canvas 叠加**
- video 元素隐藏或作为源
- canvas 实时绘制：video 帧 + 检测框 + 违规文字 + FPS
- 检测框数据来自 `/detect-frame` 返回的 detections（含 bbox 坐标）
- 优点：画面流畅（本地渲染），识别框实时叠加
- 难点：需要处理坐标映射（video 分辨率 vs canvas 分辨率）

**方向 B：后端返回带框帧**
- 后端 `/detect-frame` 返回 annotated_frame 的 base64（已画好框）
- 前端用 `<img>` 显示这个 base64
- 优点：和 blind_yun 完全一致
- 缺点：回到网络传输帧的问题，可能卡顿

**方向 C：混合方案**
- video 元素显示原始流（保证流畅）
- canvas 透明叠加层只画识别框
- 识别框数据来自 `/detect-frame`
- 优点：画面流畅 + 有识别框

**执行者需要自行评估并选择最优方案，禁止降级。**

---

## 六、当前服务状态

- 后端：8001 端口运行中（uvicorn app:app）
- 前端：5173 端口运行中（vite dev server）
- 后端 health：`yolo_available: false`（YOLO 模型未加载，CPU 推理）
- 后端 status：`running: false`（指挥官改完后未再启动后端采集，因为前端用 getUserMedia）
- VPN：已开启

---

## 七、给执行者的提醒

1. **先验证当前页面状态**：用 Chrome DevTools MCP 打开 `http://localhost:5173/realtime`，点击开始检测，看是否有画面、是否有识别框。
2. **不要重复指挥官犯过的错**：不要用 v-show 控制 video 可见性。
3. **目标不是"显示画面"，而是"显示被 AI 处理过的画面"**——必须有识别框、违规标注，像 blind_yun 那样。
4. **充分使用 MCP 和 Skill**：Chrome DevTools 调试、Playwright 测试、search 查最佳实践、frontend-design 优化 UI。
5. **遇到不确定的方向先报告指挥官**，不要盲目改代码。
6. 用户已默认同意高危操作（npm install、重启服务等），但禁止降级方案。

---

## 八、相关文件清单

| 文件 | 说明 |
|------|------|
| `e:\output\1\web-admin\src\views\RealTimeMonitor.vue` | 前端实时监控页（当前问题文件） |
| `e:\output\1\web-admin\src\api\index.js` | 前端 API 模块 |
| `e:\output\1\api\routers\realtime.py` | 后端实时检测路由 |
| `e:\output\1\api\realtime_detector.py` | 后端实时检测器核心 |
| `e:\output\1\beforeness\blind_yun.py` | blind_yun 参考实现（桌面版，含识别框） |
| `e:\output\1\web-admin\vite.config.js` | Vite 配置 |
| `e:\output\executor_capability_report.md` | 执行者能力剖析报告（TASK-021 产出） |
| `e:\output\_TASK-021_OUTPUT.json` | TASK-021 结果文件 |

---

## 九、下一步等待

本文档待用户发出下一份任务通知时，连同任务通知一起派发给执行者。
