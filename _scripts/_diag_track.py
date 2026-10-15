"""诊断：为什么全部车辆都是「轨迹断裂」？

背景（现场证据，Edge 截图）：
  CARLA 2K 视频里 5 辆车全部标红 "轨迹断裂"，px/s 只有 0.1~0.7
  而旧 bilibili 视频里有车是 5.2px/s（非断裂）

对照基准：
  CARLA 里 20 km/h 的车，在 y=720 处应约 128 px/s
  实测 0.1~0.7 px/s -> 差 200~1000 倍

两种可能（需数据判定）：
  A) 追踪到的车**本来就没动**（CARLA 场景里确实有静止车）
  B) **跟踪器每帧换 ID** -> 每条轨迹只有 1~2 个点 -> 位移算不出（"断裂"）
"""

import io
import json
import urllib.request

BASE = "http://127.0.0.1:8001"
out = []


def get(p):
    with urllib.request.urlopen(BASE + p, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "ignore")).get("data", {})


st = get("/api/realtime/status")
out.append("=== 检测状态 ===")
for k in ("running", "source_kind", "processed_frames", "tracked_vehicle_count",
          "violation_count", "avg_fps"):
    out.append(f"  {k:24s} = {st.get(k)}")
out.append(f"  video_path = {str(st.get('video_path'))[-50:]}")

vh = get("/api/realtime/vehicles")
clean = vh.get("clean") or []
bad = vh.get("violators") or []

out.append("")
out.append("=" * 76)
out.append("逐车测速细节（关键：samples 有几个点？）")
out.append("=" * 76)
hdr = f"  {'ID':>5} {'类型':6} {'px/s':>8} {'km/h':>7} {'原始':>7} {'质量':10} {'可信度':10} {'帧率':>6}"
out.append(hdr)
for x in clean + bad:
    out.append(f"  {str(x.get('track_id')):>5} {str(x.get('class_name_cn')):6} "
               f"{str(x.get('speed_px')):>8} {str(x.get('speed_kmh')):>7} "
               f"{str(x.get('speed_kmh_raw')):>7} {str(x.get('speed_quality')):10} "
               f"{str(x.get('speed_confidence')):10} {str(x.get('speed_fps')):>6}")

out.append("")
out.append("=== 车辆对象里都有哪些字段（找轨迹/采样信息）===")
if clean:
    keys = sorted(clean[0].keys())
    out.append(f"  {len(keys)} 个字段:")
    for k in keys:
        v = clean[0].get(k)
        s = str(v)
        out.append(f"     {k:26s} = {s[:70]}")

out.append("")
out.append("=== 标定信息 ===")
sc = vh.get("speed_calibration") or {}
for k, v in sc.items():
    out.append(f"  {k:26s} = {str(v)[:90]}")

out.append("")
out.append("=== 汇总判定 ===")
if clean:
    pxs = [x.get("speed_px") for x in clean if isinstance(x.get("speed_px"), (int, float))]
    quals = [x.get("speed_quality") for x in clean]
    from collections import Counter
    out.append(f"  px/s 范围: {min(pxs):.2f} ~ {max(pxs):.2f}" if pxs else "  无 px 数据")
    out.append(f"  质量分布: {dict(Counter(quals))}")
    out.append("")
    if pxs and max(pxs) < 2.0:
        out.append("  ⚠ px/s 全部 <2 -> 两种可能：")
        out.append("     A) 追踪的是静止车辆（CARLA 场景里确实有停车）")
        out.append("     B) 跟踪器频繁换 ID，轨迹点数太少")
    breaks = [q for q in quals if q and q != "ok"]
    if len(breaks) == len(quals) and quals:
        out.append(f"  ⚠ 100% 车辆质量异常（{len(breaks)}/{len(quals)}）-> 需要查轨迹点数")

io.open(r"E:\output\_diag_track.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
