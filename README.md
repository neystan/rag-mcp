# Modular RAG MCP Server

> 一个可插拔、可观测的模块化 RAG（检索增强生成）服务框架，通过 MCP（Model Context Protocol）协议对外暴露工具接口，支持 Copilot / Claude 等 AI 助手直接调用

### 不只是项目，更是一整套思路

**比这个项目本身更有价值的，是它背后蕴含的一整套工程化思路**：

- 如何编写 **DEV_SPEC**（开发规格文档）来驱动开发
- 如何用 **Skill** 基于 Spec 自动完成代码编写
- 如何用 **Skill** 进行自动化测试、打包、环境配置
- 如何基于可插拔架构进行扩展（比如扩展到 Agent）

**学会了思路，你可以自己做全新的项目和扩展**。以上每一步的具体做法、设计思路，在笔记中都有对应的视频讲解，建议配合观看。

### 核心能力一览

| 模块 | 能力 | 说明 |
|------|------|------|
| **Ingestion Pipeline** | PDF → Markdown → Chunk → Transform → Embedding → Upsert | 全链路数据摄取，支持多模态图片描述（Image Captioning） |
| **Hybrid Search** | Dense (向量) + Sparse (BM25) + RRF Fusion + Rerank | 粗排召回 + 精排重排的两段式检索架构 |
| **MCP Server** | 标准 MCP 协议暴露 Tools | `query_knowledge_hub`、`list_collections`、`get_document_summary` |
| **Dashboard** | Streamlit 六页面管理平台 | 系统总览 / 数据浏览 / Ingestion 管理 / 摄取追踪 / 查询追踪 / 评估面板 |
| **Evaluation** | Ragas + Custom 评估体系 | 支持 golden test set 回归测试，拒绝"凭感觉"调优 |
| **Observability** | 全链路白盒化追踪 | Ingestion 与 Query 两条链路的每一个中间状态透明可见 |
| **Skill 驱动全流程** | 从编写到测试、打包、配置一键完成 | auto-coder / qa-tester / package / setup 等 Skill 覆盖完整开发生命周期（笔记中每个 Skill 的使用和设计思路均有讲解，请参考配套视频） |

### 技术亮点

**🔌 全链路可插拔架构**：LLM / Embedding / Reranker / Splitter / VectorStore / Evaluator 每一个核心环节均定义了抽象接口，支持"乐高积木式"替换，通过配置文件一键切换后端，零代码修改。

**🔍 混合检索 + 重排**：BM25 稀疏检索解决专有名词精确匹配 + Dense Embedding 解决同义词语义匹配，RRF 融合后可选 Cross-Encoder / LLM Rerank 精排，平衡查全率与查准率。

**🖼️ 多模态图像处理**：采用 Image-to-Text 策略，利用 Vision LLM 自动生成图片描述并缝合进 Chunk，复用纯文本 RAG 链路即可实现"搜文字出图"。

**📡 MCP 生态集成**：遵循 Model Context Protocol 标准，可直接对接 GitHub Copilot、Claude Desktop 等 MCP Client，零前端开发，一次开发处处可用。

**📊 可视化管理 + 自动化评估**：Streamlit Dashboard 提供完整的数据管理与链路追踪能力，集成 Ragas 等评估框架，建立基于数据的迭代反馈回路。

**🧪 三层测试体系**：Unit / Integration / E2E 分层测试，覆盖独立模块逻辑、模块间交互、完整链路（MCP Client / Dashboard）。

**🤖 Skill 驱动全流程**：内置 auto-coder（自动编码）、qa-tester（自动测试）、package（清理打包）、setup（一键配置）等 Agent Skill，覆盖从代码编写到测试、打包、部署的完整开发生命周期。每个 Skill 的使用方法和设计思路在笔记的项目部分均有讲解视频，可参考学习。

> 📖 详细架构设计、模块说明和任务排期请参阅 [DEV_SPEC.md](DEV_SPEC.md)

---
---

## 🚀 快速开始

### 1. 克隆项目并进入目录

```bash
git clone <repo-url>
cd MODULAR-RAG-MCP
```

### 2. 安装依赖

推荐使用 `uv`：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

如果你已经安装了 `uv`，直接执行：

```bash
uv sync
```

### 3. 准备配置

项目默认读取 `config/settings.yaml`。运行前至少确认：

- `llm.provider` / `llm.model`
- `embedding.provider` / `embedding.model`
- `vector_store.provider` / `vector_store.persist_path`
- `retrieval.top_k`
- `rerank.provider`
- `evaluation.provider`

建议不要把真实 `api_key` 提交到仓库。开发时可先写本地配置，提交前再改成环境变量注入。

### 4. 摄取示例数据

```bash
uv run python scripts/ingest.py \
  --path tests/fixtures/sample_documents/ \
  --collection demo
```

### 5. 执行一次查询

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

### 8. 运行评估

```bash
uv run python scripts/evaluate.py \
  --test-set tests/fixtures/golden_test_set.json
```

### 9. 可选：一键配置（Setup Skill）

本项目提供了 **Setup Skill** 一键完成 Provider 选择、API Key 配置、依赖安装、配置文件生成和 Dashboard 启动。

在 VS Code 中打开项目，通过 Copilot / Claude 对话框输入：

```text
setup
```

Agent 会自动引导你完成全部配置流程；如果你想完全手动控制环境，也可以直接按上面的 CLI 步骤走通。

---

## ⚙️ 配置说明

`config/settings.yaml` 当前主要包含这些部分：

```yaml
app:
  name: modular-rag-mcp
  environment: local

llm:
  provider: qwen
  model: kimi-k2.5

vision_llm:
  provider: qwen
  model: kimi-k2.5

embedding:
  provider: qwen
  model: text-embedding-v4

splitter:
  provider: recursive
  chunk_size: 500
  chunk_overlap: 100

vector_store:
  provider: chroma
  collection: default
  persist_path: data/db/chroma

retrieval:
  top_k: 3
  mode: hybrid

rerank:
  provider: qwen
  model: qwen3-rerank

evaluation:
  provider: ragas
  enabled: true
```

各字段作用：

- `app`：项目名和环境标记。
- `llm`：回答生成、评估生成等文本模型配置。
- `vision_llm`：图片理解与图生文配置。
- `embedding`：向量编码模型配置。
- `splitter`：切块策略和参数。
- `vector_store`：向量库 provider、collection 和持久化路径。
- `retrieval`：检索层参数，比如 `top_k`、检索模式。
- `rerank`：重排模型配置。
- `evaluation`：评估后端，支持 `custom`、`ragas` 或 `backends` 组合。
- `observability`：日志配置。
- `ingestion`：摄取增强开关，如 `chunk_refiner`、`metadata_enricher`、`image_captioner`。

---

## 🔌 MCP 配置示例

### GitHub Copilot `mcp.json`

```json
{
  "servers": {
    "modular-rag-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "scripts/start_mcp_server.py"]
    }
  }
}
```

### Claude Desktop `claude_desktop_config.json`

```json
{
  "mcpServers": {
    "modular-rag-mcp": {
      "command": "uv",
      "args": ["run", "python", "scripts/start_mcp_server.py"],
      "cwd": "/absolute/path/to/MODULAR-RAG-MCP"
    }
  }
}
```

当前 MCP Server 暴露的核心工具：

- `query_knowledge_hub`
- `list_collections`
- `get_document_summary`

---

## 🖥️ Dashboard 使用指南

启动命令：

```bash
uv run python scripts/start_dashboard.py
```

页面说明：

- `系统总览`：查看当前 provider、模型、向量库路径和数据资产统计。
- `数据浏览器`：查看已摄入文档、chunk 和图片详情。
- `Ingestion 管理`：上传 PDF、触发摄取、删除文档。
- `Ingestion 追踪`：查看摄取阶段耗时和 trace 细节。
- `Query 追踪`：查看 Dense / Sparse / Fusion / Rerank 的变化。
- `评估面板`：运行 golden test set，查看进度条、历史记录和各 case 指标。

推荐操作顺序：

1. 先在 `Ingestion 管理` 上传或摄取文档。
2. 到 `数据浏览器` 确认文档和 chunk 已入库。
3. 通过 CLI 或 `Query 追踪` 验证查询链路。
4. 最后在 `评估面板` 跑 `custom` 或 `ragas` 评估。

---