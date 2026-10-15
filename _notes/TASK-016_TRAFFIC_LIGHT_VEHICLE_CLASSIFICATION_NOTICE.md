# TASK-016 红绿灯专用模型 + 车辆分类优化 + 自动化测试

## 一、任务概述

**任务编号**: TASK-016
**任务名称**: 红绿灯专用模型下载 + 车辆分类优化 + 自动化测试
**预计耗时**: 8-10小时（一整夜）
**核心目标**: 
1. 解决TASK-015遗留问题（红绿灯模型缺失、车辆类别单一）
2. 全面自动化测试系统
3. 优化数据集和模型性能

---

## 二、背景

TASK-015已用GitHub现成模型替换了fallback，但存在两个问题：
1. **红绿灯模型**：没找到专用预训练模型，还在用TASK-014的低精度模型
2. **车辆类别单一**：只有"Vehicle"一类，无法区分car/motorcycle/truck/bus

---

## 三、【已验证事实】不要重新安装

| 项目 | 状态 |
|------|------|
| PyTorch CUDA版 | ✅ 已安装 (2.5.1) |
| GPU | ✅ RTX 4060 Laptop |
| ultralytics | ✅ 已安装 (8.4.103) |
| image_recognizer.py | ✅ 已自动GPU |
| GitHub MCP | ✅ 可用 |

**重要**: 使用 `C:\miniconda\envs\zhitong-gpu\python.exe`

---

## 四、执行步骤

### 第一阶段：红绿灯专用模型（约2小时）

#### 步骤1：搜索红绿灯专用YOLOv8模型

**使用 mcp_GitHub.search_repositories 搜索**：
```
搜索1: "traffic light detection yolov8"
搜索2: "traffic light recognition yolo"
搜索3: "traffic signal detection"
搜索4: "red light green light yolo"
搜索5: "traffic light color classification"
搜索6: "LISA traffic light"
```

**重点找**：
- 能识别 red/yellow/green 三种颜色的模型
- YOLOv8格式 (.pt文件)
- star数高的项目

#### 步骤2：下载并验证红绿灯模型

**下载到**: `e:\output\1\zhitong\training\models\downloaded\`

**验证命令**:
```powershell
C:\miniconda\envs\zhitong-gpu\python.exe -c "
from ultralytics import YOLO
import torch

model = YOLO('e:/output/1/zhitong/training/models/downloaded/traffic_light_v2.pt')
print('Classes:', model.names)
if torch.cuda.is_available():
    model = model.to('cuda')

# 测试红绿灯图片
results = model('e:/output/1/zhitong/data/raw_videos/test_red_light.mp4', save=True)
print('Results:', results)
"
```

**验收标准**：
- 能识别 red/yellow/green 三种颜色
- 检测置信度 > 0.7

#### 步骤3：如果找不到专用模型，用COCO迁移学习

**策略**: 用yolov8s.pt（含traffic light类别）做基础，下载红绿灯数据集微调

**数据集搜索**:
```
使用 mcp_GitHub.search_repositories 搜索 "traffic light dataset"
使用 integrated_browser 访问 https://universe.roboflow.com/search?q=traffic+light
```

**迁移学习命令**:
```powershell
cd e:\output\1\zhitong\training
C:\miniconda\envs\zhitong-gpu\python.exe -c "
from ultralytics import YOLO
model = YOLO('yolov8s.pt')  # COCO预训练
model.train(
    data='../data/traffic_light_large.yaml',
    epochs=50,
    batch=16,
    device=0,
    optimizer='AdamW',
    lr0=0.001,
    patience=20
)
"
```

---

### 第二阶段：车辆分类优化（约2小时）

#### 步骤4：搜索能分类车辆的模型

**使用 mcp_GitHub.search_repositories 搜索**：
```
搜索1: "vehicle classification yolov8"
搜索2: "car truck bus detection yolo"
搜索3: "vehicle type detection"
搜索4: "traffic vehicle classification"
```

**目标**: 找到能区分 car/motorcycle/truck/bus 的模型

#### 步骤5：下载并验证车辆分类模型

**下载到**: `e:\output\1\zhitong\training\models\downloaded\vehicle_classification.pt`

**验证**:
```powershell
C:\miniconda\envs\zhitong-gpu\python.exe -c "
from ultralytics import YOLO
model = YOLO('e:/output/1/zhitong/training/models/downloaded/vehicle_classification.pt')
print('Classes:', model.names)
# 期望: {0: 'car', 1: 'motorcycle', 2: 'truck', 3: 'bus'}
"
```

#### 步骤6：如果找不到，用COCO预训练模型

**重要发现**: yolov8s.pt（COCO预训练）已包含车辆分类！
```python
# COCO 80类中包含：
# 2: 'car'
# 3: 'motorcycle'  
# 5: 'bus'
# 7: 'truck'
```

**直接用yolov8s.pt作为车辆分类模型**：
```powershell
# 复制yolov8s.pt作为vehicle_classification.pt
copy e:\output\1\zhitong\training\models\yolov8s.pt e:\output\1\zhitong\training\models\downloaded\vehicle_classification.pt
```

**修改image_recognizer.py**:
- 车辆模型改用yolov8s.pt
- 从检测结果中过滤出car/motorcycle/truck/bus类别

---

### 第三阶段：系统集成更新（约1小时）

#### 步骤7：更新image_recognizer.py

**修改文件**: `e:\output\1\api\image_recognizer.py`

**更新内容**:
1. 红绿灯模型指向新下载的专用模型
2. 车辆模型改用能分类的模型
3. 更新类别映射

**验证**:
```powershell
C:\miniconda\envs\zhitong-gpu\python.exe -c "
import sys
sys.path.insert(0, 'e:/output/1/api')
from image_recognizer import init_all_models, multi_model_detect
init_all_models()
print('All models loaded successfully')
"
```

#### 步骤8：更新违规规则引擎

**修改文件**: `e:\output\1\api\violation_rules.py`

**更新内容**:
- 适配新的车辆类别（car/motorcycle/truck/bus）
- 适配新的红绿灯类别（red/yellow/green）
- 更新违规判断逻辑

---

### 第四阶段：自动化测试（约2小时）

#### 步骤9：创建综合测试脚本

**创建文件**: `e:\output\1\api\test_full_system.py`

**测试内容**:
1. 模型加载测试（所有模型）
2. 单张图片检测测试
3. 多模型串联检测测试
4. 违规判断测试
5. 端云协作测试
6. API接口测试
7. 数据库操作测试

**测试脚本框架**:
```python
import sys
sys.path.insert(0, 'e:/output/1/api')
from image_recognizer import init_all_models, multi_model_detect
from violation_rules import detect_violations
from cloud_collaborator import CloudCollaborator

def test_model_loading():
    """测试所有模型加载"""
    print("=== 测试模型加载 ===")
    success = init_all_models()
    assert success, "模型加载失败"
    print("✓ 所有模型加载成功")

def test_image_detection():
    """测试图片检测"""
    print("=== 测试图片检测 ===")
    test_image = 'e:/output/1/zhitong/test.jpg'
    result = multi_model_detect(test_image)
    assert result['success'], "检测失败"
    print(f"✓ 检测成功，耗时: {result['duration_ms']}ms")

def test_violation_detection():
    """测试违规判断"""
    print("=== 测试违规判断 ===")
    # 测试各种违规场景
    test_cases = [
        {'class': 'without_helmet', 'confidence': 0.8},
        {'class': 'red', 'confidence': 0.9},
    ]
    for case in test_cases:
        violations = detect_violations([case])
        print(f"✓ 测试案例: {case['class']} -> 违规: {violations}")

def test_api_endpoints():
    """测试API接口"""
    print("=== 测试API接口 ===")
    import requests
    base_url = 'http://localhost:8001'
    
    # 测试健康检查
    response = requests.get(f'{base_url}/health')
    assert response.status_code == 200
    print("✓ 健康检查通过")
    
    # 测试检测接口
    # ... 更多测试

def test_database():
    """测试数据库"""
    print("=== 测试数据库 ===")
    # 测试数据库连接和操作

if __name__ == '__main__':
    test_model_loading()
    test_image_detection()
    test_violation_detection()
    test_api_endpoints()
    test_database()
    print("\n🎉 所有测试通过！")
```

#### 步骤10：运行测试并生成报告

**运行测试**:
```powershell
cd e:\output\1\api
C:\miniconda\envs\zhitong-gpu\python.exe test_full_system.py > test_report_task016.txt 2>&1
```

**生成Markdown报告**:
- 测试覆盖率
- 通过/失败统计
- 性能指标
- 问题列表

---

### 第五阶段：性能优化（约1小时）

#### 步骤11：模型性能优化

**使用 chart-visualization Skill** 生成:
1. 各模型检测速度对比图
2. 各模型置信度分布图
3. 系统资源使用情况

#### 步骤12：优化建议

**分析并优化**:
1. 模型加载时间优化（预热）
2. 检测速度优化（batch处理）
3. 内存使用优化（模型卸载）

---

## 五、MCP和Skill使用指南

### 必须使用的MCP

| MCP | 使用场景 |
|-----|---------|
| **`mcp_GitHub`** | 搜索红绿灯和车辆分类模型 |
| `mcp_windows-cli` | 执行训练和测试命令 |
| `integrated_browser` | 验证网页端功能 |

### 必须使用的Skill

| Skill | 使用场景 |
|-------|---------|
| `chart-visualization` | 生成性能对比图 |
| `data-analysis` | 分析测试数据 |

---

## 六、验收标准

### 核心指标

| 指标 | 要求 |
|------|------|
| 红绿灯专用模型 | 下载或训练完成 |
| 红绿灯能识别颜色 | red/yellow/green |
| 车辆分类模型 | 能区分car/motorcycle/truck/bus |
| 自动化测试脚本 | 创建并运行 |
| 测试通过率 | > 90% |
| deviations字段 | 必须列出所有变更 |

### 功能验收

- [ ] 红绿灯模型下载/训练完成
- [ ] 车辆分类模型配置完成
- [ ] image_recognizer.py更新
- [ ] violation_rules.py更新
- [ ] 自动化测试脚本创建
- [ ] 测试报告生成
- [ ] 性能对比图生成

---

## 七、关键参考

| 文件 | 路径 |
|------|------|
| TASK-015结果 | `e:\output\_TASK-015_OUTPUT.json` |
| 现有模型 | `e:\output\1\zhitong\training\models\` |
| 下载模型目录 | `e:\output\1\zhitong\training\models\downloaded\` |
| 测试视频 | `e:\output\1\zhitong\data\raw_videos\` |
| 图像识别模块 | `e:\output\1\api\image_recognizer.py` |
| 违规规则引擎 | `e:\output\1\api\violation_rules.py` |

---

## 八、降级方案

**如果红绿灯专用模型找不到**：
1. 用yolov8s.pt的COCO traffic light类别（只能检测红绿灯，不能分类颜色）
2. 用颜色识别算法（HSV色彩空间）补充颜色判断
3. 继续用TASK-014的traffic_light_best.pt

**如果车辆分类模型找不到**：
1. 直接用yolov8s.pt（COCO 80类已包含car/motorcycle/truck/bus）
2. 在image_recognizer.py中过滤出车辆类别

---

## 九、输出要求

### _TASK-016_OUTPUT.json 格式

```json
{
  "task": "TASK-016",
  "timestamp": "ISO8601",
  "status": "PASS/PARTIAL/FAIL",
  "details": {
    "traffic_light_model": {
      "source": "GitHub/迁移学习/COCO",
      "model_path": "...",
      "classes": ["red", "yellow", "green"],
      "performance": "..."
    },
    "vehicle_model": {
      "source": "GitHub/COCO",
      "model_path": "...",
      "classes": ["car", "motorcycle", "truck", "bus"],
      "performance": "..."
    },
    "system_integration": {
      "image_recognizer_updated": true,
      "violation_rules_updated": true,
      "class_mappings_added": []
    },
    "automated_tests": {
      "script_path": "...",
      "total_tests": 0,
      "passed": 0,
      "failed": 0,
      "report_path": "..."
    },
    "deviations": []
  }
}
```

---

**任务签发**: 指挥官
**签发时间**: 2026-07-21
**特别提醒**: 这是一整夜的长任务，按顺序执行，遇到问题记录到deviations
