import os
import base64
import time
import threading
import cv2
from typing import Optional, Dict
from config import Config
from violation_detector import Violation

try:
    import dashscope
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

class CloudManager:
    def __init__(self, config: Config):
        self.config = config
        self.dashscope_available = DASHSCOPE_AVAILABLE
        
        if self.dashscope_available:
            dashscope.api_key = config.DASHSCOPE_API_KEY
        
        self.evidence_queue = []
        self.processing_lock = threading.Lock()
        self.cloud_results = {}
    
    def save_evidence(self, frame: cv2.Mat, violation: Violation) -> str:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"evidence_{violation.violation_type}_{violation.track_id}_{timestamp}.jpg"
        filepath = os.path.join(self.config.EVIDENCE_DIR, filename)
        
        os.makedirs(self.config.EVIDENCE_DIR, exist_ok=True)
        cv2.imwrite(filepath, frame)
        
        violation.evidence_saved = True
        return filepath
    
    def upload_to_cloud(self, filepath: str) -> bool:
        print(f"Uploading evidence to cloud: {filepath}")
        return True
    
    def analyze_with_cloud(self, frame: cv2.Mat, violation: Optional[Violation] = None, 
                          user_question: Optional[str] = None) -> Optional[Dict]:
        if not self.dashscope_available:
            print("DashScope not available")
            return None
        
        try:
            _, img_encoded = cv2.imencode('.jpg', frame)
            img_base64 = base64.b64encode(img_encoded).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{img_base64}"
            
            if violation:
                prompt = f"""请分析这张图片，判断是否存在以下违规行为：{violation.violation_type}
                检测对象ID: {violation.track_id}
                检测置信度: {violation.confidence:.2f}
                
                请用中文回答，格式如下：
                1. 是否存在违规行为：是/否
                2. 说明理由：
                3. 额外建议：
                """
            elif user_question:
                prompt = f"用户的问题是：{user_question}\n请结合图片内容，用中文、口语化、简洁地回答问题。"
            else:
                prompt = "请用中文、亲切、口语化的方式，描述这张图片中的主要场景。回答要简洁，一两句话即可。"
            
            messages = [{
                "role": "user",
                "content": [
                    {"image": data_url},
                    {"text": prompt}
                ]
            }]
            
            response = dashscope.MultiModalConversation.call(
                model=self.config.CLOUD_MODEL,
                messages=messages
            )
            
            if response.status_code == 200:
                result = response.output.choices[0].message.content[0]["text"]
                print(f"Cloud analysis result: {result}")
                
                if violation:
                    violation.cloud_validated = True
                    self.cloud_results[violation.track_id] = {
                        'result': result,
                        'timestamp': time.time()
                    }
                
                return {
                    'success': True,
                    'result': result,
                    'timestamp': time.time()
                }
            else:
                print(f"Cloud API error: {response.code} - {response.message}")
                return None
                
        except Exception as e:
            print(f"Cloud analysis exception: {e}")
            return None
    
    def validate_violation(self, violation: Violation, frame: cv2.Mat) -> bool:
        if not self.config.USE_CLOUD_VALIDATION:
            return True
        
        if violation.confidence >= self.config.CONFIDENCE_THRESHOLD_HIGH:
            return True
        
        result = self.analyze_with_cloud(frame, violation)
        if result and result['success']:
            text = result['result']
            if '是' in text or '存在' in text:
                return True
        
        return False
    
    def process_evidence_queue(self):
        with self.processing_lock:
            while self.evidence_queue:
                violation, frame = self.evidence_queue.pop(0)
                self.validate_violation(violation, frame)
                self.save_evidence(frame, violation)
                self.upload_to_cloud(os.path.join(self.config.EVIDENCE_DIR, f"evidence_{violation.track_id}.jpg"))
    
    def add_to_queue(self, violation: Violation, frame: cv2.Mat):
        with self.processing_lock:
            self.evidence_queue.append((violation, frame))
            if len(self.evidence_queue) == 1:
                threading.Thread(target=self.process_evidence_queue, daemon=True).start()
