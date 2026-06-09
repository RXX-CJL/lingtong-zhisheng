import os
import sys
import time
import requests
from datetime import datetime
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class APITestResult:
    def __init__(self, test_name, success, message, response_time=0):
        self.test_name = test_name
        self.success = success
        self.message = message
        self.response_time = response_time
    
    def __str__(self):
        status = "[OK]" if self.success else "[FAIL]"
        return f"{status} {self.test_name}: {self.message} ({self.response_time:.2f}s)"

class CloudAPITester:
    def __init__(self):
        self.results = []
    
    def add_result(self, test_name, success, message, response_time=0):
        result = APITestResult(test_name, success, message, response_time)
        self.results.append(result)
        print(result)
    
    def test_internet_connection(self):
        start_time = time.time()
        try:
            response = requests.get("https://www.baidu.com", timeout=5)
            response_time = time.time() - start_time
            if response.status_code == 200:
                self.add_result("网络连接测试", True, "网络连接正常", response_time)
                return True
            else:
                self.add_result("网络连接测试", False, f"HTTP状态码: {response.status_code}", response_time)
                return False
        except Exception as e:
            response_time = time.time() - start_time
            self.add_result("网络连接测试", False, str(e), response_time)
            return False
    
    def test_dashscope_api(self):
        start_time = time.time()
        try:
            import dashscope
            from dashscope import Generation
            
            from config import Config
            config = Config()
            dashscope.api_key = config.DASHSCOPE_API_KEY
            
            response = Generation.call(
                model="qwen-turbo",
                prompt="Hello, this is a test."
            )
            
            response_time = time.time() - start_time
            if response.status_code == 200:
                self.add_result("DashScope API测试", True, "API调用成功", response_time)
                return True
            else:
                self.add_result("DashScope API测试", False, f"错误码: {response.code}, 消息: {response.message}", response_time)
                return False
        except ImportError as e:
            self.add_result("DashScope API测试", False, f"dashscope库未安装或版本不兼容: {e}")
            return False
        except Exception as e:
            response_time = time.time() - start_time
            self.add_result("DashScope API测试", False, str(e), response_time)
            return False
    
    def test_video_download(self):
        start_time = time.time()
        try:
            test_url = "https://www.w3schools.com/html/mov_bbb.mp4"
            response = requests.get(test_url, stream=True, timeout=30)
            
            if response.status_code == 200:
                content_length = int(response.headers.get('content-length', 0))
                if content_length > 0:
                    response_time = time.time() - start_time
                    self.add_result("视频下载测试", True, f"成功获取视频，大小: {content_length/1024:.2f} KB", response_time)
                    return True
                else:
                    self.add_result("视频下载测试", False, "视频内容为空")
                    return False
            else:
                response_time = time.time() - start_time
                self.add_result("视频下载测试", False, f"HTTP状态码: {response.status_code}", response_time)
                return False
        except Exception as e:
            response_time = time.time() - start_time
            self.add_result("视频下载测试", False, str(e), response_time)
            return False
    
    def test_multimodal_api(self):
        start_time = time.time()
        try:
            import dashscope
            import cv2
            import base64
            
            from config import Config
            config = Config()
            dashscope.api_key = config.DASHSCOPE_API_KEY
            
            test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
            _, img_encoded = cv2.imencode('.jpg', test_frame)
            img_base64 = base64.b64encode(img_encoded).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{img_base64}"
            
            messages = [{
                "role": "user",
                "content": [
                    {"image": data_url},
                    {"text": "请描述这张图片"}
                ]
            }]
            
            response = dashscope.MultiModalConversation.call(
                model="qwen3-vl-flash",
                messages=messages
            )
            
            response_time = time.time() - start_time
            if response.status_code == 200:
                result = response.output.choices[0].message.content[0]["text"]
                self.add_result("多模态API测试", True, f"成功，响应长度: {len(result)}字符", response_time)
                return True
            else:
                self.add_result("多模态API测试", False, f"错误码: {response.code}, 消息: {response.message}", response_time)
                return False
        except ImportError as e:
            self.add_result("多模态API测试", False, f"缺少依赖: {e}")
            return False
        except Exception as e:
            response_time = time.time() - start_time
            self.add_result("多模态API测试", False, str(e), response_time)
            return False
    
    def test_tts_api(self):
        start_time = time.time()
        try:
            import dashscope
            from dashscope.audio.tts import SpeechSynthesizer
            
            from config import Config
            config = Config()
            dashscope.api_key = config.DASHSCOPE_API_KEY
            
            response = SpeechSynthesizer.call(
                model='sambert-zhichu-v1',
                text='这是一个测试',
                voice='longxiaoni',
                format='wav',
                sample_rate=16000
            )
            
            response_time = time.time() - start_time
            audio_data = response.get_audio_data()
            if audio_data is not None and len(audio_data) > 0:
                audio_length = len(audio_data)
                self.add_result("TTS语音合成测试", True, f"成功，音频大小: {audio_length}字节", response_time)
                return True
            else:
                self.add_result("TTS语音合成测试", False, "音频数据为空", response_time)
                return False
        except ImportError as e:
            self.add_result("TTS语音合成测试", False, f"dashscope库未安装或版本不兼容: {e}")
            return False
        except Exception as e:
            response_time = time.time() - start_time
            self.add_result("TTS语音合成测试", False, str(e), response_time)
            return False
    
    def run_all_tests(self):
        print("=" * 60)
        print("阿里云API全面测试报告")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()
        
        self.test_internet_connection()
        self.test_dashscope_api()
        self.test_tts_api()
        self.test_video_download()
        
        print()
        print("=" * 60)
        print("测试总结")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r.success)
        total = len(self.results)
        success_rate = (passed / total) * 100
        
        print(f"通过: {passed}/{total} ({success_rate:.1f}%)")
        print()
        
        for result in self.results:
            status = "[通过]" if result.success else "[失败]"
            print(f"  {status} - {result.test_name}")
        
        return passed == total

if __name__ == "__main__":
    tester = CloudAPITester()
    tester.run_all_tests()