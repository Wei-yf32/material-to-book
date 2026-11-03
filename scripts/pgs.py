# -*- coding: utf-8 -*-
"""把课件 PDF 的指定页渲染成 PNG，供阅读/复刻公式与图。

用法：
    python _build/tools/pgs.py <pdf路径> <页码范围> [--dpi 110]
例：
    python _build/tools/pgs.py "机器学习训练营\\机器学习课件最终版PDF合集  3\\ML5.Topic3.1-决策树学习方法_最终版.pdf" 1-20
    python _build/tools/pgs.py <pdf> all

输出：_build/cw/<pdf名>/p0001.png ...，并打印每个文件路径与页数。
"""
import os
import re
import sys

import pymupdf

BUILD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BUILD, "cw")


def parse_range(spec, n):
    if spec == "all":
        return list(range(1, n + 1))
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return [p for p in out if 1 <= p <= n]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    pdf = sys.argv[1]
    spec = sys.argv[2]
    dpi = 110
    if "--dpi" in sys.argv:
        dpi = int(sys.argv[sys.argv.index("--dpi") + 1])
    doc = pymupdf.open(pdf)
    n = doc.page_count
    base = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", os.path.splitext(os.path.basename(pdf))[0])[:60]
    d = os.path.join(OUT, base)
    os.makedirs(d, exist_ok=True)
    pages = parse_range(spec, n)
    for p in pages:
        fp = os.path.join(d, "p%04d.png" % p)
        if not os.path.exists(fp):
            doc[p - 1].get_pixmap(dpi=dpi).save(fp)
        print(fp)
    print("总页数 %d，输出 %d 页 -> %s" % (n, len(pages), d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
