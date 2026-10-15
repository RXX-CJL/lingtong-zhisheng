"""验证观察器：跑检测期间用来看"新代码有没有生效"。

用法（检测已在跑时运行）：
    & 'C:\miniconda\envs\zhitong-gpu\python.exe' E:\output\_scripts\_verify_run.py

它会打印：
  1. 新事件数（对比基线 2337）—— 判断有没有"灌垃圾"
  2. 最新事件的 关键帧编号 —— 判断"证据帧是否取到了车在路口的时段"
  3. AI 复核结论 —— 判断"是不是还在被全量驳回"
  4. 违规类型统计
"""
import json
import sqlite3
import sys
import time
import urllib.request

DB = r"E:\output\1\api\zhitong_violations.db"
BASE_EVENTS = 2337        # 跑之前的基线（新事件数 = 当前 - 这个）
BASE_ID = 2337
ROUNDS = 12               # 观察多少轮
INTERVAL = 15             # 每轮间隔秒


def api(path, timeout=30):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8001" + path, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"_err": str(e)}


def main():
    print("基线：事件 %d 条。开始观察（每 %d 秒一轮，共 %d 轮）\n" % (BASE_EVENTS, INTERVAL, ROUNDS))
    for i in range(ROUNDS):
        st = (api("/api/realtime/status").get("data") or {})
        c = sqlite3.connect(DB)
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) FROM traffic_events WHERE id > ?", (BASE_ID,))
        new_evt = cur.fetchone()[0]
        cur.execute("""SELECT id, event_type, state, key_frames FROM traffic_events
                       WHERE id > ? ORDER BY id DESC LIMIT 5""", (BASE_ID,))
        rows = cur.fetchall()
        c.close()
        print("[%3ds] 运行=%-5s 处理帧=%-6s | 新事件=%-3d %s"
              % (i * INTERVAL, st.get("running"), st.get("total_frames"),
                 new_evt, "  <-- 若这里猛涨说明还在灌垃圾" if new_evt > 30 else ""))
        for r in rows[:3]:
            kf = r[3] or ""
            try:
                d = json.loads(kf)
                nums = []
                for it in d:
                    s = it if isinstance(it, str) else json.dumps(it)
                    nums.append(s.split("_frame_")[-1].split(".")[0] if "_frame_" in s else "?")
                kftxt = "关键帧=[" + ",".join(nums) + "]"
            except Exception:
                kftxt = "关键帧=(无)"
            print("        #%s %-16s %-14s %s" % (r[0], r[1], r[2], kftxt))
        if i < ROUNDS - 1:
            time.sleep(INTERVAL)

    print("\n" + "=" * 70)
    print("最终统计（本轮新增事件，id > %d）" % BASE_ID)
    print("=" * 70)
    c = sqlite3.connect(DB)
    cur = c.cursor()
    cur.execute("SELECT event_type, COUNT(*) FROM traffic_events WHERE id > ? GROUP BY event_type",
                (BASE_ID,))
    for r in cur.fetchall():
        print("   类型 %-20s %d" % (r[0], r[1]))
    cur.execute("SELECT state, COUNT(*) FROM traffic_events WHERE id > ? GROUP BY state", (BASE_ID,))
    for r in cur.fetchall():
        print("   状态 %-20s %d" % (r[0], r[1]))
    cur.execute("""SELECT COUNT(*) FROM traffic_events
                   WHERE id > ? AND ai_judgment LIKE '%confirmed%'""", (BASE_ID,))
    print("   AI 判为 confirmed 的: %d" % cur.fetchone()[0])
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
