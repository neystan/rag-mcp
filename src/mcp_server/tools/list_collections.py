"""集合列表工具。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from core.settings import load_settings
from mcp_server.protocol_handler import ProtocolHandlerError, ToolDefinition


DEFAULT_SETTINGS_PATH = Path("config/settings.yaml")


def build_list_collections_tool(settings_path: str | Path = DEFAULT_SETTINGS_PATH) -> ToolDefinition:
    """构建读取向量库集合的 Tool 定义。"""

    def handler(arguments: dict[str, Any]) -> dict[str, object]:
        """忽略参数并读取当前配置的集合。"""
        del arguments
        return list_collections(settings_path)

    return ToolDefinition(
        name="list_collections",
        description="列出当前知识库中可用于查询的文档集合",
        input_schema={
            "type": "object",
            "properties": {},
        },
        handler=handler,
    )


def list_collections(settings_path: str | Path = DEFAULT_SETTINGS_PATH) -> dict[str, object]:
    """按 Chroma metadata.collection 返回可查询集合。"""
    settings = load_settings(settings_path)
    vector_store = settings.vector_store
    provider = str(vector_store.get("provider", "")).strip().lower()
    if provider != "chroma":
        raise ProtocolHandlerError(f"unsupported vector store provider for list_collections: {provider}")

    persist_path = str(vector_store.get("persist_path", "data/db/chroma"))
    physical_collection = str(vector_store.get("collection", "default")).strip() or "default"
    client = chromadb.PersistentClient(path=persist_path)
    names = {str(getattr(item, "name", item)) for item in client.list_collections()}
    collections = _summarize_collections(client, physical_collection) if physical_collection in names else []
    if not collections:
        return {
            "content": [{"type": "text", "text": "当前没有可用集合，请先运行 ingest.py 摄取文档。"}],
            "structuredContent": {"collections": [], "count": 0},
        }

    lines = ["可用集合：", ""]
    for index, item in enumerate(collections, start=1):
        lines.append(f"{index}. {item['name']} ({item['documentCount']} documents, {item['chunkCount']} chunks)")
    return {
        "content": [{"type": "text", "text": "\n".join(lines)}],
        "structuredContent": {"collections": collections, "count": len(collections)},
    }


def _summarize_collections(client: Any, physical_collection: str) -> list[dict[str, object]]:
    """聚合当前 Chroma 物理集合中的逻辑集合统计。"""
    payload = client.get_collection(name=physical_collection).get(include=["metadatas"])
    document_ids: dict[str, set[str]] = {}
    chunk_counts: dict[str, int] = {}
    for chunk_id, raw_metadata in zip(payload.get("ids", []), payload.get("metadatas", []), strict=False):
        metadata = dict(raw_metadata or {})
        name = str(metadata.get("collection", physical_collection)).strip() or physical_collection
        source_path = str(metadata.get("source_path", "")).strip() or str(chunk_id)
        document_ids.setdefault(name, set()).add(source_path)
        chunk_counts[name] = chunk_counts.get(name, 0) + 1
    return [
        {
            "name": name,
            "documentCount": len(document_ids[name]),
            "chunkCount": chunk_counts[name],
        }
        for name in sorted(chunk_counts)
    ]
