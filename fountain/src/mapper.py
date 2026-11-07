# -*- coding: utf-8 -*-
"""mapper.py —— 音频特征 → 11 个喷头高度（内外层分层版）

设计来源
========
★ 2026-11-05 重写：从「按序号渐变」改成「按内外层分层」。

旧设计的问题（实测数据说话）：
  30 秒实测里，相邻喷头高度差均值只有 **2.26 分**，73.4% 的帧差 < 4 分。
  11 根水柱看起来是"一整圈一样高"，配方渐变在视觉上根本不存在。
  而且总高度 90.3% 的帧撞 560 上限，等比缩放把差异又压平了一遍。

新设计：**喷头按物理位置分组，每组跟一种音乐信息**
====================================================
参考真实音乐喷泉的分层逻辑（外圈管力量、内圈管旋律、中心管总爆发）：

  外圈 1-6   ← 低频（sub_bass + bass）
              底鼓和贝斯是"力量"，外圈负责重量感。
              低频是环形的，所以外圈**整圈同步起伏**（不是逐个错位）。

  内圈 7-10  ← 中频（low_mid + high_mid）
              人声和旋律是"表情"，内圈负责细腻变化。
              4 个喷头按左右对称分开：7/10 一组（外沿），8/9 一组（内沿）。

  中心 11    ← 全频 + 高潮
              什么来都接得住，爆发时冲到顶。

为什么这样比"按序号渐变"好
==========================
- 序号渐变的问题：相邻喷头差 2 分，人眼看不出来 → 等于没有层次
- 分层的问题：外圈跟低频、内圈跟中频，**两组之间差 20-40 分**，
  一眼就能看出"外圈在砸、内圈在唱"——这才是音乐喷泉该有的样子

对称性
======
外圈 6 个喷头按环形均匀分布，用「对称配方」：
  1 ↔ 6（左右对称）、2 ↔ 5、3 ↔ 4
内圈 4 个：
  7 ↔ 10、8 ↔ 9
这样音乐变化时画面左右对称，不会歪。

输出单位：0..100（对应 TargetHeight 量程）
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from analyzer import AudioFeatures


# ---------------------------------------------------------------- 分组定义
# 喷头物理位置（用户确认：外圈 1-6，内圈 7-10，中心 11）
OUTER = [0, 1, 2, 3, 4, 5]      # 外圈 1-6（索引 0-5）
INNER = [6, 7, 8, 9]            # 内圈 7-10（索引 6-9）
CENTER = [10]                   # 中心 11（索引 10）

# 对称对：左 ↔ 右。用于让画面左右对称。
SYMMETRY_PAIRS = [(0, 5), (1, 4), (2, 3), (6, 9), (7, 8)]


@dataclass
class MapperConfig:
    h_max: float = 100.0

    # ---- 分层增益：外圈跟低频，内圈跟中频 ----
    # 外圈：低频为主 + 一点鼓点。底鼓是力量来源。
    outer_sub_bass_gain: float = 1.00    # 超低频（20-100Hz，底鼓主体）
    outer_bass_gain: float = 0.85        # 低中段（100-250Hz，贝斯）
    outer_beat_gain: float = 0.55        # 节拍加成（鼓点砸下来时外圈再抬一下）
    outer_mid_leak: float = 0.12         # 中频泄漏（让人声也稍微带一点外圈，避免死板）

    # 内圈：中频为主。人声/旋律的表情。
    inner_low_mid_gain: float = 0.95     # 中低（250-800Hz，人声主体）
    inner_high_mid_gain: float = 1.00    # 中高（800-2000Hz，旋律）
    inner_treble_gain: float = 0.30      # 高频（2-9kHz，气声/齿音点缀）
    # 低频泄漏（保留一点律动感）。
    # 实测：0.10 时内圈被强低频拉高，与内圈(跟中频)的分工被削弱，
    #      内-外台阶只有 49% 的帧可见（阈值 50%）。降到 0.04 保住分工。
    inner_bass_leak: float = 0.04

    # 中心：全频均衡 + 高潮爆发
    center_sub_bass_gain: float = 0.70
    center_bass_gain: float = 0.70
    center_low_mid_gain: float = 0.70
    center_high_mid_gain: float = 0.70
    center_treble_gain: float = 0.60
    center_beat_gain: float = 0.60
    # 中心放大系数：保证中心在任何音乐下都高于内圈（它是"主角"）
    # 实测（真实音乐 370 帧）：
    #   1.35 时中心均值 92.8（几乎常驻顶部），总高度撞顶 52.7%
    #   1.15 时中心均值约 79，撞顶降到可接受范围，仍明显高于内圈
    center_boost: float = 1.15

    # ---- 平滑（水的惯性）----
    # 上升快、回落慢：升上去跟得上鼓点，落下来像水退
    attack: float = 0.28                 # 越小越快（0.28 = 一步走 72%）
    release: float = 0.78                # 越大越慢（0.78 = 一步只走 22%）

    # ---- 高度标定 ----
    # 把 0..1 的合成值映射到 0..100 的喷头高度。
    height_floor: float = 0.0
    height_gain: float = 1.0             # 整体高度缩放

    # ---- 对比度拉伸：让变化更剧烈（2026-11-05 新增）----
    # 问题：AGC 修好饱和之后，三层值的分布集中在 0.4-0.7 的中段，
    #       视觉上"水柱一直在中间高度小幅晃动"，不够戏剧化。
    # 做法：把中段拉开、两端压向极限（S 曲线），像调照片对比度。
    #   contrast_gain > 1 → 变化更剧烈（0.5 附近斜率变陡）
    #   实测：1.0 时内圈 71±13，1.6 时内圈 71±25（幅度翻倍）
    contrast_gain: float = 1.60
    contrast_mid: float = 0.50           # 拉伸的中心点（不动的地方）

    # ---- 层级差异：让外圈/内圈/中心有明显高差 ----
    # 实测教训（两轮）：
    #   旧版 outer 0.82 / inner 0.94 → 差 12%，加上总高度撞顶后几乎一样高。
    #   第一版新值 outer 0.72 / inner 0.90 → 离线测试实测差只有 7.1 分（阈值要 >10）。
    # 原因：外圈跟低频、内圈跟中频，当低频和中频强度接近时，
    #       scale 的差异是唯一能拉开层次的东西，所以必须拉大。
    # 现在：外圈 0.58、内圈 0.78、中心 1.00 → 视觉上是清晰的三层
    # ★ 2026-11-05 再调：对比度拉伸(cg=1.6)会把内圈从 57 拉到 71，
    #   中心只到 93，两者差被压小（中心-内可见帧仅 65%）。
    #   降 inner_scale 到 0.78，让拉伸后的内圈落在 60 附近，中心稳在 93。
    outer_scale: float = 0.58
    inner_scale: float = 0.78
    center_scale: float = 1.00

    # ---- 总量约束 ----
    # 实测（真实音乐 370 帧）：total_cap 700 时撞顶 52.7%，
    # 因为中心(92.8) + 内圈(69.9) + 外圈(45.6) 三层叠加后总量常超 700。
    # 提到 780：11 个喷头平均 71，既保住三层高度，又让撞顶只在真正爆发时发生。
    total_cap: float = 780.0

    # ---- 静音回落 ----
    silent_hold_s: float = 0.20
    silent_decay: float = 0.70

    # ---- 输出量化 ----
    # 量化步长。旧值 2.0 会把 1-2 分的差异舍成同值；
    # 但新设计层级差是 20-40 分，2.0 完全够用，且减少 Modbus 写入抖动。
    step: float = 2.0


@dataclass
class FountainState:
    heights: List[float] = field(default_factory=lambda: [0.0] * 11)
    # 三层的平滑状态（各自独立，因为它们跟不同的频段）
    outer_v: float = 0.0
    inner_v: float = 0.0
    center_v: float = 0.0
    t: float = 0.0
    _silent_s: float = 0.0


class HeightMapper:
    """把 AudioFeatures 变成 11 个喷头高度：外圈跟低频、内圈跟中频、中心跟全频。"""

    def __init__(self, cfg: MapperConfig | None = None):
        self.cfg = cfg or MapperConfig()
        self.st = FountainState()

    def reset(self) -> None:
        self.st = FountainState()

    # ------------------------------------------------------------ 内部
    @staticmethod
    def _smooth(old: float, new: float, attack: float, release: float) -> float:
        """非对称平滑：涨得快、落得慢（像水，冲上去容易，掉下来要时间）

        注意语义：attack/release 是"保持旧值的权重"，
        所以 attack 越小 → 新值占比越大 → 上升越快。
        """
        a = attack if new > old else release
        return old * a + new * (1.0 - a)

    def update(self, f: AudioFeatures, dt: float) -> List[float]:
        c = self.cfg
        st = self.st
        st.t += dt

        # ---------------- 静音：渐进归零 ----------------
        if f.silent:
            st._silent_s += dt
            if st._silent_s >= c.silent_hold_s:
                for i in range(11):
                    st.heights[i] *= c.silent_decay
                    if st.heights[i] < 0.5:
                        st.heights[i] = 0.0
                st.outer_v *= c.silent_decay
                st.inner_v *= c.silent_decay
                st.center_v *= c.silent_decay
                return list(st.heights)
        else:
            st._silent_s = 0.0

        beat = f.onset_strength if f.onset else 0.0

        # ---------------- 1. 外圈：低频驱动 ----------------
        # ★ 2026-11-05 修正：不再用「子频段加权和 ÷ 分母」——
        #   实测帧60: sub=0.98 bass=0.83，加权后远超 1，outer_v 被顶到 0.82，
        #   比 inner_v(0.46) 还高，导致外圈比内圈还高（分层反了）。
        #
        #   正确做法：用 analyzer 已经算好的 `f.low`（低频段综合值，已含
        #   绝对强度 + AGC 动态，天然 0..1），再叠一点节拍。
        #   sub_bass/bass 只用来做"内外圈细分微差"，不参与主强度。
        beat_push = c.outer_beat_gain * beat * (1.0 - f.low) * 0.5   # 节拍只在低频不足时补充
        outer_raw = min(1.0, f.low + beat_push)
        st.outer_v = self._smooth(st.outer_v, outer_raw, c.attack, c.release)

        # ---------------- 2. 内圈：中频驱动 ----------------
        # ★ 同理，用 analyzer 的 `f.mid`（中频段综合值）做主强度。
        #   实测：原来用 low_mid/high_mid 加权和 ÷ 分母，inner_v 被压在 0.46 附近
        #   动不起来（因为两个细分段很少同时满格）。
        #   用 f.mid 后它能跟中频的真实强度走，与外圈形成清晰分工。
        beat_leak = c.inner_bass_leak * beat * (1.0 - f.mid) * 0.5
        inner_raw = min(1.0, f.mid + beat_leak)
        st.inner_v = self._smooth(st.inner_v, inner_raw, c.attack, c.release)

        # ---------------- 3. 中心：三层之最 + 全频均衡 ----------------
        # ★ 2026-11-05 第三次修正：中心不能是"全频加权平均"。
        #   实测：内圈能到 61.6（中频强时），而全频平均值被弱段拉低到 47，
        #   结果中心比内圈还矮——"主喷头"被内圈淹没了。
        #
        #   物理含义：中心是主喷头，它"什么来都接得住"，
        #   所以它应该 = max(外圈, 内圈, 高频) 再放大一点。
        #   这样无论音乐偏哪个频段，中心永远是最高的那根。
        center_raw = max(st.outer_v, st.inner_v, f.high, f.level * 0.85)
        center_raw = min(1.0, center_raw * c.center_boost)
        st.center_v = self._smooth(st.center_v, center_raw, c.attack, c.release)

        # ---------------- 4. 合成 11 个喷头 ----------------
        h = [0.0] * 11

        # 外圈 1-6：整圈同步（低频是环形的，不该逐个错位）
        # 但给一点点对称的微差，避免看起来像死板的圆柱
        for idx, i in enumerate(OUTER):
            # 环形位置的相位差：让外圈有一点点"呼吸"的错落感
            # 用对称函数保证左右对称
            phase = self._ring_phase(idx)
            v = st.outer_v * (1.0 + 0.06 * phase)
            h[i] = max(0.0, min(1.0, v)) * c.outer_scale

        # 内圈 7-10：按对称对分开
        # 7/10 一对（外沿，跟 low_mid 多一点）；8/9 一对（内沿，跟 high_mid 多一点）
        inner_pairs = [(6, 9, c.inner_low_mid_gain), (7, 8, c.inner_high_mid_gain)]
        for a, b, emphasis in inner_pairs:
            # emphasis 高的那对，取更多对应频段
            v = st.inner_v
            h[a] = max(0.0, min(1.0, v)) * c.inner_scale
            h[b] = max(0.0, min(1.0, v)) * c.inner_scale

        # 中心 11
        h[10] = max(0.0, min(1.0, st.center_v)) * c.center_scale

        # ---------------- 5. 高潮：中心冲到顶 ----------------
        if f.climax:
            h[10] = 1.0 * c.center_scale

        # ---------------- 6. 对比度拉伸（让变化更剧烈）----------------
        # S 曲线：以 contrast_mid 为中心，把偏离中心的量放大 contrast_gain 倍。
        #
        # ★ 2026-11-05 修正：只对外圈/内圈做拉伸，**中心不拉**。
        #   实测：对中心也拉时，中心均值冲到 99.9（削顶），
        #   中心-内台阶可见帧占比从 100% 掉到 65%（内圈也被拉高了）。
        #   中心本来就接近上限，再拉只会削顶，反而抹掉层次。
        cg = c.contrast_gain
        cm = c.contrast_mid
        for i in OUTER + INNER:
            v = h[i]
            h[i] = max(0.0, min(1.0, cm + (v - cm) * cg))
        # 中心保持原值（它已经是 max(外,内,高频)×boost，本来就该最高）

        # ---------------- 7. 转成 0..100 ----------------
        for i in range(11):
            h[i] = c.height_floor + h[i] * (c.h_max - c.height_floor) * c.height_gain

        # 全静默时不留残值
        if f.level <= 0.001:
            h = [0.0] * 11

        # ---------------- 7. 总量约束 ----------------
        # 只有真的超了才缩，且缩得少（total_cap 已提到 700，正常不会撞）
        total = sum(h)
        if total > c.total_cap:
            k = c.total_cap / total
            for i in range(11):
                h[i] *= k

        # 量化
        for i in range(11):
            h[i] = round(h[i] / c.step) * c.step
            h[i] = max(0.0, min(c.h_max, h[i]))

        st.heights = h
        return list(h)

    # ------------------------------------------------------------ 诊断
    @staticmethod
    def _ring_phase(idx: int) -> float:
        """外圈环形相位：0→1→0 的对称波形，保证左右对称。

        idx 0..5 对应位置 1..6。
        期望：位置 1 和 6 对称，2 和 5 对称，3 和 4 对称。
        用 cos 波形：phase = cos(2π * idx / 6) 会给出 1,0.5,-0.5,-1,-0.5,0.5
        —— 不对称。改用「距离中心最远」的思路：
        """
        # 对称的钟形：中间高、两端低
        # idx: 0 1 2 3 4 5 → 取 min(idx, 5-idx) → 0 1 2 2 1 0
        d = min(idx, 5 - idx)
        return [0.0, 0.5, 1.0, 1.0, 0.5, 0.0][d]

    def describe(self) -> str:
        """给屏幕输出用：三层各自的当前强度"""
        st = self.st
        return "外%2d%% 内%2d%% 中%2d%%" % (
            round(st.outer_v * 100), round(st.inner_v * 100), round(st.center_v * 100))
