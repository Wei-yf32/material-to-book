# -*- coding: utf-8 -*-
r"""把 HTML 里 LaTeX 公式中的裸 `<` 转义成 `&lt;`（浏览器会把 `<j}` 当成标签开头）。

做法：状态机跟踪 \( \) \[ \] 数学模式；数学模式里遇到 `<` 只有当后面的名字
不属于已知 HTML 标签时才转义，否则认为定界符不平衡、退出数学模式（避免破坏正文标签）。
用法：
  python _build/tools/fix_lt.py vol4 vol5            # 只报告
  python _build/tools/fix_lt.py vol4 vol5 --apply    # 写回
"""
import glob, os, re, sys

TAGS = set("""a b br code dd div dl dt em figcaption figure h1 h2 h3 h4 h5 h6 i img
li ol p pre span strong sub sup table tbody td th thead tr ul script style svg path g
text tspan math mi mo mn mrow defs use rect line circle polygon polyline title desc
blockquote section article header footer nav label input button form option select""".split())
TAGNAME = re.compile(r'</?([a-zA-Z][a-zA-Z0-9]*)')


def process(text):
    out = []
    i, n = 0, len(text)
    in_math = False
    fixes = []
    while i < n:
        ch = text[i]
        if not in_math:
            if text.startswith('\\(', i) or text.startswith('\\[', i):
                in_math = True
                out.append(text[i:i + 2])
                i += 2
                continue
            out.append(ch)
            i += 1
            continue
        # 在数学模式里
        if text.startswith('\\)', i) or text.startswith('\\]', i):
            in_math = False
            out.append(text[i:i + 2])
            i += 2
            continue
        if ch == '<':
            m = TAGNAME.match(text, i)
            if m and m.group(1).lower() in TAGS and m.end() < n and text[m.end()] in '>/ \t\n\r':
                # 确实是 HTML 标签 → 定界符不平衡，退出数学模式，原样保留
                in_math = False
                out.append(ch)
                i += 1
                continue
            fixes.append((text[max(0, i - 30):i + 30].replace('\n', ' '), text[i:i + 12]))
            out.append('&lt;')
            i += 1
            continue
        out.append(ch)
        i += 1
    return ''.join(out), fixes


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    apply = '--apply' in sys.argv
    vols = args or ['vol4', 'vol5']
    total = 0
    for vol in vols:
        for f in sorted(glob.glob(os.path.join('_build', 'vol', vol, '*.html'))):
            if os.path.basename(f).startswith('_'):
                continue
            t = open(f, encoding='utf-8', errors='replace').read()
            new, fixes = process(t)
            if fixes:
                total += len(fixes)
                print(f'\n{vol}/{os.path.basename(f)}: {len(fixes)} 处')
                seen = set()
                for ctx, frag in fixes:
                    if frag in seen:
                        continue
                    seen.add(frag)
                    print(f'    …{ctx}…')
                if apply:
                    open(f, 'w', encoding='utf-8').write(new)
    print(f'\n合计 {total} 处' + ('（已写回）' if apply else '（只报告）'))


if __name__ == '__main__':
    main()
