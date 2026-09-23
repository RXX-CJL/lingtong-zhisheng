# -*- coding: utf-8 -*-
"""
HTTP客户端模块
用于数据上报和设备心跳
"""

import http.client
import json
import time
import ujson


class HttpClient:
    """HTTP客户端类"""

    def __init__(self, base_url):
        """
        初始化HTTP客户端

        Args:
            base_url: API服务器基础URL，如 "http://192.168.1.100:8001"
        """
        self.base_url = base_url

        # 解析服务器地址
        if base_url.startswith("http://"):
            self.host = base_url.replace("http://", "")
        elif base_url.startswith("https://"):
            self.host = base_url.replace("https://", "")
        else:
            self.host = base_url

        # 分离host和端口
        if ":" in self.host:
            parts = self.host.split(":")
            self.host = parts[0]
            self.port = int(parts[1]) if len(parts) > 1 else 80
        else:
            self.port = 80

        self.timeout = 10  # 超时时间(秒)

        print(f"[HTTP客户端] 初始化完成，服务器: {self.host}:{self.port}")

    def _send_request(self, method, path, data=None, headers=None):
        """
        发送HTTP请求

        Args:
            method: 请求方法 GET/POST/PUT/DELETE
            path: 请求路径
            data: 请求数据(dict)
            headers: 请求头

        Returns:
            dict: 响应数据，失败返回None
        """
        try:
            conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)

            # 设置默认请求头
            if headers is None:
                headers = {}
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/json'

            # 发送请求
            if data:
                body = json.dumps(data)
                conn.request(method, path, body, headers)
            else:
                conn.request(method, path, headers=headers)

            # 获取响应
            response = conn.getresponse()
            result = response.read().decode('utf-8')

            conn.close()

            # 解析响应
            if response.status in (200, 201):
                try:
                    return json.loads(result)
                except:
                    return {'success': True, 'data': result}
            else:
                print(f"[HTTP客户端] 请求失败: {response.status} - {result}")
                return None

        except Exception as e:
            print(f"[HTTP客户端] 请求异常: {e}")
            return None

    def send_heartbeat(self, device_id, status="online", battery_level=None, temperature=None):
        """
        发送设备心跳

        Args:
            device_id: 设备ID
            status: 设备状态
            battery_level: 电池电量(%)
            temperature: 温度(℃)

        Returns:
            bool: 是否成功
        """
        data = {
            "device_id": device_id,
            "status": status
        }

        if battery_level is not None:
            data["battery_level"] = battery_level
        if temperature is not None:
            data["temperature"] = temperature

        result = self._send_request("POST", "/api/devices/heartbeat", data)

        if result:
            print(f"[HTTP客户端] 心跳发送成功")
            return True
        else:
            print(f"[HTTP客户端] 心跳发送失败")
            return False

    def register_device(self, device_id, device_name, device_type="k230",
                       location=None, latitude=None, longitude=None):
        """
        注册设备

        Args:
            device_id: 设备ID
            device_name: 设备名称
            device_type: 设备类型
            location: 位置描述
            latitude: 纬度
            longitude: 经度

        Returns:
            bool: 是否成功
        """
        data = {
            "device_id": device_id,
            "name": device_name,
            "device_type": device_type
        }

        if location:
            data["location"] = location
        if latitude is not None:
            data["latitude"] = latitude
        if longitude is not None:
            data["longitude"] = longitude

        result = self._send_request("POST", "/api/devices/register", data)

        if result:
            print(f"[HTTP客户端] 设备注册成功")
            return True
        else:
            print(f"[HTTP客户端] 设备注册失败")
            return False

    def report_detection(self, device_id, device_name, detections, plate=None,
                        image=None, latitude=None, longitude=None):
        """
        上报检测数据

        Args:
            device_id: 设备ID
            device_name: 设备名称
            detections: 检测结果列表
            plate: 车牌号
            image: 图像对象（可选）
            latitude: 纬度
            longitude: 经度

        Returns:
            bool: 是否成功
        """
        from config import Config

        # 格式化检测数据
        formatted_detections = []
        for det in detections:
            formatted_detections.append({
                'type': det.get('label', 'unknown'),
                'plate': det.get('plate', plate) or '',
                'confidence': det.get('confidence', 0),
                'bbox': det.get('bbox', [0, 0, 0, 0])
            })

        # 构建请求数据
        data = {
            "device_id": device_id,
            "device_name": device_name,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "detections": formatted_detections
        }

        # 添加位置信息
        if latitude is not None and longitude is not None:
            data["latitude"] = latitude
            data["longitude"] = longitude
        elif latitude is not None:
            data["latitude"] = latitude
        elif longitude is not None:
            data["longitude"] = longitude

        # 添加图片路径（如果保存了）
        if image:
            # 实际应用中应该先上传图片获取URL
            # 这里简化处理
            image_path = f"/sdcard/detections/detect_{int(time.time())}.jpg"
            data["image_url"] = image_path

        result = self._send_request("POST", "/api/violations/upload", data)

        if result:
            print(f"[HTTP客户端] 检测数据上报成功")
            return True
        else:
            print(f"[HTTP客户端] 检测数据上报失败")
            return False