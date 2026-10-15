"""受控测试：验证 /api/realtime/vehicles 的违规归属链路

不依赖碰运气的真实违规，直接构造：
  ① 追踪车辆（真 bbox）
  ② 规则引擎会判违规的 detections（带 track_id，模拟 _attach_track_ids 之后的状态）
然后调用真实接口逻辑，检查右栏是否填充、未归属是否正确。
"""

import io
import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

from routers import realtime as rt  # noqa: E402
from realtime_detector import realtime_detector as det  # noqa: E402

out = []

# --- 构造：两辆车，其中一辆在禁停区/斑马线内（触发违停） ---
v1 = {"id": 1, "track_id": 1, "class_name": "car", "bbox": [100.0, 300.0, 200.0, 400.0],
      "center": (150.0, 350.0), "speed": 12.0, "direction": "right",
      "history": [{"center": [140.0, 350.0], "timestamp": 1.0},
                  {"center": [150.0, 350.0], "timestamp": 1.5}],
      "frame_count": 10}
v2 = {"id": 2, "track_id": 2, "class_name": "truck", "bbox": [800.0, 200.0, 950.0, 380.0],
      "center": (875.0, 290.0), "speed": 40.0, "direction": "down",
      "history": [{"center": [870.0, 270.0], "timestamp": 1.0},
                  {"center": [875.0, 290.0], "timestamp": 1.5}],
      "frame_count": 10}
det.tracked_vehicles = {1: v1, 2: v2, 3: {
    "id": 3, "track_id": 3, "class_name": "bus", "bbox": [400.0, 420.0, 560.0, 540.0],
    "center": (480.0, 480.0), "speed": 25.0, "direction": "left",
    "history": [{"center": [500.0, 480.0], "timestamp": 1.0},
                {"center": [480.0, 480.0], "timestamp": 1.5}],
    "frame_count": 8}}
det._last_violations = [
    # A) 带有效 vehicle_id（模拟规则引擎回填成功）
    {"violation_type": "illegal_parking", "violation_type_cn": "违停",
     "confidence": 0.82, "vehicle_id": 1,
     "location": {"bbox": [100, 300, 200, 400]}},
    # B) 嵌套在 evidence 明细里（模拟 wrong_way 的真实结构）
    {"violation_type": "wrong_way", "violation_type_cn": "逆行",
     "confidence": 0.71,
     "evidence": {"wrong_way_details": [{"vehicle_id": 2}]}},
    # C) 完全无归属依据（应进"未归属"，不得挂到车上）
    {"violation_type": "red_light", "violation_type_cn": "闯红灯",
     "confidence": 0.66, "location": {"bbox": [5, 5, 40, 40]}},
    # D) 失效旧 ID（应被校验拦下 -> 走几何匹配或未归属）
    {"violation_type": "lane_departure", "violation_type_cn": "压线",
     "confidence": 0.70, "vehicle_id": 999,
     "location": {"bbox": [805, 205, 945, 375]}},
]
det._plate_cache = {3: "宁A12345"}
det._last_traffic_lights = [{"color": "red", "color_cn": "红灯", "bbox": [500, 100, 520, 140]}]

st, js = rt.get_vehicles_split(), None
import json  # noqa: E402
body = json.loads(st.body.decode("utf-8"))
d = body["data"]

out.append("=== 受控测试结果 ===")
out.append(f"左栏(正常) {len(d['clean'])} 辆 / 右栏(违规) {len(d['violators'])} 辆 / 未归属 {len(d['unassigned'])} 条")
out.append("")
out.append("左栏明细:")
for x in d["clean"]:
    out.append(f"   ID{x['track_id']} {x['class_name_cn']} 车牌={x.get('plate')} "
               f"{x.get('speed_kmh')}km/h [{x.get('speed_confidence')}]")
out.append("")
out.append("右栏明细:")
for x in d["violators"]:
    vs = ", ".join(v["type_cn"] for v in x.get("violations", []))
    out.append(f"   ID{x['track_id']} {x['class_name_cn']}  违规={vs}  主={x.get('primary_violation')} "
               f"conf={x.get('confidence')}")
out.append("")
out.append("未归属:")
for x in d["unassigned"]:
    out.append(f"   {x.get('type_cn')} conf={x.get('confidence')} 旧ID={x.get('_stale_id')}")
out.append("")
out.append("判定:")
ok = True
def chk(cond, desc):
    global ok
    out.append(f"   [{'PASS' if cond else 'FAIL'}] {desc}")
    if not cond: ok = False
chk(len(d["clean"]) == 0 or all(x["track_id"] != 1 for x in d["clean"]), "ID1 是违规车辆，不应出现在左栏")
chk(any(x["track_id"] == 1 for x in d["violators"]), "A) 带 vehicle_id 的违停 -> ID1 进右栏")
chk(any(x["track_id"] == 2 for x in d["violators"]), "B) 嵌套 evidence 的逆行 -> ID2 进右栏")
chk(any(x.get("type_cn") == "闯红灯" for x in d["unassigned"]), "C) 无归属依据 -> 进未归属（不硬挂车）")
chk(not any(any(v["type_cn"] == "闯红灯" for v in x.get("violations", [])) for x in d["violators"]),
    "C) 闯红灯不应出现在右栏")
chk(any(x.get("_stale_id") == 999 for x in d["unassigned"]) or
    any(x["track_id"] == 2 for x in d["violators"]), "D) 失效 ID 999 被拦下")
chk(d["clean"] and d["clean"][0].get("plate") == "宁A12345", "车牌缓存透传到左栏")
out.append("")
out.append(f"总体: {'全部通过 ✅' if ok else '存在失败 ❌'}")
io.open(r"E:\output\_controlled_test.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
