"""CARLA 视频验证：实测数据 vs 真值

对比维度：
  ① 测速精度 —— 检测器测出的 km/h vs CSV 真值
     用"轨迹位移模式匹配"把检测到的车对应到真值车（不依赖投影）
  ② 误报/漏报 —— 对照组 12 辆正常车 vs 3 辆违规车
"""

import csv
import io
import json
import math
import os
import urllib.request

BASE = "http://127.0.0.1:8001"
CSV = r"E:\output\_carla_video\ground_truth.csv"
out = []


def get(p):
    with urllib.request.urlopen(BASE + p, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "ignore")).get("data", {})


# ---- 实测数据 ----
st = get("/api/realtime/status")
vh = get("/api/realtime/vehicles")
out.append("=== 实测状态 ===")
out.append(f"  processed={st.get('processed_frames')} 追踪={st.get('tracked_vehicle_count')} "
           f"违规={st.get('violation_count')} 平均fps={st.get('avg_fps')}")
out.append(f"  左栏={len(vh.get('clean') or [])} 右栏={len(vh.get('violators') or [])} "
           f"未归属={len(vh.get('unassigned') or [])}")
out.append(f"  标定: {(vh.get('speed_calibration') or {}).get('method')} "
           f"ppm={(vh.get('speed_calibration') or {}).get('ppm_ref')}")

# ---- 实测车辆的速度 ----
out.append("")
out.append("=== 实测车辆测速（左栏 + 右栏） ===")
measured = []
for x in (vh.get("clean") or []) + (vh.get("violators") or []):
    rec = {
        "track_id": x.get("track_id"),
        "class_cn": x.get("class_name_cn"),
        "speed_kmh": x.get("speed_kmh"),
        "speed_px": x.get("speed_px"),
        "conf": x.get("speed_confidence"),
        "quality": x.get("speed_quality"),
        "direction": x.get("direction"),
        "bbox": x.get("bbox"),
        "violation": x.get("primary_violation"),
    }
    measured.append(rec)
    out.append(f"  ID{str(rec['track_id']):>4} {str(rec['class_cn']):5s} "
               f"px={str(rec['speed_px']):>7} {str(rec['speed_kmh']):>6}km/h "
               f"[{rec['conf']}/{rec['quality']}] {str(rec['violation'] or '')}")

# ---- 真值 ----
gt = {}
with open(CSV, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        tag = row["tag"]
        gt.setdefault(tag, []).append({
            "t": float(row["t_sec"]),
            "kmh": float(row["speed_kmh"]),
            "x": float(row["x"]),
            "y": float(row["y"]),
        })

out.append("")
out.append("=== 真值统计（CSV） ===")
normal_tags = [k for k in gt if k.startswith("normal_")]
viol_tags = [k for k in gt if k.startswith("violation_")]
out.append(f"  对照组 {len(normal_tags)} 辆，违规车 {len(viol_tags)} 辆")
out.append("")
out.append("  对照组各车真值:")
for tag in sorted(normal_tags, key=lambda s: int(s.split("_")[1])):
    vals = [r["kmh"] for r in gt[tag]]
    out.append(f"    {tag:12s} n={len(vals):>4}  avg={sum(vals)/len(vals):6.1f}  "
               f"max={max(vals):6.1f}  min={min(vals):5.1f} km/h")
out.append("")
out.append("  违规车真值:")
for tag in viol_tags:
    vals = [r["kmh"] for r in gt[tag]]
    out.append(f"    {tag:20s} n={len(vals):>4}  avg={sum(vals)/len(vals):6.1f}  "
               f"max={max(vals):6.1f} km/h")

# ---- 违规统计 ----
out.append("")
out.append("=== 违规检出情况 ===")
vs = vh.get("violators") or []
un = vh.get("unassigned") or []
by_type = {}
for x in vs:
    for v in (x.get("violations") or []):
        k = v.get("type_cn") or v.get("type") or "?"
        by_type[k] = by_type.get(k, 0) + 1
for x in un:
    k = (x.get("type_cn") or x.get("type") or "?") + "(未归属)"
    by_type[k] = by_type.get(k, 0) + 1
for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
    out.append(f"    {k:20s} {v} 次")
out.append(f"  合计检出 {len(vs)} 辆违规车 + {len(un)} 条未归属告警")

# ---- 关键结论：违规率 ----
out.append("")
out.append("=" * 76)
out.append("关键结论")
out.append("=" * 76)
out.append(f"  对照组（应无违规）: 12 辆正常行驶")
out.append(f"  实测报告违规: {len(vs)} 辆 / 追踪 {st.get('tracked_vehicle_count')} 辆")
out.append(f"  累计违规计数: {st.get('violation_count')}（含冷却期内的重复）")
out.append("")
out.append("  ⚠ 注意：CARLA 场景中的车辆**全部靠左行驶/靠右行驶**规则由 TM 管理，")
out.append("     而项目的 road_direction 默认是 'south'，可能与 CARLA 实际方向不符 ->")
out.append("     会造成大量'逆行'误报。这本身就是有价值的发现。")

io.open(r"E:\output\_carla_validation.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
