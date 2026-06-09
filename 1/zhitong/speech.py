import subprocess
import threading
import requests
import base64
import wave
import pyaudio
import io

class SpeechManager:
    def __init__(self, config):
        self.config = config
        self.enabled = config.SPEAK_ENABLED
    
    def speak_windows(self, text):
        if not self.enabled:
            return
        
        safe_text = text.replace("'", "''")
        cmd = f'powershell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{safe_text}\')"'
        
        def run():
            subprocess.run(cmd, shell=True, capture_output=True)
        
        threading.Thread(target=run, daemon=True).start()
    
    def speak_dashscope(self, text):
        if not self.enabled:
            return
        
        if not text or len(text.strip()) == 0:
            return
        
        try:
            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
            headers = {
                "Authorization": f"Bearer {self.config.DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.config.TTS_MODEL,
                "input": {
                    "text": text,
                    "voice": self.config.TTS_VOICE,
                    "language_type": "Chinese"
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code != 200:
                self.speak_windows(text)
                return
            
            result = response.json()
            if 'output' not in result or 'audio' not in result['output'] or 'url' not in result['output']['audio']:
                self.speak_windows(text)
                return
            
            audio_url = result['output']['audio']['url']
            audio_response = requests.get(audio_url, timeout=30)
            if audio_response.status_code != 200:
                self.speak_windows(text)
                return
            
            self.play_audio_stream(audio_response.content)
            
        except Exception as e:
            print(f"TTS异常: {e}")
            self.speak_windows(text)
    
    def play_audio_stream(self, audio_data):
        try:
            with io.BytesIO(audio_data) as audio_io:
                with wave.open(audio_io, 'rb') as wf:
                    p = pyaudio.PyAudio()
                    stream = p.open(
                        format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True
                    )
                    
                    chunk_size = 1024
                    data = wf.readframes(chunk_size)
                    while data:
                        stream.write(data)
                        data = wf.readframes(chunk_size)
                    
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
        except Exception as e:
            print(f"播放异常: {e}")
    
    def speak(self, text):
        if not self.enabled:
            return
        
        threading.Thread(target=self.speak_dashscope, args=(text,), daemon=True).start()
    
    def announce_violation(self, violation):
        violation_names = {
            'red_light': '闯红灯',
            'no_helmet': '未戴头盔',
            'retrograde': '逆行',
            'parking': '违停'
        }
        
        vio_type = violation.get('type', 'unknown')
        vio_name = violation_names.get(vio_type, vio_type)
        confidence = violation.get('confidence', 0)
        
        message = f"检测到{vio_name}行为，置信度{int(confidence * 100)}%"
        print(f"[语音播报] {message}")
        self.speak(message)
