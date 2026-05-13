> ✅ **Re-Audit Status:** `closed` — gemerged via PR #3.

# Finding: OBS-LOG-UNSTRUCTURED — Logger ohne Konfiguration, ohne Struktur, ohne Trace-IDs

| Feld | Wert |
|---|---|
| **Severity** | **medium** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | OBS (Logging / Tracing) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

- `server.py:33` `logger = logging.getLogger("news-monitor-mcp")` — kein `basicConfig`, kein Handler, kein Level.
- Logger wird **genau einmal** verwendet: `server.py:141` `logger.error(f"Alert-Datei konnte nicht gespeichert werden: {e}")`. Alle anderen Fehler werden über Tool-Output zurückgegeben (siehe SEC-ERROR-PASSTHROUGH).
- Keine Request-ID, keine User-/Tenant-ID, kein Tool-Name in Log-Records.
- Kein OpenTelemetry-Setup, kein SIEM-Forwarding.

## Expected Behavior

Per OBS-Best-Practice für produktive MCP-Server:

- Strukturiertes Logging (JSON) mit Feldern: `timestamp`, `level`, `tool`, `request_id`, `duration_ms`, `cache_hit`, `outcome`.
- Korrelations-ID pro MCP-Request, durchgereicht an httpx-Calls.
- Konfigurierbares Log-Level via `LOG_LEVEL`-Env.
- Optional OpenTelemetry-Hook (OTLP-Exporter) — mindestens Stubs.

## Evidence

- `grep -n "logger\." src/news_monitor_mcp/server.py` ⇒ 1 Treffer (`server.py:141`).
- Keine `logging.basicConfig` / `dictConfig` / Handler-Registrierung.

## Risk Description

- **Forensik unmöglich:** Bei Production-Incident kein nachvollziehbares Audit-Trail (welcher Tool-Call ist gescheitert, von wem, wann).
- **DSG-Risiko:** Im Schweizer Kontext (siehe CH-Findings) muss bei Datenpannen nachweisbar sein, was passiert ist.
- **Cache-Hit-Rate-Anspruch:** README claim "80% gesparte Calls" — ohne Telemetry nicht beweisbar.
- **Quota-Spike-Detektion:** Ohne strukturierte Logs kann ein laufender Quota-Drain (siehe SEC-HTTP-NO-AUTH) nicht detektiert werden.

## Remediation

```diff
+ import logging
+ from logging.config import dictConfig
+
+ def configure_logging() -> None:
+     level = os.environ.get("LOG_LEVEL", "INFO").upper()
+     dictConfig({
+         "version": 1,
+         "disable_existing_loggers": False,
+         "formatters": {
+             "json": {
+                 "format": '{"ts":"%(asctime)s","lvl":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
+             },
+         },
+         "handlers": {
+             "console": {"class": "logging.StreamHandler", "formatter": "json", "level": level, "stream": "ext://sys.stderr"},
+         },
+         "root": {"handlers": ["console"], "level": level},
+         "loggers": {"httpx": {"level": "WARNING"}, "httpcore": {"level": "WARNING"}},
+     })
```

Plus Mask-Filter (s. SEC-API-KEY-HANDLING) auf Root-Logger.

Tool-Wrapper für Korrelations-ID:

```python
from contextvars import ContextVar
request_id: ContextVar[str] = ContextVar("request_id", default="-")

def with_request_id(fn):
    async def wrapper(*args, **kw):
        rid = uuid.uuid4().hex[:8]
        token = request_id.set(rid)
        t0 = time.time()
        try:
            return await fn(*args, **kw)
        finally:
            logger.info(f"tool={fn.__name__} rid={rid} dur_ms={(time.time()-t0)*1000:.1f}")
            request_id.reset(token)
    return wrapper
```

## Effort Estimate

**M** (1–2 Tage).

## Dependencies / Blockers

Voraussetzung für sinnvolles SEC-API-KEY-HANDLING-Mask-Filter.

## Verification After Fix

- `LOG_LEVEL=DEBUG news-monitor-mcp` liefert valide JSON-Lines auf stderr.
- Test: `tool=news_search` Record enthält `rid` und `dur_ms`.
- httpx-Logger ist auf WARNING gesetzt → keine URL-Leaks im Default.
