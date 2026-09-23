# -*- coding: utf-8 -*-
"""
智瞳实时检测预览窗口
独立运行的实时预览窗口（类似blind_yun.py的GUI）

快捷键：
- 空格 = 截图保存
- C = 强制云端咨询
- Q = 退出
"""

import cv2
import time
import threading
import base64
import os
import sys
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from api.realtime_detector import RealtimeViolationDetector
from api.image_recognizer import multi_model_detect, init_all_models, CLASS_CN_MAP
from api.violation_rules import check_violations, VIOLATION_TYPE_CN

class PreviewWindow:
    def __init__(self):
        self.detector = RealtimeViolationDetector()
        self.running = False
        self.current_frame = None
        self.last_detection_result = None
        self.collab_status = "本地检测中"
        self.collab_status_color = (0, 255, 0)
        self.snapshot_count = 0
        
        init_all_models()
        print("[PreviewWindow] 模型初始化完成")

    def _detect_available_cameras(self):
        available = []
        for i in range(4):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append(i)
                    print(f"  摄像头索引 {i}: 可用")
                cap.release()
            else:
                cap.release()
        return available

    def _draw_detection_boxes(self, frame, detections):
        annotated = frame.copy()
        for det in detections:
            bbox = det.get('bbox', [0, 0, 0, 0])
            class_name = det.get('class_name', '')
            class_name_cn = CLASS_CN_MAP.get(class_name, class_name)
            confidence = det.get('confidence', 0.0)
            
            x1, y1, x2, y2 = [int(v) for v in bbox]
            
            color = (0, 255, 0)
            if class_name in ['no_helmet', 'red_light']:
                color = (0, 0, 255)
            elif class_name in ['helmet', 'green_light']:
                color = (0, 255, 0)
            elif class_name in ['motorcycle', 'bicycle', 'car']:
                color = (255, 0, 0)
            
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            label = f"{class_name_cn} {confidence:.2f}"
            cv2.putText(annotated, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return annotated

    def _draw_violation_labels(self, frame, violations):
        annotated = frame.copy()
        h, w = annotated.shape[:2]
        
        y_offset = 30
        for idx, violation in enumerate(violations[:5]):
            vio_type = violation.get('violation_type', '')
            vio_type_cn = VIOLATION_TYPE_CN.get(vio_type, vio_type)
            confidence = violation.get('confidence', 0.0)
            
            bg_top = h - 100 + idx * 25
            bg_bottom = bg_top + 22
            cv2.rectangle(annotated, (0, bg_top), (w, bg_bottom), (0, 0, 0), -1)
            
            text = f"⚠ {vio_type_cn} - 置信度: {confidence:.4f}"
            cv2.putText(annotated, text, (10, bg_top + 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            y_offset += 25
        
        return annotated

    def _draw_status_bar(self, frame, fps, status):
        annotated = frame.copy()
        h, w = annotated.shape[:2]
        
        cv2.rectangle(annotated, (0, 0), (w, 25), (0, 0, 0), -1)
        
        status_text = f"FPS: {fps:.1f} | 状态: {self.collab_status} | 检测帧: {status['processed_frames']} | 违规: {status['violation_count']}"
        cv2.putText(annotated, status_text, (10, 18),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.collab_status_color, 1)
        
        return annotated

    def _save_snapshot(self):
        if self.current_frame is None:
            print("[PreviewWindow] 没有画面可保存")
            return
        
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snapshots')
        os.makedirs(save_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.jpg"
        filepath = os.path.join(save_dir, filename)
        
        cv2.imwrite(filepath, self.current_frame)
        self.snapshot_count += 1
        print(f"[PreviewWindow] 截图已保存: {filepath}")

    def _force_cloud_consult(self):
        if self.current_frame is None:
            print("[PreviewWindow] 没有画面可咨询")
            return
        
        print("[PreviewWindow] 正在强制云端咨询...")
        self.collab_status = "咨询云端中"
        self.collab_status_color = (0, 255, 255)
        
        def worker():
            try:
                _, img_encoded = cv2.imencode('.jpg', self.current_frame)
                img_base64 = base64.b64encode(img_encoded).decode('utf-8')
                data_url = f"data:image/jpeg;base64,{img_base64}"
                
                result = multi_model_detect(data_url)
                if result.get('success'):
                    violations = check_violations(result.get('all_detections', []))
                    self.last_detection_result = violations
                
                self.collab_status = "已确认"
                self.collab_status_color = (0, 255, 0)
                print("[PreviewWindow] 云端咨询完成")
            except Exception as e:
                self.collab_status = "本地检测中"
                self.collab_status_color = (0, 255, 0)
                print(f"[PreviewWindow] 云端咨询失败: {e}")
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _process_frame(self, frame):
        start_time = time.time()
        
        try:
            _, img_encoded = cv2.imencode('.jpg', frame)
            img_base64 = base64.b64encode(img_encoded).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{img_base64}"
            
            result = multi_model_detect(data_url)
            
            if result.get('success'):
                detections = result.get('all_detections', [])
                violation_result = check_violations(detections)
                self.last_detection_result = {
                    'detections': detections,
                    'violations': violation_result.get('violations', []),
                    'duration_ms': int((time.time() - start_time) * 1000)
                }
                
                if self.last_detection_result['violations']:
                    highest_conf = max(v.get('confidence', 0.0) for v in self.last_detection_result['violations'])
                    if highest_conf >= 0.7:
                        self.collab_status = "已确认"
                        self.collab_status_color = (0, 255, 0)
                    elif 0.4 <= highest_conf < 0.7:
                        self.collab_status = "咨询云端中"
                        self.collab_status_color = (0, 255, 255)
                    else:
                        self.collab_status = "本地检测中"
                        self.collab_status_color = (0, 255, 0)
                else:
                    self.collab_status = "本地检测中"
                    self.collab_status_color = (0, 255, 0)
                    
        except Exception as e:
            print(f"[PreviewWindow] 帧处理失败: {e}")
        
        return time.time() - start_time

    def run(self, camera_index=0, video_path=None):
        print("=" * 60)
        print("智瞳实时检测预览窗口")
        print("=" * 60)
        
        available_cameras = self._detect_available_cameras()
        if not available_cameras and not video_path:
            print("✗ 未检测到可用摄像头，且未指定视频文件")
            return
        
        try:
            self.detector.start_camera(camera_index, video_path)
            print(f"✓ 摄像头/视频已打开")
        except Exception as e:
            print(f"✗ 无法打开摄像头或视频: {e}")
            return
        
        self.running = True
        last_time = time.time()
        frame_count = 0
        fps = 0.0
        
        print("\n控制说明：")
        print("  空格键 : 截图保存")
        print("  C 键   : 强制云端咨询")
        print("  Q 键   : 退出")
        
        while self.running:
            ret, frame = self.detector.cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            self.current_frame = frame.copy()
            
            current_time = time.time()
            elapsed = current_time - last_time
            
            if elapsed >= 1.0 / 3:
                last_time = current_time
                process_time = self._process_frame(frame)
                frame_count += 1
                fps = 1.0 / elapsed
            
            annotated = frame.copy()
            
            if self.last_detection_result:
                annotated = self._draw_detection_boxes(annotated, self.last_detection_result.get('detections', []))
                annotated = self._draw_violation_labels(annotated, self.last_detection_result.get('violations', []))
            
            status = self.detector.get_status()
            annotated = self._draw_status_bar(annotated, fps, status)
            
            h, w = annotated.shape[:2]
            cv2.rectangle(annotated, (0, h-35), (w, h), (0, 0, 0), -1)
            cv2.putText(annotated, "SPACE: 截图   C: 云端咨询   Q: 退出", (10, h-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            
            cv2.imshow('智瞳实时检测', annotated)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.running = False
            elif key == ord(' '):
                self._save_snapshot()
            elif key == ord('c'):
                self._force_cloud_consult()
        
        self.detector.stop()
        cv2.destroyAllWindows()
        print(f"\n[PreviewWindow] 退出，共保存 {self.snapshot_count} 张截图")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='智瞳实时检测预览窗口')
    parser.add_argument('--camera', type=int, default=0, help='摄像头索引')
    parser.add_argument('--video', type=str, default=None, help='视频文件路径')
    
    args = parser.parse_args()
    
    preview = PreviewWindow()
    preview.run(args.camera, args.video)