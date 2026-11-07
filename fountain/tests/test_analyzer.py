# -*- coding: utf-8 -*-
"""test_analyzer.py —— 用合成信号验证分析器。

每个用例都有明确预期，不通过就打印 FAIL 并列实测值。
不是"能跑就算过"，而是"输出必须落在预期范围内"。
"""
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
from analyzer import AudioAnalyzer, AnalyzerConfig

SR = 48000
BLOCK = 2048
DT = BLOCK / SR

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  [PASS] " if cond else "  [FAIL] ") + name + ("  " + detail if detail else ""))


def tone(freq, dur, amp=0.3, sr=SR):
    t = np.arange(int(sr * dur)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def run_frames(an, signal, n_frames=None):
    """把一段长信号按 BLOCK 切帧喂进去，返回最后一帧的特征和统计。"""
    total = n_frames if n_frames is not None else len(signal) // BLOCK
    last = None
    feats = []
    for i in range(total):
        seg = signal[i * BLOCK:(i + 1) * BLOCK]
        if len(seg) < BLOCK:
            seg = np.pad(seg, (0, BLOCK - len(seg)))
        last = an.feed(seg)
        feats.append(last)
    return last, feats


print("=" * 70)
print("用例 1：静音 → 必须判定 silent，且 level≈0")
print("=" * 70)
an = AudioAnalyzer(SR, BLOCK)
silence = np.zeros(SR * 2, dtype=np.float32)
f, _ = run_frames(an, silence)
print("  实测: rms_db=%.1f level=%.4f silent=%s" % (f.rms_db, f.level, f.silent))
check("静音判定", f.silent is True)
check("静音 level 近零", f.level < 0.01, "level=%.4f" % f.level)

print()
print("=" * 70)
print("用例 2：100Hz 低音 → low 高，mid/high 低")
print("=" * 70)
an = AudioAnalyzer(SR, BLOCK)
f, _ = run_frames(an, tone(100, 2.0))
print("  实测: low=%.3f mid=%.3f high=%.3f level=%.3f" % (f.low, f.mid, f.high, f.level))
check("低频主宰", f.low > 0.5 and f.low > f.mid * 1.5 and f.low > f.high * 1.5,
      "low=%.3f mid=%.3f high=%.3f" % (f.low, f.mid, f.high))
check("有声音时不静音", f.silent is False)

print()
print("=" * 70)
print("用例 3：1000Hz 中音 → mid 高")
print("=" * 70)
an = AudioAnalyzer(SR, BLOCK)
f, _ = run_frames(an, tone(1000, 2.0))
print("  实测: low=%.3f mid=%.3f high=%.3f" % (f.low, f.mid, f.high))
check("中频主宰", f.mid > 0.5 and f.mid > f.low * 1.5 and f.mid > f.high * 1.5,
      "low=%.3f mid=%.3f high=%.3f" % (f.low, f.mid, f.high))

print()
print("=" * 70)
print("用例 4：5000Hz 高音 → high 高")
print("=" * 70)
an = AudioAnalyzer(SR, BLOCK)
f, _ = run_frames(an, tone(5000, 2.0))
print("  实测: low=%.3f mid=%.3f high=%.3f" % (f.low, f.mid, f.high))
check("高频主宰", f.high > 0.5 and f.high > f.low * 1.5 and f.high > f.mid * 1.5,
      "low=%.3f mid=%.3f high=%.3f" % (f.low, f.mid, f.high))

print()
print("=" * 70)
print("用例 5：节拍检测 —— 0.5 秒一下鼓点，共 10 下，看能不能数出来")
print("=" * 70)
sr = SR
dur = 5.5
sig = np.zeros(int(sr * dur), dtype=np.float32)
beat_times = [0.5 + i * 0.5 for i in range(10)]
for bt in beat_times:
    start = int(bt * sr)
    n = int(0.06 * sr)               # 60ms 鼓点
    env = np.exp(-np.linspace(0, 6, n)).astype(np.float32)
    burst = (0.55 * env * np.sin(2 * np.pi * 80 * np.arange(n) / sr)).astype(np.float32)
    sig[start:start + n] += burst
an = AudioAnalyzer(SR, BLOCK)
_, feats = run_frames(an, sig)
detected = [i for i, x in enumerate(feats) if x.onset]
print("  预设鼓点: %d 个" % len(beat_times))
print("  检出节拍: %d 个" % len(detected))
print("  检出帧号: %s" % detected)
ratio = len(detected) / float(len(beat_times))
check("节拍检出率 >= 70%% 且 <= 130%%", 0.7 <= ratio <= 1.3, "ratio=%.2f" % ratio)

print()
print("=" * 70)
print("用例 6：音量突变 → level 必须平滑，单帧不允许跳满")
print("=" * 70)
an = AudioAnalyzer(SR, BLOCK)
quiet = tone(440, 1.0, amp=0.02)
loud = tone(440, 1.0, amp=0.5)
sig = np.concatenate([quiet, loud])
_, feats = run_frames(an, sig)
levels = [x.level for x in feats]
# 找最大单帧跳变
max_jump = max(abs(levels[i] - levels[i - 1]) for i in range(1, len(levels)))
print("  level 范围: %.3f → %.3f" % (min(levels), max(levels)))
print("  最大单帧跳变: %.4f" % max_jump)
check("单帧跳变 < 0.55（不跟采样点抖）", max_jump < 0.55, "max_jump=%.4f" % max_jump)
check("响的时候 level 确实上去了", max(levels) > 0.45, "max=%.3f" % max(levels))

print()
print("=" * 70)
print("用例 7：由响变静 → level 应当缓慢回落，不是瞬间归零")
print("=" * 70)
an = AudioAnalyzer(SR, BLOCK)
sig = np.concatenate([tone(440, 1.0, amp=0.4), np.zeros(SR, dtype=np.float32)])
_, feats = run_frames(an, sig)
peak_i = max(range(len(feats)), key=lambda i: feats[i].level)
after = feats[peak_i + 1:peak_i + 4]
print("  峰值 level=%.3f，之后 3 帧: %s" % (feats[peak_i].level,
      ["%.3f" % a.level for a in after]))
check("下降是渐进的（不是一帧归零）",
      len(after) >= 3 and after[0].level > 0.2 and after[-1].level < after[0].level,
      "seq=%s" % ["%.3f" % a.level for a in after])

print()
print("=" * 70)
print("用例 8：静音→有声 的恢复是否及时（滞回不能卡住）")
print("=" * 70)
an = AudioAnalyzer(SR, BLOCK)
SILENT_FRAMES = SR // BLOCK          # 前面 1 秒静音 = 这么多帧
sig = np.concatenate([np.zeros(SR, dtype=np.float32), tone(440, 1.0, amp=0.4)])
_, feats = run_frames(an, sig)
first_awake = next((i for i, x in enumerate(feats) if not x.silent), None)
lag = (first_awake - SILENT_FRAMES) if first_awake is not None else None
print("  静音段 %d 帧，第 %s 帧恢复，滞后 %s 帧" % (SILENT_FRAMES, first_awake, lag))
# 断言口径：相对"第一个有声帧"算滞后，不是绝对帧号
# （原来写成 first_awake < 15，把"静音段本身就 23 帧"算成了失败）
check("有声后 2 帧内解除静音", lag is not None and lag <= 2, "lag=%s" % lag)

print()
print("=" * 70)
print("用例 9：高潮识别 —— 长时间小音量 + 突然大音量")
print("=" * 70)
an = AudioAnalyzer(SR, BLOCK)
calm = tone(440, 8.0, amp=0.06)
climax = tone(440, 3.0, amp=0.5)
sig = np.concatenate([calm, climax])
_, feats = run_frames(an, sig)
climax_frames = [i for i, x in enumerate(feats) if x.climax]
print("  总帧数=%d，判定高潮帧数=%d" % (len(feats), len(climax_frames)))
print("  高潮帧号范围: %s" % (str(climax_frames[:3]) + " ... " + str(climax_frames[-3:]) if climax_frames else "无"))
check("检测到高潮", len(climax_frames) > 0, "count=%d" % len(climax_frames))
if climax_frames:
    check("高潮发生在后半段", min(climax_frames) >= len(feats) * 0.6,
          "first=%d total=%d" % (min(climax_frames), len(feats)))

print()
print("=" * 70)
print("汇总：%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
if FAIL:
    print("失败用例：")
    for n in FAIL:
        print("   - " + n)
print("=" * 70)
sys.exit(0 if not FAIL else 1)
