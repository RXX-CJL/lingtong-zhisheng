import cv2
import numpy as np
from ultralytics import YOLO
import os

class YoloDetector:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.class_names = []
        self.load_model()
    
    def load_model(self):
        model_path = os.path.join(self.config.MODEL_DIR, self.config.YOLO_MODEL)
        
        if os.path.exists(model_path):
            self.model = YOLO(model_path)
        else:
            self.model = YOLO(self.config.YOLO_MODEL)
            self.model.save(model_path)
        
        self.class_names = self.model.names
    
    def detect(self, frame):
        if self.model is None:
            return []
        
        results = self.model(frame, conf=self.config.YOLO_CONF_THRESHOLD, iou=self.config.YOLO_IOU_THRESHOLD)
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = box.conf[0].cpu().numpy()
                cls = int(box.cls[0].cpu().numpy())
                class_name = self.class_names[cls]
                
                detections.append({
                    'bbox': (x1, y1, x2, y2),
                    'confidence': float(conf),
                    'class_id': cls,
                    'class_name': class_name
                })
        
        return detections
    
    def draw_detections(self, frame, detections):
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            class_name = det['class_name']
            conf = det['confidence']
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{class_name}: {conf:.2f}"
            cv2.putText(frame, label, (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame
