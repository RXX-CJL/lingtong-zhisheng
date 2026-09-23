# TASK-009 实时摄像头检测与系统联动

## 一、任务概述

**任务编号**: TASK-009
**任务名称**: 实时摄像头检测 + 违规识别 + 数字孪生联动
**预计耗时**: 4-6小时
**核心目标**: 让用户插上摄像头就能实时看到违规检测效果，并触发端云协作和数字孪生更新

**参考文件**: `e:\output\1\zhitong\blind_yun.py`（已实现摄像头检测、YOLO、云端AI交互）

---

## 二、执行步骤

### 第一阶段：实时检测核心模块

#### 步骤1：创建实时检测服务 `realtime_detector.py`

**文件位置**: `e:\output\1\api\realtime_detector.py`

**功能**: 基于参考文件，整合智瞳系统的违规检测逻辑

```python
class RealtimeViolationDetector:
    """
    实时违规检测服务
    - 摄像头采集
    - 本地YOLO检测（每秒处理2-5帧）
    - 违规规则引擎判断
    - 触发端云协作
    - 保存证据
    - 推送数字孪生
    """

    def __init__(self):
        self.cap = None
        self.running = False
        self.cloud_collaborator = CloudCollaborator()
        self.violation_engine = ViolationRuleEngine()

    def start_camera(self, camera_index=0):
        """启动摄像头"""

    def start_detection(self):
        """启动检测循环"""

    def process_frame(self, frame):
        """处理单帧：检测 -> 判断违规 -> 触发协作"""

    def stop(self):
        """停止检测"""
```

**关键参数**:
- `FRAME_RATE = 3` - 每秒处理帧数（不需要每帧都处理）
- `CONFIDENCE_THRESHOLD = 0.5` - 本地检测置信度阈值
- `CONSULT_THRESHOLD = 0.7` - 触发云端协作的阈值

#### 步骤2：创建实时检测API路由 `routers/realtime.py`

**文件位置**: `e:\output\1\api\routers\realtime.py`

**接口设计**:

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/realtime/start` | POST | 启动实时检测（指定摄像头索引） |
| `/api/realtime/stop` | POST | 停止检测 |
| `/api/realtime/status` | GET | 获取检测状态（运行中/已停止/帧率等） |
| `/api/realtime/snapshot` | GET | 获取当前帧（Base64） |
| `/api/realtime/violations/stream` | WebSocket | 违规事件实时推送 |

**WebSocket推送格式**:
```json
{
  "event": "violation_detected",
  "timestamp": "2026-07-17T10:30:00",
  "violation_type": "no_helmet",
  "confidence": 0.91,
  "image_base64": "...",
  "ai_trace": { ... }
}
```

#### 步骤3：创建检测预览窗口程序 `preview_window.py`

**文件位置**: `e:\output\1\zhitong\preview_window.py`

**功能**: 独立运行的实时预览窗口（类似blind_yun.py的GUI）

**界面元素**:
- 摄像头画面 + YOLO检测框
- 违规类型标签（红色高亮）
- 协作状态指示（本地检测中/咨询云端中/已确认）
- 置信度数值
- 快捷键：空格=截图保存，C=强制云端咨询，Q=退出

**参考**: `blind_yun.py` 的主循环和可视化部分

---

### 第二阶段：与现有系统整合

#### 步骤4：违规检测逻辑整合

**修改**: `e:\output\1\api\realtime_detector.py`

**整合内容**:
1. 调用 `image_recognizer.multi_model_detect()` 进行多模型串联检测
2. 调用 `violation_rules.check_violations()` 判断违规类型
3. 调用 `cloud_collaborator.should_consult_cloud()` 判断是否需要云端协作
4. 调用 `cloud_collaborator.consult_cloud()` 执行协作
5. 保存证据到数据库（通过API调用）

**检测流程**:
```
摄像头帧 → YOLO检测 → 规则引擎判断 →
├─ 无违规 → 继续下一帧
├─ 疑似违规(confidence 0.4-0.7) → 触发云端咨询
└─ 明确违规(confidence > 0.7) → 直接上报确认
```

#### 步骤5：数字孪生实时联动

**修改**: `e:\output\1\digital_twin\app.py`

**新增WebSocket端点**: `/ws/violations`

**功能**:
- 后端检测到违规时，通过WebSocket推送给数字孪生前端
- 前端收到消息后，调用 `triggerViolationEvent(violation)` 播放动画

**推送数据格式**:
```json
{
  "type": "violation",
  "camera_id": "cam_001",
  "violation_type": "no_helmet",
  "confidence": 0.91,
  "position": {"x": 120, "y": 80}
}
```

#### 步骤6：证据保存与数据库写入

**新增函数**: `save_violation_evidence(frame, violation_result)`

**保存内容**:
- 截图保存到 `api/uploads/realtime_YYYYMMDD_HHMMSS.jpg`
- 写入数据库 `ViolationEvidence` 表
- 关联协作会话（如果有）

---

### 第三阶段：启动脚本和测试

#### 步骤7：更新一键启动脚本

**修改**: `e:\output\1\lan-start.bat`

**新增选项**: 启动实时检测预览窗口

```batch
echo [4/4] 启动实时检测预览窗口...
cd /d e:\output\1\zhitong
start "智瞳实时检测" cmd /k "py -3 preview_window.py"
```

#### 步骤8：创建实时检测测试脚本

**文件位置**: `e:\output\1\api\test_realtime.py`

**测试内容**:
- 摄像头打开测试
- 单帧检测测试
- WebSocket连接测试
- 违规事件推送测试

#### 步骤9：生成测试报告

**文件位置**: `e:\output\1\zhitong\training\reports\task009_test_report.md`

---

## 三、验收标准

### 核心功能（必须100%通过）

1. **实时检测**
   - [ ] 能打开USB摄像头（索引0-3自动检测）
   - [ ] 能实时显示检测画面（>=3 FPS）
   - [ ] 能正确识别车辆、行人、摩托车等目标

2. **违规判断**
   - [ ] 能判断未戴头盔（motorcycle + person - helmet）
   - [ ] 能判断闯红灯（vehicle + red_light）
   - [ ] 检测结果有置信度数值

3. **端云协作**
   - [ ] 疑似违规时能触发云端咨询
   - [ ] 云端返回ai_trace v3结构
   - [ ] 协作结果能保存到数据库

4. **数字孪生联动**
   - [ ] WebSocket连接成功
   - [ ] 违规事件能推送到数字孪生
   - [ ] 数字孪生能播放违规动画

### 系统整合（80%以上通过）

5. **预览窗口**
   - [ ] 独立窗口能运行
   - [ ] 快捷键能响应（空格截图、C云端咨询、Q退出）
   - [ ] 界面显示正常

6. **API接口**
   - [ ] 5个新增API全部可用
   - [ ] WebSocket能正常连接

---

## 四、关键代码参考

### 从blind_yun.py复用的部分

1. **摄像头检测逻辑**（第563-616行）- 自动检测可用摄像头
2. **YOLO推理**（第675-682行）- 结果解析
3. **可视化标注**（第685-696行）- 检测框绘制

### 新增的核心逻辑

1. **违规判断** - 调用 `violation_rules.check_violations()`
2. **端云协作** - 调用 `cloud_collaborator.consult_cloud()`
3. **数字孪生推送** - WebSocket消息

---

## 五、注意事项

1. **性能优化**: 每秒只处理2-5帧，不要每帧都跑YOLO
2. **内存管理**: 及时释放不需要的帧数据
3. **错误处理**: 摄像头断开时自动重连
4. **API Key安全**: 从配置文件读取，不要硬编码
5. **代码风格**: 使用中文注释，遵循现有项目结构

---

## 六、执行顺序建议

```
第1-2小时: 第一阶段（核心模块 + API路由 + 预览窗口）
第2-3小时: 第二阶段（违规检测整合 + 数字孪生联动）
第3-4小时: 第三阶段（启动脚本 + 测试）
```

---

**任务签发**: 指挥官
**签发时间**: 2026-07-20
**预期完成**: 当日验收