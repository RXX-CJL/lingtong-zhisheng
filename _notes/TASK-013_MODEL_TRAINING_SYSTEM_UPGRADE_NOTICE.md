# TASK-013 数据增强 + 模型训练 + 系统全面升级

## 一、任务概述

**任务编号**: TASK-013
**任务名称**: 数据增强 + 三模型训练 + 系统全面集成验证
**预计耗时**: 6-8小时（一晚上）
**核心目标**: 训练真正的专用模型（红绿灯颜色分类、头盔检测、高精度车辆检测），替换所有fallback，系统整体性能跃升

---

## 二、【强制规则】变更必须汇报

⚠️ **重要**：执行过程中如遇任何与本通知单不一致的情况（模型下载失败、改用替代方案、功能简化、路径变更等），**必须在_OUTPUT.json的"deviations"字段中逐一列出**，并说明原因和替代方案。未列出的变更视为未完成。

---

## 三、执行步骤

### 第一阶段：数据采集与增强（约1.5小时）

#### 步骤1：扩充数据集

**已有数据**:
- `data/processed_frames/no_helmet/` - 未戴头盔帧（约25张）
- `data/processed_frames/red_light/` - 闯红灯帧（约70张）
- `data/processed_frames/wrong_way/` - 逆行帧（约70张）
- `data/raw_videos/` - 3个测试视频

**任务**:
1. 从3个测试视频中更多抽帧（每秒1帧，各提取100帧）
2. 数据增强（翻转、旋转±15°、亮度变化±20%、缩放0.8-1.2倍）
3. 每个类别扩充到至少200张
4. 按8:1:1划分训练集/验证集/测试集

**使用工具**: `video_extractor.py`, `auto_labeler.py`

#### 步骤2：自动标注

**任务**:
1. 用现有yolov8s模型对所有图片进行初步检测
2. 生成YOLO格式标注文件（.txt）
3. 人工校验关键字段（车灯、车牌、头盔位置）

#### 步骤3：生成数据集配置

**文件**: `data/traffic_dataset.yaml`

```yaml
path: e:/output/1/zhitong/data
train: images/train
val: images/val
test: images/test

names:
  # 红绿灯颜色分类
  0: red_light
  1: yellow_light
  2: green_light
  # 头盔检测
  3: helmet
  4: no_helmet
  # 车辆检测
  5: car
  6: motorcycle
  7: truck
  8: bus
```

---

### 第二阶段：模型训练（约3-4小时）

#### 步骤4：红绿灯颜色分类模型训练

**目标**: 训练一个能精准识别红/黄/绿灯的模型

**方案**: 基于yolov8n微调
- 预训练权重: yolov8n.pt
- 输入尺寸: 640
- 训练轮数: 100 epochs
- 批次大小: 16
- 数据增强: mosaic, mixup, hsv

**输出**: `models/traffic_light_best.pt`

**验证指标**: mAP50 > 0.85

#### 步骤5：头盔检测模型训练

**目标**: 训练头盔/未戴头盔检测模型

**方案**: 基于yolov8n微调
- 预训练权重: yolov8n.pt
- 输入尺寸: 640
- 训练轮数: 100 epochs
- 批次大小: 16

**输出**: `models/helmet_best.pt`

**验证指标**: mAP50 > 0.8

#### 步骤6：高精度车辆检测模型训练

**目标**: 微调yolov8s，专注于车辆类检测，提高小目标检测精度

**方案**: 基于yolov8s微调
- 预训练权重: yolov8s.pt
- 类别过滤: 只保留car, motorcycle, truck, bus, bicycle
- 训练轮数: 50 epochs
- 批次大小: 8

**输出**: `models/vehicle_best.pt`

**验证指标**: mAP50 > 0.9

---

### 第三阶段：模型验证与集成（约1.5小时）

#### 步骤7：模型性能对比测试

**测试内容**:
- 每个模型在测试集上的mAP、Precision、Recall
- 推理速度（单帧耗时）
- 与原fallback模型（yolov8s通用版）的对比

**生成报告**: `reports/model_comparison_report.md`

#### 步骤8：替换系统中的fallback模型

**修改文件**:
- `api/image_recognizer.py` - 更新MODEL_CONFIG，指向新训练的模型
- `api/violation_rules.py` - 更新类别映射
- `api/config.py` - 更新模型路径配置

**验证**:
- 所有模型能正常加载
- 检测结果类别正确
- API响应格式不变

#### 步骤9：端到端集成测试

**测试场景**:
1. 摄像头实时检测 → YOLO检测 → 违规判断 → 端云协作 → 数字孪生联动
2. 5种违规类型各测试10张图片
3. 统计准确率、误报率、漏报率

**生成报告**: `reports/task013_integration_report.md`

---

### 第四阶段：系统完善（约1小时）

#### 步骤10：更新项目文件索引

**修改**: `e:\output\PROJECT_FILE_INDEX.md`

**新增条目**:
- traffic_light_best.pt - 红绿灯颜色分类模型
- helmet_best.pt - 头盔检测模型
- vehicle_best.pt - 高精度车辆检测模型
- traffic_dataset.yaml - 数据集配置
- model_comparison_report.md - 模型对比报告
- training/train.py 等训练脚本

#### 步骤11：生成最终测试报告

**文件**: `e:\output\1\zhitong\training\reports\task013_final_report.md`

**包含**:
- 数据集统计（各类别数量、划分比例）
- 三个模型的训练曲线（loss、mAP）
- 模型性能对比表
- 端到端测试结果
- 系统整体性能提升百分比

---

## 四、验收标准

### 核心指标（必须达到）

| 指标 | 最低要求 |
|------|---------|
| 红绿灯颜色分类 mAP50 | > 0.80 |
| 头盔检测 mAP50 | > 0.75 |
| 车辆检测 mAP50 | > 0.85 |
| 单帧推理总耗时（3模型串联） | < 500ms |
| 端到端测试通过率 | > 90% |
| 所有API接口正常 | 100% |
| 变更汇报完整 | 必须列出所有deviations |

### 功能验收

- [ ] 三个专用模型训练完成
- [ ] 数据集扩充到每类200+张
- [ ] 替换所有fallback模型
- [ ] 端到端链路跑通
- [ ] 数字孪生联动正常
- [ ] 微信小程序正常调用
- [ ] 测试报告生成
- [ ] 文件索引更新
- [ ] deviations字段完整（即使为空也要列出）

---

## 五、关键参考文件

| 文件 | 用途 |
|------|------|
| `e:\output\1\zhitong\blind_yun.py` | 参考：本地检测窗口实现 |
| `e:\output\1\zhitong\training\` | 训练脚本目录 |
| `e:\output\1\api\image_recognizer.py` | 图像识别核心模块 |
| `e:\output\1\api\config.py` | 配置管理 |
| `e:\output\1\zhitong\data\` | 数据目录 |

---

## 六、环境说明

- **GPU**: RTX 4060（CUDA已配置）
- **Python环境**: conda zhitong-gpu
- **VPN**: 已开启（可下载模型和数据）
- **MCP插件**: 已安装（网页控制、git、数据库、服务器）

---

**任务签发**: 指挥官
**签发时间**: 2026-07-20
**预期完成**: 次日早晨验收
