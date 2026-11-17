# -*- coding: utf-8 -*-
"""
视频循环缓存模块（GPT §5）

实时维护最近 N 秒视频帧 + 检测结果，事件触发后提取事件前后视频片段
合成完整事件视频，供云端 AI 复核使用。

设计要点：
- 用 collections.deque(maxlen=duration_sec*fps) 自动淘汰旧帧
- 线程安全（threading.Lock）
- 帧引用存储，extract_event_clip 时按需返回帧引用（不拷贝）
- save_event_video 先用 cv2.VideoWriter 写 mp4v 临时文件，再用 ffmpeg 转码 H.264
  （浏览器可播放）；ffmpeg 不可用或转码失败时回退保留 mp4v
"""

import os
import json
import time
import logging
import threading
import subprocess
from collections import deque
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

logger = logging.getLogger("circular_buffer")


def _get_ffmpeg_exe() -> str:
    """定位**真的能执行**的 ffmpeg 可执行文件

    优先级：imageio_ffmpeg 自带二进制 > PATH 上的 ffmpeg > WinGet 链接目录。

    ★2026-11-18 修正：候选必须试跑 `-version` 验证，不能只看 which 有没有结果。
      本机 PATH 上的 C:\\Users\\ROG\\.local\\bin\\ffmpeg.CMD 是个 shim，
      它原本指向 CanMV IDE 自带构建，那个目录后来被删了，运行只打印
      "系统找不到指定的路径"。旧实现直接返回 which('ffmpeg') 的结果，
      于是项目"以为找到了 ffmpeg"，每次转码都失败、静默回退 mp4v，
      媒体契约测试全红却没有任何告警指向真正原因。
    """
    from shutil import which
    candidates = []
    try:
        import imageio_ffmpeg
        candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass
    for name in ('ffmpeg', 'ffmpeg.exe'):
        p = which(name)
        if p and p not in candidates:
            candidates.append(p)
    if os.name == 'nt':
        _link = os.path.join(os.environ.get('LOCALAPPDATA', ''),
                             'Microsoft', 'WinGet', 'Links', 'ffmpeg.exe')
        if os.path.isfile(_link) and _link not in candidates:
            candidates.append(_link)

    for exe in candidates:
        try:
            r = subprocess.run(
                [exe, '-version'], capture_output=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            if r.returncode == 0:
                return exe
            logger.warning(f"[CircularFrameBuffer] ffmpeg 候选不可用（退出码 {r.returncode}）：{exe}")
        except Exception as e:
            logger.warning(f"[CircularFrameBuffer] ffmpeg 候选无法执行：{exe} ({e})")
    return ''


def _transcode_to_h264(src_path: str, dst_path: str, timeout: int = 120) -> bool:
    """将 mp4v 临时文件转码为浏览器兼容的 H.264。

    优先使用 libx264；若发行版未编译该编码器，则尝试 libopenh264，
    Windows 环境还可使用 Media Foundation。编码器不可用或转码失败时返回 False。
    """
    ffmpeg = _get_ffmpeg_exe()
    if not ffmpeg:
        logger.warning("[CircularFrameBuffer] 未找到 ffmpeg，跳过 H.264 转码（回退 mp4v）")
        return False
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        enc_result = subprocess.run(
            [ffmpeg, '-hide_banner', '-encoders'], capture_output=True,
            timeout=min(timeout, 20), creationflags=creationflags,
        )
        if enc_result.returncode != 0:
            logger.warning("[CircularFrameBuffer] 无法查询 ffmpeg 编码器列表，回退 mp4v")
            return False
        encoders = (enc_result.stdout or b'').decode('utf-8', errors='replace')
        if 'libx264' in encoders:
            encoder = 'libx264'
            encoder_options = ['-preset', 'veryfast', '-crf', '23']
        elif 'libopenh264' in encoders:
            encoder = 'libopenh264'
            encoder_options = ['-b:v', '2M']
        elif os.name == 'nt' and 'h264_mf' in encoders:
            encoder = 'h264_mf'
            encoder_options = ['-b:v', '2M']
        else:
            logger.warning("[CircularFrameBuffer] 当前 ffmpeg 没有可用的 H.264 编码器，回退 mp4v")
            return False

        cmd = [
            ffmpeg, '-y', '-i', src_path,
            '-c:v', encoder, *encoder_options,
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
            '-movflags', '+faststart',
            dst_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout,
                              creationflags=creationflags)
        ok = (proc.returncode == 0 and os.path.exists(dst_path)
              and os.path.getsize(dst_path) > 0)
        if not ok:
            logger.warning(f"[CircularFrameBuffer] H.264 转码失败 encoder={encoder} rc={proc.returncode} "
                           f"stderr={(proc.stderr or b'')[-300:]}")
        else:
            logger.info(f"[CircularFrameBuffer] H.264 转码成功 encoder={encoder}: {dst_path}")
        return ok
    except Exception as e:
        logger.warning(f"[CircularFrameBuffer] H.264 转码异常: {e}")
        return False


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

    def extract_event_clip_with_meta(self, trigger_time: float, before_sec: int = 5,
                                     after_sec: int = 5) -> List[Tuple[float, Any, dict]]:
        """提取事件视频片段（含逐帧检测/跟踪元数据，TASK-COORD-007）

        与 extract_event_clip 的唯一区别：不丢弃缓冲三元组的第三个元素，
        保留该帧缓存时的本地 YOLO/Tracking 数据（tracked_vehicles 等），
        供 save_event_video 写入逐帧回放 sidecar JSON。

        Args:
            trigger_time: 事件触发时间戳
            before_sec: 事件前秒数（默认 5s）
            after_sec: 事件后秒数（默认 5s）

        Returns:
            List[(timestamp, frame, detection_result)] 三元组列表
        """
        start_time = trigger_time - before_sec
        end_time = trigger_time + after_sec
        clip = []
        with self._lock:
            for ts, frame, det in self._buffer:
                if start_time <= ts <= end_time:
                    clip.append((ts, frame, det))
        logger.info(f"[CircularFrameBuffer] 提取事件片段(含元数据): trigger={trigger_time:.3f} "
                    f"range=[{start_time:.3f}, {end_time:.3f}] 返回 {len(clip)} 帧")
        return clip

    def save_event_video(self, frames: List[Tuple[float, Any]], output_path: str,
                         fps: int = 10) -> str:
        """将帧序列保存为视频文件

        Args:
            frames: extract_event_clip / extract_event_clip_with_meta 的返回值，
                    元素为 (timestamp, frame) 或 (timestamp, frame, detection_result)
            output_path: 输出路径
            fps: 输出视频帧率

        Returns:
            保存后的文件路径；若失败返回空字符串

        副作用：当帧携带检测/跟踪元数据时，额外写 sidecar JSON
        （路径 = output_path + '.replay.json'，与视频一一对应）。
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

        # 1) 先写 mp4v 到临时文件（OpenCV 原生可用，但 Chromium 无法解码 FMP4）
        tmp_path = output_path + '.tmp.mp4'
        first_frame = frames[0][1]
        h, w = first_frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(tmp_path, fourcc, fps, (w, h))
        if not writer.isOpened():
            logger.error(f"[CircularFrameBuffer] save_event_video: VideoWriter 打开失败 path={tmp_path}")
            return ""

        try:
            # 与实际写入视频的帧一一对应的元数据（无元数据的帧记 None，不补造）
            written_metas = []
            for item in frames:
                # 兼容三种形态：裸帧 ndarray / (ts, frame) / (ts, frame, meta)
                # ★2026-11-18：原先只按元组解析，传入裸 ndarray 时 len(item) 是
                #   图像高度，item[1] 取到的是第二行像素，随后 sidecar 里
                #   `meta or {}` 对 ndarray 做布尔判断直接抛
                #   "truth value of an array is ambiguous"。现在先认 ndarray。
                if hasattr(item, 'shape') and hasattr(item, 'dtype'):
                    frame, meta = item, None
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    frame = item[1]
                    meta = item[2] if len(item) >= 3 else None
                else:
                    continue
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
                written_metas.append(meta)
            writer.release()
        except Exception as e:
            logger.error(f"[CircularFrameBuffer] save_event_video 异常: {e}")
            writer.release()
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            return ""

        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            logger.error(f"[CircularFrameBuffer] save_event_video: mp4v 产物为空 path={tmp_path}")
            return ""

        # 2) ffmpeg 转码 H.264（浏览器兼容）；成功则最终产物即 output_path
        if _transcode_to_h264(tmp_path, output_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            logger.info(f"[CircularFrameBuffer] 保存事件视频(H.264): {output_path} 共 {len(frames)} 帧")
            self._write_replay_sidecar(output_path, written_metas, w, h, fps)
            return output_path

        # 3) 转码失败回退：保留 mp4v 产物，保证功能可用
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
            os.replace(tmp_path, output_path)
        except OSError as e:
            logger.error(f"[CircularFrameBuffer] save_event_video 回退移动失败: {e}")
            return ""
        logger.info(f"[CircularFrameBuffer] 保存事件视频(mp4v 回退): {output_path} 共 {len(frames)} 帧")
        self._write_replay_sidecar(output_path, written_metas, w, h, fps)
        return output_path

    def _write_replay_sidecar(self, video_path: str, frame_metas: list,
                              width: int, height: int, fps: int) -> Optional[str]:
        """将逐帧检测/跟踪元数据写入 sidecar JSON（TASK-COORD-007）

        - sidecar 路径 = {video_path}.replay.json，与事件视频一一对应
        - frame_metas 与视频实际写入帧按索引一一对应（无元数据的帧 vehicles 为空数组）
        - 数据全部来自本地 YOLO/Tracking 缓存元数据；缺失即留空，绝不补造
        - 写失败仅告警，不影响视频本身

        Returns:
            sidecar 路径；失败或无任何元数据时返回 None
        """
        try:
            # 所有帧均无元数据（如旧调用方传 2 元组）：不写 sidecar，
            # 让回放接口走"无逐帧回放数据"的诚实降级
            if not any(m is not None for m in frame_metas):
                logger.info(f"[CircularFrameBuffer] 帧序列无检测元数据，跳过 sidecar: {video_path}")
                return None

            frames = []
            for idx, meta in enumerate(frame_metas):
                vehicles = []
                tv = (meta or {}).get('tracked_vehicles') or []
                if isinstance(tv, dict):
                    tv = list(tv.values())
                for v in tv:
                    if not isinstance(v, dict):
                        continue
                    bbox = v.get('bbox')
                    if not (isinstance(bbox, (list, tuple)) and len(bbox) == 4):
                        continue
                    try:
                        bbox_f = [round(float(bbox[0]), 1), round(float(bbox[1]), 1),
                                  round(float(bbox[2]), 1), round(float(bbox[3]), 1)]
                    except (TypeError, ValueError):
                        continue
                    speed = v.get('speed')
                    vehicles.append({
                        'track_id': v.get('id'),
                        'class_name': v.get('class_name', 'unknown'),
                        'bbox': bbox_f,
                        'speed_px': round(float(speed), 2) if isinstance(speed, (int, float)) else None,
                        'direction': v.get('direction', 'unknown'),
                    })
                frames.append({
                    'index': idx,
                    'time': round(idx / float(fps), 3) if fps else idx,
                    'vehicles': vehicles,
                })

            sidecar = {
                'version': 1,
                'event_id': os.path.splitext(os.path.basename(video_path))[0],
                'source': 'local_yolo_tracker',
                'video_width': int(width),
                'video_height': int(height),
                'fps': int(fps),
                'frame_count': len(frames),
                'generated_at': datetime.now().isoformat(),
                'frames': frames,
            }
            sidecar_path = video_path + '.replay.json'
            with open(sidecar_path, 'w', encoding='utf-8') as f:
                json.dump(sidecar, f, ensure_ascii=False)
            logger.info(f"[CircularFrameBuffer] 回放 sidecar 已写入: {sidecar_path} frames={len(frames)}")
            return sidecar_path
        except Exception as e:
            logger.warning(f"[CircularFrameBuffer] 回放 sidecar 写入失败: {e}")
            return None

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
