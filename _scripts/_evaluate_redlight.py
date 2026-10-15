# -*- coding: utf-8 -*-
"""闯红灯识别成功率评测（真值 CSV + 逐帧 trace）

★为什么要它（2026-10-06 由 DSH 建立）
  在此之前"识别成功不成功"只能靠几个事件行去猜，没有可核对的数。
  本脚本把三件事变成数字：

    ① 判色准确率   —— 受控方向那盏灯的 CNN 判色 vs 真值灯态（逐帧）
    ② 闯红灯检出率 —— 真值"红灯期越线"那一次，系统有没有报出来
    ③ 误报率       —— 非真违规时段报了多少次 red_light

  真值来自 `_dual_cam_demo\\ground_truth_dual.csv`（**该文件只有 (x,y) 与
  灯态/越线列可信**；cam1_u/v 是模型输出，本脚本不用它）。
  逐帧数据来自检测器 trace（环境变量 RT_TRACE_JSONL 开启）。

用法（两步）：
  # 1) 带 trace 跑一遍演示视频（后端已启动时改环境变量需重启后端）
  $env:RT_TRACE_JSONL='E:\\output\\_rt_trace.jsonl'
  #    然后 POST /api/realtime/start {"video_path":"E:\\output\\_dual_cam_demo\\dual_cam_demo_lossless.mkv"}
  # 2) 评测
  & 'C:\\miniconda\\envs\\zhitong-gpu\\python.exe' -B E:\\output\\_scripts\\_evaluate_redlight.py
"""
import csv
import json
import os
import sys

TRACE = os.environ.get("RT_TRACE", r"E:\output\_rt_trace.jsonl")
CSV = r"E:\output\_dual_cam_demo\ground_truth_dual.csv"
FPS = 20.0
HOLD_SEC = 1.5          # 检测器的"持续确认"时长（RUNTIME_SETTINGS.hold_sec）
# 真违规窗口：越线前 0.5s ~ 后 4.0s
#   为什么要到 +4.0s：① hold_sec=1.5 的持续确认；② 检测循环只处理约 1/3 的帧
#   （实测 ~3 fps 处理 vs 20 fps 视频），上报会滞后；③ cooldown_sec=8 内同一
#   违规可能换 track_id 再报一次（DIAG-TRACK 记录的老问题）。
#   窗口上限 4.0s 仍能排除"绿灯相位误报"（真值越线 9.55s -> 绿灯 15.05s 起）。
WIN_BEFORE, WIN_AFTER = 0.5, 4.0
EPISODE_GAP = 2.0       # 同一次违规的连续帧间隔上限（秒）


def load_truth(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    by_frame, by_tag = {}, {}
    for r in rows:
        try:
            fr = int(r["frame"])
        except (TypeError, ValueError):
            continue
        st = (r.get("readback_state") or "").strip().lower()
        by_frame[fr] = {"state": st, "t": float(r["t_sec"])}
        by_tag.setdefault(r["tag"], []).append(
            (fr, float(r["t_sec"]), float(r["x"]), float(r["y"]),
             int(r["crossed_stop"] or 0), st))
    for k in by_tag:
        by_tag[k].sort()
    return by_frame, by_tag


def truth_violations(by_tag):
    """真值：哪些车在红灯期越过停止线（= 真闯红灯）"""
    out = []
    for tag, seq in by_tag.items():
        prev = 0
        for (fr, t, x, y, c, st) in seq:
            if c == 1 and prev == 0:
                out.append({"tag": tag, "t": t, "frame": fr, "state": st,
                            "is_violation": st.startswith("red")})
            prev = c
    return out


def load_trace(path):
    if not os.path.exists(path):
        print("!! 找不到 trace 文件：%s\n   请先用 RT_TRACE_JSONL 环境变量启动后端并跑一遍视频" % path)
        sys.exit(2)
    recs = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except Exception:
            continue
    recs.sort(key=lambda r: r.get("f", 0))
    return recs


def split_loops(recs):
    """按视频时间回绕切分循环（每个循环 = 完整播放一遍）"""
    loops, cur, last_t = [], [], -1.0
    for r in recs:
        t = float(r.get("t") or 0.0)
        if t < last_t - 1.0 and cur:
            loops.append(cur)
            cur = []
        cur.append(r)
        last_t = t
    if cur:
        loops.append(cur)
    return loops


def episodes(recs, key="red_light"):
    """把逐帧的 red_light 触发合并成"违规事件"（间隔 > EPISODE_GAP 算新事件）"""
    eps, prev_t = [], None
    for r in recs:
        hit = [v for v in (r.get("viol") or [])
               if str(v.get("type") or "").lower() == key]
        if not hit:
            continue
        t = float(r.get("t") or 0.0)
        if prev_t is None or (t - prev_t) > EPISODE_GAP:
            eps.append({"t_start": t, "t_end": t, "n_frames": 1,
                        "conf": max(float(v.get("conf") or 0) for v in hit)})
        else:
            eps[-1]["t_end"] = t
            eps[-1]["n_frames"] += 1
            eps[-1]["conf"] = max(eps[-1]["conf"],
                                  max(float(v.get("conf") or 0) for v in hit))
        prev_t = t
    return eps


def main():
    by_frame, by_tag = load_truth(CSV)
    recs = load_trace(TRACE)
    loops = split_loops(recs)
    tv = truth_violations(by_tag)
    print("=" * 78)
    print("闯红灯识别成功率评测")
    print("=" * 78)
    print("trace : %s（%d 帧，%d 个循环）" % (TRACE, len(recs), len(loops)))
    print("真值  : %s" % CSV)
    print("相位数: ", end="")
    prev = None
    for fr in sorted(by_frame):
        if by_frame[fr]["state"] != prev:
            print("%s@%.2fs " % (by_frame[fr]["state"], by_frame[fr]["t"]), end="")
            prev = by_frame[fr]["state"]
    print()
    print("\n真值里的越线事件：")
    for v in tv:
        print("  %-12s t=%6.2fs 灯态=%-6s -> %s"
              % (v["tag"], v["t"], v["state"],
                 "★真闯红灯" if v["is_violation"] else "非违规（灯不是红）"))
    truth_red = [v for v in tv if v["is_violation"]]

    # ---- ① 判色准确率（逐帧，只统计"人工标了 ROI"的帧）------------------
    print("\n" + "-" * 78)
    print("① 判色准确率（受控方向灯，CNN vs 真值灯态）")
    print("-" * 78)
    conf = {}
    n_ok = n_all = n_miss = 0
    for r in recs:
        if str(r.get("scope")) not in ("roi", "roi_miss"):
            continue
        t = float(r.get("t") or 0.0)
        fr = int(round(t * FPS))
        tr = by_frame.get(fr)
        if not tr:
            continue
        judged = str(r.get("state") or "")
        truth = tr["state"]
        if str(r.get("scope")) == "roi_miss" or not judged:
            n_miss += 1
            continue
        n_all += 1
        conf[(truth, judged)] = conf.get((truth, judged), 0) + 1
        if judged == truth or (truth.startswith("red") and judged == "red"):
            n_ok += 1
    if n_all:
        print("  逐帧判色：正确 %d / %d = %.1f%%（另有 %d 帧 ROI 内没判出灯）"
              % (n_ok, n_all, 100.0 * n_ok / n_all, n_miss))
        print("  混淆（真值 -> 判定）：")
        for (a, b), c in sorted(conf.items(), key=lambda kv: -kv[1]):
            flag = "  ← 危险方向（漏红灯）" if a.startswith("red") and b != "red" else ""
            print("     真值 %-7s -> 判定 %-7s : %4d 帧%s" % (a, b, c, flag))
    else:
        print("  !! 没有可比对的帧（trace 里没有 roi 作用域记录）")

    # ---- ②③ 逐循环 检出 / 误报 -----------------------------------------
    print("\n" + "-" * 78)
    print("②③ 闯红灯事件：检出与误报（逐循环）")
    print("-" * 78)
    tot_hit = tot_fp = tot_dup = 0
    for i, lp in enumerate(loops, 1):
        eps = episodes(lp, "red_light")
        raw = sum(1 for r in lp for v in (r.get("viol") or [])
                  if str(v.get("type") or "").lower() == "red_light")
        tmax = max(float(r.get("t") or 0) for r in lp)
        # 三分类：检出 / 同一违规重复上报 / 误报
        kinds = []
        hit_done = False
        for e in eps:
            in_win = any(e["t_start"] <= v["t"] + WIN_AFTER and
                         e["t_end"] >= v["t"] - WIN_BEFORE for v in truth_red)
            if in_win and not hit_done:
                kinds.append((e, "hit"))
                hit_done = True
            elif in_win:
                kinds.append((e, "dup"))
            else:
                kinds.append((e, "fp"))
        hit_n = sum(1 for _, k in kinds if k == "hit")
        dup_n = sum(1 for _, k in kinds if k == "dup")
        fp_n = sum(1 for _, k in kinds if k == "fp")
        tot_hit += hit_n
        tot_dup += dup_n
        tot_fp += fp_n
        miss = max(0, len(truth_red) - hit_n)
        print("  循环%d（覆盖到 t=%.1fs，%d 帧，%d 帧带 red_light 标记）"
              % (i, tmax, len(lp), raw))
        print("     真违规窗口 %s" % (["%.2fs" % v["t"] for v in truth_red] or "无"))
        label = {"hit": "✅ 检出  ", "dup": "⚠ 重复上报", "fp": "❌ 误报  "}
        for e, k in kinds:
            print("     %s t=%.2f~%.2fs  conf=%.2f  %d 帧"
                  % (label[k], e["t_start"], e["t_end"], e["conf"], e["n_frames"]))
        if not eps:
            print("     （本循环没有 red_light 事件）")
        print("     小结：检出 %d / 重复 %d / 误报 %d / 漏报 %d"
              % (hit_n, dup_n, fp_n, miss))

    print("\n" + "=" * 78)
    print("总判定（%d 个循环）：" % len(loops))
    print("  · 真值闯红灯：每个循环 1 次（红灯期越线）")
    print("  · 系统：检出 %d 次 / 同一违规重复上报 %d 次 / 误报 %d 次"
          % (tot_hit, tot_dup, tot_fp))
    if tot_hit + tot_dup + tot_fp:
        prec = 100.0 * tot_hit / (tot_hit + tot_dup + tot_fp)
        print("  · 精确率（检出 / 全部 red_light 事件）= %.0f%%" % prec)
    if n_all:
        print("  · 判色准确率 %.1f%%（逐帧，%d 帧可比对）"
              % (100.0 * n_ok / n_all, n_all))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
