# -*- coding: utf-8 -*-
"""全卷体检：不生成 PDF，只检查片段与依赖是否齐全，并给出篇幅统计。

用法：
    python _build/tools/checkbook.py            # 检查全部
    python _build/tools/checkbook.py vol4       # 只检查某一卷

检查项：
    1. 每个片段是否有且仅有一个 <h1>
    2. INCLUDE-CODE / INCLUDE-OUTPUT 指向的文件是否存在
    3. <img src> 指向的图是否真实存在
    4. 是否误用了被禁用的 HTML 标签、是否残留 Markdown 代码围栏
    5. 每章汉字数、图/表/代码块/输出块/实验框数量
    6. 篇幅告警：汉字数 < 1200 视为过短
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = os.path.join(BASE, "_build")
sys.path.insert(0, BUILD)

import build as B  # noqa: E402  复用 VOLUMES 与 read()

VOLS = list(B.VOLUMES.keys())
CJK = re.compile(r"[\u4e00-\u9fff]")
INC_CODE = re.compile(r"<!--\s*INCLUDE-CODE\s+path=([^\s>]+?)(?:\s+(?:lang|ln)=|\s*-->)")
INC_OUT = re.compile(r"<!--\s*INCLUDE-OUTPUT\s+path=([^\s>]+?)(?:\s*-->)")
IMG = re.compile(r'<img[^>]+src="([^"]+)"')
BAD_TAG = re.compile(r"</?(?:script|iframe|div class=\"pagebreak|h4|h5|section)\b")


def check_fragment(path):
    """返回 (统计字典, 问题列表)。"""
    txt = B.read(path)
    probs = []
    n_h1 = len(re.findall(r"<h1[\s>]", txt))
    if n_h1 != 1:
        probs.append(f"<h1> 数量为 {n_h1}（应为 1）")

    for p in INC_CODE.findall(txt):
        p = p.strip().strip('"')
        if not os.path.exists(os.path.join(BUILD, p)):
            probs.append(f"缺代码文件 {p}")
    for p in INC_OUT.findall(txt):
        p = p.strip().strip('"')
        if not os.path.exists(os.path.join(BUILD, p)):
            probs.append(f"缺输出文件 {p}")
    for s in IMG.findall(txt):
        if s.startswith("http"):
            continue
        p1 = os.path.normpath(os.path.join(os.path.dirname(path), s))
        p2 = os.path.normpath(os.path.join(BUILD, "vol", "_virtual", s))
        if not (os.path.exists(p1) or os.path.exists(p2)):
            probs.append(f"缺图片 {s}")
    if "```" in txt:
        probs.append("残留 Markdown 代码围栏 ```")
    # 残留 Markdown 粗体（排除 <code>/<pre> 里的 Python 幂运算符）
    plain = re.sub(r"<(code|pre)\b.*?</\1>", "", txt, flags=re.S)
    for m in re.finditer(r"\*\*([^*\n<>]{1,80}?)\*\*", plain):
        probs.append(f"残留 Markdown 粗体 **{m.group(1)[:20]}**")
        break
    for m in BAD_TAG.finditer(txt):
        probs.append(f"禁用标签 {m.group(0)}")
        break

    stats = {
        "汉字": len(CJK.findall(re.sub(r"<[^>]+>", "", txt))),
        "h2": len(re.findall(r"<h2[\s>]", txt)),
        "图": len(IMG.findall(txt)),
        "表": len(re.findall(r"<table", txt)),
        "代码": len(INC_CODE.findall(txt)),
        "输出": len(INC_OUT.findall(txt)),
        "实验": len(re.findall(r'class="box lab"', txt)),
    }
    if stats["汉字"] < 1200:
        probs.append(f"篇幅偏短（{stats['汉字']} 汉字）")
    return stats, probs


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    grand = {"汉字": 0, "h2": 0, "图": 0, "表": 0, "代码": 0, "输出": 0, "实验": 0}
    all_probs = []
    for v in VOLS:
        if only and v != only:
            continue
        d = os.path.join(BUILD, "vol", v)
        if not os.path.isdir(d):
            print(f"\n== {v} ==  (目录不存在)")
            continue
        files = sorted(f for f in os.listdir(d) if f.endswith(".html") and not f.startswith("_"))
        print(f"\n== {v}：{len(files)} 章 ==")
        vt = dict.fromkeys(grand, 0)
        for f in files:
            st, pr = check_fragment(os.path.join(d, f))
            for k in vt:
                vt[k] += st[k]
            flag = "  ! " + "；".join(pr) if pr else ""
            print(f"  {f:<34} 汉字{st['汉字']:>5}  图{st['图']:>2} 表{st['表']:>2} "
                  f"码{st['代码']:>2} 出{st['输出']:>2} 实验{st['实验']:>2}{flag}")
            all_probs += [(f, p) for p in pr]
        for k in grand:
            grand[k] += vt[k]
        print(f"  小计：汉字 {vt['汉字']}，图 {vt['图']}，表 {vt['表']}，"
              f"代码块 {vt['代码']}，输出块 {vt['输出']}，实验 {vt['实验']}")

    print("\n======== 总计 ========")
    print(f"汉字 {grand['汉字']}　图 {grand['图']}　表 {grand['表']}　"
          f"代码块 {grand['代码']}　输出块 {grand['输出']}　实验 {grand['实验']}")
    if all_probs:
        print(f"\n发现 {len(all_probs)} 处问题：")
        for f, p in all_probs:
            print(f"  - {f}: {p}")
        return 1
    print("\n全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
