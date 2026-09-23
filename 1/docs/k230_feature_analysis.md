# K230 模型与功能深度分析报告

## 1. 概述

本报告对 K230 开发板的固件备份和程序源码进行了深度分析，提取了可复用的功能模块和算法思路。K230 是嘉楠科技推出的 AI 视觉开发板，搭载 KPU 神经网络处理器，支持多种 AI 模型推理。

> **注意**：K230 使用 `.kmodel` 格式的专用模型文件，无法直接移植到 PC 端。本分析重点提取**算法思路、后处理逻辑和架构设计**，而非直接使用模型文件。

---

## 2. K230 目录结构

### 2.1 固件备份目录 (`e:\output\1\固件备份\`)

| 目录 | 内容 | 重要性 |
|------|------|--------|
| `kmodel/` | 所有 AI 模型文件 | 高 |
| `libs/` | 核心库文件 (PipeLine, AIBase, YOLO, AI2D) | 高 |
| `apps/` | 应用程序 (人脸、人体、物体、OCR等) | 高 |
| `ybUtils/` | 工具模块 (网络、串口、HTTP请求) | 中 |
| `utils/` | 字典文件、配置文件 | 中 |

### 2.2 程序源码目录 (`e:\output\1\k230\程序源码\`)

| 目录 | 内容 | 重要性 |
|------|------|--------|
| `09.Scene/` | 场景应用 (OCR、车牌、目标跟踪) | 高 |
| `10.场景应用/` | 中文场景应用文档和视频 | 中 |
| `14.export/` | 跨平台导出代码 | 低 |

---

## 3. kmodel 模型清单

| 模型名称 | 功能 | 输入尺寸 | 可复用性 |
|----------|------|----------|----------|
| `LPD_640.kmodel` | 车牌检测 | 640×640 | **高** - 算法思路可参考 |
| `licence_reco.kmodel` | 车牌识别 | 220×32 | **高** - 字符字典可复用 |
| `ocr_det_int16.kmodel` | OCR文本检测 | 640×640 | **中** - 后处理逻辑可参考 |
| `ocr_rec_int16.kmodel` | OCR文本识别 | 512×32 | **中** - 字典加载逻辑可参考 |
| `person_detect_yolov5n.kmodel` | 人体检测 | 640×640 | **中** - YOLO结构参考 |
| `face_detection_320.kmodel` | 人脸检测 | 320×320 | **低** - 专用模型 |
| `yolov8n_224.kmodel` | YOLOv8n检测 | 224×224 | **中** - 后处理参考 |
| `yolov8n_320.kmodel` | YOLOv8n检测 | 320×320 | **中** - 后处理参考 |
| `yolov8n_seg_320.kmodel` | YOLOv8n分割 | 320×320 | **中** - 分割后处理参考 |
| `nanotrack_backbone_sim.kmodel` | NanoTrack骨干 | 255×255 | **高** - 跟踪架构参考 |
| `nanotracker_head_calib_k230.kmodel` | NanoTrack头 | - | **高** - 跟踪架构参考 |
| `yunet_640.kmodel` | 人脸检测(Yunet) | 640×640 | **低** - 专用模型 |
| `face_landmark.kmodel` | 人脸关键点 | - | **低** |
| `face_recognition.kmodel` | 人脸识别 | - | **低** |
| `yolov8n-pose.kmodel` | 人体姿态估计 | - | **中** - 姿态后处理参考 |
| `gesture.kmodel` | 手势识别 | - | **低** |
| `hand_det.kmodel` | 手掌检测 | - | **低** |
| `fruit_cls.kmodel` | 水果分类 | - | **低** |
| `kws.kmodel` | 关键词唤醒 | - | **低** |

---

## 4. 核心库文件分析

### 4.1 PipeLine.py

**功能**：视频流处理管线，负责摄像头采集、图像格式转换、OSD绘制

**关键类和方法**：

| 类/方法 | 功能 | 可复用性 |
|---------|------|----------|
| `PipeLine.create()` | 初始化摄像头和显示 | **高** - 架构思路 |
| `PipeLine.get_frame()` | 获取一帧图像 | **高** - 接口设计 |
| `PipeLine.show_image()` | 显示OSD图像 | **高** - 分层显示 |
| `ScopedTiming` | 计时工具 | **高** - 性能监控 |

**设计亮点**：
- 三通道架构：通道0(YUV420)用于显示，通道1(RGB565)用于辅助，通道2(RGB888)用于AI推理
- 宽度16字节对齐优化
- OSD层叠加显示

### 4.2 AIBase.py

**功能**：AI推理基类，封装了推理流程

**核心方法**：

| 方法 | 功能 |
|------|------|
| `preprocess()` | 预处理 (AI2D) |
| `inference()` | 推理 (kpu.run) |
| `postprocess()` | 后处理 (子类实现) |
| `run()` | 完整推理流程 |

**设计亮点**：
- 模板方法模式：子类只需实现 `postprocess()`
- 资源管理：`deinit()` 清理模型和内存

### 4.3 YOLO.py

**功能**：YOLOv5/8/11 模型封装

**关键特性**：
- Letterbox padding 预处理
- 支持检测、分割、OBB多种任务
- 后处理封装在 `aidemo.yolov8_det_postprocess()`

### 4.4 AI2D.py

**功能**：硬件加速图像处理

**支持操作**：
- Crop (裁剪)
- Pad (填充)
- Resize (缩放)
- Shift (平移)
- Affine (仿射变换)

---

## 5. 可复用功能深度分析

### 5.1 车牌检测 + 识别

**文件路径**：
- 检测：`apps/ai_objects/car_license_plate_det/car_license_plate_detection.py`
- 识别：`apps/ai_objects/car_license_plate_recog/car_license_plate_recognition.py`

**架构设计**：

```
输入图像 → [LPD_640.kmodel检测] → 车牌坐标 → [ROI裁剪] → [licence_reco.kmodel识别] → 车牌字符
```

**核心代码逻辑**：

1. **检测阶段** (`LicenceDetectionApp`)：
   - Center Crop 保持 1:1 比例
   - 使用 `aidemo.licence_det_postprocess()` 后处理
   - 坐标还原到原图

2. **识别阶段** (`LicenceRecognitionApp`)：
   - 字符字典：包含31个省份+10个数字+26个字母+特殊字符
   - 输入尺寸：220×32 (长条形)
   - 后处理：argmax + 去重

3. **整合类** (`LicenceRec`)：
   - 检测+识别串联
   - 使用 `aidemo.ocr_rec_preprocess()` 做ROI预处理

**可复用部分**：
- ✅ 车牌字符字典 (`dict_rec`)
- ✅ 检测+识别两阶段架构设计
- ✅ ROI裁剪和预处理思路
- ❌ kmodel模型文件无法直接使用

**移植建议**：
使用 YOLOv8 + CRNN/STN 替代，参考两阶段架构。

---

### 5.2 OCR 检测 + 识别

**文件路径**：
- 检测：`apps/ai_objects/ocr_det/ocr_detection.py`
- 识别：`apps/ai_objects/ocr_recog/ocr_recognition.py`

**架构设计**：

```
输入图像 → [ocr_det_int16.kmodel] → 四边形文本框 → [ROI裁剪] → [ocr_rec_int16.kmodel] → 文本字符串
```

**核心代码逻辑**：

1. **检测阶段** (`OCRDetectionApp`)：
   - Letterbox padding 预处理
   - 使用 `aicube.ocr_post_process()` 后处理
   - 返回四边形坐标 (8个点)

2. **识别阶段** (`OCRRecognitionApp`)：
   - 从文件加载字典 (`dict.txt`)
   - 输入尺寸：512×32
   - 后处理：argmax + 去重 + CTC解码思路

**可复用部分**：
- ✅ 字典加载逻辑 (`read_dict()`)
- ✅ 四边形文本框处理
- ✅ 多区域批量识别限制 (max_regions=4)

---

### 5.3 目标跟踪 (NanoTrack)

**文件路径**：
- `k230/程序源码/09.Scene/08.nanotracker.py`

**架构设计**：

```
初始化阶段 (8秒) → [cropped_test127.kmodel] → 模板特征
                    ↓
追踪阶段 → [nanotrack_backbone_sim.kmodel] → 源特征 → [nanotracker_head.kmodel] → 跟踪结果
```

**核心组件**：

| 类 | 功能 |
|----|------|
| `TrackCropApp` | 模板裁剪和特征提取 |
| `TrackSrcApp` | 源图像裁剪和特征提取 |
| `TrackerApp` | 跟踪头，计算匹配 |
| `NanoTracker` | 整合类，管理跟踪状态 |

**关键算法**：
- Context Amount = 0.5 (模板上下文扩展)
- Padding + Crop 处理边界情况
- 初始化阶段获取模板特征
- 追踪阶段更新跟踪框

**可复用部分**：
- ✅ 双阶段跟踪架构 (模板+搜索)
- ✅ 边界处理逻辑 (padding)
- ✅ 跟踪状态管理
- ❌ kmodel模型文件无法直接使用

**移植建议**：
使用 DeepSORT 或 ByteTrack 替代，参考跟踪状态管理思路。

---

### 5.4 人脸检测

**文件路径**：
- `apps/ai_face/face_det_core/face_detection.py`

**模型**：`face_detection_320.kmodel` (基于 Yunet)

**关键特性**：
- 输入尺寸：320×320
- 使用 anchors 机制 (`prior_data_320.bin`)
- 后处理：`aidemo.face_det_post_process()`

---

### 5.5 人体检测

**文件路径**：
- `apps/ai_body/person_det_core/person_detection.py`

**模型**：`person_detect_yolov5n.kmodel`

**关键特性**：
- 输入尺寸：640×640
- YOLOv5n 架构
- Anchors: `[10,13, 16,30, 33,23, 30,61, 62,45, 59,119, 116,90, 156,198, 373,326]`
- Strides: `[8, 16, 32]`
- 后处理：`aicube.anchorbasedet_post_process()`

---

### 5.6 工具模块

#### 5.6.1 YbRequests.py

**功能**：HTTP/HTTPS 请求处理

**支持功能**：
- GET/POST 请求
- 文件上传/下载
- SSL 支持

**可复用性**：**高** - 可作为云通信参考

#### 5.6.2 YbNetwork.py

**功能**：网络连接管理

**支持功能**：
- WiFi 连接
- AP热点模式
- MQTT 通信

#### 5.6.3 YbProtocol.py

**功能**：自定义协议封装

**支持功能**：
- 人脸检测数据格式
- 人体检测数据格式
- 车牌识别数据格式
- 跟踪数据格式

---

## 6. 可移植到 PC 端的功能清单

### 6.1 高优先级

| 功能 | 来源 | 移植方式 |
|------|------|----------|
| 车牌字符字典 | `car_license_plate_recognition.py` | 直接复制字典列表 |
| 检测+识别两阶段架构 | `LicenceRec`/`OCRDetRec` | 参考架构设计 |
| OCR字典加载逻辑 | `ocr_recognition.py` | 参考文件读取方式 |
| 图像预处理 (letterbox) | `YOLO.py`/`Utils.py` | 参考padding算法 |
| 坐标转换逻辑 | 所有应用 | 参考比例映射公式 |
| 跟踪状态管理 | `NanoTracker` | 参考状态机设计 |
| 计时工具 | `ScopedTiming` | 直接复制使用 |

### 6.2 中优先级

| 功能 | 来源 | 移植方式 |
|------|------|----------|
| HTTP请求封装 | `YbRequests.py` | 参考接口设计 |
| MQTT通信 | `mqtt.py` | 参考连接管理 |
| 四边形文本框处理 | `ocr_detection.py` | 参考坐标处理 |
| ROI裁剪逻辑 | 所有应用 | 参考裁剪参数计算 |

### 6.3 低优先级 (专用硬件相关)

| 功能 | 说明 |
|------|------|
| AI2D硬件加速 | K230专用，无法移植 |
| KPU推理 | K230专用，需用CUDA/TensorRT替代 |
| 摄像头驱动 | K230专用 |
| 显示驱动 | K230专用 |

---

## 7. 移植建议

### 7.1 车牌识别

**建议方案**：YOLOv8 + CRNN/STAR-Net

```
YOLOv8检测车牌 → 仿射变换校正 → CRNN识别字符
```

**参考资源**：
- K230 的字符字典 (31省份+36字符)
- 两阶段架构设计

### 7.2 目标跟踪

**建议方案**：YOLOv8 + DeepSORT/ByteTrack

```
YOLOv8检测 → DeepSORT跟踪 → 轨迹分析 → 违规判断
```

**参考资源**：
- NanoTrack 的状态管理逻辑
- 边界处理思路

### 7.3 OCR

**建议方案**：PaddleOCR 或 EasyOCR

**参考资源**：
- K230 的字典加载方式
- 四边形文本框处理

---

## 8. 总结

### 8.1 K230 资源价值

| 维度 | 价值 |
|------|------|
| **算法思路** | 高 - 两阶段检测+识别架构非常成熟 |
| **后处理逻辑** | 高 - 坐标转换、NMS、字典解码等可直接参考 |
| **架构设计** | 高 - PipeLine、AIBase 的分层设计值得借鉴 |
| **模型文件** | 低 - kmodel格式无法直接使用 |
| **硬件驱动** | 低 - K230专用 |

### 8.2 推荐优先移植

1. **车牌识别架构** - 最成熟，有完整检测+识别流程
2. **目标跟踪状态管理** - 为行为理解提供基础
3. **图像预处理逻辑** - letterbox padding 和坐标转换
4. **计时和性能监控** - ScopedTiming 工具

### 8.3 与当前项目的衔接

当前项目已具备：
- YOLOv8 目标检测
- DeepSORT 多目标跟踪
- 云端 AI 协作

K230 的可复用价值：
- 完善车牌识别功能（当前项目缺少）
- 优化 OCR 识别流程
- 参考两阶段架构设计模式

---

**分析完成时间**：2026-07-26
**分析范围**：固件备份 + 程序源码共 50+ 文件
**可复用功能**：6 大类，15+ 子功能
