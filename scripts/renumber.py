#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把某一卷的章号重排为连续的 01..N，并同步改写正文里的编号引用。

用法：
    python _build/tools/renumber.py vol4            # 预览（不改文件）
    python _build/tools/renumber.py vol4 --apply    # 真正执行

规则：
  * 文件名 "NN_标题.html" 里的 NN 按排序后的序号重排为 01,02,...；
  * 正文里 "图 NN-k" "表 NN-k" "实验 NN-k" "式 (NN-k)" "第 NN 章" "NN.k 节"
    中的章号一并改写；
  * 形如 "第 5 卷第 16 章" 的跨卷引用会被保护（先把 "第 N 卷" 遮住再替换）。
"""
import os
import re
import sys

BUILD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BUILD)
import build as B  # noqa: E402

NAME_RE = re.compile(r"^(\d+)_(.+)\.html$")
VOL_RE = re.compile(r"第\s*(\d+)\s*卷")


def plan(vol):
    d = os.path.join(BUILD, "vol", vol)
    files = [f for f in os.listdir(d) if NAME_RE.match(f) and not f.startswith("_")]
    files.sort(key=lambda f: int(NAME_RE.match(f).group(1)))
    mapping = {}
    for i, f in enumerate(files, 1):
        old = int(NAME_RE.match(f).group(1))
        new = i
        mapping[old] = new
    return d, files, mapping


def rewrite(txt, mapping):
    # 1) 先遮住跨卷引用 "第 N 卷"，避免把 "第 5 卷第 16 章" 误改
    masked = {}

    def mask(m):
        key = f"\x00VOL{m.group(1)}\x00"
        masked[key] = m.group(0)
        return key

    txt = VOL_RE.sub(mask, txt)

    hits = []

    def rep(old, new):
        nonlocal txt
        if old == new:
            return
        pats = [
            (rf"(图|表|实验|式|公式)(\s*){old}-(\d+)", rf"\g<1>\g<2>{new}-\g<3>"),
            (rf"第(\s*){old}(\s*)章", rf"第\g<1>{new}\g<2>章"),
            (rf"(?<![\d.]){old}\.(\d+)(\s*)节", rf"{new}.\g<1>\g<2>节"),
        ]
        for p, r in pats:
            txt, n = re.subn(p, r, txt)
            if n:
                hits.append((old, new, p, n))

    for old, new in mapping.items():
        rep(old, new)

    for k, v in masked.items():
        txt = txt.replace(k, v)
    return txt, hits


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    vol = sys.argv[1]
    apply_ = "--apply" in sys.argv
    d, files, mapping = plan(vol)
    if not files:
        raise SystemExit(f"{vol} 下没有章节文件")
    old_nums = sorted(mapping)
    if old_nums == list(range(1, len(old_nums) + 1)):
        print(f"[{vol}] 章号已是连续的 01..{len(files):02d}，无需重排")
        return

    print(f"[{vol}] 映射：")
    for old in old_nums:
        print(f"   {old:02d} -> {mapping[old]:02d}")
    for f in files:
        txt = B.read(os.path.join(d, f))
        _, hits = rewrite(txt, mapping)
        if hits:
            print(f"   引用改写 {f}: " + ", ".join(f"{o}->{n}×{c}" for o, n, _, c in hits))

    if not apply_:
        print("\n（预览模式，未改动任何文件；加 --apply 执行）")
        return

    # 先写新内容再重命名，避免中途失败留下半成品
    for f in files:
        p = os.path.join(d, f)
        txt = B.read(p)
        new_txt, _ = rewrite(txt, mapping)
        if new_txt != txt:
            B.write(p, new_txt)
    for f in files:
        old = int(NAME_RE.match(f).group(1))
        new = mapping[old]
        if old != new:
            os.rename(os.path.join(d, f), os.path.join(d, f"{new:02d}_{NAME_RE.match(f).group(2)}.html"))
    print(f"[{vol}] 已重排，共 {len(files)} 章")


if __name__ == "__main__":
    main()
