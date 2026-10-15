"""
把 ROI 画到演示视频的真实帧上，核对"框的对不对"（2026-10-09 由 DSH 编写）

输出 E:\\output\\_roi_overlay.png（不修改任何业务数据）。
"""
import json
import urllib.parse
import urllib.request

import cv2

API = 'http://127.0.0.1:8001'
VIDEO = r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv'
OUT = r'E:\output\_roi_overlay.png'


def scene_config(src):
    u = f'{API}/api/scene/config?source=' + urllib.parse.quote(src)
    return (json.loads(urllib.request.urlopen(u, timeout=20).read().decode()).get('data') or {})


cfg = scene_config(VIDEO)
rois = [[int(t) for t in r[:4]] for r in (cfg.get('traffic_light_roi') or [])]
stop_y = cfg.get('stop_line_y')

cap = cv2.VideoCapture(VIDEO)
# 取有灯相位的一帧（红灯相位在 0~13.5s；20fps -> 第 150 帧 ≈ 7.5s）
cap.set(cv2.CAP_PROP_POS_FRAMES, 150)
ok, frame = cap.read()
cap.release()
if not ok:
    raise SystemExit('取帧失败')

H, W = frame.shape[:2]
print(f'帧 {W}x{H}   ROI 数 = {len(rois)}   stop_line_y = {stop_y}')

# 画 ROI（黄色）与中心点（红点）
for i, (x1, y1, x2, y2) in enumerate(rois):
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 215, 255), 3)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    cv2.circle(frame, (cx, cy), 6, (0, 0, 255), -1)
    cv2.putText(frame, f'ROI{i+1}', (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 215, 255), 2)
    print(f'  ROI{i+1} = [{x1},{y1},{x2},{y2}]  中心=({cx},{cy})  '
          f'尺寸={x2-x1}x{y2-y1}px')

if stop_y:
    cv2.line(frame, (0, int(stop_y)), (W, int(stop_y)), (255, 200, 0), 3)
    cv2.putText(frame, f'stop_line_y={stop_y}', (20, int(stop_y) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 200, 0), 2)

cv2.imwrite(OUT, frame)
print('')
print('已写出:', OUT)
print('提示：灯头在 1920x1080 上只有约 10~16 px 宽，所以 ROI 通常很小（40x40 上下）。')
print('      若某个 ROI 明显很大、或落在天空/地面/小窗上，说明框错了。')
