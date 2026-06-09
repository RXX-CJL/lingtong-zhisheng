import numpy as np
import cv2
from deep_sort_realtime.deepsort_tracker import DeepSort
from config import Config
from language import Translation

class TrackedObject:
    def __init__(self, track_id, bbox, class_name, confidence):
        self.track_id = track_id
        self.bbox = bbox
        self.class_name = class_name
        self.confidence = confidence
        self.history = [bbox]
        self.frames_since_update = 0
        self.velocity = np.array([0, 0])
    
    def update(self, bbox, class_name, confidence):
        if len(self.history) > 0:
            old_center = np.array([(self.history[-1][0] + self.history[-1][2]) / 2, 
                                   (self.history[-1][1] + self.history[-1][3]) / 2])
            new_center = np.array([(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2])
            self.velocity = new_center - old_center
        self.bbox = bbox
        self.class_name = class_name
        self.confidence = confidence
        self.history.append(bbox)
        if len(self.history) > 30:
            self.history.pop(0)
        self.frames_since_update = 0
    
    def predict_position(self):
        if len(self.history) < 2:
            return self.bbox
        center = np.array([(self.bbox[0] + self.bbox[2]) / 2, 
                           (self.bbox[1] + self.bbox[3]) / 2])
        predicted_center = center + self.velocity
        width = self.bbox[2] - self.bbox[0]
        height = self.bbox[3] - self.bbox[1]
        return [predicted_center[0] - width/2, predicted_center[1] - height/2,
                predicted_center[0] + width/2, predicted_center[1] + height/2]

class DeepSORTTracker:
    def __init__(self, config: Config):
        self.config = config
        self.tracker = DeepSort(
            max_cosine_distance=config.MAX_DIST,
            max_age=config.MAX_AGE,
            n_init=config.N_INIT,
            nms_max_overlap=config.NMS_MAX_OVERLAP,
            nn_budget=config.NN_BUDGET,
            embedder="mobilenet",
            half=True,
            bgr=True,
            embedder_gpu=True,
            polygon=False,
            today=None
        )
        self.tracked_objects = {}
    
    def update(self, frame, detections):
        if not detections:
            for obj in self.tracked_objects.values():
                obj.frames_since_update += 1
            self._cleanup_tracks()
            return list(self.tracked_objects.values())
        
        dets = []
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            bbox = [x1, y1, x2, y2]
            score = det['confidence']
            dets.append((bbox, score, det['class_name']))
        
        tracks = self.tracker.update_tracks(dets, frame=frame)
        
        updated_ids = set()
        for track in tracks:
            if not track.is_confirmed():
                continue
            bbox = track.to_tlbr().astype(int)
            track_id = track.track_id
            class_name = track.get_det_class() if track.get_det_class() else 'unknown'
            
            confidence = detections[0]['confidence'] if detections else 0.5
            
            if track_id in self.tracked_objects:
                self.tracked_objects[track_id].update(bbox, class_name, confidence)
            else:
                self.tracked_objects[track_id] = TrackedObject(track_id, bbox, class_name, confidence)
            updated_ids.add(track_id)
        
        for obj in self.tracked_objects.values():
            if obj.track_id not in updated_ids:
                obj.frames_since_update += 1
        
        self._cleanup_tracks()
        return list(self.tracked_objects.values())
    
    def _cleanup_tracks(self):
        to_remove = []
        for track_id, obj in self.tracked_objects.items():
            if obj.frames_since_update > self.config.MAX_AGE:
                to_remove.append(track_id)
        for track_id in to_remove:
            del self.tracked_objects[track_id]
    
    def get_track(self, track_id):
        return self.tracked_objects.get(track_id)
    
    def draw_tracks(self, frame, tracks):
        for track in tracks:
            x1, y1, x2, y2 = track.bbox
            track_id = track.track_id
            
            color = (0, 255, 0)
            if track.class_name in ['car', 'truck', 'bus']:
                color = (255, 0, 0)
            elif track.class_name == 'person':
                color = (0, 0, 255)
            elif track.class_name in ['bicycle', 'motorcycle']:
                color = (255, 255, 0)
            
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            class_name_cn = Translation.translate_class(track.class_name)
            label = f"ID:{track_id} {class_name_cn} {track.confidence:.2f}"
            cv2.putText(frame, label, (int(x1), int(y1)-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame
