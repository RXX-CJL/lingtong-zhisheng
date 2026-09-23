# -*- coding: utf-8 -*-
"""
车辆检测模块
基于YOLOv8n的实时车辆检测
"""

import sensor
import image
import time
from libs.YOLO import YOLOv5


class VehicleDetector:
    """车辆检测器类"""

    # COCO数据集标签（仅保留车辆相关类别）
    COCO_LABELS = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
        "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
        "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
        "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
        "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
        "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
        "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
        "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
        "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
        "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
        "toothbrush"
    ]

    # 车辆类别（用于过滤）
    VEHICLE_CLASS_IDS = [2, 3, 5, 7]  # car, motorcycle, bus, truck
    VEHICLE_NAMES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

    def __init__(self, kmodel_path, confidence_threshold=0.5,
                 rgb888p_size=None, model_input_size=None):
        """
        初始化车辆检测器

        Args:
            kmodel_path: 模型文件路径
            confidence_threshold: 置信度阈值
            rgb888p_size: 摄像头输入尺寸 [width, height]
            model_input_size: 模型输入尺寸 [width, height]
        """
        self.confidence_threshold = confidence_threshold
        self.rgb888p_size = rgb888p_size or [640, 480]
        self.model_input_size = model_input_size or [320, 320]

        # 筛选车辆标签
        self.labels = [self.COCO_LABELS[i] for i in self.VEHICLE_CLASS_IDS]

        # 创建YOLOv5检测器（K230使用YOLOv5接口）
        self.detector = YOLOv5(
            task_type="detect",
            mode="video",
            kmodel_path=kmodel_path,
            labels=self.labels,
            rgb888p_size=self.rgb888p_size,
            model_input_size=self.model_input_size,
            display_size=[640, 480],
            conf_thresh=confidence_threshold,
            nms_thresh=0.45,
            max_boxes_num=50,
            debug_mode=0
        )

        # 配置预处理
        self.detector.config_preprocess()

        print(f"[车辆检测器] 初始化完成，模型: {kmodel_path}")
        print(f"[车辆检测器] 检测类别: {self.labels}")

    def detect(self, img):
        """
        检测图像中的车辆

        Args:
            img: sensor.snapshot()返回的图像对象

        Returns:
            list: 检测结果列表，每项包含 {'class': class_id, 'label': str,
                   'confidence': float, 'bbox': [x, y, w, h]}
        """
        # 执行推理
        det_res = self.detector.run(self.detector.inputs[0], img)

        # 后处理
        results = self.detector.postprocess(det_res)

        # 解析结果
        vehicles = []
        if results and len(results) >= 3:
            det_boxes = results[0]   # 检测框坐标
            det_classes = results[1]  # 类别ID（0-based in vehicle subset）
            det_scores = results[2]   # 置信度

            if det_boxes and len(det_boxes) > 0:
                for i in range(len(det_boxes)):
                    x, y, w, h = det_boxes[i]
                    class_idx = det_classes[i]  # 0-based索引，对应VEHICLE_CLASS_IDS
                    confidence = det_scores[i]

                    # 获取原始COCO类别ID
                    coco_class_id = self.VEHICLE_CLASS_IDS[class_idx]

                    vehicles.append({
                        'class': coco_class_id,
                        'label': self.VEHICLE_NAMES[coco_class_id],
                        'confidence': float(confidence),
                        'bbox': [int(x), int(y), int(w), int(h)]
                    })

        return vehicles

    def draw_detection(self, img, vehicles):
        """
        在图像上绘制检测结果

        Args:
            img: 图像对象
            vehicles: 检测结果列表
        """
        if vehicles:
            self.detector.draw_result(([v['bbox'] for v in vehicles],
                                       [self.VEHICLE_CLASS_IDS.index(v['class']) for v in vehicles],
                                       [v['confidence'] for v in vehicles]), img)
        else:
            img.clear()