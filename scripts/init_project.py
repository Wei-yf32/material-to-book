# -*- coding: utf-8 -*-
"""在目标资料夹里初始化一本书的构建目录（_build/）。

用法：
    python init_project.py <资料夹> [--title "书名"] [--volumes 3]

做的事：
    <资料夹>/_build/
        book.json          # 卷与标题配置（先填这里，再写章节）
        tools/             # 本 skill 附带的全套脚本（复制一份，可改）
        css/book.css       # 排版样式
        vol/vol0 ... volN/ # 每卷的章节片段（NN_标题.html）
        src/figs/          # 代码脚本（INCLUDE-CODE 引用）
        out/               # 脚本真实输出（INCLUDE-OUTPUT 引用）
        figures/           # 生成的图表（SVG/PNG）
        html/ pdf/         # 构建中间产物
"""

import argparse
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="资料夹路径")
    ap.add_argument("--title", default="资料汇总讲义")
    ap.add_argument("--volumes", type=int, default=3, help="建几个空的卷目录")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    base = os.path.abspath(a.target)
    build = os.path.join(base, "_build")
    if os.path.exists(os.path.join(build, "book.json")) and not a.force:
        print("已存在 _build/book.json，用 --force 覆盖")
        return 1

    for sub in ("tools", "css", "src", "out", "figures", "html", "pdf", "preview"):
        os.makedirs(os.path.join(build, sub), exist_ok=True)
    for i in range(a.volumes):
        os.makedirs(os.path.join(build, "vol", "vol%d" % i), exist_ok=True)

    for f in sorted(os.listdir(HERE)):
        if f.endswith(".py"):
            shutil.copy2(os.path.join(HERE, f), os.path.join(build, "tools", f))
    shutil.copy2(os.path.join(SKILL, "assets", "book.css"),
                 os.path.join(build, "css", "book.css"))

    vols = {}
    for i in range(a.volumes):
        vols["vol%d" % i] = {
            "title": "第 %d 卷 卷名待填" % i,
            "file": "%02d_卷名待填" % i,
            "subtitle": "副标题：这一卷讲什么",
            "points": ["封面要点 1（6~8 条）", "封面要点 2"]
        }
    cfg = {
        "title": a.title,
        "output": a.title + ".pdf",
        "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        # 封面与页眉文案（都可删；删了就用默认值）
        "brand": a.title,                 # 封面顶部横条左侧、页眉右侧
        "org": "",                        # 封面右上角第一行，例如 "某某大学 某学院"
        "edition": "资料整合与深化版",     # 封面右上角第二行
        "kicker": "DOCUMENTATION",         # 封面上的英文小字
        "author": "",                     # PDF 元数据作者
        "meta_lines": [                    # 封面底部说明（每项一行）
            "本卷为《%s》之一部分。" % a.title,
            "插图由本书脚本基于真实数据重新绘制；代码均可独立复现，输出为实际运行结果。"
        ],
        # 章号体例：textbook = 「第 1 章 / 1.1」；lecture = 「01 / 01.1」
        # 两种都不给「习题 / 本章小结 / 附录」编号
        "numbering": "textbook",
        # 访谈结论（scripts/intake.py --apply 会写这里；没有就删掉）
        "intake": {},
        "volumes": vols,
    }
    io.open(os.path.join(build, "book.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")

    print("已初始化:", build)
    print("下一步：")
    print("  1) 改 _build/book.json 的卷名/副标题/要点")
    print("  2) 把每卷章节写成 _build/vol/<vol>/NN_标题.html（模板见 skill 的 references/chapter-template.html）")
    print("  3) python _build/tools/build.py vol0   # 先构建一卷试水")
    print("  4) python _build/tools/build.py merge  # 合订")
    return 0


if __name__ == "__main__":
    sys.exit(main())
