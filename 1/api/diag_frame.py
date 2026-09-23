# -*- coding: utf-8 -*-
"""诊断脚本：抓取 MJPEG 流第一帧并保存，检查是否黑屏"""
import urllib.request
import time

url = "http://127.0.0.1:8001/api/realtime/stream?t=" + str(int(time.time()*1000))
out_path = r"e:\output\1\api\diag_frame.jpg"

req = urllib.request.Request(url)
try:
    with urllib.request.urlopen(req, timeout=8) as resp:
        buf = b""
        # MJPEG 流格式: --frame\r\nContent-Type: image/jpeg\r\n\r\n<jpeg>\r\n
        # 读取直到拿到第一个完整的 jpeg
        start = time.time()
        while time.time() - start < 8:
            chunk = resp.read(4096)
            if not chunk:
                break
            buf += chunk
            # 找第一个 jpeg 起始 (FFD8) 和结束 (FFD9)
            jpg_start = buf.find(b'\xff\xd8')
            if jpg_start != -1:
                jpg_end = buf.find(b'\xff\xd9', jpg_start)
                if jpg_end != -1:
                    jpg_data = buf[jpg_start:jpg_end+2]
                    with open(out_path, 'wb') as f:
                        f.write(jpg_data)
                    # 分析像素
                    import cv2
                    import numpy as np
                    img = cv2.imread(out_path)
                    if img is None:
                        print(f"FAIL: saved {len(jpg_data)} bytes but cv2.imread returned None")
                    else:
                        h, w = img.shape[:2]
                        mean = float(np.mean(img))
                        std = float(np.std(img))
                        minv = int(np.min(img))
                        maxv = int(np.max(img))
                        print(f"OK: {w}x{h}, mean={mean:.1f}, std={std:.1f}, min={minv}, max={maxv}, bytes={len(jpg_data)}")
                        if mean < 5 and std < 5:
                            print("VERDICT: BLACK SCREEN (黑屏)")
                        elif std < 2:
                            print("VERDICT: SOLID COLOR (纯色，无内容)")
                        else:
                            print("VERDICT: HAS CONTENT (有画面内容)")
                    break
        else:
            print(f"FAIL: no complete jpeg in 8s, got {len(buf)} bytes; head={buf[:50]!r}")
except Exception as e:
    print(f"ERROR: {e}")
