"""澄清 freeze 语义，并测出「不 freeze 时 5/5/5 时长是否生效」。

freeze(True)  = 钉死当前状态，永不切换（已实测：elapsed_time 卡住不动）
freeze(False) = 恢复自动循环

本测试只用 freeze(False)，设 5/5/5，观察 30 秒仿真时间内是否有 5 秒级切换。
"""
import sys

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

    tl = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == LIGHT_ID:
            tl = a
    if tl is None:
        print("no light")
        return 1

    print("初始: state=%s freeze=%s elapsed=%.2f 默认时长 g%.1f y%.1f r%.1f"
          % (tl.get_state(), tl.is_frozen(), tl.get_elapsed_time(),
             tl.get_green_time(), tl.get_yellow_time(), tl.get_red_time()))
    print("actor attributes:", dict(tl.attributes))

    print("\n--- 设 5/5/5，freeze(False)，观察 30 秒仿真时间 ---")
    tl.freeze(False)
    tl.set_green_time(5.0)
    tl.set_yellow_time(5.0)
    tl.set_red_time(5.0)
    print("设定后回读: freeze=%s g=%.1f y=%.1f r=%.1f"
          % (tl.is_frozen(), tl.get_green_time(), tl.get_yellow_time(), tl.get_red_time()))

    t0 = world.get_snapshot().timestamp.elapsed_seconds
    log = []
    last = None
    for n in range(600):              # 30 s
        world.tick()
        st = str(tl.get_state())
        if st != last:
            now = world.get_snapshot().timestamp.elapsed_seconds - t0
            log.append((round(now, 2), st, round(tl.get_elapsed_time(), 2)))
            last = st
    print("状态变化 (sim_time, state, elapsed_time):")
    for e in log:
        print("   ", e)
    dur = [(log[i][1], round(log[i + 1][0] - log[i][0], 2)) for i in range(len(log) - 1)]
    print("各段时长:", dur)
    if not dur:
        print("!! 30 秒内完全没有切换 —— 说明用 set_state/freeze 干预过之后，自动循环不再推进")

    # 再测：解冻后完全不干预，是否恢复循环
    print("\n--- 复位时长 + freeze(False)，再观察 30 秒（不做任何 set_state）---")
    tl.set_green_time(10.0)
    tl.set_yellow_time(3.0)
    tl.set_red_time(2.0)
    tl.freeze(False)
    t0 = world.get_snapshot().timestamp.elapsed_seconds
    log2 = []
    last = None
    for n in range(600):
        world.tick()
        st = str(tl.get_state())
        if st != last:
            now = world.get_snapshot().timestamp.elapsed_seconds - t0
            log2.append((round(now, 2), st, round(tl.get_elapsed_time(), 2)))
            last = st
    print("状态变化:", log2)
    dur2 = [(log2[i][1], round(log2[i + 1][0] - log2[i][0], 2)) for i in range(len(log2) - 1)]
    print("各段时长:", dur2)

    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\n已复位")
    return 0


if __name__ == "__main__":
    sys.exit(main())
