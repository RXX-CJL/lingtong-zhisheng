# TASK-015 GitHub现成模型下载 + 验证 + 迁移学习

## 一、任务概述

**任务编号**: TASK-015
**任务名称**: GitHub现成模型下载 + 验证 + 必要时迁移学习
**预计耗时**: 6-8小时
**核心目标**: 
1. **优先策略**：从GitHub下载现成的训练好的YOLOv8模型(.pt文件)
2. 验证模型性能，如果达标就直接使用
3. 如果不达标，下载大数据集做迁移学习

---

## 二、背景

TASK-014训练结果不达标（车辆mAP=0.38, 头盔mAP=0.672）原因是数据集太小（460张）。
**指挥官已确认GitHub上有大量现成的训练好的模型和数据集，优先使用现成资源。**

---

## 三、【已验证事实】不要重新安装

| 项目 | 状态 |
|------|------|
| PyTorch CUDA版 | ✅ 已安装 (2.5.1) |
| GPU | ✅ RTX 4060 Laptop |
| ultralytics | ✅ 已安装 (8.4.103) |
| image_recognizer.py | ✅ 已自动GPU |

**重要**: 使用 `C:\miniconda\envs\zhitong-gpu\python.exe`，不要用conda activate

---

## 四、执行步骤

### 第一阶段：GitHub搜索现成模型（约1小时）

#### 步骤1：使用GitHub MCP搜索训练好的模型

**调用 `mcp_GitHub.search_repositories` 搜索以下关键词**：

```
搜索1: "helmet detection yolov8"
搜索2: "safety helmet yolo"
搜索3: "traffic light detection yolov8"
搜索4: "vehicle detection yolov8"
搜索5: "traffic violation detection"
搜索6: "no helmet detection"
```

**对每个搜索结果**：
1. 按star数排序，选top 5
2. 用 `mcp_GitHub.get_file_contents` 检查仓库里是否有 `.pt` 文件
3. 检查README了解模型性能（mAP50）
4. 检查License是否允许使用

#### 步骤2：检查GitHub Releases下载训练好的权重

**很多GitHub项目把训练好的模型放在Releases里**：

```
对每个候选仓库：
1. 调用 mcp_GitHub 的 list_releases 或类似API
2. 查找 .pt 或 .pth 权重文件
3. 记录下载链接
```

**重点检查以下已知项目**：

| 项目 | 链接 | 预期资源 |
|------|------|---------|
| Traffic-Rule-Violation-Detection-System | https://github.com/ShreyAmbesh/Traffic-Rule-Violation-Detection-System | 完整违规检测系统 |
| Traffic_Violation_Detection_Yolov4_Deep-Sort | https://github.com/hasantha-nirmal/Traffic_Violation_Detection_Yolov4_Deep-Sort | 违规检测+追踪 |
| ultralytics/ultralytics | https://github.com/ultralytics/ultralytics | 官方YOLOv8 |
| kettelphant/Cap-Recognition | 搜索结果 | 头盔识别 |
| Helmet-Detection-YOLOv8 | 搜索结果 | 头盔检测 |

#### 步骤3：下载模型文件

**下载到**: `e:\output\1\zhitong\training\models\downloaded\`

**期望下载**：
- `helmet_pretrained.pt` - 头盔检测预训练模型
- `traffic_light_pretrained.pt` - 红绿灯检测预训练模型
- `vehicle_pretrained.pt` - 车辆检测预训练模型

**下载方法**：
```powershell
# 用git clone或直接下载
mkdir e:\output\1\zhitong\training\models\downloaded
cd e:\output\1\zhitong\training\models\downloaded

# 方法1: git clone整个仓库（如果模型在仓库里）
git clone <仓库URL>

# 方法2: 用PowerShell下载release文件
Invoke-WebRequest -Uri "<下载URL>" -OutFile "helmet_pretrained.pt"
```

---

### 第二阶段：模型验证（约1小时）

#### 步骤4：验证下载的模型

**对每个下载的模型文件执行验证**：

```powershell
# 头盔模型验证
C:\miniconda\envs\zhitong-gpu\python.exe -c "
from ultralytics import YOLO
import torch

# 加载模型
model = YOLO('e:/output/1/zhitong/training/models/downloaded/helmet_pretrained.pt')
print('Model device:', model.device)

# 查看模型类别
print('Model classes:', model.names)

# 移动到GPU
if torch.cuda.is_available():
    model = model.to('cuda')

# 在测试图片上验证
results = model('e:/output/1/zhitong/data/raw_videos/test_no_helmet.mp4', save=True)
print('Detection results:', results)
"
```

**验收标准**：
- 模型能正常加载
- 能检测出对应类别（helmet/no_helmet等）
- mAP50或检测置信度合理（>0.7）

#### 步骤5：决定是否需要迁移学习

**判断逻辑**：
- 如果现成模型mAP50 > 0.80 → 直接使用，跳到第四阶段
- 如果现成模型0.60 < mAP50 < 0.80 → 做迁移学习优化（第三阶段）
- 如果现成模型mAP50 < 0.60 或下载失败 → 用大数据集从头训练（第三阶段）

---

### 第三阶段：迁移学习（如需要，约3-4小时）

#### 步骤6：下载大型数据集

**如果现成模型精度不达标，下载数据集做迁移学习**：

**头盔数据集来源**：
```
使用 mcp_GitHub.search_repositories 搜索 "helmet dataset"
重点找：
- 包含5000+张图像的数据集
- YOLO格式标注
- 开源License
```

**车辆数据集来源**：
```
使用 mcp_GitHub.search_repositories 搜索 "vehicle dataset yolo"
或下载COCO车辆子集
```

**红绿灯数据集来源**：
```
搜索 "LISA traffic light dataset"
搜索 "traffic light dataset yolo"
```

#### 步骤7：迁移学习训练

**策略**: 用下载的现成模型作为预训练权重，在自己的数据集上微调

```powershell
cd e:\output\1\zhitong\training

# 头盔迁移学习（用现成模型做init）
C:\miniconda\envs\zhitong-gpu\python.exe -c "
from ultralytics import YOLO
model = YOLO('e:/output/1/zhitong/training/models/downloaded/helmet_pretrained.pt')
model.train(
    data='e:/output/1/zhitong/data/helmet_large.yaml',
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

### 第四阶段：系统集成（约1小时）

#### 步骤8：选择最佳模型

**对比以下模型性能**：
1. TASK-014训练的模型（mAP=0.38/0.672）
2. GitHub下载的现成模型
3. 迁移学习后的模型（如果做了）

**选择mAP50最高的模型作为最终模型**

#### 步骤9：替换系统模型

```powershell
# 复制最佳模型到系统目录
copy <最佳模型路径> e:\output\1\zhitong\training\models\helmet_best.pt
copy <最佳模型路径> e:\output\1\zhitong\training\models\vehicle_best.pt
copy <最佳模型路径> e:\output\1\zhitong\training\models\traffic_light_best.pt
```

**更新 `e:\output\1\api\image_recognizer.py`**：
- 确认MODEL_CONFIG指向新模型
- 确认模型加载后自动移动到GPU（已修复）

#### 步骤10：端到端测试

**使用 integrated_browser MCP** 验证：
1. 启动系统：`e:\output\1\lan-start.bat`
2. 访问 http://localhost:5173
3. 测试AI检测功能
4. 截图保存到报告

---

## 五、MCP和Skill使用指南

### 必须使用的MCP

| MCP | 使用场景 | 调用时机 |
|-----|---------|---------|
| **`mcp_GitHub`** | **核心**：搜索和下载现成模型 | 第一阶段 |
| `mcp_windows-cli` | 执行训练和测试命令 | 第二/三阶段 |
| `integrated_browser` | 验证网页端功能 | 第四阶段 |

### GitHub MCP关键调用

```
# 搜索仓库
mcp_GitHub.search_repositories({
  query: "helmet detection yolov8",
  sort: "stars",
  order: "desc"
})

# 获取仓库内容
mcp_GitHub.get_file_contents({
  owner: "用户名",
  repo: "仓库名",
  path: "README.md"
})

# 列出Releases（找.pt文件）
mcp_GitHub.list_releases({
  owner: "用户名",
  repo: "仓库名"
})
```

### 必须使用的Skill

| Skill | 使用场景 |
|-------|---------|
| `chart-visualization` | 生成模型性能对比图 |
| `data-analysis` | 分析检测结果数据 |

---

## 六、验收标准

### 核心指标

| 指标 | 要求 |
|------|------|
| GitHub模型下载 | 至少下载2-3个现成模型 |
| 头盔模型 mAP50 | > 0.80 |
| 车辆模型 mAP50 | > 0.85 |
| 红绿灯模型 mAP50 | > 0.80 |
| deviations字段 | 必须列出所有变更 |

### 功能验收

- [ ] GitHub搜索完成
- [ ] 至少下载2个现成模型
- [ ] 模型验证完成
- [ ] 系统集成完成
- [ ] 端到端测试通过
- [ ] 测试报告生成

---

## 七、关键参考

| 文件 | 路径 |
|------|------|
| TASK-014结果 | `e:\output\_TASK-014_OUTPUT.json` |
| 训练脚本 | `e:\output\1\zhitong\training\train.py` |
| 现有模型 | `e:\output\1\zhitong\training\models\` |
| 测试视频 | `e:\output\1\zhitong\data\raw_videos\` |

---

## 八、降级方案

**如果GitHub下载失败**：

1. **使用COCO预训练模型**：`yolov8s.pt` 已包含car/motorcycle/truck/bus/traffic light等80类
2. **直接用yolov8s.pt**：虽然不是专用模型，但COCO 80类已覆盖大部分需求
3. **用现有TASK-014模型**：精度虽低但能跑

**重要**: 任何降级方案都必须在deviations字段中说明

---

**任务签发**: 指挥官
**签发时间**: 2026-07-21
**核心策略**: 优先用GitHub现成模型，站在巨人肩膀上！
