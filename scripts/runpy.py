# -*- coding: utf-8 -*-
"""
运行一段示例代码并把真实输出存盘，供讲义 INCLUDE-OUTPUT 引用。
用法:
  python runpy.py <脚本路径> [输出名]
脚本用构建用 Python 执行（matplotlib/numpy/sklearn 已安装），
工作目录 = 脚本所在目录，保证相对路径可读数据。
"""
import os, sys, subprocess, io

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

PY = sys.executable
BUILD = os.path.join(_find_root(), "_build")


def main():
    script = os.path.abspath(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(os.path.basename(script))[0]
    rel = os.path.relpath(script, BUILD).replace(os.sep, "/")
    vol = rel.split("/")[1] if rel.startswith("src/") else "misc"
    outdir = os.path.join(BUILD, "out", vol)
    os.makedirs(outdir, exist_ok=True)
    outfile = os.path.join(outdir, name + ".txt")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", MPLBACKEND="Agg")
    r = subprocess.run([PY, script], capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       cwd=os.path.dirname(script), env=env, timeout=1800)
    body = (r.stdout or "")
    if r.stderr.strip():
        body += "\n[stderr]\n" + r.stderr.strip()
    with io.open(outfile, "w", encoding="utf-8", newline="\n") as f:
        f.write(body.rstrip() + "\n")
    print(body.rstrip()[-4000:])
    print(f"\n[saved] _build/out/{vol}/{name}.txt  exit={r.returncode}")
    return 0 if r.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
