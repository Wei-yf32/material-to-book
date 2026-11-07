# 安装 material-to-book

一句话：把本目录放到 `~/.dsh/skills/material-to-book/`，装好五个 Python 库，
跑一遍 `scripts/doctor.py` 看到「可以开工」，就装完了。

---

## 一、Windows 一键

在 PowerShell 里进入本目录，执行：

```powershell
.\install.ps1
```

它会依次做四件事：

1. 找一个能用的 Python（3.9 以上）；
2. 用这个 Python 的 pip 装 `requirements.txt`；
3. 把本目录复制到 `%USERPROFILE%\.dsh\skills\material-to-book`；
4. 跑 `scripts\doctor.py` 打印体检表。

常用参数：

```powershell
.\install.ps1 -Check              # 只体检，不复制、不装包
.\install.ps1 -Python "C:\...\python.exe"   # 指定解释器（机器上有多套 Python 时）
.\install.ps1 -Dest "D:\skills\material-to-book"  # 装到别处
.\install.ps1 -SkipDeps           # 依赖已装好，只复制
```

如果脚本被执行策略拦住，用：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

---

## 二、手动安装

### 1. 放到位

DSH 只会扫描 `~/.dsh/skills/` 下的一层目录，目录名要和 `SKILL.md` 里的 `name` 一致：

```
C:\Users\<你>\.dsh\skills\material-to-book\
    SKILL.md
    README.md
    scripts/
    references/
    assets/
```

三种放法任选：

- **git**：`git clone https://github.com/Wei-yf32/material-to-book.git "$env:USERPROFILE\.dsh\skills\material-to-book"`
- **复制**：把整个文件夹拷进去（不要嵌套成 `material-to-book/material-to-book`）
- **zip**：解压后把里层目录改名成 `material-to-book` 再放进去

macOS / Linux 是 `~/.dsh/skills/material-to-book/`，同上。

### 2. 装依赖

用**将实际执行构建的那个解释器**来装，不要用别的 Python：

```powershell
& "C:\Users\<你>\AppData\Local\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

```bash
python3 -m pip install -r requirements.txt
```

五个必需的库：`pymupdf`、`matplotlib`、`numpy`、`pandas`、`pygments`。
`Pillow` 可选。

### 3. 体检

```powershell
& "<python>" "<skill>\scripts\doctor.py"
```

看到这个收尾就算装好：

```
结论：可以开工。下一步：python scripts/intake.py "<资料夹>"
```

`--json` 输出机器可读结果，`--strict` 让缺失项直接返回 1（接 CI 用）。

---

## 三、还要准备的两样东西

这两样不是 Python 包，但构建时一定会用到：

| 依赖 | 用途 | 怎么查 |
|---|---|---|
| **Edge 或 Chrome** | 把 HTML 打印成 PDF（无头模式） | `doctor.py` 会列出找到的路径 |
| **中文字体** | 正文与页眉（默认 Microsoft YaHei） | Windows 自带；Linux 装 `fonts-noto-cjk` |

浏览器装在非默认位置时，把路径写进项目 `_build/book.json` 的 `edge` 字段，
不用改代码：

```json
{ "edge": "D:\\Chrome\\Application\\chrome.exe" }
```

---

## 四、在 DSH 里怎么用

装好后**新开一个会话**，输入框里 `/` 会列出技能；直接说人话也能触发，例如：

- 「把这个文件夹里的资料整理成一份讲义」
- 「把这堆课件合并成一本手册」
- 「按教材顺序把教材、教辅、课件汇总成一份完整的复习资料」

触发后它做的第一件事是**访谈**（阶段 −1）：扫一遍资料、列出「哪个是教材 / 哪个是教辅 /
哪个是课件」，再问你主线、覆盖深度、专业、是否需要代码与工程案例。

如果你想跳过访谈直接开工，说一句「全按默认」，它会用
`references/intake.md` 里的默认档位。

---

## 五、升级与卸载

```powershell
# 升级
cd "$env:USERPROFILE\.dsh\skills\material-to-book"; git pull
# 或重跑：.\install.ps1 -SkipDeps

# 卸载
Remove-Item -Recurse "$env:USERPROFILE\.dsh\skills\material-to-book"
```

已有的书稿不受影响：项目里的 `_build/tools/` 是当初复制过去的一份脚本，
想用新版工具就重新跑 `init_project.py --force`，或只把
`scripts/build.py` 覆盖过去（两者接口一致）。

---

## 六、排错

| 现象 | 原因 | 处理 |
|---|---|---|
| `No module named pip` | 用的是精简版 / 应用商店版 Python | 换完整版 Python 3.12，或 `python -m ensurepip` |
| 装完了仍报 `No module named fitz` | pip 装到了另一个 Python | 用 `doctor.py` 打印的解释器路径去装 |
| 构建卡在「打印」不动 | Edge 被上一个进程占用 | 关掉残留的 `msedge.exe`，重跑；构建器已带重试 |
| PDF 里中文是方框 | 字体没被找到 | 装微软雅黑或 Noto CJK，改 `book.css` 的 `font-family` |
| 目录页码全是 00 | 只跑了一遍 | 用 `build.py`，不要手工打印；两遍法第二遍才回填 |
| 书签里出现 `\(` | 标题里有公式 | 已在 v2 修好（`plain_title`）；旧项目覆盖 `build.py` 即可 |

体检不过时，`doctor.py` 会直接把补装命令打出来，复制执行即可。
