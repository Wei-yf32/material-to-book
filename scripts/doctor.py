#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""doctor.py —— 体检这台机器能不能跑 material-to-book。

作用
    逐项检查解释器版本、依赖库、浏览器、中文字体、脚本完整性，打印一张表，
    并给出缺什么、怎么补。安装完先跑这个，比等到构建到一半报错省事。

参数
    --json     以 JSON 输出（供 CI 或安装脚本解析）
    --strict   有任一"必需"项不通过时返回 1（默认只在致命项缺失时返回 1）

返回
    0  必需项齐全；1  有必需项缺失

关键实现
    只做只读检查，不改环境、不联网。浏览器检查用真实路径 + 一次 --version，
    避免"装了但 PATH 里没有"的误判。

边界情况
    系统 python 可能没有 pip（甚至没有 pymupdf），这不代表 skill 坏了——
    换一个装了依赖的解释器跑即可，doctor 会把当前解释器的路径打出来。
"""

import argparse
import glob
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REQUIRED = ["pymupdf", "matplotlib", "numpy", "pandas", "pygments"]
OPTIONAL = ["PIL", "docx", "pptx", "openpyxl"]
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/microsoft-edge",
    "/usr/bin/google-chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]
FONTS = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]


def check_python():
    v = sys.version_info
    ok = (v.major, v.minor) >= (3, 9)
    return ok, "%d.%d.%d @ %s" % (v.major, v.minor, v.micro, sys.executable)


def check_modules(names):
    rows = []
    for name in names:
        try:
            mod = __import__(name)
            ver = getattr(mod, "__version__", "")
            rows.append((name, True, str(ver)))
        except Exception:
            rows.append((name, False, "未安装"))
    return rows


def check_browsers():
    for path in BROWSERS:
        if os.path.exists(path):
            try:
                out = subprocess.run([path, "--version"], capture_output=True,
                                     timeout=15, text=True).stdout.strip()
            except Exception:
                out = ""
            return path, out or "(已找到，版本未知)"
    return None, "未找到 Edge / Chrome"


def check_fonts():
    hit = [p for p in FONTS if os.path.exists(p)]
    return hit


def check_scripts(root):
    scripts = sorted(glob.glob(os.path.join(root, "scripts", "*.py")))
    bad = []
    for p in scripts:
        try:
            src = open(p, encoding="utf-8").read()
            compile(src, p, "exec")
        except SyntaxError as e:
            bad.append("%s: %s" % (os.path.basename(p), e))
    return len(scripts), bad


def check_skill(root):
    sk = os.path.join(root, "SKILL.md")
    if not os.path.exists(sk):
        return False, "缺 SKILL.md"
    head = open(sk, encoding="utf-8").read(400)
    has = ("name:" in head) and ("description:" in head)
    refs = glob.glob(os.path.join(root, "references", "*.md"))
    return has, "frontmatter %s；references %d 份" % ("正常" if has else "缺字段", len(refs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    py_ok, py_desc = check_python()
    mods_req = check_modules(REQUIRED)
    mods_opt = check_modules(OPTIONAL)
    browser, bver = check_browsers()
    fonts = check_fonts()
    n_scripts, bad_scripts = check_scripts(root)
    sk_ok, sk_desc = check_skill(root)

    missing = [n for n, ok, _ in mods_req if not ok]
    fatal = (not py_ok) or bool(missing) or (browser is None) or (not sk_ok)

    result = {
        "root": root,
        "python": {"ok": py_ok, "desc": py_desc},
        "modules_required": {n: {"ok": ok, "version": v} for n, ok, v in mods_req},
        "modules_optional": {n: {"ok": ok, "version": v} for n, ok, v in mods_opt},
        "browser": {"path": browser, "version": bver},
        "fonts": fonts,
        "scripts": {"count": n_scripts, "errors": bad_scripts},
        "skill": {"ok": sk_ok, "desc": sk_desc},
        "fatal": fatal,
    }

    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        line = "-" * 66
        print("material-to-book · 环境体检")
        print(line)
        print("%-18s %s  %s" % ("解释器", "OK " if py_ok else "!! ", py_desc))
        print("%-18s %s  %s" % ("SKILL.md", "OK " if sk_ok else "!! ", sk_desc))
        print("%-18s %s  %s" % ("章节脚本", "OK " if not bad_scripts else "!! ",
                                "%d 个%s" % (n_scripts, "" if not bad_scripts else "，%d 个语法错" % len(bad_scripts))))
        print("%-18s %s  %s" % ("浏览器", "OK " if browser else "!! ", browser or bver))
        print("%-18s %s  %d 个" % ("中文字体", "OK " if fonts else "!! ", len(fonts)))
        print(line)
        print("必需库：")
        for n, ok, v in mods_req:
            print("   %-12s %s %s" % (n, "OK " if ok else "!! ", v))
        if any(not ok for _, ok, _ in mods_opt):
            print("可选库（缺了不影响出 PDF）：")
            for n, ok, v in mods_opt:
                if not ok:
                    print("   %-12s -- %s" % (n, v))
        print(line)
        if fatal:
            print("结论：还差东西。")
            if missing:
                print("  缺库：%s" % ", ".join(missing))
                print("  补装：\"%s\" -m pip install %s" % (sys.executable, " ".join(missing)))
            if browser is None:
                print("  浏览器：装 Edge 或 Chrome，或把路径写进 book.json 的 edge 字段")
            if not py_ok:
                print("  Python：需要 3.9+")
        else:
            print("结论：可以开工。下一步：python scripts/intake.py \"<资料夹>\"")
        if bad_scripts:
            print("脚本语法错：")
            for b in bad_scripts:
                print("  " + b)

    return 1 if fatal else 0


if __name__ == "__main__":
    sys.exit(main())
