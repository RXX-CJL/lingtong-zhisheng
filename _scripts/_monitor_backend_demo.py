"""监控后端检测跑完，并汇总本轮（新代码）产生的违规。"""
import json
import sys
import time
import urllib.request
from collections import Counter

BASE = "http://127.0.0.1:8001"
SINCE = "2026-10-05T23:44:00"     # 本轮启动时刻（本地时间）


def get(path, timeout=60):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:400]
    except Exception as e:
        return None, str(e)


def main():
    print("=== 监控进度 ===")
    last = None
    stall = 0
    t0 = time.time()
    while True:
        time.sleep(5)
        s, r = get("/api/realtime/status")
        d = (r or {}).get("data") or {}
        el = time.time() - t0
        key = json.dumps({k: d.get(k) for k in
                          ("running", "processed_frames", "frame_count",
                           "violation_count", "fps")}, sort_keys=True)
        if key == last:
            stall += 5
        else:
            stall = 0
            last = key
        print("   [%5.1fs] running=%-5s 已处理=%-5s 违规数=%-4s fps=%-6s 灯态=%s"
              % (el, d.get("running"), d.get("processed_frames"),
                 d.get("violation_count"), d.get("fps"),
                 (d.get("scene_config") or {}).get("traffic_light_state")
                 if isinstance(d.get("scene_config"), dict)
                 else d.get("traffic_light_state")))
        if not d.get("running"):
            print("   -> 检测结束")
            break
        if stall >= 45:
            print("   -> 45 秒无变化，停止监控")
            break
        if el > 1200:
            print("   -> 超时")
            break

    print("\n=== 本轮（%s 之后）产生的事件 ===" % SINCE)
    s, ev = get("/api/realtime/events?size=100")
    items = (ev or {}).get("data") or []
    mine = [it for it in items if str(it.get("created_at") or it.get("trigger_time") or "") >= SINCE]
    print("   本轮事件数: %d / 最近100条中" % len(mine))
    cnt = Counter(it.get("event_type") for it in mine)
    stt = Counter(it.get("state") for it in mine)
    for k, v in cnt.most_common():
        print("     类型 %-20s %d" % (k, v))
    for k, v in stt.most_common():
        print("     状态 %-20s %d" % (k, v))
    print("\n   明细（前 20 条）:")
    for it in mine[:20]:
        sc = it.get("scene_context") or {}
        print("     %-16s %-11s track=%-3s 灯态=%-7s 速度=%-6s %s"
              % (it.get("event_type"), it.get("state"), it.get("track_id"),
                 sc.get("traffic_light_state"),
                 round((it.get("vehicle_info") or {}).get("speed") or 0, 1),
                 (it.get("created_at") or "")[:19]))

    # 违规证据表
    print("\n=== 最近违规证据（violation_evidences）===")
    s, ve = get("/api/violations?page=1&size=12")
    if s == 200 and isinstance(ve, dict):
        data = ve.get("data") or ve.get("items") or []
        if isinstance(data, dict):
            data = data.get("items") or data.get("data") or []
        print("   条数:", len(data))
        for v in data[:12]:
            print("     %-18s %-10s %s" % (v.get("violation_type"), v.get("status"),
                                           (v.get("created_at") or "")[:19]))
    else:
        print("   /api/violations 获取:", s, str(ve)[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
