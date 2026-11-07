# -*- coding: utf-8 -*-
r"""扫合订 PDF 里是否残留未渲染的 LaTeX（\( \) \[ \] \\frac \\sum_ 等）。"""
import re
import pymupdf as fitz

PDF = r'驭风计划_计算机与人工智能系统讲义_全册.pdf'
doc = fitz.open(PDF)
pat = re.compile(r'(\\\(|\\\)|\\\[|\\\]|\\frac|\\sum_|\\text\{|\\begin\{)')
hits = []
for i in range(doc.page_count):
    t = doc[i].get_text()
    if pat.search(t):
        snippet = t[:200].replace('\n', ' ')
        hits.append((i + 1, snippet[:80]))
print('残留 LaTeX 页数', len(hits))
for h in hits[:12]:
    print(' ', h)
