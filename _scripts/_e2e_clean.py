"""干净重测：先 stop，再只用 /start（不调 /source），观察实际处理帧数"""

import json
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8001"
VIDEO = r"E:\output\1\test_assets\traffic_videos\test1.mp4"


def call(method, path, body=None, timeout=90):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "ignore")
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:200]
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:150]}"


def status():
    st, js = call("GET", "/api/realtime/status")
    return js.get("data", {}) if isinstance(js, dict) else {}


print("=== 0) 先停止当前检测 ===")
print("  stop:", call("POST", "/api/realtime/stop"))
time.sleep(2)

print()
print("=== 1) 只调用 /start（带 video_path，不预先调 /source）===")
st, js = call("POST", "/api/realtime/start", {"video_path": VIDEO})
print(f"  HTTP {st}: {js}")

print()
print("=== 2) 观察 60 秒 ===")
prev = None
for i in range(12):
    time.sleep(5)
    d = status()
    line = (f"  [{i*5+5:3d}s] running={d.get('running')} total={d.get('total_frames')} "
            f"processed={d.get('processed_frames')} fps={d.get('current_fps')} "
            f"cache={d.get('cache_size')} viol={d.get('violation_count')}")
    print(line)
    if prev and d.get("processed_frames") == prev.get("processed_frames") and i >= 3:
        print("  -> processed 已停止增长")
    prev = d
    if not d.get("running"):
        print("  -> 检测已结束")
        break

print()
print("=== 3) 结果 ===")
d = status()
print(f"  最终: processed={d.get('processed_frames')} / total={d.get('total_frames')} "
      f"violations={d.get('violation_count')} cache={d.get('cache_size')}")

st, js = call("GET", "/api/realtime/events?page=1&size=20")
if isinstance(js, dict):
    rows = js.get("data") or []
    print(f"  事件总数: {len(rows)}")
    for r in rows[:6]:
        print(f"    {str(r.get('event_id'))[:28]:30s} {r.get('event_type')} {r.get('state')} "
              f"video={'YES' if r.get('event_video_path') else 'no'}")
