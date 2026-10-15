"""验证：由客户端每帧 set_state，能否精确实现「每 5 秒换一个颜色」。

结论将决定演示脚本怎么写：CARLA 的 set_green/yellow/red_time 不生效，
所以相位必须由脚本按 tick 数自己驱动。
"""
import sys

import carla

LIGHT_ID = 9
PHASE_FRAMES = 100          # 100 * 0.05 = 5.0 s
CYCLE = [carla.TrafficLightState.Green,
         carla.TrafficLightState.Yellow,
         carla.TrafficLightState.Red]


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    tl = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == LIGHT_ID:
            tl = a
    if tl is None:
        print("no light")
        return 1

    tl.freeze(False)
    t0 = world.get_snapshot().timestamp.elapsed_seconds
    log = []
    last = None
    n_ticks = 0
    for n in range(600):               # 30 s
        phase = CYCLE[(n // PHASE_FRAMES) % len(CYCLE)]
        tl.set_state(phase)            # 每帧强制
        world.tick()
        n_ticks += 1
        st = str(tl.get_state())
        if st != last:
            now = world.get_snapshot().timestamp.elapsed_seconds - t0
            log.append((round(now, 2), st))
            last = st

    print("每帧 set_state 的结果 (sim_time, state):")
    for e in log:
        print("   ", e)
    durs = [(log[i][1], round(log[i + 1][0] - log[i][0], 2)) for i in range(len(log) - 1)]
    print("各段时长:", durs)
    ok = all(abs(d - 5.0) < 0.6 for _, d in durs) and len(durs) >= 5
    print("\n5 秒均匀切换:", "✅ 成立" if ok else "❌ 不成立")

    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("已复位")
    return 0


if __name__ == "__main__":
    sys.exit(main())
