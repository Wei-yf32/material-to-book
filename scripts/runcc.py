# -*- coding: utf-8 -*-
"""
用 ziglang 自带的 C/C++ 编译器编译并运行示例，验证书中的所有 C / C++ 代码。
用法:
  python runcc.py file.c            # 编译运行 C
  python runcc.py file.cpp          # 编译运行 C++
  python runcc.py file.cpp --keep   # 保留 exe
输出: 打印编译器诊断 + 程序 stdout/stderr。
"""
import os, sys, subprocess, tempfile, shutil

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

ZIG = _find_zig()
CACHE = os.path.join(tempfile.gettempdir(), "yf_zig_cache")
os.makedirs(CACHE, exist_ok=True)


def compile_run(src, keep=False, args=None, timeout=120):
    src = os.path.abspath(src)
    ext = os.path.splitext(src)[1].lower()
    is_cpp = ext in (".cpp", ".cc", ".cxx", ".hpp")
    compiler = "c++" if is_cpp else "cc"
    exe = os.path.join(os.path.dirname(src), "_" + os.path.splitext(os.path.basename(src))[0] + ".exe")
    cmd = [ZIG, compiler, "-O2", "-w", "-std=" + ("c++20" if is_cpp else "c17"),
           src, "-o", exe]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return {"ok": False, "stage": "compile", "stdout": r.stdout, "stderr": r.stderr}
    run = subprocess.run([exe] + (args or []), capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=timeout, cwd=os.path.dirname(src))
    if not keep:
        try:
            os.remove(exe)
        except OSError:
            pass
    return {"ok": run.returncode == 0, "stage": "run", "stdout": run.stdout,
            "stderr": run.stderr, "code": run.returncode}


if __name__ == "__main__":
    path = sys.argv[1]
    keep = "--keep" in sys.argv
    res = compile_run(path, keep=keep)
    print("=" * 60)
    print("COMPILE/RUN:", path, "OK" if res["ok"] else "FAIL")
    print("=" * 60)
    if res["stdout"]:
        print("--- stdout ---")
        print(res["stdout"])
    if res["stderr"]:
        print("--- stderr ---")
        print(res["stderr"])
    sys.exit(0 if res["ok"] else 1)
