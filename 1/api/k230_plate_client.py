# -*- coding: utf-8 -*-
"""
K230 车牌检测/识别客户端（PC 端）

通过 HTTP 与 K230 板载服务通信，复用 K230 的 LPD_640.kmodel + licence_reco.kmodel。
K230 断开时自动降级，所有方法返回空结果，不阻塞主流程。

参考:
- K230 固件 YbRequests.py / upload_image.py 的 HTTP 通信模式
- 固件备份/apps/ai_objects/car_license_plate_recog 的车牌识别逻辑
"""

import os
import base64
import logging
from typing import List, Dict, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("[K230Client] requests 未安装")


class K230PlateClient:
    """K230 车牌检测/识别 HTTP 客户端"""

    def __init__(self, host: str = '192.168.1.230', port: int = 8080,
                 timeout: float = 3.0, enabled: bool = True):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.enabled = enabled
        self._connected = False
        self.base_url = f"http://{host}:{port}"

    def _check_connection(self) -> bool:
        """检查 K230 是否在线"""
        if not self.enabled or not REQUESTS_AVAILABLE:
            return False
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            self._connected = resp.status_code == 200
            return self._connected
        except Exception:
            self._connected = False
            return False

    @property
    def is_connected(self) -> bool:
        """K230 是否已连接"""
        if not self.enabled:
            return False
        # 缓存连接状态，避免每次都检查
        return self._connected

    def detect_via_k230(self, frame: np.ndarray) -> List[Dict]:
        """
        通过 K230 检测车牌位置

        Args:
            frame: BGR 格式图像

        Returns:
            [{'bbox': [x1,y1,x2,y2], 'confidence': float}, ...] 或空列表
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return []

        try:
            # 编码为 JPEG
            _, img_encoded = cv2.imencode('.jpg', frame,
                                          [cv2.IMWRITE_JPEG_QUALITY, 85])
            img_b64 = base64.b64encode(img_encoded).decode('utf-8')

            resp = requests.post(
                f"{self.base_url}/detect_plate",
                json={'image': img_b64},
                timeout=self.timeout
            )

            if resp.status_code != 200:
                logger.warning(f"[K230Client] 检测请求失败: {resp.status_code}")
                return []

            data = resp.json()
            if not data.get('success'):
                return []

            plates = []
            for det in data.get('detections', []):
                plates.append({
                    'bbox': det.get('bbox', []),
                    'confidence': det.get('confidence', 0.5),
                    'source': 'k230'
                })

            self._connected = True
            return plates

        except requests.exceptions.ConnectionError:
            self._connected = False
            logger.debug("[K230Client] K230 连接失败，降级跳过")
            return []
        except Exception as e:
            logger.warning(f"[K230Client] 检测异常: {e}")
            return []

    def recognize_via_k230(self, plate_crop: np.ndarray) -> Dict:
        """
        通过 K230 识别车牌文字

        Args:
            plate_crop: 车牌区域图像

        Returns:
            {'plate_number': str, 'confidence': float}
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return {'plate_number': '', 'confidence': 0.0}

        try:
            _, img_encoded = cv2.imencode('.jpg', plate_crop,
                                          [cv2.IMWRITE_JPEG_QUALITY, 90])
            img_b64 = base64.b64encode(img_encoded).decode('utf-8')

            resp = requests.post(
                f"{self.base_url}/recognize_plate",
                json={'image': img_b64},
                timeout=self.timeout
            )

            if resp.status_code != 200:
                return {'plate_number': '', 'confidence': 0.0}

            data = resp.json()
            if not data.get('success'):
                return {'plate_number': '', 'confidence': 0.0}

            self._connected = True
            return {
                'plate_number': data.get('plate_number', ''),
                'confidence': data.get('confidence', 0.0)
            }

        except requests.exceptions.ConnectionError:
            self._connected = False
            return {'plate_number': '', 'confidence': 0.0}
        except Exception as e:
            logger.warning(f"[K230Client] 识别异常: {e}")
            return {'plate_number': '', 'confidence': 0.0}

    def detect_and_recognize(self, frame: np.ndarray) -> Dict:
        """
        一步完成：K230 检测+识别

        Returns:
            {'plate_number': str, 'confidence': float, 'bbox': list, 'source': str}
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return {
                'plate_number': '', 'confidence': 0.0,
                'bbox': [], 'source': 'k230_offline'
            }

        try:
            _, img_encoded = cv2.imencode('.jpg', frame,
                                          [cv2.IMWRITE_JPEG_QUALITY, 85])
            img_b64 = base64.b64encode(img_encoded).decode('utf-8')

            resp = requests.post(
                f"{self.base_url}/detect_and_recognize",
                json={'image': img_b64},
                timeout=self.timeout
            )

            if resp.status_code != 200:
                return {
                    'plate_number': '', 'confidence': 0.0,
                    'bbox': [], 'source': 'k230_error'
                }

            data = resp.json()
            if not data.get('success'):
                return {
                    'plate_number': '', 'confidence': 0.0,
                    'bbox': [], 'source': 'k230_fail'
                }

            self._connected = True
            return {
                'plate_number': data.get('plate_number', ''),
                'confidence': data.get('confidence', 0.0),
                'bbox': data.get('bbox', []),
                'source': 'k230'
            }

        except requests.exceptions.ConnectionError:
            self._connected = False
            return {
                'plate_number': '', 'confidence': 0.0,
                'bbox': [], 'source': 'k230_offline'
            }
        except Exception as e:
            logger.warning(f"[K230Client] 综合异常: {e}")
            return {
                'plate_number': '', 'confidence': 0.0,
                'bbox': [], 'source': 'k230_error'
            }

    def get_status(self) -> Dict:
        """获取 K230 板载服务状态"""
        if not self.enabled or not REQUESTS_AVAILABLE:
            return {'connected': False, 'enabled': False}

        try:
            resp = requests.get(f"{self.base_url}/status", timeout=self.timeout)
            if resp.status_code == 200:
                self._connected = True
                return {**resp.json(), 'connected': True, 'enabled': True}
            else:
                self._connected = False
                return {'connected': False, 'enabled': True}
        except Exception:
            self._connected = False
            return {'connected': False, 'enabled': True}


# 全局单例
_k230_client: Optional[K230PlateClient] = None


def get_k230_client() -> K230PlateClient:
    """获取全局 K230 客户端单例"""
    global _k230_client
    if _k230_client is None:
        _k230_client = K230PlateClient()
    return _k230_client
