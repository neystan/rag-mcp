# FastMCP Dual Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the handwritten MCP JSON-RPC server with the official Python MCP SDK while serving the same RAG tools over stdio and Streamable HTTP.

**Architecture:** `src/mcp_server/app.py` will be the sole FastMCP application factory. Existing RAG functions remain transport-independent and return their established text plus structured payload; thin FastMCP adapters validate typed inputs, call those functions, and translate results into official MCP content blocks. `server.py` parses launch options and runs the same application with either transport.

**Tech Stack:** Python 3.11, official `mcp` Python SDK/FastMCP, pytest, anyio, uv, Docker Compose.

## Global Constraints

- Preserve the public tool names `query_knowledge_hub`, `list_collections`, and `get_document_summary`.
- Support `--transport stdio` and `--transport streamable-http`; stdio remains the default.
- Mount Streamable HTTP at `/mcp`; the RAG Compose service exposes no host port.
- Do not change ingestion, Chroma persistence, Dashboard, TGA code, or tenant isolation in this work.
- Tool responses must retain human-readable text and structured data; TGA is not expected to consume binary image blocks.
- Make `query_knowledge_hub.top_k` effective rather than silently ignoring a declared parameter.
- Do not delete `protocol_handler.py` until official-client contract tests pass for both transports.

---

### Task 1: Characterize Tool Contracts and Decouple Legacy Errors

**Files:**
- Create: `tests/mcp_server/test_tool_contracts.py`
- Create: `src/mcp_server/errors.py`
- Modify: `src/mcp_server/tools/query_knowledge_hub.py`
- Modify: `src/mcp_server/tools/list_collections.py`
- Modify: `src/mcp_server/tools/get_document_summary.py`

**Interfaces:**
- Produces `ToolInputError(ValueError)` for invalid public tool inputs.
- Produces `query_knowledge_hub(query: str, *, top_k: int | None, collection: str | None, executor: ToolExecutor | None, ...) -> dict[str, object]`.
- `top_k=None` uses `settings.retrieval.top_k`; a supplied positive integer is passed to `executor`.

- [ ] **Step 1: Write failing contract tests**

```python
def test_query_forwards_explicit_top_k(fake_settings_path):
    seen = []
    query_knowledge_hub("What changed?", top_k=3,
        executor=lambda query, top_k, collection: seen.append(top_k) or [])
    assert seen == [3]

def test_query_rejects_non_positive_top_k():
    with pytest.raises(ToolInputError, match="top_k"):
        query_knowledge_hub("What changed?", top_k=0)
```

- [ ] **Step 2: Run the test and verify RED**

Run: `uv run pytest tests/mcp_server/test_tool_contracts.py -q`

Expected: collection fails before implementation or `top_k` remains the configured value.

- [ ] **Step 3: Add `ToolInputError` and replace imports**

Move input validation errors out of `protocol_handler.py`; do not import FastMCP in domain tool modules.

- [ ] **Step 4: Make explicit `top_k` win over configured default**

Use `_normalize_top_k(top_k)` when the argument is not `None`, otherwise use the configured setting.

- [ ] **Step 5: Run the focused test and verify GREEN**

Run: `uv run pytest tests/mcp_server/test_tool_contracts.py -q`

Expected: PASS.

### Task 2: Create the FastMCP Application and Tool Adapters

**Files:**
- Create: `tests/mcp_server/test_fastmcp_contract.py`
- Create: `src/mcp_server/app.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`

**Interfaces:**
- Produces `create_mcp_server(settings_path: str | Path = "config/settings.yaml") -> FastMCP`.
- Exposes the three stable tool names through the official SDK discovery API.
- Tool adapters return MCP text content plus `structuredContent`, or a tool-level error for invalid input.

- [ ] **Step 1: Write failing official-client tests**

```python
@pytest.mark.anyio
async def test_fastmcp_catalog_contains_stable_rag_tools():
    app = create_mcp_server(settings_path=TEST_SETTINGS)
    async with in_memory_client(app) as session:
        tools = await session.list_tools()
    assert {tool.name for tool in tools.tools} == {
        "query_knowledge_hub", "list_collections", "get_document_summary"
    }
```

- [ ] **Step 2: Run the test and verify RED**

Run: `uv run pytest tests/mcp_server/test_fastmcp_contract.py -q`

Expected: FAIL because the application factory and MCP dependency do not exist.

- [ ] **Step 3: Add the official SDK and lock dependencies**

Add the supported `mcp` major version to `pyproject.toml`, run `uv lock`, and do not add a separate third-party FastMCP package.

- [ ] **Step 4: Implement one application factory**

Register typed FastMCP functions. Use tool annotations for JSON Schema, call existing domain functions, and map their `content`/`structuredContent` into official MCP result types. Do not reintroduce JSON framing or direct stdout writes.

- [ ] **Step 5: Verify tool errors are protocol-level results**

Add a case for an empty query and assert `isError` rather than a server crash.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `uv run pytest tests/mcp_server/test_fastmcp_contract.py tests/mcp_server/test_tool_contracts.py -q`

Expected: PASS.

### Task 3: Add a Single Dual-Transport Launcher

**Files:**
- Create: `tests/mcp_server/test_server_options.py`
- Modify: `src/mcp_server/server.py`
- Modify: `scripts/start_mcp_server.py`

**Interfaces:**
- Produces `parse_args(argv: Sequence[str] | None) -> ServerOptions`.
- Accepts `--transport {stdio,streamable-http}`, `--host`, `--port`, and `--path`.
- Defaults to `stdio`; HTTP defaults to `127.0.0.1:8000/mcp` outside Docker.

- [ ] **Step 1: Write failing option tests**

```python
def test_server_defaults_to_stdio():
    assert parse_args([]).transport == "stdio"

def test_server_accepts_streamable_http_options():
    options = parse_args(["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"])
    assert (options.transport, options.host, options.port, options.path) == ("streamable-http", "0.0.0.0", 8000, "/mcp")
```

- [ ] **Step 2: Run the test and verify RED**

Run: `uv run pytest tests/mcp_server/test_server_options.py -q`

Expected: FAIL because `ServerOptions` and `parse_args` do not exist.

- [ ] **Step 3: Implement the launcher**

Load settings once, build the FastMCP application once, and delegate to the SDK-selected transport. Direct diagnostic logs to stderr. Reject invalid ports and paths before starting the server.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `uv run pytest tests/mcp_server/test_server_options.py -q`

Expected: PASS.

### Task 4: Verify Real Stdio and Streamable HTTP Parity

**Files:**
- Create: `tests/mcp_server/test_transport_parity.py`
- Modify: `tests/mcp_server/conftest.py`

**Interfaces:**
- Uses the official SDK `stdio_client` against `scripts/start_mcp_server.py --transport stdio`.
- Uses the official SDK `streamablehttp_client` against a short-lived HTTP server on a free loopback port.

- [ ] **Step 1: Write failing transport parity tests**

```python
@pytest.mark.anyio
async def test_stdio_and_http_publish_the_same_tool_catalog(rag_server):
    stdio_names = await rag_server.list_names("stdio")
    http_names = await rag_server.list_names("streamable-http")
    assert stdio_names == http_names == [
        "get_document_summary", "list_collections", "query_knowledge_hub"
    ]
```

- [ ] **Step 2: Run the test and verify RED**

Run: `uv run pytest tests/mcp_server/test_transport_parity.py -q`

Expected: FAIL until both launcher paths are operational.

- [ ] **Step 3: Implement only missing transport wiring**

Keep the test service isolated in a temporary directory and use injected test settings. Do not require a real LLM, Chroma database, or dashboard process.

- [ ] **Step 4: Verify GREEN and run the full suite**

Run: `uv run pytest -q`

Expected: PASS with no warnings from unclosed sessions or child processes.

### Task 5: Containerize HTTP Mode and Retire the Manual Protocol Layer

**Files:**
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `README.md`
- Delete: `src/mcp_server/protocol_handler.py`
- Modify: `src/mcp_server/__init__.py`

- [ ] **Step 1: Write Docker contract assertions**

Assert that Compose runs `--transport streamable-http --host 0.0.0.0 --port 8000`, retains the existing data/config/log mounts, and has no `ports:` entry for the RAG MCP service.

- [ ] **Step 2: Run the assertion and verify RED**

Run: `uv run pytest tests/mcp_server/test_container_contract.py -q`

Expected: FAIL until the Compose service exists.

- [ ] **Step 3: Configure the image and Compose service**

Keep Dockerfile default `CMD` as stdio. Add a `rag-mcp` Compose service which uses HTTP internally, `expose: ["8000"]`, and existing persistent mounts. Do not publish a host port or add TGA to this Compose file.

- [ ] **Step 4: Remove handwritten protocol code**

Delete `protocol_handler.py` only after no source or test imports remain. The FastMCP factory is the sole server capability registry.

- [ ] **Step 5: Build and smoke-test the image**

Run: `docker compose build rag-mcp`

Run: `docker compose run --rm --no-deps rag-mcp python scripts/start_mcp_server.py --transport stdio`

Expected: image builds; stdio process starts and waits for client input without writing logs to stdout.

- [ ] **Step 6: Update operations documentation**

Document both local commands, the internal `http://rag-mcp:8000/mcp` target for a future shared Compose network, volume persistence, and the fact that this task does not implement multi-tenant authorization.

## Final Verification

- [ ] Run `uv run pytest -q`.
- [ ] Run `python -m compileall src scripts`.
- [ ] Run `docker compose build rag-mcp`.
- [ ] Inspect `git diff --check` if the directory later becomes a Git checkout; otherwise use a whitespace-only scan of touched files.
- [ ] Confirm neither TGA files nor RAG ingestion/query behavior outside the documented `top_k` correction changed.
