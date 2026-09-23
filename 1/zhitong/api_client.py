import os
import base64
import time
import queue
import threading
import cv2
import requests
from datetime import datetime
from typing import Optional, Dict
from config import Config

class APIClient:
    def __init__(self, config: Config):
        self.config = config
        self.submit_url = config.API_BASE_URL + config.API_SUBMIT_ENDPOINT
        self.timeout = config.API_TIMEOUT
        self.retry_times = config.API_RETRY_TIMES
        self.enable_upload = config.ENABLE_API_UPLOAD
        
        self.upload_queue = queue.Queue()
        self.worker_thread = None
        self.stop_flag = threading.Event()
        
        if self.enable_upload:
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
    
    def _worker(self):
        while not self.stop_flag.is_set():
            try:
                item = self.upload_queue.get(timeout=0.5)
                if item is None:
                    break
                violation_obj, frame_image = item
                self._do_submit(violation_obj, frame_image)
                self.upload_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self._log_error(f"Worker error: {e}")
    
    def _do_submit(self, violation_obj, frame_image):
        try:
            _, img_encoded = cv2.imencode('.jpg', frame_image)
            img_base64 = base64.b64encode(img_encoded).decode('utf-8')
            
            position = violation_obj.position
            timestamp_str = datetime.fromtimestamp(violation_obj.timestamp).isoformat()
            
            payload = {
                'violation_type': violation_obj.violation_type,
                'track_id': violation_obj.track_id,
                'confidence': float(violation_obj.confidence),
                'position': {
                    'x': int(position[0]),
                    'y': int(position[1]),
                    'w': int(position[2]),
                    'h': int(position[3])
                },
                'timestamp': timestamp_str,
                'image_data': img_base64,
                'additional_info': violation_obj.additional_info or {}
            }
            
            for attempt in range(self.retry_times + 1):
                try:
                    response = requests.post(
                        self.submit_url,
                        json=payload,
                        timeout=self.timeout
                    )
                    if response.status_code == 200:
                        print(f"[API] 违规提交成功: type={violation_obj.violation_type}, track_id={violation_obj.track_id}")
                        return
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        if attempt == self.retry_times:
                            self._log_error(error_msg, violation_obj)
                            return
                except requests.exceptions.Timeout:
                    if attempt == self.retry_times:
                        self._log_error(f"Timeout after {self.retry_times + 1} attempts", violation_obj)
                        return
                except requests.exceptions.RequestException as e:
                    if attempt == self.retry_times:
                        self._log_error(f"Request error: {e}", violation_obj)
                        return
                
                if attempt < self.retry_times:
                    time.sleep(1)
                    
        except Exception as e:
            self._log_error(f"Submit error: {e}")
    
    def _log_error(self, error_msg: str, violation_obj=None):
        log_dir = self.config.LOG_DIR
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'api_upload_error.log')
        
        log_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}"
        if violation_obj:
            log_entry += f" | violation_type={violation_obj.violation_type}, track_id={violation_obj.track_id}"
        log_entry += "\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def submit_violation(self, violation_obj, frame_image):
        if not self.enable_upload:
            return
        
        self.upload_queue.put((violation_obj, frame_image))
    
    def stop(self):
        self.stop_flag.set()
        self.upload_queue.put(None)
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2)
