"""端到端验证：把「双摄闯红灯演示」视频喂进项目真实检测链路，看违规能否被判出来。

用的是真实代码路径：RealtimeViolationDetector.process_frame()
（与 /realtime/detect-frame 同一入口，只是这里逐帧喂，便于收集每帧结果）
"""
import json
import os
import sys
import time
from collections import Counter, defaultdict

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
sys.path.insert(0, r"E:\output\1")

VIDEO = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"
OUTDIR = r"E:\output\_e2e"
os.makedirs(OUTDIR, exist_ok=True)
MAX_FRAMES = int(os.environ.get("E2E_MAX_FRAMES", "0"))   # 0 = 全片


def main():
    from realtime_detector import RealtimeViolationDetector

    cap = cv2.VideoCapture(VIDEO)
    if not cap.isOpened():
        print("无法打开视频:", VIDEO)
        return 1
    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print("视频 %dx%d  %.2f fps  %d 帧" % (W, H, fps, total))

    det = RealtimeViolationDetector()
    det._source_fps = float(fps)          # 让追踪器用视频时间而非墙钟

    n = total if MAX_FRAMES <= 0 else min(total, MAX_FRAMES)
    per_frame = []
    tl_states = Counter()
    vtypes = Counter()
    vframes = defaultdict(list)
    frames_with_det = 0
    veh_conf = []
    t0 = time.time()

    for i in range(n):
        ok, frame = cap.read()
        if not ok:
            print("第 %d 帧读取失败，提前结束" % i)
            break
        det.frame_count = i
        try:
            res = det.process_frame(frame)
        except Exception as e:
            print("  第 %d 帧处理异常: %s" % (i, e))
            continue
        dets = res.get("detections") or []
        tvs = res.get("tracked_vehicles") or []
        viols = res.get("violations") or []
        sc = getattr(det, "scene_config", {}) or {}
        tl = sc.get("traffic_light_state", "unknown")
        tl_states[tl] += 1
        if dets:
            frames_with_det += 1
        for d in dets:
            if d.get("class_name") in ("car", "truck", "bus"):
                veh_conf.append(float(d.get("confidence") or 0))
        for v in viols:
            vt = v.get("violation_type") or v.get("type") or "?"
            vtypes[vt] += 1
            vframes[vt].append(i)
        per_frame.append({
            "frame": i, "t": round(i / fps, 3),
            "n_det": len(dets), "n_tracked": len(tvs),
            "n_viol": len(viols),
            "tl_state": tl,
            "tl_raw": (res.get("ai_trace") or {}).get("traffic_light") if isinstance(res.get("ai_trace"), dict) else None,
            "vtypes": [ (v.get("violation_type") or v.get("type")) for v in viols ],
            "tl_confirmed": len(getattr(det, "_last_traffic_lights", []) or []),
            "tl_stats": getattr(det, "traffic_light_stats", {}),
        })
        if i % 40 == 0:
            print("  %4d/%d  det=%2d veh=%2d viol=%d tl=%-8s 已用 %.1fs"
                  % (i, n, len(dets), len(tvs), len(viols), tl, time.time() - t0))
    cap.release()
    dt = time.time() - t0

    print("\n" + "=" * 78)
    print("端到端结果（%d 帧，耗时 %.1f s，平均 %.1f ms/帧）" % (len(per_frame), dt, 1000 * dt / max(1, len(per_frame))))
    print("=" * 78)
    print("有检测结果的帧: %d/%d" % (frames_with_det, len(per_frame)))
    print("车辆检测置信度: n=%d  均值=%.3f  最小=%.3f  最大=%.3f"
          % (len(veh_conf), np.mean(veh_conf) if veh_conf else 0,
             np.min(veh_conf) if veh_conf else 0, np.max(veh_conf) if veh_conf else 0))
    print("红绿灯状态分布:", dict(tl_states))
    print("违规类型统计:", dict(vtypes) if vtypes else "（无）")
    for vt, fl in vframes.items():
        print("   %-16s 出现 %d 帧，帧号 %s..%s" % (vt, len(fl), fl[0], fl[-1]))

    # 红绿灯判色统计汇总
    agg = Counter()
    for r in per_frame:
        for k, v in (r.get("tl_stats") or {}).items():
            agg[k] += int(v or 0)
    print("红绿灯判色累计统计:", dict(agg))
    tl_confirm = sum(1 for r in per_frame if r["tl_confirmed"] > 0)
    print("确认出红绿灯框的帧: %d/%d" % (tl_confirm, len(per_frame)))

    with open(os.path.join(OUTDIR, "e2e_result.json"), "w", encoding="utf-8") as f:
        json.dump({"video": VIDEO, "frames": len(per_frame), "fps": fps,
                   "tl_states": dict(tl_states), "violation_types": dict(vtypes),
                   "violation_frames": {k: v for k, v in vframes.items()},
                   "tl_stats": dict(agg), "per_frame": per_frame}, f,
                  ensure_ascii=False, indent=2)
    print("\n明细: %s" % os.path.join(OUTDIR, "e2e_result.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
