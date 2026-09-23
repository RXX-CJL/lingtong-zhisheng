import requests
import time
import json
import sys

BASE_URL = "http://localhost:8001"

def test_detect_cameras():
    print("=== 测试摄像头检测 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/stream/detect-cameras")
        result = response.json()
        print(f"状态: {'成功' if result.get('success') else '失败'}")
        print(f"消息: {result.get('message')}")
        if result.get('data'):
            cameras = result['data'].get('cameras', [])
            for cam in cameras:
                print(f"  摄像头 {cam['index']}: {cam['width']}x{cam['height']} @ {cam['fps']} FPS")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_start_local_camera():
    print("\n=== 测试启动本地摄像头 ===")
    try:
        response = requests.post(f"{BASE_URL}/api/stream/start-local", json={"camera_index": 0})
        result = response.json()
        print(f"状态: {'成功' if result.get('success') else '失败'}")
        print(f"消息: {result.get('message')}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_stream_info():
    print("\n=== 测试获取视频流信息 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/stream/info/local_camera")
        result = response.json()
        print(f"状态: {'成功' if result.get('success') else '失败'}")
        if result.get('data'):
            data = result['data']
            print(f"设备ID: {data.get('device_id')}")
            print(f"帧率: {data.get('fps')} FPS")
            print(f"时间戳: {data.get('timestamp')}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_list_streams():
    print("\n=== 测试获取视频流列表 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/stream/list")
        result = response.json()
        print(f"状态: {'成功' if result.get('success') else '失败'}")
        print(f"消息: {result.get('message')}")
        if result.get('data'):
            streams = result['data'].get('streams', [])
            for stream in streams:
                print(f"  设备: {stream['device_id']}, FPS: {stream['fps']}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_stop_local_camera():
    print("\n=== 测试停止本地摄像头 ===")
    try:
        response = requests.post(f"{BASE_URL}/api/stream/stop-local")
        result = response.json()
        print(f"状态: {'成功' if result.get('success') else '失败'}")
        print(f"消息: {result.get('message')}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_snapshot():
    print("\n=== 测试获取快照 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/stream/snapshot/local_camera")
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            print(f"状态: 成功")
            print(f"内容类型: {content_type}")
            print(f"图片大小: {len(response.content)} bytes")
            return True
        else:
            print(f"状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"错误: {e}")
        return False

def main():
    print("=" * 60)
    print("智瞳智慧交管系统 - 实时摄像头API测试")
    print("=" * 60)
    
    results = []
    
    results.append(("检测摄像头", test_detect_cameras()))
    
    input("\n按回车继续测试摄像头启动...")
    
    results.append(("启动本地摄像头", test_start_local_camera()))
    
    time.sleep(2)
    
    results.append(("获取视频流信息", test_stream_info()))
    results.append(("获取视频流列表", test_list_streams()))
    results.append(("获取快照", test_snapshot()))
    
    input("\n按回车停止摄像头...")
    
    results.append(("停止本地摄像头", test_stop_local_camera()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    report = {
        "test_name": "实时摄像头API测试",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": [{"name": name, "passed": success} for name, success in results],
        "summary": {
            "passed": passed,
            "total": total,
            "percentage": (passed / total) * 100
        }
    }
    
    with open("test_stream_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n测试报告已保存到 test_stream_results.json")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)