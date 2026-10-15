"""停掉后端正在跑的检测（止损，避免继续循环产生无效事件）。"""
import json
import urllib.request

BASE = "http://127.0.0.1:8001"


def call(path, method="GET", body=None, timeout=30):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8")[:300]
    except Exception as e:
        return None, str(e)


def main():
    print("stop ->", call("/api/realtime/stop", "POST"))
    import time
    time.sleep(3)
    s, b = call("/api/realtime/status")
    print("status ->", s, b[:400])
    return 0


if __name__ == "__main__":
    main()
