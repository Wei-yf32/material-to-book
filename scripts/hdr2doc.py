"""把脚本顶部的「# 作用：… / # 用法：… / # 返回：…」注释块改成模块级 docstring。

规则：
- 只处理文件开头（允许前面有 shebang 与 coding 行）。
- 只在连续注释块里出现「作用：」时改写。
- 保留注释里每行的正文，去掉行首的「# 」与「作用：/用法：/返回：/关键行：」前缀，
  第一行作为摘要，其后按原顺序成段。
"""

import io
import sys
import glob
import ast


def convert(path):
    src = io.open(path, encoding="utf-8").read()
    lines = src.splitlines()
    i = 0
    head = []
    if i < len(lines) and lines[i].startswith("#!"):
        head.append(lines[i])
        i += 1
    if i < len(lines) and "coding" in lines[i] and lines[i].lstrip().startswith("#"):
        head.append(lines[i])
        i += 1
    j = i
    block = []
    while j < len(lines) and lines[j].lstrip().startswith("#"):
        block.append(lines[j])
        j += 1
    if not block or "作用" not in "".join(block):
        return False
    body = []
    for ln in block:
        s = ln.lstrip()[1:].strip()
        for pref in ("作用：", "作用:", "用法：", "用法:", "返回：", "返回:",
                     "关键行：", "关键行:", "数据：", "数据:", "输出：", "输出:"):
            if s.startswith(pref):
                s = s[len(pref):].strip()
                break
        body.append(s)
    if not body:
        return False
    out = list(head)
    out.append('"""' + body[0])
    rest = body[1:]
    if rest:
        out.append("")
        out.extend(rest)
    out.append('"""')
    out.extend(lines[j:])
    new = "\n".join(out) + ("\n" if src.endswith("\n") else "")
    try:
        ast.parse(new)
    except SyntaxError:
        return False
    io.open(path, "w", encoding="utf-8", newline="\n").write(new)
    return True


def main():
    pats = sys.argv[1:] or ["_build/src/vol4/*.py", "_build/src/vol5/*.py"]
    n = 0
    for pat in pats:
        for f in sorted(glob.glob(pat)):
            try:
                if convert(f):
                    n += 1
                    print("converted", f)
            except Exception as e:
                print("skip", f, e)
    print("total", n)


if __name__ == "__main__":
    main()
