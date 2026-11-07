# -*- coding: utf-8 -*-
"""verify_music.py —— 端到端验证：播放测试音乐 + 实时分析 + 输出 11 个喷头高度

不连 MCGS，纯本地验证「音乐 → 特征 → 高度」这条链。
"""
from __future__ import annotations
import os, sys, time, threading, wave

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from analyzer import AudioAnalyzer, AnalyzerConfig
from capture import CaptureConfig, SystemAudioCapture
from mapper import HeightMapper, MapperConfig

WAV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_music.wav")
DUR = 12.0
LEAD = 1.5          # 播放前先空转，让采集稳定
TAIL = 2.5


def play_async(path: str):
    """用 soundcard 播放（走真实声卡，WASAPI loopback 才能抓到）"""
    import soundcard as sc
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    def run():
        spk = sc.default_speaker()
        with spk.player(samplerate=sr, channels=data.shape[1]) as p:
            # 分块送，避免一次性大 buffer 卡住
            step = sr // 10
            for i in range(0, len(data), step):
                p.play(data[i:i+step])
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def main():
    print("=" * 70)
    print(" 端到端验证：音乐 → 音频特征 → 11 个喷头高度")
    print("=" * 70)

    cap = SystemAudioCapture(CaptureConfig(block_size=2048))
    cap.start()
    time.sleep(1.0)
    if not cap.is_running:
        print("采集启动失败:", cap.last_error)
        return 2
    sr = cap.sample_rate or 48000
    print("采集设备: %s   采样率: %d" % (cap.device_name, sr))

    an = AudioAnalyzer(sr, 2048, AnalyzerConfig())
    global MP
    MP = HeightMapper(MapperConfig())
    mp = MP
    dt = 2048.0 / sr

    # 预热（丢弃前 0.5 秒）
    t_warm = time.time()
    while time.time() - t_warm < 0.5:
        cap.read_block(timeout=0.1)

    print("开始播放测试音乐（%.0f 秒）...\n" % DUR)
    play_async(WAV)

    rows = []
    t0 = time.time()
    while True:
        el = time.time() - t0
        if el >= DUR + TAIL:
            break
        blk = cap.read_block(timeout=0.2)
        if blk is None:
            continue
        f = an.feed(blk)
        h = mp.update(f, dt)
        rows.append((el, f.level, f.low, f.mid, f.high,
                     int(f.onset), f.onset_strength, int(f.climax), int(f.silent), h))

    cap.stop()
    print("\n采集完成，共 %d 帧" % len(rows))

    # ---------- 分析 ----------
    # 只统计"播放窗口"内的帧
    inwin = [r for r in rows if LEAD*0.0 <= r[0] < DUR]
    tail = [r for r in rows if r[0] >= DUR + 0.6]

    lv = np.array([r[1] for r in inwin])
    lo = np.array([r[2] for r in inwin])
    mi = np.array([r[3] for r in inwin])
    hi = np.array([r[4] for r in inwin])
    onsets = sum(r[5] for r in inwin)
    climax = sum(r[7] for r in inwin)
    top = max(sum(1 for v in r[9] if v > 1) for r in inwin)

    print()
    print("--- 频段与响度（播放窗口 %d 帧）---" % len(inwin))
    print("  音量   平均%.3f  峰值%.3f" % (lv.mean(), lv.max()))
    print("  低频   平均%.3f  峰值%.3f" % (lo.mean(), lo.max()))
    print("  中频   平均%.3f  峰值%.3f" % (mi.mean(), mi.max()))
    print("  高频   平均%.3f  峰值%.3f" % (hi.mean(), hi.max()))
    print("  节拍检出 %d 次   高潮 %d 帧   最多同时喷头 %d 个" % (onsets, climax, top))

    print()
    print("--- 喷头高度抽样（每 0.5 秒取一帧）---")
    lastt = -9
    for r in inwin:
        if r[0] - lastt >= 0.5:
            lastt = r[0]
            bars = " ".join("%3d" % round(v) for v in r[9])
            print("  %5.1fs  音量%.2f 低%.2f 中%.2f 高%.2f | %s" %
                  (r[0], r[1], r[2], r[3], r[4], bars))

    print()
    print("--- 静音回落检查（播放结束后）---")
    if tail:
        for r in tail[:3]:
            bars = " ".join("%3d" % round(v) for v in r[9])
            print("  %5.1fs  音量%.2f 静音=%d | %s" % (r[0], r[1], r[8], bars))
        endzero = all(all(v < 1 for v in r[9]) for r in tail[-2:])
        print("  末段是否全部归零:", "是 ✔" if endzero else "否 ✘")
    else:
        endzero = False
        print("  （无尾段数据）")

    # ---------- 判据 ----------
    print()
    print("=" * 70)
    ok = []
    ok.append(("听到声音（音量峰值 > 0.15）", lv.max() > 0.15, "峰%.3f" % lv.max()))
    ok.append(("低频响应（峰值 > 0.5）", lo.max() > 0.5, "峰%.3f" % lo.max()))
    ok.append(("中频响应（峰值 > 0.3）", mi.max() > 0.3, "峰%.3f" % mi.max()))
    ok.append(("检出了节拍（>= 8 次）", onsets >= 8, "%d 次" % onsets))
    ok.append(("高潮被识别", climax >= 1, "%d 帧" % climax))
    ok.append(("外围与内圈有层次差", abs(lo.mean() - mi.mean()) > 0.05,
               "低%.2f vs 中%.2f" % (lo.mean(), mi.mean())))
    # 容差 = 量化步长 × 喷头数：缩放后每个喷头各自舍入到 step 的整数倍，
    # 11 个喷头累计误差最大就是 step*11。这不是逻辑错，是量化的必然。
    maxtot = max(sum(r[9]) for r in inwin)
    tol = MP.cfg.step * 11
    ok.append(("总高度不超上限（水泵约束）", maxtot <= MP.cfg.total_cap + tol,
               "峰值%d / 上限%d（容差%d）" % (maxtot, MP.cfg.total_cap, tol)))
    ok.append(("结束后归零", endzero, ""))

    npass = sum(1 for _, v, _ in ok if v)
    for name, v, extra in ok:
        print("  [%s] %-28s %s" % ("PASS" if v else "FAIL", name, extra))
    print()
    print("  %d/%d 通过" % (npass, len(ok)))
    print("=" * 70)
    return 0 if npass == len(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
