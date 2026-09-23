import cv2
import time
import keyboard
import os
import sys
import numpy as np
from datetime import datetime
from config import Config
from language import Translation
from tensorrt_engine import TensorRTEngine
from tracker import DeepSORTTracker
from violation_detector import ViolationDetector
from speech_manager import SpeechManager
from cloud_manager import CloudManager
from warning_manager import WarningManager
from api_client import APIClient

class ZhiTongSystem:
    def __init__(self):
        self.config = Config()
        self.config.create_dirs()
        
        print("=" * 60)
        print("智瞳灵声 - 基于视觉识别与云端推理的智慧交管系统")
        print("=" * 60)
        print("\n初始化系统...")
        
        self.engine = TensorRTEngine(self.config)
        print("✓ YOLO检测引擎已加载")
        
        self.tracker = DeepSORTTracker(self.config)
        print("✓ DeepSORT跟踪器已加载")
        
        self.violation_detector = ViolationDetector(self.config)
        print("✓ 违规检测引擎已加载")
        
        self.speech_manager = SpeechManager(self.config)
        print("✓ 语音播报模块已加载")
        
        self.cloud_manager = CloudManager(self.config)
        print("✓ 云端管理模块已加载")
        
        self.warning_manager = WarningManager()
        print("✓ 分级警告系统已加载")
        
        self.api_client = APIClient(self.config)
        print("✓ API客户端已加载")
        
        self.running = False
        self.current_frame = None
        self.last_detected_objects = []
        
        print("✓ 系统初始化完成")
    
    def detect_cameras(self):
        print("\n正在检测可用摄像头...")
        available_cameras = []
        for i in range(4):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available_cameras.append(i)
                    print(f"  索引 {i}: 可用")
                cap.release()
        
        if not available_cameras:
            print("✗ 未检测到可用摄像头")
            return None
        
        if len(available_cameras) == 1:
            cam_index = available_cameras[0]
            print(f"✓ 自动选择摄像头索引 {cam_index}")
            return cam_index
        
        print(f"\n检测到 {len(available_cameras)} 个摄像头")
        print("请选择摄像头索引:")
        for idx in available_cameras:
            print(f"  [{idx}]")
        
        return available_cameras[0]
    
    def setup_roi(self, frame):
        print("\n设置检测区域 (按ESC跳过，按Space确认)")
        print("选择停车线点 (左键点击，Space完成):")
        points = []
        
        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                points.append((x, y))
                print(f"  点 {len(points)}: ({x}, {y})")
        
        cv2.namedWindow('Setup ROI')
        cv2.setMouseCallback('Setup ROI', mouse_callback)
        
        temp_frame = frame.copy()
        while True:
            display_frame = temp_frame.copy()
            
            if len(points) >= 2:
                cv2.polylines(display_frame, [np.array(points)], True, (0, 255, 0), 2)
                for i, (x, y) in enumerate(points):
                    cv2.circle(display_frame, (x, y), 5, (0, 0, 255), -1)
                    cv2.putText(display_frame, str(i+1), (x+10, y+10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            cv2.imshow('Setup ROI', display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                print("  跳过区域设置")
                points = []
                break
            elif key == 32:
                if len(points) >= 2:
                    print(f"✓ 设置完成，共 {len(points)} 个点")
                else:
                    print("  点不足，跳过区域设置")
                    points = []
                break
        
        cv2.destroyWindow('Setup ROI')
        
        if len(points) >= 2:
            self.violation_detector.set_stop_line(points)
    
    def process_frame(self, frame):
        detections = self.engine.get_detections(frame)
        tracked_objects = self.tracker.update(frame, detections)
        current_time = time.time()
        violations = self.violation_detector.detect_all(frame, detections, tracked_objects, current_time)
        
        self.last_detected_objects = [det['class_name'] for det in detections]
        
        return detections, tracked_objects, violations
    
    def draw_ui(self, frame, detections, tracked_objects, violations):
        annotated = frame.copy()
        
        annotated = self.violation_detector.draw_lane_lines(annotated)
        annotated = self.tracker.draw_tracks(annotated, tracked_objects)
        annotated = self.violation_detector.draw_violations(annotated, violations)
        
        h, w = annotated.shape[:2]
        cv2.rectangle(annotated, (0, h-90), (w, h), (0, 0, 0), -1)
        cv2.putText(annotated, Translation.get_ui_text('title'), (10, h-60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(annotated, "空格:本地播报  C:云端分析  Q:退出", (10, h-30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        if len(tracked_objects) > 0:
            cv2.putText(annotated, f"{Translation.get_ui_text('tracks')}: {len(tracked_objects)}", (w-200, h-60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        if len(violations) > 0:
            cv2.putText(annotated, f"{Translation.get_ui_text('violations')}: {len(violations)}", (w-200, h-30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        for obj in tracked_objects:
            speed = self.violation_detector.speed_estimator.calculate_speed(obj.track_id)
            if speed > 0:
                x1, y1, x2, y2 = obj.bbox
                speed_text = f"{Translation.get_ui_text('speed')}: {speed:.1f} km/h"
                cv2.putText(annotated, speed_text, (int(x1), int(y2) + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        return annotated
    
    def handle_violations(self, violations, frame):
        for vio in violations:
            response_level = self.violation_detector.confidence_evaluator.get_response_level(vio.confidence)
            need_cloud = self.violation_detector.confidence_evaluator.should_send_to_cloud(vio.confidence)
            
            record = self.warning_manager.add_violation(vio)
            
            if record and record.should_warn():
                warning_message = record.get_warning_message()
                correction_guide = record.get_correction_guide()
                
                print(f"\n[分级警告] 级别{record.current_level}: {warning_message}")
                self.speech_manager.announce_warning(record.current_level, warning_message, correction_guide)
                
                record.last_warning_time = datetime.now()
            
            if response_level == "high":
                evidence_path = self.cloud_manager.save_evidence(frame, vio)
                self.api_client.submit_violation(vio, frame)
            elif response_level == "medium" and need_cloud:
                self.cloud_manager.add_to_queue(vio, frame.copy())
                self.api_client.submit_violation(vio, frame.copy())
    
    def on_space(self):
        if self.last_detected_objects:
            print("\n[本地播报]")
            self.speech_manager.speak_local_objects(self.last_detected_objects)
    
    def on_c(self):
        if self.current_frame is not None:
            print("\n[云端分析] 正在请求...")
            def worker():
                result = self.cloud_manager.analyze_with_cloud(self.current_frame)
                if result and result['success']:
                    self.speech_manager.speak(result['result'])
            import threading
            threading.Thread(target=worker, daemon=True).start()
    
    def on_q(self):
        self.running = False
        print("\n正在退出...")
        print("等待API上传队列清空...")
        self.api_client.stop()
        print("API上传已完成")
    
    def start(self):
        cam_index = self.detect_cameras()
        if cam_index is None:
            return
        
        cap = cv2.VideoCapture(cam_index)
        if not cap.isOpened():
            print(f"✗ 无法打开摄像头索引 {cam_index}")
            return
        
        print(f"✓ 摄像头已打开，索引 {cam_index}")
        
        ret, first_frame = cap.read()
        if ret:
            self.setup_roi(first_frame)
        
        keyboard.add_hotkey('space', self.on_space)
        keyboard.add_hotkey('c', self.on_c)
        keyboard.add_hotkey('q', self.on_q)
        
        print("\n系统启动成功！")
        print("控制说明：")
        print("  SPACE - 本地快速播报")
        print("  C     - 云端图像分析")
        print("  Q     - 退出系统\n")
        
        self.running = True
        fps_start_time = time.time()
        fps_counter = 0
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            
            self.current_frame = frame.copy()
            
            detections, tracked_objects, violations = self.process_frame(frame)
            display_frame = self.draw_ui(frame, detections, tracked_objects, violations)
            
            if violations:
                self.handle_violations(violations, frame)
            
            fps_counter += 1
            if time.time() - fps_start_time >= 1.0:
                fps = fps_counter / (time.time() - fps_start_time)
                h, w = display_frame.shape[:2]
                cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                fps_counter = 0
                fps_start_time = time.time()
            
            cv2.imshow('智瞳灵声 - 智慧交管系统', display_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        keyboard.unhook_all_hotkeys()
        print("系统已退出")

def main():
    try:
        system = ZhiTongSystem()
        system.start()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")

if __name__ == '__main__':
    main()
