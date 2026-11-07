# -*- coding: utf-8 -*-
"""验证 _world_state.py 的 diff 能真的抓到污染（故意改一个灯配时）。"""
import importlib.util, json, subprocess, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("ws", r"E:\output\_scripts\_world_state.py")
ws = importlib.util.module_from_spec(spec); spec.loader.exec_module(ws)

_, world = ws.connect()
before = ws.snapshot(world)
Path(r"E:\output\_scripts\_ws_baseline.json").write_text(
    json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8")
print("基线已存：actor=%d, lights=%d" % (before["actor_total"], len(before["traffic_lights"])))

# 1) 未改动时应报告一致
after = ws.snapshot(world)
ok, problems = ws.diff(before, after)
print("未改动 -> ok=%s, 差异数=%d" % (ok, len(problems)))

# 2) 故意改一盏灯配时，必须被抓到
lights = list(world.get_actors().filter("traffic.traffic_light*"))
target = lights[0]
orig = (target.get_green_time(), target.get_yellow_time(), target.get_red_time())
target.set_green_time(orig[0] + 7.0)
world.wait_for_tick(2.0)
dirty = ws.snapshot(world)
ok2, problems2 = ws.diff(before, dirty)
print("改了配时 -> ok=%s, 差异数=%d" % (ok2, len(problems2)))
for p in problems2[:3]:
    print("   ", p)

# 3) 恢复后必须又一致
target.set_green_time(orig[0])
world.wait_for_tick(2.0)
restored = ws.snapshot(world)
ok3, problems3 = ws.diff(before, restored)
print("恢复后 -> ok=%s, 差异数=%d" % (ok3, len(problems3)))

print("\nRESULT:", "PASS" if (ok and not ok2 and ok3) else "FAIL")
