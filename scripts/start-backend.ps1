param(
    [string]$PythonPath = ""
)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $PythonPath) {
    $PythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "请先按 README 安装后端虚拟环境，或用 -PythonPath 指定 Python。"
}
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
Push-Location -LiteralPath $projectRoot
try {
    # 使用一个进程，复用本地模型并保持文档索引与删除顺序一致。
    & $PythonPath -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
    if ($LASTEXITCODE -ne 0) { throw "后端启动失败，退出码 $LASTEXITCODE" }
}
finally {
    Pop-Location
}
