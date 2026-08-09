FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Keep the image independent from the host's uv installation.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN python -m pip install --upgrade pip \
    && python -m pip install .

COPY scripts ./scripts
COPY main.py ./main.py
COPY config/settings.example.yaml ./config/settings.example.yaml

RUN mkdir -p /app/config /app/data /app/logs

# Default entrypoint: MCP over stdio.
CMD ["python", "scripts/start_mcp_server.py"]
