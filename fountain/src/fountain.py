# -*- coding: utf-8 -*-
"""fountain.py —— 音乐驱动喷泉主程序

用法：
  python fountain.py                  # 实时监听 + 写 MCGS
  python fountain.py --dry            # 只听不动（不连 MCGS）
  python fountain.py --seconds 20     # 跑 20 秒后退出
  python fountain.py --log out.csv    # 存每帧数据

退出：Ctrl+C
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer import AudioAnalyzer, AnalyzerConfig
from capture import CaptureConfig, SystemAudioCapture
from mapper import HeightMapper, MapperConfig
from modbus_client import ModbusWriter

BAR = "........................................"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只预览，不写 MCGS")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--unit", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=0.0)
    ap.add_argument("--log", default="")
    ap.add_argument("--block", type=int, default=1024)
    ap.add_argument("--write-interval", type=float, default=0.02,
                    help="写 MCGS 的间隔秒数（默认 0.02 = 50Hz）。"
                         "要与 MCGS 设备属性里的『最小采集周期』匹配，"
                         "否则写太快只会堆积等待，不会更快。")
    args = ap.parse_args()

    # ---- 1) 先启动采集，拿到真实采样率 ----
    cap = SystemAudioCapture(CaptureConfig(block_size=args.block))
    cap.start()
    time.sleep(0.8)
    if not cap.is_running:
        print("采集启动失败：", cap.last_error)
        return 2
    sr = cap.sample_rate or 48000
    print("[采集] 设备=%s  采样率=%d  块大小=%d" % (cap.device_name, sr, args.block))

    # ---- 2) 分析器要用真实采样率构造 ----
    an = AudioAnalyzer(sr, args.block, AnalyzerConfig())
    mp = HeightMapper(MapperConfig())

    # ---- 3) MCGS ----
    mb = ModbusWriter(args.host, args.port, args.unit)
    dry = args.dry
    if not dry:
        if mb.connect():
            print("[MCGS] 已连接 %s:%d 站号 %d" % (args.host, args.port, args.unit))
        else:
            print("[MCGS] 连接失败(%s) → 转为只看不写" % mb.last_error)
            dry = True
    if dry:
        print("[MCGS] 预览模式（不写寄存器）")

    log_f = log_w = None
    if args.log:
        log_f = open(args.log, "w", newline="", encoding="utf-8")
        log_w = csv.writer(log_f)
        log_w.writerow(["t", "level", "low", "mid", "high", "onset", "onset_str",
                        "climax", "silent"] + ["H%d" % (i + 1) for i in range(11)])

    print()
    print("=" * 76)
    print(" 破晓·潮汐 — 音乐智能响应   %s" % ("【预览】" if dry else "【已接 MCGS】"))
    print("=" * 76)
    print(" 现在去放音乐（网易云 / QQ音乐 / 浏览器 / 游戏都行）。Ctrl+C 退出。")
    print()

    dt = args.block / float(sr)
    t0 = time.time()
    last_write = 0.0
    last_draw = 0.0
    # ★ 2026-11-05：原来写死 0.10（100ms），等于把刷新率锁在 10 Hz。
    #   改成命令行参数，默认 0.02（20ms）与 MCGS 采集周期对齐。
    #   实测 FC16 写 11 个寄存器只要 15ms，20ms 间隔完全跟得上。
    write_interval = args.write_interval
    frames = 0
    writes = 0
    msg = ""

    try:
        while True:
            now = time.time()
            elapsed = now - t0
            if args.seconds > 0 and elapsed >= args.seconds:
                break

            block = cap.read_block(timeout=0.2)
            if block is None:
                continue

            feats = an.feed(block)
            frames += 1
            heights = mp.update(feats, dt)

            # ---- 写 MCGS ----
            if not dry and (now - last_write) >= write_interval:
                n = mb.write_all([int(round(v)) for v in heights])
                msg = ("写%d个" % n) if not mb.last_error else ("写失败:" + mb.last_error)
                last_write = now
                writes += 1

            # ---- 存盘 ----
            if log_w:
                log_w.writerow(
                    ["%.3f" % elapsed] +
                    ["%.4f" % x for x in (feats.level, feats.low, feats.mid, feats.high)] +
                    [int(feats.onset), "%.3f" % feats.onset_strength,
                     int(feats.climax), int(feats.silent)] +
                    ["%d" % round(h) for h in heights]
                )

            # ---- 屏幕：单行原地刷新 ----
            if now - last_draw >= 0.10:
                last_draw = now
                flags = ""
                if feats.silent:
                    flags += " 静音"
                if feats.onset:
                    flags += " 节拍%.2f" % feats.onset_strength
                if feats.climax:
                    flags += " 高潮"
                print("\r%6.1fs 音%.2f 低%.2f 中%.2f 高%.2f  %s" % (
                    elapsed, feats.level, feats.low, feats.mid, feats.high, flags),
                    end="", flush=True)

    except KeyboardInterrupt:
        print("\n\n收到 Ctrl+C，正在退出…")
    finally:
        cap.stop()
        if not dry:
            try:
                mb.write_all([0] * 11)  # 退出前归零（11 个通道，少写一个就留残值）
            except Exception:
                pass
            mb.close()
        if log_f:
            log_f.close()

    print("\n运行 %.1f 秒，处理 %d 帧，写 MCGS %d 次（%.1f Hz）。" % (
        time.time() - t0, frames, writes, writes / max(0.001, time.time() - t0)))
    if args.log:
        print("日志：", args.log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
