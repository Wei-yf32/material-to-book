# -*- coding: utf-8 -*-
"""编译 C/C++ 讲义示例、运行、把「命令 + 警告 + 真实输出 + 退出码」写入 out/vol3/*.txt。

与 runcc.py 的区别：多写一个输出文件，且用 -Wall -Wextra -Werror 编译（证明 0 警告）。
用法:
  python runcc_out.py _build/src/vol3/ch04_sort.c              # 输出 out/vol3/ch04_sort.txt
  python runcc_out.py _build/src/vol3/ch04_sort.cpp out/x.txt  # 指定输出路径
"""
import os
import subprocess
import sys
import tempfile

def _find_zig():
    """找 zig：环境变量 ZIG > PATH > pip 包 ziglang 自带。"""
    env = os.environ.get("ZIG")
    if env and os.path.exists(env):
        return env
    w = shutil.which("zig") or shutil.which("zig.exe")
    if w:
        return w
    try:
        import ziglang
        p = os.path.join(os.path.dirname(ziglang.__file__), "zig.exe")
        if os.path.exists(p):
            return p
    except Exception:
        pass
    return "zig"

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)          # _build/
ZIG = _find_zig()


def main() -> int:
    src = os.path.abspath(sys.argv[1])
    name = os.path.splitext(os.path.basename(src))[0]
    rel_out = sys.argv[2] if len(sys.argv) > 2 else os.path.join("out", "vol3", name + ".txt")
    out = rel_out if os.path.isabs(rel_out) else os.path.join(ROOT, rel_out)

    is_cpp = os.path.splitext(src)[1].lower() in (".cpp", ".cc", ".cxx")
    comp = "c++" if is_cpp else "cc"
    std = "c++20" if is_cpp else "c17"
    exe = os.path.join(tempfile.gettempdir(), "yf_" + name + ".exe")
    cmd = [ZIG, comp, "-std=" + std, "-O2", "-Wall", "-Wextra", "-Werror", src, "-o", exe]

    build = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = ["> zig %s -std=%s -O2 -Wall -Wextra -Werror %s -o %s.exe"
             % (comp, std, os.path.basename(src), name)]
    if build.returncode != 0:
        lines.append(build.stdout + build.stderr)
        lines.append("[编译失败，退出码 %d]" % build.returncode)
        open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print("\n".join(lines))
        return 1
    lines.append("（编译器无任何输出 = 0 warning 编译通过）")
    if build.stderr.strip():
        lines.append(build.stderr)

    run = subprocess.run([exe], capture_output=True, text=True, encoding="utf-8",
                         errors="replace", timeout=300, cwd=os.path.dirname(src))
    lines.append("> .\\%s.exe" % name)
    lines.append(run.stdout.rstrip("\n"))
    if run.stderr.strip():
        lines.append("[stderr] " + run.stderr.strip())
    lines.append("[退出码 %d]" % run.returncode)
    try:
        os.remove(exe)
    except OSError:
        pass

    os.makedirs(os.path.dirname(out), exist_ok=True)
    text = "\n".join(lines) + "\n"
    open(out, "w", encoding="utf-8").write(text)
    print(text)
    print("[saved] " + out)
    return 0 if run.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
