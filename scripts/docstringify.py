#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""docstringify.py —— 把脚本里「# 作用 / # 参数 / # 返回 / # 关键行」注释块
改写成 PyCharm 那种（光标悬停即可看到的）多行 docstring。

用法：
    python _build/tools/docstringify.py <文件或目录> [...] [--apply]

规则：
  * 只看 def/class 之后、紧跟的连续 `#` 注释块；
  * 识别 `作用:` `参数:` `返回:` `关键行:` `边界:` `副作用:` 这些字段；
  * 生成 Google/Sphinx 混排风格的中文 docstring：首行作用，空行，参数/返回/关键实现分段；
  * 其余 # 注释原样保留（函数体内部的注释不动）；
  * 已有 docstring 的函数跳过（幂等）。
"""
import argparse
import io
import os
import re
import sys

FIELD = re.compile(r"^#\s*(作用|参数|返回|关键行|关键实现|边界|边界情况|副作用|注意)\s*[：:]\s*(.*)$")
ANY = re.compile(r"^#\s?(.*)$")


def collect_block(lines, i):
    """从 i 开始收集连续注释行，返回 (注释行列表, 结束下标)。"""
    j = i
    block = []
    while j < len(lines):
        s = lines[j].rstrip("\n")
        if s.strip() == "":
            # 允许注释块中间有一个空行
            if j + 1 < len(lines) and lines[j + 1].lstrip().startswith("#"):
                block.append("")
                j += 1
                continue
            break
        if not s.lstrip().startswith("#"):
            break
        block.append(s)
        j += 1
    return block, j


def build_doc(fields, indent):
    order = ["作用", "参数", "返回", "关键实现", "关键行", "边界", "边界情况", "副作用", "注意"]
    def get(k):
        for kk in (k,) if isinstance(k, str) else k:
            if kk in fields and fields[kk].strip():
                return fields[kk].strip()
        return ""

    # 原注释常把两件事写在一行（“…；返回：…”），先按分号拆开再排版
    for sep, newk in (("；返回：", "返回"), ("；关键行：", "关键行"),
                      ("；关键实现：", "关键实现"), ("；注意：", "注意"),
                      ("；参数：", "参数")):
        for k in list(fields.keys()):
            v = fields.get(k, "")
            if sep in v:
                head, tail = v.split(sep, 1)
                fields[k] = head.strip()
                fields.setdefault(newk, tail.strip())

    summary = get("作用")
    body = []
    params = get("参数")
    rets = get("返回")
    key = get(("关键实现", "关键行"))
    edge = get(("边界", "边界情况"))
    side = get("副作用")
    note = get("注意")

    if params:
        body += ["", "参数", "----", params]
    if rets:
        body += ["", "返回", "----", rets]
    if key:
        body += ["", "关键实现", "--------", key]
    if edge:
        body += ["", "边界情况", "--------", edge]
    if side:
        body += ["", "副作用", "------", side]
    if note:
        body += ["", "注意", "----", note]

    pad = " " * indent
    out = [pad + '"""' + summary]
    for b in body:
        out.append(pad + b if b else "")
    out.append(pad + '"""')
    return out


def process(path):
    src = io.open(path, encoding="utf-8").read()
    lines = src.split("\n")
    out = []
    i = 0
    changed = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = re.match(r"^(\s*)(def|class)\s+\w+", line)
        if not m:
            i += 1
            continue
        # 函数签名可能跨行：等到以冒号结尾的那一行
        sig_end = i
        while sig_end < len(lines) and not lines[sig_end].rstrip().endswith(":"):
            sig_end += 1
            if sig_end - i > 12:
                break
        if sig_end >= len(lines) or sig_end != i:
            # 多行签名：把签名行整体输出，再继续
            for k in range(i + 1, sig_end + 1):
                out.append(lines[k])
            i = sig_end + 1
        else:
            i += 1
        # 下一行若已是 docstring，跳过
        if i < len(lines) and lines[i].lstrip().startswith('"""'):
            continue
        block, j = collect_block(lines, i)
        if not block:
            continue
        stripped = [b.strip() for b in block if b.strip()]
        if not stripped:
            continue
        first = stripped[0]
        mm = FIELD.match(first)
        if not mm:
            continue  # 不是“作用/参数/返回”式的注释块，不动
        indent = len(lines[i]) - len(lines[i].lstrip())
        fields = {}
        for s in stripped:
            fm = FIELD.match(s)
            if fm:
                fields[fm.group(1)] = fm.group(2).strip()
            else:
                # 续行，接到上一个字段
                if fields:
                    last = list(fields.keys())[-1]
                    fields[last] = (fields[last] + " " + ANY.match(s).group(1)).strip()
        out.extend(build_doc(fields, indent))
        changed += 1
        i = j
    if changed:
        io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    targets = []
    for p in a.paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in files:
                    if f.endswith(".py"):
                        targets.append(os.path.join(root, f))
        elif p.endswith(".py"):
            targets.append(p)

    total = 0
    for t in sorted(targets):
        if not a.apply:
            # 干跑：只统计会遇到多少块
            src = io.open(t, encoding="utf-8").read().split("\n")
            n = 0
            for k in range(len(src) - 1):
                if re.match(r"^\s*def\s+\w+.*:\s*$", src[k]):
                    nxt = src[k + 1].strip()
                    if FIELD.match(nxt):
                        n += 1
            if n:
                print(f"{t}: {n} 块")
                total += n
            continue
        n = process(t)
        if n:
            print(f"{t}: 改写 {n} 块")
            total += n
    print(("共 " + str(total) + " 块") if total else "没有需要改写的注释块")


if __name__ == "__main__":
    main()
