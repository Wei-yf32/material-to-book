# 实验规范（experiment-spec）

每个实验是一个 `<div class="box lab">`，内部八节，缺一节就是不合格。目标：读者照着能把实验**从零重做一遍**，且知道每个数字是怎么来的。

## 八节骨架

```html
<div class="box lab">
<p class="lab-head"><b>实验 3-B</b>　从零实现一棵 ID3（对应训练营作业 hw1）</p>

<p><b>1. 实验目的</b></p>
<p>不用 sklearn，自己实现 DecisionTree，在 9879 场对局上训练，测试准确率 &gt; 0.6。
验证三件事：信息增益怎么算、两个终止条件怎么卡、剪枝为什么能救过拟合。</p>

<p><b>2. 实验要求</b></p>
<ul>
<li>接口：<code>DecisionTree(classes, features, max_depth=10, min_samples_split=10, impurity_t="entropy")</code>，
  每个参数写清含义与取值范围；</li>
<li>实现 <code>fit</code> / <code>predict</code>，predict 要同时支持单个样本与一批样本；</li>
<li>…每条要求都要能被"跑一次"验证…</li>
</ul>

<p><b>3. 文件结构</b></p>
<!--INCLUDE-TREE path=src/vol4/tree_3B.txt-->

<p><b>4. 阅读顺序</b></p>
<ol class="steps">
<li>先看下面「数据长什么样」：40 列分别是什么、有没有缺失、标签怎么分布；</li>
<li>读 <code>load()</code> 与 <code>discretize()</code>：这是"原始表 → 15 个差值特征 → 8 个箱号"的两次变形；</li>
<li>再读 <code>Node</code> 与 <code>DecisionTree</code>：建树、递归、预测、剪枝全在这里；</li>
<li>最后看「运行输出」，四组数字逐个对回代码；</li>
<li>自己跑一遍：<code>python _build/tools/runpy.py _build/src/vol4/ch12_id3.py</code>。</li>
</ol>

<p><b>5. 数据长什么样</b></p>
<p>一句话说明数据来源与规模，然后：</p>
<!--INCLUDE-DATA path=out/vol4/csv_lol.txt-->
<p><b>看什么：</b></p>
<ul>
<li>…三个具体观察点，每个都指向后文的某个设计决定…</li>
</ul>
<figure><img src="../../figures/vol4/v403_data.svg" class="w80">
<figcaption>图 3-… 特征分布/标签分布。数据由 <code>src/figs/vol4_03.py</code> 从原始 CSV 直接统计。</figcaption></figure>

<p><b>6. 逐段讲代码</b></p>
<p>导语 1~2 句：这个脚本按几段组织、先看哪段。</p>
<!--INCLUDE-CODE path=src/vol4/ch12_id3.py lang=py-->
<p>分段讲解：每 5~15 行一段，说清"这段为什么这么写"。</p>

<p><b>7. 运行输出怎么读</b></p>
<!--INCLUDE-OUTPUT path=out/vol4/ch12_id3.txt-->
<p>把输出里的每个数字指回代码里的某一行/某个变量。</p>

<p><b>8. 动手改一改</b></p>
<ul>
<li>改 <code>impurity_t="gini"</code>，叶数从 488 变 477，为什么少？</li>
<li>把 <code>min_samples_split</code> 调到 2，测试准确率怎么变？为什么？</li>
<li>…每条都要有"预期现象 + 解释"…</li>
</ul>
</div>
```

## 文件树格式（`INCLUDE-TREE` 的输入）

每行：`缩进 + 名字 + 至少两个空格 + 说明`；目录以 `/` 结尾；`#` 开头是整行注释。

```
_build/
  src/vol4/
    ch12_id3.py           本实验的程序（唯一要读的代码）
  out/vol4/
    ch12_id3.txt          运行输出（下文贴的就是它）
    数据目录/
      high_diamond.csv    9879 行 × 40 列
# 只列本实验真正用到的文件，不要列 ai 中间产物
```

规则：

- **只列本实验真正用到的文件**（脚本、输出、数据、图脚本、原始数据）；中间产物、备份、别人的文件不列。
- 每个文件都要有说明，说明里写"它是什么"，不要写"它很重要"。
- 树里出现的路径，读者应该真的能在项目里找到。

## 数据节（`INCLUDE-DATA`）

用 `csvpeek.py` 生成，不要手写：

```bash
python _build/tools/csvpeek.py "数据/xxx.csv" --rows 6 --head-cols 6 --out out/vol4/csv_xxx.txt
```

输出包含：形状与内存、每列（dtype/缺失数/不同值数/首个非空值）、前 6 行、数值列五数概括、低基数列的取值分布。

正文还要补：

1. **三到四条"看什么"**：每条都指向后文的一个设计决定（例如"blueWins 均值 0.4990 → 没有类别不平衡，不需要重采样"）。
2. **一张特征图**：标签分布、关键特征分布、相关性热力图，任选其一，脚本生成。
3. 如果没有 CSV（数据是代码造的），就贴"造数据的那段代码 + 样张表 + 一张散点图"。

## 代码注释规范（docstring 四段）

`def` / `class` 上方必须是多行注释（docstring），**不是** `# 作用/参数/返回` 这种行注释堆叠：

```python
def entropy(y):
    """计算标签集合的香农熵（单位 bit）。

    参数:
        y: 一维整型数组，每个元素是类别编号。允许重复值，长度即样本数。

    返回:
        浮点数，范围 [0, log2(K)]；全同一类时为 0.0。

    关键实现:
        先用 np.bincount 统计每类计数，再取 p*log2(p) 求和取负。
        计数为 0 的类别跳过，否则 log2(0) 会报警告。

    边界情况:
        y 为空数组时返回 0.0（视为"没有不确定性"），调用方需自行判断是否合法。
    """
```

- 每个参数都要写"是什么类型、什么形状、取什么值"，不能只写参数名。
- 返回值的类型、形状、取值范围要写。
- 有坑的地方写进"边界情况"。
- 函数体内再用段落注释标出"这一段在做什么"，每 5~15 行一条。

迁移旧脚本：`python _build/tools/docstringify.py <脚本> --apply`（把 `# 作用/参数/返回/关键行` 注释块改成上面这种 docstring，幂等）。脚本头的运行说明用 `hdr2doc.py` 转成模块 docstring。

## 代码关系要讲清（不只是逐段）

代码块讲完之后，补 1 段"这几个东西是怎么串起来的"：谁调用谁、数据在哪一步变形、哪个函数是纯计算、哪个有副作用（读文件/打印）。
读者应该能凭这段说明在脑子里画出调用链，而不是记住 12 个函数名。

函数内部按 5~15 行一组加段落注释，写"这一块在做什么、为什么这么做"，不复述代码字面。

## 硬性限制

- 正文里**不许**用 `print("== 第 1 部分 ==")` 这种方式当小标题：注释写在代码里，正文用段落讲。
- 每个实验至少 1 段可运行代码；跑不动的（缺数据集/缺 GPU）要写明"需要什么、输出见哪一节"。
- 书里贴的输出必须与正文数字一致；如果因为库版本变了数字变了，要重跑并把新数字写进正文，同时注明版本。
