# -*- coding: utf-8 -*-
"""
单章预览 / 片段体检工具（供各章写作时自检，不参与成书）。

用法:
  python preview.py <片段.html> [--pdf]     # 生成单章 PDF 预览（含公式/代码/图）
  python preview.py <片段.html> --check     # 只做静态体检
输出:
  体检报告（缺图、未转义代码、结构问题、字数统计）
  PDF 预览保存到 _build/preview/<名字>.pdf，并报告页数
"""
import os, re, sys, html, time, subprocess, shutil

def _find_edge():
    """找 Chromium 内核浏览器：环境变量 EDGE_BIN > 常见安装位置 > PATH。"""
    env = os.environ.get("EDGE_BIN")
    if env and os.path.exists(env):
        return env
    cands = [
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                     "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                     "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     "Google", "Chrome", "Application", "chrome.exe"),
        "/usr/bin/microsoft-edge",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
    ]
    for p in cands:
        if os.path.exists(p):
            return p
    return shutil.which("msedge") or shutil.which("google-chrome") or "msedge"

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

BASE = _find_root()
BUILD = os.path.join(BASE, "_build")
EDGE = _find_edge()
sys.path.insert(0, os.path.join(BUILD))


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def check(path):
    txt = read(path)
    problems = []
    warns = []
    # 1) 结构
    if not re.search(r"<h1[\s>]", txt):
        problems.append("缺少 <h1> 章标题")
    if re.search(r"<(!DOCTYPE|html|head|body|style|script)\b", txt, re.I):
        problems.append("片段中不允许出现 html/head/body/style/script 标签")
    # 2) 图片
    srcs = re.findall(r'<img[^>]+src="([^"]+)"', txt)
    for s in srcs:
        if s.startswith("http"):
            continue
        # 片段最终会被放进 _build/vol/<vol>/ 参与整卷拼装，因此按该层级解析相对路径
        p1 = os.path.normpath(os.path.join(os.path.dirname(path), s))
        p2 = os.path.normpath(os.path.join(BUILD, "vol", "_virtual", s))
        if not (os.path.exists(p1) or os.path.exists(p2)):
            problems.append(f"图片不存在: {s}")
    # 3) 未转义代码：<pre class="code"> 里出现 <标签形状
    for m in re.finditer(r'<pre class="code"[^>]*>(.*?)</pre>', txt, re.S):
        body = m.group(1)
        if re.search(r"<[A-Za-z/!]", body):
            problems.append("代码块里有未转义的 < 或标签（应使用 INCLUDE-CODE）")
    # 4) 数学公式
    if re.search(r"(?<!\\)\$[^$]{1,80}\$", txt):
        warns.append("疑似使用了 $...$ 行内公式，请改为 \\( \\)")
    if "\\begin{" in txt and "\\[" not in txt:
        warns.append("检测到 LaTeX 环境，确认放在 \\[ \\] 中")
    # 5) 表格
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", txt, re.S):
        if "<thead" not in m.group(1):
            warns.append("表格缺少 <thead>，跨页时不会重复表头")
    # 6) 标题层级
    hs = re.findall(r"<h([1-4])", txt)
    prev = 0
    for h in hs:
        h = int(h)
        if prev and h > prev + 1:
            warns.append(f"标题层级跳跃: h{prev} -> h{h}")
        prev = h
    # 7) 计数
    text = re.sub(r"<[^>]+>", "", re.sub(r"<pre.*?</pre>", "", txt, flags=re.S))
    nchar = len(re.findall(r"[\u4e00-\u9fff]", text))
    stats = {
        "正文汉字": nchar,
        "h2 小节": len(re.findall(r"<h2", txt)),
        "h3 小节": len(re.findall(r"<h3", txt)),
        "代码块": len(re.findall(r'<pre class="code"', txt)) + len(re.findall(r"INCLUDE-CODE", txt)),
        "输出块": len(re.findall(r'<pre class="output"', txt)) + len(re.findall(r"INCLUDE-OUTPUT", txt)),
        "图": len(re.findall(r"<img", txt)),
        "表": len(re.findall(r"<table", txt)),
        "公式(display)": len(re.findall(r"\\\[", txt)),
        "提示框": len(re.findall(r'class="box ', txt)),
    }
    print(f"== 体检: {os.path.basename(path)} ==")
    for k, v in stats.items():
        print(f"   {k:12s}{v}")
    if problems:
        print("\n[必须修复]")
        for p in problems:
            print("  x " + p)
    if warns:
        print("\n[建议检查]")
        for w in warns:
            print("  ! " + w)
    if not problems and not warns:
        print("\n通过。")
    return problems


def preview_pdf(path):
    import build as B
    name = os.path.splitext(os.path.basename(path))[0]
    frag = B.fix_fig_paths(B.expand_includes(read(path)))
    css = os.path.join(BUILD, "css", "book.css").replace("\\", "/")
    out = os.path.join(BUILD, "preview")
    os.makedirs(out, exist_ok=True)
    hp = os.path.join(out, name + ".html")
    # 单章预览没有封面，需取消“首页满版”规则，否则第 1 页会没有页边距
    override = "<style>@page:first{margin:20mm 17mm 18mm 17mm;}</style>"
    B.write(hp, B.HEAD.format(title=name, css=css, mj=B.MATHJAX_CDN)
            .replace("</head>", override + "</head>") + frag + B.TAIL)
    pdf, dt = B.print_pdf(hp, os.path.join(out, name + ".pdf"), budget=90000)
    import pymupdf
    d = pymupdf.open(pdf)
    n = d.page_count
    d.close()
    # 简单溢出检测：页面文字最下方 / 最右方是否越界
    d = pymupdf.open(pdf)
    over = []
    for i, pg in enumerate(d):
        for b in pg.get_text("blocks"):
            x0, y0, x1, y1 = b[:4]
            if x1 > pg.rect.width - 20 or y1 > pg.rect.height - 10 or x0 < 20:
                over.append((i + 1, round(x0), round(y0), round(x1), round(y1)))
                break
    d.close()
    print(f"[preview] {n} 页 -> {pdf}")
    if over:
        print(f"[preview] 警告: {len(over)} 页存在内容越界迹象 {over[:5]}")
    return pdf, n


if __name__ == "__main__":
    p = sys.argv[1]
    if "--check" in sys.argv:
        sys.exit(1 if check(p) else 0)
    probs = check(p)
    if "--pdf" in sys.argv or not probs:
        preview_pdf(p)
    sys.exit(1 if probs else 0)
