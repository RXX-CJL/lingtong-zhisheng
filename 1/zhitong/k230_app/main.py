# -*- coding: utf-8 -*-
"""
智瞳交管系统 - K230视觉识别应用
主程序入口

功能：
- 车辆检测（YOLOv8n）
- 车牌识别（LPD + 车牌识别）
- 语音播报（TTS）
- 数据上报（HTTP）
- 状态显示（LCD）
"""

import sensor
import lcd
import time
import os

# 导入配置
from config import Config

# 导入检测器
from detectors.vehicle_detector import VehicleDetector
from detectors.plate_recognizer import PlateRecognizer

# 导入工具模块
from utils.wifi import connect_wifi, get_wifi_status
from utils.http_client import HttpClient
from utils.tts_speaker import Speaker
from utils.display import Display


class ZhitongSystem:
    """智瞳系统主类"""

    def __init__(self):
        """初始化智瞳系统"""
        print("=" * 50)
        print("[系统] 智瞳交管系统 K230 视觉识别应用")
        print("[系统] 初始化中...")
        print("=" * 50)

        # 配置
        self.config = Config

        # 状态
        self.frame_count = 0
        self.detection_count = 0
        self.last_heartbeat = 0
        self.last_detection_time = 0

        # 检测间隔
        self.detect_interval = Config.DETECT_INTERVAL

        # 初始化组件
        self.vehicle_detector = None
        self.plate_recognizer = None
        self.http_client = None
        self.speaker = None
        self.display = None

        # WiFi状态
        self.wifi_connected = False

    def initialize(self):
        """初始化所有组件"""
        print("[系统] 1. 初始化摄像头...")

        # 初始化摄像头
        sensor.reset()
        sensor.set_pixformat(sensor.RGB565)
        sensor.set_framesize(sensor.VGA)  # 640x480
        sensor.set_brightness(0)  # 亮度
        sensor.set_contrast(0)    # 对比度
        sensor.set_saturation(0)   # 饱和度
        sensor.run(1)

        print("[系统]    摄像头初始化完成")

        print("[系统] 2. 初始化LCD显示...")
        self.display = Display()
        print("[系统]    LCD初始化完成")

        print("[系统] 3. 连接WiFi...")
        self.wifi_connected = connect_wifi(
            Config.WIFI_SSID,
            Config.WIFI_PASSWORD,
            Config.WIFI_TIMEOUT
        )

        if self.wifi_connected:
            print("[系统]    WiFi连接成功")
        else:
            print("[系统]    WiFi连接失败，继续运行")

        print("[系统] 4. 初始化HTTP客户端...")
        self.http_client = HttpClient(Config.API_BASE_URL)
        print("[系统]    HTTP客户端初始化完成")

        print("[系统] 5. 初始化车辆检测器...")
        try:
            self.vehicle_detector = VehicleDetector(
                kmodel_path=Config.YOLOV8N_MODEL,
                confidence_threshold=Config.CONFIDENCE_THRESHOLD,
                rgb888p_size=[Config.SENSOR_WIDTH, Config.SENSOR_HEIGHT],
                model_input_size=Config.MODEL_INPUT_SIZE
            )
            print("[系统]    车辆检测器初始化完成")
        except Exception as e:
            print(f"[系统]    车辆检测器初始化失败: {e}")
            print("[系统]    警告: 车辆检测功能不可用")

        print("[系统] 6. 初始化车牌识别器...")
        try:
            self.plate_recognizer = PlateRecognizer(
                det_model=Config.LPD_MODEL,
                rec_model=Config.LICENCE_RECO_MODEL
            )
            print("[系统]    车牌识别器初始化完成")
        except Exception as e:
            print(f"[系统]    车牌识别器初始化失败: {e}")
            print("[系统]    警告: 车牌识别功能不可用")

        print("[系统] 7. 初始化TTS语音...")
        self.speaker = Speaker()
        if Config.TTS_ENABLED:
            self.speaker.enable()
            print("[系统]    TTS语音初始化完成")
        else:
            print("[系统]    TTS语音已禁能")

        print("[系统] 8. 注册设备...")
        if self.wifi_connected and self.http_client:
            self.http_client.register_device(
                device_id=Config.DEVICE_ID,
                device_name=Config.DEVICE_NAME,
                device_type="k230"
            )

        print("[系统] 9. 发送初始心跳...")
        self.send_heartbeat()

        # 创建保存目录
        try:
            os.mkdir(Config.IMAGE_SAVE_PATH)
        except:
            pass

        print("=" * 50)
        print("[系统] 初始化完成!")
        print(f"[系统] 设备ID: {Config.DEVICE_ID}")
        print(f"[系统] 设备名称: {Config.DEVICE_NAME}")
        print("=" * 50)

        # 语音播报启动
        if Config.TTS_ENABLED:
            self.speaker.speak("智瞳系统启动")

    def send_heartbeat(self):
        """发送设备心跳"""
        if self.wifi_connected and self.http_client:
            self.http_client.send_heartbeat(
                device_id=Config.DEVICE_ID,
                status="online"
            )
            self.last_heartbeat = time.time()

    def process_frame(self, img):
        """
        处理单帧图像

        Args:
            img: 摄像头图像对象

        Returns:
            list: 检测到的车辆列表
        """
        vehicles = []

        # 定期进行车辆检测
        if self.frame_count % self.detect_interval == 0:
            if self.vehicle_detector:
                vehicles = self.vehicle_detector.detect(img)

                # 处理检测到的车辆
                if vehicles:
                    self.handle_detections(img, vehicles)

        return vehicles

    def handle_detections(self, img, vehicles):
        """
        处理检测结果

        Args:
            img: 图像对象
            vehicles: 车辆列表
        """
        current_time = time.time()

        # 过滤车辆类别
        filtered_vehicles = [
            v for v in vehicles
            if v['class'] in Config.VEHICLE_CLASSES
        ]

        if not filtered_vehicles:
            return

        print(f"[检测] 发现 {len(filtered_vehicles)} 辆车")

        # 车牌识别
        for vehicle in filtered_vehicles:
            if self.plate_recognizer:
                plate = self.plate_recognizer.recognize(img, vehicle['bbox'])
                vehicle['plate'] = plate

        # 语音播报
        if Config.TTS_ENABLED and self.speaker:
            if len(filtered_vehicles) == 1:
                v = filtered_vehicles[0]
                plate = v.get('plate')
                if plate:
                    self.speaker.speak_vehicle_detected(plate)
                else:
                    self.speaker.speak_vehicle_detected(vehicle_type=v.get('label'))
            else:
                self.speaker.speak_multiple_vehicles(len(filtered_vehicles))

        # 数据上报（限制频率）
        if current_time - self.last_detection_time > 5:  # 至少间隔5秒
            if self.wifi_connected and self.http_client:
                self.http_client.report_detection(
                    device_id=Config.DEVICE_ID,
                    device_name=Config.DEVICE_NAME,
                    detections=filtered_vehicles
                )
                self.last_detection_time = current_time

        # 保存图片
        if Config.SAVE_DETECTION_IMAGES:
            try:
                filename = f"{Config.IMAGE_SAVE_PATH}detect_{int(current_time)}.jpg"
                img.save(filename)
                print(f"[保存] 图片已保存: {filename}")
            except Exception as e:
                print(f"[保存] 保存失败: {e}")

        # 更新统计
        self.detection_count += len(filtered_vehicles)

    def run(self):
        """运行主循环"""
        print("[系统] 开始主循环...")

        last_fps_time = time.time()
        fps = 0
        frame_count = 0

        while True:
            # 捕获摄像头图像
            img = sensor.snapshot()

            # 处理帧
            vehicles = self.process_frame(img)

            # 显示画面
            if self.display:
                self.display.show(
                    sensor_img=img,
                    vehicles=vehicles,
                    device_id=Config.DEVICE_ID,
                    wifi_connected=self.wifi_connected,
                    detection_count=self.detection_count,
                    fps=fps
                )

            # 计算FPS
            frame_count += 1
            self.frame_count += 1
            current_time = time.time()

            if current_time - last_fps_time >= 1.0:
                fps = frame_count / (current_time - last_fps_time)
                frame_count = 0
                last_fps_time = current_time

            # 定时心跳
            if current_time - self.last_heartbeat >= Config.HEARTBEAT_INTERVAL:
                self.send_heartbeat()

            # 小延时，防止处理过快
            time.sleep_ms(10)


def main():
    """主函数入口"""
    try:
        # 创建系统实例
        system = ZhitongSystem()

        # 初始化
        system.initialize()

        # 运行主循环
        system.run()

    except Exception as e:
        print(f"[系统] 发生错误: {e}")
        import sys
        sys.print_exception(e)

    finally:
        print("[系统] 系统退出")


if __name__ == "__main__":
    main()