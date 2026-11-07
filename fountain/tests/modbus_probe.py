# -*- coding: utf-8 -*-
"""modbus_probe.py —— 手写最小 Modbus TCP 客户端（不装任何包）"""
import socket, struct, sys, time
sys.stdout.reconfigure(encoding="utf-8")

HOST, PORT, UNIT = "127.0.0.1", 502, 1

def mbap(tid, pdu):
    return struct.pack(">HHHB", tid, 0, len(pdu) + 1, UNIT) + pdu

def send(sock, tid, pdu, expect_len=None):
    sock.sendall(mbap(tid, pdu))
    hdr = sock.recv(7)
    if len(hdr) < 7:
        return None, "短响应 %r" % hdr
    t, p, ln, u = struct.unpack(">HHHB", hdr)
    body = b""
    while len(body) < ln - 1:
        chunk = sock.recv(ln - 1 - len(body))
        if not chunk: break
        body += chunk
    return (t, p, u, body), None

def read_holding(sock, addr, qty, tid=1):
    r, err = send(sock, tid, struct.pack(">BHH", 3, addr, qty))
    if err: return None, err
    t, p, u, body = r
    fc = body[0]
    if fc & 0x80:
        return None, "异常码 0x%02x" % body[1]
    n = body[1]
    vals = struct.unpack(">" + "H"*(n//2), body[2:2+n])
    return vals, None

def write_single(sock, addr, val, tid=2):
    r, err = send(sock, tid, struct.pack(">BHH", 6, addr, val))
    if err: return None, err
    t, p, u, body = r
    if body[0] & 0x80:
        return None, "异常码 0x%02x" % body[1]
    return struct.unpack(">HH", body[1:5]), None

print("="*70)
print("Modbus TCP 端到端测试  目标 127.0.0.1:502 站号 %d" % UNIT)
print("="*70)

# 1) TCP 连接
t0 = time.time()
try:
    s = socket.create_connection((HOST, PORT), timeout=3)
    print("[1] TCP 连接       : OK  耗时 %.1f ms" % ((time.time()-t0)*1000))
except Exception as e:
    print("[1] TCP 连接       : 失败 %r" % (e,))
    sys.exit(1)

s.settimeout(3)

# 2) 读保持寄存器 0..7
vals, err = read_holding(s, 0, 8)
print("[2] 读4区 0..7     : %s" % (("OK %s" % (vals,)) if vals else ("失败 " + err)))

# 3) 读保持寄存器 0..10（试 11 个，看通道够不够）
vals11, err11 = read_holding(s, 0, 11, tid=3)
print("[3] 读4区 0..10    : %s" % (("OK %s" % (vals11,)) if vals11 else ("失败 " + err11)))

# 4) 写单个寄存器 addr=0 -> 55，再读回
w, err = write_single(s, 0, 55, tid=4)
print("[4] 写4区[0]=55    : %s" % (("OK 回显 %s" % (w,)) if w else ("失败 " + err)))
time.sleep(0.15)
rb, err = read_holding(s, 0, 4, tid=5)
print("[5] 读回 0..3      : %s" % (("OK %s" % (rb,)) if rb else ("失败 " + err)))
if rb:
    print("     → 写进去的 55 读回来是 %d  %s" % (rb[0], "✔ 通" if rb[0]==55 else "✘ 不通/被覆盖"))

# 6) 再写一个不同的值确认不是巧合
write_single(s, 1, 77, tid=6)
time.sleep(0.15)
rb2, _ = read_holding(s, 0, 4, tid=7)
print("[6] 写[1]=77 再读  : %s" % (rb2,))

s.close()
print()
print("="*70)
print("结论：TCP+Modbus 协议层 %s" % ("已打通" if vals is not None else "未打通"))
print("="*70)
