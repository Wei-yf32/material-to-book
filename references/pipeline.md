# 构建流水线细节

## 目录布局（项目内）

```
<项目>/
├── _build/
│   ├── book.json          # 唯一入口配置
│   ├── tools/             # 本 skill 的脚本副本
│   ├── css/book.css       # 排版（A4 页面、页眉页脚、代码/树/数据块）
│   ├── vol/<vol>/NN_标题.html   # 章节片段（_ 开头的文件被忽略）
│   ├── src/<vol>/*.py|*.c|*.cpp # 可运行源码（INCLUDE-CODE 引用）
│   ├── src/figs/*.py      # 出图脚本
│   ├── out/<vol>/*.txt    # 脚本真实输出（INCLUDE-OUTPUT 引用）
│   ├── figures/<vol>/*.svg|png  # 由脚本生成
│   ├── text/              # extract_sources 抽取的原文
│   ├── cw/<pdf名>/pNNNN.png     # 原始课件页渲染（读图 + 影印）
│   ├── html/ pdf/ preview/      # 中间产物
│   └── backup/            # 改版前备份
└── <书名>.pdf             # 合订产物
```

## book.json

```json
{
  "title": "书名",
  "output": "书名.pdf",
  "edge": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "volumes": {
    "vol0": {"title": "总导论与学习路线", "file": "00_总导论",
             "subtitle": "全书结构 · 知识地图 · 零基础阅读指南",
             "points": ["封面要点 1", "封面要点 2"]},
    "vol1": {"title": "Python 编程与科学计算", "file": "01_Python编程与科学计算",
             "subtitle": "语言基础 · 面向对象 · NumPy · pandas",
             "points": ["..."]}
  }
}
```

可选品牌字段（都可以删，删了用默认值）：

| 字段 | 出现在哪 |
|---|---|
| `brand` | 封面顶部横条左侧、页眉右侧 |
| `org` / `edition` | 封面右上角两行小字（学校/院系、版本名） |
| `kicker` | 封面上的英文小字（如 `COMPUTING & ARTIFICIAL INTELLIGENCE`） |
| `author` | PDF 元数据作者 |
| `meta_lines` | 封面底部说明，字符串数组，每项一行 |

- `file` 决定分卷 PDF 名：`_build/pdf/<file>.pdf`。
- 卷序按 `vol0, vol1, ...` 字符串排序，务必用两位数以上的编号。
- `points` 是封面中部的两栏要点（6~8 条，每条 ≤ 22 字）。

## 章节片段能用的东西

| 写法 | 结果 |
|---|---|
| `<!--INCLUDE-CODE path=src/vol4/ch12_id3.py lang=py-->` | 代码高亮 + 顶部文件条 `src/vol4/ch12_id3.py` |
| `<!--INCLUDE-OUTPUT path=out/vol4/ch12_id3.txt-->` | 深色「运行输出」块 |
| `<!--INCLUDE-TREE path=src/vol4/tree_3B.txt-->` | 彩色树状图（目录/脚本/数据/输出/注释五色） |
| `<!--INCLUDE-DATA path=out/vol4/csv_lol.txt-->` | 浅色「数据速览」块 |
| `<figure class="cwpage"><img src="../../figures/cw/ML5_p004.jpg" class="w88"><figcaption>…</figcaption></figure>` | 原始课件页影印 |
| `<div class="box note|warn|key|lab|paper">` | 五种提示框 |
| `<dl class="terms">` | 名词解释双列块（v5 之后代码解释不再用它） |
| `<ol class="steps">` | 带圆形编号的步骤列表 |
| `<pre class="tree">` / `<pre class="data">` | 由构建器生成，正文不要手写 |

图片宽类：`w45 w50 … w95`（5% 步长）。表格用 `<thead>`（跨页自动重复表头）。

## 两遍法（目录页码）

1. `mark_headings()`：每个 `<h1>`/`<h2>` 内注入白色 0.4pt 的唯一标记 `ZZQ{k}ZZ`。
2. 第一遍打印（页码占位）。
3. `map_pages()`：用 PyMuPDF 搜 `ZZQ{k}ZZ`，得到每个标题的真实页码。
4. 第二遍把页码填进目录，再打印；`assemble()` 里 `assert` 标记数与条目数一致。

要点：**永远不要用标题文字定位**——目录页本身就含全部标题文字，会出现"页码指向目录页"的经典错误。

## 页眉页脚与书签

`stamp()`：

- 页眉：左 = 卷名（microsoft yahei 7.6pt），右 = 书名（右对齐 7.2pt），下方 0.5pt 灰线。
- 页脚：`— N —` 居中。
- 书签：`doc.set_toc([[level, title, page], ...])`，h1=1，h2=2；合订时每卷插一条一级书签并把卷内层级 +1。
- 元数据：`doc.set_metadata({...})`。

字体必须用 `fontfile=r"C:\Windows\Fonts\msyh.ttc", fontname="msyh"`，否则 PyMuPDF 内置 `china-ss` 会把英文渲染成等宽（"P y t h o n"）。

## Windows 上的打印锁

Edge 打印后会延迟释放输出文件，导致 `PermissionError: [WinError 32]`。对策（已在 build.py 里）：

- 输出 PDF 名带毫秒时间戳；
- `--user-data-dir` 也带时间戳，避免多个实例抢配置目录；
- 写 `.tmp.pdf` 后 `os.replace`，失败重试 6 次，每次 `time.sleep(0.7)`；
- 合订文件被阅读器占用时，先写 `_build/pdf/full_new.pdf`，再尝试替换；仍失败就另存为 `..._第N版.pdf` 并告知用户。

## 快照一致性

`build_vol()` 开头 `frags = collect(vol_id)` 只取一次片段快照，三遍构建都传 `frags`。否则子代理正在写文件时，两遍之间标题数量变化会让目录页码错位（`IndexError`）。

## 合订

```python
out = fitz.open()
for vol in volumes:
    src = fitz.open(pdf_path)
    offset = out.page_count
    out.insert_pdf(src)
    for lvl, title, page in src.get_toc():
        out.set_toc(...)  # 需要自行累积，逐条 append
```

`verify_book.py` 检查：越界文本块、近空白页、一级书签是否为卷名、卷起始页是否连续。

## 时长参考

- 单卷 600 页：打印 70~90 s（4 万~5 万字纯文本 + 300 图）。
- 合订 2252 页：约 40 s（不含打印）。
- 全书从零到交付（24 章、72 实验、12 子代理）：约 3 天（含多轮返工）。
