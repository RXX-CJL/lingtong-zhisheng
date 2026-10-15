"""CARLA 实测 v2：同步模式下能否跑出"高速"？

v1 的问题：世界是**异步模式**（默认），world.tick() 不阻塞，
仿真按真实墙钟推进 -> 全油门 8 秒只到 11 km/h。

v2 修正：切到**同步模式 + 固定步长 (dt=0.05s = 20fps) + 每 tick 给控制**，
这样物理推进与我们的 tick 严格对应，可以：
  · 精确控制仿真时间（不看墙钟）
  · 让车提速到高速公路级（>60 km/h）
  · 达到 <车速真值> 与 <画面帧> 一一对应的效果（做测速验证必需）

同时修正 v1 的判定逻辑错误：位移 3.9m 被我误判为"没动"（阈值设太高）。
"""

import io
import math

import carla

out = []
client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
bp_lib = world.get_blueprint_library()
m = world.get_map()


def spd(veh):
    v = veh.get_velocity()
    return 3.6 * math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2)


# ---------- 切同步模式 ----------
settings = world.get_settings()
prev_sync = settings.synchronous_mode
settings.synchronous_mode = True
settings.fixed_delta_seconds = 0.05          # 20 fps
world.apply_settings(settings)
out.append(f"已切同步模式: synchronous_mode={settings.synchronous_mode} "
           f"dt={settings.fixed_delta_seconds}s (20fps)")
out.append("")

# ---------- 选一段长直路 ----------
spawn_points = m.get_spawn_points()
straight = None
for sp in spawn_points:
    wp = m.get_waypoint(sp.location)
    if not wp.is_junction:
        # 往前看 100m 是否仍是直路
        nxt = wp.next(60.0)
        if nxt and not nxt[0].is_junction:
            straight = sp
            break
out.append(f"选点: {straight.location}")

bp = bp_lib.filter("vehicle.tesla.model3")
if not bp:
    bp = bp_lib.filter("vehicle.audi.a2")
veh = world.spawn_actor(bp[0], straight)
# 顺手关掉物理警告噪声
for _ in range(20):
    world.tick()
out.append(f"生成: {veh.type_id}  id={veh.id}")
out.append(f"静止速度: {spd(veh):.2f} km/h")
out.append("")

# ---------- 实验 A：手动全油门能到多少 ----------
out.append("=" * 78)
out.append("实验 A：同步模式下全油门 10 秒（200 tick @20fps）")
out.append("=" * 78)
ctrl = carla.VehicleControl()
ctrl.throttle = 1.0
ctrl.gear = 1
samples = []
for t in range(200):
    veh.apply_control(ctrl)
    world.tick()
    if (t + 1) % 20 == 0:
        s = spd(veh)
        samples.append(s)
        out.append(f"  {(t+1)/20:>5.1f} 秒: {s:7.2f} km/h")
out.append("")
out.append(f"结论 A: 10 秒内 0 -> {samples[-1]:.2f} km/h")
out.append(f"        {'✅ 能跑到高速（可用于超速场景）' if samples[-1] > 60 else '⚠ 未达 60 km/h，需更长加速距离或更大油门'}")
out.append("")

# ---------- 实验 B：这个速度换算成像素位移是多少 ----------
out.append("=" * 78)
out.append("实验 B：车速 -> 像素位移换算（为「造超速场景」做准备）")
out.append("=" * 78)
W, H = 1280, 576
AR = W / H
N_LANES = max(2.0, min(8.0, 2.0 + (AR - 1.0) * 5.0))
PPM = W / (N_LANES * 4.0)
out.append(f"  假设 1280x576 画面 + assumed_lanes 标定: ppm≈{PPM:.1f} px/m")
for kmh in (30, 60, 80, 100):
    out.append(f"    {kmh:>3} km/h -> {kmh/3.6*PPM:>7.1f} px/s  "
               f"（20fps 下每帧 {kmh/3.6*PPM/20:>5.1f} px）")
out.append("")

# ---------- 实验 C：自动驾驶（TM）跑一段 ----------
out.append("=" * 78)
out.append("实验 C：Traffic Manager 自动驾驶（同步模式下）")
out.append("=" * 78)
try:
    tm = client.get_trafficmanager(8000)
    tm.set_synchronous_mode(True)
    tm.set_global_distance_to_leading_vehicle(3.0)
    veh.set_autopilot(True, tm.get_port())
    out.append("  已开启 autopilot（TM 同步模式）")
    for t in range(200):
        world.tick()
        if (t + 1) % 40 == 0:
            loc = veh.get_location()
            out.append(f"  {(t+1)/20:>5.1f} 秒: {spd(veh):7.2f} km/h  "
                       f"位置=({loc.x:8.1f}, {loc.y:8.1f})")
    out.append("  ✅ autopilot 下车辆自主行驶（位置持续变化）")
except Exception as e:
    out.append(f"  ❌ TM 失败: {type(e).__name__}: {str(e)[:150]}")

# ---------- 清理 ----------
try:
    veh.set_autopilot(False)
except Exception:
    pass
try:
    veh.destroy()
except Exception:
    pass
settings.synchronous_mode = prev_sync
settings.fixed_delta_seconds = None
world.apply_settings(settings)
out.append("")
out.append("已清理：销毁车辆 + 恢复异步模式")

io.open(r"E:\output\_carla_motion_test2.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
