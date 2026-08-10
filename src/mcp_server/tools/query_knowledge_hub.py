"""知识库查询工具。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from core.response.multimodal_assembler import MultimodalAssembler
from core.response.response_builder import ResponseBuilder
from core.settings import Settings, load_settings
from core.types import RetrievalResult
from mcp_server.errors import ToolInputError


ToolExecutor = Callable[[str, int, str | None], list[RetrievalResult]]


def query_knowledge_hub(
    query: Any,
    *,
    top_k: Any = None,
    collection: Any = None,
    executor: ToolExecutor | None = None,
    response_builder: ResponseBuilder | None = None,
    multimodal_assembler: MultimodalAssembler | None = None,
    settings_path: str | Path = "config/settings.yaml",
) -> dict[str, object]:
    """执行知识库查询并返回 MCP Tool 结果。"""

    normalized_query = _normalize_query(query)
    normalized_collection = _normalize_collection(collection)
    settings = load_settings(settings_path)
    normalized_top_k = _normalize_top_k(top_k) if top_k is not None else _resolve_top_k(settings)
    active_builder = response_builder or ResponseBuilder()
    active_assembler = multimodal_assembler or MultimodalAssembler()
    active_executor = executor or _build_default_executor(settings_path)

    retrieval_results = active_executor(normalized_query, normalized_top_k, normalized_collection)
    payload = active_builder.build(retrieval_results, normalized_query)
    image_contents = active_assembler.assemble(retrieval_results)
    if image_contents:
        payload["content"].extend(image_contents)
    return payload


def _build_default_executor(settings_path: str | Path) -> ToolExecutor:
    def execute(query: str, top_k: int, collection: str | None) -> list[RetrievalResult]:
        from core.query_service import run_query

        execution = run_query(
            query,
            top_k=top_k,
            collection=collection,
            settings_path=settings_path,
        )
        return execution.final_results

    return execute


def _normalize_query(query: Any) -> str:
    if not isinstance(query, str) or not query.strip():
        raise ToolInputError("query is required")
    return query.strip()


def _normalize_top_k(top_k: Any) -> int:
    if not isinstance(top_k, int) or top_k <= 0:
        raise ToolInputError("top_k must be positive int")
    return top_k


def _resolve_top_k(settings: Settings) -> int:
    return _normalize_top_k(settings.retrieval.get("top_k"))


def _normalize_collection(collection: Any) -> str | None:
    if collection is None:
        return None
    if not isinstance(collection, str):
        raise ToolInputError("collection must be string")
    normalized = collection.strip()
    return normalized or None
