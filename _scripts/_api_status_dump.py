"""看 /api/realtime/status 与 /events 的真实结构。"""
import json
import urllib.request

BASE = "http://127.0.0.1:8001"


def get(path, timeout=60):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:600]
    except Exception as e:
        return None, str(e)


def main():
    s, st = get("/api/realtime/status")
    print("=== /api/realtime/status  (%s) ===" % s)
    if isinstance(st, dict):
        for k in sorted(st.keys()):
            v = st[k]
            vs = json.dumps(v, ensure_ascii=False)
            print("   %-32s = %s" % (k, vs[:160]))
    else:
        print("  ", st)

    print("\n=== /api/realtime/events?size=5 结构 ===")
    s, ev = get("/api/realtime/events?size=5")
    print("  status:", s, " type:", type(ev).__name__)
    if isinstance(ev, dict):
        print("  顶层键:", list(ev.keys()))
        for k, v in ev.items():
            if isinstance(v, list):
                print("   %s: list len=%d" % (k, len(v)))
                if v:
                    print("     首条的键:", list(v[0].keys()))
                    print("     首条:", json.dumps(v[0], ensure_ascii=False)[:500])
            else:
                print("   %s = %s" % (k, json.dumps(v, ensure_ascii=False)[:200]))
    return 0


if __name__ == "__main__":
    main()
