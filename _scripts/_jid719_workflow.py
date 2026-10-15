"""让 CARLA 窗口"看得见"作业过程 + 实测 junction 719 可用性

用户要求：
  "刚刚你虽然打开了carla窗口，但是他一直是默认视角，没有变化，
   能不能让我看到你实际的工作流程（比如移动或瞬移到这个路口，
   生成车辆，尝试移动等行为），不然每次只有截图效率很慢"

做法：
  ① 用 world.get_spectator() 拿到窗口相机
  ② 把它瞬移到 junction 719 上方（俯视），用户就能看到这个路口
  ③ 在该路口尝试生成车辆、开 autopilot，让用户看到车真的在动
  ④ 把每个步骤的 spectator 位置打印出来（用户可对照窗口确认）

注意：spectator 是 CARLA 自己的窗口视角；我架设的"演示相机"是独立 actor，
      它拍到什么仍需要抓帧给用户看。但生成/移动车辆的行为，用户能实时看到。
"""

import io
import math
import time

import carla

OUT = r"E:\output\_junction_survey"
out = []

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
m = world.get_map()
bp = world.get_blueprint_library()
world.set_weather(carla.WeatherParameters.ClearNoon)

TARGET_JID = 719

# ---- 找路口 ----
jsp = None
for sp in m.get_spawn_points():
    wp = m.get_waypoint(sp.location)
    if wp.is_junction and wp.junction_id == TARGET_JID:
        jsp = sp
        break
jl = jsp.location
out.append(f"junction_id={TARGET_JID}  中心=({jl.x:.1f},{jl.y:.1f},{jl.z:.1f})")

# ---- ① 把 CARLA 窗口瞬移到路口上方 ----
spec = world.get_spectator()
top = carla.Transform(
    carla.Location(x=jl.x - 26.0, y=jl.y, z=jl.z + 28.0),
    carla.Rotation(pitch=-55.0, yaw=0.0, roll=0.0))
spec.set_transform(top)
out.append("① 窗口已瞬移到路口上方（俯视）")
out.append(f"   spectator 位置=({top.location.x:.1f},{top.location.y:.1f},{top.location.z:.1f}) "
           f"pitch={top.rotation.pitch}")

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)

# 让窗口停一会，用户能看到
for _ in range(30):
    world.tick()

# ---- ② 找该路口可用的 spawn point（分方向）----
out.append("")
out.append("=" * 82)
out.append("② 扫描 junction 719 周边 spawn points（判断能否做压线/逆行演示）")
out.append("=" * 82)

near = sorted([(s.location.distance(jl), s) for s in m.get_spawn_points()],
              key=lambda x: x[0])[:24]
info = []
for d, s in near:
    w = m.get_waypoint(s.location)
    if w.is_junction:
        continue
    yaw = s.rotation.yaw
    # 车辆朝向与"指向路口"方向的夹角
    dx, dy = jl.x - s.location.x, jl.y - s.location.y
    to_j = math.degrees(math.atan2(dy, dx))
    diff = (yaw - to_j + 540) % 360 - 180
    info.append({"d": round(d, 1), "loc": s.location, "road": w.road_id,
                 "lane": w.lane_id, "yaw": round(yaw, 1),
                 "to_junction_deg": round(diff, 1),
                 "toward": abs(diff) < 60})

info.sort(key=lambda x: x["d"])
out.append(f"  {'距离':>7} {'road':>5} {'lane':>5} {'yaw':>7} {'朝向路口偏差':>12} {'朝路口':>6}")
for x in info[:14]:
    out.append(f"  {x['d']:>7} {x['road']:>5} {x['lane']:>5} {x['yaw']:>7} "
               f"{x['to_junction_deg']:>12} {'✅' if x['toward'] else '—':>6}")

toward = [x for x in info if x["toward"]]
away = [x for x in info if not x["toward"]]
out.append("")
out.append(f"  朝向路口（可做闯红灯/超速）: {len(toward)} 个")
out.append(f"  背离路口（对向，可做逆行）: {len(away)} 个")

# 统计车道
roads = {}
for x in info:
    roads.setdefault(x["road"], set()).add(x["lane"])
out.append(f"  涉及 road_id -> lane 集合: { {k: sorted(v) for k, v in roads.items()} }")
multi = [k for k, v in roads.items() if len(v) >= 2]
out.append(f"  有 >=2 条车道的路段: {multi}  <- 可做【压线】演示")

# ---- ③ 生成车辆，让用户看到车真的在动 ----
out.append("")
out.append("=" * 82)
out.append("③ 生成车辆并开 autopilot（用户可在窗口实时看到车辆行驶）")
out.append("=" * 82)

tm = client.get_trafficmanager(8000)
tm.set_synchronous_mode(True)
tm.set_global_distance_to_leading_vehicle(3.0)
# 注意（2026-10-04 踩坑）：ignore_lights_percentage 的签名是
#   ignore_lights_percentage(actor, perc)   —— 必须指定具体车辆，没有全局版本！
# 默认行为就是"遵守红绿灯"，所以这里不调用它。
# 制造闯红灯时应写成：tm.ignore_lights_percentage(某辆车, 100.0)
out.append("  已确认: ignore_lights_percentage 需指定车辆，默认遵守红绿灯")

veh_bps = [b for b in bp.filter("vehicle.*")
           if not any(k in b.id for k in ("bike", "harley", "crossbike", "kawasaki",
                                          "microlino", "carlacola", "truck"))]
spawned = []
for i, x in enumerate(toward[:4] + away[:2]):
    try:
        v = world.spawn_actor(veh_bps[i % len(veh_bps)], x["loc"] and
                              next(s for d, s in near if s.location.distance(x["loc"]) < 0.1))
    except Exception:
        # 回退：直接用位置构造 transform
        try:
            tf = carla.Transform(x["loc"])
            v = world.spawn_actor(veh_bps[i % len(veh_bps)], tf)
        except Exception as e:
            out.append(f"  生成失败: {str(e)[:60]}")
            continue
    try:
        v.set_autopilot(True, tm.get_port())
        spawned.append({"v": v, "tag": "朝路口" if x["toward"] else "对向"})
    except Exception as e:
        out.append(f"  autopilot 失败: {str(e)[:50]}")

out.append(f"  已生成 {len(spawned)} 辆车（autopilot 开启）")

# ---- 推进仿真，并让窗口跟着车辆移动 ----
out.append("")
out.append("④ 推进仿真 15 秒，窗口跟随主车（用户可见车辆行驶）")
out.append("=" * 82)
main = spawned[0]["v"] if spawned else None
speeds = []
for i in range(300):        # 15 秒 @20fps
    world.tick()
    if main is not None and i % 10 == 0:
        try:
            loc = main.get_location()
            vel = main.get_velocity()
            kmh = 3.6 * math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
            speeds.append(round(kmh, 1))
            # 窗口跟到主车后上方（第三人称跟随，用户能看清车在动）
            follow = carla.Transform(
                carla.Location(x=loc.x - 12.0, y=loc.y, z=loc.z + 8.0),
                carla.Rotation(pitch=-20.0, yaw=0.0, roll=0.0))
            spec.set_transform(follow)
        except Exception:
            pass

out.append(f"  主车速度采样（每 0.5 秒）: {speeds[:20]}")
if speeds:
    out.append(f"  速度范围: {min(speeds)} ~ {max(speeds)} km/h")
    moving = sum(1 for s in speeds if s > 1.0)
    out.append(f"  运动中采样: {moving}/{len(speeds)}  -> "
               + ("✅ 车辆确实在行驶（非静止）" if moving > len(speeds)*0.5 else "⚠ 车辆多数时间静止"))

# ---- 检查是否有人停车等红灯（我们关心"真实行为"）----
out.append("")
out.append("=" * 82)
out.append("⑤ 车辆行为观察（关键：是否会等红灯/跟车，而不是机械前进）")
out.append("=" * 82)
for it in spawned:
    try:
        v = it["v"]
        vel = v.get_velocity()
        kmh = 3.6 * math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
        loc = v.get_location()
        d = loc.distance(jl)
        out.append(f"  id={v.id:>3} {it['tag']:>6}  {kmh:>6.1f} km/h  距路口 {d:>6.1f}m")
    except Exception:
        pass

# 清理
for it in spawned:
    try:
        it["v"].set_autopilot(False)
        it["v"].destroy()
    except Exception:
        pass
st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)
out.append("")
out.append("已清理生成车辆（窗口保持在路口附近）")

io.open(r"E:\output\_jid719_workflow.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
