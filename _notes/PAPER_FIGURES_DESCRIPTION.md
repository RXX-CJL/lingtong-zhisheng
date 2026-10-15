# 论文图表描述清单

> **文档版本**: 1.0
> **生成时间**: 2026-08-21
> **用途**: 为真人论文撰写成员提供图表绘制指引，每张图表提供内容描述、数据来源和建议绘制方式

---

## 图表清单

共 18 张图表建议，覆盖系统架构、数据流、状态机、时序、对比表等。

---

### 图 1：系统三层架构图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 1 |
| **标题** | 端云协同智慧交通系统三层架构 |
| **内容描述** | 展示端侧感知层、云端复核层、数字孪生展示层三层架构。端侧包含 YOLO 多模型检测、DeepSORT 跟踪、行为分析、规则引擎、循环缓存、事件引擎。云端包含豆包视觉大模型（一级）、DeepSeek 大模型（二级）、Claude（备选）。数字孪生包含 Three.js 3D 场景、WebSocket 实时推送。层间用箭头表示数据流方向。 |
| **数据来源** | PAPER_MATERIAL_PACK.md 第 2 章 |
| **建议绘制方式** | Visio / draw.io 分层架构图，三层用不同背景色区分，层内模块用矩形框，层间用箭头连接 |

---

### 图 2：完整数据流图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 2 |
| **标题** | 交通事件闭环系统数据流 |
| **内容描述** | 展示从视频帧输入到 Web 展示的完整数据流：视频帧 → YOLO 多模型检测 → DeepSORT 车辆跟踪 → 行为分析引擎 → 规则引擎插件评估 → 发现疑似事件 → 创建 TrafficEvent (TRIGGERED) → 循环缓存提取事件视频 (T-5s~T+5s) → 状态转换 RECORDING → PENDING_AI → 云端 AI 按需分析 → AI_REVIEWED → CONFIRMED/REJECTED/MANUAL_REVIEW → EvidenceChain 证据链存储 → traffic_events 表 → Web 端展示 + 人工复核 |
| **数据来源** | PAPER_MATERIAL_PACK.md 第 2.5 节 |
| **建议绘制方式** | draw.io 流程图，从左到右排列，用不同颜色区分端侧（蓝色）、云端（绿色）、存储（橙色）、前端（紫色） |

---

### 图 3：交通事件 8 状态生命周期状态机图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 3 |
| **标题** | 交通事件 8 状态生命周期状态机 |
| **内容描述** | 展示 8 个状态的合法转换关系：DETECTING → TRIGGERED → RECORDING → PENDING_AI → AI_REVIEWED → CONFIRMED/REJECTED/MANUAL_REVIEW → CONFIRMED/REJECTED。MANUAL_REVIEW → CONFIRMED/REJECTED。终态用双线圆圈标注。 |
| **数据来源** | `api/traffic_event_engine.py` 的 `VALID_TRANSITIONS` 映射 |
| **建议绘制方式** | UML 状态机图（State Diagram），每个状态用圆角矩形，转换用带标签箭头，终态用双线圆圈 |

---

### 图 4：ai_trace v3 多级嵌套验证结构图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 4 |
| **标题** | ai_trace v3 多级嵌套 AI 验证结构 |
| **内容描述** | 展示四级嵌套结构：第一级 YOLO 本地检测（输出 detections）→ 第二级 豆包视觉大模型（输出 confidence + judgment）→ 第三级 DeepSeek 逻辑审核（输出 agreed + reason）→ 第四级 final 最终裁决（输出 judgment + confidence + explanation + risk_flag）。 |
| **数据来源** | PAPER_MATERIAL_PACK.md 第 3.1 节 ai_trace v3 结构 |
| **建议绘制方式** | 嵌套层次图（从上到下流水线），每级用矩形框 + 输入/输出标注 |

---

### 图 5：视频循环缓存机制示意图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 5 |
| **标题** | 视频循环缓存与事件视频提取机制 |
| **内容描述** | 展示 deque(maxlen=300) 循环缓存结构，时间轴上标注 30 秒缓存窗口。事件触发时刻 T 标注，提取窗口 T-5s 至 T+5s 高亮显示。旧帧自动淘汰（左侧箭头出队），新帧持续入队（右侧箭头入队）。 |
| **数据来源** | `api/circular_frame_buffer.py` 的 `CircularFrameBuffer` 类 |
| **建议绘制方式** | 时间轴图，deque 用水平条形表示，触发时刻 T 用竖线标注，提取窗口用高亮区域 |

---

### 图 6：多帧确认滑动窗口机制图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 6 |
| **标题** | 多帧确认滑动窗口投票机制 |
| **内容描述** | 展示 window_size=10、confirm_threshold=5 的滑动窗口。窗口内 10 帧中同一 track_id 出现 ≥5 帧则确认。展示匹配条件：Levenshtein 车牌相似度 ≥0.8 或 IOU ≥0.3 或中心距离 ≤平均尺寸*0.3。 |
| **数据来源** | `api/multi_frame_validator.py` |
| **建议绘制方式** | 滑动窗口示意图，10 个帧用方格表示，匹配的帧标绿色，未匹配标红色，阈值线标注 |

---

### 图 7：规则引擎插件化架构图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 7 |
| **标题** | 规则引擎插件化架构 |
| **内容描述** | 展示 BaseRulePlugin 抽象基类 + 3 个具体插件（traffic_plugin / urban_management_plugin / public_security_plugin）。PluginLoader 用 importlib 动态加载。ViolationEvent 数据类作为插件输出。 |
| **数据来源** | `api/rule_engine/base_plugin.py` + `plugin_loader.py` |
| **建议绘制方式** | UML 类图，基类在顶部，子类在下方，PluginLoader 在侧面用依赖箭头连接 |

---

### 图 8：事件证据链结构图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 8 |
| **标题** | 完整证据链 18 字段结构 |
| **内容描述** | 展示 EvidenceChain 的 18 个字段，分为 5 类：基础信息（camera_id/timestamp/location）、车辆信息（vehicle_id/vehicle_type/plate_number/plate_color/lane_id）、场景上下文（traffic_light_state/stop_line_relation/trajectory）、视觉证据（key_frames/event_video_path）、判断结果（rule_judgment/ai_judgment/ai_confidence/ai_explanation）、最终状态（final_status）。 |
| **数据来源** | `api/evidence_chain.py` 的 `EvidenceChain` 数据类 |
| **建议绘制方式** | 分类框图，5 个类别用不同颜色，字段用列表展示 |

---

### 图 9：端云协同时序图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 9 |
| **标题** | 端云协同按需调用时序图 |
| **内容描述** | 展示端侧持续感知 → 规则触发事件 → 循环缓存提取视频 → 提交云端 → 豆包分析 → DeepSeek 验证 → 返回 ai_trace v3 → 应用结果 → 状态转换的完整时序。涉及角色：RealtimeDetector、EventEngine、CircularBuffer、CloudCollaborator、DoubaoAPI、DeepSeekAPI。 |
| **数据来源** | PAPER_MATERIAL_PACK.md 第 2.5 节数据流 |
| **建议绘制方式** | UML 时序图（Sequence Diagram），角色用生命线，消息用箭头，关键状态转换用标注 |

---

### 图 10：数据库 ER 图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 10 |
| **标题** | 数据库实体关系图 |
| **内容描述** | 展示 traffic_events 表（20 列 + 6 索引）和 violation_evidences 表（20 列）的结构及逻辑关系。两表通过 track_id 和 event_type 逻辑关联。 |
| **数据来源** | `api/models.py` |
| **建议绘制方式** | ER 图（Entity-Relationship Diagram），表用矩形，字段用列表，主键标注，关系用连线 |

---

### 图 11：API 路由架构图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 11 |
| **标题** | REST API 路由总览 |
| **内容描述** | 展示 34 个 API 路由的分类：事件路由（6 个）、PTZ 路由（4 个）、CARLA 路由（5 个）、追踪路由（3 个）、插件路由（4 个）、现有路由（12 个）。 |
| **数据来源** | PAPER_MATERIAL_PACK.md 第 6 章 |
| **建议绘制方式** | 树形分类图，根节点为 /api/realtime，子节点按类别分组 |

---

### 图 12：前端页面架构图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 12 |
| **标题** | Web 管理后台页面架构 |
| **内容描述** | 展示 8 个前端页面的路由关系：仪表盘(/)、实时监控(/realtime)、交通事件中心(/events)、事件详情(/events/:id)、AI 追踪(/ai-trace)、违规列表(/violations)、违规详情(/violations/:id)、设置(/settings)。 |
| **数据来源** | `web-admin/src/router/index.js` |
| **建议绘制方式** | 页面导航图，每个页面用矩形框，路由用箭头连接 |

---

### 图 13：违规颜色编码表

| 项目 | 内容 |
|------|------|
| **图号** | Figure 13 |
| **标题** | 6 类违规颜色编码体系 |
| **内容描述** | 展示 6 类违规的颜色映射：闯红灯=深红、逆行=橙色、违停=紫色、未戴头盔=青色、占道经营=蓝色、人员聚集=黄色。在 bbox 标注和数字孪生中统一使用。 |
| **数据来源** | `web-admin/src/views/RealTimeMonitor.vue` 的 VIOLATION_COLOR_MAP |
| **建议绘制方式** | 颜色色卡表，每行一个类别 + 颜色色块 + 中文名称 |

---

### 图 14：数字孪生 3D 场景截图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 14 |
| **标题** | 数字孪生 3D 可视化场景 |
| **内容描述** | 展示 Three.js 渲染的 3D 城市道路场景：车辆模型、信号灯模型、CSS2DRenderer 车牌卡片标注、红色旋转箭头违规指示。 |
| **数据来源** | `digital_twin/static/js/main.js` + 实际运行截图 |
| **建议绘制方式** | 直接使用系统运行截图（需启动后端 + 数字孪生服务后截屏） |

---

### 图 15：API 调用成本对比图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 15 |
| **标题** | 逐帧分析 vs 按事件分析 API 调用成本对比 |
| **内容描述** | 柱状图对比两种方案的日均 API 成本：逐帧分析（259200 次/日 × ¥0.01 = ¥2592）vs 按事件分析（100 次/日 × ¥0.05 = ¥5），成本降低 99.8%。 |
| **数据来源** | PAPER_MATERIAL_PACK.md 第 8.2.5 节 |
| **建议绘制方式** | ECharts 柱状图，两个柱子，纵轴为日均成本（元），标注成本降低百分比 |

---

### 图 16：多帧确认效果对比图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 16 |
| **标题** | 不同确认阈值下的误判率与召回率对比 |
| **内容描述** | 折线图展示确认阈值（1/3/5/7 帧）对误判率和召回率的影响。误判率随阈值增大而下降，召回率也下降。 |
| **数据来源** | PAPER_MATERIAL_PACK.md 第 8.2.6 节 |
| **建议绘制方式** | ECharts 双 Y 轴折线图，横轴为确认阈值，左 Y 轴为误判率，右 Y 轴为召回率 |

---

### 图 17：端到端延迟分解图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 17 |
| **标题** | 端到端延迟分解 |
| **内容描述** | 展示各阶段延迟：YOLO 检测(45ms) + DeepSORT 跟踪(10ms) + 行为分析(5ms) + 事件触发(500ms) + 事件视频提取(2s) + 云端 AI 分析(5s) + Web 展示(1s)。 |
| **数据来源** | PAPER_MATERIAL_PACK.md 第 8.2.4 节 |
| **建议绘制方式** | 甘特图或堆叠条形图，展示各阶段耗时占比 |

---

### 图 18：系统部署架构图

| 项目 | 内容 |
|------|------|
| **图号** | Figure 18 |
| **标题** | 系统部署架构 |
| **内容描述** | 展示系统部署拓扑：枪神8 笔记本（RTX 4060 GPU）运行端侧感知 + FastAPI 后端（端口 8001）+ 数字孪生服务。K230 开发板作为边缘端车牌识别。Web 前端（Vite dev server 端口 5173）。云端 AI API 通过 HTTPS 调用。 |
| **数据来源** | PAPER_MATERIAL_PACK.md 第 10 章 + 硬件约束 |
| **建议绘制方式** | 部署拓扑图，物理设备用矩形，网络连接用云形，端口标注 |

---

*以上 18 张图表覆盖系统架构、数据流、状态机、时序、数据库、API、前端、性能对比等维度，建议使用 Visio / draw.io / ECharts 绘制。*
