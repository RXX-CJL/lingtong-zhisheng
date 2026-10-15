"""读取关键闭环接口的参数定义（OpenAPI schema），不做任何写操作"""

import json
import urllib.request

BASE = "http://127.0.0.1:8001"
WANT = [
    ("/api/realtime/source", "post"),
    ("/api/realtime/start", "post"),
    ("/api/realtime/stop", "post"),
    ("/api/realtime/status", "get"),
    ("/api/realtime/events", "get"),
    ("/api/realtime/detect-frame", "post"),
    ("/api/violations/upload-multipart", "post"),
]

with urllib.request.urlopen(f"{BASE}/openapi.json", timeout=30) as r:
    spec = json.loads(r.read().decode("utf-8"))

comps = spec.get("components", {}).get("schemas", {})


def resolve(ref):
    name = ref.split("/")[-1]
    return name, comps.get(name, {})


def show_schema(name, sch, indent="      "):
    props = sch.get("properties", {})
    req = set(sch.get("required", []))
    if not props:
        print(f"{indent}(无字段)")
        return
    for pname, pdef in props.items():
        ptype = pdef.get("type") or pdef.get("anyOf") and "anyOf" or "?"
        if "anyOf" in pdef:
            types = [x.get("type") for x in pdef["anyOf"] if isinstance(x, dict)]
            ptype = "/".join(t for t in types if t)
        default = pdef.get("default", "—")
        mark = "必填" if pname in req else "可选"
        enum = ("  enum=" + str(pdef["enum"])) if "enum" in pdef else ""
        print(f"{indent}- {pname}: {ptype}  [{mark}]  默认={default}{enum}")
        if pdef.get("description"):
            print(f"{indent}    # {str(pdef['description'])[:90]}")


for path, method in WANT:
    item = spec["paths"].get(path)
    print("=" * 78)
    print(f"  {method.upper()} {path}")
    print("=" * 78)
    if not item:
        print("      路由不存在")
        continue
    op = item.get(method)
    if not op:
        print("      方法不存在")
        continue
    if op.get("summary"):
        print(f"      说明: {op['summary']}")
    params = op.get("parameters", [])
    if params:
        print("      -- 路径/查询参数 --")
        for p in params:
            sch = p.get("schema", {})
            print(f"        {p['name']} ({p['in']}) type={sch.get('type')} "
                  f"{'必填' if p.get('required') else '可选'} 默认={sch.get('default','—')}")
    rb = op.get("requestBody")
    if rb:
        print("      -- 请求体 --")
        content = rb.get("content", {})
        for ctype, cdef in content.items():
            print(f"        content-type: {ctype}")
            sch = cdef.get("schema", {})
            if "$ref" in sch:
                name, real = resolve(sch["$ref"])
                print(f"        schema: {name}")
                show_schema(name, real)
            elif sch.get("type") == "object" and sch.get("properties"):
                show_schema("inline", sch)
            else:
                print(f"        schema: {json.dumps(sch, ensure_ascii=False)[:200]}")
    print()
