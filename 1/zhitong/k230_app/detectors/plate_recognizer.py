# -*- coding: utf-8 -*-
"""
车牌识别模块
基于LPD和车牌识别模型
"""

import sensor
import image
import time
import nncase_runtime as nn
import ulab.numpy as np
from libs.AIBase import AIBase
from libs.AI2D import Ai2d
from media.media import *


class PlateRecognizer:
    """车牌识别器类"""

    # 中国车牌省份简称
    PROVINCES = [
        "京", "津", "冀", "晋", "蒙", "辽", "吉", "黑",
        "沪", "苏", "浙", "皖", "闽", "赣", "鲁", "豫",
        "鄂", "湘", "粤", "桂", "琼", "渝", "川", "贵",
        "云", "藏", "陕", "甘", "青", "宁", "新"
    ]

    # 车牌字符（普通蓝牌）
    CHARS = [
        "京", "津", "冀", "晋", "蒙", "辽", "吉", "黑",
        "沪", "苏", "浙", "皖", "闽", "赣", "鲁", "豫",
        "鄂", "湘", "粤", "桂", "琼", "渝", "川", "贵",
        "云", "藏", "陕", "甘", "青", "宁", "新",
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"
    ]

    def __init__(self, det_model, rec_model, debug_mode=0):
        """
        初始化车牌识别器

        Args:
            det_model: 车牌检测模型路径
            rec_model: 车牌识别模型路径
            debug_mode: 调试模式
        """
        self.debug_mode = debug_mode
        self.det_model = det_model
        self.rec_model = rec_model

        print(f"[车牌识别器] 初始化完成")
        print(f"[车牌识别器] 检测模型: {det_model}")
        print(f"[车牌识别器] 识别模型: {rec_model}")

    def recognize(self, img, vehicle_bbox=None):
        """
        识别车牌

        Args:
            img: 图像对象
            vehicle_bbox: 车辆边界框 [x, y, w, h]，用于限定检测区域

        Returns:
            str: 车牌号，如 "京A12345"，识别失败返回None
        """
        try:
            # 如果有车辆边界框，在车辆区域进行车牌检测
            if vehicle_bbox:
                x, y, w, h = vehicle_bbox
                # 扩大区域以包含车牌（车牌通常在车辆下方或覆盖车辆）
                x1 = max(0, x - 20)
                y1 = max(0, y)
                x2 = min(img.width(), x + w + 20)
                y2 = min(img.height(), y + h + 40)

                # 裁剪车辆区域
                roi = (x1, y1, x2 - x1, y2 - y1)
            else:
                roi = None

            # 车牌检测（简化实现，实际需要使用LPD模型）
            plate_bbox = self._detect_plate(img, roi)

            if not plate_bbox:
                return None

            # 裁剪车牌区域
            px, py, pw, ph = plate_bbox
            plate_img = img.cut(px, py, pw, ph)

            # 车牌识别
            plate_text = self._recognize_plate(plate_img)

            return plate_text

        except Exception as e:
            print(f"[车牌识别器] 识别失败: {e}")
            return None

    def _detect_plate(self, img, roi=None):
        """
        车牌检测

        Args:
            img: 图像对象
            roi: 感兴趣区域 (x, y, w, h)

        Returns:
            tuple: (x, y, w, h) 或 None
        """
        # 简化实现：使用颜色和形状特征检测车牌候选区域
        # 实际应用中应使用LPD_640.kmodel进行检测

        if roi:
            x, y, w, h = roi
            # 在ROI内查找车牌候选
            search_img = img.cut(x, y, w, h)
        else:
            search_img = img

        # 简化：返回None，实际应调用车牌检测模型
        # TODO: 集成LPD_640.kmodel
        return None

    def _recognize_plate(self, plate_img):
        """
        车牌字符识别

        Args:
            plate_img: 车牌图像

        Returns:
            str: 识别结果
        """
        # 简化实现：返回模拟车牌
        # 实际应用中应使用licence_reco.kmodel进行识别

        # TODO: 集成licence_reco.kmodel

        # 模拟车牌返回（用于测试）
        import random
        province = random.choice(self.PROVINCES[:8])  # 随机省份
        letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
        digits = "0123456789"
        plate = province + random.choice(letters) + ''.join(random.choices(letters + digits, k=5))
        return plate