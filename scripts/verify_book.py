# -*- coding: utf-8 -*-
"""合订 PDF 体检：越界文本块、近空白页、书签层级、卷起始页。"""
import sys
import pymupdf as fitz

P = sys.argv[1] if len(sys.argv) > 1 else r'驭风计划_计算机与人工智能系统讲义_全册.pdf'
doc = fitz.open(P)
print('页数', doc.page_count, '书签', len(doc.get_toc()))

w, h = doc[0].rect.width, doc[0].rect.height
overflow, blank = [], []
for i, pg in enumerate(doc):
    blocks = pg.get_text('blocks')
    for b in blocks:
        x0, y0, x1, y1 = b[:4]
        if x1 > w - 12 or y1 > h - 8 or x0 < 12:
            overflow.append((i + 1, round(x0), round(y0), round(x1), round(y1)))
    text = ''.join(b[4] for b in blocks).strip()
    if len(text) < 40:
        blank.append((i + 1, len(text)))

print('越界块', len(overflow), overflow[:6])
print('近空白页', len(blank), blank[:8])

toc = doc.get_toc()
top = [(lvl, t, p) for lvl, t, p in toc if lvl == 1]
print('一级书签', top)
print('卷起始页连续性', [p for _, _, p in top])
