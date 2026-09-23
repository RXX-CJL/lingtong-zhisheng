# -*- coding: utf-8 -*-
"""
视频循环缓存模块（GPT §5）

实时维护最近 N 秒视频帧 + 检测结果，事件触发后提取事件前后视频片段
合成完整事件视频，供云端 AI 复核使用。

设计要点：
- 用 collections.deque(maxlen=duration_sec*fps) 自动淘汰旧帧
- 线程安全（threading.Lock）
- 帧引用存储，extract_event_clip 时按需返回帧引用（不拷贝）
- save_event_video 用 cv2.VideoWriter 写 mp4v 编码
"""

import os
import time
import logging
import threading
from collections import deque
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

logger = logging.getLogger("circular_buffer")


class CircularFrameBuffer:
    """视频循环缓存 — 实时维护最近 N 秒视频帧+检测结果

    事件触发后提取事件前后视频片段合成完整事件视频。

    属性:
        duration_sec: 缓存时长（秒），默认 30s
        fps: 预期帧率，默认 10fps
        maxlen: 内部 deque 最大长度 = duration_sec * fps
    """

    def __init__(self, duration_sec: int = 30, fps: int = 10):
        """初始化循环缓存

        Args:
            duration_sec: 缓存时长（秒），默认 30s
            fps: 预期帧率，默认 10fps
        """
        if duration_sec <= 0 or fps <= 0:
            raise ValueError(f"duration_sec 和 fps 必须为正数，收到 duration_sec={duration_sec}, fps={fps}")
        self.duration_sec = duration_sec
        self.fps = fps
        self.maxlen = duration_sec * fps
        # 内部存储 deque，元素为 (timestamp, frame, detection_result)
        self._buffer: deque = deque(maxlen=self.maxlen)
        self._lock = threading.Lock()
        logger.info(f"[CircularFrameBuffer] 初始化: duration={duration_sec}s fps={fps} maxlen={self.maxlen}")

    def add(self, timestamp: float, frame, detection_result: dict):
        """添加一帧到缓存

        Args:
            timestamp: time.time() 时间戳
            frame: numpy ndarray (BGR)
            detection_result: 当前帧的检测结果 dict（detections/tracked_vehicles/behaviors）
        """
        if frame is None:
            return
        with self._lock:
            self._buffer.append((timestamp, frame, detection_result))

    def extract_event_clip(self, trigger_time: float, before_sec: int = 5,
                          after_sec: int = 5) -> List[Tuple[float, Any]]:
        """提取事件视频片段

        Args:
            trigger_time: 事件触发时间戳
            before_sec: 事件前秒数（默认 5s）
            after_sec: 事件后秒数（默认 5s）

        Returns:
            List[(timestamp, frame)] 用于合成事件视频
        """
        start_time = trigger_time - before_sec
        end_time = trigger_time + after_sec
        clip = []
        with self._lock:
            for ts, frame, _ in self._buffer:
                if start_time <= ts <= end_time:
                    clip.append((ts, frame))
        logger.info(f"[CircularFrameBuffer] 提取事件片段: trigger={trigger_time:.3f} "
                    f"range=[{start_time:.3f}, {end_time:.3f}] 返回 {len(clip)} 帧")
        return clip

    def save_event_video(self, frames: List[Tuple[float, Any]], output_path: str,
                         fps: int = 10) -> str:
        """将帧序列保存为视频文件

        Args:
            frames: extract_event_clip 的返回值 [(timestamp, frame)]
            output_path: 输出路径
            fps: 输出视频帧率

        Returns:
            保存后的文件路径；若失败返回空字符串
        """
        if not frames:
            logger.warning("[CircularFrameBuffer] save_event_video: frames 为空，跳过")
            return ""

        try:
            import cv2
        except ImportError:
            logger.error("[CircularFrameBuffer] save_event_video: cv2 未安装")
            return ""

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 用第一帧确定视频尺寸
        first_frame = frames[0][1]
        h, w = first_frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
        if not writer.isOpened():
            logger.error(f"[CircularFrameBuffer] save_event_video: VideoWriter 打开失败 path={output_path}")
            return ""

        try:
            for _, frame in frames:
                if frame is None:
                    continue
                # 兼容灰度图
                if len(frame.shape) == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                # 尺寸不一致则 resize
                fh, fw = frame.shape[:2]
                if (fw, fh) != (w, h):
                    frame = cv2.resize(frame, (w, h))
                writer.write(frame)
            writer.release()
            logger.info(f"[CircularFrameBuffer] 保存事件视频: {output_path} 共 {len(frames)} 帧")
            return output_path
        except Exception as e:
            logger.error(f"[CircularFrameBuffer] save_event_video 异常: {e}")
            writer.release()
            return ""

    def get_latest(self, n: int = 1) -> List[Tuple[float, Any, dict]]:
        """获取最近 n 帧

        Args:
            n: 帧数

        Returns:
            List[(timestamp, frame, detection_result)]
        """
        with self._lock:
            if n >= len(self._buffer):
                return list(self._buffer)
            return list(self._buffer)[-n:]

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._buffer.clear()
        logger.info("[CircularFrameBuffer] 缓存已清空")

    @property
    def size(self) -> int:
        """当前缓存帧数"""
        with self._lock:
            return len(self._buffer)

    @property
    def duration(self) -> float:
        """当前缓存覆盖的时长（秒）

        用首尾时间戳差值计算；若不足 2 帧则返回 0。
        """
        with self._lock:
            if len(self._buffer) < 2:
                return 0.0
            first_ts = self._buffer[0][0]
            last_ts = self._buffer[-1][0]
            return max(0.0, last_ts - first_ts)

    def generate_event_video_path(self, event_id: str, base_dir: Optional[str] = None) -> str:
        """生成事件视频输出路径

        Args:
            event_id: 事件 ID
            base_dir: 基础目录（默认用 Config.EVENT_VIDEO_DIR）

        Returns:
            完整路径 {base_dir}/{YYYYMMDD}/{event_id}.mp4
        """
        if base_dir is None:
            try:
                from config import Config
                base_dir = Config.EVENT_VIDEO_DIR
            except Exception:
                base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        'output', 'event_videos')
        date_str = datetime.now().strftime('%Y%m%d')
        return os.path.join(base_dir, date_str, f'{event_id}.mp4')


# 模块级单例（按需创建，避免无事件场景浪费内存）
_singleton_instance: Optional[CircularFrameBuffer] = None
_singleton_lock = threading.Lock()


def get_default_buffer() -> CircularFrameBuffer:
    """获取默认 CircularFrameBuffer 单例（按 Config 配置初始化）"""
    global _singleton_instance
    if _singleton_instance is not None:
        return _singleton_instance
    with _singleton_lock:
        if _singleton_instance is None:
            try:
                from config import Config
                _singleton_instance = CircularFrameBuffer(
                    duration_sec=Config.FRAME_BUFFER_DURATION,
                    fps=Config.FRAME_BUFFER_FPS,
                )
            except Exception:
                _singleton_instance = CircularFrameBuffer()
        return _singleton_instance
