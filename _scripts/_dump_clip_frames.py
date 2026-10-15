"""看看：事件送审时到底用了哪几张图？（找"裁错时间点"的证据）

只读查询 + 落盘几张图，供人工核对。
输出：
  1. 最近几个事件的时间线（触发时刻 vs 关键帧时刻）
  2. 把事件的关键帧拷到一个目录，便于你看"图里有没有车"
"""
import json
import os
import shutil
import sqlite3
import sys

DB = r"E:\output\1\api\zhitong_violations.db"
OUT = r"E:\output\_clip_check"
os.makedirs(OUT, exist_ok=True)


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()
    cur.execute("""SELECT id, event_id, event_type, state, trigger_time, created_at,
                          key_frames, event_video_path, trajectory
                   FROM traffic_events ORDER BY id DESC LIMIT 6""")
    rows = cur.fetchall()
    print("=" * 78)
    print("最近 6 个事件：触发时刻 / 关键帧")
    print("=" * 78)
    for r in rows:
        print("\n#%s  %s  状态=%s" % (r["id"], r["event_type"], r["state"]))
        print("   触发时刻 trigger_time = %s" % (r["trigger_time"] or "")[:26])
        print("   创建时刻 created_at   = %s" % (r["created_at"] or "")[:26])
        kf = r["key_frames"]
        if kf:
            try:
                d = json.loads(kf) if isinstance(kf, str) else kf
                if isinstance(d, list):
                    print("   关键帧数量 = %d" % len(d))
                    for i, it in enumerate(d[:6]):
                        if isinstance(it, dict):
                            print("      [%d] %s" % (i, json.dumps(it, ensure_ascii=False)[:150]))
                        else:
                            print("      [%d] %s" % (i, str(it)[:150]))
                else:
                    print("   关键帧:", str(d)[:300])
            except Exception as e:
                print("   关键帧解析失败:", e, str(kf)[:200])
        else:
            print("   关键帧: (空)")
        print("   事件视频: %s" % (r["event_video_path"] or "(空)"))
        tj = r["trajectory"]
        if tj:
            try:
                t = json.loads(tj) if isinstance(tj, str) else tj
                if isinstance(t, list) and t:
                    print("   轨迹点 %d 个，前3: %s" % (
                        len(t), json.dumps(t[:3], ensure_ascii=False)[:200]))
            except Exception:
                pass

    # 把存在的关键帧拷出来
    print("\n" + "=" * 78)
    print("把关键帧拷到 %s 便于查看" % OUT)
    print("=" * 78)
    n = 0
    for r in rows:
        kf = r["key_frames"]
        if not kf:
            continue
        try:
            d = json.loads(kf) if isinstance(kf, str) else kf
        except Exception:
            continue
        if not isinstance(d, list):
            continue
        for i, it in enumerate(d):
            p = None
            if isinstance(it, dict):
                p = it.get("path") or it.get("image_path") or it.get("file")
            elif isinstance(it, str) and os.path.exists(it):
                p = it
            if p and os.path.exists(p):
                dst = os.path.join(OUT, "evt%s_%s_%02d%s"
                                   % (r["id"], r["event_type"], i, os.path.splitext(p)[1]))
                shutil.copy2(p, dst)
                n += 1
    print("   拷贝了 %d 张" % n)
    if n == 0:
        print("   （关键帧字段里没有可直接读取的文件路径；下面列出 uploads 里最近的图）")
        up = r"E:\output\1\api\uploads"
        if os.path.isdir(up):
            fs = sorted((os.path.join(up, f) for f in os.listdir(up) if f.endswith(".jpg")),
                        key=os.path.getmtime, reverse=True)[:8]
            for f in fs:
                print("      %s  (%s)" % (os.path.basename(f),
                                          __import__("time").strftime(
                                              "%H:%M:%S", __import__("time").localtime(
                                                  os.path.getmtime(f)))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
