from __future__ import annotations

import pytest

from mcp_server.server import parse_args


def test_server_defaults_to_stdio() -> None:
    options = parse_args([])

    assert options.transport == "stdio"
    assert options.host == "127.0.0.1"
    assert options.port == 8000
    assert options.path == "/mcp"
    assert options.settings_path == "config/settings.yaml"


def test_server_accepts_streamable_http_options() -> None:
    options = parse_args(
        [
            "--transport",
            "streamable-http",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--path",
            "/mcp",
        ]
    )

    assert options.transport == "streamable-http"
    assert options.host == "0.0.0.0"
    assert options.port == 8000
    assert options.path == "/mcp"


@pytest.mark.parametrize("args", [["--port", "0"], ["--path", "mcp"]])
def test_server_rejects_invalid_network_options(args: list[str]) -> None:
    with pytest.raises(SystemExit):
        parse_args(args)
