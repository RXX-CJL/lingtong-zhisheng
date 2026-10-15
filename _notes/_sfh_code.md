=== speed_from_history 起于 L357 ===
357: def speed_from_history(history: List[Dict], calibrator: SpeedCalibrator,
358:                        min_dt: float = 0.15, max_samples: int = 8,
359:                        expected_fps: float = None) -> Dict:
360:     """从轨迹历史估算实际车速
361: 
362:     history: [{'center': (x,y), 'timestamp': t}, ...]  按时间升序
363:     做法：取最近的若干点，计算总位移（像素）与总时长，按**平均 y** 标定后换算。
364:           用总位移而非单帧差分，可降低跟踪抖动带来的误差。
365: 
366:     expected_fps: 期望帧率（用于帧率补偿）。不传则从 dt 反推，
367:                   反推失败则不补偿（宁可低估，不可高估）。
368: 
369:     返回：
370:       {kmh, kmh_raw, fps_compensation, px_per_sec, samples, dt, fps,
371:        method, confidence, measurement_quality, note}
372:     """
373:     out = {"kmh": 0.0, "px_per_sec": 0.0, "samples": 0, "dt": 0.0,
374:            "method": calibrator.method, "confidence": calibrator.method,
375:            "note": calibrator.note}
376:     if not history or len(history) < 2:
377:         out["confidence"] = "unavailable"
378:         return out
379: 
380:     pts = history[-max_samples:]
381:     try:
382:         total_px = 0.0
383:         total_dt = 0.0
384:         ys = []
385:         for i in range(1, len(pts)):
386:             c0, c1 = pts[i - 1].get("center"), pts[i].get("center")
387:             t0, t1 = pts[i - 1].get("timestamp"), pts[i].get("timestamp")
388:             if not (c0 and c1 and t0 and t1):
389:                 continue
390:             dt = float(t1) - float(t0)
391:             if dt <= 0:
392:                 continue
393:             d = math.hypot(float(c1[0]) - float(c0[0]), float(c1[1]) - float(c0[1]))
394:             total_px += d
395:             total_dt += dt
396:             ys.append((float(c0[1]) + float(c1[1])) / 2.0)
397:     except (TypeError, ValueError, IndexError):
398:         out["confidence"] = "unavailable"
399:         return out
400: 
401:     if total_dt < min_dt or total_px <= 0:
402:         out["confidence"] = "unavailable"
403:         return out
404:     if any((float(pts[i].get("timestamp", 0)) - float(pts[i - 1].get("timestamp", 0))) > 1.0
405:            for i in range(1, len(pts))):
406:         # 轨迹有明显时间断裂（跟踪中断），降低可信度
407:         out["note"] = (out["note"] + "；轨迹含时间断裂，精度下降").strip("；")
408: 
409:     y_avg = sum(ys) / len(ys) if ys else calibrator.y_ref
410:     px_per_sec = total_px / total_dt
411:     kmh_raw = calibrator.px_speed_to_kmh(px_per_sec, y_avg)
412: 
413:     # ---- 帧率补偿 + 测量质量自检（2026-10-03 由 DSH 新增）--------------
414:     # 帧率：优先用调用方给的；否则从平均 dt 反推
415:     fps = None
416:     try:
