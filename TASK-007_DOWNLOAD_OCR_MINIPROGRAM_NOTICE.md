# TASK-007 任务通知单：下载专用模型 + 集成车牌OCR + 完善小程序

## 一、任务目标
1. 下载专用违规检测模型（红绿灯/头盔/车道线）
2. 集成车牌OCR识别功能（使用K230自带模型或PaddleOCR）
3. 完善微信小程序功能

## 二、项目信息
- **主项目路径**：e:\output\1\
- **后端API路径**：e:\output\1\api\
- **模型路径**：e:\output\1\zhitong\training\models\
- **K230源码路径**：e:\output\1\K230\程序源码\
- **K230固件路径**：e:\output\1\K230\固件备份\kmodel\
- **微信小程序路径**：e:\output\1\wechat-miniprogram\

---

## 三、参考文件
1. K230车牌检测：e:\output\1\K230\程序源码\09.Scene\06.licence_det.py
2. K230车牌识别：e:\output\1\K230\程序源码\09.Scene\07.licence_det_rec.py
3. 现有检测模块：e:\output\1\api\image_recognizer.py
4. 规则引擎：e:\output\1\api\violation_rules.py
5. K230现有模型：e:\output\1\K230\固件备份\kmodel\（含LPD_640.kmodel和licence_reco.kmodel）

---

## 四、任务清单

### 任务1：下载专用违规检测模型（最高优先级）
**优先级**：🔴 最高

**目标**：下载3个专用YOLO模型

| 模型 | 搜索关键词 | 期望类别 | 保存路径 |
|------|-----------|---------|---------|
| **红绿灯检测** | traffic light detection YOLOv8 | red_light, yellow_light, green_light | models/traffic_light.pt |
| **头盔检测** | helmet detection YOLOv8 safety | helmet, no_helmet, head | models/helmet.pt |
| **车道线检测** | lane detection YOLOv8 road | lane_line, road_line | models/lane.pt |

**下载渠道**：
1. HuggingFace（优先）
2. GitHub
3. 国内镜像站

**验证方法**：
```python
from ultralytics import YOLO
m = YOLO('model.pt')
print(m.names)  # 检查是否包含期望类别
```

**注意**：VPN已开启，可以正常访问HuggingFace

---

### 任务2：集成车牌OCR识别（高优先级）
**优先级**：🟠 高

**目标**：实现车牌字符识别

**方案**：使用K230自带的车牌识别模型

**K230已有模型**（固件备份中）：
- `LPD_640.kmodel` — 车牌检测（定位）
- `licence_reco.kmodel` — 车牌识别（字符）

**后端方案**：
1. 使用YOLOv8车牌检测模型（如果能下载到）
2. 使用PaddleOCR进行字符识别
3. 或者使用K230端的车牌识别结果（通过HTTP上报）

**修改文件**：e:\output\1\api\image_recognizer.py

**新增功能**：
```python
def detect_license_plate(image_input):
    """检测并识别车牌"""
    # 方案A：YOLO检测 + PaddleOCR识别
    # 方案B：直接返回K230上报的车牌识别结果
    return {
        'plate_number': '粤A12345',
        'confidence': 0.95,
        'bbox': [x, y, w, h]
    }
```

**验收**：
- 能检测车牌位置
- 能识别车牌字符（含中文省份）
- 返回车牌号码和置信度

---

### 任务3：完善微信小程序（高优先级）
**优先级**：🟠 高

**目标**：完善微信小程序用户端功能

**页面清单**：

| 页面 | 功能 | 状态 |
|------|------|------|
| **首页** | 违规记录列表、统计概览 | 待开发 |
| **违规详情** | 违规图片、违规类型、申诉按钮 | 待开发 |
| **申诉页面** | 申诉表单、提交申诉 | 待开发 |
| **个人中心** | 用户信息、消息通知、设置 | 待开发 |

**API接口**（后端已有）：
- GET /api/wechat/violations — 获取违规记录
- POST /api/wechat/appeal — 提交申诉
- GET /api/wechat/user — 获取用户信息

**修改文件**：e:\output\1\wechat-miniprogram\src\

**验收**：
- 4个页面完整
- 能正常调用后端API
- 能显示违规记录和图片
- 能提交申诉

---

### 任务4：更新多模型检测系统（中优先级）
**优先级**：🟡 中

**目标**：将下载的专用模型整合到检测系统

**修改文件**：e:\output\1\api\image_recognizer.py

**更新内容**：
1. 更新MODEL_CONFIG，移除fallback配置
2. 更新multi_model_detect函数，使用真实专用模型
3. 更新类别中文映射（确保专用模型类别正确映射）

**验收**：
- 专用模型能正常加载和推理
- 检测结果包含专用模型的检测结果
- 中文类别显示正确

---

### 任务5：测试整体效果（中优先级）
**优先级**：🟡 中

**目标**：测试所有功能

**测试内容**：
1. 专用模型测试（红绿灯/头盔/车道线）
2. 车牌OCR测试
3. 微信小程序功能测试
4. API接口测试
5. 违规检测端到端测试

**报告位置**：e:\output\1\zhitong\training\reports\final_integration_test_report.md

**验收**：
- 所有测试通过
- 生成完整测试报告

---

## 五、验收标准

### 模型下载
1. ✅ traffic_light.pt 下载成功，包含red/yellow/green类别
2. ✅ helmet.pt 下载成功，包含helmet类别
3. ✅ lane.pt 下载成功，包含lane_line类别

### 车牌OCR
1. ✅ 能检测车牌位置
2. ✅ 能识别车牌字符
3. ✅ 返回车牌号码和置信度

### 微信小程序
1. ✅ 4个页面完整
2. ✅ 能正常调用后端API
3. ✅ 能显示违规记录和图片
4. ✅ 能提交申诉

### 多模型整合
1. ✅ 专用模型能正常加载和推理
2. ✅ 中文类别显示正确
3. ✅ API响应正常

---

## 六、执行顺序
1. 任务1：下载专用模型（先做，其他任务依赖）
2. 任务2：集成车牌OCR
3. 任务3：完善微信小程序
4. 任务4：更新多模型检测系统
5. 任务5：测试整体效果

---

## 七、输出要求
1. 下载的模型：e:\output\1\zhitong\training\models\
2. 更新后的image_recognizer.py：e:\output\1\api\image_recognizer.py
3. 更新后的违规规则：e:\output\1\api\violation_rules.py
4. 微信小程序页面：e:\output\1\wechat-miniprogram\src\
5. 测试报告：e:\output\1\zhitong\training\reports\final_integration_test_report.md
6. 完成后写入结果文件：e:\_TASK-007_OUTPUT.json

---

## 八、注意事项
1. **优先下载现成模型**，不要自己训练
2. **车牌识别优先使用K230自带模型**（LPD_640.kmodel + licence_reco.kmodel）
3. **微信小程序页面要美观**，符合微信设计规范
4. **所有API接口要兼容现有后端**

---
**任务下发时间**：2026-07-15
**预计完成时间**：8-12小时
**优先级**：最高
