from __future__ import annotations

import pytest
from mcp.types import CallToolResult, ImageContent, TextContent

from mcp_server.app import create_mcp_server, payload_to_call_tool_result


@pytest.mark.anyio
async def test_fastmcp_catalog_contains_stable_rag_tools() -> None:
    app = create_mcp_server()

    tools = await app.list_tools()

    assert {tool.name for tool in tools} == {
        "query_knowledge_hub",
        "list_collections",
        "get_document_summary",
    }


def test_payload_adapter_preserves_text_structured_content_and_images() -> None:
    payload = {
        "content": [
            {"type": "text", "text": "A cited answer"},
            {"type": "image", "mimeType": "image/png", "data": "aW1hZ2U="},
        ],
        "structuredContent": {"source": "manual.pdf", "page": 2},
    }

    result = payload_to_call_tool_result(payload)

    assert isinstance(result, CallToolResult)
    assert result.structuredContent == {"source": "manual.pdf", "page": 2}
    assert result.content == [
        TextContent(type="text", text="A cited answer"),
        ImageContent(type="image", mimeType="image/png", data="aW1hZ2U="),
    ]
