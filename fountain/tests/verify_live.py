# -*- coding: utf-8 -*-
"""verify_live.py —— 边播音乐边跑 listen.py 的真实链路验证，输出可核对的统计"""
import os, sys, time, threading, subprocess
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
import soundcard as sc

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
SR = 48000
DUR = 8.0

def make_music(sr=SR, dur=DUR):
    n = int(sr*dur); t = np.arange(n)/sr
    out = np.zeros(n)
    # 低频底鼓 0.5s 一记 -> 16 记
    for k in range(int(dur/0.5)):
        s=int(k*0.5*sr); ln=int(0.10*sr)
        if s+ln>n: break
        out[s:s+ln] += 0.55*np.exp(-np.linspace(0,7,ln))*np.sin(2*np.pi*80*np.arange(ln)/sr)
    # 高频镲片 0.25s 一记 -> 32 记（弱，用来验证"不该主导节拍"）
    for k in range(int(dur/0.25)):
        s=int(k*0.25*sr); ln=int(0.03*sr)
        if s+ln>n: break
        rng=np.random.default_rng(k)
        out[s:s+ln] += 0.12*np.exp(-np.linspace(0,9,ln))*(np.sin(2*np.pi*6400*np.arange(ln)/sr)+rng.standard_normal(ln)*0.3)
    # 中频旋律 1s 一换
    notes=[523.25,659.25,783.99,659.25,523.25,783.99,587.33,698.46]
    for k in range(int(dur)):
        s=int(k*sr); ln=min(sr, n-s)
        if ln<=0: break
        st=np.arange(ln)/sr
        env=np.minimum(1.0, np.minimum(st*8,(ln/sr-st)*8))
        out[s:s+ln] += 0.22*env*np.sin(2*np.pi*notes[k%len(notes)]*st)
    p=np.max(np.abs(out))
    if p>0.85: out*=0.85/p
    return np.stack([out,out],1).astype(np.float32)

csv = os.path.join(HERE, "_live_out.csv")
if os.path.exists(csv): os.remove(csv)

# 先起 listen.py 子进程
proc = subprocess.Popen(
    [sys.executable, os.path.join(SRC, "listen.py"), "--seconds", str(DUR+1.5),
     "--json", "--log", csv],
    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1"))

LEAD = 1.2        # listen.py 比播放早启动这么多秒，统计时间口径必须扣掉
time.sleep(LEAD)  # 等采集流建起来

music = make_music()
err = {}
def play():
    try:
        spk = sc.default_speaker()
        with spk.player(samplerate=SR, channels=2, blocksize=2048) as p:
            p.play(music)
    except Exception as e:
        err["e"] = repr(e)

th = threading.Thread(target=play, daemon=True); th.start()
th.join(timeout=DUR+2)
proc.wait(timeout=DUR+8)

print("="*76)
print("真实播放链路验证（listen.py 子进程 + 系统音频回环）")
print("="*76)
print("播放异常:", err.get("e","无"))
if not os.path.exists(csv):
    print("!! listen.py 没产出 CSV"); print(proc.stderr.read().decode("utf-8","ignore")[:500]); sys.exit(1)

import csv as csvmod
rows = list(csvmod.DictReader(open(csv, encoding="utf-8")))
print("采集帧数:", len(rows))
if not rows:
    sys.exit(1)

def col(k): return np.array([float(r[k]) for r in rows])
t = col("t"); lvl = col("level"); low=col("low"); mid=col("mid"); high=col("high")
ons = col("onset"); sil = col("silent"); cli = col("climax")

# 时间口径：t 是 listen.py 的进程内时间，播放从 LEAD 开始、到 LEAD+DUR 结束
# 原版直接用 t<DUR 会把"还没开始播"也算进播放段，把"已经播完"也算进去。
mask = (t >= LEAD + 0.3) & (t < LEAD + DUR - 0.3)
print()
print("--- 播放段（t=%.1f~%.1fs，%d 帧）---" % (LEAD + 0.3, LEAD + DUR - 0.3, mask.sum()))
print("  音量  : min=%.3f  max=%.3f  均值=%.3f" % (lvl[mask].min(), lvl[mask].max(), lvl[mask].mean()))
print("  低频  : max=%.3f  均值=%.3f" % (low[mask].max(), low[mask].mean()))
print("  中频  : max=%.3f  均值=%.3f" % (mid[mask].max(), mid[mask].mean()))
print("  高频  : max=%.3f  均值=%.3f" % (high[mask].max(), high[mask].mean()))
print("  非静音帧: %d/%d" % (int((1-sil[mask]).sum()), int(mask.sum())))
print("  检出节拍: %d 个（底鼓预期 16，镲片 32）" % int(ons[mask].sum()))
print("  高潮帧  : %d" % int(cli[mask].sum()))

# 尾段：播放结束后至少 1.2 秒（给 level 释放曲线和静音保持窗口留时间）
tail = t >= LEAD + DUR + 1.2
if tail.sum():
    print()
    print("--- 停止播放后（%d 帧）---" % tail.sum())
    last_sil = sil[tail][-3:]
    print("  末尾 3 帧 silent: %s" % last_sil.tolist())
    print("  末尾 level: %s" % [round(float(x),3) for x in lvl[tail][-3:]])

ok = True
checks = []
def ck(name, cond, detail):
    global ok
    checks.append((name, cond, detail))
    if not cond: ok = False

ck("播放段非静音", (1-sil[mask]).sum() > mask.sum()*0.7,
   "非静音 %d/%d" % (int((1-sil[mask]).sum()), int(mask.sum())))
ck("音量确实上去了", lvl[mask].max() > 0.3, "max=%.3f" % lvl[mask].max())
ck("低频有响应", low[mask].max() > 0.3, "max=%.3f" % low[mask].max())
ck("中频有响应", mid[mask].max() > 0.3, "max=%.3f" % mid[mask].max())
ck("节拍数在合理区间(8~40)", 8 <= int(ons[mask].sum()) <= 40, "检出=%d" % int(ons[mask].sum()))
if tail.sum():
    ck("停止后能识别静音", bool(sil[tail][-1]) is True or lvl[tail][-1] < 0.15,
       "末帧 silent=%s level=%.3f" % (sil[tail][-1], lvl[tail][-1]))

print()
print("="*76)
for n,c,d in checks:
    print(("  [PASS] " if c else "  [FAIL] ") + n + "  " + d)
print("="*76)
print("判定:", "PASS —— 真实音乐链路打通" if ok else "FAIL")
sys.exit(0 if ok else 1)
