# -*- coding: utf-8 -*-
"""diag_onset.py —— 诊断：为什么 6 秒检出 25 个节拍（预期底鼓 12 记）

假设：0.25s 一记的高频镲片也被判定成节拍。
验证法：分别只播底鼓、只播镲片，看各自触发多少。
"""
import os, sys, time, threading
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
import soundcard as sc
from analyzer import AudioAnalyzer
from capture import SystemAudioCapture, CaptureConfig

SR, BLOCK = 48000, 2048
DUR = 5.0

def kick_only(sr=SR, dur=DUR):
    n = int(sr*dur); out = np.zeros(n)
    for k in range(int(dur/0.5)):
        s = int(k*0.5*sr); ln = int(0.10*sr)
        if s+ln > n: break
        env = np.exp(-np.linspace(0,7,ln))
        out[s:s+ln] += 0.55*env*np.sin(2*np.pi*80*np.arange(ln)/sr)
    return np.stack([out,out],1).astype(np.float32)

def hat_only(sr=SR, dur=DUR):
    n = int(sr*dur); out = np.zeros(n)
    for k in range(int(dur/0.25)):
        s = int(k*0.25*sr); ln = int(0.03*sr)
        if s+ln > n: break
        env = np.exp(-np.linspace(0,9,ln))
        rng = np.random.default_rng(k)
        noise = rng.standard_normal(ln)*0.35
        out[s:s+ln] += 0.22*env*(np.sin(2*np.pi*6400*np.arange(ln)/sr)+noise)
    return np.stack([out,out],1).astype(np.float32)

cap = SystemAudioCapture(CaptureConfig(block_size=BLOCK))
cap.start()
for _ in range(100):
    if cap.is_running and cap.sample_rate: break
    time.sleep(0.05)
sr_dev = cap.sample_rate

def run(sig, name, expect):
    cap.drain()
    an = AudioAnalyzer(sr_dev, BLOCK)
    err = {}
    def play():
        try:
            spk = sc.default_speaker()
            with spk.player(samplerate=sr_dev, channels=2, blocksize=BLOCK) as p:
                p.play(sig)
        except Exception as e:
            err["e"] = repr(e)
    th = threading.Thread(target=play, daemon=True); th.start()
    t0 = time.monotonic(); onsets = 0; frames = 0
    high_sum = 0.0
    while time.monotonic()-t0 < DUR + 0.4:
        blk = cap.read_block(timeout=0.2)
        if blk is None: continue
        f = an.feed(blk); frames += 1
        if f.onset: onsets += 1
        high_sum += f.high
    th.join(timeout=DUR+1)
    print("  %-10s 预期~%-3d 检出=%-3d 帧数=%-3d 平均high=%.3f  %s" % (
        name, expect, onsets, frames, high_sum/max(frames,1), err.get("e","")))
    return onsets

print("=" * 70)
print("对照实验：分别播不同频段，看谁在触发节拍")
print("=" * 70)
k = run(kick_only(), "只底鼓", 10)
time.sleep(0.4)
h = run(hat_only(),  "只镲片", 20)
time.sleep(0.4)
cap.stop()

print()
print("=" * 70)
print("结论")
print("=" * 70)
print("底鼓+镲片合计检出 %d 个；纯底鼓 %d 个，纯镲片 %d 个" % (k + h, k, h))
if h > 5:
    print("→ 确认：高频镲片正在被误判为节拍。节拍检测必须加权偏向低频瞬态。")
else:
    print("→ 镲片没有明显触发，节拍偏多的原因在别处。")
