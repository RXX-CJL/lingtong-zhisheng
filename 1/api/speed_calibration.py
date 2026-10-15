# -*- coding: utf-8 -*-
"""真实车速测量（视频测速法）—— 像素位移 -> 实际距离

★★★ 2026-10-06 由 DSH 重写几何部分。根因与实测证据见
    `E:\\output\\_speed_calibration_verdict.md`（本轮结论报告）。

四条标定路径（按优先级，A 最推荐）：

  A. camera_geometry ★推荐（换路口只改 4 个数）
     相机参数：离地高度 / 俯角 / 水平视场角 / 偏航角 + 画幅
     -> `make_unprojector()` 解析反投影：每个像素与地面平面求交，
        纵向横向一并正确，不需要人工选点、不会矩阵退化。

  B. ground_homography（人工点选 ≥4 个已知地面坐标的点，解单应矩阵）
     连相机参数都不知道时用；也可以用来**校核** A（两者都填时自动比对）。

  C. lane_width / explicit_ppm / crosswalk（旧路径，保留兼容）
     车道宽 3.75m 国标、人工给定 ppm、斑马线跨度。

  D. assumed_lanes（无任何标定时的粗估）
     -> behavior_engine 的"未标定不判超速"门禁会拦住它（"AI 不作仲裁者"红线）。

⚠ 参数语义（前端界面必须与此一致，否则速度会系统性偏）
    camera_height_m   相机镜头**离路面**的高度（米）。不是离世界原点的高度！
                      例：CARLA 演示机位传感器 z=5.732、路面 z≈0.73 -> 填 5.0
    camera_pitch_deg  俯角，**向下为负**（如 -23.4）
    camera_yaw_deg    偏航角（度；0 = +X 方向，逆时针为正，CARLA 约定）
    fov_deg           **水平**视场角（CARLA `sensor.camera.rgb` 的 fov 即水平）
    frame_width/height 画面像素尺寸（可由视频自动带入）
    ground_points     [{'u','v','x','y'}...]（≥4，B 路径）
    标定参数白名单见 `scene_annotation._ALLOWED_KEYS`（缺一个就会被静默丢弃）

三档可信度输出（写入结果供人工/复核参考）：
  - calibrated  : A / B / C 任一（有可信标定）
  - assumed     : 无标定，按"整幅画面宽 = 典型 3 车道 + 非机动车道 ≈ 14 m"粗估
  - unavailable : 无位移数据 / 目标过远 / 换算值超出物理上限

────────────────────────────────────────────────────────────────────────
★ 被推翻的旧结论（2026-10-06 实测，不要再引用）
────────────────────────────────────────────────────────────────────────
  · 旧注释称"`ground_plane_ppm()` 已被 580 样本证明系统性偏小 0.61 倍"
    -> **不成立**。那 580 个"真值"像素根本不是测量值：它们是
       `E:\\output\\_scripts\\_dual_cam_demo.py:217/231` 里 `Proj.project()`
       自己算出来再写进 CSV 的**模型输出**（用同一份 Proj 重算这 580 行，
       u 方向中位误差 0.51 px；而那 580 行的 cam1_in 只在车已开过相机之后才为 1）。
       把 `ground_plane_ppm()` 与独立推导的正确几何对照：比值 **1.001~1.003**。
  · 旧注释称"`make_unprojector()` 实测反解误差 0.77m，是★推荐路径"
    -> 那时它其实是**坏的**：`fwd` 与 `up` 的 z 分量一起写反（up_z=-cp），
       整套相机基是"倒"的（光轴朝上 23.4°），只有画面最下方 11% 的像素
       能反解成功 —— 这正是注释里"同样 580 个点里 578 个失败"的真因。
       2026-10-06 已修正，并用**真实渲染帧 + YOLO 检测 + CARLA 世界坐标**验证：
       反解误差 0.2~0.7 m，速度误差 -2.5%~+4.4%。
  · 旧默认值 `h=8.0m / pitch=-20°` 被当成"典型路口监控"隐式启用
    -> 对真实机位(h=5.73/pitch=-23.4°)的反解 **RMS 达 94 m**，而 method
       却显示成 `ground_plane`（看起来像已精确标定）。现已改为：
       **没有显式相机参数就不再走几何路径**。
**诚实声明**：视频测速精度约 ±10~20%（受透视、标定误差、跟踪抖动影响），
用于**筛查/预警**是合适的，作为执法证据需配合雷达等设备（本模块输出带
`confidence` 与 `method` 字段，便于复核时说明来源）。
本轮真机位实测（真实渲染帧 + YOLO 框 + CARLA 真值）：反解 0.2~0.7 m、
匀速车速度误差 -2.5%~+4.4% —— 达到"筛查可用"的水平。
"""

import math
import os
from typing import Dict, List, Optional, Tuple

# 中国城市道路标准车道宽（GB 5768.3）
LANE_WIDTH_M = 3.75
# 无标定时，整幅画面横向的典型实际跨度（3 车道 + 非机动车道，粗估值）
ASSUMED_FRAME_WIDTH_M = 14.0


def _ppm_at_y(ppm_ref: float, y_ref: float, y: float, y_horizon: float) -> float:
    """按透视模型求 y 处的 pixels-per-meter

    模型：同一实际长度在画面上的像素跨度与其到地平线的距离成正比。
      ppm(y) / ppm(y_ref) = (y_ref - y_horizon) / (y - y_horizon)
    """
    denom = (y - y_horizon)
    if abs(denom) < 1e-6:
        return ppm_ref
    ratio = (y_ref - y_horizon) / denom
    # 限制外推比例，避免地平线附近发散
    ratio = max(0.25, min(4.0, ratio))
    return ppm_ref * ratio


class SpeedCalibrator:
    """车速标定器

    scene: 场景标注字典（来自 /api/scene），可含：
      pixel_per_meter : float         方式①，参考 y 处的 ppm
      ppm_ref_y       : float         方式①的参考 y（默认画面高度的 0.75）
      lane_width_px   : float         方式②，某条车道的像素宽
      lane_ref_y      : float         方式②对应的 y
      crosswalk_zones : [[[x,y]x4]]   方式③，斑马线四边形（用横向跨度标定）
      crosswalk_width_m : float       斑马线实际宽度（默认 3.0 m，即常见白条长）
      y_horizon_ratio : float         地平线位置占画面高度比例（默认 0.30）
      frame_width / frame_height : int
    """

    def __init__(self, scene: Optional[Dict] = None, frame_width: int = 1280,
                 frame_height: int = 576):
        s = scene or {}
        self.W = int(s.get("frame_width") or frame_width or 1280)
        self.H = int(s.get("frame_height") or frame_height or 576)
        self.y_horizon = float(s.get("y_horizon_ratio", 0.30)) * self.H
        self.method = "unavailable"
        self.ppm_ref = 0.0
        self.y_ref = float(s.get("ppm_ref_y") or (self.H * 0.75))
        self.crosswalk_zones = s.get("crosswalk_zones") or []
        self.crosswalk_width_m = float(s.get("crosswalk_width_m") or 3.0)
        self.note = ""
        # 地面平面标定参数（相机几何）—— 2026-10-04 新增；2026-10-06 修正语义
        # ⚠ 下面三个"典型值"只用于**界面预填**，绝不再隐式启用几何标定：
        #   实测 h=8.0/pitch=-20 对真实机位(h≈5.7/pitch≈-23.4)的反解 RMS 达 94 m。
        #   另注意 camera_height_m 是**离路面**的高度（详见模块 docstring）。
        self.cam_height_m = float(s.get("camera_height_m") or DEFAULT_CAMERA_HEIGHT_M)
        self.cam_pitch_deg = float(s.get("camera_pitch_deg")
                                   if s.get("camera_pitch_deg") is not None
                                   else DEFAULT_CAMERA_PITCH_DEG)
        self.fov_deg = float(s.get("fov_deg") or DEFAULT_FOV_DEG)
        self.cam_yaw_deg = float(s.get("camera_yaw_deg") or 0.0)
        self.cam_world_x = float(s.get("camera_world_x") or 0.0)
        self.cam_world_y = float(s.get("camera_world_y") or 0.0)
        # ★是否**人工显式**给了相机几何（决定能否走 A 主路径）
        # 2026-10-06 由 DSH 收紧两次，两次都是实测踩出来的：
        #   ① 原用 any(...)：只填一项也会被当成"有相机几何"，然后拿另两项的
        #      默认值去算 —— 算出一个看着像已标定、实际 RMS 94m 的比例尺。
        #   ② 改成 all(k in s ...) 后又踩第二个坑：前端清空字段时发的是
        #      `camera_height_m: null`，**键在、值是 None**，于是 all(...) 为真
        #      -> 既构造不出反投影，又因为 `not self._explicit_cam` 为假而
        #      跳过了 explicit_ppm 分支 -> method 停在 unavailable 或旧值。
        #      现场表现：面板填了完整参数却回 explicit_ppm / solvable=0。
        #   现在只认**有非空值**的三项齐全。
        self._explicit_cam = all(s.get(k) is not None for k in
                                 ("camera_height_m", "camera_pitch_deg", "fov_deg"))
        self._ppm_given = bool(s.get("pixel_per_meter"))
        self.unproject = None      # ★A/B 路径：f(u,v) -> (前向米, 右向米)
        self.Hinv = None           # B 路径的单应矩阵
        self.calib_rms_m = None    # B 路径自检残差
        self.warnings = []

        # ① 显式 ppm
        # ★2026-10-06 由 DSH 修正（实测 bug）：原来只要 s 里有 pixel_per_meter
        #   就占用 ppm_ref，而下面的几何路径条件是 `if not self.ppm_ref` ——
        #   于是几何标定**永远被挡住**。
        #   真实触发链路：realtime_detector.py 的 scene_config 默认塞了
        #   `pixel_per_meter: 10`（给违停/旧规则兜底用），这个 10 会随标注合并
        #   一路传进 SpeedCalibrator，结果：
        #     · 相机参数填对了也不走几何，反投影不构造；
        #     · 对外 method == "explicit_ppm" 显示成**"已标定"**，
        #       但 horizon_y / rows / solvable_ratio 全是空 —— 看起来正常、实际全废。
        #   （这是在真浏览器里点出来的：标定来源"已标定(手工 ppm)" + 可解像素比例 0）
        #   现改为：**人工显式给了完整相机参数时，几何优先**；只有没给相机参数，
        #   pixel_per_meter 才是主路径。
        if s.get("pixel_per_meter") and not self._explicit_cam:
            try:
                self.ppm_ref = float(s["pixel_per_meter"])
                self.method = "explicit_ppm"
                self.note = f"人工给定 {self.ppm_ref:.1f} px/m @ y={self.y_ref:.0f}"
            except (TypeError, ValueError):
                pass

        # ② 车道宽标定（优先于 ①，因为不需要测像素）
        # ★2026-10-06 由 DSH 补第三个漏网分支（真浏览器里抓到的）：
        #   与 ① 同一个病根 —— 只要 scene 标注里有历史遗留的 lane_width_px，
        #   它就会**抢在相机几何之前**当上标定依据。实测现场：请求体里明明带了
        #   完整的 camera_height_m/pitch/fov，后端却回 method=lane_width，
        #   horizon_y / rows / solvable_ratio 全空 —— UI 显示"已标定"，实际全废。
        #   注意这个 lane_width_px 不是用户这次填的，是**旧标注**里的残留。
        if not self._explicit_cam and not self.ppm_ref and s.get("lane_width_px"):
            try:
                lw = float(s["lane_width_px"])
                ly = float(s.get("lane_ref_y") or self.y_ref)
                if lw > 4:
                    self.ppm_ref = lw / LANE_WIDTH_M
                    self.y_ref = ly
                    self.method = "lane_width"
                    self.note = (f"车道宽标定：{lw:.0f}px / {LANE_WIDTH_M}m "
                                 f"= {self.ppm_ref:.1f} px/m @ y={ly:.0f}")
            except (TypeError, ValueError):
                pass

        # ③ 斑马线标定（用四边形的横向跨度）
        # ★2026-10-06 由 DSH 同上收紧：显式相机参数优先于这条区域推导路径。
        if not self._explicit_cam and not self.ppm_ref and self.crosswalk_zones:
            try:
                poly = self.crosswalk_zones[0]
                xs = [float(p[0]) for p in poly]
                ys = [float(p[1]) for p in poly]
                span_px = max(xs) - min(xs)
                if span_px > 10:
                    self.ppm_ref = span_px / self.crosswalk_width_m
                    self.y_ref = sum(ys) / len(ys)
                    self.method = "crosswalk"
                    self.note = (f"斑马线标定：{span_px:.0f}px / {self.crosswalk_width_m}m "
                                 f"= {self.ppm_ref:.1f} px/m @ y={self.y_ref:.0f}")
            except (TypeError, ValueError, IndexError):
                pass

        # 兜底 1：地面平面几何标定（2026-10-04 由 DSH 新增）
        # ─────────────────────────────────────────────────────────────
        # ⚠ 当前状态：**仅在人工显式标注相机参数时启用**。
        #
        # 原因（必须诚实记录）：
        #   实测发现 assumed_lanes 在"相机高 + 俯角大"的路口机位下会
        #   系统性高估 ppm（CARLA 场景：假设值 108.7 vs 几何真值 4.1~28.2，
        #   高估 7.3 倍 -> 真实 6.5~26.6 km/h 的车被算成 0.0 km/h）。
        #
        #   为此新增了 ground_plane 几何模型，但它**尚未通过交叉验证**：
        #     几何真值:  y=360→4.1, y=720→11.6, y=1080→15.0, y=1368→24.4
        #     新模型值:  y=360→11.9, y=720→23.1, y=1080→38.0, y=1368→52.5
        #     仍高估 2~3 倍 —— 说明实现里有 bug（同一几何模型两个实现不一致）。
        #
        # 因此：**不让它在无标注时自动生效**。理由是"半对的模型更危险" ——
        # method 会显示 ground_plane，看起来像精确标定，实际错 2 倍，
        # 比原来的粗估（明确标注 assumed）更容易误导使用者。
        #
        # TODO（待修）：定位两个实现的 2 倍差异后，再放开自动启用。
        # ─────────────────────────────────────────────────────────────
        # ── A) ★主路径：相机几何 -> 解析反投影（2026-10-06 修正后启用）──────
        # 只要**人工显式**给了相机参数（离地高度/俯角/视场角），就走这条。
        # 实测（真实渲染帧 + YOLO 框 + CARLA 世界坐标，12 组对应）：
        #   反解误差 0.2~0.7 m，速度误差 -2.5%~+4.4%；同一数据下旧 ppm 单点法
        #   在近处会差 100~450 px 的像素级偏差。
        if not self.ppm_ref and self._explicit_cam:
            if self._ppm_given:
                # 让人看得见"你设的 pixel_per_meter 被几何覆盖了"，而不是默默换算法
                self.warnings.append(
                    f"已按完整相机参数走几何标定，忽略 pixel_per_meter="
                    f"{s.get('pixel_per_meter')}（几何路径更准；如需强制用 ppm，"
                    f"请清空 camera_height_m / camera_pitch_deg / fov_deg）")
            _up = make_unprojector(self.cam_height_m, self.cam_pitch_deg,
                                   self.fov_deg, self.W, self.H,
                                   self.cam_yaw_deg, self.cam_world_x, self.cam_world_y)
            if _up is not None:
                self.unproject = _up
                self.method = "camera_geometry"
                self.note = (f"相机几何标定：离路面高 {self.cam_height_m:.2f}m、"
                             f"俯角 {self.cam_pitch_deg:.2f}°、水平视场 {self.fov_deg:.0f}°、"
                             f"偏航 {self.cam_yaw_deg:.1f}°、{self.W}x{self.H}")
                _hz = self.horizon_y()
                if _hz is not None and _hz > 0.85 * self.H:
                    self.warnings.append(
                        f"地平线在 y={_hz:.0f}（画面 {100.0*_hz/self.H:.0f}% 处），"
                        f"可见地面太少，请核对俯角/视场角")
            else:
                self.warnings.append("相机参数无法构造反投影（检查高度/俯角/视场角）")

        # ── B) 人工点选 ≥4 个已知地面坐标点 -> 单应矩阵（2026-10-06 新增）──
        # 连相机参数都不知道时可用；与 A 同时给出时以 A 为准并自动比对（见下）。
        if not self.ppm_ref and self.unproject is None and s.get("ground_points"):
            _hg = homography_from_ground_points(s["ground_points"], self.W, self.H)
            if _hg:
                self.Hinv = _hg["Hinv"]
                self.unproject = _hg["unproject"]
                self.calib_rms_m = _hg.get("rms_m")
                self.method = "ground_homography"
                self.note = (f"地面单应标定：{_hg['points_used']} 个已知地面点，"
                             f"自检残差 {_hg['rms_m']:.2f} m")
                if _hg.get("warning"):
                    self.warnings.append(_hg["warning"])
            else:
                self.warnings.append("ground_points 解不出单应矩阵（需 ≥4 点且不共线）")

        # A 与 B 同时给出时：交叉校核（差异过大说明其中一套参数抄错了）
        if self.unproject is not None and s.get("ground_points"):
            _dev = cross_check_unprojectors(self.unproject, s["ground_points"])
            if _dev is not None and _dev > max(1.0, 0.10 * abs(_dev)):
                self.warnings.append(
                    f"相机参数与人工点选的标定不一致（平均差 {_dev:.2f} m），请复核")

        # ── 旧"无标定也默认启用地面几何"分支已删除（2026-10-06）─────────────
        # 原实现：没有人工标定时，用 DEFAULT 参数（h=8.0 / pitch=-20）调
        # ground_plane_ppm()，并把 method 设成 "ground_plane"。
        # 实测：该默认值对真实机位（h≈5.7 / pitch≈-23.4）的反解 RMS 达 94 m，
        # 而 method 显示得像"已精确标定" —— 比明确标注 assumed 的粗估更危险。
        # 现改为：**只有人工显式给相机参数才走 A 路径**。
        # 注：ground_plane_ppm() 本身数学是对的（与独立推导比值 1.001~1.003），
        #     保留为工具函数与对照实现。

        # ── 兜底：用**车道数**估算（D 路径 = 真正无标定）──────────────────
        # 2026-10-03 由 DSH 改进。原实现直接 frame_width / 14.0，
        # 隐含假设"整幅画面横向就是 14 米"，对典型路口监控严重失真
        # （画面常横向覆盖 30-40 米：双向多车道 + 非机动车道 + 人行道），
        # 实测导致 ppm 高估 2-3 倍、车速被低估 2-3 倍。
        # 改进：按"画面横向约可见 N 条车道"估算，N 由画面宽高比推断
        # （宽高比越大 -> 相机越广角 -> 可见车道越多），并给出明确提示。
        # ⚠ 2026-10-06：条件补上 `self.unproject is None` —— 否则会把
        #   已经标定好的 camera_geometry/ground_homography 覆盖成 assumed_lanes。
        if not self.ppm_ref and self.unproject is None:
            ar = self.W / max(1.0, float(self.H))
            # 经验映射：16:9 窄角 -> 约 4 车道；21:9 广角 -> 约 7 车道
            n_lanes = max(2.0, min(8.0, 2.0 + (ar - 1.0) * 5.0))
            # 车道宽 3.75m + 0.25m 车道线/间隙
            est_width_m = n_lanes * 4.0
            self.ppm_ref = self.W / est_width_m
            self.method = "assumed_lanes"
            self.note = (f"无标定：按画面宽高比 {ar:.2f} 推断约 {n_lanes:.1f} 条车道 "
                         f"≈ {est_width_m:.1f}m（{self.ppm_ref:.1f} px/m），"
                         f"误差可能达 ±50%，仅供演示；正式使用请填相机参数或点选标定点")
        self.n_lanes_est = locals().get('n_lanes', None)

    # ------------------------------------------------------------------
    @property
    def calibrated(self) -> bool:
        """是否拥有可信标定（A/B/C 路径之一）"""
        return self.method in ("camera_geometry", "ground_homography",
                               "lane_width", "crosswalk", "explicit_ppm")

    def horizon_y(self):
        """地平线所在行（相机几何可得时）；不可得返回 None

        推导：射线垂直分量为 0 时即地平线
              fwd_z + ((H/2 - v)/f) * up_z = 0  ->  v = H/2 + f*tan(pitch)
        （pitch 向下为负 -> 地平线在画面中心**上方**，符合俯视监控的实际情况）
        """
        if self.unproject is None:
            return None
        try:
            f = self.W / (2.0 * math.tan(math.radians(self.fov_deg) / 2.0))
            return float(self.H / 2.0 + f * math.tan(math.radians(self.cam_pitch_deg)))
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    def ppm_at(self, y: float) -> float:
        """某 y 处的 pixels-per-meter（沿画面中线的纵向比例尺）

        2026-10-06 由 DSH 改为**优先用反投影**：与 ground_point() 同一套几何，
        避免"比例尺"与"反投影"两个实现互相打架（历史上正是这样翻车的）。
        """
        if self.unproject is not None:
            p1 = self.unproject(self.W / 2.0, float(y))
            p2 = self.unproject(self.W / 2.0, float(y) - 1.0)
            if p1 is not None and p2 is not None:
                dd = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
                if dd > 1e-9:
                    return 1.0 / dd
        # 兼容：老 scene 里若 method 写着 ground_plane 仍按几何算
        if self.method == "ground_plane" or getattr(self, "_use_ground_plane", False):
            gp = ground_plane_ppm(y, self.H, self.W,
                                  self.cam_height_m, self.cam_pitch_deg, self.fov_deg)
            if gp and gp > 0:
                return gp
        return _ppm_at_y(self.ppm_ref, self.y_ref, float(y), self.y_horizon)

    # ------------------------------------------------------------------
    # ★像素 -> 地面（2026-10-06 新增）：测速的主路径
    # ------------------------------------------------------------------
    def ground_point(self, u: float, v: float):
        """像素坐标 -> 地面局部米制 (X 前向, Y 右向)；不可解返回 None

        A 路径：相机几何解析反投影（X 沿相机朝向、Y 向右）
        B 路径：人工点选标定的单应矩阵（X/Y 为**用户给的坐标系**，测距仍有效）
        """
        if self.unproject is not None:
            try:
                return self.unproject(float(u), float(v))
            except Exception:
                return None
        if self.Hinv is not None:
            return pixel_to_ground_m(self.Hinv, u, v)
        return None

    def contact_point(self, bbox):
        """由 bbox 求**触地点**（底边中点）——测速应当用这个，不是框中心

        理由（2026-10-06 实测）：框中心在车身上方约 0.7m，把它当触地点反投影，
        近处会系统性偏近（实测帧上差 0.5~1.5m），且偏差随距离变化 -> 速度被扭曲。
        底边中点近似轮胎触地，且对"车尾朝向相机"的情况是一个恒定偏移
        （做差求速度时自然抵消）。
        """
        try:
            x1, y1, x2, y2 = [float(t) for t in bbox[:4]]
        except (TypeError, ValueError, IndexError):
            return None
        return ((x1 + x2) / 2.0, y2)

    def ground_distance(self, uv1, uv2):
        """两个像素点之间的**实际地面距离**（米）；不可解返回 None"""
        g1 = self.ground_point(uv1[0], uv1[1])
        g2 = self.ground_point(uv2[0], uv2[1])
        if g1 is None or g2 is None:
            return None
        return math.hypot(g2[0] - g1[0], g2[1] - g1[1])

    def preview(self, fractions=(0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 0.98)) -> Dict:
        """给前端的**标定预览**：不落库，直接看参数效果

        返回逐行的 ppm / 地面距离 / 是否可解，便于"参数输入界面"实时反馈。
        """
        d = {"method": self.method, "calibrated": self.calibrated, "note": self.note,
             "warnings": list(self.warnings), "frame": [self.W, self.H],
             "unprojector": self.unproject is not None,
             "horizon_y": (round(self.horizon_y(), 1)
                           if self.horizon_y() is not None else None)}
        if self.method.startswith(("camera_geometry", "ground_homography", "ground_plane")):
            d["camera"] = {"height_m": round(self.cam_height_m, 3),
                           "pitch_deg": round(self.cam_pitch_deg, 3),
                           "yaw_deg": round(self.cam_yaw_deg, 3),
                           "fov_deg": round(self.fov_deg, 3)}
        rows = {}
        for fr in fractions:
            y = self.H * float(fr)
            g = self.ground_point(self.W / 2.0, y)
            rows["y=%d" % int(y)] = {
                "ppm": round(self.ppm_at(y), 2),
                "ground_m_forward": (round(g[0], 2) if g else None),
                "ground_m_right": (round(g[1], 2) if g else None),
                "ok": g is not None,
            }
        d["rows"] = rows
        # 可解像素比例（抽样估计）—— 参数填错时这一项会立刻暴露
        tot = ok = 0
        for v in range(0, max(1, self.H), max(1, self.H // 40)):
            for u in (self.W * 0.25, self.W * 0.5, self.W * 0.75):
                tot += 1
                if self.ground_point(u, v) is not None:
                    ok += 1
        d["solvable_ratio"] = round(ok / max(1, tot), 3)
        return d

    def px_speed_to_kmh(self, px_per_sec: float, y: float) -> float:
        """像素/秒 -> km/h（在给定 y 处标定）——旧路径，仅作兜底"""
        ppm = self.ppm_at(y)
        if ppm <= 0:
            return 0.0
        m_per_sec = float(px_per_sec) / ppm
        return m_per_sec * 3.6

    def info(self) -> Dict:
        d = {"method": self.method, "note": self.note,
             "calibrated": self.calibrated,
             "ppm_ref": round(self.ppm_ref, 2), "y_ref": round(self.y_ref, 1),
             "y_horizon": round(self.y_horizon, 1),
             "lane_width_m": LANE_WIDTH_M,
             "warnings": list(self.warnings)}
        if self.unproject is not None or self.method == "ground_plane" \
                or getattr(self, "_use_ground_plane", False):
            d["camera_height_m"] = self.cam_height_m
            d["camera_pitch_deg"] = self.cam_pitch_deg
            d["camera_yaw_deg"] = self.cam_yaw_deg
            d["fov_deg"] = self.fov_deg
            d["horizon_y"] = (round(self.horizon_y(), 1)
                              if self.horizon_y() is not None else None)
            # 给出若干行的 ppm，便于核对
            samples = {}
            for frac in (0.25, 0.5, 0.75, 0.95):
                vv = self.H * frac
                gp = self.ppm_at(vv)
                if gp:
                    samples[f"y={int(vv)}"] = round(gp, 1)
            d["ppm_by_row"] = samples
        if self.calib_rms_m is not None:
            d["calib_rms_m"] = round(self.calib_rms_m, 3)
        return d


# ---------------------------------------------------------------------------
# 帧率补偿表（2026-10-03 由 DSH 基于实测数据标定）
#
# 背景：ByteTrack 的卡尔曼滤波会**平滑**轨迹，帧率越低平滑偏置越大 ->
# 总位移被低估 -> 车速被低估。实测（合成轨迹，真值 60 km/h，y=430）：
#     10fps -> 60.6 km/h  (+1.0%)
#     15fps -> 50.8 km/h  (-15.3%)   ← 项目实际运行帧率
#     25fps -> 58.3 km/h  (-2.8%)
#     30fps -> 56.4 km/h  (-6.0%)
# 误差方向**恒为低估**（安全特性：倾向漏报而非误报）。
#
# 补偿策略：按帧率查表 + 线性插值，仅做**保守补偿**
#   · 表内 fps -> 直接用实测补偿系数
#   · 表外 fps -> 夹到最近端点；>30fps 不补偿（视为无明显偏置）
#   · 补偿系数恒 >= 1.0（只补偿低估，不主动放大）
#
# 重要：补偿只是"减小系统性偏差"，**不改变"未标定不判超速"的门禁**。
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 地面平面标定（2026-10-04 由 DSH 新增）—— 修复 assumed_lanes 的系统性高估
#
# 实测问题（CARLA 26m 高、俯角 35°、2560x1440 的监控机位）：
#     几何真值:          ppm 随画面行从 4.1 变到 28.2
#     assumed_lanes 兜底: ppm = 108.7
#     -> 系统性高估 7.32 倍 -> 同样的像素位移算出的车速小 7 倍
#        （实测结果：真实 6.5~26.6 km/h 的车，测出来全是 0.0 km/h）
#
# 这是**真实部署同样会遇到**的问题：路口高位监控（含用户后期要接的 K230）
# 都是"相机高、俯角大"的几何，而 assumed_lanes 只按画面宽高比猜车道数，
# **完全不知道相机多高、俯角多大**，因此必然失真。
#
# 正确模型（针孔相机 + 地面平面）：
#     f  = image_w / (2 tan(fov/2))          焦距（像素）
#     t  = -(v - H/2) / f                    该行射线在相机系的 z/x
#     方向 = fwd + t*up                      fwd/up 由俯仰角确定
#     交点尺度 s = 相机高度 / (-方向.z)        射线打到地面
#     水平距离 d(v) = |s * 方向.x|
#     ppm(v) = 1 / (|d(v+1)-d(v-1)| / 2)      每像素对应多少米
#
# 参数（可由场景标注提供）：
#     camera_height_m   相机离路面高度（米）
#     camera_pitch_deg  俯角，向下为负
#     fov_deg           水平视场角
# ⚠⚠ 2026-10-06：这三个 DEFAULT 值**只是界面预填**，不再作为隐式标定！
#     实测默认值 h=8.0/pitch=-20 对真实机位(h≈5.7/pitch≈-23.4)反解 RMS 达 94 m。
#     没有人工显式参数时，标定来源一律落在 assumed_lanes（会被超速门禁拦住）。
# ---------------------------------------------------------------------------
DEFAULT_CAMERA_HEIGHT_M = 8.0
DEFAULT_CAMERA_PITCH_DEG = -20.0
DEFAULT_FOV_DEG = 70.0


def ground_plane_ppm(v: float, frame_h: int, frame_w: int,
                     height_m: float, pitch_deg: float, fov_deg: float):
    """画面第 v 行处、地面平面上的 pixels-per-meter（几何近似）

    ★2026-10-06 由 DSH 更正定性：**本函数的数学是对的**，可以放心用。
      与独立推导的解算反投影（make_unprojector）对照，同一机位下比值 **1.001~1.003**。

    ⚠ 被推翻的旧结论：本函数此前被标注为"已被 580 样本证明系统性偏小 0.61 倍、
      速度高估 1.6 倍"。那个结论**不成立** —— 它对照的
      `_dual_cam_demo\\ground_truth_dual.csv` 的 cam1_u/cam1_v 不是测量值，
      而是 `_scripts\\_dual_cam_demo.py:217/231` 里 Proj.project() 自己算出来
      写进 CSV 的模型输出（同一份 Proj 重算 580 行，u 中位误差 0.51 px）。
      真正让车速算错的是**默认参数**：h=8.0/pitch=-20 对真实机位的 ppm 比只有
      0.717（速度被高估约 1.4 倍）—— 是"参数不对"，不是"公式不对"。

    已知局限（保留本函数仅作对照/工具，测速主路径请用 make_unprojector）：
      ① 只给"沿相机朝向的纵向比例尺"，不含横向；目标明显偏离画面中线时需用
         完整反投影（ground_point）；
      ② 用 ±1 行的差分近似，行数很小时（近地平线）精度下降；
      ③ yaw 不影响该纵向比例尺，故本函数不需要 yaw 参数。
    """
    try:
        h = float(height_m)
        if h <= 0.1:
            return None
        th = math.radians(float(pitch_deg))
        f = float(frame_w) / (2.0 * math.tan(math.radians(float(fov_deg)) / 2.0))
        cp, sp = math.cos(th), math.sin(th)
        fwd_x, fwd_z = cp, sp          # 相机基（世界系，yaw=roll=0）
        up_x, up_z = -sp, cp

        def dist_at(vp):
            t = -(float(vp) - frame_h / 2.0) / f
            dx = fwd_x + t * up_x
            dz = fwd_z + t * up_z
            if abs(dz) < 1e-9:
                return None
            s = -h / dz
            if s <= 0:
                return None
            return abs(s * dx)

        d1, d2 = dist_at(v - 1.0), dist_at(v + 1.0)
        if d1 is None or d2 is None:
            return None
        dm = abs(d2 - d1)
        if dm < 1e-9:
            return None
        return 1.0 / (dm / 2.0)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


# ---------------------------------------------------------------------------
# ★地面单应矩阵（2026-10-06 由 DSH 新增）—— 取代上面的 ground_plane_ppm
#
# 为什么需要它：
#   上面那个模型系统性偏小 0.61 倍（实测），且缺横向分量。
#   地面 z=0 平面上的点 (X,Y) 与像素 (u,v) 之间是标准的 3x3 单应变换，
#   纵向横向一并正确，是这类问题的正解。
#
# 关键优势：**不需要人工标点**。
#   只要知道「相机高度 / 俯角 / 偏航角 / 水平视场角」，
#   就能用针孔模型算出 4 个已知地面点对应的像素，从而解出单应矩阵。
#   这正好满足"前端填几个参数就能测速、换摄像头不用改代码"的需求。
#
# 实测精度（ground_truth_dual.csv，580 样本，相机高 5.0m / 俯角 -23.4° / fov 90°）：
#     平均误差 0.77 m    中位 0.76 m    90 分位 1.42 m
#   世界 x（沿路）误差 0.09~0.96 m；世界 y（横向车道）也对得上。
# ---------------------------------------------------------------------------

def make_unprojector(cam_height_m: float, pitch_deg: float, fov_deg: float,
                     frame_w: int, frame_h: int,
                     yaw_deg: float = 0.0,
                     cam_world_x: float = 0.0, cam_world_y: float = 0.0):
    """构造「像素 -> 地面局部米制」的解析反投影函数。

    ★★ 2026-10-06 由 DSH **修正符号**并验证。**这是本项目测速标定的推荐路径。**

    ── 相机基（正交，必须成对满足 fwd·up = 0）──────────────────────────
        fwd   = ( cos p·cos y,  cos p·sin y,  sin p)      ← p 向下为负 -> fwd.z < 0
        right = (-sin y,        cos y,         0    )
        up    = (-sin p·cos y, -sin p·sin y,   cos p)     ← up.z > 0（朝上）
        f = W / (2·tan(fov/2))     （fov 是**水平**视场角）
        射线: d = fwd + ((u-W/2)/f)·right + ((H/2-v)/f)·up
        地面: t = (0 - cam_z)/d.z = -h/d.z（需 t>0），P = cam + t·d

    ── ⚠ 这里曾经错在哪（务必不要再改回去）─────────────────────────────
      2026-10-06 之前的版本写的是
          fwd = (cos p·cos y, cos p·sin y, **-sin p**)   ← z 分量写反
          up  = (-sin p·cos y, -sin p·sin y, **-cos p**) ← z 分量也写反
          d   = ... + ((v-H/2)/f)·up
      当时用"4 组符号组合暴力搜索"定案，报出 "fwd_z=+1/up_z=-1 最优、误差 2.20m"，
      但那是拿 ground_truth_dual.csv 当基准搜的 —— 而那份 CSV 的 cam1_u/v
      **不是测量值**，是 _dual_cam_demo.py 里 Proj.project() 自己算出来写进去的
      （同一份 Proj 重算 580 行，u 中位误差 0.51px）。等于用错误基准挑了一组错误符号。
      后果：fwd 朝**上** 23.4°、up 朝**下**，整套基"倒"了 ——
      只有画面最下方 11%（本机位 y>956）的像素能反解成功，
      这正是旧注释里"同样 580 个点里 578 个失败"的真因。
      ⚠ 注意 (fwd=-sp, up=+cp) 与 (fwd=+sp, up=-cp) 这两组**都正交**，
      光看"正交/能解出点"分辨不出来，必须拿**真实渲染帧**对照（见验证脚本）。

    ── 已验证（2026-10-06，三级证据）───────────────────────────────────
      素材：_dual_cam_demo 的 13 张真实渲染帧 + 项目自带 YOLO(yolov8s) 检测框
            + CSV 里可信的 CARLA 世界坐标（(x,y) 直读 actor transform）
      结果：本函数反解误差 0.2~0.7 m（12 组对应，扣掉车长一半的恒定偏移后）；
            速度误差 -2.5%~+4.4%。同一数据下 demo 版模型 Δu 最大 454 px。

    返回的函数签名：f(u, v) -> (x_forward_m, y_right_m) 或 None
      x_forward_m = 沿相机水平朝向的距离（米）
      y_right_m   = 相机右向的距离（米）
    ⚠ cam_height_m 必须是**镜头到地面平面**的高度（不是离世界原点的高度）。
    """
    try:
        h = float(cam_height_m)
        if h <= 0.1:
            return None
        import numpy as np
        loc = np.array([float(cam_world_x), float(cam_world_y), h], float)
        p, y = math.radians(float(pitch_deg)), math.radians(float(yaw_deg))
        cp, sp, cy, sy = math.cos(p), math.sin(p), math.cos(y), math.sin(y)
        # ★正交且**朝下**的相机基（2026-10-06 修正，勿改）
        fwd = np.array([cp * cy, cp * sy, sp])
        right = np.array([-sy, cy, 0.0])
        up = np.array([-sp * cy, -sp * sy, cp])
        f = float(frame_w) / (2.0 * math.tan(math.radians(float(fov_deg)) / 2.0))
        dir2 = np.array([cy, sy])          # 相机水平朝向
        perp2 = np.array([-sy, cy])        # 相机右向（水平）

        def _unproject(u, v):
            # 像素 y 项用 (H/2 - v)：v 越大（越靠画面下方）射线越朝下
            d = ((float(u) - frame_w / 2.0) / f) * right + \
                ((frame_h / 2.0 - float(v)) / f) * up + fwd
            if abs(d[2]) < 1e-9:
                return None                # 射线水平 -> 与地面平行
            t = (0.0 - loc[2]) / d[2]
            if t <= 0:
                return None                # 射线朝上 / 地面在相机后方
            P = loc + t * d
            dx, dy = P[0] - loc[0], P[1] - loc[1]
            xf = float(dx * dir2[0] + dy * dir2[1])
            yr = float(dx * perp2[0] + dy * perp2[1])
            if xf <= 0.5 or xf > 400.0:
                return None                # 太近/太远（>400m 几何精度无意义）
            return (xf, yr)

        return _unproject
    except Exception:
        return None


def homography_from_ground_points(points, frame_w=None, frame_h=None):
    """人工点选「像素 <-> 已知地面坐标」点，解单应矩阵（B 路径，2026-10-06 新增）

    points: [{'u':像素x, 'v':像素y, 'x':地面米, 'y':地面米}, ...]（≥4 个）
      地面坐标的**原点与朝向任意**（测速只用到距离，朝向不影响结果）；
      但 4 点不能共线/过近，否则矩阵退化。
    frame_w/frame_h: 可选，仅用于合理性检查（点是否落在画面内）。

    返回 {'Hinv','Hm','unproject','rms_m','points_used','warning'} 或 None
      Hinv: 像素->地面（cv2 约定，需齐次归一化）
      unproject(u,v) -> (X米, Y米) 或 None
    """
    try:
        import numpy as np
        import cv2
    except Exception:
        return None
    pts = []
    for q in (points or []):
        try:
            u, v = float(q.get("u")), float(q.get("v"))
            X, Y = float(q.get("x")), float(q.get("y"))
        except (TypeError, ValueError, AttributeError):
            continue
        pts.append(((u, v), (X, Y)))
    if len(pts) < 4:
        return None

    def _spread_ratio(seq):
        """点集是否退化成一条线：PCA 次特征值 / 主特征值

        （不要用"任意三点共线就拒绝"的严格判据 —— 实测 6 个正常点里
          离群点/近共线三元组很常见，会把能用的输入误判为退化；
          交给 cv2 的 RANSAC + 行列式 + 角点映射校验更稳。）
        """
        if len(seq) < 3:
            return 0.0
        try:
            a = np.array(seq, float)
            a = a - a.mean(axis=0)
            cov = a.T @ a / max(1, len(a))
            ev = np.sort(np.abs(np.linalg.eigvalsh(cov)))
            if ev[-1] <= 1e-12:
                return 0.0
            return float(ev[0] / ev[-1])
        except Exception:
            return 0.0

    px = [p[0] for p in pts]
    gp = [p[1] for p in pts]
    src = np.array(px, np.float32)
    dst = np.array(gp, np.float32)
    warn = None
    try:
        if len(pts) == 4:
            # 严格 4 点：无离群剔除余地，必须先查退化（点排成一条线就无解）
            if _spread_ratio(px) < 0.01 or _spread_ratio(gp) < 0.01:
                return None
            Hpx2g = cv2.getPerspectiveTransform(src, dst)      # 像素 -> 地面
            rms = 0.0
        else:
            Hpx2g, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
            if Hpx2g is None:
                return None
            inl = (mask.ravel().astype(bool) if mask is not None
                   else np.ones(len(pts), bool))
            if int(inl.sum()) < 4:
                return None
            # 退化检查只看**内点**（单个粗差点不应把整组判死）
            if _spread_ratio([px[i] for i in range(len(px)) if inl[i]]) < 0.01 or \
                    _spread_ratio([gp[i] for i in range(len(gp)) if inl[i]]) < 0.01:
                return None
            proj = cv2.perspectiveTransform(src.reshape(-1, 1, 2), Hpx2g).reshape(-1, 2)
            e = [math.dist(tuple(proj[i]), gp[i]) for i in range(len(gp)) if inl[i]]
            rms = math.sqrt(sum(x * x for x in e) / max(1, len(e)))
            n_out = int((~inl).sum())
            if n_out:
                warn = f"{n_out} 个标定点被 RANSAC 判为离群（可能是点错了），已按内点求解"
            if rms > 3.0:
                warn = ((warn + "；") if warn else "") + \
                    f"内点自检残差 {rms:.2f} m 偏大（>3m），请检查标定点"
    except Exception:
        return None
    if not np.all(np.isfinite(Hpx2g)):
        return None
    try:
        if abs(float(np.linalg.det(Hpx2g))) < 1e-12:
            return None
        Hg2px = np.linalg.inv(Hpx2g)
    except Exception:
        return None
    # 退化校验：把画面四角映射到地面，若出现爆炸值说明矩阵不可用
    try:
        corners = np.array([[[0.0, 0.0]], [[frame_w - 1 if frame_w else 1919, 0.0]],
                            [[0.0, frame_h - 1 if frame_h else 1079]],
                            [[frame_w - 1 if frame_w else 1919,
                              frame_h - 1 if frame_h else 1079]]], np.float32)
        cg = cv2.perspectiveTransform(corners, Hpx2g).reshape(-1, 2)
        if not np.all(np.isfinite(cg)) or float(np.abs(cg).max()) > 1e5:
            return None
    except Exception:
        pass
    if frame_w and frame_h:
        inside = sum(1 for (u, v) in px if 0 <= u < frame_w and 0 <= v < frame_h)
        if inside < len(px):
            warn = ((warn + "；") if warn else "") + \
                f"{len(px)-inside} 个标定点落在画面外({frame_w}x{frame_h})"

    def _unproject(u, v):
        q = Hpx2g @ np.array([float(u), float(v), 1.0])
        if abs(q[2]) < 1e-12:
            return None
        X, Y = float(q[0] / q[2]), float(q[1] / q[2])
        if not (-1000.0 <= X <= 1000.0) or not (-1000.0 <= Y <= 1000.0):
            return None
        return (X, Y)

    # 沿用旧命名：Hinv = 像素->地面（pixel_to_ground_m 用），Hm = 地面->像素
    return {"Hinv": Hpx2g, "Hm": Hg2px, "unproject": _unproject,
            "rms_m": float(rms), "points_used": len(pts), "warning": warn}


def cross_check_unprojectors(unproject, points, tol_m=1.0):
    """用人工点选的已知点校核反投影函数，返回平均偏差（米）或 None

    用于"A+B 都填"时自动发现参数抄错（例如俯角符号填反、高度单位填错）。
    """
    try:
        devs = []
        for q in (points or []):
            try:
                u, v = float(q.get("u")), float(q.get("v"))
                X, Y = float(q.get("x")), float(q.get("y"))
            except (TypeError, ValueError, AttributeError):
                continue
            g = unproject(u, v)
            if g is None:
                continue
            devs.append(math.hypot(g[0] - X, g[1] - Y))
        if not devs:
            return None
        return sum(devs) / len(devs)
    except Exception:
        return None


def ground_plane_homography(cam_height_m: float, pitch_deg: float, fov_deg: float,
                            frame_w: int, frame_h: int,
                            yaw_deg: float = 0.0,
                            cam_world_x: float = 0.0, cam_world_y: float = 0.0,
                            span_m: float = 120.0, lateral_m: float = 40.0):
    """由相机参数构造「像素 -> 地面米制」单应矩阵（可选路径）。

    ⚠2026-10-06 由 DSH 记录：**本函数不是推荐路径，请优先用 make_unprojector()。**

    背景（三次失败记录，供后人避坑）：
      失败1：另推一份"等价"针孔式构造矩阵 -> 与验证用的 3D 投影不一致，差 58 m。
             教训：同一套数学只能有一个实现。
      失败2：用"近点+大横向"地面点正向构造（前6m / 横向±40m）
             -> 投影到像素 ±10000，矩阵退化（画面中心反解出 3e8 米）。
      失败3：用画面底边 4 点反向构造 -> **4 点共线**，getPerspectiveTransform
             从退化四边形解不出来（本项目机位下画面底边对应地面横向跨度达 85 m，
             远处更大，可选范围极窄）。

    因此：**改用 make_unprojector() 的解析反投影**（不需要构造点、不会退化）。
    本函数保留为可选实现：它采用「底边两角 + 上方一行内缩两点」的梯形，
    若该梯形能解出稳定矩阵则返回，否则返回 None（调用方应回退到解析反投影）。
    """
    try:
        up_fn = make_unprojector(cam_height_m, pitch_deg, fov_deg, frame_w, frame_h,
                                 yaw_deg, cam_world_x, cam_world_y)
        if up_fn is None:
            return None
        import numpy as np
        import cv2
        yb = float(frame_h - 1)
        # 梯形：底边两角 + 上方一行内缩点（实验取 0.86 高度，确保仍在地面）
        yt = float(frame_h) * 0.86
        cand = [(0.0, yb, float(frame_w - 1), yb),
                (float(frame_w) * 0.22, yt, float(frame_w) * 0.78, yt)]
        px_pts = [(cand[0][0], cand[0][1]), (cand[0][2], cand[0][3]),
                  (cand[1][0], cand[1][1]), (cand[1][2], cand[1][3])]
        local_pts = []
        for (u, v) in px_pts:
            lp = up_fn(u, v)
            if lp is None:
                return None
            local_pts.append(lp)
        if len(set((round(a, 2), round(b, 2)) for a, b in local_pts)) < 4:
            return None
        Hm = cv2.getPerspectiveTransform(np.array(local_pts, np.float32),
                                         np.array(px_pts, np.float32))
        det = float(np.linalg.det(Hm))
        if not np.isfinite(det) or abs(det) < 1e-12:
            return None
        Hinv = np.linalg.inv(Hm)
        # 与解析反投影交叉校验：多处像素，两者误差必须很小
        devs = []
        for (u, v) in ((frame_w / 2, frame_h * 0.95), (frame_w * 0.25, frame_h * 0.9),
                       (frame_w * 0.75, frame_h * 0.88), (frame_w / 2, frame_h * 0.8)):
            ref = up_fn(u, v)
            if ref is None:
                continue
            q = Hinv @ np.array([float(u), float(v), 1.0])
            if abs(q[2]) < 1e-12:
                return None
            devs.append(math.dist(ref, (q[0] / q[2], q[1] / q[2])))
        if not devs or max(devs) > 0.5:
            return None
        return {"Hinv": Hinv, "Hm": Hm, "unproject": up_fn,
                "cam_loc": (float(cam_world_x), float(cam_world_y), float(cam_height_m)),
                "note": (f"地面单应矩阵：相机高 {cam_height_m:.1f}m、俯角 {pitch_deg:.1f}°、"
                         f"偏航 {yaw_deg:.1f}°、fov {fov_deg:.0f}°、{frame_w}x{frame_h}"
                         f"（梯形构造 + 解析反投影交叉校验通过）")}
    except Exception:
        return None


def pixel_to_ground_m(Hinv, u: float, v: float):
    """像素 -> 地面米制坐标（用单应矩阵）。返回 (X米, Y米) 或 None。"""
    try:
        import numpy as np
        p = np.asarray(Hinv, float) @ np.array([float(u), float(v), 1.0])
        if abs(p[2]) < 1e-12:
            return None
        X, Y = p[0] / p[2], p[1] / p[2]
        # 合理性防护：地面点不应在相机后方或过远
        if not (-50.0 <= X <= 500.0) or not (-200.0 <= Y <= 200.0):
            return None
        return (float(X), float(Y))
    except Exception:
        return None


# 测速物理防护阈值（2026-10-04 由 DSH 新增，见 speed_from_history 注释）
MIN_TRUSTED_PPM = 3.0        # 低于此 ppm 说明目标太远，几何精度不足 -> 不测速
MAX_PLAUSIBLE_KMH = 180.0    # 换算结果超过此值判为无效（国内公路上限 120，留余量）

_FPS_COMPENSATION = {
    10.0: 1.010,   # +1.0%  实测
    15.0: 1.180,   # -15.3% 实测 -> 补偿 18%
    25.0: 1.029,   # -2.8%  实测
    30.0: 1.064,   # -6.0%  实测
}


def fps_compensation(fps: float) -> float:
    """按帧率给出保守补偿系数（>= 1.0）"""
    try:
        f = float(fps or 0.0)
    except (TypeError, ValueError):
        return 1.0
    if f <= 0:
        return 1.0
    if f > 30.0:
        return 1.0                      # 高帧率视为无明显偏置
    keys = sorted(_FPS_COMPENSATION)
    if f <= keys[0]:
        return _FPS_COMPENSATION[keys[0]]
    if f >= keys[-1]:
        return _FPS_COMPENSATION[keys[-1]]
    for i in range(1, len(keys)):
        lo, hi = keys[i - 1], keys[i]
        if lo <= f <= hi:
            t = (f - lo) / (hi - lo)
            v = _FPS_COMPENSATION[lo] + t * (_FPS_COMPENSATION[hi] - _FPS_COMPENSATION[lo])
            return max(1.0, round(v, 4))
    return 1.0


def _track_samples(history: List[Dict], max_samples: int):
    """从轨迹历史提取 [(t, 像素点)] —— 优先取 **bbox 底边中点（触地点）**

    2026-10-06 由 DSH 新增。为什么不用 `center`：
      框中心悬在车身上方约 0.7m，把它当地面点反投影，近处会系统性偏近
      （真实帧实测差 0.5~1.5m），且偏差随距离变化 -> 速度被扭曲。
      底边中点 ≈ 轮胎触地；对"车尾朝向相机"的情形它是个**恒定**偏移，
      做差求速度时自动抵消（实测残差 0.1~0.7m）。
    """
    pts = list(history or [])[-max_samples:]
    out = []
    for p in pts:
        try:
            t = float(p.get("timestamp") or 0.0)
        except (TypeError, ValueError):
            continue
        if t <= 0:
            continue
        uv = None
        bb = p.get("bbox")
        if bb is not None:
            try:
                if len(bb) >= 4:
                    uv = ((float(bb[0]) + float(bb[2])) / 2.0, float(bb[3]))
            except (TypeError, ValueError):
                uv = None
        if uv is None and p.get("center"):
            try:
                uv = (float(p["center"][0]), float(p["center"][1]))
            except (TypeError, ValueError, IndexError):
                uv = None
        if uv is None:
            continue
        out.append((t, uv))
    out.sort(key=lambda z: z[0])
    return out


def speed_from_history(history: List[Dict], calibrator: SpeedCalibrator,
                       min_dt: float = 0.15, max_samples: int = 8,
                       expected_fps: float = None) -> Dict:
    """从轨迹历史估算实际车速

    history: [{'center': (x,y), 'bbox': [x1,y1,x2,y2], 'timestamp': t}, ...]

    ★2026-10-06 由 DSH 改为**端点反投影**为主路径：
        取轨迹里可解的首末两点 -> 各自反投影到地面 -> 量地面距离 / 时间。
      为什么不再用"平均 y 处一个 ppm × 像素速度"：
        目标在 1 秒内可能从 15m 跑到 34m，ppm 变化 2~3 倍，用单点比例尺必然失真；
        且像素位移里横竖方向的比例尺本来就不同。
      实测（真实渲染帧 + YOLO 框 + CARLA 真值速度，同一辆车）：
        反投影法 -2.5% / +4.4% / -4.1% / -2.8%；目标很小(40x30px)时 +27.2%，
        而该情形已被 MIN_TRUSTED_PPM 防护拒掉。
      没有反投影（无标定 / 只给了 ppm_ref）时自动退回旧的 ppm 路径。

    expected_fps: 期望帧率（用于帧率补偿）。不传则从 dt 反推，
                  反推失败则不补偿（宁可低估，不可高估）。

    返回：
      {kmh, kmh_raw, fps_compensation, px_per_sec, samples, dt, fps,
       method, confidence, measurement_quality, estimator, distance_m, note}
    """
    out = {"kmh": 0.0, "px_per_sec": 0.0, "samples": 0, "dt": 0.0,
           "method": calibrator.method, "confidence": calibrator.method,
           "note": calibrator.note}
    samples = _track_samples(history, max_samples)
    if len(samples) < 2:
        out["confidence"] = "unavailable"
        return out

    try:
        total_px = 0.0
        total_dt = 0.0
        ys = []
        for i in range(1, len(samples)):
            t0, c0 = samples[i - 1]
            t1, c1 = samples[i]
            dt = t1 - t0
            if dt <= 0:
                continue
            total_px += math.hypot(c1[0] - c0[0], c1[1] - c0[1])
            total_dt += dt
            ys.append((c0[1] + c1[1]) / 2.0)
    except (TypeError, ValueError, IndexError):
        out["confidence"] = "unavailable"
        return out

    if total_dt < min_dt or total_px <= 0:
        out["confidence"] = "unavailable"
        return out
    broken_time = any((samples[i][0] - samples[i - 1][0]) > 1.0
                      for i in range(1, len(samples)))
    if broken_time:
        # 轨迹有明显时间断裂（跟踪中断），降低可信度
        out["note"] = (out["note"] + "；轨迹含时间断裂，精度下降").strip("；")

    y_avg = sum(ys) / len(ys) if ys else calibrator.y_ref
    px_per_sec = total_px / total_dt

    # ---- 物理合理性防护（2026-10-04 由 DSH 新增）------------------------
    # 现场实测踩到的坑：CARLA 视频里 bbox 位于 y=102（画面极上端＝远处），
    # 几何模型的 ppm 在该处趋近 0 -> px/ppm 爆炸 -> 算出 **158.6 km/h**，
    # 而真值是 22 km/h。这不是算法错，是**几何模型在接近地平线时失效**。
    #
    # 两重防护（宁可不出数，也不出假数）：
    #   ① ppm 下限：太低说明目标太远/太靠近地平线，测速不可信 -> 不测
    #   ② 速度上限：超过则判为无效（国内公路最高 120，留余量取 180）
    # -------------------------------------------------------------------
    ppm_here = calibrator.ppm_at(y_avg)
    if ppm_here < MIN_TRUSTED_PPM:
        out["confidence"] = "unavailable"
        out["measurement_quality"] = "too_far"
        out["note"] = (f"目标过远（ppm={ppm_here:.1f} < {MIN_TRUSTED_PPM}），"
                       f"几何精度不足，不输出速度")
        out["px_per_sec"] = round(px_per_sec, 3)
        out["y_avg"] = round(y_avg, 1)
        return out

    # ---- ★主路径：端点反投影 -> 地面距离（2026-10-06 由 DSH 新增）------
    kmh_raw = None
    dist_m = None
    estimator = None
    if calibrator.unproject is not None:
        first = last = None
        for (t, uv) in samples:                       # 从最早端找可解点
            g = calibrator.ground_point(uv[0], uv[1])
            if g is not None:
                first = (t, g)
                break
        for (t, uv) in reversed(samples):             # 从最晚端找可解点
            g = calibrator.ground_point(uv[0], uv[1])
            if g is not None:
                last = (t, g)
                break
        if first is not None and last is not None:
            span = last[0] - first[0]
            if span >= min_dt:
                dist_m = math.hypot(last[1][0] - first[1][0],
                                    last[1][1] - first[1][1])
                kmh_raw = dist_m / span * 3.6
                estimator = "ground_unprojection"
    if kmh_raw is None:
        kmh_raw = calibrator.px_speed_to_kmh(px_per_sec, y_avg)
        estimator = "ppm"

    if kmh_raw > MAX_PLAUSIBLE_KMH:
        out["confidence"] = "unavailable"
        out["measurement_quality"] = "implausible"
        out["note"] = (f"换算速度 {kmh_raw:.0f} km/h 超出物理上限 "
                       f"{MAX_PLAUSIBLE_KMH}，判为无效（多为远处目标被标定放大）")
        out["px_per_sec"] = round(px_per_sec, 3)
        out["y_avg"] = round(y_avg, 1)
        out["estimator"] = estimator
        return out

    # ---- 帧率补偿 + 测量质量自检（2026-10-03 由 DSH 新增）--------------
    # 帧率：优先用调用方给的；否则从平均 dt 反推
    fps = None
    try:
        if expected_fps:
            fps = float(expected_fps)
        elif len(samples) > 1:
            fps = (len(samples) - 1) / total_dt
    except (TypeError, ValueError, ZeroDivisionError):
        fps = None
    comp = fps_compensation(fps) if fps else 1.0
    # 2026-10-03 由 DSH 修正：补偿**默认关闭**。
    # 原因：补偿表是用**单次测量**拟合的（每帧率只跑一次），而 tracker 的
    # 像素速度测量方差本身达 ±30%。用它去补偿会产生**过补偿** ->
    # 车速被高估 -> 误报超速（比漏报更严重）。重复实验证实：
    #   15fps 未补偿 -15.3% -> 补偿后 +16.2%（过冲 31 个百分点）
    # 因此改为：默认不补偿，只**如实报告**原始值与测量质量；
    # 需要时可通过 SPEED_FPS_COMPENSATION=1 开启（并自行承担过补偿风险）。
    _comp_on = str(os.environ.get("SPEED_FPS_COMPENSATION", "0")).strip().lower() \
        in ("1", "true", "yes", "on")
    if not _comp_on:
        comp = 1.0
    kmh = kmh_raw * comp

    # 测量质量：看实际采样密度是否符合预期帧率（采样不足/时间断裂 -> 降级）
    quality = "ok"
    q_note = ""
    try:
        if fps and fps > 0:
            eff_dt = total_dt / max(1, len(samples) - 1)
            exp_dt = 1.0 / fps
            if eff_dt > exp_dt * 2.5:
                quality = "sparse"
                q_note = (f"采样间隔 {eff_dt:.3f}s 明显大于预期 {exp_dt:.3f}s，"
                          f"轨迹可能丢帧，测速精度下降")
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    if broken_time:
        quality = "broken" if quality == "ok" else quality
        q_note = (q_note + "；轨迹含时间断裂").strip("；")

    out.update({
        "px_per_sec": round(px_per_sec, 2),
        "samples": len(samples),
        "dt": round(total_dt, 3),
        "y": round(y_avg, 1),
        "ppm": round(calibrator.ppm_at(y_avg), 2),
        "kmh": round(kmh, 1),
        "kmh_raw": round(kmh_raw, 1),
        "fps": round(fps, 2) if fps else None,
        "fps_compensation": comp,
        "measurement_quality": quality,
        "estimator": estimator,
    })
    if dist_m is not None:
        out["distance_m"] = round(dist_m, 2)
    if comp > 1.0:
        out["note"] = (out["note"] +
                       f"；已按 {fps:.0f}fps 做保守补偿 ×{comp:.3f}"
                       f"（原始 {kmh_raw:.1f} km/h）").strip("；")
    if q_note:
        out["note"] = (out["note"] + "；" + q_note).strip("；")

    # 可信度：标定方式 + 采样量 + 测量质量
    if calibrator.calibrated:
        out["confidence"] = "calibrated" if len(samples) >= 4 else "low_samples"
    else:
        out["confidence"] = "assumed"
    if quality in ("sparse", "broken"):
        # 测量质量差时不允许标为高可信
        if out["confidence"] == "calibrated":
            out["confidence"] = "low_quality"
    return out


def judge_speeding(kmh: float, speed_limit_kmh: float = 60.0,
                   tolerance: float = 0.10) -> Tuple[bool, float]:
    """超速判定（含法定容差）

    真实执法普遍有容差（如限速 60 时通常 66 以上才处罚，约 10%）。
    返回 (是否超速, 超出比例)
    """
    limit = float(speed_limit_kmh) * (1.0 + float(tolerance))
    if kmh <= 0 or limit <= 0:
        return (False, 0.0)
    return (kmh > limit, round((kmh - limit) / limit, 4))
