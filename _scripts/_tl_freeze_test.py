"""录前验证：同步模式下能否把红绿灯钉死在红灯？

为什么必须先验证：
  上一轮我测这个时脚本里写了 `world.tick() if False else None`（等于不推进），
  所以没测出来 —— 不能拿"未验证"当"可用"。

正确测法：同步模式 + 真正 world.tick() + 多帧读取状态。
"""

import io

import carla

out = []
client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)
out.append("同步模式已开")

tls = list(world.get_actors().filter("traffic.traffic_light*"))
out.append(f"红绿灯 {len(tls)} 个")
tl = tls[0]

# ---- 试验 1：置红后观察是否保持（真正 tick）----
out.append("")
out.append("=" * 72)
out.append("试验 1：set_state(Red)，然后真正推进 100 帧（5 秒仿真）")
out.append("=" * 72)
tl.set_state(carla.TrafficLightState.Red)
states = set()
for i in range(100):
    world.tick()
    states.add(str(tl.get_state()).split(".")[-1])
out.append(f"  100 帧内出现过的状态: {states}")
out.append(f"  -> {'✅ 保持红灯（可信）' if states == {'Red'} else '❌ 会自己变 -> 不可用于钉红灯'}")

# ---- 试验 2：freeze(True) + set_state(Red) 是否更稳 ----
out.append("")
out.append("=" * 72)
out.append("试验 2：freeze(True) + set_state(Red)，推进 100 帧")
out.append("=" * 72)
try:
    tl.freeze(True)
    tl.set_state(carla.TrafficLightState.Red)
    states2 = set()
    for i in range(100):
        world.tick()
        states2.add(str(tl.get_state()).split(".")[-1])
    out.append(f"  出现过的状态: {states2}")
    out.append(f"  -> {'✅ 冻结成功，稳定为红' if states2 == {'Red'} else '⚠ 仍有变化'}")
    tl.freeze(False)
    out.append("  已解冻")
except Exception as e:
    out.append(f"  失败: {type(e).__name__}: {str(e)[:120]}")

# ---- 试验 3：能否用 set_state 在录制中动态切红 ----
out.append("")
out.append("=" * 72)
out.append("试验 3：录制中动态切灯（绿 -> 红）")
out.append("=" * 72)
try:
    tl.set_state(carla.TrafficLightState.Green)
    for _ in range(20):
        world.tick()
    s1 = str(tl.get_state()).split(".")[-1]
    tl.set_state(carla.TrafficLightState.Red)
    for _ in range(20):
        world.tick()
    s2 = str(tl.get_state()).split(".")[-1]
    out.append(f"  设绿后读: {s1}   设红后读: {s2}")
    out.append(f"  -> {'✅ 可动态控制' if s1=='Green' and s2=='Red' else '⚠ 不完全受控'}")
except Exception as e:
    out.append(f"  失败: {str(e)[:100]}")

st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)

io.open(r"E:\output\_tl_freeze_test.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
