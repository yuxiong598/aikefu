# 智能客服知识库与售后工单系统

本科毕业设计项目。客服上传 PDF 或 Word 文档，经人工核对正文和片段后入库。用户通过聊天查询知识、核验引用来源，并创建售后工单。客服在工单详情中处理问题。

## 环境

- Python 3.12 或更新版本，当前验证版本为 Windows Python 3.13.5。
- Node.js 22.12 或更新版本，当前构建验证版本为 Node.js 24.22.1。
- 后端使用同步 FastAPI 业务路由、SQLAlchemy 2.x 和 SQLite。
- BGE 使用 CPU 懒加载，Chroma 使用本地 PersistentClient。
- 前端使用 Vue 3、Vite、JavaScript、Element Plus、Pinia、Vue Router 和 Axios。

首次安装包含 PyTorch 等较大依赖。首次编码会下载 BGE 权重并初始化模型，耗时取决于网络和机器。模型缓存后会复用本地文件，同一后端进程复用内存中的模型。

## 首次安装

在项目根目录打开 PowerShell。

    py -3.13 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
    .\.venv\Scripts\python.exe -m pip check

    if (-not (Test-Path -LiteralPath .\backend\.env)) {
        Copy-Item -LiteralPath .\backend\.env.example -Destination .\backend\.env
    }

    Set-Location .\frontend
    node --version
    npm.cmd ci
    Set-Location ..

已有 .venv 时可直接安装依赖。把真实 DeepSeek 密钥填写到 backend/.env 的 DEEPSEEK_API_KEY，保存后重启后端。

| 后端配置 | 含义 |
|---|---|
| SQLITE_PATH | 业务数据库文件，相对路径以 backend 为基准 |
| CHROMA_DIR | 本地向量索引目录 |
| BGE_MODEL_NAME | 默认 BAAI/bge-small-zh-v1.5，也可填写本地模型目录 |
| BGE_CACHE_DIR | 模型下载缓存目录 |
| DEEPSEEK_API_KEY | 真实模型密钥 |
| DEEPSEEK_BASE_URL | DeepSeek 的 API 地址 |
| DEEPSEEK_MODEL | 账号可用的模型名称 |
| AUTH_SESSION_HOURS | 登录会话有效期，默认 24 小时 |

配置从后端 .env 和代码默认值读取。前端通过 /api 请求后端，开发服务器将请求转发到 127.0.0.1:8000。

## 创建账号

创建客服账号时在终端输入密码。

    Set-Location .\backend
    ..\.venv\Scripts\python.exe -m app.create_staff --username support
    Set-Location ..

用户名为 3–32 位英文字母、数字或下划线，大小写统一处理。密码为 8–128 个字符。普通用户通过登录页注册。测试脚本中的账号仅存在于临时数据库，正式运行时需要自行创建账号。

## 启动

窗口 1 在项目根目录运行后端。

    .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

窗口 2 运行前端。

    Set-Location .\frontend
    npm.cmd run dev

也可运行 scripts/start-backend.ps1 和 scripts/start-frontend.ps1。前端脚本支持 -NodePath 指定已安装的新版 Node。脚本会在运行期间占用当前窗口，按 Ctrl+C 停止。

- 工作台 http://127.0.0.1:5173/
- 接口文档 http://127.0.0.1:8000/docs
- 健康检查 http://127.0.0.1:8000/api/health

按上述单进程方式启动。本地模型和文档修改操作由单一后端进程管理。退出登录会清理页面缓存，未提交草稿保存在当前页面内。

## 演示和回归

    # 生成上传用的虚构政策文档，已有同名文件时会停止
    .\.venv\Scripts\python.exe .\scripts\create_demo.py

    # 默认使用真实 BGE 和 Chroma，模型回答使用接口替身
    .\.venv\Scripts\python.exe .\scripts\verify_system.py

    # 读取真实后端密钥，向 DeepSeek 发送一次问答请求
    .\.venv\Scripts\python.exe .\scripts\verify_system.py --live

    # 编译前端
    Set-Location .\frontend
    npm.cmd run build

回归脚本使用项目内临时 SQLite 和 Chroma 目录，退出子进程后清理临时数据。BGE 缓存使用配置中的路径。--live 会发送脚本内的虚构售后片段和测试问题，按 DeepSeek 账号规则计费。

完整演示顺序见 [答辩演示](docs/DEMO.md)，验收范围和实际验证状态见 [验收说明](docs/ACCEPTANCE.md)。

## 主要行为

- PDF 提取文字层，Word 支持 .docx。上传处理上限为 10 MiB。
- 正文和切分结果由用户核对。确认前保留在前端，提交确认接口后保存原文和向量。
- 默认每片最多 500 个字符，按段落、句末和长度切分，顺序拼接可还原原文。
- RAG 回答附带文件名、片段位置和原文。模型资料不足时返回提示。
- 会话和工单按登录账号归属。客服可以处理所有工单，知识库管理接口要求客服权限。
- 工单按待处理、处理中、已完成顺序流转。关联工单保存建单时最近 20 轮会话及引用。
- 文档删除先退出检索，再清理向量和正文。失败时保留继续删除入口。
- 同一确认、提问或建单请求重试时复用请求编号，以避免重复保存。
- 旧版浏览器历史可通过登录后的认领按钮关联到当前账号。

## 数据与代码

    backend/app/
      router/       普通 def 业务路由
      service/      认证、知识、聊天和工单业务
      crud/         业务数据读写
      model/        SQLAlchemy 模型
      schema/       请求和响应校验
      rag/          BGE 和 Chroma
    frontend/src/
      api/          后端请求
      stores/       登录与聊天状态
      *View.vue     各模块页面
    scripts/        启动、样例和回归工具
    docs/           演示与验收说明

默认业务数据位于 backend/data/customer_service.db，向量位于 backend/data/chroma，模型位于 backend/data/models。备份业务库和向量目录时先停止后端，并将两者作为同一组保存。历史问答中的引用快照会保留。

当前启动时自动创建缺失的数据表。结构变更需要另行编写迁移，生产部署和多进程扩展需要单独验证。

## 常见操作问题

| 现象 | 检查方式 |
|---|---|
| 前端提示 Node 版本不满足 | 检查 node --version，使用 22.12 或更新版本，或指定启动脚本的 NodePath |
| 前端无法请求接口 | 确认后端已启动且健康检查为 200，前端由 Vite 开发服务器提供 |
| 回答提示尚未配置密钥 | 检查 backend/.env 中的密钥并重启后端 |
| 首次入库或提问耗时较长 | 等待模型下载和加载，失败时保留原提交并重试 |
| PDF 没有可提取文字 | 使用带文字层的 PDF，或先完成 OCR |
| 文档显示待索引 | 客服在文档列表点击重试索引 |
| 文档显示待完成删除 | 客服在列表点击继续删除 |
| 普通用户看不到知识库管理 | 使用客服账号登录 |
