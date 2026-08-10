"""Launch the RAG FastMCP application over stdio or Streamable HTTP."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from core.settings import SettingsError, load_settings
from mcp_server.app import create_mcp_server
from observability.logger import get_logger


Transport = Literal["stdio", "streamable-http"]


@dataclass(frozen=True, slots=True)
class ServerOptions:
    """Validated launch settings for a single FastMCP application."""

    transport: Transport
    host: str
    port: int
    path: str
    settings_path: str


def parse_args(argv: Sequence[str] | None = None) -> ServerOptions:
    """Parse launcher arguments without constructing a transport."""

    parser = argparse.ArgumentParser(description="Run the rag-mcp server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport to run (default: stdio).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host.")
    parser.add_argument("--port", type=_port, default=8000, help="HTTP bind port.")
    parser.add_argument("--path", type=_path, default="/mcp", help="Streamable HTTP path.")
    parser.add_argument(
        "--settings",
        default="config/settings.yaml",
        dest="settings_path",
        help="Path to the RAG settings YAML file.",
    )
    parsed = parser.parse_args(argv)
    return ServerOptions(
        transport=parsed.transport,
        host=parsed.host,
        port=parsed.port,
        path=parsed.path,
        settings_path=parsed.settings_path,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Validate settings, create one application catalog, and run its transport."""

    options = parse_args(argv)
    logger = get_logger(__name__)
    try:
        settings = load_settings(options.settings_path)
    except SettingsError as exc:
        logger.error("configuration failed: %s", exc)
        return 1

    logger.info("mcp server starting: %s (%s)", settings.app["name"], options.transport)
    server = create_mcp_server(
        options.settings_path,
        host=options.host,
        port=options.port,
        streamable_http_path=options.path,
    )
    server.run(transport=options.transport)
    return 0


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def _path(value: str) -> str:
    if not value.startswith("/"):
        raise argparse.ArgumentTypeError("path must start with '/'")
    if value == "/":
        raise argparse.ArgumentTypeError("path must not be '/'")
    return value.rstrip("/")
