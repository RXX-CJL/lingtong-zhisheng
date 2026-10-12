# 结论报告 · 标定热重载 + 绘制侧 ROI 过滤 + 检测类白名单（`_design_2026-10-09_verdict.md`）

> **执行轮次**：2026-10-09 深夜 ~ 2026-10-10 00:20（第七轮）
> **任务来源**：`_DESIGN_NOTES_2026-10-06.md` **§11.0 的前 3 项**
> **执行者**：DSH（DeepSeek Harness Desktop）
> **本轮性质**：**第一次真正改代码**（上一轮 2026-10-09 只做设计讨论）
> **证据等级**：全文按协议 §7 标注 `[一]`命令结果 / `[二]`文件状态 / `[三]`真实行为

---

## 〇、一句话结论

**§11.0 前 3 项已完成并验证通过**：标定保存后**无需重启**即在当前视频上生效（实测 `reload_count` 自增）、
标定面板**只认正在运行的源**（不在错画面上标了）、画面里**不再画 ROI 外的红绿灯**、
**盆栽等非交通类在检测出口被裁掉**，且**判定链路语义完全未变**（trace 73/73 帧自洽）。
前端回归 **17/17 + 15/15**，后端新增自校验 **25/25**，端到端 HTTP 探针 **0 failed**。

---

## 一、根因复核结论（**用户提供的前提，全部成立；另发现两条用户没写的**）

| 设计单结论 | 复核结果 | 复核方式 |
|---|---|---|
| ①a 前端硬编码默认源 `LiveMonitor.vue:366` | ✅ **成立**（行号精确命中） | 读源码 `[二]` |
| ①b 后端标注不热重载（只有 `start_camera()` 一处 `load_scene()`） | ✅ **成立**（全仓 grep 仅 1 处加载点，另 1 处在 `get_status` 里的重载检查是新增的） | grep `[一]` |
| ② 判定只认 ROI，绘制不过滤 | ✅ **成立**（`_last_traffic_lights` 全收、渲染器全画） | 读源码 + trace `[三]` |
| ③渲染器只跳过红绿灯、其余照画 | ✅ **成立**，但**根因在检测出口缺少类白名单**，见 §三 O39 | 读源码 `[二]` |

### ★ 用户没写、我核到的两条地雷（已当场报备并获同意一并修）

| # | 问题 | 为什么危险 | 修法 |
|---|---|---|---|
| **L1** | **渲染器的红绿灯跳过名单与检测侧不一致**：`annotation_renderer.py:401` 判 `("traffic light","traffic_light","red_light","green_light","yellow_light")`，而检测侧 `_collect_traffic_lights` 还认**裸色名** `red/green/yellow`（判色器实际输出）。只要上游吐 COCO 原生 `"traffic light"`（这正是实际输出）就**漏网** → 被当普通目标画成灰框 + 英文标签，**按灯色着色的配色整体失效** | 直接让 ②③ 的修复"看不出来" | 收敛为 `annotation_renderer.TRAFFIC_LIGHT_CLASS_NAMES` 单一 frozenset，检测/绘制两处共用 |
| **L2** | **`LiveMonitor.vue:494` 的 `sc` 是未定义变量** → `refresh()` 的 `try` 在第 495 行**之前**抛 `ReferenceError`，被 `catch {}` 静默吞掉 → **`/realtime/vehicles` 的赋值（497~501 行）永远不执行**，灯态徽标永远空 | 是上一轮改 ROI 警告时留下的**隐形回归**；不修则用户根本看不到修复效果 | `const sc = status.value?.traffic_light_scope \|\| ''` |

> 这两条已在动手前用 ask_user_question 报备，用户选择"一并修"。

---

## 二、改了什么（逐条，含文件与行号级说明）

### 2.1 ① 标定能生效（两条根因）

| 改动 | 位置 | 说明 |
|---|---|---|
| **删掉硬编码默认源** | `web-admin/src/views/LiveMonitor.vue` | 原 L366 `ref('E:\\output\\1\\test_assets\\traffic_videos\\ea1ca6cb….mp4')` → `ref(localStorage.getItem('zt_live_source_v1') \|\| '')`，**绝不写死任何视频路径**；改动自动记住 |
| **面板源改为"正在跑的源"** | 同上 + `CalibrationPanel.vue` | 新增 `runningSource`（`/status` 的 `video_path`‖`source_url`）、`calSrc`（优先 runningSource）、`sourceMismatch`；`<CalibrationPanel :source="calSrc">` —— **画面与保存目标必然同一个源** |
| **红警告 + 禁止保存（带越权勾选）** | `CalibrationPanel.vue` | 新增 `.cal-alert` 提示条 + `blocked` 计算属性 + `save()` 二次拦截（不只靠按钮 disabled）+「我确认就是要给这个源做标定」勾选 |
| **顶栏"当前生效源" + 「⟲ 同步运行源」** | `LiveMonitor.vue` | 新增 `.src-bar` 一行：直接写出后端在跑哪个文件；不一致时整条变红 |
| **挂载时自动对齐一次** | `LiveMonitor.vue` | `syncFromStatusOnce()`：**只做一次**，不覆盖用户正在输入的内容（避免变成另一种"输入框自己跳变"） |
| **★后端热重载** | `api/realtime_detector.py` | 新增 `_scene_config_path()` / `_scene_sig_of()` / `_maybe_reload_scene_annotation()`；调用点在 **`_detection_loop()` 的 while 顶部**（保存后**下一帧**即生效）+ `get_status()` 前（未运行时点保存也立刻反映） |
| **可观测字段** | `api/realtime_detector.py` `/status` | `scene_annotation_reloaded_at` / `_reload_count` / `_roi_count` |

**为什么用 mtime+size 而不是"保存接口通知 detector"**（设计单 §12.5 的三选一）：
零耦合（不引入 routers→detector 反向依赖）、`os.stat` 微秒级、**任何写入方式都生效**（管理端接口 / 手工改文件 / 别的进程）。

**⚠ 实现里一个必须记住的坑（T85）**：`scene_annotation.video_key()` 是对**源字符串本身**取 sha1，
所以路径必须在**源就绪时算一次存下来**（`_scene_cfg_path`），不能事后拿 `_source_path` 重新推导 —— 差一个字符就是另一个键，热重载会永远检测不到变化。

### 2.2 ② 绘制侧 ROI 过滤

| 改动 | 位置 | 说明 |
|---|---|---|
| 绘制前过滤副本 | `api/realtime_detector._draw_detection_boxes()` | 只过滤**传给渲染器**的 `traffic_lights`；**`_last_traffic_lights` 一个字都没改**；未标 ROI 时保持旧行为（全部画，便于第一次标定时找灯） |

**★ 顺序约束（设计单特别警告过）**：灯态汇总 `_scene_light_state_from_cnn()` 读的**就是** `_last_traffic_lights`，
所以过滤必须发生在**绘制侧**、且**不改原列表**。本轮严格遵守 —— trace 证明判定语义零变化（§四）。

### 2.3 ③ 检测类白名单

| 改动 | 位置 | 说明 |
|---|---|---|
| 新增 `TRAFFIC_CLASS_WHITELIST`（41 个类名） | `api/image_recognizer.py` | 覆盖 `violation_rules` 里**全部**类名分组（VEHICLE/HELMET/NO_HELMET/PERSON/TRAFFIC_SIGNAL/RED_LIGHT/YELLOW_LIGHT/GREEN_LIGHT/LANE_LINE/STOP_SIGN）+ 车牌 + 红绿灯三种写法 |
| 检测出口过滤 | `realtime_detector.process_frame()` | `detections = self._filter_traffic_classes(detections)` **紧跟在 `_yolo_detect` 之后** |
| 可观测计数 | `_class_filter_stats` → `/status` | `kept`/`dropped`/`last_dropped_classes` + 最多每 5 秒一条 info 日志（**兜底必须可观测**，见 T75 教训） |

**为什么按白名单而不是"排掉盆栽"**：COCO 有 83 个无关类名，只排一个等于掩耳盗铃。
**为什么在检测出口而不是只在绘制时跳**：规则引擎/行为引擎/跟踪器/多帧确认器**同时**不再被垃圾框污染（T73 的 `license_plate` 回退 COCO 吐 12 个垃圾框也一并兜住）。

### 2.4 两条地雷的修复

- `annotation_renderer.TRAFFIC_LIGHT_CLASS_NAMES`（新常量，11 个名字）+ 主循环改用它；
  `realtime_detector` 模块级 `_TL_LIGHT_NAMES` 也 import 它 → **两处永远不可能再漂移**。
- `LiveMonitor.vue` 的 `sc` 已定义；顺带把 `loadRoiState()` 改为读 `calSrc`（不再是输入框），
  并加 `watch(calSrc)` —— 源一变就重判"ROI 标没标"（实测踩到过：挂载时后端没跑 → 按钮一直停在"⚠（未标）"）。

---

## 三、验证证据（按等级）

### 三级证据（真实行为，最强）

| 验证 | 证据 |
|---|---|
| **热重载真的生效**（检测**运行中**保存，不重启） | `/status`：`scene_annotation_reload_count` **0 → 1**，`reloaded_at=2026-10-10 00:11:30` / `00:14:37`，`roi_count=4`；后端日志同步出现 `★场景标注已热重载（无需重启检测）: ROI 4 -> 4 个` `[三]` |
| **绘制侧 ROI 过滤生效**（trace 逐帧核算） | `E:\output\_rt_trace_roi_filter_20261010.jsonl` **单一代码版本、一次不间断录制、120 帧**：收集 1472 盏、**ROI 内 784 盏、ROI 外 688 盏**（**120/120 帧**都有 ROI 外的灯被挡掉）。用户点名的那两盏：`('yellow',(419,120))` **214 帧全在 ROI 外**、`('red',(275,182))` **240 帧全在 ROI 外**、两者**无一帧**落在 ROI 内 → 新逻辑下**不再被画** `[三]` |
| **判定语义未被改动**（同一 trace） | **120/120 帧** `matched == ROI 内灯数`；`scope=roi` 120/120 帧 `[三]` |
| **类白名单真的在挡** | `/status` `class_filter_stats`：`kept=1644 / dropped=252`，`last_dropped_classes={"potted plant":252}`；后端日志 `已挡掉非交通类检测 2 个（累计 …）: potted plant×2` `[三]` |
| **前端：标定面板现在跟的是"正在跑的源"** | `check.mjs` 实测面板首帧 `naturalSize=1920x1080`（**演示视频**）；修复前 `diag-calib-source.mjs` 实测是 **1280x576**（旧 B 站视频）`[三]` |
| **前端回归** | `check.mjs` **17/17 PASS**、`check2.mjs` **15/15 PASS** `[三]` |
| **后端自校验** | `_scripts\_verify_hotreload_and_filter.py` **25/25 PASS**（白名单/热重载/ROI 谓词，全程用临时目录的假场景文件，不碰真实标注）`[一]` |
| **端到端 HTTP 探针** | `_scripts\_verify_fixes_e2e.py` **RESULT: PASS (0 failed)** —— 真跑演示视频，含"运行中保存→热重载"`[三]` |

### 二级证据（文件/配置状态）

- `E:\output\1\api\output\scene_configs\dual_cam_demo_lossless_4744a9bf2226.json`（1310 B）内容完好：
  `traffic_light_roi` 4 个 + `stop_line_y=511` + 相机参数 4 项 + 斑马线/公路区域 —— **回存测试没有丢字段** `[二]`
- 三个 Python 文件 `py_compile` 通过；`vite build` 通过（`✓ built in 16.42s`）`[一]`
- 后端运行配置：`models=vehicle,traffic_light,helmet,lane` / `imgsz=960` / `frame_rate=6` / `tl_color_model=tl_color_cnn5_carla.pt` `[一]`

### 一级证据（命令结果）

- `PASS 17/17`、`PASS 15/15`、`RESULT: PASS (0 failed)`、`RESULT: PASS (0 failed)`（脚本自打印）

---

## 四、★被推翻的旧结论（协议 §9.2 强制一节）

| # | 旧结论（已作废 / 需修正） | 更正 | 证据 |
|---|---|---|---|
| **O36** | "运行中保存的标定，后端会自己用上" | **错**。修前全仓只有 `start_camera()` 一处 `load_scene()` → 必须「停止→开始」；且 `/status` 仍报 `scope=roi`（旧标注里本来就有 1 个 ROI）→ **看起来在用、实际用旧值**。本轮已修（T85） | 日志时间线 22:33 启动 / 23:19 保存；修后 `reload_count 0→1` |
| **O37** | "标定面板显示的是当前画面" | **错**。面板跟输入框，而输入框被硬编码默认源重置 → 面板首帧是 1280×576 旧视频。本轮已修（T88/T81 同族） | `diag-calib-source.mjs` 实测；修后 1920×1080 |
| **O38** | "左侧那盏黄灯被识别，是判色/判定的问题" | **错**。判定侧**一直**只认 ROI。真相是**绘制侧完全没有过滤**。修的是绘制，不是判定 —— 若去改判定，会破坏"每循环 1 次真违规、0 误报" | trace 144 帧全在 ROI 外；73/73 帧 `matched == ROI 内灯数` |
| **O39** | "画面里有盆栽框是渲染器的问题" | **半错**。渲染器是**放大器**，根因是**检测出口没有类白名单**（COCO 83 个无关类）。只改渲染器 = 治标，规则/跟踪/行为引擎仍被污染 | `class_filter_stats`；`_filter_traffic_classes` 位置 |
| **O40**（我本轮自己的错判） | 我一度断言 **"`matched` 必须等于 `drawn`"**，并据此两次报 `FAIL` | **我的断言写错了**。`collected/drawn` 只在 `_draw_detection_boxes()` 里写，**没有 MJPEG 客户端时绘制侧根本不跑 → 这两个值会冻住**（实测无浏览器时恒为 12/6，而 matched 已变到 8）。可靠的不变量是 `drawn <= collected`；逐帧严格自洽性只能用 trace 验（120/120） | 400ms × 18 次采样；已写进 T84 |
| **O41**（我本轮自己造成又修回的） | 我手工 `python -m uvicorn` 重启后端，以为"配置一样" | **错，代价是性能静默退化**：`TUNE_*` 只在两个 `.bat` 里设 → 手工启动后 `imgsz` 变 1280、模型序列多出 `license_plate`、`frame_rate` 变 3。已改回带 `TUNE_*` 的启动方式并写进 T86 | `/status` 前后对比 |

---

## 五、风险与遗留

| # | 项 | 状态 |
|---|---|---|
| R1 | **`/status` 的 `traffic_lights_collected/drawn` 会"冻住"**（无流客户端时） | 已写进 T84 + 代码注释。**不是 bug，是读取姿势问题**；如将来要让它每帧更新，可把统计移到检测线程 |
| R2 | **ROI2 `[1639,894,1793,945]` 圈的是 CAM-2 小窗里的灯**（画中画） | 设计单 §12.5 已注明"技术上合法，留着不影响判定"。**未动**（属用户标注口径，不擅自改） |
| R3 | **`road_zones` 仍无任何消费方** | 设计单 §12.5 附带发现②，本轮未处理（不在前 3 项内） |
| R4 | **我重启后端的方式与 `.bat` 不完全等价** | 当前实例带 `TUNE_*` + `RT_TRACE_JSONL`，但**不带** `--reload`。与 `.bat` 默认路径一致。**下次请用 `restart-backend.bat`**（T86） |
| R5 | **本次跑的检测产生了真实事件/抓拍记录**（演示视频循环播放，属正常行为） | 事件表新增若干条（含 1 条 `state=manual_review`）。如需清理请用户定 |
| R6 | **`_rt_trace_roi_filter_20261010.jsonl`（120 帧、单一代码版本、一次不间断录制）留在工作区** | **建议保留** —— 它是"绘制侧 ROI 过滤"的唯一逐帧证据（同类资产：`_rt_trace_final.jsonl`）；如需清理请用户定 |
| R7 | ⚠ **库里 514 条事件的 `trigger_time` 是 1970 年**（历史脏数据，T93 的遗留产物） | **未修，待用户定**。可用抓拍文件名/事件 ID 反推真实时间做回填，但那是**改历史数据**，需用户明确同意（改前会先备份 DB） |
| R8 | ⚠ **后端原生崩溃（FFmpeg 解码器）已 4 次** | 见 §十。本轮又有一次（22:30:13，同一模块同一偏移）。**建议单独一轮排查**（换解码后端/改抽帧方式），不要与 MJPEG 线程池问题混修 |
| R9 | ⚠ **`loop_dedup_sec` 默认 300s 是"演示口径"** | 若将来用于真实场景（非循环视频），300s 可能过长；已做成运行时设置，可在设置页/接口调整，设 0 即关闭 |

---

## 六、下一步（**不在本轮范围，按 §11.0 顺序**）

| 序 | 任务 | 依据 |
|---|---|---|
| **4** | ~~两个框~~ | ✅ **本轮已完成**（见 §九） |
| **5** | **MJPEG 僵尸流**（"开久了像断网" + timeout + 刷新卡） | ⚠ **已用真实日志取证，结论推翻了预判**：不是线程池，是**后端进程崩了**（见 §十二）。**新的第 5 项 = 解决那个原生崩溃** |
| **6** | ~~云端开关连带推送~~ | ✅ **本轮已完成**（见 §十一，含更根本的"重启即重置"） |
| **7** | **画面违规文字方案 a**（`minimal` 档不画违规类型，保留红/绿框） | §12.2，用户已定 |
| **8** | **录违停视频** | §9；**帧率已定 = 30 fps**（用户 2026-10-10 确认）；建议在第 5/7 项之后录 |
| **9** | 其余：旧事件视频 2×、非模型成本拆分、审计项 | §1 §2 |
| **10** | ⚠ **后端会被 `cv2` 自带的 FFmpeg 解码器拖崩**（见 §十） | 本轮实测（已 4 次，同一模块同一偏移） |
| **11** | ⚠ **库里 514 条事件的 `trigger_time` 是 1970 年**（历史脏数据） | 本轮实测；**待用户定：是否按抓拍文件名回填** |
| **12** | ⚠ **同类 `instanceof`/Proxy 陷阱值得全仓复查**（见 T96） | 本轮实测 |

---

## 十二、★第 5 项取证结果：**"像断网" = 后端进程原生崩溃**（2026-10-10 追加）

**取证材料**：用户导出的前端日志 `C:\Users\ROG\Desktop\zhitong-frontend-log.json`（4.5 MB / 264 条）。
分析脚本：`E:\output\_scripts\_analyze_frontend_log.py`（可复跑）。

> **更正记录（2026-10-11）**：该原始文件**现已不在桌面/工作区**（复查时找不到）。
> **但本节的结论与数字都是当时实测所得**，已完整归档在此，不依赖原文件。
> 如需原始材料：管理端「系统设置 → **系统日志**」页 → 「导出 JSON」或「复制诊断摘要」
> （该导出崩溃的 bug 已修复）。
> **面向 GPT6 的完整疑难移交书见 `_GPT6_HANDOFF_BRIEF.md`。**

### 12.1 日志说明了什么（与设计单 §12.1 的预判**不一致**）

| 判据 | 预判（§12.1） | **实测** |
|---|---|---|
| 失败形态 | `timeout of 15000ms` | **25 个 HTTP 500 + 2 个 NO_RESP**，**一个 timeout 都没有** |
| 影响面 | 所有走线程池的接口排队 | **9 个不同接口同时 500**：`/realtime/status`、`/realtime/vehicles`、`/realtime/stop`、`/realtime/settings`、`/realtime/plugins`、`/realtime/plugins/scene-modes`、`/system/quota`、`/system/models`、`/system/performance`、`/devices/list`、`/statistics/overview` |
| `cost` 分布 | 集中在 15000ms | **4669 → 3170 → 1671 → 175 → 6 → 4 ms**（排队积压后**瞬间全失败**） |
| 持续时间 | "开久了"持续恶化 | **只有 8 秒**（15:14:00 → 15:14:08） |

**同一时刻的硬证据**：Windows 事件日志 `23:13:54`（本地）= `15:13:54`（UTC）——
`python.exe` 崩溃，模块 `opencv_videoio_ffmpeg500_64.dll`，异常码 `0xc000001d`，偏移 `0x2e9930`。

⇒ **后端进程死了**。那 25 个 500 是 uvicorn 在进程死亡过程中的挣扎（请求先排队 4.7 秒、
然后随进程一起失败），之后前端每次轮询只能拿到 `Network Error`。
**用户感知的"像断网"就是这个。**

### 12.2 崩溃的性质与诱因（已排除的、未排除的）

| 项 | 结论 | 依据 |
|---|---|---|
| 是不是 Python 异常 | **不是** | 日志无 traceback；Windows 事件日志 + 288MB 崩溃转储 |
| 是不是内存泄漏 | **不是** | 连续 10 分钟监控：WS 稳定在 **3.36 GB**（±20 MB）、句柄 704（±12）、不崩 |
| 单独解码会崩吗 | **不会** | `_stress_cv2_decode.py`：FFV1 顺序解码 **1040 帧**（44 fps）不崩 |
| 多线程解码会崩吗 | **不会** | `_stress_concurrent_decode.py`：3 线程并发 **6334 帧 / 60 秒**不崩 |
| 与"有没有人看画面"相关 | **强相关（尚未定案）** | 三次崩（22:11/22:30/23:13）**都**有浏览器开着 `/live`；不带画面连跑 10 分钟不崩 |
| 与素材编码相关 | **高度可疑** | 演示素材是 **FFV1 / BGRA / 373 Mbps**（极不寻常），崩溃点正在 FFmpeg 解码器内 |

### 12.3 已落地的规避措施（**不是修好，是绕开**）

1. **转出 H.264 版本**：`E:\output\_dual_cam_demo\dual_cam_demo_h264.mp4`
   —— 1920×1080 / 20 fps / **26.00 s**（与原版**同时长同帧率**）、**7.5 MB**（原版 1156 MB）；
   抽第 12 秒同帧对比：**平均像素差 2.02/255**、完全相同像素占 1.22% → **判色与演示观感无影响**
2. **补上换素材的副作用**：场景标注按"整条源路径 sha1"存储，换 `.mp4` 会**静默丢掉全部人工标定**
   （`scope` 从 `roi` 掉回 `frame`，闯红灯退化成"画面里任意一盏灯"）。
   已用 `_scripts\_copy_scene_config.py` 把标定复制到新键，**两个源现在都 `ROI=4`、`scope=roi`** `[三级]`
3. ⚠ **诚实说明**：我没有在受控条件下复现出这个崩溃（单独/并发解码都不崩），
   所以 H.264 只是**降低风险**，**不能保证**消除。判定方式：**用 H.264 版跑一次完整演示**，
   若不崩 → 就用它；若仍崩 → 说明与编码无关，转查"有 MJPEG 客户端"这条线。

---


## 十一、★第 6 项（云端开关）与"离线取证"修复 —— 2026-10-10 追加

### 11.1 云端开关"自己打开"：**两层根因，都修了**

| 层 | 现象 | 根因 | 修法 |
|---|---|---|---|
| **后端（更根本）** | 用户 22:01 关掉 `cloud_review`/`cloud_consult`；22:13 按流程重启后端 → `/settings` **立刻变回 `true/true`** | `RUNTIME_SETTINGS` 是**模块级内存字典**，两个开关默认 `True` → **每次重启都重置** | 新增 `api/output/runtime_settings.json`：改设置即落盘，启动时读回（`_PERSIST_KEYS` 只含安全字段，不含 `TUNE_*` 环境变量项） |
| **前端** | 在实时监测页**动任何控件**（勾检测项/拖置信度/改时长）都可能把两个开关按"内存里的值"推回后端 | `pushSettings()` 连带推送 `cloud_consult`/`cloud_review`；且 `loadSettings()` 是 **fail-open**（`d.cloud_consult !== false`，字段缺失就当 true） | ① 两个开关**只由各自控件单独推送**；② `loadSettings()` 只在**明确拿到布尔值**时回写，否则**置灰并提示**（绝不猜、绝不默认开） |

**验证**：重启后端 → `cloud_review=False cloud_consult=False`（保持住）`[三级]`；
`_uicheck\_run_cloudswitch.mjs` **4/4**（动其它控件后两个开关未被改动）`[三级]`。

### 11.2 违规抓拍取证"重复且无意义"：**根因是循环播放 + 时钟口径**

**用户原话**："实时检测的违规抓拍证据功能似乎存在不同步和重复的无意义的取证问题"。

| # | 发现 | 证据 | 修法 |
|---|---|---|---|
| **1** | **同一违规每圈重新取证** | `position` bbox 落在同一 40px 桶的记录 **141 条**，间隔稳定 **30/31 秒**（= 一圈墙钟），track_id 每次都不同（1,16,28,35,44…）。26 秒视频循环播 5 分钟 → 约 **9 条**内容几乎相同的"闯红灯" `[一级]` | 新增 `loop_dedup_sec`（默认 300s，**墙钟**）+「类型 + 位置(40px 网格，查 **3×3 邻域**)」指纹跨圈抑制；`/settings` 可调，设 0 关闭。**实测 9 条 → 3.4 条/5 分钟** |
| **2** | **视频时间变负 → 取证窗口错位** | 最近 400 条事件里 **14 条** `event_id` 带负号（`evt_-119350`/`evt_-231600`/`evt_-327250`…），最早 2026-10-06。成因：`start_detection()` 归零 `frame_count` 却漏了 `_loop_frame_base` → 新一轮视频时间是大负数 → 事件按"trigger_time ± 窗口"取帧时**取到上一圈的帧**（云端看到空路口 → rejected） `[一级]` | `start_detection()` 同步归零 `_loop_frame_base` |
| **3** | **落库时间戳是 1970** | 库里 **514 行** `trigger_time < 2000-01-01`（如 `1970-01-01 08:00:10`）。成因：事件 `trigger_time` 装的是**视频秒**（10.95），落库时直接 `datetime.fromtimestamp()` `[一级]` | 事件新增 `wall_time` 字段，落库改用它；修复后新建 5 条事件全部为正确墙钟 |
| **4** | **证据图同秒覆盖** | 文件名只到秒：`realtime_{类型}_{YYYYmmdd_HHMMSS}.jpg`；同秒同类违规后写的覆盖前一张，而两条 DB 记录指向同一文件名 → 其中一条图内容不对（证据可追溯是红线） | 文件名加毫秒并用 `-` 分隔（`..._HHMMSS-mmm.jpg`），列表接口正则同步放宽（**新旧 4 种文件名都已验证能正确解析**） |

**验证**：修复后跑「60s → 停止 → 再启动 90s」（正是产生负时间的序列）→ 新建 5 条事件：
`negative: 0   epoch(1970): 0   correct wall-clock: 5` `[一级]`。

> ⚠ **我在这条上犯过一个错并已回退**（如实登记）：我先把 `_now()` 的负值"兜成墙钟"，
> 结果更糟 —— `_now()` 是**视频时间**，混用后事件表出现 **1970 行**（比负数还糟）。
> 正确做法是"让视频时间不要变负 + 落库换墙钟"两件事，而不是在时钟函数里打补丁（T94）。

### 11.3 前端日志导出崩溃（用户实测报错）

**用户现象**：点导出 → `TypeError: Converting circular structure to JSON`（`component` → `vnode` 闭环）。

| 层 | 根因 | 修法 |
|---|---|---|
| ① | `push()` 里 `JSON.stringify(a)` 失败就把**原始对象**塞进 `extra` —— 等于存了颗定时炸弹 | `_safeJson()`：循环引用→`[Circular]`、DOM→`[DOM x]`、组件→`[VueComponent]`、函数→`[Function]`、bigint→`"5n"` |
| ② | 导出/落盘时再 stringify → 抛错（`persistNow` 的错还被 `try/catch` **静默吞掉** → 那条日志永远存不下来） | 导出改用 `_safeJson`；`extra` **只存字符串**；导出失败时**逐条降级导出**（绝不整份丢失） |
| ③ | **坑中坑**：我第一版用 `val instanceof Node` → 触发 **Vue 响应式 Proxy 的 getPrototypeOf 陷阱** → 目标不可扩展时**直接抛错** → 所有对象都变 `[Unserializable]`（实测导出仅剩 **18 字节**） | 改成**只用读属性**做鸭子类型（`typeof nodeName`/`$el`）；**禁止 `instanceof`/`getPrototypeOf`/`constructor`** |

**顺带新增**：日志页「**复制诊断摘要**」按钮（第 5 项取证要用；剪贴板不可用时自动改为下载 txt）。
**验证**：`_uicheck\_run_loggerexport.mjs` **6/6** —— 真实点击「导出 JSON」得到 5KB+ 合法 JSON、
19 条日志全在、无 `[Unserializable]`、落盘 JSON 合法 `[三级]`。

---

## 九、★第 4 项（两个框）执行记录 —— 2026-10-10 追加

### 9.1 修了什么

| 改动 | 位置 | 说明 |
|---|---|---|
| **多级关联替代 bbox 精确匹配** | `annotation_renderer._match_track_for_detection()` + `_build_track_index()`（新增，模块级） | ① `det['track_id']`（检测链路 `_attach_track_ids` 已回填）→ ② 精确 bbox（旧行为，兼容）→ ③ ±3 px 容差 → ④ IoU≥0.15 → ⑤ 中心距≤0.30×对角线。**`used_ids` 保证一个 track 只被一条 detection 占用**（否则两辆车会抢同一个 ID） |
| **灰框（用户口径）** | `annotation_renderer` 主绘制循环 + `_draw_direction_arrow(unknown=)` | 没拿到 track ID 的检测框：**灰框、不写任何文字、不画方向箭头**。三色分工：绿=已追踪正常 / 红=已追踪违规 / **灰=尚未追踪** |
| **消除"类名标签"** | 同上 | 旧代码在 `tid is None` 时把**原始类名**（`car`/`truck`）当标签 → 这正是用户"一会儿 ID、一会儿车型"的来源。现在 `minimal` 档下它**完全不再出现**（`standard`/`full` 档保留类名，属旧行为） |
| **★可观测（防复发）** | `annotation_renderer._BOX_STATS` + `get_box_draw_stats()` → `/status` 的 `box_draw_stats` | `main_boxes` / `fallback_boxes` / `unmatched_dets` / **`max_dets_per_track`**（>1 就是"会画重框"）/ `tracks_drawn`。**这类纯视觉回归以后可自动检测**，不必再靠肉眼 |
| 索引构建收敛为一处 | `render()` 内部 | 原来同一个函数里有两处几乎相同的 `track_boxes`/`bbox_to_track` 构建代码（改一处漏一处的隐患），现统一走 `_build_track_index()` |

**修法选择理由（设计单给了 A/B/C 三个方案）**：选 **B（改关联方式）**，因为
① 改动最小、不动判定链路（`_predict_boxes` 仍是"只改显示副本"）；
② 顺带修掉"框一动就关联不上"这类隐患；
③ 保留精确 bbox 路径，旧行为可回退。

### 9.2 验证证据

| 验证 | 结果 | 等级 |
|---|---|---|
| **单元验证（真代码路径）** `_scripts\_verify_two_boxes_fix.py` | **20/20 PASS**：预测关/预测开+有 track_id/预测开+无 track_id **各只画 1 个框**；两辆车两条检测=2 框无兜底；漏检测的车仍由兜底补画（不丢框）；**旧逻辑回放证明"预测开启时确实产生 2 个框"**（可复现的因果证据）；`render()` 真跑不抛异常 | 一级 |
| **三色方案** 同脚本第 5 节 | 灰框（无文字）/ 绿框+`ID18` / 红框+`ID18` 全部按预期；**"灰框零文字"用拦截 `draw_texts` 精确验证** | 一级 |
| **真数据/实时** `/status` 的 `box_draw_stats` | 多轮采样：`main=2 tracks=2 max_dets_per_track=1 fallback=0 unmatched=0` —— **主循环画了几个框就等于追踪了几辆车，没有第二遍兜底重画** | 三级 |
| **画面上人工核对**（无头 Edge 截 `/live` 视频区，1920×1080） | 一帧内 2 辆车各 1 个绿框 + `ID2`/`ID4`；**画面里 6 盆盆栽一个框都没有**；ROI 内 3 盏灯按灯色画（红/绿）、ROI 外的灯不画 | 三级 |
| 前端回归 | `check.mjs` **17/17**、`check2.mjs` **15/15** | 三级 |

### 9.3 ★被推翻 / 被补充的结论（追加 O42）

| # | 旧说法 | 更正 |
|---|---|---|
| **O42** | 我按设计单 §12.3 认定"用户看到的就是两个框重叠"，并据此修完 | **机制没修错，但用户的现象有两层**。第二层是"同一辆车一会儿 `ID18`、一会儿 `car`"——关联失败的过渡帧把**原始类名**当标签画了。用户 2026-10-10 亲自更正："有时候会显示ID，有时候会显示车辆类别，我还以为是两个识别框重叠了"。**教训：用户的现象描述是线索不是结论；修完要请用户再看一次** |

### 9.4 过程中我自己踩的坑（如实登记）

| # | 坑 | 后果 / 修法 |
|---|---|---|
| 1 | 统计代码里 `for _t, v in ...` **遮蔽了函数开头的 `import time as _t`** | `render()` 末尾 `_t.perf_counter()` 抛 `AttributeError`，**渲染直接失效**（被我的单元测试第 4 节抓住）。改名 `_tk` |
| 2 | 我在 `annotation_renderer` 用了 `Any` 但没 import | `NameError`（启动即崩）。补进 `from typing import` |
| 3 | `PowerShell` 的 `Get-Content ... -replace ... \| Set-Content` **把 UTF-8 中文写成乱码** | 我的验证脚本被自己弄坏 → 用 write 工具整份重写。**以后禁止用 PS 管道改含中文的源文件** |
| 4 | 我为了清理自己开的测试浏览器窗口，**误杀了用户正在用的 Chrome/Edge** | 已向用户致歉；**改用无头 Playwright（`channel:'msedge'`, headless）**，不再碰用户的浏览器 |
| 5 | 跨进程读 `realtime_detector` 单例拿到空数据（我的探针 import 出的是**另一个实例**） | 改为走 HTTP `/status` 的新字段；进程内验证则用真对象直接调 |

---

## 十、⚠ 本轮新发现：后端被 `cv2` 自带 FFmpeg 解码器拖崩（**未修，需用户定**）

| 项 | 内容 |
|---|---|
| **现象** | 后端进程**突然消失**（不是 Python 异常、日志无 traceback、无 uvicorn 错误） |
| **证据（一级）** | Windows 事件日志两条完全相同的记录：`出错应用程序 python.exe` / **`出错模块 opencv_videoio_ffmpeg500_64.dll`** / **`异常代码 0xc000001d`（STATUS_ILLEGAL_INSTRUCTION）** / 同一偏移 `0x2e9930`；时间 2026-10-10 **00:11:52** 与 **00:33:44**；同期生成 288 MB / 290 MB 崩溃转储 |
| **性质** | **原生崩溃**，发生在 `cv2.VideoCapture` 的 FFmpeg 解码路径里 —— **与我本轮改的 Python 代码无关**（我不碰解码；所有原生帧都在 0x2e9930 同一处） |
| **可疑触发条件** | 两次崩溃都出现在"**同时**开着 MJPEG 客户端 + 检测在跑"时；`RT_TRACE_JSONL` 也在场（但崩溃点在解码器，不是在写 trace 的地方） |
| **影响** | 演示中途后端会**静默死掉**（用户会看到"像断网"）。⚠ 与 §12.1 那条"MJPEG 僵尸流占满线程池"**不是一回事**：那条是"变慢"，这条是"进程没了" |
| **建议** | ① 先用 `restart-backend.bat` 正常方式复现，确认是否稳定出现；② 若复现，考虑换解码后端（`cv2.CAP_FFMPEG` → `CAP_DSHOW`/`CAP_MSMF`）或改用项目已有的 `imageio_ffmpeg` 7.1 抽帧；③ **不要**把它和 MJPEG 线程池问题混在一起修 |

> 本轮我是用 `cmd start` + 显式 `TUNE_*` 环境变量起后端的（等价于 `.bat`）。
> 崩溃后我重启并继续验证，**当前实例是好的**（见 §九 的实时采样）。

---

## 七、交接自检（协议 §9.4）

- [x] 只读 3 个文件能否知道"项目有什么功能" → `_PROJECT_MAP.md` 已补本轮 4 项能力（§一 第 9/10 条 + §二 表项）
- [x] 能否知道"上一步做到哪、下一步做什么" → `_SESSION_HANDOFF.md` §二 已更新
- [x] 能否知道"哪些结论已被推翻" → 本文 §四 + §9.3（**O36~O43**；其中 O40/O41 是我自己本轮的两次错判）
- [x] 交接文件里的路径是否都真实存在 → 逐个核对（见 §八）
- [x] 是否把"推断"写成"事实" → 所有断言都标了等级；未验证项（R2/R3）如实登记为"未动"

## 八、本轮涉及文件（完整绝对路径）

**改动的代码**

| 文件 | 改动 |
|---|---|
| `E:\output\1\api\realtime_detector.py` | 热重载三方法 + `_filter_traffic_classes` + 绘制侧 ROI 过滤 + `/status` 6 个新字段 + `_TL_LIGHT_NAMES` |
| `E:\output\1\api\image_recognizer.py` | 新增 `TRAFFIC_CLASS_WHITELIST`（41 类） |
| `E:\output\1\api\annotation_renderer.py` | 新增 `TRAFFIC_LIGHT_CLASS_NAMES`，主循环改用它 |
| `E:\output\1\web-admin\src\views\LiveMonitor.vue` | 干掉硬编码源 + `runningSource`/`calSrc`/`sourceMismatch` + `.src-bar` + 修 `sc` + `watch(calSrc)` |
| `E:\output\1\web-admin\src\views\CalibrationPanel.vue` | `source` 语义明确 + `.cal-alert` 红警告 + 保存闸门 + 越权勾选 |

**新增的验证脚本**（可复跑）

| 文件 | 用途 | 耗时 |
|---|---|---|
| `E:\output\_scripts\_verify_hotreload_and_filter.py` | 后端自校验 25 项（临时目录，零副作用） | ~30 s |
| `E:\output\_scripts\_verify_fixes_e2e.py` | 端到端 HTTP 探针（真跑演示视频，自动恢复运行状态） | ~60 s |
| `E:\output\_scripts\_verify_trace_roi_filter.py` | trace 逐帧核算 ROI 过滤 + 判定自洽 | ~5 s |

**数据 / 证据**

- `E:\output\_rt_trace_roi_filter_20261010.jsonl`（73 帧，本轮 ROI 过滤的逐帧铁证）
- `E:\output\1\api\output\scene_configs\dual_cam_demo_lossless_4744a9bf2226.json`（演示源的标定，4 个 ROI）
- `E:\output\_uicheck\result.json` + 截图（`check.mjs` 17/17）
- 报告修订：`E:\output\_PROJECT_MAP.md`（新增 T81~T88、O36~O43）、`E:\output\_SESSION_HANDOFF.md`
