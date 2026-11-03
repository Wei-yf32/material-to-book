# -*- coding: utf-8 -*-
"""课件覆盖表审计（v3）。

不依赖"MLx pN"这类前缀：直接找表头含"课件页"的表格，
把每一行读成 (课件页, 本讲义位置, 处理方式)，按处理方式分类统计，
并列出所有"合并 / 略讲 / 不采纳"的行——这些是 v3 必须回头重看的地方
（导入、例子、回顾不能用"合并/不采纳"打发）。

用法：
    python _build/tools/cwaudit.py               # vol4 + vol5
    python _build/tools/cwaudit.py vol4          # 单卷
    python _build/tools/cwaudit.py vol5 06       # 单卷单章（文件名前缀）
    python _build/tools/cwaudit.py vol4 03 -v    # 连"展开/复述"行也打印
"""
import os
import re
import sys

BUILD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG = re.compile(r"<[^>]+>")
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
TABLE = re.compile(r"<table[^>]*>(.*?)</table>", re.S)
PAGEISH = re.compile(r"^(?:([A-Z]{2}\d+)\s*)?p?\s*(\d+)\s*(?:[–—\-~至]\s*p?\s*(\d+))?\s*页?$", re.I)

CATS = ("不采纳", "略讲", "合并", "重绘", "复述", "改写", "新增", "展开")


def clean(s):
    s = TAG.sub("", s)
    s = (s.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
         .replace("&amp;", "&").replace("&times;", "x"))
    return " ".join(s.split())


def find_cov_table(txt):
    """返回表头含"课件页"的那张表的所有行。"""
    for tm in TABLE.finditer(txt):
        body = tm.group(1)
        if "课件页" not in clean(body)[:200]:
            continue
        rows = []
        for rm in ROW.finditer(body):
            cells = [clean(c) for c in CELL.findall(rm.group(1))]
            if len(cells) < 3:
                continue
            rows.append(tuple(cells[:3]))
        if rows:
            return rows
    return []


def cat_of(how):
    for c in CATS:
        if c in how:
            return c
    if "无内容" in how or "空白" in how:
        return "不采纳"
    return "其他"


def audit(vol, filt=None, verbose=False):
    d = os.path.join(BUILD, "vol", vol)
    if not os.path.isdir(d):
        return
    files = sorted(f for f in os.listdir(d) if f.endswith(".html") and not f.startswith("_"))
    for fn in files:
        if filt and not fn.startswith(filt):
            continue
        txt = open(os.path.join(d, fn), encoding="utf-8").read()
        rows = find_cov_table(txt)
        head = f"\n=== {vol}/{fn} ==="
        if not rows:
            print(head + "  ✗ 没有找到表头含「课件页」的覆盖表")
            continue
        buckets = {}
        for p, loc, how in rows:
            buckets.setdefault(cat_of(how), []).append((p, loc, how))
        print(head)
        print("  覆盖表 %d 行 | " % len(rows) +
              "  ".join(f"{k} {len(v)}" for k, v in sorted(buckets.items(), key=lambda x: -len(x[1]))))
        # 页数统计
        pages = set()
        for p, _, _ in rows:
            m = PAGEISH.match(p)
            if m:
                a = int(m.group(2))
                b = int(m.group(3)) if m.group(3) else a
                pages.update(range(a, b + 1))
        if pages:
            print(f"  表中共涉及 {len(pages)} 个课件页码（{min(pages)}–{max(pages)}），"
                  f"连续区间是否完整：{'是' if len(pages) == max(pages) - min(pages) + 1 else '否'}")
        show = list(buckets.get("不采纳", [])) + list(buckets.get("略讲", [])) + list(buckets.get("合并", []))
        if verbose:
            show += [r for k in ("重绘", "复述", "改写", "新增", "展开", "其他") for r in buckets.get(k, [])]
        for p, loc, how in show:
            print(f"    [{cat_of(how)}] {p:10s} → {loc:22s} {how[:70]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "-v" in sys.argv
    vols = [args[0]] if args else ["vol4", "vol5"]
    filt = args[1] if len(args) > 1 else None
    for v in vols:
        audit(v, filt, verbose)
