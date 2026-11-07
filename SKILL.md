---
name: material-to-book
description: Turn a folder of heterogeneous materials (course slides, lecture PDFs, notebooks, source code, CSV/datasets, old notes) into one deeply-integrated, typeset deliverable — by default a multi-volume PDF book with covers, TOC, bookmarks, real figures and run-verified code; can also emit DOCX reports, PPT decks, single-file HTML or Markdown. Use when the user says "把这堆资料整理成一份讲义/手册/汇总", "合并这些课件", "生成一份教学文档", "把实验代码讲清楚", or hands over a course/材料 folder and wants a teaching-quality document rather than a summary.
whenToUse: 用户给了一个装着课件 PDF / 代码 / notebook / 数据集的文件夹，要求合并、深化、扩写成一份能读、能复现、能教学的文档（讲义、手册、白皮书、实验指导书）。也适用于把已有长文档升级成"可复现 + 有实验 + 有图"的版本。
metadata:
  version: "2.0"
  author: "wyf"
  language: "zh-CN"
---

# 资料 → 讲义（material-to-book）

把一个资料夹变成一本**能读、能跑、能对照**的书。核心不是"总结"，而是**重建**：把散在 30 个 PDF、几十个脚本、若干 notebook 里的知识，按学科逻辑重排成一份有先修关系、有实验、有真实数字、有图的教材，并把原始材料里的每一页都在新书里有归属。

## 第一件事：先访谈（阶段 −1）

**不要一上来就读材料、排章节。**先花十分钟把四件事问清楚：哪份是主线、按什么顺序讲、写到多深、给谁看。这四件事猜错的代价是整本返工（真实项目里 848 页的详版→324 页→250 页，两次大改都源于方向猜错）。

```bash
python scripts/intake.py "D:\课程资料"        # 扫出文件角色表 + 打印访谈卡 + 写 _build/intake.json 草案
# 答完访谈、改好 json 之后：
python scripts/intake.py "D:\课程资料" --apply   # 合并进 _build/book.json 的 intake 段
```

十四问的完整问法、选项、默认值、派生参数、矛盾检查见 `references/intake.md`；访谈卡可直接整段发给用户。

## 何时用

- 用户给一个文件夹（课件、讲义、实验代码、notebook、数据集），要"汇总成一份讲义/手册/教程"。
- 用户嫌材料"讲得不透、代码看不懂、实验不知道为什么做"，要深化。
- 用户要把内部资料整理成可对外/可培训的文档（DOCX/PPT/PDF）。
- 用户要的是一份**能照着学、照着做**的东西，而不是目录式摘要。

不适用：只要一页摘要、只要摘录原文、只要格式转换（那用 pandoc/office 技能）。

## 先想清楚：交付什么"类型"

默认产物是 **多卷 PDF 书**（本 skill 的构建链就是为它写的）。用户没指定时按这个做；指定了就走对应分支，但**内容规范（下面第 3 节）全部通用**。

| 类型 | 何时选 | 落地方式 |
|---|---|---|
| 多卷 PDF 书（默认） | 材料 ≥ 20 页、章节 ≥ 6、要长期读 | 本 skill 的 `scripts/build.py`：HTML 片段 → Edge 无头打印 PDF → PyMuPDF 回填页码/书签/页眉页脚 → 合订 |
| 单文件 HTML | 要交互（折叠、搜索、公式、动画）、发链接即可 | 同一套 HTML 片段，去掉分页 CSS，加侧边导航 |
| DOCX 报告 | 单位要求 Word、要批注修订 | 内容写 Markdown → `office-docx` 技能生成；图用脚本出 PNG 再嵌入 |
| PPT 讲义 | 要讲、要投屏 | 每章提炼成 10~20 页 → `dsh-ppt` 技能；PPT 只放结论与图，细节留在 PDF |
| Markdown 仓库 | 要进 Git、要被检索 | 直接写 `docs/NN_标题.md`，代码用相对路径引用，图放 `assets/` |

一条硬规则：**内容只写一遍**。正文写在 HTML/Markdown 里，其它格式都由它派生；不要为 PPT 另写一套说法，否则两版会打架。

## 内容规范（所有类型都必须满足）

这些是用户在真实项目里逐条提过的要求，做成清单逐项验收：

1. **不是搬运，是重建**：原始材料只取"关键图、关键逻辑、关键数字"；每章按 `动机 → 直觉 → 形式化 → 代码 → 实验 → 常见错误 → 小结` 组织。
2. **深度四层**：先用生活类比讲清"它在解决什么"，再给定义/公式，再给**真实数字**（自己跑出来的），最后讲边界与失效条件。只讲前两层＝不合格。
3. **每个数字都能追**：正文里的每个统计量、指标、耗时，要么由书里的脚本跑出来（贴真实输出），要么来自材料并注明出处。**禁止估算、禁止编造**。
4. **每个实验都能复现**：目标 / 要求 / 文件结构 / 阅读顺序 / 数据长什么样 / 逐段讲代码 / 运行输出怎么读 / 动手改一改。缺一节＝不合格。
5. **函数说明写在代码里**：`def`/`class` 上方必须是多行注释（docstring），写清"作用 / 参数（是什么、取什么值）/ 返回 / 关键实现 / 边界情况"。正文不再单列"函数卡片"。
6. **代码整份贴出并逐段讲**：代码块顶部标出来源文件路径（像 IDE 的标签），块前 1~2 句导语，块后按 5~15 行一组讲"为什么这么写"。不要用表格罗列"xx.py 做什么"。
7. **图上不放截图凑数**：数据图必须由脚本从真实数据生成（matplotlib，文字转 path 避免字体缺失），图注写清数据来源与脚本路径。**例外**：用户明确要求"把原资料那页贴过来"时，按页影印原页（每章 ≤16 张），并注明文件名与总页数。
8. **覆盖表**：每章末尾一张表，把原始材料的每一页/每一节映射到"本书哪一节、怎么处理（复述/改写/重绘/新增/合并/无内容）"。**不允许出现"不采纳"**——不用就写"无内容（封面/分隔页）"并给理由。
9. **课件/资料指路句要清掉**："课件第 4 页讲了……"改成用内容作主语直接讲；页码只保留在影印图注和覆盖表里。
10. **去 AI 味**：禁用"首先/其次/综上所述/值得注意的是/众所周知/不难发现/让我们"，一段不超过 4 句，少用"我们看到"。
11. **术语首次出现给英文**，符号首次出现给含义；公式统一 `\( \)` / `\[ \]`（HTML 链）或 `$ $`（Markdown 链），公式里的 `<` 必须转义成 `&lt;`。
12. **只增不减**（改版阶段）：不允许为了"好看"删掉用户已有的内容；确需删（重复段落）要在交付说明里写清楚删了什么、为什么。

13. **前沿知识自己重述**：每章至少一处 2020 年后的新进展（论文/工程实践），用自己的话讲清"它解决了什么旧问题"，给 arXiv/DOI 链接；不要整段翻译摘要。

14. **读图不只读文字**：原资料的示例图要看清图型、轴与单位、刻度范围、图例、拐点/极值、高亮线与图中标注，然后用 3~6 句话写"这张图在说什么、支持哪个结论"。

15. **导入、例子、回顾三件套**：章首要有导入（原资料的开场素材 + 一个当代例子），正文要有 worked example（原表逐行抄、每步中间值），章末要有回顾块（原资料小结逐条抄 + 本书额外补了什么）。

16. **面向工科学习与工程落地**：不绑定具体专业。数学给到「能算」的程度，重点补工程侧——复杂度、内存、数据规模、部署与延迟、失败模式与代价；至少一章用一个「能上岗」的完整案例（从数据到指标到上线约束）走通一遍。

17. **标题先沿用原书，再补一句**：标题要同时做到"能被检索"和"能预告内容"。原书标题通常已经做到了第一条（老师、考纲、真题都用它），所以**默认不改**。只对"名字对、但读者看不出里面讲什么"的节动手，且优先加副标题（`对数函数：多值从哪一步冒出来`）而不是换掉原名。换掉原名词的节不超过全章三成；原书或考纲用过的名词必须出现在标题或副标题里；"三件事、两个数、一次跳变"这类只有钩子没有名词的标题一律不用。

> 40+ 条要求的逐条对照表（带验收动作）在 `references/requirements.md`，交付前逐行过一遍。

## 工作流

### 阶段 −1 · 访谈（十分钟，省一次返工）

要问的只有四类：

| 类 | 必须问到的 | 默认值 |
|---|---|---|
| 材料 | 哪份是**主线**（骨架）；哪些是扩展、参考、不用 | 最厚那份；旧 AI 汇总一律"参考" |
| 主线 | 章序按教材／考点／项目／概念地图；覆盖到多细（定义定理、例题、证明、习题四项分别定） | 教材顺序；定义定理全含，例题与证明含主体，习题全含 |
| 写法 | 体例（教材体／讲义体／手册体）、语气、重点标记方式、要不要"应用"节、标题策略 | 教材体＋讲课腔；应用节走完整流程；标题沿用原书 |
| 交付 | 代码与工程案例档位（0–3）、篇幅、形态、验收口径 | 按学科查 `references/intake.md` 的矩阵 |

三条纪律：

1. **一次问完**，标 ★ 的只留三四项，其余给默认值，允许用户说"按默认"。
2. **先扫再问**：空手问用户答不出，先给一张"文件 / 页数 / 文字层 / 信号 / 判断"的表，让他改判断而不是从零描述。
3. **答完复述**：一句话把结论重复给用户（"主线是 A，教辅是 B 和 C，按教材顺序，电子专业，不放代码"），改一个字比改一本书便宜。

访谈结果写进 `_build/intake.json`，再由 `book.json.intake` 引用。**写作开始后改体例＝重排全书**，所以体例这一项必须在动笔前定死。

### 阶段 0 · 侦察（不要跳过）

先把资料摸清，写一份 `_build/INVENTORY.md`：

- 目录树 + 文件数 + 体积；哪些是原始材料、哪些是别人（或 AI）生成的旧汇总（旧汇总**不要参考**，只会拉低质量）。
- 每个 PDF：页数、是否有文字层（用 PyMuPDF `get_text()` 抽样判断；很多课件是扫描/图片版，文字层为空，只能渲染成图读）。
- 每个 notebook：能否解析（损坏的 ipynb 常见），有没有内嵌输出。
- 每个数据集：行数、列数、体积、标签分布。
- 每个代码文件：语言、能否在本机跑（依赖是否可用：torch? GPU? 网络?）。

工具：`scripts/extract_sources.py`（PDF→文本、ipynb→py）、`scripts/pgs.py`（PDF 指定页→PNG 供人眼读图）、`scripts/csvpeek.py`（CSV 体检）。

### 阶段 1 · 抽取

```bash
python _build/tools/extract_sources.py pdf   # _build/text/<tag>.txt，每页带 ===== [pN] ===== 标记
python _build/tools/extract_sources.py nb    # _build/code/*.py，含 CELL 标记与真实输出
```

规则：**文字层 ≠ 内容**。公式、表格、图几乎都在图片里，必须 `pgs.py` 渲染 + 逐页看图。这一步的产出决定了后面覆盖表能不能做全。

### 阶段 2 · 规划

写 `_build/PLAN.md`：卷 → 章 → 每章页数预算 → 每章对应的原始材料页范围 → 先修关系图。

- 卷按**学科板块**分（如 Python / C++ / 数据结构 / 机器学习 / 深度学习 / Agent），不要按"文件顺序"分。
- 每章 15k~35k 汉字（约 40~70 页 PDF），低于 8k 的章基本是"搬运"。
- 给每章指定"原始材料页范围"，这是后面覆盖表的验收依据。
- 画一张先修关系图（matplotlib 方块+箭头），放在总导论里。

### 阶段 3 · 规范先行

在写正文前，先落两份文件 + 一个样板章：

1. `_build/STYLE_GUIDE.md`：读者画像、章节骨架、允许的 HTML/CSS 类、代码/图/表/提示框模板、退稿原因清单。
2. `_build/REVISION_SPEC.md`：本轮改版的硬约束（实验八节、docstring 四段、覆盖表、字数下限、自检命令、回报格式）。
3. `_build/EXAMPLE.html`：**一个完整样板章**（2000~3000 字，含真实数据表、两张真实图、一段可跑代码、逐函数讲解）。子代理照它写，比一万字规范有用。

### 阶段 4 · 并行写作（子代理）

一章一个子代理，**给足上下文但划清边界**。模板见 `references/prompts.md`。每份 prompt 必须含：

- 读者画像（零基础本科生/工程师）与本章在体系中的位置；
- 本章要覆盖的原始材料（精确文件名 + 页码范围）；
- 必读：STYLE_GUIDE / REVISION_SPEC / EXAMPLE；
- 工具命令（runpy / runcc / csvpeek / preview / checkbook）；
- **ownership**：只许改自己那一章的 HTML 与该章的 src/figures/out 子目录，禁止改 build.py / css / 别人的章节；
- 铁律：数字必须真跑、不许编造；代码必须 `INCLUDE-CODE`（不许在 HTML 里手写代码）；图必须脚本生成；
- 自检命令与回报格式（每章一行统计，不要复述正文）。

并发建议 6~12 个；超过后失败率明显上升。子代理失败（no closing message）时**不要重派全部**，让它从断点续做。

### 阶段 5 · 构建

```bash
python _build/tools/build.py vol0      # 单卷试水（先跑这个）
python _build/tools/build.py all
python _build/tools/build.py merge     # 合订
```

流水线（`scripts/build.py`）：

```
vol/<vol>/NN_标题.html  ──collect──►  整卷 HTML（封面 + 目录 + 正文）
        │                                    │
        │  INCLUDE-CODE / INCLUDE-OUTPUT     │ Edge --headless --print-to-pdf
        │  INCLUDE-TREE / INCLUDE-DATA       ▼
        │                              原始 PDF（无页码/书签）
        └──────────────► PyMuPDF：两遍法回填目录页码 + 页眉页脚 + 书签 + 元数据
                                             │
                                      merge()：逐卷 insert_pdf + 书签偏移
```

关键设计（踩过坑才有）：

- **两遍法**：第一遍目录页码是占位符，打印后从 PDF 文本里找到每章标题所在页，第二遍把真页码填回去，再打印。标题定位靠注入不可见的唯一标记，不要靠标题文字（会撞车）。
- **快照**：`build_vol()` 开头只 `collect()` 一次，三遍构建用同一份片段快照，否则并发写作时会 IndexError。
- **打印锁**：Windows 上 Edge 会延迟释放文件，输出名带时间戳 + `--user-data-dir` 带时间戳，再 `os.replace` 重试。

### 阶段 6 · 质检（不许省）

```bash
python _build/tools/checkbook.py            # 结构体检：缺图/缺 include 目标/字数/图表代码块统计
python _build/tools/preview.py <章节.html> --check   # 单章静态体检
python _build/tools/preview.py <章节.html> --pdf     # 单章渲染 + 越界检测
python _build/tools/numcheck.py vol4        # 图/表/实验/公式编号 vs 章号
python _build/tools/fix_lt.py vol4          # 公式里的裸 < 转义（否则半页内容会被浏览器吞掉）
python _build/tools/scan_latex.py <pdf>     # 合订后扫未渲染的 LaTeX
python _build/tools/verify_book.py <pdf>    # 越界/空白页/卷起始页连续性
```

外加**人眼抽查**（脚本查不出"丑"）：目录页码、代码块跨页、宽表、公式是否渲染、图为空否。清单见 `references/qa-checklist.md`。

### 阶段 7 · 交付

- 合订 PDF + 分卷 PDF（`分卷PDF/`）；
- `交付说明.md`：这版做了什么、和上版的差异、数字口径、已知局限；
- `交接文档.md`：目录结构、工具速查、重建命令、踩坑、还能做什么；
- 全部源料留在 `_build/`（章节 HTML、可跑脚本、真实输出、图表脚本），**必须可重建**。

## 支持的输入，怎么读

| 输入 | 怎么读 | 注意 |
|---|---|---|
| 课件/讲义 PDF | `extract_sources.py pdf` 取文字 + `pgs.py` 渲染逐页看图 | 文字层常为空；公式/图必须看图；注意课件自己的勘误 |
| ipynb | `extract_sources.py nb` → py（含 `# >>> OUTPUT:`） | 损坏的 ipynb 用同目录的 `.py` 副本；内嵌输出是"当时的数字"，要注明 |
| 源代码（py/c/cpp） | 直接读；C/C++ 用 `runcc.py` 编译验证 | zig/cc 可替代 gcc；故意报错的示例要标注 |
| CSV/数据集 | `csvpeek.py` 出"体检报告"（形状/缺失/分布/五数概括） | 太大就抽样，并把抽样规则写进正文 |
| Word/Markdown/网页 | 直接读；`office-docx` 技能可解析 docx | 旧 AI 生成的汇总不要参考 |
| 图片/截图 | 当作"图"，描述其信息，必要时重绘 | 不允许整页截图凑数（除非用户要求影印原页） |

## 常见失败模式（看到就要返工）

1. 章章都是"概念 + 一段代码 + 输出"，没有真实数字 → 读者学不会。
2. 代码是手写进 HTML 的（不是 INCLUDE），跑不起来 → 一律改成 include。
3. 图是"示意图"、数据是编的 → 必须脚本生成。
4. 覆盖表里一堆"不采纳" → 说明没读原始材料。
5. 公式里的 `<` 没转义 → 半页内容消失。
6. 目录页码错位 → 两遍法没做对。
7. 各章风格不一（有的用 `##`，有的用裸数字编号）→ 阶段 3 的样板章没给。
8. 子代理互相改文件 → ownership 没写死。

## 目录结构（skill 自身）

```
material-to-book/
├── SKILL.md
├── scripts/            # 23 个可执行工具（init_project 会复制到项目的 _build/tools/）
│   ├── intake.py           # 阶段 −1：扫文件角色 + 打印访谈卡 + 生成 intake.json
│   ├── build.py            # HTML→PDF 流水线（配置驱动，读 _build/book.json）
│   ├── extract_sources.py  # PDF/ipynb 抽取
│   ├── pgs.py              # PDF 页 → PNG（人眼读图）
│   ├── csvpeek.py          # CSV 体检
│   ├── runpy.py runcc.py   # 跑 Python / 编译跑 C-C++
│   ├── docstringify.py     # 把 # 作用/参数/返回 注释块改成 docstring
│   ├── hdr2doc.py          # 脚本头注释 → 模块 docstring
│   ├── preview.py checkbook.py numcheck.py fix_lt.py scan_latex.py
│   ├── v3check.py cwaudit.py    # 三类内容 / 覆盖表审计
│   ├── renumber.py fixrefs.py   # 章号重排 / 跨卷引用修正
│   ├── cwembed.py          # 把原始 PDF 页影印进正文
│   ├── verify_book.py      # 合订体检
│   └── finalize.py         # 一键收尾（重排→构建→合订）
├── assets/book.css     # 排版样式（A4、页眉页脚、代码块、树状图、数据块）
└── references/
    ├── intake.md           # 十四问访谈、学科默认档位、派生参数、矛盾检查
    ├── pipeline.md         # 构建细节与 book.json 字段
    ├── style-guide.md      # 写作规范
    ├── experiment-spec.md  # 实验八节 + docstring 四段
    ├── chapter-template.html
    ├── qa-checklist.md
    ├── prompts.md          # 子代理 prompt 模板
    └── lessons.md          # 20 条踩坑
```

## 快速开始

```bash
# 0. 先访谈（十分钟）：扫出角色表、发访谈卡、生成 intake.json
python <skill>/scripts/intake.py "D:\课程资料"
python <skill>/scripts/intake.py "D:\课程资料" --apply    # 答完后合并进 book.json

# 1. 在资料夹里初始化
python <skill>/scripts/init_project.py "D:\课程资料" --title "XX 系统讲义" --volumes 3

# 2. 改 _build/book.json（卷名/副标题/封面要点/输出文件名）

# 3. 先写一个样板章，构建单卷试水
python _build/tools/build.py vol0

# 4. 按 references/prompts.md 分派子代理，逐章写

# 5. 质检 → 全量构建 → 合订 → 写交付说明
```

依赖：Python 3.12（`pymupdf`、`matplotlib`、`numpy`、`pandas`、`pygments`；跑 C/C++ 还要 `ziglang` 或系统 gcc）、Edge/Chrome（打印 PDF）、中文字体（正文 Noto Serif SC，图 Microsoft YaHei）。缺 LibreOffice 也能跑，本流水线不需要它。
