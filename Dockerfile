# syntax=docker/dockerfile:1

# --- Build stage --------------------------------------------------------------
FROM python:3.14-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY pyproject.toml README.md ./
COPY src/ ./src/

# `pip wheel .` builds news-monitor-mcp and resolves every transitive
# dependency from pyproject.toml into /wheels. The runtime stage installs
# offline from this directory, so the final image has neither pip's index
# cache nor build toolchain residue.
RUN pip install --upgrade pip wheel \
 && pip wheel -w /wheels .

# --- Runtime stage ------------------------------------------------------------
FROM python:3.14-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    LOG_LEVEL=INFO \
    NEWS_MONITOR_ALERTS_DIR=/data

# Non-root user. Numeric UID/GID so the container also works under
# Kubernetes/OpenShift SecurityContext that forbid name lookups.
RUN groupadd --system --gid 10001 mcp \
 && useradd  --system --uid 10001 --gid 10001 --home-dir /home/mcp --shell /sbin/nologin mcp \
 && mkdir -p /data \
 && chown -R 10001:10001 /data

COPY --from=build /wheels /wheels
RUN pip install --no-index --find-links /wheels news-monitor-mcp \
 && rm -rf /wheels

USER 10001:10001
WORKDIR /home/mcp
EXPOSE 8000

# HTTP transport is the only sensible mode inside a container.
# MCP_BEARER_TOKEN and WORLD_NEWS_API_KEY MUST be provided at runtime;
# the entrypoint refuses to start without them (see PR #2).
ENTRYPOINT ["news-monitor-mcp"]
CMD ["--http"]
