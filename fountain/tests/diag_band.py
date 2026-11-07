# -*- coding: utf-8 -*-
import sys, os, math
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
from analyzer import AudioAnalyzer, AnalyzerConfig

SR, BLOCK = 48000, 2048
t = np.arange(int(SR)); sig = (0.3*np.sin(2*np.pi*100*t/SR)).astype(np.float32)
x = sig[:BLOCK]
win = np.hanning(BLOCK).astype(np.float32)
mag = np.abs(np.fft.rfft(x*win))
freqs = np.fft.rfftfreq(BLOCK, 1.0/SR)

def band_stats(lo, hi):
    li = max(1, int(np.searchsorted(freqs, lo, side="left")))
    hii = int(np.searchsorted(freqs, hi, side="right"))
    seg = mag[li:hii]
    e = float(np.mean(seg.astype(np.float64)**2))
    db = 10*math.log10(e) if e > 1e-14 else -120.0
    peak_i = int(np.argmax(seg))
    return dict(lo=lo, hi=hi, bins=f"{li}:{hii}", n=len(seg), mean_db=round(db,2),
                max_mag=round(float(seg.max()),6), peak_hz=round(float(freqs[li+peak_i]),1))

print("100Hz 正弦，各段统计：")
for name,(a,b) in [("low",(20,250)),("mid",(250,2000)),("high",(2000,8000))]:
    s = band_stats(a,b)
    print("  %-4s bins=%-8s n=%-3d mean_db=%-8s max_mag=%-10s peak=%s Hz" % (
        name, s["bins"], s["n"], s["mean_db"], s["max_mag"], s["peak_hz"]))

print()
print("--- 关键：mid 段每个 bin 的量级（前 12 个） ---")
li = int(np.searchsorted(freqs, 250, side="left"))
for i in range(li, li+12):
    print("   bin %3d  %7.1f Hz  mag=%.3e  db=%7.2f" % (
        i, freqs[i], mag[i], 20*math.log10(mag[i]+1e-30)))

print()
print("--- 归一化后 ---")
cfg = AnalyzerConfig()
for name,(a,b),val in [("low",(20,250),None),("mid",(250,2000),None)]:
    pass
an = AudioAnalyzer(SR, BLOCK)
for _ in range(60):
    f = an.feed(sig[_*BLOCK:(_+1)*BLOCK])
print("  60 帧后: low=%.4f mid=%.4f high=%.4f" % (f.low, f.mid, f.high))

print()
print("--- 旁瓣真因检验：把 100Hz 换成 187.5Hz（bin 8 整数倍） ---")
f2 = 187.5
sig2 = (0.3*np.sin(2*np.pi*f2*t/SR)).astype(np.float32)
an2 = AudioAnalyzer(SR, BLOCK)
for _ in range(60):
    g = an2.feed(sig2[_*BLOCK:(_+1)*BLOCK])
print("  187.5Hz: low=%.4f mid=%.4f" % (g.low, g.mid))

print()
print("--- 检验：mid 段 max_mag 是否来自低频旁瓣还是真噪声 ---")
print(" 低频频谱前 12 bin 的 mag：")
for i in range(1, 13):
    print("   bin %2d %6.1f Hz  mag=%.4e" % (i, freqs[i], mag[i]))
