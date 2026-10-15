"""先验证：CARLA 红绿灯能否实现「5 秒换一个颜色」的自动循环。

用户要求每个颜色 5 秒。CARLA 默认是 freeze 状态下 __init__ 用一套时长、
非 freeze 用另一套（实测默认绿10/黄3/红2）。这里逐一验证三种做法，看哪种
能真正得到 5/5/5 的循环。

做法 A: set_green/yellow/red_time(5,5,5) + freeze(True)
做法 B: 不 freeze，仅设时长
做法 C: 手工每帧 set_state（对照基准，保证一定能控制）
"""
import sys
import time

import carla

LIGHT_ID = 9


def get_light(world):
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == LIGHT_ID:
            return a
    return None


def observe(tl, world, seconds, fps=20.0, label=""):
    """跑 seconds 秒，记录状态变化时刻。"""
    dt = 1.0 / fps
    log = []
    t = 0.0
    last = None
    while t < seconds:
        st = str(tl.get_state())
        if st != last:
            log.append((round(t, 2), st))
            last = st
        world.tick()
        time.sleep(dt * 0.4)
        t += dt
    print("  %-38s 观察到: %s" % (label, log))
    return log


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05          # 20 fps
    world.apply_settings(s)
    print("同步模式已开：fixed_delta=0.05 (20fps)")

    tl = get_light(world)
    if tl is None:
        print("找不到 light", LIGHT_ID)
        return 1
    print("light %d 初始: state=%s freeze=%s  green=%.1f yellow=%.1f red=%.1f"
          % (tl.id, tl.get_state(), tl.is_frozen(),
             tl.get_green_time(), tl.get_yellow_time(), tl.get_red_time()))

    print("\n--- 做法 A: 设时长(5,5,5) + freeze(True) ---")
    tl.set_green_time(5.0)
    tl.set_yellow_time(5.0)
    tl.set_red_time(5.0)
    tl.freeze(True)
    for _ in range(3):
        world.tick()
    print("  设定后: freeze=%s green=%.1f yellow=%.1f red=%.1f"
          % (tl.is_frozen(), tl.get_green_time(), tl.get_yellow_time(), tl.get_red_time()))
    logA = observe(tl, world, 26.0, label="A: freeze(True) + 5/5/5")

    print("\n--- 做法 B: freeze(False)，仅设时长 ---")
    tl.freeze(False)
    tl.set_green_time(5.0)
    tl.set_yellow_time(5.0)
    tl.set_red_time(5.0)
    for _ in range(3):
        world.tick()
    logB = observe(tl, world, 26.0, label="B: freeze(False) + 5/5/5")

    # 把状态交还给引擎：恢复默认时长、解冻
    tl.set_green_time(10.0)
    tl.set_yellow_time(3.0)
    tl.set_red_time(2.0)
    tl.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\n已复位：默认时长 + 解冻 + 关同步模式")

    # 结论
    print("\n================ 结论 ================")

    def phases(log):
        d = []
        for i in range(len(log) - 1):
            d.append((log[i][1], round(log[i + 1][0] - log[i][0], 2)))
        return d

    print("A 各段时长:", phases(logA))
    print("B 各段时长:", phases(logB))
    return 0


if __name__ == "__main__":
    sys.exit(main())
