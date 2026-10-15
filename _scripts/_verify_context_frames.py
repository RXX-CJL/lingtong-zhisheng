"""验证上下文帧合并（多帧拼图）是否真的能生成并送给 AI"""

import base64
import io
import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

import cv2  # noqa: E402
import numpy as np  # noqa: E402

out = []

# 1) 从真实视频取 3 帧，转 base64（模拟 get_context_frames 的输出）
VIDEO = r"E:\output\1\test_assets\traffic_videos\3e9b3f659e257969d581993be3c9e59e.mp4"
cap = cv2.VideoCapture(VIDEO)
frames_b64 = []
for pos in (100, 115, 130):
    cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
    ok, f = cap.read()
    if ok:
        _, buf = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frames_b64.append(base64.b64encode(buf.tobytes()).decode())
cap.release()
out.append(f"取到 {len(frames_b64)} 帧 base64（每帧约 {len(frames_b64[0])//1024}KB）")

# 2) 复现合并逻辑
MAX_FRAMES = 3
frames = frames_b64[-MAX_FRAMES:]
imgs = []
for f in frames:
    s = f.split(',', 1)[-1] if f.startswith('data:image') else f
    buf = base64.b64decode(s)
    arr = cv2.imdecode(np.frombuffer(buf, np.uint8), cv2.IMREAD_COLOR)
    if arr is not None and arr.size > 0:
        imgs.append(arr)
out.append(f"解码成功 {len(imgs)} 帧，尺寸 {[im.shape for im in imgs]}")

if len(imgs) >= 2:
    h = max(64, int(min(im.shape[0] for im in imgs)))
    scaled = []
    for im in imgs:
        sh = im.shape[0]
        if sh != h:
            w = int(im.shape[1] * h / max(1, sh))
            im = cv2.resize(im, (w, h))
        scaled.append(im)
    merged = np.hstack(scaled)
    out.append(f"合并成功: {merged.shape[1]}x{merged.shape[0]} (横向拼 {len(scaled)} 帧)")
    p = r"E:\output\_screens\context_merged.jpg"
    cv2.imwrite(p, merged, [cv2.IMWRITE_JPEG_QUALITY, 82])
    out.append(f"已存: {p}  ({os.path.getsize(p)//1024}KB)")
    # 合并后的 base64 大小（影响 API 请求体）
    _, buf2 = cv2.imencode(".jpg", merged, [cv2.IMWRITE_JPEG_QUALITY, 82])
    out.append(f"合并图 base64 大小: {len(base64.b64encode(buf2.tobytes()))//1024}KB")
    out.append("")
    out.append("结论: 多帧合并可用 ✅ —— AI 将看到 3 个时间点的画面")
else:
    out.append("❌ 合并失败：解码帧不足")

# 3) 真正调用一次云端（验证端到端，含新拼图）
out.append("")
out.append("=== 实测调用云端（豆包，带 3 帧拼图）===")
try:
    from cloud_collaborator import CloudCollaborator
    cc = CloudCollaborator()
    res = cc._analyze_with_dual_images(None, frames_b64[0], "speeding", frames_b64)
    ok = bool(res.get("success"))
    out.append(f"  success={ok}  used_frames={res.get('_context_frames_used')}")
    out.append(f"  is_violation_confirmed={res.get('is_violation_confirmed')} "
               f"confidence={res.get('confidence_adjusted')}")
    txt = str(res.get("result_text") or "")
    out.append(f"  result_text 前 400 字:")
    out.append("    " + txt[:400].replace("\n", "\n    "))
except Exception as e:
    import traceback
    out.append(f"  调用失败: {type(e).__name__}: {str(e)[:200]}")
    out.append("  " + traceback.format_exc()[-500:].replace("\n", "\n  "))

io.open(r"E:\output\_context_frames_test.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
