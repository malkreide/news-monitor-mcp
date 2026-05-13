# Finding: SDK-LIFESPAN — Keine FastMCP-Lifespan; httpx-Client wird nie geschlossen

| Feld | Wert |
|---|---|
| **Severity** | **medium** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | SDK (Server Lifecycle) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

- `_client: Optional[httpx.AsyncClient]` (`server.py:216`) wird lazily erstellt und **nie** mit `aclose()` geschlossen.
- Kein `@mcp.lifespan` / `async def lifespan(...)` registriert.
- `main()` (`server.py:1116-1126`) ruft direkt `mcp.run(...)` ohne Setup/Teardown.

## Expected Behavior

FastMCP unterstützt einen `lifespan`-Context-Manager (Starlette-Konvention). Best-Practice:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(_):
    client = httpx.AsyncClient(base_url=BASE_URL, timeout=DEFAULT_TIMEOUT,
                               headers={"User-Agent": "news-monitor-mcp/0.2.0"})
    try:
        yield {"client": client}
    finally:
        await client.aclose()

mcp = FastMCP("news_monitor_mcp", instructions=..., lifespan=lifespan)
```

Tools erhalten den Client via `Context` statt globalem Singleton.

## Evidence

- `server.py:216-226` — Lazy-Init, kein Teardown
- `grep -n lifespan src/` ⇒ keine Treffer

## Risk Description

- **Connection-Leak bei Server-Restart:** TCP-Connections von WorldNewsAPI bleiben offen, bis OS-Cleanup eingreift.
- **Resource-Warnung in pytest:** `pytest -W error::ResourceWarning` würde rot.
- **Erschwert Multi-Instance:** Singleton-Pattern verträgt sich schlecht mit Worker-basierten Deployments (Gunicorn pre-fork etc.).

## Remediation

Siehe Code-Snippet oben. Migration in zwei Schritten:

1. `lifespan` hinzufügen, Client in `app.state.client` legen.
2. Globalen `_client` entfernen; `_get_client()` ersetzen durch `Context`-Helper.

## Effort Estimate

**S** (< 1 Tag).

## Dependencies / Blockers

Lose verkoppelt mit ARCH-CONCURRENCY (gleicher Singleton-Eliminationspfad).

## Verification After Fix

- `pytest -W error::ResourceWarning` grün.
- Smoke-Test: `mcp.run` startet, SIGTERM beendet sauber (kein hängender Connection).
