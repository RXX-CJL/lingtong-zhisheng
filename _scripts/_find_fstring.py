"""用 AST 找出代码里所有 f-string 中的浮点格式占位符，并列出变量名/所在函数

目的：定位 "Unknown format code 'f' for object of type 'str'" 的确切抛错点。
"""

import ast
import io
import os

ROOT = r"E:\output\1\api"
SKIP = ("test_", "diag_", "__pycache__")
OUT = r"E:\output\_fstring_report.md"

rows = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "node_modules")]
    for fn in filenames:
        if not fn.endswith(".py") or fn.startswith(SKIP):
            continue
        p = os.path.join(dirpath, fn)
        try:
            src = io.open(p, encoding="utf-8", errors="replace").read()
            tree = ast.parse(src)
        except Exception:
            continue

        # 建立 行号 -> 外层函数名 的映射
        func_of_line = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for ln in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                    func_of_line.setdefault(ln, node.name)

        for node in ast.walk(tree):
            if not isinstance(node, ast.JoinedStr):
                continue
            for part in node.values:
                if not isinstance(part, ast.FormattedValue):
                    continue
                fmt = None
                if isinstance(part.format_spec, ast.JoinedStr):
                    fmt = "".join(v.value for v in part.format_spec.values
                                  if isinstance(v, ast.Constant) and isinstance(v.value, str))
                if not fmt or "f" not in fmt:
                    continue

                # 还原表达式文本
                try:
                    expr = ast.unparse(part.value)
                except Exception:
                    expr = "<?>"
                rows.append({
                    "file": os.path.relpath(p, ROOT),
                    "line": part.value.lineno,
                    "func": func_of_line.get(part.value.lineno, "(module)"),
                    "expr": expr,
                    "fmt": fmt,
                })

# 按"表达式里出现 confidence/speed/score/rate/fps 等数值关键词"优先排序
NUMISH = ("confidence", "speed", "score", "rate", "fps", "conf", "prob", "value", "ratio")

buf = [f"# f-string 浮点格式化清单（共 {len(rows)} 处）\n"]
buf.append("\n重点：对**可能是字符串**的值做 f 格式化会抛 "
           "`Unknown format code 'f' for object of type 'str'`。\n")

buf.append("\n## 1) 数值语义最强（最可疑）\n")
prim = [r for r in rows if any(k in r["expr"].lower() for k in NUMISH)]
for r in sorted(prim, key=lambda x: (x["file"], x["line"])):
    buf.append(f"- `{r['file']}:{r['line']}` 函数 `{r['func']}`")
    buf.append(f"  - 表达式: `{r['expr']}`   格式: `{r['fmt']}`")

buf.append(f"\n## 2) 其余 {len(rows) - len(prim)} 处\n")
for r in sorted([x for x in rows if x not in prim], key=lambda x: (x["file"], x["line"])):
    buf.append(f"- `{r['file']}:{r['line']}` `{r['expr']}` :{r['fmt']}  （{r['func']}）")

io.open(OUT, "w", encoding="utf-8").write("\n".join(buf) + "\n")
print("OK ->", OUT, len(rows), "处")
