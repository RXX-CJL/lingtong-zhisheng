"""
验证「两个框」根因假设（2026-10-09 由 DSH 编写，只读）

假设：`annotation_renderer` 用 **bbox 精确匹配**（`tuple(int(x) for x in bb)`）
      把 detection 关联到 track（用于决定画 ID 还是画 class_name）。
      而 `_predict_boxes` 会把 `tracked_vehicles` 的框**平移成 float**。
      -> 主循环里 `bbox_to_track.get(key)` 查不到 -> tid=None
      -> 画 `car`（车型标签）而**不进 drawn_tracks**
      -> 兜底循环再画一次**带 ID**的框
      => 结果：**一辆车两个框：一个 ID 框 + 一个车型框**（与用户描述完全一致）

本脚本用**纯 Python 复现这段匹配逻辑**，对比"预测开/关"两种情况。
不启动检测、不改代码。
"""
import sys
import time

sys.path.insert(0, r'E:\output\1\api')

import numpy as np
from realtime_detector import RealtimeViolationDetector

d = RealtimeViolationDetector()
d.current_frame = np.zeros((1080, 1920, 3), np.uint8)

# 一辆正在行驶的车（bbox 是 int，模拟 YOLO 输出）
DET_BBOX = [1367, 623, 1725, 778]
VEH = {
    'id': 18,
    'bbox': [1367.0, 623.0, 1725.0, 778.0],
    'class_name': 'car', 'speed': 160.0, 'direction': 'up',
    'history': [{'center': (1450.0, 700.0), 'timestamp': 1.0},
                {'center': (1460.0, 690.0), 'timestamp': 1.05},
                {'center': (1470.0, 680.0), 'timestamp': 1.10}],
}
tracked = {18: VEH}
detections = [{'bbox': DET_BBOX, 'class_name': 'car', 'confidence': 0.75,
               'source_model': 'vehicle'}]


def build_bbox_to_track(tracked_vehicles):
    """复刻 annotation_renderer.py:388 的关联键构造"""
    m = {}
    for tid, veh in tracked_vehicles.items():
        bb = veh.get('bbox') or []
        if len(bb) >= 4:
            m[tuple(int(x) for x in bb[:4])] = veh
    return m


def simulate(label, tracked_vehicles):
    b2t = build_bbox_to_track(tracked_vehicles)
    key = tuple(int(x) for x in DET_BBOX)
    veh = b2t.get(key)
    tid = None
    if veh is not None:
        try:
            tid = int(veh.get('id'))
        except (TypeError, ValueError):
            tid = None

    drawn_tracks = set()
    if tid is not None:
        drawn_tracks.add(tid)
        main_label = f'ID{tid}'
    else:
        main_label = 'car'          # 无 track -> 画 class_name

    # 兜底循环：遍历 tracked_vehicles，已被 drawn_tracks 覆盖的跳过
    fallback_drawn = []
    for t, v in tracked_vehicles.items():
        try:
            ti = int(t)
        except (TypeError, ValueError):
            continue
        if ti in drawn_tracks:
            continue
        fallback_drawn.append(ti)

    n_boxes = 1 + len(fallback_drawn)
    print(f'{label}')
    print(f'    bbox_to_track 的键 : {list(b2t.keys())}')
    print(f'    主循环用 detection 框查表: {key}')
    print(f'    命中 veh            : {"是" if veh is not None else "否"}')
    print(f'    主循环标签           : {main_label}')
    print(f'    主循环登记 drawn    : {sorted(drawn_tracks) or "（空）"}')
    print(f'    兜底循环又画了       : {fallback_drawn or "（无）"}')
    print(f'    => 该车**共画 {n_boxes} 个框**  {"← 用户看到的两个框" if n_boxes > 1 else "← 正常，1 个框"}')
    print('')
    return n_boxes


print('=' * 70)
print('用真实代码路径构造两种情形（预测关 / 预测开）')
print('=' * 70)
print('')

# 情形 A：预测关闭 -> tracked 的 bbox 与 detection 完全一致（int 化后相等）
n_a = simulate('【情形 A】BOX_PREDICTION=0（tracked bbox 未被平移）', tracked)

# 情形 B：预测开启 -> tracked 的 bbox 被平移成带小数的值
d._last_detect_wall_ts = time.time() - 0.30
d._det_interval_ema = 0.30
predicted = d._predict_boxes(dict(tracked))
n_b = simulate('【情形 B】BOX_PREDICTION=1（tracked bbox 被预测平移）', predicted)

print('=' * 70)
print('结论：')
print(f'  预测关闭 -> {n_a} 个框；预测开启 -> {n_b} 个框')
if n_b > n_a:
    print('  ★ 假设成立：**框预测导致 bbox 精确匹配失效，从而多画一个框**')
    print('    这解释了用户的现象"一个 ID 框 + 一个汽车类型识别框，很多时候有重叠"，')
    print('    且"所有视频处理后都这样"。')
else:
    print('  假设不成立，需继续排查其它路径。')
print('=' * 70)
