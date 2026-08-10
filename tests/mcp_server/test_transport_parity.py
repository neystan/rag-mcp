from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import socket
import subprocess
import sys
from typing import AsyncIterator

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client


EXPECTED_TOOLS = [
    "get_document_summary",
    "list_collections",
    "query_knowledge_hub",
]


def _write_settings(path: Path) -> Path:
    persist_path = (path.parent / "chroma").as_posix()
    path.write_text(
        "\n".join(
            [
                "app:",
                "  name: test-rag-mcp",
                "llm:",
                "  provider: test",
                "embedding:",
                "  provider: test",
                "splitter:",
                "  provider: recursive",
                "vector_store:",
                "  provider: chroma",
                "  collection: test",
                f"  persist_path: {persist_path}",
                "retrieval:",
                "  top_k: 3",
                "rerank:",
                "  provider: none",
                "evaluation:",
                "  provider: none",
                "observability:",
                "  log_level: INFO",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


async def _tool_names_from_stdio(settings_path: Path) -> list[str]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "scripts/start_mcp_server.py",
            "--transport",
            "stdio",
            "--settings",
            str(settings_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
    )
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            result = await session.list_tools()
    return sorted(tool.name for tool in result.tools)


async def _tool_names_from_http(port: int) -> list[str]:
    async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as streams:
        async with ClientSession(*streams[:2]) as session:
            await session.initialize()
            result = await session.list_tools()
    return sorted(tool.name for tool in result.tools)


async def _empty_query_is_tool_error_over_stdio(settings_path: Path) -> tuple[bool, str]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "scripts/start_mcp_server.py",
            "--transport",
            "stdio",
            "--settings",
            str(settings_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
    )
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool("query_knowledge_hub", {"query": ""})
    return result.isError, result.content[0].text


async def _empty_query_is_tool_error_over_http(port: int) -> tuple[bool, str]:
    async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as streams:
        async with ClientSession(*streams[:2]) as session:
            await session.initialize()
            result = await session.call_tool("query_knowledge_hub", {"query": ""})
    return result.isError, result.content[0].text


async def _list_collections_over_stdio(settings_path: Path) -> tuple[bool, str, dict[str, object] | None]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "scripts/start_mcp_server.py",
            "--transport",
            "stdio",
            "--settings",
            str(settings_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
    )
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool("list_collections", {})
    return result.isError, result.content[0].text, result.structuredContent


async def _list_collections_over_http(port: int) -> tuple[bool, str, dict[str, object] | None]:
    async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as streams:
        async with ClientSession(*streams[:2]) as session:
            await session.initialize()
            result = await session.call_tool("list_collections", {})
    return result.isError, result.content[0].text, result.structuredContent


@asynccontextmanager
async def _http_server(settings_path: Path, port: int) -> AsyncIterator[None]:
    root = Path(__file__).resolve().parents[2]
    process = subprocess.Popen(
        [
            sys.executable,
            "scripts/start_mcp_server.py",
            "--transport",
            "streamable-http",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--settings",
            str(settings_path),
        ],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        for _ in range(100):
            if process.poll() is not None:
                _, stderr = process.communicate(timeout=1)
                raise RuntimeError(f"HTTP MCP server exited early: {stderr}")
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
            except OSError:
                await asyncio.sleep(0.05)
                continue
            writer.close()
            await writer.wait_closed()
            break
        else:
            raise TimeoutError("HTTP MCP server did not bind its port")
        yield
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@pytest.mark.anyio
async def test_stdio_and_streamable_http_publish_the_same_tool_catalog(tmp_path: Path) -> None:
    settings_path = _write_settings(tmp_path / "settings.yaml")
    port = _free_port()

    stdio_names = await _tool_names_from_stdio(settings_path)
    async with _http_server(settings_path, port):
        http_names = await _tool_names_from_http(port)

    assert stdio_names == EXPECTED_TOOLS
    assert http_names == EXPECTED_TOOLS


@pytest.mark.anyio
async def test_invalid_query_is_a_tool_error_for_both_transports(tmp_path: Path) -> None:
    settings_path = _write_settings(tmp_path / "settings.yaml")
    port = _free_port()

    stdio_error = await _empty_query_is_tool_error_over_stdio(settings_path)
    async with _http_server(settings_path, port):
        http_error = await _empty_query_is_tool_error_over_http(port)

    assert stdio_error[0] is True
    assert http_error[0] is True
    assert "query is required" in stdio_error[1]
    assert "query is required" in http_error[1]


@pytest.mark.anyio
async def test_list_collections_result_is_equivalent_for_both_transports(tmp_path: Path) -> None:
    settings_path = _write_settings(tmp_path / "settings.yaml")
    port = _free_port()

    stdio_result = await _list_collections_over_stdio(settings_path)
    async with _http_server(settings_path, port):
        http_result = await _list_collections_over_http(port)

    assert stdio_result == http_result
    assert stdio_result == (
        False,
        "当前没有可用集合，请先运行 ingest.py 摄取文档。",
        {"collections": [], "count": 0},
    )
