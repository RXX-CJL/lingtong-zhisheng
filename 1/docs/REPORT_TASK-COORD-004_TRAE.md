# TASK-COORD-004 报告：真实交通视频最小闭环验证

> 执行 Agent：Trae IDE
> 日期：2026-09-25
> 性质：运行验证。未修改任何业务代码/测试/数据库结构/配置/前端/API 路由/启动脚本。唯一新增报告文件为本文件；验证过程按授权产生了真实事件记录与事件视频（清单见 §6）。
> Git：main @ 4a67b5a；验证前后 DSH 未提交改动（traffic_plugin.py、test_traffic_plugin_contract.py）原样保留；`git diff --check` EXIT=0；目标业务文件无任何新增改动。

## 0. 最终判定：**PARTIAL**

E 级闭环已打通至"真实视频 → YOLO → Tracking → TrafficPlugin → TrafficEventEngine → 事件视频 mp4 → traffic_events → FastAPI → EventCenter"，**但 EventDetail 中事件视频无法在浏览器播放（编码格式不兼容）、关键帧加载失败（占位路径）**，按验收标准从严判 PARTIAL 而非 ACCEPT。

## 1. 证据等级汇总

| 环节 | 等级 | 证据 |
|---|---|---|
| 5 个视频元信息检查 | D | §2 全部可读、非黑屏 |
| 后端启动 + /health | C | HTTP 200 `{"status":"healthy","overall":"ok","yolo_available":true,"dashscope_available":true}` |
| 视频读取 + YOLO + Tracking | D | total_frames=11071（真实视频全量读取）、processed_frames=15、tracked_vehicle_count=9、violation_count=9 |
| TrafficPlugin → 引擎触发事件 | D | 事件引擎 total_events=7（6 speeding + 1 wrong_way），active_events=7 |
| 事件视频落盘 | D | 7 个 mp4（3.7~4.9MB，299-300 帧 @10fps，cv2 全部可读） |
| traffic_events 落库 | D | sqlite 实查 7 行，event_video_path 指向真实 mp4 |
| 事件列表/详情/视频/关键帧接口 | C | 列表 total=7；详情 200；video HTTP 200/206（video/mp4 4867911B）；frames count=3 |
| EventCenter 列表展示 | E | 浏览器实测 7 行真实事件 + 截图 |
| EventDetail 详情展示 | E（部分） | 事件信息/状态时间线/复核区正常；**视频播放失败 + 关键帧加载失败**（§7） |
| 云端 AI 复核 | C（执行了，结果不可用） | 豆包无有效输出 → DeepSeek 判"需人工、置信度 0"，7 事件停在 pending_ai |

## 2. 视频元信息（步骤 3）

命令：conda env `zhitong-gpu`（Python 3.11.15）+ cv2 枚举读取：

| 文件（E:\output\1\test_assets\traffic_videos\） | 分辨率 | fps | 帧数 | 时长 | 大小 | 首帧/中帧亮度均值 |
|---|---|---|---|---|---|---|
| 3a3f1dd6…mp4 | 1280x576 | 24 | 168 | 7.0s | 0.3MB | 79.4 / 87.9 |
| 3e9b3f65…mp4 | 960x432 | 15 | 11071 | 738.1s | 126.3MB | 61.4 / 63.3 |
| 701c5154…mp4 | 1280x576 | 24 | 479 | 20.0s | 1.0MB | 86.0 / 89.2 |
| ea1ca6cb…mp4 | 1280x576 | 24 | 248 | 10.3s | 0.5MB | 89.8 / 105.4 |
| f640e913…mp4 | 1280x576 | 24 | 196 | 8.2s | 0.4MB | 89.8 / 83.4 |

**样本选择**：先跑 701c5154（20s）——结果 total_frames=479 在 ~20s 内全速读完、processed_frames=**1**（YOLO 首帧加载 + FRAME_RATE=3 限速），无法建立轨迹，未触发事件；**改用 3e9b3f65（12.3 分钟长视频）**成功触发。短样本不可用的根因见 §8 问题 1。

## 3. 启动环境与健康检查（步骤 4）

```text
启动命令（cwd=E:\output\1\api）：
C:\miniconda\envs\zhitong-gpu\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8001
GET /health → 200 {"status":"healthy","version":"2.0.0","yolo_available":true,
                   "dashscope_available":true,"uploads_dir_exists":true,"db_exists":true,"overall":"ok"}
```

## 4. 检测启动与过程记录（步骤 5、6）

命令（未改写任何业务入口，直接用既有接口）：

```text
POST /api/realtime/stop        （先停 701c5154 的首轮）
POST /api/realtime/start  {"camera_index":0,"video_path":"E:\\output\\1\\test_assets\\traffic_videos\\3e9b3f659e257969d581993be3c9e59e.mp4"}
→ {"success":true,"message":"检测已启动"}
```

GET /api/realtime/status 关键采样：

| 时刻 | total_frames | processed | tracked | violations | active_events | 引擎状态 |
|---|---|---|---|---|---|---|
| +20s（701c5154 短样本） | 479 | 1 | 1 | 0 | 0 | total=0 |
| 长样本 +60s | 11071 | 15 | 9 | 9 | **7** | total=7，pending_ai=7 |

注：`/status` 报告 frame_buffer_duration=0.36s（处理速率 3fps 下 300 帧缓存窗口换算），但 `extract_event_clip` 实际产出 299-300 帧 ≈30s 片段（缓存按帧数计，非按墙钟秒数）。

## 5. 数据库与接口验证（步骤 7）

sqlite 实查（`api/zhitong_violations.db`，GET /events 触发 `_sync_active_events_to_db` 后）：

```text
traffic_events rows = 7
evt_1790324866083_2_baecaf  | speeding  | track=2  | pending_ai | video=E:\output\1\api\output\event_videos\20260925\evt_..._2_baecaf.mp4
evt_1790324866083_10_6a490c | speeding  | track=10 | pending_ai | ...6a490c.mp4
evt_1790324869127_16_6a49bc | speeding  | track=16 | pending_ai | ...6a49bc.mp4
evt_1790324869127_19_fca8c3 | speeding  | track=19 | pending_ai | ...fca8c3.mp4
evt_1790324873606_20_4ff131 | wrong_way | track=20 | pending_ai | ...4ff131.mp4
evt_1790324876514_39_ee9ac0 | speeding  | track=39 | pending_ai | ...ee9ac0.mp4
evt_1790324876514_40_305b53 | speeding  | track=40 | pending_ai | ...305b53.mp4
```

接口实测（Invoke-WebRequest）：

```text
GET /api/realtime/events?page=1&size=10        → 200 total=7（6 speeding + 1 wrong_way）
GET /api/realtime/events/evt_..._16_6a49bc     → 200，event_video_path 已设置，key_frames=3
GET /api/realtime/events/evt_..._16_6a49bc/video → 200 video/mp4 4867911 bytes（浏览器侧 206 Partial Content 亦正常）
GET /api/realtime/events/evt_..._16_6a49bc/frames → 200 count=3
```

mp4 可读性（cv2）：7/7 可读，299-300 帧 @10fps，960x432，FOURCC=**FMP4**（MPEG-4 Part 2）。

## 6. 本轮验证新增数据与文件（授权范围内产物）

- `api/output/event_videos/20260925/`：7 个 mp4（evt_1790324866083_2_baecaf / _10_6a490c、evt_1790324869127_16_6a49bc / _19_fca8c3、evt_1790324873606_20_4ff131、evt_1790324876514_39_ee9ac0 / _40_305b53；共约 29.5MB）
- `api/zhitong_violations.db` traffic_events 表：新增 7 行（如上）
- 未删除/覆盖任何原有记录或文件；未触碰其他 Agent 未提交改动

## 7. 前端验证（步骤 8，浏览器实测）

前端：`npm run dev`（cwd=web-admin）→ http://localhost:5173/ 200。浏览器（Chromium 内核）实测：

**EventCenter（/events）——通过**：
- 统计卡：活跃事件 7、待 AI 分析 7、待人工复核 0、已确认违法 0
- 表格"交通事件列表（共 7 条）"渲染 7 行：6 行"超速" + 1 行"逆行"（TYPE_MAP 中文映射正常），每行含车辆 ID（#2…#40）、摄像头 cam_0、触发时间、"待AI分析"状态与详情按钮
- 截图：`browser_take_screenshot('evidence_eventcenter_list.png')`（浏览器截图目录 shot-20260925-083115…jpg）

**EventDetail（/events/evt_1790324873606_20_4ff131）——部分通过**：
- 正常：标题"⏳ 等待云端 AI 分析"、事件类型"逆行"、车辆 #20、状态"待AI分析"、证据链状态时间线（已触发→录制中→待AI分析）
- 失败 1：`<video>` 元素 error.code=4（MEDIA_ERR_SRC_NOT_SUPPORTED），页面显示"视频加载失败/视频文件不存在或格式不支持"。**接口层正常**（HTTP 206 Range 响应正常），根因是 mp4 编码为 FMP4（MPEG-4 Part 2，OpenCV mp4v 写入），Chromium 不解码该编码
- 失败 2：关键帧 3 张全部"加载失败"。后端日志实锤：`GET /frame_0 404`、`GET /frame_150 404`、`GET /frame_299 404` —— key_frames 为占位字符串（`["frame_0","frame_150","frame_299"]`），前端拼接出 `http://localhost:8001/frame_0` 无效 URL
- 失败 3（记录）：状态时间线时间戳显示 1970-01-22（秒/毫秒单位错配）

## 8. 发现的额外问题（只记录，未修复）

| # | 文件/模块 | 问题 | 阻塞本任务 | 建议 |
|---|---|---|---|---|
| 1 | `api/realtime_detector.py` L306-309（`_detection_loop`） | 视频文件源为**全速读取**（cap.read 无播放速率限制），短视频（<1min）在处理链建立轨迹前就读完；701c5154 仅 processed=1 | 否（改用长视频绕过） | 后续 TASK：视频源按帧间隔节流读取 |
| 2 | `api/circular_frame_buffer.py` / `realtime_detector.py` L579 | `save_event_video` 用 mp4v/FMP4 编码，浏览器（Chromium）不支持 → EventDetail 视频播放失败（error code 4） | **是（阻塞 E 级完整 ACCEPT）** | 后续 TASK：改用 avc1/H.264（OpenMP4 支持 `avc1` 需 openh264）或转码 |
| 3 | `api/realtime_detector.py` L629-643（`_pick_key_frame_paths`） | key_frames 写入占位字符串 `frame_0/frame_150/frame_299` 而非真实 jpg 路径 → 前端请求 `/frame_0` 404 | **是（阻塞 E 级完整 ACCEPT）** | 后续 TASK：落盘真实关键帧 jpg 并写实际路径 |
| 4 | `api/cloud_collaborator.py`（analyze_event 链路） | 7 事件全部 PENDING_AI 不流转：日志显示豆包视觉"未返回任何有效分析内容"，DeepSeek 判"需人工、置信度 0"；apply_ai_result 后状态仍 pending_ai（疑似"无法确定"分支未映射或异常被吞） | 否（不阻塞闭环验收） | 后续 TASK：排查豆包输入帧格式与 apply_ai_result 状态映射 |
| 5 | `web-admin/src/views/EventDetail.vue`（时间线） | state_history 时间戳按毫秒解析秒级 epoch → 显示 1970-01-22 | 否 | 后续 TASK：统一秒/毫秒 |
| 6 | `api/config.py:19` vs `api/database.py:7` | DB 路径矛盾（TASK-COORD-002 已记录，本轮再次确认影响面） | 否 | 独立 TASK |

## 9. 服务停止与 Git 终态（步骤 10、11）

```text
POST /api/realtime/stop → {"success":true,"message":"检测已停止"}
停 node（PID 40660, port 5173）、停 python（PID 25700, port 8001）
port 5173 after_stop=False；port 8001 after_stop=False   ← 全部释放
git branch: main；git status 计数 21（验证前 19 + 新增本报告 + event_videos 下 gitignore 产物）
git diff --check EXIT=0
业务文件（realtime_detector/traffic_event_engine/traffic_plugin/realtime.py/models/config/database/EventCenter/EventDetail/api.index）无任何改动
DSH 未提交改动原样保留：M 1/api/rule_engine/plugins/traffic_plugin.py、?? 1/tests/test_traffic_plugin_contract.py
```

## 10. 尚未验证的事项

1. 云端 AI 复核完成后的 CONFIRMED/REJECTED/MANUAL_REVIEW 状态流转与前端状态更新（当前全部停在 pending_ai，见 §8.4）
2. EventDetail 中事件视频在浏览器的实际播放（受编码阻塞）；人工复核按钮的端到端写入
3. 闯红灯事件（traffic_light_state 检测依赖 YOLO 检出 red/green 类别，本次视频未检出红绿灯类，仅触发超速/逆行）
4. K230/CARLA/小程序等旁路（超出本任务范围）

## 11. 结论

真实数据闭环 **D 级全部达成**，E 级达成 EventCenter 侧（列表展示真实事件），EventDetail 侧因 mp4 编码不兼容与关键帧占位符两个明确根因未完整达成。判定 **PARTIAL**。修复 §8.2、§8.3 两项后，预期无需重跑检测即可通过浏览器回放已落盘的 7 个事件达成完整 E 级（建议作为下一个 TASK）。

---

【本次任务模型信息】

- 实际使用模型：GLM-5.3-Flash
- 任务复杂度：L4
- 模型选择理由：跨 YOLO→Tracking→事件引擎→数据库→FastAPI→前端的多层实时链路运行验证，需在"检测状态异常→样本策略调整→根因定位（编码/占位符/秒毫秒）"中做大量跨文件推断与实时决策，属 L4；使用当前可用高能力模型完成，未降低能力。
- 是否发生模型切换：否
- 切换原因：不适用。全程未遇到可靠完成跨文件分析的能力瓶颈。
