"""长时观察：违规是否带上有效 vehicle_id（右栏能否填充）"""

import io
import json
import time
import urllib.request

BASE = "http://127.0.0.1:8001"


def get(p):
    with urllib.request.urlopen(BASE + p, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", "ignore")).get("data", {})


out = []
seen_viol = 0
for i in range(8):
    time.sleep(12)
    try:
        d = get("/api/realtime/vehicles")
        s = get("/api/realtime/status")
        viol = d.get("violators") or []
        un = d.get("unassigned") or []
        cl = d.get("clean") or []
        seen_viol = max(seen_viol, len(viol))
        line = (f"[{(i+1)*12:>3}s] 追踪={s.get('tracked_vehicle_count')} 违规计数={s.get('violation_count')} "
                f"| 左栏={len(cl)} 右栏={len(viol)} 未归属={len(un)}")
        out.append(line)
        for x in viol[:3]:
            out.append(f"       [右] ID{x.get('track_id')} {x.get('primary_violation')} "
                       f"conf={x.get('confidence')} 旧ID={x.get('_stale_id')}")
        for x in un[:2]:
            out.append(f"       [未归属] {x.get('type_cn')} conf={x.get('confidence')}")
    except Exception as e:
        out.append(f"[{(i+1)*12:>3}s] 请求失败: {type(e).__name__}")

out.append("")
out.append(f"观察期内右栏最大车辆数: {seen_viol}")
io.open(r"E:\output\_right_panel.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
