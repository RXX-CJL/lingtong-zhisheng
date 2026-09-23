# 智瞳交管系统 - K230视觉识别应用

基于K230豪华版的智慧交管系统视觉识别应用。

## 功能特性

- **车辆检测**: 基于YOLOv8n的实时车辆检测（car, motorcycle, bus, truck）
- **车牌识别**: 车牌检测(LPD) + 字符识别
- **语音播报**: TTS语音播报检测结果
- **数据上报**: HTTP POST上报检测数据到平台API
- **状态显示**: LCD显示设备状态和检测结果

## 目录结构

```
k230_app/
├── main.py                      # 主程序入口
├── config.py                    # 配置文件
├── detectors/
│   ├── __init__.py
│   ├── vehicle_detector.py      # 车辆检测器
│   └── plate_recognizer.py      # 车牌识别器
├── utils/
│   ├── __init__.py
│   ├── wifi.py                  # WiFi连接
│   ├── http_client.py           # HTTP客户端
│   ├── tts_speaker.py           # TTS语音
│   └── display.py               # LCD显示
├── kmodel/                      # 模型文件目录
│   ├── yolov8n_320.kmodel       # YOLOv8n目标检测
│   ├── LPD_640.kmodel           # 车牌检测
│   ├── licence_reco.kmodel      # 车牌识别
│   ├── zh_fastspeech_1_f32.kmodel # TTS编码器
│   ├── zh_fastspeech_2.kmodel   # TTS解码器
│   └── hifigan.kmodel           # TTS声码器
└── README.md
```

## 配置说明

编辑 `config.py` 修改以下配置：

```python
# 设备信息
DEVICE_ID = "K230_001"
DEVICE_NAME = "K230移动节点01"

# WiFi配置
WIFI_SSID = "你的WiFi名称"
WIFI_PASSWORD = "你的WiFi密码"

# API服务器地址
API_BASE_URL = "http://192.168.1.100:8001"
```

## 模型文件

模型文件需要从K230固件备份复制到 `/sdcard/kmodel/` 目录：

```bash
# 从固件备份复制模型
cp /path/to/固件备份/kmodel/* /sdcard/kmodel/
```

需要的模型文件：
- `yolov8n_320.kmodel` - YOLOv8n目标检测（COCO 80类）
- `LPD_640.kmodel` - 车牌检测
- `licence_reco.kmodel` - 车牌识别
- `zh_fastspeech_1_f32.kmodel` - TTS编码器
- `zh_fastspeech_2.kmodel` - TTS解码器
- `hifigan.kmodel` - TTS声码器

## 运行

```bash
# 在K230开发板上运行
python /sdcard/k230_app/main.py
```

## 数据上报

检测数据通过HTTP POST上报到平台API：

```json
POST /api/violations/upload
{
    "device_id": "K230_001",
    "device_name": "K230移动节点01",
    "timestamp": "2026-06-25T10:30:00",
    "latitude": 39.9042,
    "longitude": 116.4074,
    "detections": [
        {
            "type": "car",
            "plate": "京A12345",
            "confidence": 0.95,
            "bbox": [100, 200, 300, 400]
        }
    ],
    "image_url": "/sdcard/detections/detect_xxx.jpg"
}
```

设备心跳：

```json
POST /api/devices/heartbeat
{
    "device_id": "K230_001",
    "status": "online",
    "battery_level": 85
}
```

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/violations/upload` | POST | 上报复用数据 |
| `/api/devices/heartbeat` | POST | 设备心跳 |
| `/api/devices/register` | POST | 设备注册 |

## 开发指南

### 添加新的检测类别

在 `config.py` 中修改：

```python
VEHICLE_CLASSES = [2, 3, 5, 7]  # COCO类别ID
VEHICLE_LABELS = ["car", "motorcycle", "bus", "truck"]
```

### 调整检测灵敏度

```python
CONFIDENCE_THRESHOLD = 0.5  # 置信度阈值
DETECT_INTERVAL = 10       # 检测间隔（帧）
```

## 注意事项

1. 模型文件必须放在 `/sdcard/kmodel/` 目录
2. WiFi配置需要根据实际环境修改
3. API服务器地址需要修改为实际服务器IP
4. 首次运行需要确保设备已注册到平台