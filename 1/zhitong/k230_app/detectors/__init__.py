# -*- coding: utf-8 -*-
"""
detectors包
车辆检测和车牌识别模块
"""

from .vehicle_detector import VehicleDetector
from .plate_recognizer import PlateRecognizer

__all__ = ['VehicleDetector', 'PlateRecognizer']