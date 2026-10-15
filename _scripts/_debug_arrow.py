"""调试：为何箭头未渲染（直接调 render 并检查像素变化）"""

import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from annotation_renderer import AnnotationRenderer, _direction_vector  # noqa: E402

frame = cv2.imread(r"E:\output\_screens\scene_firstframe.jpg")
if frame is None:
    print("底图读取失败")
    sys.exit(1)
print(f"底图: {frame.shape}")

base = frame.copy()


def hist(cx, cy, dx, dy, n=6):
    return [{"center": [cx + dx * i * 8, cy + dy * i * 8], "timestamp": 1000 + i * 0.5}
            for i in range(n)]


veh = {"id": 1, "bbox": [200, 300, 300, 420], "class_name": "轿车", "speed": 40.0,
       "history": hist(250, 360, 0, -1), "direction": "up"}
print(f"  方向向量: {_direction_vector(veh)}")

r = AnnotationRenderer(font_size=18)
out = r.render(frame.copy(), [{"bbox": veh["bbox"], "class_name": "car"}], {1: veh}, [], [], {})
diff = cv2.absdiff(base, out)
gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
nz = int(cv2.countNonZero(gray))
print(f"  渲染后变化像素: {nz}")
ys, xs = np.where(gray > 0)
if len(xs):
    print(f"  变化区域: x {xs.min()}-{xs.max()}  y {ys.min()}-{ys.max()}")

# 手工画一次箭头做对照
manual = base.copy()
cv2.arrowedLine(manual, (250, 360), (250, 300), (240, 200, 60), 3, tipLength=0.32)
d2 = cv2.absdiff(base, manual)
print(f"  手工箭头变化像素: {int(cv2.countNonZero(cv2.cvtColor(d2, cv2.COLOR_BGR2GRAY)))}")
cv2.imwrite(r"E:\output\_screens\arrow_debug.png", out)
cv2.imwrite(r"E:\output\_screens\arrow_manual.png", manual)
print("  输出: arrow_debug.png / arrow_manual.png")

# 检查 render 内部是否走了箭头分支
import inspect  # noqa: E402
src = inspect.getsource(AnnotationRenderer.render)
print()
print("  render 中箭头代码是否存在于源码:", "arrowedLine" in src)
idx = src.find("arrowedLine")
if idx > 0:
    print("  ---- 箭头代码段 ----")
    print(src[max(0, idx - 700):idx + 200])
