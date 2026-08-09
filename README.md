# Modular RAG MCP Server

## 项目简介

Modular RAG MCP Server 是一个本地优先、可插拔的 RAG 服务，通过 MCP 协议向 Copilot、Claude 等 AI 客户端提供知识库检索能力。

项目包含：

- PDF 文档摄取、切分、向量化和持久化；
- Dense + Sparse 混合检索与可选重排；
- MCP 工具：`query_knowledge_hub`、`list_collections`、`get_document_summary`；
- Streamlit Dashboard，用于查看数据、摄取过程和查询追踪；
- LLM、Embedding、Reranker、Vector Store 等模块的可插拔配置。

## 使用开始

### 1. 克隆项目

```bash
git clone https://github.com/neystan/rag-mcp.git
cd rag-mcp
```

### 2. 安装依赖

项目使用 `uv` 管理依赖：

```bash
uv sync
```

### 3. 准备配置

复制脱敏配置模板：

```bash
cp config/settings.example.yaml config/settings.yaml
```

然后编辑 `config/settings.yaml`，至少填写对应的 Provider、模型、向量库和 API Key。该文件已被 `.gitignore` 忽略，不要提交真实密钥。

### 4. 摄取文档

将 PDF 文件放入本地 `data/input/` 目录，然后执行：

```bash
uv run python scripts/ingest.py \
  --path data/input/ \
  --collection demo
```

### 5. 查询知识库

```bash
uv run python scripts/query.py \
  --query "What is Modular RAG?" \
  --collection demo \
  --verbose
```

### 6. 启动 Dashboard

```bash
uv run python scripts/start_dashboard.py
```

### 7. 启动 MCP Server

```bash
uv run python scripts/start_mcp_server.py
```

MCP 客户端使用 stdio 方式连接，工作目录应设置为项目根目录。

### 8. 使用 Docker

Docker 部署不要求宿主机安装 `uv`。先准备本地配置和数据目录：

```bash
cp config/settings.example.yaml config/settings.yaml
mkdir -p data logs
```

启动 Dashboard：

```bash
docker compose up --build dashboard
```

启动后访问 <http://localhost:8501>。

也可以直接在容器中摄取文档和执行查询，不需要在宿主机安装 `uv`：

```bash
docker compose run --rm dashboard \
  python scripts/ingest.py \
  --path data/input/ \
  --collection demo

docker compose run --rm dashboard \
  python scripts/query.py \
  --query "What is Modular RAG?" \
  --collection demo \
  --verbose
```

如果需要让 MCP 客户端通过 Docker 启动 stdio Server：

```bash
docker build -t modular-rag-mcp:local .
docker run --rm -i \
  -v "$PWD/config/settings.yaml:/app/config/settings.yaml:ro" \
  -v "$PWD/data:/app/data" \
  -v "$PWD/logs:/app/logs" \
  modular-rag-mcp:local
```
