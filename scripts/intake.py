#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""intake.py —— 阶段 −1：把资料夹读成一张表，并生成访谈卡与 intake.json 草案。

作用
    扫描一个资料夹，为每个文件取六项事实（页数、有无文字层、内嵌图尺寸、
    页脚/标题行、关键词信号、判断），打印成表格；同时打印可直接发给用户的
    "访谈卡"，并写出 _build/intake.json 草案（角色、顺序、覆盖深度等默认值）。

参数
    folder            资料夹路径（必填）
    --out PATH        intake.json 的输出路径（默认 <folder>/_build/intake.json）
    --apply           把草案合并进 <folder>/_build/book.json 的 intake 段
    --json            只打印 JSON 草案，不打印表格与访谈卡
    --max-pages N     每个 PDF 最多探测多少页（默认 12，够判断文字层与页脚）
    --major TEXT      专业（写进草案，例如 电气工程）
    --purpose TEXT    用途（例如 期末与考研）

返回
    0  正常；2  资料夹不存在或为空

关键实现
    PDF 用 PyMuPDF 取页数、文字层字符数、内嵌图尺寸；没有 pymupdf 时降级为
    只报文件大小与后缀。角色判断只给"候选 + 置信度"，最终由用户确认——
    猜错的代价是整本返工，所以这里不装作确定。

边界情况
    加密 PDF 打不开 → 记为 unreadable 并提示先解密；
    扫描件文字层为空是正常现象（要靠 pgs.py 渲染读图），不是错误。
"""

import argparse
import io
import json
import os
import re
import sys

# Windows 控制台默认 GBK，中文表头会炸；能改就改成 utf-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TEXTUAL_EXT = {".md", ".txt", ".tex", ".rst"}
CODE_EXT = {".py", ".c", ".cc", ".cpp", ".h", ".hpp", ".java", ".js", ".ts", ".go", ".rs"}
DATA_EXT = {".csv", ".tsv", ".xlsx", ".json", ".parquet"}

# 判断角色的关键词信号：命中越多，越像那一类
SIGNALS = {
    "spine": ["习题", "定理", "定义", "证明", "目录", "第一章", "教程", "教材", "第2版", "第3版", "第4版"],
    "extend_workbook": ["备考", "考情", "考点", "小测", "真题", "冲刺", "必考", "笔记", "学霸", "学考", "答案", "★"],
    "extend_slides": ["板书", "课件", "课堂", "第讲", "扫码", "全板书", "手写"],
    "reference_ai": ["讲义", "综述", "汇总", "白皮书", "开智", "图解"],
}


def human(nbytes):
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024 or unit == "GB":
            return "%.1f%s" % (nbytes, unit)
        nbytes /= 1024.0


def probe_pdf(path, max_pages=12):
    """返回 (页数, 每页平均字符数, 内嵌图最大宽×高, 首页前 120 字, 文字层判断)。"""
    try:
        import warnings
        warnings.filterwarnings("ignore")
        import pymupdf as fitz  # 新版包名；旧版只有 fitz
    except Exception:
        try:
            import fitz  # noqa: F401
        except Exception:
            return None
    try:
        doc = fitz.open(path)
    except Exception:
        return ("unreadable", 0, "", "")
    pages = doc.page_count
    chars = 0
    biggest = (0, 0)
    head = ""
    for i in range(min(pages, max_pages)):
        page = doc[i]
        text = page.get_text() or ""
        chars += len(text.strip())
        if i == 0:
            head = re.sub(r"\s+", " ", text.strip())[:120]
        for img in page.get_images(full=True):
            w, h = img[2], img[3]
            if w * h > biggest[0] * biggest[1]:
                biggest = (w, h)
    doc.close()
    # 文字层按"每页平均字符"判断：扫描件通常 < 40
    per_page = chars / max(1, min(pages, max_pages))
    layer = "有" if per_page >= 200 else ("仅页脚" if per_page >= 20 else "无")
    return (pages, int(per_page), "%d×%d" % biggest if biggest[0] else "", head, layer)


def guess_role(name, pages, layer, head, size):
    low = name + " " + head
    score = {"spine": 0, "extend_workbook": 0, "extend_slides": 0, "reference_ai": 0}
    for role, kws in SIGNALS.items():
        for kw in kws:
            if kw in low:
                score[role] += 1
    if pages and pages >= 150:
        score["spine"] += 2          # 教材通常最厚
    if layer == "无" and pages and pages <= 90:
        score["extend_slides"] += 1  # 薄 + 扫描，多半是板书
    if layer == "有":
        score["reference_ai"] += 1   # 有文字层的多为电子稿（可能是旧讲义）
    # "讲义/笔记/课件"这类词一出现，"教材"这两个字多半是引用的书名，不是它自己
    if any(kw in name for kw in ("讲义", "笔记", "课件", "板书", "开智")):
        score["spine"] -= 2
    role = max(score, key=score.get)
    if score[role] <= 0:
        return "unknown", "低"
    conf = "高" if score[role] >= 3 else ("中" if score[role] == 2 else "低")
    return role, conf


def scan(folder, max_pages=12):
    rows = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in ("_build", ".git", "__pycache__", "node_modules")]
        for fn in sorted(files):
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, folder)
            ext = os.path.splitext(fn)[1].lower()
            size = os.path.getsize(path)
            row = {"path": rel, "ext": ext, "bytes": size}
            if ext == ".pdf":
                info = probe_pdf(path, max_pages)
                if info is None:
                    row.update(pages=None, layer="?", imgs="", head="", note="未安装 pymupdf，只能凭文件名判断")
                    row["role"], row["conf"] = guess_role(fn, None, "?", "", size)
                elif info[0] == "unreadable":
                    row.update(pages=None, layer="?", imgs="", head="", note="打不开（可能加密）")
                    row["role"], row["conf"] = "unknown", "低"
                else:
                    pages, per_page, imgs, head, layer = info
                    row.update(pages=pages, layer=layer, imgs=imgs, head=head, note="")
                    row["role"], row["conf"] = guess_role(fn, pages, layer, head, size)
            else:
                row.update(pages=None, layer="-", imgs="", head="", note="")
                if ext in CODE_EXT:
                    row["role"], row["conf"] = "extend", "低"
                elif ext in DATA_EXT:
                    row["role"], row["conf"] = "extend", "低"
                elif ext in TEXTUAL_EXT:
                    row["role"], row["conf"] = "reference", "低"
                else:
                    row["role"], row["conf"] = "unknown", "低"
            rows.append(row)
    return rows


def print_table(rows):
    print("扫描结果（前五列是事实，最后一列是判断，判断需你确认）\n")
    head = ("文件", "页数", "文字层", "内嵌图", "信号", "判断")
    print("%-46s %5s %6s %10s  %-24s %s" % head)
    print("-" * 118)
    for r in rows:
        signal = (r.get("head") or r.get("note") or "")[:22]
        role = r["role"]
        if role.startswith("extend_"):
            role = "extend/" + role.split("_", 1)[1]
        print("%-46s %5s %6s %10s  %-24s %s(%s)" % (
            r["path"][:44], r.get("pages") or "-", r.get("layer", "-"),
            r.get("imgs") or "-", signal, role, r["conf"]))
    print()


def draft(rows, major=None, purpose=None):
    spine = [r["path"] for r in rows if r["role"] == "spine"]
    extend = [r["path"] for r in rows if r["role"].startswith("extend")]
    reference = [r["path"] for r in rows if r["role"] == "reference"]
    return {
        "schema": 1,
        "materials": [{"path": r["path"],
                       "role": ("extend" if r["role"].startswith("extend") else r["role"]),
                       "pages": r.get("pages"),
                       "text_layer": r.get("layer") == "有"} for r in rows],
        "spine_hint": spine[:3],
        "extend_hint": extend[:8],
        "reference_hint": reference[:8],
        "outline": "textbook_order",
        "coverage": {"defs": "all", "examples": "main", "proofs": "main", "exercises": "all"},
        "solution_depth": "key_steps",
        "side_channel": 1,
        "modern": "200w_per_chapter",
        "major": major or "",
        "purpose": purpose or "",
        "style": "textbook",
        "tone": "lecture",
        "emphasis": "block",
        "application_section": "full_flow",
        "terms_en": True,
        "figures": "script_only",
        "code_level": 1,
        "case_level": 1,
        "length": {"per_chapter_pages": [12, 16], "total_pages": 280},
        "form": ["pdf"],
        "audit": "spine_by_page",
        "titles": "keep_original",
        "confirmed": False,
    }


CARD = """
访谈卡（可整段发给用户；括号里是默认值，标★建议确认）

【材料】
1★ 哪份是主线（骨架）？其余我按"扩展"处理，只补它没有的；不想进正文的标"参考"或"不用"。
2  主线按什么顺序排？[教材顺序] / 考点 / 项目 / 概念地图

【覆盖与深度】
3★ 主线收到多细？定义定理[全含] 例题[含主体] 证明[含主体] 习题[全含]
4  课后题解析到哪一步？[答案＋关键步] / 只答案 / 完整过程；带 π 与三角的要不要折算小数？[不折]
5  主线之外我可以补什么？[常识性背景] / 联网核对（注明来源）/ 写我自己的讲法与比喻
6  每章要不要一段"后来怎么样了"？[要，至多两百字]

【写法与排版】
7★ 体例：[教材体] / 讲义体 / 手册体 / 速查体
8  语气：教材腔 / [讲课腔] / 手册腔；比喻密度 [每节至多一个]
9  重点怎么标：[底色＋边线分块] / 只用字号与缩进
10 每章要不要"应用"节？[要一节，走完整流程] / 只要背景 / 不要
11 术语首次给英文[给]、要索引[要]、图必须脚本生成[必须]、标题[沿用原书标题，难懂的加副标题]

【代码与交付】
12 要代码吗？[0–3 档，按专业推荐]；要工程案例吗？[0–3 档]
13 篇幅 [每章 12–16 页，共约 280 页]；单卷/分卷；PDF / HTML / Word
14 "包含所有内容"按什么口径验收？[主线逐页、教辅逐节、板书逐页]

不确定的直接说"按默认"。第 1、3、7 三项建议看一眼——改这三项最省后面返工。
"""


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("folder")
    ap.add_argument("--out", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-pages", type=int, default=12)
    ap.add_argument("--major", default=None)
    ap.add_argument("--purpose", default=None)
    a = ap.parse_args()

    folder = os.path.abspath(a.folder)
    if not os.path.isdir(folder):
        print("资料夹不存在：%s" % folder)
        return 2

    rows = scan(folder, a.max_pages)
    if not rows:
        print("资料夹里没有文件：%s" % folder)
        return 2

    d = draft(rows, a.major, a.purpose)
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=2))
    else:
        print_table(rows)
        print(CARD)

    out = a.out or os.path.join(folder, "_build", "intake.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(d, ensure_ascii=False, indent=2))
    if not a.json:
        print("\n草案已写入：%s" % out)
        print("答完访谈后：改这份 json，再执行  python scripts/intake.py \"%s\" --apply" % folder)

    if a.apply:
        bj = os.path.join(folder, "_build", "book.json")
        if not os.path.exists(bj):
            print("没有找到 _build/book.json，先跑 scripts/init_project.py")
            return 2
        cfg = json.load(io.open(bj, encoding="utf-8"))
        cfg["intake"] = d
        with io.open(bj, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(cfg, ensure_ascii=False, indent=2))
        print("已合并进 %s 的 intake 段" % bj)
    return 0


if __name__ == "__main__":
    sys.exit(main())
