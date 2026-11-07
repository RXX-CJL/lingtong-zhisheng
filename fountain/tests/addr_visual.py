# -*- coding: utf-8 -*-
"""addr_visual.py —— 用「阶梯水柱」一眼判断地址偏移

原理：把 11 个高度写成互不相同的阶梯（10,20,...,110）。
      映射正确时，画面上的 11 根水柱应该「从矮到高、依次排列」；
      映射错一位时，会看到整体错开一根（第一根高度不对 / 最后一根不动）。

跑两轮，你只需要回答「哪一轮顺序是对的」：
  A 轮：写地址 0..10
  B 轮：写地址 1..11

用法：
  python tests/addr_visual.py          # A、B 两轮都跑，每轮 8 秒
  python tests/addr_visual.py --hold 12
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from modbus_client import ModbusWriter

# 阶梯值：相邻差 10，肉眼能分辨
LADDER = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110]


def clear(w, span=16):
    w.write_all([0] * span, base=0)


def run_round(w, base, hold):
    clear(w)
    time.sleep(0.8)
    n = w.write_all(LADDER, base=base)
    back = w.read_registers(0, 16)
    print("\n" + "=" * 60)
    print("  写入地址 %d..%d  ← 阶梯 %s" % (base, base + 10, LADDER))
    print("  写入 %d 个，读回 0..15: %s" % (n, back))
    print("  保持 %.0f 秒 —— 现在看画面" % hold)
    print("=" * 60)
    for i in range(int(hold), 0, -1):
        sys.stdout.write("\r  剩余 %2d 秒 " % i)
        sys.stdout.flush()
        time.sleep(1.0)
    print("\r  本轮结束        ")
    clear(w)
    time.sleep(0.8)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hold", type=float, default=8.0)
    args = ap.parse_args()

    w = ModbusWriter()
    if not w.connect():
        print("连接失败:", w.last_error)
        print("→ 先确认 MCGS 已进入运行环境（502 端口在监听）")
        return 2

    print("开始前先清零")
    clear(w)
    time.sleep(1.0)

    print("\n" + "#" * 60)
    print("#  A 轮：地址 0..10")
    print("#  判据：11 根水柱是否「从矮到高、依次排列」？")
    print("#" * 60)
    run_round(w, 0, args.hold)

    print("\n" + "#" * 60)
    print("#  B 轮：地址 1..11")
    print("#  判据：同上")
    print("#" * 60)
    run_round(w, 1, args.hold)

    clear(w)
    w.close()
    print("\n" + "=" * 60)
    print("  两轮跑完。请回答：")
    print("    A 轮顺序正确 → Python 应 base=0（改 config）")
    print("    B 轮顺序正确 → Python 应 base=1（改 config）")
    print("    两轮都错     → 映射不是连续地址，需要逐点探测")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
