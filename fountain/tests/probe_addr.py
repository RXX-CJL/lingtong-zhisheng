# -*- coding: utf-8 -*-
"""probe_addr.py —— 确认 Modbus 地址与喷头的对应关系

方法：每次只把一个地址写成 100，其余全 0，看哪一根水柱升起。
如果写地址 N 时第 K 根动，就说明 地址 N -> 喷头 K。

用法：
  python tests/probe_addr.py 0      # 只让地址0=100，其余0
  python tests/probe_addr.py 1      # 只让地址1=100，其余0
  python tests/probe_addr.py 0 1    # 同时测两个地址（分别停 6 秒）
"""
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from modbus_client import ModbusWriter

HOLD = 6.0
PEAK = 100


def clear(w):
    w.write_all([0] * 16, base=0)


def main() -> int:
    addrs = [int(a) for a in sys.argv[1:]] or [0, 1]
    w = ModbusWriter()
    if not w.connect():
        print("连接失败:", w.last_error)
        return 2

    print("先把 0..15 全清零")
    clear(w)
    time.sleep(1.0)

    for a in addrs:
        vals = [0] * 16
        vals[a] = PEAK
        n = w.write_all(vals, base=0)
        back = w.read_registers(0, 16)
        print("\n=== 地址 %d = %d（其余 0），保持 %.0fs ===" % (a, PEAK, HOLD))
        print("  写入 %d 个，读回:" % n, back)
        print("  现在看画面：哪一根水柱升起来了？")
        time.sleep(HOLD)

    print("\n收尾归零")
    clear(w)
    w.close()
    print("完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
