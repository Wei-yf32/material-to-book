# -*- coding: utf-8 -*-
"""全书统一的绘图样式工具。所有插图都必须由本脚本体系生成（真实计算数据）。"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

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
FIGDIR = os.path.join(BASE, "_build", "figures")

# 统一的配色（印刷友好、灰度下仍可区分）
C = {
    "blue":   "#2c6e9b",
    "orange": "#c9631f",
    "green":  "#3f7f5a",
    "red":    "#a4382f",
    "purple": "#5c4f9e",
    "gray":   "#6e6e6e",
    "teal":   "#1f7a7a",
    "gold":   "#a8862a",
    "pink":   "#b5506e",
    "light":  "#c9d6df",
}
CYCLE = [C["blue"], C["orange"], C["green"], C["red"], C["purple"],
         C["teal"], C["gold"], C["pink"]]


def setup():
    rcParams.update({
        "font.family": ["Microsoft YaHei", "Noto Sans SC", "SimHei", "DejaVu Sans"],
        "font.sans-serif": ["Microsoft YaHei", "Noto Sans SC", "SimHei"],
        "axes.unicode_minus": False,
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.06,
        "font.size": 10,
        "axes.titlesize": 11.5,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "legend.frameon": False,
        "axes.grid": True,
        "grid.alpha": 0.28,
        "grid.linewidth": 0.6,
        "grid.linestyle": "-",
        "axes.linewidth": 0.8,
        "axes.edgecolor": "#4a4a4a",
        "axes.labelcolor": "#2a2a2a",
        "xtick.color": "#3a3a3a",
        "ytick.color": "#3a3a3a",
        "axes.prop_cycle": matplotlib.cycler(color=CYCLE),
        "svg.fonttype": "path",      # 文字转路径，保证任何机器上显示一致
        "svg.hashsalt": "yufeng",
        "lines.linewidth": 1.8,
        "lines.markersize": 5,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "mathtext.fontset": "cm",
    })


def save(fig, vol, name, png=True):
    """保存 SVG（用于 PDF，矢量清晰）与 PNG（用于快速预览）。"""
    d = os.path.join(FIGDIR, vol)
    os.makedirs(d, exist_ok=True)
    svg = os.path.join(d, name + ".svg")
    fig.savefig(svg)
    if png:
        fig.savefig(os.path.join(d, name + ".png"), dpi=220)
    plt.close(fig)
    return svg


def fig(w=6.4, h=3.6, nrows=1, ncols=1, **kw):
    return plt.figure(figsize=(w, h), **kw)
