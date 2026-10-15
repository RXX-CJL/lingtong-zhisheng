# -*- coding: utf-8 -*-
"""车牌识别器（hyperlpr3 封装）—— 车辆框裁剪 + 放大后识别

背景（2026-10-03 由 DSH 接入）：
  项目原车牌识别依赖 paddleocr，未安装 -> 长期降级。
  改用 hyperlpr3（pip 一条、不依赖 numpy、不冲突现有环境）。

实测关键点：
  - 直接在 1280x576 全图上识别 -> 检不到（车牌仅几十像素）
  - **裁剪车辆框 + 放大 2 倍** -> 可识别（实测 粤G7N263 0.99 / 浙EDK217 0.88）
  所以本模块对外暴露的是"整帧 + 车辆框列表 -> 车牌"的接口。

设计：
  - 懒加载 + 单例，线程安全
  - 屏蔽 numpy 2.x 的 RuntimeWarning（hyperlpr3 内部有空切片均值计算）
  - 失败静默返回 None（不影响主流程，车牌属增强信息）
  - 带 TTL 缓存：同一 track 在 TTL 内不重复识别（节省算力）
"""

import os
import threading
import time
import warnings
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

# hyperlpr3 在 numpy 2.x 下会产生 RuntimeWarning（Mean of empty slice），此处屏蔽
warnings.filterwarnings("ignore")
np.seterr(all="ignore")

_lock = threading.Lock()
_catcher = None
_load_failed = False

_CACHE_TTL = float(os.environ.get("PLATE_CACHE_TTL", "30"))   # 秒
_cache: Dict[int, Tuple[str, float]] = {}                      # track_id -> (plate, ts)
_UPSCALE = float(os.environ.get("PLATE_UPSCALE", "2.0"))
_MIN_BOX = int(os.environ.get("PLATE_MIN_BOX", "60"))


def _ensure_loaded() -> bool:
    global _catcher, _load_failed
    if _catcher is not None:
        return True
    if _load_failed:
        return False
    with _lock:
        if _catcher is not None:
            return True
        if _load_failed:
            return False
        try:
            import hyperlpr3 as lpr3
            _catcher = lpr3.LicensePlateCatcher()
            return True
        except Exception:
            _load_failed = True
            return False


def is_available() -> bool:
    return _ensure_loaded()


def recognize_in_frame(frame: np.ndarray,
                       vehicle_boxes: Optional[List] = None,
                       track_ids: Optional[List] = None) -> List[Dict]:
    """在整帧里识别车牌

    Args:
        frame: BGR 整帧
        vehicle_boxes: [[x1,y1,x2,y2], ...] 车辆框（可选；提供则只在框内识别，准确率高得多）
        track_ids: 与 vehicle_boxes 对应的 track id（用于缓存）

    Returns:
        [{"plate": str, "confidence": float, "bbox": [x1,y1,x2,y2], "track_id": int|None}, ...]
    """
    if frame is None or frame.size == 0 or not _ensure_loaded():
        return []

    results: List[Dict] = []
    regions = []

    if vehicle_boxes:
        for i, bb in enumerate(vehicle_boxes):
            try:
                x1, y1, x2, y2 = [int(v) for v in bb[:4]]
            except Exception:
                continue
            if (x2 - x1) < _MIN_BOX or (y2 - y1) < 40:
                continue
            tid = None
            if track_ids and i < len(track_ids):
                try:
                    tid = int(track_ids[i])
                except (TypeError, ValueError):
                    tid = None
            # 缓存命中则跳过
            if tid is not None:
                hit = _cache.get(tid)
                if hit and (time.time() - hit[1]) < _CACHE_TTL:
                    continue
            regions.append(((x1, y1, x2, y2), tid))
    else:
        regions.append(((0, 0, frame.shape[1], frame.shape[0]), None))

    H, W = frame.shape[:2]
    for (x1, y1, x2, y2), tid in regions:
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(W, x2), min(H, y2)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        if _UPSCALE != 1.0:
            crop = cv2.resize(crop, None, fx=_UPSCALE, fy=_UPSCALE,
                              interpolation=cv2.INTER_CUBIC)
        try:
            res = _catcher(crop)
        except Exception:
            continue
        for item in (res or []):
            try:
                plate = str(item[0])
                conf = float(item[1])
                # item 可能含 bbox（相对裁剪图坐标），转换回整帧坐标
                bbox = [x1, y1, x2, y2]
                if len(item) >= 4 and isinstance(item[3], (list, tuple)) and len(item[3]) == 4:
                    try:
                        bx1, by1, bx2, by2 = [float(v) / _UPSCALE for v in item[3]]
                        bbox = [int(x1 + bx1), int(y1 + by1), int(x1 + bx2), int(y1 + by2)]
                    except Exception:
                        pass
                results.append({"plate": plate, "confidence": conf,
                                "bbox": bbox, "track_id": tid})
                if tid is not None:
                    _cache[tid] = (plate, time.time())
            except Exception:
                continue

    # 清理过期缓存
    if len(_cache) > 200:
        now = time.time()
        for k in [k for k, v in _cache.items() if now - v[1] > _CACHE_TTL]:
            _cache.pop(k, None)

    return results


def cached_plate(track_id: int) -> Optional[str]:
    """读取某 track 的缓存车牌（供画框时零延迟使用）"""
    hit = _cache.get(int(track_id))
    if hit and (time.time() - hit[1]) < _CACHE_TTL:
        return hit[0]
    return hit[0] if hit else None
