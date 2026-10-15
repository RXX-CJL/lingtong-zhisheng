"""诊断实时后端里违规归属失败的原因（打印违规结构 + 追踪框）"""

import io
import json
import sys
import urllib.request

sys.path.insert(0, r"E:\output\1\api")
import os  # noqa: E402
os.chdir(r"E:\output\1\api")

BASE = "http://127.0.0.1:8001"


def get(p):
    with urllib.request.urlopen(BASE + p, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


out = []
st = get("/api/realtime/status").get("data", {})
out.append(f"追踪车辆数={st.get('tracked_vehicle_count')} 违规计数={st.get('violation_count')}")

tv = get("/api/realtime/tracked-vehicles")
vehs = tv.get("data") or tv
if isinstance(vehs, dict):
    vehs = list(vehs.values())
out.append(f"\n当前追踪车辆 {len(vehs or [])} 辆:")
for v in (vehs or [])[:6]:
    if isinstance(v, dict):
        out.append(f"   id={v.get('id')} bbox={[int(x) for x in (v.get('bbox') or [])]}")

# 直接读后端实例属性（同进程不可达，改看 /vehicles 的原始 JSON）
dv = get("/api/realtime/vehicles").get("data", {})
out.append(f"\n/vehicles 结果: 左栏={len(dv.get('clean') or [])} "
           f"右栏={len(dv.get('violators') or [])} 未归属={len(dv.get('unassigned') or [])}")

un = dv.get("unassigned") or []
out.append(f"\n未归属条目（含 _stale_id 说明旧ID）:")
for x in un[:5]:
    out.append("   " + json.dumps(x, ensure_ascii=False))

# 通过 cloud 接口看后端内部的最近违规（若有暴露）
out.append("\n诊断：检查违规是否真的带 vehicle_id —— 需看后端日志")
p = os.path.join(os.environ.get("TEMP", "."), "api-r4.err")
if os.path.exists(p):
    lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    hits = [l for l in lines if "未归属" in l or "vehicle_id" in l or "归属" in l]
    out.append(f"日志中归属相关 {len(hits)} 行")
    for l in hits[-6:]:
        out.append("   " + l[:160])
io.open(r"E:\output\_attr_diag.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
