# 智瞳灵声 · 项目能力清单（_PROJECT_MAP.md）

> 最后更新: **2026-10-23（管理端前端图表 T50-T53 已全部修复并三级验收：中文映射收敛为单一来源 / 环形→横向排序条形 / echarts 亮色主题生效 / 排行卡换审核状态分布）** / 维护规则见 `_DSH_WORK_PROTOCOL.md` §4.4
> 本文件用途：新 AI **先读 `E:\output\_AI_COMMON_RULES.md`，再读本文件**，5 分钟内了解项目已有能力，避免重复造轮子。
>
> **证据等级标注**：`[一]` = 命令结果 / `[二]` = 文件状态 / `[三]` = 真实行为（最强）。未标注者为代码静态阅读所得（介于一级与二级之间）。
> **本文件不是文件树**，是"能用的能力"清单：每条写清 模块名 / 干什么 / 核心类或函数 / 是否在实时链路 / 谁调用它。
>
> **本轮新增（2026-10-10 第七轮）**：
> `RealtimeViolationDetector._maybe_reload_scene_annotation()`（**场景标注热重载**，标定保存后无需重启）、
> `_filter_traffic_classes()` + `image_recognizer.TRAFFIC_CLASS_WHITELIST`（**检测类白名单**，挡掉盆栽等 83 个无关 COCO 类）、
> `_draw_detection_boxes()` 里的**绘制侧 ROI 过滤**、
> `annotation_renderer.TRAFFIC_LIGHT_CLASS_NAMES`（红绿灯类名唯一权威名单）、
> `_match_track_for_detection()` + `_build_track_index()`（**"每辆车两个框"根治**）、
> **三色框**（绿=正常 / 红=违规 / **灰=尚未追踪，无文字**）、
> `box_draw_stats`（绘制侧关联统计，让这类视觉回归可自动检测）、
> **运行时设置持久化 `api/output/runtime_settings.json`**（重启不再重置付费开关）、
> **跨圈重复取证抑制 `loop_dedup_sec`**（同一车同一位置 5 分钟内只报一次）、
> **事件墙钟 `wall_time`**（修掉 1970 时间戳）+ `_loop_frame_base` 归零（修掉负时间）、
> **证据图文件名加毫秒**（修掉同秒覆盖）、`utils/logger.js` 的 `_safeJson`（修掉导出崩溃）、
> `CalibrationPanel.vue` 的**源闸门**（源不一致红警告 + 禁止保存）、`LiveMonitor.vue` 干掉硬编码默认源 + 云端开关拆开推送。
> 结论报告：`_design_2026-10-09_verdict.md`（含被推翻的旧结论 **O36~O39、O42~O43**；O40/O41 是 DSH 自己的两次错判，另登记在 T76/T86）。


---

## 一、30 秒速览（这个项目能做什么）

**一句话**：智瞳灵声 CityGuardian 是一套"端—云—边"协同的**城市交通违法智能取证与事件管理平台**——本地轻量模型做初筛、云端大模型做复核、K230 做边缘补盲，前端 Web 管理后台 + 数字孪生 + 微信小程序三端呈现，最终产出**可追溯的完整证据链**（而不是仅一个 AI 判断结果）。

**5 条要点**：

1. **实时违规检测链路是通的**：`RealtimeViolationDetector`（`api/realtime_detector.py`，2346 行）单帧走完 采集 → YOLO 多模型 → 追踪 → 规则引擎 + 行为引擎 → 红绿灯 CNN 判色 → 中文标注 → 事件状态机 → 证据链落库 → 微信推送。`[三]` 升级为最新视频后 520 帧端到端跑通，`red_light` 首次被判出（修复前恒 0）。
2. **红绿灯判色已有自训 CNN**（4 类 green/red/yellow/none），另有一套完整的"发光区定位 + 通道比"备选实现（已写未接）。
3. **视频测速标定已有完整模块**（`speed_calibration.py`，722 行）：3 类人工标定 + 地面单应反投影 + 帧率补偿表 + 物理防护阈值 + "未标定不判超速"门禁。**不要再自己推导数学。**
4. **规则引擎是可插拔多场景的**：`rule_engine/` 下 traffic / urban_management / public_security 三个插件默认全部启用，还有独立的交通事件 8 状态机 + 30 秒视频循环缓存 + 证据链持久化。
5. **后端共有 132 个 REST 接口 + 1 个 WebSocket**（2026-10-06 新增 `POST /api/scene/calibration-preview`；运行中的实例需重启后 openapi 才会显示 132），覆盖违规/设备/申诉/统计/端云协作/实时/场景标注/微信小程序 8 大域；数据库 12 张表、`violation_evidences` 已积累 2393 行、`traffic_events` 2552 行。`[一]`
6. **视频测速标定已于 2026-10-06 修正并验证**：`make_unprojector()` 的相机基符号错误已修（旧版只有画面最下 11% 像素可反解），测速改用"端点反投影求地面距离"；真实渲染帧实测反投影 **0.84 m**、匀速车速误差 **−2.7%~+5.6%**。前端标定契约见 `_speed_calibration_verdict.md` §五。
7. **★管理端已有标定界面**（`web-admin/src/views/CalibrationPanel.vue`）：信号灯 ROI 框选 / 停止线 / 相机参数 4 项 / 地面标定点 / 量距 / 参数校验。真实浏览器行为验证 **17/17 PASS**（`E:\output\_uicheck\check.mjs`）。
8. **★云端 AI 复核有总开关了**：运行时 `cloud_review`（前端「云端AI复核」勾选）。关闭后事件走 `RECORDING → PENDING_AI → MANUAL_REVIEW`，**零云调用**，等人工在事件中心点一下。`_redlight_demo_final.md` 时代的"每次都打豆包+Claude+DeepSeek"已可一键关停。
9. **★标定真的是"存了就生效"了（2026-10-10）**：后端按场景配置文件的 **mtime+size 热重载**，保存后**无需「停止→开始」**——实测检测运行中保存，下一帧即用新 ROI（`/status` 的 `scene_annotation_reload_count` 自增）。而且**标定面板只认"后端正在跑的源"**（不再是输入框文本），源不一致时红警告并禁止保存 —— 根治"在错画面上标、存到错的视频"。
10. **★画面干净了两处（2026-10-10）**：① **绘制侧 ROI 过滤** —— 只画 ROI 内的信号灯（判色链路完全不动）；② **检测类白名单** `TRAFFIC_CLASS_WHITELIST` —— 盆栽/消防栓/运动球等非交通类在检测出口就被裁掉（实测每帧挡掉约 2 个 `potted plant`）。
11. **★识别框不再重复、且颜色分工明确（2026-10-10）**：**每辆车只会画一个框**（修掉我上一轮"框预测"引入的两个框回归）；框色三档一眼可辨 —— **绿=已追踪正常 / 红=已追踪违规 / 灰=尚未追踪（无任何文字）**。这套"绘制侧关联"还暴露成 `/status` 的 `box_draw_stats`，**这类纯视觉回归以后可以被自动检测**。

---

## 二、后端模块总表

> 目录：`E:\output\1\api\`（相对路径以该目录为基准）
> **"在实时链路?"** 的判定方法：查 `realtime_detector.py` / `app.py` / `routers\` 是否有 import 或调用点，**并给出具体行号**。

### 2.1 ★实时检测链路内（每帧或按帧按需执行）

| 模块 | 用途 | 核心类/函数 | 在实时链路? | 谁调用它（证据） | 大小 / 最后修改 |
|---|---|---|---|---|---|
| `realtime_detector.py` | **实时违规检测主循环**：采集→检测→追踪→判定→判色→标注→事件→落库→推送 | `RealtimeViolationDetector`、`get_runtime_settings`、`update_runtime_settings`、**`_filter_traffic_classes`（检测类白名单过滤）**、**`_maybe_reload_scene_annotation`（场景标注热重载）**、**`_scene_config_path` / `_scene_sig_of`**、`_light_in_rois` | ✅ 自身即链路 | `routers/realtime.py:28` `from realtime_detector import realtime_detector`；`routers/scene.py:113`；`app.py:133` | 150 KB / 2026-10-10 |
| `image_recognizer.py` | 图像识别核心：YOLO 多模型串联 + 豆包/DeepSeek/Claude 云端分析 + 车牌 OCR | `multi_model_detect`、`detect_with_yolo`、`init_all_models`、`switch_model`、`get_model_status`、`analyze_with_doubao`、`analyze_with_deepseek_judge`、`analyze_with_claude`、`analyze_with_collaboration`、`analyze_image`、`detect_license_plate`、`MODEL_CONFIG`、`CLASS_CN_MAP`、**`TRAFFIC_CLASS_WHITELIST`（★交通检测类白名单，唯一权威）** | ✅ 模块级 | `realtime_detector.py:27`（模块级 import） | 108 KB / 2026-10-10 |
| `violation_rules.py` | 规则引擎：6 类违规判定（未戴头盔/违停/压线/逆行/闯红灯/超速）+ 类名白名单 + vehicle_id 回填 | `ViolationRuleEngine`、`check_violations`、`VIOLATION_TYPE_CN`、`ViolationRuleEngine._attach_vehicle_ids` | ✅ 模块级 | `realtime_detector.py:28`、`:964`；`routers/realtime.py:26` | 48.8 KB / 2026-10-04 01:48 |
| `behavior_engine.py` | 行为理解：基于轨迹判 8 类行为（含抢黄灯/违规掉头/未礼让行人，规则引擎没有的） | `BehaviorEngine`、`BehaviorResult`、`BEHAVIOR_TYPE_CN`、`analyze_behavior` | ✅ 模块级 | `realtime_detector.py:31`；`rule_engine/plugins/traffic_plugin.py:26` | 33.6 KB / 2026-10-04 01:48 |
| `vehicle_tracker.py` | 车辆追踪双模式（质心 / ByteTrack）+ 方向与逆行判断 + 轨迹历史 | `VehicleTracker`、`CentroidTracker`、`ByteTrackWrapper`、`_DetShim`、`_TrackShim`、`_Arr` | ✅ 模块级（**已启用 ByteTrack**，`realtime_detector.py:132` `use_bytetrack=True`） | `realtime_detector.py:116`；`violation_rules.py:665`；`traffic_plugin.py:27` | 23.2 KB / 2026-10-04 02:35 |
| `cloud_collaborator.py` | 端云协作：URGENT / CONSULT / NORMAL 三模式，本地不确定时主动咨询云端 | `CloudCollaborator` | ✅ 模块级（经 `_cloud_queue` 独立 worker 线程异步，见 `realtime_detector.py:175-186`） | `realtime_detector.py:29`；`routers/cloud_collab.py:22` | 55.0 KB / 2026-10-03 04:54 |
| `multi_frame_validator.py` | 多帧确认：滑动窗口 + 车牌 Levenshtein 相似度 + IOU/中心距双重 bbox 匹配；+ FPS 监控 | `MultiFrameValidator`、`FPSMonitor`、`levenshtein_similarity`、`bbox_match` | ✅ 模块级（`realtime_detector.py:188` 实例化 window=10 / confirm=5） | `realtime_detector.py:117` | 9.2 KB / 2026-07-29 15:40 |
| `circular_frame_buffer.py` | 最近 N 秒视频**循环缓存**；事件触发后抽前后片段合成事件视频（mp4v → ffmpeg 转 H.264） | `CircularFrameBuffer`、`get_default_buffer`、`_transcode_to_h264`、`_get_ffmpeg_exe` | ✅ 模块级（`realtime_detector.py:191`） | `realtime_detector.py:119`、`:196-208` | 16.2 KB / 2026-10-02 00:18 |
| `traffic_event_engine.py` | 交通事件**8 状态机**（DETECTING→TRIGGERED→RECORDING→PENDING_AI→AI_REVIEWED→CONFIRMED/REJECTED/MANUAL_REVIEW）+ 60s 冷却 + 生成云端提交请求 | `TrafficEventEngine`、`TrafficEvent`、`EventState` | ✅ 模块级（`realtime_detector.py:225` 注入统一时钟 `clock=self._now`） | `realtime_detector.py:120`、`:210-238` | 29.3 KB / 2026-10-06 00:48 |
| `traffic_light_classifier.py` | 红绿灯颜色 **CNN 分类器**（green/red/yellow/none），懒加载单例、线程安全、缺模型回退 HSV | `classify_traffic_light`、`hsv_fallback_state`、`is_available`、`find_glow_region`、`crop_around_glow`、`classify_with_glow`、`_channel_ratio_state` | ✅ 延迟导入（`realtime_detector.py:1503`，调用点 `:1573`） | `realtime_detector.py:1503` | 14.9 KB / 2026-10-05 17:38 |
| `annotation_renderer.py` | 中文标注渲染：PIL+TTF 画中文（`cv2.putText` 画不出中文）、车辆红/绿框、红绿灯按色着色、方向箭头、灯框去重 | `AnnotationRenderer`、`get_renderer`、`get_font`、`_dedupe_traffic_lights`、`_direction_vector`、**`TRAFFIC_LIGHT_CLASS_NAMES`（★红绿灯类名唯一权威名单）** | ✅ 延迟导入 ×3 | `realtime_detector.py:109`、`:1385`、`:1826` | 30 KB / 2026-10-10 |
| `plate_recognizer.py` | 车牌识别（hyperlpr3 封装）：**整帧 + 车辆框 → 裁框放大 2 倍**再识别，带 TTL 缓存 | `recognize_in_frame`、`cached_plate`、`is_available` | ✅ 延迟导入 | `realtime_detector.py:1649` | 5.3 KB / 2026-10-03 01:53 |
| `scene_annotation.py` | 场景标注持久化：人工手绘（斑马线四边形/车道线/停止线/园区区域）+ AI 自动建议；白名单含**测速标定与相机几何字段** | `load_scene`、`save_scene`、`list_scenes`、`auto_detect_all`、`auto_detect_crosswalk`、`auto_detect_stop_line`、`video_key`、`_path_for` | ✅ 延迟导入 | `realtime_detector.py:348`；`routers/scene.py:24`、`:94` | 11.5 KB / 2026-10-04 02:46 |
| `speed_calibration.py` | **视频测速标定**：像素位移 → 实际距离；4 条标定路径（相机几何★推荐 / 4点单应 / 车道宽等旧路径 / 无标定粗估）、解析反投影、帧率补偿表、物理防护阈值、超速容差判定 | `SpeedCalibrator`（新增 `ground_point`/`contact_point`/`ground_distance`/`horizon_y`/`preview`）、`speed_from_history`（**已改为端点反投影求地面距离**）、**`make_unprojector`（2026-10-06 修正符号，★推荐）**、`homography_from_ground_points`（新增）、`cross_check_unprojectors`（新增）、`ground_plane_ppm`（**数学正确，保留为对照**）、`fps_compensation`、`judge_speeding` | ✅ **间接在链路**（超速判定 / 前端速度输出） | `behavior_engine.py:407`（超速判定取 `kmh`）；`routers/realtime.py:573`（`/api/realtime/vehicles` 输出 `speed_kmh`）；`routers/scene.py`（`/api/scene/calibration-preview`） | 约 46 KB / 2026-10-06 |
| `carla_source.py` | CARLA 仿真数据源，与 `VideoCapture` 同级接口，未装 CARLA 时优雅降级；**L234 注明 raw_data 是 BGRA** | `CarlaSource` | ✅ 延迟导入 | `realtime_detector.py:433`；`routers/realtime.py:1055` | 19.0 KB / 2026-07-29 15:40 |
| `evidence_chain.py` | **事件级完整证据链** dataclass（摄像头/时间/地点/车辆/车道/灯态/轨迹/停止线关系/关键帧/事件视频/规则判断/AI判断/AI置信度/最终状态） | `EvidenceChain`（`to_json`） | ✅ 延迟导入 | `realtime_detector.py:1960`（`_persist_evidence_chain`）；`routers/realtime.py:1372` | 9.0 KB / 2026-09-25 15:19 |
| `wechat_miniapp.py` | 微信小程序**数据层**（直连 sqlite）：登录/绑定车辆/我的违规/通知/申诉/统计 | `code2session`、`upsert_user`、`normalize_plate`、`bind_vehicle`、`list_my_violations`、`create_notification`、`submit_appeal`、`review_appeal`、`stats`、`_conn` 等 **21 个模块级函数**（`_conn`/`init_tables`/`_now`/`is_configured`/`code2session`/`upsert_user`/`normalize_plate`/`bind_vehicle`/`unbind_vehicle`/`list_bound_vehicles`/`_violation_rows_for_plates`/`list_my_violations`/`create_notification`/`list_notifications`/`mark_read`/`push_subscribe_message`/`get_access_token`/`submit_appeal`/`list_my_appeals`/`review_appeal`/`stats`） | ✅ 延迟导入 | `realtime_detector.py:2020`（`_notify_owner` 违规推送）；`routers/wx_miniapp.py:29` | 23.1 KB / 2026-10-03 04:32 |
| `config.py` | 统一配置：端口/路径/DB/模型目录/帧率/事件缓存/插件清单；**顶部显式加载 `api/.env`**。★2026-10-06 修：`DB_PATH` 原指向项目根（**0 字节空壳**），现与 `database.py` 对齐 | `Config`、`get_config` | ✅ 模块级 | `realtime_detector.py:30`；`image_recognizer.py:13`；`routers/realtime.py:303`、`:953`；`app.py:142`、`:159`；`rule_engine/plugin_loader.py:261` | 6.6 KB / 2026-10-06 |
| `models.py` | SQLAlchemy ORM：7 张表模型 | `ViolationEvidence`、`SystemConfig`、`APILog`、`User`、`CollaborationSession`、`SystemStatistics`、**`TrafficEventRecord`** | ✅ 延迟导入 | `realtime_detector.py:1912`、`:1964`；`database.py:42`；`routers/*` 多处 | 11.1 KB / 2026-09-25 15:19 |
| `database.py` | DB 引擎/会话工厂（**绝对路径锚定**，与启动 cwd 无关）+ 建表 + 缺列迁移 | `engine`、`SessionLocal`、`get_db`、`init_db`、`migrate_missing_columns` | ✅ 延迟导入 | `realtime_detector.py:1911`、`:1961`；`app.py:14`；`routers/*` 全部 | 3.4 KB / 2026-10-02 01:22 |
| `rule_engine/base_plugin.py` | 插件接口契约 | `BaseRulePlugin`(ABC)、`ViolationEvent`(dataclass) | ✅ 经插件加载器 | `rule_engine/plugin_loader.py:15`；三个插件 | 3.0 KB / 2026-07-29 |
| `rule_engine/plugin_loader.py` | 动态发现/加载 `plugins/` 全部插件，按 `Config.PLUGINS_ENABLED` 启用 | `PluginLoader`、`get_default_loader`、`discover`、`initialize_all`、`list_enabled` | ✅ 延迟导入 | `realtime_detector.py:215`；`routers/realtime.py:693` | 10.6 KB / 2026-07-29 |
| `rule_engine/plugins/traffic_plugin.py` | 交通场景插件（`scenario_name="traffic"`，5 类可检测），包装 `behavior_engine` + `vehicle_tracker` | `TrafficPlugin`、`TRAFFIC_TYPE_CN`、`TRAFFIC_TYPE_COLOR` | ✅ **默认启用** | `plugin_loader.discover()` → `realtime_detector.py:215-221` 注入 `TrafficEventEngine` | 9.6 KB / 2026-09-25 15:58 |
| `rule_engine/plugins/urban_management_plugin.py` | 城管场景插件（`street_stall` / `illegal_occupancy`） | `UrbanManagementPlugin` | ✅ **默认启用** | 同上 | 13.2 KB / 2026-07-29 |
| `rule_engine/plugins/public_security_plugin.py` | 治安场景插件（`crowd_gathering` / `abnormal_assembly`） | `PublicSecurityPlugin` | ✅ **默认启用** | 同上 | 12.6 KB / 2026-07-29 |

> 默认启用清单来自 `config.py:65-67`：`PLUGINS_ENABLED = 'traffic,urban_management,public_security'`。

### 2.2 在接口层（非每帧链路）

| 模块 | 用途 | 核心类/函数 | 在实时链路? | 谁调用它（证据） | 大小 / 最后修改 |
|---|---|---|---|---|---|
| **`web-admin/src/views/CalibrationPanel.vue`** | **★管理端测速标定 + 信号灯 ROI 面板**（2026-10-06 由 DSH 新建）：4 种交互（拖框 ROI / 点停止线 / 点地面标定点 / 量距）+ 相机参数 4 项 + 调后端 `calibration-preview` 实时反馈（地平线/可解比例/逐行 ppm/告警/点误差）。**几何一律交后端，前端不重算** | `CalibrationPanel`（`applyConfig` / `buildConfig` / `runPreview` / `toImg`） | ❌ 仅界面 | `LiveMonitor.vue`（`<CalibrationPanel v-model="calDlg" …>`） | ~660 行 / 2026-10-06 |
| `virtual_tracker.py` | 虚拟线圈 / 越线跟踪，供 tracking 接口 | `VirtualTracker` | ❌ 仅接口层 | `routers/realtime.py:834`（`_get_virtual_tracker`，`/api/realtime/tracking/*`） | 21.5 KB / 2026-07-29 15:40 |
| `ptz_controller.py` | 云台控制抽象（ONVIF 真实实现 + 模拟实现） | `PTZControllerBase`(ABC)、`ONVIFPTZController`、`SimulatedPTZController`、`PTZFactory` | ❌ 仅接口层 | `routers/realtime.py:950`（`/api/realtime/ptz/*`） | 23.5 KB / 2026-07-29 15:40 |
| `config_manager.py` | API Key 管理：`config_runtime.json` 读写、掩码展示、调用计数、额度心跳探测 | `load_config`、`save_config`、`get_masked_config`、`set_api_key`、`heartbeat`、`_heartbeat_dashscope`、`_heartbeat_deepseek`、`init_dashscope_key` | ❌ API 层 | `routers/system.py:9`；`image_recognizer.py:196` | 8.1 KB / 2026-06-15 |
| `schemas.py` | Pydantic 请求/响应模型（违规/微信/用户/设备/申诉，19 个） | `ViolationEvidenceCreate/Response/Update`、`WeChatViolationSubmit`、`ViolationStatistics`、`ApiResponse` … | ❌ | `routers/violations.py:13`；`routers/wechat.py:8`；`routers/auth.py:15` | 7.2 KB / 2026-07-29 |
| `license_plate_recognizer.py` | PaddleOCR 车牌识别（含 3D 投影辅助） | `LicensePlateRecognizer`、`get_recognizer`、`detect_and_recognize_plate` | ❌ | **仅** `1/scripts/run_carla_demo.py:47` | 14.3 KB / 2026-07-29 15:40 |

### 2.3 脚本 / 工具 / 疑似死代码（**不在链路**）

| 模块 | 用途 | 核心类/函数 | 引用情况（证据） | 大小 / 最后修改 |
|---|---|---|---|---|
| `scene_perception.py` | 场景感知：`LaneDetector` 车道线 / `TrafficLightDetector` / `SceneContext` | `LaneDetector`、`TrafficLightDetector`、`SceneContext` | ⚠ **无任何代码引用**（全仓 grep 仅命中自身 + 2 份文档） | 26.1 KB / 2026-07-29 15:40 |
| `k230_plate_client.py` | K230 边缘设备车牌识别 HTTP 客户端 | `K230PlateClient`、`get_k230_client` | ⚠ **无任何代码引用**（仅 `NATIONAL_SPRINT_BRIEF.md:71`、`docs/project_analysis_gpt_upgrade.md:203` 宣称"已实现"） | 7.7 KB / 2026-07-29 15:40 |
| `main.py` | **旧版（v1.0）FastAPI 应用**：自带 `/token`、`/users/`、`/violations/`、`/control/`、`/logs/`、`/stats/violations` | `app`(FastAPI)、`get_current_user`、`require_admin` … | ⚠ 无人 import（`TASKS.md:90` 曾提及端口 8000）；若被挂载会与 `routers/auth.py`、`routers/violations.py` 路由重名 | 12.4 KB / 2026-06-15 |
| `backend_evaluation.py` | 离线后端能力评估（AST 扫源码打分 + 调 API） | `BackendEvaluator`、`main` | 无引用，手工运行 | 33.6 KB / 2026-06-15 |
| `migrate_db.py` | 独立迁移脚本：建 `collaboration_sessions`/`system_statistics`/`traffic_events` 表 + 版本表 + `rollback` + `show_status` | `migrate`、`rollback`、`show_status`、`main` | 无引用，手工运行 | 18.3 KB / 2026-09-25 |
| `seed_demo_data.py` | 演示数据填充 | `seed_data`、`show_summary`、`main` | 无引用，手工运行 | 6.6 KB / 2026-07-29 |
| `diag_frame.py` | 拉流取帧诊断（urllib） | — | 无引用，手工运行 | 2.2 KB / 2026-07-29 |
| `create_test_image.py` / `submit_test_images.py` | 造测试图 / 批量提交测试图 | — | 无引用，手工运行 | 1.1 KB / 3.4 KB |
| `test_api.py`、`test_camera.py`、`test_claude_integration.py`、`test_integration.py`、`test_parser_logic.py`、`test_realtime.py`、`test_recognizer.py`、`test_stream_api.py`、`test_task010.py`、`test_traffic_light_vehicle.py` | 手工测试脚本（11 个） | — | 无引用；**正式测试在 `1/tests/`（pytest）** | — |

> **另有「演示素材生产线」（不属于项目本体，2026-10-17 用户明确）**：
> `E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py`（2111 行）
> —— CARLA 可视化摆车 / 行为模式 / 红绿灯配时 / 道具 / 1080p 录制；入口 `E:\output\1\carla\启动CARLA创造工坊.bat`。
> 结论、硬坑（K1/K2）与未做项见 **`E:\output\_carla_sim_tooling_verdict.md` §13–§14**。

### 2.4 路由模块（`api/routers/`）

| 文件 | 前缀 | 路由数 | 用途 | 大小 / 最后修改 |
|---|---|---|---|---|
| `realtime.py` | `/api/realtime` | **40**（39 REST + 1 WS） | 实时检测主控：启停/状态/MJPEG 流/帧检测/事件中心/CARLA/PTZ/虚拟线圈/插件场景/运行时设置 | 63.2 KB / 2026-10-03 05:21 |
| `wx_miniapp.py` | `/api/wx` | 21 | 微信小程序：登录/档案/车辆绑定/违规/通知/申诉/统计 | 16.7 KB / 2026-10-03 04:45 |
| `violations.py` | `/api/violations` | 11 | 违规证据 CRUD、批量提交、按车牌查、车牌图、重新分析、统计 | 33.4 KB / 2026-07-29 15:40 |
| `rtsp_stream.py` | `/api/stream` | 10 | RTSP/本地摄像头流：推送帧、MJPEG、快照、列表、本地摄像头启停、设备探测、单帧分析 | 13.7 KB / 2026-09-01 00:09 |
| `system.py` | `/api/system` | 9 | 额度监控/心跳、YOLO 模型加载切换卸载、性能统计 | 6.3 KB / 2026-07-27 21:33 |
| `devices.py` | `/api/devices` | 7 | 设备注册/列表/详情/更新/删除/心跳/设备违规 | 9.0 KB / 2026-06-26 |
| `appeals.py` | `/api/appeals` | 6 | 申诉提交（含图片）/列表/详情/处理/统计 | 8.5 KB / 2026-06-26 |
| `auth.py` | `/api/auth` | 6 | 登录（JWT）/当前用户/注册/用户 CRUD | 7.7 KB / 2026-07-29 |
| `cloud_collab.py` | `/api/cloud` | 6 | 端云协作：咨询/协作列表/详情/统计/分歧案例/人工裁决 | 14.8 KB / 2026-07-27 |
| `scene.py` | `/api/scene` | **7** | 场景标注：列表/读写配置/删除/**标定预览**/自动检测/首帧 | 6.6 KB / 2026-10-03 02:25 |
| `statistics.py` | `/api/statistics` | 4 | 总览/按日/类型分布/小时分布 | 6.3 KB / 2026-06-26 |
| `wechat.py` | `/api/wechat` | 4 | 旧版微信接口：违规提交/列表/详情/我的统计 | 6.5 KB / 2026-06-15 |
| `app.py`（非 routers） | — | 2 | `GET /` 根信息、`GET /health` 健康检查（含 YOLO/DashScope 可用性） | 6.8 KB / 2026-10-03 04:32 |

**路由总数核对**：源代码 `@router.*` 装饰器 **131 个**（含 1 个 WebSocket）= 130 REST + 1 WS（2026-10-06 新增 `POST /api/scene/calibration-preview`；旧口径为 130 个 / 129 REST）+ `app.py` 的 `/` 与 `/health` = **132 REST + 1 WS**。运行中的 8001 实例仍是旧进程（openapi 显示 131 operations），**重启后**才会变成 132。`[一]`
> 判定方法：`Invoke-WebRequest http://127.0.0.1:8001/openapi.json` 返回 200，长度 101474 字节；`paths` 共 122 条。

---

## 三、API 路由（权威清单）

> 数据来源：**运行中的后端** `http://127.0.0.1:8001/openapi.json` `[一]`（端口 8001 正在跑，进程 `C:\miniconda\envs\zhitong-gpu\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8001`）。已与源码 grep 交叉核对，两侧一致。
> 全部 **132** 条 REST + 1 条 WS（口径见 §二 末尾：源码 130 + `app.py` 2；运行中的旧实例只显示 131）。**加粗**的是本轮新增/容易忽略的能力。

### 3.1 实时域 `/api/realtime`（40）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/realtime/start` | 启动实时检测 |
| POST | `/api/realtime/stop` | 停止实时检测 |
| GET | `/api/realtime/status` | 检测状态（含 `traffic_light_stats`、`event_engine` 统计） |
| GET | `/api/realtime/stream` | MJPEG 视频流 |
| GET | `/api/realtime/snapshot` | 当前帧快照 |
| POST | `/api/realtime/detect-frame` | 单帧检测（上传图） |
| **WS** | **`/api/realtime/violations/stream`** | **WebSocket 违规事件推送（★旧索引写成 `/api/realtime/ws`，是错的）** |
| GET | `/api/realtime/camera/list` | 枚举可用摄像头 |
| POST | `/api/realtime/source` | 切换数据源（camera / video / carla） |
| POST | `/api/realtime/consult` | 强制云端咨询 |
| GET | `/api/realtime/tracked-vehicles` | 当前追踪车辆列表 |
| **GET** | **`/api/realtime/vehicles`** | **左右分流视图：车辆 + 归属违规 + `speed_kmh`（内部用 `SpeedCalibrator`）** |
| GET | `/api/realtime/behavior-stats` | 行为引擎统计 |
| GET | `/api/realtime/zoom-frame` | 局部放大帧 |
| GET | `/api/realtime/evidence` | 实时证据列表 |
| GET | `/api/realtime/settings` | 读取运行时设置 |
| POST | `/api/realtime/settings` | 局部更新运行时设置 |
| GET | `/api/realtime/plugins` | 规则插件列表 |
| POST | `/api/realtime/plugins/switch` | 启用/禁用插件 |
| GET | `/api/realtime/plugins/scene-modes` | 场景模式清单 |
| POST | `/api/realtime/plugins/scene-mode` | 切换场景模式 |
| POST | `/api/realtime/tracking/start` | 启动虚拟线圈跟踪 |
| POST | `/api/realtime/tracking/stop` | 停止跟踪 |
| GET | `/api/realtime/tracking/status` | 跟踪状态 |
| GET | `/api/realtime/ptz/status` | 云台状态 |
| POST | `/api/realtime/ptz/move` | 云台转动 |
| POST | `/api/realtime/ptz/zoom` | 云台变焦 |
| POST | `/api/realtime/ptz/home` | 云台回位 |
| GET | `/api/realtime/carla/status` | CARLA 连接状态 |
| POST | `/api/realtime/carla/connect` | 连接 CARLA |
| POST | `/api/realtime/carla/spawn` | 生成车辆 |
| POST | `/api/realtime/carla/next-scene` | 切换场景 |
| GET | `/api/realtime/carla/actors` | CARLA actor 列表 |
| GET | `/api/realtime/events` | 交通事件列表 |
| GET | `/api/realtime/events/active` | 活跃事件 |
| GET | `/api/realtime/events/{event_id}` | 事件详情 |
| **GET** | **`/api/realtime/events/{event_id}/video`** | **事件视频（循环缓存合成）** |
| **GET** | **`/api/realtime/events/{event_id}/replay`** | **事件重放** |
| **GET** | **`/api/realtime/events/{event_id}/frames`** | **事件关键帧** |
| **POST** | **`/api/realtime/events/{event_id}/review`** | **人工复核事件（写入证据链）** |

### 3.2 场景标注 `/api/scene`（7）

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/scene` | 已标注场景列表 |
| GET | `/api/scene/config` | 读取某视频/流的标注 |
| POST | `/api/scene/config` | 保存标注（人工手绘斑马线/车道线/停止线/区域/相机几何/标定点） |
| DELETE | `/api/scene/config` | 删除标注 |
| **POST** | **`/api/scene/calibration-preview`** | **★测速标定预览（不落盘）：给参数即返回地平线行、逐行 ppm/地面距离、可解像素比例、告警；`pairs` 可量两点实际地面距离（车道宽校验）** |
| POST | `/api/scene/auto-detect` | AI 自动建议（斑马线/停止线） |
| GET | `/api/scene/first-frame` | 取首帧供手绘 |

### 3.3 违规证据 `/api/violations`（11）

`POST /submit`、`POST /batch`、`POST /upload-multipart`、`GET /list`、`GET /{id}`、`PUT /{id}`、`DELETE /{id}`、`PUT /{id}/reanalyze`（重新分析）、`GET /plate/{plate_number}`、`GET /plate-image/file`、`GET /statistics/summary`

### 3.4 实时视频流 `/api/stream`（10）

`POST /push-frame`、`GET /mjpeg/{device_id}`、`GET /snapshot/{device_id}`、`GET /info/{device_id}`、`GET /list`、`DELETE /{device_id}`、`POST /start-local`、`POST /stop-local`、`GET /detect-cameras`、`POST /analyze-frame`

### 3.5 系统管理 `/api/system`（9）

`GET /quota`、`PUT /quota/{provider}`、`POST /quota/{provider}/heartbeat`、`GET /models`、`POST /models/switch`、`DELETE /models/{model_key}`、`POST /models/init`、`GET /performance`、`POST /performance/reset`

### 3.6 微信小程序 `/api/wx`（21）+ 旧微信 `/api/wechat`（4）

- `/api/wx`：`POST /login`、`GET /profile`、`GET /vehicles`、`POST /vehicles/bind`、`POST /vehicles/unbind`、`POST /vehicles/bind-by-suggest`、`GET /violations`、`GET /violations/list`（别名）、`GET /violations/{id}`、`GET /notifications`、`POST /notifications/read`、`POST /notify-test`、`POST /appeals`、`GET /appeals`、`GET /appeals/list`（别名）、`POST /appeals/review`、`GET /appeals/statistics/summary`、`GET /overview`、`GET /stats`、`GET /statistics/overview`、`GET /bind/status`
- `/api/wechat`（旧，保留兼容）：`POST /violation/submit`、`GET /violation/list`、`GET /violation/{id}`、`GET /statistics/my`

### 3.7 端云协作 `/api/cloud`（6）

`POST /consult`、`GET /collab-list`、`GET /collab-detail/{record_id}`、`GET /statistics`、`GET /disagreements`、`POST /resolve-disagreement`

### 3.8 设备 `/api/devices`（7）、申诉 `/api/appeals`（6）、认证 `/api/auth`（6）、统计 `/api/statistics`（4）、根/健康（2）

- devices：`POST /register`、`GET /list`、`GET /{id}`、`PUT /{id}`、`DELETE /{id}`、`POST /heartbeat`、`GET /{id}/violations`
- appeals：`POST /submit`、`POST /submit-with-image`、`GET /list`、`GET /{violation_id}`、`PUT /{violation_id}/process`、`GET /statistics/summary`
- auth：`POST /login`、`GET /me`、`POST /register`、`GET /users`、`PUT /users/{user_id}`、`DELETE /users/{user_id}`
- statistics：`GET /overview`、`GET /daily`、`GET /type-distribution`、`GET /hourly`
- app：`GET /`、`GET /health`

### 3.9 静态挂载

| 路径 | 目录 | 证据 |
|---|---|---|
| `/uploads` | `Config.UPLOAD_DIR`（多布局兜底探测） | `app.py:141-154` |
| `/event-videos` | `Config.EVENT_VIDEO_DIR`（默认 `api/output/event_videos`，按 `{YYYYMMDD}/{event_id}.mp4`） | `app.py:156-165` |

---

## 四、数据与模型资产

### 4.1 YOLO / 检测模型 —— `E:\output\1\zhitong\training\models\` `[一]`

| 文件 | 大小 | 最后修改 | 说明 |
|---|---|---|---|
| `yolov8n.pt` | 6.25 MB | 2026-07-13 | COCO 通用检测（`model_key='yolov8n'` → 实际命中） |
| `yolov8s.pt` | 21.54 MB | 2026-07-13 | COCO 通用（**`vehicle` / `traffic_light` / `license_plate` 三个 key 实际都命中它**） |
| `lane.pt` | 21.54 MB | 2026-07-15 | 车道线（`model_key='lane'` → 实际命中） |
| `helmet_best.pt` | 5.92 MB | 2026-07-21 | **头盔检测实际生效模型**（`find_model_path('helmet')` 把它插到候选首位） |
| `helmet.pt` | 21.54 MB | 2026-07-15 | TASK-007 下载版，**被 `helmet_best.pt` 遮蔽，实际不生效** |
| `traffic_light.pt` | 21.54 MB | 2026-07-13 | TASK-007 下载版，**被 `yolov8s.pt` 遮蔽，实际不生效** |
| `traffic_light_best.pt` | 21.53 MB | 2026-07-21 | 同样被 `yolov8s.pt` 遮蔽 |
| `vehicle_best.pt` | 5.96 MB | 2026-07-21 | 被 `yolov8s.pt` 遮蔽 |
| `best.pt` | 21.48 MB | 2026-07-21 | `find_model_path` 的候选里没有 `best.pt`（无 key 指向） |
| `yolov8m.pt` / `yolov8n_official.pt` / `yolov8n_pretrained.pt` | 49.7 / 6.23 / 6.25 MB | — | 未被任何 `model_key` 引用 |
| `helmet_pretrained.pt` | 21.5 MB | 2026-07-21 | 未被引用 |
| `download_records.json` | 0 B | 2026-07-13 | 空文件 |

**模型 key → 文件映射**（`image_recognizer.py:212-233` `find_model_path`）：
`yolov8n→yolov8n.pt`｜`yolov8s→yolov8s.pt`｜`vehicle→yolov8s.pt`｜`helmet→helmet_best.pt`（插到候选首位）｜`traffic_light→yolov8s.pt`｜`lane→lane.pt`｜`license_plate→license_plate.pt`（**该文件不存在** → 回退 `yolov8s`）。
候选顺序：`models/{映射名}` → `models/{key}_best.pt` → `../models/{映射名}` → `api/{映射名}` → `../data/models/{映射名}`，**取第一个存在者**。

### 4.2 红绿灯判色模型 —— `E:\output\_tl_color_cls\` `[一]`

| 文件 | 大小 | 最后修改 | 说明 |
|---|---|---|---|
| `tl_color_cnn.pt` | 2,272,416 B | 2026-10-03 01:17 | 首版（3 类？）—— 已被 cnn4 取代 |
| `tl_color_cnn4.pt` | 2,272,703 B | 2026-10-03 01:24 | **4 类（green/red/yellow/none），真实视频数据训练**；`traffic_light_classifier.py:27` 的**代码默认值**。离线基准：真实素材 93.2% 判色 / 99.6% 拒识（red 54/54） |
| `tl_color_cnn5_carla.pt` | 2,272,953 B | 2026-10-05 18:13 | **v1 CARLA 数据微调**（以 cnn4 为 base，冻结前几层）。`_redlight_demo_final.md` 记录：lit 裁图 14/14 = 100%，推理快 2×，**报告称"采用 CNN5"** |
| `tl_color_cnn6_carla.pt` | 2,272,953 B | 2026-10-05 23:11 | **v2 CARLA 数据**（修正 v1 三处数据污染：只裁点亮镜片、只含灯珠、按亮度 90 分位取边缘）。lit 裁图 14/14；自采数据 0.987；**留作备选，未接入** |
| `history.json` | 5,136 B | 2026-10-03 01:17 | 训练曲线 —— **时间戳停留在 cnn4，cnn5/cnn6 无元数据记录** |
| `val_predictions.csv` | 1,045 B | 2026-10-03 01:17 | 同上，仅覆盖 cnn4 |

**三者区别（一句话）**：`cnn4` = 真实视频训练（域内最强，CARLA 域外红灯召回 0）；`cnn5` = 在 cnn4 上用 CARLA v1 数据微调（接入候选）；`cnn6` = CARLA v2 修正数据微调（自采更优、鲁棒性证据不足，备选）。
**训练脚本**：`_scripts/_train_4class.py`（产出 cnn4）、`_scripts/_retrain_carla_classifier.py`（base=cnn4，产出 cnn6；v1 产出 cnn5）。
**切换方式**：环境变量 `TL_COLOR_MODEL`（`traffic_light_classifier.py:26-27`）。

### 4.3 数据库 —— `E:\output\1\api\zhitong_violations.db`（26,247,168 B，2026-10-06 00:50）`[一]`

| 表名 | 行数 | 列数 | 关键列 |
|---|---|---|---|
| `violation_evidences` | **2393** | 25 | violation_type, track_id, confidence, image_path, video_path, cloud_validated, status, yolo_detection_result, deepseek_result, ai_trace_version, final_judgment_source, plate_number, plate_confidence, plate_image_path, plate_color, confirmed_frames |
| `traffic_events` | **2552** | 20 | event_id, event_type, track_id, **state**, trigger_time, vehicle_info, scene_context, trajectory, key_frames, event_video_path, rule_judgment, ai_judgment, ai_confidence, ai_explanation, **evidence_chain**, state_history, camera_id |
| `wx_notifications` | 43 | 13 | openid, kind, title, body, plate_number, violation_id, event_id, payload, is_read, pushed, push_result |
| `wx_users` | 6 | 9 | openid, unionid, nickname, session_key, last_login |
| `wx_vehicle_bindings` | 6 | 7 | openid, plate_number, vin_tail, relation, verified |
| `system_configs` | 1 | 6 | config_key, config_value |
| `users` | 1 | 9 | username(unique), password_hash, role(admin/user), email, name, is_active |
| `api_logs` | 0 | 9 | client_type, endpoint, method, request_data, response_data, status_code, execution_time |
| `collaboration_sessions` | 0 | 13 | session_id, violation_type, local_confidence, final_confidence, judgment_result, disagreement, resolved, ai_trace_json |
| `system_statistics` | 0 | 10 | stat_date, total_detections, consultations, confirmations, disagreements, accuracy_before/after, saved_cost |
| `wx_appeals` | 0 | 13 | openid, violation_id, event_id, plate_number, reason, status, reviewer, review_note |
| `sqlite_sequence` | — | — | SQLite 内部 |

索引 30 个（`ix_*` + `sqlite_autoindex_*`）。

### 4.4 场景标注数据 —— `E:\output\1\api\output\scene_configs\` `[一]`

仅 1 个文件：`ea1ca6cbb27653af24ebe585d56f0ffd_7bc8e08680df.json`（882 B，2026-10-03 03:45）。
命名规则（`scene_annotation.py:63-76`）：`{源文件名去扩展名后前 40 字符}_{源路径 sha1 前 12 位}.json`；所以"导入视频"与"接入摄像头"各持久化一套标注。上面这个文件名 = 视频 `ea1ca6cb…mp4` + URL/路径哈希 `7bc8e08680df`。

### 4.5 其它资产

- `E:\output\1\api\.env` 存在（DASHSCOPE_API_KEY / DEEPSEEK_API_KEY，已从 `config_runtime.json` 迁移）`[二]`
- `E:\output\1\api\config_runtime.json`（334 B）仍在
- `E:\output\1\web-admin\`（Vue3 + Vite）：19 个 view，新增 `LiveMonitor.vue`、`EventCenter.vue`、`EventDetail.vue`、`SystemLog.vue`
- `E:\output\1\digital_twin\app.py`（20 KB）、`E:\output\1\miniprogram\`、`E:\output\1\wechat-miniprogram\`
- `E:\output\1\tests\`（pytest 正式测试，含 `test_traffic_plugin_contract.py`、`test_cloud_collaborator_event.py`）
- `E:\output\_scripts\`：**286 个**脚本（CARLA 采集、判色评测、投影验证等；2026-10-04 批量修复过通道序，备份在 `_scripts\_bak_byteorder\`）
  - **★`_validate_speed_calibration.py`**（2026-10-06 新建）：测速标定端到端验证 —— 真实渲染帧 + YOLO 框 + CARLA 世界坐标，输出反投影/速度误差与 PASS/FAIL（约 1 分钟，可复跑）
  - **★`_carla_calibration_markers.py`**（2026-10-06 新建）：CARLA **物理级**验证 —— 按已知世界坐标摆锥桶/draw_point → 真实渲染 → 像素检测 → 与模型对照；需 CARLA 运行 + Python 3.12
  - **★`_evaluate_redlight.py`**（2026-10-06 新建）：闯红灯识别成功率评测 —— 真值 CSV + 逐帧 trace → 判色准确率 / 检出 / 重复 / 误报 / 精确率（需先设 `RT_TRACE_JSONL` 启动后端）
  - 旧脚本 `_debug_homography.py` / `_verify_homography*.py` / `_unproject_numeric.py` / `_compare_two_impls.py` 等：**其结论建立在损坏的 CSV"真值"上，不要再作为判据**（见 T40）
  - 逐帧 trace 文件：`E:\output\_rt_trace*.jsonl`（`_final` = 本轮成功那 3 个循环的证据）
- `E:\output\1\K230\`、`E:\output\1\carla\`、`E:\output\1\data\`、`E:\output\1\固件备份\`

---

## 五、★已知陷阱（改代码前必读）

> 全部为代码注释 / 已归档报告中的**实测记录**，不是推测。

### 5.0 ★管理端前端图表（2026-10-23 新增）

| # | 陷阱 | 证据 |
|---|---|---|
| **T50** | ✅**已于 2026-10-23 修复**（format.js TYPE_MAP 6→12 key + 未映射兜底「未知类型」+ console.warn；EventDetail.vue 删本地补丁）。历史记录：**中文类型名有 5 套映射表各自为政，前端 `TYPE_MAP` 只有 6 类，后端能产出 10-11 类** → 未覆盖的类型会在界面上**直接显示英文 key**（实测仪表盘出现 `running_yellow`、截断成 `ing_yellow`）。根因文件 `web-admin/src/utils/format.js:1-8`。**修前端局部补丁无效**（`EventDetail.vue:612` 的 `EXTRA_TYPE_CN` 就是历史遗留的局部补丁），必须修 `format.js` 根因并加"未映射兜底"（禁止英文外露）。 | `_ui_optimization_verdict.md` §1.4；三模型独立评审一致 |
| **T51** | ✅**已于 2026-10-23 修复**（类型分布改横向排序条形图，yAxis.inverse:true 最大值置顶，条尾标百分比，删图例）。历史记录：**饼图/环形图在 400×250 卡片里最多装 5-6 类，超过必然标签重叠**。当前仪表盘 7 类塞环形 + `avoidLabelOverlap:false` + 底部 7 项图例折行 → 实测 3 处标签压叠 + 环形被裁切。**这是选型错误，调参救不回来**（三模型独立判定一致）。正解：换成**横向排序条形图**（类目走 Y 轴、条尾直接标百分比、删图例）。 | `_ui_optimization_verdict.md` §2.2-2.5；本地设计库 `charts.csv` 规则 No.3（Pie 限 ≤5 类） |
| **T52** | ✅**已于 2026-10-23 修复**（echarts-theme.js 重写为亮色 zt-light，Dashboard 三处 echarts.init(el, 'zt-light')；Statistics.vue 三处 init 仍未传主题，属既有不一致，见 G16）。历史记录：**`web-admin/src/utils/echarts-theme.js` 定义的主题从未生效**：`Dashboard.vue` 三处 `echarts.init(el)` 均**未传主题参数**。且该主题是**深色**体系，而 `styles/design-tokens.css` 是**亮色**体系（`--zt-bg:#F6F7F9`）—— 两套设计语言并存。改图表前先确认配色基线。 | `Dashboard.vue:341,357,368`；`echarts-theme.js:10-73` vs `design-tokens.css:21-49` |
| **T53** | ✅**已于 2026-10-23 处理**（决策 1 选 A：该卡改为「审核状态分布」环形图，数据取接口已有 by_status，零后端改动）。历史记录：**仪表盘"设备违规排行 TOP10"卡从无数据源**：全项目 grep `by_device` **仅 1 处命中**，且是前端自己读 `stats.value.by_device \|\| []` 的空兜底；`api/routers/statistics.py:93-100` 返回体**没有** `by_device` 字段。**它不是故障，是设计时就没做的空壳**。要让它有数据必须后端新增聚合（join 设备表）。 | `_ui_optimization_verdict.md` §1.3 |

### 5.1 颜色与通道

| # | 陷阱 | 证据 |
|---|---|---|
| T1 | **CARLA `raw_data` 是 BGRA，取 `[:, :, :3]` 就是 BGR —— 绝不能再加 `[::-1]`**。多加一次 → R/B 互换 → **红灯看起来是青蓝**，本轮所有颜色结论全错。 | `_ROOTCAUSE_channel_order.md` §一/§二/§三；`carla_source.py:234` 有同样注释。铁证：橙路障修前 BGR=(239,236,231) 偏蓝、修后 (99,170,238) 橙 |
| T2 | **遗留 bug 位点未修**：`1\beforeness\blind_yun.py:371` 与 `1\zhitong\blind_yun.py:371` 仍是 `array[:, :, :3][:, :, ::-1]  # RGBA -> BGR`（同样多反转一次）。**未经确认不要擅自改**。 | `_ROOTCAUSE_channel_order.md` §五 |
| T3 | **"假验证"教训**：用 `cv2.imwrite` 存已知 BGR 再 `cv2.imread` 读回一致，**只证明 imwrite/imread 自洽，完全没验证数据源**。验证必须针对被测链路本身。 | `_ROOTCAUSE_channel_order.md` §七；`_redlight_demo_final.md` §七 |
| T4 | **投影公式 `up` 向量符号**：必须是 `[-sp*cy, -sp*sy, cp]`，写成 `[sp*cy, sp*sy, cp]` → v 全跑到画面外。修正后灯头投影误差降到 11 px。 | `_ROOTCAUSE_channel_order.md` §四；`speed_calibration.py:394-403` |

### 5.2 判色（红绿灯）

| # | 陷阱 | 证据 |
|---|---|---|
| T5 | **存在三条判色路径，会互相打架**：① `image_recognizer._detect_traffic_light_color()`（HSV，`model_key=='traffic_light'` 时把 class_name 直接换成裸色名）；② `_detect_traffic_light_state()`（读上游模型裸色名，**实测 520/520 帧恒输出 'yellow'** → 闯红灯 base=red 永远不可能触发）；③ `traffic_light_classifier` CNN（**唯一可信**）。现链路已改为 **CNN 优先，仅 CNN 无结论才回退 ②**。 | `realtime_detector.py:741-753`、`image_recognizer.py:641-646`；`_redlight_demo_final.md` §一 |
| T6 | **判色白名单必须包含裸色名** `'red'/'yellow'/'green'`，否则该模型全部检测被 `continue` 掉 → 红绿灯框一个都画不出来（实测 0/520 帧）。 | `realtime_detector.py:1511-1526` |
| T7 | **不要对灯框扩边**。扩边 25% 会让"黄灯被判成红灯"（9 例错中 8 例，危险方向）。最优是**原样裁图**。 | `realtime_detector.py:1532-1549`（377 张真实样本对照表） |
| T8 | **判色前必须先裁出"被点亮的那颗镜片"**（`_crop_lit_lens`，框内竖直三等分取最亮片）。真实视频灯珠填满 YOLO 框，CARLA 里只占一小块（灯头 15×41 px，点亮镜片仅 ~10×12 px）。不裁：CNN4/CNN5 在演示视频 0/14、11/14；裁了：CNN5 14/14。 | `realtime_detector.py:1560-1572`；`_redlight_demo_final.md` §二 |
| T9 | **HSV 兜底已收紧为"仅 CNN 完全不可用时才用"**。真实视频上 CNN 与 HSV 一致率仅 **23%**，且出现 CNN=red(0.97) 而 HSV=green 的**危险方向**错误。恢复旧行为需 `TL_HSV_FALLBACK=always`。 | `realtime_detector.py:1577-1590` |
| T10 | **删扩边块时连带删掉 `x1,y1,x2,y2` 解包** → `NameError` 被外层 `except` 静默吞掉 → 判色 100% 失效。同类还有漏写 `self.`（`_crop_lit_lens(roi)` 应为 `self._crop_lit_lens(roi)`）。 | `realtime_detector.py:1547-1549`；`_redlight_demo_final.md` §一 bug#3 |
| T11 | **`traffic_light` 这个 model key 实际加载的是 `yolov8s.pt`（COCO）**，不是 `traffic_light.pt`；颜色完全由 HSV `_detect_traffic_light_color` 给出。`MODEL_CONFIG['traffic_light']['classes']=['red','yellow','green']` 是**声明**，与真实 COCO 输出（`traffic light`）不符。 | `image_recognizer.py:212-233` 候选顺序 + `:641-646` + `:173-178` |
| **T45** | **★场景灯态必须取"受控方向那盏灯"，不能取"画面里任意一盏"**（2026-10-06 定位并修复）。原实现按 红>绿>黄 优先级在**全部**灯框上取值 → 演示视频每个循环误报 5~7 次 `red_light`，其中 t≈15.7~16.0s 那几次**真值是绿灯**（横向车道的红灯被当成本方向）。修法：人工标注 `traffic_light_roi`，只统计中心落在 ROI 内的灯；ROI 内漏检时**不退回全画面**。修复后：4 轮实测**每循环恰好 1 次真违规、0 误报、判色 95.6%~97%**。 | `realtime_detector._scene_light_state_from_cnn`；`_redlight_accuracy_verdict.md` |
| **T46** | **灯框收集必须在灯态汇总之前**（2026-10-06 修）。原顺序是"先汇总灯态、后收集灯框" → 用的是**上一帧**判色结果，且同帧白跑两次 CNN。 | `realtime_detector.process_frame` 开头注释 |
| **T47** | **方向类判据（逆行/抢黄灯）有两个致命前提**（2026-10-06 修）：① **静止/微动不判方向** —— 停在停止线前等红灯的车 1~2px 抖动会被读成方向，且判"是否在动"必须用**最近几个采样**（那辆车十几秒前开过 20 米，整段 history 的净位移依然很大）；② **抢黄灯要求越线发生在最近几个采样内**，否则绿灯合法通过的车在黄灯亮起时会被误报。另：`frame_width` 硬编码 1280（画面是 1920）会让"对向车道"阈值偏左 30%。 | `behavior_engine.analyze_wrong_way/analyze_running_yellow`；`vehicle_tracker._analyze_lane_position`；`violation_rules._check_wrong_way` |
| **T48** | **x_std 启发式判逆行只对"道路横向穿过画面"的机位成立**。纵深机位（如本演示，车朝画面里驶离）下车辆因透视自然左漂（x 1550→1306、x_std≈80px < 5%×1920）→ 刚合法越线的车被判逆行。本轮改为"判不准就不判"（`road_direction` 留空 + 启发式只在横向道路启用）。 | `behavior_engine.analyze_wrong_way` |
| **T49** | **`running_yellow`/`speeding` 等规则与闯红灯共用同一套 scene_config**，改灯态/画幅/方向会影响它们；本轮已把三者收敛到"该视频每循环只有 1 条违规（真值那条）"。 | `_redlight_accuracy_verdict.md` §一 |

### 5.2b ★标定优先级与"静默失效"（2026-10-06 第二轮实测挖出）

> 共性：**症状都是"界面显示已标定、实际什么都没生效"**，且都不报错。
> 报告：`_calibration_panel_verdict.md` §三。

| # | 陷阱 | 证据 |
|---|---|---|
| **T50** | **`pixel_per_meter` 会抢在相机几何之前**：`realtime_detector.py` 的 `scene_config` 默认塞 `pixel_per_meter: 10`（违停/旧规则兜底），只要它落进 scene 标注，就一路传到 `SpeedCalibrator` 占用 `ppm_ref`，而几何路径条件是 `if not self.ppm_ref` → **相机参数填对了也不走几何**，对外还显示"已标定（手工 ppm）" | `speed_calibration.py:__init__` ① 分支；现场：面板回 `explicit_ppm` + 地平线空 + 可解比例 0 |
| **T51** | **`lane_width_px` / `crosswalk_zones` 是同一病根的另两条分支**（优先级比几何高）。实测：请求体里根本没发 `pixel_per_meter`，后端仍回 `lane_width` —— 因为旧存档里有 `lane_width_px`。**改这一族逻辑要三条分支一起看** | `speed_calibration.py` ② ③ 分支；抓包证据见报告 §三 BUG-2 |
| **T52** | **"键在、值为 None" ≠ "有参数"**：前端清空字段发的是 `{"camera_height_m": null}`。用 `all(k in s ...)` 判断会把"全空"当成"有相机几何" → 几何构造不出来、`explicit_ppm` 又被 `not self._explicit_cam` 跳过 → 两边都不生效。**必须 `all(s.get(k) is not None ...)`** | `speed_calibration.py:_explicit_cam`；报告 §三 BUG-3 |
| **T53** | **`only_camera` 的粒度也要小心**：`_explicit_cam` 从 `any(...)` 改成 `all(...)` 是对的（只填一项不该拿默认值算），但改动本身引入了 T52 —— **同一个开关改两次才对，别只看第二次** | 同上 |
| **T54** | **`horizon_y = H/2 + f·tan(pitch)` 可能为负**：负值不是错误，而是"地平线在画面上方之外"（俯角大时常见）。演示机位 1280×576/fov90/pitch−23.445 → **−10.5**；界面必须翻译成人话，别直接显示裸负数 | `speed_calibration.py:horizon_y`；`CalibrationPanel.horizonText` |
| **T55** | **`.bat` 脚本必须纯 ASCII**：cmd.exe 在 `chcp` 生效**之前**就解析整个脚本，中文注释（UTF-8/GBK 都一样）会把命令行撕裂成 `'xxx' 不是内部或外部命令`。中文说明放 `.md` | `start-all.bat` / `restart-backend.bat` 头部注释；本轮实测踩两次 |
| **T56** | **启动后端必须带 `PYTHONPATH=E:\output\1\api;E:\output\1`**，否则报 `Error loading ASGI app. Could not import module "app"`（`app.py` 在 api/ 下，而 cwd 是项目根） | 本轮实测；`restart-backend.bat` 已固化 |
| **T57** | **跑 `vite build` 要把 `TEMP/TMP` 指到工作区**：默认用 `%TEMP%` 时 esbuild 清临时文件会 `Access is denied`（沙箱/杀软锁定），build 在"2255 modules transformed"之后失败，看着像代码错 | 本轮实测；`_STARTUP_GUIDE.md` §五 |
| **T58** | **`el-dialog` 关闭是 `display:none`，DOM 仍在**：自动化断言不能查"元素是否还存在"，要查可见性 | 本轮 UI 测试踩过 |

### 5.2c ★第三轮（2026-10-06 晚，用户第二轮反馈驱动）新踩的坑

| # | 陷阱 | 证据 |
|---|---|---|
| **T59** | **事件视频 fps 必须从"片段时间跨度"推导，不能写死 `FRAME_BUFFER_FPS`**。源 20fps 而写死 10 → **时间轴拉长一倍、播放快一倍**；实测 **4855 个事件视频全部 2.0×**。`config.py:80` 的 `EVENT_VIDEO_FPS_FROM_SOURCE` 曾**定义了却全仓没人读**（空壳），现已真正接上。改完别忘了 `replay.json` 的 `fps`/`time` 是**按同一个 fps 算的**，不同步会让回放叠加框逐渐错位 | `realtime_detector.py` 事件视频保存处；用户报告 `evt_11200_18_60c808` |
| **T60** | **`v-if`/`v-else` 不能跨组件边界**：写在 `<el-tooltip>` 内部的 `el-input` 上、`v-else` 留在外面 → Vue 编译报 `Invalid end tag`（`file: ...vue:undefined:undefined`，**不给行号**，很难查）。要成对写在**同一层** | `LiveMonitor.vue` 本轮实际报错 |
| **T61** | **前端"设置页"可能整栏是装饰品**：`Settings.vue` 的 `saveAiConfig()` 全文只有一句 `ElMessage.success()` —— 不调接口、不落盘、刷新即丢。**判断一个开关真假的唯一办法：改一下，再回读后端接口**。本项目现有真开关都在 `/api/realtime/settings`（`cloud_review` / `cloud_consult` / `cloud_review_uncalibrated` / `hold_sec` / `cooldown_sec` / `display_mode`） | `Settings.vue` R3；本轮已改造 |
| **T62** | **上传接口的 `result` 作用域 bug**：变量只在"图片 + run_ai=true"分支赋值，后面**无条件**读 → 视频上传 / `run_ai=false` 抛 `UnboundLocalError`（**视频上传必失败**，与大小无关）。教训：分支里赋值的变量必须在函数开头初始化 | `routers/violations.py` 本轮实测 + git 原始代码隔离复现 |
| **T63** | **测大文件上传不能用 requests 的生成器文件对象**：`requests` 对无 `__len__` 的类文件对象改用 **chunked** 传输，uvicorn/Starlette 会截断（实测只传 1MB 就 200 返回，看着像"限制没生效"）。**必须用磁盘真实文件 + `curl -F`** | 本轮实测 |
| **T64** | **上传被拒必须删除半成品**：原实现先 `open(path,'wb')` 再判大小 → 被拒时磁盘留半个垃圾（现场就有个 `upload_c6ddb831_*.mp4` 0 字节孤儿）。改流式写后要显式 `os.remove` | `routers/violations.py` |
| **T65** | **删除类 SQL 禁止用 `like` 批量**：我用 `where image_path like 'upload_%' limit 10` 清测试数据，**误删 6 条旧演示记录**（id 19~24）。必须**先列清单 → 按精确 ID 执行** | 本轮我的真实教训 |
| **T66** | **`ffmpeg`/`ffprobe` shim 的解析顺序**：项目是 `imageio_ffmpeg` 自带（`site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe`）**优先于 PATH**；所以 PATH 上的 shim 坏掉不影响项目转码，只影响手工命令。CanMV IDE 自带 FFmpeg n6.0 完整版可作 shim 备选（**无 libx264**，重封视频要用 imageio 那个 7.1） | `circular_frame_buffer._get_ffmpeg_exe`；本轮实测 |
| **T67** | **`/live` 曾**没有导航入口**（只能手打 URL），且不在 `App.vue` 的 `subToMain` 映射里 → 进去后顶部导航一项都不高亮**。现已加「实时监测」「交通事件」两个顶级项 | 用户反馈 R1；本轮修复 |
| **T68** | **`/api/realtime/evidence` 会随抓拍文件数线性变慢**：原实现 `glob` 全部 + 逐个 `os.stat` + 排序，**才**切片 `limit`。实测 `uploads/` 涨到 4526 个文件（4513 张抓拍）时**每次请求 500 ms**，而 `/live` 每 1.5 秒轮询一次 → 持续 I/O 抖动、界面发顿。修法：`os.scandir` 单次遍历 + 取前 N 再建对象 → **10~19 ms**。⚠ **同类写法的接口都要按这个模式复查**（先排序/截断，再做重活） | 本轮实测；`routers/realtime.py` `/evidence` |
| **T69** | **`app.py` 的 `log_dir` 曾是相对 cwd 的 `"output/logs"`** → 从项目根启动写 `1\output\logs\api.log`，从 `api\` 启动写 `api\output\logs\api.log`。**"日志在哪"取决于启动方式**，排查时极易看错文件（本轮我就误判成"日志没在写"）。已锚定绝对路径 `api\output\logs\` | `app.py:setup_logging` |
| **T70** | **重定向启动后端时，stderr 有缓冲**：刚启动时读日志文件可能仍是 0 字节，**不代表没写**。要判断"日志是否在工作"，先发一次请求再看文件大小 | 本轮实测；`backend_stderr.log` |
| **T71** | **`uploads/` 目录会无限增长**：现有 **4526 个文件 / 2234 MB**，抓拍图按 `realtime_{类型}_{时间戳}.jpg` **每帧违规都存**，没有保留策略。⚠ 清理属删除操作，**必须先问用户** | `routers/realtime.py` 抓拍落盘处 |
| **T72** | **"框跟不上车"的真因不是算力**：模型只占 **139 ms/帧**、GPU 仅用 **393 MB/8585 MB**，但端到端单帧 **558 ms** → 每帧画面时间跳 **0.30 s**（6 帧没检测）。**单纯提 `FRAME_RATE` 几乎无效**（1.79→1.92 fps）——瓶颈在渲染/编码/事件/落库等**非模型环节** | `_PERF_FPS_verdict.md` §二；`_scripts/_ab_fps_configs.py` |
| **T73** | **`license_plate` 模型文件不存在 → 静默回退 COCO `yolov8s`**，每帧产出 **12 个垃圾框**（`fire hydrant`/`potted plant`/`sports ball`），白花 ~30 ms 且污染 `all_detections`。**用 `YOLO_MODEL_SEQUENCE` 裁掉**（helmet/lane 不要裁，那是功能） | `image_recognizer.multi_model_detect` |
| **T74** | **`tracked_vehicles` 是 `{track_id: {...}}` 的 dict，不是 list**（`vehicle_tracker` 返回 OrderedDict），而 `AnnotationRenderer.render(tracked_vehicles=...)` **也要求 Dict**。把它当 list 遍历 → 遍历出字符串键 → `v.get()` 抛异常 | 我在 `_predict_boxes` 上踩的坑（P2/P3） |
| **T75** | **★`try/except` 兜底会把类型错误彻底静默**：我加了"任何异常都退回原框"的兜底，导致框预测**从未生效却毫无迹象**。**兜底必须配可观测计数**（`prediction_stats` 的 `ran`/`skip_*`），否则等于埋雷 | `realtime_detector._pred_stats`；靠它才发现 `ran=47` 但输出为空 |
| **T76** | **单元测试用错输入类型 = 无效验证**：我拿 **list** 喂 `_predict_boxes`，"6 场景全过"其实只证明"喂错类型时不崩"（异常被吞）。**写测试前先核对上游真实类型** | O40 |
| **T77** | **修 bug 时新增的字段必须能被外部观测**：核对"helmet/lane 到底在不在跑"时只能翻日志，而 `cmd /k` 新窗口的 stdout **不落在日志文件里** → 无法判定运行实例的真实配置。现 `/status` 自报 `model_sequence`/`yolo_imgsz`/`box_prediction`/`predicted_boxes`/`prediction_stats` | 同上；同类教训见 U1/G3 |
| **T78** | **前端"轮询回写"会覆盖一次性查询的结果**：`refresh()`（每 1.5 s）里 `if (sc) roiMissing.value = (sc === 'frame')`，而**未启动检测时后端固定返回 `frame`** → 把 `loadRoiState()` 得出的"尚未标注 ROI"覆盖成 false，按钮永远不报警告。**标注态（查配置）与运行态（查 status）必须分成两个状态** | `LiveMonitor.vue` 的 `roiMissing` / `lightScope` |
| **T79** | **`python -c` 内联脚本输出非 ASCII 会崩**：控制台是 GBK，打印 `✓`/`✗` 直接 `UnicodeEncodeError`，**统计结果一个字都出不来**（我因此白跑两轮）。脚本内输出保持纯 ASCII，中文写进文件 | 本轮实测两次 |
| **T80** | **重启脚本可能"假成功"**：`restart-backend.bat` 若在端口检测环节漏判（`netstat`/`findstr` 对中文 `LISTENING` 匹配不到），会直接启动新实例 → **新实例绑不上端口即退出**，而自检打到的是**旧实例**，看起来一切正常。**验证重启必须核对监听进程的创建时间/PID，不能只看自检输出** | 本轮实测；`_PERF_FPS_verdict.md` |



### 5.2d ★界面上的"真开关"与"假开关"（务必分清）

| 开关 | 位置 | 真假 | 后端字段 |
|---|---|---|---|
| 事件级云端 AI 复核 | **系统设置 → AI模型配置**（也可在实时监测页控制条） | ✅ **真** | `cloud_review` |
| 逐帧云端咨询 | 同上（实时监测页原叫「云端复核」，易混，已改名） | ✅ **真** | `cloud_consult` |
| 未标定的超速也送云端复核 | 系统设置 → AI模型配置（**建议保持关**） | ✅ **真** | `cloud_review_uncalibrated` |
| 违规确认时长 / 同类违规冷却期 / 画面标注档位 | 同上 | ✅ **真** | `hold_sec` / `cooldown_sec` / `display_mode` |
| ~~启用AI审核~~ / ~~启用兜底模型~~ / ~~默认模型~~ / ~~超时~~ / ~~重试次数~~ | 原「AI模型配置」栏 | ❌ **假（已删除或改为"未实现"说明）** | 无 |
| 通知设置那一栏 | 系统设置 → 通知设置 | ❌ **假**（`saveNotificationConfig` 同样只弹提示） | 无 —— **尚未处理** |

### 5.2e ★第七轮（2026-10-10）新踩的坑 —— 全部围绕"标定到底生效了没有"

> 报告：`_design_2026-10-09_verdict.md`。**这一节请与 §5.2b（标定优先级与静默失效）连读。**

| # | 陷阱 | 证据 |
|---|---|---|
| **T81** | **★"看得到的画框"与"判定用的数据"是两份，过滤时必须只动绘制那份**。`_collect_traffic_lights()` 把画面里**所有**判出颜色的灯塞进 `_last_traffic_lights`，而灯态判定 `_scene_light_state_from_cnn()` 读的**就是它**、并自己按 ROI 过滤；渲染器也读它、**原先完全不过滤** → 用户"左边不该识别的红绿灯还是识别了"。修法：在 `_draw_detection_boxes()` 里只过滤**传给渲染器的副本**，绝不改 `_last_traffic_lights` 本身 | trace 铁证（73 帧）：`('yellow',(419,120))` 144 帧、`('red',(275,182))` 72 帧**全在 ROI 外**；同批 73/73 帧 `matched == ROI 内灯数`（判定语义未被改动）。`_scripts\_verify_trace_roi_filter.py` |
| **T82** | **★同一个"类名"在检测侧与绘制侧各写一份手写名单，必然漂移**。绘制侧原判 `("traffic light","traffic_light","red_light","green_light","yellow_light")`，检测侧判 `("traffic light","traffic_light","red_light","green_light","yellow_light","red","green","yellow")` —— **两套不一致**，且后者多了判色器实际输出的**裸色名**。后果：上游吐 COCO 原生 `"traffic light"` 或裸色名时，红绿灯**漏进车辆绘制分支**被画成灰框 + 英文标签，按灯色着色的配色整体失效。修法：收敛为 `annotation_renderer.TRAFFIC_LIGHT_CLASS_NAMES` 一个 frozenset，两处共用 | `annotation_renderer.py` 该常量处注释；`realtime_detector` 模块级 `_TL_LIGHT_NAMES` |
| **T83** | **★"检测类白名单"必须按白名单裁，不能按黑名单排**。COCO 80 类里 83 个类名与交通无关（`potted plant`/`fire hydrant`/`sports ball`/`chair`/`bench`/`dog`…），只排"盆栽"等于掩耳盗铃（下个视频冒出别的）。裁点选在 `process_frame()` 的检测出口（`result['detections'] = ...` 之前），规则引擎/行为引擎/跟踪器/渲染器**同时**受益。⚠ 该集合是**判定链路的输入契约**：`violation_rules` 里新增类名分组时必须同步补，否则那条规则被**静默废掉** | 实测 kept=1644 / dropped=252（全是 `potted plant`）；`/status` 的 `class_filter_stats` |
| **T84** | **★★`/status` 里"绘制侧"的计数会冻住 —— 没有 MJPEG 客户端时 `_draw_detection_boxes()` 根本不跑**。实测：无浏览器时 `traffic_lights_collected=12 / drawn=6` **恒定不变**，而 `traffic_light_matched` 已变到 8 → 看起来像"过滤算错了"，其实是"没人请求画面，绘制侧那一帧的计数没再更新"。**读这类字段必须先确认有没有流客户端**。另：`drawn` 统计在 `_dedupe_traffic_lights` **之前**，所以它 ≥ 最终画出的框数 | 400ms × 18 次采样（本文件同批实测）；`get_status()` 该字段处注释 |
| **T85** | **★热重载的判定依据要按"原始字符串"算哈希，不能事后重新推导**。`scene_annotation.video_key()` 对**源字符串本身**取 sha1 —— 差一个字符就是另一个键。若在 `start_camera()` 里用归一化后的 `norm` 加载、之后却拿 `_source_path` 重新推导路径，**可能落到另一个文件**（热重载永远检测不到变化）。修法：源就绪时把 `_path_for(norm)` **算一次存下来**（`_scene_cfg_path`），之后只 `os.stat` 它 | `realtime_detector._scene_config_path()` 注释；实测 1→4 ROI 热重载成功 |
| **T86** | **★手工重启后端会静默丢掉 `TUNE_*` 调优**（`YOLO_IMGSZ=960` / `FRAME_RATE=6` / `YOLO_MODEL_SEQUENCE=vehicle,traffic_light,helmet,lane` / `BOX_PREDICTION=1`，只在两个 `.bat` 里设置）。实测：我手工 `python -m uvicorn` 起了一次 → `/status` 立刻变成 `imgsz=1280`、模型序列多出 `license_plate`（回退 COCO 吐垃圾）、`frame_rate=3` —— **性能悄悄退回上一轮之前**。**判定"配置对不对"永远看 `/status` 的 `model_sequence`/`yolo_imgsz`/`frame_rate`，不要相信"我起的时候设了"** | 本轮实测（同一台机器、同一份代码，仅启动方式不同） |
| **T87** | **★手工启动后端还容易漏 `PYTHONPATH`**：少了它直接 `Error loading ASGI app. Could not import module "app"`，进程**秒退且窗口一闪而过**（`Start-Process` 无窗口时表现为"启动了但 8001 不监听"）。而 `/health` 一旦能通则说明**模型已加载完**（本轮实测 3 秒即通） | 本轮实测两次（T74 同源）；`_STARTUP_GUIDE.md` §五 |
| **T88** | **★"源不一致"是标定失效的头号原因，且它同时坑了判定与提示**：`LiveMonitor.loadRoiState()` 原先读**输入框**的源、标定面板也读输入框 → 输入框被刷新重置成硬编码旧视频时，**按钮永远显示"未标"、面板在旧视频首帧上画、保存到旧视频**。修法三件套：① 干掉硬编码默认源（改 `localStorage`）；② 面板 `source` 改从 `/status` 的 `video_path`‖`source_url` 推导；③ 不一致时红警告 + 禁止保存（带显式越权勾选） | `LiveMonitor.vue` 注释；`CalibrationPanel.vue` 的 `.cal-alert`；实测面板首帧从 1280×576（旧视频）变为 **1920×1080**（演示视频） |
| **T89** | **★"每辆车两个框"的真身 = `bbox_to_track` 用 bbox 精确匹配，而框预测把 bbox 平移成了 float**。取整后键不再相等 → 主循环 `tid=None` → 画车型标签且**不登记 `drawn_tracks`** → 兜底循环（遍历 `tracked_vehicles`）**又画一次带 ID 的** → 一辆车两个框、还重叠。**这是"仅显示用"的框预测引入的回归**（预测本身没错，错在关联方式）。修法：多级关联 `_match_track_for_detection()` —— ① `det['track_id']`（检测链路已回填）② 精确 bbox（旧行为）③ ±3 px 容差 ④ IoU≥0.15 ⑤ 中心距≤0.30×对角线，且**一个 track 只被一条 detection 占用**（`used_ids`） | `annotation_renderer._match_track_for_detection`；`_scripts\_verify_two_boxes_fix.py` **20/20**（含"旧逻辑在预测开启时确实产生 2 个框"的可复现证明） |
| **T90** | **★"有时候显示 ID、有时候显示车辆类别"不是两个框，是关联失败的过渡帧**。跟踪器刚建立/刚丢失时 detection 关联不到 track，旧代码把**原始类名**（`car`/`truck`）当标签画，而正常帧画 `IDxx` → 同一辆车一会儿 "car" 一会儿 "ID18"，看起来像两套标注。**用户已定口径：没 ID 就画灰框、什么都不显示**。现三色分工：绿=已追踪正常 / 红=已追踪违规 / **灰=尚未追踪（无标签、无箭头）** | 用户 2026-10-10 原话："有时候会显示ID，有时候会显示车辆类别，我还以为是两个识别框重叠了"；`COLOR_UNKNOWN`；单元测试 5a/5b/5c 验证三色 + "灰框零文字" |
| **T91** | **★这类"视觉回归"必须变成可自动检测的字段**：两个框**不报错、不写日志**，只能靠肉眼看出来（用户就是这么发现的）。现在 `/status` 的 `box_draw_stats` 暴露 `main_boxes` / `fallback_boxes` / `unmatched_dets` / **`max_dets_per_track`**（>1 = 会画重框）/ `tracks_drawn`。⚠ 与 `traffic_lights_*` 同理：**只有真有 MJPEG 客户端时才会更新**（绘制侧不跑就不刷新），`last_update` 用于确认新鲜度 | `annotation_renderer._BOX_STATS` + `get_box_draw_stats()`；实测 `main=2 tracks=2 max_dets_per_track=1 fallback=0 unmatched=0` |
| **T92** | **★★运行时设置只存内存 = 每次重启都把用户关掉的付费开关重置回默认（True）**。`RUNTIME_SETTINGS` 是模块级字典，`cloud_review`/`cloud_consult` 默认 `True`。铁证：用户 22:01 关掉两个开关 → 22:13 按流程重启后端 → `/settings` 立刻变回 `true/true`。**这就是"开关自己打开"的根本原因**（前端连带推送只是第二层）。修法：`update_runtime_settings()` 落盘 `api/output/runtime_settings.json`，启动时 `_load_persisted_runtime_settings()` 读回；只持久化安全字段（不含 `TUNE_*` 那类环境变量项） | `realtime_detector._PERSIST_KEYS`；实测重启后仍为 `false/false` |
| **T93** | **★视频时间不是 Unix 时间戳，落库前必须换墙钟**。事件引擎的 `trigger_time` 装的是**视频时间**（`(frame_count - 循环基准)/fps`，用于在帧缓存里定位关键帧），而落库时直接 `datetime.fromtimestamp(trigger_time)` → **视频第 10.95 秒变成 1970-01-01 08:00:10**。实测库里 **566 行**是 1970 时间戳（2026-10-12 只读查库复核：`traffic_events` 共 3209 行）；更早的"负数"版本反而因 `fromtimestamp` 抛异常被 `except` 兜成 `now()` 而**看起来正常**（巧合掩盖了 bug）。修法：事件新增 `wall_time` 字段，落库用它 | `traffic_event_engine.TrafficEvent.wall_time`；修复后新建事件全部为正确墙钟 |
| **T94** | **★`_loop_frame_base` 必须与 `frame_count` 同时归零**。`start_detection()` 把 `frame_count=0` 却漏了 `_loop_frame_base` → 新一轮开始后视频时间是**大负数**（−119s/−231s/−327s）→ 事件 ID 带负号、取证窗口错位取到**上一圈**的帧 → 云端复核看到空路口判 rejected。实测最近 400 条事件里 **14 条**为负，最早可追溯到 2026-10-06（该时钟机制上线当天）。⚠ **别用"负值就返回墙钟"来兜** —— 我试过，导致事件表出现 1970 行，比负数更糟 | `start_detection()` 内注释 |
| **T95** | **★证据图文件名只有"秒"精度会互相覆盖**：`realtime_{类型}_{YYYYmmdd_HHMMSS}.jpg` —— 同一秒内两条**同类型**违规（多车同时闯红灯）后写的会覆盖前一张，而两条 DB 记录都指向同一文件名 → 其中一条的图**内容不对**（证据可追溯是红线）。修法：加毫秒且用 `-` 分隔（`..._HHMMSS-mmm.jpg`；用 `-` 是为了让"最后一个下划线后是时间戳"的类型解析规则继续成立），列表接口正则同步放宽 | 实测 `realtime_red_light_20261010_223901-697.jpg` |
| **T96** | **★前端 logger 的 `extra` 曾存"原始对象"= 导出必崩 + 落盘静默失败**。`push()` 里 `JSON.stringify(a)` 失败就把原对象塞进 `extra`；导出时再 stringify → `Converting circular structure to JSON`（用户实测报错），而 `persistNow()` 的同类错误**被 try/catch 吞掉** → 那条日志永远存不下来。修法：`_safeJson()`（循环引用/DOM/组件→占位符）+ `extra` **只存字符串** + 导出失败时**逐条降级导出**。⚠ 坑中坑：`val instanceof Node` 会触发 **Vue 响应式 Proxy 的 getPrototypeOf 陷阱**，目标不可扩展时**直接抛错** → 所有对象都变 `[Unserializable]`（实测导出仅剩 18 字节）。**这类 replacer 里只能用"读属性"做鸭子类型，禁止 `instanceof`/`getPrototypeOf`/`constructor`** | `utils/logger.js` `_safeJson` 注释；`_uicheck\_run_loggerexport.mjs` **6/6** |
| **T97** | **★演示视频"循环播放"会让同一违规每圈重新取证**。测试视频里闯红灯的车是固定的那几辆；每回放一圈 tracker 就重新编号（track=1 先后被不同车占用），而 `_viol_hold` 每圈清空、`_viol_last_report` 用的是**每圈归零的视频时间** → 同一辆车、同一位置、同一个红灯，**每圈都生成一条新记录**。铁证：`position` bbox 落在同一个 40px 桶的记录 **141 条**，间隔稳定 30/31 秒（= 一圈墙钟），track_id 每次都不同。修法：`loop_dedup_sec`（默认 300s，**墙钟**）+「类型 + 位置(40px 网格，查 **3×3 邻域**)」指纹跨圈抑制。实测 5 分钟窗口产出 **9 条 → 3.4 条** | 用户原话"重复的无意义的取证"；`_viol_position_key` / `_viol_neighbor_keys`；`/status` 的 `loop_dedup_sec` |
| **T98** | **★杀后端只杀 python.exe 会留下"空白命令行窗口"**：两个 `.bat` 用 `start "ZhiTong Backend API" cmd /k ...` 起后端，`cmd /k` 是**父进程且常驻**。只 `Stop-Process` 掉 python 子进程时，父 `cmd` 窗口**不会退出**，留在桌面上就是一个**标题为 "ZhiTong Backend API" 但里面什么都没有**的黑窗口。2026-10-10 我反复重启后端（Python 代码改动多轮），**累计留下 8 个空壳窗口**，用户直接看到并质问。**正确做法：要么用 `restart-backend.bat`（它按端口找 PID 并整套处理），要么杀进程时连父 cmd 一起收拾**；事后清理要**先确认全系统 python.exe 只剩当前那一个**（否则可能误杀正在服务的实例） | 实测：`Get-CimInstance Win32_Process -Filter "Name='cmd.exe'"` 列出 8 个 `cmd /k cd /d E:\output\1`（22:12~22:33），而当时全系统只有 1 个 python.exe |
| **T99** | **★★后端"像断网"的真身是 `cv2` 自带 FFmpeg 解码器原生崩溃（已 5 次，同一偏移）**，不是"僵尸 MJPEG 流占满线程池"。用户导出的前端日志给出决定性判据：**25 个 HTTP 500 + 2 个 NO_RESP，覆盖 9 个不同接口**，`cost` 序列 **4669ms → 3170 → 1671 → 175 → 6 → 4ms**（典型"排队积压后瞬间全失败"），**只持续 8 秒**；而同一时刻 Windows 事件日志记录 `python.exe` 崩在 `opencv_videoio_ffmpeg500_64.dll`（`0xc000001d`，偏移 `0x2e9930`）。⇒ **进程死了**，那 25 个 500 是 uvicorn 临死前的挣扎。**判据教训：设计单 §12.1 预判的是"timeout 15000ms"，实测却是"500 全站"—— 两者根因完全不同，别照预判下手** | `C:\Users\ROG\Desktop\zhitong-frontend-log.json`（4.5MB/264 条）+ Windows 事件日志 23:13:54；分析脚本 `_scripts\_analyze_frontend_log.py` |
| **T100** | **★演示素材 `dual_cam_demo_lossless.mkv` 是 FFV1 无损 / BGRA / 373 Mbps**（1156 MB，26 秒）—— 这是个**极不寻常**的编码，正是崩溃所在解码路径。已转出 **H.264 版本** `dual_cam_demo_h264.mp4`（7.5 MB，**同时长同帧率**，抽帧对比平均像素差仅 **2.02/255**，判色/演示无影响）。⚠ **换素材会踩 T101** | `_scripts\_stress_cv2_decode.py`（单独解码 1040 帧不崩、3 线程并发 6334 帧不崩 → 崩溃需"整链路 + 有画面客户端"的组合条件）；`_stress_concurrent_decode.py` |
| **T101** | **★场景标注按"整条源路径的 sha1"存储 → 同一录像的不同编码是两个键，换素材会静默丢掉全部人工标定**（信号灯 ROI / 停止线 / 相机几何），界面只表现为 `scope=frame`；而灯态判据一失效，闯红灯就退化成"画面里任意一盏灯"（每循环误报 5~7 次）。**我试过在 `load_scene` 里做"同文件名主干兜底匹配"——实测不成立**（`dual_cam_demo_h264_` 与 `dual_cam_demo_lossless_` 前缀不同；要命中就得放宽到 `dual_cam_demo_`，会把同目录所有视频混成一个标注，风险大于收益），**已撤回**。改为**显式动作**：`_scripts\_copy_scene_config.py <旧源> <新源>`（只新增目标键、不改不删原文件、已存在默认拒绝） | 实测：换 `.mp4` 后 `/status` 的 `scope=frame`、`scene_annotation_roi_count=0`；复制后两个源都 `ROI=4`、`scope=roi` |
| **T102** | **★★"违规告警栏来不及反应"的真身 = 违规车一驶出画面，那条告警就被撤掉**。`/api/realtime/vehicles` 里有一句 `if tid not in _valid_ids: tid = None` —— 提取到的 track_id 若不在**当前**追踪集合里就置空，于是该违规归不到任何车上，右栏立刻消失。实测：右栏只存在 **2.89 秒**，而违规缓存本身有 **10 秒**；前端 1.5 秒才轮询一次 → **最坏情况整段错过**。修法：ID 失效**不再丢弃**，改用违规缓存自带的 bbox 生成一张 `stale=True` 的卡片（前端标注「已离开画面」），保留到 TTL 结束；同时前端轮询 1.5s → **0.8s**、聚焦小窗跳过 stale 条目。**实测窗口 2.89s → 10.15s、延迟 ≈ 0** | 用户原话"违规告警页面很慢，有时候甚至还来不及反应"；`_scripts\_measure_violation_panel_lag.py`（0.25s 采样对照 `/status` 与 `/vehicles`） |
| **T103** | **★`_recent_violations` 的 TTL(10s) 才是右栏告警的真实寿命**（不是"违规持续多久"）。因为违规只在"通过 hold+cooldown 闸门"的那一帧才被 `_push_recent_violations` 写入，之后 8 秒冷却期内不再写入 —— 所以卡片在"最后一次写入 + TTL"时消失。调这个 TTL（`RECENT_VIOLATION_TTL`）就是调告警停留时长 | `realtime_detector._push_recent_violations`；实测两段窗口 10.15s / 9.91s 与该 TTL 吻合 |
| **T104** | **★★"违规告警栏长时间毫无反应" = 我上一轮加的 `loop_dedup_sec` 把展示一起掐掉了**。那个抑制本意是"同一车同一位置 5 分钟内不重复**存证据**"，但它作用在**上报闸门**上 → 违规连 `_recent_violations` 都进不去 → 右栏长时间挂着"暂无违规"。实测：后端累计违规已 6 条，右栏卡片 = 0；随后 **129 秒**才动一次。**根因算式**：检测约 2.4 fps × 520 帧 = **一圈墙钟约 217 秒**，而抑制窗口 **300 秒 > 一圈**，等于把后面整圈都压掉了。修法：抑制**只作用于"存证据/计费"**，被抑制的重复违规**仍然喂展示缓存**并打 `repeat=True`（前端标注「重复出现」，蓝色，与「已离开画面」橙色区分）。同类第三种状态：ID 不在当前追踪集合 → `stale=True`「已离开画面」。修后实测每约 30 秒必然出现一次（采样占比 24/60），浏览器侧 API 94 次 / DOM 90 次一致 | 用户原话"违规告警窗口有时候甚至就没有任何反应"；`_push_repeat_alert`；`_uicheck\_run_panel_dom_check.mjs`（DOM vs API 同时对齐） |
| **T105** | **★排查"界面不更新"必须同时记录「接口返回什么」与「页面显示什么」**。我前两轮只测了接口（`/vehicles` 确实有数据、窗口也确实 10 秒），就以为修好了 —— 其实用户看到的页面与接口**根本不同步的原因在别处**（是数据源被抑制，不是渲染）。后来用真实浏览器在**同一时刻**取 DOM 文本 + 直接 fetch 接口，才一次看清：`API=[] 且 DOM=0` 说明"没有数据"，而不是"渲染坏了"。**两类症状（无数据 / 渲染坏）必须这样区分** | `_uicheck\_run_panel_dom_check.mjs`；对比 T84（绘制侧计数冻住） |
| **T106** | **★"告警栏"与"抓拍证据"是两条不同职责的展示，别混**。用户最终口径（2026-10-10）：**"汽车离开画面后就不用显示了……只要下方的违规抓拍证据能有记录就行，而且最好要有违法时间等关键信息"**。⇒ 告警栏只服务"画面里正在发生的违规"（车走了就撤卡）；**留痕由抓拍证据承担**。我一度做成"车走了仍保留告警卡（标「已离开画面」）"，属于**没问清职责就下手**，已按口径撤回。⚠ 真正修掉"没反应"的是 T104 那层（重复违规也喂展示），与"车走了要不要留卡"是**两件事** | `routers/realtime.py` `/vehicles` 内注释；`/evidence` 关键信息字段 |
| **T107** | **★抓拍证据必须带"违法时间等关键信息"**：原 `/api/realtime/evidence` 只回 文件名/类型/大小/紧凑时间戳（`20261010 221353`），看不出"什么时候违的、哪辆车"。现在按 `image_path` **批量**查 `violation_evidences`（只查要返回的那 ≤limit 行，避免 T68 的性能坑），回带 `captured_at`（文件名，**最可靠**）/ `violation_at`（落库时间）/ `track_id` / `confidence` / `plate_number` / `review_status`。实测两者只差 **30 毫秒**（`captured 00:20:02.223` vs `violation_at 00:20:02.255`）→ 抓拍与落库同一时刻，**无错位** | `routers/realtime.py` `/evidence`；`_uicheck\_run_evidence_info_check.mjs` 5/5 |
| **T108** | **★★"告警栏比画面标注慢"的答案是两条不同链路：画面是"推"、告警栏是"问"**。画面左上角的标注由检测那一帧**直接画在图上**，进 MJPEG 流（20fps 持续推）→ 追加延迟 ≈ 0；告警栏写进缓存后由前端**定时轮询** → 追加延迟 = 一次轮询周期（平均 T/2、最坏 T）。**实测后端→接口的延迟是 0ms**（`_scripts\_measure_alert_latency.py`），慢的全在轮询等待（当时 T=800ms）。**修法：接上项目本来就有的 `/api/realtime/violations/stream` WebSocket**（后端 `_push_violation_event` 一直在推，但**前端从来没人接**），收到推送即刷新（推送只作"触发器"，数据仍走单一来源 `/vehicles`，避免两套解析漂移） | 用户问"明明用的是同一个代码？"；`LiveMonitor.connectViolationWs` |
| **T109** | **★★★WebSocket 推送曾被静默吞掉：`send_json` 异常被 `except Exception:` 吃掉只做"移除客户端"**。症状极具迷惑性：`push_scheduled` 在涨、`push_failed=0`、前端日志显示"已连接"、**但一条都收不到** —— 我为此绕了三轮（先怀疑 CDP 抓不到帧、再怀疑 Vite 代理）。**两个独立缺陷叠加**：① `vite.config.js` 的 `/api` 代理**没开 `ws: true`**，WebSocket upgrade 不被转发 → 前端改用**直连 `127.0.0.1:8001`**（项目本来就有直连先例 `realtimeRequest`）；② 后端的发送异常**没有任何可观测痕迹**。修法：异常处 `_ws_push_failed += 1` + `logger.warning`（T75 的老教训：异步/兜底路径必须可观测）。另在 `/status` 暴露 `ws_push`（`ws_clients` / `push_loop_alive` / `push_scheduled` / `push_failed`） | 修后实测：Python 客户端 2/2 收到、浏览器侧 `收到 violation_detected 推送: 2 次`、`push_failed=0` |
| **T110** | **★★"告警栏仍比画面标注慢半拍"的最后一层：推送发得太晚**。三处都取到数字、逐一排除后才定位：① 前端埋点 `window.__alertLatency`：WS 收到推送 → DOM 出现卡片 = **152~277ms**（其中 150ms 是我加的去抖）→ 前端不是瓶颈；② 事件引擎耗时 = **0~0.2ms**（峰值 10ms）→ 也不是它；③ 剩下的是**这一帧的处理时长**：画面标注在 `process_frame` **内部**就画好了，而推送原先要等这个函数**跑完**（`worker()` 里返回之后）才发 → 告警栏整整晚后半截（单帧 ~0.4~0.5s）。**修法：`_push_violation_event` 提前到"画完框、写好展示缓存"那一刻**，事件引擎/落库/云端都排到推送之后；**同时删掉** `worker()` 里的原推送点（原地留注释防止有人"补回来"）—— 实测 `violation_count=2 / push_scheduled=2` 一一对应，**无重复推送** | 浏览器埋点 + `/status` 的 `event_engine_ms`；`LiveMonitor.vue` 的 `window.__alertLatency`；`_uicheck\_run_alert_latency_probe.mjs` |
| **T111** | **★"左边正常通行栏很快、右边违规告警慢"≠ 两条数据通路不同**：两者在**同一个** `/api/realtime/vehicles` 响应里（`clean` / `violators`），同一请求、同一帧数据。差的是**这份数据什么时候才产生**：`clean` 依赖每帧更新的 `tracked_vehicles`；`violators` 依赖**违规判定成立**（要过 hold 闸门），且它的推送时机原先排在整帧处理之后。**排查"两栏不同步"先确认是不是同一个请求**，别去改请求层 | `routers/realtime.py` `/vehicles` 一次返回 `{clean, violators, traffic_lights}` |
| **T112** | **★另一种故障形态：`/status`+`/vehicles` 各超时 14 次、cost 精确 15000ms（两个直连后端的接口）**，而同一时刻**后端仍在正常跑检测**（日志帧号连续、无空档）。⇒ 是"进程活着但不响应 HTTP"（阻塞在锁/IO 上），与"原生崩溃导致全站 500"是**两种不同故障**。用户还原的那份日志正是这种（`_evidence\zhitong-frontend-log_export-20261011-0016.json`）。**GPT6 可继续查**：`_scripts\_probe_log_gap.py` 能扫出日志空档，`_scripts\_analyze_frontend_log.py` 能按状态码区分两类故障 | 两级证据：前端日志（NO_RESP×28 / cost=15000）+ 后端日志同期帧号连续 |

### 5.3 测速标定（`speed_calibration.py`）

| # | 陷阱 | 证据 |
|---|---|---|
| T12 | **（2026-10-06 更正）`ground_plane_ppm()` 数学是**对的**，"偏小 0.61 倍"是假象。** 旧结论对照的是 `_dual_cam_demo\ground_truth_dual.csv` 的 cam1_u/v，而那两列**不是测量值**（是 `_dual_cam_demo.py:217/231` 里 `Proj.project()` 自己算出来写盘的模型输出 —— 同参数重算 580 行，u 中位误差 0.51 px）。用独立推导的正确几何与它对照：比值 **1.001~1.003**。真正让车速算错的是**默认参数**（h=8.0/pitch=−20 → ppm 比仅 0.717）。 | 本轮实测；`_speed_calibration_verdict.md` §二/§三 |
| T13 | **`ground_plane_homography()` 保留为可选实现**（三次失败记录仍有效：另推等价矩阵差 58 m、近点大横向退化、底边 4 点共线）。**但 2026-10-06 起不再是主路径也不再是"唯一选项"**：`make_unprojector()` 已修好并验证；需要单应时请用新增的 `homography_from_ground_points()`（人工点选已知地面点，含 RANSAC + 退化校验 + 残差自检）。 | `speed_calibration.py` 对应函数注释 |
| T14 | **`assumed_lanes` 兜底在"相机高 + 俯角大"机位下会系统性高估**（方向仍成立）。⚠ 但原证据里的"真值 11.6"取自同一条**损坏引用链**，具体倍数（9 倍）待复核。**现行做法**：没有显式相机参数就不再走几何路径，`assumed_lanes` 只作最后兜底，且被"未标定不判超速"门禁拦住（T17）。 | `speed_calibration.py:__init__` 兜底分支 |
| T15 | **帧率补偿默认关闭**。补偿表是**单次测量**拟合的（每帧率只跑一次），而 tracker 像素速度方差达 ±30%；15fps 未补偿 −15.3%、补偿后 **+16.2%（过冲 31 个百分点）** → 会误报超速（比漏报严重）。需要时 `SPEED_FPS_COMPENSATION=1`。 | `speed_calibration.py:650-661` |
| T16 | **物理防护阈值不可绕过**：`MIN_TRUSTED_PPM = 3.0`（目标太远/接近地平线 → 不测速）、`MAX_PLAUSIBLE_KMH = 180.0`（超限判无效）。踩坑现场：bbox 在 y=102 时 ppm 趋 0 → 算出 **158.6 km/h**，真值 22 km/h。 | `speed_calibration.py:519-521`、`:610-637` |
| T17 | **"未标定不判超速"门禁**：`behavior_engine.py:434-449` 中若 `calib_conf/method` 以 `assumed` 开头，且 `allow_uncalibrated_speeding=False`（默认），则**只记录证据、不判违规**。这是"AI 不作仲裁者"红线的实现。 | `behavior_engine.py:430-449` |
| T18 | **标定参数必须写进 `scene_annotation._ALLOWED_KEYS`**，否则人工标定的 `pixel_per_meter`/`ppm_ref_y`/`lane_width_px`/`camera_height_m` 等会被静默丢弃 → 车速永远走 `assumed` 粗估。 | `scene_annotation.py:36-60` |
| T19 | **（2026-10-06 已闭环）** 原 L131-148 与 L151-169 两段注释互相矛盾（"未通过交叉验证不启用" vs "改为默认启用"）。现两段都已删除，替换为一条明确规则：**没有人工显式给相机参数，就不走几何标定路径**（默认值 h=8.0/pitch=−20 对真实机位反解 RMS 达 94 m，却显示得像已标定，比 assumed 更危险）。 | `speed_calibration.py:__init__` 内注释 |
| T40 | **★测速标定的"真值"必须来自渲染或实拍，绝不能来自另一个模型的输出。** `_dual_cam_demo\ground_truth_dual.csv` 的 cam1_u/v 就是模型输出（自证），用它验证导致**连续 6 次修复失败**。只有 `(x, y)` 列可信。 | `_speed_calibration_verdict.md` §二；`_scripts\_validate_speed_calibration.py` 头注释 |
| T41 | **相机基必须正交且成对**：`fwd=(cp·cy, cp·sy, sin p)` 配 `up=(−sp·cy, −sp·sy, cos p)`（p 向下为负）。写成 `fwd_z=−sin p` + `up_z=+cos p`（项目旧写法）`fwd·up=0.73≠0`，相机"倒过来"，只有画面最下 11% 像素能反解。⚠ 注意 `(fwd=−sp, up=+cp)` 与 `(fwd=+sp, up=−cp)` **都正交**，光看正交分辨不出来，必须拿真实渲染帧对照。 | `speed_calibration.py:make_unprojector` 注释 |
| T42 | **标定字段有"两道静默丢弃"**：① `scene_annotation._ALLOWED_KEYS` 白名单；② `realtime_detector.py:805-823` 合并人工标注时**手工逐个 copy**。只加①不加② → 参数存进去了却到不了 `SpeedCalibrator`，超速换算永远落回 `assumed`（=永远不判超速，且不报错）。新增标定字段时**两处都要加**。 | `realtime_detector.py` 该分支注释 |
| T43 | **测速用 bbox 底边中点，不要用 bbox 中心**：中心悬在车身上方约 0.7 m，反投影会系统性偏近 0.5~1.5 m 且随距离变化 → 速度被扭曲。底边≈轮胎触地，且对"车尾朝相机"是恒定偏移（做差求速度时抵消）。实测残差 0.1~0.7 m。 | `speed_calibration._track_samples` / `contact_point` |
| T44 | **`fov` 是水平视场角**（CARLA `sensor.camera.rgb` 即水平）。真实监控相机手册常给对角视场角，直接填会让比例尺整体偏 10~20%。 | `_speed_calibration_verdict.md` §五 |

### 5.4 实时链路 / 时钟 / 性能

| # | 陷阱 | 证据 |
|---|---|---|
| T20 | **时钟必须按数据源类型选择**：回放本地视频要用"视频时间"，摄像头/CARLA 用墙钟。统一在 `_now()`（`:1018`）+ `_loop_frame_base`（`:136`）。写死 `time.time()` 会导致事件 `trigger_time`、冷却、证据帧窗口三者不同源 → 证据帧取到空镜头，云端 AI 全判驳回。 | `realtime_detector.py:136-142`、`:923-926`、`:1018-1024`、`:1060` |
| T21 | **云端咨询必须异步**：`consult_cloud_dual` 是 1-5 s 同步网络调用，原先放在 `process_frame` 里 → `process_lock` 长期占用 → 实测 processed 仅 **0.7 fps**（配置 3 fps）。现走 `_cloud_queue`（有界 maxsize=2）+ 独立 worker。 | `realtime_detector.py:175-186` |
| T22 | **违规必须加时间维度**：规则引擎**每帧**都判违规（违停只要"有车 + 在区域内"即 True），实测违规率 **96-99%**；仅加"持续 1.5s 确认"也只降到 89%。必须 `hold_sec=1.5` + `cooldown_sec=8`+。 | `realtime_detector.py:913-953` |
| T23 | **`_last_violations` 每帧被覆盖、无违规帧立刻清空** → `/api/realtime/vehicles` 几乎永远读到空列表（实测右栏恒为 0）。另用带 TTL 的 `_recent_violations`（默认 10 s）供前端展示。 | `realtime_detector.py:164-171` |
| T24 | **行为引擎产生的违规没有 `vehicle_id`**（规则引擎内部已回填，行为引擎没有）→ speeding/illegal_parking 全落"未归属"。需在合并后的最终列表上再补一次 `_attach_vehicle_ids`。 | `realtime_detector.py:958-967` |
| T25 | **不要"全场仅一辆车就硬归给它"**：无几何依据的归属会造成"违规挂到无关车辆"（实测红灯违规挂到画面中央卡车）。宁留空。 | `routers/realtime.py:560-566` |
| T26 | **`EvidenceChain` 曾长期未落库**：`traffic_events.evidence_chain` 实测 **541 条全为空**——模型字段存在、类已实现，但从未有人调用。现由 `_persist_evidence_chain` 写入（`:1949`）。注意**模型类名是 `TrafficEventRecord`，不是 `TrafficEvent`**（后者是事件引擎里的 dataclass），写错会 ImportError。 | `realtime_detector.py:1949-1964` |
| T27 | **不要送未标定数值违规（超速）去云端复核**：云端视觉模型无法从图像测速（实测它自己也这么说），送审只烧 token 并产生 rejected。默认 `cloud_review_uncalibrated=False`。 | `realtime_detector.py:56-59` |

### 5.5 环境 / 启动 / 数据库

| # | 陷阱 | 证据 |
|---|---|---|
| T28 | **`database.py` 必须锚定绝对路径**：`sqlite:///./x.db` 相对**进程 cwd** 解析，从项目根启动会静默连到 `E:\output\1\zhitong_violations.db`（**0 字节空壳**）→ 表现为"总违规数 0"却不报错。 | `database.py:6-19` `[一]`（确认空壳文件存在、0 字节） |
| T29 | **`database.py:51` 该修复只做了一半**：`migrate_missing_columns()` 里仍是 `sqlite3.connect("zhitong_violations.db")`（相对路径）→ 从项目根启动时迁移检查作用于空壳库，**静默失效**。见 §七。 | `database.py:51` |
| T30 | **后端必须从项目根启动**，且 `PYTHONPATH` 含 `api` 与项目根；解释器必须用 conda 环境 `C:\miniconda\envs\zhitong-gpu\python.exe`（fastapi/uvicorn/torch/ultralytics/dashscope/dotenv 都装在那里，PATH 上的 `py -3` 起不来）。 | `start-all.bat:12-27` |
| T31 | **静态文件挂载曾经 404**：原用相对路径 `"uploads"`，依赖 cwd，而证据图由 `Config.UPLOAD_DIR`（绝对）写入 → 实测 **2043 张证据图全部无法访问**。现为多布局兜底探测。 | `app.py:137-154` |
| T32 | **YOLO 推理分辨率**：不指定 `imgsz` 时 Ultralytics 默认 640 → 960×432 输入被缩到 288×640 → 远处小目标（红绿灯/车牌/头盔）直接消失。实测 traffic light 检出 imgsz=640 → 1~3，imgsz=1920 → 2~5。现默认 `YOLO_IMGSZ=1280`。 | `image_recognizer.py:621-628` |
| T33 | **中文不能用 `cv2.putText`**（Hershey 字体只有 ASCII，中文渲染成 "???"）。必须 PIL + TTF。另：**标注里不要用 emoji**（微软雅黑无该字形，渲染成方框）。 | `annotation_renderer.py:11-13`；`realtime_detector.py:1832` |
| T34 | **循环播放本地视频时要注意"每圈归零"与去重状态清理**（`_loop_frame_base`），否则同一违规每圈重复上报 / 事件片段窗口对不上内容。`cap.read()` 到末尾后会**永久返回 False** 并空转（已实测）。 | `realtime_detector.py:516`、`:532` |
| T35 | **CARLA 演示脚本的两个硬编码陷阱**：`LIGHT_ID = 9` 硬编码（新实例 id 变成 40/62/170）；CAM-1 从 `get_spectator()` 取（重启后 spectator 回默认 `(-172,184,28)`，拍到完全错误的地方）。 | `_redlight_demo_final.md` §三 |

### 5.6 已被证伪 / 未接入的方案（别再实现一遍）

| # | 方案 | 状态 |
|---|---|---|
| T36 | **发光区定位判色**（`find_glow_region` + `crop_around_glow` + `classify_with_glow` + `_channel_ratio_state`） | **代码已写好但未接入**（`realtime_detector` 用的是 `_crop_lit_lens` + `classify_traffic_light`）。记忆档案标注为"已证伪方案"。如需用，先读 `_lightup_verdict.md`、`_tl_colour_verdict.md`。 |
| T37 | **HSV 判色作主路径** | 已证伪（一致率 23%、危险方向错误），降级为"仅 CNN 不可用时"的兜底。见 T9。 |
| T38 | **CNN 重训 v1 的三处数据污染做法** | 已证伪：① 对灯头三颗镜片都打当前状态标签；② 裁图把灯箱一起给模型；③ 按峰值取灯珠（过曝白心，峰值饱和度只有 9）。正解见 `_redlight_demo_final.md` §二。 |
| T39 | **云端视觉模型测速** | 已证伪（模型自己说做不到）。见 T27。 |

---

## 六、★已被推翻的旧结论（不要再引用）

> 来源：`_ROOTCAUSE_channel_order.md` §四、`_redlight_demo_final.md` §一/§五、`speed_calibration.py` 注释、本工作区记忆档案。

| # | 旧结论（已作废） | 更正 | 来源 |
|---|---|---|---|
| O1 | "CARLA 红灯镜片渲染成淡青蓝色，是**地图资产缺陷**" | **错**。是读图代码把 R/B 互换。红灯渲染正常。 | `_ROOTCAUSE_channel_order.md` §四 |
| O2 | "旧视频红灯是红的、我这边不正常" | **错**。旧视频那 41 个"红块"在 **140/140 帧都出现且位置固定**，是静态背景物体（红招牌/红砖），两个视频都没拍到过真红灯。 | 同上 |
| O3 | "橙色路障渲染成蓝主导" | **错**。是通道反转。 | 同上 |
| O4 | "绿色正常、红色异常" | **错**。绿色之所以"看起来正常"，是因为 **G 通道在 R/B 互换中位置不变**。 | 同上 |
| O5 | "投影公式（Proj 类）可用" | **部分错**。`up` 向量符号写反（应为 `[-sp*cy, -sp*sy, cp]`）。 | 同上 |
| O6 | "该场景被判黄灯是检测结果" | **错**。是上游专门红绿灯模型的裸色名恒为 'yellow'（520/520 帧），导致 `red_light` 永远不可能触发。 | `_redlight_demo_final.md` §一 |
| O7 | "扩边 25% 对判色有帮助（分类器需要灯壳上下文）" | **错**。扩边有害（黄→红误判），最优是原样裁图。 | `realtime_detector.py:1532-1545` |
| O8 | "HSV 可以作为 CNN 的兜底常态使用" | **错**。仅允许在 CNN 完全不可用时使用。 | `realtime_detector.py:1577-1590` |
| O9 | "帧率补偿应该默认开启以修正低估" | **错**。会过补偿（15fps 从 −15.3% 冲到 +16.2%），默认关闭。 | `speed_calibration.py:650-661` |
| O10 | "`ground_plane_ppm` 是测速标定的正解" | **错/已降级**。系统性偏小 0.61 倍且缺横向分量；推荐 `make_unprojector()`。 | `speed_calibration.py:287-307` |
| O11 | "简单透视外推（`_ppm_at_y`）可用" | **错**。在"相机高 + 俯角大"机位下高估 9 倍。 | `speed_calibration.py:191-206` |
| O12 | "`PROJECT_FILE_INDEX.md` 是项目文件索引，可以据此判断项目有什么" | **失效**。它停在 **TASK-011 / 2026-07-20**，此后 TASK-012~031 及全部 DSH 轮次（scene_annotation、speed_calibration、traffic_event_engine、traffic_light_classifier、证据链、事件中心、微信小程序…）**从未进入该索引**。其中的 `/api/realtime/ws` 路由**根本不存在**（真实是 `/api/realtime/violations/stream`）。**以本文件为准。** | `PROJECT_FILE_INDEX.md:3`、`:170` `[一]` |
| O36 | "运行中保存的标定，后端会自己用上" | **错**（2026-10-10 前）。全仓只有 `start_camera()` 一处 `load_scene()` → 保存后必须「停止→开始」才生效；而 `/status` 仍报 `scope=roi`（旧标注里本来就有 1 个 ROI）→ **看起来在用、实际用旧值**。铁证：进程 22:33:14 启动、标注 23:19:09 保存，那一轮跑的是 22:33 的旧标注（1 个 ROI，磁盘上是 4 个）。**现已修**（T85） | `_design_2026-10-09_verdict.md` §一；`/status` 的 `scene_annotation_reload_count` |
| O37 | "标定面板显示的永远是当前画面" | **错**（2026-10-10 前）。`LiveMonitor.vue:366` **硬编码**默认源 `ea1ca6cb….mp4`（B 站测试视频），刷新即重置；面板 `source` 跟输入框 → 面板首帧是 **1280×576 旧视频**（实测），而运行中的是 1920×1080 演示视频 → 用户在错画面上标、存到错的视频。**现已修**（T88） | `_uicheck\diag-calib-source.mjs` 实测输出；修后面板首帧 = 1920×1080 |
| O38 | "左侧那盏黄灯被识别，是判色/判定的问题" | **错**。判定侧**一直**只认 ROI（`_scene_light_state_from_cnn`）。真相是**绘制侧完全没有 ROI 过滤** —— `_collect_traffic_lights` 收集全部、渲染器全画。修的是绘制，不是判定（改判定会破坏"每循环 1 次真违规、0 误报"） | trace：`('yellow',(419,120))` 144 帧全在 ROI 外；`_scripts\_verify_trace_roi_filter.py` |
| O39 | "画面里有盆栽框，是渲染器的问题" | **半错**。渲染器"只跳过红绿灯、其余照画"确实是**放大器**，但根因是**检测出口没有类白名单**：COCO 会吐 `potted plant` 等 83 个无关类。只改渲染器 = 治标（规则/跟踪/行为引擎仍被垃圾框污染）。**正确修法是在 `process_frame()` 检测出口按白名单裁** | kept=1644 / dropped=252（全 `potted plant`）；`/status` 的 `class_filter_stats` |
| **O42** | "用户看到的是**两个识别框重叠**"（我按设计单 §12.3 复现并当成唯一真相去修） | **修对了机制，但用户的现象描述其实有两层**。第二层是：**同一辆车一会儿显示 `ID18`、一会儿显示 `car`** —— 那是关联失败的过渡帧把**原始类名**当标签画了，不是第二个框。用户 2026-10-10 亲自更正："有时候会显示ID，有时候会显示车辆类别，我还以为是两个识别框重叠了"。**教训：用户的现象描述是"线索"不是"结论"，修完要请用户再看一次，别把"我复现的机制"当成"用户看到的全部"**（我上一轮就吃过同类亏：把推断写成事实） | 用户原话；`COLOR_UNKNOWN` 三色方案；单元测试 5a/5b/5c |
| **O43** | "云端开关自动打开是**前端连带推送**造成的"（设计单 §8 的结论） | **前端那层是真的，但只是第二层**。真正的根因：`RUNTIME_SETTINGS` **只存内存**，而两个开关的默认值是 `True` → **每次重启后端都把用户关掉的付费开关重置回"开"**（用户 22:01 关、22:13 重启后变回 `true/true`，铁证）。两层都修了才算闭环 | `realtime_detector._load_persisted_runtime_settings`；重启后实测仍 `false/false` |

---

## 七、缺失 / 待补（扫描中发现的不一致与坏引用）

| # | 类型 | 问题 | 证据 | 建议 |
|---|---|---|---|---|
| G1 | **坏引用** | `_PROJECT_MAP.md` **此前根本不存在**，而 `~/.dsh/AGENTS.md` 铁律 §4 与 `_DSH_WORK_PROTOCOL.md` §4.4 都已要求"开工先读它"。协议引用了一个空文件路径。 | `[一]` `Test-Path E:\output\_PROJECT_MAP.md` → `False`（创建前） | **本文件即为首次创建**，已闭环 |
| G2 | **路径不一致（真 bug）** | `database.py:51` `sqlite3.connect("zhitong_violations.db")` 用**相对路径**，而同一文件 L6-19 的注释与 L11 已经说明必须锚定绝对路径。从项目根启动（`start-all.bat` 就是这么启的，L23-27）时，迁移检查作用在 **`E:\output\1\zhitong_violations.db`（0 字节空壳）** 上 → 缺列迁移**静默失效**。 | `[一]` 两个同名文件：`E:\output\1\zhitong_violations.db` = **0 B**、`E:\output\1\api\zhitong_violations.db` = 26,247,168 B；`database.py:11` vs `:51` | 改 L51 为 `sqlite3.connect(_DB_FILE)`。**未确认是否需 DSH 之外的人批准，未改** |
| G3 | **高风险不一致** | **判色模型默认值 ≠ 报告结论**。`_redlight_demo_final.md` §二/§5.4 明确"**采用 CNN5**、CNN6 留备选"，但 `traffic_light_classifier.py:27` 默认仍是 **`tl_color_cnn4.pt`**（报告实测 CNN4 在 CARLA 演示视频上 lit 裁图 **0/14**），且 `start-all.bat` **未设置** `TL_COLOR_MODEL`。 | `[一]` 运行中进程命令行：`...python.exe -m uvicorn app:app --host 127.0.0.1 --port 8001`（无 `TL_COLOR_MODEL`）；`[二]` `traffic_light_classifier.py:26-27`；`[三]` `GET /api/realtime/status` → `traffic_light_stats={"total":16,"cnn":14,"hsv":0,"unknown":2}`（CNN 在工作，但**无法从接口判断加载的是哪一版**） | **未确认**端到端验证当时是否用环境变量覆盖。建议确认后统一（或在 `start-all.bat` 显式指定） |
| G4 | **资产不可达** | `find_model_path` 候选顺序导致多个模型文件**永远不会被加载**：`traffic_light.pt` / `traffic_light_best.pt` / `vehicle_best.pt` / `best.pt` / `yolov8m.pt` / `yolov8n_official.pt` / `yolov8n_pretrained.pt` / `helmet_pretrained.pt`。其中 `model_key='traffic_light'` 命中 `yolov8s.pt`（COCO），`model_key='vehicle'` 命中的也是 `yolov8s.pt`（而非 `vehicle_best.pt`）。 | `image_recognizer.py:212-238`；`[一]` 目录清单 | 明确"哪些模型是真正在用的"，其余标注为归档或删除（删除需按协议 §6 报备） |
| G5 | **疑似死代码** | `scene_perception.py`（26.1 KB，含 `LaneDetector`/`TrafficLightDetector`/`SceneContext`）与 `k230_plate_client.py`（7.7 KB，`K230PlateClient`）**全仓无任何代码 import**，仅被文档宣称"已实现"。 | 全仓 grep：`scene_perception` 仅命中自身 + `PROJECT_AUDIT_AND_BASELINE_REPORT.md:66`；`k230_plate_client` 仅命中 `NATIONAL_SPRINT_BRIEF.md:71`、`docs/project_analysis_gpt_upgrade.md:203` | 确认是"备用能力"还是"废弃实现"，写进本清单的对应状态 |
| G6 | **疑似死代码（更危险）** | `api/main.py`（12.4 KB）是**旧版 v1.0 FastAPI 应用**，自带 `/token`、`/users/`、`/violations/`、`/control/`、`/logs/`、`/stats/violations`、`/health`，**与 `routers/auth.py`、`routers/violations.py` 等大量重名**。虽当前无人 import，但一旦被误挂载（或有人照它写代码）会产生路由冲突与认知混乱。 | `main.py:171-356`；`TASKS.md:90` 曾写"`uvicorn app:app --reload --port 8000`" | 建议加显著 deprecated 头注释（改代码需先报备） |
| G7 | **未接入实现** | `traffic_light_classifier.py` 的 `find_glow_region()` / `crop_around_glow()` / `classify_with_glow()` / `_channel_ratio_state()` 已完整实现（含参数调优注释）但**无调用方**；实时链路用的是另一套 `_crop_lit_lens`。 | grep：这些符号仅在 `traffic_light_classifier.py` 内出现；`realtime_detector.py:1572` 用的是 `self._crop_lit_lens(roi)` | 明确"备选，未接入"，避免后人以为它在跑 |
| G8 | **无调用方的导出函数** | `speed_calibration.judge_speeding()`（含 10% 法定容差的超速判定）**全仓无调用方**——超速判定实际在 `behavior_engine` 里另写。 | grep `judge_speeding` 仅命中 `speed_calibration.py:712` 定义处 | 要么接入 `behavior_engine`，要么标注为"未接入" |
| G9 | **元数据缺失** | `_tl_color_cls/history.json`（5,136 B）与 `val_predictions.csv`（1,045 B）的 mtime 都是 **2026-10-03 01:17**，即**只覆盖 cnn4**；cnn5 / cnn6 没有任何训练曲线或指标落盘，只在 `_redlight_demo_final.md` 里有表格。 | `[一]` 文件 mtime；`[二]` `_retrain_carla_classifier.py` 未写 history | 重训时补落盘，否则"哪版更好"只能靠报告回忆 |
| G10 | **两套迁移并存** | `database.migrate_missing_columns()`（建表时自动跑，只补 `violation_evidences` 的列）与 `migrate_db.py`（版本表 + `collaboration_sessions`/`system_statistics`/`traffic_events` 建表 + rollback）职责重叠且互不感知。 | `database.py:48-87`；`migrate_db.py:197/286/400` | 明确哪个是权威入口 |
| G11 | **旧索引与代码不符（多处）** | `PROJECT_FILE_INDEX.md` 除 O12 所述整体过期外，还有：只列 10 个 router（实际 12 个 + app.py）、只列 5 个模型文件（实际 15 个）、只列 6 张表（实际 12 个）、模型清单里没有判色 CNN。 | `PROJECT_FILE_INDEX.md` 全文 vs `[一]` 目录/DB 实测 | 保留为历史文件但**顶部加"已废弃，见 `_PROJECT_MAP.md`"**（改文件需先报备） |
| G12 | **状态字段 vs 磁盘不符** | `E:\output\1\zhitong_violations.db`（0 B）与 `api/zhitong_violations.db`（26 MB）同名共存。`database.py:14-19` 已加只读警告，但 `app.py:203` 的健康检查仍用相对路径 `os.path.exists("zhitong_violations.db")` 与 `os.path.exists("uploads")` 判断 → 这两项检查结果**取决于 cwd**，可能是假的。 | `app.py:202-203` | 健康检查应改用 `Config.DB_PATH` / `Config.UPLOAD_DIR` |
| G13 | **规则引擎双实现** | 违规判定同时存在 `violation_rules.ViolationRuleEngine`（6 类）与 `behavior_engine.BehaviorEngine`（8 类）+ `rule_engine/plugins/traffic_plugin`（包装前者）。实时链路**两条都跑**（`realtime_detector.py:130-131`），语义重叠但类型集合不同（behavior 多出抢黄灯/违规掉头/未礼让行人）。 | `realtime_detector.py:130-131`、`:955-967` | 明确"谁是权威判定"，避免后人只改一处 |
| **G14** | **★坏"真值"污染了 6 次修复（2026-10-06 定位并已建立替代验证）** | `E:\output\_dual_cam_demo\ground_truth_dual.csv` 的 `cam1_u/cam1_v` 是 `_dual_cam_demo.py:217/231` 里 `Proj.project()` 的**模型输出**，而该 `Proj` 的相机基不正交（`fwd·up=0.73`）。围绕它写的验证脚本（`_debug_homography.py`、`_verify_homography*.py`、`_unproject_numeric.py`、`_compare_two_impls.py`、`_check_projection_consistency.py`、`_quantify_old_model.py`）**结论全部作废**。 | `[一]` 同参数重算 580 行 u 中位误差 0.51 px；`_speed_calibration_verdict.md` §二 | CSV 的 `(x,y)` 保留为真值、像素列作废；本轮已建立 `_validate_speed_calibration.py`（真实帧）与 `_carla_calibration_markers.py`（物理级） |
| **G15** | **★第二道静默丢弃（2026-10-06 已修）** | `realtime_detector.py:805-823` 合并人工标注时**手工逐个字段 copy**，只拷了 8 个字段 → `camera_height_m/camera_pitch_deg/fov_deg/lane_width_px/...` 即使存进 scene 也到不了 `SpeedCalibrator`，超速换算永远落回 `assumed`（不报错、也不判超速）。 | `[一]` 白名单存-取往返测试 + 静态核对 | 已改为成组拷贝；新增标定字段时**两处同步**（见 T42） |

| **G16** | **前端图表主题仍不一致** | 本轮已把 `utils/echarts-theme.js` 重写为亮色 `zt-light`，并在 `Dashboard.vue` 三处 `echarts.init(el, 'zt-light')` 生效。但 `Statistics.vue:181,184,187` 三处 `echarts.init` **仍未传主题参数**，该页图表走 ECharts 默认色板 —— 与全站亮色令牌不一致。**本轮未改（超出 F1-F10 授权范围）**。 | `Statistics.vue:181,184,187`；`Dashboard.vue:450,485,504` | 下一轮把三处补上第二参数即可（主题已注册，改一行） |
| **G17** | **★既有 bug：违规列表"设备位置"列显示 `x:undefined, y:undefined`** | `ViolationList.vue:334-337` 读 `pos.x / pos.y`，但后端 `position` 字段实际是 `{bbox, center_x, center_y}`，**没有 x/y 键**。因 `pos` 是真值对象，`if (pos)` 通过，于是拼出 `x:undefined, y:undefined`。**与本轮 UI 改动无关**（该文件未被改动，文件哈希与备份一致）。 | `[一]` `GET /api/violations/list` 实际返回 `position = {"bbox":[...],"center_x":1035.95,"center_y":331.61}`；`[三]` 截图 `reg_violations.png` 该列显示 `x:undefined, y:undefined` | 改 `ViolationList.vue:337` 用 `center_x/center_y`，或后端补 x/y。**需用户确认是否本轮修** |

### 未确认项（如实登记，**没有编**）

| # | 未确认的事 | 说明 |
|---|---|---|
| U1 | 运行中的判色器究竟加载 `cnn4` 还是 `cnn5` | 命令行无 `TL_COLOR_MODEL` → **按代码默认应为 cnn4**；但 `_redlight_demo_final.md` 的端到端结论只有用 cnn5 才自洽。接口 `/api/realtime/status` 不暴露模型版本。见 G3 |
| U2 | `/api/realtime/status` 里 `traffic_light_confirmed: 14` 的 14 个灯颜色**是否正确** | 接口只给数量不给颜色分布；无真值对照不能判定 |
| U3 | `scene_perception.py` / `k230_plate_client.py` 是"备用"还是"废弃" | 无调用方、无测试、无 README 说明；需作者确认 |
| U4 | `_crop_lit_lens` 与 `classify_with_glow` 哪套在 CARLA 上更优 | 两套都在仓库里，只有前者接了线，没有 A/B 记录（`_lightup_verdict.md` 说发光区方案被证伪，但那是另一套 `find_glow_region` 的早期版本，措辞需谨慎） |

---

## 附：本文件的维护规则（来自 `_DSH_WORK_PROTOCOL.md` §4.4）

| 触发 | 必须更新 |
|---|---|
| 新增 / 删除 / 重命名模块或路由 | 本文件对应表项（§二 / §三） |
| 发现"原来项目已经有 X" | 立刻补进本文件，并记录自己差点重复 |
| 会话结束 / 交接 | 核对本文件与代码一致 |

**建新东西前的强制动作**：先在 `E:\output\1\api` 内搜索同类关键词（如 `calibration` / `speed` / `track` / `color`），确认没有现成实现；搜索结果要写进交付说明（"查过 X/Y/Z，无现成实现，故新建"）。

---

## 附：本文件的生成方式（可复现）

| 数据 | 命令 / 证据 |
|---|---|
| 模块清单 + 大小 + mtime | `Get-ChildItem E:\output\1\api -Recurse -File -Filter *.py` `[一]` |
| 核心类/函数 | `Select-String -Pattern '^(class \|def \|async def )'` 全量扫描 `[一]` |
| 实时链路判定 | grep `^\s*(from\|import)\s+\S+` 于 `realtime_detector.py`（43 处匹配）、`routers\*.py`（170 处）、`app.py` `[一]` |
| 路由清单 | `Invoke-WebRequest http://127.0.0.1:8001/openapi.json` → 131 operations / 122 paths `[一]`（**运行中实例为旧进程**；源码 `@router.*` 装饰器已于 2026-10-06 增至 131 个 = 130 REST + 1 WS，重启后 openapi 应为 132 operations），交叉核对 |
| 数据库表 | Python `sqlite3` 读 `sqlite_master` + `PRAGMA table_info` + `count(*)` `[一]` |
| 模型资产 | 目录列出（含字节数与 mtime）`[一]` |
| 实时行为 | `GET /api/realtime/status`（源 = `E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv`）`[三]` |
