"""
瞳声-基于端云协同的轻量化智能识别系统
整合功能：
- 空格键：本地 YOLO 快速播报
- C 键：云端 AI 描述画面（带语音合成，非机械音）
- V 键（按住说话）：录制语音问题，结合画面进行对话问答
- Q 键：退出
- CARLA 模式：WASD 控制行人移动

改进点：
- 使用 DashScope TTS (qwen3-tts-flash) 替代 Windows 机械语音
- 使用 DashScope ASR (paraformer-realtime-v2) 替代 Google Speech Recognition
- 流式播放音频，无需保存文件
"""

import cv2
import time
import threading
import subprocess
import base64
import keyboard
import os
import tempfile
import math
from ultralytics import YOLO
import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
import requests
import io
import wave
import pyaudio
import numpy as np

# ========== 1. 配置 ==========
dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', '')
dashscope.base_websocket_api_url = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'
CLOUD_MODEL = "qwen3-vl-flash"
TTS_MODEL = "qwen3-tts-flash"
TTS_VOICE = "Cherry"
ASR_MODEL = "paraformer-realtime-v2"

# CARLA 移动参数
WALKER_SPEED = 2.0  # 行人移动速度 (m/s)
TURN_SPEED = 90.0   # 转向速度 (度/秒)

model = YOLO('./yolov8n.pt')

# ========== 2. 语音合成（DashScope TTS 替代 Windows 机械音）==========
def synthesize_and_play(text, voice=TTS_VOICE):
    """
    调用 DashScope TTS 合成语音并直接播放
    使用流式播放，无需保存文件
    """
    if not text or len(text.strip()) == 0:
        print("TTS: 空文本，跳过")
        return False
    
    print(f"TTS合成: {text[:50]}...")
    
    try:
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        headers = {
            "Authorization": f"Bearer {dashscope.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": TTS_MODEL,
            "input": {
                "text": text,
                "voice": voice,
                "language_type": "Chinese"
            }
        }
        
        # 请求TTS
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code != 200:
            print(f"TTS请求失败: {response.status_code}")
            speak_windows(text)
            return False
        
        result = response.json()
        if 'output' not in result or 'audio' not in result['output'] or 'url' not in result['output']['audio']:
            print("TTS响应格式错误")
            speak_windows(text)
            return False
        
        audio_url = result['output']['audio']['url']
        print(f"获取音频URL: {audio_url[:60]}...")
        
        # 下载音频数据
        audio_response = requests.get(audio_url, timeout=30)
        if audio_response.status_code != 200:
            print("音频下载失败")
            speak_windows(text)
            return False
        
        audio_data = audio_response.content
        print(f"音频大小: {len(audio_data)} 字节，开始播放...")
        
        # 流式播放（不保存文件）
        play_audio_stream(audio_data)
        return True
        
    except Exception as e:
        print(f"TTS异常: {e}")
        speak_windows(text)
        return False

def play_audio_stream(audio_data):
    """
    从内存中流式播放WAV音频
    """
    try:
        with io.BytesIO(audio_data) as audio_io:
            with wave.open(audio_io, 'rb') as wf:
                nchannels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                nframes = wf.getnframes()
                
                print(f"音频参数: {nchannels}声道, {sampwidth*8}bit, {framerate}Hz, {nframes}帧")
                
                p = pyaudio.PyAudio()
                stream = p.open(
                    format=p.get_format_from_width(sampwidth),
                    channels=nchannels,
                    rate=framerate,
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
                print("播放完成")
                
    except Exception as e:
        print(f"播放异常: {e}")

def speak_windows(text):
    """
    备用：Windows PowerShell TTS（机械音）
    当 DashScope TTS 失败时使用
    """
    print(f"[备用TTS] {text}")
    safe_text = text.replace("'", "''")
    cmd = f'powershell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{safe_text}\')"'
    def run():
        subprocess.run(cmd, shell=True, capture_output=True)
    threading.Thread(target=run, daemon=True).start()

def speak(text):
    """
    主语音播报函数
    优先使用 DashScope TTS，失败时自动降级到 Windows TTS
    """
    threading.Thread(target=synthesize_and_play, args=(text,), daemon=True).start()

# ========== 3. 云端单次分析（不带问题）==========
def analyze_with_cloud(frame, user_question=None):
    """
    分析图像，可选额外的问题。
    user_question: 用户语音转文字后的问题
    返回: AI 回答文本
    """
    try:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        _, img_encoded = cv2.imencode('.jpg', frame_rgb)
        img_base64 = base64.b64encode(img_encoded).decode('utf-8')
        data_url = f"data:image/jpeg;base64,{img_base64}"

        if user_question:
            text_prompt = f"用户的问题是：{user_question}\n请结合图片内容，用中文、口语化、简洁地回答问题。"
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
            model=CLOUD_MODEL,
            messages=messages
        )

        if response.status_code == 200:
            return response.output.choices[0].message.content[0]["text"]
        else:
            print(f"API 错误: {response.code} - {response.message}")
            return ""
    except Exception as e:
        print(f"云端异常: {e}")
        return ""

# ========== 4. 语音识别（DashScope ASR 替代 Google SR）==========
def aliyun_asr(wav_file_path):
    """
    使用 DashScope paraformer-realtime-v2 识别 WAV 文件
    输入: WAV 文件路径（16kHz, 16bit, 单声道）
    输出: 识别出的中文字符串，失败返回空字符串
    """
    recognized_text = ""
    recognition_done = threading.Event()

    class ASRCallback(RecognitionCallback):
        def on_open(self):
            print("[ASR] 连接建立")

        def on_close(self):
            print("[ASR] 连接关闭")

        def on_complete(self):
            print("[ASR] 识别完成")
            recognition_done.set()

        def on_error(self, message):
            print(f"[ASR] 错误: {message}")
            recognition_done.set()

        def on_event(self, result: RecognitionResult):
            nonlocal recognized_text
            sentence = result.get_sentence()
            if sentence and 'text' in sentence:
                recognized_text = sentence['text']
                if RecognitionResult.is_sentence_end(sentence):
                    print(f"[ASR] 最终结果: {recognized_text}")

    try:
        callback = ASRCallback()
        recognition = Recognition(
            model=ASR_MODEL,
            format='wav',
            sample_rate=16000,
            callback=callback
        )

        recognition.start()

        # 读取WAV文件并分帧发送
        with open(wav_file_path, 'rb') as f:
            # 跳过WAV头部（44字节），只发送PCM数据
            f.seek(0, 2)
            file_size = f.tell()
            f.seek(44)  # 跳过标准WAV头

            send_frame_length = 3200  # 每帧约100ms
            while f.tell() < file_size:
                chunk = f.read(send_frame_length)
                if len(chunk) == 0:
                    break
                recognition.send_audio_frame(chunk)
                time.sleep(0.05)  # 模拟实时发送

        recognition.stop()

        # 等待识别完成（最多5秒）
        if not recognition_done.wait(timeout=5):
            print("[ASR] 等待超时")

    except Exception as e:
        print(f"[ASR] 异常: {e}")

    # 清理文本
    recognized_text = recognized_text.strip()
    if recognized_text:
        print(f"[ASR] 识别结果: {recognized_text}")
    return recognized_text


def record_and_recognize():
    """
    录制音频（按住V键录音，松开停止），保存为临时WAV文件，
    然后调用 DashScope ASR 识别，返回识别文字。
    录音参数: 16kHz, 单声道, 16bit, WAV格式
    """
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1024
    MAX_RECORD_SECONDS = 5

    frames = []
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                    input=True, frames_per_buffer=CHUNK)

    print("[录音] 请按住 V 键说话，松开停止...")

    # 等待V键按下开始录音
    while not keyboard.is_pressed('v'):
        time.sleep(0.05)

    print("[录音] 开始录音...")
    recording = True
    start_time = time.time()

    while recording:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        except Exception as e:
            print(f"[录音] 读取错误: {e}")
            break

        # 松开V键或超过最大时长则停止
        if not keyboard.is_pressed('v'):
            recording = False
        if time.time() - start_time > MAX_RECORD_SECONDS:
            print("[录音] 达到最大时长")
            recording = False

    print("[录音] 停止录音")
    stream.stop_stream()
    stream.close()
    p.terminate()

    if len(frames) == 0:
        print("[录音] 未录到音频")
        return ""

    # 保存为临时WAV文件
    temp_wav = None
    try:
        fd, temp_wav = tempfile.mkstemp(suffix='.wav')
        os.close(fd)

        with wave.open(temp_wav, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))

        duration = len(frames) * CHUNK / RATE
        print(f"[录音] 保存成功: {temp_wav} ({duration:.1f}秒)")

        # 调用阿里云ASR
        text = aliyun_asr(temp_wav)
        return text

    except Exception as e:
        print(f"[录音] 保存失败: {e}")
        return ""
    finally:
        # 清理临时文件
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except:
                pass

# ========== 5. CARLA 仿真支持 ==========
carla_frame = None
carla_actors = []
walker_actor = None
carla_module = None

def carla_camera_callback(image):
    global carla_frame
    array = np.frombuffer(image.raw_data, dtype=np.uint8)
    array = np.reshape(array, (image.height, image.width, 4))
    carla_frame = array[:, :, :3][:, :, ::-1]  # RGBA -> BGR

def init_carla():
    global carla_frame, carla_actors, walker_actor, carla_module
    try:
        import carla
        carla_module = carla
        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)
        world = client.get_world()
        bp_lib = world.get_blueprint_library()
        
        # 创建行人（遍历生成点，跳过碰撞位置）
        walker_bp = bp_lib.filter('walker.pedestrian.*')[0]
        spawn_points = world.get_map().get_spawn_points()
        walker = None
        for sp in spawn_points:
            try:
                sp_loc = carla.Location(sp.location.x, sp.location.y, sp.location.z + 1.0)
                walker = world.try_spawn_actor(walker_bp, carla.Transform(sp_loc))
                if walker is not None:
                    break
            except:
                continue
        if walker is None:
            print("CARLA: no valid spawn point found")
            return False
        walker_actor = walker
        
        # 创建摄像头（附加到行人）
        camera_bp = bp_lib.find('sensor.camera.rgb')
        camera_bp.set_attribute('image_size_x', '640')
        camera_bp.set_attribute('image_size_y', '480')
        camera_bp.set_attribute('fov', '90')
        camera_transform = carla.Transform(carla.Location(x=0.5, z=1.7))
        camera = world.spawn_actor(camera_bp, camera_transform, attach_to=walker)
        camera.listen(carla_camera_callback)
        
        carla_actors = [camera, walker]
        print("CARLA init OK")
        print("WASD: W=forward, S=back, A=left, D=right")
        return True
    except ImportError:
        print("CARLA module not found, pip install carla")
        return False
    except Exception as e:
        print(f"CARLA init failed: {e}")
        return False

def cleanup_carla():
    global carla_actors, walker_actor
    for actor in carla_actors:
        if actor is not None:
            try:
                if hasattr(actor, 'stop'):
                    actor.stop()
                actor.destroy()
            except:
                pass
    carla_actors = []
    walker_actor = None
    print("CARLA cleanup done")

def update_walker_control(dt):
    """根据 WASD 按键状态更新行人移动"""
    global walker_actor, carla_module
    if walker_actor is None or carla_module is None:
        return
    
    move_forward = keyboard.is_pressed('w')
    move_backward = keyboard.is_pressed('s')
    turn_left = keyboard.is_pressed('a')
    turn_right = keyboard.is_pressed('d')
    
    if not (move_forward or move_backward or turn_left or turn_right):
        walker_actor.apply_control(carla_module.WalkerControl())
        return
    
    transform = walker_actor.get_transform()
    rotation = transform.rotation
    yaw = rotation.yaw
    
    if turn_left:
        yaw -= TURN_SPEED * dt
    if turn_right:
        yaw += TURN_SPEED * dt
    
    yaw_rad = math.radians(yaw)
    
    speed = 0.0
    if move_forward:
        speed = WALKER_SPEED
    elif move_backward:
        speed = -WALKER_SPEED * 0.5
    
    direction = carla_module.Vector3D(
        x=math.cos(yaw_rad),
        y=math.sin(yaw_rad),
        z=0.0
    )
    
    control = carla_module.WalkerControl()
    control.direction = direction
    control.speed = speed
    
    new_rotation = carla_module.Rotation(pitch=rotation.pitch, yaw=yaw, roll=rotation.roll)
    new_transform = carla_module.Transform(transform.location, new_rotation)
    walker_actor.set_transform(new_transform)
    walker_actor.apply_control(control)

# ========== 6. 全局状态 ==========
last_local_objects = []
current_frame = None
is_listening = False

# ========== 7. 按键回调 ==========
def on_space():
    """空格键：本地 YOLO 快速播报"""
    global last_local_objects
    if last_local_objects:
        zh_map = {
            'person': '行人', 'car': '汽车', 'traffic light': '红绿灯',
            'bicycle': '自行车', 'truck': '卡车', 'bus': '公交车',
            'motorcycle': '摩托车', 'dog': '狗', 'cat': '猫',
            'chair': '椅子', 'table': '桌子', 'bottle': '瓶子'
        }
        zh_objs = [zh_map.get(o, o) for o in last_local_objects if o in zh_map or len(o) < 10]
        msg = "前方有" + "、".join(zh_objs[:5]) if zh_objs else "未检测到明显物体"
    else:
        msg = "未检测到明显物体"
    speak(msg)
    print(f"[本地] {msg}")

def on_cloud_describe():
    """C 键：云端描述画面"""
    global current_frame
    if current_frame is None:
        speak("没有图像")
        return
    print("[云端] 正在请求画面描述...")
    def worker():
        desc = analyze_with_cloud(current_frame)
        if desc:
            speak(desc)
            print(f"[云端] {desc}")
        else:
            speak("描述失败")
    threading.Thread(target=worker, daemon=True).start()

def on_voice_query():
    """V 键：按住说话，与 AI 对话（使用 DashScope ASR）"""
    global is_listening, current_frame
    if is_listening:
        return
    if current_frame is None:
        speak("请先确保摄像头有画面")
        return
    is_listening = True

    def worker():
        # 录音并识别（在子线程中，因为需要等待按键）
        question = record_and_recognize()

        if question:
            speak("正在思考...")
            print(f"[问题] {question}")
            answer = analyze_with_cloud(current_frame, user_question=question)
            if answer:
                speak(answer)
                print(f"[回答] {answer}")
            else:
                speak("抱歉，我没能理解")
        else:
            speak("没有听到问题")

        global is_listening
        is_listening = False

    threading.Thread(target=worker, daemon=True).start()

def on_q():
    print("退出")
    exit(0)

# ========== 8. 主函数 ==========
def main():
    global current_frame, last_local_objects

    print("=" * 60)
    print("瞳声-基于端云协同的轻量化智能识别系统")
    print("=" * 60)

    # 选择输入源
    print("\n请选择输入源：")
    print("  0 - 真实摄像头")
    print("  1 - CARLA 仿真（需先启动 CARLA 服务器）")
    choice = input("请输入数字 [0/1]：").strip()
    use_carla = (choice == '1')

    cap = None
    carla_mode = False
    if use_carla:
        if init_carla():
            carla_mode = True
            print("已切换到 CARLA 仿真模式，等待图像数据...")
        else:
            print("CARLA 初始化失败，将回退到真实摄像头模式")
            use_carla = False

    if not carla_mode:
        # 选择摄像头
        print("\n正在检测可用摄像头...")
        available = []
        for i in range(4):
            c = cv2.VideoCapture(i)
            if c.isOpened():
                ret, _ = c.read()
                if ret:
                    available.append(i)
                    print(f"  索引 {i}: 可用")
                c.release()
            else:
                c.release()

        if not available:
            print("✗ 未检测到可用摄像头")
            return

        if len(available) == 1:
            cam_index = available[0]
            print(f"✓ 自动选择摄像头索引 {cam_index}")
        else:
            print(f"\n检测到 {len(available)} 个摄像头: {available}")
            cam_index = available[0]
            for idx in available:
                choice = input(f"  使用索引 {idx} 的摄像头? (y/n, 默认y): ").strip().lower()
                if choice == '' or choice == 'y':
                    cam_index = idx
                    break
            print(f"✓ 已选择摄像头索引 {cam_index}")

        cap = cv2.VideoCapture(cam_index)
        if not cap.isOpened():
            print(f"✗ 无法打开摄像头索引 {cam_index}")
            return
        print(f"✓ 摄像头已打开，索引 {cam_index}")

    # 测试麦克风
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000,
                        input=True, frames_per_buffer=1024)
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("✓ 麦克风可用")
    except Exception as e:
        print(f"⚠ 警告：麦克风不可用 ({e})")

    # 注册热键
    keyboard.add_hotkey('space', on_space)
    keyboard.add_hotkey('c', on_cloud_describe)
    keyboard.add_hotkey('q', on_q)
    keyboard.on_press_key('v', lambda e: on_voice_query())

    print("\n开始运行。")
    if carla_mode:
        print("CARLA 仿真模式：")
        print("  WASD: 控制行人移动（W前进, S后退, A左转, D右转）")
        print("  V: 按住说话，松开后自动识别")
        print("  C: 云端描述画面")
        print("  空格: 本地播报")
        print("  Q: 退出")
    else:
        print("控制说明：")
        print("  空格键 : 本地快速播报")
        print("  C 键   : 云端描述画面（AI语音，非机械音）")
        print("  V 键   : 按住并说话，与 AI 对话（阿里云ASR）")
        print("  Q 键   : 退出")

    # 主循环
    last_time = time.time()
    while True:
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time

        if carla_mode:
            # CARLA 模式下更新行人移动
            update_walker_control(dt)

            if carla_frame is not None:
                frame = carla_frame.copy()
            else:
                time.sleep(0.02)
                continue
        else:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
        current_frame = frame.copy()

        # 本地 YOLO 识别
        results = model(frame)
        boxes = results[0].boxes
        if boxes is not None and len(boxes):
            class_ids = boxes.cls.int().tolist()
            detected = [results[0].names[cid] for cid in class_ids]
            last_local_objects = list(set(detected))
        else:
            last_local_objects = []

        # 可视化
        annotated = results[0].plot()
        h, w = annotated.shape[:2]
        cv2.rectangle(annotated, (0, h-90), (w, h), (0,0,0), -1)
        cv2.putText(annotated, "SPACE: local   C: cloud   V: speak   Q: quit", (10, h-30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
        if carla_mode:
            cv2.putText(annotated, "[CARLA] WASD: move   Hold V to ask", (10, h-60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
        else:
            cv2.putText(annotated, "Hold V to ask questions (Aliyun ASR)", (10, h-60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
        cv2.imshow('AI Assistant - Voice', annotated)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 清理资源
    if cap is not None:
        cap.release()
    if carla_mode:
        cleanup_carla()
    cv2.destroyAllWindows()
    keyboard.unhook_all()

if __name__ == '__main__':
    main()

