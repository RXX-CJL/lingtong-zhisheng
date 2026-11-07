# -*- coding: utf-8 -*-
"""
listen.py —— 第二阶段交付物：实时监听电脑正在播放的音乐

用途（不接 MCGS，纯验证）：
  把电脑上任何程序播放的声音抓下来，实时显示：
    音量 / 低频 / 中频 / 高频 / 节拍 / 高潮 / 静音
  用来肉眼确认「有没有抓到声音、低中高在哪跳、节拍准不准」。

用法：
  python listen.py              # 一直跑到 Ctrl+C
  python listen.py --seconds 30 # 跑 30 秒自动退出（方便截图/复现）
  python listen.py --json       # 每行输出一条 JSON（给别的程序读）
  python listen.py --log out.csv# 顺便把每帧特征存 CSV（事后分析用）

为什么是控制台而不是窗口：
  用户原话「做完我在仿真里面看效果就行了，其它的先不着急」。
  这一阶段的目标是把「耳朵」调准，不是做界面。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from analyzer import AudioAnalyzer, AnalyzerConfig
from capture import SystemAudioCapture, CaptureConfig


def bar(v: float, width: int = 20, ch: str = "#") -> str:
    n = int(round(max(0.0, min(1.0, v)) * width))
    return ch * n + "." * (width - n)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=0, help="运行秒数，0=一直跑")
    ap.add_argument("--json", action="store_true", help="输出 JSON 行")
    ap.add_argument("--log", default="", help="把每帧特征写入 CSV")
    ap.add_argument("--block", type=int, default=2048, help="每帧采样数")
    args = ap.parse_args()

    cap = SystemAudioCapture(CaptureConfig(block_size=args.block))
    cap.start()
    for _ in range(120):
        if cap.is_running and cap.sample_rate:
            break
        time.sleep(0.05)

    if not cap.is_running:
        print("!! 采集没起来：%s" % cap.last_error, file=sys.stderr)
        print("   排查：① 是否有默认输出设备 ② 是否有程序占用独占模式", file=sys.stderr)
        cap.stop()
        return 2

    sr = cap.sample_rate
    an = AudioAnalyzer(sr, args.block)
    frame_dt = args.block / sr

    if not args.json:
        print("=" * 78)
        print("破晓·潮汐 —— 系统音频实时监听（WASAPI Loopback）")
        print("=" * 78)
        print("设备  : %s" % cap.device_name)
        print("采样率: %d Hz   帧长: %d 采样 = %.1f ms" % (sr, args.block, frame_dt * 1000))
        print("提示  : 现在去放音乐（网易云 / QQ音乐 / 浏览器 / 游戏都行）")
        if args.seconds:
            print("时长  : %.0f 秒后自动退出" % args.seconds)
        print("-" * 78)
        print("%-8s %-6s %-22s %-22s %-22s %-22s %s" %
              ("时间", "音量", "低频(鼓点)", "中频(人声)", "高频(镲片)", "状态", ""))
        print("-" * 78)

    log_f = None
    if args.log:
        log_f = open(args.log, "w", encoding="utf-8")
        log_f.write("t,rms_db,level,low,mid,high,flux,onset,onset_strength,silent,climax\n")

    t0 = time.monotonic()
    frames = 0
    onsets = 0
    last_onset_t = -1.0
    running = True

    try:
        while running:
            if args.seconds and (time.monotonic() - t0) >= args.seconds:
                break
            blk = cap.read_block(timeout=0.2)
            if blk is None:
                if not cap.is_running:
                    print("\n!! 采集中断：%s" % cap.last_error, file=sys.stderr)
                    break
                continue

            f = an.feed(blk)
            frames += 1
            now = time.monotonic() - t0

            if f.onset:
                onsets += 1
                last_onset_t = now

            if log_f:
                log_f.write("%.3f,%.2f,%.4f,%.4f,%.4f,%.4f,%.5f,%d,%.3f,%d,%d\n" %
                            (now, f.rms_db, f.level, f.low, f.mid, f.high,
                             f.flux, int(f.onset), f.onset_strength,
                             int(f.silent), int(f.climax)))

            if args.json:
                d = f.as_dict()
                d["t"] = round(now, 3)
                d["device"] = cap.device_name
                d["sample_rate"] = sr
                print(json.dumps(d, ensure_ascii=False), flush=True)
                continue

            # 控制台：每 100ms 刷一行
            if int(now * 10) == int((now - frame_dt) * 10):
                continue
            status = []
            if f.silent:
                status.append("静音")
            if f.climax:
                status.append("高潮")
            if (now - last_onset_t) < 0.12:
                status.append("节拍")
            print("\r%-8s %-6.2f %-22s %-22s %-22s %-22s %s" % (
                "%.1fs" % now, f.level,
                bar(f.low), bar(f.mid), bar(f.high),
                bar(f.level, 12, "="),
                " ".join(status)),
                end="", flush=True)
    except KeyboardInterrupt:
        running = False
    finally:
        if log_f:
            log_f.close()
        cap.stop()

    if not args.json:
        dur = time.monotonic() - t0
        print("\n" + "-" * 78)
        print("运行 %.1f 秒，分析 %d 帧（%.1f 帧/秒），检出节拍 %d 个（约 %.1f 次/秒）" % (
            dur, frames, frames / max(dur, 1e-9), onsets, onsets / max(dur, 1e-9)))
        print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
