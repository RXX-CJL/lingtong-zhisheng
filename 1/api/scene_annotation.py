# -*- coding: utf-8 -*-
"""场景标注（Scene Annotation）—— 人工描绘 / AI 自动检测

背景（2026-10-03 由 DSH 实现，融合参考项目"运行前人工标注"的思路）：
  实测 COCO 模型**不输出**斑马线/车道线等交通设施类（`CROSSWALK_CLASSES`
  永远 0 检出），导致"斑马线违停""压线"等规则形同虚设。
  参考项目的做法是**运行前人工标注**场景要素 —— 可靠且立刻生效。

两种模式：
  1. **人工描绘**（manual）：管理员在视频首帧上用鼠标点若干角点
                            - 斑马线：点击 4 个角点 -> 四边形
                            - 车道线：点击 2 点 -> 线段（从上到下）
                            - 停止线：点击 2 点，取其 y 作为 stop_line_y
  2. **AI 描绘**（auto）：用图像处理自动给出建议（斑马线 = 高对比等间距横纹区域）
                          结果作为**建议**返回，需人工确认后才保存

存储：`api/output/scene_configs/{video_key}.json`
  video_key = 视频文件名（不含扩展名）的 sha1 前 12 位；摄像头流用 URL 的哈希。
  这样"导入视频"与"接入摄像头"都能各自持久化一套标注。
"""

import hashlib
import json
import os
import re
import time
from typing import Dict, List, Optional

import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCENE_DIR = os.path.join(BASE_DIR, "output", "scene_configs")
os.makedirs(SCENE_DIR, exist_ok=True)

# 允许的标注字段（白名单，避免脏数据写库）
# 2026-10-03 由 DSH 扩充：加入**速度标定参数**，否则人工标定的
# pixel_per_meter / ppm_ref_y 等会被静默丢弃，导致车速永远走 "assumed" 粗估。
_ALLOWED_KEYS = ("crosswalk_zones", "lane_lines", "stop_line_y",
                 "no_parking_zones", "road_direction", "speed_limit",
                 "pixel_per_meter", "is_no_parking_zone",
                 # --- 速度标定（speed_calibration.py 使用）---
                 "ppm_ref_y",            # 参考 y（该 y 处 ppm 有效）
                 "lane_width_px",        # 车道像素宽（配合国标 3.75m）
                 "lane_ref_y",           # 车道宽测量处的 y
                 "crosswalk_width_m",    # 斑马线实际宽度（默认 3.0m）
                 "y_horizon_ratio",      # 地平线位置（占画面高比例，默认 0.30）
                 "frame_width", "frame_height",
                 # --- 区域标注（2026-10-04 由 DSH 新增，用户明确要求）---
                 # 用户原话："导入视频时最关键的斑马线，公路，人行道，
                 #           可停车，不可停车……最好需要人工手绘"
                 "road_zones",           # 公路区域（多边形列表）
                 "sidewalk_zones",       # 人行道区域
                 "parking_zones",        # 可停车区域
                 # --- 相机几何（2026-10-04 由 DSH 新增，测速准确的前提）---
                 # 实测证明：几何标定必须知道相机真实参数；缺省值不匹配时
                 # 测速偏 2.4 倍，远处甚至算出 158 km/h 的荒谬值。
                 # ★2026-10-06 更正：那条"2.4 倍/158km/h"的实测是拿一份
                 #   损坏的 reference CSV 得出的（详见 speed_calibration.py 头部），
                 #   但"必须知道真实参数"这个结论**依然成立** —— 真机位实测：
                 #   默认值(h=8/pitch=-20)对真实机位的反解 RMS 达 94 m。
                 "camera_height_m",      # 相机**离路面**高度（米）
                 "camera_pitch_deg",     # 俯角（向下为负）
                 "fov_deg",              # **水平**视场角
                 "camera_yaw_deg",       # 偏航角（度，CARLA 约定）
                 "camera_world_x",       # 可选：相机世界 x（仅多机位对齐用）
                 "camera_world_y",       # 可选：相机世界 y
                 # --- 人工点选标定（2026-10-06 由 DSH 新增）---
                 # [{'u':像素x,'v':像素y,'x':地面米,'y':地面米} × ≥4]
                 # 连相机参数都不知道时用；与相机参数同时给出会**自动交叉校核**。
                 "ground_points",
                 # --- 车道级灯态 ROI（2026-10-06 由 DSH 新增）---
                 # [[x1,y1,x2,y2], ...]：**控制被拍方向**的那盏（几盏）信号灯
                 # 在画面上的区域。闯红灯判定只认 ROI 内的灯态。
                 # 不标的后果（实测）：画面里任意一盏红灯（含横向车道、CAM-2 小窗）
                 # 都会被当成"本方向红灯" -> 演示视频每循环误报 5~6 次。
                 "traffic_light_roi",
                 # --- 来源标识（2026-11-05 由 DSH 新增）---
                 # 为什么必须加进白名单：save_scene 会无条件写入 `_source`（视频路径/流URL），
                 # 但 load_scene 只保留本白名单内的键 → 运行时读回的 scene_config 里
                 # **永远没有 `_source`**。后果（实测）：证据链 location 一直为空，
                 # 因为没有任何"这是哪个点位"的可追溯标识。
                 # 只读元数据，前端不写它，加进白名单安全。
                 "_source")


def video_key(source: str) -> str:
    """把视频路径/流 URL 归一化成稳定的存储键"""
    if not source:
        return "default"
    s = str(source).strip()
    base = os.path.basename(s.split("?")[0]) or s
    base = re.sub(r"[^\w\u4e00-\u9fa5\.\-]", "_", base)
    h = hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()[:12]
    stem = os.path.splitext(base)[0][:40] or "src"
    return f"{stem}_{h}"


def _path_for(source: str) -> str:
    return os.path.join(SCENE_DIR, f"{video_key(source)}.json")


def _stem_prefix(source: str) -> str:
    """`video_key` 里"文件名主干前 40 字符 + 下划线"那一部分（供 /api/scene/copy 用）"""
    s = str(source or "").strip()
    base = os.path.basename(s.split("?")[0]) or s
    base = re.sub(r"[^\w\u4e00-\u9fa5\.\-]", "_", base)
    return (os.path.splitext(base)[0][:40] or "src") + "_"


def load_scene(source: str) -> Dict:
    """读取标注（不存在则返回空配置）

    ⚠ 2026-10-10 记录一次**做了一半又撤回**的尝试（避免后人重走）：
      因为 `video_key` 是**整条源路径的 sha1**，同一段录像的**不同编码/容器**
      （`..._lossless.mkv` vs `..._h264.mp4`）是两个键 —— 换素材会让人工标定
      （信号灯 ROI / 停止线 / 相机几何）**静默失效**（界面只表现为 `scope=frame`，
      而灯态一失效，闯红灯就退化成"画面里任意一盏灯"，每循环误报 5~7 次）。
      我一度想在这里做"**同文件名主干兜底匹配**"，但实测不成立：
      `dual_cam_demo_h264_` 与现有文件的 `dual_cam_demo_lossless_` 前缀并不相同，
      要让它命中就得放宽到 `dual_cam_demo_` —— 那会把**同目录里所有视频**混成一个标注，
      风险大于收益。**故撤回，改为显式动作**：需要共用标注时调用
      `E:\output\_scripts\_copy_scene_config.py <旧源> <新源>`（它在两个键之间复制 JSON，
      不删不改原文件）。这样"共用"是**看得见的一步**，而不是一条隐式规则。
    """
    p = _path_for(source)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_scene(source: str, config: Dict, annotated_by: str = "manual",
               merge: bool = True) -> Dict:
    """保存标注（只保留白名单字段；写入来源与时间）

    2026-10-03 由 DSH 修复：默认改为**合并**语义（merge=True）。
    原实现整份替换，导致"只画一个斑马线"会把此前人工标定的
    pixel_per_meter / lane_width_px / stop_line_y 等**静默清空**
    （实测：前端标注演示后标定参数全丢）。传 merge=False 可强制替换。
    """
    clean = {}
    if merge:
        existing = load_scene(source)
        for k in _ALLOWED_KEYS:
            if k in existing:
                clean[k] = existing[k]
    for k in _ALLOWED_KEYS:
        if k in (config or {}) and config[k] is not None:
            clean[k] = config[k]
    # 显式置 None 表示"清除该字段"（前端可用来删除）
    for k in _ALLOWED_KEYS:
        if k in (config or {}) and config[k] is None and k in clean:
            clean.pop(k, None)
    clean["_source"] = str(source)
    clean["annotated_by"] = annotated_by
    clean["annotated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    p = _path_for(source)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    return clean


def list_scenes() -> List[Dict]:
    """列出所有已保存的标注（供管理端查看/清理）"""
    out = []
    for fn in sorted(os.listdir(SCENE_DIR)):
        if not fn.endswith(".json"):
            continue
        p = os.path.join(SCENE_DIR, fn)
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            out.append({
                "key": fn[:-5],
                "source": d.get("_source"),
                "annotated_by": d.get("annotated_by"),
                "annotated_at": d.get("annotated_at"),
                "has_crosswalk": bool(d.get("crosswalk_zones")),
                "has_lane_lines": bool(d.get("lane_lines")),
                "stop_line_y": d.get("stop_line_y"),
            })
        except Exception:
            continue
    return out


# ---------------------------------------------------------------------------
# AI 自动检测：斑马线
# 原理（参考项目思路的简化版）：
#   斑马线特征 = 高对比 + 等间距 + 多根横向条纹，集中在画面下半部（路面）
#   实现：灰度 -> 自适应阈值 -> 形态学 -> 找轮廓 -> 按"宽扁 + 条纹密度"筛选
# 说明：这是**启发式**方法，输出作为"建议"供人工确认，不直接当作真值。
# ---------------------------------------------------------------------------
def auto_detect_crosswalk(frame: np.ndarray, max_zones: int = 3) -> List[List[List[int]]]:
    """自动检测斑马线，返回候选四边形列表 [[[x,y]x4], ...]

    2026-10-03 由 DSH 收紧（原版过检严重：把整个下半屏当候选）：
      新增约束 —— ① 宽度上限（不得超过画面宽 60%）
                  ② 高度范围（斑马线是"宽扁带"，8~18% 画面高）
                  ③ 等间距条纹检测（斑马线的强特征：亮暗交替周期稳定）
                  ④ 不贴画面边缘（左右各留 3%）
      仍属启发式，输出**仅作建议**，必须人工确认。
    """
    if frame is None or frame.size == 0:
        return []
    try:
        H, W = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        roi_y0 = int(H * 0.45)
        roi = gray[roi_y0:, :]
        th = cv2.adaptiveThreshold(roi, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, 31, -8)
        k1 = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 7))
        th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, k1, iterations=2)
        th = cv2.morphologyEx(th, cv2.MORPH_OPEN,
                              cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3)))
        cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 约束参数
        max_w = W * 0.60
        min_w = W * 0.10
        min_h = H * 0.05
        max_h = H * 0.22
        edge_margin = W * 0.03

        cands = []
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            # ① 尺寸约束
            if w < min_w or w > max_w or h < min_h or h > max_h:
                continue
            if w / max(1, h) < 2.0:          # 宽扁
                continue
            # ④ 不贴边
            if x < edge_margin or (x + w) > (W - edge_margin):
                continue
            if cv2.contourArea(c) < 1200:
                continue
            # ③ 等间距条纹：统计列投影的亮暗交替周期稳定性
            patch = th[y:y + h, x:x + w]
            colsum = patch.mean(axis=0)
            binary = (colsum > 127).astype(np.int8)
            flips = np.abs(np.diff(binary))
            n_flip = int(flips.sum())
            if n_flip < 6:                    # 至少 6 次交替（约 3 条白线）
                continue
            # 条纹间距一致性：交替位置差分的标准差越小越像斑马线
            pos = np.flatnonzero(flips)
            if len(pos) >= 3:
                gaps = np.diff(pos)
                mean_gap = float(gaps.mean()) if len(gaps) else 0.0
                std_gap = float(gaps.std()) if len(gaps) else 999.0
                # 变异系数 > 0.75 视为间距不规律（路面纹理/阴影而非斑马线）
                if mean_gap <= 0 or (std_gap / mean_gap) > 0.75:
                    continue
            cands.append((n_flip, cv2.contourArea(c), x, y + roi_y0, w, h))

        # 按"交替次数多 + 面积大"排序
        cands.sort(key=lambda t: (-t[0], -t[1]))
        return [[[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
                for _f, _a, x, y, w, h in cands[:max_zones]]
    except Exception:
        return []


def auto_detect_stop_line(frame: np.ndarray) -> Optional[int]:
    """自动估计停止线 y 坐标（返回建议值，供人工确认）

    做法：在路面区域找"最长的水平白线"。
    """
    if frame is None or frame.size == 0:
        return None
    try:
        H, W = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        roi = gray[int(H * 0.35):, :]
        edges = cv2.Canny(roi, 60, 160)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=90,
                                minLineLength=int(W * 0.25), maxLineGap=12)
        if lines is None:
            return None
        best_y, best_len = None, 0
        for l in lines[:, 0]:
            x1, y1, x2, y2 = int(l[0]), int(l[1]), int(l[2]), int(l[3])
            if abs(y2 - y1) > 6:              # 只要近水平的线
                continue
            ln = abs(x2 - x1)
            if ln > best_len:
                best_len = ln
                best_y = int((y1 + y2) / 2) + int(H * 0.35)
        return best_y
    except Exception:
        return None


def auto_detect_all(frame: np.ndarray) -> Dict:
    """一次性给出所有可自动检测的建议（供前端弹出标注对话框时预填）"""
    return {
        "crosswalk_zones": auto_detect_crosswalk(frame),
        "stop_line_y": auto_detect_stop_line(frame),
        "detected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": "AI 建议仅供参考，请人工确认后再保存",
    }
