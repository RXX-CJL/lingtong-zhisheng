# -*- coding: utf-8 -*-
"""
演示脚本 - 使用测试视频模拟实时检测流程
自动触发端云协作，生成演示数据
"""

import os
import sys
import cv2
import time
import json
import base64
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from image_recognizer import multi_model_detect, init_all_models, CLASS_CN_MAP
from violation_rules import check_violations, VIOLATION_TYPE_CN
from cloud_collaborator import CloudCollaborator
from config import Config

class DemoRunner:
    def __init__(self, video_path=None):
        self.video_path = video_path
        self.cap = None
        self.cloud_collaborator = CloudCollaborator()
        self.frame_count = 0
        self.violation_count = 0
        self.detection_results = []
        self.init_success = False
        
    def init(self):
        logger.info("初始化演示环境...")
        try:
            init_all_models()
            logger.info("模型初始化完成")
            
            if self.video_path and os.path.exists(self.video_path):
                self.cap = cv2.VideoCapture(self.video_path)
                if not self.cap.isOpened():
                    logger.error(f"无法打开视频文件: {self.video_path}")
                    return False
                logger.info(f"视频文件加载成功: {self.video_path}")
                logger.info(f"视频帧率: {self.cap.get(cv2.CAP_PROP_FPS):.1f}")
                logger.info(f"视频分辨率: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
                logger.info(f"视频总帧数: {int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))}")
            else:
                logger.warning("未指定视频文件，将使用模拟数据")
            
            self.init_success = True
            return True
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    def _draw_detection_boxes(self, frame, detections):
        color_map = {
            'motorcycle': (255, 0, 0),
            'car': (255, 0, 0),
            'truck': (255, 0, 0),
            'bus': (255, 0, 0),
            'bicycle': (255, 0, 0),
            'person': (0, 255, 0),
            'helmet': (0, 255, 0),
            'no_helmet': (0, 0, 255),
            'red_light': (0, 0, 255),
            'yellow_light': (0, 255, 255),
            'green_light': (0, 255, 0),
            'lane_line': (0, 255, 255),
        }
        
        for det in detections:
            bbox = det.get('bbox', [0, 0, 0, 0])
            class_name = det.get('class_name', '')
            class_name_cn = CLASS_CN_MAP.get(class_name, class_name)
            confidence = det.get('confidence', 0.0)
            
            x1, y1, x2, y2 = [int(v) for v in bbox]
            color = color_map.get(class_name, (0, 255, 0))
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            label = f"{class_name_cn} {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 5), (x1 + label_size[0], y1), color, -1)
            cv2.putText(frame, label, (x1, y1 - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return frame
    
    def _frame_to_base64(self, frame):
        _, img_encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return base64.b64encode(img_encoded).decode('utf-8')
    
    def run_single_frame(self, frame):
        self.frame_count += 1
        
        start_time = time.time()
        
        _, img_encoded = cv2.imencode('.jpg', frame)
        img_base64 = base64.b64encode(img_encoded).decode('utf-8')
        data_url = f"data:image/jpeg;base64,{img_base64}"
        
        detect_result = multi_model_detect(data_url, conf_threshold=Config.CONFIDENCE_THRESHOLD)
        detections = detect_result.get('all_detections', [])
        
        result = {
            'frame_index': self.frame_count,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'detection_count': len(detections),
            'detections': detections,
            'violations': [],
            'cloud_consulted': False,
            'processing_time_ms': 0
        }
        
        if detections:
            violation_result = check_violations(detections)
            violations = violation_result.get('violations', [])
            result['violations'] = violations
            
            if violations:
                self.violation_count += 1
                logger.info(f"帧 {self.frame_count}: 检测到 {len(violations)} 个违规")
                
                for vio in violations:
                    logger.info(f"  - {vio.get('violation_type_cn')}: 置信度 {vio.get('confidence', 0):.4f}")
                
                highest_conf = max(v.get('confidence', 0.0) for v in violations)
                violation_type = violations[0].get('violation_type')
                
                consult_type = self.cloud_collaborator.should_consult_cloud({
                    'violation_type': violation_type,
                    'confidence': highest_conf,
                    'detections': detections,
                    'success': True
                })
                
                if consult_type:
                    logger.info(f"  → 触发云端咨询 ({consult_type})")
                    
                    annotated_frame = self._draw_detection_boxes(frame.copy(), detections)
                    annotated_base64 = self._frame_to_base64(annotated_frame)
                    
                    cloud_result = self.cloud_collaborator.consult_cloud_dual(
                        data_url,
                        annotated_base64,
                        {'violation_type': violation_type, 'confidence': highest_conf},
                        consult_type,
                        None
                    )
                    
                    if cloud_result.get('success'):
                        result['cloud_consulted'] = True
                        result['cloud_result'] = cloud_result
                        result['ai_trace'] = cloud_result.get('ai_trace')
                        logger.info(f"  ← 云端咨询完成")
                    else:
                        logger.warning(f"  ← 云端咨询失败: {cloud_result.get('error', '未知错误')}")
        
        processing_time = (time.time() - start_time) * 1000
        result['processing_time_ms'] = round(processing_time, 2)
        
        self.detection_results.append(result)
        
        return result
    
    def run_video(self, max_frames=100):
        if not self.init_success:
            logger.error("初始化未成功，无法运行")
            return
        
        logger.info(f"开始视频演示（最大帧数: {max_frames}）")
        logger.info("=" * 60)
        
        frame_interval = 1.0 / Config.FRAME_RATE
        last_frame_time = time.time()
        
        frame_count = 0
        failed_reads = 0
        
        while frame_count < max_frames:
            ret, frame = self.cap.read()
            
            if not ret or frame is None:
                failed_reads += 1
                if failed_reads > 10:
                    logger.warning("连续读取失败，切换到模拟模式")
                    self.run_simulated(iterations=20)
                    return
                time.sleep(0.05)
                continue
            
            failed_reads = 0
            
            current_time = time.time()
            elapsed = current_time - last_frame_time
            
            if elapsed >= frame_interval:
                last_frame_time = current_time
                
                result = self.run_single_frame(frame)
                
                if result.get('violations'):
                    annotated = self._draw_detection_boxes(frame.copy(), result['detections'])
                    cv2.imshow('Demo - 违规检测', annotated)
                else:
                    cv2.imshow('Demo - 实时监控', frame)
                
                frame_count += 1
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("用户中断演示")
                    break
            
            time.sleep(0.01)
        
        cv2.destroyAllWindows()
        logger.info("=" * 60)
        self._print_summary()
    
    def run_simulated(self, iterations=20):
        logger.info(f"开始模拟演示（迭代次数: {iterations}）")
        logger.info("=" * 60)
        
        import numpy as np
        
        for i in range(iterations):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, f'Demo Frame {i+1}/{iterations}', (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            if i % 5 == 0:
                cv2.putText(frame, 'SIMULATED VIOLATION: NO HELMET', (50, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            result = self.run_single_frame(frame)
            
            if result.get('violations'):
                annotated = self._draw_detection_boxes(frame.copy(), result['detections'])
                cv2.imshow('Demo - 模拟检测', annotated)
            else:
                cv2.imshow('Demo - 模拟监控', frame)
            
            if cv2.waitKey(200) & 0xFF == ord('q'):
                logger.info("用户中断演示")
                break
            
            time.sleep(0.5)
        
        cv2.destroyAllWindows()
        logger.info("=" * 60)
        self._print_summary()
    
    def _print_summary(self):
        logger.info("演示总结")
        logger.info(f"  总处理帧数: {self.frame_count}")
        logger.info(f"  检测到违规次数: {self.violation_count}")
        
        violation_types = {}
        for result in self.detection_results:
            for vio in result.get('violations', []):
                vt = vio.get('violation_type_cn', vio.get('violation_type'))
                violation_types[vt] = violation_types.get(vt, 0) + 1
        
        if violation_types:
            logger.info("  违规类型分布:")
            for vt, count in violation_types.items():
                logger.info(f"    - {vt}: {count} 次")
        
        avg_time = sum(r.get('processing_time_ms', 0) for r in self.detection_results) / max(len(self.detection_results), 1)
        logger.info(f"  平均处理时间: {avg_time:.2f} ms")
        
        cloud_consulted = sum(1 for r in self.detection_results if r.get('cloud_consulted'))
        logger.info(f"  云端咨询次数: {cloud_consulted}")
    
    def save_results(self, output_file=None):
        if not output_file:
            output_file = os.path.join(os.path.dirname(__file__), 'demo_results.json')
        
        output = {
            'demo_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'video_path': self.video_path,
            'total_frames': self.frame_count,
            'violation_count': self.violation_count,
            'results': self.detection_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logger.info(f"演示结果已保存到: {output_file}")
        return output_file


def main():
    video_dir = os.path.join(os.path.dirname(__file__), 'data', 'raw_videos')
    
    test_videos = []
    if os.path.exists(video_dir):
        for f in os.listdir(video_dir):
            if f.endswith(('.mp4', '.avi', '.mov')):
                test_videos.append(os.path.join(video_dir, f))
    
    logger.info(f"找到 {len(test_videos)} 个测试视频")
    for i, v in enumerate(test_videos):
        logger.info(f"  [{i+1}] {os.path.basename(v)}")
    
    if test_videos:
        video_path = test_videos[0]
        logger.info(f"\n使用视频: {video_path}")
        
        demo = DemoRunner(video_path)
        if demo.init():
            demo.run_video(max_frames=50)
            demo.save_results()
    else:
        logger.info("\n未找到测试视频，使用模拟模式")
        
        demo = DemoRunner()
        if demo.init():
            demo.run_simulated(iterations=15)
            demo.save_results()


if __name__ == "__main__":
    main()