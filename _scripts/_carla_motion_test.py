"""CARLA 实测：车辆到底会不会动？

用户质疑："我一直以为里面的车就是静止不动的"
本脚本用**可测量的数据**回答，不靠文档背书：

实验 1：生成一辆车，手动给油门，看速度是否从 0 上升
实验 2：用 Traffic Manager 自动驾驶，看它是否自己跑起来
实验 3：读 API 的车速真值（后续测速验证就靠它）
"""

import io
import math
import time

import carla

out = []
client = carla.Client("127.0.0.1", 2000)
client.set_timeout(20.0)
world = client.get_world()
bp_lib = world.get_blueprint_library()


def speed_kmh(veh):
    """从 CARLA API 读真实车速（m/s -> km/h）"""
    v = veh.get_velocity()
    return 3.6 * math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2)


out.append("=" * 78)
out.append("实验 1：手动油门 —— 车会不会动？")
out.append("=" * 78)

# 找一段直路（非路口）的 spawn point
spawn_points = world.get_map().get_spawn_points()
straight = None
for sp in spawn_points:
    wp = world.get_map().get_waypoint(sp.location)
    if not wp.is_junction:
        straight = sp
        break
out.append(f"选点: {straight.location}")

bp = bp_lib.filter("vehicle.audi.a2")[0]
vehicle = world.spawn_actor(bp, straight)
out.append(f"已生成: {vehicle.type_id}  id={vehicle.id}")

# 等物理稳定
for _ in range(10):
    world.tick()
time.sleep(0.5)
out.append(f"静止时速度: {speed_kmh(vehicle):.2f} km/h")

# 给全油门
out.append("")
out.append("给全油门 (throttle=1.0)，每秒采样一次:")
ctrl = carla.VehicleControl()
ctrl.throttle = 1.0
ctrl.steer = 0.0
samples = []
for i in range(8):
    vehicle.apply_control(ctrl)
    for _ in range(20):          # 推进若干 tick
        world.tick()
    s = speed_kmh(vehicle)
    samples.append(s)
    out.append(f"  第 {i+1} 秒: {s:6.2f} km/h")

moved = samples[-1] > samples[0] + 1.0
out.append("")
out.append(f"结论 1: {'✅ 车会动（油门有效）' if moved else '❌ 车不动'}  "
           f"速度 {samples[0]:.2f} -> {samples[-1]:.2f} km/h")

# 刹车
ctrl.throttle = 0.0
ctrl.brake = 1.0
vehicle.apply_control(ctrl)
for _ in range(60):
    world.tick()
out.append(f"刹车后速度: {speed_kmh(vehicle):.2f} km/h（证明控制真的生效）")

out.append("")
out.append("=" * 78)
out.append("实验 2：Traffic Manager 自动驾驶 —— 车会自己跑吗？")
out.append("=" * 78)
try:
    tm = client.get_trafficmanager(8000)
    tm.set_global_distance_to_leading_vehicle(2.5)
    out.append("Traffic Manager 已连接 (端口 8000)")
    vehicle.set_autopilot(True, tm.get_port())
    out.append("已开启 autopilot，采样 6 秒:")
    auto = []
    for i in range(6):
        for _ in range(20):
            world.tick()
        s = speed_kmh(vehicle)
        auto.append(s)
        loc = vehicle.get_location()
        out.append(f"  第 {i+1} 秒: {s:6.2f} km/h   位置=({loc.x:.1f}, {loc.y:.1f})")
    d = math.sqrt((vehicle.get_location().x - straight.location.x) ** 2 +
                  (vehicle.get_location().y - straight.location.y) ** 2)
    out.append("")
    out.append(f"结论 2: 自动驾驶下速度 {auto[0]:.1f} -> {auto[-1]:.1f} km/h，"
               f"位移 {d:.1f} m")
    out.append("        " + ("✅ 车会自己跑（TM 有效）" if d > 5 else "❌ 没动"))
except Exception as e:
    out.append(f"❌ Traffic Manager 失败: {type(e).__name__}: {str(e)[:180]}")

out.append("")
out.append("=" * 78)
out.append("实验 3：API 速度真值可用性（后续测速验证的基础）")
out.append("=" * 78)
for i in range(3):
    for _ in range(20):
        world.tick()
    v = vehicle.get_velocity()
    out.append(f"  get_velocity() = ({v.x:6.2f}, {v.y:6.2f}, {v.z:6.2f}) m/s  "
               f"-> {speed_kmh(vehicle):.2f} km/h")
out.append("")
out.append("结论 3: " + ("✅ 可直接读出真实车速，可作为测速精度的『真值』"
                        if samples[-1] > 0 else "❓ 待确认"))

# 清理
try:
    vehicle.destroy()
    out.append("")
    out.append("已清理生成的车辆")
except Exception:
    pass

io.open(r"E:\output\_carla_motion_test.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
