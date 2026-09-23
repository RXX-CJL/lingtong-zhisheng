# -*- coding: utf-8 -*-
"""
M09: 软件虚拟追踪模块 (Virtual Tracker)
=====================================
在无 PTZ 硬件或硬件不可用时，通过软件裁剪 + 数字变焦实现"虚拟追踪"，
将锁定目标始终居中并放大显示。

核心特性:
    - start_tracking(track_id, target_bbox): 锁定追踪目标
    - update(frame, all_tracks): 根据追踪 ID 更新目标位置
    - get_tracking_crop(frame, out_size): 输出目标区域 + 边缘 padding + 高斯平滑放大
    - get_focus_indicator(): 返回目标中心、裁剪尺寸、变焦级别
    - 指数移动平均 (EMA) 平滑，避免画面抖动
    - 追踪优先级: confirmed 违规车辆 > pending 违规 > 普通车辆

依赖:
    - OpenCV (cv2): 图像裁剪与高斯放大
    - numpy: 数值计算

数据格式约定:
    - all_tracks: List[Dict]，每条 track 至少包含:
        {
            "track_id": int,
            "bbox": [x1, y1, x2, y2],
            "class_name": str,         # "car"/"motorcycle"/...
            "confidence": float,
            "violation_type": str|None, # 违规类型，无违规为 None
            "status": str,              # "confirmed"/"pending"/"normal"
        }
    - bbox 坐标为像素绝对坐标
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# 优先级常量
# ----------------------------------------------------------------------------
# 数值越大优先级越高
_PRIORITY_WEIGHTS: Dict[str, int] = {
    "confirmed_violation": 100,  # confirmed 违规车辆
    "pending_violation": 50,     # pending 违规车辆
    "normal_vehicle": 10,        # 普通车辆
    "unknown": 0,
}

# 默认 EMA 平滑系数: 越小越平滑 (0~1)
_DEFAULT_EMA_ALPHA = 0.35

# 车辆类别集合 (与 vehicle_tracker.py 保持一致)
_VEHICLE_CLASSES = {"car", "motorcycle", "truck", "bus", "bicycle"}


class VirtualTracker:
    """软件虚拟追踪器。

    通过 EMA 平滑跟踪目标中心，并在画面中裁剪目标区域进行数字放大，
    模拟 PTZ 摄像头的追踪效果。

    使用流程::

        tracker = VirtualTracker()
        # 锁定一个目标
        tracker.start_tracking(track_id=5, target_bbox=[100, 100, 300, 300])
        # 每帧更新
        for frame in video:
            all_tracks = detector.detect(frame)
            tracker.update(frame, all_tracks)
            crop = tracker.get_tracking_crop(frame, out_size=(640, 640))
            info = tracker.get_focus_indicator()
            # 显示 crop...
    """

    def __init__(
        self,
        ema_alpha: float = _DEFAULT_EMA_ALPHA,
        default_zoom: float = 2.0,
        max_zoom: float = 4.0,
        min_zoom: float = 1.2,
        padding_ratio: float = 0.25,
        lost_timeout: float = 3.0,
    ) -> None:
        """初始化虚拟追踪器。

        Args:
            ema_alpha: EMA 平滑系数 (0~1)，越小越平滑，默认 0.35
            default_zoom: 默认数字变焦倍率
            max_zoom: 最大变焦倍率
            min_zoom: 最小变焦倍率
            padding_ratio: 裁剪区域相对目标的边缘 padding 比例 (0.25 = 25%)
            lost_timeout: 目标丢失多久后自动取消追踪 (秒)
        """
        self.ema_alpha = float(ema_alpha)
        self.default_zoom = float(default_zoom)
        self.max_zoom = float(max_zoom)
        self.min_zoom = float(min_zoom)
        self.padding_ratio = float(padding_ratio)
        self.lost_timeout = float(lost_timeout)

        # 当前追踪状态
        self._track_id: Optional[int] = None
        self._target_bbox: Optional[List[int]] = None  # 平滑后的 bbox
        self._raw_bbox: Optional[List[int]] = None     # 最近一次原始 bbox
        self._zoom_level: float = self.default_zoom
        self._last_seen_ts: float = 0.0
        self._is_tracking: bool = False
        self._frame_size: Tuple[int, int] = (0, 0)  # (width, height)

        # 平滑后的目标中心 (像素坐标)
        self._smooth_center: Optional[Tuple[float, float]] = None
        # 平滑后的目标尺寸 (宽, 高)
        self._smooth_size: Optional[Tuple[float, float]] = None

        logger.info(
            "VirtualTracker 初始化: ema_alpha=%.2f zoom=%.1f~%.1f padding=%.0f%%",
            self.ema_alpha, self.min_zoom, self.max_zoom, self.padding_ratio * 100,
        )

    # ========================================================================
    # 公开 API
    # ========================================================================
    def start_tracking(self, track_id: int, target_bbox: List[int]) -> bool:
        """锁定追踪目标。

        Args:
            track_id: 追踪 ID
            target_bbox: 目标初始 bbox [x1, y1, x2, y2]
        Returns:
            bool: 是否成功锁定
        """
        if len(target_bbox) != 4:
            logger.error("start_tracking: bbox 长度异常 %s", target_bbox)
            return False

        self._track_id = int(track_id)
        self._raw_bbox = [int(v) for v in target_bbox]
        # 初始化平滑状态为原始值
        x1, y1, x2, y2 = target_bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        w = float(x2 - x1)
        h = float(y2 - y1)
        self._smooth_center = (cx, cy)
        self._smooth_size = (w, h)
        self._target_bbox = [int(x1), int(y1), int(x2), int(y2)]
        self._zoom_level = self.default_zoom
        self._last_seen_ts = time.time()
        self._is_tracking = True

        logger.info(
            "开始追踪: track_id=%d bbox=%s center=(%.1f,%.1f) size=(%.1f,%.1f)",
            track_id, target_bbox, cx, cy, w, h,
        )
        return True

    def stop_tracking(self) -> None:
        """停止追踪。"""
        if self._is_tracking:
            logger.info("停止追踪: track_id=%s", self._track_id)
        self._is_tracking = False
        self._track_id = None
        self._target_bbox = None
        self._raw_bbox = None
        self._smooth_center = None
        self._smooth_size = None

    def is_tracking(self) -> bool:
        """是否正在追踪。"""
        return self._is_tracking

    def get_current_track_id(self) -> Optional[int]:
        """获取当前追踪的 ID。"""
        return self._track_id

    def update(
        self,
        frame: Optional[np.ndarray],
        all_tracks: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """根据当前帧的所有 track 更新目标位置。

        优先级规则:
            1. 如果当前已锁定 track_id 且仍在 all_tracks 中，继续追踪它
            2. 如果当前目标丢失，按优先级选择新目标:
               confirmed 违规车辆 > pending 违规 > 普通车辆
            3. 如果当前无追踪目标，按优先级自动锁定最高优先级目标
            4. 目标丢失超过 lost_timeout 秒，自动停止追踪

        Args:
            frame: 当前帧 (用于获取尺寸，可为 None)
            all_tracks: 当前帧所有 track 列表
        Returns:
            Dict|None: 当前追踪目标信息，未追踪时返回 None
        """
        # 更新帧尺寸
        if frame is not None and frame.size > 0:
            h, w = frame.shape[:2]
            self._frame_size = (w, h)

        # 未在追踪状态: 尝试自动锁定最高优先级目标
        if not self._is_tracking:
            best = self._pick_highest_priority_track(all_tracks)
            if best is not None:
                self.start_tracking(best["track_id"], best["bbox"])
            else:
                return None

        # 已在追踪状态: 尝试在 all_tracks 中找到当前 track_id
        matched: Optional[Dict[str, Any]] = None
        for t in all_tracks:
            if t.get("track_id") == self._track_id:
                matched = t
                break

        if matched is not None:
            # 找到目标，更新位置 (EMA 平滑)
            self._raw_bbox = [int(v) for v in matched.get("bbox", [0, 0, 0, 0])]
            self._last_seen_ts = time.time()
            self._apply_ema_smoothing()
            return self._build_track_info(matched)
        else:
            # 目标暂时丢失
            elapsed = time.time() - self._last_seen_ts
            if elapsed > self.lost_timeout:
                logger.info(
                    "目标丢失 %.1fs 超过阈值 %.1fs，停止追踪 (track_id=%s)",
                    elapsed, self.lost_timeout, self._track_id,
                )
                self.stop_tracking()
                # 尝试自动锁定新目标
                best = self._pick_highest_priority_track(all_tracks)
                if best is not None:
                    self.start_tracking(best["track_id"], best["bbox"])
                    return self._build_track_info(best)
                return None
            else:
                # 短暂丢失，保持上一帧位置 (用平滑后的值)
                logger.debug(
                    "目标短暂丢失 %.2fs，保持位置 (track_id=%s)",
                    elapsed, self._track_id,
                )
                return self._build_track_info(None)

    def get_tracking_crop(
        self,
        frame: Optional[np.ndarray],
        out_size: Tuple[int, int] = (640, 640),
    ) -> Optional[np.ndarray]:
        """获取目标区域裁剪 + 边缘 padding + 高斯平滑放大后的图像。

        流程:
            1. 根据平滑后的目标中心和尺寸计算裁剪区域 (含 padding)
            2. 裁剪区域会限制在画面范围内
            3. 裁剪后用高斯平滑 + 双三次插值放大到 out_size
            4. 未追踪或帧无效时返回 None

        Args:
            frame: 输入帧
            out_size: 输出尺寸 (width, height)
        Returns:
            np.ndarray|None: 裁剪放大后的图像，未追踪时返回 None
        """
        if frame is None or frame.size == 0:
            logger.debug("get_tracking_crop: 帧无效")
            return None
        if not self._is_tracking or self._smooth_center is None or self._smooth_size is None:
            logger.debug("get_tracking_crop: 未在追踪状态")
            return None

        h, w = frame.shape[:2]
        out_w, out_h = out_size

        # 计算裁剪区域 (目标尺寸 * 变焦 + padding)
        tw, th = self._smooth_size
        # 目标尺寸不能为 0
        tw = max(tw, 1.0)
        th = max(th, 1.0)

        # 裁剪区域 = 目标尺寸 / 变焦倍率 + padding
        # 变焦越大，裁剪区域越小 (放大效果)
        crop_w = tw / self._zoom_level + tw * self.padding_ratio
        crop_h = th / self._zoom_level + th * self.padding_ratio

        # 保证最小裁剪尺寸，避免极小目标导致放大过度
        min_crop = 64.0
        crop_w = max(crop_w, min_crop)
        crop_h = max(crop_h, min_crop)

        cx, cy = self._smooth_center
        x1 = int(cx - crop_w / 2.0)
        y1 = int(cy - crop_h / 2.0)
        x2 = int(cx + crop_w / 2.0)
        y2 = int(cy + crop_h / 2.0)

        # 边界处理: 超出画面时平移裁剪框 (保持尺寸不变)
        if x1 < 0:
            x2 -= x1
            x1 = 0
        if y1 < 0:
            y2 -= y1
            y1 = 0
        if x2 > w:
            x1 -= (x2 - w)
            x2 = w
        if y2 > h:
            y1 -= (y2 - h)
            y2 = h
        # 再次钳制
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        # 裁剪
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            logger.warning("裁剪区域为空: x1=%d y1=%d x2=%d y2=%d (frame=%dx%d)",
                           x1, y1, x2, y2, w, h)
            return None

        # 高斯平滑 + 双三次插值放大
        # 高斯模糊消除锯齿 (kernel 大小随放大倍数调整，必须为奇数)
        blur_k = max(3, int(self._zoom_level) | 1)  # 确保奇数
        if blur_k > 1:
            crop = cv2.GaussianBlur(crop, (blur_k, blur_k), 0)
        # 双三次插值放大
        try:
            enlarged = cv2.resize(crop, (out_w, out_h), interpolation=cv2.INTER_CUBIC)
        except cv2.error as e:
            logger.error("resize 失败: %s", e)
            return None

        return enlarged

    def get_focus_indicator(self) -> Dict[str, Any]:
        """获取焦点指示信息，用于 UI 叠加显示。

        Returns:
            Dict:
                {
                    "target_center_x": float,   # 目标中心 X (像素)
                    "target_center_y": float,   # 目标中心 Y (像素)
                    "crop_size": Tuple[int,int],# 裁剪区域尺寸 (w, h)
                    "zoom_level": float,        # 当前数字变焦倍率
                    "track_id": int|None,       # 当前追踪 ID
                    "is_tracking": bool,        # 是否在追踪
                }
            未追踪时返回默认值。
        """
        if not self._is_tracking or self._smooth_center is None or self._smooth_size is None:
            return {
                "target_center_x": 0.0,
                "target_center_y": 0.0,
                "crop_size": (0, 0),
                "zoom_level": 1.0,
                "track_id": None,
                "is_tracking": False,
            }

        cx, cy = self._smooth_center
        tw, th = self._smooth_size
        # 裁剪尺寸 (与 get_tracking_crop 计算一致)
        crop_w = tw / self._zoom_level + tw * self.padding_ratio
        crop_h = th / self._zoom_level + th * self.padding_ratio
        crop_w = max(crop_w, 64.0)
        crop_h = max(crop_h, 64.0)

        return {
            "target_center_x": float(cx),
            "target_center_y": float(cy),
            "crop_size": (int(crop_w), int(crop_h)),
            "zoom_level": float(self._zoom_level),
            "track_id": self._track_id,
            "is_tracking": True,
        }

    def set_zoom(self, zoom: float) -> float:
        """手动设置变焦倍率 (会被钳制到 min~max 范围)。"""
        self._zoom_level = max(self.min_zoom, min(self.max_zoom, float(zoom)))
        return self._zoom_level

    def get_zoom(self) -> float:
        return self._zoom_level

    # ========================================================================
    # 内部方法
    # ========================================================================
    def _apply_ema_smoothing(self) -> None:
        """对目标中心和应用 EMA 平滑，避免抖动。

        公式: smoothed = alpha * new + (1 - alpha) * old
        """
        if self._raw_bbox is None or self._smooth_center is None or self._smooth_size is None:
            return

        x1, y1, x2, y2 = self._raw_bbox
        new_cx = (x1 + x2) / 2.0
        new_cy = (y1 + y2) / 2.0
        new_w = float(x2 - x1)
        new_h = float(y2 - y1)

        old_cx, old_cy = self._smooth_center
        old_w, old_h = self._smooth_size

        a = self.ema_alpha
        self._smooth_center = (a * new_cx + (1 - a) * old_cx,
                               a * new_cy + (1 - a) * old_cy)
        self._smooth_size = (a * new_w + (1 - a) * old_w,
                             a * new_h + (1 - a) * old_h)

        # 同步更新 _target_bbox (平滑后的)
        scx, scy = self._smooth_center
        sw, sh = self._smooth_size
        self._target_bbox = [
            int(scx - sw / 2.0),
            int(scy - sh / 2.0),
            int(scx + sw / 2.0),
            int(scy + sh / 2.0),
        ]

        logger.debug(
            "EMA 平滑: new=(%.1f,%.1f,%.1f,%.1f) smooth=(%.1f,%.1f) size=(%.1f,%.1f)",
            new_cx, new_cy, new_w, new_h,
            self._smooth_center[0], self._smooth_center[1],
            self._smooth_size[0], self._smooth_size[1],
        )

    def _pick_highest_priority_track(
        self, all_tracks: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """从所有 track 中选择优先级最高的目标。

        优先级:
            confirmed 违规车辆 (100) > pending 违规车辆 (50) > 普通车辆 (10)

        同优先级下选 confidence 最高的。

        Args:
            all_tracks: 所有 track 列表
        Returns:
            优先级最高的 track，无候选返回 None
        """
        best: Optional[Dict[str, Any]] = None
        best_score = -1.0

        for t in all_tracks:
            # 只追踪车辆类
            if t.get("class_name", "").lower() not in _VEHICLE_CLASSES:
                continue

            bbox = t.get("bbox")
            if not bbox or len(bbox) != 4:
                continue

            # 计算优先级
            status = str(t.get("status", "normal")).lower()
            has_violation = bool(t.get("violation_type"))

            if status == "confirmed" and has_violation:
                priority = _PRIORITY_WEIGHTS["confirmed_violation"]
            elif status == "pending" and has_violation:
                priority = _PRIORITY_WEIGHTS["pending_violation"]
            else:
                priority = _PRIORITY_WEIGHTS["normal_vehicle"]

            # 综合得分 = 优先级 + confidence (confidence 0~1 影响较小)
            conf = float(t.get("confidence", 0.0))
            score = priority + conf

            if score > best_score:
                best_score = score
                best = t

        if best is not None:
            logger.debug(
                "选择最高优先级目标: track_id=%s score=%.2f status=%s",
                best.get("track_id"), best_score, best.get("status"),
            )
        return best

    def _build_track_info(self, matched: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """构造当前追踪目标信息字典。"""
        info: Dict[str, Any] = {
            "track_id": self._track_id,
            "is_tracking": self._is_tracking,
            "smooth_center": self._smooth_center,
            "smooth_size": self._smooth_size,
            "smooth_bbox": self._target_bbox,
            "raw_bbox": self._raw_bbox,
            "zoom_level": self._zoom_level,
        }
        if matched is not None:
            info["class_name"] = matched.get("class_name")
            info["confidence"] = matched.get("confidence", 0.0)
            info["violation_type"] = matched.get("violation_type")
            info["status"] = matched.get("status", "normal")
        return info


# ----------------------------------------------------------------------------
# 模块自检 (python -m api.virtual_tracker)
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 60)
    print("Virtual Tracker 自检")
    print("=" * 60)

    # 构造测试帧 (1280x720 黑色画面)
    test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    tracker = VirtualTracker(ema_alpha=0.4, default_zoom=2.0)

    # 1. 未追踪时 get_focus_indicator
    print("\n[1] 未追踪状态")
    print(f"  is_tracking: {tracker.is_tracking()}")
    print(f"  indicator: {tracker.get_focus_indicator()}")
    print(f"  crop: {tracker.get_tracking_crop(test_frame)}")

    # 2. 锁定目标
    print("\n[2] 锁定目标 track_id=5")
    tracker.start_tracking(5, [400, 200, 600, 400])
    print(f"  is_tracking: {tracker.is_tracking()}")
    print(f"  indicator: {tracker.get_focus_indicator()}")

    # 3. 模拟目标移动 (EMA 平滑)
    print("\n[3] 模拟目标逐帧移动 (EMA 平滑)")
    tracks_seq = [
        [{"track_id": 5, "bbox": [410, 205, 610, 405], "class_name": "car",
          "confidence": 0.9, "violation_type": None, "status": "normal"}],
        [{"track_id": 5, "bbox": [430, 215, 630, 415], "class_name": "car",
          "confidence": 0.88, "violation_type": None, "status": "normal"}],
        [{"track_id": 5, "bbox": [460, 230, 660, 430], "class_name": "car",
          "confidence": 0.92, "violation_type": None, "status": "normal"}],
    ]
    for i, tracks in enumerate(tracks_seq):
        tracker.update(test_frame, tracks)
        ind = tracker.get_focus_indicator()
        print(f"  frame {i}: center=({ind['target_center_x']:.1f},{ind['target_center_y']:.1f}) zoom={ind['zoom_level']}")

    # 4. 裁剪测试
    print("\n[4] 裁剪测试")
    crop = tracker.get_tracking_crop(test_frame, out_size=(640, 640))
    if crop is not None:
        print(f"  crop shape: {crop.shape}")
    else:
        print("  crop: None")

    # 5. 优先级测试
    print("\n[5] 优先级测试")
    tracker.stop_tracking()
    mixed_tracks = [
        {"track_id": 1, "bbox": [100, 100, 200, 200], "class_name": "car",
         "confidence": 0.95, "violation_type": None, "status": "normal"},
        {"track_id": 2, "bbox": [300, 300, 400, 400], "class_name": "car",
         "confidence": 0.85, "violation_type": "running_red_light", "status": "pending"},
        {"track_id": 3, "bbox": [500, 500, 600, 600], "class_name": "car",
         "confidence": 0.80, "violation_type": "illegal_lane_change", "status": "confirmed"},
    ]
    tracker.update(test_frame, mixed_tracks)
    print(f"  自动锁定 track_id: {tracker.get_current_track_id()} (应为 3=confirmed)")
    print(f"  indicator: {tracker.get_focus_indicator()}")

    # 6. 丢失超时测试
    print("\n[6] 目标丢失超时测试")
    tracker.lost_timeout = 0.5  # 缩短超时便于测试
    tracker.start_tracking(99, [100, 100, 200, 200])
    print(f"  追踪中: {tracker.is_tracking()}")
    time.sleep(0.6)
    tracker.update(test_frame, [])  # 空 tracks
    print(f"  超时后追踪状态: {tracker.is_tracking()}")

    print("\n自检完成。")
