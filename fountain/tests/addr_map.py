# -*- coding: utf-8 -*-
"""addr_map.py —— 自动探测 Modbus 地址与喷头序号的映射

问题：MCGS 通道地址可能从 0 或 1 开始，Python 写错一位就整体错开一根。
不靠猜，用探测：

  1. 把 0..15 全写 0
  2. 只写 地址A = 100，观察 M1 是否变成 100
  3. 判断依据不是画面，而是「读回值」——但读回只能证明从站层，
     不能证明变量绑定。所以真正可靠的判据是：

     **把 11 个高度写成互不相同的阶梯，读回后看哪一段与写入一致。**

  这仍不能证明变量层。所以本模块给出的是「候选映射」，
  最终判据由 verify_channels.py --visual 的人眼/截图确认。

真正能自证的办法：写一个极端值到单个地址，保持 5 秒，看画面。
本模块提供 probe() 做这件事，并把结果记录到 addr_map.json。

用法：
  python tests/addr_map.py probe     # 交互式探测（每次停 5 秒，你看画面）
  python tests/addr_map.py show      # 显示已记录的映射
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from modbus_client import ModbusWriter

MAP_FILE = os.path.join(ROOT, "addr_map.json")
HOLD = 5.0


def _clear(w, span: int = 16):
    w.write_all([0] * span, base=0)


def probe() -> int:
    """逐个地址点亮，让人观察哪根喷头动。"""
    w = ModbusWriter()
    if not w.connect():
        print("连接失败:", w.last_error)
        return 2

    print("清零 0..15")
    _clear(w)
    time.sleep(1.0)

    results = {}
    for addr in range(0, 12):
        vals = [0] * 16
        vals[addr] = 100
        w.write_all(vals, base=0)
        time.sleep(0.2)
        back = w.read_registers(0, 16)
        print("\n" + "=" * 50)
        print("  地址 %d = 100，其余 0（保持 %.0f 秒）" % (addr, HOLD))
        print("  读回:", back)
        print("  → 现在看画面：哪一根水柱升到最高？")
        ans = input("  第几根喷头动了？（填 1-11，没动填 0，跳过填 s）: ").strip()
        results[addr] = ans
        if ans and ans != "s":
            print("  记录：地址 %d → 喷头 %s" % (addr, ans))

    _clear(w)
    w.close()

    # 推断映射
    mapped = {int(k): int(v) for k, v in results.items() if v.isdigit() and v != "0"}
    offset = None
    if mapped:
        # 地址 a 对应喷头 p，则 offset = p - a
        offs = {p - a for a, p in mapped.items()}
        if len(offs) == 1:
            offset = offs.pop()
        print("\n" + "=" * 50)
        print("  探测结果:", mapped)
        print("  推断偏移: 喷头号 = 地址 + %s" % offset if offset is not None else "  偏移不唯一，需复查")
    else:
        print("\n没有有效记录，无法推断")

    out = {"probed": results, "offset": offset,
           "note": "offset=1 表示 MCGS 通道从地址1开始，Python 应 base=1"}
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("已写入", MAP_FILE)
    return 0


def show() -> int:
    if not os.path.exists(MAP_FILE):
        print("还没有探测记录:", MAP_FILE)
        return 1
    d = json.load(open(MAP_FILE, encoding="utf-8"))
    print(json.dumps(d, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "probe"
    sys.exit(probe() if cmd == "probe" else show())
