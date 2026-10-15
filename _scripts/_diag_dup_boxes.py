"""
只读诊断：量化"同一辆车出现多个重叠框"（2026-10-06 由 DSH 编写）

做法：用真实帧调 multi_model_detect，统计 all_detections 里
      1) 各 source_model 贡献了多少框
      2) 有多少对框的 IoU 超过阈值（= 同一目标被重复检出）
不修改任何东西。
"""
import base64
import sys

sys.path.insert(0, r'E:\output\1\api')
import cv2
import numpy as np

VIDEO = r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv'

cap = cv2.VideoCapture(VIDEO)
# 取有车的一帧（前面实测 260 帧附近有车 + 12 个红绿灯）
cap.set(cv2.CAP_PROP_POS_FRAMES, 260)
_, frame = cap.read()
cap.release()
_, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
URL = 'data:image/jpeg;base64,' + base64.b64encode(buf.tobytes()).decode()

from image_recognizer import init_all_models, multi_model_detect
init_all_models()
# 预热一次（避免冷启动）
multi_model_detect(URL, 0.5)
r = multi_model_detect(URL, 0.5)
dets = r.get('all_detections') or []

print(f'帧 {frame.shape[1]}x{frame.shape[0]}  检出 {len(dets)} 个框')
print('')

from collections import Counter
by_model = Counter(d.get('source_model') for d in dets)
by_class = Counter(d.get('class_name') for d in dets)
print('按来源模型:', dict(by_model))
print('按类别    :', dict(by_class))
print('')


def iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / ua if ua > 0 else 0.0


VEH = {'car', 'truck', 'bus', 'motorcycle', 'bicycle', 'van', 'vehicle'}
veh_dets = [d for d in dets if str(d.get('class_name', '')).lower() in VEH]
print(f'其中"车辆类"框 = {len(veh_dets)} 个')
print('明细（类别 / 来源模型 / 置信度 / 框）：')
for d in sorted(veh_dets, key=lambda x: -float(x.get('confidence') or 0)):
    bb = [round(float(t)) for t in (d.get('bbox') or [])[:4]]
    print('   %-12s %-14s %.2f  %s' % (d.get('class_name'), d.get('source_model'),
                                       float(d.get('confidence') or 0), bb))

print('')
print('重叠对（IoU > 0.5，说明是同一个目标被重复检出）：')
n_dup = 0
for i in range(len(veh_dets)):
    for j in range(i + 1, len(veh_dets)):
        a = veh_dets[i].get('bbox') or []
        b = veh_dets[j].get('bbox') or []
        if len(a) < 4 or len(b) < 4:
            continue
        v = iou([float(t) for t in a[:4]], [float(t) for t in b[:4]])
        if v > 0.5:
            n_dup += 1
            print('   IoU=%.2f  %s(%s) <-> %s(%s)' % (
                v, veh_dets[i].get('class_name'), veh_dets[i].get('source_model'),
                veh_dets[j].get('class_name'), veh_dets[j].get('source_model')))
print(f'   -> 共 {n_dup} 对重叠（用户看到"每辆车两个框"的直接原因）')
print('')
print('注：all_detections 的去重键是 (class_name, bbox元组)，')
print('    框不同就都留下 -> 同一辆车会被不同模型各画一个框。')
