"""验证 _as_float 助手对各种真实形态的处理"""

import os
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

from cloud_collaborator import _as_float  # noqa: E402

CASES = [
    ("浮点数", 85.6),
    ("整数", 25),
    ("纯数字字符串", "85.6"),
    ("带单位字符串", "85.6 km/h"),
    ("带单位+空格", " 0.0 px/s "),
    ("角度字符串", "180.0°"),
    ("科学计数", "1.2e2"),
    ("空字符串", ""),
    ("None", None),
    ("中文字符串", "未识别"),
    ("负数字符串", "-12.5 m/s"),
    ("列表（异常输入）", [1, 2]),
]

print("=" * 68)
print("_as_float 行为验证")
print("=" * 68)
allok = True
for name, val in CASES:
    try:
        out = _as_float(val)
        print(f"  {name:16s} {str(val)[:18]:20s} -> {out}")
    except Exception as e:
        allok = False
        print(f"  {name:16s} {str(val)[:18]:20s} -> 异常 {type(e).__name__}: {e}")

print()
print("=" * 68)
print("模拟修复前的崩溃（证明 bug 真实存在）")
print("=" * 68)
for val in ("85.6 km/h", "0.0", 85.6):
    try:
        s = f"{val:.1f}"
        print(f"  f'{{val:.1f}}' val={val!r:16s} -> OK '{s}'")
    except Exception as e:
        print(f"  f'{{val:.1f}}' val={val!r:16s} -> 崩溃: {type(e).__name__}: {e}")

print()
print("=" * 68)
print("模拟修复后的行为")
print("=" * 68)
for val in ("85.6 km/h", "0.0", 85.6, None):
    print(f"  f'{{_as_float(val):.1f}}' val={val!r:16s} -> OK '{_as_float(val):.1f}'")

print()
print("RESULT:", "PASS 助手健壮" if allok else "FAIL")
