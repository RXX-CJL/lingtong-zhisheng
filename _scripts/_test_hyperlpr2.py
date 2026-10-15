"""hyperlpr3 车牌识别实测（模型已下载完成）"""

import os
import sys
import time

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402
import hyperlpr3 as lpr3  # noqa: E402

print("hyperlpr3 导入 OK")
t0 = time.time()
catcher = lpr3.LicensePlateCatcher()
print(f"识别器初始化 {time.time()-t0:.1f}s")

VIDEOS = [
    r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4",
    r"E:\output\1\test_assets\traffic_videos\701c5154f47975564a8039bb03bd3340.mp4",
    r"E:\output\1\test_assets\traffic_videos\test1.mp4",
]
total_hits = 0
for vp in VIDEOS:
    if not os.path.exists(vp):
        continue
    cap = cv2.VideoCapture(vp)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    name = os.path.basename(vp)[:16]
    print(f"\n{name} ({n} 帧)")
    for fi in range(0, n, max(1, n // 6)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        try:
            t1 = time.time()
            res = catcher(frame)
            ms = (time.time() - t1) * 1000
            if res:
                total_hits += len(res)
                parts = []
                for it in res[:4]:
                    try:
                        parts.append(f"{it[0]}({float(it[1]):.2f})")
                    except Exception:
                        parts.append(str(it)[:36])
                print(f"  帧{fi:4d}: {len(res)} 个 -> {', '.join(parts)}  [{ms:.0f}ms]")
            else:
                print(f"  帧{fi:4d}: 无  [{ms:.0f}ms]")
        except Exception as e:
            print(f"  帧{fi:4d}: 异常 {type(e).__name__}: {str(e)[:80]}")
    cap.release()

print()
print("=" * 70)
print(f"总检出: {total_hits} 个车牌")
print("结论:", "✅ 可用，可接入" if total_hits > 0 else "⚠ 这些视频里车牌太小，未检出")
