# -*- coding: utf-8 -*-
"""在两个"场景标注键"之间复制标注（2026-10-10 由 DSH 编写）

## 为什么需要它
`scene_annotation.video_key` 是**整条源路径的 sha1**，所以同一段录像的
**不同编码 / 容器**（`dual_cam_demo_lossless.mkv` vs `dual_cam_demo_h264.mp4`）
是两个不同的键，标注**不共用**。换素材时会让人工标定
（信号灯 ROI / 停止线 / 相机几何）**静默失效** —— 界面只表现为 `scope=frame`，
而灯态一失效，闯红灯判定就退化成"画面里任意一盏灯"，每循环误报 5~7 次。

我试过在 `load_scene` 里做"同文件名主干兜底匹配"，但**实测不成立**
（`dual_cam_demo_h264_` 与 `dual_cam_demo_lossless_` 前缀不同，要命中就得放宽到
`dual_cam_demo_`，那会把同目录所有视频混成一个标注）。所以改成**显式动作**：
需要共用就显式跑一次本脚本。这样"共用"是看得见的一步，不是隐式规则。

## 安全
· **只新增**目标键的文件，**不改、不删**源文件；
· 目标已存在时**默认拒绝**（要覆盖得显式加 `--force`，且会先备份成 `.bak`）；
· 复制后打印两边读到什么，便于核对。

用法：
  python _copy_scene_config.py <源视频路径> <目标视频路径> [--force]
输出纯 ASCII。
"""
import json
import os
import shutil
import sys

sys.path.insert(0, r'E:\output\1\api')
from scene_annotation import SCENE_DIR, _path_for, load_scene, video_key  # noqa: E402

if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)

src, dst = sys.argv[1], sys.argv[2]
force = '--force' in sys.argv[3:]

sp, dp = _path_for(src), _path_for(dst)
print('source key : %s' % video_key(src))
print('  file     : %s' % sp)
print('target key : %s' % video_key(dst))
print('  file     : %s' % dp)

if not os.path.exists(sp):
    print('RESULT: FAIL - 源标注不存在，无可复制')
    sys.exit(2)

if os.path.exists(dp) and not force:
    same = False
    try:
        with open(sp, 'r', encoding='utf-8') as a, open(dp, 'r', encoding='utf-8') as b:
            same = json.load(a) == json.load(b)
    except Exception:
        pass
    print('RESULT: SKIP - 目标标注已存在（%s）。内容相同=%s；如需覆盖请加 --force'
          % (os.path.basename(dp), same))
    sys.exit(0 if same else 3)

try:
    if os.path.exists(dp):
        bak = dp + '.bak'
        shutil.copy2(dp, bak)
        print('已备份原目标 -> %s' % os.path.basename(bak))
    shutil.copy2(sp, dp)
except Exception as e:
    print('RESULT: FAIL - %s: %s' % (type(e).__name__, e))
    sys.exit(4)

for label, p in (('源', sp), ('目标', dp)):
    d = {}
    try:
        with open(p, 'r', encoding='utf-8') as f:
            d = json.load(f)
    except Exception:
        pass
    print('  %s: ROI=%d  stop_line_y=%s  相机参数齐全=%s  斑马线=%d'
          % (label, len(d.get('traffic_light_roi') or []), d.get('stop_line_y'),
             all(d.get(k) is not None
                 for k in ('camera_height_m', 'camera_pitch_deg', 'fov_deg', 'camera_yaw_deg')),
             len(d.get('crosswalk_zones') or [])))

print('RESULT: OK - 标注已复制（原文件未改动）')
