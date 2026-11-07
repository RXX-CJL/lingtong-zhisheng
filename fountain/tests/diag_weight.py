# -*- coding: utf-8 -*-
"""diag_weight.py —— 验证频段加权到底有没有生效
用"干净信号"（不含宽带噪声）对照：
  A. 纯 80Hz 底鼓（低频主导）
  B. 纯 6400Hz 正弦短促脉冲（高频主导，无噪声）
如果加权生效：A 的 flux 应远大于 B。
"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
from analyzer import AudioAnalyzer, AnalyzerConfig

SR, BLOCK = 48000, 2048

def kick(n=SR*2, sr=SR):
    out = np.zeros(n)
    for k in range(4):
        s=int(k*0.5*sr); ln=int(0.10*sr)
        env=np.exp(-np.linspace(0,7,ln))
        out[s:s+ln] += 0.55*env*np.sin(2*np.pi*80*np.arange(ln)/sr)
    return out.astype(np.float32)

def hat_clean(n=SR*2, sr=SR):
    """纯 6400Hz 正弦脉冲，不加白噪声"""
    out = np.zeros(n)
    for k in range(16):     # 0.125s 一下，共 16 下
        s=int(k*0.125*sr); ln=int(0.03*sr)
        env=np.exp(-np.linspace(0,9,ln))
        out[s:s+ln] += 0.35*env*np.sin(2*np.pi*6400*np.arange(ln)/sr)
    return out.astype(np.float32)

def hat_noisy(n=SR*2, sr=SR):
    """6400Hz + 白噪声（模拟真实镲片的宽带成分）"""
    out = np.zeros(n)
    for k in range(16):
        s=int(k*0.125*sr); ln=int(0.03*sr)
        env=np.exp(-np.linspace(0,9,ln))
        rng=np.random.default_rng(k)
        out[s:s+ln] += 0.35*env*(np.sin(2*np.pi*6400*np.arange(ln)/sr)
                                 + rng.standard_normal(ln)*0.3)
    return out.astype(np.float32)

def run(sig, label):
    an = AudioAnalyzer(SR, BLOCK)
    onsets=0; fluxes=[]; maxflux=0.0
    for i in range(len(sig)//BLOCK):
        f = an.feed(sig[i*BLOCK:(i+1)*BLOCK])
        if f.onset: onsets+=1
        fluxes.append(f.flux); maxflux=max(maxflux,f.flux)
    print("  %-22s 段数=%-3d 检出=%-3d 最大flux=%.6f 中位flux=%.6f" % (
        label, len(fluxes), onsets, maxflux, float(np.median(fluxes))))
    return onsets, maxflux

print("="*78)
print("加权是否生效的对照（干净信号，分析器内 onset_band_weights=(1.0,0.45,0.12)）")
print("="*78)
run(kick(),      "A 纯80Hz底鼓(4记)")
run(hat_clean(), "B 纯6400Hz脉冲(16记,无噪声)")
run(hat_noisy(), "C 6400Hz+白噪声(16记)")

print()
print("--- 检查掩码实际值 ---")
an = AudioAnalyzer(SR, BLOCK)
m = an._onset_mask
freqs = an._freqs
for lo,hi,w in [(20,250,1.0),(250,2000,0.45),(2000,8000,0.12)]:
    idx = np.where((freqs>=lo)&(freqs<hi))[0]
    if len(idx):
        print("  %5d-%5d Hz  mask 值域=[%.2f, %.2f]  bin数=%d" % (
            lo, hi, m[idx].min(), m[idx].max(), len(idx)))
print("  >8000Hz      mask 值域=[%.2f, %.2f]" % (
    m[freqs>=8000].min() if (freqs>=8000).any() else 0,
    m[freqs>=8000].max() if (freqs>=8000).any() else 0))
