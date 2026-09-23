# TASK-003 任务通知单：下载现成YOLO模型并集成

## 一、任务目标
利用开源预训练模型快速构建智瞳项目的违规检测能力，跳过从零训练的漫长过程。

## 二、项目信息
- **项目路径**：e:\output\1\zhitong\training\
- **模型下载工具**：model_downloader.py（已创建）
- **当前模型**：仅yolov8n.pt（通用目标检测）
- **目标模型**：头盔检测、交通违规检测等专用模型

## 三、参考文件
1. 模型下载工具：e:\output\1\zhitong\training\model_downloader.py
2. 训练工具链：e:\output\1\zhitong\training\
3. 后端API：e:\output\1\api\image_recognizer.py

## 四、具体任务清单

### 任务0：安装CUDA版PyTorch（VPN已开启）
**优先级**：最高

当前PyTorch是CPU版本（2.13.0+cpu），需要安装CUDA版以使用RTX 4060显卡。

**安装命令**：
```bash
pip install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

**验证命令**：
```bash
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

**要求**：
- 必须验证 torch.cuda.is_available() == True
- 必须验证能检测到RTX 4060显卡
- 验证成功后再继续后续任务
- 如果安装失败，记录错误信息

### 任务1：下载开源预训练模型
**优先级**：最高

使用model_downloader.py下载以下模型：

| 模型 | 来源 | 用途 | 类别 |
|------|------|------|------|
| yolov8n.pt | Ultralytics官方 | 通用目标检测 | 80类 |
| yolov8s.pt | Ultralytics官方 | 中等规模检测 | 80类 |
| helmet模型 | HuggingFace | 头盔佩戴检测 | helmet, rider |
| 交通违规模型 | GitHub/网络 | 违规行为检测 | 多种违规 |

**下载地址**：
- HuggingFace: arnabdhar/YOLOv8-Helmet-Detection
- GitHub: 搜索 "YOLOv8 traffic violation detection"
- 百度网盘: 搜索 "YOLOv8 头盔检测 模型"

**要求**：
- 下载到 e:\output\1\zhitong\training\models\ 目录
- 记录每个模型的类别列表和来源
- 如果网络下载失败，尝试国内镜像

### 任务2：测试模型效果
**优先级**：高

对每个下载的模型进行测试：
- 使用 evaluate.py 评估模型性能
- 用测试图片验证检测效果
- 记录每个模型能检测哪些类别
- 重点关注：车辆、头盔、红绿灯

**要求**：
- 生成测试报告
- 记录模型大小和推理速度
- 确认模型的类别名称和ID映射

### 任务3：整合多模型检测系统
**优先级**：最高

将多个模型整合到检测流程中：

```
检测流程：
    输入图片
        ↓
    yolov8n（车辆检测）
        ↓
    helmet模型（头盔检测）
        ↓
    违规判断（规则引擎）
        ↓
    输出违规结果
```

**要求**：
- 修改 image_recognizer.py 支持多模型
- 检测流程：先检测车辆→再检测头盔→最后判断违规
- 支持中文类别名称显示
- 保留原有YOLO+豆包+DeepSeek的融合逻辑

### 任务4：实现违规行为检测规则
**优先级**：高

基于检测结果实现规则引擎：

| 违规行为 | 检测规则 | 需要的模型 |
|---------|---------|-----------|
| 未戴头盔 | 检测到motorcycle但未检测到helmet | helmet模型 |
| 违停 | 车辆在禁停区域停留超过N秒 | yolov8n |
| 压线 | 车辆位置与车道线重叠 | yolov8n + 车道线检测 |
| 逆行 | 车辆行驶方向与道路方向相反 | yolov8n + 方向判断 |
| 闯红灯 | 红灯时车辆越过停止线 | yolov8n + 红绿灯检测 |

**要求**：
- 编写规则引擎模块
- 支持配置化规则（阈值、时间等）
- 输出结构化违规结果

### 任务5：修改类别为中文显示
**优先级**：中

将模型类别名称改为中文：

| 英文类别 | 中文类别 |
|---------|---------|
| car | 轿车 |
| motorcycle | 摩托车 |
| truck | 卡车 |
| bus | 公交车 |
| bicycle | 自行车 |
| helmet | 头盔 |
| rider | 骑手 |

**要求**：
- 修改 data.yaml 中的类别名称
- 修改检测结果输出为中文
- 修改前端显示为中文

## 五、验收标准

### 模型要求
1. ✅ 至少下载3个预训练模型
2. ✅ 头盔检测模型能正常工作
3. ✅ 模型推理速度 > 10 FPS

### 功能要求
1. ✅ 支持多模型串联检测
2. ✅ 规则引擎能判断至少3种违规
3. ✅ 检测结果输出中文类别名称
4. ✅ 与后端API集成正常

## 六、执行步骤
1. 运行 model_downloader.py 下载模型
2. 测试每个模型的效果
3. 修改 image_recognizer.py 支持多模型
4. 编写规则引擎模块
5. 修改类别为中文显示
6. 测试完整检测流程

## 七、输出要求
1. 模型文件：e:\output\1\zhitong\training\models\*.pt
2. 模型测试报告：reports/model_test_report.md
3. 更新后的检测模块：e:\output\1\api\image_recognizer.py
4. 规则引擎模块：e:\output\1\api\violation_rules.py
5. 完成后写入结果文件：e:\_TASK-003_MODEL_OUTPUT.json

## 八、注意事项
1. 优先使用国内镜像下载模型（HuggingFace镜像）
2. 如果下载失败，尝试百度网盘等国内资源
3. 模型只需下载一次，后续复用
4. 保留原有模型文件，不要覆盖
5. 中文类别只在显示层修改，模型内部仍用英文

---
**任务下发时间**：2026-07-13
**预计完成时间**：4-6小时
**优先级**：最高
