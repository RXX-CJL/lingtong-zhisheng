# TASK-005 任务通知单：用conda安装CUDA + 软件端完善

## 一、任务目标
1. 使用conda创建独立环境并安装CUDA版PyTorch（必须成功）
2. 完善软件端：后端API、前端管理后台、数字孪生
3. 头盔检测作为次要任务，能弄就弄，不能弄跳过

## 二、项目信息
- **主项目路径**：e:\output\1\
- **后端API路径**：e:\output\1\api\
- **前端管理后台**：e:\output\1\web-admin\
- **数字孪生**：e:\output\1\digital_twin\
- **模型路径**：e:\output\1\zhitong\training\models\

---

## 三、第一部分：CUDA环境搭建（最高优先级）

### 任务1：检查并创建conda环境
**优先级**：🔴 最高

**步骤**：
1. 检查conda是否安装：`conda --version`
2. 如果没装，安装Miniconda（从清华镜像下载）
3. 创建新环境：`conda create -n zhitong-gpu python=3.11 -y`
4. 激活环境：`conda activate zhitong-gpu`
5. 确认Python版本：`python --version`（应为3.11.x）

**注意**：Python 3.11兼容性最好，不要用3.12/3.13

---

### 任务2：安装CUDA版PyTorch（通过conda）
**优先级**：🔴 最高

**步骤**：
1. 确认环境已激活：`conda activate zhitong-gpu`
2. 使用conda安装（推荐，自动处理CUDA依赖）：
   ```bash
   conda install pytorch torchvision torchaudio pytorch-cuda=12.4 -c pytorch -c nvidia
   ```
3. 验证：`python -c "import torch; print(torch.__version__); print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0))"`
4. 如果上面失败，尝试指定版本：
   ```bash
   conda install pytorch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 pytorch-cuda=12.1 -c pytorch -c nvidia
   ```
5. 安装ultralytics：`pip install ultralytics`

**验收标准**：
- torch.cuda.is_available() == True
- 能检测到RTX 4060显卡
- YOLO模型能在GPU上推理

---

### 任务3：环境迁移与配置
**优先级**：🟠 高

把现有项目依赖迁移到新环境：
1. 安装项目依赖：`pip install -r e:\output\1\api\requirements.txt`
2. 安装dashscope：`pip install dashscope`
3. 安装fastapi相关：`pip install fastapi uvicorn python-multipart`
4. 测试后端API能否启动：`python e:\output\1\api\app.py`

---

## 四、第二部分：软件端完善（高优先级）

### 任务4：后端API完善
**优先级**：🟠 高

完善以下API功能：
1. 违规类型扩展：支持5种违规（未戴头盔、违停、压线、逆行、闯红灯）
2. 规则引擎集成：把violation_rules.py集成到image_recognizer.py
3. 批量处理：支持批量上传图片检测
4. 模型热切换：支持运行时切换检测模型
5. 性能统计：记录每次检测耗时、置信度分布

**修改文件**：e:\output\1\api\image_recognizer.py

---

### 任务5：前端管理后台完善
**优先级**：🟠 高

完成之前TASK-001的前端任务：

| 页面 | 功能 |
|------|------|
| Dashboard | 统计卡片（今日违规数、设备数、在线率）、4个统计图表 |
| 违规列表页 | 筛选（时间、类型、状态）、分页、批量审核、导出 |
| 违规详情页 | 大图查看、推理过程展示、审核操作、历史记录 |
| 设备管理页 | 设备列表、设备详情、在线状态、控制指令 |
| 系统设置页 | AI配置、通知设置、用户管理 |

**技术栈**：Vue 3 + Element Plus + Chart.js

---

### 任务6：数字孪生增强
**优先级**：🟡 中

增强数字孪生系统：
1. 接入后端真实数据（替换模拟数据）
2. 增加3D元素（建筑物、树木、路灯）
3. 违规事件回放（支持时间段选择）
4. 统计图表面板（实时违规统计）
5. 摄像头视角模拟（从各个摄像头位置看场景）

---

## 五、第三部分：头盔检测（次要任务）

### 任务7：头盔检测模型尝试
**优先级**：🟢 低

尝试找到头盔检测模型：
1. HuggingFace搜索：helmet detection model
2. GitHub搜索：YOLOv8 helmet detection
3. 如果找不到现成模型，下载数据集微调训练
4. 如果数据不足或训练失败，**可以跳过**

**注意**：这是次要任务，不要在这里花太多时间

---

## 六、验收标准

### CUDA部分
1. ✅ conda环境创建成功（zhitong-gpu）
2. ✅ CUDA版PyTorch安装成功（torch.cuda.is_available() == True）
3. ✅ RTX 4060可用
4. ✅ 项目依赖安装成功
5. ✅ 后端API能正常启动

### 软件端部分
1. ✅ 规则引擎集成到检测流程
2. ✅ 前端5个页面完整可用
3. ✅ 数字孪生接入真实数据
4. ✅ 系统能完整跑通（上传图片→检测→显示结果）

---

## 七、执行顺序
1. 任务1：检查conda环境
2. 任务2：安装CUDA版PyTorch（必须成功）
3. 任务3：环境迁移配置
4. 任务4：后端API完善
5. 任务5：前端管理后台完善
6. 任务6：数字孪生增强
7. 任务7：头盔检测（可选）

---

## 八、输出要求
1. CUDA安装日志：e:\output\1\zhitong\training\logs\cuda_install_conda.log
2. 环境配置文件：e:\output\1\zhitong\training\conda_env.yaml
3. 更新后的后端API：e:\output\1\api\image_recognizer.py
4. 更新后的前端：e:\output\1\web-admin\src\
5. 更新后的数字孪生：e:\output\1\digital_twin\
6. 完成后写入结果文件：e:\_TASK-005_OUTPUT.json

---

## 九、注意事项
1. 优先保证CUDA安装成功，这是本次任务的核心
2. 头盔检测是次要任务，不要浪费太多时间
3. 前端页面要美观实用，参考Element Plus官方示例
4. 所有修改要兼容现有代码，不要破坏已有功能

---
**任务下发时间**：2026-07-13
**预计完成时间**：8-12小时
**优先级**：最高
