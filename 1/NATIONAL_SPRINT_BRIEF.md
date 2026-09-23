# 智瞳灵声 · 冲击国家级 执行简报（最终版 · 双 AI 复核定稿）

> **文档定位**：面向"执行方 IDE / 编码智能体"的作战清单，基于**对真实代码的逐文件核查**（而非方案书构想）。
> **版本**：v2.0 最终版（2026-09-05）——由架构评审方初稿 + 豆包（字节跳动）独立代码复核，双方就异议点达成一致后定稿。
> **复核记录**：豆包的完整回应见 `NATIONAL_SPRINT_RESPONSE.md`；本版已吸收其全部有效更正（见 §6）。
> **指挥人**：项目架构评审 + 项目负责人
> **执行人**：IDE / 开发者（技术）+ 团队（商务/落地）
> **总目标**：结题前把"已具雏形的真实系统"打磨到 **中国国际大学生创新大赛 国家级可获奖** 的成色。
> **项目根目录**：`e:\output\1`

---

## 0. 给执行方 IDE 的阅读须知（务必先读）

### 0.1 核心策略（双方一致认可，作为全项目总纲）

> **"不是堆功能，而是做实 + 自证 + 落地。"**
> **"做深一个能自证的点，胜过吹六个做不出来的点。"**

项目已运行约 2 个月，工程**广度**在本科生中属上游（端-边-云-数字孪生-仿真-小程序-Web 全打通）。
距离国家级的差距**不在功能数量**，而在：

1. **跑不稳、演不了**：最新核心闭环（按事件云端分析）存在参数错位 bug，导致**静默降级失效**（详见 B1/B2）。
2. **无法自证**：方案书里的性能/准确率数据（TensorRT 15ms、82%→91%）**代码里无任何支撑**，评委一问即穿。
3. **安全与工程卫生差**：**12 处**明文密钥、无 `.gitignore`、小程序三套重复、数据库二进制入库、`beforeness/` 废弃目录。
4. **无真实落地**：没有真实试点/客户/数据。

### 0.2 硬性红线（执行时必须遵守）

- ❌ **禁止编造任何性能/准确率/试点数据**。写进材料的每个数字，必须由脚本**实测产出**并可复现（保留原始日志/截图）。
- ❌ **禁止删除现有可用模块**（检测/跟踪/行为/多帧/云端协作/事件引擎/前端）。改造以"叠加、修复"为主。
- ❌ **禁止把真实密钥写进任何被 git 跟踪的文件**（含 `.env.example`、文档、示例）。
- ❌ **禁止从零训练大型视频理解模型**（沿用现有 YOLOv8 + 云端大模型 API）。
- ✅ **禁止用"删掉 try/except"来让 B1/B2"不报错"**——那是优雅降级设计，必须保留；正解是**对齐参数让正常路径返回真实结果**（见 P0-1）。
- ✅ 每次改动后自问："这一改，让哪个**演示环节**或**真实指标**变得可自证了？"

### 0.3 最终任务优先级总览（已按双 AI 复核结论调整）

| 优先级 | 编号 | 主题 | 归属 | 工作量 |
|--------|------|------|------|--------|
| **P0 止血** | P0-1 | 修复事件闭环参数错位（B1/B2 静默降级） | IDE | 0.5-1 天 |
| | P0-2 | 清除 **12 处**明文密钥 + `.gitignore` + `.env`（B3/B4/B13） | IDE | 0.5-1 天 |
| | P0-3 | 端到端最小闭环跑通 + `event_videos` 真实产出 + demo 录屏（B6/B8） | IDE | 1-2 天 |
| **P1 自证** | P1-1 | 真实指标实测脚本 + `REAL_METRICS.md`（延迟/FPS/mAP，B5） | IDE | 3-5 天 |
| **P2 落地/对齐/加分** | P2-1a | 试点技术支撑：一键部署包 + 运行统计导出 | IDE | 2-3 天 |
| | P2-1b | 试点商务落地：真实场景 + 试用证明 + 现场数据 | **团队** | 结题前持续 |
| | P2-2 | 方案书与真实实现对齐 + 统一项目名（B9） | IDE+团队 | 2-3 天 |
| | P2-3 | 交通场景微调（**条件启动**：仅当 P1-1 显示准确率不足） | IDE | 视数据决定 |
| **P3 卫生** | P3-1 | 小程序：删/归档 2 套重复目录（低成本止血），完整统一视答辩重点 | IDE | 0.5 天起 |
| | P3-2 | logging 统一 / `beforeness/` 清理 / 第三方代码声明 / 过期报告清理 | IDE | 穿插 |

> **变更说明**（相对初稿）：原 P1-2 微调 → 降为 **P2-3 且条件启动**；原 P1-3 小程序 → 降为 **P3-1**；原 P2-1 试点 → **拆分为 P2-1a（IDE）/ P2-1b（团队）**。理由见 §6。

---

## 1. 项目真实现状快照（基于代码核查，非方案书）

### 1.1 真实已实现、代码质量可用的能力（你们的家底，材料就讲这些）

| 能力 | 真实实现位置 | 核查结论 |
|------|-------------|---------|
| YOLOv8 目标检测（多模型管理） | `api/image_recognizer.py`(2292行) | ✅ 真实，但仅用官方 `yolov8n.pt`，**未做交通场景微调** |
| 车辆跟踪 | `api/vehicle_tracker.py`(ByteTrack 封装 + 自定义回退) | ✅ 真实 |
| 行为分析（6+类违规） | `api/behavior_engine.py`(576行) | ✅ 真实：闯红灯/逆行/违停/超速/压线/未戴头盔/黄灯 |
| 多帧确认 | `api/multi_frame_validator.py`(window=10,confirm=5) | ✅ 真实，含 FPS 监控 |
| **端云三级协作仲裁** | `api/cloud_collaborator.py`(945行) | ✅ **真实且是最大亮点**：Claude 主 → 豆包兜底 → DeepSeek 二审，含分歧检测、ai_trace v3/v3.1、优雅降级 |
| **交通事件 8 状态机** | `api/traffic_event_engine.py`(381行) | ✅ 真实：DETECTING→TRIGGERED→RECORDING→PENDING_AI→AI_REVIEWED→CONFIRMED/REJECTED/MANUAL_REVIEW，含合法转换校验、冷却、状态历史 |
| 30s 循环缓存 + 事件视频提取 | `api/circular_frame_buffer.py`(177行) | ✅ 代码真实，但**尚未产出过真实事件视频**（受 B1/B2 拖累） |
| 证据链 | `api/evidence_chain.py`(170行) | ✅ 真实 |
| 插件化规则引擎（3 场景） | `api/rule_engine/`（traffic/urban_management/public_security，importlib 动态加载） | ✅ 真实 |
| 车牌识别 | `api/license_plate_recognizer.py` + `api/k230_plate_client.py` | ✅ 真实（PaddleOCR + K230 边缘车牌） |
| CARLA 仿真数据源 | `api/carla_source.py`(413行) + `carla/CARLA_0.9.16` | ✅ 真实，已接入 `realtime_detector.set_source` |
| K230 边缘端 app | `zhitong/k230_app/`（车牌/车辆检测+TTS+HTTP上传+WiFi） | ✅ 真实嵌入式工作 |
| Web 管理端 | `web-admin/`（Vue3，17 视图/15 路由） | ✅ **完整**：Dashboard/ViolationDetail(1548行)/RealTimeMonitor(1501行)/EventCenter/EventDetail(1120行)/AITrace/CollabStats 等 |
| 数字孪生 | `digital_twin/`（Flask+SocketIO+Three.js） | ✅ 真实：**轮询真实后端 `/api/realtime/status`、`/api/violations` 并经 WebSocket 推入 3D 场景** |
| 单元测试 | `tests/`（6 个：事件引擎/缓存/证据链/多帧/集成/core） | ✅ 覆盖新模块 |
| 真实运行痕迹 | `api/uploads/`(38 张违规证据图)、`api/zhitong_violations.db`(200KB) | ✅ 系统确实跑出过真实检测 |

> **一句话家底**：端云协同 + 事件级证据链闭环 + 多模型仲裁 + 数字孪生联动 + K230 边缘 + CARLA 仿真，**这套"全链路真打通"本身就是国家级可讲的故事**——前提是先修好 B1/B2 让事件闭环真正生效。

### 1.2 真实存在的问题（分级，均已代码核实）

#### 🔴 P0 级（致命：功能失效 / 泄密 / 演示失败）

| # | 问题 | 证据（文件:行） | 影响（**已按复核修正**） |
|---|------|----------------|------|
| B1 | **事件路径调用 Claude 参数数量错误** | `cloud_collaborator.py:_analyze_event_with_claude`(784) 用 3 参调用 `image_recognizer.py:1715 analyze_with_claude(image_input, violation_type)`（仅 2 参） | **静默降级失效**：调用触发 `TypeError`，但被 `try/except`(789) 捕获返回 `{}`。**服务不崩**，然而事件永远拿不到 Claude 真实仲裁结果 |
| B2 | **事件路径调用 DeepSeek 参数语义错位** | `_analyze_event_with_deepseek`(811) 传 `(result_text, event_type, context_prompt)`，但定义 `image_recognizer.py:1260 analyze_with_deepseek_judge(violation_type, yolo_result_dict, doubao_result_dict)` 需 `(类型, yolo字典, 豆包字典)`；异常被 `try/except`(813) 吞掉 | 二审入参错误 → 结果无意义或异常被吞 → `ai_trace.final.judgment` **始终走降级默认值**，隐蔽性比"崩溃"更强 |
| B3 | **明文 API Key 硬编码（12 处，非初稿的 4 处）** | 见 §4 完整清单：`api/config_runtime.json:3,10`、`api/image_recognizer.py:206`、`api/DEVELOPMENT_GUIDE.md:21,26`、`zhitong/config.py:50`、`zhitong/blind_yun.py:35`、`beforeness/{blind_yun.py:35, photo_ai_analysis.py:19, untitled_2.py:24}`、`项目问题记录文档.md:26,27` | 密钥泄露红线；6 月已标记至今未修 |
| B4 | **根目录无 `.gitignore`** | `git ls-files` 显示 `api/zhitong_violations.db` 已被跟踪 | 密钥/数据库/大文件（2.4GB torch wheel）易入库，仓库污染+泄密 |

> **B1/B2 结论修正**（采纳豆包复核）：不是"必崩"，而是"**静默降级导致事件 AI 仲裁失效**"——表面无报错、日志仅一条 warning，实则"事件级证据链"这一核心卖点**从未真正生效**，与 `api/output/event_videos/` 无任何视频产出互相印证。修复目标因此更明确：**让正常路径返回真实云端结果**，而非仅仅"不抛异常"。

#### 🟠 P1 级（影响可信度与演示）

| # | 问题 | 证据 | 影响 |
|---|------|------|------|
| B5 | 无任何真实指标产出脚本 | 无 mAP/FPS/延迟实测；`backend_evaluation_report.md` 是**对旧单文件原型的过期评估**(71.1分) | 材料里的性能数字全部无法自证 |
| B6 | 服务疑似无法持续运行 | `RUNTIME_ISSUES.md`：uvicorn/vite 启动后数十秒退出 | 无法端到端演示（需确认是否为 IDE 终端假象） |
| B8 | 事件闭环无端到端验证 | `api/output/event_videos/` 为空 | "事件级证据链"卖点无法现场演示 |

#### 🟡 P2/P3 级（工程卫生）

| # | 问题 | 证据 |
|---|------|------|
| B7 | 微信小程序三套重复页面 | `wechat-miniprogram/pages/`、`/miniprogram/pages/`、`/src/pages/` 并存（**负责人已表示小程序暂非本轮重点 → 降 P3，但至少删除重复目录避免"代码混乱"观感**） |
| B9 | 项目名不统一 | 代码/文档中"智瞳灵声"(5处) 与"灵瞳智声"(2处) 混用 |
| B10 | 部分模块用 `print()` 而非 logging | `app.py` 已用 RotatingFileHandler，其他模块不统一 |
| B11 | zhitong 体量虚高 | `zhitong/training/downloads/` 有 **63,877 行下载的第三方代码**，易被误认为原创 |
| B12 | CORS `allow_origins=["*"]`、SQLite 用于"生产" | `app.py:115`、`database.py` |
| **B13** | **`beforeness/` 废弃目录含明文密钥**（豆包补充发现） | `beforeness/{blind_yun.py, photo_ai_analysis.py, untitled_2.py, yolov8n.pt}`，3 个脚本各含 1 处 `sk-` key | 评审浏览仓库时易被质疑"代码混乱/泄密"，需确认废弃后归档删除 |

### 1.3 方案书 vs 真实实现 的偏差（结题前必须对齐方案书）

> 双方一致：**让方案书向真实实现对齐**，没做的删掉或降级为"规划中"，真做的放大。

| 方案书原宣称 | 真实情况 | 建议处理 |
|-------------|---------|---------|
| TensorRT 15ms/帧、66FPS、显存↓39% | `USE_TENSORRT=False`，**无任何 .engine 文件** | 要么 P1-1/P2-3 真做一次并实测，要么改为"规划中/预期" |
| YOLOv8「交通场景微调」 | 仅官方 COCO `yolov8n.pt` | 先由 P1-1 测真实 mAP；不足再启动 P2-3 微调，或改口径"COCO 预训练，微调视数据启动" |
| LSTM+GNN+Transformer 预测式治理 | **零实现** | 从方案书删除，或明确标注"下一阶段规划" |
| 四 Agent 协同决策 | 实为**多大模型串行仲裁**（Claude/豆包/DeepSeek） | **改口径**为真实且更强的"端云三级仲裁 + 事件状态机"，别硬套 Agent |
| 自进化持续学习（82%→91%） | **零实现** | 删除编造数据；可做"人工审核→标注沉淀"的**轻量真闭环** |
| 区块链存证 | **零实现** | 删除；用现有"证据链 + 状态历史 + 协作日志"讲"可追溯存证"即可 |

---

## 2. 执行任务清单（每任务含 目标/文件/步骤/验收/禁止）

> 约定：每个任务给出**可验收标准**。IDE 完成后自检，并在该任务下追加"✅ 完成记录（日期 + 证据路径 + 复现命令）"。

### 🔴 P0-1 修复事件闭环参数错位（B1/B2）——最高优先，决定"能不能演"

**目标**：让"按事件云端分析"闭环**真正返回有效结果**（而非静默降级），且**保留**优雅降级设计。

**涉及文件**：
- `api/cloud_collaborator.py`（`_analyze_event_with_claude`:765、`_analyze_event_with_deepseek`:793）
- `api/image_recognizer.py`（`analyze_with_claude`:1715、`analyze_with_deepseek_judge`:1260、`analyze_with_doubao`:997 的真实签名）

**步骤**：
1. 以 `image_recognizer.py` 三个云端函数的**真实签名与内部期望入参**为准。
2. 修 `_analyze_event_with_claude`：`analyze_with_claude` 只接受 `(image_input, violation_type)`。若必须传 `context_prompt`，**给被调函数增加可选参数** `context_prompt: str = ""`（而非在调用处多塞位置参数），并把事件上下文拼进 prompt；保持全项目调用一致。
3. 修 `_analyze_event_with_deepseek`：按定义传 `(event_type, yolo_result_dict, primary_visual_result_dict)`，把 `context_prompt` 并入 `yolo_result_dict` 或豆包结果 dict 的说明字段。
4. 全局搜索 `analyze_with_claude(`、`analyze_with_deepseek_judge(`、`analyze_with_doubao(`，确保**所有调用点签名一致**（违规路径 `consult_cloud` 已正确，勿改坏）。
5. **保留** 789/813 的 `try/except` 优雅降级（这是设计，不删）；修复只针对"正常路径的参数对齐"。
6. 在 `tests/` 新增 `test_cloud_collaborator_event.py`：mock 三个云端函数返回**可区分的真实结果**，断言 `analyze_event(...)` 走正常路径，且返回的 `ai_trace.final.judgment` **来源于真实云端结果而非降级默认值**（不联网）。

**验收标准**：
- [ ] mock 下 `analyze_event()` 不触发 `TypeError`，返回含**非降级** `final.judgment` 的 ai_trace（断言判定来源）。
- [ ] 全部云端函数调用点签名与被调定义一致（grep 复核）。
- [ ] 保留 try/except；人为制造真实异常时仍能优雅降级不崩。
- [ ] `pytest tests/test_cloud_collaborator_event.py -q` 通过。

**禁止**：❌ 删掉 try/except 来"消除报错"；❌ 用兜底默认值冒充真实结果通过测试。

> **✅ 完成记录（2026-09-05 · IDE 执行）**
>
> **改动文件与内容**：
> - `api/image_recognizer.py`：`analyze_with_claude`(1715) 与 `analyze_with_doubao`(997) 各新增**可选参** `context_prompt=""`（向后兼容，全部 2 参调用点不受影响），并把事件结构化上下文拼进各自 prompt——修复 B1，同时让此前"构建却被丢弃"的 `context_prompt` 真正送达主视觉模型。
> - `api/cloud_collaborator.py`：`_analyze_event_with_doubao`(755) 传入 `context_prompt`；`analyze_event`(659) 向二审传 `yolo_result`；`_analyze_event_with_deepseek`(793) 按 `analyze_with_deepseek_judge(violation_type, yolo_result_dict, doubao_result_dict)` 真实签名传 `(event_type, 构造的YOLO dict, primary_result dict)`，其中 YOLO dict 每项补 `confidence` 以避免 deepseek 内部 `KeyError`——修复 B2。**保留** 789/813 的 try/except 优雅降级。
> - 事件路径修复**镜像了违规路径本就正确的调用范式**（`cloud_collaborator.py:220-221 / 513-514`），未触碰违规路径。
>
> **验收对照**：
> - [x] mock 下 `analyze_event()` 不触发 TypeError，`ai_trace.claude.reasoning` / `deepseek.review_summary` 为真实结果、`final.judgment=confirmed`、`method=claude_plus_deepseek`、`evidence_count=2`（非降级）。
> - [x] DeepSeek 二审实参类型断言为 `(str, dict, dict)`。
> - [x] 全库调用点 grep 复核签名一致（claude/doubao 违规路径 2 参、事件路径 3 参均合法）。
> - [x] try/except 保留：制造 RuntimeError 时仍优雅降级、产出结构完整 `ai_trace`。
> - [x] 新增 `tests/test_cloud_collaborator_event.py`（纯 unittest，兼容 pytest）。
>
> **证据与复现命令**：
> - 测试文件：`tests/test_cloud_collaborator_event.py`
> - 复现：`.venv\Scripts\python.exe tests\test_cloud_collaborator_event.py -v` → **Ran 4 tests, OK（退出码 0）**
> - 回归：`.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"` → Ran 37，仅 `test_core` 因**环境缺 pytest** 报错（既有问题，非本次回归）；`test_task029_integration.py` 中 `analyze_event 接口存在性` PASS。
> - 备注：环境未装 pytest，故以 unittest 等价验证；如需简报验收命令 `pytest tests/test_cloud_collaborator_event.py -q`，先 `pip install pytest` 即可。

---

### 🔴 P0-2 清除 12 处明文密钥 + 建立 `.gitignore` + `.env`（B3/B4/B13）

**目标**：消除泄密红线，建立规范配置管理。

**涉及文件**（12 处密钥，见 §4）：源码 4 处（`image_recognizer.py:206`、`config_runtime.json:3,10`、`zhitong/config.py:50`、`zhitong/blind_yun.py:35`）+ `beforeness/` 3 处 + 文档 4 处（`DEVELOPMENT_GUIDE.md`、`项目问题记录文档.md`）。

**步骤**：
1. 新建根 `.gitignore`，至少含：`.env`、`*.db`、`api/config_runtime.json`、`uploads/`、`output/`、`node_modules/`、`.venv/`、`__pycache__/`、`*.whl`、`*.pt`、`*.engine`、`collaboration_logs/`、`carla/CARLA_0.9.16/`、`zhitong/training/downloads/`、`beforeness/`。
2. 源码密钥改为读环境变量（`os.getenv("DASHSCOPE_API_KEY"/"DEEPSEEK_API_KEY"/"CLAUDE_API_KEY")`），**复用** `cloud_collaborator` 已有的"未配置→优雅降级"逻辑。
3. `beforeness/`：确认废弃后**整目录删除或归档**（含 3 处密钥），从源头消除（见 P3-2/B13）。
4. 文档中的密钥用占位符 `<YOUR_API_KEY>` 替换。
5. 生成 `.env.example`（只留键名与占位符，**不留真值**）。
6. `git rm --cached api/zhitong_violations.db`，停止跟踪数据库。
7. **提醒指挥人（人工动作，IDE 不能代做）**：已泄露的 key 需在服务商后台**立即作废重置**；若已进 git 历史需评估是否清理历史。完成记录里必须显式提示此项。

**验收标准**：
- [ ] 被跟踪源码 `grep -E "sk-[a-zA-Z0-9]{16,}"` **0 命中**；`git ls-files` 无 `.db`/`config_runtime.json`。
- [ ] 未配置环境变量时后端能启动并走"云端不可用→本地兜底/待人工复核"降级。
- [ ] `.env.example` 无任何真值；`beforeness/` 已删除或归档且不再被跟踪。

**禁止**：❌ 把真实 key 写进 `.env.example`/文档/提交 `.env`。

---

### 🔴 P0-3 端到端最小闭环跑通 + 一键稳定运行（B6/B8）

**目标**：从"视频/摄像头输入"到"事件视频+证据链+前端可见"的**真实闭环**至少跑通一次并留存证据。

**涉及文件**：`api/app.py`、`api/realtime_detector.py`、`start-all.bat`、`api/routers/realtime.py`

**步骤**：
1. 先确认 B6"服务退出"是否为 IDE 终端假象：用 `start "后端" cmd /k uvicorn app:app --port 8001`（独立窗口，不用 --reload）验证能否持续运行；把可用启动方式固化进 `start-all.bat`。
2. 准备一段**测试视频**（含闯红灯/逆行等），走 `set_source("video", path)` → `start_detection()`。
3. 触发一次事件，确认：循环缓存写入 → 事件状态机流转 → **P0-1 修复后云端仲裁返回真实结果** → `api/output/event_videos/{日期}/{event_id}.mp4` **真实产出** → 证据链落库 → 前端 `/events`、`/events/:id` 可见。
4. 录制一段**端到端演示视频**（检测框→事件触发→云端仲裁 ai_trace→数字孪生联动→前端事件中心），存到 `presentation/demo/`。

**验收标准**：
- [ ] `api/output/event_videos/` 至少出现 1 个真实 `.mp4`，且其事件的 `ai_trace.final.judgment` 为真实云端结果。
- [ ] 前端 EventDetail 能展示该事件的 ai_trace 与视频。
- [ ] `presentation/demo/` 有一段完整闭环录屏。

---

### 🟠 P1-1 建立"真实指标"实测脚本（B5）——决定"能不能自证"

**目标**：产出**可复现、可写进材料**的真实性能与准确率数据，替换所有编造数字。

**新增文件**：`scripts/benchmark_detection.py`、`scripts/eval_accuracy.py`、`docs/REAL_METRICS.md`

**步骤**：
1. **延迟/FPS 实测**：对固定视频，统计 YOLO 单帧推理延迟、端到端 FPS、显存占用（`nvidia-smi`/`torch.cuda`）。**先拿 PyTorch 原生真实值**（哪怕 45ms/22FPS 也真实可用）。
2. **准确率评测**：用**公开交通数据集**（如 CCTSDB2021 / 自建小集）跑 mAP、各类违规 Precision/Recall/误报率，脚本化、可复现。
3. **TensorRT（可选加分）**：若做，用 `zhitong/tensorrt_engine.py` 真导出 `yolov8n.engine` 实测加速比；做不到就**如实写"未启用，规划中"**。
4. 结果写入 `docs/REAL_METRICS.md`：注明**测试环境、数据集、样本量、脚本路径、原始日志路径**，每个数字都能被评委复现。
5. **决策闸门**：P1-1 的真实 mAP 结果，作为"是否启动 P2-3 微调"的依据。

**验收标准**：
- [ ] `python scripts/benchmark_detection.py` / `eval_accuracy.py` 输出真实数据并落盘。
- [ ] `docs/REAL_METRICS.md` 每个数字都有对应脚本与原始日志，无一手写死数据。

**禁止**：❌ 把方案书里的 15ms/91%/580 等旧数字直接抄进 `REAL_METRICS.md`。

---

### 🟡 P2-1a 试点技术支撑（IDE 负责）

**目标**：降低现场部署门槛 + 提供可导出的真实运行统计。

**步骤**：
1. 提供**一键部署包 + 独立窗口稳定启动**（承接 P0-3）。
2. 增加"运行时长/累计检测量/累计违规量/误报人工复核率"的**真实统计导出**（复用 `system_statistics` 表 + `statistics` 路由）。

**验收标准**：
- [ ] 有可复现的一键部署/启动方式；有真实运行统计导出（非 demo 数据）。

### 🟡 P2-1b 试点商务落地（团队负责，IDE 不背 KPI）

**目标**：真实场景（校园门口/园区/合作路口）跑 2-4 周，留下**真实证据**。

**步骤**：联系试点场景、争取**盖章试用证明/意向书**、现场照片、真实运行数据截图，归入 `presentation/pilot/`。

**验收标准**：
- [ ] `presentation/pilot/` 有试用证明/照片/真实数据看板截图。

---

### 🟡 P2-2 方案书与真实实现对齐（结题材料修订）

**目标**：按 §1.3 表，把方案书改成"讲真做过的、删没做的、放大亮点"。

**步骤**：
1. 删除/降级：LSTM+GNN 预测、区块链存证、自进化 82%→91%、TensorRT 15ms（除非 P1-1/P2-3 真测出）。
2. 放大真实亮点：**端云三级仲裁（分歧检测）+ 事件级 8 状态证据链闭环 + 数字孪生实时联动 + K230 边缘 + CARLA 仿真验证**。
3. 用 `docs/REAL_METRICS.md` 真实数据替换所有旧数字。
4. 统一项目名为 **"智瞳灵声"**（B9），全库替换"灵瞳智声"。

**验收标准**：
- [ ] 方案书每个技术宣称都能在代码或 `REAL_METRICS.md` 找到支撑；全库项目名统一。

---

### 🟡 P2-3 交通场景微调（**条件启动**：仅当 P1-1 显示准确率不足）

> 由初稿 P1 降级而来（采纳豆包意见）。**先看数据再决定**，不先入为主。

**触发条件**：P1-1 实测 mAP / 违规类 P/R 明显不达标（例如车辆/行人漏检高、闯红灯判定不稳）。

**步骤**：用公开交通违规数据集微调 `yolov8n.pt` → 存 `api/models/yolov8n_traffic.pt` → `image_recognizer.py` 支持加载自训练权重 → 用 `eval_accuracy.py` 对比"微调前后 mAP"，写入 `REAL_METRICS.md`。

**验收标准**：
- [ ] 存在自训练权重且被真实加载；有"微调前后 mAP 对比"真实数据与训练日志。

---

### ⚪ P3-1 微信小程序整理（由初稿 P1 降级）

> 负责人已明确小程序暂非本轮重点（采纳豆包意见降 P3），但**重复目录是仓库观感红线**，做低成本止血。

**步骤**：
1. **低成本止血（建议尽快做）**：判定 `wechat-miniprogram/pages/` 为唯一权威套，删除/归档 `miniprogram/pages/`、`src/pages/` 两套重复目录（移到 `_deprecated/` 并在 README 说明）。
2. 完整统一（视答辩重点决定）：校对 `utils/api.js` 提交格式与后端 `WeChatViolationSubmit` 一致（`PROJECT_ISSUES.md` 问题4）；`app.js` 的 `baseUrl` 改可配置，不再硬编码 `127.0.0.1`。

**验收标准**：
- [ ] 仓库内小程序只剩一套权威实现（或明确归档）；如启用，微信开发者工具可编译、提交接口字段不报错。

### ⚪ P3-2 工程卫生清理（B10/B11/B12/B13）

- `beforeness/` 确认废弃后归档删除（消除 B13 密钥与"代码混乱"观感）。
- 统一 logging：核心模块 `print()` → `logging`（复用 `app.py` 的 `zhitong_api` logger）。
- `zhitong/training/downloads/` 加 `README_THIRD_PARTY.md` 注明来源与许可，避免被误认为原创体量。
- 生产部署文档补：CORS 收敛白名单、SQLite→PostgreSQL 迁移路径（`requirements.txt` 已含 alembic）。
- 更新/删除过期的 `api/backend_evaluation_report.md`（评的是旧原型）。

---

## 3. 国家级评审对标自查表（执行完 P0-P2 后逐项打勾）

| 评审维度 | 关键问题 | 达标动作 |
|---------|---------|---------|
| 创新性 | 有没有"别人没这么做过"且**能演示**的点？ | 主打"端云三级仲裁 + 事件级证据链闭环"，现场演示分歧检测与状态流转 |
| 技术实现 | 核心链路**真跑通**了吗？ | P0-1/P0-3 完成，端到端 demo 录屏，事件拿到**真实**云端结果 |
| 可自证 | 每个数字都能复现吗？ | P1-1 的 `REAL_METRICS.md` + 脚本 + 原始日志 |
| 落地性 | 有真实场景/客户/数据吗？ | P2-1a/b 试点证明 + 真实运行数据 |
| 完整性 | 材料宣称的都存在吗？ | P2-2 方案书对齐，零"讲了没做" |
| 成熟度 | 能稳定一键演示吗？ | P0-3 一键启动 + 独立窗口稳定运行 |
| 工程可信度 | 仓库干净、无泄密吗？ | P0-2 + P3-2：0 明文密钥、有 `.gitignore`、无废弃混乱目录 |
| 团队 | 是否跨学科、分工清晰？ | （团队动作）补商科/设计成员，材料体现分工 |

---

## 4. 附：已确认的代码级问题索引（供 IDE 直接定位）

| 编号 | 文件:行 / 位置 | 问题 |
|------|---------------|------|
| B1 | `api/cloud_collaborator.py:784`（`_analyze_event_with_claude`） | 3 参调用 2 参 `analyze_with_claude(image_input, violation_type)`；异常被 `try/except:789` 吞 → **静默降级** |
| B2 | `api/cloud_collaborator.py:811`（`_analyze_event_with_deepseek`） | 入参与 `analyze_with_deepseek_judge(violation_type, yolo_result_dict, doubao_result_dict)`(:1260) 不符；异常被 `:813` 吞 → 结果始终降级 |
| B3 | **12 处明文 `sk-` 密钥** | `api/config_runtime.json:3,10`；`api/image_recognizer.py:206`；`api/DEVELOPMENT_GUIDE.md:21,26`；`zhitong/config.py:50`；`zhitong/blind_yun.py:35`；`beforeness/blind_yun.py:35`；`beforeness/photo_ai_analysis.py:19`；`beforeness/untitled_2.py:24`；`项目问题记录文档.md:26,27` |
| B4 | 根目录 | 无 `.gitignore`；`api/zhitong_violations.db` 被 git 跟踪 |
| B5 | `api/backend_evaluation_report.md` | 整份过期（评的是旧单文件原型），勿作当前质量依据 |
| B7 | `wechat-miniprogram/` | `pages/` + `miniprogram/pages/` + `src/pages/` 三套重复 |
| B8 | `api/output/event_videos/` | 空目录，事件闭环从未产出真实视频 |
| B9 | 全库 | "智瞳灵声" vs "灵瞳智声" 命名不统一 |
| B13 | `beforeness/` | 废弃目录（3 脚本含密钥 + `yolov8n.pt`），定位不明，需归档删除 |

---

## 5. 最终执行顺序（双 AI 一致的排期）

```
🔴 第 1 天    P0-1  修复 B1/B2 事件闭环参数错位（保留降级）+ mock 单测
🔴 第 1-2 天  P0-2  清除 12 处明文密钥 + .gitignore + .env（含 beforeness 处理）
🔴 第 2-3 天  P0-3  端到端最小闭环跑通 + event_videos 真实产出 + demo 录屏
🟠 第 1 周    P1-1  真实指标实测脚本 + REAL_METRICS.md（延迟/FPS/mAP）
🟡 第 2 周    P2-2  方案书与真实实现对齐（删虚的、写实的、统一项目名）
🟡 结题前     P2-1a IDE：一键部署包 + 运行统计导出   |  P2-1b 团队：试点/证明/数据
⚪ 视数据     P2-3  交通场景微调（仅当 P1-1 显示准确率不足才启动）
⚪ 有精力     P3-1  小程序整理（先删重复目录）  /  P3-2  工程卫生
```

**关键路径**：P0-1 → P0-3 → P1-1 → P2-2。
**时间紧张时的最小可冲奖集**（采纳豆包建议，需负责人确认时间线）：**P0-1 + P0-2 + P0-3 + P1-1 + P2-2**，其余可砍。

---

## 6. 双 AI 复核结论（对豆包 5 个问题的正式回应）

> 豆包对初稿做了**独立代码复核**，我已逐条二次验证，其更正**全部属实并采纳**。以下为定论：

| # | 豆包意见 | 我的复核与结论 |
|---|---------|---------------|
| 1 | B1/B2 是"静默降级"非"必崩"；try/except 是降级设计**不应删**，应"对齐参数+保留降级+断言非降级结果" | ✅ **完全采纳**。已核实 `:789/:813` 确有 try/except 返回空。初稿"禁止 try/except"表述已修正为"禁止删降级来消错"（§0.2、P0-1） |
| 2 | P1-2 微调降 P2，先看 P1-1 真实 mAP 再决定 | ✅ **采纳**。我无数据证明 yolov8n 交通场景不足，应先测再定 → 已改为 **P2-3 条件启动** |
| 3 | P1-3 小程序降 P3（负责人称暂没弄） | ✅ **采纳**，降为 **P3-1**；但补充"低成本止血"：先删 2 套重复目录，避免评审观感扣分 |
| 4 | P2-1 拆分为 P2-1a（IDE）/ P2-1b（团队） | ✅ **完全采纳**，已在 §0.3、§2 拆分并明确归属边界 |
| 5 | 时间线 2027.05 需确认；紧张则砍任务 | ✅ **采纳**，§5 增加"最小可冲奖集"应急方案，**待负责人确认时间线** |
| 补充 | 明文密钥实为 **12 处**（非 4）；`beforeness/` 废弃目录含密钥 | ✅ **独立复核属实**，已更新 B3 清单、新增 B13，并纳入 P0-2/P3-2 |

**双方一致认可的总纲**："做实 + 自证 + 落地"、"做深一个能自证的点，胜过吹六个做不出来的点"、"禁止编造数据"、"方案书向真实实现对齐"。

**待项目负责人拍板的 2 件事**：
1. **时间线**：2027.05 结题是否准确？若更紧，是否按"最小可冲奖集"执行？
2. **小程序**：本轮答辩是否演示小程序？决定 P3-1 是"仅删重复目录"还是"完整统一"。

---

*本文件为最终版 IDE 执行指南。完成任一任务后，请在该任务下追加"✅ 完成记录（日期 + 证据文件路径 + 复现命令）"，供指挥人审阅。遇到与本文件冲突的实现细节，以"真实代码 + 可自证"为最高准则。复核往来记录见 `NATIONAL_SPRINT_RESPONSE.md`。*
