from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_compose_runs_rag_mcp_as_an_internal_http_service() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))

    service = compose["services"]["rag-mcp"]

    assert service["command"] == [
        "python",
        "scripts/start_mcp_server.py",
        "--transport",
        "streamable-http",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    assert service["expose"] == ["8000"]
    assert service["ports"] == ["127.0.0.1:8010:8000"]


def test_fastmcp_is_the_only_protocol_registry() -> None:
    assert not (ROOT / "src/mcp_server/protocol_handler.py").exists()
    for tool_path in (ROOT / "src/mcp_server/tools").glob("*.py"):
        assert "protocol_handler" not in tool_path.read_text(encoding="utf-8")
