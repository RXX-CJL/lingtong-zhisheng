"""测试场景标注完整工作流"""

import io
import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8001"
SRC = r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"


def call(method, path, body=None, timeout=60):
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
                return r.status, raw[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:250]
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:150]}"


enc = urllib.parse.quote(SRC)

print("=" * 74)
print("1) AI 自动检测斑马线（用视频首帧）")
print("=" * 74)
st, js = call("POST", f"/api/scene/auto-detect?source={enc}&use_current=false")
if isinstance(js, dict):
    d = js.get("data", {})
    zones = d.get("crosswalk_zones") or []
    print(f"  HTTP {st}")
    print(f"  检测到斑马线候选: {len(zones)} 个")
    for i, z in enumerate(zones[:3]):
        print(f"    #{i}: {z}")
    print(f"  停止线建议 y: {d.get('stop_line_y')}")
else:
    print(f"  HTTP {st}: {js}")

print()
print("=" * 74)
print("2) 保存标注（模拟人工确认：斑马线 + 停止线 + 禁停区）")
print("=" * 74)
cfg = {
    "crosswalk_zones": zones if zones else [[[400, 380], [900, 380], [900, 470], [400, 470]]],
    "stop_line_y": 370,
    "no_parking_zones": [{"x1": 0, "y1": 430, "x2": 1280, "y2": 576}],
    "lane_lines": [[[640, 200], [620, 560]]],
    "road_direction": "south",
    "pixel_per_meter": 10,
}
st, js = call("POST", "/api/scene/config",
              {"source": SRC, "config": cfg, "annotated_by": "manual"})
if isinstance(js, dict):
    print(f"  HTTP {st}  key={js.get('key')}")
    saved = js.get("data", {})
    print(f"  已保存字段: {[k for k in saved if not k.startswith('_')]}")
    print(f"  annotated_by={saved.get('annotated_by')}  at={saved.get('annotated_at')}")
else:
    print(f"  HTTP {st}: {js}")

print()
print("=" * 74)
print("3) 读回验证")
print("=" * 74)
st, js = call("GET", f"/api/scene/config?source={enc}")
if isinstance(js, dict):
    d = js.get("data", {})
    print(f"  HTTP {st}  exists={js.get('exists')}")
    print(f"  斑马线: {len(d.get('crosswalk_zones') or [])} 个")
    print(f"  停止线: {d.get('stop_line_y')}   禁停区: {len(d.get('no_parking_zones') or [])} 个")
    print(f"  车道线: {len(d.get('lane_lines') or [])} 条")
else:
    print(f"  HTTP {st}: {js}")

print()
print("=" * 74)
print("4) 启动检测 -> 验证标注被自动加载")
print("=" * 74)
st, js = call("POST", "/api/realtime/start", {"video_path": SRC})
print(f"  启动: HTTP {st}")
import time
time.sleep(12)
st, js = call("GET", "/api/realtime/status")
if isinstance(js, dict):
    d = js.get("data", {})
    print(f"  running={d.get('running')} processed={d.get('processed_frames')}")
print()
print("  后端日志中的标注加载记录:")
import io
import os
p = os.path.join(os.environ.get("TEMP", "."), "api-sc.err")
if os.path.exists(p):
    for l in io.open(p, encoding="utf-8", errors="replace").read().splitlines():
        if "场景标注" in l or "scene" in l.lower():
            print("   " + l[:160])

print()
print("=" * 74)
print("5) 列出所有标注")
print("=" * 74)
st, js = call("GET", "/api/scene")
if isinstance(js, dict):
    for item in js.get("data", []):
        print(f"  {item.get('key')}  来源={item.get('annotated_by')}  "
              f"斑马线={item.get('has_crosswalk')}  停止线={item.get('stop_line_y')}")
