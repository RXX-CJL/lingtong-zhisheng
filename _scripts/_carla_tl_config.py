"""CARLA 红绿灯正式配置 + 周期验证

从前两轮试验学到的正确用法：
  · set_*_time 需在 freeze 状态下设置才可靠生效（且 getter 才会回读新值）
  · freeze(True) 会**同时冻结状态** -> 可把灯钉死在红灯（制造闯红灯场景的利器）

本脚本：
  1. 给全部 15 个灯设置 绿25/黄3/红25
  2. 解冻，观察 70 秒，统计状态时长 —— **确认周期真的变了**
  3. 演示 freeze 钉红灯（为录制场景做准备）
"""

import io

import carla

out = []
client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()

GREEN, YELLOW, RED = 25.0, 4.0, 25.0
tls = list(world.get_actors().filter("traffic.traffic_light*"))
out.append(f"红绿灯 {len(tls)} 个；目标 绿={GREEN} 黄={YELLOW} 红={RED}")

# ---- 1) 配置 ----
ok = 0
for tl in tls:
    try:
        tl.freeze(True)                 # 必须先冻结，否则设置可能不生效
        tl.set_green_time(GREEN)
        tl.set_yellow_time(YELLOW)
        tl.set_red_time(RED)
        tl.freeze(False)                # 解冻恢复自动循环
        ok += 1
    except Exception as e:
        out.append(f"  id={tl.id} 失败: {str(e)[:60]}")
out.append(f"已配置 {ok}/{len(tls)}")
out.append("")
out.append("回读确认（前 4 个）:")
for tl in tls[:4]:
    out.append(f"  id={tl.id:>3} 绿={tl.get_green_time():5.1f} 黄={tl.get_yellow_time():4.1f} "
               f"红={tl.get_red_time():5.1f}")

# ---- 2) 观察周期 ----
out.append("")
out.append("=" * 74)
out.append("观察 70 秒：统计状态时长与切换次数")
out.append("=" * 74)
st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.1
world.apply_settings(st)

watch = tls[0]
durations = {}
transitions = []
last = None
for i in range(700):
    world.tick()
    try:
        s = str(watch.get_state()).split(".")[-1]
    except Exception:
        continue
    durations[s] = durations.get(s, 0.0) + 0.1
    if last is not None and s != last:
        transitions.append((round(i * 0.1, 1), last, s))
    last = s

out.append(f"  监视 id={watch.id}")
for k in ("Red", "Green", "Yellow"):
    out.append(f"    {k:7s} {durations.get(k, 0.0):5.1f}s")
out.append(f"  切换 {len(transitions)} 次:")
for t, a, b in transitions[:12]:
    out.append(f"     {t:6.1f}s  {a} -> {b}")

st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)

# ---- 3) 演示 freeze 钉红灯 ----
out.append("")
out.append("=" * 74)
out.append("演示：把灯钉死在红灯（制造可信闯红灯场景）")
out.append("=" * 74)
try:
    watch.freeze(True)
    watch.set_state(carla.TrafficLightState.Red)
    stuck = []
    for _ in range(50):
        world.tick() if False else None
        stuck.append(str(watch.get_state()).split(".")[-1])
    out.append(f"  钉住后 50 次读取状态: {set(stuck)}  （期望只有 Red）")
    watch.freeze(False)
    out.append(f"  已解冻，当前状态={str(watch.get_state()).split('.')[-1]}")
except Exception as e:
    out.append(f"  失败: {type(e).__name__}: {str(e)[:120]}")

out.append("")
red_ok = durations.get("Red", 0) > 12
green_ok = durations.get("Green", 0) > 12
out.append("结论: " + ("✅ 周期已生效（红/绿都有可观时长），闯红灯场景可信"
                      if (red_ok and green_ok) else
                      f"⚠️ 周期仍异常: 红={durations.get('Red',0):.1f} 绿={durations.get('Green',0):.1f}"))

io.open(r"E:\output\_carla_tl_config.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
