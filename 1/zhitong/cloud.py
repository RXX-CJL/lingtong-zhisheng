import dashscope
import base64
import cv2
import os
import time

class CloudManager:
    def __init__(self, config):
        self.config = config
        dashscope.api_key = config.DASHSCOPE_API_KEY
    
    def analyze_image(self, frame, prompt=None):
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            _, img_encoded = cv2.imencode('.jpg', frame_rgb)
            img_base64 = base64.b64encode(img_encoded).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{img_base64}"
            
            if prompt:
                text_prompt = f"用户的问题是：{prompt}\n请结合图片内容，用中文、口语化、简洁地回答问题。"
            else:
                text_prompt = "请用中文、亲切、口语化的方式，描述这张图片中的主要场景。回答要简洁，一两句话即可。"
            
            messages = [{
                "role": "user",
                "content": [
                    {"image": data_url},
                    {"text": text_prompt}
                ]
            }]
            
            response = dashscope.MultiModalConversation.call(
                model=self.config.CLOUD_MODEL,
                messages=messages
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content[0]["text"]
            else:
                print(f"云端API错误: {response.code} - {response.message}")
                return ""
        except Exception as e:
            print(f"云端分析异常: {e}")
            return ""
    
    def confirm_violation(self, frame, violation_type):
        descriptions = {
            'red_light': '请判断图片中的车辆是否正在闯红灯',
            'no_helmet': '请判断图片中的骑乘人员是否佩戴头盔',
            'retrograde': '请判断图片中的车辆是否在逆行',
            'parking': '请判断图片中的车辆是否属于违停'
        }
        
        prompt = descriptions.get(violation_type, '请分析图片内容')
        result = self.analyze_image(frame, prompt)
        
        if '是' in result or '存在' in result or '违规' in result:
            return True, result
        return False, result
    
    def save_evidence(self, frame, violation, output_dir=None):
        if output_dir is None:
            output_dir = self.config.EVIDENCE_DIR
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        vio_type = violation.get('type', 'unknown')
        track_id = violation.get('track_id', 'unknown')
        
        filename = f"vio_{vio_type}_{track_id}_{timestamp}.jpg"
        filepath = os.path.join(output_dir, filename)
        
        cv2.imwrite(filepath, frame)
        return filepath
    
    def upload_to_cloud(self, file_path):
        try:
            print(f"正在上传证据: {file_path}")
            return True
        except Exception as e:
            print(f"上传失败: {e}")
            return False
