import os
import threading
import time
from typing import Optional
import winsound

class SpeechManager:
    def __init__(self, config):
        self.config = config
        self.enabled = config.ENABLE_SPEECH
        self.tts_engine = config.TTS_ENGINE
        self.speaking = False
        self.lock = threading.Lock()
        
        self.warning_levels = {
            1: {'name': '轻度提示', 'volume': 0.8, 'speed': 1.0},
            2: {'name': '正式警告', 'volume': 1.0, 'speed': 0.9},
            3: {'name': '严厉警告', 'volume': 1.2, 'speed': 0.8}
        }
    
    def speak(self, text: str, volume: float = 1.0, speed: float = 1.0):
        if not self.enabled:
            return
        
        thread = threading.Thread(target=self._speak_thread, args=(text, volume, speed))
        thread.daemon = True
        thread.start()
    
    def _speak_thread(self, text: str, volume: float, speed: float):
        with self.lock:
            if self.speaking:
                return
            self.speaking = True
        
        try:
            if self.tts_engine == 'dashscope':
                self._speak_dashscope(text, volume, speed)
            else:
                self._speak_windows(text, volume)
        except Exception as e:
            print(f"Speech error: {e}")
            self._speak_windows(text, volume)
        finally:
            self.speaking = False
    
    def _speak_dashscope(self, text: str, volume: float, speed: float):
        try:
            import dashscope
            from dashscope.audio.tts import SpeechSynthesizer
            
            dashscope.api_key = self.config.DASHSCOPE_API_KEY
            
            response = SpeechSynthesizer.call(
                model='sambert-zhichu-v1',
                text=text,
                voice='longxiaoni',
                format='wav',
                sample_rate=16000
            )
            
            audio_data = response.get_audio_data()
            if audio_data and len(audio_data) > 0:
                temp_file = os.path.join(self.config.OUTPUT_DIR, 'temp_audio.wav')
                
                with open(temp_file, 'wb') as f:
                    f.write(audio_data)
                
                self._play_audio(temp_file, volume)
                
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        except Exception as e:
            print(f"DashScope TTS failed: {e}")
            raise
    
    def _speak_windows(self, text: str, volume: float):
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            
            voices = speaker.GetVoices()
            for voice in voices:
                if 'Chinese' in voice.GetDescription():
                    speaker.Voice = voice
                    break
            
            speaker.Rate = int((self.config.TTS_SPEED - 1.0) * 10)
            
            volume_level = min(int(volume * 100), 100)
            speaker.Volume = volume_level
            
            speaker.Speak(text)
        except Exception as e:
            print(f"Windows TTS failed: {e}")
            self._play_beep()
    
    def _play_audio(self, file_path: str, volume: float):
        try:
            winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            duration = self._estimate_duration(file_path)
            time.sleep(duration * volume)
        except Exception as e:
            print(f"Audio playback failed: {e}")
            self._play_beep()
    
    def _estimate_duration(self, file_path: str) -> float:
        try:
            import wave
            with wave.open(file_path, 'r') as f:
                frames = f.getnframes()
                rate = f.getframerate()
                return frames / float(rate)
        except:
            return 3.0
    
    def _play_beep(self):
        try:
            winsound.Beep(1000, 500)
        except:
            pass
    
    def announce_warning(self, level: int, message: str, correction_guide: Optional[str] = None):
        config = self.warning_levels.get(level, self.warning_levels[1])
        volume = config['volume']
        speed = config['speed']
        
        self.speak(message, volume=volume, speed=speed)
        
        if correction_guide and level >= 3:
            time.sleep(1)
            self.speak(correction_guide, volume=volume * 0.9, speed=speed)
    
    def greet(self):
        self.speak('欢迎使用智瞳灵声智慧交管系统，系统已启动')
    
    def goodbye(self):
        self.speak('系统即将关闭，感谢使用')
