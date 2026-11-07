# -*- coding: utf-8 -*-
"""analyzer.py —— 音频特征分析内核（纯算法，不碰音频设备，可离线重复测试）

职责：吃进一帧 PCM（float32，-1..1），吐出这一帧的音乐特征。
不做任何设备操作，不做任何界面，便于用合成信号做确定性验证。

输出的特征（映射算法直接用这些）：
  rms_db      : 当前 RMS 响度（dBFS，-120 表示数字静音）
  level       : 平滑后的响度，0..1，带攻击/释放不对称（水柱不要跟着采样点抖）
  low / mid / high : 三个频段的能量，0..1，已平滑（**各自独立 AGC，互不压制**）
  flux        : 频谱通量（这一帧比上一帧"多出来"的能量）
  onset       : 本帧是否判定为节拍起点（bool）
  onset_strength : 这次节拍的强度 0..1（用于决定喷头抬多高）
  silent      : 是否处于静音状态（bool）
  climax      : 是否处于高潮（长时能量显著高于中长期基准）

设计上的几个关键取舍（都写在这里，防止后面自己忘了为什么）：

1) 攻击快、释放慢：水柱升上去要跟得上鼓点，落下来要缓。
   所以 level/low/mid/high 都用一阶低通，但上升系数大于下降系数。

2) 节拍用 median + MAD 做自适应阈值，不用 mean + std。
   音乐能量分布是长尾的，mean/std 会被大鼓点带偏，MAD 对离群点不敏感。

3) 静音判定必须带保持时间（hold），否则音乐里的换气停顿会误判成"没声音"。

4) 所有参数集中在 AnalyzerConfig，方便按音乐类型调，不用改代码。

★ 2026-11-05 重大修正：频段归一化从「相对主导频段」改成「每段独立 AGC」
   ------------------------------------------------------------------
   实测数据（蓝牙耳机放歌 30 秒 / 176 帧）暴露的问题：
     low  均值 0.996，97.2% 的帧 = 1.000   ← 完全饱和，低音轻重分不出来
     mid  均值 0.807，std 仅 0.0495        ← 动态范围被压扁
     high 均值 0.476，std 0.0866           ← 唯一还有变化的段

   根因：旧算法 `band_rel_range_db = 45` 是「以当前最响的频段为 0 dB 基准」。
   当低频一直是主导（流行/电子乐几乎必然），低频恒等于 1.0，
   中频按「落后多少 dB」算，也被拉到 0.8 附近 —— 三个段全被钉死。

   正确做法（参考 Dan Ellis 的 tf_agc 时频自动增益控制）：
   **每个频段各自维护一条能量包络，各自除以自己的包络**。
   这样"低频今天整体很响"不会压掉"低频这一刻比刚才更响"这个信息。

   实现：每段一条「慢速包络」（追踪该段的常态能量），
   输出 = 当前能量 / 包络，再按 dB 压缩到 0..1。
   包络用两档时间常数（快 0.5s / 慢 8s）混合，既能跟上换歌，又不会被单帧带偏。
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass, field

import numpy as np


# --------------------------------------------------------------------------
# 参数
# --------------------------------------------------------------------------
@dataclass
class AnalyzerConfig:
    # ---- 频段划分（Hz）----
    # 更贴近人耳与音乐的听觉分区，而不是平均切：
    #   低频 20-250    ：底鼓、贝斯、重低音——外圈的驱动力
    #   中低 250-800   ：主歌人声、吉他中段——内圈的"身体"
    #   中高 800-2500  ：旋律高段、钢琴——内圈的"表情"
    #   高频 2500-9000 ：镲片、气声、齿音——点缀
    # 主分析仍用三段（low/mid/high），细分段只用于"外圈 vs 内圈"的层次分配。
    low_band: tuple = (20.0, 250.0)      # 鼓点、重低音
    mid_band: tuple = (250.0, 2000.0)    # 人声、主旋律
    high_band: tuple = (2000.0, 9000.0)  # 镲片、清脆打击乐

    # ---- 响度归一化（dBFS 映射到 0..1）----
    db_floor: float = -60.0              # 低于这个算 0
    db_ceil: float = -6.0                # 高于这个算 1

    # ---- 频段归一化：绝对强度 × AGC 动态（2026-11-05 两轮迭代的最终版）----
    # ① 绝对强度：这段比全场最响的段低多少 dB → 决定"该不该有高度"
    #    实测教训：纯低频信号下，若只看 AGC，low_mid 也会拿到 0.22（因为它稳定）。
    #    加上绝对强度后，low_mid 落后低频 30+ dB → 接近 0 → 内圈不动。
    band_rel_range_db: float = 40.0   # 比全场峰值低这么多 dB 就算没能量
                                      # （旧值 45 太宽，安静段也拿到分；40 更锐利）
    # ② AGC 动态：这段比自己的常态高多少 dB → 决定"这一刻有多激动"
    #    这是防饱和的关键：低频今天整体很响，不压掉"这一刻比刚才更响"的信息。
    agc_env_fast_s: float = 0.60         # 快速包络（跟得上段落变化）
    agc_env_slow_s: float = 6.0          # 慢速包络（记住整首歌的量级）
    agc_env_mix: float = 0.35            # 快速包络占的比重（其余给慢速）
    agc_env_floor_db: float = -75.0      # 包络的绝对下限（别除以接近 0 的数）
    agc_range_up_db: float = 10.0        # 高于包络 10 dB → 动态项 1.0
    agc_range_down_db: float = 16.0      # 低于包络 16 dB → 动态项 0.0
                                         # ★ 灵敏度主要看这两个值：范围小=灵敏，大=迟钝
    # 绝对门限：整段能量低于此值时直接归零（防止静音时 AGC 把噪声放大）
    band_abs_floor_db: float = -80.0
    band_gate_db: float = -62.0          # 整段低于此 → 按比例压到 0

    # ---- 平滑系数（0..1，越大越跟手；alpha 是"保持旧值"的权重）----
    level_attack: float = 0.35
    level_release: float = 0.90
    # 频段平滑：2026-11-05 调快（原 0.40/0.88 太钝，起伏被抹平）
    band_attack: float = 0.30            # 上升更快 → 跟得上鼓点
    band_release: float = 0.82            # 回落稍慢 → 有水的惯性

    # ---- 静音判定 ----
    silence_db: float = -52.0            # 低于此视为静音候选
    silence_hold_s: float = 0.50         # 连续这么久才算真静音
    resume_db: float = -46.0             # 高于此立刻解除静音（滞回，防抖动）

    # ---- 节拍检测 ----
    flux_window_s: float = 1.6           # 自适应阈值的历史窗口长度
    flux_k_mad: float = 3.2              # 阈值 = median + k * MAD
    onset_min_interval_s: float = 0.11   # 两个节拍最小间隔（约 545 BPM 上限）
    onset_min_flux: float = 1e-4         # flux 本身的绝对下限（低于此不考虑）
    onset_thr_floor: float = 0.055       # 自适应阈值的绝对地板（防止 median/MAD 退化）
                                         # 实测：底鼓加权 flux≈0.49，镲片≈0.08。
                                         # 地板 0.055 → 镲片能过（弱节拍），背景噪声过不了
    onset_decay: float = 0.82            # 节拍强度衰减（每帧）
    # 节拍加权的频段切分（Hz）。实测教训：不加权时，0.25s 一记的高频镲片会
    # 单独触发 19/20 次，和底鼓混在一起就变成"节拍数翻倍"，水柱会乱跳。
    # 真实音乐里镲片也是节拍，但喷泉的主节拍应该由鼓点主导 → 低频权重最高。
    onset_bands: tuple = ((20.0, 250.0), (250.0, 2000.0), (2000.0, 9000.0))
    onset_band_weights: tuple = (1.0, 0.45, 0.12)

    # ---- 高潮检测 ----
    climax_short_s: float = 1.5          # 短时能量窗口
    climax_long_s: float = 6.0           # 长时基准窗口
    climax_ratio: float = 1.45           # 短/长 超过这个倍数算高潮
    climax_min_level: float = 0.45       # 同时绝对响度也得够


# --------------------------------------------------------------------------
# 特征包
# --------------------------------------------------------------------------
@dataclass
class AudioFeatures:
    rms_db: float = -120.0
    level: float = 0.0
    low: float = 0.0
    mid: float = 0.0
    high: float = 0.0
    flux: float = 0.0
    onset: bool = False
    onset_strength: float = 0.0
    silent: bool = True
    climax: bool = False
    # ---- 新增：给「内外层分层」用的细分段（2026-11-05）----
    # 低频拆两档，让外圈有"内低/外低"的层次；中频同理给内圈。
    sub_bass: float = 0.0      # 20-100Hz  超低频（底鼓主体）→ 最外圈
    bass: float = 0.0          # 100-250Hz 低中段           → 外圈
    low_mid: float = 0.0       # 250-800Hz 中低（人声主体）  → 内圈外沿
    high_mid: float = 0.0      # 800-2000Hz 中高（旋律）     → 内圈
    treble: float = 0.0        # 2000-9000Hz 高频            → 中心/点缀
    # 诊断用（不参与映射，但排错时必须有）
    frames_seen: int = 0
    onsets_total: int = 0
    peak_freq_hz: float = 0.0

    def as_dict(self) -> dict:
        return {
            "rms_db": round(self.rms_db, 2),
            "level": round(self.level, 4),
            "low": round(self.low, 4),
            "mid": round(self.mid, 4),
            "high": round(self.high, 4),
            "sub_bass": round(self.sub_bass, 4),
            "bass": round(self.bass, 4),
            "low_mid": round(self.low_mid, 4),
            "high_mid": round(self.high_mid, 4),
            "treble": round(self.treble, 4),
            "flux": round(self.flux, 5),
            "onset": self.onset,
            "onset_strength": round(self.onset_strength, 3),
            "silent": self.silent,
            "climax": self.climax,
        }


# --------------------------------------------------------------------------
# 分析器
# --------------------------------------------------------------------------
class AudioAnalyzer:
    """有状态的流式分析器。每次 feed() 一帧，返回这一帧的特征。"""

    # 五个细分段（用于内外层分层），按频率从低到高
    SUB_BANDS = (
        ("sub_bass", (20.0, 100.0)),
        ("bass", (100.0, 250.0)),
        ("low_mid", (250.0, 800.0)),
        ("high_mid", (800.0, 2000.0)),
        ("treble", (2000.0, 9000.0)),
    )

    def __init__(self, sample_rate: int, block_size: int, cfg: AnalyzerConfig | None = None):
        self.sr = int(sample_rate)
        self.n = int(block_size)
        self.cfg = cfg or AnalyzerConfig()

        # 频段对应的 FFT bin 下标
        freqs = np.fft.rfftfreq(self.n, d=1.0 / self.sr)
        self._freqs = freqs
        self._low_idx = self._band_slice(self.cfg.low_band)
        self._mid_idx = self._band_slice(self.cfg.mid_band)
        self._high_idx = self._band_slice(self.cfg.high_band)
        # 五个细分段
        self._sub_idx = {name: self._band_slice(band) for name, band in self.SUB_BANDS}

        # 节拍检测用的加权掩码（逐 bin 权重）
        self._onset_mask = np.zeros(len(freqs), dtype=np.float32)
        for (lo, hi), w in zip(self.cfg.onset_bands, self.cfg.onset_band_weights):
            sl = self._band_slice((lo, hi))
            self._onset_mask[sl] = max(self._onset_mask[sl].max(initial=0.0), float(w))

        # 汉宁窗（抑制频谱泄漏，避免低频鼓点污染邻段）
        self._window = np.hanning(self.n).astype(np.float32)

        # 平滑状态
        self._level = 0.0
        self._low = 0.0
        self._mid = 0.0
        self._high = 0.0
        self._onset_strength = 0.0
        self._subs = {name: 0.0 for name, _ in self.SUB_BANDS}

        # ★ 每段独立的 AGC 包络（快/慢两档，单位 dB）
        # 关键：这是「各段自己的常态」，不是全局峰值。
        self._env_fast = {}
        self._env_slow = {}
        for name in ("low", "mid", "high") + tuple(n for n, _ in self.SUB_BANDS):
            self._env_fast[name] = None   # None = 还没初始化
            self._env_slow[name] = None

        # 频谱通量历史（环形，用于自适应阈值）
        win = max(8, int(self.cfg.flux_window_s * self.sr / self.n))
        self._flux_hist = collections.deque(maxlen=win)
        self._prev_mag = None

        # 节拍计时
        self._last_onset_t = -1e9
        self._t = 0.0            # 累计时间（秒）
        self._frame_dt = self.n / self.sr

        # 静音计时
        self._quiet_time = 0.0
        self._silent = True

        # 高潮能量历史
        short_win = max(4, int(self.cfg.climax_short_s / self._frame_dt))
        long_win = max(short_win + 4, int(self.cfg.climax_long_s / self._frame_dt))
        self._energy_short = collections.deque(maxlen=short_win)
        self._energy_long = collections.deque(maxlen=long_win)

        # 诊断计数
        self._frames = 0
        self._onsets = 0

    # ---- 内部工具 ----------------------------------------------------
    def _band_slice(self, band):
        lo = max(1, int(np.searchsorted(self._freqs, band[0], side="left")))
        hi = int(np.searchsorted(self._freqs, band[1], side="right"))
        hi = max(hi, lo + 1)
        hi = min(hi, len(self._freqs))
        return slice(lo, hi)

    @staticmethod
    def _smooth(prev: float, cur: float, attack: float, release: float) -> float:
        """上升用 attack、下降用 release 的一阶低通。"""
        a = attack if cur > prev else release
        # a 是"保持旧值"的权重
        return prev * a + cur * (1.0 - a)

    def _db_to_unit(self, db: float, floor_db: float, ceil_db: float) -> float:
        if db <= floor_db:
            return 0.0
        if db >= ceil_db:
            return 1.0
        return (db - floor_db) / (ceil_db - floor_db)

    def _env_update(self, name: str, db: float) -> float:
        """更新某一段的能量包络，返回包络值（dB）。"""
        cfg = self.cfg
        db = max(db, cfg.agc_env_floor_db)

        # 包络初始化：第一帧直接用当前值（避免起步时输出被拉满）
        if self._env_fast[name] is None:
            self._env_fast[name] = db
            self._env_slow[name] = db
        else:
            a_f = math.exp(-self._frame_dt / max(1e-3, cfg.agc_env_fast_s))
            a_s = math.exp(-self._frame_dt / max(1e-3, cfg.agc_env_slow_s))
            self._env_fast[name] = a_f * self._env_fast[name] + (1.0 - a_f) * db
            self._env_slow[name] = a_s * self._env_slow[name] + (1.0 - a_s) * db

        return cfg.agc_env_mix * self._env_fast[name] + (1.0 - cfg.agc_env_mix) * self._env_slow[name]

    def _band_unit(self, name: str, db: float) -> float:
        """★ 2026-11-05 第二版：绝对强度 × AGC 动态，两者相乘。

        第一版只用了「每段独立 AGC」，结果踩了个大坑（离线测试抓出来的）：

          纯低频信号（60Hz 底鼓 + 120Hz 贝斯）下，实测各段输出：
            sub_bass 0.201 / bass 0.200 / low_mid 0.220 / high_mid 0.205
          → 低频段和中频段几乎一样高！内圈被低频一起抬起来了。

          原因：每段除以"自己的包络"，那么任何**稳定存在**的成分都会得到 ~0.5。
          纯低频信号里，low_mid 段虽然绝对能量很低，但它一直稳定，
          相对自己的包络就是"常态"，于是也拿到 0.22。

        正确做法（两条信息缺一不可）：
          ① **绝对强度**：这段比全场最响的段低多少 dB —— 决定"该不该有高度"
             （纯低频时 low_mid 落后很多 → 接近 0 → 内圈不动）
          ② **AGC 动态**：这段比自己的常态高多少 dB —— 决定"这一刻有多激动"
             （低频段有鼓点时值高、安静时值低 → 有起伏，不饱和）

          最终值 = 绝对强度 × AGC动态，两个维度都保留。
        """
        cfg = self.cfg
        env = self._env_update(name, db)

        # ---- ① 绝对强度：相对全场峰值 ----
        if not hasattr(self, "_cur_peak_db") or self._cur_peak_db is None:
            self._cur_peak_db = db
        peak = max(self._cur_peak_db, cfg.agc_env_floor_db)
        span = max(1e-6, cfg.band_rel_range_db)
        strength = max(0.0, 1.0 + (db - peak) / span)

        # ---- ② AGC 动态：相对自己的包络 ----
        rel_db = db - env
        up = max(1e-6, cfg.agc_range_up_db)
        down = max(1e-6, cfg.agc_range_down_db)
        if rel_db >= 0:
            dyn = 0.5 + 0.5 * min(1.0, rel_db / up)
        else:
            dyn = 0.5 * max(0.0, 1.0 - (-rel_db) / down)

        # 绝对门限：整段太安静时按比例压到 0（防止静音时 AGC 把噪声放大）
        gate = self._db_to_unit(db, cfg.band_gate_db, cfg.band_gate_db + 25.0)

        return strength * dyn * gate

    # ---- 主入口 ------------------------------------------------------
    def feed(self, samples: np.ndarray) -> AudioFeatures:
        cfg = self.cfg
        f = AudioFeatures()

        # 归一化成单声道 float32
        x = np.asarray(samples, dtype=np.float32)
        if x.ndim > 1:
            x = x.mean(axis=1)
        if x.size < self.n:
            x = np.pad(x, (0, self.n - x.size))
        elif x.size > self.n:
            x = x[: self.n]

        self._frames += 1
        f.frames_seen = self._frames
        self._t += self._frame_dt

        # ---- 1. 响度 ----
        rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
        rms_db = 20.0 * math.log10(rms) if rms > 1e-12 else -120.0
        f.rms_db = rms_db

        level_raw = self._db_to_unit(rms_db, cfg.db_floor, cfg.db_ceil)
        self._level = self._smooth(self._level, level_raw, cfg.level_attack, cfg.level_release)
        f.level = self._level

        # ---- 2. 频段能量（每段独立 AGC）----
        spec = np.fft.rfft(x * self._window)
        mag = np.abs(spec).astype(np.float32)

        def band_db(sl):
            seg = mag[sl]
            if seg.size == 0:
                return -120.0
            e = float(np.mean(seg.astype(np.float64) ** 2))
            return 10.0 * math.log10(e) if e > 1e-14 else -120.0

        db_low = band_db(self._low_idx)
        db_mid = band_db(self._mid_idx)
        db_high = band_db(self._high_idx)

        # 整段绝对门限：全静音时直接全 0（不做 AGC，否则会把噪声放大）
        db_peak = max(db_low, db_mid, db_high)
        # ★ 把全场峰值记下来，供各段的「绝对强度」判断用
        self._cur_peak_db = db_peak

        if db_peak < cfg.band_abs_floor_db:
            low_u = mid_u = high_u = 0.0
            for name, _ in self.SUB_BANDS:
                self._subs[name] = 0.0
            f.sub_bass = f.bass = f.low_mid = f.high_mid = f.treble = 0.0
        else:
            # ★ 绝对强度 × AGC 动态
            low_u = self._band_unit("low", db_low)
            # ★ mid 段特殊处理：宽段（250-2000Hz）平均会把起伏抵消掉
            #   实测：混合信号下 mid 段 std=0.008（几乎不动），
            #   但它的两个细分段 low_mid std=0.248、high_mid std=0.154 都很活跃。
            #   原因：low_mid 响的时候 high_mid 静，平均后相互抵消。
            #   修法：mid 用两个细分段的最大值，而不是宽段平均。
            db_low_mid = band_db(self._sub_idx["low_mid"])
            db_high_mid = band_db(self._sub_idx["high_mid"])
            mid_u = max(self._band_unit("low_mid", db_low_mid),
                        self._band_unit("high_mid", db_high_mid))
            high_u = self._band_unit("high", db_high)

        self._low = self._smooth(self._low, low_u, cfg.band_attack, cfg.band_release)
        self._mid = self._smooth(self._mid, mid_u, cfg.band_attack, cfg.band_release)
        self._high = self._smooth(self._high, high_u, cfg.band_attack, cfg.band_release)
        f.low, f.mid, f.high = self._low, self._mid, self._high

        # 细分段平滑 + 输出
        for name, _ in self.SUB_BANDS:
            raw = self._band_unit(name, band_db(self._sub_idx[name])) if db_peak >= cfg.band_abs_floor_db else 0.0
            self._subs[name] = self._smooth(self._subs[name], raw, cfg.band_attack, cfg.band_release)
        f.sub_bass = self._subs["sub_bass"]
        f.bass = self._subs["bass"]
        f.low_mid = self._subs["low_mid"]
        f.high_mid = self._subs["high_mid"]
        f.treble = self._subs["treble"]

        # 峰值频率（诊断用）
        if mag.size > 1:
            f.peak_freq_hz = float(self._freqs[int(np.argmax(mag[1:])) + 1])

        # ---- 3. 频谱通量 + 节拍 ----
        if self._prev_mag is None or self._prev_mag.shape != mag.shape:
            flux = 0.0
        else:
            diff = mag - self._prev_mag
            # 加权：只统计"变响"的部分，再按频段权重求和
            flux = float(np.sum(np.maximum(diff, 0.0) * self._onset_mask) / (self.n / 2.0))
        self._prev_mag = mag
        f.flux = flux

        onset = False
        med = 0.0
        if flux > cfg.onset_min_flux:
            # 与历史比，判断是不是"明显高于常态"
            if len(self._flux_hist) >= 8:
                arr = np.fromiter(self._flux_hist, dtype=np.float64)
                med = float(np.median(arr))
                mad = float(np.median(np.abs(arr - med))) + 1e-9
                # 实测踩过的坑：稀疏信号（鼓点之间有静音）时 median≈0、MAD≈0，
                # 阈值退化成 0，任何非零 flux 都被判成节拍（镲片 12/16 全中）。
                # 必须给阈值一个绝对地板，地板取权重已生效后的 flux 尺度。
                thr = max(med + cfg.flux_k_mad * 1.4826 * mad, cfg.onset_thr_floor)
                # 必须是局部峰值，且离上次节拍够远
                is_peak = (len(self._flux_hist) < 2) or (flux >= arr[-1])
                far_enough = (self._t - self._last_onset_t) >= cfg.onset_min_interval_s
                if flux > thr and is_peak and far_enough:
                    onset = True
        self._flux_hist.append(flux)

        if onset:
            self._last_onset_t = self._t
            self._onsets += 1
            # 强度：flux 相对阈值的富余量，压到 0..1
            excess = (flux - med) / (med + 1e-6) if len(self._flux_hist) >= 8 else 1.0
            self._onset_strength = max(self._onset_strength, min(1.0, 0.35 + excess * 0.35))
        else:
            self._onset_strength *= cfg.onset_decay

        f.onset = onset
        f.onset_strength = self._onset_strength
        f.onsets_total = self._onsets

        # ---- 4. 静音（带滞回 + 保持时间）----
        if rms_db < cfg.silence_db:
            self._quiet_time += self._frame_dt
            if self._quiet_time >= cfg.silence_hold_s:
                self._silent = True
        else:
            self._quiet_time = 0.0
            if rms_db > cfg.resume_db:
                self._silent = False
        f.silent = self._silent

        # ---- 5. 高潮 ----
        self._energy_short.append(rms)
        self._energy_long.append(rms)
        if len(self._energy_short) >= 4 and len(self._energy_long) >= 8:
            s = float(np.mean(self._energy_short))
            l = float(np.mean(self._energy_long)) + 1e-9
            if s / l >= cfg.climax_ratio and self._level >= cfg.climax_min_level:
                f.climax = True

        return f

    # ---- 复位（换设备、切歌时用）------------------------------------
    def reset(self):
        self._level = self._low = self._mid = self._high = 0.0
        self._onset_strength = 0.0
        self._flux_hist.clear()
        self._prev_mag = None
        self._quiet_time = 0.0
        self._silent = True
        self._energy_short.clear()
        self._energy_long.clear()
        self._last_onset_t = -1e9
        self._subs = {name: 0.0 for name, _ in self.SUB_BANDS}
        self._cur_peak_db = None
        for name in ("low", "mid", "high") + tuple(n for n, _ in self.SUB_BANDS):
            self._env_fast[name] = None
            self._env_slow[name] = None
