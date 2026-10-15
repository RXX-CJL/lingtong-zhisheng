# TASK-014 GPU环境修复 + GitHub资源下载 + 模型训练继续

## 一、任务概述

**任务编号**: TASK-014
**任务名称**: GPU环境修复 + GitHub现成资源下载 + 继续训练
**预计耗时**: 6-8小时
**核心目标**: 
1. 激活正确的GPU环境（zhitong-gpu）
2. 从GitHub下载现成模型和数据集
3. 继续车辆模型训练
4. 优化头盔模型精度

---

## 二、【强制规则】变更必须汇报

⚠️ **重要**：执行过程中如遇任何与本通知单不一致的情况，**必须在_OUTPUT.json的"deviations"字段中逐一列出**。

---

## 二·零、【已验证事实】不要重新安装

⚠️ **重要**：以下项目已被指挥官验证可用，**执行者不要再尝试重新安装**：

| 项目 | 状态 | 验证命令 |
|------|------|---------|
| PyTorch CUDA版 | ✅ 已安装 | `C:\miniconda\envs\zhitong-gpu\python.exe -c "import torch; print(torch.cuda.is_available())"` → True |
| GPU驱动 | ✅ 已安装 | `nvidia-smi` → 566.07 |
| conda环境 | ✅ 已存在 | `C:\miniconda\envs\zhitong-gpu\python.exe` |
| ultralytics | ✅ 已安装 | 8.4.103版本 |
| image_recognizer.py | ✅ 已修复 | 模型加载后自动移动到GPU |

**重要**: 不需要安装CUDA Toolkit，PyTorch自带CUDA运行时
**重要**: 不要用 `conda activate`，直接用绝对路径 `C:\miniconda\envs\zhitong-gpu\python.exe`

---

## 三、执行步骤

### 第零阶段：GitHub资源下载（约1小时）

#### 步骤0.1：下载现成的头盔检测模型

**使用GitHub MCP搜索**:
```
调用 mcp_GitHub.search_repositories 搜索 "helmet detection yolov8"
调用 mcp_GitHub.get_file_contents 获取模型文件或训练脚本
```

**目标仓库**:
- ultralytics/ultralytics （官方YOLOv8）
- 搜索结果中评分最高的头盔检测项目

#### 步骤0.2：下载交通违规检测系统参考代码

**项目1**: https://github.com/ShreyAmbesh/Traffic-Rule-Violation-Detection-System
- 功能：信号违规、逆行、违停检测
- 操作：用GitHub MCP获取关键代码文件

**项目2**: https://github.com/hasantha-nirmal/Traffic_Violation_Detection_Yolov4_Deep-Sort
- 功能：违规检测 + Deep Sort车辆追踪
- 操作：获取Deep Sort相关代码

#### 步骤0.3：下载大型数据集（可选）

**搜索**: "helmet dataset yolov8" 或 "traffic violation dataset"
**目标**: 找到大于5000张图像的数据集
**记录**: 如果找到，把链接记录到deviations字段

---

### 第一阶段：环境验证（5分钟，不要重新安装任何东西）

#### 步骤1：验证GPU可用

**命令**（不要用conda activate，直接用绝对路径）:
```powershell
C:\miniconda\envs\zhitong-gpu\python.exe -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0))"
```

**验收标准**: 输出应显示 "CUDA: True" 和 "GPU: NVIDIA GeForce RTX 4060 Laptop GPU"
**如果显示True**: 继续步骤2
**如果显示False**: 才需要报告指挥官

#### 步骤2：验证ultralytics CUDA支持

**命令**:
```powershell
C:\miniconda\envs\zhitong-gpu\python.exe -c "from ultralytics import YOLO; model = YOLO('yolov8n.pt').to('cuda'); print('Model device:', model.device)"
```

**验收标准**: 输出应包含 "cuda:0"

---

### 第二阶段：继续训练（约4-5小时）

#### 步骤3：训练高精度车辆检测模型

**配置**:
- 模型: YOLOv8s
- Epochs: 50
- Batch: 8
- 数据集: `e:\output\1\zhitong\data\vehicle_dataset.yaml`

**命令**:
```powershell
cd e:\output\1\zhitong\training
C:\miniconda\envs\zhitong-gpu\python.exe train.py --model yolov8s --data ../data/vehicle_dataset.yaml --epochs 50 --batch 8 --device 0
```

#### 步骤4：优化头盔检测模型

**问题分析**: 上次训练mAP50=0.621，未达标
**优化方案**:
1. 增加epochs: 30 → 100
2. 使用更大模型: YOLOv8n → YOLOv8s
3. 如果GitHub下载到现成模型，直接使用

**命令**:
```powershell
C:\miniconda\envs\zhitong-gpu\python.exe train.py --model yolov8s --data ../data/helmet_dataset.yaml --epochs 100 --batch 16 --device 0
```

---

### 第三阶段：模型验证与对比（约1小时）

#### 步骤5：模型性能对比测试

**使用chart-visualization Skill**:
```
调用 chart-visualization 生成：
1. loss曲线图（训练过程）
2. mAP曲线图（精度变化）
3. 对比表（GPU vs CPU训练效果）
```

#### 步骤6：替换系统中的fallback模型

**修改文件**:
- `api/image_recognizer.py` - 更新MODEL_CONFIG
- `api/config.py` - 更新模型路径

---

## 四、MCP和Skill使用指南

### 必须使用的MCP

| MCP | 使用场景 | 调用时机 |
|-----|---------|---------|
| `mcp_GitHub` | 搜索和下载模型代码 | 第零阶段 |
| `mcp_windows-cli` | 执行conda activate命令 | 第一阶段 |
| `integrated_browser` | 验证网页端监控功能 | 第三阶段 |

### 必须使用的Skill

| Skill | 使用场景 | 调用时机 |
|-------|---------|---------|
| `chart-visualization` | 生成训练曲线图 | 第三阶段 |
| `data-analysis` | 分析训练日志数据 | 第三阶段 |

---

## 五、验收标准

### 核心指标

| 指标 | 要求 |
|------|------|
| CUDA可用 | ✅ True |
| GPU型号 | NVIDIA GeForce RTX 4060 |
| 车辆模型 mAP50 | > 0.85 |
| 头盔模型 mAP50 | > 0.80 |
| GitHub资源下载 | 至少下载1个现成模型或数据集 |
| deviations字段 | 必须列出所有变更 |

### 功能验收

- [ ] GPU环境正确激活
- [ ] 从GitHub下载现成资源
- [ ] 车辆模型训练完成
- [ ] 头盔模型优化完成
- [ ] chart-visualization生成图表
- [ ] 测试报告生成

---

## 六、关键参考

| 文件 | 路径 |
|------|------|
| 进展报告 | `e:\output\TASK-013_WORK_PROGRESS_REPORT.md` |
| 能力报告 | `e:\output\TASK-013_CAPABILITY_ASSESSMENT_REPORT.md` |
| 训练脚本 | `e:\output\1\zhitong\training\train.py` |
| 数据集配置 | `e:\output\1\zhitong\data\*.yaml` |

---

**任务签发**: 指挥官
**签发时间**: 2026-07-21