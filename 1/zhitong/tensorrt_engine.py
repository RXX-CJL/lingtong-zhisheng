import os
import numpy as np
import cv2
from config import Config

try:
    import tensorrt as trt
    TENSORRT_AVAILABLE = True
except ImportError:
    TENSORRT_AVAILABLE = False
    print("TensorRT not available, using standard YOLO inference")

try:
    import torch
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

# CUDA 相关导入（可选）
try:
    import cuda
    CUDA_AVAILABLE = True
except ImportError:
    CUDA_AVAILABLE = False

class TensorRTEngine:
    def __init__(self, config: Config):
        self.config = config
        self.engine = None
        self.context = None
        self.inputs = []
        self.outputs = []
        self.bindings = []
        self.stream = None
        self.tensorrt_available = TENSORRT_AVAILABLE and CUDA_AVAILABLE
        self.ultralytics_available = ULTRALYTICS_AVAILABLE
        
        self.logger = trt.Logger(trt.Logger.WARNING) if self.tensorrt_available else None
        
        self.model = None
        if self.ultralytics_available:
            self._load_ultralytics_model()
        
        # 自动尝试加载 TensorRT engine
        self._auto_load_engine()
    
    def _auto_load_engine(self):
        """自动检测并加载 TensorRT engine"""
        if self.ultralytics_available and self.tensorrt_available:
            engine_path = os.path.join(self.config.MODEL_DIR, 'yolov8n.engine')
            if os.path.exists(engine_path):
                success = self.load_tensorrt_engine(engine_path)
                if success:
                    print(f"✓ TensorRT engine loaded: {engine_path}")
                    self.config.USE_TENSORRT = True
                else:
                    print("⚠ TensorRT engine load failed, using PyTorch")
                    self.config.USE_TENSORRT = False
            else:
                print(f"ℹ TensorRT engine not found at {engine_path}, using PyTorch")
                self.config.USE_TENSORRT = False
    
    def _load_ultralytics_model(self):
        model_path = os.path.join(self.config.MODEL_DIR, self.config.YOLO_MODEL)
        if not os.path.exists(model_path):
            model_path = self.config.YOLO_MODEL
        self.model = YOLO(model_path)
        print(f"Loaded YOLO model from {model_path}")
    
    def export_to_tensorrt(self, output_path=None):
        if not self.tensorrt_available or not self.ultralytics_available:
            print("TensorRT export not available")
            return False
        
        if output_path is None:
            output_path = os.path.join(self.config.MODEL_DIR, 'yolov8n.engine')
        
        print(f"Exporting model to TensorRT: {output_path}")
        self.model.export(format='engine', device=0, half=True, imgsz=(640, 640))
        self.config.TENSORRT_ENGINE = output_path
        return True
    
    def load_tensorrt_engine(self, engine_path=None):
        """加载 TensorRT engine"""
        if not self.tensorrt_available:
            print("TensorRT not available, using PyTorch inference")
            return False
        
        if engine_path is None:
            engine_path = self.config.TENSORRT_ENGINE
        
        if engine_path is None or not os.path.exists(engine_path):
            print("TensorRT engine not found, using PyTorch inference")
            return False
        
        try:
            print(f"Loading TensorRT engine: {engine_path}")
            # 使用 ultralytics 的 TRT 模型加载
            self.model = YOLO(engine_path)
            self.config.USE_TENSORRT = True
            print("TensorRT engine loaded successfully")
            return True
        except Exception as e:
            print(f"TensorRT engine load failed: {e}")
            self.config.USE_TENSORRT = False
            return False
    
    def preprocess(self, img):
        img = cv2.resize(img, (640, 640))
        img = img.transpose(2, 0, 1)
        img = img / 255.0
        img = np.expand_dims(img, axis=0).astype(np.float32)
        return img
    
    def postprocess(self, outputs, original_shape):
        return outputs
    
    def infer(self, img):
        if self.config.USE_TENSORRT and self.engine is not None:
            return self._infer_tensorrt(img)
        elif self.model is not None:
            return self._infer_ultralytics(img)
        return []
    
    def _infer_tensorrt(self, img):
        original_shape = img.shape[:2]
        processed = self.preprocess(img)
        
        np.copyto(self.inputs[0]['host'], processed.ravel())
        cuda.memcpy_htod_async(self.inputs[0]['device'], self.inputs[0]['host'], self.stream)
        self.context.execute_async_v2(bindings=self.bindings, stream_handle=self.stream.handle)
        for output in self.outputs:
            cuda.memcpy_dtoh_async(output['host'], output['device'], self.stream)
        self.stream.synchronize()
        
        outputs = [output['host'] for output in self.outputs]
        detections = self.postprocess(outputs, original_shape)
        return detections
    
    def _infer_ultralytics(self, img):
        results = self.model(img, conf=self.config.YOLO_CONF_THRESHOLD, iou=self.config.YOLO_IOU_THRESHOLD)
        boxes = results[0].boxes
        
        detections = []
        if boxes is not None and len(boxes) > 0:
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = results[0].names[class_id]
                
                detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'confidence': confidence,
                    'class_id': class_id,
                    'class_name': class_name
                })
        
        return detections
    
    def get_detections(self, img):
        return self.infer(img)
