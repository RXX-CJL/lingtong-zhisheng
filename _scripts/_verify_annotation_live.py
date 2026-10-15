"""验证真实检测流程的标注输出：抓 MJPEG 流的一帧 + 检查证据图"""

import os
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8001"
OUT = r"E:\output\_screens"
VIDEO = r"E:\output\1\test_assets\traffic_videos\test1.mp4"

print("=" * 74)
print("1) 启动检测")
print("=" * 74)
body = ('{"video_path":"' + VIDEO.replace("\\", "\\\\") + '"}').encode()
req = urllib.request.Request(BASE + "/api/realtime/start", data=body, method="POST")
req.add_header("Content-Type", "application/json")
with urllib.request.urlopen(req, timeout=60) as r:
    print("  ", r.read().decode("utf-8", "ignore"))

print()
print("=" * 74)
print("2) 等 35 秒后抓 MJPEG 流的一帧（带标注的画面）")
print("=" * 74)
time.sleep(35)

os.makedirs(OUT, exist_ok=True)
shot = os.path.join(OUT, "live_annotated.jpg")
try:
    req = urllib.request.Request(BASE + "/api/realtime/stream")
    with urllib.request.urlopen(req, timeout=30) as resp:
        buf = b""
        # 读一段 multipart 数据，提取第一个 JPEG
        while len(buf) < 400000:
            chunk = resp.read(8192)
            if not chunk:
                break
            buf += chunk
            start = buf.find(b"\xff\xd8")     # JPEG SOI
            end = buf.find(b"\xff\xd9")       # JPEG EOI
            if start >= 0 and end > start:
                jpg = buf[start:end + 2]
                with open(shot, "wb") as f:
                    f.write(jpg)
                print(f"  已保存: {shot}  ({len(jpg)} 字节)")
                break
        else:
            print("  未能从流中提取到完整 JPEG")
except Exception as e:
    print(f"  取流失败: {type(e).__name__}: {str(e)[:150]}")

print()
print("=" * 74)
print("3) 状态与渲染统计")
print("=" * 74)
with urllib.request.urlopen(BASE + "/api/realtime/status", timeout=20) as r:
    import json
    d = json.loads(r.read().decode("utf-8", "ignore")).get("data", {})
    print(f"  running={d.get('running')} processed={d.get('processed_frames')} "
          f"总帧={d.get('total_frames')} 违规={d.get('violation_count')} fps={d.get('current_fps')}")
    print(f"  追踪车辆={d.get('tracked_vehicle_count')}")

print()
print("=" * 74)
print("4) 最新证据图（画框后的违规证据）")
print("=" * 74)
up = r"E:\output\1\api\uploads"
if os.path.isdir(up):
    files = sorted([f for f in os.listdir(up) if f.startswith("realtime_")],
                   key=lambda f: os.path.getmtime(os.path.join(up, f)), reverse=True)
    print(f"  uploads 下 realtime_* 文件数: {len(files)}")
    for f in files[:4]:
        p = os.path.join(up, f)
        print(f"    {f}  {os.path.getsize(p)/1024:.0f} KB  {time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(p)))}")
    if files:
        newest = os.path.join(up, files[0])
        dst = os.path.join(OUT, "evidence_annotated.jpg")
        import shutil
        shutil.copy2(newest, dst)
        print(f"  最新证据图已复制: {dst}")
else:
    print("  uploads 目录不存在")

print()
print("=" * 74)
print("5) 停止检测")
print("=" * 74)
req = urllib.request.Request(BASE + "/api/realtime/stop", method="POST")
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("  ", r.read().decode("utf-8", "ignore"))
except Exception as e:
    print("  ", e)
