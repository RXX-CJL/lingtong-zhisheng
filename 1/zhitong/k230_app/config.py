# -*- coding: utf-8 -*-
"""
K230视觉识别应用配置文件
智瞳智慧交管系统 - K230移动节点配置
"""

class Config:
    """应用配置类"""

    # ============== 设备信息 ==============
    DEVICE_ID = "K230_001"                    # 设备唯一标识
    DEVICE_NAME = "K230移动节点01"             # 设备显示名称

    # ============== WiFi配置 ==============
    # 请根据实际WiFi修改以下配置
    WIFI_SSID = "Your_WiFi_SSID"              # WiFi名称
    WIFI_PASSWORD = "Your_WiFi_Password"      # WiFi密码
    WIFI_TIMEOUT = 15000                       # WiFi连接超时(ms)

    # ============== API服务器配置 ==============
    # 请修改为实际服务器IP地址和端口
    API_BASE_URL = "http://192.168.1.100:8001"
    API_VIOLATION_UPLOAD = "/api/violations/upload"    # 违规上报接口
    API_DEVICE_HEARTBEAT = "/api/devices/heartbeat"   # 设备心跳接口
    API_DEVICE_REGISTER = "/api/devices/register"     # 设备注册接口

    # ============== K230模型路径 ==============
    # 模型文件需放在/sdcard/kmodel/目录下
    MODEL_DIR = "/sdcard/kmodel"

    # YOLOv8n目标检测模型（COCO 80类）
    YOLOV8N_MODEL = MODEL_DIR + "/yolov8n_320.kmodel"

    # 车牌检测模型
    LPD_MODEL = MODEL_DIR + "/LPD_640.kmodel"

    # 车牌识别模型
    LICENCE_RECO_MODEL = MODEL_DIR + "/licence_reco.kmodel"

    # TTS模型
    TTS_ENCODER = MODEL_DIR + "/zh_fastspeech_1_f32.kmodel"
    TTS_DECODER = MODEL_DIR + "/zh_fastspeech_2.kmodel"
    TTS_VOCODER = MODEL_DIR + "/hifigan.kmodel"

    # ============== 检测参数 ==============
    # 车辆类别ID（COCO数据集）
    # car=2, motorcycle=3, bus=5, truck=7
    VEHICLE_CLASSES = [2, 3, 5, 7]
    VEHICLE_LABELS = ["car", "motorcycle", "bus", "truck"]

    # 置信度阈值
    CONFIDENCE_THRESHOLD = 0.5

    # 检测间隔（每多少帧检测一次，节省算力）
    DETECT_INTERVAL = 10

    # NMS阈值
    NMS_THRESHOLD = 0.45

    # 最大检测框数量
    MAX_BOXES_NUM = 50

    # ============== 图像参数 ==============
    # 摄像头分辨率
    SENSOR_WIDTH = 640
    SENSOR_HEIGHT = 480

    # 模型输入尺寸
    MODEL_INPUT_SIZE = [320, 320]

    # 显示分辨率
    DISPLAY_SIZE = [640, 480]

    # ============== 心跳配置 ==============
    HEARTBEAT_INTERVAL = 60  # 心跳间隔(秒)

    # ============== 其他配置 ==============
    # 是否启用语音播报
    TTS_ENABLED = True

    # 是否保存检测图片
    SAVE_DETECTION_IMAGES = True

    # 检测图片保存路径
    IMAGE_SAVE_PATH = "/sdcard/detections/"

    # Debug模式
    DEBUG_MODE = 0