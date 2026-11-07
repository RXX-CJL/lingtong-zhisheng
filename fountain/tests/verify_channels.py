# -*- coding: utf-8 -*-
"""verify_channels.py —— 验证 Modbus 通道是否真的绑到了 M1..M11

判据分三层，逐层递进（不能跳级）：
  L1 从站层：写 11 个不同值，能原样读回  → 证明 502 从站与寄存器映射 OK
  L2 变量层：写进去后，MCGS 里的 M1..M11 真的变了
  L3 画面层：ControlMode=2 时，Height1..11 跟着动

L2/L3 无法从这里直接读 MCGS 内部变量，所以用「可观测代理」：
  - 让脚本在 ControlMode=2 下把 M1..M11 直通到 TargetHeight1..11
  - Height 会平滑逼近 TargetHeight
  - 画面水柱高度是 Height 的可视化

用法：
  python tests/verify_channels.py            # 只做 L1
  python tests/verify_channels.py --visual   # L1 + 写台阶值，留给人眼/截图判断
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from modbus_client import ModbusWriter


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--unit", type=int, default=1)
    ap.add_argument("--visual", action="store_true", help="写台阶值并保持，供截图判断")
    ap.add_argument("--hold", type=float, default=6.0, help="台阶值保持秒数")
    ap.add_argument("--restore", action="store_true", help="结束时归零")
    args = ap.parse_args()

    w = ModbusWriter(args.host, args.port, args.unit)
    if not w.connect():
        print("连接失败:", w.last_error)
        return 2
    print("[L1] 已连接 %s:%d 站号 %d" % (args.host, args.port, args.unit))

    # ---- L1：读写一致性 ----
    before = w.read_registers(0, 11)
    print("写入前:", before)

    probe = [11, 22, 33, 44, 55, 66, 77, 88, 99, 110, 121]
    n = w.write_all(probe)
    print("写入 %d 个" % n)
    time.sleep(0.15)
    back = w.read_registers(0, 11)
    print("读回:", back)

    ok_l1 = (back == probe)
    print("  [%s] L1 从站读写一致 (11 个寄存器)" % ("PASS" if ok_l1 else "FAIL"))
    if not ok_l1:
        print("  !! 读回与写入不符，说明寄存器没映射到预期地址")

    # ---- L2 的可观测代理：写台阶，看画面 ----
    if args.visual:
        # 台阶：从 10 递增到 100，相邻喷头高度差明显，肉眼/截图易分辨
        steps = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110]
        print("\n[L2/L3] 写台阶值，保持 %.1fs —— 现在去看 MCGS 画面" % args.hold)
        print("  台阶:", steps)
        w.write_all(steps)
        for i in range(int(args.hold * 10)):
            time.sleep(0.1)
        print("  台阶值已保持完毕")

    # ---- 收尾 ----
    if args.restore:
        w.write_all([0] * 11)
        print("已归零:", w.read_registers(0, 11))
    else:
        w.write_all([0] * 11)
        print("收尾归零:", w.read_registers(0, 11))

    w.close()
    return 0 if ok_l1 else 1


if __name__ == "__main__":
    sys.exit(main())
