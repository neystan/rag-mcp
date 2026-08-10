"""Start the MCP stdio server from the repository root."""

from __future__ import annotations

import os
from pathlib import Path
import sys

from mcp_server.server import main


def _chdir_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)


if __name__ == "__main__":
    _chdir_repo_root()
    raise SystemExit(main(sys.argv[1:]))
