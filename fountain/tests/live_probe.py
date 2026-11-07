# -*- coding: utf-8 -*-
"""live_probe.py —— 音乐感应活体验证：边播边抓，只看 RMS 与三频段

判据（不靠自评，只看数字）：
  静音期 RMS < 0.01
  播放期 RMS > 0.05
  且 低/中/高 三段至少两段 > 0.3

用法：python tests/live_probe.py [wav路径] [秒数]
"""
import os
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

import numpy as np

from capture import CaptureConfig, SystemAudioCapture
from analyzer import AudioAnalyzer, AnalyzerConfig

WAV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "test_music.wav")
SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 14.0
BLOCK = 2048


def play_async(path):
    """用 winsound 异步播放，返回播放器句柄。"""
    import winsound
    winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    return winsound


def main():
    if not os.path.exists(WAV):
        print("找不到 wav:", WAV)
        return 2

    cap = SystemAudioCapture(CaptureConfig(block_size=BLOCK))
    cap.start()
    time.sleep(0.8)
    if not cap.is_running:
        print("采集启动失败:", cap.last_error)
        return 2
    sr = cap.sample_rate or 48000
    print("[采集] 设备=%s  采样率=%d" % (cap.device_name, sr))

    an = AudioAnalyzer(sr, BLOCK, AnalyzerConfig())

    # ---- 阶段 1：静音基线（2 秒，不放任何声音）----
    print("\n=== 阶段1 静音基线 2s ===")
    base_rms = []
    t_end = time.time() + 2.0
    while time.time() < t_end:
        b = cap.read_block(timeout=0.2)
        if b is None:
            continue
        base_rms.append(float(np.sqrt(np.mean(np.square(b)))))
    base = max(base_rms) if base_rms else -1
    print("静音 RMS 峰值 = %.4f  (%d 块)" % (base, len(base_rms)))

    # ---- 阶段 2：播放并抓取 ----
    print("\n=== 阶段2 播放 %s ===" % os.path.basename(WAV))
    cap.drain()
    w = play_async(WAV)

    play_rms = []
    segs = []
    t0 = time.time()
    last_print = 0.0
    try:
        while time.time() - t0 < SECS:
            b = cap.read_block(timeout=0.2)
            if b is None:
                continue
            play_rms.append(float(np.sqrt(np.mean(np.square(b)))))
            f = an.feed(b)
            segs.append((f.level, f.low, f.mid, f.high))
            now = time.time()
            if now - last_print >= 0.5:
                last_print = now
                print("  %5.1fs  音%.3f 低%.3f 中%.3f 高%.3f" %
                      (now - t0, f.level, f.low, f.mid, f.high))
    finally:
        w.PlaySound(None, w.SND_PURGE)
        cap.stop()

    peak = max(play_rms) if play_rms else -1
    mean = float(np.mean(play_rms)) if play_rms else -1
    print("\n播放 RMS 峰值 = %.4f  均值 = %.4f  (%d 块)" % (peak, mean, len(play_rms)))

    # ---- 判据 ----
    print("\n=== 判据 ===")
    ok = True

    def chk(name, cond, detail):
        global ok
        print("  [%s] %-22s %s" % ("PASS" if cond else "FAIL", name, detail))
        if not cond:
            ok = False

    chk("静音基线低", base >= 0 and base < 0.01, "静音RMS峰值=%.4f (阈值<0.01)" % base)
    chk("听到声音", peak > 0.05, "播放RMS峰值=%.4f (阈值>0.05)" % peak)
    chk("静音/播放分离", peak > base * 3 if base > 0 else peak > 0.05,
        "峰值%.4f / 基线%.4f = %.1f 倍" % (peak, base, (peak / base) if base > 1e-9 else float('inf')))

    if segs:
        mx = [max(s[i] for s in segs) for i in range(4)]
        chk("低频响应", mx[1] > 0.3, "低频峰值=%.3f" % mx[1])
        chk("中频响应", mx[2] > 0.3, "中频峰值=%.3f" % mx[2])
        chk("高频响应", mx[3] > 0.3, "高频峰值=%.3f" % mx[3])

    print("\n结果:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
