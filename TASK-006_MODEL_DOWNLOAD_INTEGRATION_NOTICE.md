# TASK-006 任务通知单：下载现成模型 + 组合检测系统

## 一、任务目标
1. 下载现成的违规检测相关模型（站在巨人肩膀上）
2. 整合多模型串联检测系统（车辆+车牌+红绿灯+头盔+规则引擎）
3. 完善5种违规行为检测逻辑
4. K230车牌检测代码移植到项目

## 二、项目信息
- **主项目路径**：e:\output\1\
- **后端API路径**：e:\output\1\api\
- **模型路径**：e:\output\1\zhitong\training\models\
- **K230源码路径**：e:\output\1\K230\程序源码\09.Scene\
- **规则引擎**：e:\output\1\api\violation_rules.py

---

## 三、参考文件
1. K230车牌检测：e:\output\1\K230\程序源码\09.Scene\06.licence_det.py
2. K230车牌识别：e:\output\1\K230\程序源码\09.Scene\07.licence_det_rec.py
3. 现有检测模块：e:\output\1\api\image_recognizer.py
4. 规则引擎：e:\output\1\api\violation_rules.py

---

## 四、任务清单

### 任务1：下载现成模型（最高优先级）
**优先级**：🔴 最高

**目标**：下载4个现成YOLO模型，不要自己训练！

| 模型 | 来源 | 关键词 | 保存路径 |
|------|------|--------|---------|
| **红绿灯检测** | HuggingFace/GitHub | traffic light detection YOLOv8 | models/traffic_light.pt |
| **头盔检测** | HuggingFace/GitHub | helmet detection YOLOv8 safety | models/helmet.pt |
| **车道线检测** | GitHub/CV技术 | lane detection YOLOv8 | models/lane.pt |
| **车辆检测** | Ultralytics官方 | yolov8s（已下载） | models/yolov8s.pt |

**下载渠道**：
1. HuggingFace搜索关键词：traffic light detection, helmet detection, lane detection
2. GitHub搜索：YOLOv8 traffic light model, YOLOv8 helmet detection model
3. 如果找不到免费模型，下载数据集微调训练

**验收**：每个模型下载成功后，输出类别列表验证：
```python
from ultralytics import YOLO
m = YOLO('model.pt')
print(m.names)
```
- 红绿灯模型应包含：red_light, yellow_light, green_light
- 头盔模型应包含：helmet, head, no_helmet等
- 车道线模型应包含：lane_line, road_line等

---

### 任务2：整合多模型串联检测系统
**优先级**：🔴 最高

**目标**：在image_recognizer.py中实现多模型串联检测

**检测流程**：
```
图片输入
    ↓
yolov8s（检测车辆：car/motorcycle/truck/bus/bicycle）
    ↓
traffic_light（检测红绿灯：red/yellow/green）
    ↓
helmet（检测头盔：helmet/no_helmet）
    ↓
lane（检测车道线）
    ↓
规则引擎（判断违规类型）
    ↓
结果输出（含违规类型、车牌、置信度）
```

**修改文件**：e:\output\1\api\image_recognizer.py

**新增方法**：
```python
def multi_model_detect(image_input):
    """多模型串联检测"""
    # 1. 车辆检测
    # 2. 红绿灯检测
    # 3. 头盔检测
    # 4. 车道线检测
    # 5. 规则引擎判断违规
    return results
```

**验收**：
- 支持同时调用多个模型
- 返回结构化检测结果
- 类别名中文显示

---

### 任务3：完善规则引擎（5种违规）
**优先级**：🔴 最高

**目标**：完善violation_rules.py，实现5种违规判断

**违规类型及判断逻辑**：

| 违规类型 | 判断规则 | 需要的检测结果 |
|---------|---------|--------------|
| **闯红灯** | 红灯状态下，车辆越过停止线 | 红绿灯检测 + 车辆位置 |
| **逆行** | 车辆行驶方向与道路方向相反 | 车辆位置 + 道路方向配置 |
| **压线** | 车辆检测框与车道线重叠 | 车道线检测 + 车辆检测 |
| **违停** | 车辆在禁停区域停留超过N秒 | 车辆检测 + 时间分析 |
| **未戴头盔** | 检测到motorcycle但未检测到helmet | 车辆检测 + 头盔检测 |

**修改文件**：e:\output\1\api\violation_rules.py

**验收**：
- 5种违规判断逻辑完整
- 可配置参数（阈值、时间等）
- 返回结构化违规结果（类型、置信度、位置）

---

### 任务4：车牌检测整合
**优先级**：🟠 高

**目标**：将K230的车牌检测逻辑整合到后端

**方案**：
1. 在后端API中添加车牌检测接口
2. 使用YOLOv8车牌检测模型（如果能下载到）
3. 使用OCR识别车牌字符（PaddleOCR或CRNN）
4. 如果没有车牌检测模型，使用K230端的车牌识别结果（通过HTTP上报）

**修改文件**：e:\output\1\api\image_recognizer.py

**新增接口**：
```python
def detect_license_plate(image_input):
    """检测并识别车牌"""
    # 1. 检测车牌位置
    # 2. 识别车牌字符
    return {'plate_number': '粤A12345', 'confidence': 0.95}
```

**验收**：
- 能检测车牌位置
- 能识别车牌字符
- 返回车牌号码和置信度

---

### 任务5：K230端检测程序移植
**优先级**：🟠 高

**目标**：基于K230现成代码，创建项目专用检测程序

**参考代码**：
- 车牌检测：e:\output\1\K230\程序源码\09.Scene\06.licence_det.py
- 车牌识别：e:\output\1\K230\程序源码\09.Scene\07.licence_det_rec.py
- 目标检测：e:\output\1\K230\程序源码\09.Scene\03.object_detect_yolov8n.py

**修改内容**：
1. 将串口上报改为HTTP上报
2. 添加WiFi连接逻辑
3. 整合违规检测逻辑
4. 添加语音播报（中文TTS）
5. 添加OLED显示

**输出文件**：e:\output\1\K230\zhitong_detect.py

**验收**：
- K230端代码完整
- HTTP上报逻辑正确
- WiFi连接正常

---

### 任务6：测试整体检测效果
**优先级**：🟡 中

**目标**：测试多模型检测系统效果

**测试内容**：
1. 使用测试图片测试各模型
2. 测试违规判断逻辑
3. 测试车牌识别效果
4. 测试API接口响应速度
5. 生成测试报告

**报告位置**：e:\output\1\zhitong\training\reports\integration_test_report.md

**验收**：
- 各模型能正常加载和推理
- 违规判断逻辑正确
- API接口响应正常

---

## 五、验收标准

### 模型下载
1. ✅ 红绿灯检测模型下载成功
2. ✅ 头盔检测模型下载成功（含helmet类别）
3. ✅ 车道线检测模型下载成功
4. ✅ 各模型类别验证通过

### 多模型整合
1. ✅ image_recognizer.py支持多模型串联
2. ✅ 类别名中文显示
3. ✅ 返回结构化检测结果

### 规则引擎
1. ✅ 5种违规判断逻辑完整
2. ✅ 参数可配置
3. ✅ 与检测结果正确关联

### K230移植
1. ✅ 车牌检测+识别代码完整
2. ✅ HTTP上报逻辑正确
3. ✅ WiFi连接代码完整

---

## 六、执行顺序
1. 任务1：下载现成模型（先做，其他任务依赖）
2. 任务2：整合多模型检测系统
3. 任务3：完善规则引擎
4. 任务4：车牌检测整合
5. 任务5：K230端检测程序移植
6. 任务6：测试整体效果

---

## 七、输出要求
1. 下载的模型：e:\output\1\zhitong\training\models\
2. 更新后的image_recognizer.py：e:\output\1\api\image_recognizer.py
3. 更新后的violation_rules.py：e:\output\1\api\violation_rules.py
4. K230端代码：e:\output\1\K230\zhitong_detect.py
5. 测试报告：e:\output\1\zhitong\training\reports\integration_test_report.md
6. 完成后写入结果文件：e:\_TASK-006_OUTPUT.json

---

## 八、注意事项
1. **不要自己训练！** 优先下载现成模型，找不到再微调
2. **类别名要中文**，最终用户看到的是中文
3. **K230代码要基于现成代码改**，不要从零写
4. **所有模型要能在CPU和GPU上运行**
5. **API接口要兼容现有前端**

---
**任务下发时间**：2026-07-15
**预计完成时间**：8-12小时
**优先级**：最高
