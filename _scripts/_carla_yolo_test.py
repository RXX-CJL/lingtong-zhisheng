"""关键验证：YOLO 能否识别 CARLA 渲染的车辆？

这是"CARLA 能否替代外部素材"的**分水岭**：
  · 我自制的纯色矩形 -> YOLO 识别不出（不在 COCO 分布内）
  · CARLA 是真 3D 车辆模型 -> **预期能识别**，但必须实测

做法：把刚才的 4K 帧缩到项目检测用的尺寸，喂给项目的 multi_model_detect。
"""

import io
import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

import cv2  # noqa: E402

out = []
frame_path = r"E:\output\_carla_frames\carla_junction_4k_0.png"
img = cv2.imread(frame_path)
out.append(f"原图: {img.shape[1]}x{img.shape[0]}")

# 项目检测用的分辨率（YOLO_IMGSZ 默认 1280）
for target_w in (1920, 1280):
    h = int(img.shape[0] * target_w / img.shape[1])
    small = cv2.resize(img, (target_w, h), interpolation=cv2.INTER_AREA)
    p = rf"E:\output\_carla_frames\carla_{target_w}.jpg"
    cv2.imwrite(p, small, [cv2.IMWRITE_JPEG_QUALITY, 92])
    out.append("")
    out.append("=" * 74)
    out.append(f"喂给项目检测器 @ {target_w}x{h}")
    out.append("=" * 74)
    try:
        from image_recognizer import multi_model_detect
        r = multi_model_detect(p, conf_threshold=0.25)
        dets = r.get("all_detections", []) if r.get("success") else []
        veh = [d for d in dets if d.get("class_name") in
               ("car", "truck", "bus", "motorcycle", "bicycle")]
        out.append(f"  总检测: {len(dets)}   车辆类: {len(veh)}")
        for d in dets[:8]:
            bb = [int(x) for x in (d.get("bbox") or [])]
            out.append(f"    {str(d.get('class_name')):12s} conf={d.get('confidence'):.2f} "
                       f"bbox={bb}  尺寸={bb[2]-bb[0]}x{bb[3]-bb[1]}")
        if not dets:
            out.append("  ⚠ 无任何检测")
    except Exception as e:
        import traceback
        out.append(f"  ❌ 检测异常: {type(e).__name__}: {str(e)[:200]}")

out.append("")
out.append("=" * 74)
out.append("结论")
out.append("=" * 74)
io.open(r"E:\output\_carla_yolo_test.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
