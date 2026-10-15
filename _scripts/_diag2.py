"""直接读实时后端实例的违规对象（同机器，用 HTTP 暴露不了就写临时端点）"""

import io
import json
import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

import urllib.request  # noqa: E402

BASE = "http://127.0.0.1:8001"
out = []


def get(p):
    with urllib.request.urlopen(BASE + p, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


# 用 /vehicles 的 unassigned 看到的是精简后的 entry，拿不到 location。
# 改用 /realtime/status 的 tracked_vehicles（若有）+ 追踪车辆 bbox 对比。
st = get("/api/realtime/status").get("data", {})
out.append(f"追踪={st.get('tracked_vehicle_count')}  违规计数={st.get('violation_count')}")

tv = get("/api/realtime/tracked-vehicles")
vehs = tv.get("data") or tv
if isinstance(vehs, dict):
    vehs = list(vehs.values())
out.append(f"追踪车辆（含 bbox）:")
for v in (vehs or [])[:8]:
    if isinstance(v, dict):
        out.append(f"   id={v.get('id')} bbox={[int(x) for x in (v.get('bbox') or [])]} "
                   f"class={v.get('class_name')} speed={v.get('speed')}")

dv = get("/api/realtime/vehicles").get("data", {})
out.append(f"左={len(dv.get('clean') or [])} 右={len(dv.get('violators') or [])} "
           f"未归属={len(dv.get('unassigned') or [])}")
for x in (dv.get("unassigned") or [])[:4]:
    out.append("   未归属: " + json.dumps(x, ensure_ascii=False))

# 关键：读后端日志里我们加的 debug（vehicle_id 回填失败？）
for fn in ("api-r5.err", "api-r5.log"):
    p = os.path.join(os.environ.get("TEMP", "."), fn)
    if not os.path.exists(p):
        continue
    lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    keys = ["回填失败", "归属", "vehicle_id", "追踪失败", "行为分析失败"]
    for k in keys:
        hits = [l for l in lines if k in l]
        out.append(f"日志[{fn}] \"{k}\": {len(hits)} 行")
        for l in hits[-3:]:
            out.append("      " + l[:150])
io.open(r"E:\output\_attr_diag2.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
