"""修复后验证：视频源应持续处理帧（而非读完后冻结）

期望（基于修复设计）：
  - 源 FPS ≈ 15，读取按 1/15 秒限速 → 读取速率 ≈ 15 f/s
  - 处理节流 3 f/s → processed 每 10 秒约 +30
  - cache 不超过 maxlen(300) 且持续增长到 300 后稳定
  - 播完自动回到开头，不出现永久 False
"""

import json
import time
import urllib.error
import urllib.request

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


def data():
    st, js = call("GET", "/api/realtime/status")
    return js.get("data", {}) if isinstance(js, dict) else {}


print("=== 启动前事件数 ===")
st, js = call("GET", "/api/realtime/events?page=1&size=100")
before = set()
if isinstance(js, dict):
    before = {r.get("event_id") for r in (js.get("data") or [])}
print(f"  {len(before)} 条")

print()
print("=== 启动检测（只调 /start）===")
st, js = call("POST", "/api/realtime/start", {"video_path": VIDEO})
print(f"  HTTP {st}: {js}")

print()
print("=== 90 秒观察（每 10 秒采样）===")
print("   时间   running  total  processed  fps    cache  违规  事件")
samples = []
for i in range(9):
    time.sleep(10)
    d = data()
    st2, ev = call("GET", "/api/realtime/events?page=1&size=100")
    nev = len((ev.get("data") or [])) if isinstance(ev, dict) else -1
    print(f"  {i*10+10:3d}s   {str(d.get('running')):7s} {d.get('total_frames'):6} "
          f"{d.get('processed_frames'):9}  {d.get('current_fps'):5} {d.get('cache_size'):6} "
          f"{d.get('violation_count'):5}  {nev}")
    samples.append(d.get("processed_frames", 0))

print()
print("=== 判定 ===")
if len(samples) >= 2:
    growth = samples[-1] - samples[0]
    print(f"  processed 从 {samples[0]} 增长到 {samples[-1]}（+{growth}，历时 80 秒）")
    print(f"  等效处理速率: {growth/80:.2f} f/s（期望 ≈ 3 f/s）")
    print("  结论:", "PASS 持续处理，修复生效" if growth > 100 else
          ("PARTIAL 增长但偏慢" if growth > 10 else "FAIL 仍然冻结"))

st, ev = call("GET", "/api/realtime/events?page=1&size=100")
if isinstance(ev, dict):
    rows = ev.get("data") or []
    new = [r for r in rows if r.get("event_id") not in before]
    print(f"  新增事件: {len(new)} 条")
    for r in new[:6]:
        print(f"    {str(r.get('event_id'))[:30]:32s} {r.get('event_type'):10s} "
              f"{r.get('state'):12s} video={'YES' if r.get('event_video_path') else 'no'}")

print()
print("=== 停止检测 ===")
print("  ", call("POST", "/api/realtime/stop"))
