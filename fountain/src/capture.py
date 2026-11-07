# -*- coding: utf-8 -*-
"""
capture.py —— WASAPI Loopback 系统音频采集（模式四的耳朵）

只用 SoundCard 的 loopback 端点抓"电脑正在播放的声音"，不用麦克风。
关键设计（都是第一阶段审计结论的落实）：
1) 每 1 秒核对一次当前默认输出设备是否变了（插耳机/切 HDMI/接蓝牙都会变），
   变了就重建采集流——否则会出现"换了耳机喷泉就不动了"。
2) 采样率以设备实际值为准，不写死 44100/48000。
3) 采集异常不抛到主流程，用状态位暴露，让上层走安全回落。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

import numpy as np

try:
    import soundcard as sc
except ImportError:  # 给上层一个明确的错，而不是静默降级
    sc = None


@dataclass
class CaptureConfig:
    block_size: int = 2048
    device_check_interval_s: float = 1.0
    queue_max_blocks: int = 64


class SystemAudioCapture:
    """后台线程持续抓系统输出音频，主线程取帧。"""

    def __init__(self, cfg: CaptureConfig | None = None):
        self.cfg = cfg or CaptureConfig()
        self._q = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._device_name = ""
        self._sample_rate = 0
        self._fail_count = 0
        self._last_error = ""
        self._running = False

    # ---- 属性（给上层做安全回落用）--------------------------------
    @property
    def device_name(self) -> str:
        return self._device_name

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def is_running(self) -> bool:
        return self._running and not self._stop.is_set()

    @property
    def last_error(self) -> str:
        return self._last_error

    # ---- 设备查找 --------------------------------------------------
    @staticmethod
    def _find_loopback():
        """返回 (loopback_mic, default_speaker) 或 (None, None)。"""
        if sc is None:
            return None, None
        try:
            spk = sc.default_speaker()
        except Exception:
            spk = None
        try:
            mics = sc.all_microphones(include_loopback=True)
        except Exception:
            return None, spk
        loops = [m for m in mics if getattr(m, "isloopback", False)]
        if not loops:
            return None, spk
        # 有默认扬声器就优先挑同名端点
        if spk is not None:
            for m in loops:
                if m.name == spk.name:
                    return m, spk
        return loops[0], spk

    # ---- 线程主体 --------------------------------------------------
    def _worker(self):
        last_check = 0.0
        rec_ctx = None
        mic = None
        while not self._stop.is_set():
            now = time.monotonic()

            # 定期核对默认设备
            if now - last_check >= self.cfg.device_check_interval_s:
                last_check = now
                cur_mic, spk = self._find_loopback()
                if cur_mic is None:
                    self._running = False
                    self._last_error = "找不到 WASAPI loopback 设备"
                    self._stop.wait(0.5)
                    continue
                if rec_ctx is None or cur_mic.name != self._device_name:
                    # 设备变了（或首次），重建
                    try:
                        if rec_ctx is not None:
                            try:
                                rec_ctx.__exit__(None, None, None)
                            except Exception:
                                pass
                        sr = 48000
                        if spk is not None:
                            try:
                                sr = int(getattr(spk, "default_samplerate", 48000) or 48000)
                            except Exception:
                                sr = 48000
                        rec_ctx = cur_mic.recorder(
                            samplerate=sr, channels=2,
                            blocksize=self.cfg.block_size,
                            exclusive_mode=False,
                        )
                        rec_ctx.__enter__()
                        mic = cur_mic
                        self._device_name = cur_mic.name
                        self._sample_rate = sr
                        self._running = True
                        self._last_error = ""
                    except Exception as e:
                        self._running = False
                        self._last_error = "打开采集流失败: %r" % (e,)
                        rec_ctx = None
                        self._stop.wait(0.5)
                        continue

            # 读一块
            try:
                data = rec_ctx.record(numframes=self.cfg.block_size)
                arr = np.asarray(data, dtype=np.float32)
                self._fail_count = 0
                self._running = True
                with self._lock:
                    if len(self._q) >= self.cfg.queue_max_blocks:
                        self._q.pop(0)          # 丢最旧的，保证实时
                    self._q.append(arr)
            except Exception as e:
                self._fail_count += 1
                self._last_error = "采集失败: %r" % (e,)
                if self._fail_count >= 3:
                    self._running = False
                    # 强制下一轮重建
                    try:
                        if rec_ctx is not None:
                            rec_ctx.__exit__(None, None, None)
                    except Exception:
                        pass
                    rec_ctx = None
                    self._device_name = ""
                self._stop.wait(0.05)

        # 收尾
        try:
            if rec_ctx is not None:
                rec_ctx.__exit__(None, None, None)
        except Exception:
            pass
        self._running = False

    # ---- 对外接口 --------------------------------------------------
    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True,
                                        name="SystemAudioCapture")
        self._thread.start()

    def stop(self, timeout: float = 2.0):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def read_block(self, timeout: float = 0.5):
        """取一块。没数据返回 None（不是零数组——静音和"没抓到"要能区分）。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if self._q:
                    return self._q.pop(0)
            if self._stop.is_set():
                return None
            time.sleep(0.002)
        return None

    def drain(self):
        with self._lock:
            n = len(self._q)
            self._q.clear()
        return n
