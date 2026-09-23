# -*- coding: utf-8 -*-
"""
红绿灯颜色识别与车辆分类系统 - 自动化测试脚本
"""
import os
import sys
import json
import cv2
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from image_recognizer import (
    init_yolo_model,
    detect_with_yolo,
    multi_model_detect,
    _detect_traffic_light_color,
    MODEL_CONFIG
)
from violation_rules import ViolationRuleEngine


def test_model_loading():
    """测试模型加载"""
    print("=" * 60)
    print("测试1: 模型加载")
    print("=" * 60)
    
    models_to_test = ['yolov8s', 'vehicle', 'traffic_light', 'helmet']
    
    results = {}
    for model_key in models_to_test:
        start_time = time.time()
        try:
            success = init_yolo_model(model_key)
            duration = time.time() - start_time
            
            config = MODEL_CONFIG.get(model_key, {})
            results[model_key] = {
                'success': success,
                'model_path': config.get('model_path'),
                'duration_ms': round(duration * 1000, 2),
                'message': '加载成功' if success else '加载失败'
            }
            
            if success:
                print(f"✓ {model_key}: {config.get('name')} - {results[model_key]['duration_ms']}ms")
            else:
                print(f"✗ {model_key}: 加载失败")
                
        except Exception as e:
            results[model_key] = {
                'success': False,
                'error': str(e),
                'message': f"异常: {e}"
            }
            print(f"✗ {model_key}: {e}")
    
    return results


def test_hsv_color_recognition():
    """测试HSV颜色识别"""
    print("\n" + "=" * 60)
    print("测试2: HSV颜色识别")
    print("=" * 60)
    
    test_images = [
        ('red', np.zeros((100, 100, 3), dtype=np.uint8)),
        ('yellow', np.zeros((100, 100, 3), dtype=np.uint8)),
        ('green', np.zeros((100, 100, 3), dtype=np.uint8)),
    ]
    
    test_images[0][1][:, :, 2] = 255
    test_images[1][1][:, :, 1] = 255
    test_images[1][1][:, :, 2] = 255
    test_images[2][1][:, :, 1] = 255
    
    results = {}
    for expected_color, img in test_images:
        color, conf = _detect_traffic_light_color(img, [0, 0, 100, 100])
        
        results[expected_color] = {
            'expected': expected_color,
            'detected': color,
            'confidence': round(conf, 4),
            'match': color == expected_color,
            'message': f"预期:{expected_color}, 检测:{color}, 置信度:{conf:.4f}"
        }
        
        if color == expected_color:
            print(f"✓ {expected_color}: 检测正确 (置信度: {conf:.4f})")
        else:
            print(f"✗ {expected_color}: 预期:{expected_color}, 实际:{color}")
    
    return results


def test_traffic_light_detection(image_path):
    """测试红绿灯检测"""
    print("\n" + "=" * 60)
    print("测试3: 红绿灯检测")
    print("=" * 60)
    
    if not os.path.exists(image_path):
        print(f"✗ 测试图片不存在: {image_path}")
        return {'success': False, 'message': '测试图片不存在'}
    
    img = cv2.imread(image_path)
    if img is None:
        print(f"✗ 无法读取图片: {image_path}")
        return {'success': False, 'message': '无法读取图片'}
    
    print(f"图片尺寸: {img.shape}")
    
    results = {}
    
    for model_key in ['yolov8s', 'traffic_light']:
        start_time = time.time()
        result = detect_with_yolo(image_path, model_key, conf_threshold=0.1)
        duration = time.time() - start_time
        
        detected_colors = [d['class_name'] for d in result['detections']]
        light_detections = [d for d in result['detections'] 
                           if d['class_name'] in ['red', 'yellow', 'green', 'traffic light']]
        
        results[model_key] = {
            'success': result['success'],
            'duration_ms': round(duration * 1000, 2),
            'total_detections': len(result['detections']),
            'light_detections': len(light_detections),
            'detected_colors': detected_colors,
            'message': result.get('message', '')
        }
        
        if result['success'] and light_detections:
            print(f"✓ {model_key}: {len(light_detections)}个红绿灯 - {results[model_key]['duration_ms']}ms")
            for d in light_detections:
                print(f"  - {d['class_name']}: {d['class_name_cn']} (置信度: {d['confidence']:.4f})")
        else:
            print(f"✗ {model_key}: 未检测到红绿灯")
    
    return results


def test_vehicle_classification(image_path):
    """测试车辆分类"""
    print("\n" + "=" * 60)
    print("测试4: 车辆分类")
    print("=" * 60)
    
    if not os.path.exists(image_path):
        print(f"✗ 测试图片不存在: {image_path}")
        return {'success': False, 'message': '测试图片不存在'}
    
    expected_classes = {'car', 'motorcycle', 'truck', 'bus'}
    
    start_time = time.time()
    result = detect_with_yolo(image_path, 'vehicle', conf_threshold=0.1)
    duration = time.time() - start_time
    
    detected_classes = set([d['class_name'] for d in result['detections']])
    vehicle_classes = detected_classes & expected_classes
    
    results = {
        'success': result['success'],
        'duration_ms': round(duration * 1000, 2),
        'total_detections': len(result['detections']),
        'detected_vehicle_classes': list(vehicle_classes),
        'all_detected_classes': list(detected_classes),
        'message': result.get('message', '')
    }
    
    if result['success']:
        print(f"✓ vehicle模型: {len(result['detections'])}个检测 - {results['duration_ms']}ms")
        for d in result['detections']:
            print(f"  - {d['class_name']}: {d['class_name_cn']} (置信度: {d['confidence']:.4f})")
    else:
        print(f"✗ vehicle模型: 检测失败")
    
    return results


def test_multi_model_detection(image_path):
    """测试多模型串联检测"""
    print("\n" + "=" * 60)
    print("测试5: 多模型串联检测")
    print("=" * 60)
    
    if not os.path.exists(image_path):
        print(f"✗ 测试图片不存在: {image_path}")
        return {'success': False, 'message': '测试图片不存在'}
    
    start_time = time.time()
    result = multi_model_detect(image_path, conf_threshold=0.25)
    duration = time.time() - start_time
    
    results = {
        'success': result['success'],
        'duration_ms': round(duration * 1000, 2),
        'total_detections': len(result.get('all_detections', [])),
        'violations': result.get('violations', []),
        'message': result.get('message', '')
    }
    
    if result['success']:
        print(f"✓ 多模型检测成功 - {results['duration_ms']}ms")
        print(f"  检测到 {len(result.get('all_detections', []))} 个对象")
        
        for det in result.get('all_detections', []):
            print(f"  - {det['class_name']}: {det['class_name_cn']} (置信度: {det['confidence']:.4f})")
        
        if result.get('violations'):
            print(f"\n  检测到 {len(result['violations'])} 个违规:")
            for v in result['violations']:
                print(f"  - {v['violation_type_cn']}: 置信度 {v['confidence']}")
    else:
        print(f"✗ 多模型检测失败")
    
    return results


def test_violation_rules():
    """测试违规规则引擎"""
    print("\n" + "=" * 60)
    print("测试6: 违规规则引擎")
    print("=" * 60)
    
    engine = ViolationRuleEngine()
    
    test_cases = [
        {
            'name': '闯红灯检测',
            'detections': [
                {'class_name': 'car', 'confidence': 0.9, 'bbox': [100, 200, 300, 400]},
                {'class_name': 'red', 'confidence': 0.8, 'bbox': [500, 50, 550, 150]}
            ],
            'expected': ['red_light']
        },
        {
            'name': '未戴头盔检测',
            'detections': [
                {'class_name': 'motorcycle', 'confidence': 0.85, 'bbox': [100, 200, 300, 400]},
                {'class_name': 'person', 'confidence': 0.78, 'bbox': [150, 180, 280, 380]}
            ],
            'expected': ['no_helmet']
        },
        {
            'name': '绿灯正常通行',
            'detections': [
                {'class_name': 'car', 'confidence': 0.9, 'bbox': [100, 200, 300, 400]},
                {'class_name': 'green', 'confidence': 0.8, 'bbox': [500, 50, 550, 150]}
            ],
            'expected': []
        },
        {
            'name': '黄灯检测',
            'detections': [
                {'class_name': 'truck', 'confidence': 0.8, 'bbox': [100, 200, 300, 400]},
                {'class_name': 'yellow', 'confidence': 0.7, 'bbox': [500, 50, 550, 150]}
            ],
            'expected': []
        }
    ]
    
    results = {}
    for test_case in test_cases:
        result = engine.detect_violations(test_case['detections'])
        detected_types = [v['violation_type'] for v in result['violations']]
        passed = set(detected_types) == set(test_case['expected'])
        
        results[test_case['name']] = {
            'success': passed,
            'detected': detected_types,
            'expected': test_case['expected'],
            'violation_count': len(result['violations']),
            'message': f"检测到{len(result['violations'])}个违规"
        }
        
        if passed:
            print(f"✓ {test_case['name']}: 通过")
        else:
            print(f"✗ {test_case['name']}: 预期{test_case['expected']}, 实际{detected_types}")
    
    return results


def main():
    """主测试函数"""
    api_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(api_dir)
    
    test_images = [
        os.path.join(project_root, 'zhitong', 'data', 'processed_frames', 'wrong_way', 'test_wrong_way_20260609_104659_0000.jpg'),
        os.path.join(project_root, 'zhitong', 'data', 'processed_frames', 'no_helmet', 'test_no_helmet_20260609_104625_0000.jpg'),
        os.path.join(project_root, 'zhitong', 'data', 'processed_frames', 'red_light', 'test_red_light_20260609_104659_0000.jpg'),
        os.path.join(project_root, 'zhitong', 'data', 'test_images', 'test_traffic.jpg'),
    ]
    
    test_image_path = None
    for path in test_images:
        if os.path.exists(path):
            test_image_path = path
            break
    
    if test_image_path is None:
        test_image_path = os.path.join(project_root, 'zhitong', 'data', 'test_images', 'test_traffic.jpg')
        print(f"警告: 未找到测试图片，使用生成的测试图片")
        os.makedirs(os.path.dirname(test_image_path), exist_ok=True)
        test_img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.imwrite(test_image_path, test_img)
    
    print(f"测试图片: {test_image_path}")
    
    all_results = {
        'test_info': {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_image': test_image_path,
            'api_version': 'v2.0'
        },
        'tests': {}
    }
    
    all_results['tests']['model_loading'] = test_model_loading()
    all_results['tests']['hsv_color_recognition'] = test_hsv_color_recognition()
    all_results['tests']['traffic_light_detection'] = test_traffic_light_detection(test_image_path)
    all_results['tests']['vehicle_classification'] = test_vehicle_classification(test_image_path)
    all_results['tests']['multi_model_detection'] = test_multi_model_detection(test_image_path)
    all_results['tests']['violation_rules'] = test_violation_rules()
    
    passed_count = 0
    total_count = 0
    for test_name, test_result in all_results['tests'].items():
        if isinstance(test_result, dict):
            if test_result.get('success') is True:
                passed_count += 1
            elif isinstance(test_result.get('success'), dict):
                sub_passed = sum(1 for r in test_result.values() if r.get('success') is True or r.get('match'))
                passed_count += sub_passed
                total_count += len(test_result)
                continue
            total_count += 1
    
    if total_count == 0:
        total_count = len(all_results['tests'])
    
    all_results['summary'] = {
        'passed': passed_count,
        'total': total_count,
        'pass_rate': round(passed_count / total_count * 100, 2),
        'status': 'PASS' if passed_count == total_count else 'PARTIAL' if passed_count > 0 else 'FAIL'
    }
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"通过: {passed_count}/{total_count}")
    print(f"通过率: {all_results['summary']['pass_rate']}%")
    print(f"状态: {all_results['summary']['status']}")
    
    output_dir = os.path.join(project_root, 'test_results')
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"test_results_{time.strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n测试报告已保存: {output_file}")
    
    return all_results


if __name__ == "__main__":
    main()
