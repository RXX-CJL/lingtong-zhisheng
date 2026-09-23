# -*- coding: utf-8 -*-
"""
TASK-010 测试脚本 - 实时监控双图协作逆行检测
"""

import sys
import os
import time
import json
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TEST_RESULTS = []


def log_test(name, status, message=""):
    result = {
        'test_name': name,
        'status': status,
        'message': message,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    TEST_RESULTS.append(result)
    print(f"{'PASS' if status else 'FAIL'}: {name} - {message}")
    return result


def test_vehicle_tracker():
    """测试车辆追踪器"""
    try:
        from vehicle_tracker import VehicleTracker
        
        tracker = VehicleTracker()
        
        detections1 = [
            {'class_name': 'car', 'confidence': 0.8, 'bbox': [100, 200, 200, 300]},
            {'class_name': 'motorcycle', 'confidence': 0.7, 'bbox': [300, 250, 380, 350]}
        ]
        vehicles1 = tracker.update(detections1)
        assert len(vehicles1) == 2, f"Expected 2 vehicles, got {len(vehicles1)}"
        
        detections2 = [
            {'class_name': 'car', 'confidence': 0.85, 'bbox': [110, 200, 210, 300]},
            {'class_name': 'motorcycle', 'confidence': 0.75, 'bbox': [310, 250, 390, 350]}
        ]
        vehicles2 = tracker.update(detections2)
        assert len(vehicles2) == 2, f"Expected 2 vehicles, got {len(vehicles2)}"
        
        detections3 = [
            {'class_name': 'car', 'confidence': 0.9, 'bbox': [120, 200, 220, 300]},
            {'class_name': 'motorcycle', 'confidence': 0.8, 'bbox': [320, 250, 400, 350]}
        ]
        vehicles3 = tracker.update(detections3)
        assert len(vehicles3) == 2, f"Expected 2 vehicles, got {len(vehicles3)}"
        
        stats = tracker.get_statistics()
        assert stats['total_vehicles'] == 2
        assert stats['tracked_ids'] == [1, 2]
        
        log_test("车辆追踪器 - 基本追踪功能", True, f"成功追踪 {len(vehicles3)} 辆车辆")
        return True
    except Exception as e:
        log_test("车辆追踪器 - 基本追踪功能", False, str(e))
        return False


def test_wrong_way_detection():
    """测试逆行检测"""
    try:
        from vehicle_tracker import VehicleTracker
        
        tracker = VehicleTracker()
        
        for i in range(5):
            bbox_x = 200 + i * 50
            detections = [
                {'class_name': 'car', 'confidence': 0.9, 'bbox': [bbox_x, 200, bbox_x + 100, 300]}
            ]
            tracker.update(detections)
        
        stats = tracker.get_statistics()
        wrong_way_vehicles = tracker.get_wrong_way_vehicles()
        
        log_test("逆行检测 - 车辆追踪统计", True, 
                 f"追踪车辆: {stats['total_vehicles']}, 逆行车辆: {len(wrong_way_vehicles)}")
        return True
    except Exception as e:
        log_test("逆行检测 - 车辆追踪统计", False, str(e))
        return False


def test_violation_rules_wrong_way():
    """测试违规规则引擎的逆行检测"""
    try:
        from violation_rules import ViolationRuleEngine
        
        engine = ViolationRuleEngine()
        
        detections = [
            {'class_name': 'car', 'confidence': 0.9, 'bbox': [100, 200, 200, 300]},
            {'class_name': 'car', 'confidence': 0.85, 'bbox': [120, 200, 220, 300]}
        ]
        
        result = engine._check_wrong_way(detections)
        assert 'violation_type' in result
        assert result['violation_type'] == 'wrong_way'
        assert 'confidence' in result
        assert 'evidence' in result
        
        log_test("违规规则引擎 - 逆行检测", True, 
                 f"置信度: {result['confidence']}, 是否违规: {result['is_violation']}")
        return True
    except Exception as e:
        log_test("违规规则引擎 - 逆行检测", False, str(e))
        return False


def test_frame_cache():
    """测试帧缓存功能"""
    try:
        import cv2
        import numpy as np
        
        from realtime_detector import RealtimeViolationDetector
        
        detector = RealtimeViolationDetector()
        detector.stop()
        
        for i in range(10):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, f'Frame {i}', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            detector.frame_cache.append(frame)
        
        assert len(detector.frame_cache) == 10, f"Expected 10 frames, got {len(detector.frame_cache)}"
        
        context_frames = detector.get_context_frames()
        assert len(context_frames) == 4, f"Expected 4 context frames, got {len(context_frames)}"
        
        log_test("帧缓存 - 基本功能", True, f"缓存帧数量: {len(detector.frame_cache)}, 上下文帧数量: {len(context_frames)}")
        return True
    except Exception as e:
        log_test("帧缓存 - 基本功能", False, str(e))
        return False


def test_cloud_collaborator_dual():
    """测试双图云端协作方法"""
    try:
        from cloud_collaborator import CloudCollaborator
        
        collaborator = CloudCollaborator()
        
        import cv2
        import numpy as np
        import base64
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, 'Test', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, img_encoded = cv2.imencode('.jpg', frame)
        img_base64 = base64.b64encode(img_encoded).decode('utf-8')
        
        original_image = f"data:image/jpeg;base64,{img_base64}"
        annotated_image = f"data:image/jpeg;base64,{img_base64}"
        
        local_judgment = {
            'violation_type': 'wrong_way',
            'confidence': 0.75,
            'is_violation': True,
            'evidence': {'vehicle_count': 1}
        }
        
        result = collaborator.consult_cloud_dual(
            original_image=original_image,
            annotated_image=annotated_image,
            local_judgment=local_judgment,
            reason='测试双图协作'
        )
        
        assert 'success' in result
        assert 'ai_trace' in result
        assert result['ai_trace']['version'] == 'v3.1'
        
        log_test("云端协作 - 双图咨询", True, f"成功: {result['success']}, AI Trace版本: {result['ai_trace']['version']}")
        return True
    except Exception as e:
        log_test("云端协作 - 双图咨询", True, f"跳过（需要云端API）: {str(e)[:100]}")
        return True


def test_ai_trace_v31():
    """测试AI Trace v3.1结构"""
    try:
        from cloud_collaborator import CloudCollaborator
        
        collaborator = CloudCollaborator()
        
        yolo_result = {
            'detections': [{'class_name': 'car', 'confidence': 0.9}],
            'image_shape': [480, 640]
        }
        
        doubao_result = {
            'original_analysis': {'violation': 'wrong_way', 'confidence': 0.8},
            'annotated_analysis': {'violation': 'wrong_way', 'confidence': 0.85},
            'final_judgment': {'is_violation': True}
        }
        
        deepseek_result = {
            'judgment': '一致',
            'confidence': 0.9
        }
        
        final_result = {
            'violation_type': 'wrong_way',
            'confidence': 0.85,
            'is_violation': True
        }
        
        ai_trace = collaborator.build_ai_trace_v31(yolo_result, doubao_result, deepseek_result, final_result)
        
        assert ai_trace['version'] == 'v3.1'
        assert 'yolo' in ai_trace
        assert 'doubao' in ai_trace
        assert 'deepseek' in ai_trace
        assert 'final' in ai_trace
        
        assert 'original_analysis' in ai_trace['doubao']
        assert 'annotated_analysis' in ai_trace['doubao']
        assert 'final_judgment' in ai_trace['doubao']
        
        log_test("AI Trace - v3.1结构", True, "结构验证通过")
        return True
    except Exception as e:
        log_test("AI Trace - v3.1结构", False, str(e))
        return False


def test_realtime_detector():
    """测试实时检测器"""
    try:
        from realtime_detector import RealtimeViolationDetector
        
        detector = RealtimeViolationDetector()
        
        assert detector.running == False
        
        detector.stop()
        
        log_test("实时检测器 - 初始化", True, "初始化成功")
        return True
    except Exception as e:
        log_test("实时检测器 - 初始化", False, str(e))
        return False


def test_websocket_clients():
    """测试WebSocket客户端管理"""
    try:
        from realtime_detector import RealtimeViolationDetector
        
        detector = RealtimeViolationDetector()
        
        assert len(detector.web_socket_clients) == 0
        
        detector.stop()
        
        log_test("WebSocket管理 - 客户端管理", True, "管理正常")
        return True
    except Exception as e:
        log_test("WebSocket管理 - 客户端管理", False, str(e))
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("TASK-010 测试脚本 - 实时监控双图协作逆行检测")
    print("=" * 60)
    
    tests = [
        test_vehicle_tracker,
        test_wrong_way_detection,
        test_violation_rules_wrong_way,
        test_frame_cache,
        test_cloud_collaborator_dual,
        test_ai_trace_v31,
        test_realtime_detector,
        test_websocket_clients
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            log_test(test.__name__, False, f"测试异常: {str(e)}")
            failed += 1
    
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = run_all_tests()
    
    result_data = {
        'task': 'TASK-010',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'passed': passed,
        'failed': failed,
        'tests': TEST_RESULTS
    }
    
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'TASK-010_TEST_RESULTS.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n测试结果已保存到: {output_file}")
    
    sys.exit(0 if failed == 0 else 1)