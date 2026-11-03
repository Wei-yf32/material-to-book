# 子代理 prompt 模板

四条原则：**上下文给足、边界写死、验收可跑、回报简短**。

- 一章一个子代理，不要一章分给两个人（会互相覆盖）。
- 并发 6~12 个；再多失败率陡增。
- 失败（no closing message）时让它从断点续做，不要重派全部。
- 每个 prompt 里重复写"只改你自己的文件"——重复三遍都不过分。

---

## 模板 A：新写一章

```
你在为《{书名}》第 {N} 卷写第 {NN} 章，读者是零基础工科本科生。

必读（先读，再动手）：
1. _build/STYLE_GUIDE.md —— 写作规范
2. _build/EXAMPLE.html —— 样板章，照它的密度与结构写
3. _build/text/{原文tag}.txt —— 本章要覆盖的原始材料（第 {a}~{b} 页）
4. _build/cw/{pdf名}/p{a}..p{b}.png —— 原始页渲染图，必须逐页看图（公式/表格在图里）

章节文件：_build/vol/vol{N}/{NN}_标题.html（只写这一个文件）
结构：h1 + p.h1note + box.key 目标 + 导入 + 6~8 个 h2（直觉/形式化/例子/代码/实验/常见错误/小结/覆盖表）

硬性要求：
- 每章 ≥ {字数} 汉字；每个概念走"直觉 → 形式化 → 真实数值 → 边界"四层。
- 代码一律用 <!--INCLUDE-CODE path=src/vol{N}/xxx.py lang=py-->，源文件你写，必须能跑：
  写完执行 python _build/tools/runpy.py _build/src/vol{N}/xxx.py，输出存 _build/out/vol{N}/xxx.txt，
  正文用 <!--INCLUDE-OUTPUT path=out/vol{N}/xxx.txt-->。禁止把代码/输出手写进 HTML。
- 图一律脚本生成：_build/src/figs/vol{N}_{NN}.py（用 figstyle.py 的 setup/save），
  存 _build/figures/vol{N}/；图注写"数据来源 + 脚本路径"。禁止示意图/编数据。
- 每个 def/class 写中文 docstring（作用/参数/返回/关键实现/边界）。
- 章末覆盖表：把原始材料每一页映射到本书小节，第三列禁止"不采纳"。
- 公式用 \( \) 与 \[ \]，公式里的 < 写 &lt;。

边界：只许改 {章节文件}、_build/src/vol{N}/ 下你新建的脚本、_build/src/figs/vol{N}_{NN}.py、
_build/out/vol{N}/ 下你的输出。禁止改 build.py、css、figstyle.py、别人的章节。

自检（必须全绿再回报）：
python _build/tools/preview.py "_build/vol/vol{N}/{NN}_标题.html" --pdf
python _build/tools/checkbook.py vol{N}
python _build/tools/numcheck.py vol{N}

回报（5 行，不要复述正文）：
章节 / 汉字数·图·表·代码块·实验 / 新增的可跑脚本 / 覆盖表行数与不采纳数 / 自检结果
```

---

## 模板 B：把已有章节改成"实验八节 + 注释即讲解"（改版）

```
你在改《{书名}》第 {N} 卷第 {NN} 章，目标是把 {K} 个实验改成第 5 版规范。

必读：_build/REVISION_SPEC_V5.md（规范）、_build/vol/vol4/03_xxx.html 的 §3.17（样板）

对每个 <div class="box lab"> 实验：
1. 删「文件清单」表，改「3. 文件结构」：写 _build/src/vol{N}/tree_{NN}{X}.txt（缩进+名字+两空格+说明），
   正文用 <!--INCLUDE-TREE path=src/vol{N}/tree_{NN}{X}.txt-->。
2. 加「4. 阅读顺序」：<ol class="steps"> 5 条，末条是运行命令。
3. 加「5. 数据长什么样」：CSV 用 csvpeek.py 生成 _build/out/vol{N}/csv_xxx.txt 再 INCLUDE-DATA；
   代码造的数据就贴造数据代码 + 样张表；再配 1 张真实特征图（脚本 src/figs/vol{N}_{NN}x.py）。
4. 每个代码块前 1~2 句导语 + INCLUDE-CODE（构建器会自动加文件条）。
5. 改脚本：docstring 写全四段（作用/参数/返回/关键实现/边界），函数体内每 5~15 行一条段落注释，
   删掉 print("== … ==") 式标题；改完重跑 runpy.py，确认 exit=0，并让正文数字与输出一致。
6. 删正文里"课件第 N 页讲了……"的指路句，改成用内容作主语直接讲（影印图注与覆盖表保留）。

自检：preview --pdf 通过无越界；checkbook vol{N} 通过；numcheck vol{N} OK；grep "课件 p" 应为 0。
回报 5 行：章节 / 实验（新增树 N、数据速览 N、特征图 N）/ 代码（docstring N、段落注释 N、删 print N）/ 叙事（删指路句 N）/ 自检。
```

---

## 模板 C：独立审校（不写正文，只挑错）

```
你是审校。不要改文件，只输出问题清单。

范围：_build/vol/vol{N}/*.html（{章数} 章）
检查：
1. 函数讲解缺失：有 def/class 但没有 docstring 或参数没解释；
2. 实验缺段：八节里缺哪几节；
3. 数字可疑：正文数字与 out/*.txt 里的输出不一致（列出 three-tuple：文件、句子、疑点）；
4. 编号错误：图/表/实验前缀与章号不符、跨章引用指向不存在的小节；
5. 跨卷引用：写死了"第 X 卷第 N 章"但没有对应内容；
6. 语言问题：禁用词、过长的句子、"课件 pN"指路句；
7. 宽表与超长代码块（>400 行）。

输出：_build/QC_REPORT.md，按严重度排序（blocker / high / medium / low），每条给"文件:行 + 问题 + 改法"。
```

---

## 模板 D：清理与一致性（机械工作）

```
只做机械替换，不改语义。范围：_build/vol/vol{N}/*.html

1. 把"原始讲义第 N 页/课件第 N 页/原讲义第 N 页"改成"原始讲义"或删掉（保留 figure.cwpage 图注与覆盖表）；
2. 把 $...$ 公式改成 \(...\)（若用本流水线）；
3. 公式里的裸 < 改成 &lt;（用 fix_lt.py）；
4. 过时跨章引用：按内容判定，不要机械 n−9。

改完逐章跑 preview --check，并在最后列出"改了哪些文件、各多少处"。
```
