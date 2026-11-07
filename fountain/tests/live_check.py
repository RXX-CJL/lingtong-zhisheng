# -*- coding: utf-8 -*-
"""live_check.py —— 系统音频采集 + 分析 端到端实跑

流程：
1. 启动 capture（真抓 WASAPI loopback）
2. 同时用另一个线程播放一段"人工合成音乐"（有低频鼓点 + 中频旋律 + 高频镲片）
3. 主线程读帧、喂 analyzer、打印实时特征
4. 播完后继续录 1 秒静音，验证能正确识别静音
5. 输出可核对的统计
"""
import os, sys, time, threading, math
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
import soundcard as sc
from analyzer import AudioAnalyzer
from capture import SystemAudioCapture, CaptureConfig

SR = 48000
BLOCK = 2048
PLAY_S = 6.0        # 播放 6 秒
TAIL_S = 1.2        # 之后留 1.2 秒静音

# ---------- 造一段"音乐" ----------
def make_music(sr=SR, dur=PLAY_S):
    n = int(sr * dur)
    t = np.arange(n) / sr
    out = np.zeros(n, dtype=np.float64)

    # 低频：每 0.5s 一记底鼓（80Hz 衰减包络）
    beat = 0.5
    for k in range(int(dur / beat)):
        s = int(k * beat * sr); ln = int(0.10 * sr)
        if s + ln > n: break
        env = np.exp(-np.linspace(0, 7, ln))
        out[s:s+ln] += 0.55 * env * np.sin(2*np.pi*80*np.arange(ln)/sr)

    # 高频：每 0.25s 一记镲片（6kHz 极短衰减）
    hat = 0.25
    for k in range(int(dur / hat)):
        s = int(k * hat * sr); ln = int(0.03 * sr)
        if s + ln > n: break
        env = np.exp(-np.linspace(0, 9, ln))
        rng = np.random.default_rng(k)
        noise = rng.standard_normal(ln) * 0.35
        out[s:s+ln] += 0.22 * env * (np.sin(2*np.pi*6400*np.arange(ln)/sr) + noise)

    # 中频：一条连续的"旋律"，每 1s 换一个音（C5/E5/G5）
    notes = [523.25, 659.25, 783.99, 659.25, 523.25, 783.99]
    for k in range(int(dur)):
        s = int(k * sr); ln = sr
        if s + ln > n: ln = n - s
        if ln <= 0: break
        f = notes[k % len(notes)]
        seg_t = np.arange(ln) / sr
        env = np.minimum(1.0, np.minimum(seg_t*8, (ln/sr - seg_t)*8))
        out[s:s+ln] += 0.20 * env * np.sin(2*np.pi*f*seg_t)

    # 整体收一下，防止削顶
    peak = np.max(np.abs(out))
    if peak > 0.85:
        out *= 0.85 / peak
    stereo = np.stack([out, out], axis=1).astype(np.float32)
    return stereo


print("=" * 74)
print("端到端实跑：WASAPI Loopback 采集 → 实时分析")
print("=" * 74)

cap = SystemAudioCapture(CaptureConfig(block_size=BLOCK))
cap.start()
# 等采集流真正建起来
for _ in range(100):
    if cap.is_running and cap.sample_rate:
        break
    time.sleep(0.05)
print("采集设备: %s" % cap.device_name)
print("采样率  : %d Hz" % cap.sample_rate)
print("运行状态: %s" % cap.is_running)
if not cap.is_running:
    print("!! 采集没起来: %s" % cap.last_error)
    sys.exit(1)

sr_dev = cap.sample_rate
an = AudioAnalyzer(sr_dev, BLOCK)
music = make_music(sr_dev, PLAY_S)

play_err = {}
def player():
    try:
        spk = sc.default_speaker()
        with spk.player(samplerate=sr_dev, channels=2, blocksize=BLOCK) as p:
            p.play(music)
    except Exception as e:
        play_err["e"] = repr(e)

th = threading.Thread(target=player, daemon=True)
th.start()

# 主循环：边读边分析，打印 12 行快照
t0 = time.monotonic()
snaps = []
last_print = 0.0
frames = 0
onsets = 0
while time.monotonic() - t0 < PLAY_S + TAIL_S:
    blk = cap.read_block(timeout=0.2)
    if blk is None:
        continue
    f = an.feed(blk)
    frames += 1
    if f.onset:
        onsets += 1
    now = time.monotonic() - t0
    if now - last_print >= 0.5:
        last_print = now
        snaps.append((now, f))
        bar = lambda v: "#" * int(round(v * 24))
        print("t=%4.1fs | 音量%-6.2f %-24s| 低%-5.2f%-13s| 中%-5.2f%-13s| 高%-5.2f%-13s| %s%s%s" % (
            now, f.level, bar(f.level),
            f.low, bar(f.low), f.mid, bar(f.mid), f.high, bar(f.high),
            "BEAT " if f.onset else "     ",
            "CLIMAX " if f.climax else "",
            "SILENT" if f.silent else ""))

th.join(timeout=PLAY_S + 2)
cap.stop()

print()
print("=" * 74)
print("结果统计")
print("=" * 74)
print("总分析帧数      : %d" % frames)
print("检出节拍数      : %d（6 秒内每 0.5s 一记底鼓 = 12 记预期）" % onsets)
print("播放异常        : %s" % (play_err.get("e", "无")))

play_snaps = [s for s in snaps if s[0] < PLAY_S]
tail_snaps = [s for s in snaps if s[0] >= PLAY_S]
if play_snaps:
    print()
    print("播放段（%d 个快照）：" % len(play_snaps))
    print("  音量 max=%.3f  low max=%.3f  mid max=%.3f  high max=%.3f" % (
        max(s[1].level for s in play_snaps),
        max(s[1].low for s in play_snaps),
        max(s[1].mid for s in play_snaps),
        max(s[1].high for s in play_snaps)))
    awake = sum(1 for s in play_snaps if not s[1].silent)
    print("  非静音快照: %d/%d" % (awake, len(play_snaps)))
if tail_snaps:
    print()
    print("静音尾段（%d 个快照）：" % len(tail_snaps))
    for t, f in tail_snaps:
        print("  t=%4.1fs silent=%-5s level=%.3f" % (t, f.silent, f.level))

ok = True
if play_snaps:
    if max(s[1].level for s in play_snaps) < 0.25:
        print("!! 播放段音量偏低，可能没真抓到"); ok = False
    if sum(1 for s in play_snaps if not s[1].silent) < len(play_snaps) * 0.5:
        print("!! 播放段被判静音的过多"); ok = False
if tail_snaps:
    if not all(f.silent for _, f in tail_snaps[-1:]):
        print("!! 尾段没有识别为静音（可能是别的程序在出声）")
print()
print("=" * 74)
print("判定: %s" % ("PASS —— 真实系统音频采集+分析链路打通" if ok else "需进一步核查"))
print("=" * 74)
