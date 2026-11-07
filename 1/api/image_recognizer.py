# -*- coding: utf-8 -*-
"""
图像识别模块 - 集成 YOLOv8 和 豆包大模型
支持多模型串联检测
"""
import os
import base64
import json
import cv2
import numpy as np
from datetime import datetime

from config import Config

# 尝试导入 YOLO
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# 尝试导入 dashscope
try:
    import dashscope
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

yolo_models = {}
paddleocr_detector = None
# ★2026-10-06 由 DSH 新增：多模型检测**实际生效**的序列（默认 5 个，
# 可被环境变量 YOLO_MODEL_SEQUENCE 裁剪）。multi_model_detect 每次调用刷新它，
# /api/realtime/status 把它暴露出去 —— 让"到底跑了哪几个模型"可观测，
# 不再需要靠翻日志猜（`cmd /k` 新窗口的 stdout 并不落在日志文件里）。
ACTIVE_MODEL_SEQUENCE = []

# DashScope API Key（通过 _get_dashscope_key() 动态获取）
DASHSCOPE_API_KEY = ""

CLASS_CN_MAP = {
    'person': '行人',
    'bicycle': '自行车',
    'car': '轿车',
    'motorcycle': '摩托车',
    'airplane': '飞机',
    'bus': '公交车',
    'train': '火车',
    'truck': '卡车',
    'boat': '船',
    'traffic light': '红绿灯',
    'fire hydrant': '消防栓',
    'stop sign': '停止标志',
    'parking meter': '停车计时器',
    'bench': '长椅',
    'bird': '鸟',
    'cat': '猫',
    'dog': '狗',
    'horse': '马',
    'sheep': '羊',
    'cow': '牛',
    'elephant': '大象',
    'bear': '熊',
    'zebra': '斑马',
    'giraffe': '长颈鹿',
    'backpack': '背包',
    'umbrella': '雨伞',
    'handbag': '手提包',
    'tie': '领带',
    'suitcase': '行李箱',
    'frisbee': '飞盘',
    'skis': '滑雪板',
    'snowboard': '滑雪板',
    'sports ball': '运动球',
    'kite': '风筝',
    'baseball bat': '棒球棒',
    'baseball glove': '棒球手套',
    'skateboard': '滑板',
    'surfboard': '冲浪板',
    'tennis racket': '网球拍',
    'bottle': '瓶子',
    'wine glass': '酒杯',
    'cup': '杯子',
    'fork': '叉子',
    'knife': '刀',
    'spoon': '勺子',
    'bowl': '碗',
    'banana': '香蕉',
    'apple': '苹果',
    'sandwich': '三明治',
    'orange': '橙子',
    'broccoli': '西兰花',
    'carrot': '胡萝卜',
    'hot dog': '热狗',
    'pizza': '披萨',
    'donut': '甜甜圈',
    'cake': '蛋糕',
    'chair': '椅子',
    'couch': '沙发',
    'potted plant': '盆栽',
    'bed': '床',
    'dining table': '餐桌',
    'toilet': '厕所',
    'tv': '电视',
    'laptop': '笔记本电脑',
    'mouse': '鼠标',
    'remote': '遥控器',
    'keyboard': '键盘',
    'cell phone': '手机',
    'microwave': '微波炉',
    'oven': '烤箱',
    'toaster': '烤面包机',
    'sink': '水槽',
    'refrigerator': '冰箱',
    'book': '书',
    'clock': '时钟',
    'vase': '花瓶',
    'scissors': '剪刀',
    'teddy bear': '泰迪熊',
    'hair drier': '吹风机',
    'toothbrush': '牙刷',
    'helmet': '头盔',
    'rider': '骑手',
    'red_light': '红灯',
    'yellow_light': '黄灯',
    'green_light': '绿灯',
    'no_helmet': '未戴头盔',
    'head': '头部',
    'hard_hat': '安全帽',
    'safety_helmet': '安全头盔',
    'lane_line': '车道线',
    'road_line': '道路标线',
    'white_line': '白色标线',
    'yellow_line': '黄色标线',
    'license_plate': '车牌',
    'plate': '车牌',
    'car_plate': '车牌',
    'with_helmet': '佩戴头盔',
    'without_helmet': '未戴头盔',
    'With Helmet': '佩戴头盔',
    'Without Helmet': '未戴头盔',
    'Vehicle': '车辆',
    'red': '红灯',
    'yellow': '黄灯',
    'green': '绿灯',
    'red_light': '红灯',
    'yellow_light': '黄灯',
    'green_light': '绿灯',
    'traffic_light_red': '红灯',
    'traffic_light_yellow': '黄灯',
    'traffic_light_green': '绿灯'
}

MODEL_CONFIG = {
    'yolov8n': {
        'name': '通用目标检测',
        'model_path': None,
        'description': 'YOLOv8 Nano - 80类通用目标检测',
        'classes': ['person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck', 'traffic light']
    },
    'yolov8s': {
        'name': '中等规模检测',
        'model_path': None,
        'description': 'YOLOv8 Small - 80类通用目标检测',
        'classes': ['person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck', 'traffic light']
    },
    'vehicle': {
        'name': '高精度车辆检测',
        'model_path': None,
        'description': 'YOLOv8s COCO预训练（支持car/motorcycle/truck/bus分类）',
        'classes': ['car', 'motorcycle', 'truck', 'bus']
    },
    'helmet': {
        'name': '头盔检测',
        'model_path': None,
        'description': 'GitHub下载的头盔佩戴检测模型（YOLOv8训练）',
        'classes': ['with_helmet', 'without_helmet']
    },
    'traffic_light': {
        'name': '红绿灯检测',
        'model_path': None,
        'description': 'YOLOv8s检测红绿灯位置 + HSV颜色识别（red/yellow/green）',
        'classes': ['red', 'yellow', 'green']
    },
    'lane': {
        'name': '车道线检测',
        'model_path': None,
        'description': '车道线检测模型',
        'classes': ['lane_line', 'road_line', 'white_line', 'yellow_line']
    },
    'license_plate': {
        'name': '车牌检测',
        'model_path': None,
        'description': '车牌检测模型',
        'classes': ['license_plate', 'plate', 'car_plate']
    }
}

def _get_dashscope_key():
    """从 config_manager 优先获取 API Key，读不到再用环境变量兜底"""
    try:
        from config_manager import load_config
        cfg = load_config()
        key = cfg.get('dashscope', {}).get('api_key', '')
        if key:
            return key
    except:
        pass
    env_key = os.environ.get('DASHSCOPE_API_KEY', '')
    if env_key:
        return env_key
    return ""  # 最后兜底返回空，由调用方处理未配置情况（Key 请通过环境变量或 config_runtime.json 配置）

def find_model_path(model_key):
    """查找模型文件路径"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    model_filename_map = {
        'yolov8n': 'yolov8n.pt',
        'yolov8s': 'yolov8s.pt',
        'vehicle': 'yolov8s.pt',
        'helmet': 'helmet_best.pt',
        'traffic_light': 'yolov8s.pt',
        'lane': 'lane.pt',
        'license_plate': 'license_plate.pt'
    }
    
    expected_filename = model_filename_map.get(model_key, f"{model_key}.pt")
    
    candidates = [
        os.path.join(base_dir, '..', 'zhitong', 'training', 'models', expected_filename),
        os.path.join(base_dir, '..', 'zhitong', 'training', 'models', f"{model_key}_best.pt"),
        os.path.join(base_dir, '..', 'models', expected_filename),
        os.path.join(base_dir, expected_filename),
        os.path.join(base_dir, '..', 'data', 'models', expected_filename),
    ]
    
    if model_key == 'helmet':
        candidates.insert(0, os.path.join(base_dir, '..', 'zhitong', 'training', 'models', 'helmet_best.pt'))
    
    for p in candidates:
        norm_p = os.path.normpath(p)
        if os.path.exists(norm_p):
            return norm_p
    
    return None


def init_yolo_model(model_key):
    """初始化指定的 YOLO 模型"""
    global yolo_models
    if not YOLO_AVAILABLE:
        return False
    
    if model_key in yolo_models:
        return True
    
    model_path = find_model_path(model_key)
    if model_path:
        try:
            yolo_models[model_key] = YOLO(model_path)
            try:
                import torch
                if torch.cuda.is_available():
                    yolo_models[model_key] = yolo_models[model_key].to('cuda')
                    print(f"YOLO model loaded and moved to GPU: {model_key} -> {model_path}")
                else:
                    print(f"YOLO model loaded (CPU): {model_key} -> {model_path}")
            except:
                print(f"YOLO model loaded: {model_key} -> {model_path}")
            MODEL_CONFIG[model_key]['model_path'] = model_path
            return True
        except Exception as e:
            print(f"YOLO model load failed ({model_key}): {e}")
    
    fallback_models = {
        'vehicle': 'yolov8s',
        'helmet': 'yolov8s',
        'traffic_light': 'yolov8s',
        'lane': 'yolov8s',
        'license_plate': 'yolov8s'
    }
    
    if model_key in fallback_models:
        fallback_key = fallback_models[model_key]
        if fallback_key not in yolo_models:
            if not init_yolo_model(fallback_key):
                return False
        
        yolo_models[model_key] = yolo_models[fallback_key]
        print(f"Using fallback model {fallback_key} for {model_key}")
        MODEL_CONFIG[model_key]['model_path'] = MODEL_CONFIG[fallback_key]['model_path']
        return True
    
    if model_key == 'yolov8n':
        try:
            yolo_models[model_key] = YOLO('yolov8n.pt')
            try:
                import torch
                if torch.cuda.is_available():
                    yolo_models[model_key] = yolo_models[model_key].to('cuda')
                    print("YOLOv8n loaded from ultralytics (GPU)")
                else:
                    print("YOLOv8n loaded from ultralytics (CPU)")
            except:
                print("YOLOv8n loaded from ultralytics")
            return True
        except Exception as e:
            print(f"YOLOv8n load failed: {e}")
            return False
    
    return False


def init_all_models():
    """初始化所有配置的模型"""
    for model_key in MODEL_CONFIG:
        init_yolo_model(model_key)
    
    print(f"已初始化模型: {list(yolo_models.keys())}")


def switch_model(model_key):
    """
    热切换检测模型
    
    参数:
        model_key: 模型名称 (yolov8n, yolov8s, helmet)
    
    返回:
        {'success': bool, 'message': str, 'current_model': str}
    """
    if model_key not in MODEL_CONFIG:
        return {
            'success': False,
            'message': f'未知模型: {model_key}，可用模型: {list(MODEL_CONFIG.keys())}',
            'current_model': None
        }
    
    if not init_yolo_model(model_key):
        return {
            'success': False,
            'message': f'模型加载失败: {model_key}',
            'current_model': list(yolo_models.keys())[0] if yolo_models else None
        }
    
    return {
        'success': True,
        'message': f'模型切换成功: {model_key}',
        'current_model': model_key,
        'available_models': list(yolo_models.keys())
    }


def unload_model(model_key):
    """
    卸载指定模型（释放内存）
    
    参数:
        model_key: 模型名称
    
    返回:
        {'success': bool, 'message': str}
    """
    global yolo_models
    if model_key in yolo_models:
        del yolo_models[model_key]
        return {
            'success': True,
            'message': f'模型已卸载: {model_key}',
            'available_models': list(yolo_models.keys())
        }
    return {
        'success': False,
        'message': f'模型不存在: {model_key}',
        'available_models': list(yolo_models.keys())
    }


def get_model_status():
    """
    获取所有模型状态
    
    返回:
        {'models': dict, 'count': int}
    """
    status = {}
    for model_key, config in MODEL_CONFIG.items():
        loaded = model_key in yolo_models
        status[model_key] = {
            'name': config['name'],
            'loaded': loaded,
            'description': config['description'],
            'classes': config['classes']
        }
    return {
        'models': status,
        'count': len(yolo_models),
        'total_configured': len(MODEL_CONFIG)
    }


# 性能统计
performance_stats = {
    'total_detections': 0,
    'total_duration_ms': 0,
    'min_duration_ms': float('inf'),
    'max_duration_ms': 0,
    'detections_by_model': {},
    'confidence_distribution': {
        '0-0.2': 0,
        '0.2-0.4': 0,
        '0.4-0.6': 0,
        '0.6-0.8': 0,
        '0.8-1.0': 0
    }
}


def update_performance_stats(model_key, duration_ms, detections):
    """更新性能统计"""
    global performance_stats
    
    performance_stats['total_detections'] += len(detections)
    performance_stats['total_duration_ms'] += duration_ms
    
    if duration_ms < performance_stats['min_duration_ms']:
        performance_stats['min_duration_ms'] = duration_ms
    if duration_ms > performance_stats['max_duration_ms']:
        performance_stats['max_duration_ms'] = duration_ms
    
    if model_key not in performance_stats['detections_by_model']:
        performance_stats['detections_by_model'][model_key] = {
            'count': 0,
            'total_duration_ms': 0,
            'avg_duration_ms': 0
        }
    perf_model = performance_stats['detections_by_model'][model_key]
    perf_model['count'] += 1
    perf_model['total_duration_ms'] += duration_ms
    perf_model['avg_duration_ms'] = perf_model['total_duration_ms'] / perf_model['count']
    
    for det in detections:
        conf = det.get('confidence', 0.0)
        if conf < 0.2:
            performance_stats['confidence_distribution']['0-0.2'] += 1
        elif conf < 0.4:
            performance_stats['confidence_distribution']['0.2-0.4'] += 1
        elif conf < 0.6:
            performance_stats['confidence_distribution']['0.4-0.6'] += 1
        elif conf < 0.8:
            performance_stats['confidence_distribution']['0.6-0.8'] += 1
        else:
            performance_stats['confidence_distribution']['0.8-1.0'] += 1


def get_performance_stats():
    """获取性能统计"""
    global performance_stats
    avg_duration = performance_stats['total_duration_ms'] / performance_stats['total_detections'] if performance_stats['total_detections'] > 0 else 0
    
    return {
        'total_detections': performance_stats['total_detections'],
        'total_duration_ms': performance_stats['total_duration_ms'],
        'avg_duration_ms': round(avg_duration, 2),
        'min_duration_ms': performance_stats['min_duration_ms'] if performance_stats['min_duration_ms'] != float('inf') else 0,
        'max_duration_ms': performance_stats['max_duration_ms'],
        'detections_by_model': performance_stats['detections_by_model'],
        'confidence_distribution': performance_stats['confidence_distribution']
    }


def reset_performance_stats():
    """重置性能统计"""
    global performance_stats
    performance_stats = {
        'total_detections': 0,
        'total_duration_ms': 0,
        'min_duration_ms': float('inf'),
        'max_duration_ms': 0,
        'detections_by_model': {},
        'confidence_distribution': {
            '0-0.2': 0,
            '0.2-0.4': 0,
            '0.4-0.6': 0,
            '0.6-0.8': 0,
            '0.8-1.0': 0
        }
    }
    return {'success': True, 'message': '性能统计已重置'}


def batch_detect(image_inputs, model_keys=None, conf_threshold=0.25):
    """
    批量检测图片
    
    参数:
        image_inputs: 图片路径或 base64 字符串列表
        model_keys: 模型列表
        conf_threshold: 置信度阈值
    
    返回:
        {'results': list, 'summary': dict}
    """
    if model_keys is None:
        model_keys = ['yolov8n']
    
    results = []
    success_count = 0
    failed_count = 0
    
    for idx, image_input in enumerate(image_inputs):
        try:
            result = detect_with_multiple_models(image_input, model_keys, conf_threshold)
            result['index'] = idx
            results.append(result)
            if result['success']:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            results.append({
                'index': idx,
                'success': False,
                'message': f'检测失败: {str(e)}',
                'detections': [],
                'merged_detections': []
            })
            failed_count += 1
    
    return {
        'results': results,
        'summary': {
            'total': len(image_inputs),
            'success': success_count,
            'failed': failed_count,
            'model_keys': model_keys
        }
    }


def get_class_name_cn(class_name):
    """获取类别中文名称"""
    return CLASS_CN_MAP.get(class_name, class_name)

# 违规类型中文映射
VIOLATION_TYPE_CN = {
    'red_light': '闯红灯',
    'no_helmet': '未戴头盔',
    'wrong_way': '逆行',
    'illegal_parking': '违规停车',
    'lane_departure': '压线行驶',
    'speeding': '超速'
}

# YOLO 类别中与交通相关的类别
TRAFFIC_CLASSES = {
    0: 'person',
    1: 'bicycle',
    2: 'car',
    3: 'motorcycle',
    5: 'bus',
    7: 'truck',
    9: 'traffic light',
    11: 'stop sign'
}

# ★★2026-10-09 由 DSH 新增：**交通检测类白名单**（唯一权威版本）
#
# 起因（用户原话）："画面中甚至还识别了路旁的盆栽"。
# 根因（设计单 §12.6 问题 2）：COCO 有 80 类，`CLASS_CN_MAP` 里有 107 个类名，
#   其中 **83 类与交通无关**（potted plant / fire hydrant / sports ball / chair /
#   bench / dog / cake …），而渲染器主循环**只跳过红绿灯、其余照画** ->
#   只要上游 YOLO 输出它们，就会被画到画面上。
# 修法：**按白名单裁**，而不是"排掉盆栽"—— 只排一个等于掩耳盗铃，
#   下一个视频会冒出别的垃圾类。裁点选在 process_frame 的检测出口，
#   这样规则引擎/行为引擎/跟踪器/渲染器**同时**都不再受垃圾框干扰
#   （历史证据：`license_plate` 模型文件不存在 -> 静默回退 COCO yolov8s ->
#     每帧产出 12 个垃圾框，白花 ~30ms，见 _PROJECT_MAP.md T73）。
#
# ⚠ 维护须知：本集合是**判定链路的输入契约**。规则引擎里出现新的类名分组
#   （violation_rules.py: VEHICLE_CLASSES / HELMET_CLASSES / PERSON_CLASSES /
#    TRAFFIC_SIGNAL_CLASSES / *_LIGHT_CLASSES / LANE_LINE_CLASSES /
#    NO_HELMET_CLASSES / STOP_SIGN_CLASSES …）时，这里必须同步补上，
#   否则那条规则会被**静默废掉**（本项目已有同类教训：判色白名单漏裸色名
#   -> 红绿灯框一个都画不出来，实测 0/520 帧）。
# 观测：/status 的 class_filter_stats 会报告实际挡掉了什么，先看它再改这里。
TRAFFIC_CLASS_WHITELIST = {
    # 车辆 / 两轮 / 行人（violation_rules.VEHICLE_CLASSES / PERSON_CLASSES）
    'car', 'motorcycle', 'truck', 'bus', 'bicycle',
    'person', 'rider', 'motorcyclist', 'cyclist', 'pedestrian',
    # 信号灯：COCO 原生是带空格的 'traffic light'；
    # 裸色名来自 MODEL_CONFIG['traffic_light']（其 class_name 直接被换成颜色）
    'traffic light', 'traffic_light',
    'red_light', 'green_light', 'yellow_light',
    'red', 'green', 'yellow',
    'traffic_light_red', 'traffic_light_green', 'traffic_light_yellow',
    # 交通标志
    'stop sign', 'stop_sign', 'yield', 'yield_sign', 'give_way',
    # 头盔（MODEL_CONFIG['helmet'] 实际输出 with_helmet / without_helmet）
    'helmet', 'with_helmet', 'without_helmet', 'no_helmet', 'no-helmet',
    'head', 'hard_hat', 'safety_helmet',
    # 车道线（MODEL_CONFIG['lane']）
    'lane_line', 'road_line', 'white_line', 'yellow_line',
    # 车牌（MODEL_CONFIG['license_plate']）
    'license_plate', 'plate', 'car_plate',
}

def _process_image_input(image_input):
    """处理图片输入，返回 numpy 数组"""
    if image_input.startswith('data:image') or 'base64,' in image_input:
        if 'base64,' in image_input:
            base64_data = image_input.split('base64,')[1]
        else:
            base64_data = image_input
        
        image_data = base64.b64decode(base64_data)
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    elif os.path.exists(image_input):
        img = cv2.imread(image_input)
    else:
        return None
    
    return img


def detect_with_yolo(image_input, model_key='yolov8n', conf_threshold=0.25):
    """
    使用指定的 YOLO 模型检测图片中的对象
    
    参数:
        image_input: 可以是图片路径(str)或 base64 字符串
        model_key: 模型名称 (yolov8n, yolov8s, helmet)
        conf_threshold: 置信度阈值
    
    返回:
        {
            'success': bool,
            'detections': list of {class_name, class_name_cn, confidence, bbox},
            'message': str,
            'model_key': str
        }
    """
    global yolo_models
    
    if model_key not in yolo_models:
        if not init_yolo_model(model_key):
            return {
                'success': False,
                'detections': [],
                'message': f'Model {model_key} not available',
                'model_key': model_key
            }
    
    model = yolo_models[model_key]
    
    try:
        img = _process_image_input(image_input)
        if img is None:
            return {
                'success': False,
                'detections': [],
                'message': 'Invalid image input',
                'model_key': model_key
            }
        
        # 推理分辨率（2026-10-03 由 DSH 修复）
        # 原实现未指定 imgsz，Ultralytics 默认 640 -> 960x432 的输入被缩到 288x640，
        # 导致远处小目标（红绿灯、车牌、头盔）直接消失：
        #   实测同一模型，traffic light 检出数 imgsz=640 -> 1~3，imgsz=1920 -> 2~5，
        #   且总检出数 20 -> 31（帧0）。代价是推理耗时 6ms -> 35ms（仍远快于帧间隔）。
        # 可用环境变量 YOLO_IMGSZ 覆盖（如低配机器可设 640）。
        _imgsz = int(os.environ.get('YOLO_IMGSZ', '1280'))
        results = model(img, conf=conf_threshold, imgsz=_imgsz)
        
        detections = []
        class_names = model.names if hasattr(model, 'names') else {}
        
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                class_name = class_names.get(cls_id, str(cls_id)) if class_names else str(cls_id)
                class_name_cn = get_class_name_cn(class_name)
                confidence = float(box.conf[0])
                bbox = box.xyxy[0].tolist()
                
                if model_key == 'traffic_light' and class_name == 'traffic light':
                    color, color_conf = _detect_traffic_light_color(img, bbox)
                    if color:
                        class_name = color
                        class_name_cn = get_class_name_cn(color)
                        confidence = min(1.0, confidence * 0.7 + color_conf * 0.3)
                
                if model_key == 'vehicle' and class_name not in ['car', 'motorcycle', 'truck', 'bus']:
                    continue
                
                detections.append({
                    'class_name': class_name,
                    'class_name_cn': class_name_cn,
                    'confidence': confidence,
                    'bbox': bbox
                })
        
        return {
            'success': True,
            'detections': detections,
            'message': f'Detected {len(detections)} objects with {model_key}',
            'model_key': model_key
        }
    
    except Exception as e:
        return {
            'success': False,
            'detections': [],
            'message': f'YOLO detection failed: {str(e)}',
            'model_key': model_key
        }


def _detect_traffic_light_color(img, bbox):
    """
    使用HSV颜色空间识别红绿灯颜色
    
    参数:
        img: cv2图像（BGR格式）
        bbox: [x1, y1, x2, y2] 边界框
    
    返回:
        ('red'/'yellow'/'green', confidence) 或 (None, 0)
    """
    x1, y1, x2, y2 = map(int, bbox)
    height, width = img.shape[:2]
    
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(width, x2)
    y2 = min(height, y2)
    
    if x2 - x1 < 10 or y2 - y1 < 10:
        return None, 0
    
    roi = img[y1:y2, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    
    red_lower1 = np.array([0, 100, 100])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([160, 100, 100])
    red_upper2 = np.array([180, 255, 255])
    
    yellow_lower = np.array([15, 100, 100])
    yellow_upper = np.array([40, 255, 255])
    
    green_lower = np.array([40, 50, 50])
    green_upper = np.array([90, 255, 255])
    
    mask_red1 = cv2.inRange(hsv, red_lower1, red_upper1)
    mask_red2 = cv2.inRange(hsv, red_lower2, red_upper2)
    mask_red = mask_red1 + mask_red2
    
    mask_yellow = cv2.inRange(hsv, yellow_lower, yellow_upper)
    mask_green = cv2.inRange(hsv, green_lower, green_upper)
    
    red_pixels = cv2.countNonZero(mask_red)
    yellow_pixels = cv2.countNonZero(mask_yellow)
    green_pixels = cv2.countNonZero(mask_green)
    
    total_pixels = roi.shape[0] * roi.shape[1]
    
    if total_pixels == 0:
        return None, 0
    
    red_ratio = red_pixels / total_pixels
    yellow_ratio = yellow_pixels / total_pixels
    green_ratio = green_pixels / total_pixels
    
    max_ratio = max(red_ratio, yellow_ratio, green_ratio)
    
    if max_ratio < 0.05:
        return None, 0
    
    if red_ratio == max_ratio:
        return 'red', red_ratio
    elif yellow_ratio == max_ratio:
        return 'yellow', yellow_ratio
    else:
        return 'green', green_ratio


def detect_with_multiple_models(image_input, model_keys=None, conf_threshold=0.25):
    """
    使用多个模型串联检测
    
    参数:
        image_input: 图片路径或 base64 字符串
        model_keys: 模型列表，如 ['yolov8n', 'helmet']
        conf_threshold: 置信度阈值
    
    返回:
        {
            'success': bool,
            'all_detections': dict {model_key: detections},
            'merged_detections': list of unique detections,
            'message': str
        }
    """
    if model_keys is None:
        model_keys = ['yolov8n', 'helmet']
    
    all_detections = {}
    merged_detections = []
    detection_set = set()
    
    for model_key in model_keys:
        result = detect_with_yolo(image_input, model_key, conf_threshold)
        all_detections[model_key] = result
        
        if result['success']:
            for det in result['detections']:
                key = (det['class_name'], tuple(det['bbox']))
                if key not in detection_set:
                    detection_set.add(key)
                    merged_detections.append(det)
    
    success = any(v['success'] for v in all_detections.values())
    
    return {
        'success': success,
        'all_detections': all_detections,
        'merged_detections': merged_detections,
        'message': f'Processed {len(model_keys)} models, merged {len(merged_detections)} unique detections'
    }


def multi_model_detect(image_input, conf_threshold=0.25):
    """
    多模型串联检测 - 完整的交通违规检测流程
    
    检测流程:
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
    
    参数:
        image_input: 图片路径或 base64 字符串
        conf_threshold: 置信度阈值
    
    返回:
        {
            'success': bool,
            'vehicle_detection': dict,
            'traffic_light_detection': dict,
            'helmet_detection': dict,
            'lane_detection': dict,
            'all_detections': list,
            'violations': list,
            'license_plate': dict,
            'message': str
        }
    """
    import time
    
    start_time = time.time()
    
    detection_result = {
        'success': False,
        'vehicle_detection': {},
        'traffic_light_detection': {},
        'helmet_detection': {},
        'lane_detection': {},
        'all_detections': [],
        'violations': [],
        'license_plate': {},
        'message': '',
        'duration_ms': 0
    }
    
    all_detections = []
    detection_set = set()
    
    # ★★2026-10-06 由 DSH 改为**可配置**（环境变量 YOLO_MODEL_SEQUENCE）。
    # 起因（实测数据）：用户反馈"识别框帧率太低、跟不上车"。定位后：
    #   · 每处理 1 帧要串行跑这 5 个模型，**稳态 139ms/帧**（GPU 只占 393MB/8.5GB）；
    #   · 但端到端真实吞吐只有 ~3 fps（338ms/帧）-> 提 FRAME_RATE 也上不去；
    #   · 其中 `license_plate` **模型文件根本不存在**，回退成 COCO yolov8s，
    #     检出的却是"消防栓/盆栽/运动球"这类无关目标（实测 12 个），
    #     既白花 ~30ms/帧，又把这些垃圾塞进 all_detections 污染去重与规则判定。
    # 所以按场景裁剪模型序列是**正确且必要**的优化，而不是偷工减料：
    #   闯红灯/测速场景实际只需要 vehicle + traffic_light（+ 需要时 helmet）。
    # 用法（不设则保持原样，向后兼容）：
    #   YOLO_MODEL_SEQUENCE=vehicle,traffic_light,helmet
    _DEFAULT_SEQ = [
        ('vehicle', '高精度车辆检测'),
        ('traffic_light', '红绿灯检测'),
        ('helmet', '头盔检测'),
        ('lane', '车道线检测'),
        ('license_plate', '车牌检测'),
    ]
    _want = os.environ.get('YOLO_MODEL_SEQUENCE', '').strip()
    if _want:
        _names = {'vehicle': '高精度车辆检测', 'traffic_light': '红绿灯检测',
                  'helmet': '头盔检测', 'lane': '车道线检测',
                  'license_plate': '车牌检测'}
        picked = [(k.strip(), _names.get(k.strip(), k.strip()))
                  for k in _want.split(',') if k.strip() in _names]
        model_sequence = picked or _DEFAULT_SEQ
        if picked and not getattr(multi_model_detect, '_seq_logged', False):
            multi_model_detect._seq_logged = True
            print(f'[multi_model_detect] 模型序列由 YOLO_MODEL_SEQUENCE 裁剪为: '
                  f'{[k for k, _ in picked]}（默认 5 个）')
    else:
        model_sequence = _DEFAULT_SEQ

    # ★2026-10-06 由 DSH 新增：把**实际生效的序列**记为模块级状态，
    # 供 /api/realtime/status 暴露（配置必须可观测，不能靠猜日志）。
    # 起因：核对"helmet/lane 到底在不在跑"时只能翻日志，而 `cmd /k` 新窗口的
    # stdout 不落在日志文件里 -> 无法判定运行中实例的真实配置。
    # （本项目历史上已有同类教训：U1/G3"外部无法判定实际加载哪版模型"。）
    try:
        import image_recognizer as _self_mod
        _self_mod.ACTIVE_MODEL_SEQUENCE = [k for k, _ in model_sequence]
    except Exception:
        pass

    for model_key, model_name in model_sequence:
        result = detect_with_yolo(image_input, model_key, conf_threshold)
        detection_result[f'{model_key}_detection'] = result
        
        if result['success']:
            for det in result['detections']:
                det['source_model'] = model_key
                det['source_model_name'] = MODEL_CONFIG.get(model_key, {}).get('name', model_key)
                key = (det['class_name'], tuple(det['bbox']))
                if key not in detection_set:
                    detection_set.add(key)
                    all_detections.append(det)
    
    detection_result['all_detections'] = all_detections
    
    try:
        from violation_rules import check_violations
        violation_result = check_violations(all_detections)
        detection_result['violations'] = violation_result.get('violations', [])
    except ImportError:
        detection_result['violations'] = []
    
    duration_ms = int((time.time() - start_time) * 1000)
    detection_result['duration_ms'] = duration_ms
    detection_result['success'] = len(all_detections) > 0
    detection_result['message'] = f'多模型串联检测完成，共检测到 {len(all_detections)} 个目标，耗时 {duration_ms}ms'
    
    return detection_result


def _image_input_to_cv2(image_input):
    """将图片输入转换为cv2格式"""
    if isinstance(image_input, str):
        if image_input.startswith('data:image'):
            image_input = image_input.split(',')[1]
        if image_input.startswith('/9j/') or image_input.startswith('iVBOR'):
            import base64
            img_data = base64.b64decode(image_input)
            np_arr = np.frombuffer(img_data, np.uint8)
            return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return cv2.imread(image_input)
    elif isinstance(image_input, np.ndarray):
        return image_input
    return None

def detect_license_plate(image_input, conf_threshold=0.25):
    """
    检测并识别车牌（使用YOLO+PaddleOCR）
    
    参数:
        image_input: 图片路径或 base64 字符串
        conf_threshold: 置信度阈值
    
    返回:
        {'plate_number': str, 'confidence': float, 'bbox': list, 'success': bool}
    """
    global paddleocr_detector
    
    result = detect_with_yolo(image_input, 'license_plate', conf_threshold)
    
    if not result['success'] or not result['detections']:
        result_yolov8 = detect_with_yolo(image_input, 'yolov8s', conf_threshold)
        if result_yolov8['success']:
            plate_dets = [d for d in result_yolov8['detections'] if d['class_name'] in ['license_plate', 'plate']]
            if plate_dets:
                best_plate = max(plate_dets, key=lambda x: x['confidence'])
                plate_number, ocr_conf = _ocr_plate(image_input, best_plate['bbox'])
                return {
                    'plate_number': plate_number if plate_number else '未知车牌',
                    'confidence': best_plate['confidence'] * ocr_conf,
                    'bbox': best_plate['bbox'],
                    'success': True,
                    'message': '使用通用模型检测到疑似车牌区域'
                }
        return {
            'plate_number': '',
            'confidence': 0.0,
            'bbox': [],
            'success': False,
            'message': '未检测到车牌'
        }
    
    best_plate = max(result['detections'], key=lambda x: x['confidence'])
    plate_number, ocr_conf = _ocr_plate(image_input, best_plate['bbox'])
    
    return {
        'plate_number': plate_number if plate_number else '未知车牌',
        'confidence': best_plate['confidence'] * ocr_conf,
        'bbox': best_plate['bbox'],
        'success': True,
        'message': '车牌检测成功'
    }

def _ocr_plate(image_input, bbox):
    """对车牌区域进行OCR识别"""
    try:
        import paddleocr
        global paddleocr_detector
        
        if paddleocr_detector is None:
            paddleocr_detector = paddleocr.PaddleOCR(
                use_angle_cls=True,
                lang='ch',
                show_log=False,
                use_gpu=True
            )
        
        img = _image_input_to_cv2(image_input)
        if img is None:
            return '', 0.5
        
        x1, y1, x2, y2 = bbox
        height, width = img.shape[:2]
        
        x1 = max(0, int(x1 * width))
        y1 = max(0, int(y1 * height))
        x2 = min(width, int(x2 * width))
        y2 = min(height, int(y2 * height))
        
        if x2 - x1 < 20 or y2 - y1 < 10:
            return '', 0.5
        
        plate_img = img[y1:y2, x1:x2]
        
        result = paddleocr_detector.ocr(plate_img, cls=True)
        
        if result and len(result) > 0 and len(result[0]) > 0:
            texts = []
            total_conf = 0.0
            count = 0
            
            for line in result[0]:
                if len(line) >= 2:
                    text = line[1][0]
                    conf = line[1][1]
                    if text and conf > 0.5:
                        texts.append(text)
                        total_conf += conf
                        count += 1
            
            if texts:
                plate_number = ''.join(texts)
                avg_conf = total_conf / count if count > 0 else 0.5
                plate_number = plate_number.replace(' ', '').replace('-', '')
                return plate_number, avg_conf
        
        return '', 0.5
    
    except Exception as e:
        print(f"OCR识别失败: {e}")
        return '', 0.5

def analyze_with_doubao(image_input, violation_type, context_prompt=""):
    """
    使用豆包大模型（DashScope）进行视觉分析
    
    参数:
        image_input: 图片路径或 base64 字符串
        violation_type: 违规类型（英文）
    
    返回:
        {
            'success': bool,
            'result_text': str,
            'is_violation_confirmed': bool,
            'confidence_adjusted': float,
            'message': str,
            'prompt': str  # 新增：发送给豆包的完整 prompt
        }
    """
    if not DASHSCOPE_AVAILABLE:
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'message': 'DashScope SDK not installed',
            'prompt': ''
        }
    
    try:
        # 动态获取最新的 API Key
        global DASHSCOPE_API_KEY
        DASHSCOPE_API_KEY = _get_dashscope_key()
        
        # 设置 API Key
        dashscope.api_key = DASHSCOPE_API_KEY

        # ---- 图片输入归一化（2026-10-02 由 DSH 补充）--------------------
        # 原实现只处理 3 种输入：data: URI / 文件路径 / base64 字符串，
        # 一旦传入 numpy 数组（BGR）或 PIL.Image 就直接崩在
        #   image_input.startswith(...)  ->  AttributeError:
        #   'numpy.ndarray' object has no attribute 'startswith'
        # 该异常被上层 try/except 吞掉，表现为"豆包（主视觉分析）永远失败"，
        # 进而使事件级多模型仲裁退化为单模型审核（事件被大量误驳回）。
        # 这里统一转换为 base64 字符串，兼容所有调用方的传参习惯。
        try:
            if isinstance(image_input, np.ndarray):
                _ok, _buf = cv2.imencode('.jpg', image_input,
                                         [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not _ok:
                    return {
                        'success': False, 'result_text': '',
                        'is_violation_confirmed': False, 'confidence_adjusted': 0.0,
                        'message': 'numpy 图像编码失败', 'prompt': ''
                    }
                image_input = base64.b64encode(_buf.tobytes()).decode('utf-8')
            elif type(image_input).__name__ == 'Image':
                import io as _io
                _b = _io.BytesIO()
                image_input.convert('RGB').save(_b, format='JPEG', quality=85)
                image_input = base64.b64encode(_b.getvalue()).decode('utf-8')
            elif isinstance(image_input, (bytes, bytearray)):
                image_input = base64.b64encode(bytes(image_input)).decode('utf-8')
        except Exception as _e:
            return {
                'success': False, 'result_text': '',
                'is_violation_confirmed': False, 'confidence_adjusted': 0.0,
                'message': f'图像输入归一化失败: {_e}', 'prompt': ''
            }

        # 处理图片输入（统一归一化：数组 / PIL / bytes / 文件路径 / data:URI / 纯 base64）
        import re as _re
        if isinstance(image_input, str) and 'base64,' in image_input:
            base64_data = image_input.split('base64,', 1)[1]
            data_url = f"data:image/jpeg;base64,{base64_data}"
        elif isinstance(image_input, str) and os.path.exists(image_input):
            # 从文件读取并转为 base64
            with open(image_input, 'rb') as f:
                base64_data = base64.b64encode(f.read()).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{base64_data}"
        elif isinstance(image_input, str) and len(image_input) >= 24 and \
                _re.fullmatch(r'[A-Za-z0-9+/=\r\n]+', image_input):
            # 纯 base64 字符串（无 data: 前缀）——原实现不支持此形态，会误判为
            # Invalid image input；此处显式识别（2026-10-02 由 DSH 修复）
            base64_data = image_input.strip()
            data_url = f"data:image/jpeg;base64,{base64_data}"
        else:
            return {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'message': 'Invalid image input',
                'prompt': ''
            }
        
        # 构建中文提示词，让豆包用中文回答
        violation_cn = VIOLATION_TYPE_CN.get(violation_type, violation_type)

        # 给不同违规类型补充具体定义，提高大模型判断准确性
        type_definitions = {
            'wrong_way': '【逆行定义】车辆或非机动车朝向与道路规定行驶方向相反的方向行驶；包括车辆明显驶入对向车道、非机动车反向骑行等。注意：车辆在路口短暂越过停止线后倒车不属于逆行；车辆正常行驶但拍摄角度产生的错觉也不是逆行。',
            'red_light': '【闯红灯定义】红灯亮起后，车辆越过停止线并继续通过路口；需同时满足：(a) 信号灯为红灯 (b) 车辆已越过停止线。注意：黄灯通过不算闯红灯；车辆在停止线后等待也不是闯红灯。',
            'illegal_parking': '【违规停车定义】车辆在禁止停车的区域停留或停放，包括但不限于：禁停标志/标线区域、人行横道/斑马线、交叉路口、非机动车道、消防通道等。注意：车辆在停车场内正常车位停放不是违规；车辆在路边临时停靠有人在车上也需结合禁停标志判断。',
            'lane_departure': '【压线行驶/变道定义】车辆骑轧车道分界线（白色实线）行驶，或在禁止变道区域（路口、公交车站等）变更车道。注意：车辆正常行驶时短暂轻微越线不算违规；虚线变道是允许的。',
            'speeding': '【超速定义】车辆行驶速度超过该道路限速标志规定的速度。仅从图片难以准确判断速度，若没有测速辅助信息，请标注为"不确定"。',
            'no_helmet': '【未戴头盔定义】驾驶或乘坐摩托车/电动自行车的人员未佩戴安全头盔。注意：头盔颜色与衣物颜色相近但确实佩戴了不属于违规。'
        }
        extra_def = type_definitions.get(violation_type, '')

        # 事件级分析时附加结构化上下文（车辆/信号灯/轨迹），单帧违规分析时为空
        context_block = f"\n【结构化上下文（本地检测/跟踪提供，供参考）】\n{context_prompt}\n" if context_prompt else ""

        prompt = f"""请仔细、严谨地分析这张图片，判断是否存在"[{violation_cn}]"违规行为。

{extra_def}
{context_block}
【分析规则】
1. 只基于图片中可清晰辨识的内容进行判断，不要猜测
2. 如果图片模糊、信息不足或无法明确判断，必须标注为"不确定"
3. 不要被拍摄角度、光线阴影等干扰因素误导

【回答格式（必须严格遵守，使用中文）】
---分析结果---
第一步·场景描述：用1-2句话描述图片中的主要内容
第二步·是否违规：【是】或【否】或【不确定】（三选一，必须放在方括号内）
第三步·判断依据：列出支持你判断的2-3条关键视觉证据
第四步·置信度评分：给出一个 0-100 的整数（越大表示越确定存在违规；确定不存在违规时请给低分如10-30）
"""

        messages = [{
            "role": "user",
            "content": [
                {"image": data_url},
                {"text": prompt}
            ]
        }]
        
        # 调用大模型
        # 2026-11-01 修正（DSH）：原硬编码 'qwen3-vl-flash' 在本账号返回
        #   404 InvalidParameter: Model not exist
        # 实测该 key 可用的视觉模型是 'qwen3-vl-plus'（能正确读出图中文字）。
        # 改为环境变量可覆盖，换模型不用改代码：DASHSCOPE_VL_MODEL=qwen3-vl-plus
        _vl_model = os.environ.get('DASHSCOPE_VL_MODEL', 'qwen3-vl-plus')
        response = dashscope.MultiModalConversation.call(
            model=_vl_model,
            messages=messages,
            timeout=30
        )
        
        # 增加调用计数（成功或失败都算）
        try:
            from config_manager import increment_call_count
            increment_call_count('dashscope')
        except:
            pass
        
        if response.status_code == 200:
            result_text = response.output.choices[0].message.content[0]["text"]
            print(f"Doubao analysis result: {result_text}")

            # ===== 严格解析结果（v2 修复版：避免「不存在」不会再误判为「存在」）
            is_confirmed = False
            is_uncertain = False
            confidence_adjusted = 0.3  # 默认偏保守

            import re
            text_lower = result_text.lower()

            # 优先信任格式化结论；“不确定”与“否”必须分开保存。
            bracket_match = re.search(r'[【\[]\s*(是|否|不确定|不確定|未违规|未发现|不存在)\s*[】\]]', result_text)
            if bracket_match:
                signal = bracket_match.group(1)
                if signal == '是':
                    is_confirmed = True
                elif signal in ('不确定', '不確定'):
                    is_uncertain = True
                else:
                    is_confirmed = False
            else:
                # ---------- 第 2 步：严格关键字分析                # ---------- 第 2 步：严格关键字分析
                # 先查否定表达（优先级最高，避免"不存在"被误判）
                neg_patterns = [
                    r'不存在违规', r'没有发现.*违规', r'未发现.*违规',
                    r'未.*违规', r'不是违规', r'并未.*违规', r'不算违规',
                    r'不构成违规', r'不属于.*违规', r'并未.*违规',
                    r'判断为.*否', r'结论为.*否', r'判定为.*否',
                    r'：否', r':\s*否',
                    r'no.*没有.*no', r'不存在',
                ]
                found_neg = any(re.search(p, result_text) for p in neg_patterns)

                # 再查肯定表达
                pos_patterns = [
                    r'存在违规', r'发现.*违规', r'确认.*违规',
                    r'属于.*违规', r'判定为.*是', r'结论为.*是',
                    r'：是', r':\s*是',
                ]
                found_pos = any(re.search(p, result_text) for p in pos_patterns)
                found_uncertain = bool(re.search(r'不确定|不確定|无法判断|无法确定|信息不足|证据不足', result_text))

                # 缺少证据时不能把“不确定”当成“确认不存在违规”。
                if found_uncertain and not found_pos and not found_neg:
                    is_uncertain = True
                elif found_neg and not found_pos:
                    is_confirmed = False
                elif found_pos and not found_neg:
                    is_confirmed = True
                elif found_pos and found_neg:
                    # 两者都出现 → 取“是否违规”或“第二步”后面的明确结论
                    m = re.search(r'(?:是否违规|第二步|第二步.*是否|结论|判定|判断)[^。\n]*[：:]\s*([^。\n]+)', result_text)
                    if m:
                        conclusion = m.group(1)
                        is_uncertain = bool(re.search(r'不确定|不確定|无法判断|无法确定', conclusion))
                        is_confirmed = ('是' in conclusion and '否' not in conclusion and not is_uncertain)
                    else:
                        is_uncertain = True
            # ---------- 第 3 步：提取置信度（优先找"置信度"或"评分"字段）
            try:
                conf_match = re.search(r'(?:置信度|置信|评分|可能性|信心)[^0-9]{0,10}(\d{1,3})\s*(?:分|%|％)?', result_text)
                if conf_match:
                    try:
                        val = int(conf_match.group(1))
                        confidence_adjusted = max(0.05, min(val / 100.0, 1.0))
                    except ValueError:
                        pass
                else:
                    # 兜底：从文本中任意位置搜索 XX% 或 XX分
                    pct_match = re.search(r'(\d{1,3})\s*(?:%|％|分(?!$))', result_text)
                    if pct_match:
                        try:
                            confidence_adjusted = max(0.05, min(int(pct_match.group(1)) / 100.0, 1.0))
                        except ValueError:
                            pass
                    else:
                        # 完全没找到任何数字 → 根据判定结果给一个保守值
                        confidence_adjusted = 0.65 if is_confirmed else 0.20
            except Exception as parse_err:
                print(f"[warn] 置信度解析失败: {parse_err}，使用默认值 0.5")
                confidence_adjusted = 0.5
            
            return {
                'success': True,
                'result_text': result_text,
                'is_violation_confirmed': is_confirmed,
                'is_uncertain': is_uncertain,
                'confidence_adjusted': confidence_adjusted,
                'message': '豆包分析成功',
                'prompt': prompt
            }
        else:
            error_msg = f"豆包API调用失败: {response.code} - {response.message}"
            print(error_msg)
            return {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'message': error_msg,
                'prompt': prompt
            }

    except TimeoutError as e:
        error_msg = f"豆包分析超时（30秒）: {str(e)}"
        print(error_msg)
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'message': '云端分析超时，请稍后重试',
            'prompt': ''
        }
    except Exception as e:
        error_msg = f"豆包分析异常: {str(e)}"
        print(error_msg)
        # 一些 dashscope SDK 异常没有继承自 TimeoutError
        msg = str(e).lower()
        if 'timeout' in msg or 'timed out' in msg or 'time out' in msg:
            return {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'message': '云端分析超时，请稍后重试',
                'prompt': ''
            }
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'message': error_msg,
            'prompt': ''
        }

# ============ DeepSeek 审核员（新增） ============

def _get_deepseek_key():
    """从 config_manager 获取 DeepSeek API Key"""
    try:
        from config_manager import load_config
        cfg = load_config()
        key = cfg.get('deepseek', {}).get('api_key', '')
        if key:
            return key
    except:
        pass
    env_key = os.environ.get('DEEPSEEK_API_KEY', '')
    if env_key:
        return env_key
    return ""

def analyze_with_deepseek_judge(violation_type, yolo_result_dict, doubao_result_dict):
    """
    DeepSeek 作为"第二审核员"：读取 YOLO 检测结果和豆包完整推理过程，
    从逻辑层面审核豆包的判断是否合理，给出独立的审核意见。

    参数:
        violation_type: 违规类型（英文）
        yolo_result_dict: detect_with_yolo() 的返回结果
        doubao_result_dict: analyze_with_doubao() 的返回结果

    返回:
        {
            'success': bool,
            'result_text': str,          # DeepSeek 的完整审核文本
            'is_violation_confirmed': bool,  # DeepSeek 的独立判断
            'confidence_adjusted': float,    # DeepSeek 给的置信度
            'risk_level': str,           # 'high' | 'medium' | 'low'
            'doubao_opinion_match': bool,    # DeepSeek 是否同意豆包的结论
            'message': str,
            'prompt': str
        }
    """
    import requests

    api_key = _get_deepseek_key()
    if not api_key:
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'risk_level': 'low',
            'doubao_opinion_match': True,
            'message': 'DeepSeek API Key 未配置',
            'prompt': ''
        }

    # 原始 YOLO 置信度未随事件上下文传入时，明确标注“不可用”，不要伪装成 0.00。
    if yolo_result_dict and yolo_result_dict.get('confidence_available') is False:
        yolo_summary = '- ' + str(yolo_result_dict.get('message') or '本次事件未提供原始 YOLO 置信度，无法评估该字段')
    elif yolo_result_dict and yolo_result_dict.get('success'):
        dets = yolo_result_dict.get('detections', [])
        car_like = [d for d in dets if d.get('class_name') in ['car', 'motorcycle', 'bus', 'truck']]
        other_obj = [d for d in dets if d.get('class_name') not in ['car', 'motorcycle', 'bus', 'truck']]
        yolo_summary_lines = []
        if car_like:
            top3_car = sorted(car_like, key=lambda x: -x['confidence'])[:3]
            yolo_summary_lines.append("- 车辆/机动车检测：发现 {} 个目标，Top3：{}".format(
                len(car_like), '、'.join(["{}(置信度{:.2f})".format(d['class_name'], d['confidence']) for d in top3_car])
            ))
        if other_obj:
            top3_other = sorted(other_obj, key=lambda x: -x['confidence'])[:3]
            yolo_summary_lines.append("- 其他对象：{}，Top3：{}".format(
                len(other_obj), '、'.join(["{}(置信度{:.2f})".format(d['class_name'], d['confidence']) for d in top3_other])
            ))
        if not dets:
            yolo_summary_lines.append("- 本次事件未提供可量化的 YOLO 目标置信度")
        yolo_summary = '\n'.join(yolo_summary_lines)
    else:
        yolo_summary = "- YOLO 检测结果不可用（原因：{}）".format(
            yolo_result_dict.get('message', '未知') if yolo_result_dict else '未提供检测结果'
        )
    # 准备豆包推理
    doubao_success = doubao_result_dict and doubao_result_dict.get('success')
    doubao_raw = doubao_result_dict.get('result_text', '') if doubao_result_dict else ''
    doubao_decision = doubao_result_dict.get('is_violation_confirmed', False) if doubao_result_dict else False
    doubao_conf = doubao_result_dict.get('confidence_adjusted', 0.0) if doubao_result_dict else 0.0

    violation_cn = VIOLATION_TYPE_CN.get(violation_type, violation_type)

    # 定义各类违规的判定要点（给 DeepSeek 用）
    type_definitions = {
        'wrong_way': '逆行判定要点：必须有证据证明车辆朝向与正常行驶方向相反，且位于不应出现的车道。仅"看到有车"不算逆行。',
        'red_light': '闯红灯判定要点：必须同时观察到 (a) 信号灯为红灯 (b) 车辆已越过停止线继续行驶。缺一不可。',
        'illegal_parking': '违规停车判定要点：必须看到禁停标志/标线，或车辆停在明确禁止停车的区域（斑马线、消防通道、路口、非机动车道等）。路边有车不等于违规。',
        'lane_departure': '压线行驶判定要点：车辆必须骑轧白色实线，或在明确禁止变道的区域变道。正常行驶中轻微越线不算。',
        'speeding': '超速判定要点：仅凭静态图片无法准确判断车速，若豆包声称存在超速但未提供测速依据，应判定为不可靠。',
        'no_helmet': '未戴头盔判定要点：必须清晰看到骑手头部未佩戴头盔。图片模糊、角度不佳导致看不清的情况下，不能随意判定。'
    }
    extra_def = type_definitions.get(violation_type, '请基于通用逻辑审核。')

    # 构建 DeepSeek 的审核 prompt
    prompt = f"""你是一位严谨、保守的交通违规识别审核员。你的任务是阅读"豆包视觉模型"的推理过程，
并结合"YOLO 目标检测"的结果，从逻辑层面判断豆包的推理是否可靠、是否可信。

【当前违规类型】{violation_cn}
【判定要点】{extra_def}

【输入信息一：YOLO 目标检测摘要】
（YOLO 只能告诉我们"图片里有什么对象"，但无法判断这些对象是否违规。请仅作为场景上下文参考。）
{yolo_summary}

【输入信息二：豆包视觉模型的完整推理过程】
（这是豆包模型看了图片后给出的分析，包括它对场景的描述、它对违规与否的最终判断、它的判断依据。
 注意：视觉模型有时会出现"幻觉"——即描述与事实不符，或推理逻辑跳跃。你的任务是审核这段推理。）
--- 豆包推理开始 ---
{doubao_raw if doubao_raw else "（豆包分析失败，未返回有效内容）"}
--- 豆包推理结束 ---

【你的任务】
1. 先阅读豆包的完整推理，判断其证据与结论之间是否存在逻辑跳跃
2. 特别关注：豆包给出的"判断依据"能否支撑它的"是否违规"结论
3. 注意：如果 YOLO 检测到图片中根本没有车辆/目标对象，而豆包却说违规，这极有可能是误判
4. 注意：如果豆包的推理中出现了"看起来像……""可能是……""疑似……"等模糊措辞，但结论却很肯定，这也值得警惕

【请严格按以下格式输出（用中文）】
--- 审核报告 ---
第一步·你对场景的简要总结：用一句话概括图片中实际看到的内容
第二步·你对豆包推理的评价：
  - 证据充分性：【充分】/【不足】/【有矛盾】（三选一）
  - 逻辑严谨性：【严谨】/【有跳跃】/【明显不严谨】（三选一）
第三步·你的独立判断：【是违规】/【不是违规】/【无法确定·需人工】（三选一，必须放在方括号内）
第四步·你给出的置信度：0-100 的整数（数字越大表示你越确定该图片"确实"展示了该违规行为；若你认为图片中无违规，请给低分）
第五步·风险评估：【高风险误判】/【中风险】/【低风险可信】（三选一，基于你对豆包推理的信任程度）
第六步·给管理员的一句话建议：不超过 30 字
"""

    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个严谨、保守的推理审核员。你对证据的要求很高——没有充分证据就不能确认违规。你擅长从文本中识别逻辑矛盾、证据不足、主观臆断。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1500
            },
            timeout=30
        )

        # 计数
        try:
            from config_manager import increment_call_count
            increment_call_count('deepseek')
        except:
            pass

        if response.status_code == 200:
            result_text = response.json()['choices'][0]['message']['content']
            print(f"DeepSeek judge result: {result_text}")

            # 解析 DeepSeek 的输出
            is_confirmed = False
            is_uncertain = False
            confidence_adjusted = 0.3
            risk_level = 'medium'

            import re
            # 第三步·独立判断：【是违规】/【不是违规】/【无法确定·需人工】
            judge_match = re.search(r'第三步[^\n]*[：:][^\n]*[【\[]\s*(是违规|不是违规|无法确定|无法确定·需人工|不能确定|不确定)\s*[】\]]', result_text)
            if judge_match:
                signal = judge_match.group(1)
                if signal == '是违规':
                    is_confirmed = True
                elif signal in ('无法确定', '无法确定·需人工', '不能确定', '不确定'):
                    is_uncertain = True
            else:
                if re.search(r'无法确定|不能确定|不确定|证据不足', result_text):
                    is_uncertain = True
                elif '是违规' in result_text and '不是违规' not in result_text:
                    is_confirmed = True
                elif '不是违规' in result_text:
                    is_confirmed = False
            # 置信度
            conf_match = re.search(r'第四步[^\n]*[：:][^\n]*(\d{1,3})', result_text)
            if conf_match:
                try:
                    confidence_adjusted = max(0.05, min(int(conf_match.group(1)) / 100.0, 1.0))
                except ValueError:
                    pass
            else:
                confidence_adjusted = 0.7 if is_confirmed else 0.2

            # 风险等级
            if '高风险' in result_text:
                risk_level = 'high'
            elif '低风险' in result_text:
                risk_level = 'low'
            else:
                risk_level = 'medium'

            # DeepSeek 与豆包是否意见一致
            doubao_match = is_confirmed == doubao_decision

            return {
                'success': True,
                'result_text': result_text,
                'is_violation_confirmed': is_confirmed,
                'is_uncertain': is_uncertain,
                'confidence_adjusted': confidence_adjusted,
                'risk_level': risk_level,
                'doubao_opinion_match': (None if is_uncertain else is_confirmed == doubao_decision),
                'message': 'DeepSeek 审核成功',
                'prompt': prompt
            }
        else:
            try:
                err_detail = response.json().get('error', {}).get('message', response.text)
            except:
                err_detail = response.text
            return {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'risk_level': 'low',
                'doubao_opinion_match': True,
                'message': f"DeepSeek API 调用失败: {response.status_code} - {err_detail}",
                'prompt': prompt
            }

    except requests.exceptions.Timeout:
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'risk_level': 'low',
            'doubao_opinion_match': True,
            'message': 'DeepSeek 请求超时（30秒），请稍后重试',
            'prompt': ''
        }
    except Exception as e:
        msg = str(e).lower()
        if 'timeout' in msg or 'timed out' in msg:
            return {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'risk_level': 'low',
                'doubao_opinion_match': True,
                'message': 'DeepSeek 请求超时，请稍后重试',
                'prompt': ''
            }
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'risk_level': 'low',
            'doubao_opinion_match': True,
            'message': f'DeepSeek 调用异常: {str(e)}',
            'prompt': ''
        }

def analyze_with_deepseek_vision(image_input, violation_type):
    """
    DeepSeek 独立视觉识别（当豆包失败时的兜底方案）

    参数:
        image_input: 图片路径或 base64 字符串
        violation_type: 违规类型（英文）

    返回:
        {
            'success': bool,
            'result_text': str,
            'is_violation_confirmed': bool,
            'confidence_adjusted': float,
            'message': str,
            'prompt': str
        }
    """
    import requests
    import re

    api_key = _get_deepseek_key()
    if not api_key:
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'message': 'DeepSeek API Key 未配置',
            'prompt': ''
        }

    # 处理图片输入（复用 analyze_with_doubao 的逻辑）
    try:
        if image_input.startswith('data:image') or 'base64,' in image_input:
            if 'base64,' in image_input:
                base64_data = image_input.split('base64,')[1]
            else:
                base64_data = image_input
            image_base64 = base64_data
        elif os.path.exists(image_input):
            with open(image_input, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
        else:
            return {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'message': 'Invalid image input',
                'prompt': ''
            }
    except Exception as e:
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'message': f'图片读取失败: {str(e)}',
            'prompt': ''
        }

    violation_cn = VIOLATION_TYPE_CN.get(violation_type, violation_type)

    prompt_text = f"""请观察图片，判断是否存在【{violation_cn}】。

回答格式严格如下：

第一步·场景描述：一句话；
第二步·是否违规：【是】/【否】/【不确定】三选一，必须方括号；
第三步·判断依据：2-3条证据；
第四步·置信度：0-100整数。

注意：图像模糊/证据不足/无法看清时必须写【不确定】。"""

    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一名严谨的交通违规识别员，只做客观描述，不主观臆断"
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                            },
                            {
                                "type": "text",
                                "text": prompt_text
                            }
                        ]
                    }
                ],
                "max_tokens": 1500,
                "temperature": 0.2
            },
            timeout=30
        )

        # 计数
        try:
            from config_manager import increment_call_count
            increment_call_count('deepseek')
        except:
            pass

        if response.status_code == 200:
            result_text = response.json()['choices'][0]['message']['content']
            print(f"DeepSeek vision result: {result_text}")

            # 解析结果
            is_confirmed = False
            confidence_adjusted = 0.3

            # 匹配 【是】/【否】/【不确定】
            decision_match = re.search(r'第二步[^\n]*[：:]\s*[【\[]\s*(是|否|不确定)\s*[】\]]', result_text)
            if decision_match:
                signal = decision_match.group(1)
                if signal == '是':
                    is_confirmed = True
                elif signal in ['否', '不确定']:
                    is_confirmed = False
            else:
                # 兜底：直接搜索关键词
                if '是违规' in result_text and '不是违规' not in result_text:
                    is_confirmed = True
                else:
                    is_confirmed = False

            # 提取置信度
            conf_match = re.search(r'第四步[^\n]*[：:][^\n]*(\d{1,3})', result_text)
            if conf_match:
                try:
                    confidence_adjusted = max(0.05, min(int(conf_match.group(1)) / 100.0, 1.0))
                except ValueError:
                    pass
            else:
                confidence_adjusted = 0.7 if is_confirmed else 0.2

            return {
                'success': True,
                'result_text': result_text,
                'is_violation_confirmed': is_confirmed,
                'confidence_adjusted': confidence_adjusted,
                'message': 'DeepSeek 视觉识别成功',
                'prompt': prompt_text
            }
        else:
            try:
                err_detail = response.json().get('error', {}).get('message', response.text)
            except:
                err_detail = response.text
            return {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'message': f"DeepSeek API 调用失败: {response.status_code} - {err_detail}",
                'prompt': prompt_text
            }

    except requests.exceptions.Timeout:
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'message': 'DeepSeek 请求超时（30秒），请稍后重试',
            'prompt': prompt_text
        }
    except Exception as e:
        msg = str(e).lower()
        if 'timeout' in msg or 'timed out' in msg:
            return {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'message': 'DeepSeek 请求超时，请稍后重试',
                'prompt': prompt_text
            }
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'message': f'DeepSeek 调用异常: {str(e)}',
            'prompt': prompt_text
        }

def analyze_with_claude(image_input, violation_type, context_prompt=""):
    """
    使用 Claude 3.5 Sonnet 进行视觉分析（替代豆包作为主要视觉模型）

    参数:
        image_input: 图片路径或 base64 字符串
        violation_type: 违规类型（英文）
        context_prompt: 事件级结构化上下文（可选；单帧违规分析留空）

    返回:
        {
            'success': bool,
            'result_text': str,
            'is_violation_confirmed': bool,
            'confidence_adjusted': float,
            'risk_level': str,
            'message': str,
            'prompt': str
        }
    """
    import requests
    import re

    api_key = Config.CLAUDE_API_KEY
    if not api_key:
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'risk_level': 'low',
            'message': 'Claude API Key 未配置',
            'prompt': ''
        }

    try:
        if image_input.startswith('data:image') or 'base64,' in image_input:
            if 'base64,' in image_input:
                base64_data = image_input.split('base64,')[1]
            else:
                base64_data = image_input
            image_base64 = base64_data
        elif os.path.exists(image_input):
            with open(image_input, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
        else:
            return {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'risk_level': 'low',
                'message': 'Invalid image input',
                'prompt': ''
            }
    except Exception as e:
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'risk_level': 'low',
            'message': f'图片读取失败: {str(e)}',
            'prompt': ''
        }

    violation_cn = VIOLATION_TYPE_CN.get(violation_type, violation_type)

    # 事件级分析时附加结构化上下文（车辆/信号灯/轨迹），单帧违规分析时为空
    context_block = f"\n【结构化上下文（本地检测/跟踪提供，供参考）】\n{context_prompt}\n" if context_prompt else ""

    prompt_text = f"""你是一名严谨的交通违规识别专家。请仔细观察图片，判断是否存在【{violation_cn}】。
{context_block}
回答格式严格如下：

第一步·场景描述：一句话描述图片中的交通场景；
第二步·是否违规：【是】/【否】/【不确定】三选一，必须使用方括号；
第三步·判断依据：列出2-3条关键证据；
第四步·置信度：0-100的整数，表示你对判断的信心程度；
第五步·风险等级：【高风险】/【中风险】/【低风险】三选一。

注意事项：
- 图像模糊、证据不足、无法看清细节时，必须回答【不确定】
- 必须严格按照上述格式输出，不要添加额外内容
- 【不确定】情况下，风险等级应为【低风险】"""

    try:
        response = requests.post(
            Config.CLAUDE_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-3-5-sonnet-20240620",
                "max_tokens": 1500,
                "temperature": 0.2,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt_text
                            }
                        ]
                    }
                ]
            },
            timeout=60
        )

        try:
            from config_manager import increment_call_count
            increment_call_count('claude')
        except:
            pass

        if response.status_code == 200:
            result_data = response.json()
            result_text = result_data.get('content', [{}])[0].get('text', '')
            print(f"Claude result: {result_text}")

            is_confirmed = False
            is_uncertain = False
            confidence_adjusted = 0.3
            risk_level = 'medium'

            decision_match = re.search(r'第二步[^\n]*[：:]\s*[【\[]\s*(是|否|不确定)\s*[】\]]', result_text)
            if decision_match:
                signal = decision_match.group(1)
                if signal == '是':
                    is_confirmed = True
                elif signal == '不确定':
                    is_uncertain = True
                else:
                    is_confirmed = False
            else:
                if re.search(r'无法确定|无法判断|不确定|证据不足', result_text):
                    is_uncertain = True
                elif '是违规' in result_text and '不是违规' not in result_text:
                    is_confirmed = True
                elif '不是违规' in result_text:
                    is_confirmed = False

            conf_match = re.search(r'第四步[^\n]*[：:][^\n]*(\d{1,3})', result_text)
            if conf_match:
                try:
                    confidence_adjusted = max(0.05, min(int(conf_match.group(1)) / 100.0, 1.0))
                except ValueError:
                    pass
            else:
                confidence_adjusted = 0.7 if is_confirmed else 0.2

            risk_match = re.search(r'第五步[^\n]*[：:]\s*[【\[]\s*(高风险|中风险|低风险)\s*[】\]]', result_text)
            if risk_match:
                risk_level = risk_match.group(1)
            else:
                if is_confirmed and confidence_adjusted > 0.8:
                    risk_level = 'high'
                elif is_confirmed:
                    risk_level = 'medium'
                else:
                    risk_level = 'low'

            return {
                'success': True,
                'result_text': result_text,
                'is_violation_confirmed': is_confirmed,
                'is_uncertain': is_uncertain,
                'confidence_adjusted': confidence_adjusted,
                'risk_level': risk_level,
                'message': 'Claude 分析成功',
                'prompt': prompt_text
            }
        else:
            try:
                err_detail = response.json().get('error', {}).get('message', response.text)
            except:
                err_detail = response.text
            return {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'risk_level': 'low',
                'message': f"Claude API 调用失败: {response.status_code} - {err_detail}",
                'prompt': prompt_text
            }

    except requests.exceptions.Timeout:
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'risk_level': 'low',
            'message': 'Claude 请求超时（60秒），请稍后重试',
            'prompt': prompt_text
        }
    except Exception as e:
        msg = str(e).lower()
        if 'timeout' in msg or 'timed out' in msg:
            return {
                'success': False,
                'result_text': '',
                'is_violation_confirmed': False,
                'confidence_adjusted': 0.0,
                'risk_level': 'low',
                'message': 'Claude 请求超时，请稍后重试',
                'prompt': prompt_text
            }
        return {
            'success': False,
            'result_text': '',
            'is_violation_confirmed': False,
            'confidence_adjusted': 0.0,
            'risk_level': 'low',
            'message': f'Claude 调用异常: {str(e)}',
            'prompt': prompt_text
        }

def analyze_image(image_input, violation_type, use_multi_model=True):
    """
    完整的图片分析流程（v4 - 支持多模型）：
    阶段1：多模型串联检测 —— yolov8n（车辆）→ helmet模型（头盔）
    阶段2：规则引擎判断 —— 基于检测结果判断违规
    阶段3：豆包视觉分析 —— 视觉模型判断是否存在违规
    阶段4：DeepSeek（根据豆包结果决定是审核还是独立视觉）

    参数:
        image_input: 图片路径或 base64 字符串
        violation_type: 违规类型
        use_multi_model: 是否使用多模型串联检测

    返回:
        {
            'success': bool,
            'yolo_result': dict,
            'multi_model_result': dict,
            'doubao_result': dict,
            'deepseek_result': dict,
            'violation_result': dict,
            'final_decision': bool,
            'final_confidence': float,
            'needs_human_review': bool,
            'message': str,
            'fallback': bool,
            'ai_trace': { ... }
        }
    """
    import time
    started_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    start_time = time.time()

    # ===== 阶段 1：多模型串联检测 =====
    yolo_start = time.time()
    if use_multi_model:
        yolo_result = detect_with_multiple_models(image_input, model_keys=['yolov8n', 'helmet'])
    else:
        yolo_result = detect_with_yolo(image_input)
    yolo_duration_ms = int((time.time() - yolo_start) * 1000)

    # ===== 阶段 2：规则引擎判断 =====
    violation_start = time.time()
    violation_result = {
        'success': False,
        'violations': [],
        'message': '规则引擎未启用'
    }
    try:
        from violation_rules import check_violations
        all_detections = []
        if use_multi_model and yolo_result.get('merged_detections'):
            all_detections = yolo_result['merged_detections']
        elif yolo_result.get('detections'):
            all_detections = yolo_result['detections']
        
        violation_result = check_violations(all_detections, violation_type)
    except ImportError:
        violation_result['message'] = '规则引擎模块未安装'
    except Exception as e:
        violation_result['message'] = f'规则引擎执行失败: {str(e)}'
    violation_duration_ms = int((time.time() - violation_start) * 1000)

    # ===== 阶段 3：豆包视觉分析 =====
    doubao_start = time.time()
    doubao_result = analyze_with_doubao(image_input, violation_type)
    doubao_duration_ms = int((time.time() - doubao_start) * 1000)

    # ===== 阶段 4：DeepSeek（根据豆包结果决定模式） =====
    deepseek_start = time.time()
    mode = 'doubao+deepseek_audit'
    ds_role = 'logic_audit'
    ds_warning = None

    if doubao_result.get('success'):
        deepseek_result = analyze_with_deepseek_judge(violation_type, yolo_result, doubao_result)
    else:
        deepseek_result = analyze_with_deepseek_vision(image_input, violation_type)
        mode = 'deepseek_vision_only'
        ds_role = 'vision_only'
        ds_warning = '豆包未返回结果，本次由 DeepSeek 独立识别，缺少双模型对比校验'

    deepseek_duration_ms = int((time.time() - deepseek_start) * 1000)

    total_duration_ms = int((time.time() - start_time) * 1000)
    finished_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ===== 综合判定（v4） =====
    final_decision = False
    final_confidence = 0.3
    needs_human_review = False
    rule_used = 'all_failed'
    messages = []

    # ---- 多模型检测摘要 ----
    if yolo_result['success']:
        if use_multi_model and yolo_result.get('merged_detections'):
            detected = [f"{d['class_name_cn']}({d['confidence']:.2f})" for d in yolo_result['merged_detections']]
            messages.append(f"多模型检测：{', '.join(detected) if detected else '无对象'}")
        elif yolo_result.get('detections'):
            detected = [f"{d['class_name_cn']}({d['confidence']:.2f})" for d in yolo_result.get('detections', [])]
            messages.append(f"YOLO检测：{', '.join(detected) if detected else '无对象'}")
    else:
        messages.append(f"检测：{yolo_result.get('message', '失败')}")

    # ---- 规则引擎摘要 ----
    if violation_result['success'] and violation_result.get('violations'):
        vio_names = [v['violation_type_cn'] for v in violation_result['violations']]
        messages.append(f"规则引擎：检测到 {', '.join(vio_names)}")
        if any(v.get('confidence', 0) > 0.7 for v in violation_result['violations']):
            final_decision = True
            final_confidence = max(v.get('confidence', 0) for v in violation_result['violations'])

    # ---- 豆包摘要 ----
    if doubao_result['success']:
        messages.append(f"豆包：{'是违规' if doubao_result.get('is_violation_confirmed') else '不是违规'}"
                        f"（置信度 {doubao_result.get('confidence_adjusted', 0):.2f}）")
    else:
        messages.append(f"豆包：分析失败（{doubao_result.get('message', '未知错误')}）")

    # ---- DeepSeek 摘要 ----
    if deepseek_result['success']:
        ds_text = "DeepSeek：{}{}（置信度 {:.2f}，{}）"
        ds_decision_text = '是违规' if deepseek_result.get('is_violation_confirmed') else '不是违规/不确定'
        risk_cn = {'high': '高风险', 'medium': '中风险', 'low': '低风险'}.get(deepseek_result.get('risk_level', 'medium'), '中风险')
        messages.append(ds_text.format(ds_decision_text, '' if deepseek_result.get('doubao_opinion_match') else '（与豆包不一致）',
                                       deepseek_result.get('confidence_adjusted', 0), risk_cn))
    else:
        messages.append(f"DeepSeek：{deepseek_result.get('message', '不可用')}")

    # ---- 决策引擎 + rule_used 计算 ----
    doubao_ok = doubao_result.get('success', False)
    deepseek_ok = deepseek_result.get('success', False)
    doubao_decide = doubao_result.get('is_violation_confirmed', False) if doubao_ok else None
    deepseek_decide = deepseek_result.get('is_violation_confirmed', False) if deepseek_ok else None

    if doubao_ok and deepseek_ok:
        # 两个模型都可用
        if doubao_result.get('is_violation_confirmed') == deepseek_result.get('is_violation_confirmed'):
            # 意见一致 → 采纳
            final_decision = doubao_result['is_violation_confirmed']
            final_confidence = (doubao_result.get('confidence_adjusted', 0.5) + deepseek_result.get('confidence_adjusted', 0.5)) / 2
            rule_used = 'both_agree'
        else:
            # 意见不一致 → 默认 "不违规"（宁纵勿枉），强制标记为"待人工"
            final_decision = False
            final_confidence = min(doubao_result.get('confidence_adjusted', 0.5), deepseek_result.get('confidence_adjusted', 0.5)) * 0.6
            needs_human_review = True
            rule_used = 'disagreement_pending'
            messages.append("⚠ 豆包与 DeepSeek 意见不一致，已标记待人工审核")

        # 高风险强制标记：无论意见是否一致
        if deepseek_result.get('risk_level') == 'high':
            needs_human_review = True
            messages.append("⚠ DeepSeek 评估为「高风险误判」，建议人工复核")

    elif doubao_ok and not deepseek_ok:
        # 只有豆包可用 → 采用豆包判断，但标记"建议人工"（缺了一层审核）
        final_decision = doubao_result['is_violation_confirmed']
        final_confidence = doubao_result.get('confidence_adjusted', 0.5)
        needs_human_review = True
        rule_used = 'doubao_only'
        messages.append("（仅有豆包结果，建议人工复核）")

    elif not doubao_ok and deepseek_ok:
        # 只有 DeepSeek 可用 → DeepSeek 独立视觉
        final_decision = deepseek_result['is_violation_confirmed']
        final_confidence = deepseek_result.get('confidence_adjusted', 0.3)
        needs_human_review = True
        rule_used = 'deepseek_only'
        messages.append("（豆包失败，DeepSeek 独立识别，建议人工复核）")

    else:
        # 两个模型都失败
        final_decision = False
        final_confidence = 0.2
        needs_human_review = True
        rule_used = 'all_failed'
        messages.append("（两个云端模型均不可用，无法自动判断）")

    # ---- AI 推理链（v3·嵌套结构）----
    # YOLO 摘要化（不包含 bbox 原始数据）
    if yolo_result.get('success'):
        yolo_detections_sorted = sorted(
            yolo_result.get('detections', []),
            key=lambda x: -x.get('confidence', 0)
        )[:5]
        yolo_detections_summary = [
            {'class_name': d.get('class_name', '未知'), 'confidence': round(d.get('confidence', 0), 2)}
            for d in yolo_detections_sorted
        ]
        yolo_message = '; '.join([d['class_name'] for d in yolo_detections_summary]) if yolo_detections_summary else '无对象'
    else:
        yolo_detections_summary = []
        yolo_message = yolo_result.get('message', '失败')

    ai_trace = {
        'version': 'v3',
        'mode': mode,
        'rule_used': rule_used,
        'started_at': started_at,
        'finished_at': finished_at,
        'total_duration_ms': total_duration_ms,

        # YOLO：嵌套对象（摘要化）
        'yolo': {
            'success': yolo_result.get('success', False),
            'message': yolo_message,
            'object_count': len(yolo_result.get('detections', [])),
            'detections': yolo_detections_summary
        },

        # 豆包：嵌套对象
        'doubao': {
            'success': doubao_ok,
            'status': 'success' if doubao_ok else 'failed',
            'decision': bool(doubao_result.get('is_violation_confirmed')) if doubao_ok else None,
            'confidence': round(doubao_result.get('confidence_adjusted', 0.0), 2) if doubao_ok else None,
            'raw_text': doubao_result.get('result_text', '') if doubao_ok else '',
            'duration_ms': doubao_duration_ms
        },

        # DeepSeek：嵌套对象（带 warning 字段）
        'deepseek': {
            'success': deepseek_ok,
            'role': ds_role,
            'decision': bool(deepseek_result.get('is_violation_confirmed')) if deepseek_ok else None,
            'confidence': round(deepseek_result.get('confidence_adjusted', 0.0), 2) if deepseek_ok else None,
            'risk_level': deepseek_result.get('risk_level', 'low') if deepseek_ok else 'low',
            'agree_with_doubao': (
                deepseek_result.get('is_violation_confirmed') == doubao_result.get('is_violation_confirmed')
                if deepseek_ok and doubao_ok else None
            ),
            'warning': ds_warning if deepseek_ok else ('DeepSeek 不可用: ' + deepseek_result.get('message', '未知')),
            'raw_text': deepseek_result.get('result_text', '') if deepseek_ok else '',
            'duration_ms': deepseek_duration_ms
        },

        # 最终决策：嵌套对象
        'final': {
            'decision': '确认违规' if final_decision else '未确认违规',
            'confidence': round(final_confidence, 2),
            'needs_human_review': needs_human_review,
            'rule_used': rule_used
        }
    }

    # 兜底：如果 YOLO 和两端都失败
    if not yolo_result['success'] and not doubao_ok and not deepseek_ok:
        return {
            'success': False,
            'yolo_result': yolo_result,
            'doubao_result': doubao_result,
            'deepseek_result': deepseek_result,
            'final_decision': False,
            'final_confidence': 0.2,
            'needs_human_review': True,
            'message': '所有模型均不可用，请人工审核',
            'fallback': True,
            'ai_trace': ai_trace
        }

    return {
        'success': True,
        'yolo_result': yolo_result,
        'doubao_result': doubao_result,
        'deepseek_result': deepseek_result,
        'final_decision': final_decision,
        'final_confidence': round(final_confidence, 2),
        'needs_human_review': needs_human_review,
        'message': '; '.join(messages),
        'fallback': False,
        'ai_trace': ai_trace
    }

# 测试代码
if __name__ == "__main__":
    print("=== Image Recognition Module Test (v4) ===")
    
    init_all_models()
    
    test_image = os.path.join(os.path.dirname(__file__), 'uploads', 'violation_b0b9a3ad_20260609_112733.jpg')
    if not os.path.exists(test_image):
        test_image = os.path.join(os.path.dirname(__file__), 'uploads', 'upload_0deea0ce_20260612_031455.jpg')
    
    print(f"\n测试图片: {test_image}")
    if not os.path.exists(test_image):
        print("测试图片未找到")
        exit(1)
    
    # 测试单模型检测
    print("\n1. Test Single Model Detection (yolov8n)")
    result = detect_with_yolo(test_image, model_key='yolov8n')
    print(f"Success: {result['success']}")
    if result['success']:
        for d in result['detections']:
            print(f"  - {d['class_name']} ({d['class_name_cn']}): {d['confidence']:.2f}")
    
    # 测试头盔模型检测
    print("\n2. Test Helmet Model Detection")
    result = detect_with_yolo(test_image, model_key='helmet')
    print(f"Success: {result['success']}")
    if result['success']:
        for d in result['detections']:
            print(f"  - {d['class_name']} ({d['class_name_cn']}): {d['confidence']:.2f}")
    
    # 测试多模型串联检测
    print("\n3. Test Multi-Model Detection")
    result = detect_with_multiple_models(test_image, model_keys=['yolov8n', 'helmet'])
    print(f"Success: {result['success']}")
    print(f"Merged detections: {len(result['merged_detections'])}")
    for d in result['merged_detections']:
        print(f"  - {d['class_name']} ({d['class_name_cn']}): {d['confidence']:.2f}")
    
    # 测试完整流程
    print("\n4. Test Complete Analysis (multi-model)")
    result = analyze_image(test_image, 'no_helmet', use_multi_model=True)
    print(f"Final decision: {'Violation confirmed' if result['final_decision'] else 'Not confirmed'}")
    print(f"Final confidence: {result['final_confidence']}")
    print(f"Message: {result['message']}")


# ============ 端云协作集成（TASK-008 步骤3） ============

def analyze_with_collaboration(image_input, violation_type=None):
    """
    端云协作检测完整流程

    流程：
        a. 本地 YOLO（yolov8s）检测
        b. 多模型串联检测
        c. 从检测结果中提取违规信息
        d. 实例化 CloudCollaborator（延迟导入避免循环依赖）
        e. 判断是否需要咨询云端（urgent/consult/normal）
        f. 如需咨询，调用云端大模型（豆包 + DeepSeek）
        g. 生成最终裁决
        h. 构建 v3 格式 ai_trace
        i. 返回完整结果

    参数:
        image_input: 图片路径或 base64 字符串
        violation_type: 违规类型（英文），可选；为空时从检测结果推断

    返回:
        {
            'success': bool,
            'mode': 'urgent' | 'consult' | 'normal',
            'local_detection': {...},
            'cloud_result': {...},
            'final_judgment': 'confirmed' | 'rejected' | 'uncertain',
            'final_confidence': float,
            'ai_trace': {
                'version': 'v3',
                'yolo': {...},
                'doubao': {...},
                'deepseek': {...},
                'final': {...}
            },
            'session_id': str,
            'message': str
        }
    """
    import uuid

    # 生成会话 ID
    session_id = uuid.uuid4().hex

    # 初始化返回结构（保证任何步骤失败都有可返回的结构）
    result = {
        'success': False,
        'mode': 'normal',
        'local_detection': {},
        'cloud_result': {},
        'final_judgment': 'uncertain',
        'final_confidence': 0.0,
        'ai_trace': {
            'version': 'v3',
            'yolo': {},
            'doubao': {},
            'deepseek': {},
            'final': {}
        },
        'session_id': session_id,
        'message': '端云协作检测完成'
    }

    # ===== 步骤 a：本地 YOLO 检测（yolov8s）=====
    try:
        yolo_result = detect_with_yolo(image_input, 'yolov8s')
        if not isinstance(yolo_result, dict):
            yolo_result = {
                'success': False,
                'detections': [],
                'message': 'detect_with_yolo 返回格式异常',
                'model_key': 'yolov8s'
            }
    except Exception as e:
        yolo_result = {
            'success': False,
            'detections': [],
            'message': f'YOLO 检测异常: {e}',
            'model_key': 'yolov8s'
        }

    # ===== 步骤 b：多模型串联检测 =====
    try:
        multi_result = multi_model_detect(image_input)
        if not isinstance(multi_result, dict):
            multi_result = {
                'success': False,
                'all_detections': [],
                'violations': [],
                'message': 'multi_model_detect 返回格式异常'
            }
    except Exception as e:
        multi_result = {
            'success': False,
            'all_detections': [],
            'violations': [],
            'message': f'多模型检测异常: {e}'
        }

    # ===== 步骤 c：从检测结果中提取违规信息 =====
    violations = multi_result.get('violations', []) if multi_result else []

    # 确定违规类型：优先使用传入参数，否则从检测结果推断
    detected_violation_type = violation_type
    if not detected_violation_type and violations:
        detected_violation_type = violations[0].get('violation_type', 'unknown')
    if not detected_violation_type:
        detected_violation_type = 'unknown'

    # 计算本地整体置信度
    local_confidence = 0.0
    if violations:
        # 有违规：取最高违规置信度
        try:
            local_confidence = max(float(v.get('confidence', 0.0)) for v in violations)
        except Exception:
            local_confidence = 0.0
    elif yolo_result.get('success') and yolo_result.get('detections'):
        # 无违规但有检测对象：取最高检测置信度
        try:
            local_confidence = max(float(d.get('confidence', 0.0)) for d in yolo_result['detections'])
        except Exception:
            local_confidence = 0.0

    # 本地是否判定违规
    local_is_violation = len(violations) > 0

    # 整合本地检测结果（供 should_consult_cloud 使用）
    local_detection = {
        'success': bool(yolo_result.get('success', False) or multi_result.get('success', False)),
        'violation_type': detected_violation_type,
        'confidence': local_confidence,
        'detections': yolo_result.get('detections', []),
        'violations': violations,
        'yolo_result': yolo_result,
        'multi_model_result': multi_result,
        'is_violation': local_is_violation
    }

    result['local_detection'] = local_detection

    # ===== 步骤 d：延迟导入 CloudCollaborator，避免循环依赖 =====
    collaborator = None
    try:
        from cloud_collaborator import CloudCollaborator
        collaborator = CloudCollaborator()
    except Exception as e:
        # 导入失败：仅返回本地检测结果，不中断流程
        result['success'] = bool(local_detection['success'])
        result['mode'] = 'normal'
        result['final_judgment'] = 'confirmed' if local_is_violation else 'rejected'
        result['final_confidence'] = round(local_confidence, 2)
        result['ai_trace'] = {
            'version': 'v3',
            'yolo': {
                'violation_type': detected_violation_type,
                'confidence': local_confidence,
                'detections': yolo_result.get('detections', []),
                'duration_ms': int(multi_result.get('duration_ms', 0) or 0)
            },
            'doubao': {},
            'deepseek': {},
            'final': {
                'judgment': result['final_judgment'],
                'confidence': result['final_confidence'],
                'method': 'local_only',
                'evidence_count': 1
            }
        }
        result['message'] = f'CloudCollaborator 加载失败，仅使用本地检测: {e}'
        return result

    # ===== 步骤 e：判断是否需要咨询云端 =====
    consult_mode = None
    try:
        consult_mode = collaborator.should_consult_cloud(local_detection)
    except Exception as e:
        # 判断失败：视为无需咨询，记录错误后继续
        consult_mode = None

    # 设置协作模式
    if consult_mode == 'urgent':
        result['mode'] = 'urgent'
    elif consult_mode == 'consult':
        result['mode'] = 'consult'
    else:
        result['mode'] = 'normal'

    # ===== 步骤 f：如果需要咨询，调用 consult_cloud =====
    cloud_result = {}
    if consult_mode in ('urgent', 'consult'):
        try:
            local_judgment = {
                'violation_type': detected_violation_type,
                'yolo_result': yolo_result,
                'confidence': local_confidence
            }
            cloud_result = collaborator.consult_cloud(
                image_input,
                local_judgment,
                consult_mode
            )
            if not isinstance(cloud_result, dict):
                cloud_result = {
                    'success': False,
                    'doubao_result': {},
                    'deepseek_result': {},
                    'duration_ms': 0,
                    'reason': consult_mode,
                    'pending_review': True,
                    'violation_type': detected_violation_type,
                    'timestamp': datetime.now().isoformat(),
                    'message': 'consult_cloud 返回格式异常'
                }
        except Exception as e:
            # 云端咨询异常：标记待人工复核，不中断流程
            cloud_result = {
                'success': False,
                'doubao_result': {},
                'deepseek_result': {},
                'duration_ms': 0,
                'reason': consult_mode,
                'pending_review': True,
                'violation_type': detected_violation_type,
                'timestamp': datetime.now().isoformat(),
                'message': f'consult_cloud 异常: {e}'
            }

    result['cloud_result'] = cloud_result

    # ===== 步骤 g：调用 process_cloud_response 生成最终裁决 =====
    final_result = {}
    try:
        if cloud_result:
            local_for_judge = {
                'is_violation': local_is_violation,
                'confidence': local_confidence
            }
            final_result = collaborator.process_cloud_response(local_for_judge, cloud_result)
        else:
            # 无需咨询云端：直接基于本地结果生成裁决
            final_result = {
                'judgment': 'confirmed' if local_is_violation else 'rejected',
                'confidence': round(local_confidence, 4),
                'method': 'local_autonomous',
                'evidence_count': 1,
                'disagreement_flag': False,
                'pending_review': False,
                'doubao_opinion_match': True
            }
        if not isinstance(final_result, dict):
            final_result = {
                'judgment': 'uncertain',
                'confidence': 0.0,
                'method': 'unknown',
                'evidence_count': 0,
                'disagreement_flag': False,
                'pending_review': True,
                'doubao_opinion_match': True
            }
    except Exception as e:
        # 裁决生成异常：标记为不确定，不中断流程
        final_result = {
            'judgment': 'pending_review',
            'confidence': 0.0,
            'method': 'error_fallback',
            'evidence_count': 0,
            'disagreement_flag': False,
            'pending_review': True,
            'doubao_opinion_match': True,
            'error': f'process_cloud_response 异常: {e}'
        }

    # 映射 judgment 到 final_judgment
    # process_cloud_response 返回 'confirmed'/'rejected'/'pending_review'
    # 任务要求返回 'confirmed'/'rejected'/'uncertain'
    judgment_map = {
        'confirmed': 'confirmed',
        'rejected': 'rejected',
        'pending_review': 'uncertain'
    }
    result['final_judgment'] = judgment_map.get(final_result.get('judgment', ''), 'uncertain')
    try:
        result['final_confidence'] = round(float(final_result.get('confidence', 0.0)), 2)
    except (TypeError, ValueError):
        result['final_confidence'] = 0.0

    # ===== 步骤 h：调用 build_ai_trace 构建 v3 格式 ai_trace =====
    try:
        doubao_for_trace = cloud_result.get('doubao_result', {}) if cloud_result else {}
        deepseek_for_trace = cloud_result.get('deepseek_result', {}) if cloud_result else {}

        ai_trace = collaborator.build_ai_trace(
            yolo_result,
            doubao_for_trace,
            deepseek_for_trace,
            final_result
        )
        if isinstance(ai_trace, dict):
            result['ai_trace'] = ai_trace
        else:
            raise ValueError('build_ai_trace 返回非字典')
    except Exception as e:
        # 构建 ai_trace 失败：使用最小化结构兜底
        result['ai_trace'] = {
            'version': 'v3',
            'yolo': {
                'violation_type': detected_violation_type,
                'confidence': local_confidence,
                'detections': yolo_result.get('detections', []),
                'duration_ms': int(multi_result.get('duration_ms', 0) or 0)
            },
            'doubao': cloud_result.get('doubao_result', {}) if cloud_result else {},
            'deepseek': cloud_result.get('deepseek_result', {}) if cloud_result else {},
            'final': final_result,
            'error': f'build_ai_trace 异常: {e}'
        }

    # ===== 步骤 i：返回完整结果 =====
    result['success'] = True
    result['message'] = '端云协作检测完成'

    return result
