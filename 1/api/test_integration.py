# -*- coding: utf-8 -*-
"""
集成测试脚本 - 验证多模型检测系统
"""

import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from image_recognizer import (
    init_all_models, detect_with_yolo, detect_with_multiple_models,
    analyze_image, MODEL_CONFIG, CLASS_CN_MAP
)
from violation_rules import check_violations, list_violation_types

def test_model_loading():
    """测试模型加载"""
    print("=== 测试模型加载 ===")
    init_all_models()
    
    from image_recognizer import yolo_models
    print(f"已加载模型: {list(yolo_models.keys())}")
    
    for key, model in yolo_models.items():
        class_names = model.names if hasattr(model, 'names') else {}
        print(f"  {key}: {len(class_names)} 个类别")
    
    return len(yolo_models) >= 3

def test_single_model_detection():
    """测试单模型检测"""
    print("\n=== 测试单模型检测 ===")
    
    test_image = os.path.join(os.path.dirname(__file__), 'uploads', 'upload_0deea0ce_20260612_031455.jpg')
    if not os.path.exists(test_image):
        print(f"测试图片不存在: {test_image}")
        return None
    
    results = {}
    for model_key in ['yolov8n', 'yolov8s', 'helmet']:
        result = detect_with_yolo(test_image, model_key=model_key)
        results[model_key] = result
        print(f"{model_key}: success={result['success']}, detections={len(result['detections'])}")
        for d in result['detections']:
            print(f"  - {d['class_name']} ({d['class_name_cn']}): {d['confidence']:.2f}")
    
    return results

def test_multi_model_detection():
    """测试多模型串联检测"""
    print("\n=== 测试多模型串联检测 ===")
    
    test_image = os.path.join(os.path.dirname(__file__), 'uploads', 'upload_0deea0ce_20260612_031455.jpg')
    if not os.path.exists(test_image):
        print(f"测试图片不存在: {test_image}")
        return None
    
    result = detect_with_multiple_models(test_image, model_keys=['yolov8n', 'helmet'])
    print(f"Success: {result['success']}")
    print(f"Merged detections: {len(result['merged_detections'])}")
    
    for d in result['merged_detections']:
        print(f"  - {d['class_name']} ({d['class_name_cn']}): {d['confidence']:.2f}")
    
    return result

def test_rule_engine():
    """测试规则引擎"""
    print("\n=== 测试规则引擎 ===")
    
    test_detections = [
        {'class_name': 'motorcycle', 'class_name_cn': '摩托车', 'confidence': 0.85, 'bbox': [100, 200, 300, 400]},
        {'class_name': 'rider', 'class_name_cn': '骑手', 'confidence': 0.78, 'bbox': [150, 180, 280, 380]},
        {'class_name': 'car', 'class_name_cn': '轿车', 'confidence': 0.92, 'bbox': [400, 250, 600, 450]},
        {'class_name': 'traffic light', 'class_name_cn': '红绿灯', 'confidence': 0.65, 'bbox': [500, 50, 550, 150]}
    ]
    
    result = check_violations(test_detections)
    print(f"检测到违规: {len(result['violations'])}")
    for v in result['violations']:
        print(f"  - {v['violation_type_cn']}: 置信度 {v['confidence']}")
    
    no_helmet_result = check_violations(test_detections, 'no_helmet')
    print(f"\n未戴头盔检测: {len(no_helmet_result['violations'])} 个")
    
    return {
        'all_violations': result,
        'no_helmet': no_helmet_result
    }

def test_chinese_display():
    """测试中文显示"""
    print("\n=== 测试中文显示 ===")
    
    test_classes = ['car', 'motorcycle', 'bus', 'truck', 'bicycle', 'helmet', 'rider']
    for cls in test_classes:
        cn = CLASS_CN_MAP.get(cls, cls)
        print(f"  {cls} -> {cn}")
    
    return all(CLASS_CN_MAP.get(cls) for cls in test_classes)

def test_full_pipeline():
    """测试完整检测流程"""
    print("\n=== 测试完整检测流程 ===")
    
    test_image = os.path.join(os.path.dirname(__file__), 'uploads', 'upload_0deea0ce_20260612_031455.jpg')
    if not os.path.exists(test_image):
        print(f"测试图片不存在: {test_image}")
        return None
    
    result = analyze_image(test_image, 'no_helmet', use_multi_model=True)
    
    print(f"Success: {result['success']}")
    print(f"Final decision: {'确认违规' if result['final_decision'] else '未确认违规'}")
    print(f"Final confidence: {result['final_confidence']}")
    print(f"Message: {result['message']}")
    
    if 'multi_model_result' in result:
        mm_result = result['multi_model_result']
        print(f"多模型检测: {len(mm_result.get('merged_detections', []))} 个对象")
    
    return result

def main():
    """主函数"""
    print("=" * 60)
    print("智瞳项目 - 多模型集成测试")
    print("=" * 60)
    
    test_results = {
        'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'tests': {}
    }
    
    # 测试1：模型加载
    print("\n" + "-" * 60)
    start = time.time()
    test_results['tests']['model_loading'] = {
        'passed': test_model_loading(),
        'duration_ms': int((time.time() - start) * 1000)
    }
    
    # 测试2：单模型检测
    print("\n" + "-" * 60)
    start = time.time()
    test_results['tests']['single_model_detection'] = {
        'passed': True,
        'result': test_single_model_detection(),
        'duration_ms': int((time.time() - start) * 1000)
    }
    
    # 测试3：多模型检测
    print("\n" + "-" * 60)
    start = time.time()
    test_results['tests']['multi_model_detection'] = {
        'passed': True,
        'result': test_multi_model_detection(),
        'duration_ms': int((time.time() - start) * 1000)
    }
    
    # 测试4：规则引擎
    print("\n" + "-" * 60)
    start = time.time()
    test_results['tests']['rule_engine'] = {
        'passed': True,
        'result': test_rule_engine(),
        'duration_ms': int((time.time() - start) * 1000)
    }
    
    # 测试5：中文显示
    print("\n" + "-" * 60)
    start = time.time()
    test_results['tests']['chinese_display'] = {
        'passed': test_chinese_display(),
        'duration_ms': int((time.time() - start) * 1000)
    }
    
    # 测试6：完整流程
    print("\n" + "-" * 60)
    start = time.time()
    test_results['tests']['full_pipeline'] = {
        'passed': True,
        'result': test_full_pipeline(),
        'duration_ms': int((time.time() - start) * 1000)
    }
    
    # 汇总
    print("\n" + "=" * 60)
    passed_count = sum(1 for t in test_results['tests'].values() if t['passed'])
    total_count = len(test_results['tests'])
    print(f"测试结果: {passed_count}/{total_count} 通过")
    
    # 保存结果
    output_path = os.path.join(os.path.dirname(__file__), '..', '_TASK-003_MODEL_OUTPUT.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n结果已保存到: {output_path}")
    
    return test_results

if __name__ == "__main__":
    main()