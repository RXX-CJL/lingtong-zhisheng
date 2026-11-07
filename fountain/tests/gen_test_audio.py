# -*- coding: utf-8 -*-
"""gen_test_audio.py —— 合成一段测试音频（低频鼓点+中频旋律+高频镲片）"""
import sys, wave, struct, math, os
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np

SR = 48000
DUR = 12.0
n = int(SR * DUR)
t = np.arange(n) / SR
out = np.zeros(n, dtype=np.float64)

# ---- 低频：120 BPM 底鼓（每 0.5s 一次），80Hz 带衰减包络 ----
bpm = 120.0
beat = 60.0 / bpm
for k in range(int(DUR / beat)):
    s = int(k * beat * SR)
    L = int(0.18 * SR)
    if s + L > n: break
    tt = np.arange(L) / SR
    env = np.exp(-tt * 22.0)
    out[s:s+L] += 0.55 * env * np.sin(2*np.pi*80.0*tt)

# ---- 中频：一条 A 小调旋律（440/494/523/587 Hz），每拍一个音 ----
notes = [440.0, 523.25, 493.88, 587.33, 440.0, 493.88, 523.25, 392.00]
for k in range(int(DUR / beat)):
    s = int(k * beat * SR)
    L = int(0.42 * SR)
    if s + L > n: break
    tt = np.arange(L) / SR
    f = notes[k % len(notes)]
    env = np.minimum(1.0, tt/0.02) * np.exp(-tt * 3.0)
    out[s:s+L] += 0.28 * env * (np.sin(2*np.pi*f*tt) + 0.35*np.sin(2*np.pi*f*2*tt))

# ---- 高频：八分音符踩镲，6kHz 短促噪声 ----
rng = np.random.default_rng(7)
hstep = beat / 2.0
for k in range(int(DUR / hstep)):
    s = int(k * hstep * SR)
    L = int(0.05 * SR)
    if s + L > n: break
    tt = np.arange(L) / SR
    env = np.exp(-tt * 90.0)
    # 高通化的噪声
    noise = rng.standard_normal(L)
    noise = np.diff(np.concatenate([[0.0], noise]))
    out[s:s+L] += 0.16 * env * noise

# ---- 高潮段：8~10 秒全部叠加 ----
cst, cen = int(8.0*SR), int(10.0*SR)
seg = out[cst:cen].copy()
tt = np.arange(len(seg)) / SR
out[cst:cen] = seg + 0.30*np.sin(2*np.pi*110*tt) + 0.20*np.sin(2*np.pi*700*tt)

# 归一化 + 淡入淡出
out = out / (np.max(np.abs(out)) + 1e-9) * 0.85
fade = int(0.05*SR)
out[:fade] *= np.linspace(0, 1, fade)
out[-fade:] *= np.linspace(1, 0, fade)

p = r"E:\output\fountain\tests\test_music.wav"
pcm = (out * 32767).astype(np.int16)
with wave.open(p, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())

print("已生成:", p, " 时长 %.1fs  %d 采样点  峰值=%.2f" % (DUR, n, np.max(np.abs(out))))
