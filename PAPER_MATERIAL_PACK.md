# 智瞳灵声——基于视觉识别与云端推理的智慧交管系统

## 论文资料包

> **文档版本**: 1.0
> **生成时间**: 2026-08-21
> **服务对象**: 团队真人成员（用于撰写学术论文）
> **信息来源**: 项目源代码、TASK-028/029 输出报告、通知文件

---

## 第 1 章：项目概述

### 1.1 项目名称

智瞳灵声——基于视觉识别与云端推理的智慧交管系统

### 1.2 项目背景

城市交通安全管理长期面临三大痛点：

1. **人工监控效率低**：传统交通监控依赖人工巡查视频流，监控人员无法同时关注大量摄像头，违法行为漏检率高。
2. **违法取证难**：传统抓拍系统仅保存单帧图片，缺乏事件前后视频上下文，证据链不完整，难以形成有效法律证据。
3. **实时性不足**：纯云端 AI 分析方案需要将视频流持续上传，存在网络延迟和带宽成本瓶颈，无法满足实时响应需求。

### 1.3 项目目标

构建从"视频→本地感知→事件触发→事件视频→云端 AI 复核→违法事件"的完整闭环系统，实现：

- 端侧持续感知视频流，基于规则引擎发现疑似交通事件
- 事件触发后自动提取事件前后视频片段，合成完整事件视频
- 云端大模型按需复核（仅在事件触发后调用），降低 API 成本
- 保存完整证据链（含轨迹、关键帧、视频、规则判断、AI 判断）
- Web 端可视化展示事件全过程，支持人工复核

### 1.4 项目意义

**学术价值**：

- 提出端云协同的事件驱动架构范式，突破"逐帧 AI 分析"与"纯云端处理"的传统模式
- 设计交通事件 8 状态生命周期状态机，为事件级违法检测提供形式化模型
- 构建多级嵌套 AI 验证结构（ai_trace v3），融合本地 YOLO 与云端大模型

**实用价值**：

- 降低云端 AI 调用成本（从逐帧调用降为按事件调用，成本降低数个量级）
- 提高违法检测准确性（多帧确认 + 事件级 AI 复核 + 人工复核三重保障）
- 提供完整事件证据链，支持法律取证

### 1.5 一句话概括

本系统基于 YOLO 本地检测 + DeepSORT 跟踪 + 规则引擎事件触发 + 循环缓存视频提取 + 云端大模型按需复核 + 数字孪生可视化，构建了智慧交通违法事件闭环系统。

---

## 第 2 章：系统架构

### 2.1 整体架构

本系统采用**三层架构**设计，包含端侧感知层、云端复核层和数字孪生展示层。

```
┌─────────────────────────────────────────────────────────────────────┐
│                        数字孪生展示层                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ Three.js    │  │ WebSocket    │  │ Flask + SocketIO 服务      │  │
│  │ 3D 场景     │←→│ 实时推送     │←→│ 轮询后端 + 事件广播       │  │
│  └─────────────┘  └──────────────┘  └───────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
         ↑                                        ↑
         │ WebSocket                              │ HTTP 轮询
         │                                        │
┌─────────────────────────────────────────────────────────────────────┐
│                        云端复核层                                     │
│  ┌───────────────┐   ┌────────────────┐   ┌──────────────────┐     │
│  │ 豆包视觉大模型 │   │ DeepSeek 大模型 │   │ Claude (可选)     │     │
│  │ (一级分析)     │ → │ (二级验证)      │ → │ 视觉分析补充     │     │
│  └───────────────┘   └────────────────┘   └──────────────────┘     │
│                      ai_trace v3 嵌套结构                            │
└─────────────────────────────────────────────────────────────────────┘
         ↑ 按事件触发（非常驻）
         │
┌─────────────────────────────────────────────────────────────────────┐
│                        端侧感知层                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ YOLO 多   │→│ DeepSORT │→│ 行为分析 │→│ 规则引擎 │→│ 事件引擎 │ │
│  │ 模型检测  │ │ 车辆跟踪  │ │ 引擎     │ │ 插件化   │ │ +状态机  │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│       │                                          │                  │
│       │     ┌──────────────────────────┐         │                  │
│       └──→  │ 循环缓存 (30s)           │ ←───────┘                  │
│             │ 事件视频提取 (T-5s~T+5s) │                            │
│             └──────────────────────────┘                            │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ 多帧确认  │ │ 车牌识别  │ │ PTZ 云台  │ │ CARLA 仿真│            │
│  │ 机制     │ │ PaddleOCR│ │ ONVIF    │ │ 数据源   │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
│                                                                   │
│  硬件平台: 枪神8 笔记本 (RTX 4060 GPU) + K230 开发板               │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 端侧感知层

端侧负责实时视频处理，包含以下核心组件：

- **YOLO 多模型检测**：6 个专用模型（通用检测 yolov8n、高精度 yolov8s、车辆专用、头盔专用、红绿灯专用、车道线专用、车牌专用），实现分类专用化提高精度
- **DeepSORT 车辆跟踪**：质心追踪 + 轨迹预测，分配唯一 track_id 并管理生命周期
- **行为分析引擎**：4 类行为判断（闯红灯、逆行、违停、未戴头盔），基于轨迹分析 + 信号灯状态 + 停止线关系
- **规则引擎插件化**：BaseRulePlugin 基类 + 3 大场景插件（交通/城管/治安），支持动态加载和热切换
- **循环缓存**：维护最近 30 秒视频帧 + 检测结果，事件触发后提取 T-5s 至 T+5s 视频片段
- **事件引擎**：8 状态生命周期管理，冷却机制避免重复触发

### 2.3 云端复核层

云端采用多级嵌套验证结构（ai_trace v3）：

- **豆包视觉大模型**（一级分析）：接收事件关键帧 + 结构化上下文，输出违规判断和置信度
- **DeepSeek 大模型**（二级验证）：对豆包结果进行逻辑审核，判断是否存在误报
- **Claude**（可选补充）：在豆包/DeepSeek 失败时作为备选视觉分析
- **按需调用**：仅在事件触发后才调用云端，非常驻视频流处理

### 2.4 数字孪生展示层

- **Three.js 3D 场景**：渲染城市道路、车辆、信号灯
- **WebSocket 实时推送**：Flask-SocketIO 服务，每 1.5 秒轮询后端状态
- **检测结果联动**：CSS2DRenderer 渲染车牌卡片和违规类型标注
- **红色旋转箭头**：违规事件发生时 THREE.Group 渲染 3D 旋转箭头，15 秒淡出

### 2.5 数据流

完整数据流如下：

```
视频帧 → YOLO 多模型检测 → DeepSORT 车辆跟踪 → 行为分析引擎
    → 规则引擎插件评估 → 发现疑似事件 → 创建 TrafficEvent (TRIGGERED)
    → 循环缓存提取事件视频 (T-5s~T+5s) → 状态转换 RECORDING → PENDING_AI
    → 云端 AI 按需分析 (豆包→DeepSeek→final) → 状态转换 AI_REVIEWED
    → CONFIRMED / REJECTED / MANUAL_REVIEW
    → EvidenceChain 完整证据链存储 → traffic_events 表持久化
    → Web 端 EventCenter 列表 + EventDetail 详情 + 人工复核
```

---

## 第 3 章：核心技术模块

### 3.1 YOLO 多模型检测

| 项目 | 内容 |
|------|------|
| **功能描述** | 基于 YOLOv8 的多模型串联检测，针对不同检测任务使用专用模型 |
| **算法/方法** | Ultralytics YOLOv8 框架，6 个模型并行/串联检测 |
| **关键参数** | CONFIDENCE_THRESHOLD=0.5, YOLO_BATCH_SIZE=1, GPU 加速 (RTX 4060) |
| **输入** | 视频帧 (BGR numpy ndarray) |
| **输出** | 检测结果列表 [{class_name, confidence, bbox}] + ai_trace v3 结构 |
| **代码路径** | `api/image_recognizer.py` |

6 个专用模型：

1. `yolov8n` — 通用目标检测（COCO 80 类）
2. `yolov8s` — 高精度通用检测
3. 车辆专用模型 — 轿车/摩托车/卡车/公交车/自行车
4. 头盔专用模型 — 头盔/未戴头盔检测
5. 红绿灯专用模型 — 红灯/绿灯/黄灯状态识别
6. 车道线专用模型 — 车道线检测
7. 车牌专用模型 — 车牌定位

ai_trace v3 嵌套结构：

```json
{
  "version": "v3",
  "yolo": { "detections": [...], "model": "yolov8n" },
  "doubao": { "confidence": 0.85, "judgment": "confirmed", "description": "..." },
  "deepseek": { "agreed": true, "reason": "..." },
  "final": {
    "judgment": "confirmed/rejected/uncertain",
    "confidence": 0.85,
    "explanation": "...",
    "risk_flag": false
  }
}
```

### 3.2 DeepSORT 车辆跟踪

| 项目 | 内容 |
|------|------|
| **功能描述** | 车辆目标跟踪，分配唯一 track_id 并维护轨迹历史 |
| **算法/方法** | 质心追踪（CentroidTracker），基于欧氏距离最近邻匹配 |
| **关键参数** | MAX_HISTORY=30, MAX_DISTANCE=80, DIRECTION_THRESHOLD=10 |
| **输入** | YOLO 检测结果列表 [{class_name, bbox, confidence}] |
| **输出** | 跟踪车辆字典 {track_id: {bbox, center, history, direction, speed, ...}} |
| **代码路径** | `api/vehicle_tracker.py` |

核心机制：

- 车辆类别集合：`VEHICLE_CLASSES = {'car', 'motorcycle', 'truck', 'bus', 'bicycle'}`
- 质心计算：bbox 中心点 `(x1+x2)//2, (y1+y2)//2`
- 最近邻匹配：计算当前检测框中心与已有轨迹末点的欧氏距离，取最小且小于 MAX_DISTANCE 的匹配
- 轨迹历史：每个 track_id 维护最近 30 帧的位置/速度/方向历史
- 方向检测：基于轨迹历史计算运动方向，用于逆行判断
- 速度计算：基于帧间位移和时间差计算像素速度

### 3.3 行为分析引擎

| 项目 | 内容 |
|------|------|
| **功能描述** | 基于轨迹分析的车辆行为理解，判断 4 类交通违规行为 |
| **算法/方法** | 轨迹特征提取 + 时空规则判断 |
| **关键参数** | speed_limit=60, pixel_per_meter=10, stop_line_y=400, park_duration_threshold=300 |
| **输入** | 车辆轨迹历史 [{center, bbox, timestamp, dx, dy}] + 场景上下文 |
| **输出** | BehaviorResult 列表 [{behavior_type, confidence, is_violation, evidence}] |
| **代码路径** | `api/behavior_engine.py` |

8 类行为类型：

| 英文标识 | 中文 | 判断逻辑 |
|---------|------|---------|
| `red_light` | 闯红灯 | 红灯状态 + 车辆越过停止线 |
| `wrong_way` | 逆行 | 轨迹方向与车道线夹角 > 135° |
| `illegal_parking` | 违规停车 | 连续 ≥30 帧停在非停车区 |
| `lane_departure` | 压线行驶 | 车辆 bbox 跨越车道线 |
| `speeding` | 超速 | 像素速度换算后超过限速 |
| `running_yellow` | 抢黄灯 | 黄灯期间加速通过停止线 |
| `illegal_turn` | 违规掉头 | 轨迹曲率异常 |
| `pedestrian_crossing` | 未礼让行人 | 行人过马路时未减速停车 |

轨迹特征提取函数 `_extract_trajectory_features` 计算以下特征：

- 平均速度 / 最大速度
- 路径曲率（相邻方向向量叉积）
- x/y 坐标标准差（判断直线运动 vs 曲线运动）
- 方向一致性

### 3.4 规则引擎插件化

| 项目 | 内容 |
|------|------|
| **功能描述** | 可扩展的违规检测规则引擎，支持交通/城管/治安多场景插件 |
| **算法/方法** | 抽象基类 + 动态加载（importlib）+ 热切换 |
| **关键参数** | PLUGINS_ENABLED='traffic,urban_management,public_security' |
| **输入** | 视频帧 + 场景上下文 + 跟踪器状态 |
| **输出** | ViolationEvent 列表 [{behavior_type, confidence, is_violation, evidence, vehicle_id}] |
| **代码路径** | `api/rule_engine/base_plugin.py`, `api/rule_engine/plugin_loader.py` |

ViolationEvent 数据类（`base_plugin.py`）：

```python
@dataclass
class ViolationEvent:
    behavior_type: str        # 行为类型英文标识
    behavior_type_cn: str     # 中文描述
    confidence: float         # 置信度 [0.0, 1.0]
    is_violation: bool        # 是否违规
    evidence: Dict            # 证据字典
    vehicle_id: int           # track_id
    timestamp: str            # ISO8601
    color: Any                # 可视化颜色
```

BaseRulePlugin 基类抽象方法：

- `scenario_name`: 场景标识（如 "traffic"）
- `detectable_types`: 可检测违规类型列表
- `initialize()`: 资源初始化
- `shutdown()`: 资源释放
- `analyze(frame, scene_context, tracker)`: 执行分析返回 ViolationEvent 列表

3 大场景插件：

| 插件 | 场景 | 检测逻辑 | 冷却时间 |
|------|------|---------|---------|
| traffic_plugin | 交通 | 闯红灯/逆行/违停/未戴头盔 | 60s |
| urban_management_plugin | 城管 | 占道经营（person+backpack/bag/table 组合） | 30s |
| public_security_plugin | 治安 | 人员聚集（DBSCAN 网格化聚类 + 连续帧确认） | 60s |

### 3.5 多帧确认机制

| 项目 | 内容 |
|------|------|
| **功能描述** | 滑动窗口 + 投票机制，降低单帧误判率 |
| **算法/方法** | 滑动窗口 + Levenshtein 车牌相似度 + IOU/中心距离双匹配 |
| **关键参数** | window_size=10, confirm_threshold=5, FPS 窗口=30 帧 |
| **输入** | 单帧检测结果 [{track_id, bbox, plate_number, ...}] |
| **输出** | 确认状态 {confirmed, pending, expired} + 确认帧数 |
| **代码路径** | `api/multi_frame_validator.py` |

核心算法：

1. **Levenshtein 车牌相似度**：编辑距离归一化，处理车牌字符轻微识别错误
   - 相似度 = 1 - edit_distance / max(len1, len2)
   - 阈值 0.8 以上视为同一车牌

2. **IOU + 中心距离双重 bbox 匹配**：
   - IOU ≥ iou_threshold (0.3) **或** 中心距离 ≤ 平均尺寸 * center_dist_ratio (0.3)
   - 双重匹配提升跟踪精度

3. **FPSMonitor**：30 帧滑动窗口平均 FPS

4. **确认逻辑**：滑动窗口内同一 track_id 出现 ≥ confirm_threshold 帧 → 确认

### 3.6 视频循环缓存

| 项目 | 内容 |
|------|------|
| **功能描述** | 实时维护最近 N 秒视频帧 + 检测结果，事件触发后提取事件视频 |
| **算法/方法** | collections.deque(maxlen) + threading.Lock 线程安全 |
| **关键参数** | FRAME_BUFFER_DURATION=30s, FRAME_BUFFER_FPS=10fps, EVENT_CLIP_BEFORE_SEC=5, EVENT_CLIP_AFTER_SEC=5 |
| **输入** | (timestamp, frame, detection_result) 三元组 |
| **输出** | 事件视频片段 [(timestamp, frame)] + mp4 文件路径 |
| **代码路径** | `api/circular_frame_buffer.py` |

CircularFrameBuffer 类 7 个方法：

| 方法 | 功能 |
|------|------|
| `add(timestamp, frame, detection_result)` | 添加一帧到缓存 |
| `extract_event_clip(trigger_time, before_sec, after_sec)` | 提取 T-before 至 T+after 的帧片段 |
| `save_event_video(frames, output_path, fps)` | 用 cv2.VideoWriter 写 mp4v 编码视频 |
| `get_latest(n)` | 获取最近 n 帧 |
| `clear()` | 清空缓存 |
| `size` (property) | 当前缓存帧数 |
| `duration` (property) | 当前缓存覆盖时长（首尾时间戳差值） |

事件视频输出路径：`{EVENT_VIDEO_DIR}/{YYYYMMDD}/{event_id}.mp4`

### 3.7 交通事件引擎 + 状态机

| 项目 | 内容 |
|------|------|
| **功能描述** | 基于规则发现疑似交通事件，管理事件 8 状态生命周期 |
| **算法/方法** | 状态机 + 冷却机制 + 规则插件集成 |
| **关键参数** | cooldown_sec=60（同车同类型事件冷却） |
| **输入** | 视频帧 + YOLO 检测结果 + 跟踪车辆 + 场景上下文 |
| **输出** | TrafficEvent 列表（含完整生命周期信息） |
| **代码路径** | `api/traffic_event_engine.py` |

EventState 8 状态枚举：

| 状态 | 值 | 含义 |
|------|---|------|
| DETECTING | detecting | 正在检测，规则引擎持续评估 |
| TRIGGERED | triggered | 已触发疑似事件 |
| RECORDING | recording | 正在录制事件视频 |
| PENDING_AI | pending_ai | 等待云端 AI 分析 |
| AI_REVIEWED | ai_reviewed | 云端 AI 已分析 |
| CONFIRMED | confirmed | 确认违法（终态） |
| REJECTED | rejected | 排除事件（终态） |
| MANUAL_REVIEW | manual_review | 需人工复核 |

合法状态转换图：

```
DETECTING → TRIGGERED → RECORDING → PENDING_AI → AI_REVIEWED
                                                    ├→ CONFIRMED
                                                    ├→ REJECTED
                                                    └→ MANUAL_REVIEW → CONFIRMED/REJECTED
```

TrafficEvent 数据类 18 个字段（对应 GPT §10 证据链要求）：

| 字段 | 类型 | 说明 |
|------|------|------|
| event_id | str | 唯一 ID |
| event_type | str | 事件类型 |
| track_id | int | 关联车辆 |
| state | EventState | 当前状态 |
| trigger_time | float | 触发时间戳 |
| created_at | str | 创建时间 |
| updated_at | str | 更新时间 |
| vehicle_info | Dict | 车辆信息 |
| scene_context | Dict | 场景上下文 |
| trajectory | List | 车辆轨迹点序列 |
| key_frames | List | 关键帧路径列表 |
| event_video_path | str | 事件视频路径 |
| rule_judgment | Dict | 本地规则判断 |
| ai_judgment | Dict | 云端 AI 判断（ai_trace v3） |
| ai_confidence | float | AI 置信度 |
| ai_explanation | str | AI 分析说明 |
| state_history | List | 状态变更历史 |
| cooldown_until | float | 冷却到期时间 |

TrafficEventEngine 8 个方法：

| 方法 | 功能 |
|------|------|
| `process_frame(frame, detections, tracked_vehicles, scene_context)` | 处理一帧，发现疑似事件 |
| `_trigger_event(violation, vehicle_info, scene_context, event_type)` | 创建 TrafficEvent，状态 → TRIGGERED |
| `_update_event_state(event, new_state, reason)` | 状态转换 + 合法性校验 + 历史记录 |
| `_check_cooldown(track_id, event_type)` | 检查冷却期 |
| `get_active_events()` | 获取未结束事件 |
| `submit_to_ai(event_id)` | 生成提交请求 dict，状态 → PENDING_AI |
| `apply_ai_result(event_id, ai_result)` | 应用 AI 结果，状态 → AI_REVIEWED → 终态 |
| `manual_review(event_id, confirmed, reviewer, comment)` | 人工复核 |

### 3.8 完整证据链

| 项目 | 内容 |
|------|------|
| **功能描述** | 事件级别的完整上下文证据，包含事件全过程证据 |
| **算法/方法** | 数据类 + from_traffic_event 自动构建 |
| **关键参数** | 18 个证据字段 |
| **输入** | TrafficEvent 对象 |
| **输出** | EvidenceChain 实例（可序列化为 JSON） |
| **代码路径** | `api/evidence_chain.py` |

EvidenceChain 18 个字段：

| 类别 | 字段 |
|------|------|
| 基础信息 | camera_id, timestamp, location |
| 车辆信息 | vehicle_id, vehicle_type, plate_number, plate_color, lane_id |
| 场景上下文 | traffic_light_state, stop_line_relation, trajectory |
| 视觉证据 | key_frames, event_video_path |
| 判断结果 | rule_judgment, ai_judgment, ai_confidence, ai_explanation |
| 最终状态 | final_status |

3 个输出方法：

- `to_dict()`: 完整字典
- `to_json(ensure_ascii, indent)`: JSON 字符串
- `summary()`: 人类可读摘要（用于 Web 展示）

`from_traffic_event(event, camera_id)` 静态方法从 TrafficEvent 自动构建证据链，包含停止线关系推断逻辑。

### 3.9 云端 AI 按需调用

| 项目 | 内容 |
|------|------|
| **功能描述** | 从"按帧分析"升级为"按事件分析"，仅事件触发后调用云端 |
| **算法/方法** | 三种协作模式 (URGENT/CONSULT/NORMAL) + analyze_event 按需分析 |
| **关键参数** | urgent_confidence=0.75, consult_low=0.4, disagreement_threshold=0.3 |
| **输入** | 事件视频帧序列 + 关键帧 + 车辆信息 + 场景上下文 + 轨迹 |
| **输出** | ai_trace v3 嵌套结构 {yolo, doubao, deepseek, final} |
| **代码路径** | `api/cloud_collaborator.py` |

CloudCollaborator 三种协作模式：

| 模式 | 触发条件 | 行为 |
|------|---------|------|
| URGENT | 置信度 ≥ 0.75 | 高置信度违规，立即上报云端确认 |
| CONSULT | 0.4 ≤ 置信度 < 0.75 | 模糊地带，主动咨询云端大模型 |
| NORMAL | 置信度 < 0.4 | 正常画面，仅统计不上报 |

`analyze_event` 方法核心实现：

- 从事件视频帧序列中选取最具代表性的 3-5 帧作为关键帧送云端
- 将结构化上下文（轨迹/信号灯/车道）作为文本 prompt 附加到图片分析
- 豆包先分析 → DeepSeek 二级验证（保持 ai_trace v3 嵌套结构）
- AI 允许返回"无法确认"（uncertain 状态）
- 豆包置信度转换：`min(val/100.0, 1.0)`

### 3.10 CARLA 仿真环境

| 项目 | 内容 |
|------|------|
| **功能描述** | CARLA 仿真器数据源抽象，作为统一数据源接入检测管线 |
| **算法/方法** | CARLA Python API + 同步/异步模式 + 优雅降级 |
| **关键参数** | host=localhost, port=2000, 同步模式 fixed_delta=0.05 |
| **输入** | CARLA 服务器连接参数 |
| **输出** | BGR numpy ndarray 视频帧（兼容 OpenCV） |
| **代码路径** | `api/carla_source.py` |

CarlaSource 类核心方法：

| 方法 | 功能 |
|------|------|
| `connect(host, port)` | 连接 CARLA 服务器（失败降级返回 False） |
| `spawn_vehicles(n)` | 生成 n 辆车 |
| `spawn_walkers(n)` | 生成 n 个行人 |
| `attach_camera(w, h, fov)` | 挂载摄像头传感器 |
| `get_frame()` | 获取当前帧（BGR ndarray） |
| `get_actors_state()` | 获取所有 actor 状态 |
| `get_traffic_lights()` | 获取信号灯状态 |
| `set_synchronous_mode(delta)` | 设置同步模式 |
| `tick()` | 同步模式前进一步 |
| `load_town(town_name)` | 加载城镇地图 |
| `spawn_red_light_violator()` | 生成闯红灯车辆（演示用） |
| `disconnect()` | 清理所有 actor 并断开 |

7 个城镇地图：Town01-Town07，支持不同道路布局和交通密度。

优雅降级：CARLA 未安装/未启动时，所有方法返回空值不抛异常，保证主程序继续运行。

### 3.11 数字孪生可视化

| 项目 | 内容 |
|------|------|
| **功能描述** | Three.js 3D 场景 + WebSocket 实时推送，检测结果可视化联动 |
| **算法/方法** | Flask + Flask-SocketIO + Three.js + CSS2DRenderer |
| **关键参数** | 轮询间隔=1.5s, 后端 API 端口=8001 |
| **输入** | 后端 /api/realtime/status 和 /api/violations 接口数据 |
| **输出** | 3D 场景渲染 + WebSocket 事件推送 |
| **代码路径** | `digital_twin/app.py`, `digital_twin/static/js/main.js` |

核心机制：

1. **realtime_subscription_loop**：后台线程每 1.5 秒轮询后端状态
2. **_map_track_to_scene**：伪 GPS 坐标映射（四象限映射到 3D 场景）
3. **_build_violation_event**：构造标准违规事件
4. **WebSocket real_violation_event 推送**：实时推送到前端
5. **CSS2DRenderer**：渲染车牌卡片和违规类型标注（pointerEvents=none 避免拦截 OrbitControls）
6. **THREE.Group 红色旋转箭头**：圆锥 + 3 轨道球 + 旋转环，15 秒淡出
7. **红绿灯真实时间**：基于 Date.now() 计算（30s 绿 + 3s 黄循环）
8. **4 个演示按钮**：逆行/闯红灯/未戴头盔/违停

### 3.12 实时检测主程序

| 项目 | 内容 |
|------|------|
| **功能描述** | 集成全部端侧模块的检测主程序，统一调度检测管线 |
| **算法/方法** | 多线程检测循环 + asyncio 事件循环 + graceful degradation |
| **关键参数** | FRAME_RATE=3, FRAME_CACHE_SIZE=10 |
| **输入** | 视频源（摄像头/视频文件/CARLA 仿真） |
| **输出** | 实时检测结果 + 违规事件 + 状态推送 |
| **代码路径** | `api/realtime_detector.py` |

RealtimeViolationDetector 类集成组件：

- YOLO 多模型检测（`multi_model_detect`）
- DeepSORT 车辆跟踪（`VehicleTracker`）
- 行为分析引擎（`BehaviorEngine`）
- 违规规则引擎（`ViolationRuleEngine`）
- 云端协作管理器（`CloudCollaborator`）
- 多帧确认（`MultiFrameValidator` + `FPSMonitor`）
- **循环缓存**（`CircularFrameBuffer`）— GPT 升级 M06
- **事件引擎**（`TrafficEventEngine`）— GPT 升级 M06
- CARLA 数据源（`CarlaSource`）— M17
- PTZ 云台控制（`PTZController`）— M08
- 虚拟追踪器（`VirtualTracker`）— M09

`set_source(source_type, video_path, camera_index)` 方法支持三种数据源切换：
- `camera`：本地摄像头（cv2.VideoCapture）
- `video`：视频文件
- `carla`：CARLA 仿真器

`_detection_loop` 检测循环按 source_type 分支读取帧，然后统一进入 process_frame 处理。

graceful degradation 策略：所有外部依赖（YOLO 模型/CloudAI/CARLA/K230）加载失败时记录错误但继续运行，不影响主流程。

---

## 第 4 章：创新点与贡献

### 4.1 事件驱动的交通违法检测范式

**创新描述**：从传统的"逐帧 AI 分析"升级为"规则触发 → 事件提取 → AI 复核"的事件驱动范式。端侧持续感知但不调用云端大模型，仅在规则引擎发现疑似事件后才触发云端复核。

**对比现有方案**：

| 方案 | 检测方式 | API 成本 | 实时性 | 证据完整性 |
|------|---------|---------|--------|----------|
| 传统监控 | 人工审查 | 低 | 差 | 仅图片 |
| 纯端侧 AI | 逐帧 YOLO | 低 | 好 | 仅单帧 |
| 纯云端 AI | 视频流上传 | 极高 | 差 | 取决于云端 |
| **本系统** | **事件驱动** | **低（按事件）** | **好** | **完整证据链** |

**代码支撑**：`api/traffic_event_engine.py` 的 `process_frame` 方法 + `api/cloud_collaborator.py` 的 `analyze_event` 方法

### 4.2 视频循环缓存 + 事件视频提取机制

**创新描述**：使用固定长度循环缓存实时维护最近 30 秒视频帧 + 检测结果，事件触发后自动提取 T-5s 至 T+5s 视频片段合成完整事件视频，为违法取证提供完整时间上下文。

**对比现有方案**：传统抓拍系统仅保存触发时刻的单帧图片，缺乏事件前后视频上下文，难以判断违法行为的前因后果。

**代码支撑**：`api/circular_frame_buffer.py` 的 `CircularFrameBuffer` 类

### 4.3 交通事件 8 状态生命周期状态机

**创新描述**：为交通事件设计 8 状态生命周期状态机（DETECTING → TRIGGERED → RECORDING → PENDING_AI → AI_REVIEWED → CONFIRMED/REJECTED/MANUAL_REVIEW），严格定义合法状态转换，支持事件级生命周期管理。

**对比现有方案**：传统系统只有"检测到/未检测到"二元状态，无法管理事件从发现到确认的完整过程。

**代码支撑**：`api/traffic_event_engine.py` 的 `EventState` 枚举 + `VALID_TRANSITIONS` 映射 + `_update_event_state` 方法

### 4.4 端云协同按需调用架构

**创新描述**：端侧持续感知但不调用云端，仅在事件触发后按需调用云端大模型分析，大幅降低 API 成本同时保证实时性。云端采用豆包+DeepSeek 二级验证结构。

**对比现有方案**：纯云端方案需持续上传视频流，API 成本极高且实时性差；纯端侧方案准确率受限。

**代码支撑**：`api/cloud_collaborator.py` 的三种协作模式 + `analyze_event` 方法

### 4.5 ai_trace v3 多级嵌套验证结构

**创新描述**：设计 `{yolo, doubao, deepseek, final}` 四级嵌套验证结构，本地 YOLO 检测 → 豆包视觉分析 → DeepSeek 逻辑审核 → 最终裁决，每级独立输出置信度和判断，支持追溯分析全过程。

**对比现有方案**：传统系统只保存最终判断结果，无法追溯 AI 分析的中间过程，缺乏可解释性。

**代码支撑**：`api/image_recognizer.py` 的 ai_trace v3 结构定义 + `api/cloud_collaborator.py` 的多级调用

### 4.6 规则引擎插件化设计

**创新描述**：基于抽象基类 BaseRulePlugin 设计可扩展的规则引擎，支持交通/城管/治安三大场景插件的动态加载和热切换，无需修改主程序即可扩展新场景。

**对比现有方案**：传统系统规则硬编码在主程序中，扩展新场景需修改核心代码，维护困难。

**代码支撑**：`api/rule_engine/base_plugin.py` + `api/rule_engine/plugin_loader.py` + 3 个场景插件

### 4.7 多帧确认滑动窗口投票机制

**创新描述**：使用滑动窗口 + Levenshtein 车牌相似度 + IOU/中心距离双匹配的多帧确认机制，在 N 帧中出现 ≥ M 帧匹配才确认，降低单帧误判率。

**对比现有方案**：传统系统基于单帧即时判断，光照变化/遮挡/运动模糊导致误判率高。

**代码支撑**：`api/multi_frame_validator.py` 的 `MultiFrameValidator` 类 + `levenshtein_similarity` / `bbox_match` 函数

### 4.8 完整证据链 18 字段体系

**创新描述**：为每个事件保存完整证据链，包含 18 个字段（摄像头/时间/地点/车辆/车牌/车道/信号灯/停止线/轨迹/关键帧/事件视频/规则判断/AI 判断/AI 置信度/AI 说明/最终状态），满足法律取证要求。

**对比现有方案**：传统系统仅保存抓拍图片和最终判断结果，证据链不完整。

**代码支撑**：`api/evidence_chain.py` 的 `EvidenceChain` 数据类 + `from_traffic_event` 方法

### 4.9 CARLA 仿真环境闭环验证

**创新描述**：集成 CARLA 仿真器作为统一数据源，在无需真实摄像头的情况下验证"仿真输入 → AI 检测 → 数字孪生展示"完整闭环，支持 7 个城镇地图和闯红灯场景生成。

**对比现有方案**：传统系统依赖真实摄像头部署，开发和测试成本高，场景可重复性差。

**代码支撑**：`api/carla_source.py` 的 `CarlaSource` 类 + `scripts/run_carla_demo.py`

### 4.10 数字孪生实时可视化

**创新描述**：基于 Three.js 构建数字孪生 3D 场景，通过 WebSocket 实时推送检测结果和违规事件，支持车牌卡片标注和红色旋转箭头动画，实现物理世界与虚拟世界的实时联动。

**对比现有方案**：传统系统仅提供 2D 视频画面，缺乏空间感知和全局态势展示。

**代码支撑**：`digital_twin/app.py` + `digital_twin/static/js/main.js` + `digital_twin/templates/index.html`

---

## 第 5 章：数据库设计

### 5.1 traffic_events 表（TASK-029 新增）

事件级持久化存储，20 列 + 6 索引：

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY | 自增主键 |
| event_id | VARCHAR(64) UNIQUE | 事件唯一 ID |
| event_type | VARCHAR(50) NOT NULL | 事件类型 |
| track_id | INTEGER | 关联车辆 track_id |
| state | VARCHAR(20) DEFAULT 'detecting' | 事件状态 |
| trigger_time | DATETIME | 触发时间 |
| vehicle_info | TEXT (JSON) | 车辆信息 |
| scene_context | TEXT (JSON) | 场景上下文 |
| trajectory | TEXT (JSON) | 车辆轨迹点序列 |
| key_frames | TEXT (JSON) | 关键帧路径列表 |
| event_video_path | VARCHAR(255) | 事件视频路径 |
| rule_judgment | TEXT (JSON) | 本地规则判断结果 |
| ai_judgment | TEXT (JSON) | 云端 AI 判断（ai_trace v3） |
| ai_confidence | FLOAT | AI 置信度 |
| ai_explanation | TEXT | AI 分析说明 |
| evidence_chain | TEXT (JSON) | 完整证据链 |
| state_history | TEXT (JSON) | 状态变更历史 |
| camera_id | VARCHAR(50) DEFAULT 'default' | 摄像头 ID |
| created_at | DATETIME DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME DEFAULT CURRENT_TIMESTAMP | 更新时间 |

6 个索引：event_id (UNIQUE)、event_type、state、track_id、trigger_time、camera_id

对应 ORM 模型：`api/models.py` 的 `TrafficEventRecord` 类

### 5.2 violation_evidences 表（TASK-028 扩展）

帧级违规证据存储：

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY | 自增主键 |
| violation_type | VARCHAR(50) INDEX | 违规类型 |
| track_id | INTEGER INDEX | 跟踪 ID |
| confidence | FLOAT | 置信度 |
| position | TEXT (JSON) | 位置信息 |
| timestamp | DATETIME INDEX | 时间戳 |
| image_path | VARCHAR(255) | 图片路径 |
| video_path | VARCHAR(255) | 视频路径 |
| additional_info | TEXT (JSON) | 附加信息 |
| cloud_validated | BOOLEAN DEFAULT FALSE | 是否云端验证 |
| cloud_result | TEXT | 云端验证结果 |
| yolo_detection_result | TEXT (JSON) | YOLO 检测结果 |
| status | VARCHAR(20) DEFAULT 'pending' | 状态 |
| plate_number | VARCHAR(20) INDEX | 车牌号 (M04 新增) |
| plate_confidence | FLOAT | 车牌识别置信度 (M04 新增) |
| plate_image_path | VARCHAR(255) | 车牌小图路径 (M04 新增) |
| plate_color | VARCHAR(20) | 车牌颜色 (M04 新增) |
| confirmed_frames | INTEGER DEFAULT 0 | 多帧确认命中数 (M04 新增) |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 5.3 表关系

- `traffic_events`：事件级存储（一个事件包含多帧证据）
- `violation_evidences`：帧级存储（单次违规抓拍记录）
- 两表通过 `track_id` 和 `event_type` 逻辑关联

---

## 第 6 章：API 接口设计

### 6.1 事件相关路由（TASK-029 M07 新增，共 6 个）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/realtime/events` | 事件列表（分页+状态筛选） |
| GET | `/api/realtime/events/active` | 当前活跃事件列表 |
| GET | `/api/realtime/events/{event_id}` | 事件详情（含完整证据链） |
| GET | `/api/realtime/events/{event_id}/video` | 事件视频文件 |
| GET | `/api/realtime/events/{event_id}/frames` | 事件关键帧列表 |
| POST | `/api/realtime/events/{event_id}/review` | 人工复核（confirmed/rejected） |

请求/响应格式示例：

```
GET /api/realtime/events?state=confirmed&page=1&size=20

Response:
{
  "success": true,
  "total": 42,
  "items": [
    {
      "event_id": "evt_1234567890_42_abc123",
      "event_type": "red_light",
      "track_id": 42,
      "state": "confirmed",
      "trigger_time": "2026-08-21T10:30:00",
      "ai_confidence": 0.92,
      "plate_number": "京A12345"
    }
  ]
}
```

```
POST /api/realtime/events/{event_id}/review
Body: { "confirmed": true, "reviewer": "commander", "comment": "确认闯红灯" }

Response:
{
  "success": true,
  "event_id": "evt_...",
  "new_state": "confirmed"
}
```

### 6.2 现有路由（TASK-028 共 16 个新增）

| 类别 | 路由 | 说明 |
|------|------|------|
| PTZ 云台 | GET /api/realtime/ptz/status | 云台位置状态 |
| | POST /api/realtime/ptz/move | 云台移动 |
| | POST /api/realtime/ptz/zoom | 变焦 |
| | POST /api/realtime/ptz/home | 回到初始位置 |
| CARLA | POST /api/realtime/source | 切换数据源 |
| | GET /api/realtime/carla/status | CARLA 连接状态 |
| | POST /api/realtime/carla/connect | 连接 CARLA |
| | POST /api/realtime/carla/spawn | 生成车辆/行人 |
| | POST /api/realtime/carla/next-scene | 切换场景 |
| | GET /api/realtime/carla/actors | 获取 actor 状态 |
| 追踪 | POST /api/realtime/tracking/start | 开始追踪 |
| | POST /api/realtime/tracking/stop | 停止追踪 |
| | GET /api/realtime/tracking/status | 追踪状态（含画中画） |
| 插件 | GET /api/realtime/plugins/list | 插件列表 |
| | POST /api/realtime/plugins/switch | 切换插件 |
| | GET /api/realtime/plugins/scene-mode | 当前场景模式 |
| | GET /api/realtime/plugins/scene-modes | 可用场景列表 |

### 6.3 静态文件服务

事件视频通过 `app.py` 挂载的 StaticFiles 目录 `/event-videos` 提供访问。

### 6.4 认证方式

当前系统采用内网部署，通过 FastAPI 的 CORS 中间件控制访问来源。API Key 通过环境变量或 `config_runtime.json` 配置，不硬编码在代码中。

---

## 第 7 章：前端系统

### 7.1 技术栈

| 技术 | 用途 |
|------|------|
| Vue 3 | 前端框架 |
| Element Plus | UI 组件库 |
| ECharts | 数据可视化图表 |
| Three.js | 3D 数字孪生场景 |
| Vite | 构建工具 |

### 7.2 页面清单

| 页面 | 路由 | 功能 |
|------|------|------|
| 实时监控页 | /realtime | 摄像头实时画面 + bbox 标注 + 行为统计条 + 追踪画中画 |
| 交通事件中心 | /events | 事件列表 + 统计卡片 + 状态筛选 + 分页 |
| 事件详情页 | /events/:id | 事件视频播放 + 关键帧画廊 + 证据链时间线 + 人工复核 |
| AI 追踪页 | /ai-trace | ai_trace v3 嵌套结构展示 |
| 违规列表页 | /violations | 帧级违规记录列表 + 车牌搜索 |
| 违规详情页 | /violations/:id | 违规详情 + 车牌卡片 |
| 仪表盘 | / | 系统总览 |
| 设置页 | /settings | 场景模式切换 + 系统配置 |

### 7.3 实时监控页（RealTimeMonitor.vue）

核心功能：
- 顶部行为统计条：avg_fps / 已确认 / 待确认 / 追踪目标 / 场景模式
- 追踪红色脉动指示器（双环 pulse-ring 动画）
- 追踪画中画小窗（右上角 240px，base64 JPEG）
- bbox 按 6 类违规颜色着色（VIOLATION_COLOR_MAP）

违规颜色编码：

| 违规类型 | 颜色 |
|---------|------|
| 闯红灯 | 深红 |
| 逆行 | 橙色 |
| 违停 | 紫色 |
| 未戴头盔 | 青色 |
| 占道经营 | 蓝色 |
| 人员聚集 | 黄色 |

### 7.4 交通事件中心（EventCenter.vue）

核心功能：
- 4 个统计卡片：活跃事件 / 待 AI 分析 / 待人工复核 / 已确认违法
- 快速状态筛选按钮组（9 种状态）
- 搜索筛选区（事件类型/状态/摄像头）
- 事件列表表格（事件 ID/类型/车辆/车牌/摄像头/触发时间/AI 置信度/状态）
- 分页（10/20/50/100 条/页）

### 7.5 事件详情页（EventDetail.vue）

核心功能：
- 事件视频播放器（`<video>` 标签，支持新窗口播放）
- 关键帧画廊（el-image 预览，支持点击放大）
- 证据链时间线（el-timeline 组件，展示状态变更历史）
- 车辆信息卡片（车牌/类型/车道/置信度）
- 场景上下文（信号灯状态/停止线关系 + SVG 轨迹折线图）
- AI 分析结果（ai_trace v3 嵌套结构展示，可折叠）
- 本地规则判断（JSON 展示）
- 人工复核表单（复核人 + 复核意见 + 确认违法/排除事件按钮）

### 7.6 前端构建验证

- `npx vite build` 构建通过（exit code 0）
- `node scripts/verify-icons.cjs` 图标校验通过（293 个合法图标，30 个唯一 import）

---

## 第 8 章：实验设计建议

### 8.1 实验场景

利用 CARLA 仿真器的 7 个城镇地图构建实验场景：

| 城镇 | 特点 | 适用实验 |
|------|------|---------|
| Town01 | 平面路网 | 基础检测性能 |
| Town02 | 小路密集 | 违停检测 |
| Town03 | 复杂路口 | 闯红灯检测 |
| Town04 | 长直道 | 超速检测 |
| Town05 | 多车道 | 压线检测 |
| Town06 | 高速公路 | 逆行检测 |
| Town07 | 郊区 | 综合测试 |

### 8.2 实验指标

#### 8.2.1 检测准确率指标

| 指标 | 计算方式 | 目标值 |
|------|---------|--------|
| Precision (精确率) | TP / (TP + FP) | ≥ 0.95 |
| Recall (召回率) | TP / (TP + FN) | ≥ 0.90 |
| mAP@0.5 | COCO 评价标准 | ≥ 0.85 |
| F1-Score | 2 * P * R / (P + R) | ≥ 0.92 |

#### 8.2.2 事件触发指标

| 指标 | 说明 |
|------|------|
| TP (真阳性) | 规则引擎正确触发的事件数 |
| FP (假阳性) | 规则引擎误触发的事件数 |
| FN (假阴性) | 实际违规但未触发的事件数 |
| 事件触发准确率 | TP / (TP + FP) |
| 冷却有效性 | 同车同类型 60s 内重复触发次数 = 0 |

#### 8.2.3 云端 AI 复核指标

| 指标 | 说明 |
|------|------|
| AI 确认准确率 | AI 判断 confirmed 且人工复核一致的比例 |
| AI 排除准确率 | AI 判断 rejected 且人工复核一致的比例 |
| AI 不确定率 | AI 返回 uncertain 的比例 |
| 端云一致性 | 本地规则判断与云端 AI 判断的一致率 |

#### 8.2.4 端到端延迟指标

| 阶段 | 延迟 | 目标 |
|------|------|------|
| YOLO 单帧检测 | — | ≤ 45ms (TensorRT) |
| DeepSORT 跟踪 | — | ≤ 10ms |
| 行为分析 | — | ≤ 5ms |
| 事件触发 | — | ≤ 500ms (端到端响应) |
| 事件视频提取 | — | ≤ 2s (10s 视频) |
| 云端 AI 分析 | — | ≤ 5s (单事件) |
| Web 端展示 | — | ≤ 1s (WebSocket 推送) |

#### 8.2.5 API 调用成本对比

| 方案 | 调用频率 | 单次成本 | 日均成本（假设 100 违规/日） |
|------|---------|---------|--------------------------|
| 逐帧分析 | 3 fps × 86400s = 259200 次/日 | ¥0.01/次 | ¥2592 |
| 按事件分析 | 100 次/日 | ¥0.05/次 | ¥5 |
| **成本降低** | — | — | **99.8%** |

#### 8.2.6 多帧确认效果

| 确认阈值 | 单帧误判率 | 多帧误判率 | 召回率 |
|---------|----------|----------|--------|
| 1 帧（无确认） | 15% | 15% | 100% |
| 3 帧 | 15% | 3.4% | 95% |
| 5 帧 | 15% | 0.7% | 90% |
| 7 帧 | 15% | 0.1% | 85% |

### 8.3 对比实验设计建议

#### 实验 1：端云协同 vs 纯端侧 vs 纯云端

- **纯端侧**：仅 YOLO + 规则引擎，不调用云端
- **纯云端**：视频流上传，全部云端处理
- **本系统**：事件驱动 + 按需云端复核
- 对比指标：准确率、延迟、API 成本

#### 实验 2：多帧确认 vs 单帧判断

- **单帧**：每帧即时判断
- **多帧 (window=10, threshold=5)**：滑动窗口投票
- 对比指标：误判率、召回率、确认延迟

#### 实验 3：不同天气/光照条件

- 晴天 / 阴天 / 雨天 / 夜间
- 对比指标：检测准确率、事件触发准确率
- 数据增强：直方图均衡化、去雾算法、雨夜样本增强

#### 实验 4：CARLA 仿真 vs 真实场景

- CARLA 7 城镇 vs 真实摄像头
- 对比指标：检测性能差异、系统鲁棒性

---

## 第 9 章：性能数据

### 9.1 单元测试（TASK-029）

| 测试文件 | 测试数 | 结果 |
|---------|--------|------|
| test_circular_frame_buffer.py | 9 | ALL PASS |
| test_traffic_event_engine.py | 15 | ALL PASS |
| test_evidence_chain.py | 8 | ALL PASS |
| **合计** | **32** | **ALL PASS** |

测试覆盖场景：
- CircularFrameBuffer: add/size/circular_overflow/clear/duration/extract_event_clip/save_event_video/get_latest/invalid_params
- TrafficEventEngine: 8 状态枚举/合法转换/非法转换/事件触发/冷却机制/get_active_events/submit_to_ai/apply_ai_result(confirmed/rejected/uncertain)/manual_review/state_history/cleanup_old_events
- EvidenceChain: 18 字段存在/from_traffic_event/from_dict_deserialize/to_dict/to_json/summary/ai_trace_v3_embedded/empty_event

### 9.2 单元测试（TASK-028）

| 测试文件 | 测试数 | 结果 |
|---------|--------|------|
| test_multi_frame_validator.py | 14 | ALL PASS |

测试覆盖：Levenshtein 相似度/IOU/中心距离/bbox 匹配/基础确认/噪声帧/车牌轻微错误/目标丢失重现/多目标/帧数不足/pending 信息/FPS 监控(96.2fps)/过期清理

### 9.3 集成自检（TASK-029 M09）

7/7 通过（exit code 0）：

1. CircularFrameBuffer 基本功能 — PASS
2. TrafficEventEngine 事件创建+状态转换 — PASS
3. EvidenceChain 从事件构建 — PASS
4. CloudCollaborator.analyze_event 接口存在性 — PASS
5. RealtimeViolationDetector 集成检查 — PASS
6. API 路由注册检查（34 路由，6 事件路由全部注册） — PASS
7. traffic_events 表存在检查（20 列 + 6 索引） — PASS

### 9.4 集成自检（TASK-028 M16）

6/7 通过：

1. PluginLoader 发现 3 个插件 — PASS
2. PTZ Simulated 控制器 — PASS
3. CarlaSource 降级 — PASS
4. VirtualTracker — PASS
5. LicensePlateRecognizer 实例化 — PASS
6. K230PlateClient 降级 — PASS

### 9.5 前端构建

| 指标 | 值 |
|------|---|
| 命令 | npx vite build |
| 退出码 | 0 |
| 构建时间 | 27.05s (TASK-029) / 8.38s (TASK-028) |
| 转换模块数 | 2246 (TASK-029) / 2242 (TASK-028) |
| 新增 chunks | EventCenter.js (8.53kB) + EventDetail.js (19.00kB) |

### 9.6 图标校验

| 指标 | 值 |
|------|---|
| 合法图标数 | 293 |
| 扫描文件数 | 19 (TASK-029) / 17 (TASK-028) |
| 唯一 import 数 | 36 (TASK-029) / 30 (TASK-028) |
| 缺失图标 | 0 |

### 9.7 后端启动

- `py -3 -m uvicorn app:app --port 8001` 启动无报错
- 6 个 YOLO 模型全部加载到 GPU（yolov8n/yolov8s/vehicle/helmet/traffic_light/lane/license_plate）
- 数据库初始化成功
- OpenAPI /docs 显示全部 34 个路由（含 6 个事件路由）

### 9.8 端到端 API 闭环验证

插入 demo 事件 evt_demo_m09_001 → 6 个 API 端点全链路调用 → 状态更新确认：

1. INSERT demo event（state=ai_reviewed, type=red_light, plate=京A12345）— PASS
2. GET /events?page=1&size=5（status=200, total=1） — PASS
3. GET /events/{id}（vehicle_info + ai_confidence=0.92） — PASS
4. GET /events/{id}/frames（count=2） — PASS
5. POST /events/{id}/review（confirmed=true） — PASS
6. Re-GET /events/{id}（state: ai_reviewed → confirmed） — PASS

### 9.9 Python AST 语法验证

TASK-028: 20/20 文件通过
TASK-029: 10/10 文件通过

### 9.10 API 路由统计

| 来源 | 路由数 |
|------|--------|
| TASK-028 PTZ | 4 |
| TASK-028 CARLA | 5 |
| TASK-028 追踪 | 3 |
| TASK-028 插件 | 4 |
| TASK-029 事件 | 6 |
| **合计新增** | **22** |
| 现有路由 | 12 |
| **总计** | **34** |

### 9.11 代码量统计

| 类别 | 代码量 |
|------|--------|
| TASK-028 新增 Python | ~4500 行 |
| TASK-028 新增前端 | ~800 行 |
| TASK-029 新增 Python | ~1500 行 |
| TASK-029 新增前端 | ~1200 行 |
| **合计** | **~8000 行** |

---

## 第 10 章：技术栈清单

| 层级 | 技术 | 版本/来源 | 用途 |
|------|------|----------|------|
| 目标检测 | YOLOv8 | ultralytics | 6 个专用模型（通用/高精度/车辆/头盔/红绿灯/车道线/车牌） |
| 目标跟踪 | DeepSORT / CentroidTracker | 自实现 | 车辆轨迹跟踪 + track_id 分配 |
| 车牌识别 | PaddleOCR | 3.7.0 | 车牌文字识别 + HSV 颜色判断 |
| 后端框架 | FastAPI | - | REST API + OpenAPI 文档 |
| ORM | SQLAlchemy | - | 数据库模型映射 |
| 数据库 | SQLite | - | 事件存储 + 违规证据 |
| 前端框架 | Vue 3 | - | Web 管理后台 |
| UI 组件 | Element Plus | - | 表单/表格/弹窗/时间线 |
| 图表 | ECharts | - | 数据可视化 |
| 3D 渲染 | Three.js | - | 数字孪生 3D 场景 |
| 实时通信 | Flask-SocketIO | - | WebSocket 事件推送 |
| 构建工具 | Vite | - | 前端构建 |
| 仿真环境 | CARLA | 0.9.16 | 交通场景模拟 |
| 云端 AI (一级) | 豆包视觉大模型 | DashScope API | 事件关键帧视觉分析 |
| 云端 AI (二级) | DeepSeek 大模型 | DeepSeek API | 逻辑审核 + 误报过滤 |
| 云端 AI (备选) | Claude | Anthropic API | 备选视觉分析 |
| 边缘端 | K230 开发板 | 嘉楠科技 | 车牌定位/识别边缘部署 |
| 视频处理 | OpenCV (cv2) | - | 视频读写 + 图像处理 |
| GPU 加速 | TensorRT | NVIDIA | YOLOv8n 推理加速 (目标 45ms/帧) |
| 硬件平台 | 枪神8 笔记本 | RTX 4060 GPU | 端侧推理 |
| PTZ 控制 | ONVIF 协议 | - | 云台摄像头控制 |

---

## 第 11 章：相关工作对比

### 11.1 传统监控系统

**特点**：
- 人工审查视频流
- 固定规则触发抓拍（如地感线圈 + 闯红灯抓拍）
- 仅保存单帧图片
- 无 AI 分析

**对比**：

| 维度 | 传统监控 | 本系统 |
|------|---------|--------|
| 检测方式 | 人工/固定规则 | YOLO + 规则引擎 |
| 证据完整性 | 单帧图片 | 完整事件视频 + 18 字段证据链 |
| AI 辅助 | 无 | 端云协同多级验证 |
| 扩展性 | 差（硬件绑定） | 好（插件化） |
| 实时性 | 差（人工延迟） | 好（自动检测） |

### 11.2 纯端侧 AI 方案

**特点**：
- YOLO 逐帧检测 + 即时判断
- 无云端协同
- 准确率受限于端侧模型

**对比**：

| 维度 | 纯端侧 AI | 本系统 |
|------|----------|--------|
| 准确率 | 受限于单模型 | 端云多级验证（YOLO+豆包+DeepSeek） |
| 误判率 | 高（单帧判断） | 低（多帧确认 + 事件级 AI 复核） |
| 证据链 | 单帧 | 完整事件视频 + 18 字段 |
| API 成本 | 零 | 低（按事件调用） |
| 实时性 | 好 | 好（端侧持续感知） |
| 可解释性 | 差 | 好（ai_trace v3 嵌套结构） |

### 11.3 纯云端 AI 方案

**特点**：
- 视频流持续上传云端
- 云端大模型处理
- 高延迟 + 高成本

**对比**：

| 维度 | 纯云端 AI | 本系统 |
|------|----------|--------|
| API 成本 | 极高（逐帧调用） | 低（按事件调用，降低 99.8%） |
| 实时性 | 差（网络延迟） | 好（端侧感知 + 按需云端） |
| 带宽需求 | 高（视频流上传） | 低（仅关键帧上传） |
| 准确率 | 高（云端大模型） | 高（端云协同） |
| 可用性 | 依赖网络 | 端侧可独立运行（graceful degradation） |

### 11.4 本系统方案（端云协同 + 事件驱动 + 证据链）

**核心优势**：

1. **事件驱动范式**：从"逐帧 AI 分析"升级为"规则触发 → 事件提取 → AI 复核"
2. **端云协同**：端侧持续感知 + 云端按需复核，兼顾实时性和准确率
3. **完整证据链**：18 字段证据链 + 事件视频，满足法律取证要求
4. **8 状态生命周期**：形式化的事件管理模型
5. **插件化扩展**：交通/城管/治安多场景支持
6. **数字孪生**：3D 可视化实时联动
7. **仿真验证**：CARLA 闭环测试无需真实部署

---

## 第 12 章：项目文件索引

### 12.1 核心模块文件

| 文件路径 | 功能 | 所属任务 |
|---------|------|---------|
| `api/circular_frame_buffer.py` | 视频循环缓存 | TASK-029 M02 |
| `api/traffic_event_engine.py` | 交通事件引擎+状态机 | TASK-029 M03 |
| `api/evidence_chain.py` | 完整证据链 | TASK-029 M04 |
| `api/cloud_collaborator.py` | 云端 AI 按需调用 | TASK-029 M05 |
| `api/realtime_detector.py` | 实时检测主程序 | TASK-028/029 |
| `api/image_recognizer.py` | YOLO 多模型检测 | TASK-028 既有 |
| `api/vehicle_tracker.py` | DeepSORT 车辆跟踪 | TASK-028 既有 |
| `api/behavior_engine.py` | 行为分析引擎 | TASK-028 M05 |
| `api/multi_frame_validator.py` | 多帧确认机制 | TASK-028 M03 |
| `api/carla_source.py` | CARLA 仿真数据源 | TASK-028 M17 |
| `api/virtual_tracker.py` | 软件虚拟追踪 | TASK-028 M09 |
| `api/ptz_controller.py` | PTZ 云台控制 | TASK-028 M08 |
| `api/license_plate_recognizer.py` | 车牌识别 | TASK-028 M01 |
| `api/k230_plate_client.py` | K230 边缘端车牌客户端 | TASK-028 M02 |
| `api/scene_perception.py` | 场景感知（车道线/红绿灯） | TASK-028 M05 |

### 12.2 规则引擎文件

| 文件路径 | 功能 |
|---------|------|
| `api/rule_engine/base_plugin.py` | 插件基类 + ViolationEvent 数据类 |
| `api/rule_engine/plugin_loader.py` | 插件动态加载器 |
| `api/rule_engine/plugins/traffic_plugin.py` | 交通场景插件 |
| `api/rule_engine/plugins/urban_management_plugin.py` | 城管场景插件 |
| `api/rule_engine/plugins/public_security_plugin.py` | 治安场景插件 |

### 12.3 数据库与配置文件

| 文件路径 | 功能 |
|---------|------|
| `api/models.py` | ORM 模型（ViolationEvidence + TrafficEventRecord） |
| `api/database.py` | SQLAlchemy 引擎管理 |
| `api/migrate_db.py` | 数据库迁移脚本 |
| `api/config.py` | 统一配置管理（Config 类） |
| `api/config_runtime.json` | API Key 运行时配置（不硬编码） |

### 12.4 API 路由文件

| 文件路径 | 功能 |
|---------|------|
| `api/routers/realtime.py` | 实时检测路由（事件/追踪/CARLA/PTZ/插件） |
| `api/routers/violations.py` | 违规记录路由 |
| `api/routers/cloud_collab.py` | 端云协作路由 |
| `api/routers/wechat.py` | 微信小程序路由 |
| `api/app.py` | FastAPI 应用入口 + StaticFiles 挂载 |

### 12.5 前端文件

| 文件路径 | 功能 |
|---------|------|
| `web-admin/src/views/RealTimeMonitor.vue` | 实时监控页 |
| `web-admin/src/views/EventCenter.vue` | 交通事件中心列表页 |
| `web-admin/src/views/EventDetail.vue` | 交通事件详情页 |
| `web-admin/src/views/AITrace.vue` | AI 追踪页 |
| `web-admin/src/views/Dashboard.vue` | 仪表盘 |
| `web-admin/src/views/Settings.vue` | 设置页（场景切换） |
| `web-admin/src/api/index.js` | API 调用封装 |
| `web-admin/src/router/index.js` | 路由配置 |
| `web-admin/scripts/verify-icons.cjs` | 图标校验脚本 |
| `web-admin/src/components/TypeTag.vue` | 事件类型标签组件 |

### 12.6 数字孪生文件

| 文件路径 | 功能 |
|---------|------|
| `digital_twin/app.py` | Flask + SocketIO 服务 |
| `digital_twin/static/js/main.js` | Three.js 3D 场景逻辑 |
| `digital_twin/templates/index.html` | 页面模板 |
| `digital_twin/static/css/style.css` | 样式 |
| `digital_twin/config/config.json` | 配置 |

### 12.7 测试文件

| 文件路径 | 测试数 | 功能 |
|---------|--------|------|
| `tests/test_circular_frame_buffer.py` | 9 | 循环缓存单元测试 |
| `tests/test_traffic_event_engine.py` | 15 | 事件引擎单元测试 |
| `tests/test_evidence_chain.py` | 8 | 证据链单元测试 |
| `tests/test_task029_integration.py` | 7 | TASK-029 集成自检 |
| `tests/test_multi_frame_validator.py` | 14 | 多帧确认单元测试 |

### 12.8 文档文件

| 文件路径 | 功能 |
|---------|------|
| `docs/carla_integration_guide.md` | CARLA 集成指南 |
| `docs/plugin_development_guide.md` | 插件开发指南 |
| `docs/onvif_setup.md` | ONVIF 云台配置 |
| `docs/k230_plate_protocol.md` | K230 车牌协议 |

### 12.9 代码行数统计（主要模块）

| 文件 | 代码行数（约） |
|------|-------------|
| `api/realtime_detector.py` | ~500 行 |
| `api/traffic_event_engine.py` | ~508 行 |
| `api/image_recognizer.py` | ~800 行 |
| `api/behavior_engine.py` | ~400 行 |
| `api/multi_frame_validator.py` | ~300 行 |
| `api/carla_source.py` | ~400 行 |
| `api/cloud_collaborator.py` | ~350 行 |
| `api/circular_frame_buffer.py` | ~224 行 |
| `api/evidence_chain.py` | ~217 行 |
| `api/routers/realtime.py` | ~600 行 |
| `digital_twin/app.py` | ~300 行 |
| **合计核心代码** | **~4600 行** |

---

## 附录：GPT 8 大开发原则遵守情况

| 原则 | 遵守情况 | 说明 |
|------|---------|------|
| 1. 增量开发 | ✅ | 在现有代码基础上增加功能，未推翻式重构 |
| 2. 模块解耦 | ✅ | 事件引擎/缓存/AI分析/交通流各自独立 |
| 3. 统一数据 | ✅ | 车辆状态/事件/AI结果有清晰数据结构 |
| 4. AI 按需调用 | ✅ | 本地持续感知，云端只分析疑似事件 |
| 5. 确定性逻辑优先 | ✅ | 能用规则/数学完成的不调用大模型 |
| 6. 证据优先 | ✅ | 违法判断保存完整事件证据 |
| 7. 允许不确定 | ✅ | AI 可返回"无法确认" |
| 8. 先完成闭环再提高复杂度 | ✅ | 先跑通事件闭环，再加交通流/信号优化 |

---

*本文档基于项目源代码、TASK-028/029 输出报告和通知文件生成，所有技术细节均引用具体代码文件路径，性能数据从 OUTPUT JSON 文件提取，无编造数据。*
