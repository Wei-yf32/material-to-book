# 踩坑记录（lessons）

按"症状 → 原因 → 解法"记。做同类项目前扫一遍，能省一天。

1. **半页内容凭空消失，公式变成源码**
   原因：LaTeX 里写了裸 `<`（如 `j<i`、`x_{<t}`），浏览器把 `<i` 当斜体标签。
   解法：公式里 `<` 一律 `&lt;`；用 `fix_lt.py` 兜底（它只在"标签名后面紧跟 `>`、`/`、空格"时才认作真标签）。

2. **目录页码全部指向第 2 页（目录自己）**
   原因：用标题文字在 PDF 里搜页码，目录页本身含所有标题。
   解法：标题内注入唯一不可见标记，搜标记；两遍法回填。

3. **`IndexError: list index out of range`（构建时）**
   原因：子代理正在写文件，两遍构建之间标题数量变了。
   解法：`build_vol()` 开头取一次片段快照，三遍都用它；`build_toc` 加越界保护。

4. **`PermissionError: [WinError 32]` / `FzErrorSystem: cannot remove file`**
   原因：Edge 打印后延迟释放；或用户开着 PDF 阅读器。
   解法：输出名与 `--user-data-dir` 带时间戳；`.tmp` + `os.replace` 重试；合订先写临时文件，被占就另存 `..._第N版.pdf` 并告知用户关掉阅读器。

5. **页眉英文变成 "P y t h o n"**
   原因：PyMuPDF 内置 `china-ss` 把 ASCII 当全角。
   解法：`insert_text(..., fontfile=r"C:\Windows\Fonts\msyh.ttc", fontname="msyh")`。

6. **matplotlib 中文全是方框 / 报 `findfont` 警告**
   原因：字体族里首选字体缺对应字重（Noto Serif SC 没有 Regular）。
   解法：`font.family = ["Microsoft YaHei", "Noto Sans SC", ...]`；`font.savefig.dpi=300`；SVG 里 `svg.fonttype='path'`（文字转路径，任何机器都能显示）。

7. **表格第一列被压成两行**
   原因：Chrome 自动布局平均分配。
   解法：`<th style="width:12%">` 指定比例；数字列 `class="num"` 右对齐。

8. **表格文字被 justify 拉开（"返回 新表"）**
   原因：单元格继承 body 的 `text-align:justify`。
   解法：`td, th { text-align: left }`。

9. **图宽类 `w72` 无效、图撑满整页**
   原因：CSS 只定义了少数宽度类。
   解法：生成 `w45…w95` 全部 5% 步长。

10. **子代理互相覆盖文件**
    原因：prompt 里没写死 ownership。
    解法：每章明确"只许改 X 文件与 Y 目录"，并在回报里要求列出改动文件。

11. **子代理集体 `failed before it finished`**
    原因：并发过高（>12）导致的运行时错误，不是内容问题。
    解法：降并发；逐章落盘；失败后从断点续做（`send_message` 指定"只补第 3、4 章"）。

12. **ipynb 解析失败**
    原因：文件损坏/含非法 JSON。
    解法：同目录常 `.py` 副本或已执行版；`extract_sources.py nb` 失败时改读 `.py`。

13. **课件文字层是空的（提取只有几十字）**
    原因：整页是图片（扫描版/导出图）。
    解法：`pgs.py` 渲染成 PNG 逐页看图；文字量统计不能用 `text/*.txt` 的字数衡量"覆盖度"。

14. **`import fitz` 触发 FutureWarning 且 exit code 1**
    原因：PyMuPDF 2.x 改名。
    解法：`import pymupdf as fitz`。

15. **joblib 进程后端在中文临时目录报 `UnicodeEncodeError`**
    原因：Windows + 非 ASCII 路径。
    解法：所有脚本回避 `n_jobs=-1`；或设 `JOBLIB_TEMP_FOLDER` 到纯英文路径。

16. **稀疏矩阵喂 RandomForest 慢 1000 倍**
    原因：树模型对稀疏输入会转 dense 逐列扫描。
    解法：统一 `.toarray()`（在样本量可承受时）。

17. **本机没有 torch/xgboost/ultralytics/cv2**
    原因：教学机不装重型依赖。
    解法：实验用 NumPy 手写；引用的原始 notebook 数字标注"你当时的结果"；并在正文说明"本机复现会得到什么"。

18. **`print("== 第 1 部分 ==")` 当小标题**
    原因：AI 生成代码的坏习惯，读者读到的是"输出很乱"。
    解法：删掉，改用 docstring + 段落注释；正文用段落讲。

19. **正文数字与输出块不一致**
    原因：改了库版本/改了代码没重跑。
    解法：任何代码改动后重跑 `runpy.py`；正文数字从输出里抄，不凭记忆。

20. **改版把用户原有内容删掉了**
    原因：为了"统一风格"重排、合并。
    解法：只增不减；确需删除要单独列清单并在交付说明里写明。

21. **PowerShell 里 `python -c "…中文与反斜杠…"` 报 `SyntaxError: unterminated string`**
    原因：引号与反斜杠互相吞。
    解法：写成 `.py` 文件再执行；不要用 `-c` 塞长字符串。

22. **不同卷章号重复（第 4 卷和第 5 卷都有"第 10 章"）**
    原因：各卷独立编号，后期又重排。
    解法：`renumber.py` 统一重排 + 改写"图/表/实验 NN-k"；`fixrefs.py` 修跨卷引用；`numcheck.py` 复查。
