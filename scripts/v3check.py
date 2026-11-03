#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
v3check.py —— 第 3 版（导入 / 例子 / 回顾 / 覆盖表）体检

用法：
    python _build\\tools\\v3check.py [vol4|vol5] [章号前缀] [-v]

检查每章：
    导入：是否有 h2 标题含"导入"或"开场"或在首个 h2 内出现"课件 p1/p2"的复述
    例子：h2 标题含"例子"的个数
    回顾：是否有 box key 里含"课件回顾"
    覆盖表：行数、"不采纳"出现次数
    规模：汉字数、图、实验框
退出码 1 表示有章不达标。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOLS = ["vol4", "vol5"]


def read(p):
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            with open(p, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def cjk(s):
    return len(re.findall(r"[\u4e00-\u9fff]", s))


def strip_tags(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    return re.sub(r"<[^>]+>", "", s)


def rows(txt):
    """取覆盖表的数据行（表头含 课件页 的表格）。"""
    out = []
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", txt, re.S):
        tb = m.group(1)
        if "课件页" not in tb:
            continue
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S):
            cells = [strip_tags(c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if len(cells) >= 3 and cells[0] and cells[0] not in ("课件页", "课件页码"):
                out.append(cells)
    return out


def check(vol, prefix=None):
    d = os.path.join(BASE, "vol", vol)
    files = sorted(f for f in os.listdir(d) if f.endswith(".html") and not f.startswith("_"))
    bad = 0
    tot = dict(ch=0, fig=0, lab=0, ex=0, rows=0)
    for f in files:
        if prefix and not f.startswith(prefix):
            continue
        p = os.path.join(d, f)
        txt = read(p)
        body = strip_tags(txt)
        h2 = [strip_tags(x) for x in re.findall(r"<h2[^>]*>(.*?)</h2>", txt, re.S)]
        h3 = [strip_tags(x) for x in re.findall(r"<h3[^>]*>(.*?)</h3>", txt, re.S)]
        imp_pat = re.compile(r"(导入|开场|为什么学|为什么需要|写在最前|从.{2,18}说起)")
        n_imp = sum(1 for h in h2 if imp_pat.search(h))
        n_ex = sum(1 for h in h2 + h3 if "例子" in h)
        n_rec = sum(1 for h in h2 + h3 if "回顾" in h)
        for m in re.finditer(r'class="box key"', txt):
            seg = txt[m.start():m.start() + 2500]
            if "回顾" in seg:
                n_rec += 1
        rs = rows(txt)
        na = sum(1 for r in rs if "不采纳" in "".join(r))
        nfig = len(re.findall(r"<figure", txt))
        nlab = len(re.findall(r'class="box lab"', txt))
        ch = cjk(body)
        flag = []
        if n_imp == 0:
            flag.append("缺导入")
        if n_ex == 0:
            flag.append("缺例子")
        if n_rec == 0:
            flag.append("缺回顾")
        if na:
            flag.append(f"不采纳{na}")
        notes = []
        if not rs:
            if "知识点清单覆盖表" in txt:
                notes.append("覆盖表=知识点清单")
            else:
                flag.append("无覆盖表")
        if flag:
            bad += 1
        tot["ch"] += ch
        tot["fig"] += nfig
        tot["lab"] += nlab
        tot["ex"] += n_ex
        tot["rows"] += len(rs)
        mark = "  " if not flag else "!!"
        print(f" {mark} {f:44s} 汉字{ch:6d} 导入{n_imp} 例子{n_ex} 回顾{n_rec} 图{nfig:2d} 实验{nlab:2d} 覆盖{len(rs):3d}行  {'、'.join(flag)}")
    print(f" 小计：汉字 {tot['ch']:,}，例子 {tot['ex']}，图 {tot['fig']}，实验 {tot['lab']}，覆盖表 {tot['rows']} 行")
    return bad


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    vol = args[0] if args else None
    prefix = args[1] if len(args) > 1 else None
    bad = 0
    for v in ([vol] if vol else VOLS):
        print(f"\n== {v} ==")
        bad += check(v, prefix)
    print("\n" + ("全部达标。" if bad == 0 else f"有 {bad} 章未达标。"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
