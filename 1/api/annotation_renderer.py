# -*- coding: utf-8 -*-
"""中文标注渲染器 —— 统一的"画框 + 中文标签"实现

设计目标（2026-10-02 由 DSH 实现，用户需求）：
  1. 车辆框：违规 → 红框 + 违规类型；正常 → 绿框（不显示违规类型）
  2. 左上角标签：ID / 速度 / 车牌 / 违规类型（全中文）
  3. 红绿灯框：按颜色着色 + 标注"红灯/黄灯/绿灯"
  4. 中文渲染：cv2.putText 不支持中文，改用 PIL + TTF
  5. 性能：字体对象 / 颜色 / 尺寸全部缓存，避免每帧重建

为什么不用 cv2.putText 画中文：
  OpenCV 的 Hershey 字体只有 ASCII，中文会渲染成 "???"。
  项目原实现里的 cv2.putText(frame, "逆行", ...) 实际上画不出任何可见文字。
"""

import os
import threading
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# 字体解析（按优先级找可用的中文字体；找不到时降级为英文标签）
# ---------------------------------------------------------------------------
_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",     # 微软雅黑 Bold
    r"C:\Windows\Fonts\msyh.ttc",       # 微软雅黑
    r"C:\Windows\Fonts\simhei.ttf",     # 黑体
    r"C:\Windows\Fonts\simsun.ttc",     # 宋体
    r"E:\output\1\K230\00.开发板资料\字体\OPPO Sans 4.0.ttf",
]

_font_cache: Dict[int, ImageFont.FreeTypeFont] = {}
_font_path: Optional[str] = None
_font_lock = threading.Lock()

# ★★2026-10-09 由 DSH 新增：**绘制侧关联统计**（让"每辆车几个框"可被外部观测）
#
# 为什么必须可观测（本项目血泪教训 T75）：
#   "每辆车两个框"这个 bug 的真身是"detection 关联不到 track -> 主循环画车型标签
#   且不登记 drawn_tracks -> 兜底循环又画一次"。它**不报错、不写日志**，
#   只能靠人眼看画面发现（用户就是这么发现的）。
#   现在把每帧的关联结果记在这里，由 `/status` 的 `box_draw_stats` 暴露：
#     · unmatched_dets 持续 > 0  -> 有关联不上的检测（可能就是"多出来的框"）
#     · fallback_boxes > 0       -> 兜底循环在补画（漏检正常，异常增多要查）
#     · max_dets_per_track > 1   -> **一个 track 被多条 detection 占用**（会画重框）
#   以后再有同类回归，看这三个数即可，不必再靠肉眼。
_BOX_STATS: Dict[str, Any] = {
    'frames': 0, 'main_boxes': 0, 'fallback_boxes': 0, 'unmatched_dets': 0,
    'max_dets_per_track': 0, 'tracks_drawn': 0, 'multi_hit_tracks': 0,
    'last_update': None,
}
_BOX_STATS_LOCK = threading.Lock()


def get_box_draw_stats() -> Dict[str, Any]:
    """读取绘制侧关联统计（供 /status 暴露；返回副本，调用方改不到内部状态）"""
    with _BOX_STATS_LOCK:
        return dict(_BOX_STATS)


def _resolve_font_path() -> Optional[str]:
    global _font_path
    if _font_path is None:
        for p in _FONT_CANDIDATES:
            if os.path.exists(p):
                _font_path = p
                break
        else:
            _font_path = ""
    return _font_path or None


def get_font(size: int = 18) -> Optional[ImageFont.FreeTypeFont]:
    """按字号取字体对象（带缓存；同一字号只创建一次）"""
    with _font_lock:
        if size in _font_cache:
            return _font_cache[size]
        path = _resolve_font_path()
        if not path:
            return None
        try:
            f = ImageFont.truetype(path, size)
        except Exception:
            return None
        _font_cache[size] = f
        return f


# 颜色（BGR，与 OpenCV 一致）
COLOR_NORMAL = (80, 220, 80)        # 正常：绿
COLOR_VIOLATION = (60, 60, 235)     # 违规：红
# ★2026-10-09 由 DSH 新增：**还没拿到追踪 ID 的检测框 = 灰**
#
# 用户原话："没有ID要不直接用灰色框就行了（刚好和正常行驶的绿框和违规行驶的红框
# 分开来），什么都不用显示"。
# 起因：用户先反馈"有时候显示 ID、有时候显示车辆类别，我还以为是两个框重叠了"。
# 真相是——跟踪器刚建立/刚丢失的那一两帧里，detection 关联不到 track，
# 旧代码就把**原始类名（car/truck）**当标签画上去；而正常帧画的是 `IDxx`。
# 用户看到同一辆车一会儿 "car" 一会儿 "ID18"，视觉上像两个不同的标注。
# 现在三色分工一眼可辨：
#   绿框 = 已追踪 + 无违规   /   红框 = 已追踪 + 违规   /   灰框 = 尚未追踪（无文字）
COLOR_UNKNOWN = (150, 150, 150)     # 未追踪：灰（无标签）
COLOR_VIOLATION_ALERT = (60, 60, 235)   # 违规文字色（等同违规红，语义上区分用途）
COLOR_TEXT_BG = (40, 40, 40)        # 标签底色（2026-10-04 起默认不启用）
COLOR_TEXT_FG = (255, 255, 255)     # 标签文字
COLOR_TEXT_STROKE = (15, 15, 15)    # 文字描边色（替代色块保证可读性，2026-10-04 新增）
COLOR_ARROW = (240, 200, 60)        # 方向箭头（青蓝，与红绿框区分）

# ★★2026-10-09 由 DSH 新增：**红绿灯类名集合（唯一权威版本）**
#
# 为什么要有这个常量（真实 bug，2026-10-09 定位）：
#   绘制侧原先把"是不是红绿灯"硬编码成两个名字：
#       if cls in ("traffic light", "traffic_light", "red_light",
#                  "green_light", "yellow_light"): continue
#   而**同一个仓里的检测侧**（realtime_detector._collect_traffic_lights，
#   :2162）用的是另一套：带下划线、**还多了裸色名** red/green/yellow。
#   两套名单不一致的后果（只要上游吐 COCO 原生的带空格写法 "traffic light"，
#   而它正是实际输出）：
#     · 红绿灯**掉不进** `continue` -> 被当成普通目标画成默认灰框 + 英文
#       "traffic light" 标签（不是按灯色着色的彩色框）；
#     · 判色得到的 red/green/yellow **裸色名**同样漏网。
#   -> 用户看到的"标注重叠/颜色不对"，根因就在这里（并会让灯色配色失效）。
# 现值 = 检测侧名单 ∪ 渲染侧旧名单 ∪ 规则引擎的红/黄/绿灯三组
#   （violation_rules.py 的 TRAFFIC_SIGNAL_CLASSES / *_LIGHT_CLASSES）。
_HEX_LIGHT_ALIASES = ("traffic_light_red", "traffic_light_green", "traffic_light_yellow")
TRAFFIC_LIGHT_CLASS_NAMES = frozenset(
    ("traffic light", "traffic_light", "red_light", "green_light", "yellow_light",
     "red", "green", "yellow") + _HEX_LIGHT_ALIASES)


def _direction_vector(veh, tracked_history=None):
    """推导车辆行进方向（单位向量，图像坐标系：x 向右、y 向下）

    优先级（2026-10-03 由 DSH 实现）：
      ① 轨迹历史：用最近若干个 center 点做线性拟合（比首尾两点抗抖动）
      ② tracker 给出的 direction 字段（中文/英文枚举）
    返回 None 表示无法判定（车辆静止或历史不足）。
    """
    hist = (veh or {}).get("history") or tracked_history
    if isinstance(hist, (list, tuple)) and len(hist) >= 2:
        pts = []
        for h in hist[-8:]:
            if isinstance(h, dict) and h.get("center"):
                try:
                    pts.append((float(h["center"][0]), float(h["center"][1])))
                except (TypeError, ValueError, IndexError):
                    continue
        if len(pts) >= 2:
            # 先判"是否真的在动"：总位移过小则视为静止，不画箭头
            span_x = max(p[0] for p in pts) - min(p[0] for p in pts)
            span_y = max(p[1] for p in pts) - min(p[1] for p in pts)
            if (span_x * span_x + span_y * span_y) ** 0.5 < 6.0:
                return None
            # 方向 = 首尾位移（直观、与 tracker 的 direction 语义一致）
            # 修正记录（2026-10-03）：上一版用"协方差主轴 + 符号"推导，
            # 当轨迹近圆形/斜向时 sxx≈syy，会错误地输出水平向量
            # （实测 tracker 报 down，却输出 (-1.0,0)）。首尾位移无此问题。
            sx = pts[-1][0] - pts[0][0]
            sy = pts[-1][1] - pts[0][1]
            # 若首尾位移过小（可能首尾恰好在同一位置），退化用最大位移对
            if (sx * sx + sy * sy) ** 0.5 < 3.0:
                far = max(pts, key=lambda p: (p[0] - pts[0][0]) ** 2 + (p[1] - pts[0][1]) ** 2)
                sx = far[0] - pts[0][0]
                sy = far[1] - pts[0][1]
            norm = (sx * sx + sy * sy) ** 0.5
            if norm > 1e-6:
                return (sx / norm, sy / norm)

    d = (veh or {}).get("direction")
    if isinstance(d, str) and d and d.lower() != "unknown":
        m = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0),
             "向上": (0, -1), "向下": (0, 1), "向左": (-1, 0), "向右": (1, 0),
             "stationary": None, "静止": None}
        v = m.get(d.lower()) or m.get(d)
        if v:
            return v
    return None

# 红绿灯颜色（BGR）
LIGHT_COLORS = {
    "red": (60, 60, 235),
    "yellow": (60, 200, 240),
    "green": (80, 220, 80),
    "unknown": (170, 170, 170),
}
LIGHT_CN = {"red": "红灯", "yellow": "黄灯", "green": "绿灯", "unknown": "信号灯"}


def _bgr_of(t: Tuple[int, int, int]):
    """PIL 用 RGB，OpenCV 用 BGR，此处统一转换"""
    return (int(t[2]), int(t[1]), int(t[0]))


class AnnotationRenderer:
    """画框 + 中文标注渲染器（线程安全、字体缓存）

    用法：
        r = AnnotationRenderer()
        frame = r.render(frame, detections, tracked_vehicles, violations, traffic_light)
    """

    def __init__(self, font_size: int = 18, line_thickness: int = 2,
                 box_alpha: float = 0.0):
        self.font_size = font_size
        self.line_thickness = line_thickness
        self.box_alpha = box_alpha
        self.mode = os.environ.get('ANNOTATION_MODE', 'minimal')
        # 极简档线条收细（2026-10-04 由 DSH 新增）：减少遮挡
        self.thin_thickness = max(1, int(line_thickness) - 1)
        self._font = get_font(font_size)
        self._small_font_size = max(11, font_size - 5)
        self._small_font = get_font(self._small_font_size)
        # 统计：便于外部观测渲染耗时
        self.last_render_ms = 0.0
        self.rendered_frames = 0

    # ------------------------------------------------------------------
    # 中文文本绘制（PIL 往返一次，批量绘制所有文本以减少转换次数）
    # ------------------------------------------------------------------
    def draw_texts(self, frame: np.ndarray, items) -> np.ndarray:
        """items: List[(text, x, y, color_bgr, bg_bgr|None, font_size)]

        一次性把所有文本画到同一张 PIL 图上，避免每段文字都做
        BGR<->RGB 与 ndarray<->Image 的往返（性能关键）。

        2026-10-04 由 DSH 修改 —— **默认不再画文字底色**：
          原来把 bbox 的框色当作底色画成实心矩形（绿框配绿底、红框配红底），
          一块块实心色块在多车场景下非常挡视野（用户反馈"这才是最挡的"）。
          现在改为「无底色 + 深色描边」：靠 stroke 保证在任何背景上都可读，
          同时不再遮挡画面内容。
          如需恢复旧观感，设置环境变量 ANNOTATION_TEXT_BG=1。
        """
        if not items:
            return frame
        _want_bg = str(os.environ.get("ANNOTATION_TEXT_BG", "0")).strip().lower() \
            in ("1", "true", "yes", "on")
        if self._font is None:
            # 无中文字体：降级用 cv2 画 ASCII（至少不丢信息）
            for text, x, y, color, bg, _sz in items:
                # 先用深色描粗一遍做描边，再用本色写一遍
                cv2.putText(frame, text, (int(x), int(y)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 20, 20), 3, cv2.LINE_AA)
                cv2.putText(frame, text, (int(x), int(y)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
            return frame

        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img)
        for text, x, y, color, bg, size in items:
            font = get_font(size) or self._font
            # 文本基线：y 视为文本顶部
            try:
                l, t, r, b = draw.textbbox((0, 0), text, font=font)
                tw, th = r - l, b - t
            except Exception:
                tw, th = len(text) * size // 2, size
            x, y = int(x), int(y)
            # 仅当显式开启时才画底色（默认关闭，见上方说明）
            if _want_bg and bg is not None:
                pad = 3
                draw.rectangle([x - pad, y - pad, x + tw + pad, y + th + pad],
                               fill=_bgr_of(bg))
            # 深色描边 + 本色文字：无底色也可读
            try:
                draw.text((x, y), text, font=font, fill=_bgr_of(color),
                          stroke_width=max(2, size // 8),
                          stroke_fill=_bgr_of(COLOR_TEXT_STROKE))
            except TypeError:
                # 极老版本 PIL 不支持 stroke_*，退回无描边
                draw.text((x, y), text, font=font, fill=_bgr_of(color))
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # ------------------------------------------------------------------
    # 主渲染入口
    # ------------------------------------------------------------------
    def _draw_direction_arrow(self, frame, bbox, veh, is_violation,
                              mode: str = "minimal", unknown: bool = False):
        """画行进方向箭头（2026-10-04 由 DSH 抽成方法）

        为什么抽出来：原先箭头代码只写在**兜底循环**（遍历 tracked_vehicles）里，
        而实际车辆是被**主循环**（遍历 detections）画的，兜底循环遇到已画过的
        车辆会 continue -> **箭头实际上很少被画出来**。
        抽成方法后两个循环都能调用，彻底消除这个盲区。

        ★2026-10-09：新增 `unknown`（该 detection 还没关联到 track）。
        灰框表示"尚未追踪"，此时 `veh` 是空 dict，画方向箭头只会给出**无依据的
        方向暗示**；且用户明确说灰框"什么都不用显示" -> 直接不画。
        """
        try:
            if unknown:
                return
            x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
            cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            vec = _direction_vector(veh, tracked_history=None)
            if vec is None:
                return
            dx, dy = vec
            bw, bh = max(1.0, x2 - x1), max(1.0, y2 - y1)
            if mode == "minimal":
                L = max(22.0, min(64.0, max(bw, bh) * 0.38))
                thick, white_pad = 3, 2
            else:
                L = max(34.0, min(110.0, max(bw, bh) * 0.55))
                thick = 5 if is_violation else 4
                white_pad = 3
            ex, ey = cx + dx * L, cy + dy * L
            wrong = bool(is_violation or veh.get("is_wrong_way"))
            # ★2026-10-09：箭头颜色与框色保持同一套语义
            #   红框(违规/逆行告警) -> 红箭头 / 绿框(正常) -> 琥珀箭头 / 灰框 -> 不画
            arrow_color = COLOR_VIOLATION if wrong else COLOR_ARROW
            if wrong and mode == "minimal":
                thick = 4          # 逆行仍加粗一档（告警不能弱化）
            cv2.arrowedLine(frame, (int(cx), int(cy)), (int(ex), int(ey)),
                            (255, 255, 255), thick + white_pad, tipLength=0.34)
            cv2.arrowedLine(frame, (int(cx), int(cy)), (int(ex), int(ey)),
                            arrow_color, thick, tipLength=0.34)
        except Exception:
            pass

    def render(self, frame: np.ndarray,
               detections=None,
               tracked_vehicles: Optional[Dict] = None,
               violations=None,
               traffic_lights=None,
               plate_of_track: Optional[Dict] = None) -> np.ndarray:
        """在帧上绘制所有标注

        Args:
            frame: BGR ndarray
            detections: YOLO 检测列表 [{'bbox','class_name','confidence'}, ...]
            tracked_vehicles: {track_id: {'id','bbox','class_name','speed',
                                          'direction','is_wrong_way',...}}
            violations: 违规列表 [{'violation_type','violation_type_cn',
                                   'vehicle_id'/'track_id','confidence'}, ...]
            traffic_lights: [{'bbox','color','countdown'}, ...] 或 [{'bbox','state'}]
            plate_of_track: {track_id: '粤B12345'} 车牌缓存（异步填充）

        Returns:
            绘制后的帧（原地修改并返回）
        """
        import time as _t
        t0 = _t.perf_counter()
        if frame is None:
            return frame
        tracked_vehicles = tracked_vehicles or {}
        detections = detections or []
        violations = violations or []
        traffic_lights = traffic_lights or []
        plate_of_track = plate_of_track or {}

        # 违规车辆集合：track_id -> 中文违规类型
        # 映射策略（2026-10-02 由 DSH 实现）：违规对象来自两条链路，字段形态不同——
        #   - 行为引擎：带 vehicle_id（= track_id）            -> 直接可用
        #   - 规则引擎：只有 evidence / location（无 track_id） -> 需按 bbox/点位归属推断
        # 因此这里做多来源取值 + 空间匹配，避免"红框永不出现"。
        viol_by_track: Dict[int, str] = {}
        _unmatched = []          # 无 ID 的违规，稍后按空间匹配
        for v in violations:
            cn = v.get("violation_type_cn") or v.get("violation_type") or "违规"
            tid = None
            for src in (v, v.get("evidence") or {}, v.get("location") or {}):
                if not isinstance(src, dict):
                    continue
                for key in ("track_id", "vehicle_id", "id", "object_id"):
                    raw = src.get(key)
                    if raw is None or isinstance(raw, bool):
                        continue
                    try:
                        tid = int(float(raw))
                        break
                    except (TypeError, ValueError):
                        # 形如 "car_3" 的字符串：取尾部数字
                        import re as _re2
                        m = _re2.search(r"(\d+)\s*$", str(raw))
                        if m:
                            tid = int(m.group(1))
                            break
                if tid is not None:
                    break
            if tid is not None:
                viol_by_track[tid] = cn
            else:
                _unmatched.append((v, cn))

        # 追踪车辆的空间索引，用于给"无 ID 违规"找归属
        # ★2026-10-09 由 DSH 收敛：不再自己重新遍历一遍，改用 _build_track_index()
        # （同一个 render() 里原本有两处几乎相同的索引构建代码，容易改一处漏一处）
        _by_id_i, _by_bbox_i, track_boxes = _build_track_index(tracked_vehicles)

        def _find_track_by_bbox(bb):
            """按 IoU 找最匹配的车辆（阈值 0.3）"""
            if not bb or len(bb) < 4:
                return None
            ax1, ay1, ax2, ay2 = [float(x) for x in bb[:4]]
            a_area = max(1.0, (ax2 - ax1) * (ay2 - ay1))
            best, best_iou = None, 0.0
            for tid_i, tb in track_boxes:
                if tid_i is None:
                    continue
                ix1, iy1 = max(ax1, tb[0]), max(ay1, tb[1])
                ix2, iy2 = min(ax2, tb[2]), min(ay2, tb[3])
                if ix2 <= ix1 or iy2 <= iy1:
                    continue
                inter = (ix2 - ix1) * (iy2 - iy1)
                b_area = max(1.0, (tb[2] - tb[0]) * (tb[3] - tb[1]))
                iou = inter / (a_area + b_area - inter)
                if iou > best_iou:
                    best, best_iou = tid_i, iou
            return best if best_iou >= 0.3 else None

        def _find_track_by_point(pt):
            """按点位落在哪个车辆框内找归属"""
            if not isinstance(pt, dict):
                return None
            try:
                px, py = float(pt.get("x")), float(pt.get("y"))
            except (TypeError, ValueError):
                return None
            for tid_i, tb in track_boxes:
                if tid_i is not None and tb[0] <= px <= tb[2] and tb[1] <= py <= tb[3]:
                    return tid_i
            return None

        for v, cn in _unmatched:
            tid = None
            for src in (v, v.get("evidence") or {}, v.get("location") or {}):
                if isinstance(src, dict) and isinstance(src.get("bbox"), (list, tuple)) \
                        and len(src["bbox"]) >= 4:
                    tid = _find_track_by_bbox(src["bbox"])
                    if tid is not None:
                        break
            if tid is None:
                loc = v.get("location")
                tid = _find_track_by_point(loc) if isinstance(loc, dict) else None
            if tid is not None:
                viol_by_track[tid] = cn
            elif len(_unmatched) == len(violations) and len(track_boxes) == 1:
                # 退化场景：全场只有一辆车且只有一类违规 -> 归属给它（避免完全不可见）
                viol_by_track[track_boxes[0][0]] = cn

        # 建立 detection -> track 的索引（兼容 detections 与 tracked_vehicles 分开传入）
        #
        # ★★2026-10-09 由 DSH 修正（"每辆车两个框"的根治点，设计单 §12.3 方案 B）
        # 旧实现是 **bbox 精确匹配**：
        #     bbox_to_track[tuple(int(x) for x in bb[:4])] = veh
        # 而框位置预测会把 tracked_vehicles 的框平移成带小数的值 -> 取整后**不再等于**
        # detection 的框 -> 主循环查不到 -> 画车型标签且不登记 drawn_tracks ->
        # 兜底循环又画一次带 ID 的 -> **一个 ID 框 + 一个车型框**（用户实测现象）。
        # 现改为"先按 track_id，再按空间"的多级关联，且**一个 track 只被一条 detection 占用**。
        # 兼容方式保留：`bbox_to_track` 这个名字继续存在（精确匹配命中时行为与旧版一致），
        # 兜底循环里 `if tid_i in drawn_tracks: continue` 依赖 drawn_tracks，故必须正确登记。
        _by_id, bbox_to_track, _boxed = _build_track_index(tracked_vehicles)
        _used_ids = set()
        _assoc_stats = {'by_id': 0, 'by_bbox': 0, 'by_space': 0, 'none': 0}
        # 每个 track 被几条 detection 关联上（>1 就是"会画重框"的信号，见 box_draw_stats）
        _hits_per_track = {}

        texts = []
        # ---------------- 车辆 / 目标框 ----------------
        drawn_tracks = set()
        for det in detections:
            bb = det.get("bbox") or []
            if len(bb) < 4:
                continue
            x1, y1, x2, y2 = [int(v) for v in bb[:4]]
            cls = (det.get("class_name") or "").lower()

            # 红绿灯单独处理
            # ★2026-10-09 由 DSH 修正：改用模块级权威名单 TRAFFIC_LIGHT_CLASS_NAMES。
            # 原来这里只认 5 个名字（且与检测侧名单不一致）—— 见该常量处的说明：
            # 上游实际输出的是 COCO 原生 "traffic light"（带空格）与判色裸色名
            # red/green/yellow，两者都会漏网到下面的车辆绘制分支。
            if cls in TRAFFIC_LIGHT_CLASS_NAMES:
                continue

            key = (x1, y1, x2, y2)
            tid, veh = _match_track_for_detection(
                det, _by_id, bbox_to_track, _boxed, _used_ids)
            if tid is not None:
                _used_ids.add(tid)
                _hits_per_track[tid] = _hits_per_track.get(tid, 0) + 1
            if tid is not None and veh is not None:
                if key in bbox_to_track:
                    _assoc_stats['by_bbox'] += 1
                elif (det.get('track_id') is not None
                      or det.get('vehicle_id') is not None):
                    _assoc_stats['by_id'] += 1
                else:
                    _assoc_stats['by_space'] += 1
            else:
                _assoc_stats['none'] += 1

            is_violation = tid is not None and tid in viol_by_track
            # ★2026-10-09 由 DSH 修正（用户口径）：**没拿到追踪 ID 就画灰框、不写字**。
            # 三色分工：绿=正常 / 红=违规 / **灰=尚未追踪**（跟踪器刚建或刚丢时的过渡帧）
            if tid is None:
                color = COLOR_UNKNOWN
            else:
                color = COLOR_VIOLATION if is_violation else COLOR_NORMAL

            # ---- 分级显示（2026-10-04 由 DSH 新增，用户需求）---------------
            # 注意：**这里是主绘制循环**（遍历 detections），另有一个遍历
            # tracked_vehicles 的兜底循环。两处都要服从同一档位，否则改一处
            # 看不到效果（实测踩过：先只改了兜底循环）。
            #   minimal  只画 ID —— 最清爽，信息靠左栏承载
            #   standard ID + 速度
            #   full     ID + 速度 + 车牌 + 违规类型（旧行为）
            #   off      不画文字
            mode = getattr(self, "mode", "minimal")
            _lw = (self.thin_thickness if mode == "minimal" else self.line_thickness)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, _lw)

            parts = []
            if mode != "off":
                if tid is not None:
                    parts.append(f"ID{tid}")
                    drawn_tracks.add(tid)
                elif is_violation:
                    # 理论上到不了这里（违规按 track 归属）；真到了就如实标红字，
                    # **绝不回退成类名** —— 那正是用户误以为"两个框"的原因。
                    parts.append("异常")
                # tid is None 且非违规 -> parts 保持为空 -> 下面 label 为空 -> 不画任何文字
            if mode in ("standard", "full") and veh:
                sp = veh.get("speed")
                if isinstance(sp, (int, float)) and sp > 0:
                    parts.append(f"{sp:.1f}px/s")
            if mode == "full":
                if veh:
                    plate = plate_of_track.get(tid) or (veh.get("plate_number") or "")
                    if plate:
                        parts.append(str(plate))
                if is_violation:
                    parts.append(viol_by_track[tid])
            if not parts:
                parts.append("")

            label = " ".join(str(p) for p in parts if p)
            if label:
                fsz = self._small_font_size if mode == "minimal" else self.font_size
                texts.append((label, x1, max(2, y1 - fsz - 6),
                              COLOR_TEXT_FG, color, fsz))

            # 方向箭头（主循环也要画 —— 2026-10-04 由 DSH 修复）
            # ★2026-10-09：tid is None（灰框）时不画箭头 —— 没有追踪轨迹就没有方向依据
            self._draw_direction_arrow(frame, (x1, y1, x2, y2), veh or {},
                                       is_violation, mode, unknown=(tid is None))

        # ---- 已追踪但未被 detections 覆盖的车辆（避免漏画）----
        for tid, veh in tracked_vehicles.items():
            try:
                tid_i = int(tid)
            except (TypeError, ValueError):
                continue
            if tid_i in drawn_tracks:
                continue
            bb = veh.get("bbox") or []
            if len(bb) < 4:
                continue
            x1, y1, x2, y2 = [int(v) for v in bb[:4]]
            if x2 <= x1 or y2 <= y1:
                continue
            is_violation = tid_i in viol_by_track
            color = COLOR_VIOLATION if is_violation else COLOR_NORMAL
            # 极简档框线收细（2026-10-04 由 DSH 新增）：减少画面遮挡
            _lw = (self.thin_thickness
                   if getattr(self, "mode", "minimal") == "minimal"
                   else self.line_thickness)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, _lw)

            # ---- 分级显示（2026-10-04 由 DSH 新增，用户需求）---------------
            # 背景：车辆多时"框+ID+速度+车牌+方向箭头+违规标签"全画在画面上
            # 会严重遮挡视野（截图中 8+ 辆车同时标注）。用户要求：
            #   **画面只留 ID 与方向箭头，其余信息移到左侧信息栏**。
            # 档位（环境变量 ANNOTATION_MODE 或实例参数）：
            #   minimal  只画 ID（默认）—— 最清爽，适合演示与多车场景
            #   standard ID + 速度
            #   full     ID + 速度 + 车牌 + 违规类型（旧行为）
            #   off      完全不画文字（只留框与箭头）
            mode = getattr(self, "mode", "minimal")
            parts = []
            if mode != "off":
                parts.append(f"ID{tid_i}")
            if mode in ("standard", "full"):
                sp = veh.get("speed")
                if isinstance(sp, (int, float)) and sp > 0:
                    parts.append(f"{sp:.0f}")
            if mode == "full":
                plate = plate_of_track.get(tid_i) or veh.get("plate_number") or ""
                if plate:
                    parts.append(str(plate))
                if is_violation:
                    parts.append(viol_by_track[tid_i])
            if parts:
                # 字号随档位缩放：极简档用更小的字，减少遮挡
                fsz = self._small_font_size if mode == "minimal" else self.font_size
                texts.append((" ".join(parts), x1, max(2, y1 - fsz - 6),
                              COLOR_TEXT_FG, color, fsz))

            # ---- 行进方向箭头（2026-10-03 由 DSH 新增，用户需求）----------
            # 目的：让"逆行"判定肉眼可验证 —— 箭头指向车辆实际行进方向，
            #       与道路规定方向（scene_config['road_direction']）不一致即为逆行。
            # 画法：从 bbox 中心沿方向向量画箭头，逆行时用红色并加粗（突出告警）。
            try:
                cx = float((x1 + x2) / 2.0)
                cy = float((y1 + y2) / 2.0)
                vec = _direction_vector(veh, tracked_history=None)
                if vec is not None:
                    dx, dy = vec
                    bw, bh = max(1.0, x2 - x1), max(1.0, y2 - y1)
                    # 分级显示下箭头也要收细（2026-10-04 由 DSH 调整）
                    # minimal: 更短更细，只表达方向，不抢视线
                    if mode == "minimal":
                        L = max(22.0, min(64.0, max(bw, bh) * 0.38))
                        thick = 3
                        white_pad = 2
                    else:
                        # 标准/详细档保持醒目（2026-10-03 由 DSH 调整：
                        # 原 18-60px/2px 细箭头在截图里几乎看不清）
                        L = max(34.0, min(110.0, max(bw, bh) * 0.55))
                        thick = 5 if is_violation else 4
                        white_pad = 3
                    ex, ey = cx + dx * L, cy + dy * L
                    wrong = bool(is_violation or veh.get("is_wrong_way"))
                    arrow_color = COLOR_VIOLATION if wrong else COLOR_ARROW
                    if wrong and mode == "minimal":
                        thick = 4          # 逆行仍加粗一档（告警不能弱化）
                    # 先描白边（在深色/浅色背景上都可读），再画彩色箭头
                    cv2.arrowedLine(frame, (int(cx), int(cy)), (int(ex), int(ey)),
                                    (255, 255, 255), thick + white_pad, tipLength=0.34)
                    cv2.arrowedLine(frame, (int(cx), int(cy)), (int(ex), int(ey)),
                                    arrow_color, thick, tipLength=0.34)
            except Exception:
                pass
            # --------------------------------------------------------------

        # ---------------- 红绿灯框 ----------------
        # 2026-10-04 由 DSH 修复（用户反馈"标注重叠"）：
        # 问题：YOLO 会把同一根灯杆上的多个灯头、以及灯箱的黄色外壳各检出一个框，
        #       渲染器**直接逐个画**，于是画面上出现多个重叠框 + 多个"黄灯"标签。
        #       用户观察到的"一个红绿灯侧面全是黄的被误认为黄灯"就是这个现象。
        # 修法：① 按 IoU 去重（重叠 >0.55 视为同一个灯，保留置信度高的）
        #       ② 同一位置附近只保留一个标签
        try:
            _tls = _dedupe_traffic_lights(traffic_lights)
        except NameError:
            _tls = traffic_lights
        for tl in _tls:
            bb = tl.get("bbox") or []
            if len(bb) < 4:
                continue
            x1, y1, x2, y2 = [int(v) for v in bb[:4]]
            state = (tl.get("color") or tl.get("state") or "unknown").lower()
            if state not in LIGHT_COLORS:
                state = "unknown"
            color = LIGHT_COLORS[state]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, self.line_thickness + 1)
            label = LIGHT_CN[state]
            cd = tl.get("countdown")
            if cd not in (None, "", 0):
                label = f"{label} {cd}s"
            texts.append((label, x1, max(2, y1 - self.font_size - 8),
                          COLOR_TEXT_FG, color, self.font_size))

        # 一次性绘制所有中文文本
        frame = self.draw_texts(frame, texts)

        # ★2026-10-09 由 DSH 新增：登记本帧的关联统计（供 /status 的 box_draw_stats）
        # 只在**真的画了框**的路径上统计；判定语义与此无关。
        _n_main = 0
        for d in detections:
            if (d.get("class_name") or "").lower() in TRAFFIC_LIGHT_CLASS_NAMES:
                continue
            if len(d.get("bbox") or []) >= 4:
                _n_main += 1
        _n_fallback = 0
        for _tk, v in (tracked_vehicles or {}).items():
            if not isinstance(v, dict) or len(v.get("bbox") or []) < 4:
                continue
            try:
                _ti = int(_tk)
            except (TypeError, ValueError):
                try:
                    _ti = int(v.get("id"))
                except (TypeError, ValueError):
                    _ti = None
            if _ti is None or _ti not in drawn_tracks:
                _n_fallback += 1
        _max_hit = max(_hits_per_track.values()) if _hits_per_track else 0
        try:
            with _BOX_STATS_LOCK:
                _BOX_STATS['frames'] = int(_BOX_STATS.get('frames', 0)) + 1
                _BOX_STATS['main_boxes'] = _n_main
                _BOX_STATS['fallback_boxes'] = _n_fallback
                _BOX_STATS['unmatched_dets'] = int(_assoc_stats.get('none', 0))
                _BOX_STATS['max_dets_per_track'] = int(_max_hit)
                _BOX_STATS['tracks_drawn'] = len(drawn_tracks)
                _BOX_STATS['last_update'] = _t.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass

        self.last_render_ms = (_t.perf_counter() - t0) * 1000.0
        self.rendered_frames += 1
        return frame


# 模块级单例（字体缓存复用，避免每帧新建）
_default_renderer: Optional[AnnotationRenderer] = None
_default_lock = threading.Lock()


def _build_track_index(tracked_vehicles):
    """把 tracked_vehicles 整理成渲染器可直接用的索引（2026-10-09 由 DSH 新增）

    Args:
        tracked_vehicles: `{track_id: {'id','bbox',...}}`（**必须是 dict**，
            见 T74：把它当 list 遍历会遍历出字符串键）
    Returns:
        `(by_id, by_bbox, boxed)`：
          by_id   —— `{int(track_id): veh}`，主关联路径
          by_bbox —— `{(int x1,y1,x2,y2): veh}`，兼容路径（与旧行为完全一致）
          boxed   —— `[(int tid, [x1,y1,x2,y2]), ...]`，供宽松匹配与违规归属用
    """
    by_id, by_bbox, boxed = {}, {}, []
    for raw_tid, veh in (tracked_vehicles or {}).items():
        if not isinstance(veh, dict):
            continue
        bb = veh.get("bbox") or []
        if len(bb) < 4:
            continue
        try:
            x1, y1, x2, y2 = [float(v) for v in bb[:4]]
        except (TypeError, ValueError):
            continue
        try:
            tid = int(raw_tid)
        except (TypeError, ValueError):
            try:
                tid = int(veh.get("id"))
            except (TypeError, ValueError):
                tid = None
        if tid is not None:
            by_id[tid] = veh
        by_bbox[(int(x1), int(y1), int(x2), int(y2))] = veh
        boxed.append((tid, [x1, y1, x2, y2]))
    return by_id, by_bbox, boxed


def _match_track_for_detection(det, by_id, by_bbox, boxed, used_ids,
                               tol: float = 3.0, iou_min: float = 0.15,
                               dist_frac: float = 0.30):
    """把一条 detection 关联到某辆追踪车辆（2026-10-09 由 DSH 新增）

    ★★ 这是"每辆车两个框"的根治点（设计单 §12.3 方案 B）。
    旧实现的关联方式是 **bbox 精确匹配**：
        bbox_to_track[tuple(int(x) for x in bb[:4])] = veh   # 键 = int 化后的框
        veh = bbox_to_track.get((x1, y1, x2, y2))            # 主循环按 detection 的框查
    而"框位置预测"（`_predict_boxes`）会把 tracked_vehicles 的框**平移成带小数的值**
    -> 取整后不再等于 detection 的框 -> **查不到** -> `tid=None` ->
    主循环画车型标签（`car`）且**不登记 drawn_tracks** ->
    兜底循环（遍历 tracked_vehicles）**又画一次带 `ID18` 的框**
    => 用户看到的"**一个 ID 框 + 一个车型框，还重叠**"，且**所有视频都这样**。
    （实测对比见 `_scripts\_verify_two_boxes.py`：预测关 = 1 个框 ✅ / 预测开 = 2 个框 ❌）

    现在的关联顺序（**先按 ID，再按空间**，并把已占用的 track 排除掉）：
      ① `det['track_id']` —— 检测链路 `_attach_track_ids()` 已经回填的 track id（**最快最准**）；
      ② bbox **精确匹配** —— 与旧行为完全一致，保住既有回退路径；
      ③ bbox 按像素**容差匹配**（默认 ±3 px）—— 覆盖"取整差 1 px"这类漂移；
      ④ IoU 最近邻（≥ 0.15）；
      ⑤ 中心距最近邻（≤ 0.30 × 框对角线）—— 兜住预测位移较大的情况。
    ⚠ `used_ids` 保证**一个 track 只被一条 detection 占用**（避免两辆车都匹配到同一个 ID）。
    ⚠ 这里只决定"画什么"，不改任何判定数据（预测本身只作用于显示副本）。
    ⚠ ③④⑤ 是**兜底**：实测 `_attach_track_ids()`（IoU 0.12 + 中心包含）绝大多数帧已把
      `track_id` 回填好，① 就解决了 —— 所以兜底阈值取保守值，宁可留空标签也不乱挂 ID。

    Returns: `(track_id 或 None, veh 或 None)`
    """
    bb = (det or {}).get("bbox") or []
    if len(bb) < 4:
        return None, None
    try:
        x1, y1, x2, y2 = [int(v) for v in bb[:4]]
    except (TypeError, ValueError):
        return None, None

    # ① 按 track_id（检测链路已回填；`_attach_track_ids` 用 IoU 0.12 + 中心包含兜底）
    raw = (det or {}).get("track_id")
    if raw is None:
        raw = (det or {}).get("vehicle_id")
    if raw is not None and not isinstance(raw, bool):
        try:
            cand = int(float(raw))
        except (TypeError, ValueError):
            cand = None
        if cand is not None and cand not in used_ids and cand in by_id:
            return cand, by_id[cand]

    # ② 精确 bbox（旧行为）
    veh = by_bbox.get((x1, y1, x2, y2))
    if veh is not None:
        try:
            cand = int(veh.get("id"))
        except (TypeError, ValueError):
            cand = None
        if cand is not None and cand not in used_ids:
            return cand, veh

    if not boxed:
        return None, None

    # ③ 按像素容差匹配（覆盖 int() 取整造成的 1~3 px 漂移）
    for cand, t in boxed:
        if cand is None or cand in used_ids:
            continue
        if (abs(t[0] - x1) <= tol and abs(t[1] - y1) <= tol
                and abs(t[2] - x2) <= tol and abs(t[3] - y2) <= tol):
            return cand, by_id.get(cand)

    # ④ IoU 最近邻
    a_area = max(1.0, (x2 - x1) * (y2 - y1))
    best, best_iou = None, 0.0
    for cand, t in boxed:
        if cand is None or cand in used_ids:
            continue
        ix1, iy1 = max(x1, t[0]), max(y1, t[1])
        ix2, iy2 = min(x2, t[2]), min(y2, t[3])
        if ix2 <= ix1 or iy2 <= iy1:
            continue
        inter = (ix2 - ix1) * (iy2 - iy1)
        b_area = max(1.0, (t[2] - t[0]) * (t[3] - t[1]))
        iou = inter / (a_area + b_area - inter)
        if iou > best_iou:
            best, best_iou = cand, iou
    if best is not None and best_iou >= iou_min:
        return best, by_id.get(best)

    # ⑤ 中心距最近邻（预测位移较大时兜底）
    acx, acy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    best, best_d2 = None, None
    for cand, t in boxed:
        if cand is None or cand in used_ids:
            continue
        tcx, tcy = (t[0] + t[2]) / 2.0, (t[1] + t[3]) / 2.0
        d2 = (tcx - acx) ** 2 + (tcy - acy) ** 2
        if best_d2 is None or d2 < best_d2:
            best, best_d2 = cand, d2
    if best is not None and best_d2 is not None:
        diag = max(1.0, ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
        if best_d2 ** 0.5 <= dist_frac * diag:
            return best, by_id.get(best)
    return None, None


def _dedupe_traffic_lights(tls, iou_thr: float = 0.55):
    """红绿灯去重（2026-10-04 由 DSH 新增）

    用户反馈："标注好像有重叠（比如黄灯）"、"有一个红绿灯的侧面全是黄的，
    被误认为是黄灯了"。

    原因：YOLO 会把同一根灯杆的多个灯头、以及灯箱黄色外壳各检出一个框；
    渲染器逐个画 -> 画面出现多个重叠框与多个"黄灯"标签。

    做法：按 IoU 去重，重叠超过阈值视为同一个灯。状态冲突时保留
    "红灯 > 绿灯 > 黄灯/未知"优先级更高的（把红灯误显示成黄灯后果更严重，
    宁可保守），同级按置信度。
    """
    items = []
    for t in (tls or []):
        bb = (t or {}).get("bbox") or []
        if len(bb) < 4:
            continue
        try:
            x1, y1, x2, y2 = [float(v) for v in bb[:4]]
        except (TypeError, ValueError):
            continue
        if x2 <= x1 or y2 <= y1:
            continue
        items.append({
            "t": t,
            "box": (x1, y1, x2, y2),
            "conf": float((t or {}).get("confidence") or 0.0),
            "state": str((t or {}).get("color") or (t or {}).get("state") or "").lower(),
        })

    def _iou(a, b):
        ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
        ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
        iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
        inter = iw * ih
        if inter <= 0:
            return 0.0
        aa = (a[2] - a[0]) * (a[3] - a[1])
        bb2 = (b[2] - b[0]) * (b[3] - b[1])
        u = aa + bb2 - inter
        return inter / u if u > 0 else 0.0

    _prio = {"red": 3, "green": 2, "yellow": 1}
    items.sort(key=lambda d: (_prio.get(d["state"], 0), d["conf"]), reverse=True)

    kept = []
    for it in items:
        if any(_iou(it["box"], k["box"]) >= iou_thr for k in kept):
            continue
        kept.append(it)
    return [k["t"] for k in kept]


def get_renderer(font_size: int = 18) -> AnnotationRenderer:
    global _default_renderer
    if _default_renderer is None:
        with _default_lock:
            if _default_renderer is None:
                _default_renderer = AnnotationRenderer(font_size=font_size)
    return _default_renderer
