"""测试APIClient与系统的集成"""
import sys
import time
import numpy as np
import cv2
from config import Config
from violation_detector import Violation, ViolationType
from api_client import APIClient

def test_api_client_integration():
    """测试API客户端集成"""
    print("=" * 60)
    print("测试APIClient与系统集成")
    print("=" * 60)
    
    # 1. 初始化配置和API客户端
    print("\n[1] 初始化配置和API客户端...")
    config = Config()
    api_client = APIClient(config)
    print("✓ API客户端初始化成功")
    
    # 2. 创建测试违规对象
    print("\n[2] 创建测试违规对象...")
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(test_frame, (100, 100), (200, 300), (0, 255, 0), 2)
    cv2.putText(test_frame, "TEST VIOLATION", (100, 400), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    violation = Violation(
        violation_type=ViolationType.RED_LIGHT,
        track_id=1,
        frame=test_frame,
        confidence=0.95,
        position=(100, 100, 100, 200),
        timestamp=time.time(),
        additional_info={
            'location': '测试位置',
            'camera_id': 'TEST_001',
            'test_mode': True
        }
    )
    print(f"✓ 违规对象创建成功")
    print(f"  类型: {violation.violation_type}")
    print(f"  跟踪ID: {violation.track_id}")
    print(f"  置信度: {violation.confidence}")
    
    # 3. 提交违规到队列
    print("\n[3] 提交违规到上传队列...")
    api_client.submit_violation(violation, test_frame)
    print("✓ 违规已提交到队列")
    
    # 4. 等待上传处理
    print("\n[4] 等待上传处理...")
    print("  提示: 上传将在后台线程中处理")
    time.sleep(2)
    
    # 5. 停止API客户端
    print("\n[5] 停止API客户端...")
    api_client.stop()
    print("✓ API客户端已停止")
    
    # 6. 验证结果
    print("\n[6] 验证结果...")
    log_file = "output/logs/api_upload_error.log"
    import os
    if os.path.exists(log_file):
        print(f"⚠ 发现错误日志文件: {log_file}")
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                print("最后10行日志:")
                for line in lines[-10:]:
                    print(f"  {line.strip()}")
    else:
        print("✓ 未发现错误日志，上传可能成功")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n提示: ")
    print("1. 如果后端API服务正在运行 http://127.0.0.1:8000")
    print("2. 违规证据应该已经成功提交到后端")
    print("3. 可以通过 http://127.0.0.1:8000/docs 查看API文档")
    print("4. 可以通过 http://127.0.0.1:8000/api/violations/list 查看提交的数据")

if __name__ == '__main__':
    try:
        test_api_client_integration()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
