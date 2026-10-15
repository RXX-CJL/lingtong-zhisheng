# TASK-COORD-005 执行报告（Trae IDE）

## 0. 元信息

| 项 | 值 |
|---|---|
| 任务书 | docs/PROMPT_TRAE_TASK-COORD-005.md |
| 执行者 | Trae IDE（GLM-5.3-Flash） |
| 执行日期 | 2026-09-25 |
| 起始 Git HEAD | main @ 4a67b5a |
| 最终判定 | **ACCEPT** |

## 1. 结论

EventDetail 两个已定位问题（视频 FMP4 编码 Chromium 无法解码、key_frames 占位符 404）已修复，并同时覆盖：
- **未来事件生成路径**（代码修复 + 单测/冒烟验证）
- **现有 7 个真实事件**（H.264 兼容副本 + 21 张真实 JPG 关键帧 + DB 更新，原始 FMP4 全部保留）

浏览器（Chromium 内核）实测：视频实际播放成功、3 张关键帧全部渲染真实画面。判定 **ACCEPT**。

## 2. 根因与修复方案

### 2.1 视频编码问题
- 根因：`save_event_video` 用 OpenCV `mp4v` fourcc 产出 **FMP4** 编码，Chromium 不支持（`video.error.code=4` MEDIA_ERR_SRC_NOT_SUPPORTED）。
- 环境探测结论：OpenCV 原生 H.264 不可用（缺 openh264 DLL，下载链路全失败）；**imageio-ffmpeg 自带 ffmpeg 7.1 + libx264 实测可用**（任务书要求"必须实际验证编码器输出"，已按此执行）。
- 修复（`api/circular_frame_buffer.py`）：
  - 新增模块级 `_get_ffmpeg_exe()`（imageio_ffmpeg → PATH 兜底）与 `_transcode_to_h264()`（libx264 + yuv420p + faststart，奇数尺寸自动缩偶，120s 超时，任何失败返回 False）。
  - `save_event_video` 改为三段式：① mp4v 写入 `{output_path}.tmp.mp4` 临时文件 → ② ffmpeg 转码 H.264 到 `output_path`（成功则删临时文件）→ ③ 转码失败回退保留 mp4v（功能不中断）。**调用方契约不变**（返回路径即 DB 记录路径）。

### 2.2 关键帧占位符问题
- 根因：`_pick_key_frame_paths` 返回 `["frame_0", ...]` 字符串占位符，前端拼接后请求 404。
- 路径契约追踪结论：前端 `getEventFrameUrl`（web-admin/src/api/index.js:334）将非 URL 值归一化后拼到 `BACKEND_DIRECT_URL/{path}`；后端静态挂载 `/event-videos` → `Config.EVENT_VIDEO_DIR`。因此 DB 必须存 `event-videos/{YYYYMMDD}/{file}.jpg` 形式（正斜杠相对路径）。
- 修复（`api/realtime_detector.py`）：
  - `_pick_key_frame_paths(clip, event_id, save_dir)` 从真实 clip 取首/中/尾帧，`cv2.imencode` 写 JPG 到事件视频同目录，返回 `event-videos/...` 相对路径；跨盘符场景 relpath 抛 ValueError 时按目录名兜底；全部失败返回空列表（**不返回占位符**）。
  - 调用点（L583）传入 `event_id` 与视频所在目录。

## 3. 现有 7 事件迁移（tests/migrate_existing_events_f5.py）

结果：**ok=7 skip=0 fail=0**

| 事件 | 原始 FMP4（保留） | H.264 副本 | 帧数 | 关键帧 |
|---|---|---|---|---|
| evt_..._10_6a490c | 4,380,109B ✓ | 1,651,581B | 299 | 3 张 |
| evt_..._2_baecaf | 4,380,109B ✓ | 1,651,581B | 299 | 3 张 |
| evt_..._19_fca8c3 | 4,867,911B ✓ | 1,854,736B | 299 | 3 张 |
| evt_..._16_6a49bc | 4,867,911B ✓ | 1,854,736B | 299 | 3 张 |
| evt_..._20_4ff131 | 3,720,815B ✓ | 1,200,151B | 300 | 3 张 |
| evt_..._40_305b53 | 3,720,815B ✓ | 1,200,151B | 300 | 3 张 |
| evt_..._39_ee9ac0 | 3,720,815B ✓ | 1,200,151B | 300 | 3 张 |

- 副本命名 `{event_id}_h264.mp4`（新文件名），fourcc 实测 = h264。
- 关键帧从原视频真实帧提取（首/中/尾），命名 `{event_id}_frame_{idx}.jpg` 与新代码约定一致。
- DB 更新：`event_video_path` → H.264 副本绝对路径；`key_frames` → `event-videos/20260925/...jpg` JSON 数组。终态验证 7/7：video_exists=True、files_ok=True、placeholder=False。

## 4. 验收标准逐条核对

| # | 任务书验收标准 | 结果 | 证据 |
|---|---|---|---|
| 1 | 新事件编码方案有代码证据 + 实际编码验证 | ✅ | circular_frame_buffer.py `_transcode_to_h264`；冒烟/单测产物 fourcc=h264（非假设，实测） |
| 2 | 至少一个事件在 Chromium 实际播放成功 | ✅ | evt_..._2_baecaf：readyState=4、error=null、`v.play()` 后 currentTime 0→5.905s、paused=false、画面渲染真实交通场景（截图 task_coord_005_eventdetail_verified.png） |
| 3 | 7 事件 key_frames 不再是占位值 | ✅ | DB 终态 7/7 placeholder=False；单测 test_02 断言 `^frame_\d+$` 占位符为零 |
| 4 | 三张关键帧 200 且显示 | ✅ | 接口/静态挂载 200（image/jpeg 90KB）；浏览器 3 张 960x432 naturalWidth>0 全部渲染（截图 task_coord_005_keyframes_verified.png） |
| 5 | 原始 FMP4 保留 | ✅ | 7 个原始文件均在且尺寸未变；单测 test_04 断言 `_h264.mp4` 旁必有原始 mp4 |
| 6 | 测试 + 构建通过 | ✅ | 定向测试 18/18 OK；vite build ✓ 8.93s |
| 7 | 判定 ACCEPT/PARTIAL/BLOCKED/REJECT | **ACCEPT** | 以上全部满足 |

补充接口验证（curl）：事件列表 200；`/video` 200 video/mp4 1,651,581B；`/frames` 返回 3 条真实相对路径；静态 JPG 200；静态 H.264 mp4 200；Range 请求 206（浏览器流式播放前提）。

## 5. 修改清单（Git 核实）

**本次授权范围内修改：**
- `api/circular_frame_buffer.py`（+90 行）：转码函数 + save_event_video 三段式
- `api/realtime_detector.py`（+54 行）：_pick_key_frame_paths 真实 JPG + 调用点
- `api/zhitong_violations.db`：7 事件两个字段更新（任务书明确授权）
- 新增 `tests/test_event_media_contract.py`（9 个用例）、`tests/migrate_existing_events_f5.py`、`tests/smoke_f4_media_pipeline.py`
- 新增 `api/output/event_videos/20260925/` 下 7 个 `_h264.mp4` + 21 张 JPG（原始文件未删除）

**非本次修改（既有未提交，未触碰）：**
`_TASK-029-M09_integration_selfcheck.json`、`api/rule_engine/plugins/traffic_plugin.py`（DSH TASK-COORD-003 遗留）、`tests/test_traffic_plugin_contract.py`、docs/ 下既有任务书与报告等。

**未修改**：TrafficPlugin/TrafficEventEngine/YOLO/Tracking/云端 AI 判定逻辑、数据库结构、EventCenter、启动脚本、API 契约（get_event_video/get_event_frames 路由零改动）。

## 6. 测试证据

| 套件 | 结果 |
|---|---|
| tests/test_event_media_contract.py（新增，9 用例：DB 契约×5 + 未来路径×3 + 空片段） | **9/9 OK**（2.46s） |
| tests/test_circular_frame_buffer.py（既有） + 上者合跑 | **18/18 OK**（2.32s） |
| tests 全量 discover（56 tests） | 55 通过 + 1 个**既有**收集错误 |
| 冒烟 tests/smoke_f4_media_pipeline.py | PASS（ffmpeg 定位/H.264 产物/关键帧落盘） |

全量 discover 的唯一错误：`test_core` 因环境未安装 pytest 无法导入（ModuleNotFoundError）——**既有问题，与本任务无关**；按规则 5 未擅自安装依赖，报请指挥官决定。

## 7. 环境变更声明

- f2 阶段经指挥官流程安装 **imageio-ffmpeg**（清华 PyPI 镜像），为本任务核心相关依赖（提供 libx264 编码器），非无关依赖。`api/requirements.txt` 未改动（imageio-ffmpeg 若需固化请指挥官批准后追加）。
- 前后端服务已全部停止，8001/5173 端口确认释放（REMAINING_LISTENERS=0）。

## 8. 遗留问题与建议（不阻塞本任务）

1. **test_core 依赖 pytest**：环境未装 pytest，该文件无法收集；建议统一测试运行器或经批准安装。
2. **requirements.txt 未含 imageio-ffmpeg**：换机复现需 `pip install imageio-ffmpeg`；建议固化。
3. **既有记录级问题（TASK-COORD-004 §8 遗留）**：豆包 AI 无有效输出、秒/毫秒时间戳不一致、短视频源全速读取导致 processed=1——均不在本任务范围。
4. 转码参数（crf=23/veryfast）如需更小体积或更快速度可后续调优；当前 300 帧约 1.2-1.9MB，单事件转码耗秒级。

## 9. 结果文件

- 本报告：docs/REPORT_TASK-COORD-005_TRAE.md
- 结果 JSON：e:\output\_TASK-COORD-005_OUTPUT.json
- 截图：task_coord_005_eventdetail_verified.png（视频播放）、task_coord_005_keyframes_verified.png（关键帧画廊）
