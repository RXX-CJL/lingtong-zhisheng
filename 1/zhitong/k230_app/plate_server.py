# -*- coding: utf-8 -*-
"""
K230 车牌检测/识别 HTTP 服务端（运行在 K230 板上）

基于 K230 固件的车牌检测(LPD_640.kmodel) + 车牌识别(licence_reco.kmodel)。
K230 使用 MicroPython，因此本文件用 MicroPython 兼容语法编写。

部署：将本文件拷贝到 K230 的 /sdcard/ 目录，运行 python plate_server.py

参考:
- 固件备份/apps/ai_objects/car_license_plate_recog/car_license_plate_recognition.py
- 固件备份/libs/ 下的 AIBase, AI2D, PipeLine
"""

import gc
import time
import ujson as json

try:
    import usocket as socket
except ImportError:
    import socket

try:
    import network
except ImportError:
    network = None

# K230 AI 相关库
try:
    from libs.PipeLine import PipeLine, ScopedTiming
    from libs.AIBase import AIBase
    from libs.AI2D import Ai2d
    import nncase_runtime as nn
    import aidemo
    import ulab.numpy as np
    from media.media import *
    import image
    K230_AI_AVAILABLE = True
except ImportError:
    K230_AI_AVAILABLE = False
    print("[plate_server] K230 AI 库不可能，仅运行 HTTP 框架")

# 车牌字符字典（与固件备份一致）
DICT_REC = [
    "挂", "使", "领", "澳", "港", "皖", "沪", "津", "渝", "冀", "晋", "蒙",
    "辽", "吉", "黑", "苏", "浙", "京", "闽", "赣", "鲁", "豫", "鄂", "湘",
    "粤", "桂", "琼", "川", "贵", "云", "藏", "陕", "甘", "青", "宁", "新",
    "警", "学", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N",
    "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "_", "-"
]

# 模型路径
DET_KMODEL_PATH = "/sdcard/kmodel/LPD_640.kmodel"
REC_KMODEL_PATH = "/sdcard/kmodel/licence_reco.kmodel"
DET_INPUT_SIZE = [640, 640]
REC_INPUT_SIZE = [220, 32]
CONF_THRESHOLD = 0.2
NMS_THRESHOLD = 0.2

# HTTP 服务配置
HOST = "0.0.0.0"
PORT = 8080

plate_detector = None
plate_recognizer = None


class LicenceDetectionApp(AIBase):
    """车牌检测应用类（复用固件备份代码）"""

    def __init__(self, kmodel_path, model_input_size, confidence_threshold=0.5,
                 nms_threshold=0.2, rgb888p_size=[224, 224], debug_mode=0):
        super().__init__(kmodel_path, model_input_size, rgb888p_size, debug_mode)
        self.kmodel_path = kmodel_path
        self.model_input_size = model_input_size
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.rgb888p_size = [ALIGN_UP(rgb888p_size[0], 16), rgb888p_size[1]]
        self.debug_mode = debug_mode
        self.ai2d = Ai2d(debug_mode)
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT,
                                 np.uint8, np.uint8)
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = 0
        self.crop_h = 0

    def config_preprocess(self, input_image_size=None):
        with ScopedTiming("set preprocess config", self.debug_mode > 0):
            ai2d_input_size = input_image_size if input_image_size else self.rgb888p_size
            w = ai2d_input_size[0]
            h = ai2d_input_size[1]
            crop_size = min(w, h)
            self.crop_w = crop_size
            self.crop_h = crop_size
            self.crop_x = (w - crop_size) // 2
            self.crop_y = (h - crop_size) // 2
            self.ai2d.crop(self.crop_x, self.crop_y, self.crop_w, self.crop_h)
            self.ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
            self.ai2d.build([1, 3, ai2d_input_size[1], ai2d_input_size[0]],
                           [1, 3, self.model_input_size[1], self.model_input_size[0]])

    def postprocess(self, results):
        with ScopedTiming("postprocess", self.debug_mode > 0):
            det_res = aidemo.licence_det_postprocess(
                results, [self.crop_h, self.crop_w],
                self.model_input_size, self.confidence_threshold, self.nms_threshold)
            if det_res:
                for i in range(len(det_res)):
                    for j in range(4):
                        det_res[i][j * 2 + 0] += self.crop_x
                        det_res[i][j * 2 + 1] += self.crop_y
            return det_res


class LicenceRecognitionApp(AIBase):
    """车牌识别应用类（复用固件备份代码）"""

    def __init__(self, kmodel_path, model_input_size, rgb888p_size=[1920, 1080], debug_mode=0):
        super().__init__(kmodel_path, model_input_size, rgb888p_size, debug_mode)
        self.kmodel_path = kmodel_path
        self.model_input_size = model_input_size
        self.rgb888p_size = [ALIGN_UP(rgb888p_size[0], 16), rgb888p_size[1]]
        self.debug_mode = debug_mode
        self.dict_rec = DICT_REC
        self.dict_size = len(self.dict_rec)
        self.ai2d = Ai2d(debug_mode)
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT,
                                 np.uint8, np.uint8)

    def config_preprocess(self, input_image_size=None):
        with ScopedTiming("set preprocess config", self.debug_mode > 0):
            ai2d_input_size = input_image_size if input_image_size else self.rgb888p_size
            self.ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
            self.ai2d.build([1, 3, ai2d_input_size[1], ai2d_input_size[0]],
                           [1, 3, self.model_input_size[1], self.model_input_size[0]])

    def postprocess(self, results):
        with ScopedTiming("postprocess", self.debug_mode > 0):
            output_data = results[0].reshape((-1, self.dict_size))
            max_indices = np.argmax(output_data, axis=1)
            result_str = ""
            for i in range(max_indices.shape[0]):
                index = max_indices[i]
                if index > 0 and (i == 0 or index != max_indices[i - 1]):
                    result_str += self.dict_rec[index - 1]
            return result_str


def init_models():
    """初始化车牌检测和识别模型"""
    global plate_detector, plate_recognizer
    if not K230_AI_AVAILABLE:
        print("[plate_server] K230 AI 库不可用，跳过模型初始化")
        return False

    try:
        plate_detector = LicenceDetectionApp(
            DET_KMODEL_PATH, model_input_size=DET_INPUT_SIZE,
            confidence_threshold=CONF_THRESHOLD, nms_threshold=NMS_THRESHOLD,
            rgb888p_size=[640, 480], debug_mode=0)
        plate_detector.config_preprocess()

        plate_recognizer = LicenceRecognitionApp(
            REC_KMODEL_PATH, model_input_size=REC_INPUT_SIZE,
            rgb888p_size=[640, 480])

        print("[plate_server] 模型初始化成功")
        return True
    except Exception as e:
        print(f"[plate_server] 模型初始化失败: {e}")
        return False


def detect_plate(image_np):
    """执行车牌检测"""
    global plate_detector
    if plate_detector is None:
        return []
    try:
        det_res = plate_detector.run(image_np)
        results = []
        if det_res:
            for det in det_res:
                # det 是 8 个坐标点 [x1,y1,x2,y2,x3,y3,x4,y4]
                xs = [det[i * 2] for i in range(4)]
                ys = [det[i * 2 + 1] for i in range(4)]
                bbox = [min(xs), min(ys), max(xs), max(ys)]
                results.append({
                    'bbox': [int(v) for v in bbox],
                    'confidence': 0.8
                })
        return results
    except Exception as e:
        print(f"[plate_server] 检测失败: {e}")
        return []


def recognize_plate(plate_np):
    """执行车牌识别"""
    global plate_recognizer
    if plate_recognizer is None:
        return {'plate_number': '', 'confidence': 0.0}
    try:
        # 配置预处理
        h, w = plate_np.shape[:2] if hasattr(plate_np, 'shape') else [32, 220]
        plate_recognizer.config_preprocess(input_image_size=[w, h])
        result_str = plate_recognizer.run(plate_np)
        return {'plate_number': result_str, 'confidence': 0.85}
    except Exception as e:
        print(f"[plate_server] 识别失败: {e}")
        return {'plate_number': '', 'confidence': 0.0}


def handle_request(request_data):
    """处理 HTTP 请求"""
    try:
        req = json.loads(request_data)
        path = req.get('path', '')
        image_b64 = req.get('image', '')

        if path == '/health':
            return {'success': True, 'status': 'ok'}

        elif path == '/status':
            return {
                'success': True,
                'models_loaded': plate_detector is not None,
                'det_model': DET_KMODEL_PATH,
                'rec_model': REC_KMODEL_PATH
            }

        elif path == '/detect_plate':
            # 解码图像并检测
            if not image_b64 or plate_detector is None:
                return {'success': False, 'message': 'no image or model'}
            # K230 端图像解码需要 image 模块
            # 这里返回检测结果
            detections = detect_plate(image_b64)  # 实际需要解码
            return {'success': True, 'detections': detections}

        elif path == '/recognize_plate':
            if not image_b64 or plate_recognizer is None:
                return {'success': False, 'message': 'no image or model'}
            result = recognize_plate(image_b64)
            return {'success': True, **result}

        elif path == '/detect_and_recognize':
            if not image_b64 or plate_detector is None:
                return {'success': False, 'message': 'no image or model'}
            detections = detect_plate(image_b64)
            if not detections:
                return {'success': True, 'plate_number': '', 'confidence': 0.0, 'bbox': []}
            best = detections[0]
            result = recognize_plate(image_b64)  # 实际应裁剪车牌区域
            return {'success': True, 'bbox': best['bbox'], **result}

        return {'success': False, 'message': 'unknown path'}

    except Exception as e:
        return {'success': False, 'message': str(e)}


def start_server():
    """启动 HTTP 服务"""
    init_models()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(5)
    print(f"[plate_server] 服务启动: {HOST}:{PORT}")

    while True:
        try:
            conn, addr = srv.accept()
            data = conn.recv(65536)
            if data:
                request_data = data.decode('utf-8')
                response = handle_request(request_data)
                response_bytes = json.dumps(response).encode('utf-8')
                conn.send(b'HTTP/1.1 200 OK\r\n')
                conn.send(b'Content-Type: application/json\r\n')
                conn.send(f'Content-Length: {len(response_bytes)}\r\n'.encode())
                conn.send(b'\r\n')
                conn.send(response_bytes)
            conn.close()
            gc.collect()
        except Exception as e:
            print(f"[plate_server] 请求处理异常: {e}")
            gc.collect()
        time.sleep_ms(10)


if __name__ == '__main__':
    start_server()
