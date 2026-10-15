"""检查关键 YOLO 模型的类别名（决定红绿灯/车牌/倒计时可行性）"""

import os
import sys

MODELS_DIR = r"E:\output\1\zhitong\training\models"
TARGETS = ["traffic_light.pt", "traffic_light_best.pt", "lane.pt",
           "vehicle_best.pt", "best.pt", "helmet_best.pt", "yolov8s.pt"]

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

from ultralytics import YOLO  # noqa: E402

print("=" * 78)
for name in TARGETS:
    p = os.path.join(MODELS_DIR, name)
    if not os.path.exists(p):
        print(f"  [缺失] {name}")
        continue
    try:
        m = YOLO(p)
        names = getattr(m, "names", None) or {}
        if isinstance(names, dict):
            items = [f"{k}:{v}" for k, v in list(names.items())[:20]]
        else:
            items = [f"{i}:{v}" for i, v in enumerate(list(names)[:20])]
        print(f"\n{name}")
        print(f"  类别数: {len(names)}")
        print(f"  类别名: {', '.join(items)}")
    except Exception as e:
        print(f"\n{name}\n  读取失败: {type(e).__name__}: {str(e)[:120]}")

print()
print("=" * 78)
print("判定要点")
print("=" * 78)
print("  - 若 traffic_light 模型类别含 red/yellow/green -> 可直接画颜色框")
print("  - 若含 countdown/digit 类 -> 可识别倒计时数字")
print("  - 若含 plate 类 -> 已有车牌定位能力")
