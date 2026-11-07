# -*- coding: utf-8 -*-
"""bench.py —— 实测各环节耗时，定位刷新率瓶颈

为什么需要这个：水柱刷新率 = 1 / (音频帧周期 + 处理耗时 + 写MCGS耗时)
想提高刷新率，必须知道哪一段占大头，不能靠猜。

用法：python tests/bench.py [块大小]
"""
from __future__ import annotations

import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import numpy as np

from capture import CaptureConfig, SystemAudioCapture
from analyzer import AudioAnalyzer, AnalyzerConfig
from mapper import HeightMapper, MapperConfig
from modbus_client import ModbusWriter

BLOCK = int(sys.argv[1]) if len(sys.argv) > 1 else 2048
N = 80


def pct(vals, p):
    a = sorted(vals)
    i = max(0, min(len(a) - 1, int(len(a) * p / 100)))
    return a[i]


def main() -> int:
    cap = SystemAudioCapture(CaptureConfig(block_size=BLOCK))
    cap.start()
    time.sleep(1.0)
    if not cap.is_running:
        print("采集启动失败:", cap.last_error)
        return 2
    sr = cap.sample_rate or 48000
    frame_ms = BLOCK / sr * 1000

    an = AudioAnalyzer(sr, BLOCK, AnalyzerConfig())
    mp = HeightMapper(MapperConfig())
    w = ModbusWriter()
    connected = w.connect()

    print("=" * 62)
    print("  块大小=%d  采样率=%d  音频帧周期=%.2f ms" % (BLOCK, sr, frame_ms))
    print("  MCGS 连接 = %s" % connected)
    if not connected:
        print("  !! MCGS 未连接 → 写耗时无法测量，下面的结论不含写入部分")
        print("     （别把『写MCGS 0.00ms』当成真的快，那是没测到）")
    print("=" * 62)

    t_read, t_an, t_mp, t_wr = [], [], [], []
    for _ in range(N):
        t0 = time.perf_counter()
        b = cap.read_block(timeout=0.5)
        t1 = time.perf_counter()
        if b is None:
            continue
        f = an.feed(b)
        t2 = time.perf_counter()
        h = mp.update(f, BLOCK / sr)
        t3 = time.perf_counter()
        if connected:
            w.write_all([int(round(v)) for v in h])
            t4 = time.perf_counter()
            t_wr.append((t4 - t3) * 1000)
        t_read.append((t1 - t0) * 1000)
        t_an.append((t2 - t1) * 1000)
        t_mp.append((t3 - t2) * 1000)

    cap.stop()
    if connected:
        w.write_all([0] * 11)
        w.close()

    def line(name, vals, note=""):
        if not vals:
            print("  %-16s  (无数据) %s" % (name, note))
            return 0.0
        m = sum(vals) / len(vals)
        print("  %-16s 均值=%6.2f ms  p95=%6.2f ms  max=%6.2f ms  %s"
              % (name, m, pct(vals, 95), max(vals), note))
        return m

    print("\n【各环节耗时】")
    m_read = line("读音频块", t_read, "（含等下一块到达）")
    m_an = line("音频分析", t_an, "FFT + AGC + 节拍")
    m_mp = line("高度映射", t_mp, "分层合成 + 量化")
    m_wr = line("写MCGS(11个)", t_wr, "11次FC06往返")

    # 真实处理耗时（不含等待）
    proc = m_an + m_mp + m_wr
    print("\n【结论】")
    if not connected:
        print("  !! 本次没有测到写MCGS耗时（未连接），结论不完整")
    print("  真实处理耗时 = %.2f ms （音频分析 %.2f + 映射 %.2f + 写MCGS %.2f）"
          % (proc, m_an, m_mp, m_wr))
    print("  音频帧周期   = %.2f ms" % frame_ms)
    if proc < frame_ms:
        print("  → 处理比音频快 %.1f 倍，瓶颈在音频块大小，不在代码" % (frame_ms / max(proc, 1e-6)))
    else:
        print("  → 处理慢于音频！瓶颈在代码，需要优化")

    print("\n【理论刷新率上限】")
    print("  受音频块大小限制：最大 %.1f Hz（每 %.1f ms 一帧）" % (1000.0 / frame_ms, frame_ms))
    for blk in (4096, 2048, 1024, 512, 256):
        print("    块=%-5d → %.1f ms → %.1f Hz" % (blk, blk / sr * 1000, sr / blk))
    print("\n  但 MCGS 采集周期是 100ms（设备属性里设的），")
    print("  所以最终画面上限 = min(音频刷新率, 10 Hz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
