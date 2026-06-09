import requests
import json
import base64
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """测试健康检查"""
    print("测试健康检查...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()

def create_test_image_base64():
    """创建测试图片的Base64数据"""
    # 这里使用一个简单的1x1像素的红色图片作为示例
    # 实际项目中应该使用真实的违规图片
    red_pixel = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'
    return base64.b64encode(red_pixel).decode('utf-8')

def test_submit_violation():
    """测试提交违规证据"""
    print("测试提交违规证据...")
    
    violation_data = {
        "violation_type": "red_light",
        "track_id": 1,
        "confidence": 0.95,
        "position": {
            "x": 100,
            "y": 200,
            "width": 50,
            "height": 100
        },
        "timestamp": datetime.now().isoformat(),
        "image_data": create_test_image_base64(),
        "additional_info": {
            "location": "北京市朝阳区",
            "camera_id": "CAM001"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/violations/submit", json=violation_data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()
    return response.json()

def test_get_violation_list():
    """测试获取违规列表"""
    print("测试获取违规列表...")
    
    params = {
        "page": 1,
        "page_size": 10
    }
    
    response = requests.get(f"{BASE_URL}/api/violations/list", params=params)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"总数: {result['total']}")
    print(f"当前页: {result['page']}")
    print(f"违规数量: {len(result['items'])}")
    print()

def test_get_statistics():
    """测试获取统计信息"""
    print("测试获取统计信息...")
    
    response = requests.get(f"{BASE_URL}/api/violations/statistics/summary")
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"总违规数: {result['total_count']}")
    print(f"按类型统计: {result['by_type']}")
    print(f"按状态统计: {result['by_status']}")
    print()

def test_wechat_submit():
    """测试微信小程序提交"""
    print("测试微信小程序提交...")
    
    wechat_data = {
        "openid": "test_openid_123456",
        "violation_data": {
            "violation_type": "no_helmet",
            "track_id": 2,
            "confidence": 0.88,
            "position": {
                "x": 150,
                "y": 250,
                "width": 60,
                "height": 120
            },
            "timestamp": datetime.now().isoformat(),
            "image_data": create_test_image_base64(),
            "additional_info": {
                "location": "上海市浦东新区"
            }
        },
        "device_info": {
            "platform": "ios",
            "version": "1.0.0"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/wechat/violation/submit", json=wechat_data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()

def main():
    """主测试函数"""
    print("=" * 50)
    print("智瞳API功能测试")
    print("=" * 50)
    print()
    
    try:
        # 基础测试
        test_health_check()
        
        # 违规证据测试
        test_submit_violation()
        test_get_violation_list()
        test_get_statistics()
        
        # 微信小程序测试
        test_wechat_submit()
        
        print("=" * 50)
        print("所有测试完成！")
        print("=" * 50)
        
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到API服务")
        print("请确保API服务已启动: python app.py")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")

if __name__ == "__main__":
    main()