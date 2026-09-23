# TASK-002 任务通知单：数据集收集 + GPU训练全流程

## 一、任务目标
完成从数据集收集到模型训练的全流程：
1. 收集不少于5000张带标注的车辆图片
2. 配置GPU训练环境（RTX 4060）
3. 训练出可用的YOLOv8车辆检测模型
4. 评估模型性能并导出ONNX格式

## 二、项目信息
- **项目路径**：e:\output\1\zhitong\data_tools\
- **工作目录**：e:\output\1\zhitong\data_tools\data\
- **已有数据**：COCO128提取的22张车辆图片（76个目标）
- **目标数据量**：5000张以上带标注的车辆图片
- **检测类别**：car(轿车), motorcycle(摩托车), truck(卡车), bus(公交车), bicycle(自行车)

## 三、参考文件
1. 数据工具目录：e:\output\1\zhitong\data_tools\
2. 数据集准备脚本：e:\output\1\zhitong\data_tools\data_prep.py
3. 数据增强工具：e:\output\1\zhitong\training\data_augment.py
4. 训练工具链：e:\output\1\zhitong\training\

## 四、具体任务清单

### 任务1：下载公开车辆检测数据集
**优先级**：最高

搜索并下载以下公开数据集（找到哪个下哪个，越多越好）：

| 数据集名称 | 说明 | 预计数量 |
|-----------|------|---------|
| UA-DETRAC | 交通监控车辆检测数据集 | ~8250车辆 |
| BITVehicle | 车辆检测数据集 | ~9850张 |
| PASCAL VOC | 包含车辆类别 | ~1万张含车 |
| KITTI | 自动驾驶车辆检测 | ~7000张 |
| 其他车辆数据集 | 能找到的都可以 | 越多越好 |

**要求**：
- 下载到 e:\output\1\zhitong\data_tools\data\datasets\ 目录下
- 每个数据集建一个子文件夹
- 记录下载来源和数据集说明
- 优先下载体积小、标注格式清晰的数据集

### 任务2：数据集格式转换
**优先级**：高

将下载的数据集统一转换为YOLO格式：
- 图片：data/images/raw/
- 标注：data/labels/raw/
- 类别映射：
  - car/轿车/小汽车 → 0
  - motorcycle/摩托车 → 1  
  - truck/卡车 → 2
  - bus/公交车/巴士 → 3
  - bicycle/自行车 → 4

**要求**：
- 编写转换脚本（converters/目录下）
- 支持VOC格式、COCO格式、UA-DETRAC格式等
- 转换后统计类别分布
- 去除重复或模糊的图片

### 任务3：网络图片爬取补充
**优先级**：中

如果公开数据集不够，从网络爬取补充：
- 关键词："交通监控"、"路口监控"、"城市道路"、"高速公路监控"
- 来源：百度图片、必应图片等（合法范围内）
- 使用YOLO预训练模型自动标注
- 人工筛选（可选，先自动标注）

**要求**：
- 爬取不少于2000张图片
- 自动标注后筛选置信度≥0.5的
- 去重（感知哈希）
- 保存到data/images/raw/和data/labels/raw/

### 任务4：数据集质量清洗
**优先级**：高

对所有收集到的数据进行清洗：
- 感知哈希去重（阈值=5）
- 删除模糊/过曝/欠曝图片
- 删除标注框异常的（宽高为0、超出图片范围）
- 类别数量平衡（如果某类太少，针对性补充）

**要求**：
- 编写清洗脚本 clean_dataset.py
- 输出清洗报告（删除数量、原因统计）
- 清洗后的数据保存到最终数据集目录

### 任务5：构建最终训练数据集
**优先级**：最高

将所有数据整合为最终训练集：
- 按7:2:1划分train/val/test
- 生成data.yaml配置文件
- 统计数据集信息（各类别数量、各集数量）
- 生成数据集报告

### 任务6：数据增强扩充
**优先级**：中

如果数据量仍然不足，使用增强工具扩充：
- 水平翻转、旋转、亮度变化、模糊、噪声
- 每张图生成5-10个增强版本
- 使用 data_augment.py 工具

### 任务7：配置GPU训练环境
**优先级**：最高

当前PyTorch是CPU版本，需要安装CUDA版以使用RTX 4060显卡：
- 检查当前Python环境和PyTorch版本
- 安装CUDA版PyTorch（对应CUDA 12.4）
  命令参考：`pip install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124`
- 验证torch.cuda.is_available() == True
- 验证能检测到RTX 4060显卡
- 重装ultralytics（确保兼容GPU版torch）

**要求**：
- 必须能使用GPU训练
- 训练脚本device设置为0（使用第0块GPU）
- 如果安装失败，记录错误信息，尝试其他版本

### 任务8：YOLO模型训练
**优先级**：最高

使用收集的数据集训练YOLOv8n模型：
- 训练配置文件：e:\output\1\zhitong\training\configs\train_config.yaml
- 训练脚本：e:\output\1\zhitong\training\train.py
- 参数：imgsz=320, epochs=200, batch=32（GPU显存足够可调大）
- 使用GPU训练（device=0）
- 训练完成后自动复制best.pt到models/目录

**要求**：
- 训练过程中定期保存检查点
- 记录训练日志（loss、mAP等指标变化）
- 目标mAP50 ≥ 0.85
- 如果数据量小导致过拟合，调小epoch或增加数据增强

### 任务9：模型评估与导出
**优先级**：高

训练完成后：
- 运行评估脚本：e:\output\1\zhitong\training\evaluate.py
- 输出完整评估报告（mAP50, mAP50-95, Precision, Recall, F1）
- 分类别统计性能
- 导出ONNX格式模型：e:\output\1\zhitong\training\export.py
- 验证ONNX模型推理正确性

**要求**：
- 评估报告保存为Markdown和JSON格式
- ONNX模型能正常推理
- 记录模型大小、推理速度（FPS）

## 五、验收标准

### 数据量要求
1. ✅ 最终训练集≥5000张图片
2. ✅ 每类目标≥500个
3. ✅ 验证集≥500张，测试集≥500张

### 质量要求
1. ✅ 无重复图片（感知哈希去重）
2. ✅ 标注格式正确（YOLO格式，归一化坐标）
3. ✅ 图片清晰，无严重模糊/过曝
4. ✅ 类别分布相对均衡（最多:最少 ≤ 5:1）

### 文档要求
1. ✅ 数据集统计报告（JSON + Markdown）
2. ✅ 数据来源说明
3. ✅ 转换脚本有注释和使用说明
4. ✅ 最终data.yaml配置正确

### 模型训练要求
1. ✅ GPU训练正常运行（RTX 4060）
2. ✅ 训练日志完整（loss曲线、mAP变化）
3. ✅ 最佳模型保存：models/best.pt
4. ✅ mAP50 ≥ 0.80（数据足够时）
5. ✅ ONNX模型导出成功

## 六、执行步骤
1. 先检查现有数据工具和目录结构
2. 配置GPU训练环境（安装CUDA版PyTorch）
3. 搜索并下载公开数据集
4. 转换数据集格式为YOLO格式
5. 数据清洗和去重
6. 补充网络爬取数据（如需要）
7. 数据增强扩充（如需要）
8. 划分数据集并生成配置
9. 启动YOLO模型训练（GPU）
10. 模型评估与导出ONNX
11. 生成数据集统计报告和训练报告

## 七、输出要求
1. 所有数据保存到 e:\output\1\zhitong\data_tools\data\ 目录
2. 转换脚本保存到 e:\output\1\zhitong\data_tools\converters\ 目录
3. 最终数据集配置：data/data.yaml
4. 数据集统计报告：data/dataset_report.md
5. 训练好的模型：e:\output\1\zhitong\training\models\best.pt
6. 训练报告：e:\output\1\zhitong\training\reports\training_report.md
7. 评估报告：e:\output\1\zhitong\training\reports\evaluation_report.md
8. ONNX模型：e:\output\1\zhitong\training\models\best.onnx
9. 完成后写入结果文件：e:\_TASK-002_DATASET_OUTPUT.json

## 八、注意事项
1. 数据收集仅用于模型训练研究，不得用于商业用途
2. 爬取网络图片时遵守网站robots.txt规定
3. 优先使用公开免费的学术数据集
4. 数据集转换时注意保留原始标注信息
5. 遇到下载不了的数据集就跳过，找下一个
6. 尽量多找不同来源的数据，提高模型泛化能力
7. 有任何问题在结果文件中说明

---
**任务下发时间**：2026-07-12
**预计完成时间**：12-24小时
**优先级**：最高
**任务类型**：长时间任务
**硬件**：RTX 4060 8GB GPU
