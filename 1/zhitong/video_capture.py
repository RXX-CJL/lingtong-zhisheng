import cv2
import threading
import time

class VideoCapture:
    def __init__(self, config):
        self.config = config
        self.cap = None
        self.running = False
        self.current_frame = None
        self.lock = threading.Lock()
        self.thread = None
    
    def open(self, camera_index=None):
        index = camera_index if camera_index is not None else self.config.CAMERA_INDEX
        self.cap = cv2.VideoCapture(index)
        
        if not self.cap.isOpened():
            return False
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.VIDEO_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.VIDEO_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, self.config.FRAME_RATE)
        
        return True
    
    def open_video_file(self, file_path):
        self.cap = cv2.VideoCapture(file_path)
        return self.cap.isOpened()
    
    def start(self):
        if self.cap is None or not self.cap.isOpened():
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        return True
    
    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.current_frame = frame.copy()
            else:
                time.sleep(0.01)
    
    def get_frame(self):
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
    
    def release(self):
        self.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
    
    @staticmethod
    def list_cameras(max_check=4):
        available = []
        for i in range(max_check):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append(i)
                cap.release()
        return available
