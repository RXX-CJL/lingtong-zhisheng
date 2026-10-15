"""秒级单元验证：新的统一时钟 _now() 与去重语义是否正确。"""
import sys
import time

sys.path.insert(0, r"E:\output\1\api")


class FakeCap:
    def __init__(self, fps=20.0):
        self._fps = fps

    def get(self, prop):
        return self._fps


def main():
    from realtime_detector import RealtimeViolationDetector
    from traffic_event_engine import TrafficEventEngine

    print("=== 1) 摄像头场景：必须回退墙钟（行为不能变）===")
    d = RealtimeViolationDetector()
    d._source_is_file = False
    d.frame_count = 12345
    d.cap = FakeCap(20.0)
    t = d._now()
    now = time.time()
    print("   _now()=%.3f  墙钟=%.3f  差=%.3f 秒" % (t, now, abs(t - now)))
    print("   -> %s" % ("OK（用墙钟）" if abs(t - now) < 5 else "!!! 异常"))

    print("\n=== 2) 视频回放场景：必须用视频时间 ===")
    d._source_is_file = True
    d._source_fps = 20.0
    d._loop_frame_base = 0
    d.cap = FakeCap(20.0)
    for fc in (0, 100, 200, 400):
        d.frame_count = fc
        print("   帧 %-5d -> 视频时间 %6.2f 秒" % (fc, d._now()))

    print("\n=== 3) 循环归零：第 2 圈的时间必须从 0 重新开始 ===")
    d.frame_count = 520          # 第 1 圈结束（520 帧 / 20fps = 26 秒）
    print("   第1圈末: 帧%d -> %.2f 秒" % (d.frame_count, d._now()))
    d._loop_frame_base = d.frame_count     # 模拟循环归零
    d.frame_count = 521
    print("   第2圈起: 帧%d -> %.2f 秒   <- 应接近 0" % (d.frame_count, d._now()))
    d.frame_count = 620
    print("   第2圈中: 帧%d -> %.2f 秒" % (d.frame_count, d._now()))

    print("\n=== 4) 帧缓存时间戳与事件触发时间必须同源 ===")
    calls = []

    def fake_clock():
        return 12.34

    e = TrafficEventEngine(rule_plugins=[], frame_buffer=None, cooldown_sec=60,
                           clock=fake_clock)
    print("   注入时钟后 engine._now() = %.2f  (期望 12.34)" % e._now())
    e2 = TrafficEventEngine(rule_plugins=[], frame_buffer=None, cooldown_sec=60)
    t2 = e2._now()
    print("   未注入     engine._now() = %.3f (期望≈墙钟 %.3f) 差=%.3f"
          % (t2, time.time(), abs(t2 - time.time())))
    e2.set_clock(fake_clock)
    print("   set_clock 后 engine._now() = %.2f (期望 12.34)" % e2._now())

    print("\n=== 5) 冷却按注入时钟判断（同一违规一圈内只报一次）===")
    e3 = TrafficEventEngine(rule_plugins=[], frame_buffer=None, cooldown_sec=8,
                            clock=lambda: 5.0)
    print("   无冷却记录      -> 可触发=%s (期望 True)" % e3._check_cooldown(1, 'red_light'))
    e3._cooldowns[(1, 'red_light')] = 13.0        # 冷却到 13 秒
    print("   t=5,冷却到13    -> 可触发=%s (期望 False，冷却中)" % e3._check_cooldown(1, 'red_light'))
    e3.set_clock(lambda: 20.0)
    print("   t=20,冷却到13   -> 可触发=%s (期望 True，已过期)" % e3._check_cooldown(1, 'red_light'))
    return 0


if __name__ == "__main__":
    sys.exit(main())
