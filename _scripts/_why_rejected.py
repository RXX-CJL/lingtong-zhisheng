"""查 red_light / wrong_way 事件被拒的真实理由（读 state_history）。"""
import json
import sqlite3

DB = r"E:\output\1\api\zhitong_violations.db"


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()
    cur.execute("""SELECT id, event_id, event_type, state, trigger_time, created_at,
                          vehicle_info, scene_context, rule_judgment, ai_judgment,
                          ai_confidence, ai_explanation, state_history
                   FROM traffic_events ORDER BY id DESC LIMIT 14""")
    for r in cur.fetchall():
        print("=" * 78)
        print("#%s %-16s state=%-10s %s" % (r["id"], r["event_type"], r["state"],
                                            (r["created_at"] or "")[:19]))
        sh = r["state_history"]
        if sh:
            try:
                h = json.loads(sh) if isinstance(sh, str) else sh
                if isinstance(h, list):
                    for step in h[-4:]:
                        if isinstance(step, dict):
                            print("   历史: %s -> %s | %s" % (
                                step.get("from") or step.get("old_state"),
                                step.get("to") or step.get("new_state"),
                                (step.get("reason") or "")[:150]))
                        else:
                            print("   历史:", str(step)[:150])
                else:
                    print("   历史:", str(h)[:300])
            except Exception as e:
                print("   历史解析失败:", e, str(sh)[:200])
        else:
            print("   历史: (空)")
        vi = r["vehicle_info"]
        if vi:
            try:
                v = json.loads(vi) if isinstance(vi, str) else vi
                print("   车辆: speed=%s dir=%s calib=%s method=%s" % (
                    v.get("speed"), v.get("direction"),
                    (v.get("calibration") or (v.get("evidence") or {}).get("calibration")),
                    v.get("speed_method")))
            except Exception:
                pass
        if r["ai_judgment"]:
            print("   AI 判断: %s conf=%s" % (r["ai_judgment"], r["ai_confidence"]))
        if r["ai_explanation"]:
            print("   AI 说明:", str(r["ai_explanation"])[:220].replace("\n", " "))
    return 0


if __name__ == "__main__":
    main()
