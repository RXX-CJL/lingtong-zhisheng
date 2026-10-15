# -*- coding: utf-8 -*-
"""红绿灯颜色分类器（CNN4）—— 替代 HSV 阈值法

背景（2026-10-03 由 DSH 实现）：
  原实现用 HSV 色域阈值判色，问题：
    1. 遇背光/偏色/远距离直接放弃（实测 unknown 占 41.4%）
    2. 对误检（限速牌、广告牌）会"硬猜"一个颜色 —— 生产环境很危险
  自训 CNN 分类器（green/red/yellow/none）解决了这两点：
    - 5 折交叉验证准确率 0.997
    - none 类 260/260 正确拒识（能明确说"这不是红绿灯"）

设计：
  - 懒加载 + 单例（避免 import 时就占显存）
  - 线程安全（推理可能来自多个线程）
  - 模型缺失时自动回退到 HSV（保证功能不中断）
  - 置信度低于阈值时返回 unknown，交由调用方决定
"""

import os
import threading
from typing import Optional, Tuple

import cv2
import numpy as np

_MODEL_PATH = os.environ.get(
    "TL_COLOR_MODEL", r"E:\output\_tl_color_cls\tl_color_cnn4.pt")
_IMG_SIZE = 64
_MIN_CONF = float(os.environ.get("TL_COLOR_MIN_CONF", "0.55"))

# ★2026-10-06 由 DSH 新增：两套判色模型，按数据源自动选择
#
# 为什么必须分两套（实测依据）：
#   CNN4 = 用**真实视频**训练（黑/深色灯箱、灯珠填满框）
#   CNN5 = 在 CNN4 基础上用 **CARLA 渲染的灯珠裁图**微调（青蓝色灯箱、灯珠只占框内一小块）
#
#   在 CARLA 演示视频上的准确率（lit 裁图，14 帧真值对照）：
#       CNN4 ->  0/14   （红灯召回 0.000，39 个红灯样本全判 none）
#       CNN5 -> 14/14   （红灯 8/8、绿灯 3/3、黄灯 3/3）
#
# 所以：
#   本地视频回放（多为 CARLA 录制）-> CNN5
#   实时摄像头（真实画面）          -> CNN4
#
# 背景（子代理审计发现的问题 U1/G3）：
#   报告结论是"采用 CNN5"，但本文件默认仍是 cnn4，
#   且 start-all.bat 未设 TL_COLOR_MODEL ->
#   **后端不带环境变量启动就会退回 CNN4，红灯判不出来**。
#   本次改为代码内自动选择，不再依赖环境变量（环境变量仍可覆盖，优先级最高）。
_MODEL_CNN4 = r"E:\output\_tl_color_cls\tl_color_cnn4.pt"
_MODEL_CNN5 = r"E:\output\_tl_color_cls\tl_color_cnn5_carla.pt"

_lock = threading.Lock()
_net = None
_classes = None
_torch = None
_load_failed = False
_loaded_path = None          # 当前已加载的模型路径（供 /status 观测）


def model_file_for_source(source_is_file: bool) -> str:
    """按数据源类型给出应使用的判色模型路径。

    环境变量 `TL_COLOR_MODEL` 优先级最高（显式指定时不自动切换）。
    """
    env = os.environ.get("TL_COLOR_MODEL")
    if env:
        return env
    if source_is_file:
        return _MODEL_CNN5 if os.path.exists(_MODEL_CNN5) else _MODEL_CNN4
    return _MODEL_CNN4 if os.path.exists(_MODEL_CNN4) else _MODEL_CNN5


def use_model(path: str) -> bool:
    """切换判色模型（若与当前不同则重置缓存，下次判色时重新加载）。

    返回 True 表示当前已就绪的模型就是目标模型（或切换动作已登记）。
    线程安全：与 _ensure_loaded 共用同一把锁。
    """
    global _MODEL_PATH, _net, _classes, _load_failed, _loaded_path, _torch
    if not path:
        return False
    with _lock:
        if _loaded_path == path and _net is not None:
            return True
        _MODEL_PATH = path
        # 重置，强制下次 _ensure_loaded 重新加载
        _net = None
        _classes = None
        _load_failed = False
        _loaded_path = None
        _torch = None
    ok = _ensure_loaded()
    logger_msg = "[TLClassifier] 判色模型切换 -> %s (%s)" % (
        os.path.basename(path), "成功" if ok else "加载失败，将回退")
    try:
        import logging
        logging.getLogger("zhitong_api").info(logger_msg)
    except Exception:
        pass
    return ok


def current_model_info() -> dict:
    """当前判色模型信息（供 /api/realtime/status 暴露，便于外部核对）。"""
    return {
        "path": _loaded_path or _MODEL_PATH,
        "file": os.path.basename(_loaded_path or _MODEL_PATH),
        "loaded": _net is not None,
        "load_failed": bool(_load_failed),
        "classes": list(_classes) if _classes else None,
        "env_override": os.environ.get("TL_COLOR_MODEL") or None,
    }


def _ensure_loaded() -> bool:
    """懒加载模型（成功返回 True；失败或缺失返回 False，调用方可回退 HSV）"""
    global _net, _classes, _torch, _load_failed, _loaded_path
    if _net is not None:
        return True
    if _load_failed:
        return False
    with _lock:
        if _net is not None:
            return True
        if _load_failed:
            return False
        if not os.path.exists(_MODEL_PATH):
            _load_failed = True
            return False
        try:
            import torch
            _torch = torch
            # 复用训练脚本的网络定义（保持结构一致）
            import sys
            _sd = r"E:\output\_scripts"
            if _sd not in sys.path:
                sys.path.insert(0, _sd)
            from _train_tl_classifier import TLColorNet

            dev = "cuda" if torch.cuda.is_available() else "cpu"
            ck = torch.load(_MODEL_PATH, map_location=dev, weights_only=False)
            net = TLColorNet(len(ck["classes"])).to(dev)
            net.load_state_dict(ck["model_state"])
            net.eval()
            _net = net
            _classes = list(ck["classes"])
            _loaded_path = _MODEL_PATH      # ★记录实际加载的路径（供 /status 观测）
            return True
        except Exception:
            _load_failed = True
            return False


def classify_traffic_light(roi_bgr: np.ndarray,
                           min_conf: Optional[float] = None) -> Tuple[str, float]:
    """对红绿灯 ROI 判色

    Args:
        roi_bgr: BGR 裁剪图（建议含约 25% 扩边，保留灯壳上下文）
        min_conf: 置信度下限，低于则判为 unknown

    Returns:
        (state, confidence)
        state ∈ {"red","yellow","green","none","unknown"}
          - red/yellow/green: 对应灯色
          - none : 模型明确认为"这不是红绿灯"（应丢弃，不画框）
          - unknown: 模型不可用或置信度不足（调用方可回退 HSV）
    """
    if roi_bgr is None or roi_bgr.size == 0:
        return "unknown", 0.0
    h, w = roi_bgr.shape[:2]
    if h < 8 or w < 8:
        return "unknown", 0.0

    if not _ensure_loaded():
        return "unknown", 0.0

    try:
        im = cv2.resize(roi_bgr, (_IMG_SIZE, _IMG_SIZE), interpolation=cv2.INTER_AREA)
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        x = _torch.from_numpy(im.transpose(2, 0, 1).copy()).unsqueeze(0)
        dev = next(_net.parameters()).device
        x = x.to(dev)
        with _torch.no_grad():
            prob = _torch.softmax(_net(x), 1)[0]
        idx = int(prob.argmax())
        conf = float(prob[idx])
        state = _classes[idx]
        thr = _MIN_CONF if min_conf is None else float(min_conf)
        if conf < thr:
            return "unknown", conf
        return state, conf
    except Exception:
        return "unknown", 0.0


def hsv_fallback_state(roi_bgr: np.ndarray) -> str:
    """HSV 判色（回退路径）—— 与 annotation_renderer 原实现保持一致"""
    try:
        if roi_bgr is None or roi_bgr.size == 0:
            return "unknown"
        h, w = roi_bgr.shape[:2]
        if h < 4 or w < 4:
            return "unknown"
        hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
        masks = {
            "red": cv2.bitwise_or(cv2.inRange(hsv, (0, 70, 60), (10, 255, 255)),
                                  cv2.inRange(hsv, (170, 70, 60), (180, 255, 255))),
            "yellow": cv2.inRange(hsv, (15, 70, 70), (35, 255, 255)),
            "green": cv2.inRange(hsv, (40, 60, 60), (90, 255, 255)),
        }
        counts = {k: int(cv2.countNonZero(v)) for k, v in masks.items()}
        total = h * w
        best = max(counts, key=counts.get)
        if total > 0 and counts[best] >= max(6, int(total * 0.02)):
            return best
        return "unknown"
    except Exception:
        return "unknown"


def is_available() -> bool:
    """供外部探测 CNN 是否可用（用于状态展示）"""
    return _ensure_loaded()


# ======================================================================
# 发光区定位与判色（2026-10-04 由 DSH 新增）
#
# 背景（见 E:\output\_dual_cam_verdict.md / _tl_colour_verdict.md）：
#   1. CARLA 信号灯镜片物理直径仅约 **8.5 cm**（13 m 处约 12 px）——
#      靠"像素够多"判色不可行，必须靠"找到发光区再判色"。
#   2. CNN4 在真实素材上 93.2% 判色 / 99.6% 拒识（red 54/54）是最强组件；
#      但它吃的是 YOLO 框 +25% 扩边，框里常混入背景高光 -> 定位不准会拖坏它。
#   3. 因此本模块提供两件事：
#      ① find_glow_region()  精确定位点亮镜片（种子+生长，真值裁图上 97% 命中）
#      ② classify_with_glow() 用定位结果给 CNN **裁紧框**再判色（推荐路径）
#
# v2 相对 v1 的修复：v1 用"绝对亮度 + 局部对比"全局找最大连通域，会把
# 灯杆/天空高光当成发光区（真值裁图上命中率 0%）。v2 改为
# **先在 ROI 内取亮度峰值当种子，再按"峰值 × 比例"生长**，从根上避免跑到别处。
# ======================================================================

# 定位参数（已用 36 张机器校验真值的 CARLA 裁图调优）
_GLOW_GROW = float(os.environ.get("TL_GLOW_GROW", "0.70"))     # 生长阈值 = 峰值 × 此值
_GLOW_MIN_AREA = int(os.environ.get("TL_GLOW_MIN_AREA", "4"))
_GLOW_MIN_PEAK = float(os.environ.get("TL_GLOW_MIN_PEAK", "60"))
_GLOW_MIN_CONTRAST = float(os.environ.get("TL_GLOW_MIN_CONTRAST", "12"))

# 通道比判据（相对关系，不用死色域）
_G_REL_STRONG = float(os.environ.get("TL_G_REL_STRONG", "1.20"))
# ★ 发光区核心必须达到的通道跨度；过曝成白/灰时无颜色信息，直接交给 CNN
_RATIO_MIN_CHROMA = float(os.environ.get("TL_RATIO_MIN_CHROMA", "40"))


def find_glow_region(roi_bgr: np.ndarray):
    """在灯框内定位**点亮的镜片**（发光区）。

    算法（v2）：
      1. 3x3 均值平滑后取亮度峰值作为**种子**
      2. 要求峰值比本 ROI 中位数亮 `_GLOW_MIN_CONTRAST` 以上（否则视为无发光区）
      3. 在种子上按 `峰值 × _GLOW_GROW` 生长连通域，并做形态学合理性检查

    Returns:
        dict(cx, cy, w, h, area, peak, thr, mask) 或 None（没找到 -> 调用方返回 unknown）
    """
    try:
        if roi_bgr is None or roi_bgr.size == 0:
            return None
        g = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        h, w = g.shape
        if h < 4 or w < 4:
            return None
        seed_map = cv2.blur(g, (3, 3))
        med = float(np.median(g))
        py, px = np.unravel_index(int(np.argmax(seed_map)), g.shape)
        peak = float(seed_map[py, px])
        if peak < _GLOW_MIN_PEAK or (peak - med) < _GLOW_MIN_CONTRAST:
            return None
        sel = None
        for ratio in (_GLOW_GROW, 0.55, 0.40):
            thr = max(20.0, peak * ratio)
            m = (g >= thr).astype(np.uint8)
            n, lab = cv2.connectedComponents(m, 8)
            sid = lab[py, px]
            if sid == 0:
                continue
            cand = (lab == sid)
            if int(cand.sum()) >= _GLOW_MIN_AREA:
                sel = cand
                break
        if sel is None:
            return None
        ys, xs = np.nonzero(sel)
        bw = int(xs.max() - xs.min() + 1)
        bh = int(ys.max() - ys.min() + 1)
        if bw <= 0 or bh <= 0:
            return None
        if max(bw, bh) / max(1, min(bw, bh)) > 4.0:
            return None                      # 过扁/过长：不是镜片
        return {"cx": float(xs.mean()), "cy": float(ys.mean()), "w": bw, "h": bh,
                "area": int(sel.sum()), "peak": peak, "mask": sel}
    except Exception:
        return None


def crop_around_glow(roi_bgr: np.ndarray, glow, box_min: float = 42.0, pad: float = 0.25):
    """按定位结果裁出**符合 CNN4 训练分布**的子图。

    ★关键（踩过两次的坑）：CNN4 训练时吃的是"YOLO 框 + 25% 扩边"，
    所以喂给它的图必须是**大约 40~70 px 见方、镜片居中、四周留出灯壳**的裁图。
    早先两版都错在"按镜片尺寸缩放裁切"——镜片只有 8~13 px 时会裁出十几像素的
    小图，严重偏离训练分布，CNN 一律判 none。

    做法：以镜片中心为中心，取边长 = max(box_min, 镜片最长边 / (1-2*pad))，
    使其与 YOLO 框尺寸同量级；再整体扩边 pad。
    """
    try:
        h, w = roi_bgr.shape[:2]
        cx, cy = float(glow["cx"]), float(glow["cy"])
        lens = float(max(glow["w"], glow["h"]))
        side = max(box_min, lens / max(1e-6, 1.0 - 2.0 * pad))
        side = side * (1.0 + 2.0 * pad)
        half = side / 2.0
        x0 = int(round(cx - half))
        y0 = int(round(cy - half))
        x1 = int(round(cx + half))
        y1 = int(round(cy + half))
        # 越界时用复制边缘补齐（与训练时 copyMakeBorder 的做法一致）
        px0, py0 = max(0, -x0), max(0, -y0)
        px1, py1 = max(0, x1 - w), max(0, y1 - h)
        x0c, y0c = max(0, x0), max(0, y0)
        x1c, y1c = min(w, x1), min(h, y1)
        if x1c - x0c < 4 or y1c - y0c < 4:
            return None
        sub = roi_bgr[y0c:y1c, x0c:x1c]
        if px0 or py0 or px1 or py1:
            sub = cv2.copyMakeBorder(sub, py0, py1, px0, px1, cv2.BORDER_REPLICATE)
        if sub.shape[0] < 8 or sub.shape[1] < 8:
            return None
        return sub
    except Exception:
        return None


def _channel_ratio_state(roi_bgr: np.ndarray, glow) -> str:
    """按发光区的通道关系判色（不用色相，规避灯壳染色）。

    ★ 2026-10-04 实测修正：**必须先门控"发光区是否真的带色"**。
    在真实行车记录仪素材里，点亮的镜片/车灯常常**过曝到纯白**
    （实测红/绿/none 三类样本的发光区核心中位色都接近 (230,230,230)，
     G/B ≈ 1.00）——此时通道比没有任何颜色信息，
    若仍强行判色就一律输出"黄"，与 CNN 冲突并互相拖累（曾把整体从 100% 拖到 12.8%）。

    门控条件：发光区核心的**色度跨度** max-min 通道差 >= _RATIO_MIN_CHROMA。
    不满足 -> 返回 "unknown"（交给 CNN 决定），**不猜**。

    依据（CARLA 真值裁图实测的灯珠核心 BGR 中位值）：
        红珠 (211,  92,  44) -> 通道跨度 167，G/B≈0.44
        黄珠 (249, 245, 116) -> 通道跨度 133，G/B≈0.98
        绿珠 (106, 242,  83) -> 通道跨度 159，G/B≈2.3
    """
    try:
        m = glow["mask"]
        core = roi_bgr[m]
        if core.size < 3:
            return "unknown"
        cb, cg, cr = [float(core[:, i].mean()) for i in range(3)]
        chroma = max(cb, cg, cr) - min(cb, cg, cr)
        if chroma < _RATIO_MIN_CHROMA:
            return "unknown"          # 过曝成白/灰：没有颜色信息，不猜
        cb = max(cb, 1e-6)
        g_over_b = cg / cb
        b_over_r = cb / max(cr, 1e-6)

        if g_over_b >= _G_REL_STRONG and cg >= cr:
            return "green"
        if g_over_b >= 0.80:
            return "yellow"
        if b_over_r >= 1.6:
            return "red"
        if g_over_b < 0.80 and cr > cg:
            return "red"
        return "unknown"
    except Exception:
        return "unknown"


def classify_with_glow(roi_bgr: np.ndarray, use_cnn: bool = True,
                       min_conf: Optional[float] = None):
    """发光区**存在性校验** + CNN 判色（推荐路径）

    设计依据（2026-10-04 实测，377 张真实样本）：

      * CNN4 的最优输入是 **YOLO 框原样**（不加任何扩边）：
            原样    117/117 = 100% 判色 / 260/260 = 100% 拒识 / 0 假阳性
            扩边25% 109/117 =  93% / 259/260 = 100% / 1 假阳性
        被扩边害错的 9 例里有 8 例是"黄→红"，会误报闯红灯。
      * 但"框原样"也会把背景一起框进来（YOLO 框本身可能偏大），
        所以仍需一层**发光区存在性校验**：框里必须真的有一颗亮的紧凑镜片，
        否则判 `none`（不猜）—— 这是本函数的职责。

    实测（同 377 张）：本函数与 CNN4 单独使用结果一致（100% / 100%），
    因为发光区校验在真实样本上不误杀；但它能挡住"框内没有镜片"的误检。

    Returns:
        (state, confidence, info)
        state ∈ {"red","yellow","green","none","unknown"}
    """
    info = {"glow": None, "cnn": None, "cnn_conf": 0.0, "ratio": None,
            "source": None, "cropped": False}
    if roi_bgr is None or roi_bgr.size == 0:
        return "unknown", 0.0, info

    glow = find_glow_region(roi_bgr)
    if glow is None:
        # 框内没有亮的紧凑镜片 -> 不是交通灯，或灯没亮
        info["source"] = "no_glow"
        return "none", 0.0, info
    info["glow"] = {"cx": round(glow["cx"], 1), "cy": round(glow["cy"], 1),
                    "w": glow["w"], "h": glow["h"], "area": glow["area"],
                    "peak": round(glow["peak"], 1)}

    cnn_state, cnn_conf = ("unknown", 0.0)
    if use_cnn:
        # ★ 不裁切、不扩边：原样喂给 CNN4（实测此为最优输入）
        cnn_state, cnn_conf = classify_traffic_light(roi_bgr, min_conf=min_conf)
    info["cnn"], info["cnn_conf"] = cnn_state, round(float(cnn_conf), 3)

    ratio_state = _channel_ratio_state(roi_bgr, glow)
    info["ratio"] = ratio_state

    if cnn_state == "none":
        info["source"] = "cnn_none"
        return "none", cnn_conf, info
    if cnn_state != "unknown" and ratio_state == cnn_state:
        info["source"] = "agree"
        return cnn_state, cnn_conf, info
    if cnn_state != "unknown" and ratio_state == "unknown":
        info["source"] = "cnn_only"
        return cnn_state, cnn_conf, info
    if cnn_state == "unknown" and ratio_state != "unknown":
        info["source"] = "ratio_only"
        return ratio_state, 0.0, info
    info["source"] = "conflict"
    return "unknown", 0.0, info
