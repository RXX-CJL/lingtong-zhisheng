# TASK-029: 交通事件闭环系统架构升级（GPT 建议第一阶段）

> **任务级别**: 大型架构升级任务（9 个子任务）
> **来源**: GPT《灵瞳智声项目架构升级技术需求说明.docx》22 章节
> **核心目标**: 建立可靠的"交通事件闭环"——从"视频→AI→违法"升级为"视频→本地感知→事件触发→事件视频→云端AI复核→违法事件"
> **前提必读**: `e:\output\PROJECT_HANDOVER_REPORT.md` 第十五、十六章（GPT 创新点 + 交接文件维护规则）
> **依赖**: TASK-028 已完成（YOLO检测/多帧确认/规则引擎/CARLA/数字孪生全部就位）

---

## 〇、GPT 原则总纲（每个子任务都必须遵守）

GPT 文档第 20 章规定的 8 大开发原则：

1. **增量开发** — 在现有代码基础上增加功能，不推翻式重构
2. **模块解耦** — 事件引擎/缓存/AI分析/交通流各自独立
3. **统一数据** — 车辆状态/事件/AI结果有清晰数据结构
4. **AI 按需调用** — 本地持续感知，云端只分析疑似事件
5. **确定性逻辑优先** — 能用规则/数学完成的不调用大模型
6. **证据优先** — 违法判断必须保存完整事件证据
7. **允许不确定** — AI 可返回"无法确认"，不强判
8. **先完成闭环再提高复杂度** — 先跑通事件闭环，再加交通流/信号优化

---

## 一、子任务总览与依赖关系

```
M01 项目分析报告（GPT §19 强制要求）
 ├── M02 CircularFrameBuffer 视频循环缓存（GPT §5）
 ├── M03 TrafficEventEngine 交通事件引擎 + 事件状态机（GPT §6-7）
 │    └── M04 EvidenceChain 完整证据链（GPT §10）
 ├── M05 CloudAI 按需调用改造（GPT §8）
 │    └── M06 realtime_detector 集成循环缓存+事件引擎（GPT §11）
 │         └── M07 API 路由 + 数据库迁移
 │              └── M08 Web 端交通事件中心（GPT §15.1）
 └── M09 集成测试 + 闭环验证（GPT §21）
```

**执行顺序**: M01 → (M02 / M03 / M05 可并行) → M04 → M06 → M07 → M08 → M09

---

## 二、子任务详情

### M01: 项目分析报告（GPT §19 强制要求）

**目的**: GPT 文档第 19 章明确要求"在修改任何代码之前，必须先完成项目分析"。本任务是整个升级的基础。

**执行步骤**:

1. 读取交接报告 `e:\output\PROJECT_HANDOVER_REPORT.md` 全文
2. 分析以下 12 个维度（对应 GPT §19 的 12 项检查）：
   - 项目目录结构
   - 前端技术栈
   - 后端技术栈
   - 数据库结构
   - 当前视频流处理方式（`realtime_detector.py` 的 `_detection_loop`）
   - 当前 YOLO 调用方式（`image_recognizer.py` 的 `multi_model_detect`）
   - 当前目标跟踪实现（`vehicle_tracker.py`）
   - 当前违法判断逻辑（`violation_rules.py` + `behavior_engine.py` + `rule_engine/`）
   - 当前云端 AI 接口（`cloud_collaborator.py` 的 `analyze_with_doubao/deepseek`）
   - Web 与后端数据交互方式（Vue3 → FastAPI `/api/realtime/*`）
   - 微信小程序与后端交互（`routers/wechat.py` 现状）
   - 已实现 vs 未实现功能清单

3. 对照 GPT 建议，输出分析报告，包含：
   - 当前架构总结（一段话）
   - 已有功能清单（表格）
   - 与 GPT 需求的对应关系（表格，标注 ✅已有 / 🟡部分 / 🔴缺失）
   - 需要新增的模块清单
   - 需要修改的模块清单
   - 技术风险评估
   - 推荐开发顺序

4. 将分析报告写入 `e:\output\1\docs\project_analysis_gpt_upgrade.md`

**验收标准**:
- [ ] 分析报告涵盖 GPT §19 的全部 12 项检查
- [ ] 每一项都引用了具体的现有文件路径
- [ ] 输出了"需要新增"和"需要修改"两个清单
- [ ] 输出了技术风险评估（至少 3 条）
- [ ] 输出了推荐开发顺序

**输出文件**: `e:\output\_TASK-029-M01_OUTPUT.json`

---

### M02: CircularFrameBuffer 视频循环缓存（GPT §5）

**目的**: GPT §5 要求"实时维护一个固定长度的循环缓存（20-30 秒），事件触发后提取事件前后的视频片段"。

**这是全新模块，现有代码没有此功能。**

**现有代码参考**:
- `realtime_detector.py` 第 57 行 `self.frame_cache = deque(maxlen=Config.FRAME_CACHE_SIZE)` — 现有只有 10 帧缓存，太短
- `_detection_loop` 第 188/202 行 `self.frame_cache.append(frame.copy())` — 现有只存帧不存时间戳和检测结果

**执行步骤**:

1. 新建文件 `e:\output\1\api\circular_frame_buffer.py`

2. 实现 `CircularFrameBuffer` 类，接口设计：
   ```python
   class CircularFrameBuffer:
       """视频循环缓存 — 实时维护最近 N 秒视频帧+检测结果
       
       事件触发后提取事件前后视频片段合成完整事件视频。
       """
       def __init__(self, duration_sec=30, fps=10):
           """初始化循环缓存
           
           Args:
               duration_sec: 缓存时长（秒），默认 30s
               fps: 预期帧率，默认 10fps
           """
       
       def add(self, timestamp: float, frame, detection_result: dict):
           """添加一帧到缓存
           
           Args:
               timestamp: time.time() 时间戳
               frame: numpy ndarray (BGR)
               detection_result: 当前帧的检测结果 dict（detections/tracked_vehicles/behaviors）
           """
       
       def extract_event_clip(self, trigger_time: float, before_sec=5, after_sec=5) -> list:
           """提取事件视频片段
           
           Args:
               trigger_time: 事件触发时间戳
               before_sec: 事件前秒数（默认 5s）
               after_sec: 事件后秒数（默认 5s）
           
           Returns:
               List[(timestamp, frame)] 用于合成事件视频
           """
       
       def save_event_video(self, frames: list, output_path: str, fps=10) -> str:
           """将帧序列保存为视频文件
           
           Args:
               frames: extract_event_clip 的返回值
               output_path: 输出路径
               fps: 输出视频帧率
           
           Returns:
               保存后的文件路径
           """
       
       def get_latest(self, n=1) -> list:
           """获取最近 n 帧"""
       
       def clear(self):
           """清空缓存"""
       
       @property
       def size(self) -> int:
           """当前缓存帧数"""
       
       @property
       def duration(self) -> float:
           """当前缓存覆盖的时长（秒）"""
   ```

3. 配置参数必须在 `config.py` 的 `Config` 类中增加：
   ```python
   FRAME_BUFFER_DURATION = int(os.environ.get('FRAME_BUFFER_DURATION', 30))  # 缓存时长秒
   FRAME_BUFFER_FPS = int(os.environ.get('FRAME_BUFFER_FPS', 10))  # 预期帧率
   EVENT_CLIP_BEFORE_SEC = int(os.environ.get('EVENT_CLIP_BEFORE_SEC', 5))  # 事件前秒数
   EVENT_CLIP_AFTER_SEC = int(os.environ.get('EVENT_CLIP_AFTER_SEC', 5))  # 事件后秒数
   ```

4. 事件视频保存目录：`e:\output\1\api\output\event_videos\{YYYYMMDD}\{event_id}.mp4`
   - 使用 `cv2.VideoWriter` 写入
   - 编码格式 `mp4v`

5. 单元测试：新建 `e:\output\1\tests\test_circular_frame_buffer.py`
   - 测试添加帧和缓存大小限制
   - 测试 extract_event_clip 提取正确时间范围
   - 测试 save_event_video 生成有效 mp4 文件
   - 测试 duration 属性正确

**验收标准**:
- [ ] `CircularFrameBuffer` 类完整实现上述 7 个方法
- [ ] 缓存大小自动按 `duration_sec * fps` 限制
- [ ] `extract_event_clip` 能正确提取 T-before 到 T+after 的帧
- [ ] `save_event_video` 生成可播放的 mp4 文件
- [ ] 配置参数全部可通过环境变量调整
- [ ] 单元测试 ≥ 6 个全部通过
- [ ] Python AST 语法验证通过

**输出文件**: `e:\output\_TASK-029-M02_OUTPUT.json`

---

### M03: TrafficEventEngine 交通事件引擎 + 事件状态机（GPT §6-7）

**目的**: GPT §6-7 要求"基于规则/状态机/轨迹/信号灯发现疑似交通事件，并为事件设计 8 状态生命周期"。

**现有代码参考**:
- `rule_engine/base_plugin.py` — `BaseRulePlugin` 基类 + `ViolationEvent` 数据类
- `rule_engine/plugins/traffic_plugin.py` — 交通违规插件（现有规则分析）
- `behavior_engine.py` — `BehaviorEngine` 行为分析（闯红灯/逆行/违停/未戴头盔）
- `multi_frame_validator.py` — `MultiFrameValidator` 多帧确认（已有"疑似事件确认"雏形）

**关键设计思路**: 现有 `rule_engine` 插件是"单帧即时判断"，事件引擎是"跨帧持续跟踪+状态机+事件生命周期"。

**执行步骤**:

1. 新建文件 `e:\output\1\api\traffic_event_engine.py`

2. 实现 `EventState` 枚举（GPT §7 的 8 状态）：
   ```python
   from enum import Enum
   
   class EventState(Enum):
       DETECTING = "detecting"          # 正在检测，规则引擎持续评估
       TRIGGERED = "triggered"          # 已触发疑似事件
       RECORDING = "recording"          # 正在等待事件结束并录制完整视频
       PENDING_AI = "pending_ai"        # 等待云端 AI 分析
       AI_REVIEWED = "ai_reviewed"      # 云端 AI 已分析
       CONFIRMED = "confirmed"          # 确认违法
       REJECTED = "rejected"            # 排除事件
       MANUAL_REVIEW = "manual_review"   # 需人工复核
   ```

3. 实现 `TrafficEvent` 数据类：
   ```python
   @dataclass
   class TrafficEvent:
       """交通事件对象 — 拥有完整生命周期"""
       event_id: str                    # 唯一 ID（uuid 或 timestamp+track_id）
       event_type: str                  # 事件类型（red_light / wrong_way / illegal_park / no_helmet）
       track_id: int                    # 关联车辆 track_id
       state: EventState                # 当前状态
       trigger_time: float              # 触发时间戳
       created_at: str                  # 创建时间 ISO8601
       updated_at: str                  # 更新时间 ISO8601
       
       # 事件上下文
       vehicle_info: dict               # 车辆信息（type/bbox/plate）
       scene_context: dict              # 场景上下文（traffic_light/lane/stop_line）
       trajectory: list                 # 车辆轨迹点序列 [(x, y, timestamp)]
       
       # 证据
       key_frames: list                 # 关键帧路径列表
       event_video_path: str            # 事件视频路径
       rule_judgment: dict              # 本地规则判断结果
       ai_judgment: dict                # 云端 AI 判断结果
       ai_confidence: float             # AI 置信度
       ai_explanation: str              # AI 分析说明
       
       # 生命周期管理
       state_history: list              # 状态变更历史 [(timestamp, old_state, new_state, reason)]
       cooldown_until: float            # 冷却到期时间（避免同一车辆重复触发）
   ```

4. 实现 `TrafficEventEngine` 类：
   ```python
   class TrafficEventEngine:
       """交通事件引擎 — 基于规则+状态机发现和管理交通事件
       
       不直接调用云端 AI。只负责：
       1. 发现疑似事件（基于规则引擎输出）
       2. 管理事件生命周期（状态转换）
       3. 触发视频缓存提取
       4. 触发云端 AI 分析请求
       """
       def __init__(self, rule_plugins: list, frame_buffer: CircularFrameBuffer):
           """初始化事件引擎
           
           Args:
               rule_plugins: 规则插件列表（从 PluginLoader 加载）
               frame_buffer: CircularFrameBuffer 实例
           """
       
       def process_frame(self, frame, detections, tracked_vehicles, scene_context) -> list:
           """处理一帧 — 调用规则插件评估，发现疑似事件则创建/更新事件
           
           Returns:
               新创建或更新状态的 TrafficEvent 列表
           """
       
       def _trigger_event(self, violation_event, vehicle_info, scene_context) -> TrafficEvent:
           """触发新事件 — 创建 TrafficEvent 对象，状态 → TRIGGERED"""
       
       def _update_event_state(self, event, new_state, reason=""):
           """更新事件状态 — 记录状态历史"""
       
       def _check_cooldown(self, track_id, event_type) -> bool:
           """检查冷却期 — 避免同一车辆短时间内重复触发"""
       
       def get_active_events(self) -> list:
           """获取所有未结束的事件（state 不是 CONFIRMED/REJECTED）"""
       
       def get_event(self, event_id) -> TrafficEvent:
           """获取指定事件"""
       
       def submit_to_ai(self, event_id) -> dict:
           """将事件提交给云端 AI 分析 — 状态 → PENDING_AI
           
           Returns:
               提交信息（事件视频路径 + 关键帧 + 结构化上下文）
           """
       
       def apply_ai_result(self, event_id, ai_result: dict):
           """应用云端 AI 分析结果 — 状态 → AI_REVIEWED
           
           根据 ai_result 更新事件状态：
           - AI 确认违法 → CONFIRMED
           - AI 排除 → REJECTED  
           - AI 不确定 → MANUAL_REVIEW
           """
   ```

5. 状态转换规则（严格按 GPT §7）：
   ```
   DETECTING → TRIGGERED（规则满足触发条件）
   TRIGGERED → RECORDING（开始录制事件视频，等待 after_sec 后完成）
   RECORDING → PENDING_AI（事件视频录制完成，提交云端）
   PENDING_AI → AI_REVIEWED（云端返回结果）
   AI_REVIEWED → CONFIRMED（AI 确认违法）
   AI_REVIEWED → REJECTED（AI 排除）
   AI_REVIEWED → MANUAL_REVIEW（AI 不确定 / 证据不足）
   MANUAL_REVIEW → CONFIRMED（人工复核确认）
   MANUAL_REVIEW → REJECTED（人工复核排除）
   ```

6. 冷却机制：同一 `track_id + event_type` 组合在 60 秒内不重复触发（可配置）

7. 单元测试：新建 `e:\output\1\tests\test_traffic_event_engine.py`
   - 测试事件创建和状态转换
   - 测试冷却机制
   - 测试 get_active_events
   - 测试 submit_to_ai 和 apply_ai_result

**验收标准**:
- [ ] `EventState` 枚举包含 8 个状态
- [ ] `TrafficEvent` 数据类包含 GPT §10 的全部证据字段
- [ ] `TrafficEventEngine` 实现上述 8 个方法
- [ ] 状态转换严格按照 GPT §7 的规则，不允许非法转换
- [ ] 冷却机制生效（同车同类型 60s 内不重复触发）
- [ ] 不直接调用云端 AI（只生成提交请求 dict）
- [ ] 单元测试 ≥ 8 个全部通过
- [ ] Python AST 语法验证通过

**输出文件**: `e:\output\_TASK-029-M03_OUTPUT.json`

---

### M04: EvidenceChain 完整证据链（GPT §10）

**目的**: GPT §10 要求"每个事件保存完整证据链，不能只保存 AI 判断结果"。

**现有代码参考**:
- `models.py` 的 `ViolationEvidence` 表 — 已有 `plate_number/plate_confidence/ai_trace` 等字段
- `image_recognizer.py` 的 `ai_trace v3` — `{yolo, doubao, deepseek, final}` 嵌套结构

**GPT 要求的证据链**:
```
摄像头ID → 时间 → 地点 → 车辆ID → 车辆类型 → 车道 → 信号灯状态
→ 车辆轨迹 → 停止线关系 → 关键帧 → 事件视频
→ 本地规则判断结果 → 云端AI判断结果 → AI置信度 → AI分析说明 → 最终事件状态
```

**执行步骤**:

1. 新建文件 `e:\output\1\api\evidence_chain.py`

2. 实现 `EvidenceChain` 类：
   ```python
   @dataclass
   class EvidenceChain:
       """完整证据链 — 事件级别的完整上下文
       
       比 ai_trace v3（单帧AI判断）更丰富，包含事件全过程证据。
       ai_trace v3 作为其中的 ai_judgment 字段嵌入。
       """
       # 基础信息
       camera_id: str                    # 摄像头 ID
       timestamp: str                   # 事件时间 ISO8601
       location: str                     # 事件地点
       
       # 车辆信息
       vehicle_id: int                   # track_id
       vehicle_type: str                 # 车辆类型（car/truck/bus/motorcycle）
       plate_number: str                 # 车牌号
       plate_color: str                 # 车牌颜色
       lane_id: str                      # 车道 ID（如有）
       
       # 场景上下文
       traffic_light_state: str         # 信号灯状态（red/green/yellow）
       stop_line_relation: str          # 停止线关系（before/after/crossing）
       trajectory: list                  # 轨迹点序列 [(x, y, timestamp)]
       
       # 视觉证据
       key_frames: list                  # 关键帧路径列表
       event_video_path: str             # 事件视频路径
       
       # 判断结果
       rule_judgment: dict               # 本地规则判断结果
       ai_judgment: dict                 # 云端 AI 判断结果（嵌入 ai_trace v3）
       ai_confidence: float              # AI 置信度
       ai_explanation: str               # AI 分析说明
       
       # 最终状态
       final_status: str                 # 最终事件状态
       
       def to_dict(self) -> dict:
           """输出完整证据链字典"""
       
       def to_json(self) -> str:
           """输出 JSON 字符串"""
       
       def summary(self) -> str:
           """输出人类可读摘要（用于 Web 展示）"""
   ```

3. 实现从 `TrafficEvent` 到 `EvidenceChain` 的转换方法：
   ```python
   @staticmethod
   def from_traffic_event(event: TrafficEvent, camera_id: str = "default") -> EvidenceChain:
       """从 TrafficEvent 构建完整证据链"""
   ```

4. 数据库迁移：在 `models.py` 的 `ViolationEvidence` 表增加字段（或新建 `traffic_events` 表）：
   - 如果新建表，需要包含：`event_id`, `state`, `event_type`, `trajectory(JSON)`, `key_frames(JSON)`, `event_video_path`, `rule_judgment(JSON)`, `ai_explanation`, `evidence_chain(JSON)`, `state_history(JSON)`
   - 迁移脚本：修改 `migrate_db.py` 增加 ALTER TABLE 或 CREATE TABLE

5. 单元测试：新建 `e:\output\1\tests\test_evidence_chain.py`

**验收标准**:
- [ ] `EvidenceChain` 包含 GPT §10 要求的全部 15 个证据字段
- [ ] `from_traffic_event` 能从 TrafficEvent 正确构建证据链
- [ ] `to_dict` / `to_json` / `summary` 三个输出方法可用
- [ ] ai_trace v3 作为 ai_judgment 字段嵌入（不破坏现有结构）
- [ ] 数据库迁移脚本安全（不破坏现有数据）
- [ ] 单元测试 ≥ 5 个通过
- [ ] Python AST 语法验证通过

**输出文件**: `e:\output\_TASK-029-M04_OUTPUT.json`

---

### M05: CloudAI 按需调用改造（GPT §8）

**目的**: GPT §8 要求"云端 AI 不持续处理整个视频流，只在事件引擎触发疑似事件后才提交分析"。

**现有代码参考**:
- `cloud_collaborator.py` — `CloudCollaborator` 类，现有按帧调用模式
- `image_recognizer.py` — `analyze_with_doubao` / `analyze_with_deepseek_judge`
- 现有 ai_trace v3 结构：`{yolo, doubao, deepseek, final}`

**核心变化**: 从"按帧分析"改为"按事件分析"，输入从"单张图片"变为"事件视频+关键帧+轨迹+结构化上下文"。

**执行步骤**:

1. 在 `cloud_collaborator.py` 的 `CloudCollaborator` 类中新增方法：
   ```python
   def analyze_event(self, event_clip_frames: list, key_frames: list, 
                      vehicle_info: dict, scene_context: dict,
                      event_type: str, trajectory: list) -> dict:
       """按事件分析 — 云端 AI 只在事件触发后调用
       
       Args:
           event_clip_frames: 事件视频帧序列（extract_event_clip 返回值）
           key_frames: 关键帧列表（numpy ndarray）
           vehicle_info: 车辆信息（type/bbox/plate_number）
           scene_context: 场景上下文（traffic_light/lane/stop_line）
           event_type: 事件类型（red_light/wrong_way/...）
           trajectory: 车辆轨迹点序列
       
       Returns:
           ai_trace v3 嵌套结构：
           {
             "version": "v3",
             "yolo": { ... },
             "doubao": { "confidence": min(val/100.0, 1.0), ... },
             "deepseek": { ... },
             "final": {
               "judgment": "confirmed/rejected/uncertain",
               "confidence": 0.85,
               "explanation": "...",
               "risk_flag": false
             }
           }
       """
   ```

2. 关键实现点：
   - 从事件视频帧序列中选取最具代表性的 3-5 帧作为关键帧送云端
   - 将结构化上下文（轨迹/信号灯/车道）作为文本 prompt 附加到图片分析中
   - 豆包先分析 → DeepSeek 二级验证（保持现有 ai_trace v3 嵌套结构）
   - **AI 必须允许返回"无法确认"**（GPT §7 原则）
   - 豆包置信度必须 `min(val/100.0, 1.0)` 转换（硬约束 #5）

3. 不删除现有的 `analyze_frame` 方法（保持兼容），只新增 `analyze_event`

4. 增加日志：记录每次事件分析的输入帧数/输出结果/耗时

**验收标准**:
- [ ] `analyze_event` 方法完整实现
- [ ] 输入参数包含 GPT §8 要求的全部内容（事件视频/关键帧/轨迹/信号灯/车道）
- [ ] 输出保持 ai_trace v3 嵌套结构
- [ ] AI 可返回"无法确认"（uncertain）状态
- [ ] 豆包置信度转换正确 `min(val/100.0, 1.0)`
- [ ] DeepSeek 作为二级验证器
- [ ] 不删除现有 `analyze_frame` 方法
- [ ] Python AST 语法验证通过

**输出文件**: `e:\output\_TASK-029-M05_OUTPUT.json`

---

### M06: realtime_detector 集成循环缓存+事件引擎（GPT §11）

**目的**: GPT §11 要求"将现有违法抓拍功能逐步从'视频→AI→违法'改造成'视频→本地感知→事件触发→事件视频→云端AI复核→违法事件'"。

**现有代码参考**:
- `realtime_detector.py` — `RealtimeViolationDetector` 类
  - `_detection_loop` — 检测循环（第 164 行）
  - `process_frame` — 帧处理（第 236 行）
  - `frame_cache` — 现有 10 帧 deque（第 57 行，太短）
- `_push_violation_event` — 现有违规事件推送

**执行步骤**:

1. 在 `RealtimeViolationDetector.__init__` 中增加：
   ```python
   # GPT 升级：循环缓存 + 事件引擎
   self.frame_buffer = CircularFrameBuffer(
       duration_sec=Config.FRAME_BUFFER_DURATION,
       fps=Config.FRAME_BUFFER_FPS
   )
   self.event_engine = TrafficEventEngine(
       rule_plugins=self.plugin_loader.get_active_plugins() if hasattr(self, 'plugin_loader') else [],
       frame_buffer=self.frame_buffer
   )
   self.active_events = {}  # event_id → TrafficEvent
   ```

2. 在 `_detection_loop` 中增加帧缓存写入：
   - 在现有 `self.frame_cache.append(frame.copy())` 之后（或替代）：
   ```python
   # GPT 升级：写入循环缓存
   self.frame_buffer.add(time.time(), frame, {
       'detections': detections,
       'tracked_vehicles': self.tracked_vehicles,
       'scene_config': self.scene_config
   })
   ```

3. 在 `process_frame` 末尾增加事件引擎调用：
   ```python
   # GPT 升级：调用事件引擎
   new_events = self.event_engine.process_frame(
       frame, detections, self.tracked_vehicles, self.scene_config
   )
   for event in new_events:
       self.active_events[event.event_id] = event
       # 触发事件视频提取
       clip = self.frame_buffer.extract_event_clip(
           event.trigger_time,
           Config.EVENT_CLIP_BEFORE_SEC,
           Config.EVENT_CLIP_AFTER_SEC
       )
       # 保存事件视频
       video_path = self.frame_buffer.save_event_video(
           clip, f"output/event_videos/{event.event_id}.mp4"
       )
       event.event_video_path = video_path
       # 提交云端 AI 分析
       ai_result = self.cloud_collaborator.analyze_event(...)
       self.event_engine.apply_ai_result(event.event_id, ai_result)
   ```

4. 在 `get_status` 方法中增加事件相关状态：
   ```python
   'active_events': len(self.active_events),
   'event_engine': {
       'total_events': ...,
       'pending_ai': ...,
       'confirmed': ...,
       'rejected': ...
   }
   ```

5. 不删除现有逻辑（多帧确认/违规检测/推送），新的事件引擎是**叠加层**

**验收标准**:
- [ ] `CircularFrameBuffer` 正确集成到 `__init__` 和 `_detection_loop`
- [ ] `TrafficEventEngine` 正确集成到 `process_frame`
- [ ] 事件触发后自动提取视频+保存+提交AI
- [ ] `get_status` 返回事件引擎状态
- [ ] 现有功能（YOLO检测/多帧确认/违规推送/数字孪生）不受影响
- [ ] Python AST 语法验证通过
- [ ] 后端启动无报错（`py -3 -m uvicorn app:app --port 8001` 启动 3 秒内无异常）

**输出文件**: `e:\output\_TASK-029-M06_OUTPUT.json`

---

### M07: API 路由 + 数据库迁移

**目的**: 为交通事件系统提供 API 接口和数据库存储。

**现有代码参考**:
- `routers/realtime.py` — 已有 `/api/realtime/status` / `/source` / `/plugins` / `/tracking` / `/ptz` / `/carla` 等路由
- `models.py` — `ViolationEvidence` 表
- `database.py` — SQLAlchemy 引擎管理

**执行步骤**:

1. 数据库迁移：在 `migrate_db.py` 中增加 `traffic_events` 表创建：
   ```sql
   CREATE TABLE IF NOT EXISTS traffic_events (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       event_id VARCHAR(64) UNIQUE NOT NULL,
       event_type VARCHAR(50) NOT NULL,
       track_id INTEGER,
       state VARCHAR(20) NOT NULL DEFAULT 'detecting',
       trigger_time DATETIME,
       vehicle_info TEXT,        -- JSON
       scene_context TEXT,        -- JSON
       trajectory TEXT,           -- JSON
       key_frames TEXT,           -- JSON (路径列表)
       event_video_path VARCHAR(255),
       rule_judgment TEXT,        -- JSON
       ai_judgment TEXT,          -- JSON (ai_trace v3)
       ai_confidence FLOAT,
       ai_explanation TEXT,
       evidence_chain TEXT,      -- JSON (完整证据链)
       state_history TEXT,       -- JSON
       camera_id VARCHAR(50) DEFAULT 'default',
       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
       updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. 在 `models.py` 中增加 `TrafficEventRecord` ORM 类（对应上述表）

3. 在 `routers/realtime.py` 中增加事件路由：
   | 方法 | 路径 | 说明 |
   |------|------|------|
   | GET | `/api/realtime/events` | 事件列表（分页+状态筛选） |
   | GET | `/api/realtime/events/{event_id}` | 事件详情（含证据链） |
   | GET | `/api/realtime/events/{event_id}/video` | 事件视频文件 |
   | GET | `/api/realtime/events/{event_id}/frames` | 事件关键帧列表 |
   | POST | `/api/realtime/events/{event_id}/review` | 人工复核（CONFIRMED/REJECTED） |
   | GET | `/api/realtime/events/active` | 当前活跃事件列表 |

4. 事件视频文件服务：配置 StaticFiles 挂载 `output/event_videos/` 目录

**验收标准**:
- [ ] `traffic_events` 表创建成功（迁移脚本运行无报错）
- [ ] 6 个 API 路由全部注册（FastAPI /docs 可见）
- [ ] `GET /api/realtime/events` 返回分页列表（支持 `?state=confirmed&page=1&size=20`）
- [ ] `GET /api/realtime/events/{id}` 返回完整证据链 JSON
- [ ] `GET /api/realtime/events/{id}/video` 返回视频文件
- [ ] `POST /api/realtime/events/{id}/review` 能更新事件状态
- [ ] 不破坏现有路由
- [ ] Python AST 语法验证通过

**输出文件**: `e:\output\_TASK-029-M07_OUTPUT.json`

---

### M08: Web 端交通事件中心（GPT §15.1）

**目的**: GPT §15.1 要求新增"交通事件中心"页面，展示事件全过程。

**现有代码参考**:
- `web-admin/src/views/Violations.vue` — 现有违规列表页
- `web-admin/src/views/ViolationDetail.vue` — 现有违规详情页
- `web-admin/src/views/RealTimeMonitor.vue` — 实时监控页
- `web-admin/src/views/AITrace.vue` — AI 追踪页

**执行步骤**:

1. 新建 `web-admin/src/views/EventCenter.vue`（交通事件中心列表页）：
   - 事件列表表格：时间 / 摄像头 / 类型 / 车辆 / 状态（带颜色标签）/ AI置信度
   - 状态筛选下拉：全部 / 检测中 / 已触发 / 录制中 / 待AI分析 / AI已分析 / 已确认 / 已排除 / 待人工复核
   - 点击行跳转详情页
   - 分页

2. 新建 `web-admin/src/views/EventDetail.vue`（事件详情页）：
   - **事件视频播放器**（`<video>` 标签播放事件视频）
   - **关键帧画廊**（多张关键帧图片横向排列）
   - **证据链时间线**（从检测→触发→录制→AI分析→确认的全过程）
   - **车辆信息卡片**（车牌/类型/车道/轨迹折线图）
   - **场景上下文**（信号灯状态/停止线关系）
   - **AI 分析结果**（ai_trace v3 展示，复用 AITrace.vue 的展示逻辑）
   - **人工复核按钮**（确认违法 / 排除事件）

3. 在 `web-admin/src/router/index.js` 中注册路由：
   - `/events` → EventCenter.vue
   - `/events/:id` → EventDetail.vue

4. 在侧边栏菜单中增加"交通事件中心"入口

**验收标准**:
- [ ] EventCenter.vue 事件列表页正常渲染
- [ ] EventDetail.vue 包含视频播放器+关键帧画廊+证据链时间线+车辆信息+AI结果
- [ ] 人工复核按钮可调用 `POST /api/realtime/events/{id}/review`
- [ ] 状态筛选和分页功能正常
- [ ] 路由注册成功（`/events` 和 `/events/:id` 可访问）
- [ ] 侧边栏菜单增加入口
- [ ] `npx vite build` 构建通过（exit code 0）
- [ ] 图标校验通过（`node scripts/verify-icons.cjs` 无缺失）

**输出文件**: `e:\output\_TASK-029-M08_OUTPUT.json`

---

### M09: 集成测试 + 闭环验证（GPT §21）

**目的**: GPT §21 要求"最终能够完成完整的交通事件闭环"。

**验证闭环**:
```
读取交通视频 → 本地 YOLO 检测 → 车辆跟踪 → 根据规则发现疑似交通事件
→ 从循环缓存中提取事件前后视频 → 创建交通事件对象
→ 调用云端 AI 分析 → 保存完整分析结果 → Web 端查看事件
```

**执行步骤**:

1. 集成自检脚本（Python）：
   - CircularFrameBuffer 基本功能
   - TrafficEventEngine 事件创建+状态转换
   - EvidenceChain 从事件构建
   - CloudCollaborator.analyze_event 接口存在性
   - RealtimeViolationDetector 集成检查
   - API 路由注册检查
   - 数据库表存在检查

2. 端到端验证（使用 CARLA 或视频文件）：
   - 启动 CARLA（或使用测试视频）
   - 启动后端 API
   - 前端访问 `/events` 页面
   - 触发一个违规事件（如闯红灯）
   - 验证：
     - [ ] 事件被创建（状态 TRIGGERED → RECORDING → PENDING_AI → AI_REVIEWED → CONFIRMED）
     - [ ] 事件视频文件生成
     - [ ] 关键帧保存
     - [ ] 前端 EventCenter 列表显示该事件
     - [ ] 前端 EventDetail 能播放视频+查看证据链

3. 更新交接报告：
   - 按交接报告第十六章规则，追加任务执行记录
   - 更新第十五章 GPT 建议实施进度表
   - 更新第五章待办事项

**验收标准**:
- [ ] 集成自检 7/7 通过
- [ ] 事件生命周期完整经历（至少 TRIGGERED → CONFIRMED 或 REJECTED）
- [ ] 事件视频文件生成且可播放
- [ ] 前端列表和详情页正常显示
- [ ] 交接报告已更新（第十六章任务执行记录 + 第十五章进度表）
- [ ] 总报告 `_TASK-029_OUTPUT.json` 生成

**输出文件**: `e:\output\_TASK-029-M09_OUTPUT.json` + `e:\output\_TASK-029_OUTPUT.json`

---

## 三、GPT 明确禁止的事项（不能做）

执行者在任何子任务中**不得**：

1. ❌ 自己从零训练大型视频理解模型（GPT §17.1）
2. ❌ 全天候将完整视频发送到云端 AI（GPT §17.3）
3. ❌ 使用一个大模型负责所有交通判断（GPT §17.4）
4. ❌ 直接控制真实交通信号灯（GPT §17.5）
5. ❌ 为每个功能单独创建一个 AI 模型（GPT §17.7）
6. ❌ 在没有真实数据支撑下设计过度复杂的算法（GPT §17.8）
7. ❌ 删除现有违法判断模块（GPT §11："不能直接删除"）
8. ❌ 在未分析现有代码的情况下强行创建重复模型（GPT §4.2）

---

## 四、硬约束提醒（与 TASK-028 相同，仍然有效）

1. API Key 不硬编码（`config_runtime.json` 或环境变量）
2. 后端端口 8001 + 前端端口 5173
3. Python 用 `py -3`
4. ai_trace v3 嵌套结构不变
5. DeepSeek 二级验证不变
6. 实时监控画面用 getUserMedia
7. graceful degradation（所有外部资源连不上返回空不报错）
8. 每个子任务 OUTPUT 文件包含 feedback 字段（project_suggestions ≥ 1 / commander_suggestions ≥ 2 / dissent / suggestions_adopted）
9. 每次任务完成后更新交接报告 `e:\output\PROJECT_HANDOVER_REPORT.md`（新规！第十六章）

---

## 五、文件索引（本任务涉及的全部文件）

### 新建文件
| 文件 | 子任务 | 说明 |
|------|--------|------|
| `api/circular_frame_buffer.py` | M02 | 视频循环缓存 |
| `api/traffic_event_engine.py` | M03 | 交通事件引擎+状态机 |
| `api/evidence_chain.py` | M04 | 完整证据链 |
| `tests/test_circular_frame_buffer.py` | M02 | 缓存单元测试 |
| `tests/test_traffic_event_engine.py` | M03 | 事件引擎单元测试 |
| `tests/test_evidence_chain.py` | M04 | 证据链单元测试 |
| `web-admin/src/views/EventCenter.vue` | M08 | 事件中心列表页 |
| `web-admin/src/views/EventDetail.vue` | M08 | 事件详情页 |
| `docs/project_analysis_gpt_upgrade.md` | M01 | 项目分析报告 |

### 修改文件
| 文件 | 子任务 | 修改内容 |
|------|--------|---------|
| `api/config.py` | M02 | 增加缓存配置参数 |
| `api/cloud_collaborator.py` | M05 | 新增 `analyze_event` 方法 |
| `api/realtime_detector.py` | M06 | 集成缓存+事件引擎 |
| `api/models.py` | M07 | 新增 TrafficEventRecord ORM |
| `api/migrate_db.py` | M07 | 新增 traffic_events 表迁移 |
| `api/routers/realtime.py` | M07 | 新增 6 个事件路由 |
| `api/app.py` | M07 | 挂载事件视频静态文件 |
| `web-admin/src/router/index.js` | M08 | 注册事件路由 |
| `web-admin/src/layout/` 侧边栏 | M08 | 增加菜单入口 |
| `e:\output\PROJECT_HANDOVER_REPORT.md` | M09 | 更新交接报告 |

---

## 六、验收标准总表

| 子任务 | 核心验收点 | 验证方式 |
|--------|-----------|---------|
| M01 | 分析报告覆盖 GPT §19 全部 12 项 | 人工审查 |
| M02 | CircularFrameBuffer 7 方法+6 测试 | `py -3 -m pytest` |
| M03 | EventState 8 状态+EventEngine 8 方法+8 测试 | `py -3 -m pytest` |
| M04 | EvidenceChain 15 字段+from_traffic_event+5 测试 | `py -3 -m pytest` |
| M05 | analyze_event 保持 ai_trace v3 结构 | AST + 接口检查 |
| M06 | realtime_detector 集成无报错 | AST + 启动检查 |
| M07 | 6 路由+表创建+StaticFiles | `/docs` + 迁移脚本 |
| M08 | 2 新页面+路由+构建通过 | `npx vite build` |
| M09 | 闭环验证 7/7+前端展示 | 集成自检脚本 |

**总验收**: 9/9 子任务全部 PASS = TASK-029 PASS

---

*本通知文件基于 GPT《灵瞳智声项目架构升级技术需求说明.docx》22 章节制定。执行者必须先读交接报告第十五章（GPT 创新点）再开始执行。*
