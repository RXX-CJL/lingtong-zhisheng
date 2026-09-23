# TASK-028: 超长大型任务 · 车牌识别·多帧确认·行为增强·规则引擎·云台追踪·非交通演示·CARLA仿真·端到端闭环

> **创建时间**: 2026-07-29
> **最后更新**: 2026-07-29（精简至 12 个核心子任务，新增 M17 CARLA 接入）
> **优先级**: P0（最高）
> **预计子任务数**: 12（已移除小程序 M11-M13、答辩材料 M15；新增 M17 CARLA 接入）
> **项目根目录**: `e:\output\1`
> **项目正式名称**: 智瞳灵声-基于视觉识别与云端推理的智慧交管系统（国家级大创）
> **CARLA 已就位**: `e:\output\1\carla\CARLA_0.9.16\`（含 CarlaUE4.exe + PythonAPI + 7 个城镇地图）
>
> **指挥官寄语（给执行者）**：
> 你我是战友关系，不是上下级。任务量大，遇到难题直接在 feedback 中提出异议和替代方案，不必等批准。Git 优先复用规则强制执行——每个子任务动手前必须先用 GitHub Skill 搜现成实现，禁止从零造轮子。多互帮互助，共同把项目做深做透。

---

## 一、指挥官工作报告

### 1.1 已做工作

1. **项目书确认**：审阅了 C:\Users\ROG\Desktop\智瞳灵声 目录的申报书，确认项目书技术路线为 **YOLOv8 + DeepSORT + 端云协同 + K230**，正式名称和结题时间不可改
2. **战略定位升级**：从"交管系统"扩展为内部按"城市智眼"格局开发，架构预留多场景扩展接口；实物方案定为 **PC（大脑）+ K230（眼睛）+ 云台（脖子）**，为未来 AI 交管车铺路
3. **痛点分析**：六大核心痛点按致命程度排序：①无车牌识别 ②小程序空壳 ③行为理解浅 ④单帧误判 ⑤云端无成本控制 ⑥端到端无法演示
4. **优先级规划**：P0 四项（车牌识别+小程序+行为增强+规则引擎扩展），P1 两项（数字孪生四场景+云台追踪），P2 两项（专利论文+答辩准备）
5. **K230 资源确认**：K230 资料目录下现成模型：`LPD_640.kmodel`（车牌检测）、`licence_reco.kmodel`（车牌识别）、`yolov8n_320.kmodel`（目标检测），以及 `01.快速入门/9.二维云台安装教程` 现成资源可直接用
6. **执行者建议吸收**：回顾 TASK-027 feedback，吸收其有效建议：①在 process_frame 中加入 FPS 监控 ②前端做图标名称校验脚本 ③不同行为类型不同颜色标注 ④改进 bbox 匹配精度
7. **时间规划确认**：答辩最早 2027 年 6 月，不赶工，每个模块做深做透

### 1.2 使用的技能与工具

| 阶段 | 工具/Skill | 用途 |
|------|-----------|------|
| 项目书分析 | RunCommand + zipfile（提取 docx） | 从申报书 docx 提取文本，确认技术路线和项目名 |
| 规则检查 | Read + Grep | 全面检查 memory 中所有硬约束、工程约定、经验教训 |
| 任务梳理 | Glob + LS | 盘点项目文件结构，确认 K230 现成资源位置 |
| 方案设计 | 参考记忆中的 brainstorming 规则 | 每个方案都列出理由和决策依据 |
| 现状检查 | Grep + Read | 检查当前 realtime_detector / violations / wechat 路由现状，确保任务不重复 |

### 1.3 决策依据与难题建议

**核心决策依据**：
- 大创结题前的核心目标：**所有功能真实跑通、端到端闭环可演示、关键技术证明可落地**
- "群众智眼" + "移动智眼" 是答辩亮点，必须做
- 现成 K230 模型/云台教程直接用，禁止从零造轮子（Git/GitHub 优先复用规则）

**难题建议（执行者可参考，也可提异议）**：
1. **PaddleOCR 依赖冲突**：建议先 CPU 版 `pip install paddlepaddle paddleocr`，不行就先查 GitHub 上成熟解决方案再动手
2. **K230 与 PC 通信**：K230 固件里已有 `YbRequests.py` / `upload_image.py` / HTTP 通信例子，复用现有通信逻辑，不要重写
3. **规则引擎抽象化**：不要把新类型硬编码在 BehaviorEngine，要做"场景插件化"——加新场景 = 写一个 `RulePlugin` 类
4. **小程序微信登录**：如果暂时没有 AppID，可以做"手机号+验证码"或"模拟微信登录"的降级方案，但代码结构要预留真实登录接口位置
5. **端到端演示数据**：建议准备几段预录制交通视频（含车牌+违规行为），演示时用视频文件跑，避免现场随机因素
6. **非交通场景选择**：建议选"占道经营（城管）"+"人员聚集（治安）"，两个场景视觉特征明显，容易从 GitHub 找参考模型

### 1.4 指挥官自我反思（供执行者监督）

1. TASK-026 任务过多（搜索+文档+集成都堆在一个任务），导致 M4/M5 质量打折 — 本任务拆成 12 个子任务，每块聚焦
2. 之前对"城市智眼"格局强调不够，执行者可能按"交管小系统"思路写代码 — 本任务明确要求架构预留扩展接口
3. 之前对"听取执行者有利建议"没有在任务中强制落实 — 本任务明确 M16 中必须逐条列出采纳/未采纳哪些过去的建议
4. 之前没有要求每个子任务后写反馈，导致协作反馈断档 — 本任务每个 OUTPUT 都必须含 feedback + skills 清单
5. 本次精简了小程序和答辩材料（M11-M13/M15），聚焦核心检测+CARLA 仿真链路 — 如果执行者认为顺序不合理或遗漏，直接在 feedback 中提出
6. 新增 M17 CARLA 仿真接入，是本任务最大亮点 — CARLA 仿真+数字孪生联动是答辩的"杀手锏"，但显存风险已列入风险提示

---

## 二、全局规则（12 个子任务全部遵守）

### 2.1 Git 优先复用（强制，违反即 FAIL）
> 每个子任务执行前，必须先用 GitHub Skill 搜对应关键词，把搜到的成熟实现列在 notes 里，再选择"稍加修改即可用"的方案。禁止一上来就从零写代码。

| 子任务关键词 | GitHub 搜索建议 |
|------------|----------------|
| 车牌识别 | "paddleocr license plate recognition python", "lprnet", "hyperlpr", "easyocr chinese plate" |
| 多帧确认 | "multi-frame object tracking voting", "sliding window detection", "DeepSORT license plate" |
| 行为增强 | "video behavior understanding transformer", "traffic violation detection tracking", "ByteTrack rules engine" |
| 规则引擎扩展 | "python pluggable rule engine", "plugin based detection system", "scenario plugin system" |
| ONVIF 云台 | "python-onvif ptz control", "onvif-zeep camera control", "ONVIF continuous move python" |
| 非交通场景 | "street vendor detection YOLO", "crowd gathering detection", "illegal occupancy detection" |
| 数字孪生 | "three.js label follow object sprite", "CSS2DRenderer arrow rotate", "digital twin socketio real-time" |
| CARLA 仿真 | "carla python api traffic simulation", "carla sensor data yolo integration", "carla synchronous mode example", "carla vehicle position websocket stream" |
| 端到端演示 | "streamlit demo computer vision", "gradio traffic detection dashboard" |

### 2.2 能力优先使用（强制）
执行前对照 [project_memory.md](file:///c:/Users/ROG/.trae-cn/memory/projects/-e-output/project_memory.md) 中"工作流能力优先级"：P0→P1→P2。**降级前必须通知指挥官**，允许后才降级。

### 2.3 Vibe Coding 理念
效果优先。一个模块写完，先跑起来看结果，再考虑代码风格。方案不行就快速换，不纠结。

### 2.4 子任务间依赖（严格遵守，禁止跳）
```
M01(PaddleOCR车牌) → M02(K230车牌) → M03(多帧确认) → M04(车牌绑定违规)
                                                            ↓
M05(行为增强+车道灯) → M06(规则引擎抽象化) → M07(非交通场景插件)
                                                            ↓
M08(云台ONVIF) → M09(软件虚拟追踪) → M10(追踪前端UI)
                                                            ↓
M14(数字孪生真实数据联动) → M17(CARLA仿真接入+孪生联动) → M16(集成测试+清理+建议反馈+采纳记录)
```

**已移除的子任务**（暂缓，不在本任务范围）：
- ~~M11 小程序真实上传~~ → 后续单独任务
- ~~M12 小程序违规通知+车牌绑定~~ → 后续单独任务
- ~~M13 小程序申诉与管理端接通~~ → 后续单独任务
- ~~M15 端到端预录制演示脚本~~ → 部分能力已并入 M17 CARLA 演示

**新增子任务**：
- **M17: CARLA 仿真环境接入**（输入端+数字孪生联动，替代 M15 的演示功能）

### 2.5 OUTPUT 字段强制格式（每个子任务）
```json
{
  "task": "TASK-028-Mxx",
  "timestamp": "ISO8601",
  "status": "PASS/PARTIAL/FAIL",
  "vpn_status": "ON/OFF/NOT_NEEDED",
  "skills_used": [
    {"skill": "GitHub Skill", "used": true, "detail": "搜到 paddleocr 参考 xxx，复用后改了 xxx"},
    {"skill": "test-driven-development", "used": true, "detail": "先写了 8 个测试，实现后全部通过"},
    {"skill": "...", "used": false, "detail": "没用到的也要写理由"}
  ],
  "git_references": [
    {"repo_url": "https://github.com/xxx/yyy", "star": 3200, "reused": true, "detail": "复用了 detect_and_recognize 函数，改了参数校验"}
  ],
  "deviations": ["做了什么与任务通知不一致的变更，原因是..."],
  "feedback": {
    "project_suggestions": ["..."],
    "commander_suggestions": ["...对指挥官任务设计/优先级/沟通的建议"],
    "difficulties": ["具体困难，怎么解决，是否需要支持"],
    "dissent": ["对指挥官本任务中哪个决策有异议，理由+替代方案"],
    "suggestions_adopted": [
      {"from": "TASK-027 feedback Mx", "content": "建议添加 FPS 监控", "adopted": true, "action": "在 realtime_detector 中加入了 fps_monitor"}
    ]
  },
  "details": {}
}
```
**缺失字段 = 任务不通过**。

### 2.6 验收验证（每个子任务强制）
- Python 文件：`py -3 -c "import ast; ast.parse(...)"`
- 前端：`cd e:\output\1\web-admin ; npx vite build`（exit code 0）
- 小程序：`cd e:\output\1\wechat-miniprogram` 检查 app.json/pages 路由
- 临时文件：结束后必须清理（test_*.py、tmp_*.jpg、__pycache__、diag_*、camera_test_* 等）

---

## 三、16 个子任务详细清单

---

### M01: PaddleOCR 车牌识别模块（PC端主力）
**目标**：从视频帧中提取车牌文字，支持蓝/绿/黄牌

**必须做的 Git 复用步骤**：
1. GitHub Skill 搜 "paddleocr chinese license plate" / "hyperlpr python" / "easyocr chinese plate"
2. 至少对比 3 个仓库 star 数、最后更新日期、代码结构，选最适合的
3. 把对比结果写进 OUTPUT 的 git_references

**具体要求**：
- 安装：优先 `pip install paddlepaddle paddleocr`，CPU 版优先；冲突时再按 GitHub 方案处理
- 创建 `e:\output\1\api\license_plate_recognizer.py`：
  - `detect_plate(image) -> bbox` 车牌定位
  - `recognize_plate(image) -> str` 车牌文字
  - `recognize_plate_batch(images) -> List` 批量识别（配合多帧确认）
  - `detect_and_recognize(image) -> {plate_number, confidence, bbox, plate_color}`
- 车牌图像增强：模糊/低对比度时自动锐化+超分辨率（可复用 GitHub 现有轻量实现，禁止从零写超分网络）
- 失败兜底：PaddleOCR 安装失败则用 EasyOCR 或 HyperLPR 作后备（同样 GitHub 搜）

**验收**：
- [ ] `license_plate_recognizer.py` ast 验证通过
- [ ] 准备 3-5 张测试车牌图（可以从 K230 示例或公开数据集截），识别成功率 ≥ 80%
- [ ] 返回结构正确（plate_number/confidence/bbox/plate_color）
- [ ] PaddleOCR 或后备库 import 无报错

---

### M02: K230 车牌检测模型集成（边缘端辅助定位）
**目标**：用 K230 现成 `LPD_640.kmodel` + `licence_reco.kmodel` 做边缘端车牌定位/识别候选结果

**必须复用的本地资源**：
- 模型：`e:\output\1\固件备份\kmodel\LPD_640.kmodel`、`licence_reco.kmodel`
- 现成代码：`e:\output\1\固件备份\libs\*.py`（AI2D / YOLO / PipeLine）
- 场景示例：`e:\output\1\K230\10.场景应用\6.车牌检测` + `7.车牌识别`

**具体要求**：
- 创建 `e:\output\1\api\k230_plate_client.py`：
  - `K230HTTPClient` 类（K230 端做 HTTP Server，PC 端做 Client — 参考 `YbRequests.py` / `upload_image.py` 现有通信代码）
  - `detect_via_k230(frame) -> List[bbox]`
  - `recognize_via_k230(plate_crop) -> {plate_number, confidence}`
  - **graceful degradation**：K230 连不上时自动跳过，所有函数返回空，不报错不阻塞主流程
- 创建 `e:\output\1\docs\k230_plate_protocol.md`：
  - 输入格式（图片编码、尺寸）、输出 JSON 结构、HTTP 端口、错误码
  - 把 K230 端需要的服务端脚本代码框架也写好（放在 `zhitong/k230_app/` 下，命名 `plate_server.py`）
- 把 K230 端 kmodel 的推理代码包装成标准 Python 接口，方便之后真正烧录到板子时直接用

**验收**：
- [ ] `k230_plate_client.py` ast 通过
- [ ] `plate_server.py`（K230 端）ast 通过
- [ ] `k230_plate_protocol.md` 文档齐全
- [ ] K230 断开时，单元测试能跑通（返回空结构，不抛异常）

---

### M03: 多帧确认机制 + TASK-027 反馈采纳（FPS监控/匹配精度）
**目标**：连续多帧确认车牌+违规，避免单帧误判；同时采纳 TASK-027 feedback 的建议

**必须采纳的执行者建议（来自 TASK-027）**：
1. ✅ 在 process_frame 中添加 FPS 监控（实时显示处理帧率）
2. ✅ 考虑前端图标校验脚本（后续在 M10 实现，本任务只做接口预留）
3. ✅ 不同行为类型不同颜色标注（已在本任务 M05/M06 强制要求）
4. ✅ 改进 bbox 与 tracking 的匹配精度（本任务中 IOU + 中心距离双重匹配）

**具体要求**：
- 创建 `e:\output\1\api\multi_frame_validator.py`：
  - `MultiFrameValidator(window_size=N, confirm_threshold=M, plate_sim=0.8)`
  - 滑动窗口：保存最近 N 帧的 `{track_id, plate, violation_type, bbox}`
  - 车牌匹配：Levenshtein 相似度 ≥ plate_sim 视为同一车牌
  - bbox 匹配：IOU ≥ 0.3 **或** 中心距离 ≤ 平均尺寸*0.3（二选一满足）
  - `add_frame(frame_results) -> pending_list`
  - `get_confirmed() -> List[confirmed_record]`（连续 N 帧中 ≥ M 帧同车牌+同违规）
  - `pending_info() -> {track_id: {plate_histo, frames, votes}}`
- 集成到 `e:\output\1\api\realtime_detector.py`：
  - 新成员：`self.multi_validator = MultiFrameValidator(...)`
  - 新成员：`self.fps_monitor = ...`（滑动窗口 FPS，过去 30 帧的平均）
  - `process_frame` 中：detect → track → plate → behavior → 送 validator → validator 返回 confirmed → 才写数据库
  - `/api/realtime/status` 新返回：`avg_fps`, `pending_count`, `confirmed_count`
- 写单元测试 `tests/test_multi_frame_validator.py`：10+ 条用例，覆盖"噪声帧""车牌轻微识别错误""目标丢失又出现"等场景

**验收**：
- [ ] `multi_frame_validator.py` + 测试 ast 通过
- [ ] pytest 全部通过（或 py -3 直接跑测试函数）
- [ ] Grep 确认 realtime_detector.py 中引用了 multi_frame_validator + fps_monitor
- [ ] `/api/realtime/status` 返回结构中含 avg_fps / pending / confirmed
- [ ] 在 OUTPUT suggestions_adopted 里明确列出"采纳了 TASK-027 feedback 哪几条，做了什么动作"

---

### M04: 车牌与违规记录绑定（数据库+API+前端）
**目标**：违规记录有"身份证"，能关联到具体车牌、置信度、截图、确认帧数

**具体要求**：
- 数据库：
  - 在 `e:\output\1\api\models.py` + `database.py` 给 Violations 表加字段（或建迁移脚本）：
    - `plate_number STRING`, `plate_confidence FLOAT`, `plate_image_path STRING`, `confirmed_frames INT`
  - 如果用 SQLite，用 `migrate_db.py` 思路做安全迁移（不破坏现有数据）
- 后端路由：
  - `POST /api/violations/` 提交违规时，如果已有 plate 数据自动写入
  - `GET /api/violations/{id}` 返回 plate 四字段
  - `GET /api/violations/plate/{plate}` 按车牌查历史
  - `plate_images/` 目录按日期组织：`e:\output\1\data\plate_images\{YYYYMMDD}\{violation_id}.jpg`
- 前端：
  - 违规列表页（Violations.vue 或对应位置）新增车牌列 + 车牌颜色小标签（蓝底白/绿底黑/黄底黑）
  - 违规详情页新增车牌卡片：车牌大图 + 车牌号 + 置信度 + 确认帧数 + 颜色
  - 按车牌搜索框输入 → 调 `/violations/plate/{plate}`
- `vite build` 必须通过

**验收**：
- [ ] 迁移脚本/模型文件 ast 通过，实际执行不报错
- [ ] 新建测试违规记录，GET 返回 plate 四字段齐全
- [ ] `vite build` exit code 0
- [ ] 前端 3 处改动（列表列/详情卡片/搜索）真实存在（Grep + Read 验证）

---

### M05: 行为理解增强（车道线+红绿灯+违规判定深度化）
**目标**：从"方向变了就判逆行"升级到"结合车道线/红绿灯位置/轨迹变化来判定违规"

**Git 复用关键词**：
- "ultralytics yolov8 lane detection"
- "traffic light detection chinese benchmark"
- "ByteTrack violation detection rules"
- "unet lane segmentation lightweight"

**具体要求**：
- 创建 `e:\output\1\api\scene_perception.py`：
  - `LaneDetector`：优先使用 GitHub 成熟轻量车道线检测模型（如果太大装不了就降级为"基于 Hough 变换+图像掩膜"的经典方案，降级前报备指挥官）
  - `TrafficLightDetector`：红绿灯识别（颜色+状态），复用已有 YOLO 或找 GitHub 专门模型
  - `SceneContext` 聚合：当前帧的车道线位置、红绿灯状态、车辆位置
- 增强 `e:\output\1\api\behavior_engine.py`：
  - 现有 `ViolationRuleEngine` 保留作基础
  - 新增 `ContextAwareBehaviorAnalyzer`：
    - 闯红灯：红绿灯是红灯 + 车越过停止线（停止线=车道线端点估计）
    - 逆行：车辆轨迹方向与车道线方向夹角 > 135°
    - 违规停车：车辆连续 N 帧（≥30）停在非停车区域
    - 未戴头盔：已有，但结合 rider + 两轮车一起判断（骑手在两轮车 bbox 上方）
  - 不同违规类型用不同颜色（TASK-027 建议采纳）：闯红灯=深红、逆行=橙、违停=紫、未戴头盔=青、占道经营=蓝、人员聚集=黄
- 输出 `/api/realtime/behavior-context` 接口返回：lane_lines、traffic_light_state、vehicle_lane_positions

**验收**：
- [ ] `scene_perception.py` ast 通过
- [ ] `behavior_engine.py` 改动经 Grep 可见新增 ContextAwareBehaviorAnalyzer
- [ ] 6 类违规颜色配置可在 `config.py` 中找到
- [ ] 至少 1 张测试图（可以画出来模拟）能跑出 lane_lines + traffic_light 结果

---

### M06: 规则引擎可扩展性（场景插件化，证明"大脑可扩展"）
**目标**：证明"加新场景 = 写插件，不改核心"，为"城市智眼"格局铺路

**Git 复用关键词**：
- "python plugin architecture importlib"
- "pluggable rule engine framework"
- "scenario based detection system design"

**具体要求**：
- 创建 `e:\output\1\api\rule_engine\` 目录：
  - `__init__.py`
  - `base_plugin.py`：`BaseRulePlugin` 基类，定义接口：
    - `scenario_name: str` 例如 "traffic", "urban_management", "public_security"
    - `detectable_types: List[str]`
    - `initialize()` / `shutdown()`
    - `analyze(frame, scene_context, tracker) -> List[ViolationEvent]`
  - `plugin_loader.py`：`PluginLoader` 用 `importlib.import_module` 动态加载指定目录下所有插件
  - `plugins/traffic_plugin.py`：把现有行为分析封装成第一个插件（从 behavior_engine 迁移核心逻辑）
  - `plugins/__init__.py`
- 修改 `realtime_detector.py` / 主流程：
  - 原硬编码行为分析替换为 `self.plugin_loader.get("traffic").analyze(...)`
  - 配置 `plugins_enabled=["traffic", "urban_management", "public_security"]` 在 config.py 中
- 文档：`e:\output\1\docs\plugin_development_guide.md`：写一个新插件只需三步（继承 Base → 放到 plugins/ → config 启用），含代码模板

**验收**：
- [ ] 目录结构正确，4 个核心文件 ast 通过
- [ ] `plugins_enabled` 配置关闭 traffic 插件 → 不分析交通违规（测试验证）
- [ ] 文档 guide 有可复制粘贴的代码模板
- [ ] Grep 确认原硬编码调用已替换为插件调用

---

### M07: 非交通场景演示（2 个：城管+治安）
**目标**：答辩时能切到"占道经营"和"人员聚集"两个场景，证明"城市智眼"架构不限于交通

**Git 复用关键词**：
- "street vendor detection YOLOv8"
- "crowd counting detection python github"
- "illegal street stall dataset"
- "crowd gathering detection YOLO"

**具体要求**：
- 插件 1：`plugins/urban_management_plugin.py`
  - 场景：占道经营（人员+摊位+货物+人行道区域）
  - 简化版：检测到 person + backpack/bag/table 等在道路边缘区域 → 触发"疑似占道经营"
  - 颜色：蓝色（与 M05 颜色表统一）
- 插件 2：`plugins/public_security_plugin.py`
  - 场景：人员聚集（≥6 人聚集在同一区域超过 10 秒）
  - 实现：检测人数 + 聚类（DBSCAN，GitHub 搜现成片段）+ 连续 N 帧确认
  - 颜色：黄色（与 M05 颜色表统一）
- 演示模式：
  - 在前端 Settings 页增加"场景模式"下拉：交通/城管/治安/全量
  - 切换后只启用对应插件（调 `/api/realtime/plugins` 接口）
- 准备测试图片或简单位置模拟（可画假 bbox 让插件判定流程跑通），保证在没有真实现场数据时也能演示插件架构是通的

**验收**：
- [ ] 两个插件文件 ast 通过
- [ ] Settings 页面有下拉，vite build 通过
- [ ] 插件接口 `/api/realtime/plugins` 能列出并切换
- [ ] 至少 1 次假数据测试：切换后对应颜色违规事件能产生

---

### M08: 云台控制（ONVIF 协议 + 软件就绪）
**目标**：软件层写好 PTZ 控制代码，硬件到了直接接；为"移动智眼"铺路

**Git 复用关键词**：
- "python-onvif ptz continuousMove example"
- "onvif-zeep camera control"
- "python onvif absolute move relative move"
- "海康 onvif python"

**必须参考的本地资源**：
- `e:\output\1\K230\01.快速入门\9.二维云台安装教程`（K230 自带云台的 PWM 控制方式，为后续 K230 直接驱动云台做备选）

**具体要求**：
- 创建 `e:\output\1\api\ptz_controller.py`：
  - `PTZControllerBase` 抽象类
  - `ONVIFPTZController(PTZControllerBase)`：
    - 初始化：camera_ip、port、username、password、profile
    - `get_position() -> {pan, tilt, zoom}`
    - `move_absolute(pan, tilt, zoom, speed)`
    - `move_relative(dx, dy, dz, speed)`
    - `zoom_in(level)`, `zoom_out(level)`
    - `track_object(bbox_xyxy, frame_width, frame_height) -> dx, dy, dz`（根据目标在画面中的位置计算偏移量，为追踪做准备）
    - `goto_home()`（追踪结束回中）
  - `SimulatedPTZController`（无硬件时的模拟控制器，返回设定值）
  - 策略：`PTZFactory(config)` 根据配置选 ONVIF/Simulated
- 依赖安装：`pip install onvif-zeep` 或维护更活跃的 fork，先搜 GitHub 选对库
- 接口：`POST /api/realtime/ptz/move`, `POST /api/realtime/ptz/zoom`, `POST /api/realtime/ptz/home`, `GET /api/realtime/ptz/status`
- 文档：`e:\output\1\docs\onvif_setup.md`：摄像头端开启 ONVIF、确认端口、获取 profile token 的步骤清单

**验收**：
- [ ] `ptz_controller.py` ast 通过
- [ ] 4 个 PTZ 路由接口存在（Grep 路由文件）
- [ ] Simulated 模式下，调用接口返回结构正确
- [ ] `onvif_setup.md` 文档可操作（不含敏感信息）

---

### M09: 软件虚拟追踪（无硬件时也能追踪 + 画面输出）
**目标**：检测到违规车辆后自动锁定，数字裁剪+放大，多帧车牌捕捉；硬件到了无缝替换 ONVIF

**Git 复用关键词**：
- "object tracking visual servoing python"
- "cv2 crop zoom bounding box smooth"
- "license plate super frame accumulation"

**具体要求**：
- 创建 `e:\output\1\api\virtual_tracker.py`：
  - `VirtualTracker`：
    - `start_tracking(track_id, target_bbox)` → 锁定追踪目标
    - `update(frame, all_tracks)` → 根据追踪 ID 更新目标位置
    - `get_tracking_crop(frame, out_size=(640,640))` → 目标区域 + 边缘 + 高斯平滑放大（"数字变焦"）
    - `get_focus_indicator()` → 前端画中画需要的 {target_center_x, target_center_y, crop_size, zoom_level}
    - 平滑：目标移动时做指数移动平均（EMA），避免抖动
  - 追踪优先级：confirmed 违规车辆 > pending 违规 > 普通车辆（优先级队列，每帧重选）
- 集成到 realtime：
  - `/api/realtime/tracking/start?track_id=xxx`
  - `/api/realtime/tracking/stop`
  - `/api/realtime/tracking/status` → 含 crop 的 base64 JPEG 小图
  - `/api/realtime/stream`（或现有 snapshot 扩展）增加可选参数 `?tracking_crop=1` 返回追踪放大图
- 车牌采集增强：追踪状态下每 200ms 自动裁一张车牌图送入 license_plate_recognizer，取多帧结果投票（融合 M03 多帧确认）

**验收**：
- [ ] `virtual_tracker.py` ast 通过
- [ ] 3 个 tracking 路由存在
- [ ] 单元测试：给定模拟 bbox 序列，EMA 平滑后抖动降低（最大位移差 ≤ 原值*0.5）
- [ ] 追踪状态下车牌至少累计 3 张样本才投票

---

### M10: 追踪 + 行为标注前端 UI（采纳 TASK-027 建议：图标校验脚本）
**目标**：实时监控画面显示追踪中目标、不同行为不同颜色、追踪画中画；加图标校验脚本

**采纳 TASK-027 建议落实**：
- 不同行为不同颜色标注（本任务强制）
- 图标名称校验脚本（本任务新建）

**具体要求**：
- `RealTimeMonitor.vue` 增加：
  - 追踪目标：红色圆形脉动指示器 + 追踪 ID 标签 + 跟随放大的"画中画"小窗（右上角/左上角）
  - bbox 颜色按 M05 的颜色表，标签右边加违规类型图标
  - 顶部行为统计条：已确认违规数、待确认数、平均 FPS、当前场景模式
  - 左/右键或按钮：切换追踪目标、取消追踪、回到全局视图
- 图标校验脚本：`e:\output\1\web-admin\scripts\verify-icons.cjs`
  - 读取 RealTimeMonitor.vue 和所有 views/*.vue，抽 import { xxx } from '@element-plus/icons-vue'
  - 对每个图标查 `@element-plus/icons-vue/dist/index.js`（或其 exports）确认存在
  - 不存在就报错退出、输出缺失图标列表
  - package.json `scripts` 加 `"verify-icons": "node scripts/verify-icons.cjs"`，并写入构建命令前的 hook（可选）
- `vite build` 通过；`npm run verify-icons` 通过

**验收**：
- [ ] RealTimeMonitor.vue 改动点 ≥ 4 处（追踪指示/颜色/统计条/画中画）
- [ ] verify-icons 脚本能执行并输出 OK（至少对 3 个真实图标做测试）
- [ ] `vite build` exit code 0

---

### M14: 数字孪生与真实数据联动（可视化治理）
**目标**：数字孪生不再是独立动画，真实检测到的违规会在数字孪生场景中出现红色旋转箭头+车牌标注

**Git 复用关键词**：
- "three.js label follow object sprite"
- "CSS2DRenderer arrow rotate around object"
- "digital twin real time data feed socketio"

**具体要求**：
- 后端 `e:\output\1\digital_twin\app.py`：
  - 新增订阅机制：轮询（或 WebSocket）api 的 `/api/realtime/status` 和 `/violations`
  - 把最新违规事件推到前端：`{track_id, plate_number, violation_type, lat, lng, confidence}`
  - lat/lng 暂时用"十字路口四个象限映射到固定坐标"，真实 GPS 接口预留
- 前端 `digital_twin/templates/index.html` + static/js/main.js：
  - 新增违规标注层：CSS2D 渲染车牌号 + 违规类型卡片
  - 红色旋转跟随箭头（用 THREE.Group + 子 Mesh，每帧绕目标车旋转）
  - 仪表盘同步：今日逆行数、未戴头盔数、闯红灯数、违停数（从后端统计接口拉）
  - 四种违规场景演示按钮：点"演示逆行"→ 在场景中按规范生成一次逆行违规动画，联动后端产生一条示例违规
- 红绿灯逻辑（之前提过的）：倒计时 + 真正的三色逻辑（灯与灯之间联动，不再流水灯）

**验收**：
- [ ] app.py 新增订阅/推送，ast 通过
- [ ] 数字孪生页面能显示红色旋转箭头 + 车牌标签（静态 mock 数据也可）
- [ ] 仪表盘四个计数字段有来源
- [ ] 红绿灯有倒计时数字，且颜色切换顺序正确（红→绿→黄→红...）

---

### M17: CARLA 仿真环境接入（输入端 + 数字孪生联动）
**目标**：CARLA 仿真画面作为数据源替代真实摄像头，同时 CARLA 场景中的车辆位置/红绿灯状态同步到数字孪生 3D 场景，实现"仿真输入→AI检测→数字孪生展示"完整链路。答辩时点"开始仿真演示"就能跑完闭环，无需真实摄像头。

**CARLA 资源已就位**：
- 安装路径：`e:\output\1\carla\CARLA_0.9.16\`
- 主程序：`CarlaUE4.exe`
- PythonAPI：`e:\output\1\carla\CARLA_0.9.16\PythonAPI\`（含 `manual_control.py`、`generate_traffic.py`、`dynamic_weather.py`、`synchronous_mode.py` 等示例）
- 地图：Town01-Town07 + Town10HD（7 个城镇）
- HDMaps：含点云高精地图

**已有可复用代码**：
- [blind_yun.py](file:///e:/output/1/beforeness/blind_yun.py) 的 `init_carla()` / `carla_camera_callback()` / `cleanup_carla()` 函数框架
- PythonAPI/examples 下的官方示例（`spawn_npc.py`、`generate_traffic.py`）

**必须做的 Git 复用步骤**：
1. GitHub Skill 搜 "carla python api traffic simulation" / "carla sensor data yolo integration" / "carla synchronous mode example" / "carla vehicle position websocket stream"
2. 重点找：CARLA 传感器数据 → YOLO 检测的集成方案、CARLA 同步模式最佳实践、CARLA 车辆位置实时推送方案
3. 对比至少 2 个仓库，选最适合的方案复用

**具体要求**：

#### 1. CARLA 客户端封装
- 创建 `e:\output\1\api\carla_source.py`：
  - `CarlaSource` 类（作为数据源抽象，与摄像头/视频文件同级）：
    - `connect(host='localhost', port=2000)` → 连接 CARLA 服务器
    - `spawn_vehicles(n=20)` → 生成 N 辆自动驾驶车辆（复用 `generate_traffic.py` 逻辑）
    - `spawn_walkers(n=10)` → 生成行人
    - `attach_camera(width=640, height=480, fov=90)` → 生成摄像头传感器，回调存帧
    - `get_frame() -> np.ndarray` → 获取最新帧（BGR 格式，兼容 OpenCV）
    - `get_actors_state() -> List[{id, type, location, rotation, velocity}]` → 获取所有车辆/行人位置
    - `get_traffic_lights() -> List[{id, location, state}]` → 获取红绿灯状态
    - `set_synchronous_mode(dt=0.05)` → 同步模式（推荐，保证检测稳定性）
    - `tick()` → 同步模式下推进一帧
    - `disconnect()` → 清理所有 actor
  - **graceful degradation**：CARLA 未启动时 `connect()` 返回 False，所有方法返回空，不阻塞主流程
  - 复用 `blind_yun.py` 中已验证可行的 `init_carla()` 逻辑

#### 2. 集成到实时检测主流程
- 修改 `e:\output\1\api\realtime_detector.py`：
  - 新增数据源选择：`source_type = "camera" | "video" | "carla"`
  - `source_type == "carla"` 时：
    - `CarlaSource.get_frame()` 替代摄像头读取
    - 每帧检测后，用 `get_actors_state()` 获取车辆真实位置（用于数字孪生联动）
    - 用 `get_traffic_lights()` 获取红绿灯真实状态（喂给 M05 的 TrafficLightDetector 做交叉验证）
  - `process_frame` 流程不变：detect → track → plate → behavior → validate → write
- 新增路由：
  - `POST /api/realtime/source` 切换数据源 `{source_type, video_path?}`
  - `GET /api/realtime/carla/status` → CARLA 连接状态、actor 数量、当前地图
  - `POST /api/realtime/carla/spawn` → 生成车辆/行人 `{vehicles, walkers}`
  - `POST /api/realtime/carla/next-scene` → 切换城镇（Town01→Town03 等）

#### 3. 数字孪生联动
- 修改 `e:\output\1\digital_twin\app.py`：
  - 新增 CARLA 状态订阅：轮询 `/api/realtime/carla/status` + `/api/realtime/actors`
  - 把 CARLA 车辆位置映射到数字孪生 3D 场景坐标：
    - CARLA (x, y, z) → Three.js 场景坐标（缩放 + 旋转校正）
    - 建立 Town01-Town07 的坐标映射表（每个城镇一个 transform 矩阵）
  - 实时推送：CARLA 车辆位置 → WebSocket → 前端 3D 场景车辆模型同步移动
  - 红绿灯同步：CARLA 红绿灯状态 → 数字孪生路口红绿灯模型颜色切换
- 前端 `digital_twin/static/js/main.js`：
  - 新增 "CARLA 模式" 切换按钮
  - 车辆模型跟随 CARLA 真实位置移动（不再是随机动画）
  - 检测到违规时，对应 CARLA 车辆在数字孪生中出现红色旋转箭头（复用 M14 的标注层）

#### 4. 一键演示脚本
- 创建 `e:\output\1\scripts\run_carla_demo.py`：
  - 自动启动 CarlaUE4.exe（或提示用户手动启动）
  - 连接 CARLA → 生成交通 → 切换数据源为 carla → 启动检测
  - 演示场景：
    - `--scene town01` → Town01 城镇交通流
    - `--scene town03` → Town03 复杂路口（含红绿灯）
    - `--scene violation` → 生成一辆闯红灯车辆（用 CARLA 交通管理器控制）
  - 输出：违规日志 + 车牌识别结果 + 数字孪生事件推送
- 文档：`e:\output\1\docs\carla_integration_guide.md`：
  - CARLA 启动步骤、PythonAPI 安装（`pip install carla==0.9.16`）
  - 同步模式 vs 异步模式选择建议
  - 常见问题（端口占用、actor 数量上限、GPU 显存）

**验收**：
- [ ] `carla_source.py` ast 通过，CarlaSource 类所有方法定义齐全
- [ ] CARLA 未启动时，`connect()` 返回 False，主流程不报错（单元测试）
- [ ] `realtime_detector.py` 中 source_type 支持 "carla"（Grep 验证）
- [ ] 4 个 CARLA 路由存在（Grep 路由文件）
- [ ] `digital_twin/app.py` 新增 CARLA 状态订阅（Grep 验证）
- [ ] `run_carla_demo.py` ast 通过
- [ ] `carla_integration_guide.md` 文档齐全（含启动步骤+常见问题）
- [ ] **真实跑通验证**（需用户醒来后在 Edge 浏览器确认）：
  - 启动 CarlaUE4.exe → 启动后端 → 切换数据源为 carla → 看到实时检测画面
  - 数字孪生场景中车辆模型跟随 CARLA 车辆移动
  - 检测到违规时数字孪生出现红色箭头标注

**注意事项**：
1. CARLA 启动需要独立终端运行 `CarlaUE4.exe -quality-level=Low`（降低 GPU 压力）
2. PythonAPI 需安装对应版本：`pip install carla==0.9.16`
3. 同步模式下，Server 等待 Client 调用 `world.tick()` 才推进，适合检测稳定性
4. CARLA 占用显存较大，建议 RTX 4060 上 actor 数量 ≤ 50（车辆+行人合计）
5. 如果 CARLA 启动失败或显存不足，降级为视频文件演示模式（在 deviations 中说明）

---

### M16: 集成测试 · 临时文件清理 · 建议采纳汇总 · OUTPUT 总报告
**目标**：全流程验证 + 清理 + 执行者反馈 + 建议采纳记录

**具体要求**：
1. **集成测试**：
   - 启动后端 → `run_carla_demo.py --scene town01` → 看产生的违规是否包含：车牌 + 多帧确认 + 行为标注 + 颜色正确
   - CARLA 链路：启动 CARLA → 切换数据源 → 实时检测 → 数字孪生车辆同步移动 → 违规出现红色箭头
   - 插件切换：管理端切换到"城管"模式 → 占道经营插件工作
   - 数字孪生：CARLA 模式 → 数字孪生收到事件 → 出现旋转箭头 + 车牌标注
2. **代码质量**：
   - verification-before-completion 强制跑：所有新文件 ast + vite build + verify-icons
   - CodeRabbit Skill（或至少 Grep + 肉眼）审查 3 个最核心文件：`license_plate_recognizer.py`、`virtual_tracker.py`、`carla_source.py`
3. **清理**：
   - `e:\output\1\camera_test_frame_*.jpg` 全部删
   - `e:\output\1\api\diag_frame.*` 删
   - `e:\output\1\api\test_*.py` 如不是正式 `tests/` 目录则移到 `tests/` 或归档
   - `__pycache__` 清理
4. **反馈与建议（强制）**：
   - OUTPUT feedback 中必须包含：
     - 对指挥官任务设计/优先级/沟通的具体改进建议（≥ 2 条）
     - 对本项目技术方向最值得优先投入的一个方向
     - 本任务中，对指挥官哪个决策最有异议，替代方案是什么
   - suggestions_adopted 必须逐条列出（≥ 3 条，含 M03 中已采纳的 TASK-027 建议，另加至少 2 条本任务新建议）

**验收**：
- [ ] 4 条集成链路有日志证明跑通（或单元测试模拟证明链路完整）
- [ ] 清理前后文件对比（至少 3 类临时文件被清理/归档）
- [ ] CodeRabbit 审查输出/或审查记录在 OUTPUT notes 中
- [ ] suggestions_adopted ≥ 3 条，commander_suggestions ≥ 2 条

---

## 四、文件路径总索引

```
e:\output\1\api\
├── license_plate_recognizer.py    M01 新建
├── k230_plate_client.py          M02 新建
├── multi_frame_validator.py      M03 新建
├── scene_perception.py           M05 新建
├── ptz_controller.py             M08 新建
├── virtual_tracker.py            M09 新建
├── carla_source.py               M17 新建（CARLA 数据源封装）
├── rule_engine\                  M06 新建目录
│   ├── base_plugin.py
│   ├── plugin_loader.py
│   └── plugins\
│       ├── traffic_plugin.py
│       ├── urban_management_plugin.py   M07
│       └── public_security_plugin.py    M07
├── routers\
│   ├── realtime.py (M03/M04/M08/M09/M17 改动)
│   └── violations.py (M04 改动)
├── realtime_detector.py          M03/M06/M09/M17 集成（新增 source_type 切换）
├── behavior_engine.py            M05 增强
├── config.py                     全局配置补充
└── database.py / models.py       M04 新增字段 / 迁移

e:\output\1\zhitong\k230_app\
└── plate_server.py               M02 K230 端服务端框架

e:\output\1\web-admin\
├── src\views\
│   ├── RealTimeMonitor.vue       M10 大改
│   ├── Settings.vue              M07 场景下拉
│   ├── Violations.vue            M04 列表/搜索
│   └── ViolationDetail.vue       M04 车牌卡片
├── scripts\verify-icons.cjs      M10 新建
└── package.json                  scripts 新增 verify-icons

e:\output\1\digital_twin\
├── app.py                        M14/M17 改动（新增 CARLA 状态订阅）
└── static\js\main.js             M14/M17 改动（CARLA 模式 + 车辆同步）

e:\output\1\scripts\
└── run_carla_demo.py             M17 新建（一键演示脚本）

e:\output\1\docs\
├── k230_plate_protocol.md        M02 新建
├── plugin_development_guide.md   M06 新建
├── onvif_setup.md                M08 新建
└── carla_integration_guide.md    M17 新建

e:\output\1\tests\
└── test_multi_frame_validator.py M03 新建

e:\output\1\carla\CARLA_0.9.16\   已就位（不动）
├── CarlaUE4.exe                  主程序
├── PythonAPI\                    官方示例和工具
└── HDMaps\                       7 个城镇高精地图
```

---

## 五、OUTPUT 文件清单
- `e:\output\_TASK-028-M01_OUTPUT.json` … `M10_OUTPUT.json`
- `e:\output\_TASK-028-M14_OUTPUT.json`、`M17_OUTPUT.json`、`M16_OUTPUT.json`
- `e:\output\_TASK-028_OUTPUT.json` 总报告（12 个子任务汇总 + 总状态 + 建议采纳总数）
- **已移除**：M11/M12/M13（小程序）/ M15（答辩材料）的 OUTPUT 不需要产生

---

## 六、风险提示（执行者可提出更好方案，无需等批准）
1. **PaddleOCR 安装重**：建议先查 GitHub 上有哪些 "10MB 以内轻量 OCR 车牌方案"，能跑通就优先用轻量的
2. **非交通场景没数据**：允许用假 bbox + mock 数据演示插件架构，但文档要说明"这是演示模式，真实模型在 xx 数据集上训练"
3. **12 个子任务量大**：可在 OUTPUT 中建议拆分，但**在指挥官批准之前必须按顺序推进**，允许部分子任务标记 PARTIAL，理由要写清楚
4. **K230 未连接**：K230 相关模块在 K230 未连接情况下必须能跳过，不能阻塞 PC 端其他模块
5. **CARLA 显存压力**：RTX 4060 Laptop GPU 同时跑 CARLA + YOLO 检测可能显存紧张，建议：
   - CARLA 用 `-quality-level=Low` 启动
   - actor 数量 ≤ 50
   - 如果显存不足，CARLA 检测降级为"CARLA 录制视频 → 离线检测"模式
6. **CARLA + 实时检测性能**：同步模式下 CARLA 等 tick，可能降低整体 FPS。建议先测异步模式，FPS 不达标再切同步
7. **战友协作提醒**：执行者遇到任何难题、异议、更好方案，直接在 feedback 中提出，不必等批准。指挥官承诺对合理建议全部采纳
