# rag-mcp

> 将本地 PDF 知识库以 MCP 工具的形式提供给 Claude、Copilot 及其他兼容 MCP 的 Agent。
>
> 支持带来源信息的混合检索、知识库集合管理和文档摘要查询；可通过 stdio 或 Streamable HTTP 接入。

`rag-mcp` 是一个本地优先的 RAG 服务。它将 PDF 文档摄取为可持久化的知识库，并通过标准 Model Context Protocol (MCP) 暴露检索、集合浏览和文档摘要能力，使已有的 Agent 可以在不重建 RAG 管线的前提下访问私有知识。

项目面向已经具备 Agent 或 MCP Client 的开发者。它不负责聊天界面或 Agent 编排，而是把本地文档检索能力封装为稳定、可调用的 MCP Tool Catalog：Agent 通过工具查询，服务端负责召回、融合、重排、来源组织与可观测性记录。

### 特性与亮点

- **面向 Agent 的标准接入**：同一套 FastMCP Tool Catalog 同时支持本地 `stdio` 和 Streamable HTTP；三个公开工具名称稳定，便于接入 Claude、Copilot 和其他 MCP Client。
- **本地优先的知识库**：PDF、索引、Chroma 持久化数据和日志均保存在本地目录；模型 Provider 按配置替换，不绑定单一云服务。
- **混合检索与可追溯结果**：结合 Dense Retrieval 与 BM25 Sparse Retrieval，经融合和可选重排后返回结果；输出尽可能保留源文件路径、页码和得分，便于 Agent 与用户复核。
- **可插拔 RAG 管线**：LLM、视觉模型、Embedding、文本切分、Vector Store、Reranker 和评测器均通过工厂模块和 YAML 配置解耦。
- **多模态摄取准备**：摄取链路支持可选的 LLM 分块优化、元数据增强和图片描述，并会保存图片相关索引信息。
- **可视化运维与评测**：内置 Streamlit Dashboard，覆盖数据、摄取、查询追踪和 Golden Test Set 评估；可使用 RAGAS 评估检索上下文与生成答案质量。

### 技术栈

| 领域 | 实现 |
|---|---|
| MCP 服务 | Python MCP SDK / FastMCP，stdio 与 Streamable HTTP |
| 文档处理 | PyPDF、LangChain Text Splitters |
| 检索 | Dense Retrieval、BM25、Fusion、可选 Reranker |
| 向量与持久化 | ChromaDB、本地 BM25 索引、SQLite 元数据 |
| 可观测性 | 本地 JSONL Trace、Streamlit Dashboard |
| 评测 | Golden Test Set、RAGAS、轻量 Hit Rate / MRR 评测器 |
| 工程化 | Python 3.11+、uv、pytest、Docker Compose |

## 你可以用它做什么

- 将本地 PDF 摄取为可持久化的知识库集合。
- 让 Agent 查询知识库，并获得带来源路径、页码和分数的检索结果。
- 让 Agent 查看可用集合，或读取指定文档的标题、摘要和标签。
- 使用同一套 MCP 工具目录，通过本地 `stdio` 或 Streamable HTTP 运行。
- 在 Dashboard 中查看摄取、查询追踪、数据和评测信息。

## 快速接入 MCP

### 1. 准备服务端

要求：Python 3.11+，以及 [uv](https://docs.astral.sh/uv/)。

```powershell
git clone https://github.com/neystan/rag-mcp.git
Set-Location rag-mcp
uv sync
Copy-Item config/settings.example.yaml config/settings.yaml
```

编辑 `config/settings.yaml`，配置所需的 LLM、Embedding、向量库和 API Key。该文件用于保存本地密钥，不应提交到 Git。

将 PDF 放到 `data/input/`，再创建一个逻辑知识库集合：

```powershell
uv run python scripts/ingest.py --path data/input --collection company-docs
```

### 2. 在 MCP Client 中配置 stdio

`stdio` 是默认方式，适合 Claude Desktop、Codex、VS Code 扩展或其他能够拉起本地子进程的客户端。将下面的内容合并到客户端 MCP 配置中，并替换项目绝对路径。

```json
{
  "mcpServers": {
    "rag-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\rag-mcp",
        "run",
        "python",
        "scripts/start_mcp_server.py",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

> 客户端进程必须能找到 `uv`。若不在 `PATH` 中，请将 `command` 改为 `uv` 的绝对路径。

### 3. 验证

重启或重新连接 MCP Client 后，客户端应发现以下三个工具：

| Tool | 用途 |
|---|---|
| `query_knowledge_hub` | 查询知识库，返回可读结果和结构化检索数据。 |
| `list_collections` | 列出当前可查询的逻辑集合。 |
| `get_document_summary` | 获取指定文档的标题、摘要和标签。 |

先调用 `list_collections`，确认 `company-docs` 已存在；然后使用自然语言调用 `query_knowledge_hub`。

## MCP 工具契约

### `query_knowledge_hub`

查询本地知识库。服务会执行 Dense + Sparse 混合检索、融合和可选重排，并返回带来源信息的结果。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `query` | string | 是 | 用户问题或检索语句，不能为空。 |
| `top_k` | integer | 否 | 返回条数；正整数。省略时使用 `retrieval.top_k` 配置。 |
| `collection` | string | 否 | 仅检索指定逻辑集合。 |

调用示例：

```json
{
  "query": "员工请假流程是什么？",
  "top_k": 3,
  "collection": "company-docs"
}
```

结果包含可读 Markdown，以及供 Agent 消费的结构化内容。检索条目会尽可能给出源文件路径、页码和得分；具体字段取决于已摄取文档的元数据。

### `list_collections`

列出可检索的逻辑集合及其文档、分块数量。无参数。

```json
{}
```

当尚未摄取任何文档时，工具会明确提示先运行 `ingest.py`。

### `get_document_summary`

获取单个文档的摘要信息。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `doc_id` | string | 是 | 文档标识。当前实现使用摄取时记录的 `source_path`。 |

```json
{
  "doc_id": "data/input/员工手册.pdf"
}
```

返回字段包括 `doc_id`、`title`、`summary`、`tags` 和 `source_path`。若找不到文档，MCP 会返回工具级错误。

## HTTP 接入

对于无法启动本地子进程的客户端，可启动 Streamable HTTP：

```powershell
uv run python scripts/start_mcp_server.py `
  --transport streamable-http `
  --host 127.0.0.1 `
  --port 8000
```

端点为：`http://127.0.0.1:8000/mcp`

建议仅绑定 loopback 地址，或将服务部署在受控私有网络中。HTTP 模式没有在本项目中实现认证、多租户隔离或公网暴露保护。

## 知识库准备与本地查询

### 摄取 PDF

```powershell
uv run python scripts/ingest.py `
  --path data/input `
  --collection company-docs
```

支持输入单个 PDF 或包含 PDF 的目录。默认会做去重；需要重新处理时使用 `--force`：

```powershell
uv run python scripts/ingest.py `
  --path data/input/员工手册.pdf `
  --collection company-docs `
  --force
```

### 在接入前调试检索

```powershell
uv run python scripts/query.py `
  --query "员工请假流程是什么？" `
  --collection company-docs `
  --verbose
```

`--verbose` 会显示 Dense、Sparse、融合和重排阶段的中间结果。若只想跳过重排，可增加 `--no-rerank`。

## 配置

以 `config/settings.example.yaml` 为起点。主要配置区域如下：

| 区域 | 作用 |
|---|---|
| `llm` / `vision_llm` | 文本与视觉模型配置。 |
| `embedding` | 文档向量化模型和连接信息。 |
| `splitter` | 文本分块策略、块大小和重叠长度。 |
| `vector_store` | 向量库提供方、持久化目录与物理 collection。 |
| `retrieval` | 默认返回数量和检索模式。 |
| `rerank` | 可选重排模型及其返回数量。 |
| `ingestion` | LLM 分块优化、元数据增强和图片描述开关。 |
| `observability` | 日志级别与日志文件路径。 |

项目通过工厂模块适配 LLM、Embedding、Reranker 和 Vector Store；可根据已有实现切换 Provider。默认数据和索引位于 `data/`，日志位于 `logs/`。

## Docker

先在宿主机准备配置和数据目录：

```powershell
Copy-Item config/settings.example.yaml config/settings.yaml
New-Item -ItemType Directory -Force data, logs
```

启动 MCP HTTP 服务：

```powershell
docker compose up --build rag-mcp
```

当前 Compose 配置将容器 `8000` 端口映射到宿主机 loopback 的 `8010`，因此本机 MCP 地址为：

```text
http://127.0.0.1:8010/mcp
```

在 Compose 网络内，其他服务可通过下列地址访问：

```text
http://rag-mcp:8000/mcp
```

摄取和调试查询也可以在容器中执行：

```powershell
docker compose run --rm dashboard python scripts/ingest.py `
  --path data/input `
  --collection company-docs

docker compose run --rm dashboard python scripts/query.py `
  --query "员工请假流程是什么？" `
  --collection company-docs `
  --verbose
```

若 MCP Client 需要由 Docker 以 stdio 启动：

```powershell
docker build -t rag-mcp:local .
docker run --rm -i `
  -v "${PWD}/config/settings.yaml:/app/config/settings.yaml:ro" `
  -v "${PWD}/data:/app/data" `
  -v "${PWD}/logs:/app/logs" `
  rag-mcp:local
```

## Dashboard

Dashboard 是本项目的本地运维与质量观察界面，不是 MCP 接入所必需的组件。它读取同一份配置、数据目录和 Trace 日志，适合在调试知识库质量或调整检索配置时使用。

```powershell
uv run python scripts/start_dashboard.py
```

启动后访问：[http://localhost:8501/](http://localhost:8501/)

### Dashboard 页面

| 页面 | 用途 |
|---|---|
| 系统总览 | 显示当前模型、Embedding、向量库和重排组件配置，以及集合、文档、Chunk、图片数量与持久化路径。 |
| 数据浏览器 | 浏览已入库的数据资产和集合信息。 |
| Ingestion 管理 | 在浏览器上传 PDF、选择或新建逻辑集合、观察加载/切分/增强/编码/写入进度，并管理或删除已入库文档。 |
| Ingestion 追踪 | 查看每次摄取的历史记录、总耗时、阶段瀑布图和原始 Trace。 |
| Query 追踪 | 查看查询预处理、Dense 检索、BM25 检索、融合与重排等阶段的执行明细。 |
| 评估面板 | 加载 Golden Test Set，选择评估后端，运行评测并查看总体指标、逐题上下文、检索 ID、回答和历史对比。 |

### RAGAS 与 Golden Test Set 评测

项目可通过 `evaluation.provider: ragas` 使用 RAGAS 评估器，也保留无需 LLM 的轻量 `custom` 评估器。评测执行器会读取 Golden Test Set，对每条用例执行检索；若用例未提供答案和上下文，则基于召回内容生成评测答案，再计算指定指标。

Golden Test Set 是一个 JSON 文件，顶层包含非空的 `test_cases`。单条用例至少需要问题和参考答案：

```json
{
  "test_cases": [
    {
      "question": "员工请假流程是什么？",
      "reference": "员工需提交请假申请并由直属主管审批。",
      "expected_sources": ["员工手册.pdf"]
    }
  ]
}
```

还可选填 `answer`、`contexts`、`expected_chunk_ids` 和 `expected_sources`，以固定生成答案、上下文或期望召回目标。

RAGAS 默认评估以下指标：

| 指标 | 含义 |
|---|---|
| `context_precision` | 召回上下文中与问题相关内容的精确程度。 |
| `context_recall` | 召回上下文对参考答案所需信息的覆盖程度。 |
| `faithfulness` | 生成答案是否受已提供上下文支撑。 |
| `answer_relevancy` | 生成答案与用户问题的相关程度。 |

在 Dashboard 的“评估面板”中可直接预览测试集、选择后端、查看进度与逐题结果；也可从命令行运行：

```powershell
uv run python scripts/evaluate.py --test-set tests/fixtures/golden_test_set.json
```

评测会使用配置中的模型与 Embedding。RAGAS 模式会产生模型调用成本，并要求所配置的 Provider 能被 RAGAS 适配层支持。

Docker 方式：

```powershell
docker compose up --build dashboard
```

## 工作方式

```text
MCP Client
    |
    | stdio 或 Streamable HTTP
    v
FastMCP Tool Catalog
    +-- query_knowledge_hub
    +-- list_collections
    +-- get_document_summary
    |
    v
RAG 查询服务
    +-- Dense Retrieval
    +-- BM25 Sparse Retrieval
    +-- Fusion
    +-- Optional Reranking
    |
    v
Chroma 持久化向量库 + 本地 BM25 索引
```

文档摄取链路为：PDF 加载 -> 分块 -> 可选的 LLM 优化、元数据增强和图片描述 -> 向量写入与 BM25 建索引。

## 安全与边界

- `config/settings.yaml` 可能包含模型密钥，必须保持在本地且不得提交。
- MCP 工具读取本地索引与已摄取文档元数据；模型供应商会接收由当前配置和功能决定的文本或图像内容。
- HTTP 模式默认建议只绑定 `127.0.0.1`。将其暴露到局域网或公网前，须自行提供认证、授权、TLS、网络隔离和访问审计。
- 本项目提供检索能力，不保证模型生成内容的事实正确性。Agent 应将来源信息用于复核，而不是把检索结果视为最终事实。
- 当前项目不实现多租户隔离；不要让互不可信的用户共享同一数据目录和 MCP 服务实例。

## 已知限制

- 当前摄取入口仅接受 PDF。
- `list_collections` 与 `get_document_summary` 当前要求 Chroma 作为向量库提供方。
- `get_document_summary.doc_id` 使用源文件路径，而非独立的全局文档 ID。
- 认证、授权、多租户隔离和公网安全部署不在项目范围内。

## 许可证

本项目采用 MIT 许可证，详见 [`LICENSE`](LICENSE)。
