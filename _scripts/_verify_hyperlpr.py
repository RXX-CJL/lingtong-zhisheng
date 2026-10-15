"""验证 hyperlpr3 车牌识别是否可用（用真实视频帧测试）"""

import os
import sys
import time

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402

print("=" * 74)
print("1) 导入检查")
print("=" * 74)
try:
    import hyperlpr3 as lpr3
    print("  hyperlpr3 导入成功")
    print("  可用属性:", [a for a in dir(lpr3) if not a.startswith('_')][:15])
except Exception as e:
    print(f"  ❌ 导入失败: {type(e).__name__}: {str(e)[:200]}")
    sys.exit(1)

print()
print("=" * 74)
print("2) 初始化识别器（首次会加载 ONNX 模型）")
print("=" * 74)
t0 = time.time()
try:
    catcher = lpr3.LicensePlateCatcher()
    print(f"  LicensePlateCatcher 初始化成功，耗时 {time.time()-t0:.1f}s")
except Exception as e:
    print(f"  ❌ 初始化失败: {type(e).__name__}: {str(e)[:250]}")
    sys.exit(1)

print()
print("=" * 74)
print("3) 用真实视频帧测试（多帧找车牌）")
print("=" * 74)
VIDEOS = [
    r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4",
    r"E:\output\1\test_assets\traffic_videos\701c5154f47975564a8039bb03bd3340.mp4",
    r"E:\output\1\test_assets\traffic_videos\test1.mp4",
]
hits = 0
for vp in VIDEOS:
    if not os.path.exists(vp):
        continue
    cap = cv2.VideoCapture(vp)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"\n  {os.path.basename(vp)[:16]}  ({total} 帧)")
    for fi in range(0, total, max(1, total // 8)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        try:
            t1 = time.time()
            res = catcher(frame)
            ms = (time.time() - t1) * 1000
            if res:
                hits += len(res)
                desc = []
                for item in res[:4]:
                    # hyperlpr3 返回格式: [code, confidence, type_idx, box]
                    try:
                        code, conf = item[0], item[1]
                        desc.append(f"{code}({conf:.2f})")
                    except Exception:
                        desc.append(str(item)[:40])
                print(f"    帧{fi:4d}: 检出 {len(res)} 个车牌 -> {', '.join(desc)}  ({ms:.0f}ms)")
            else:
                if fi % (max(1, total // 8) * 2) == 0:
                    print(f"    帧{fi:4d}: 无车牌  ({ms:.0f}ms)")
        except Exception as e:
            print(f"    帧{fi:4d}: 识别异常 {type(e).__name__}: {str(e)[:90]}")
    cap.release()

print()
print("=" * 74)
print(f"总检出行数: {hits}")
print("结论:", "✅ 车牌识别可用，可接入" if hits > 0 else "⚠ 未检出车牌（可能视频里车牌太小/太远）")
print("=" * 74)
