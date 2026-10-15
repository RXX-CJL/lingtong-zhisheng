"""端到端闭环测试：记录基线 → 启动视频源 → 轮询状态

只做真实 API 调用，不修改项目文件。
"""

import json
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8001"
VIDEO = r"E:\output\1\test_assets\traffic_videos\test1.mp4"


def call(method, path, body=None, timeout=60):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
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
        return e.code, e.read().decode("utf-8", "ignore")[:300]
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:200]}"


print("=" * 78)
print("1) 基线：当前状态与事件数")
print("=" * 78)
st, js = call("GET", "/api/realtime/status")
print("  status:", json.dumps(js, ensure_ascii=False)[:260] if isinstance(js, dict) else js)

st, js = call("GET", "/api/realtime/events?page=1&size=100")
before_ids = []
if isinstance(js, dict):
    rows = js.get("data") or []
    before_ids = [r.get("event_id") or r.get("id") for r in rows]
    print(f"  现有事件数: {len(before_ids)}")

print()
print("=" * 78)
print("2) 设置视频源（绝对路径）")
print("=" * 78)
st, js = call("POST", "/api/realtime/source",
              {"source_type": "video", "video_path": VIDEO})
print(f"  HTTP {st}: {json.dumps(js, ensure_ascii=False)[:300] if isinstance(js, (dict, list)) else js}")

print()
print("=" * 78)
print("3) 启动检测")
print("=" * 78)
st, js = call("POST", "/api/realtime/start", {"video_path": VIDEO})
print(f"  HTTP {st}: {json.dumps(js, ensure_ascii=False)[:300] if isinstance(js, (dict, list)) else js}")

print()
print("=" * 78)
print("4) 轮询进度（最多 100 秒）")
print("=" * 78)
last = None
for i in range(20):
    time.sleep(5)
    st, js = call("GET", "/api/realtime/status")
    if not isinstance(js, dict):
        print(f"  [{i*5+5:3d}s] status 取失败: {js}")
        continue
    d = js.get("data", js)
    line = (f"  [{i*5+5:3d}s] running={d.get('running')} "
            f"总帧={d.get('total_frames')} 已处理={d.get('processed_frames')} "
            f"fps={d.get('current_fps')} 违规={d.get('violation_count')}")
    if line != last:
        print(line)
        last = line
    if not d.get("running"):
        print("  -> 检测已停止（视频可能已播完）")
        break

print()
print("=" * 78)
print("5) 结果：新增事件")
print("=" * 78)
st, js = call("GET", "/api/realtime/events?page=1&size=100")
if isinstance(js, dict):
    rows = js.get("data") or []
    new = [r for r in rows if (r.get("event_id") or r.get("id")) not in before_ids]
    print(f"  事件总数: {len(rows)}   新增: {len(new)}")
    for r in new[:10]:
        print(f"    {str(r.get('event_id'))[:30]:32s} type={r.get('event_type')} "
              f"state={r.get('state')} video={'YES' if r.get('event_video_path') else 'no'}")
        if r.get("event_video_path"):
            print(f"        -> {r.get('event_video_path')}")
else:
    print("  取事件失败:", js)
