# syntax=docker/dockerfile:1
#
# Build from the repository root (the build context is the whole repo):
#   docker build -f deploy/Dockerfile -t asciicharts .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ASCIICHARTS_STATS=off

WORKDIR /app
COPY python/pyproject.toml python/README.md python/LICENSE ./
COPY python/asciicharts.py ./
COPY python/server ./server
RUN pip install ".[stats]" && useradd --system --no-create-home app
USER app

# By default the server speaks MCP over stdio, so it must be run with
# `docker run -i` (an MCP client typically manages this via its own config).
# Setting PORT switches it to a long-running HTTP server instead, serving MCP
# at /mcp and a plain health check at /healthz — see deploy/docker-compose.yml's
# "web" service and docs/development.md.
#
# Anonymous usage statistics are OFF (ASCIICHARTS_STATS=off above). To record them
# in Postgres, override at run time:
#   docker run --rm -e PORT=8080 -p 8080:8080 \
#     -e ASCIICHARTS_STATS=on -e DATABASE_URL=postgres://user:pass@host:5432/db asciicharts
EXPOSE 8080
ENTRYPOINT ["asciicharts-mcp"]
