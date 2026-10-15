"""查出 realtime 相关接口的参数，便于正确调用。"""
import json
import urllib.request

BASE = "http://127.0.0.1:8001"


def main():
    with urllib.request.urlopen(BASE + "/openapi.json", timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    comps = d.get("components", {}).get("schemas", {})
    for p in ("/api/realtime/start", "/api/realtime/stop", "/api/realtime/status",
              "/api/realtime/events", "/api/realtime/source"):
        if p not in d["paths"]:
            continue
        for m, spec in d["paths"][p].items():
            print("%s %s" % (m.upper(), p))
            if spec.get("summary"):
                print("   summary: %s" % spec["summary"])
            for pr in (spec.get("parameters") or []):
                print("   query: %s (%s) required=%s default=%s"
                      % (pr["name"], pr["schema"].get("type"), pr.get("required"),
                         pr["schema"].get("default")))
            rb = spec.get("requestBody")
            if rb:
                sch = list(rb["content"].values())[0]["schema"]
                ref = sch.get("$ref")
                if ref:
                    name = ref.split("/")[-1]
                    comp = comps.get(name, {})
                    print("   body: %s" % name)
                    for k, v in (comp.get("properties") or {}).items():
                        print("      %-20s %-10s default=%s"
                              % (k, v.get("type"), v.get("default")))
                else:
                    print("   body raw: %s" % json.dumps(sch, ensure_ascii=False)[:220])
            print()


if __name__ == "__main__":
    main()
