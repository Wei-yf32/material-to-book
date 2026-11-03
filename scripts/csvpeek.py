#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""csvpeek.py —— 把一个 CSV 的“人眼可读摘要”打印成文本，供讲义 INCLUDE-OUTPUT。

用法：
    python _build/tools/csvpeek.py <csv路径> [--rows 10] [--out out/vol4/xxx.txt]
                                   [--parse-dates] [--top 6]

输出内容：
  1) 形状（行数 × 列数）与内存占用
  2) 每列的类型、缺失数、取值个数、样例值
  3) 前 N 行原样（等宽对齐，便于在纸上观察）
  4) 数值列的五数概括（count/mean/std/min/25%/50%/75%/max）
  5) 指定列的取值分布（用于二分类标签/类别特征）
"""
import argparse
import io
import os
import sys

import pandas as pd

import unicodedata


def _w(s):
    """字符串在等宽字体里的显示宽度（中文算 2）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in str(s))


def _pad(s, width):
    return str(s) + " " * max(0, width - _w(s))




def fmt_table(df, max_rows=None):
    d = df.head(max_rows) if max_rows else df
    s = d.to_string(index=False, na_rep="NaN")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--rows", type=int, default=10)
    ap.add_argument("--head-cols", type=int, default=0)
    ap.add_argument("--out", default="")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--sep", default=",")
    ap.add_argument("--encoding", default="utf-8")
    a = ap.parse_args()

    df = pd.read_csv(a.csv, sep=a.sep, encoding=a.encoding, nrows=200000)
    lines = []
    w = lines.append

    w(f"文件：{os.path.basename(a.csv)}")
    w(f"形状：{df.shape[0]} 行 × {df.shape[1]} 列；内存 {df.memory_usage(deep=True).sum() / 1048576:.1f} MB")
    w("")
    w("== 每一列长什么样（column 列名 / dtype 类型 / missing 缺失数 / uniq 不同取值数 / first_value 第一个非空值）==")
    rows = []
    for c in df.columns:
        s = df[c]
        nun = s.nunique(dropna=True)
        sample = s.dropna().iloc[0] if s.notna().any() else "NaN"
        rows.append([c, str(s.dtype), str(s.isna().sum()), str(nun), str(sample)[:24]])
    hdr = ["column", "dtype", "missing", "uniq", "first_value"]
    wd = [max(_w(h), *(_w(r[i]) for r in rows)) for i, h in enumerate(hdr)]
    w("  ".join(_pad(hdr[i], wd[i]) for i in range(len(hdr))))
    w("  ".join("-" * wd[i] for i in range(len(hdr))))
    for r in rows:
        w("  ".join(_pad(r[i], wd[i]) for i in range(len(hdr))))
    w("")
    head = df if not a.head_cols else df.iloc[:, : a.head_cols]
    extra = "" if not a.head_cols else f"（只取前 {a.head_cols} 列，共 {df.shape[1]} 列）"
    w(f"== 前 {a.rows} 行原样{extra} ==")
    w(fmt_table(head, a.rows))
    w("")

    num = df.select_dtypes("number")
    if len(num.columns):
        w("== 数值列的五数概括 ==")
        desc = num.describe().T
        w(desc.to_string(float_format=lambda x: f"{x:.4g}"))
        w("")

    # 低基数列（≤ 12 个取值）给分布，通常是标签或类别特征
    for c in df.columns:
        if df[c].nunique(dropna=True) <= 12 and df[c].nunique(dropna=True) > 1:
            vc = df[c].value_counts(dropna=False)
            w(f"== 列 {c} 的取值分布（{df[c].nunique()} 个取值）==")
            kw = max(8, *(_w(k) for k in vc.index))
            for k, v in vc.items():
                w(f"  {_pad(k, kw)} {v:>7}   {v / len(df) * 100:5.1f}%")
            w("")
            if sum(1 for _ in range(1)) and len(lines) > 200:
                break

    text = "\n".join(lines).rstrip() + "\n"
    if a.out:
        out = a.out if os.path.isabs(a.out) else os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), a.out.replace("/", os.sep)
        )
        os.makedirs(os.path.dirname(out), exist_ok=True)
        io.open(out, "w", encoding="utf-8", newline="\n").write(text)
        print(f"[saved] {out}  ({len(text.splitlines())} 行)")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
