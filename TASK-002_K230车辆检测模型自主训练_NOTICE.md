# 任务通知单 · TASK-002

**指挥官签发**：2026-06-24
**执行者**：IDE / 子代理
**工作目录**：`e:\output\1\zhitong\k230_training\`
**项目**：智瞳灵声 - K230车辆检测模型自主训练全流程

---

## 任务描述

自主搭建K230车辆检测模型训练全流程工具链，实现从数据获取→数据处理→模型训练→结果验收的端到端自动化。无需用户投喂数据，自行通过多种方式获取和扩充数据集，最终产出可部署到K230的车辆检测模型。

---

## 核心参考资料（必读）

| 资料名称 | 路径 | 用途 |
|---------|------|------|
| K230开发指南 | `e:\output\K230开发指南_智瞳项目专用.md` | K230模型训练与部署完整指南 |
| 现有YOLO模型 | `e:\output\1\api\yolov8n.pt` | 预训练权重 / 伪标签生成 |
| K230训练示例源码 | `E:\output\1\K230\程序源码\13.training\` | PlatTasks部署框架参考 |
| 部署配置示例 | `E:\output\1\K230\15.训练自己的模型\使用在线平台训练\source\deploy_config.json` | deploy_config格式参考 |
| 后端项目目录 | `e:\output\1\api\` | Python环境、依赖安装参考 |

---

## 输出目录结构（必须按此创建）

```
e:\output\1\zhitong\k230_training\
├── data\                           # 数据集目录
│   ├── raw_videos\                 # 原始视频（用于抽帧）
│   ├── raw_images\                 # 原始图片（未标注）
│   ├── images\
│   │   ├── train\                  # 训练集图片
│   │   ├── val\                    # 验证集图片
│   │   └── test\                   # 测试集图片
│   ├── labels\
│   │   ├── train\                  # 训练集标注
│   │   ├── val\                    # 验证集标注
│   │   └── test\                   # 测试集标注
│   └── data.yaml                   # YOLO数据集配置
├── tools\                          # 工具脚本
│   ├── video_extractor.py          # 视频抽帧工具
│   ├── auto_labeler.py             # 自动标注（伪标签）工具
│   ├── dataset_manager.py          # 数据集管理（划分/统计/清洗）
│   └── data_augment.py             # 数据增强工具
├── train.py                        # 训练主脚本
├── evaluate.py                     # 模型评估验收脚本
├── export_onnx.py                  # 导出ONNX模型
├── configs\                        # 配置文件
│   └── train_config.yaml           # 训练配置
├── runs\                           # 训练输出
│   └── train\                      # ultralytics输出
└── reports\                        # 验收报告
    ├── dataset_report.json         # 数据集统计报告
    └── training_report.json        # 训练结果验收报告
```

---

## 执行步骤（共7步，按顺序执行）

### 步骤 1：环境准备与目录创建

**目标**：搭建工作目录，验证Python环境

**操作**：
1. 创建上述完整目录结构
2. 验证Python环境：
   ```bash
   py -3 --version
   py -3 -c "import ultralytics; print('ultralytics', ultralytics.__version__)"
   py -3 -c "import cv2; print('opencv', cv2.__version__)"
   ```
3. 如未安装ultralytics，执行：`py -3 -m pip install ultralytics opencv-python`
4. 验证预训练模型存在：`e:\output\1\api\yolov8n.pt`
5. 将预训练模型复制到工作目录：`models\yolov8n_pretrained.pt`

**验收**：目录结构完整、依赖安装成功、预训练模型就位

---

### 步骤 2：视频抽帧工具开发

**目标**：实现从视频文件自动抽取帧的工具

**文件**：`tools\video_extractor.py`

**功能要求**：
- 支持批量处理视频目录下所有视频
- 支持自定义抽帧间隔（秒/帧两种模式）
- 支持输出图片尺寸缩放
- 自动去重（基于感知哈希，避免连续相似帧）
- 支持多种视频格式：mp4, avi, mov, mkv
- 输出抽帧统计报告

**核心API**：
```python
def extract_frames_from_video(video_path, output_dir, interval=1.0, mode='time', resize=None, dedup=True):
    """
    从视频中抽帧
    Args:
        video_path: 视频文件路径
        output_dir: 输出图片目录
        interval: 抽帧间隔（mode='time'单位秒，mode='frame'单位帧数）
        mode: 'time'按时间间隔 / 'frame'按帧数间隔
        resize: (width, height) 缩放尺寸，None表示原尺寸
        dedup: 是否启用去重
    Returns:
        dict: {total_frames, saved_frames, skipped_duplicates}
    """

def batch_extract(video_dir, output_dir, **kwargs):
    """批量处理目录下所有视频"""
```

**验证方法**：
- 如目录 `data\raw_videos\` 下有视频文件，直接运行测试
- 如无视频，生成一段合成测试视频验证功能
- 输出抽帧统计到控制台

---

### 步骤 3：自动标注工具（伪标签）开发

**目标**：用预训练YOLOv8n模型自动给图片生成标注

**文件**：`tools\auto_labeler.py`

**功能要求**：
- 加载预训练YOLO模型，对图片批量推理
- 只保留车辆相关类别（car=2, motorcycle=3, bus=5, truck=7, bicycle=1）
- 类别映射到K230项目类别：
  - 0: car (小汽车)
  - 1: motorcycle (摩托车/电动车)
  - 2: truck (货车)
  - 3: bus (公交车)
  - 4: bicycle (自行车)
- 支持置信度筛选（默认≥0.5）
- 输出YOLO格式标注文件（.txt）
- 支持批量处理目录
- 生成标注统计报告

**核心API**：
```python
class AutoLabeler:
    def __init__(self, model_path, conf_threshold=0.5, class_mapping=None):
        """初始化自动标注器"""
    
    def label_image(self, image_path, output_label_path):
        """标注单张图片，返回标注信息"""
        # 返回: {'boxes': [...], 'labels': [...], 'scores': [...]}
    
    def label_directory(self, image_dir, label_dir):
        """批量标注目录下所有图片"""
        # 返回: {'total': N, 'labeled': M, 'empty': K, 'by_class': {...}}
```

**类别映射表**（COCO → 智瞳项目）：
```python
DEFAULT_CLASS_MAPPING = {
    2: 0,    # car → car
    3: 1,    # motorcycle → motorcycle
    5: 3,    # bus → bus
    7: 2,    # truck → truck
    1: 4,    # bicycle → bicycle
}
PROJECT_LABELS = ["car", "motorcycle", "truck", "bus", "bicycle"]
```

---

### 步骤 4：数据集管理工具开发

**目标**：数据集划分、统计、清洗、格式转换

**文件**：`tools\dataset_manager.py`

**功能要求**：

1. **数据集划分**：
   - 按比例随机划分 train/val/test（默认 7:2:1）
   - 保证图片和标注同步移动
   - 保证各类别比例均匀（分层抽样）

2. **数据集统计**：
   - 各子集图片数量
   - 各类别目标数量统计
   - 标注框尺寸分布
   - 生成统计报告（JSON + 控制台输出）

3. **数据集清洗**：
   - 检测空标注文件（无目标的图片）
   - 检测标注格式错误
   - 检测损坏图片
   - 可选：删除低质量数据

4. **data.yaml生成**：
   - 自动生成YOLO训练用的data.yaml

**核心API**：
```python
class DatasetManager:
    def __init__(self, dataset_root):
        """初始化数据集管理器"""
    
    def split_dataset(self, images_dir, labels_dir, train_ratio=0.7, val_ratio=0.2):
        """划分训练/验证/测试集"""
    
    def generate_yaml(self, output_path, class_names):
        """生成data.yaml配置文件"""
    
    def get_statistics(self):
        """获取数据集统计信息"""
        # 返回: {'total_images': N, 'by_split': {...}, 'by_class': {...}}
    
    def clean_dataset(self, remove_empty=False, remove_corrupt=True):
        """清洗数据集"""
```

---

### 步骤 5：数据增强工具（可选但推荐）

**目标**：离线数据增强，扩充数据集多样性

**文件**：`tools\data_augment.py`

**功能要求**：
- 支持的增强方式：
  - 水平翻转
  - 随机裁剪
  - 亮度/对比度调整
  - 高斯模糊
  - 噪声添加
  - 随机缩放
- 保持标注同步变换
- 可配置增强概率和强度
- 支持批量处理

**验证**：对几张测试图片运行增强，可视化验证效果

---

### 步骤 6：训练脚本开发与执行

**目标**：实现完整的训练流程，并尝试跑通训练

**文件**：
- `train.py` - 训练主脚本
- `configs\train_config.yaml` - 训练配置

**训练配置**（小样本快速验证）：
```yaml
model: models/yolov8n_pretrained.pt  # 预训练权重
data: data/data.yaml                 # 数据集配置
epochs: 30                           # 训练轮次（验证阶段用30轮）
imgsz: 320                           # 输入尺寸（K230适配）
batch: 16                            # 批次大小
device: cpu                          # 没有GPU就用CPU（慢但能跑）
workers: 2
optimizer: SGD
lr0: 0.01
patience: 15
augment: true
mosaic: 1.0
mixup: 0.1
fliplr: 0.5
degrees: 10.0
translate: 0.1
scale: 0.5
close_mosaic: 5
plots: true
val: true
save: true
project: runs/train
name: k230_vehicle_det
```

**训练脚本要求**：
- 从YAML读取配置
- 支持命令行参数覆盖
- 训练前自动检查数据集
- 训练中输出进度
- 训练后自动保存最佳模型
- 输出训练指标摘要

**注意**：
- 如果数据集图片很少（< 50张），仍然要能跑通训练，用强力数据增强
- 没有GPU时用CPU训练，速度慢但可以验证流程
- 30轮足够验证流程是否正确

---

### 步骤 7：模型评估验收

**目标**：全面评估模型质量，产出验收报告

**文件**：`evaluate.py`

**评估指标**：
1. **基础指标**：
   - mAP50
   - mAP50-95
   - Precision
   - Recall
   - F1-score

2. **分类别指标**：
   - 每个类别的P/R/mAP

3. **速度指标**：
   - 单图推理时间（CPU/GPU）
   - FPS估算

4. **部署可行性评估**：
   - 模型大小（MB）
   - K230部署适配性检查

**输出报告**：`reports\training_report.json`
```json
{
  "model_path": "路径",
  "dataset": "数据集信息",
  "metrics": {
    "map50": 0.xx,
    "map50_95": 0.xx,
    "precision": 0.xx,
    "recall": 0.xx,
    "per_class": {
      "car": {"map50": ..., "precision": ..., "recall": ...},
      ...
    }
  },
  "speed": {"inference_ms": xx, "fps": xx},
  "model_size_mb": xx,
  "k230_deployable": true,
  "overall_pass": true,
  "pass_criteria": {
    "min_map50": 0.5,
    "min_precision": 0.5,
    "max_model_size_mb": 50
  },
  "recommendations": ["..."]
}
```

**通过标准**（初版模型要求低一些）：
- mAP50 ≥ 0.50 （由于是小样本+伪标签，不要求太高）
- 模型能正常推理不报错
- 5个类别至少有3个能检出

---

## 验收标准（全部达标才算PASS）

- [ ] 步骤1：目录结构完整，依赖安装成功，预训练模型就位
- [ ] 步骤2：video_extractor.py 功能完整，可正常抽帧
- [ ] 步骤3：auto_labeler.py 功能完整，能生成YOLO格式标注
- [ ] 步骤4：dataset_manager.py 功能完整，可划分/统计数据集
- [ ] 步骤5：data_augment.py 功能完整（可选，优先完成1-4、6、7）
- [ ] 步骤6：train.py 可正常运行训练，产出模型文件
- [ ] 步骤7：evaluate.py 可正常评估，产出验收报告
- [ ] 至少有一个数据集（哪怕很小）跑通完整流程
- [ ] 所有脚本都有中文注释和使用说明

---

## 数据获取策略（自主完成，无需用户投喂）

按以下优先级尝试获取数据，能获取到哪种用哪种：

### 优先级1：现有项目图片复用
- 检查 `e:\output\1\api\` 下是否有测试图片
- 检查 `e:\output\1\` 下是否有可用于训练的图片
- 检查 `e:\output\1\zhitong\` 下是否有数据

### 优先级2：网络图片下载
- 用Python脚本从必应/百度图片下载车辆相关图片
- 关键词："汽车 道路", "摩托车 行驶", "货车 路口", "公交车", "自行车 道路"
- 下载50-100张即可用于验证流程

### 优先级3：数据增强+小样本
- 即使只有十几张图片，用强力增强也能训练
- 配合mosaic/mixup等增强，验证流程正确性

### 优先级4：纯合成数据（最后手段）
- 用随机背景 + 车辆目标粘贴合成训练数据
- 仅用于验证流程，不指望模型质量

**核心原则**：不管数据多少，必须跑通全流程。质量是迭代出来的，流程通了才能迭代。

---

## 输出文件清单

### 成功时写入 `e:\output\_TASK-002_OUTPUT.json`

```json
{
  "task": "TASK-002_K230车辆检测模型自主训练",
  "timestamp": "ISO8601时间戳",
  "status": "PASS",
  "steps_completed": ["step1_env", "step2_extractor", "step3_labeler", "step4_manager", "step5_augment", "step6_train", "step7_evaluate"],
  "dataset": {
    "total_images": N,
    "train": N1,
    "val": N2,
    "test": N3,
    "by_class": {"car": N, "motorcycle": N, ...}
  },
  "training": {
    "epochs_completed": N,
    "best_model_path": "路径",
    "map50": 0.xx,
    "map50_95": 0.xx
  },
  "evaluation_report_path": "e:\\output\\1\\zhitong\\k230_training\\reports\\training_report.json",
  "k230_deployable": true,
  "tools": {
    "video_extractor": true,
    "auto_labeler": true,
    "dataset_manager": true,
    "data_augment": true
  },
  "details": {}
}
```

### 失败时写入 `e:\output\_TASK-002_ERROR.json`

```json
{
  "task": "TASK-002",
  "failed_at": "失败步骤名称",
  "error_text": "完整原始错误（含stack trace，不得截断）",
  "completed_steps": ["已完成的步骤"],
  "recommendation": "下一步建议"
}
```

---

## 风险提示与应对策略

| 风险 | 应对 |
|------|------|
| 没有GPU训练太慢 | 用CPU跑30轮验证流程，不追求精度 |
| 数据集太小 | 拉满数据增强，能用就行，流程优先 |
| ultralytics安装失败 | 先试pip install，失败就降级版本 |
| 下载图片被封 | 降低频率、增加延时、换关键词 |
| 内存不足跑不动 | 减小batch size、降低图片分辨率 |
| 训练中报错中断 | 从最近的checkpoint继续训练 |

---

## 执行原则

1. **流程优先**：先跑通，再优化。哪怕数据少、精度低，全流程跑通最重要
2. **自主决策**：遇到问题自行判断解决，不要等待用户指示
3. **逐步验证**：每个工具写完就测试，不要攒到最后
4. **详细日志**：所有操作都要有输出，便于排查问题
5. **质量记录**：每个步骤的结果都要写入报告

---

*本通知由指挥官建立 · 执行完成后报告结果文件路径 + 整体状态*
