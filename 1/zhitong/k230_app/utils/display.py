# -*- coding: utf-8 -*-
"""
LCD显示模块
用于显示状态信息和检测结果
"""

import lcd
import image
import time


class Display:
    """LCD显示类"""

    def __init__(self):
        """初始化LCD显示"""
        # 初始化LCD
        lcd.init()

        # 创建显示用图像缓冲区
        self.width = 320
        self.height = 240
        self.img = image.Image(self.width, self.height, image.RGB565)

        # 颜色定义
        self.COLOR_RED = (255, 0, 0)
        self.COLOR_GREEN = (0, 255, 0)
        self.COLOR_BLUE = (0, 0, 255)
        self.COLOR_WHITE = (255, 255, 255)
        self.COLOR_BLACK = (0, 0, 0)
        self.COLOR_YELLOW = (255, 255, 0)

        # 字体大小
        self.FONT_SIZE_SMALL = 16
        self.FONT_SIZE_MEDIUM = 24
        self.FONT_SIZE_LARGE = 32

        print("[LCD显示] 初始化完成")

    def clear(self):
        """清空显示"""
        self.img.clear()

    def show_image(self, img, x=0, y=0, layer=lcd.LAYER_OSD0):
        """
        显示图像

        Args:
            img: 图像对象
            x: X坐标
            y: Y坐标
            layer: 显示层
        """
        lcd.display(img, x, y, layer)

    def draw_text(self, text, x, y, color=None, font_size=None):
        """
        绘制文本

        Args:
            text: 文本内容
            x: X坐标
            y: Y坐标
            color: 颜色 (r, g, b)
            font_size: 字体大小
        """
        if color is None:
            color = self.COLOR_WHITE
        if font_size is None:
            font_size = self.FONT_SIZE_MEDIUM

        self.img.draw_string(x, y, text, color=color, scale=font_size // 16)

    def draw_rect(self, x, y, w, h, color=None, thickness=2):
        """
        绘制矩形

        Args:
            x: X坐标
            y: Y坐标
            w: 宽度
            h: 高度
            color: 颜色
            thickness: 线条粗细
        """
        if color is None:
            color = self.COLOR_GREEN

        self.img.draw_rectangle(x, y, w, h, color=color, thickness=thickness)

    def draw_line(self, x1, y1, x2, y2, color=None, thickness=2):
        """
        绘制线条

        Args:
            x1: 起始X
            y1: 起始Y
            x2: 结束X
            y2: 结束Y
            color: 颜色
            thickness: 线条粗细
        """
        if color is None:
            color = self.COLOR_WHITE

        self.img.draw_line(x1, y1, x2, y2, color=color, thickness=thickness)

    def show_status(self, device_id, wifi_connected, detection_count,
                   frame_count=None, fps=None):
        """
        显示状态信息

        Args:
            device_id: 设备ID
            wifi_connected: WiFi是否连接
            detection_count: 今日检测数量
            frame_count: 当前帧号
            fps: 帧率
        """
        # 清空图像
        self.img.clear()

        # 绘制顶部状态栏
        self.img.draw_rectangle(0, 0, self.width, 30, color=self.COLOR_BLUE, thickness=30)

        # 设备ID
        self.draw_text(f"ID:{device_id}", 5, 5, self.COLOR_WHITE, self.FONT_SIZE_SMALL)

        # WiFi状态
        wifi_status = "ON" if wifi_connected else "OFF"
        wifi_color = self.COLOR_GREEN if wifi_connected else self.COLOR_RED
        self.draw_text(f"WIFI:{wifi_status}", 180, 5, wifi_color, self.FONT_SIZE_SMALL)

        # 当前时间
        current_time = time.strftime("%H:%M:%S")
        self.draw_text(current_time, 250, 5, self.COLOR_WHITE, self.FONT_SIZE_SMALL)

        # 检测统计
        self.draw_text(f"检测:{detection_count}", 5, 40, self.COLOR_YELLOW, self.FONT_SIZE_MEDIUM)

        # 帧率和帧号（如果有）
        if fps:
            self.draw_text(f"FPS:{fps:.1f}", 5, 70, self.COLOR_WHITE, self.FONT_SIZE_SMALL)

        if frame_count:
            self.draw_text(f"帧:{frame_count}", 100, 70, self.COLOR_WHITE, self.FONT_SIZE_SMALL)

    def show_detection_result(self, vehicles):
        """
        显示检测结果

        Args:
            vehicles: 车辆检测列表
        """
        # 在图像底部显示检测到的车辆
        y_offset = self.height - 30

        if vehicles:
            for i, v in enumerate(vehicles[:3]):  # 最多显示3辆
                plate = v.get('plate', '')
                label = v.get('label', '')
                conf = v.get('confidence', 0)

                text = f"{label}"
                if plate:
                    text = f"{plate}"

                self.draw_text(text, 5, y_offset - i * 25, self.COLOR_GREEN, self.FONT_SIZE_SMALL)
        else:
            self.draw_text("未检测到车辆", 5, y_offset, self.COLOR_WHITE, self.FONT_SIZE_SMALL)

    def show(self, sensor_img, vehicles=None, device_id="K230_001",
            wifi_connected=True, detection_count=0, fps=None):
        """
        综合显示（用于主循环）

        Args:
            sensor_img: 摄像头图像
            vehicles: 车辆检测列表
            device_id: 设备ID
            wifi_connected: WiFi连接状态
            detection_count: 今日检测数量
            fps: 帧率
        """
        # 如果有摄像头图像，先显示它
        if sensor_img:
            # 缩放到显示尺寸
            display_img = sensor_img.resize(320, 240)
            lcd.display(display_img)
        else:
            # 显示状态信息
            self.show_status(device_id, wifi_connected, detection_count, fps=fps)
            lcd.display(self.img)

        # 在图像上叠加检测框
        if vehicles:
            for v in vehicles:
                x, y, w, h = v.get('bbox', [0, 0, 0, 0])
                label = v.get('label', '')
                plate = v.get('plate', '')

                # 绘制检测框
                if sensor_img:
                    sensor_img.draw_rectangle(x, y, w, h, color=(0, 255, 0), thickness=2)

                    # 绘制标签
                    text = label
                    if plate:
                        text = f"{plate}"
                    sensor_img.draw_string(x, y - 20, text, color=(0, 255, 0), scale=2)