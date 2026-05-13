# Finding: SCALE-NO-DOCKERFILE — Container-Deployment dokumentiert, aber kein Dockerfile

| Feld | Wert |
|---|---|
| **Severity** | **medium** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | SCALE (Container / Reproducible Deployment) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

- `README.md:153-156` zeigt einen Docker/Local-HTTP-Modus an, suggeriert Container-Deployment.
- Kein `Dockerfile`, kein `docker-compose.yml`, kein `.dockerignore` im Repo.
- Render.com kann Python-Projekte ohne Dockerfile builden (Buildpacks), aber jedes andere Deployment-Ziel (Fly.io, AWS, Kubernetes, eigenes Cluster) erfordert Eigenarbeit.

## Expected Behavior

Per SCALE-Mantra (Sandbox) sollte ein MCP-Server mit `streamable-http`-Mode ein gepflegtes, reproduzierbares Container-Image liefern:

```dockerfile
FROM python:3.12-slim
RUN useradd -m -u 10001 mcp
WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .
USER mcp
ENV MCP_TRANSPORT=streamable_http
EXPOSE 8000
CMD ["news-monitor-mcp", "--http", "--port", "8000"]
```

Plus `.dockerignore` (mind. `.git`, `tests/`, `.venv/`).

## Evidence

- `ls` im Repo-Root: kein Dockerfile.
- README spricht explizit von `# Docker / local HTTP mode` ohne Build-Anleitung.

## Risk Description

- **Sandbox-Lücke:** Ohne dedicated Container-Image bekommen User unterschiedliche Python-Versionen und Layer-Konfigurationen.
- **Egress-Filtering:** Ein Dockerfile mit klar definierter Network-Surface ist Voraussetzung für Egress-Allowlist (nur `api.worldnewsapi.com:443`).
- **Reproducibility:** Audits / Re-Audits können nicht versionsstabil reproduziert werden.

## Remediation

1. `Dockerfile` und `.dockerignore` im Repo-Root anlegen (Snippet oben).
2. CI-Job `docker-build` ergänzen, der das Image baut und einen Smoke-Test (`docker run --rm IMG --help`) ausführt.
3. README-Sektion "Docker" mit echten Commands ersetzen.

## Effort Estimate

**S** (< 1 Tag).

## Verification After Fix

- `docker build -t news-monitor-mcp:audit .` läuft grün.
- `docker run --rm news-monitor-mcp:audit news-monitor-mcp --help` zeigt argparse-Hilfe.
