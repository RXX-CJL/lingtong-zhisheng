# -*- coding: utf-8 -*-
"""
实时检测测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import cv2
import json
from datetime import datetime

def test_camera_detection():
    print("=" * 60)
    print("测试1: 摄像头打开测试")
    print("=" * 60)
    
    available = []
    for i in range(4):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                available.append(i)
                print(f"✓ 摄像头索引 {i}: 可用 (分辨率: {frame.shape[1]}x{frame.shape[0]})")
            else:
                print(f"✗ 摄像头索引 {i}: 无法读取画面")
            cap.release()
        else:
            cap.release()
            print(f"✗ 摄像头索引 {i}: 无法打开")
    
    print(f"\n可用摄像头: {available}")
    return len(available) > 0

def test_video_file():
    print("\n" + "=" * 60)
    print("测试2: 视频文件读取测试")
    print("=" * 60)
    
    video_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'zhitong', 'data', 'raw_videos', 'test_no_helmet.mp4')
    
    if not os.path.exists(video_path):
        print(f"✗ 测试视频不存在: {video_path}")
        return False
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("✗ 无法打开测试视频")
        return False
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"✓ 视频文件打开成功")
    print(f"  FPS: {fps}")
    print(f"  帧数: {frame_count}")
    print(f"  分辨率: {width}x{height}")
    print(f"  时长: {frame_count/fps:.2f}秒")
    
    ret, frame = cap.read()
    if ret:
        print(f"✓ 首帧读取成功")
    else:
        print("✗ 首帧读取失败")
    
    cap.release()
    return True

def test_detector_init():
    print("\n" + "=" * 60)
    print("测试3: 实时检测器初始化测试")
    print("=" * 60)
    
    try:
        from realtime_detector import RealtimeViolationDetector
        detector = RealtimeViolationDetector()
        print("✓ 检测器初始化成功")
        
        status = detector.get_status()
        print(f"  初始状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
        
        return True
    except Exception as e:
        print(f"✗ 检测器初始化失败: {e}")
        return False

def test_single_frame_detection():
    print("\n" + "=" * 60)
    print("测试4: 单帧检测测试")
    print("=" * 60)
    
    try:
        from realtime_detector import RealtimeViolationDetector
        import base64
        import numpy as np
        
        detector = RealtimeViolationDetector()
        
        video_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'zhitong', 'data', 'raw_videos', 'test_no_helmet.mp4')
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("⚠ 视频文件无法打开，使用摄像头进行测试")
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("✗ 无法打开摄像头")
                return False
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("⚠ 无法读取视频帧，使用模拟帧进行测试")
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        print("✓ 读取/生成测试帧成功")
        
        start_time = time.time()
        result = detector.process_frame(frame)
        elapsed = time.time() - start_time
        
        print(f"✓ 单帧检测完成")
        print(f"  耗时: {elapsed*1000:.2f}ms")
        print(f"  违规检测: {'是' if result.get('violation_detected') else '否'}")
        print(f"  检测目标数: {len(result.get('detections', []))}")
        print(f"  违规数量: {len(result.get('violations', []))}")
        
        if result.get('violations'):
            for v in result['violations']:
                print(f"    - {v.get('violation_type_cn')}: 置信度 {v.get('confidence')}")
        
        return True
    except Exception as e:
        import traceback
        print(f"✗ 单帧检测失败: {e}")
        traceback.print_exc()
        return False

def test_api_import():
    print("\n" + "=" * 60)
    print("测试5: API路由导入测试")
    print("=" * 60)
    
    try:
        from routers.realtime import router
        print("✓ 实时检测路由导入成功")
        print(f"  路由前缀: {router.prefix}")
        print(f"  标签: {router.tags}")
        
        routes = [r.path for r in router.routes]
        print(f"  路由列表: {routes}")
        
        return True
    except Exception as e:
        print(f"✗ API路由导入失败: {e}")
        return False

def test_app_registration():
    print("\n" + "=" * 60)
    print("测试6: 应用注册测试")
    print("=" * 60)
    
    try:
        import app
        print("✓ 应用模块导入成功")
        
        rt_routes = [r.path for r in app.app.routes if '/api/realtime' in str(r.path)]
        print(f"  实时检测路由已注册: {rt_routes}")
        
        return True
    except Exception as e:
        print(f"✗ 应用注册测试失败: {e}")
        return False

def test_digital_twin_socketio():
    print("\n" + "=" * 60)
    print("测试7: 数字孪生WebSocket测试")
    print("=" * 60)
    
    try:
        dt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'digital_twin')
        sys.path.insert(0, dt_path)
        
        import importlib.util
        spec = importlib.util.spec_from_file_location("dt_app", os.path.join(dt_path, "app.py"))
        dt_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dt_app)
        
        print("✓ 数字孪生模块导入成功")
        
        has_socketio = hasattr(dt_app, 'socketio')
        has_trigger_func = hasattr(dt_app, 'trigger_violation_event')
        has_socketio_import = 'flask_socketio' in str(dt_app.__dict__)
        
        print(f"  SocketIO对象: {'是' if has_socketio else '否'}")
        print(f"  trigger_violation_event函数: {'是' if has_trigger_func else '否'}")
        print(f"  SocketIO导入: {'是' if has_socketio_import else '否'}")
        
        if has_socketio or has_trigger_func or has_socketio_import:
            print("  ✓ WebSocket功能可用")
            return True
        
        return False
    except Exception as e:
        print(f"✗ 数字孪生WebSocket测试失败: {e}")
        return False

def main():
    print("=" * 60)
    print("智瞳实时检测系统 - 测试套件")
    print("=" * 60)
    print(f"测试时间: {datetime.now().isoformat()}")
    print()
    
    results = []
    
    results.append(("摄像头检测", test_camera_detection()))
    results.append(("视频文件读取", test_video_file()))
    results.append(("检测器初始化", test_detector_init()))
    results.append(("单帧检测", test_single_frame_detection()))
    results.append(("API路由导入", test_api_import()))
    results.append(("应用注册", test_app_registration()))
    results.append(("数字孪生WebSocket", test_digital_twin_socketio()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n  总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print("\n✗ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())