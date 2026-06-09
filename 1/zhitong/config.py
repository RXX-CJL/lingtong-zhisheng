import os
import numpy as np

class Config:
    # 项目根目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # 模型配置
    MODEL_DIR = os.path.join(BASE_DIR, 'models')
    YOLO_MODEL = 'yolov8n.pt'
    USE_TENSORRT = False
    TENSORRT_ENGINE = None
    
    # 摄像头/视频配置
    CAMERA_INDEX = 0
    VIDEO_WIDTH = 1280
    VIDEO_HEIGHT = 720
    VIDEO_FPS = 30
    
    # YOLO检测配置
    YOLO_CONF_THRESHOLD = 0.5
    YOLO_IOU_THRESHOLD = 0.45
    YOLO_CLASSES = ['person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck', 
                    'traffic light', 'stop sign']
    
    # DeepSORT配置
    MAX_DIST = 0.4
    MIN_CONFIDENCE = 0.5
    NMS_MAX_OVERLAP = 0.5
    MAX_AGE = 30
    N_INIT = 3
    NN_BUDGET = None
    
    # 违规检测配置
    CONFIDENCE_THRESHOLD_HIGH = 0.8
    CONFIDENCE_THRESHOLD_LOW = 0.5
    VIOLATION_FRAMES_THRESHOLD = 3
    
    # 速度检测配置
    SPEED_LIMIT = 60
    SPEED_TOLERANCE = 0.1
    PIXEL_TO_METER = 0.05
    
    # 车道检测配置
    LANE_DETECTION_ENABLED = True
    LANE_LINE_MIN_LENGTH = 100
    LANE_LINE_MAX_GAP = 50
    
    # 云端配置
    DASHSCOPE_API_KEY = "***REMOVED***"
    CLOUD_MODEL = "qwen3-vl-flash"
    USE_CLOUD_VALIDATION = True
    
    # 语音配置
    ENABLE_SPEECH = True
    TTS_ENGINE = 'dashscope'  # dashscope, piper, windows
    TTS_VOICE = 'zh-CN-XiaoxiaoNeural'
    TTS_SPEED = 1.0
    TTS_PITCH = 0.0
    
    # 分级警告配置
    VIOLATION_THRESHOLD_1 = 3    # 正式警告阈值
    VIOLATION_THRESHOLD_2 = 5    # 限制操作阈值
    
    # 警告级别配置
    WARNING_LEVELS = {
        1: {'name': '轻度提示', 'color': (255, 255, 0), 'volume': 0.8, 'speed': 1.0},
        2: {'name': '正式警告', 'color': (255, 165, 0), 'volume': 1.0, 'speed': 0.9},
        3: {'name': '严厉警告', 'color': (255, 0, 0), 'volume': 1.2, 'speed': 0.8}
    }
    
    # 输出配置
    OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
    EVIDENCE_DIR = os.path.join(OUTPUT_DIR, 'evidence')
    LOG_DIR = os.path.join(OUTPUT_DIR, 'logs')
    
    # 数据集配置
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    RAW_VIDEO_DIR = os.path.join(DATA_DIR, 'raw_videos')
    PROCESSED_FRAMES_DIR = os.path.join(DATA_DIR, 'processed_frames')
    METADATA_FILE = os.path.join(DATA_DIR, 'video_metadata.json')
    DATASET_YAML = os.path.join(DATA_DIR, 'dataset.yaml')
    
    # 预处理配置
    TARGET_WIDTH = 640
    TARGET_HEIGHT = 640
    FRAME_INTERVAL = 2
    MAX_FRAMES_PER_VIDEO = 100
    ENABLE_AUGMENTATION = True
    ENABLE_HISTOGRAM_EQUALIZATION = True
    ENABLE_DEHAZING = True
    
    # 违规类型定义
    VIOLATION_TYPES = [
        'red_light',
        'no_helmet', 
        'wrong_way',
        'illegal_parking',
        'lane_departure',
        'speeding'
    ]
    
    VIOLATION_TYPE_NAMES = {
        'red_light': '闯红灯',
        'no_helmet': '未戴头盔',
        'wrong_way': '逆行',
        'illegal_parking': '违停',
        'lane_departure': '压线',
        'speeding': '超速'
    }
    
    @classmethod
    def create_dirs(cls):
        for dir_path in [cls.MODEL_DIR, cls.OUTPUT_DIR, cls.EVIDENCE_DIR, cls.LOG_DIR, 
                        cls.RAW_VIDEO_DIR, cls.PROCESSED_FRAMES_DIR]:
            os.makedirs(dir_path, exist_ok=True)
