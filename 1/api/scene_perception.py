# -*- coding: utf-8 -*-
"""
场景感知模块 - 基于经典计算机视觉的交通场景理解
包含:
    1. LaneDetector        : 车道线检测 (Hough 变换 + ROI 掩膜)
    2. TrafficLightDetector: 红绿灯识别 (HSV 颜色空间)
    3. SceneContext        : 当前帧场景上下文聚合
    4. VIOLATION_COLORS    : 6 类违规颜色配置

设计原则:
    - 仅依赖 OpenCV + numpy, 不引入深度学习框架
    - 所有方法均具备 graceful degradation, 任意异常返回空结果而不抛出
    - 全流程日志可追踪, 便于线上排查
"""

import logging
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

# -----------------------------------------------------------------------------
# 日志配置
# -----------------------------------------------------------------------------
logger = logging.getLogger("scene_perception")
if not logger.handlers:
    # 避免重复添加 handler, 同时保证无根日志配置时也有输出
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)


# -----------------------------------------------------------------------------
# 6 类违规颜色配置 (BGR 元组 + HEX 字符串)
# 用于可视化叠加 / 前端展示统一配色
# -----------------------------------------------------------------------------
VIOLATION_COLORS: Dict[str, Dict[str, object]] = {
    "red_light":       {"hex": "#B71C1C", "bgr": (0x1C, 0x1C, 0xB7), "cn": "闯红灯"},     # 深红
    "wrong_way":       {"hex": "#FF6D00", "bgr": (0x00, 0x6D, 0xFF), "cn": "逆行"},        # 橙
    "illegal_parking": {"hex": "#7B1FA2", "bgr": (0xA2, 0x1F, 0x7B), "cn": "违停"},        # 紫
    "no_helmet":       {"hex": "#00BCD4", "bgr": (0xD4, 0xBC, 0x00), "cn": "未戴头盔"},    # 青
    "illegal_vendor":  {"hex": "#1976D2", "bgr": (0xD2, 0x76, 0x19), "cn": "占道经营"},    # 蓝
    "crowd_gather":    {"hex": "#FBC02D", "bgr": (0x2D, 0xC0, 0xFB), "cn": "人员聚集"},    # 黄
}


def get_violation_color(violation_type: str) -> Tuple[int, int, int]:
    """获取违规类型对应的 BGR 颜色, 未知类型返回白色。

    Args:
        violation_type: 违规类型键 (见 VIOLATION_COLORS)

    Returns:
        (B, G, R) 元组, uint8
    """
    entry = VIOLATION_COLORS.get(violation_type)
    if entry is None:
        logger.warning("未知违规类型: %s, 使用默认白色", violation_type)
        return (255, 255, 255)
    return tuple(int(c) for c in entry["bgr"])  # type: ignore[return-value]


# =============================================================================
# LaneDetector - 车道线检测
# =============================================================================
class LaneDetector:
    """车道线检测器 (经典方案: Hough 变换 + ROI 掩膜)

    适用场景: 结构化道路 / 城市主干道 / 摄像头固定场景
    检测流程:
        1. 灰度化 + 高斯模糊降噪
        2. Canny 边缘提取
        3. 选取下半部分梯形 ROI 掩膜
        4. 概率 Hough 变换提取直线
        5. 按斜率过滤水平/近似水平噪声, 按左右聚类
        6. 推断实线 / 虚线类型
    """

    def __init__(self,
                 roi_ratio: float = 0.55,
                 canny_low: int = 50,
                 canny_high: int = 150,
                 hough_rho: int = 1,
                 hough_theta: float = np.pi / 180,
                 hough_threshold: int = 50,
                 min_line_length: int = 50,
                 max_line_gap: int = 150,
                 min_slope: float = 0.3):
        """初始化车道线检测参数。

        Args:
            roi_ratio: ROI 起始高度比例 (0~1), 例如 0.55 表示从图像 55% 高度往下为 ROI
            canny_low: Canny 低阈值
            canny_high: Canny 高阈值
            hough_rho: Hough 累加器距离分辨率 (像素)
            hough_theta: Hough 累加器角度分辨率 (弧度)
            hough_threshold: Hough 投票阈值
            min_line_length: 最小线段长度
            max_line_gap: 最大线段间隙 (用于连接虚线)
            min_slope: 最小斜率绝对值, 用于过滤水平噪声
        """
        self.roi_ratio = float(roi_ratio)
        self.canny_low = int(canny_low)
        self.canny_high = int(canny_high)
        self.hough_rho = int(hough_rho)
        self.hough_theta = float(hough_theta)
        self.hough_threshold = int(hough_threshold)
        self.min_line_length = int(min_line_length)
        self.max_line_gap = int(max_line_gap)
        self.min_slope = float(min_slope)
        logger.debug("LaneDetector 初始化完成: roi_ratio=%.2f, canny=(%d,%d)",
                     self.roi_ratio, self.canny_low, self.canny_high)

    # ---------------- 公开接口 ----------------
    def detect(self, image: np.ndarray) -> List[Dict]:
        """检测车道线。

        Args:
            image: BGR 图像 (H, W, 3) 或灰度图 (H, W)

        Returns:
            车道线列表, 每项形如::
                {
                    "points": [[x1, y1], [x2, y2]],   # 像素坐标
                    "type":    "solid" | "dashed"
                }
            异常或无结果时返回空列表 []
        """
        try:
            if image is None or not isinstance(image, np.ndarray) or image.size == 0:
                logger.warning("LaneDetector.detect 输入图像为空")
                return []

            # 1. 灰度化
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()

            # 2. 高斯模糊降噪
            blur = cv2.GaussianBlur(gray, (5, 5), 0)

            # 3. Canny 边缘
            edges = cv2.Canny(blur, self.canny_low, self.canny_high)
            logger.debug("Canny 边缘统计: 非零像素=%d", int(np.count_nonzero(edges)))

            # 4. ROI 掩膜
            mask = self._build_roi_mask(image.shape)
            masked_edges = cv2.bitwise_and(edges, edges, mask=mask)

            # 5. Hough 概率变换
            lines = cv2.HoughLinesP(
                masked_edges,
                self.hough_rho,
                self.hough_theta,
                self.hough_threshold,
                minLineLength=self.min_line_length,
                maxLineGap=self.max_line_gap,
            )

            if lines is None:
                logger.info("Hough 未检测到直线")
                return []

            # 6. 过滤 + 分类
            results: List[Dict] = []
            for raw in lines:
                x1, y1, x2, y2 = raw[0]
                # 过滤近似水平线
                dx = float(x2 - x1)
                dy = float(y2 - y1)
                if dx == 0:
                    # 垂直线视为车道边界候选
                    slope = float("inf")
                else:
                    slope = dy / dx
                if abs(slope) < self.min_slope:
                    continue

                line_type = self._classify_line_type(x1, y1, x2, y2, masked_edges)
                results.append({
                    "points": [[int(x1), int(y1)], [int(x2), int(y2)]],
                    "type": line_type,
                })

            logger.info("LaneDetector 检测到车道线 %d 条", len(results))
            return results

        except cv2.error as e:
            logger.error("LaneDetector OpenCV 错误: %s", e, exc_info=True)
            return []
        except Exception as e:
            logger.error("LaneDetector 未知异常: %s", e, exc_info=True)
            return []

    # ---------------- 内部工具 ----------------
    def _build_roi_mask(self, shape: Tuple[int, ...]) -> np.ndarray:
        """构建梯形 ROI 掩膜 (图像下半部分)。

        Args:
            shape: 图像 shape

        Returns:
            uint8 二值掩膜, ROI 区域为 255
        """
        if len(shape) >= 2:
            h, w = int(shape[0]), int(shape[1])
        else:
            logger.warning("无法解析图像 shape: %s", shape)
            h, w = 720, 1280

        mask = np.zeros((h, w), dtype=np.uint8)
        y_top = int(h * self.roi_ratio)
        # 梯形: 顶部窄, 底部宽 (适配透视)
        top_left = (int(w * 0.45), y_top)
        top_right = (int(w * 0.55), y_top)
        bottom_left = (0, h)
        bottom_right = (w, h)
        polygon = np.array([[top_left, top_right, bottom_right, bottom_left]], dtype=np.int32)
        cv2.fillPoly(mask, polygon, 255)
        return mask

    def _classify_line_type(self, x1: int, y1: int, x2: int, y2: int,
                            edges: np.ndarray) -> str:
        """根据线段上的边缘像素连续性推断实线/虚线。

        思路: 沿线段采样若干点, 统计在 edges 上非零的比例:
            - 比例高 -> 实线 solid
            - 比例低 -> 虚线 dashed

        Args:
            x1, y1, x2, y2: 线段端点
            edges: Canny 边缘图

        Returns:
            "solid" 或 "dashed"
        """
        try:
            n_samples = 20
            xs = np.linspace(x1, x2, n_samples).astype(int)
            ys = np.linspace(y1, y2, n_samples).astype(int)
            # 限制索引范围
            h, w = edges.shape[:2]
            xs = np.clip(xs, 0, w - 1)
            ys = np.clip(ys, 0, h - 1)
            vals = edges[ys, xs]
            ratio = float(np.count_nonzero(vals)) / float(n_samples)
            # 经验阈值: >0.7 视为实线, 否则虚线
            return "solid" if ratio >= 0.7 else "dashed"
        except Exception as e:
            logger.debug("线段类型分类失败, 默认 solid: %s", e)
            return "solid"


# =============================================================================
# TrafficLightDetector - 红绿灯识别
# =============================================================================
class TrafficLightDetector:
    """红绿灯识别器 (HSV 颜色空间 + 形态学)

    适用场景: 摄像头视野中可见红绿灯本体 (无需裁剪定位时也可全图扫描)
    检测流程:
        1. BGR -> HSV
        2. 分别构建红 / 黄 / 绿三色掩膜 (覆盖 HSV 中红色色相环两端)
        3. 形态学开运算去噪
        4. 找最大连通域作为灯体候选
        5. 输出状态 / 中心位置 / 置信度

    若传入 detections (来自 YOLO 等), 则优先在 traffic light 检测框内做颜色识别.
    """

    # HSV 颜色阈值 (H: 0-179, S: 0-255, V: 0-255)
    RED_LOW_1 = np.array([0, 70, 70])
    RED_HIGH_1 = np.array([10, 255, 255])
    RED_LOW_2 = np.array([170, 70, 70])
    RED_HIGH_2 = np.array([180, 255, 255])

    YELLOW_LOW = np.array([20, 70, 70])
    YELLOW_HIGH = np.array([35, 255, 255])

    GREEN_LOW = np.array([35, 70, 70])
    GREEN_HIGH = np.array([90, 255, 255])

    # 最小灯体面积 (像素), 低于此值视为噪声
    MIN_LIGHT_AREA = 30

    def __init__(self,
                 min_area: int = 30,
                 use_morph: bool = True):
        """初始化红绿灯识别器。

        Args:
            min_area: 最小灯体面积阈值
            use_morph: 是否启用形态学开运算降噪
        """
        self.min_area = int(min_area)
        self.use_morph = bool(use_morph)
        logger.debug("TrafficLightDetector 初始化: min_area=%d, use_morph=%s",
                     self.min_area, self.use_morph)

    # ---------------- 公开接口 ----------------
    def detect(self, image: np.ndarray,
               detections: Optional[List[Dict]] = None) -> Dict:
        """识别红绿灯状态。

        Args:
            image: BGR 图像
            detections: 可选的目标检测结果, 形如::
                [{"class_name": "traffic light", "bbox": [x1,y1,x2,y2], "confidence": 0.9}, ...]
                若提供, 则在每个 traffic light 框内做颜色识别, 取置信度最高者

        Returns:
            {
                "state":     "red" | "green" | "yellow" | "unknown",
                "location":  [x, y],   # 灯体中心像素坐标
                "confidence": float    # 0.0 ~ 1.0
            }
            异常时返回 {"state": "unknown", "location": [0,0], "confidence": 0.0}
        """
        default = {"state": "unknown", "location": [0, 0], "confidence": 0.0}
        try:
            if image is None or not isinstance(image, np.ndarray) or image.size == 0:
                logger.warning("TrafficLightDetector.detect 输入图像为空")
                return default

            # 路径 A: 有目标检测框, 优先用框内识别
            if detections:
                result = self._detect_with_boxes(image, detections)
                if result["state"] != "unknown":
                    logger.info("红绿灯识别(框内) state=%s conf=%.3f loc=%s",
                                result["state"], result["confidence"], result["location"])
                    return result
                logger.info("框内未识别到有效红绿灯, 回退全图扫描")

            # 路径 B: 全图扫描
            result = self._detect_full_image(image)
            if result["state"] != "unknown":
                logger.info("红绿灯识别(全图) state=%s conf=%.3f loc=%s",
                            result["state"], result["confidence"], result["location"])
            else:
                logger.info("红绿灯识别: 未发现有效灯体")
            return result

        except cv2.error as e:
            logger.error("TrafficLightDetector OpenCV 错误: %s", e, exc_info=True)
            return default
        except Exception as e:
            logger.error("TrafficLightDetector 未知异常: %s", e, exc_info=True)
            return default

    # ---------------- 内部工具 ----------------
    def _detect_with_boxes(self, image: np.ndarray,
                           detections: List[Dict]) -> Dict:
        """在 traffic light 检测框内识别颜色, 取置信度最高者。

        Args:
            image: BGR 原图
            detections: 目标检测结果列表

        Returns:
            同 detect() 返回结构
        """
        best = {"state": "unknown", "location": [0, 0], "confidence": 0.0}
        h_img, w_img = image.shape[:2]
        for det in detections:
            try:
                cls = det.get("class_name", "") or det.get("class", "")
                if "traffic" not in str(cls).lower() or "light" not in str(cls).lower():
                    continue
                bbox = det.get("bbox") or det.get("box")
                if not bbox or len(bbox) != 4:
                    continue
                x1, y1, x2, y2 = [int(v) for v in bbox]
                x1 = max(0, min(x1, w_img - 1))
                y1 = max(0, min(y1, h_img - 1))
                x2 = max(0, min(x2, w_img - 1))
                y2 = max(0, min(y2, h_img - 1))
                if x2 <= x1 or y2 <= y1:
                    continue
                crop = image[y1:y2, x1:x2]
                state, loc, conf = self._analyze_color_blob(crop)
                # 把局部坐标映射回原图
                if state != "unknown":
                    abs_loc = [int(loc[0] + x1), int(loc[1] + y1)]
                    # 置信度与检测框置信度加权
                    det_conf = float(det.get("confidence", 1.0) or 1.0)
                    merged_conf = float(conf * det_conf)
                    if merged_conf > best["confidence"]:
                        best = {
                            "state": state,
                            "location": abs_loc,
                            "confidence": round(merged_conf, 4),
                        }
            except Exception as e:
                logger.debug("处理检测框失败: %s", e)
                continue
        return best

    def _detect_full_image(self, image: np.ndarray) -> Dict:
        """全图扫描识别红绿灯颜色。

        Args:
            image: BGR 原图

        Returns:
            同 detect() 返回结构
        """
        state, loc, conf = self._analyze_color_blob(image)
        return {
            "state": state,
            "location": [int(loc[0]), int(loc[1])],
            "confidence": round(float(conf), 4),
        }

    def _analyze_color_blob(self, roi: np.ndarray) -> Tuple[str, Tuple[float, float], float]:
        """在 ROI 内分析颜色, 返回最强状态。

        Args:
            roi: BGR 局部图像

        Returns:
            (state, (cx, cy), confidence)
        """
        if roi is None or roi.size == 0:
            return "unknown", (0.0, 0.0), 0.0

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # 三色掩膜
        mask_red = cv2.bitwise_or(
            cv2.inRange(hsv, self.RED_LOW_1, self.RED_HIGH_1),
            cv2.inRange(hsv, self.RED_LOW_2, self.RED_HIGH_2),
        )
        mask_yellow = cv2.inRange(hsv, self.YELLOW_LOW, self.YELLOW_HIGH)
        mask_green = cv2.inRange(hsv, self.GREEN_LOW, self.GREEN_HIGH)

        if self.use_morph:
            kernel = np.ones((3, 3), np.uint8)
            mask_red = cv2.morphologyEx(mask_red, cv2.MORPH_OPEN, kernel)
            mask_yellow = cv2.morphologyEx(mask_yellow, cv2.MORPH_OPEN, kernel)
            mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, kernel)

        candidates = [
            ("red", mask_red),
            ("yellow", mask_yellow),
            ("green", mask_green),
        ]

        best_state = "unknown"
        best_loc: Tuple[float, float] = (0.0, 0.0)
        best_conf = 0.0

        for state, mask in candidates:
            area, loc, conf = self._largest_blob(mask)
            if area <= 0:
                continue
            # 置信度 = 归一化面积 (上限 1.0) * 0.6 + 圆度近似 * 0.4 (简化)
            # 这里用面积占比作为置信度主体
            if conf > best_conf:
                best_state = state
                best_loc = loc
                best_conf = conf

        return best_state, best_loc, best_conf

    def _largest_blob(self, mask: np.ndarray) -> Tuple[float, Tuple[float, float], float]:
        """获取掩膜中最大连通域的面积 / 中心 / 置信度。

        Args:
            mask: 二值图 (0 / 255)

        Returns:
            (area, (cx, cy), confidence)
            若无连通域返回 (0.0, (0.0, 0.0), 0.0)
        """
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0.0, (0.0, 0.0), 0.0

        cnt = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(cnt))
        if area < self.MIN_LIGHT_AREA:
            return 0.0, (0.0, 0.0), 0.0

        m = cv2.moments(cnt)
        if m["m00"] == 0:
            cx, cy = 0.0, 0.0
        else:
            cx = float(m["m10"] / m["m00"])
            cy = float(m["m01"] / m["m00"])

        # 置信度: 面积归一化 (经验上限 2000 像素)
        conf = min(1.0, area / 2000.0)
        return area, (cx, cy), conf


# =============================================================================
# SceneContext - 场景上下文聚合
# =============================================================================
class SceneContext:
    """当前帧场景上下文聚合器。

    将车道线 / 红绿灯 / 车辆位置等检测结果统一聚合, 供违规判定与可视化使用。
    设计为可变对象, 每帧 update() 后即代表最新场景。
    """

    def __init__(self,
                 lane_detector: Optional[LaneDetector] = None,
                 traffic_light_detector: Optional[TrafficLightDetector] = None):
        """初始化场景上下文。

        Args:
            lane_detector: 车道线检测器实例, 默认新建
            traffic_light_detector: 红绿灯检测器实例, 默认新建
        """
        self.lane_detector = lane_detector or LaneDetector()
        self.traffic_light_detector = traffic_light_detector or TrafficLightDetector()

        # 当前帧聚合数据
        self.lane_lines: List[Dict] = []
        self.traffic_light_state: str = "unknown"
        self.traffic_light_location: List[int] = [0, 0]
        self.traffic_light_confidence: float = 0.0
        self.vehicle_lane_positions: List[Dict] = []

        # 时间戳 (毫秒), 用于多帧关联
        self.timestamp_ms: int = 0
        logger.debug("SceneContext 初始化完成")

    # ---------------- 公开接口 ----------------
    def update(self,
               image: np.ndarray,
               detections: Optional[List[Dict]] = None,
               timestamp_ms: int = 0) -> Dict:
        """更新当前帧场景上下文。

        Args:
            image: BGR 图像
            detections: 目标检测结果 (YOLO 等), 可选
                形如 [{"class_name": "car", "bbox": [x1,y1,x2,y2], "confidence": 0.9}, ...]
            timestamp_ms: 帧时间戳 (毫秒)

        Returns:
            场景快照字典::
                {
                    "lane_lines": [...],
                    "traffic_light": {"state": ..., "location": ..., "confidence": ...},
                    "vehicle_lane_positions": [...],
                    "timestamp_ms": int
                }
        """
        snapshot = {
            "lane_lines": [],
            "traffic_light": {
                "state": "unknown",
                "location": [0, 0],
                "confidence": 0.0,
            },
            "vehicle_lane_positions": [],
            "timestamp_ms": int(timestamp_ms),
        }

        try:
            # 1. 车道线
            self.lane_lines = self.lane_detector.detect(image)
            snapshot["lane_lines"] = self.lane_lines

            # 2. 红绿灯
            tl = self.traffic_light_detector.detect(image, detections)
            self.traffic_light_state = tl["state"]
            self.traffic_light_location = tl["location"]
            self.traffic_light_confidence = tl["confidence"]
            snapshot["traffic_light"] = tl

            # 3. 车辆在车道中的位置
            self.vehicle_lane_positions = self._compute_vehicle_lane_positions(detections)
            snapshot["vehicle_lane_positions"] = self.vehicle_lane_positions

            self.timestamp_ms = int(timestamp_ms)
            snapshot["timestamp_ms"] = self.timestamp_ms

            logger.info(
                "SceneContext 更新: 车道线=%d, 红绿灯=%s(%.2f), 车辆=%d",
                len(self.lane_lines),
                self.traffic_light_state,
                self.traffic_light_confidence,
                len(self.vehicle_lane_positions),
            )
        except Exception as e:
            logger.error("SceneContext.update 异常: %s", e, exc_info=True)

        return snapshot

    def get_snapshot(self) -> Dict:
        """获取当前场景快照 (不重新计算)。"""
        return {
            "lane_lines": self.lane_lines,
            "traffic_light": {
                "state": self.traffic_light_state,
                "location": self.traffic_light_location,
                "confidence": self.traffic_light_confidence,
            },
            "vehicle_lane_positions": self.vehicle_lane_positions,
            "timestamp_ms": self.timestamp_ms,
        }

    # ---------------- 内部工具 ----------------
    def _compute_vehicle_lane_positions(self,
                                        detections: Optional[List[Dict]]) -> List[Dict]:
        """根据车辆检测框与车道线, 估算车辆在车道中的相对位置。

        简化策略:
            - 取车辆底边中心 x 坐标
            - 与图像中心 x 对比, 判断 left / center / right
            - 若有车道线, 进一步判断是否压线 (横跨两条线)

        Args:
            detections: 目标检测结果

        Returns:
            车辆位置列表::
                [{
                    "class_name": "car",
                    "bbox": [x1,y1,x2,y2],
                    "confidence": 0.9,
                    "bottom_center": [cx, cy],
                    "lane_side": "left" | "center" | "right"
                }]
        """
        if not detections:
            return []

        vehicle_classes = {"car", "motorcycle", "truck", "bus", "bicycle"}
        positions: List[Dict] = []

        # 估算图像宽度 (取第一条车道线端点或默认 1280)
        img_width = 1280
        if self.lane_lines:
            all_x = [p[0] for line in self.lane_lines for p in line.get("points", [])]
            if all_x:
                img_width = max(all_x) if max(all_x) > 0 else 1280
        center_x = img_width / 2.0

        for det in detections:
            try:
                cls = str(det.get("class_name", "") or det.get("class", ""))
                if cls.lower() not in vehicle_classes:
                    continue
                bbox = det.get("bbox") or det.get("box")
                if not bbox or len(bbox) != 4:
                    continue
                x1, y1, x2, y2 = [int(v) for v in bbox]
                cx = (x1 + x2) / 2.0
                cy = y2  # 底边中心 y
                # 左右判断
                if cx < center_x * 0.85:
                    side = "left"
                elif cx > center_x * 1.15:
                    side = "right"
                else:
                    side = "center"

                positions.append({
                    "class_name": cls,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": float(det.get("confidence", 0.0) or 0.0),
                    "bottom_center": [int(cx), int(cy)],
                    "lane_side": side,
                })
            except Exception as e:
                logger.debug("车辆位置计算失败: %s", e)
                continue

        return positions


# -----------------------------------------------------------------------------
# 模块自检入口 (可直接 python scene_perception.py 运行)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 构造一张测试图 (1280x720, 灰色背景 + 模拟车道线)
    test_img = np.full((720, 1280, 3), 60, dtype=np.uint8)
    cv2.line(test_img, (500, 400), (300, 720), (255, 255, 255), 8)
    cv2.line(test_img, (780, 400), (980, 720), (255, 255, 255), 8)

    ctx = SceneContext()
    snap = ctx.update(test_img, detections=None, timestamp_ms=1000)
    print("snapshot:", snap)

    print("VIOLATION_COLORS keys:", list(VIOLATION_COLORS.keys()))
