# -*- coding: utf-8 -*-
"""
车牌识别模块 - 基于 PaddleOCR + YOLO + 图像增强

支持:
- 蓝/绿/黄牌检测与颜色识别
- 模糊/低对比度图像增强
- 批量识别（配合多帧确认）
- 车牌格式校验

Git 参考:
- HyperLPR (szad670401/HyperLPR_python): 车牌颜色判断逻辑
- PaddleOCR 3.7.0: OCR 引擎
- K230 LPD_640.kmodel: 车牌检测参考（边缘端）
"""

import os
import re
import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# 尝试导入 PaddleOCR
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logger.warning("[LicensePlate] PaddleOCR 未安装，车牌识别功能将降级")

# 尝试导入 YOLO
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("[LicensePlate] ultralytics 未安装，车牌检测将降级")

# 中国省份简称（车牌首位字符）
PROVINCE_CHARS = set("京沪津渝冀晋蒙辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川贵云藏陕甘青宁新")

# 车牌正则（简化版：省份+字母+5~6位字母数字，支持新能源6位）
PLATE_PATTERN = re.compile(
    r'^[' + ''.join(PROVINCE_CHARS) + r']'
    r'[A-HJ-NP-Z]'
    r'[0-9A-HJ-NP-Z]{4,5}$'
)

# 车牌颜色 HSV 范围 (OpenCV H: 0-180, S: 0-255, V: 0-255)
PLATE_COLOR_HSV = {
    'blue': {
        'lower': np.array([100, 80, 80]),
        'upper': np.array([130, 255, 255]),
        'cn': '蓝牌'
    },
    'green': {
        'lower': np.array([35, 50, 50]),
        'upper': np.array([85, 255, 255]),
        'cn': '绿牌'
    },
    'yellow': {
        'lower': np.array([15, 80, 80]),
        'upper': np.array([35, 255, 255]),
        'cn': '黄牌'
    }
}


class LicensePlateRecognizer:
    """车牌识别器，支持检测+识别+颜色判断+图像增强"""

    def __init__(self, yolo_model_path: Optional[str] = None, use_gpu: bool = False):
        self._ocr_engine = None
        self._yolo_model = None
        self._use_gpu = use_gpu
        self._yolo_model_path = yolo_model_path

        self._init_ocr()
        self._init_yolo()

    def _init_ocr(self):
        """初始化 PaddleOCR 引擎"""
        if not PADDLEOCR_AVAILABLE:
            logger.error("[LicensePlate] PaddleOCR 不可用，OCR 功能降级")
            return
        try:
            self._ocr_engine = PaddleOCR(
                use_textline_orientation=True,
                lang='ch',
                text_rec_score_thresh=0.3,
                **{'device': 'gpu'} if self._use_gpu else {}
            )
            logger.info("[LicensePlate] PaddleOCR 初始化成功")
        except Exception as e:
            logger.error(f"[LicensePlate] PaddleOCR 初始化失败: {e}")
            self._ocr_engine = None

    def _init_yolo(self):
        """初始化 YOLO 模型用于车牌检测"""
        if not YOLO_AVAILABLE:
            logger.warning("[LicensePlate] ultralytics 不可用，使用传统方法检测车牌")
            return

        model_path = self._yolo_model_path
        if model_path is None:
            # 尝试默认路径
            default_path = os.path.join(os.path.dirname(__file__), 'yolov8n.pt')
            if os.path.exists(default_path):
                model_path = default_path

        if model_path and os.path.exists(model_path):
            try:
                self._yolo_model = YOLO(model_path)
                logger.info(f"[LicensePlate] YOLO 模型加载成功: {model_path}")
            except Exception as e:
                logger.warning(f"[LicensePlate] YOLO 加载失败: {e}")

    def detect_plate(self, image: np.ndarray) -> List[Dict]:
        """
        车牌定位，返回检测到的车牌区域列表

        Args:
            image: BGR 格式图像 (np.ndarray)

        Returns:
            [{'bbox': [x1,y1,x2,y2], 'confidence': float}, ...]
        """
        if image is None or image.size == 0:
            return []

        results = []

        # 方法1: YOLO 检测（如果有模型）
        if self._yolo_model is not None:
            try:
                det_results = self._yolo_model(image, verbose=False, conf=0.3)
                for r in det_results:
                    for box in r.boxes:
                        cls_name = r.names.get(int(box.cls), '')
                        if 'plate' in cls_name.lower() or cls_name.lower() == 'license_plate':
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            results.append({
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'confidence': float(box.conf),
                                'source': 'yolo'
                            })
            except Exception as e:
                logger.warning(f"[LicensePlate] YOLO 检测失败: {e}")

        # 方法2: 如果 YOLO 没检测到，用传统方法（边缘检测+形态学）
        if not results:
            results = self._detect_plate_traditional(image)

        # 按置信度排序，取最佳
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results

    def _detect_plate_traditional(self, image: np.ndarray) -> List[Dict]:
        """传统车牌检测方法：基于边缘检测+形态学+颜色过滤"""
        try:
            h, w = image.shape[:2]
            if h < 20 or w < 50:
                return []

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # 双边滤波去噪保边
            blur = cv2.bilateralFilter(gray, 5, 75, 75)

            # Sobel 边缘检测
            sobel_x = cv2.Sobel(blur, cv2.CV_64F, 1, 0, ksize=3)
            sobel_x = np.uint8(np.absolute(sobel_x))

            # 二值化
            _, binary = cv2.threshold(sobel_x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 形态学闭操作连接区域
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 5))
            closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

            # 查找轮廓
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            candidates = []
            for cnt in contours:
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect_ratio = cw / ch if ch > 0 else 0

                # 车牌宽高比通常在 2.0~5.5 之间
                if 2.0 < aspect_ratio < 5.5 and cw > 60 and ch > 15:
                    area = cw * ch
                    img_area = w * h
                    # 车牌面积不应太大或太小
                    if 0.005 < area / img_area < 0.5:
                        candidates.append({
                            'bbox': [x, y, x + cw, y + ch],
                            'confidence': 0.5,
                            'source': 'traditional'
                        })

            return candidates
        except Exception as e:
            logger.warning(f"[LicensePlate] 传统检测失败: {e}")
            return []

    def recognize_plate(self, image: np.ndarray) -> Dict:
        """
        识别单张车牌图像，返回车牌号

        Args:
            image: 车牌区域图像 (BGR)

        Returns:
            {'plate_number': str, 'confidence': float}
        """
        if image is None or image.size == 0:
            return {'plate_number': '', 'confidence': 0.0}

        if self._ocr_engine is None:
            return {'plate_number': '', 'confidence': 0.0}

        try:
            # 图像增强
            enhanced = self._enhance_plate_image(image)

            # PaddleOCR 识别
            # ★2026-11-07 由 DSH 修复（PaddleOCR 3.x 兼容，实测踩到）：
            #   原实现是 `self._ocr_engine.ocr(enhanced, cls=True)` + 按 2.x 的
            #   `[[ [box], (text, conf) ], ...]` 结构解析。PaddleOCR 3.7.0 实际行为：
            #     · ocr() 只是 predict() 的别名，**不接受 cls 关键字**
            #       -> TypeError: predict() got an unexpected keyword argument 'cls'
            #     · 这个异常被下面的 except 吞掉 -> 永远返回空车牌，且只留一行 warning
            #   实测证据（合成蓝牌 "JING A 12345"，F 盘缓存 + 关 mkldnn）：
            #     predict() 返回 [{'rec_texts': ['JING A 12345'], 'rec_scores': [0.99921]}]
            #   现在两种结构都兼容，且按版本选择调用方式。
            try:
                result = self._ocr_engine.predict(
                    cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
                    if enhanced.ndim == 3 and enhanced.shape[2] == 3 else enhanced
                )
            except AttributeError:
                # 极旧版本没有 predict()，退回 ocr()
                result = self._ocr_engine.ocr(enhanced)

            if not result:
                return {'plate_number': '', 'confidence': 0.0}

            texts = []
            total_conf = 0.0
            count = 0

            def _iter_text_conf(res_item):
                """把 2.x / 3.x 两种返回结构统一成 (text, score) 迭代器。"""
                if isinstance(res_item, dict):
                    # 3.x: {'rec_texts': [...], 'rec_scores': [...]}
                    t = res_item.get('rec_texts') or []
                    s = res_item.get('rec_scores') or []
                    for i, txt in enumerate(t):
                        yield txt, (s[i] if i < len(s) else 0.0)
                else:
                    # 2.x: [[box], (text, conf)] 的列表
                    for line in res_item or []:
                        if isinstance(line, (list, tuple)) and len(line) >= 2:
                            payload = line[1]
                            if isinstance(payload, (list, tuple)) and len(payload) >= 2:
                                yield payload[0], payload[1]

            for _res in result:
                for text, conf in _iter_text_conf(_res):
                    if text and conf > 0.3:
                        # 清理文本
                        cleaned = self._clean_plate_text(text)
                        if cleaned:
                            texts.append(cleaned)
                            total_conf += conf
                            count += 1

            if texts:
                plate_number = ''.join(texts)
                plate_number = plate_number.replace(' ', '').replace('-', '').replace('·', '')
                avg_conf = total_conf / count if count > 0 else 0.5

                # 格式校验
                if not self._validate_plate(plate_number):
                    avg_conf *= 0.5  # 格式不对，降低置信度

                return {'plate_number': plate_number, 'confidence': round(avg_conf, 4)}

            return {'plate_number': '', 'confidence': 0.0}

        except Exception as e:
            logger.warning(f"[LicensePlate] OCR 识别失败: {e}")
            return {'plate_number': '', 'confidence': 0.0}

    def recognize_plate_batch(self, images: List[np.ndarray]) -> List[Dict]:
        """
        批量识别车牌（配合多帧确认）

        Args:
            images: 车牌区域图像列表

        Returns:
            [{'plate_number': str, 'confidence': float}, ...]
        """
        return [self.recognize_plate(img) for img in images]

    def detect_and_recognize(self, image: np.ndarray) -> Dict:
        """
        一步完成：检测车牌 + 识别文字 + 判断颜色

        Args:
            image: BGR 格式完整图像

        Returns:
            {
                'plate_number': str,
                'confidence': float,
                'bbox': [x1,y1,x2,y2],
                'plate_color': str  # 'blue'/'green'/'yellow'/'unknown'
            }
        """
        if image is None or image.size == 0:
            return {
                'plate_number': '', 'confidence': 0.0,
                'bbox': [], 'plate_color': 'unknown'
            }

        # 检测车牌
        plates = self.detect_plate(image)
        if not plates:
            return {
                'plate_number': '', 'confidence': 0.0,
                'bbox': [], 'plate_color': 'unknown'
            }

        best_plate = plates[0]
        x1, y1, x2, y2 = best_plate['bbox']
        h, w = image.shape[:2]

        # 边界保护
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        if x2 - x1 < 20 or y2 - y1 < 10:
            return {
                'plate_number': '', 'confidence': 0.0,
                'bbox': best_plate['bbox'], 'plate_color': 'unknown'
            }

        # 裁剪车牌区域
        plate_crop = image[y1:y2, x1:x2]

        # 识别文字
        ocr_result = self.recognize_plate(plate_crop)

        # 判断颜色
        plate_color = self._detect_plate_color(plate_crop)

        return {
            'plate_number': ocr_result['plate_number'],
            'confidence': round(best_plate['confidence'] * ocr_result['confidence'], 4),
            'bbox': best_plate['bbox'],
            'plate_color': plate_color,
            'source': best_plate.get('source', 'unknown')
        }

    def _enhance_plate_image(self, image: np.ndarray) -> np.ndarray:
        """车牌图像增强：锐化+对比度提升"""
        try:
            # 放大图像（小图识别率低）
            h, w = image.shape[:2]
            if h < 32 or w < 100:
                scale = max(32 / h, 100 / w, 2.0)
                image = cv2.resize(image, None, fx=scale, fy=scale,
                                   interpolation=cv2.INTER_CUBIC)

            # CLAHE 自适应直方图均衡（提升对比度）
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
            l = clahe.apply(l)
            lab = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

            # 轻度锐化
            kernel = np.array([
                [0, -1, 0],
                [-1, 5, -1],
                [0, -1, 0]
            ], dtype=np.float32)
            enhanced = cv2.filter2D(enhanced, -1, kernel)

            return enhanced
        except Exception:
            return image

    def _detect_plate_color(self, plate_img: np.ndarray) -> str:
        """通过 HSV 颜色空间判断车牌颜色"""
        try:
            if plate_img is None or plate_img.size == 0:
                return 'unknown'

            hsv = cv2.cvtColor(plate_img, cv2.COLOR_BGR2HSV)
            color_counts = {}

            for color_name, ranges in PLATE_COLOR_HSV.items():
                mask = cv2.inRange(hsv, ranges['lower'], ranges['upper'])
                ratio = np.count_nonzero(mask) / mask.size
                color_counts[color_name] = ratio

            best_color = max(color_counts, key=color_counts.get)

            if color_counts[best_color] < 0.05:
                return 'unknown'

            return best_color
        except Exception:
            return 'unknown'

    def _clean_plate_text(self, text: str) -> str:
        """清理 OCR 识别结果"""
        # 去除常见误识别字符
        text = text.strip()
        # 只保留中文省份字符、字母、数字
        cleaned = ''
        for ch in text:
            if ch in PROVINCE_CHARS or ch.isalnum():
                cleaned += ch.upper()
        return cleaned

    def _validate_plate(self, plate: str) -> bool:
        """车牌格式校验"""
        if not plate or len(plate) < 7 or len(plate) > 8:
            return False
        return bool(PLATE_PATTERN.match(plate))

    def get_plate_color_cn(self, color: str) -> str:
        """获取车牌颜色中文名"""
        return PLATE_COLOR_HSV.get(color, {}).get('cn', '未知')

    @property
    def available(self) -> bool:
        """识别器是否可用"""
        return self._ocr_engine is not None


# 全局单例
_recognizer_instance: Optional[LicensePlateRecognizer] = None


def get_recognizer() -> LicensePlateRecognizer:
    """获取全局车牌识别器单例"""
    global _recognizer_instance
    if _recognizer_instance is None:
        _recognizer_instance = LicensePlateRecognizer()
    return _recognizer_instance


def detect_and_recognize_plate(image: np.ndarray) -> Dict:
    """便捷函数：检测并识别车牌"""
    return get_recognizer().detect_and_recognize(image)
