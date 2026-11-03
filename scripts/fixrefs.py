# -*- coding: utf-8 -*-
"""
fixrefs.py —— 成书前修正 vol0 里的“跨卷章节引用”。

背景：各卷在写作阶段用的是带历史偏移的章号（例如第 4 卷从 10 开始），
最后 renumber.py 会把每卷重排成 01..N 连续编号，于是 vol0 表 1-3 与
“三条阅读路线”里写的“第 4 卷第 12 章”就会指错地方。

做法：不靠人肉数，直接按“实验名 → 关键词”去目标卷的文件名里找章节，
读它当前的 NN 前缀，再把表格单元格改写成真实章号。幂等，可重复运行。

用法：
    python _build/tools/fixrefs.py            # 只看差异
    python _build/tools/fixrefs.py --apply    # 写回文件
"""
import os
import re
import sys

BUILD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOL = os.path.join(BUILD, "vol")
TARGET = os.path.join(VOL, "vol0", "01_如何使用本讲义.html")

# (表 1-3 第一列出现的字样, 目标卷, 该章文件名里的关键词)
MAP = [
    ("决策树 · LOL 胜负", "vol4", "决策树"),
    ("回归 · 大学排名", "vol4", "回归"),
    ("贝叶斯 · 垃圾邮件", "vol4", "贝叶斯"),
    ("聚类 · AAAI 论文", "vol4", "无监督"),
    ("集成 · Amazon 评论", "vol4", "集成"),
    ("毕业设计 · 手游流失", "vol4", "深度学习基础"),
    ("DL hw1a · 逻辑回归", "vol5", "回归与分类"),
    ("DL hw1b · Softmax", "vol5", "回归与分类"),
    ("DL hw2 · 手写 MLP", "vol5", "多层感知机"),
    ("DL hw3 · CNN", "vol5", "卷积"),
    ("DL hw4 · U-Net 分割", "vol5", "计算机视觉"),
    ("DL hw5 · 目标检测", "vol5", "目标检测"),
    ("DL hw6 · 图像描述", "vol5", "循环神经网络"),
    ("DL hw7 · 超分辨率", "vol5", "生成模型"),
]


def chapters(vol):
    """返回 [(章号 int, 文件名)]，按文件名排序。"""
    d = os.path.join(VOL, vol)
    if not os.path.isdir(d):
        return []
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".html") or fn.startswith("_"):
            continue
        m = re.match(r"(\d+)_", fn)
        if m:
            out.append((int(m.group(1)), fn))
    return out


def lookup(vol, kw):
    for num, fn in chapters(vol):
        if kw in fn:
            return num, fn
    return None, None


def show_chars(n):
    return "一二三四五六七八九十"[n - 1]


def vol_cn(vol):
    return show_chars(int(vol.replace("vol", "")))


def main():
    apply = "--apply" in sys.argv
    with open(TARGET, encoding="utf-8") as f:
        txt = f.read()

    rows = re.findall(r"<tr>(.*?)</tr>", txt, re.S)
    changes = []
    for name, vol, kw in MAP:
        num, fn = lookup(vol, kw)
        if num is None:
            print(f"  [缺章] {name}: 在 {vol} 里找不到含“{kw}”的文件")
            continue
        want = f"第 {vol_cn(vol)} 卷第 {num} 章"
        # 找这一行
        for row in rows:
            if name in row:
                cells = re.findall(r"<td>(.*?)</td>", row, re.S)
                if len(cells) >= 3 and cells[2] != want:
                    changes.append((name, cells[2], want))
                    old_row = row
                    new_cells = list(cells)
                    new_cells[2] = want
                    new_row = "<td>" + "</td><td>".join(new_cells[:3]) + "</td>" + \
                              ("<td></td>" * max(0, len(cells) - 3))
                    txt = txt.replace(f"<tr>{old_row}</tr>", f"<tr>{new_row}</tr>", 1)
                break

    if not changes:
        print("  所有跨卷引用都是最新的。")
        return
    for name, old, new in changes:
        print(f"  {name}: {old}  ->  {new}")
    if apply:
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"  已写回 {os.path.relpath(TARGET, BUILD)}")
    else:
        print("  （预览模式；加 --apply 写回）")


if __name__ == "__main__":
    main()
