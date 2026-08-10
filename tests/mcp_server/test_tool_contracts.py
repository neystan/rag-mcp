from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.errors import ToolInputError
from mcp_server.tools.query_knowledge_hub import query_knowledge_hub


def _write_settings(path: Path, *, top_k: int = 7) -> Path:
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
                "  persist_path: data/db/chroma",
                "retrieval:",
                f"  top_k: {top_k}",
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


def test_query_forwards_explicit_top_k(tmp_path: Path) -> None:
    seen: list[int] = []
    settings_path = _write_settings(tmp_path / "settings.yaml")

    result = query_knowledge_hub(
        "What changed?",
        top_k=3,
        executor=lambda query, top_k, collection: seen.append(top_k) or [],
        settings_path=settings_path,
    )

    assert seen == [3]
    assert result["structuredContent"] == {
        "query": "What changed?",
        "resultCount": 0,
        "citations": [],
        "results": [],
    }


def test_query_rejects_non_positive_top_k(tmp_path: Path) -> None:
    settings_path = _write_settings(tmp_path / "settings.yaml")

    with pytest.raises(ToolInputError, match="top_k"):
        query_knowledge_hub(
            "What changed?",
            top_k=0,
            executor=lambda query, top_k, collection: [],
            settings_path=settings_path,
        )
