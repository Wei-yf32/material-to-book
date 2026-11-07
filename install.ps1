# material-to-book 安装脚本（Windows PowerShell）
#
# 用法：
#   .\install.ps1                 # 装依赖 + 复制到 ~\.dsh\skills + 体检
#   .\install.ps1 -Check          # 只体检当前目录，不动任何文件
#   .\install.ps1 -SkipDeps       # 依赖已装好，只复制
#   .\install.ps1 -Dest D:\x      # 自定义安装目录
#   .\install.ps1 -Python C:\...\python.exe   # 指定解释器

param(
    [string]$Python = "",
    [string]$Dest = "",
    [switch]$SkipDeps,
    [switch]$Check
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Say($msg, $color = "Gray") { Write-Host $msg -ForegroundColor $color }

# ---------------------------------------------------------------- 找解释器
function Resolve-Python {
    param([string]$Explicit)
    $cands = @()
    if ($Explicit) { $cands += $Explicit }
    $cands += @(
        "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python312\python.exe",
        "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python311\python.exe"
    )
    foreach ($c in $cands) {
        if ($c -and (Test-Path $c)) { return $c }
    }
    foreach ($name in @("python", "python3", "py")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    return $null
}

Say "material-to-book 安装" "Cyan"
Say ("源目录：" + $Here)

$Py = Resolve-Python -Explicit $Python
if (-not $Py) {
    Say "找不到 Python。装一个 3.10+ 的完整版，或用 -Python 指定路径。" "Red"
    exit 1
}
$ver = & $Py -c "import sys;print(str(sys.version_info[0])+'.'+str(sys.version_info[1]))"
Say ("解释器：" + $Py + "  (Python " + $ver + ")")

& $Py -c "import sys;sys.exit(0 if sys.version_info[:2] >= (3,9) else 1)"
if ($LASTEXITCODE -ne 0) {
    Say "这个解释器低于 3.9，换一个。" "Red"
    exit 1
}

if ($Check) {
    & $Py (Join-Path $Here "scripts\doctor.py")
    exit $LASTEXITCODE
}

# ---------------------------------------------------------------- 装依赖
if (-not $SkipDeps) {
    $req = Join-Path $Here "requirements.txt"
    if (Test-Path $req) {
        Say "安装依赖（pymupdf / matplotlib / numpy / pandas / pygments）…" "Yellow"
        & $Py -m pip install --upgrade pip --quiet 2>$null
        & $Py -m pip install -r $req
        if ($LASTEXITCODE -ne 0) {
            Say "pip 安装失败。常见原因：这个 Python 没有 pip。换完整版 Python 3.12 再试。" "Red"
            exit 1
        }
    }
}

# ---------------------------------------------------------------- 放到位
if (-not $Dest) { $Dest = Join-Path $env:USERPROFILE ".dsh\skills\material-to-book" }
$DestParent = Split-Path -Parent $Dest
if (-not (Test-Path $DestParent)) { New-Item -ItemType Directory -Path $DestParent -Force | Out-Null }

if ((Resolve-Path $Here).Path -eq (Resolve-Path $Dest -ErrorAction SilentlyContinue).Path) {
    Say "已经在安装位置，跳过复制。" "Yellow"
} else {
    if (Test-Path $Dest) {
        $bak = $Dest + ".bak-" + (Get-Date -Format "yyyyMMddHHmmss")
        Say ("已有旧版本，先备份到 " + $bak) "Yellow"
        Move-Item $Dest $bak
    }
    Say ("复制到 " + $Dest)
    Copy-Item -Recurse -Force $Here $Dest
    # 安装副本里不需要的东西
    foreach ($junk in @(".git", "__pycache__", "scripts\__pycache__", ".pytest_cache")) {
        $p = Join-Path $Dest $junk
        if (Test-Path $p) { Remove-Item -Recurse -Force $p -ErrorAction SilentlyContinue }
    }
}

# ---------------------------------------------------------------- 体检
Say "体检…" "Yellow"
& $Py (Join-Path $Dest "scripts\doctor.py")
$code = $LASTEXITCODE

Say ""
if ($code -eq 0) {
    Say "装好了。新开一个 DSH 会话，说「把这个文件夹的资料整理成一份讲义」即可。" "Green"
} else {
    Say "装好了但缺件，按上面的提示补齐后重跑：.\install.ps1 -Check" "Yellow"
}
exit $code
