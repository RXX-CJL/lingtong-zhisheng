# TASK-010 网页端实时监控 + 双图云端协作 + 逆行检测

## 一、任务概述

**任务编号**: TASK-010
**任务名称**: 网页端实时监控 + 双图云端协作 + 逆行规则引擎
**预计耗时**: 5-7小时
**核心目标**: 用户打开网页就能看摄像头实时画面+YOLO检测框，云端AI拿到原始图和标注图双通道分析，增加逆行检测

---

## 二、执行步骤

### 第一阶段：网页端实时监控页面

#### 步骤1：创建实时监控前端页面 `RealtimeMonitor.vue`

**文件位置**: `e:\output\1\web-admin\src\views\RealtimeMonitor.vue`

**功能**:
- 左侧：实时视频画面（WebSocket推送的MJPEG流）
- 右侧：检测信息面板
  - 当前帧率
  - 已检测目标列表
  - 违规告警（红色闪烁
- 底部：控制按钮
  - 开始/停止检测
  - 摄像头选择
  - 截图保存
  - 强制云端咨询

**技术实现**:
```html
<template>
  <div class="realtime-monitor">
    <div class="video-container">
      <img :src="imageUrl" alt="实时画面" />
      <div class="violation-badge" v-if="currentViolation">
        {{ currentViolation.type_cn }}
      </div>
    </div>
    <div class="info-panel">...</div>
    <div class="control-bar">...</div>
  </div>
</template>
```

#### 步骤2：后端MJPEG视频流接口

**修改**: `e:\output\1\api\routers\realtime.py`

**新增接口**: `/api/realtime/stream` - MJPEG视频流

**实现方式**:
- 多部分HTTP响应，每帧一个boundary
- 从realtime_detector获取最新标注帧
- 编码为JPEG后推送
- 前端`<img>`标签直接显示

```python
@router.get("/stream")
async def video_stream():
    """MJPEG视频流"""
    def generate():
        while True:
            frame = realtime_detector.get_annotated_frame()
            if frame is not None:
                _, buffer = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.1)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")
```

#### 步骤3：注册路由和菜单

**修改**:
- `e:\output\1\web-admin\src\router\index.js` - 添加路由
- `e:\output\1\web-admin\src\components\Sidebar.vue` - 添加菜单项

**菜单位置**: 实时监控（在"AI检测"下面

---

### 第二阶段：双图云端协作增强

#### 步骤4：增强端云协作 - 双图发送

**修改**: `e:\output\1\api\cloud_collaborator.py`

**核心改进**:
- 发送**原始帧**（无标注）给云端AI做独立判断
- 发送**标注帧**（有YOLO框）给云端AI做对比分析
- 云端分别分析两张图，综合判断

**修改 `consult_cloud()` 函数**:
```python
def consult_cloud(self, frame, detection_result, annotated_frame=None):
    """
    云端协作 - 发送两张图给云端AI
    - 原始帧：让云端AI独立判断
    - 标注帧：让云端AI对比本地YOLO结果
    """
    # 构造多模态消息
    messages = [{
        "role": "user",
        "content": [
            {"image": original_frame_base64},  # 原始图
            {"text": "图1（原始图）：请独立判断这张图片中是否有交通违规行为？"},
            {"image": annotated_frame_base64}, # 标注图
            {"text": "图2（标注图）：这是本地YOLO的检测结果，红色框是检测到的目标。请对比两张图，判断本地检测是否准确，有没有漏检或误检？请给出最终裁决。"},
            {"text": "请按以下JSON格式返回：
{\"final_judgment\": \"confirmed/denied/new_violation\",
  \"confidence\": 0.9,
  \"violation_type\": \"...\",
  \"evidence\": [...],
  \"local_accuracy\": \"high/medium/low\",
  \"missed_detections\": [...],
  \"false_detections\": [...]"}
        ]
    }]
```

#### 步骤5：更新ai_trace结构为v3.1

**ai_trace新增字段**:
```python
ai_trace = {
  "version": "v3.1",
  "yolo": {...},
  "doubao": {
    "original_analysis": {...},  # 基于原始图的分析
    "annotated_analysis": {...}, # 基于标注图的分析
    "final_judgment": {...}
  },
  "deepseek": {
    "original_analysis": {...},
    "annotated_analysis": {...},
    "final_judgment": {...}
  },
  "final": {...}
}
```

#### 步骤6：视频抽帧上下文分析

**修改**: `e:\output\1\api\realtime_detector.py`

**功能**: 检测到违规时，自动保存前后帧作为上下文：
- 违规前2帧（违规发生前）
- 违规帧（当前帧）
- 违规后1帧（确认违规）

发送给云端AI时，一起发送4帧（前2+当前1+后1），让AI理解时间序列

```python
def get_context_frames(self):
    """获取违规前后的上下文帧"""
    # 维护一个帧缓存队列
    # 返回最近N帧
```

---

### 第三阶段：逆行检测规则引擎

#### 步骤7：增强逆行检测规则

**修改**: `e:\output\1\api\violation_rules.py`

**新增**: `_check_wrong_way()` 函数

**判断逻辑**:
```
1. 检测车道线位置
2. 检测车辆位置
3. 追踪车辆运动方向（连续帧对比）
4. 判断车辆是否在对向车道行驶
5. 判定为逆行

**实现方式**:
- 方案A：光流法追踪车辆运动方向（连续帧
- 方案B：车辆bbox位置变化
- 方案C：结合车道线位置和车辆相对位置

#### 步骤8：车辆追踪器

**新增**: `e:\output\1\api\vehicle_tracker.py`

**功能**:
- 基于车辆ID分配
- 车辆位置追踪
- 运动方向计算
- 速度估算

```python
class VehicleTracker:
    def __init__(self):
        self.vehicles = {}  # vehicle_id -> {bbox, direction, speed, history}
    
    def update(self, detections):
        """更新追踪器"""
    
    def get_vehicle_direction(self, vehicle_id):
        """获取车辆运动方向"""
```

---

### 第四阶段：系统完善与测试

#### 步骤9：更新项目文件索引

**修改**: `e:\output\PROJECT_FILE_INDEX.md`

**新增条目**:
- RealtimeMonitor.vue - 实时监控页面
- vehicle_tracker.py - 车辆追踪器
- realtime/stream - MJPEG视频流接口
- cloud_collaborator.py - 双图协作增强

#### 步骤10：生成测试报告

**文件位置**: `e:\output\1\zhitong\training\reports\task010_test_report.md

**测试内容**:
- 网页端实时画面显示
- 双图云端协作效果
- 逆行检测准确性
- 性能测试（帧率、延迟）

---

## 三、验收标准

### 核心功能（必须100%通过）

1. **网页端实时监控**
   - [ ] 能在网页看到实时摄像头画面
   - [ ] 画面上有YOLO检测框
   - [ ] 帧率 >= 2 FPS
   - [ ] 能切换摄像头
   - [ ] 能开始/停止检测

2. **双图云端协作**
   - [ ] 发送原始帧+标注帧给云端
   - [ ] 云端能分别分析两张图
   - [ ] ai_trace v3.1结构正确
   - [ ] 能检测本地YOLO的漏检/误检

3. **逆行检测**
   - [ ] 能追踪车辆运动方向
   - [ ] 能判断逆行
   - [ ] 有置信度评分

4. **系统整合**
   - [ ] 启动脚本正常
   - [ ] API接口正常
   - [ ] 数字孪生联动正常

---

## 四、关键参考文件

| 文件 | 用途 |
|------|------|
| `e:\output\1\api\realtime_detector.py` | 实时检测服务（TASK-009已创建） |
| `e:\output\1\api\cloud_collaborator.py` | 端云协作模块 |
| `e:\output\1\api\violation_rules.py` | 违规规则引擎 |
| `e:\output\1\zhitong\blind_yun.py` | 参考：本地窗口实现 |
| `e:\output\1\K230\程序源码\07.Face\03.face_pose.py` | 参考：方向检测思路 |

---

## 五、注意事项

1. **性能优先**: 视频流不能占太多CPU，控制在2-3 FPS即可
2. **内存管理**: 帧缓存队列不要太大，控制在10帧以内
3. **API Key安全**: 不要硬编码，从配置读取
4. **代码风格**: 中文注释，遵循现有结构
5. **文件索引**: 每新增重要文件更新PROJECT_FILE_INDEX.md

---

**任务签发**: 指挥官
**签发时间**: 2026-07-20
**预期完成**: 当日验收
