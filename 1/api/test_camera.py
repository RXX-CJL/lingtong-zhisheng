# -*- coding: utf-8 -*-
"""
摄像头测试脚本
"""
import cv2
import sys

def test_cameras(max_cameras=4):
    """测试可用摄像头"""
    available_cameras = []
    
    for i in range(max_cameras):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                height, width = frame.shape[:2]
                available_cameras.append({
                    'index': i,
                    'width': width,
                    'height': height,
                    'fps': cap.get(cv2.CAP_PROP_FPS),
                    'description': f'摄像头 {i}: {width}x{height}'
                })
                print(f"✓ 摄像头索引 {i} 可用，分辨率: {width}x{height}, FPS: {cap.get(cv2.CAP_PROP_FPS):.1f}")
            else:
                print(f"✗ 摄像头索引 {i} 打开失败")
            cap.release()
        else:
            print(f"✗ 摄像头索引 {i} 不可用")
    
    return available_cameras

if __name__ == "__main__":
    print("=" * 60)
    print("摄像头测试")
    print("=" * 60)
    
    cameras = test_cameras()
    
    if cameras:
        print(f"\n找到 {len(cameras)} 个可用摄像头:")
        for cam in cameras:
            print(f"  - 索引 {cam['index']}: {cam['width']}x{cam['height']}")
        
        print("\n测试实时捕获...")
        test_index = cameras[0]['index']
        cap = cv2.VideoCapture(test_index)
        
        frame_count = 0
        import time
        start_time = time.time()
        success_frames = 0
        
        while frame_count < 10:
            ret, frame = cap.read()
            frame_count += 1
            if ret:
                success_frames += 1
                save_path = f"camera_test_frame_{frame_count}.jpg"
                cv2.imwrite(save_path, frame)
                print(f"  帧 {frame_count}: 成功, 保存到 {save_path}")
        
        elapsed_time = time.time() - start_time
        fps = success_frames / elapsed_time
        
        cap.release()
        print(f"\n测试完成: {success_frames}/{frame_count} 帧成功, {elapsed_time:.2f}秒, FPS: {fps:.2f}")
    else:
        print("\n未找到可用摄像头")
        sys.exit(1)
