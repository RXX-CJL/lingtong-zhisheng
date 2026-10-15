"""建立"灯杆 ↔ 画面检测框"的对应关系（前 6 次失败的关键缺失步骤）

背景：
  我一直假设"我 set_state 的灯 = 视频里看到的灯"，但从未验证过。
  结果验证判色时真值与画面不匹配，得出 0% 的错误结论。

本脚本：
  ① 用 v4 录制时的相机参数（位置/朝向/分辨率/fov）复算投影
  ② 对世界里每个红绿灯的【每个灯珠】算出像素位置
  ③ 与 YOLO 在视频里检出的框比对，找出真正的对应关系
  ④ 输出对应表 + 把灯珠位置画到帧上供人工确认
"""

import glob
import io
import math
import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

import cv2
import numpy as np
from ultralytics import YOLO

OUT = r"E:\output\_tl_review"
os.makedirs(OUT, exist_ok=True)
out = []

# ---- v4 录制时的相机参数（来自 _carla_record4.py）----
W, H, FOV = 2560, 1440, 70.0
CAM_LOC = (-82.6, 50.5, 7.0)
CAM_YAW = -55.3
CAM_PITCH = -22.0
FRAME_IDX = 200

out.append("v4 相机参数:")
out.append(f"  位置=({CAM_LOC[0]}, {CAM_LOC[1]}, {CAM_LOC[2]})  yaw={CAM_YAW}  pitch={CAM_PITCH}")
out.append(f"  分辨率={W}x{H}  fov={FOV}")

f_px = W / (2.0 * math.tan(math.radians(FOV) / 2.0))

# CARLA 是左手系：yaw 绕 Z，pitch 绕 Y（向下为负）
# 相机基向量（世界系）：
#   yaw 决定水平朝向，pitch 决定俯仰
def basis(yaw_deg, pitch_deg):
    y = math.radians(yaw_deg)
    p = math.radians(pitch_deg)
    # 先绕 Z 转 yaw，再绕（旋转后的）Y 转 pitch
    fwd = (math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p))
    # right = fwd × up_world 归一化
    up_w = (0.0, 0.0, 1.0)
    rx = fwd[1] * up_w[2] - fwd[2] * up_w[1]
    ry = fwd[2] * up_w[0] - fwd[0] * up_w[2]
    rz = fwd[0] * up_w[1] - fwd[1] * up_w[0]
    rn = math.sqrt(rx * rx + ry * ry + rz * rz)
    right = (rx / rn, ry / rn, rz / rn)
    # up = right × fwd
    ux = right[1] * fwd[2] - right[2] * fwd[1]
    uy = right[2] * fwd[0] - right[0] * fwd[2]
    uz = right[0] * fwd[1] - right[1] * fwd[0]
    up = (ux, uy, uz)
    return fwd, right, up


fwd, right, up = basis(CAM_YAW, CAM_PITCH)
out.append(f"  相机基: fwd=({fwd[0]:.3f},{fwd[1]:.3f},{fwd[2]:.3f}) "
           f"right=({right[0]:.3f},{right[1]:.3f},{right[2]:.3f}) "
           f"up=({up[0]:.3f},{up[1]:.3f},{up[2]:.3f})")


def project(P):
    d = (P[0] - CAM_LOC[0], P[1] - CAM_LOC[1], P[2] - CAM_LOC[2])
    cx = d[0] * fwd[0] + d[1] * fwd[1] + d[2] * fwd[2]
    cy = d[0] * right[0] + d[1] * right[1] + d[2] * right[2]
    cz = d[0] * up[0] + d[1] * up[1] + d[2] * up[2]
    if cx <= 0.1:
        return None
    return (W / 2.0 + f_px * (cy / cx), H / 2.0 - f_px * (cz / cx))


# ---- 取帧 + YOLO 检测 ----
VIDEO = r"E:\output\_carla_video4\carla_tl_face_28s.mp4"
cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, FRAME_IDX)
ok, frame = cap.read()
cap.release()
out.append(f"取帧 {FRAME_IDX}: {ok}")

model = YOLO(r"E:\output\1\yolov8n.pt")
dets = []
if ok:
    r = model.predict(frame, conf=0.2, imgsz=1280, verbose=False)[0]
    for bx in r.boxes:
        if r.names[int(bx.cls)] != "traffic light":
            continue
        bb = [int(v) for v in bx.xyxy[0].tolist()]
        dets.append({"bbox": bb, "conf": round(float(bx.conf), 2),
                     "center": ((bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2)})
    out.append(f"YOLO 检出红绿灯 {len(dets)} 个:")
    for d in dets:
        out.append(f"   bbox={d['bbox']} conf={d['conf']} center={d['center']}")

out.append("")
out.append("=" * 84)
out.append("需要 CARLA 侧数据：请在 CARLA 运行时由本脚本另一部分查询")
out.append("=" * 84)

# ---- 尝试连 CARLA 拿灯珠世界坐标 ----
try:
    import carla
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    out.append("CARLA 已连接，查询灯珠世界坐标 -> 像素:")

    lamps = []
    for tl in world.get_actors().filter("traffic.traffic_light*"):
        for lb in tl.get_light_boxes():
            pr = project((lb.location.x, lb.location.y, lb.location.z))
            if pr is None:
                continue
            in_view = (0 <= pr[0] <= W) and (0 <= pr[1] <= H)
            lamps.append({
                "tl_id": tl.id,
                "state": str(tl.get_state()).split(".")[-1],
                "world": (round(lb.location.x, 2), round(lb.location.y, 2),
                          round(lb.location.z, 2)),
                "px": (round(pr[0], 1), round(pr[1], 1)),
                "ext": (round(lb.extent.x, 3), round(lb.extent.y, 3), round(lb.extent.z, 3)),
                "in_view": in_view,
            })
    iv = [l for l in lamps if l["in_view"]]
    out.append(f"  灯珠共 {len(lamps)} 个，其中落在画面内 {len(iv)} 个:")
    for l in iv:
        out.append(f"    tl_id={l['tl_id']:>3} state={l['state']:8} "
                   f"px=({l['px'][0]:>7.1f},{l['px'][1]:>7.1f})  ext={l['ext']}")

    # 与检测框匹配（像素距离 < 80px）
    out.append("")
    out.append("  与 YOLO 检测框的匹配（距离<80px）:")
    for d in dets:
        cx, cy = d["center"]
        best, bd = None, 1e9
        for l in iv:
            dd = math.hypot(l["px"][0] - cx, l["px"][1] - cy)
            if dd < bd:
                bd, best = dd, l
        if best and bd < 80:
            out.append(f"    检测框 center=({cx},{cy})  <->  tl_id={best['tl_id']} "
                       f"state={best['state']}  距离={bd:.0f}px  ✅ 匹配")
        else:
            out.append(f"    检测框 center=({cx},{cy})  <->  无匹配（最近 {bd:.0f}px）"
                       if best else f"    检测框 center=({cx},{cy})  <->  画面内无灯珠")

    # 画到帧上
    if ok:
        vis = frame.copy()
        for l in iv:
            px, py = int(l["px"][0]), int(l["px"][1])
            cv2.drawMarker(vis, (px, py), (0, 255, 255), cv2.MARKER_CROSS, 30, 3)
            cv2.putText(vis, f"tl{l['tl_id']} {l['state']}", (px + 8, py - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        for d in dets:
            x1, y1, x2, y2 = d["bbox"]
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 3)
        p = os.path.join(OUT, "tl_correspond.png")
        cv2.imwrite(p, vis)
        out.append("")
        out.append(f"  对应关系可视化（黄十字=投影的灯珠, 绿框=YOLO检出）: {p}")
except Exception as e:
    out.append(f"CARLA 不可用（{type(e).__name__}: {str(e)[:80]}）")
    out.append("  -> 需要先启动 CARLA 才能建立对应关系")

io.open(r"E:\output\_tl_correspond.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
