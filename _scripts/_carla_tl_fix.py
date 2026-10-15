"""修复 CARLA 红绿灯周期 —— 让"闯红灯"成为可信场景

问题（实测）：CARLA 默认 绿10s / 黄3s / **红2s**。
红灯只有 2 秒 -> 车辆按正常起步逻辑出发时灯已变 -> "基本都在闯红灯"，
违规失去区分度，无法用于验证。

修法：设为 绿25s / 黄3s / 红25s，并**验证周期性真的变了**。
"""

import io
import time

import carla

out = []
client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()

GREEN, YELLOW, RED = 25.0, 3.0, 25.0
out.append(f"目标周期: 绿={GREEN}s 黄={YELLOW}s 红={RED}s")

tls = list(world.get_actors().filter("traffic.traffic_light*"))
out.append(f"发现红绿灯 {len(tls)} 个")
out.append("")

out.append("=== 修改前 ===")
for tl in tls[:4]:
    out.append(f"  id={tl.id:>3} 绿={tl.get_green_time():5.1f} 黄={tl.get_yellow_time():4.1f} "
               f"红={tl.get_red_time():5.1f}  当前={tl.get_state()}")

changed = 0
for tl in tls:
    try:
        tl.set_green_time(GREEN)
        tl.set_yellow_time(YELLOW)
        tl.set_red_time(RED)
        changed += 1
    except Exception as e:
        out.append(f"  id={tl.id} 设置失败: {str(e)[:60]}")
out.append("")
out.append(f"已修改 {changed}/{len(tls)} 个红绿灯")

out.append("")
out.append("=== 修改后（回读确认）===")
for tl in tls[:4]:
    out.append(f"  id={tl.id:>3} 绿={tl.get_green_time():5.1f} 黄={tl.get_yellow_time():4.1f} "
               f"红={tl.get_red_time():5.1f}  当前={tl.get_state()}")

# ---- 观察 60 秒，统计每个灯的状态时长分布（验证周期真的变了）----
out.append("")
out.append("=== 观察 60 秒：统计某灯的状态变化 ===")
st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.1        # 10 tick/s，60 秒 = 600 tick
world.apply_settings(st)

watch = tls[0] if tls else None
transitions = []
last_state = None
durations = {"Red": 0.0, "Green": 0.0, "Yellow": 0.0}
if watch:
    for i in range(600):
        world.tick()
        try:
            s = str(watch.get_state()).split(".")[-1]
        except Exception:
            continue
        if last_state is not None and s != last_state:
            transitions.append((i * 0.1, last_state, s))
        durations[s] = durations.get(s, 0.0) + 0.1
        last_state = s

out.append(f"  监视 id={watch.id if watch else '?'}")
out.append(f"  60 秒内状态时长: 红={durations.get('Red',0):.1f}s "
           f"绿={durations.get('Green',0):.1f}s 黄={durations.get('Yellow',0):.1f}s")
out.append(f"  状态切换 {len(transitions)} 次:")
for t, a, b in transitions[:10]:
    out.append(f"     {t:5.1f}s: {a} -> {b}")

st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)

out.append("")
ok = durations.get("Red", 0) > 15.0 and durations.get("Green", 0) > 15.0
out.append("结论: " + ("✅ 红灯/绿灯时长显著变长（闯红灯场景可信）"
                      if ok else f"⚠️ 周期仍不理想: {durations}"))

io.open(r"E:\output\_carla_tl_fix.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
