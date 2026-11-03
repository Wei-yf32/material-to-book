#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一键收尾：重排各卷章号 → 全量构建 → 合订成总册。

用法：
    python _build/tools/finalize.py            # 只体检 + 重排预览，不构建
    python _build/tools/finalize.py --apply    # 重排 + 构建 + 合订
    python _build/tools/finalize.py --apply --skip-renumber

流程：
 1. 对每卷调用 renumber 的规划逻辑，报告会改哪些章号；
 2. --apply 时真正重排文件与正文引用；
 3. 调 build.build_vol 逐卷出 PDF；
 4. 调 build.merge 合订成 _build 根目录下的总册 PDF。
"""
import os
import subprocess
import sys
import time

BUILD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BUILD)
sys.path.insert(0, os.path.join(BUILD, "tools"))
import build as B  # noqa: E402
import renumber as R  # noqa: E402

PY = sys.executable


def run(cmd, quiet=False):
    t = time.time()
    p = subprocess.run(cmd, cwd=BUILD, capture_output=True)
    out = (p.stdout or b"").decode("utf-8", "replace")
    err = (p.stderr or b"").decode("utf-8", "replace")
    if not quiet:
        print(out.strip())
        if err.strip():
            print(err.strip()[:2000])
    return p.returncode, out, err, time.time() - t


def main():
    apply_ = "--apply" in sys.argv
    skip_ren = "--skip-renumber" in sys.argv

    print("=" * 64)
    print("第 1 步 / 章号体检")
    print("=" * 64)
    need = []
    for vol in B.VOLUMES:
        d, files, mapping = R.plan(vol)
        if not files:
            print(f"  {vol}: （还没有章节）")
            continue
        olds = sorted(mapping)
        ok = olds == list(range(1, len(olds) + 1))
        print(f"  {vol}: {len(files)} 章 {'已连续' if ok else '需要重排 ' + str(olds)}")
        if not ok:
            need.append(vol)

    if apply_ and not skip_ren:
        print("\n第 2 步 / 执行重排")
        for vol in need:
            rc, out, err, _ = run([PY, os.path.join(BUILD, "tools", "renumber.py"), vol, "--apply"])
    elif apply_:
        print("\n第 2 步 / 跳过重排（--skip-renumber）")

    if not apply_:
        print("\n（体检模式；加 --apply 执行重排与构建）")
        return

    print("\n" + "=" * 64)
    print("第 3 步 / 逐卷构建")
    print("=" * 64)
    rows = []
    for vol in B.VOLUMES:
        d = os.path.join(BUILD, "vol", vol)
        if not os.path.isdir(d) or not [f for f in os.listdir(d) if not f.startswith("_")]:
            print(f"  {vol}: 跳过（无内容）")
            continue
        try:
            t = time.time()
            B.build_vol(vol)
            rows.append(vol)
        except Exception as e:
            print(f"  {vol} 失败: {e}")

    print("\n" + "=" * 64)
    print("第 4 步 / 合订")
    print("=" * 64)
    final = B.merge()
    print(f"\n总册: {final}")
    try:
        import pymupdf
        d = pymupdf.open(final)
        print(f"页数: {d.page_count}　书签: {len(d.get_toc())}")
    except Exception as e:
        print("（无法读取总册统计）", e)


if __name__ == "__main__":
    main()
