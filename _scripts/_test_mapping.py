"""验证违规映射：① 带 ID（行为引擎）② 无 ID 仅 bbox（规则引擎）③ 点位

渲染两张图对比，确认红框出现且违规类型正确显示。
"""

import os
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402

from annotation_renderer import AnnotationRenderer  # noqa: E402

cap = cv2.VideoCapture(r"E:\output\1\test_assets\traffic_videos\test1.mp4")
ok, frame = False, None
for _ in range(30):
    ok, frame = cap.read()
    if ok:
        break
cap.release()

detections = [
    {"bbox": [100, 250, 260, 400], "class_name": "car", "confidence": 0.88},
    {"bbox": [300, 260, 430, 380], "class_name": "bus", "confidence": 0.91},
    {"bbox": [700, 280, 820, 400], "class_name": "truck", "confidence": 0.80},
]
tracked = {
    1: {"id": 1, "bbox": [100, 250, 260, 400], "class_name": "轿车",
        "speed": 12.4, "plate_number": "宁A88888"},
    7: {"id": 7, "bbox": [300, 260, 430, 380], "class_name": "公交车",
        "speed": 0.0, "plate_number": "宁B12345"},
    9: {"id": 9, "bbox": [700, 280, 820, 400], "class_name": "卡车",
        "speed": 8.1},
}
lights = [{"bbox": [500, 120, 560, 190], "color": "red"}]
r = AnnotationRenderer(font_size=20)

# --- 场景 A：行为引擎式违规（带 vehicle_id）---
va = [{"violation_type": "illegal_parking", "violation_type_cn": "违规停车",
       "vehicle_id": "7", "confidence": 0.70}]
outA = r.render(frame.copy(), detections, tracked, va, lights, {1: "宁A88888"})
pA = r"E:\output\_screens\map_test_A_withid.png"
cv2.imwrite(pA, outA)
print(f"场景 A（带 vehicle_id='7'）: {pA}")

# --- 场景 B：规则引擎式违规（无 ID，只有 evidence.bbox 与 location）---
vb = [{"violation_type": "speeding", "violation_type_cn": "超速",
       "evidence": {"vehicle_count": 3, "bbox": [305, 265, 425, 375]},
       "location": {"x": 100, "y": 100},
       "confidence": 0.83}]
outB = r.render(frame.copy(), detections, tracked, vb, lights, {})
pB = r"E:\output\_screens\map_test_B_nobbox.png"
cv2.imwrite(pB, outB)
print(f"场景 B（无 ID，仅 evidence.bbox）: {pB}")

# --- 判定：检查场景 B 的车辆 7 框颜色是否为红色 ---
# 红色 BGR = (60,60,235)；在车辆7框边缘采样
def box_color(img, bb):
    x1, y1, x2, y2 = bb
    # 取上边缘中点附近的像素
    px = img[y1 + 1, (x1 + x2) // 2]
    return tuple(int(v) for v in px)

print()
print("=" * 70)
print("颜色采样（判断红/绿框）")
print("=" * 70)
print("  参考: 绿框 BGR≈(80,220,80)  红框 BGR≈(60,60,235)")
for name, img in (("A", outA), ("B", outB)):
    for tid, bb in ((1, [100, 250, 260, 400]), (7, [300, 260, 430, 380])):
        c = box_color(img, bb)
        is_red = c[2] > 150 and c[0] < 120 and c[1] < 120
        is_green = c[1] > 150 and c[0] < 150 and c[2] < 150
        tag = "红" if is_red else ("绿" if is_green else "其他")
        print(f"  场景{name} 车辆{tid}: BGR={c} -> {tag}")
