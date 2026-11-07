# -*- coding: utf-8 -*-
"""
驭风讲义 · 构建流水线
  1) 把 _build/vol/<vol>/*.html 片段拼成整卷 HTML（含封面 + 目录）
  2) 用 Edge(Chromium) headless 打印成 PDF
  3) 用 PyMuPDF 回填页码、书签、页眉页脚
  4) 目录页码采用两遍法：先占位后回填，保证版式稳定

用法:
  python build.py python            # 构建某一卷
  python build.py all               # 构建全部卷
  python build.py merge             # 合并全册
"""
import os, io, re, sys, json, glob, html, shutil, subprocess, time
from collections import OrderedDict

def _find_root(start):
    """向上找到含有 _build/ 的项目根目录（skill 里 build.py 位于 <root>/_build/tools/）。"""
    d = os.path.abspath(start)
    for _ in range(6):
        if os.path.exists(os.path.join(d, "_build", "book.json")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return os.path.abspath(os.path.join(start, "..", ".."))


BASE = _find_root(os.path.dirname(os.path.abspath(__file__)))  # project root
BUILD = os.path.join(BASE, "_build")
VOL = os.path.join(BUILD, "vol")
OUT_HTML = os.path.join(BUILD, "html")
OUT_PDF = os.path.join(BUILD, "pdf")
FIG = os.path.join(BUILD, "figures")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
_cfg_path = os.path.join(BUILD, "book.json")
CFG = json.loads(io.open(_cfg_path, encoding="utf-8").read()) if os.path.exists(_cfg_path) else {}
if CFG.get("edge"):
    EDGE = CFG["edge"]
MERGED_NAME = CFG.get("output") or "book.pdf"
BOOK_TITLE = CFG.get("title") or "资料汇总讲义"

BRAND = CFG.get("brand") or BOOK_TITLE
ORG = CFG.get("org") or ""
EDITION = CFG.get("edition") or ""
KICKER = CFG.get("kicker") or ""
AUTHOR = CFG.get("author") or ""
HEADER_RIGHT = CFG.get("header_right") or BRAND
# 章号体例：textbook=「第 N 章 / N.k」，lecture=「NN / NN.k」
NUMBERING = (CFG.get("numbering") or "textbook").lower()
if NUMBERING not in ("textbook", "lecture"):
    NUMBERING = "textbook"
_meta_lines = CFG.get("meta_lines") or ["本卷为《%s》之一部分。" % BOOK_TITLE]
FOOTER_HTML = "<br>".join(_meta_lines)


for d in (OUT_HTML, OUT_PDF, FIG):
    os.makedirs(d, exist_ok=True)

# 语法高亮（可选）
try:
    from pygments import highlight
    from pygments.lexers import PythonLexer, CppLexer, CLexer, BashLexer, TextLexer, JsonLexer, CMakeLexer
    from pygments.formatters import HtmlFormatter
    _LEX = {"py": PythonLexer, "python": PythonLexer, "cpp": CppLexer, "cxx": CppLexer,
            "c": CLexer, "bash": BashLexer, "sh": BashLexer, "json": JsonLexer,
            "text": TextLexer, "cmake": CMakeLexer}
    _FMT = HtmlFormatter(nowrap=True, classprefix="pg-")
    HAS_PYGMENTS = True
except Exception:
    HAS_PYGMENTS = False

# ---------------------------------------------------------------- 卷定义
VOLUMES = OrderedDict()
for _k, _v in (CFG.get("volumes") or {}).items():
    VOLUMES[_k] = dict(title=_v["title"], file=_v["file"],
                       subtitle=_v.get("subtitle", ""),
                       points=_v.get("points", []))
    for _extra in ("header_right", "keywords"):
        if _v.get(_extra):
            VOLUMES[_k][_extra] = _v[_extra]
if not VOLUMES:
    raise SystemExit("缺少 _build/book.json，或 volumes 为空：先运行 scripts/init_project.py")

MATHJAX_CDN = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"

HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{title} · 驭风计划</title>
<link rel="stylesheet" href="{css}">
<script>
window.MathJax = {{
  tex: {{
    inlineMath: [['\\\\(','\\\\)']],
    displayMath: [['\\\\[','\\\\]']],
    processEscapes: true,
    tags: 'none',
    macros: {{
      bm: ['\\\\boldsymbol{{#1}}',1],
      dd: '\\\\mathrm{{d}}',
      R: '\\\\mathbb{{R}}',
      E: '\\\\mathbb{{E}}',
      var: ['\\\\operatorname{{Var}}',0],
      cov: ['\\\\operatorname{{Cov}}',0],
      argmax: ['\\\\operatorname*{{arg\\\\,max}}',0],
      argmin: ['\\\\operatorname*{{arg\\\\,min}}',0]
    }}
  }},
  svg: {{ fontCache: 'none', scale: 1.02, mtextInheritFont: false, displayAlign: 'center' }},
  options: {{ enableMenu: false, skipHtmlTags: ['script','noscript','style','textarea','pre','code'] }}
}};
</script>
<script src="{mj}" id="MathJax-script"></script>
</head>
<body>
"""

TAIL = """
</body></html>
"""


def read(p):
    # 容错：不同工具保存的 UTF-8 带 BOM / UTF-16 / GBK 都能读
    raw = open(p, "rb").read()
    doc = None
    for enc in ("utf-8-sig", "utf-16", "gbk"):
        try:
            doc = raw.decode(enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if doc is None:
        doc = raw.decode("utf-8", "replace")
    # 统一换行：<pre> 里的 CRLF 会被当成两次换行，渲染出空行加倍
    return doc.replace("\r\n", "\n").replace("\r", "\n")


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


INC_CODE = re.compile(
    r'<!--\s*INCLUDE-CODE\s+path=([^\s>]+?)'
    r'(?:\s+lang=(\w+))?'
    r'(?:\s+ln=(\d))?'
    r'(?:\s+note="([^"]*)")?'
    r'\s*-->'
)
INC_OUT = re.compile(r"<!--\s*INCLUDE-OUTPUT\s+path=([^\s>]+?)\s*-->")
INC_TREE = re.compile(r"<!--\s*INCLUDE-TREE\s+path=([^\s>]+?)\s*-->")
INC_DATA = re.compile(r"<!--\s*INCLUDE-DATA\s+path=([^\s>]+?)\s*-->")


def _dw(s):
    """等宽字体下的显示宽度：中日韩字符按 2 计。"""
    import unicodedata

    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in str(s))


def _tree_html(spec_text):
    """把目录树描述渲染成带颜色的 <pre class="tree">。
    每行格式：缩进 + 名字 + 至少两个空格 + 说明；目录以 / 结尾。"""
    import html as _h

    raw_lines = [l for l in spec_text.splitlines()]
    # 先按缩进分组，算出每组名字的最大显示宽度，用于对齐说明文字
    width = {}
    for l in raw_lines:
        if not l.strip() or l.strip().startswith("#"):
            continue
        ind = len(l) - len(l.lstrip())
        nm = l.strip().split("  ")[0]
        width[ind] = max(width.get(ind, 0), _dw(nm))

    out = []
    for raw in raw_lines:
        if not raw.strip():
            out.append("")
            continue
        line = raw.rstrip()
        stripped = line.strip()
        # 用两个以上空格切出「名字 / 说明」
        parts = re.split(r"\s{2,}", stripped, maxsplit=1)
        name = parts[0]
        note = parts[1] if len(parts) > 1 else ""
        indent = line[: len(line) - len(line.lstrip())].replace("\t", "    ")
        esc = _h.escape(name)
        if stripped.startswith("#"):
            cls, esc = "t-cm", _h.escape(stripped)
        elif name.endswith("/"):
            cls = "t-dir"
        elif name.endswith(".py") or name.endswith(".cpp") or name.endswith(".c"):
            cls = "t-py"
        elif name.endswith(".csv") or name.endswith(".json") or name.endswith(".npz"):
            cls = "t-data"
        elif name.endswith(".txt") or name.endswith(".log"):
            cls = "t-out"
        else:
            cls = "t-cm"
        if note:
            padn = width.get(len(line) - len(line.lstrip()), _dw(name)) - _dw(name) + 2
            tail = " " * max(2, padn) + _h.escape(note)
        else:
            tail = ""
        out.append(f'{indent}<span class="{cls}">{esc}</span>{tail}')
    return '<pre class="tree">' + "\n".join(out) + "</pre>"


def expand_includes(txt):
    """把 <!--INCLUDE-CODE path=... lang=py--> 换成高亮后的 <pre>。
    路径相对于 _build/ 目录。代码永远不会因为手写转义出错。"""
    def repl_code(m):
        p = m.group(1).strip().strip('"')
        lang = (m.group(2) or "").lower()
        full = p if os.path.isabs(p) else os.path.join(BUILD, p.replace("/", os.sep))
        if not os.path.exists(full):
            return f'<div class="box warn"><div class="box-title">缺失代码文件</div><p>{html.escape(p)}</p></div>'
        src = read(full).replace("\t", "    ").rstrip("\n")
        if lang and HAS_PYGMENTS and lang in _LEX:
            body = highlight(src, _LEX[lang](), _FMT).rstrip("\n")
        else:
            body = html.escape(src)
        note = (m.group(4) or "").strip()
        shown = p.replace("\\", "/")
        if shown.startswith("src/"):
            shown = shown
        head = f'<div class="codefile"><span class="cf-path">{html.escape(shown)}</span>'
        if note:
            head += f'<span class="cf-note">{html.escape(note)}</span>'
        head += '</div>'
        return head + f'<pre class="code lang-{lang or "txt"}">{body}</pre>'

    def repl_out(m):
        p = m.group(1).strip().strip('"')
        full = p if os.path.isabs(p) else os.path.join(BUILD, p.replace("/", os.sep))
        if not os.path.exists(full):
            return f'<div class="box warn"><div class="box-title">缺失输出文件</div><p>{html.escape(p)}</p></div>'
        src = read(full).replace("\t", "    ").rstrip("\n")
        return f'<pre class="output">{html.escape(src)}</pre>'

    def repl_tree(m):
        p = m.group(1).strip().strip('"')
        full = p if os.path.isabs(p) else os.path.join(BUILD, p.replace("/", os.sep))
        if not os.path.exists(full):
            return f'<div class="box warn"><div class="box-title">缺失目录树文件</div><p>{html.escape(p)}</p></div>'
        return _tree_html(read(full))

    def repl_data(m):
        p = m.group(1).strip().strip('"')
        full = p if os.path.isabs(p) else os.path.join(BUILD, p.replace("/", os.sep))
        if not os.path.exists(full):
            return f'<div class="box warn"><div class="box-title">缺失数据文件</div><p>{html.escape(p)}</p></div>'
        return f'<pre class="data">{html.escape(read(full).rstrip())}</pre>'

    txt = INC_DATA.sub(repl_data, txt)
    txt = INC_TREE.sub(repl_tree, txt)
    txt = INC_CODE.sub(repl_code, txt)
    txt = INC_OUT.sub(repl_out, txt)
    return txt


def fix_fig_paths(txt):
    """片段里的 ../../figures/ 相对片段位置；整卷 HTML 在 _build/html/ 下，只需 ../figures/。"""
    txt = txt.replace('src="../../figures/', 'src="../figures/')
    txt = txt.replace("src='../../figures/", "src='../figures/")
    return txt


# ---------------------------------------------------------------- 片段收集
def collect(vol_id):
    d = os.path.join(VOL, vol_id)
    files = sorted(glob.glob(os.path.join(d, "*.html")))
    frags = []
    for f in files:
        name = os.path.basename(f)
        if name.startswith("_") or name == "cover.html":
            continue
        frags.append((name, fix_lt_in_math(fix_fig_paths(expand_includes(read(f))))))
    return renumber_headings(flatten_math_in_thead(frags))


HEAD_RE = re.compile(r"<(h1|h2)\b([^>]*)>(.*?)</\1>", re.S | re.I)


NONUM_PAT = re.compile(r"^(习题|本章小结|小结|附录|前言|复习题)")


def _is_nonum(lvl, attrs, body):
    if lvl != 2:
        return False
    if "nonum" in (attrs or ""):
        return True
    plain = re.sub(r"<[^>]+>", "", body or "").strip()
    return bool(NONUM_PAT.match(plain))


def renumber_headings(frags):
    """把正文 h1/h2 的编号统一改写成"文件前缀章号 + 出现序号"。

    章节作者写的编号（"2.1 直觉"、"4．2 泰勒"）一律先剥掉，再按文件名前缀与出现顺序重排，
    这样正文标题与目录、书签三处编号永远一致；否则会出现目录写 04.3、正文写 3.2 的错位。
    """
    out = []
    for name, txt in frags:
        m_nn = re.match(r"(\d+)", name)
        nn = int(m_nn.group(1)) if m_nn else 0
        state = {"sec": 0}

        numbered = 1 <= nn < 90

        def repl(m):
            tag, attrs, inner = m.group(1), m.group(2), m.group(3)
            lvl = 1 if tag.lower() == "h1" else 2
            body = re.sub(r'<span class="hm">.*?</span>', "", inner)
            body = re.sub(r"^\s*\d+(?:[.．]\d+)*[\s、.．]+", "", body).strip()
            body = re.sub(r"^第\s*\d+\s*章[\s　]*", "", body).strip()
            if not body:
                return m.group(0)
            if not numbered or _is_nonum(lvl, attrs, body):
                if lvl == 1:
                    state["sec"] = 0
                return "<%s%s>%s</%s>" % (tag, attrs, body, tag)
            if lvl == 1:
                state["sec"] = 0
                if NUMBERING == "textbook":
                    head = "第 %d 章　%s" % (nn, body)
                else:
                    head = "%02d　%s" % (nn, body)
            else:
                state["sec"] += 1
                if NUMBERING == "textbook":
                    head = "%d.%d　%s" % (nn, state["sec"], body)
                else:
                    head = "%02d.%d　%s" % (nn, state["sec"], body)
            return "<%s%s>%s</%s>" % (tag, attrs, head, tag)

        out.append((name, HEAD_RE.sub(repl, txt)))
    return out


def plain_title(s):
    """书签与表头用的纯文本标题：去掉 LaTeX 定界符与控制序列，尽量保留可读内容。"""
    s = re.sub(r"\\sqrt\[([^\]]*)\]\{([^{}]*)\}", r"√[\1](\2)", s)
    s = re.sub(r"\\sqrt\{([^{}]*)\}", r"√(\1)", s)
    s = re.sub(r"\\\((.*?)\\\)", r"\1", s, flags=re.S)
    s = re.sub(r"\\\[(.*?)\\\]", r"\1", s, flags=re.S)
    for k, v in GREEK:
        s = re.sub(re.escape(k) + r"(?![a-zA-Z])", v, s)
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)
    s = s.replace("\\", "").replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


# 表头/书签里的希腊字母与常用符号，换成能直接印刷的 Unicode
GREEK = [
    ("\\omega", "ω"), ("\\Omega", "Ω"), ("\\delta", "δ"), ("\\Delta", "Δ"),
    ("\\theta", "θ"), ("\\pi", "π"), ("\\varphi", "φ"), ("\\phi", "φ"),
    ("\\alpha", "α"), ("\\beta", "β"), ("\\gamma", "γ"), ("\\Gamma", "Γ"),
    ("\\sigma", "σ"), ("\\tau", "τ"), ("\\lambda", "λ"), ("\\mu", "μ"),
    ("\\xi", "ξ"), ("\\zeta", "ζ"), ("\\eta", "η"), ("\\rho", "ρ"),
    ("\\infty", "∞"), ("\\pm", "±"), ("\\times", "×"), ("\\cdot", "·"),
    ("\\le", "≤"), ("\\ge", "≥"), ("\\ne", "≠"), ("\\to", "→"),
    ("\\partial", "∂"), ("\\int", "∫"), ("\\sum", "∑"), ("\\in", "∈"),
    ("\\Rightarrow", "⇒"), ("\\leftrightarrow", "↔"), ("\\approx", "≈"),
]


TH_RE = re.compile(r"(<th\b[^>]*>)(.*?)(</th>)", re.S | re.I)
THEAD_RE = re.compile(r"<thead\b.*?</thead>", re.S | re.I)


def flatten_math_in_thead(frags):
    """把表头里的 LaTeX 换成纯文本。

    Chromium 打印跨页表格时会克隆表头，而克隆出来的节点不会再跑一遍 MathJax，
    于是第二页起的表头里公式全变空白。表头改成纯文本（f(t)/F(ω)）可以彻底避免。
    """
    out = []
    for name, txt in frags:
        def fix_head(m):
            return TH_RE.sub(
                lambda mm: mm.group(1) + html.escape(plain_title(strip_tags(mm.group(2)))) + mm.group(3),
                m.group(0))

        out.append((name, THEAD_RE.sub(fix_head, txt)))
    return out


MATH_RE = re.compile(r"(\\\(.+?\\\)|\\\[.+?\\\])", re.S)


def fix_lt_in_math(txt):
    """公式里的 < > 会被浏览器当成标签，统一转义。"""
    def repl(m):
        seg = m.group(1)
        seg = seg.replace("<", "&lt;")
        return seg
    return MATH_RE.sub(repl, txt)


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def extract_entries(frags):
    """返回 [(level, title, label)]；label 取文件名前缀的章号，保证目录编号与正文“图 NN-k”一致。"""
    entries = []
    for name, txt in frags:
        m_nn = re.match(r"(\d+)", name)
        nn = int(m_nn.group(1)) if m_nn else 0
        sec = 0
        for m in HEAD_RE.finditer(txt):
            lvl = 1 if m.group(1).lower() == "h1" else 2
            title = strip_tags(m.group(3))
            # 若标题自带编号（“1.1 xxx”），编号交给目录，标题里去掉，避免“00.1 1.1 xxx”
            title = re.sub(r"^\d+(?:[.．]\d+)*[\s、.．]+", "", title).strip()
            title = re.sub(r"^第\s*\d+\s*章[\s　]*", "", title).strip()
            if not title:
                continue
            numbered = 1 <= nn < 90
            if lvl == 1:
                sec = 0
                if not numbered:
                    entries.append((1, title, ""))
                else:
                    if NUMBERING == "textbook":
                        entries.append((1, title, f"第 {nn} 章"))
                    else:
                        entries.append((1, title, f"{nn:02d}"))
            else:
                if _is_nonum(2, m.group(2) or "", m.group(3)):
                    entries.append((2, title, ""))
                else:
                    sec += 1
                    if not numbered:
                        entries.append((2, title, ""))
                    else:
                        if NUMBERING == "textbook":
                            entries.append((2, title, f"{nn}.{sec}"))
                        else:
                            entries.append((2, title, f"{nn:02d}.{sec}"))
    return entries


def mark_headings(frags):
    """在每个 h1/h2 标题前插入白色极小标记，用于在 PDF 中精确定位页码。"""
    out = []
    k = 0
    for name, txt in frags:
        def repl(m):
            nonlocal k
            k += 1
            tag, attrs, inner = m.group(1), m.group(2), m.group(3)
            return f'<{tag}{attrs}><span class="hm">ZZQ{k}ZZ</span>{inner}</{tag}>'
        out.append((name, HEAD_RE.sub(repl, txt)))
    return out, k


def build_toc(entries, numbers=None, placeholder="00"):
    """由 [(level, title, label)] 生成目录，label 直接用作章节号。"""
    out = ['<div class="toc"><h1>目录</h1><ol>']
    for idx, (lvl, title, label) in enumerate(entries):
        if numbers is None or idx >= len(numbers):
            pg = placeholder
        else:
            pg = str(numbers[idx])
        cls = "t1" if lvl == 1 else "t2"
        out.append(f'<li class="{cls}"><span class="n">{label}</span>'
                   f'<span class="tt">{html.escape(title)}</span>'
                   f'<span class="dotfill"></span><span class="pg">{pg}</span></li>')
    out.append('</ol></div>')
    return "".join(out)


def cover_html(meta, vol_id="vol0"):
    num = vol_id.replace("vol", "")
    # 单卷本用 volc 这类非数字 id：留空，避免出现 VOL.0c
    vol_label = ("VOL." + num.zfill(2)) if num.isdigit() else ""
    big = num.zfill(2) if num.isdigit() else ""
    return f"""
<div class="cover">
  <div class="band"><span class="cn">{BRAND}</span><span class="vol">{vol_label}</span></div>
  <div class="emblem">{ORG}<br>{EDITION}</div>
  <div class="series">{KICKER}</div>
  <h1>{meta['title']}</h1>
  <div class="rule"></div>
  <div class="sub">{meta['subtitle']}</div>
  <div class="bigvol">{big}</div>
  <ul class="points">
    {''.join(f'<li>{p}</li>' for p in meta.get('points', []))}
  </ul>
  <div class="meta">
    {FOOTER_HTML}
  </div>
</div>
"""


def assemble(vol_id, numbers=None, frags=None):
    meta = VOLUMES[vol_id]
    if frags is None:
        frags = collect(vol_id)
    entries = extract_entries(frags)
    toc = build_toc(entries, numbers)
    frags, nmark = mark_headings(frags)
    assert nmark == len(entries), (nmark, len(entries))
    css = os.path.join(BUILD, "css", "book.css").replace("\\", "/")
    parts = [HEAD.format(title=meta["title"], css=css, mj=MATHJAX_CDN)]
    cv = os.path.join(VOL, vol_id, "cover.html")
    parts.append(fix_fig_paths(expand_includes(read(cv))) if os.path.exists(cv) else cover_html(meta, vol_id))
    parts.append(toc)
    for _, t in frags:
        parts.append(t)
    parts.append(TAIL)
    out = os.path.join(OUT_HTML, vol_id + ".html")
    write(out, "".join(parts))
    return out, entries


# ---------------------------------------------------------------- 打印
def print_pdf(html_path, pdf_path, budget=120000):
    # 输出名带时间戳：避免上一次 Edge 尚未完全释放文件导致 PermissionError
    stem, ext = os.path.splitext(pdf_path)
    out = f"{stem}_{int(time.time()*1000)%1000000}{ext}"
    udd = os.path.join(BUILD, "tmp", "edge_" + str(os.getpid()) + "_" + str(int(time.time()*1000)%100000))
    os.makedirs(udd, exist_ok=True)
    url = "file:///" + html_path.replace("\\", "/")
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--no-first-run",
           "--disable-extensions", "--hide-scrollbars",
           "--run-all-compositor-stages-before-draw",
           f"--virtual-time-budget={budget}",
           f"--user-data-dir={udd}",
           "--no-pdf-header-footer",
           f"--print-to-pdf={out}", url]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, timeout=1800)
    dt = time.time() - t0
    if not os.path.exists(out):
        raise RuntimeError("打印失败: " + r.stderr.decode("utf-8", "ignore")[-2000:])
    shutil.copyfile(out, pdf_path) if False else None
    return out, dt


def norm(s):
    return re.sub(r"[\s\u00a0]+", "", s)


def map_pages(pdf_path, entries, start_from=1):
    """用标题旁的隐形标记 ZZC{k}ZZ 精确定位每个标题所在页。"""
    import pymupdf as fitz
    doc = fitz.open(pdf_path)
    texts = [norm(p.get_text()) for p in doc]
    n = doc.page_count
    pages = []
    last = 1
    for k, ent in enumerate(entries, start=1):
        lvl, title = ent[0], ent[1]
        mk = f"ZZQ{k}ZZ"
        found = None
        for i in range(0, n):
            if mk in texts[i]:
                found = i + 1
                break
        if found is None:
            found = last
        pages.append(found)
        last = found
    doc.close()
    return pages


def stamp(pdf_path, out_path, meta, entries, pages, start_num=1, header_text=""):
    """加页码 + 页眉 + 书签。封面不加。使用 Microsoft YaHei 嵌入字体保证中英文宽度正常。"""
    import pymupdf as fitz
    FONT = r"C:\Windows\Fonts\msyh.ttc"
    doc = fitz.open(pdf_path)
    n = doc.page_count
    hdr = header_text or meta["title"]
    for i, pg in enumerate(doc):
        w, h = pg.rect.width, pg.rect.height
        num = i + 1
        if i == 0:
            continue  # 封面
        pg.insert_text(fitz.Point(48, 30), hdr, fontsize=7.6, fontfile=FONT,
                       fontname="msyh", color=(0.42, 0.42, 0.42))
        box = fitz.Rect(w - 48 - 170, 18, w - 48, 33)
        pg.insert_textbox(box, meta.get("header_right") or HEADER_RIGHT, fontsize=7.2, fontfile=FONT,
                          fontname="msyh", color=(0.52, 0.52, 0.52), align=2)
        pg.draw_line(fitz.Point(48, 36), fitz.Point(w - 48, 36),
                     color=(0.82, 0.80, 0.76), width=0.5)
        pg.insert_textbox(fitz.Rect(48, h - 34, w - 48, h - 20), f"— {num} —",
                          fontsize=8.6, fontfile=FONT, fontname="msyh",
                          color=(0.35, 0.35, 0.35), align=1)
    toc = []
    for ent, p in zip(entries, pages):
        label = ent[2] if len(ent) > 2 else ""
        title = plain_title(ent[1])
        toc.append([ent[0], f"{label} {title}".strip(), p])
    if toc:
        doc.set_toc(toc)
    doc.set_metadata({
        "title": meta["title"] if meta.get("header_right") or meta.get("keywords") else meta["title"] + " · " + BRAND,
        "author": AUTHOR or BRAND,
        "subject": meta["subtitle"],
        "keywords": meta.get("keywords") or "复变函数,积分变换,解析函数,留数,共形映射,傅里叶变换,拉普拉斯变换,z变换",
        "creator": "HTML+MathJax -> Chromium -> PyMuPDF pipeline",
    })
    doc.save(out_path, garbage=3, deflate=True)
    doc.close()
    return n


def build_vol(vol_id, verbose=True):
    meta = VOLUMES[vol_id]
    # 固定一次章节快照：写作期间别的进程可能正在改文件，多遍构建必须用同一份
    frags = collect(vol_id)
    # 第 1 遍：占位目录
    html1, entries = assemble(vol_id, None, frags)
    pdf1, dt = print_pdf(html1, os.path.join(OUT_PDF, vol_id + "_p1.pdf"))
    pages = map_pages(pdf1, entries)
    # 第 2 遍：回填真实页码
    html2, entries2 = assemble(vol_id, pages, frags)
    pdf2, _ = print_pdf(html2, os.path.join(OUT_PDF, vol_id + "_p2.pdf"))
    pages2 = map_pages(pdf2, entries2)
    if pages2 != pages:
        for k in range(3):
            if pages2 == pages:
                break
            pages = pages2
            html2, entries2 = assemble(vol_id, pages, frags)
            pdf2, _ = print_pdf(html2, os.path.join(OUT_PDF, vol_id + "_p2.pdf"))
            pages2 = map_pages(pdf2, entries2)
    final = os.path.join(OUT_PDF, meta["file"] + ".pdf")
    tmp_final = final + ".tmp.pdf"
    n = stamp(pdf2, tmp_final, meta, entries2, pages2)
    for attempt in range(6):
        try:
            if os.path.exists(final):
                os.remove(final)
            os.replace(tmp_final, final)
            break
        except PermissionError:
            time.sleep(1.5)
    if verbose:
        print(f"[{vol_id}] {meta['title']}: {n} 页, {len(entries2)} 个书签 "
              f"(打印 {dt:.1f}s) -> {os.path.basename(final)}")
    # 清理中间件
    for f in (pdf1, pdf2):
        try:
            os.remove(f)
        except OSError:
            pass
    return final


def merge():
    import pymupdf as fitz
    files = [os.path.join(OUT_PDF, VOLUMES[k]["file"] + ".pdf") for k in VOLUMES]
    files = [f for f in files if os.path.exists(f)]
    if not files:
        raise SystemExit("没有可合并的卷")
    out = fitz.open()
    toc = []
    offset = 0
    for f in files:
        d = fitz.open(f)
        out.insert_pdf(d)
        vol_title = os.path.splitext(os.path.basename(f))[0]
        toc.append([1, vol_title, offset + 1])
        for lvl, title, p in d.get_toc():
            toc.append([lvl + 1, title, p + offset])
        offset += d.page_count
        d.close()
    # 增加"分卷"一级书签
    final = os.path.join(BASE, MERGED_NAME)
    out.set_toc(toc)
    out.set_metadata({"title": "计算机与人工智能系统讲义（全册）",
                      "author": AUTHOR or BRAND,
                      "subject": "ML/DL/DSA/Python/C++/Agent 全体系讲义"})
    out.save(final, garbage=3, deflate=True)
    n = out.page_count
    out.close()
    print(f"[merge] {n} 页 -> {final}")
    return final


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arg == "merge":
        merge()
    elif arg == "all":
        for v in VOLUMES:
            try:
                build_vol(v)
            except Exception as e:
                print(f"[{v}] 失败: {e}")
    else:
        build_vol(arg)
