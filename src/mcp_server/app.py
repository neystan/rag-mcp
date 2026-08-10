"""FastMCP application factory for the RAG tool catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, ImageContent, TextContent

from mcp_server.tools.get_document_summary import get_document_summary as load_document_summary
from mcp_server.tools.list_collections import list_collections as load_collections
from mcp_server.tools.query_knowledge_hub import query_knowledge_hub as run_knowledge_query


def create_mcp_server(
    settings_path: str | Path = "config/settings.yaml",
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    streamable_http_path: str = "/mcp",
) -> FastMCP:
    """Create the single MCP capability catalog for every transport."""

    normalized_settings_path = Path(settings_path)
    server = FastMCP(
        "rag-mcp",
        instructions="Query and inspect the local RAG knowledge hub.",
        host=host,
        port=port,
        streamable_http_path=streamable_http_path,
    )

    @server.tool(
        name="query_knowledge_hub",
        description="Query the knowledge hub and return cited Markdown results.",
    )
    def query_knowledge_hub(
        query: str,
        top_k: int | None = None,
        collection: str | None = None,
    ) -> CallToolResult:
        return payload_to_call_tool_result(
            run_knowledge_query(
                query,
                top_k=top_k,
                collection=collection,
                settings_path=normalized_settings_path,
            )
        )

    @server.tool(
        name="list_collections",
        description="List the document collections available to query.",
    )
    def list_knowledge_collections() -> CallToolResult:
        return payload_to_call_tool_result(load_collections(normalized_settings_path))

    @server.tool(
        name="get_document_summary",
        description="Return the title, summary, and tags for a document ID.",
    )
    def get_knowledge_document_summary(doc_id: str) -> CallToolResult:
        return payload_to_call_tool_result(
            load_document_summary(doc_id, settings_path=normalized_settings_path)
        )

    return server


def payload_to_call_tool_result(payload: dict[str, object]) -> CallToolResult:
    """Map the existing RAG response contract to official MCP result types."""

    content = [_content_block(item) for item in _content_items(payload)]
    structured_content = payload.get("structuredContent")
    if structured_content is not None and not isinstance(structured_content, dict):
        raise ValueError("structuredContent must be an object")
    return CallToolResult(content=content, structuredContent=structured_content)


def _content_items(payload: dict[str, object]) -> list[dict[str, Any]]:
    raw_content = payload.get("content", [])
    if not isinstance(raw_content, list):
        raise ValueError("content must be a list")
    if not all(isinstance(item, dict) for item in raw_content):
        raise ValueError("content items must be objects")
    return [dict(item) for item in raw_content]


def _content_block(item: dict[str, Any]) -> TextContent | ImageContent:
    item_type = item.get("type")
    if item_type == "text":
        text = item.get("text")
        if not isinstance(text, str):
            raise ValueError("text content requires text")
        return TextContent(type="text", text=text)
    if item_type == "image":
        mime_type = item.get("mimeType")
        data = item.get("data")
        if not isinstance(mime_type, str) or not isinstance(data, str):
            raise ValueError("image content requires mimeType and data")
        return ImageContent(type="image", mimeType=mime_type, data=data)
    raise ValueError(f"unsupported RAG content type: {item_type}")
