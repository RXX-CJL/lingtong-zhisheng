"""秒级快照：当前事件库规模 + 新代码是否生效（时钟注入日志）。"""
import json
import sqlite3
import urllib.request

DB = r"E:\output\1\api\zhitong_violations.db"


def main():
    c = sqlite3.connect(DB)
    cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM traffic_events")
    n_evt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM violation_evidences")
    n_evi = cur.fetchone()[0]
    cur.execute("SELECT MAX(id) FROM traffic_events")
    max_id = cur.fetchone()[0]
    print("=== 基线快照 ===")
    print("  traffic_events 总数   : %d" % n_evt)
    print("  violation_evidences   : %d" % n_evi)
    print("  traffic_events 最大 id: %s" % max_id)

    try:
        with urllib.request.urlopen("http://127.0.0.1:8001/api/realtime/status",
                                    timeout=20) as r:
            d = json.loads(r.read().decode("utf-8")).get("data") or {}
        print("\n=== 后端状态 ===")
        for k in ("running", "source_kind", "video_path", "loop_playback",
                  "processed_frames", "total_frames", "avg_fps", "violation_count"):
            if k in d:
                print("  %-18s = %s" % (k, d[k]))
    except Exception as e:
        print("  状态获取失败:", e)
    return 0


if __name__ == "__main__":
    main()
