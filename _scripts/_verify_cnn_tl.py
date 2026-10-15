"""验证 CNN4 红绿灯标注的实际效果：抓 MJPEG 帧 + 读统计"""

import json
import os
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8001"
OUT = r"E:\output\_screens"
os.makedirs(OUT, exist_ok=True)

print("=" * 74)
print("1) 状态与红绿灯统计")
print("=" * 74)
with urllib.request.urlopen(BASE + "/api/realtime/status", timeout=20) as r:
    d = json.loads(r.read().decode("utf-8", "ignore")).get("data", {})
print(f"  running={d.get('running')}  processed={d.get('processed_frames')}  "
      f"违规={d.get('violation_count')}  追踪={d.get('tracked_vehicle_count')}")
tls = d.get("traffic_light_stats")
if tls:
    print(f"  红绿灯统计: {json.dumps(tls, ensure_ascii=False)}")
else:
    print("  红绿灯统计: (未在 status 中暴露，稍后从日志读取)")

print()
print("=" * 74)
print("2) 抓 3 帧 MJPEG（间隔 4 秒，提高命中红绿灯的概率）")
print("=" * 74)
for k in range(3):
    shot = os.path.join(OUT, f"cnn_tl_{k}.jpg")
    try:
        req = urllib.request.Request(BASE + "/api/realtime/stream")
        with urllib.request.urlopen(req, timeout=30) as resp:
            buf = b""
            for _ in range(60):
                chunk = resp.read(8192)
                if not chunk:
                    break
                buf += chunk
                s = buf.find(b"\xff\xd8")
                e = buf.find(b"\xff\xd9")
                if s >= 0 and e > s:
                    with open(shot, "wb") as f:
                        f.write(buf[s:e + 2])
                    print(f"  帧{k+1}: {shot}  ({e+2-s} 字节)")
                    break
            else:
                print(f"  帧{k+1}: 未取到完整 JPEG")
    except Exception as ex:
        print(f"  帧{k+1}: 失败 {type(ex).__name__}: {str(ex)[:80]}")
    time.sleep(4)

print()
print("=" * 74)
print("3) 后端日志里的红绿灯相关信息")
print("=" * 74)
err = os.path.join(os.environ.get("TEMP", "."), "api-cnn.err")
if os.path.exists(err):
    import io
    lines = io.open(err, encoding="utf-8", errors="replace").read().splitlines()
    hits = [l for l in lines if "红绿灯" in l or "traffic" in l.lower() or "分类器" in l]
    print(f"  日志 {len(lines)} 行，命中 {len(hits)} 行")
    for l in hits[-12:]:
        print("   " + l[:150])
    print()
    print("  最后 6 行:")
    for l in lines[-6:]:
        print("   " + l[:150])
else:
    print("  日志不存在")
