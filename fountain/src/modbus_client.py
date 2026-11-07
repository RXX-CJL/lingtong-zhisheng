# -*- coding: utf-8 -*-
"""modbus_client.py —— 极简 Modbus TCP 主站（只写 FC06，不装第三方包）

为什么手写：pymodbus 没装，而这里只需要"写单个保持寄存器"。
手写 40 行比装包+适配版本稳。
"""
from __future__ import annotations

import socket
import struct
import time


class ModbusError(Exception):
    pass


class ModbusWriter:
    def __init__(self, host: str = "127.0.0.1", port: int = 502,
                 unit: int = 1, timeout: float = 0.25):
        self.host = host
        self.port = port
        self.unit = unit
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._tid = 0
        self.last_error: str | None = None

    # ---------- 连接 ----------
    def connect(self) -> bool:
        self.close()
        try:
            s = socket.create_connection((self.host, self.port), timeout=self.timeout)
            s.settimeout(self.timeout)
            self._sock = s
            self.last_error = None
            return True
        except Exception as e:
            self._sock = None
            self.last_error = repr(e)
            return False

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    @property
    def connected(self) -> bool:
        return self._sock is not None

    # ---------- 底层收发 ----------
    def _request(self, pdu: bytes) -> bytes:
        if not self._sock:
            raise ModbusError("未连接")
        self._tid = (self._tid + 1) & 0xFFFF
        pkt = struct.pack(">HHHB", self._tid, 0, len(pdu) + 1, self.unit) + pdu
        self._sock.sendall(pkt)
        hdr = self._sock.recv(7)
        if len(hdr) < 7:
            raise ModbusError("响应头过短")
        _t, _p, ln, _u = struct.unpack(">HHHB", hdr)
        body = b""
        need = max(0, ln - 1)
        while len(body) < need:
            chunk = self._sock.recv(need - len(body))
            if not chunk:
                break
            body += chunk
        if not body:
            raise ModbusError("响应体为空")
        if body[0] & 0x80:
            raise ModbusError("异常码 0x%02x" % body[1])
        return body

    # ---------- 功能码 ----------
    def write_register(self, addr: int, value: int) -> None:
        """FC06 写单个保持寄存器"""
        v = int(max(0, min(0xFFFF, value)))
        self._request(struct.pack(">BHH", 6, addr, v))

    def write_registers(self, addr: int, values: list) -> None:
        """FC16 (0x10) 一次写多个连续保持寄存器。

        ★ 2026-11-05 关键优化：实测发现 11 次 FC06 要 **169.5 ms**
        （每次 15.4ms，因为每个请求都要等 MCGS 的采集周期）。
        改成一次 FC16 后应该只要 1 次等待。

        报文格式：
          请求: 功能码(1) + 起始地址(2) + 数量(2) + 字节数(1) + 数据(2N)
          响应: 功能码(1) + 起始地址(2) + 数量(2)
        """
        if not values:
            return
        n = len(values)
        if n > 123:
            raise ModbusError("FC16 一次最多写 123 个寄存器")
        vals = [int(max(0, min(0xFFFF, v))) for v in values]
        data = b"".join(struct.pack(">H", v) for v in vals)
        pdu = struct.pack(">BHHB", 16, addr, n, len(data)) + data
        self._request(pdu)

    def read_registers(self, addr: int, qty: int) -> list[int]:
        """FC03 读保持寄存器"""
        body = self._request(struct.pack(">BHH", 3, addr, qty))
        n = body[1]
        return list(struct.unpack(">" + "H" * (n // 2), body[2:2 + n]))

    # ---------- 批量写 ----------
    def write_all(self, values: list[int], base: int = 0) -> int:
        """一次连接写多个寄存器，返回成功写入个数。

        ★ 2026-11-05 改用 FC16（一次写多个），不再逐条 FC06。
        实测对比（MCGS 采集周期 20ms）：
          FC06 × 11  = 169.5 ms   ← 每条都要等一个采集周期
          FC16 × 1   = 见下方实测  ← 只等一次
        这直接决定了水柱刷新率的上限。
        """
        if not self.connected and not self.connect():
            return 0
        try:
            vals = list(values[:11])
            self.write_registers(base, vals)
            return len(vals)
        except Exception as e:
            self.last_error = repr(e)
            # FC16 失败时退回逐条 FC06（兼容某些老固件）
            try:
                ok = 0
                for i, v in enumerate(list(values[:11])):
                    self.write_register(base + i, v)
                    ok += 1
                return ok
            except Exception as e2:
                self.last_error = repr(e2)
                self.close()
                return 0
