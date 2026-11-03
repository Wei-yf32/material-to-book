# -*- coding: utf-8 -*-
"""把讲义 PDF 提取成纯文本，把 notebook 的代码单元导出成 .py，供后续写作参考。"""
import os, sys, json, glob, re

BASE = _find_root()
OUT = os.path.join(BASE, "_build")
TEXT = os.path.join(OUT, "text")
CODE = os.path.join(OUT, "code")
os.makedirs(TEXT, exist_ok=True)
os.makedirs(CODE, exist_ok=True)

import fitz  # PyMuPDF

def _find_root():
    """向上找项目根：含 _build/book.json 的目录，或本文件位于 _build/ 之下时的上一层。"""
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isfile(os.path.join(d, "_build", "book.json")):
            return d
        if os.path.basename(d) == "_build":
            return os.path.dirname(d)
        d = os.path.dirname(d)
    return os.getcwd()


def dump_pdf(src, tag):
    doc = fitz.open(src)
    pages = []
    for i, pg in enumerate(doc):
        t = pg.get_text("text")
        pages.append(f"\n===== [p{i+1}] =====\n" + t)
    out = os.path.join(TEXT, tag + ".txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"SOURCE: {src}\nPAGES: {doc.page_count}\n")
        f.write("".join(pages))
    print(f"{tag:12s} pages={doc.page_count:4d} chars={sum(len(p) for p in pages):7d}")
    return doc.page_count


def dump_ipynb(src, tag):
    with open(src, "r", encoding="utf-8", errors="replace") as f:
        nb = json.load(f)
    chunks = []
    for i, c in enumerate(nb.get("cells", [])):
        src_ = "".join(c.get("source", []))
        if c.get("cell_type") == "code":
            chunks.append(f"\n# ---------- CELL {i} (code) ----------\n" + src_)
            for o in c.get("outputs", []):
                txt = ""
                if "text" in o:
                    txt = "".join(o["text"])
                elif "data" in o and "text/plain" in o["data"]:
                    txt = "".join(o["data"]["text/plain"])
                if txt.strip():
                    chunks.append("\n# >>> OUTPUT:\n" + txt[:1500])
        elif c.get("cell_type") == "markdown":
            chunks.append(f"\n# ===== MARKDOWN {i} =====\n" + src_)
    out = os.path.join(CODE, tag + ".py")
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# SOURCE: {src}\n" + "".join(chunks))
    print(f"{tag:12s} cells={len(nb.get('cells', [])):3d} chars={sum(len(c) for c in chunks):7d}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    ml_pdf_dir = os.path.join(BASE, "机器学习训练营", "机器学习课件最终版PDF合集  3")
    dl_pdf_dir = os.path.join(BASE, "深度学习讲义")

    if mode in ("all", "pdf"):
        for fn in sorted(os.listdir(ml_pdf_dir)):
            if fn.lower().endswith(".pdf"):
                tag = "ML_" + re.sub(r"[^0-9A-Za-z]", "", fn.split(".")[0])[:16]
                dump_pdf(os.path.join(ml_pdf_dir, fn), tag)
        for fn in sorted(os.listdir(dl_pdf_dir)):
            if fn.lower().endswith(".pdf"):
                num = re.match(r"(\d+)", fn)
                tag = "DL_ch" + (num.group(1) if num else fn[:6])
                dump_pdf(os.path.join(dl_pdf_dir, fn), tag)

    if mode in ("all", "nb"):
        nbs = []
        for root, dirs, files in os.walk(BASE):
            if "_build" in root or "__MACOSX" in root:
                continue
            for f in files:
                if f.endswith(".ipynb"):
                    nbs.append(os.path.join(root, f))
        # 去重：同名不同目录时用父目录名区分
        seen = {}
        for p in sorted(nbs):
            base = os.path.splitext(os.path.basename(p))[0]
            parent = os.path.basename(os.path.dirname(p))
            tag = re.sub(r"[^0-9A-Za-z_]", "", parent)[:10] + "_" + re.sub(r"[^0-9A-Za-z_]", "", base)[:16]
            tag = tag.strip("_")
            if tag in seen:
                tag += "_2"
            seen[tag] = p
            try:
                dump_ipynb(p, tag)
            except Exception as e:
                print("ERR", p, e)


if __name__ == "__main__":
    main()
