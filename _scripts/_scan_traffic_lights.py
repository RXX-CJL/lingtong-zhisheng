"""扫描测试视频，统计红绿灯检测情况（判断能否自动构建训练集）

输出：
  - 每 N 帧跑一次 YOLO，统计 traffic light 类别的检出框数量、尺寸分布
  - 若有检出，导出若干红绿灯裁剪图到 _tl_crops/ 供人工核验
"""

import os
import sys
import time

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402

from image_recognizer import multi_model_detect  # noqa: E402

VIDEO = r"E:\output\1\test_assets\traffic_videos\test1.mp4"
OUT_DIR = r"E:\output\_tl_crops"
os.makedirs(OUT_DIR, exist_ok=True)

import base64  # noqa: E402

cap = cv2.VideoCapture(VIDEO)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
print(f"视频: {total} 帧, {fps:.1f} fps")

STEP = 30          # 每 30 帧采样一次
MAX_SAMPLES = 12   # 最多跑 12 次推理（控制耗时）

found = []
frame_idx = 0
samples = 0
t0 = time.time()

while samples < MAX_SAMPLES:
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ok, frame = cap.read()
    if not ok:
        break
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    data_url = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
    try:
        r = multi_model_detect(data_url, conf_threshold=0.35)
        dets = r.get("all_detections", []) if r.get("success") else []
    except Exception as e:
        print(f"  帧{frame_idx} 推理失败: {str(e)[:80]}")
        dets = []
    tls = [d for d in dets if str(d.get("class_name", "")).lower().replace("_", " ")
           in ("traffic light",)]
    print(f"  帧{frame_idx:4d}: 总检测 {len(dets):2d}  红绿灯 {len(tls)}")
    for i, d in enumerate(tls):
        bb = d.get("bbox") or []
        if len(bb) < 4:
            continue
        x1, y1, x2, y2 = [int(v) for v in bb[:4]]
        w, h = x2 - x1, y2 - y1
        found.append({"frame": frame_idx, "bbox": bb, "w": w, "h": h,
                      "conf": d.get("confidence")})
        if w >= 6 and h >= 6:
            crop = frame[max(0, y1):y2, max(0, x1):x2]
            if crop.size:
                cv2.imwrite(os.path.join(OUT_DIR, f"f{frame_idx}_i{i}_{w}x{h}.jpg"), crop)
    frame_idx += STEP
    samples += 1

cap.release()
print()
print("=" * 70)
print(f"采样 {samples} 帧，耗时 {time.time()-t0:.1f}s")
print(f"红绿灯检出总数: {len(found)}")
if found:
    ws = [f["w"] for f in found]
    hs = [f["h"] for f in found]
    print(f"  尺寸范围: 宽 {min(ws)}-{max(ws)}  高 {min(hs)}-{max(hs)}")
    print(f"  平均尺寸: {sum(ws)/len(ws):.0f} x {sum(hs)/len(hs):.0f}")
    small = sum(1 for f in found if f["w"] < 12 or f["h"] < 12)
    print(f"  过小(<12px)的: {small}")
    print(f"  裁剪图已导出: {OUT_DIR}")
    print()
    print("结论:", "红绿灯可检出，可自动构建训练集" if len(found) >= 5
          else "检出太少，自动构建训练集不可行")
else:
    print("结论: COCO 模型在该视频里检不到红绿灯 -> 需更换数据源或改用其他方案")
