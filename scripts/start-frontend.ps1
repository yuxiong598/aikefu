param(
    [string]$NodePath = "node"
)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$nodeCommand = (Get-Command $NodePath -ErrorAction Stop).Source
$versionText = & $nodeCommand -p "process.versions.node"
if ($LASTEXITCODE -ne 0) { throw "无法读取 Node.js 版本。" }
$nodeVersion = [version]$versionText
if ($nodeVersion -lt [version]"22.12.0") {
    throw "前端需要 Node.js 22.12 或更新版本。可用 -NodePath 指定已有的新版 node.exe。"
}
$vitePath = Join-Path $projectRoot "frontend\node_modules\vite\bin\vite.js"
if (-not (Test-Path -LiteralPath $vitePath -PathType Leaf)) {
    throw "请先在 frontend 目录执行 npm ci。"
}
Push-Location -LiteralPath (Join-Path $projectRoot "frontend")
try {
    # 直接使用指定的 Node，避免 npm.cmd 选中另一版本的解释器。
    & $nodeCommand $vitePath
    if ($LASTEXITCODE -ne 0) { throw "前端启动失败，退出码 $LASTEXITCODE" }
}
finally {
    Pop-Location
}
