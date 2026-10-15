"""校验演示视频的 ROI 标注（2026-10-09 由 DSH 编写，只读）"""
import json
import urllib.parse
import urllib.request

import cv2

API = 'http://127.0.0.1:8001'


def scene_config(src):
    u = f'{API}/api/scene/config?source=' + urllib.parse.quote(src)
    return json.loads(urllib.request.urlopen(u, timeout=20).read().decode())


P = r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv'
j = scene_config(P)
d = j.get('data') or {}

print('=== 演示视频 scene 标注全文 ===')
for k, v in d.items():
    print(f'  {k:<22} = {json.dumps(v, ensure_ascii=False)[:120]}')

cap = cv2.VideoCapture(P)
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cap.release()

print('')
print(f'视频真实分辨率        = {W}x{H}')
print(f'标注 frame_width/height = {d.get("frame_width")}x{d.get("frame_height")}')
match = (d.get('frame_width') == W and d.get('frame_height') == H)
print(f'两者是否一致          = {"是" if match else "否  <-- 坐标基准不一致！"}')

print('')
print('=== 逐 ROI 校验 ===')
rois = d.get('traffic_light_roi') or []
for i, r in enumerate(rois):
    try:
        x1, y1, x2, y2 = [int(t) for t in r[:4]]
    except Exception:
        print(f'  ROI{i+1} 解析失败: {r}')
        continue
    inside = (0 <= x1 < x2 <= W) and (0 <= y1 < y2 <= H)
    # 画中画小窗大致范围（从历史截图看：右下角约 x>1240, y>690）
    pip = (x1 >= 1200 and y1 >= 660)
    print(f'  ROI{i+1} [{x1},{y1},{x2},{y2}]  在画面内={inside}'
          f'{"  位于右下角 -> 疑似 CAM-2 画中画小窗！" if pip else ""}')

print('')
print('=== 判定 ===')
if not rois:
    print('  该视频没有 ROI 标注')
else:
    bad = [r for r in rois
           if not (0 <= int(r[0]) < int(r[2]) <= W and 0 <= int(r[1]) < int(r[3]) <= H)]
    print(f'  ROI 总数 = {len(rois)}；越界 = {len(bad)} 个')
    if not match:
        print('  ⚠ 标注的画幅与视频真实分辨率不一致 -> 所有 ROI 的像素基准可能是错的')
