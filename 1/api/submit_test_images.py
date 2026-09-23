# -*- coding: utf-8 -*-
"""
端到端测试脚本 - 提交压线行驶违规记录
"""
import requests
import base64
import os
import json
import time
from datetime import datetime

API_URL = "http://127.0.0.1:8000/api/violations/submit"

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def submit_violation(image_path, idx):
    image_data = encode_image_to_base64(image_path)
    
    payload = {
        "violation_type": "lane_departure",
        "track_id": idx,  # 整数，不是字符串
        "confidence": 0.75 + (idx * 0.03),
        "position": {"x": 100 + idx*10, "y": 200 + idx*5, "width": 180, "height": 120},  # 字典，不是JSON字符串
        "timestamp": datetime.now().isoformat(),
        "image_data": image_data,
        "additional_info": {  # 字典，不是JSON字符串
            "location": "测试路口 #" + str(idx),
            "weather": "晴朗",
            "speed": str(40 + idx*3) + " km/h",
            "description": "车辆车轮越过白色实线行驶，检测到压线行为"
        }
    }
    
    print(f"[提交 #{idx}] 违规类型: lane_departure (压线行驶), 置信度: {payload['confidence']:.2%}")
    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        print(f"  HTTP 状态: {response.status_code}")
        print(f"  响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"  提交失败: {e}")
        return False

if __name__ == "__main__":
    # 图片来源目录 - 使用项目中已有的测试图片
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    
    # 可能的图片来源
    image_sources = [
        os.path.join(base_dir, "uploads"),
        os.path.join(project_root, "test_images"),
        os.path.join(project_root, "zhitong", "data", "processed_frames", "wrong_way"),
        os.path.join(project_root, "zhitong", "data", "processed_frames", "red_light"),
        os.path.join(project_root, "zhitong", "data", "processed_frames", "no_helmet"),
    ]
    
    # 收集可用图片
    available_images = []
    for src_dir in image_sources:
        if os.path.isdir(src_dir):
            for f in os.listdir(src_dir):
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    available_images.append(os.path.join(src_dir, f))
    
    # 如果还不够，给用户提示
    if len(available_images) < 5:
        print(f"⚠️  只找到 {len(available_images)} 张图片，不足5张。")
        print("请在以下目录放置图片文件：")
        for src in image_sources:
            print(f"  - {src}")
        exit(1)
    
    print("=" * 60)
    print("智瞳灵声 - 端到端测试")
    print("=" * 60)
    print(f"共找到 {len(available_images)} 张图片，使用前5张进行测试。")
    print(f"后端 API: {API_URL}")
    print("=" * 60)
    
    success_count = 0
    for i in range(5):
        if submit_violation(available_images[i], i+1):
            success_count += 1
        time.sleep(1)
    
    print("=" * 60)
    print(f"测试完成: 成功提交 {success_count}/5 条违规记录")
    print(f"请在浏览器打开 http://localhost:5173 查看 Web 管理端")
    print("在 '违规管理' 页面应该能看到这5条 '压线行驶' 违规记录")
    print("=" * 60)
