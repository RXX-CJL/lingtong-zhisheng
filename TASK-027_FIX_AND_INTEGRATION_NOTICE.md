# TASK-027 修复与集成

> **指挥官交接说明**：TASK-026 大部分完成但有遗留问题：M4 前端构建失败（Volume2图标不存在），M5 只创建了模块但未集成到主系统，OUTPUT 缺少 feedback 字段。本任务修复这些问题，确保能跑起来。

---

## 0. 协作规则

### 0.1 基本规则

1. **Git 优先复用**：搜方案先 GitHub Skill，降级需报备
2. **禁止降级方案**：遇到问题换更好的方案，不许将就
3. **真实浏览器验证**：前端修改必须在用户真实 Edge 浏览器验证
4. **自主决策权**：用户已休息，无需请示
5. **VPN 已开启**
6. **项目根目录**：`e:\output\1`
7. **结果输出**：`_TASK-027_OUTPUT.json` / `_TASK-027_ERROR.json` 到 `e:\output\`
8. **能力优先使用规则（强制）**：执行任何任务前，必须对照 `project_memory.md` 中的"工作流能力优先级"清单，按优先级从高到低选择工具。

### 0.2 协作监督机制（战友关系）

**核心理念**：指挥官与执行者是共同协作的战友关系，不是上下级关系。双方互相监督、互相建议、共同成长。

---

## 1. 任务清单

### M1: 修复前端构建失败
- **优先级**：最高（阻塞所有前端功能）
- **问题**：RealTimeMonitor.vue 构建报错 `"Volume2" is not exported by @element-plus/icons-vue`
- **错误位置**：[RealTimeMonitor.vue:238](file:///e:/output/1/web-admin/src/views/RealTimeMonitor.vue#L238)
- **操作步骤**：
  1. 用 **SearchCodebase** 或 Grep 找出所有引用 Volume2 的地方
  2. 查 @element-plus/icons-vue 中正确的音量关闭图标名（可能是 `Bell`、`Mute`、`Microphone` 或其他）
     - **强制用 GitHub Skill** 搜 element-plus icons 文档或源码确认正确名称
  3. 替换错误的图标名
  4. 运行 `npx vite build` 验证构建成功
- **必须 MCP/Skill**：GitHub Skill（查图标名）+ Grep + Edit + vite build
- **降级规则**：GitHub Skill 不可用时立即通知指挥官
- **验收标准**：
  1. `npx vite build` 构建成功，exit code 0
  2. 所有图标正常显示
  3. 前端页面可正常访问

### M2: 集成 BehaviorEngine 到 RealtimeDetector
- **优先级**：最高（M5 的核心缺失）
- **背景**：TASK-026 创建了 [behavior_engine.py](file:///e:/output/1/api/behavior_engine.py) 和 [vehicle_tracker.py](file:///e:/output/1/api/vehicle_tracker.py)，但没有集成到 [realtime_detector.py](file:///e:/output/1/api/realtime_detector.py) 中。模块造好了但没装上车。
- **操作步骤**：
  1. 读取 realtime_detector.py 完整代码，理解现有架构
     - 第27行：`from violation_rules import check_violations, ViolationRuleEngine, VIOLATION_TYPE_CN`
     - 第39行：`self.violation_engine = ViolationRuleEngine()`
  2. 在 `__init__` 中初始化 BehaviorEngine 和 VehicleTracker
     - 默认使用质心追踪（确保向后兼容）
     - ByteTrack 作为可选（依赖不存在时自动降级）
  3. 修改 `process_frame` 方法（或等价的核心检测方法）：
     - 先 YOLO 检测 → 再 VehicleTracker 跟踪 → 再 BehaviorEngine 分析行为
     - 保留原有 ViolationRuleEngine 作为单帧检测的补充
     - 行为分析结果和违规检测结果合并输出
  4. 确保 `get_annotated_frame` 中绘制：
     - 识别框（已有）
     - 追踪 ID（新增，显示在框上方）
     - 行为标签（如"逆行"、"超速"，红色标注）
  5. 更新 WebSocket 推送数据，包含追踪信息和行为分析结果
  6. 写一个简单测试脚本验证集成效果
- **必须 MCP/Skill**：Read + Edit + Grep + systematic-debugging Skill
- **验收标准**：
  1. realtime_detector.py 成功 import BehaviorEngine 和 VehicleTracker
  2. Python 语法检查通过
  3. 启动后端不报错
  4. 追踪 ID 在识别框上正确显示
  5. 行为分析结果正确输出

### M3: 更新 realtime 路由接口
- **优先级**：高
- **操作步骤**：
  1. 读取 [routers/realtime.py](file:///e:/output/1/api/routers/realtime.py)
  2. 添加行为分析相关接口（如需要）：
     - GET /realtime/tracked_vehicles — 获取当前追踪车辆列表
     - GET /realtime/behavior_stats — 获取行为分析统计
  3. 确保现有接口（start、stop、snapshot、status）返回数据包含追踪和行为信息
  4. Python 语法检查通过
- **必须 MCP/Skill**：Read + Edit + Grep
- **验收标准**：
  1. 所有新接口可访问
  2. 现有接口向后兼容
  3. Python 语法检查通过

### M4: 更新前端实时监控页面
- **优先级**：高
- **操作步骤**：
  1. 读取 RealTimeMonitor.vue
  2. 添加追踪 ID 显示（从 WebSocket 数据中读取 track_id 显示在识别框上）
  3. 添加行为标签显示（如果检测到违规行为，显示行为类型中文标签）
  4. 确保参数调节（置信度、IOU阈值）功能正常工作
  5. 前端构建成功
- **必须 MCP/Skill**：frontend-design Skill + Edit + Chrome DevTools MCP 验证
- **验收标准**：
  1. 追踪 ID 显示在识别框上方
  2. 行为标签正确显示
  3. 前端构建成功
  4. 在真实 Edge 浏览器中验证通过

### M5: 验证完整流程 & 清理临时文件
- **优先级**：高
- **操作步骤**：
  1. 启动后端服务
  2. 启动前端
  3. 打开摄像头进行实时检测
  4. 验证以下功能：
     - 摄像头画面正常显示
     - YOLO 识别框显示（中文标签）
     - 追踪 ID 显示
     - 行为检测逻辑运行（即使没有违规行为，也要确认不报错）
     - WebSocket 数据推送正常
     - 参数调节生效
  5. 清理所有临时文件、测试文件
  6. 更新 OUTPUT 文件，添加完整的 feedback 字段
- **必须 MCP/Skill**：Chrome DevTools MCP + systematic-debugging Skill
- **验收标准**：
  1. 完整流程跑通，无报错
  2. 所有功能正常工作
  3. 临时文件已清理
  4. OUTPUT 包含完整 feedback 字段

---

## 2. 统一要求

1. **每个子任务完成**：
   - 写 `_TASK-027-MXX_OUTPUT.json` 或 `_TASK-027-MXX_ERROR.json`
   - OUTPUT 必须包含：task, timestamp, status, details, deviations, feedback
   - ERROR 必须包含：task, failed_at, error_text（完整 stack trace）, recommendation, feedback

2. **任务顺序**：M1 → M2 → M3 → M4 → M5（严格顺序，前一个不过后面做不了）

3. **高危操作**：默认同意，无需请示

4. **报告指挥官**：每个子任务完成后报告 OUTPUT 文件路径 + 状态

5. **任务后清理**：执行完所有任务后，清理临时文件

### 执行者反馈与建议模板（强制，每个 OUTPUT 必须包含）

```json
"feedback": {
  "skills_used": ["frontend-design", "chrome-devtools", "..."],
  "skills_effect": "简述各 Skill 实际效果，哪些有帮助，哪些没用",
  "project_suggestions": "对项目技术方向、架构、代码质量的建议",
  "commander_suggestions": "对指挥官任务拆解、优先级、沟通方式的建议",
  "difficulties": "遇到的困难，需要什么支持",
  "dissent": "对指挥官决策的异议（如有），无则填 null"
}
```

> **注意**：feedback 字段不可省略，即使没有建议也要填 "无"。禁止"只执行不思考"。上次 TASK-026 漏掉了 feedback，这次必须补上。

---

## 3. 验收标准

- [ ] M1 前端构建成功（vite build exit code 0）
- [ ] M2 BehaviorEngine 集成到 realtime_detector.py
- [ ] M3 realtime 路由接口更新
- [ ] M4 前端显示追踪 ID 和行为标签
- [ ] M5 完整流程验证通过
- [ ] 每个子任务 OUTPUT 包含 feedback 字段
- [ ] 临时文件已清理
- [ ] 严格遵守能力优先使用规则

---

## 4. 关键文件路径

- 项目根：`e:\output\1`
- 项目记忆：`c:\Users\ROG\.trae-cn\memory\projects\-e-output\project_memory.md`
- 后端入口：`e:\output\1\api\main.py`
- 实时检测器：`e:\output\1\api\realtime_detector.py`
- 行为引擎：`e:\output\1\api\behavior_engine.py`
- 车辆追踪器：`e:\output\1\api\vehicle_tracker.py`
- 实时路由：`e:\output\1\api\routers\realtime.py`
- 前端实时监控：`e:\output\1\web-admin\src\views\RealTimeMonitor.vue`
- TASK-026 分析文档：`e:\output\1\docs\`

---

## 5. 指挥官工作报告

> 本节是指挥官向执行者说明自己做了什么，用了什么技能，对难题的建议。让执行者了解指挥官的工作，形成双向透明。

### 已做工作
1. **TASK-026 验收校验**：读取主 OUTPUT 文件 + 5个子文件，逐个验证
2. **前端构建诊断**：运行 `npx vite build` 定位错误，确认是 `Volume2` 图标不存在
3. **集成度检查**：Grep 确认 behavior_engine 和 vehicle_tracker 未被 realtime_detector 引用
4. **任务拆解**：将"修复+集成"拆成 5 个顺序子任务
5. **战友反馈机制检查**：发现 TASK-026 OUTPUT 缺少 feedback 字段

### 使用技能
- **Read**：读取 OUTPUT 文件、代码文件、文档
- **Grep**：验证集成情况（realtime_detector.py、routers/realtime.py、violation_rules.py）
- **Glob**：查找文件是否存在
- **RunCommand**：运行 vite build 和 Python 语法检查
- **Edit/Write**：生成任务通知
- **分析与规划**：问题定位、任务拆解、优先级排序

### 难题建议
1. **前端图标错误**：Volume2 不存在。建议用 GitHub Skill 搜 element-plus/icons-vue 的 dist/index.js 或文档，确认正确的音量关闭图标名。可能的正确名称：`Bell`、`Mute`、`MicrophoneOff`、`Aim` 等，但别猜，一定要查清楚。

2. **集成 BehaviorEngine 到 realtime_detector.py**：
   - 别一上来就大改 process_frame，先加 import 和初始化，确保不破坏现有功能
   - 用 try-except 包裹 BehaviorEngine 的调用，失败了不影响原有检测
   - 追踪 ID 绘制要和现有的识别框绘制逻辑融合，别重复画框
   - 建议先在现有 `get_annotated_frame` 方法基础上添加追踪 ID 文字，再逐步加行为标签

3. **向后兼容最重要**：
   - 现有 ViolationRuleEngine 不能删，要保留作为单帧检测
   - BehaviorEngine 是增强，不是替代
   - VehicleTracker 默认用质心追踪（不依赖外部库），ByteTrack 是可选增强
   - 所有新功能都要 graceful degradation（优雅降级）

4. **测试策略**：
   - 不要等全部改完才测试
   - M2 改完先跑 Python 语法检查 + 简单 import 测试
   - M4 改完先跑 vite build
   - M5 再做完整的端到端测试

### 决策依据
- **为什么 M1 优先级最高**：前端构建都过不了，后面的前端改动都没法验证。必须先修好基础。
- **为什么是顺序任务不是并行**：M2 是 M3 的基础，M3 是 M4 的基础，M4 是 M5 的基础，环环相扣，没法并行。
- **为什么保留 ViolationRuleEngine**：BehaviorEngine 需要轨迹数据（多帧），单帧图片上传检测（如举报照片）还是需要 ViolationRuleEngine。两者是互补关系，不是替代关系。
- **为什么强调 graceful degradation**：我们吃过很多"改完一个功能崩了另一个"的亏。增量集成、优雅降级，比一次性大改要稳得多。

### 指挥官对 TASK-026 的反思
- 验收标准不够严格，只查了"文件存不存在"，没查"有没有集成到主系统"
- 没有强制要求 vite build 通过作为 M4 的验收条件
- feedback 字段的验收标准写在了统一要求里，但没在验收标准清单里重复，导致执行者可能漏了
- 这次 TASK-027 会把这些漏洞补上

### 指挥官对自己的反思
- 之前 TASK-026 的任务设计有缺陷，把"创建模块"和"集成模块"放在同一个 M5 里，导致执行者只做了前半部分
- 应该更细粒度地拆解任务，每个任务有明确的可验证产出
- 战友反馈机制是新规则，第一次没执行到位很正常，这次强调一下就好

---

**任务通知版本**：v1.0
**生成时间**：2026-07-26
**指挥官**：TRAE Assistant
**执行者**：TRAE Sub-agent
**用户状态**：已休息，全权委托执行者自主决策
