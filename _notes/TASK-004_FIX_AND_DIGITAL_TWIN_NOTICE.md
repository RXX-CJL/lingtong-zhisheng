# TASK-004 任务通知单：违规检测补全 + 数字孪生启动

## 一、任务目标
1. 修复TASK-003遗留问题（CUDA、头盔模型、规则引擎）
2. 启动数字孪生项目，搭建基础3D场景

## 二、项目信息
- **主项目路径**：e:\output\1\
- **智瞳模型路径**：e:\output\1\zhitong\training\
- **后端API路径**：e:\output\1\api\
- **数字孪生新目录**：e:\output\1\digital-twin\

## 三、参考文件
1. 检测模块：e:\output\1\api\image_recognizer.py
2. 模型目录：e:\output\1\zhitong\training\models\
3. 模型下载记录：e:\output\1\zhitong\training\models\download_records.json
4. 训练工具：e:\output\1\zhitong\training\

---

## 四、第一部分：修复与补全（优先级最高）

### 任务1：安装CUDA版PyTorch（VPN已开启）
**优先级**：🔴 最高

当前PyTorch是CPU版本，必须安装CUDA版才能用RTX 4060。

**步骤**：
1. 运行：`pip install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124`
2. 验证：`python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0))"`
3. 重装ultralytics：`pip install --force-reinstall ultralytics`
4. 记录安装日志，失败则记录错误信息

**验收**：torch.cuda.is_available() == True，能检测到RTX 4060

---

### 任务2：寻找真正的头盔检测模型
**优先级**：🔴 最高

当前下载的"头盔模型"实际只有5类车辆（car/motorcycle/truck/bus/bicycle），**没有helmet类别**，是假的头盔模型！

**寻找目标**：
- 能检测helmet（头盔）和no_helmet（未戴头盔）的模型
- 或者检测head（头部）+ helmet的模型
- 类别数应该≥2（helmet/no_helmet 或 head/helmet）

**寻找渠道**：
1. HuggingFace搜索关键词：helmet detection, safety helmet, motorcycle helmet
2. GitHub搜索：YOLOv8 helmet detection model
3. 百度网盘/CSDN搜索：头盔检测模型 权重
4. 如果找不到现成的，下载头盔数据集，用yolov8n微调训练

**验收**：模型类别中包含helmet或head类别

---

### 任务3：编写违规检测规则引擎
**优先级**：🔴 最高

创建文件：e:\output\1\api\violation_rules.py

实现以下违规判断规则：

| 违规类型 | 判断规则 | 输入 |
|---------|---------|------|
| 未戴头盔 | 检测到motorcycle但对应区域没有helmet | 车辆检测+头盔检测 |
| 违停 | 车辆在禁停区域停留超过N秒 | 车辆检测+区域配置 |
| 闯红灯 | 红灯状态下车辆越过停止线 | 红绿灯检测+车辆位置 |
| 压线 | 车辆与车道线重叠 | 车辆检测+车道线 |
| 逆行 | 车辆行驶方向与道路方向相反 | 车辆轨迹+道路方向 |

**第一版先实现（能做的）**：
1. 未戴头盔检测（等头盔模型到位）
2. 违停检测框架（基于停留时间）
3. 违规结果结构化输出

**要求**：
- 类名：ViolationRuleEngine
- 方法：detect_violations(detections, scene_config)
- 输出结构化违规列表，含违规类型、置信度、位置、时间

---

### 任务4：模型测试与报告
**优先级**：🟠 高

对所有下载的模型进行测试：
- yolov8n.pt（80类通用检测）
- yolov8s.pt（80类通用检测，更大模型）
- 头盔模型（找到后测试）

**测试内容**：
1. 模型加载测试
2. 类别列表输出
3. 推理速度测试（FPS）
4. 用测试图片验证检测效果
5. 生成测试报告

**报告位置**：e:\output\1\zhitong\training\reports\model_test_report.md

---

## 五、第二部分：数字孪生启动（优先级高）

### 任务5：创建数字孪生项目目录结构
**优先级**：🟠 高

创建目录：e:\output\1\digital-twin\

```
digital-twin/
├── public/              # 静态资源
├── src/
│   ├── components/      # 3D组件
│   ├── scenes/          # 场景配置
│   ├── utils/           # 工具函数
│   ├── App.vue          # 主组件
│   └── main.js          # 入口文件
├── package.json
├── vite.config.js
└── README.md
```

**技术选型**：
- 前端框架：Vue 3 + Vite
- 3D引擎：Three.js
- UI组件：Element Plus（与管理后台一致）

---

### 任务6：搭建基础3D场景
**优先级**：🟠 高

创建一个基础的3D路口场景：
1. 地面（马路 + 人行道）
2. 车道线（白色虚线、实线）
3. 红绿灯（可切换颜色）
4. 简单的车辆模型（方块代替即可）
5. 轨道控制器（可旋转/缩放视角）

**技术要求**：
- 使用Three.js
- 场景大小：路口50m x 50m
- 4个方向车道（双向两车道）
- 4组红绿灯（每个路口一组）
- 摄像机初始位置：俯视45度角

---

### 任务7：实时数据接入框架
**优先级**：🟡 中

实现数据接入接口：
1. WebSocket客户端（连接后端推送）
2. 车辆数据结构定义（位置、速度、方向、车牌号）
3. 违规数据结构定义（类型、时间、位置、车辆）
4. 数据驱动的3D更新（车辆移动、违规高亮）

**第一版用模拟数据**：
- 随机生成车辆在路口行驶
- 随机触发违规事件
- 验证3D场景更新是否流畅

---

## 六、验收标准

### 修复部分
1. ✅ CUDA版PyTorch安装成功，RTX 4060可用
2. ✅ 找到并测试真正的头盔检测模型
3. ✅ violation_rules.py 规则引擎可用
4. ✅ 模型测试报告完整

### 数字孪生部分
1. ✅ 项目目录结构完整
2. ✅ 基础3D路口场景可运行
3. ✅ 红绿灯、车道线、车辆可见
4. ✅ 可交互（旋转/缩放）

## 七、执行顺序
1. 先装CUDA（任务1）
2. 找头盔模型（任务2）
3. 写规则引擎（任务3）
4. 模型测试（任务4）
5. 数字孪生项目创建（任务5）
6. 3D场景搭建（任务6）
7. 数据接入框架（任务7）

## 八、输出要求
1. CUDA安装日志：e:\output\1\zhitong\training\logs\cuda_install.log
2. 模型测试报告：e:\output\1\zhitong\training\reports\model_test_report.md
3. 规则引擎：e:\output\1\api\violation_rules.py
4. 数字孪生项目：e:\output\1\digital-twin\
5. 完成后写入结果文件：e:\_TASK-004_OUTPUT.json

---
**任务下发时间**：2026-07-13
**预计完成时间**：6-8小时
**优先级**：最高
