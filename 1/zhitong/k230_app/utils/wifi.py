# -*- coding: utf-8 -*-
"""
WiFi连接模块
基于K230 YbNetwork实现
"""

import network
import os
import utime as time


class WiFiManager:
    """WiFi管理器类"""

    def __init__(self):
        """初始化WiFi管理器"""
        self.sta = None
        self.is_connected = False
        self.ip_address = None
        self.ssid = None

    def connect(self, ssid, password, timeout=15000):
        """
        连接WiFi

        Args:
            ssid: WiFi名称
            password: WiFi密码
            timeout: 超时时间(ms)

        Returns:
            bool: 连接是否成功
        """
        try:
            print(f"[WiFi] 正在连接 {ssid}...")

            # 创建WLAN实例
            self.sta = network.WLAN(0)
            self.sta.active(False)  # 先关闭
            time.sleep_ms(100)
            self.sta.active(True)   # 再开启

            # 连接WiFi
            self.sta.connect(ssid, password)

            # 等待连接
            start_time = time.ticks_ms()
            while not self.sta.isconnected():
                time.sleep_us(1)
                if time.ticks_ms() - start_time > timeout:
                    print("[WiFi] 连接超时")
                    return False

            # 获取IP
            self.ip_address = self.sta.ifconfig()[0]
            self.ssid = ssid
            self.is_connected = True

            print(f"[WiFi] 连接成功!")
            print(f"[WiFi] IP地址: {self.ip_address}")

            return True

        except Exception as e:
            print(f"[WiFi] 连接失败: {e}")
            return False

    def disconnect(self):
        """断开WiFi连接"""
        try:
            if self.sta:
                self.sta.disconnect()
                self.sta.active(False)
                self.is_connected = False
                self.ip_address = None
                self.ssid = None
                print("[WiFi] 已断开连接")
        except Exception as e:
            print(f"[WiFi] 断开连接失败: {e}")

    def get_status(self):
        """
        获取WiFi状态

        Returns:
            dict: 状态信息
        """
        return {
            'connected': self.is_connected,
            'ssid': self.ssid,
            'ip': self.ip_address,
            'rssi': self.sta.ifconfig()[2] if self.sta else None
        }


# 全局WiFi管理器实例
_wifi_manager = WiFiManager()


def connect_wifi(ssid, password, timeout=15000):
    """
    连接WiFi（快捷函数）

    Args:
        ssid: WiFi名称
        password: WiFi密码
        timeout: 超时时间(ms)

    Returns:
        bool: 连接是否成功
    """
    return _wifi_manager.connect(ssid, password, timeout)


def get_wifi_status():
    """
    获取WiFi状态（快捷函数）

    Returns:
        dict: 状态信息
    """
    return _wifi_manager.get_status()