import os
import time
import json

class Logger:
    def __init__(self, config):
        self.config = config
        self.log_file = os.path.join(config.LOG_DIR, f"log_{time.strftime('%Y%m%d')}.txt")
    
    def log(self, message, level='INFO'):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        print(log_entry.strip())
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def log_violation(self, violation, frame_path=None):
        log_data = {
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'type': violation.get('type'),
            'track_id': violation.get('track_id'),
            'bbox': violation.get('bbox'),
            'confidence': violation.get('confidence'),
            'evidence_path': frame_path
        }
        
        self.log(f"违规检测: {json.dumps(log_data, ensure_ascii=False)}", level='WARNING')
    
    def log_system(self, message):
        self.log(f"系统: {message}", level='INFO')
    
    def log_error(self, message):
        self.log(f"错误: {message}", level='ERROR')
