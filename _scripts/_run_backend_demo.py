"""拉起实时检测（重放演示视频），轮询到跑完，汇总违规结果。"""
import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8001"
VIDEO = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"


def call(path, method="GET", body=None, timeout=60):
    url = BASE + path
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:400]
    except Exception as e:
        return None, str(e)


def main():
    print("=== 1) 先停掉可能在跑的任务 ===")
    print("   stop ->", call("/api/realtime/stop", "POST")[0])

    print("\n=== 2) 启动检测（视频源）===")
    s, b = call("/api/realtime/start", "POST",
                {"video_path": VIDEO, "camera_index": 0}, timeout=120)
    print("   start -> %s  %s" % (s, json.dumps(b, ensure_ascii=False)[:300] if isinstance(b, dict) else b))
    if s != 200:
        return 1

    print("\n=== 3) 轮询状态 ===")
    last = None
    t0 = time.time()
    stall = 0
    while True:
        time.sleep(5)
        s, st = call("/api/realtime/status")
        if s != 200 or not isinstance(st, dict):
            print("   status 异常:", s, st)
            break
        key = json.dumps({k: st.get(k) for k in
                          ("running", "processed_frames", "frame_count", "violation_count",
                           "source_kind", "fps", "traffic_light_state")},
                         ensure_ascii=False, sort_keys=True)
        el = time.time() - t0
        if key == last:
            stall += 5
        else:
            stall = 0
            last = key
        print("   [%5.1fs] %s" % (el, key))
        if not st.get("running"):
            print("   -> 检测已停止")
            break
        if stall >= 40:
            print("   -> 状态 40 秒无变化，视为跑完/卡住，继续收集结果")
            break
        if el > 900:
            print("   -> 超时 15 分钟，停止")
            break

    print("\n=== 4) 事件与违规汇总 ===")
    s, ev = call("/api/realtime/events?size=100")
    if s == 200 and isinstance(ev, dict):
        items = ev.get("items") or ev.get("events") or ev.get("data") or []
        print("   事件条数: %d" % len(items))
        from collections import Counter
        cnt = Counter()
        for it in items:
            vt = it.get("violation_type") or it.get("event_type") or "?"
            cnt[vt] += 1
        for k, v in cnt.most_common():
            print("     %-22s %d" % (k, v))
        print("\n   最近 8 条:")
        for it in items[:8]:
            print("     %-20s %-10s %s" % (
                it.get("violation_type") or it.get("event_type"),
                it.get("state") or it.get("status"),
                (it.get("created_at") or it.get("trigger_time") or "")[:19]))
    else:
        print("   events 获取失败:", s, ev)

    print("\n=== 5) 判色统计（/status 里的 traffic_light_stats）===")
    s, st = call("/api/realtime/status")
    if s == 200 and isinstance(st, dict):
        for k in ("traffic_light_stats", "traffic_light_state", "confirmed_traffic_lights",
                  "processed_frames", "violation_count", "fps"):
            if k in st:
                print("   %-28s = %s" % (k, json.dumps(st[k], ensure_ascii=False)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
