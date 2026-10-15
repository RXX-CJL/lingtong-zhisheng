"""查后端进程内车牌缓存是否被填充 + 长时间观察"""

import json
import os
import time
import urllib.request

BASE = "http://127.0.0.1:8001"


def status():
    with urllib.request.urlopen(BASE + "/api/realtime/status", timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "ignore")).get("data", {})


print("=" * 72)
print("轮询 90 秒，观察车牌与红绿灯")
print("=" * 72)
for i in range(9):
    time.sleep(10)
    d = status()
    tls = d.get("traffic_light_stats") or {}
    print(f"  [{i*10+10:3d}s] processed={d.get('processed_frames'):>5} "
          f"违规={d.get('violation_count'):>3} 追踪={d.get('tracked_vehicle_count'):>3} "
          f"| 红绿灯 total={tls.get('total')} none丢弃={tls.get('none_dropped')} "
          f"cnn={tls.get('cnn')} 确认={d.get('traffic_light_confirmed')}")

print()
print("=" * 72)
print("后端日志中的车牌记录")
print("=" * 72)
p = os.path.join(os.environ.get("TEMP", "."), "api-final.err")
if os.path.exists(p):
    import io
    lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    hits = [l for l in lines if "车牌" in l or "plate" in l.lower()]
    print(f"  命中 {len(hits)} 行")
    for l in hits[-8:]:
        try:
            print("  " + l[:150])
        except Exception:
            pass
    print()
    print(f"  日志总行数 {len(lines)}，最后 3 行:")
    for l in lines[-3:]:
        try:
            print("  " + l[:150])
        except Exception:
            pass
