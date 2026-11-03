#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cwembed.py —— 把课件原页「影印」嵌入章节正文（第 4 版需求）

用户在 m03727 要求：不要只说"课件 pN 讲了什么"，要把那一页直接贴过来，
可以是图片也可以是文字，不要让他再回去翻 PPT。

做法：
  1. 从每章的「课件覆盖表」解析出 页号 -> 课件 PDF 的对应关系（表里写作 "ML5 p13"）；
  2. 再从正文里扫"课件 pN"、"(ML5 )p13/p14"、"p15–p20" 这类引用，得到要贴的页；
  3. 覆盖表里标「重绘 / 复述…图 / 表」但正文没点名的页，作为补充页（每章最多 6 张）；
  4. 每页渲染成 JPEG（150 dpi，整页不裁，保留课件标题与版式），存 _build/figures/cw/；
  5. 在第一次提到该页的段落之后插入 <figure class="cwpage">，幂等（已贴过就跳过）。

用法：
    python _build\\tools\\cwembed.py vol4          # 只报告
    python _build\\tools\\cwembed.py vol4 --apply  # 写入 HTML
"""
import os
import re
import sys

import pymupdf as fitz
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
FIG = os.path.join(BASE, "figures", "cw")
MLDIR = os.path.join(ROOT, "机器学习训练营", "机器学习课件最终版PDF合集  3")
DLDIR = os.path.join(ROOT, "深度学习讲义")

# 章 -> [(tag, 文件名)]，顺序即优先级（页码歧义时用第一个）
CHAPTERS = {
    "vol4": {
        "01": [("ML1", "ML1.Topic1.1-概述_最终版.pdf"), ("ML2", "ML2.Topic1.2-G通用系统设计_最终版.pdf")],
        "02": [("ML3", "ML3.Topic2.1-实验方法与原则(1)_最终版.pdf"), ("ML4", "ML4.Topic2.2-实验方法与原则(2)_最终版.pdf")],
        "03": [("ML5", "ML5.Topic3.1-决策树学习方法_最终版.pdf"), ("ML6", "ML6.Topic3.2-决策树学习进阶_最终版.pdf")],
        "04": [("ML7", "ML7.Topic4-Regression_最终版.pdf")],
        "05": [("ML8", "ML8.Topic5.1-贝叶斯(I)_最终版.pdf"), ("ML9", "ML9.Topic5.2-贝叶斯(II)_最终版.pdf")],
        "06": [("ML10", "ML10.Topic6.1-IBL(1)_最终版.pdf"), ("ML11", "ML11.Topic6.2-IBL(2)_最终版.pdf")],
        "07": [("ML12", "ML12.Topic7.1-SVM(1)_最终版.pdf"), ("ML13", "ML13.Topic7.2-SVM(2)_最终版.pdf")],
        "08": [("ML14", "ML14.Topic8.1-Unsupervised-I_最终版.pdf"), ("ML15", "ML15.Topic8.2-Unsupervised-II_最终版.pdf")],
        "09": [("ML16", "ML16.Topic9-Ensemble_最终版.pdf")],
        "10": [("ML17", "ML17.Toipc10.1-DLintro-I_最终版.pdf"), ("ML18", "ML18.Toipc10.2-DLinto-II_最终版.pdf")],
        "11": [("ML19", "ML19.Topic11-GWAP_最终版.pdf"), ("ML20", "ML20.Topic12-overview_已排版.pdf")],
        "12": [],
    },
    "vol5": {
        "01": [("DL1", "1 (1).pdf")],
        "02": [("DL2", "深度学习第二章节讲义修订 (1).pdf")],
        "03": [("DL3", "3 (1).pdf")],
        "04": [("DL4", "4 (1).pdf")],
        "05": [("DL5", "5 (1).pdf")],
        "06": [("DL6", "6.训练技巧_已排版 (1).pdf")],
        "07": [("DL7", "7.深度学习在计算机视觉中的应用-汉化_已排版 (1).pdf")],
        "08": [("DL7", "7.深度学习在计算机视觉中的应用-汉化_已排版 (1).pdf")],
        "09": [("DL8", "8.反馈神经网络-汉化_已排版 (1).pdf")],
        "10": [("DL9", "9.深度学习在自然语言中的应用-汉化_已排版0 (1).pdf")],
        "11": [("DL10", "10.深度生成式模型-汉化_已排版v2 (1).pdf")],
        "12": [],
    },
}
NAMES = {"vol4": "机器学习", "vol5": "深度学习"}
MAX_PER_CH = 16
MAX_FALLBACK = 6
MIN_SHOW = 10

REF = re.compile(r"课件\s*(ML\d+)?\s*[pP]\s*(\d{1,3})(?:\s*[/、,，\-–~至]\s*(?:[pP])?(\d{1,3}))?")


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def table_rows(txt):
    out = []
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", txt, re.S):
        tb = m.group(1)
        if "课件页" not in tb:
            continue
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S):
            cells = [strip_tags(c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if len(cells) >= 2:
                out.append(cells)
    return out


def page_map(rows, tags):
    """覆盖表第一列 -> {页号: tag}，按表内出现顺序，先到先得。"""
    pm = {}
    for c in rows:
        m = re.match(r"(ML\d+)\s*[pP]\s*(\d{1,3})", c[0])
        if not m:
            m2 = re.match(r"[pP]\s*(\d{1,3})", c[0])
            if m2:
                key = int(m2.group(1))
                pm.setdefault(key, tags[0])
            continue
        tag, page = m.group(1), int(m.group(2))
        if tag not in tags:
            continue
        pm.setdefault(page, tag)
    return pm


def prose_pages(txt):
    """正文里点名的页（含 a/b 与区间），返回 {页号: tag或None}。"""
    wanted = {}
    for m in REF.finditer(txt):
        tag = m.group(1)
        a = int(m.group(2))
        b = m.group(3)
        for p in range(a, (int(b) if b else a) + 1):
            if p <= 0 or p > 400:
                continue
            if p not in wanted or (tag and not wanted[p]):
                wanted[p] = tag
    return wanted


def visual_pages(rows):
    """覆盖表里处理方式提到 图/表/重绘 的页（正文没点名时补充）。"""
    out = []
    for c in rows:
        if len(c) < 3:
            continue
        m = re.match(r"(ML\d+)\s*[pP]\s*(\d{1,3})", c[0])
        if not m:
            continue
        how = c[2]
        if re.search(r"重绘|图|表|算例|例题|演示", how):
            out.append((int(m.group(2)), m.group(1)))
    return out


_cache = {}


def render(tag, pdf_name, page):
    key = (tag, page)
    if key in _cache:
        return _cache[key]
    pdf = os.path.join(MLDIR if tag.startswith("ML") else DLDIR, pdf_name)
    if not os.path.exists(pdf):
        _cache[key] = None
        return None
    out = os.path.join(FIG, f"{tag}_p{page:03d}.jpg")
    if not os.path.exists(out):
        os.makedirs(FIG, exist_ok=True)
        doc = fitz.open(pdf)
        if page > doc.page_count:
            doc.close()
            _cache[key] = None
            return None
        pix = doc[page - 1].get_pixmap(dpi=150)
        pix.save(out.replace(".jpg", ".png"))
        with Image.open(out.replace(".jpg", ".png")) as im:
            im.convert("RGB").save(out, "JPEG", quality=84, optimize=True)
        os.remove(out.replace(".jpg", ".png"))
        doc.close()
    _cache[key] = out
    return out


def pdf_info(tag):
    """tag -> (文件名, 页数)"""
    if tag in _info:
        return _info[tag]
    for vol in CHAPTERS:
        for plan in CHAPTERS[vol].values():
            for t, f in plan:
                if t == tag:
                    p = os.path.join(MLDIR if t.startswith("ML") else DLDIR, f)
                    n = fitz.open(p).page_count if os.path.exists(p) else 0
                    _info[tag] = (f, n)
                    return _info[tag]
    _info[tag] = ("", 0)
    return _info[tag]


_info = {}


def fig_html(tag, page, vol):
    f, n = pdf_info(tag)
    return (
        '\n<figure class="cwpage">\n'
        f'<img src="../../figures/cw/{tag}_p{page:03d}.jpg" class="w88" alt="课件 {tag} 第 {page} 页">\n'
        f'<figcaption>课件原页影印 · {tag} 第 {page} 页 —— 清华大学“驭风计划”'
        f'《{NAMES[vol]}》课件《{os.path.splitext(f)[0]}》，原 PDF 共 {n} 页</figcaption>\n'
        "</figure>\n"
    )


def recaption(txt, vol):
    """把旧版「…，12 / 全讲）」图注改成带 PDF 名与总页数的写法。"""
    def rep(m):
        tag, page = m.group(1), int(m.group(2))
        f, n = pdf_info(tag)
        return (f"课件原页影印 · {tag} 第 {page} 页 —— 清华大学“驭风计划”"
                f"《{NAMES[vol]}》课件《{os.path.splitext(f)[0]}》，原 PDF 共 {n} 页")
    return re.sub(r"课件原页影印 · (ML\d+|DL\d+) 第 (\d+) 页（清华大学“驭风计划”《[^》]+》课件，\d+ / 全讲）", rep, txt)


def do_chapter(vol, fname, apply=False):
    nn = fname[:2]
    plan = CHAPTERS[vol].get(nn, [])
    if not plan:
        return 0, 0
    tags = [t for t, _ in plan]
    by_tag = dict(plan)
    path = os.path.join(BASE, "vol", vol, fname)
    txt = read(path)
    txt = recaption(txt, vol)
    existing = set((a, int(b)) for a, b in re.findall(r"figures/cw/(ML\d+|DL\d+)_p(\d+)\.jpg", txt))
    rows = table_rows(txt)
    pm = page_map(rows, tags)

    want = prose_pages(txt)                      # {页: tag|None}
    order = []                                   # 要贴的 (tag, page)，按正文出现顺序
    seen = set(existing)
    for m in REF.finditer(txt):
        tag = m.group(1) or pm.get(int(m.group(2))) or tags[0]
        a = int(m.group(2))
        b = m.group(3)
        for p in range(a, (int(b) if b else a) + 1):
            t = tag
            if m.group(1) is None and p in pm:
                t = pm[p]
            if (t, p) in seen:
                continue
            seen.add((t, p))
            order.append((t, p))

    # 补充：覆盖表里标了图/表/重绘、但正文没点名的页
    extra = []
    have = {p for _, p in order}
    for p, tag in visual_pages(rows):
        if p in have or (tag, p) in seen:
            continue
        extra.append((tag, p))
        seen.add((tag, p))
        if len(extra) >= MAX_FALLBACK:
            break

    # 仍不足 MIN_SHOW 页时，按页均分补几张「关键页」（跳过封面），保证每章都有影印可看
    if len(order) + len(extra) < MIN_SHOW:
        for tag, fname_pdf in plan:
            pdf = os.path.join(MLDIR if tag.startswith("ML") else DLDIR, fname_pdf)
            if not os.path.exists(pdf):
                continue
            cnt = fitz.open(pdf).page_count
            step = max(2, cnt // 6)
            for p in range(3, cnt + 1, step):
                if (tag, p) in seen:
                    continue
                extra.append((tag, p))
                seen.add((tag, p))
                if len(order) + len(extra) >= MIN_SHOW:
                    break
            if len(order) + len(extra) >= MIN_SHOW:
                break

    order = order[:MAX_PER_CH]
    n_img = 0
    for tag, page in order + extra:
        if render(tag, by_tag.get(tag, ""), page):
            n_img += 1

    if not apply:
        return len(order) + len(extra), n_img

    # 逐段插入：在首次提到该页的段落之后贴图
    parts = re.split(r"(</p>)", txt)
    done = set()
    out = []
    pending = list(order)
    for seg in parts:
        out.append(seg)
        if seg != "</p>":
            continue
        para = "".join(out[-6:]) if len(out) >= 6 else "".join(out)
        plain = strip_tags(para)
        hits = []
        for tag, page in pending:
            pats = [rf"[pP]\s*{page}(?!\d)", rf"{tag}\s*[pP]\s*{page}(?!\d)"]
            if any(re.search(x, plain) for x in pats):
                hits.append((tag, page))
        for tag, page in hits[:2]:
            out.append(fig_html(tag, page, vol))
            done.add((tag, page))
            pending.remove((tag, page))
    txt2 = "".join(out)
    # 没找到落点的（补充页等）统一放在「课件原页影印」小节，插在覆盖表之前
    left = [(t, p) for t, p in order + extra if (t, p) not in done]
    if left:
        block = ['\n<h2>课件原页影印</h2>\n<p>\n本页汇集本章正文提到、但没能贴着正文排的原页，'
                 '顺序与课件一致，方便你对照。</p>\n']
        for tag, page in left[:MAX_PER_CH]:
            if render(tag, by_tag.get(tag, ""), page):
                block.append(fig_html(tag, page, vol))
        block = "".join(block)
        i = txt2.find("<h2>本单元课件覆盖表")
        if i < 0:
            i = txt2.find("<h2>知识点清单覆盖表")
        if i > 0:
            txt2 = txt2[:i] + block + txt2[i:]
        else:
            txt2 += block
    write(path, txt2)
    return len(order + extra), n_img


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    vols = args or ["vol4", "vol5"]
    total = 0
    for vol in vols:
        d = os.path.join(BASE, "vol", vol)
        for f in sorted(x for x in os.listdir(d) if x.endswith(".html") and not x.startswith("_")):
            n, k = do_chapter(vol, f, apply)
            if n:
                print(f"{'[写入]' if apply else '[计划]'} {vol}/{f[:26]:28s} 页 {n:2d}  图 {k:2d}")
                total += n
    print(f"\n合计 {total} 张课件原页")


if __name__ == "__main__":
    main()
