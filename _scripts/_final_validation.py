"""端到端验证：真值 vs 实测（终于有条件做了）

数据：
  · 真值 CSV: 1120 行（车A 正常 30km/h、车B 闯红灯 35km/h，视野内 630 样本）
  · 实测: /api/realtime/vehicles 的 speed_px / speed_kmh

判定目标：
  ① 测速数量级对不对（真值 21-30 km/h，实测多少？）
  ② 标定 ppm 是否需要修（用像素位移反推）
  ③ 误报率（2 辆车的简单场景）
"""

import csv
import io
import json
import urllib.request

BASE = "http://127.0.0.1:8001"
CSV_P = r"E:\output\_carla_video3\ground_truth.csv"
out = []


def get(p):
    with urllib.request.urlopen(BASE + p, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "ignore")).get("data", {})


# ---- 实测 ----
vh = get("/api/realtime/vehicles")
st = get("/api/realtime/status")
clean = vh.get("clean") or []
viol = vh.get("violators") or []
un = vh.get("unassigned") or []
sc = vh.get("speed_calibration") or {}

out.append("=== 实测 ===")
out.append(f"  处理帧={st.get('processed_frames')}  左栏={len(clean)}  右栏={len(viol)}  未归属={len(un)}")
out.append(f"  标定: {sc.get('method')}  ppm={sc.get('ppm_ref')}  y_ref={sc.get('y_ref')}")
out.append("")
out.append(f"  {'ID':>5} {'px/s':>9} {'实测km/h':>9} {'质量':8} {'可信度':10} {'bbox'}")
for x in clean + viol:
    bb = x.get("bbox") or []
    out.append(f"  {str(x.get('track_id')):>5} {str(x.get('speed_px')):>9} "
               f"{str(x.get('speed_kmh')):>9} {str(x.get('speed_quality')):8} "
               f"{str(x.get('speed_confidence')):10} "
               f"{[int(v) for v in bb[:4]] if len(bb)>=4 else ''}")

# ---- 真值 ----
gt = {}
for r in csv.DictReader(open(CSV_P, encoding="utf-8")):
    if r["in_view"] == "1":
        gt.setdefault(r["tag"], []).append(r)

out.append("")
out.append("=== 真值（仅视野内样本）===")
for tag, rs in gt.items():
    sp = [float(r["speed_kmh"]) for r in rs]
    out.append(f"  {tag:12s} {len(rs):>4} 样本  "
               f"avg={sum(sp)/len(sp):5.1f}  min={min(sp):5.1f}  max={max(sp):5.1f} km/h")

# ---- 关键：用实测 px/s 反推需要的 ppm ----
out.append("")
out.append("=" * 74)
out.append("关键分析：用实测像素速度反推「正确 ppm」")
out.append("=" * 74)
out.append("  原理: km/h = (px/s ÷ ppm) × 3.6   =>   ppm = px/s × 3.6 ÷ km/h")
out.append("")
for x in clean + viol:
    pxs = x.get("speed_px")
    if not isinstance(pxs, (int, float)) or pxs <= 0:
        continue
    for tag, rs in gt.items():
        sp = sum(float(r["speed_kmh"]) for r in rs) / len(rs)
        need_ppm = pxs * 3.6 / sp
        out.append(f"  若 ID{x.get('track_id')} 对应真值 {tag}({sp:.1f}km/h):")
        out.append(f"     当前 ppm={sc.get('ppm_ref')}  ->  实测 {x.get('speed_kmh')} km/h")
        out.append(f"     需要的 ppm = {need_ppm:.1f}   "
                   f"(即当前 ppm 需 ×{need_ppm/float(sc.get('ppm_ref') or 1):.2f})")
        break

# ---- 误报 ----
out.append("")
out.append("=" * 74)
out.append("误报/漏报")
out.append("=" * 74)
out.append(f"  场景: 2 辆车（1 正常 + 1 闯红灯）")
out.append(f"  实测报告违规: {len(viol)} 辆 + {len(un)} 条未归属")
for x in viol:
    out.append(f"    ID{x.get('track_id')} {x.get('primary_violation')} "
               f"conf={x.get('primary_confidence')}")
out.append(f"  真值: 应有 1 起闯红灯（车B 在 t=4.05s 后红灯通过）")

io.open(r"E:\output\_final_validation.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
