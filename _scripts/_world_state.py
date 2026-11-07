# -*- coding: utf-8 -*-
r"""世界状态快照 / 差异检测：给"跑完必须还原干净"提供可断言的工具。

用法：
    py -3.12 world_state.py snapshot      # 打印当前状态 JSON
    py -3.12 world_state.py diff A.json   # 与存档对比，列出差异
    py -3.12 world_state.py check         # 与内置基线对比（基线见 BASELINE）

设计动机（真实教训）：
  2026-10-23 第 4 批 ① 交付时，"世界干净"只查了 actor 数量，
  结果红绿灯配时被永久改成 12/2/15 却没人发现。
  → 凡是写进服务器的世界状态都必须逐项断言：actor / 配时 / 天气 / 机位 / 装饰物可见性。
"""
import json
import sys
import time

import carla

HOST = "127.0.0.1"
PORT = 2000
ENV_LABELS = ("Vegetation", "Poles", "Fences", "Buildings", "Walls", "TrafficSigns")
LABEL_MAP = {name: getattr(carla.CityObjectLabel, name) for name in ENV_LABELS}

# 用户机位基线（2026-10-23 用户调好的机位）
BASELINE_SPECTATOR = {
    "location": {"x": -172.196579, "y": 183.859116, "z": 27.638052},
    "rotation": {"pitch": 0.0, "yaw": -45.592178, "roll": 0.0},
}


def snapshot(world):
    actors = world.get_actors()
    lights = list(actors.filter("traffic.traffic_light*"))
    t = world.get_spectator().get_transform()
    env = {}
    for name, label in LABEL_MAP.items():
        env[name] = len(world.get_environment_objects(label))
    return {
        "map": world.get_map().name,
        "actor_total": len(actors),
        "actors": {
            "vehicle": len(actors.filter("vehicle.*")),
            "walker": len(actors.filter("walker.*")),
            "prop": len(actors.filter("static.prop.*")),
            "camera": len(actors.filter("sensor.camera.*")),
            "light": len(lights),
        },
        "traffic_lights": [
            {
                "id": int(l.id),
                "opendrive_id": str(l.get_opendrive_id()),
                "green": round(float(l.get_green_time()), 3),
                "yellow": round(float(l.get_yellow_time()), 3),
                "red": round(float(l.get_red_time()), 3),
            }
            for l in lights
        ],
        "environment": env,
        "spectator": {
            "location": {"x": t.location.x, "y": t.location.y, "z": t.location.z},
            "rotation": {"pitch": t.rotation.pitch, "yaw": t.rotation.yaw, "roll": t.rotation.roll},
        },
        "taken_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def diff(a, b, tol_dist=0.01, tol_angle=0.05):
    """返回 (ok, 差异行列表)。a = 之前，b = 现在。"""
    problems = []

    if a.get("map") != b.get("map"):
        problems.append("地图变了: %s -> %s" % (a.get("map"), b.get("map")))

    if a.get("actor_total") != b.get("actor_total"):
        problems.append("actor 总数变了: %s -> %s" % (a.get("actor_total"), b.get("actor_total")))

    for key, before in (a.get("actors") or {}).items():
        now = (b.get("actors") or {}).get(key)
        if before != now:
            problems.append("actor[%s] 变了: %s -> %s" % (key, before, now))

    before_lights = {x["id"]: x for x in (a.get("traffic_lights") or [])}
    now_lights = {x["id"]: x for x in (b.get("traffic_lights") or [])}
    for lid, before in before_lights.items():
        now = now_lights.get(lid)
        if now is None:
            problems.append("红绿灯 id=%s 消失了" % lid)
            continue
        for k in ("green", "yellow", "red"):
            if abs(float(before[k]) - float(now[k])) > 1e-3:
                problems.append("红绿灯 odr=%s 的 %s 配时变了: %s -> %s"
                                % (before["opendrive_id"], k, before[k], now[k]))
    for lid in now_lights:
        if lid not in before_lights:
            problems.append("多出红绿灯 id=%s" % lid)

    for key, before in (a.get("environment") or {}).items():
        now = (b.get("environment") or {}).get(key)
        if before != now:
            problems.append("装饰物[%s] 数量变了: %s -> %s" % (key, before, now))

    sp_a, sp_b = a.get("spectator") or {}, b.get("spectator") or {}
    for axis in ("x", "y", "z"):
        va = (sp_a.get("location") or {}).get(axis)
        vb = (sp_b.get("location") or {}).get(axis)
        if va is not None and vb is not None and abs(va - vb) > tol_dist:
            problems.append("机位 location.%s 变了: %.4f -> %.4f" % (axis, va, vb))
    for axis in ("pitch", "yaw", "roll"):
        va = (sp_a.get("rotation") or {}).get(axis)
        vb = (sp_b.get("rotation") or {}).get(axis)
        if va is not None and vb is not None and abs(va - vb) > tol_angle:
            problems.append("机位 rotation.%s 变了: %.4f -> %.4f" % (axis, va, vb))

    return (not problems), problems


def connect():
    client = carla.Client(HOST, PORT)
    client.set_timeout(20.0)
    return client, client.get_world()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    action = sys.argv[1]
    _, world = connect()

    if action == "snapshot":
        print(json.dumps(snapshot(world), ensure_ascii=False, indent=2))
        return 0

    if action == "check":
        _, problems = diff({"spectator": BASELINE_SPECTATOR}, snapshot(world))
        # 只关心机位那一部分
        problems = [p for p in problems if p.startswith("机位")]
        if problems:
            print("机位与基线不一致：")
            for p in problems:
                print("  - " + p)
            return 1
        print("机位与基线一致")
        return 0

    if action == "diff":
        if len(sys.argv) < 3:
            print("用法: world_state.py diff <快照.json>")
            return 2
        with open(sys.argv[2], "r", encoding="utf-8") as f:
            before = json.load(f)
        ok, problems = diff(before, snapshot(world))
        if ok:
            print("与快照一致，世界已还原干净")
            return 0
        print("发现 %d 处差异：" % len(problems))
        for p in problems:
            print("  - " + p)
        return 1

    print("未知动作: %s" % action)
    return 2


if __name__ == "__main__":
    sys.exit(main())
