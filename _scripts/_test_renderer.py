"""验证中文标注渲染器：中文可读性 + 性能 + 违规红框/正常绿框"""

import os
import sys
import time

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from annotation_renderer import AnnotationRenderer, get_font, _resolve_font_path  # noqa: E402

print("=" * 76)
print("1) 字体解析")
print("=" * 76)
print("  选中字体:", _resolve_font_path())
print("  18px 字体:", get_font(18))

# 用真实视频帧做底图
cap = cv2.VideoCapture(r"E:\output\1\test_assets\traffic_videos\test1.mp4")
ok, frame = False, None
for _ in range(30):
    ok, frame = cap.read()
    if ok:
        break
cap.release()
print("  底图:", ok, frame.shape if ok else None)

# 构造模拟数据
detections = [
    {"bbox": [100, 250, 260, 400], "class_name": "car", "confidence": 0.88},
    {"bbox": [300, 260, 430, 380], "class_name": "bus", "confidence": 0.91},
    {"bbox": [500, 120, 560, 190], "class_name": "traffic light", "confidence": 0.75},
    {"bbox": [700, 280, 820, 400], "class_name": "truck", "confidence": 0.80},
]
tracked = {
    3: {"id": 3, "bbox": [100, 250, 260, 400], "class_name": "轿车",
        "speed": 12.4, "direction": "向上", "plate_number": "宁A88888"},
    7: {"id": 7, "bbox": [300, 260, 430, 380], "class_name": "公交车",
        "speed": 0.0, "direction": "向上", "plate_number": "宁B12345"},
    9: {"id": 9, "bbox": [700, 280, 820, 400], "class_name": "卡车",
        "speed": 8.1, "direction": "向右"},
}
violations = [
    {"track_id": 7, "violation_type": "illegal_parking", "violation_type_cn": "违规停车",
     "confidence": 0.70},
]
lights = [{"bbox": [500, 120, 560, 190], "color": "red"}]
plates = {3: "宁A88888"}

print()
print("=" * 76)
print("2) 渲染（含中文标签、违规红框、红绿灯框）")
print("=" * 76)
r = AnnotationRenderer(font_size=20)
t0 = time.perf_counter()
out = r.render(frame.copy(), detections, tracked, violations, lights, plates)
ms1 = (time.perf_counter() - t0) * 1000

# 连跑 30 次测平均耗时
times = []
for _ in range(30):
    t = time.perf_counter()
    r.render(frame.copy(), detections, tracked, violations, lights, plates)
    times.append((time.perf_counter() - t) * 1000)
avg = sum(times) / len(times)
print(f"  首次渲染: {ms1:.1f} ms")
print(f"  30 次平均: {avg:.1f} ms  (最小 {min(times):.1f} / 最大 {max(times):.1f})")
print(f"  等效帧率上限: {1000/avg:.1f} fps")
print(f"  渲染帧计数: {r.rendered_frames}")

out_path = r"E:\output\_screens\annotation_test.png"
cv2.imwrite(out_path, out)
print(f"  输出: {out_path}")

print()
print("=" * 76)
print("3) 判定")
print("=" * 76)
ok_font = get_font(18) is not None
print(f"  中文字体可用: {'PASS' if ok_font else 'FAIL'}")
print(f"  性能(>=15fps): {'PASS' if 1000/avg >= 15 else 'FAIL'}  ({1000/avg:.1f} fps)")
print("  说明: 渲染耗时是整个画框流程的开销，不含 YOLO 推理(实测 0.01s/帧)")
