"""看本轮新增事件的细节：关键帧编号、触发时刻、AI 理由。

判断三件事：
  1. 关键帧编号是否已从 0,80,160 变成小数字（时钟修复是否生效）
  2. 一圈之内同类型违规触发了几次（去重是否生效）
  3. AI 驳回的理由是否仍是"画面中无车辆"
"""
import json
import sqlite3
import sys
import time


def main():
    since = int(sys.argv[1]) if len(sys.argv) > 1 else 2337
    c = sqlite3.connect(r"E:\output\1\api\zhitong_violations.db")
    c.row_factory = sqlite3.Row
    cur = c.cursor()
    cur.execute("""SELECT id, event_type, state, trigger_time, created_at,
                          key_frames, vehicle_info, scene_context, ai_judgment,
                          ai_explanation
                   FROM traffic_events WHERE id > ? ORDER BY id""", (since,))
    rows = cur.fetchall()
    print("本轮新增事件 %d 条（id > %d）\n" % (len(rows), since))
    print("%-6s %-11s %-13s %-24s %-16s %s" %
          ("id", "类型", "状态", "本地 time.time()", "关键帧编号", "AI 灯态/车"))
    for r in rows:
        kf = r["key_frames"] or ""
        nums = []
        try:
            d = json.loads(kf)
            for it in d:
                s = it if isinstance(it, str) else json.dumps(it)
                if "_frame_" in s:
                    nums.append(s.split("_frame_")[-1].split(".")[0])
        except Exception:
            pass
        sc = {}
        try:
            sc = json.loads(r["scene_context"] or "{}")
        except Exception:
            pass
        aj = str(r["ai_judgment"] or "")
        has_no_car = ("无任何车辆" in aj) or ("未见任何车辆" in aj) or ("未检测到任何车辆" in aj)
        print("%-6s %-11s %-13s %-24s %-16s 灯态=%-7s 无车=%s"
              % (r["id"], r["event_type"], r["state"],
                 str(r["trigger_time"])[:24], ",".join(nums) or "(无)",
                 sc.get("traffic_light_state"), "是" if has_no_car else "否"))

    print("\n=== AI 驳回理由抽样（最新 3 条）===")
    for r in rows[-3:]:
        aj = r["ai_judgment"] or ""
        try:
            d = json.loads(aj)
            reason = ((d.get("doubao") or {}).get("reasoning") or "")[:400]
        except Exception:
            reason = str(aj)[:400]
        print("\n#%s %s" % (r["id"], r["event_type"]))
        print("   " + reason.replace("\n", " ")[:380])
    return 0


if __name__ == "__main__":
    sys.exit(main())
