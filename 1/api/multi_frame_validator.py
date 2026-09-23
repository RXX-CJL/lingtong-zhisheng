# -*- coding: utf-8 -*-
"""
多帧确认机制

滑动窗口 + 车牌相似度匹配 + IOU/中心距离双重 bbox 匹配，
避免单帧误判。

采纳 TASK-027 建议:
- 改进 bbox 与 tracking 的匹配精度：IOU + 中心距离双重匹配
- FPS 监控：滑动窗口 FPS（过去 30 帧平均）
"""

import time
from collections import deque
from typing import List, Dict, Optional, Tuple
import logging
import numpy as np

logger = logging.getLogger(__name__)


def levenshtein_similarity(s1: str, s2: str) -> float:
    """Levenshtein 相似度（0~1，1=完全相同）"""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    len1, len2 = len(s1), len(s2)
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)

    max_len = max(len1, len2)
    return 1.0 - dp[len1][len2] / max_len if max_len > 0 else 0.0


def calculate_iou(bbox1: list, bbox2: list) -> float:
    """计算两个 bbox 的 IOU"""
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    inter = (x2 - x1) * (y2 - y1)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union = area1 + area2 - inter

    return inter / union if union > 0 else 0.0


def calculate_center_distance(bbox1: list, bbox2: list) -> float:
    """计算两个 bbox 中心点距离"""
    cx1 = (bbox1[0] + bbox1[2]) / 2
    cy1 = (bbox1[1] + bbox1[3]) / 2
    cx2 = (bbox2[0] + bbox2[2]) / 2
    cy2 = (bbox2[1] + bbox2[3]) / 2
    return np.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)


def bbox_match(bbox1: list, bbox2: list, iou_threshold: float = 0.3,
               center_dist_ratio: float = 0.3) -> bool:
    """
    bbox 匹配：IOU ≥ 阈值 **或** 中心距离 ≤ 平均尺寸 * 比例
    采纳 TASK-027 建议：双重匹配提升精度
    """
    if not bbox1 or not bbox2:
        return False

    # IOU 匹配
    iou = calculate_iou(bbox1, bbox2)
    if iou >= iou_threshold:
        return True

    # 中心距离匹配
    dist = calculate_center_distance(bbox1, bbox2)
    avg_size = ((bbox1[2] - bbox1[0] + bbox1[3] - bbox1[1]) / 2 +
                (bbox2[2] - bbox2[0] + bbox2[3] - bbox2[1]) / 2) / 2
    if avg_size > 0 and dist <= avg_size * center_dist_ratio:
        return True

    return False


class MultiFrameValidator:
    """多帧确认验证器"""

    def __init__(self, window_size: int = 10, confirm_threshold: int = 5,
                 plate_sim_threshold: float = 0.8):
        """
        Args:
            window_size: 滑动窗口大小（帧数）
            confirm_threshold: 确认所需最少帧数
            plate_sim_threshold: 车牌相似度阈值
        """
        self.window_size = window_size
        self.confirm_threshold = confirm_threshold
        self.plate_sim_threshold = plate_sim_threshold
        self.frame_history: deque = deque(maxlen=window_size)
        self.confirmed_records: List[Dict] = []
        self.pending: Dict[int, Dict] = {}  # track_id -> pending info

    def add_frame(self, frame_results: List[Dict]) -> List[Dict]:
        """
        添加一帧的检测结果

        Args:
            frame_results: [{'track_id': int, 'plate': str, 'violation_type': str, 'bbox': list}, ...]

        Returns:
            当前帧的 pending 列表
        """
        timestamp = time.time()
        self.frame_history.append({
            'timestamp': timestamp,
            'results': frame_results
        })

        # 更新 pending
        current_pending = []
        for item in frame_results:
            track_id = item.get('track_id', -1)
            plate = item.get('plate', '')
            violation_type = item.get('violation_type', '')
            bbox = item.get('bbox', [])

            if track_id < 0:
                continue

            # 查找已有 pending
            matched_id = self._find_matching_pending(track_id, plate, bbox)

            if matched_id is not None:
                p = self.pending[matched_id]
                p['frames'] += 1
                # 车牌投票
                if plate:
                    if plate not in p['plate_votes']:
                        p['plate_votes'][plate] = 0
                    p['plate_votes'][plate] += 1
                p['last_seen'] = timestamp
                p['bbox'] = bbox

                current_pending.append({
                    'track_id': matched_id,
                    'plate': self._get_best_plate(matched_id),
                    'votes': p['frames'],
                    'confirmed': p['frames'] >= self.confirm_threshold
                })
            else:
                # 新 pending
                self.pending[track_id] = {
                    'frames': 1,
                    'plate_votes': {plate: 1} if plate else {},
                    'violation_type': violation_type,
                    'bbox': bbox,
                    'first_seen': timestamp,
                    'last_seen': timestamp
                }
                current_pending.append({
                    'track_id': track_id,
                    'plate': plate,
                    'votes': 1,
                    'confirmed': False
                })

        # 清理过期的 pending（超过窗口时间未更新）
        self._cleanup_expired(timestamp)

        return current_pending

    def get_confirmed(self) -> List[Dict]:
        """获取已确认的记录（连续 ≥ M 帧同车牌+同违规）"""
        confirmed = []
        to_remove = []

        for track_id, p in self.pending.items():
            if p['frames'] >= self.confirm_threshold:
                best_plate = self._get_best_plate(track_id)
                confirmed.append({
                    'track_id': track_id,
                    'plate_number': best_plate,
                    'violation_type': p['violation_type'],
                    'confirmed_frames': p['frames'],
                    'bbox': p['bbox'],
                    'confidence': min(1.0, p['frames'] / self.window_size)
                })
                to_remove.append(track_id)

        for tid in to_remove:
            del self.pending[tid]

        self.confirmed_records.extend(confirmed)
        return confirmed

    def pending_info(self) -> Dict:
        """获取所有 pending 信息"""
        return {
            tid: {
                'plate_histo': p['plate_votes'],
                'frames': p['frames'],
                'votes': p['frames'],
                'violation_type': p['violation_type']
            }
            for tid, p in self.pending.items()
        }

    @property
    def pending_count(self) -> int:
        return len(self.pending)

    @property
    def confirmed_count(self) -> int:
        return len(self.confirmed_records)

    def _find_matching_pending(self, track_id: int, plate: str, bbox: list) -> Optional[int]:
        """查找匹配的 pending 记录"""
        # 1. track_id 直接匹配
        if track_id in self.pending:
            return track_id

        # 2. 车牌 + bbox 匹配
        for tid, p in self.pending.items():
            # 车牌相似度匹配
            if plate and p['plate_votes']:
                best_plate = max(p['plate_votes'], key=p['plate_votes'].get)
                if levenshtein_similarity(plate, best_plate) >= self.plate_sim_threshold:
                    if bbox_match(bbox, p.get('bbox', [])):
                        return tid
            # 仅 bbox 匹配（车牌未识别时）
            elif not plate and bbox and bbox_match(bbox, p.get('bbox', [])):
                return tid

        return None

    def _get_best_plate(self, track_id: int) -> str:
        """获取投票数最多的车牌"""
        p = self.pending.get(track_id, {})
        if not p.get('plate_votes'):
            return ''
        return max(p['plate_votes'], key=p['plate_votes'].get)

    def _cleanup_expired(self, current_time: float, max_age: float = 5.0):
        """清理过期的 pending 记录"""
        expired = [tid for tid, p in self.pending.items()
                   if current_time - p['last_seen'] > max_age]
        for tid in expired:
            del self.pending[tid]


class FPSMonitor:
    """FPS 监控器（滑动窗口，过去 N 帧的平均 FPS）
    采纳 TASK-027 建议：在 process_frame 中添加 FPS 监控"""

    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.timestamps: deque = deque(maxlen=window_size)

    def tick(self):
        """记录一帧的时间戳"""
        self.timestamps.append(time.time())

    @property
    def avg_fps(self) -> float:
        """平均 FPS"""
        if len(self.timestamps) < 2:
            return 0.0
        elapsed = self.timestamps[-1] - self.timestamps[0]
        if elapsed <= 0:
            return 0.0
        return (len(self.timestamps) - 1) / elapsed

    def reset(self):
        self.timestamps.clear()
