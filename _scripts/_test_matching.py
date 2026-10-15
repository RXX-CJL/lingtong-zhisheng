"""隔离测试：违规 -> 车辆 空间匹配逻辑是否有效"""

import json
import urllib.request

BASE = "http://127.0.0.1:8001"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


print("=" * 74)
print("1) 当前追踪车辆（bbox）")
print("=" * 74)
tv = get("/api/realtime/tracked-vehicles")
vehs = tv.get("data") or tv
if isinstance(vehs, dict):
    vehs = list(vehs.values())
for v in (vehs or [])[:6]:
    if isinstance(v, dict):
        print(f"  id={v.get('id')} bbox={v.get('bbox')} class={v.get('class_name')} "
              f"hist={len(v.get('history') or [])} speed={v.get('speed')}")

print()
print("=" * 74)
print("2) 当前违规对象（看有无 track_id / bbox）")
print("=" * 74)
st = get("/api/realtime/status")
print(f"  violation_count={st.get('data', {}).get('violation_count')}")

# 通过 /vehicles 看分流
dv = get("/api/realtime/vehicles").get("data", {})
print(f"  clean={len(dv.get('clean') or [])}  violators={len(dv.get('violators') or [])}")
for x in (dv.get("clean") or [])[:3]:
    print(f"    [clean] ID{x.get('track_id')} {x.get('class_name_cn')} "
          f"kmh={x.get('speed_kmh')} conf={x.get('speed_confidence')}")
for x in (dv.get("violators") or [])[:3]:
    print(f"    [violator] ID{x.get('track_id')} {x.get('primary_violation')} "
          f"conf={x.get('confidence')}")

print()
print("=" * 74)
print("3) 标定器隔离测试（用场景标注）")
print("=" * 74)
import os
import sys
sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")
from speed_calibration import SpeedCalibrator, speed_from_history, judge_speeding  # noqa: E402

SCENE = {"pixel_per_meter": 10.0, "ppm_ref_y": 432, "crosswalk_zones":
         [[[400, 380], [900, 380], [900, 470], [400, 470]]]}
cal = SpeedCalibrator(SCENE, frame_width=1280, frame_height=576)
print(f"  {cal.info()}")

# 构造一条真实感的轨迹：以 40px/s 移动 2 秒
hist = [{"center": [100 + 40 * i * 0.5, 400], "timestamp": 1000.0 + i * 0.5}
        for i in range(5)]
est = speed_from_history(hist, cal)
print(f"  合成轨迹(40px/s @ y=400): {est}")

# 超速判定
for kmh in (0.7, 40, 55, 65, 75):
    over, ratio = judge_speeding(kmh, 60.0, 0.10)
    print(f"    {kmh:>5} km/h (限速60,容差10%) -> {'超速' if over else '正常'}  超出={ratio:.2%}")
