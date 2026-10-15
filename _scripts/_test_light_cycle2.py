"""把红绿灯推进行为测清楚：
1) 确认同步模式真的生效
2) 确认 world.tick() 是否推进服务器仿真时间
3) 从 Green 起观察 25 秒，看是否出现相位切换及各段时长
"""
import sys
import time

import carla

LIGHT_ID = 9


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)
    s2 = world.get_settings()
    print("同步模式回读: synchronous_mode=%s fixed_delta=%s" % (s2.synchronous_mode, s2.fixed_delta_seconds))
    print("world frame before:", world.get_snapshot().frame, " sim time:", world.get_snapshot().timestamp.elapsed_seconds)

    tl = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == LIGHT_ID:
            tl = a
    if tl is None:
        print("no light")
        return 1

    # 从 Green 起，且用较短时长，观察是否切换
    tl.set_green_time(5.0)
    tl.set_yellow_time(5.0)
    tl.set_red_time(5.0)
    tl.freeze(True)
    tl.set_state(carla.TrafficLightState.Green)
    for _ in range(5):
        world.tick()
    print("起始状态:", tl.get_state(), " elapsed_time:", round(tl.get_elapsed_time(), 2))

    t0 = world.get_snapshot().timestamp.elapsed_seconds
    log = []
    last = None
    n = 0
    while n < 500:                     # 500 tick * 0.05 = 25 s of sim time
        world.tick()
        n += 1
        st = str(tl.get_state())
        if st != last:
            now = world.get_snapshot().timestamp.elapsed_seconds - t0
            log.append((round(now, 2), st, round(tl.get_elapsed_time(), 2)))
            last = st
    print("状态变化 (sim_time, state, light.elapsed_time):")
    for e in log:
        print("   ", e)

    print("\nframes ticked:", n,
          " sim seconds elapsed:", round(world.get_snapshot().timestamp.elapsed_seconds - t0, 2))
    dur = [(log[i][1], round(log[i + 1][0] - log[i][0], 2)) for i in range(len(log) - 1)]
    print("各段时长:", dur)

    # reset
    tl.set_green_time(10.0)
    tl.set_yellow_time(3.0)
    tl.set_red_time(2.0)
    tl.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("已复位")
    return 0


if __name__ == "__main__":
    sys.exit(main())
