# Finding: SEC-API-KEY-HANDLING — API-Key als Klartext-Env und URL-Query-Parameter

| Feld | Wert |
|---|---|
| **Severity** | **high** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | SEC (Secret Handling) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

1. API-Key wird unmaskiert aus der Umgebung geladen, als String herumgereicht:

   `src/news_monitor_mcp/server.py:218-219`
   ```python
   def _get_api_key() -> Optional[str]:
       return os.environ.get("WORLD_NEWS_API_KEY")
   ```

2. Der Key wird in **jedem** WorldNewsAPI-Call als URL-Query-Parameter `api-key=...` mitgesendet (`src/news_monitor_mcp/server.py:487, 533, 588, 661, 707, 745, 779, 821, 864, 990`). httpx schreibt das in die Request-URL — bei Proxy-Logging, `respx`-Inspect, Tracing-Backends, oder `logger.debug` auf httpx-Ebene landet der Key in den Logs.

3. Keine Pydantic-`SecretStr`-Wrapper, kein Mask-Filter im Logger, keine Sanitisierung in `_handle_api_error()` (`server.py:276-284`) — bei `HTTPStatusError` wird `e.response` weitergereicht, dessen Repräsentation enthält ggf. die Request-URL inkl. Key.

## Expected Behavior

- API-Key in `pydantic.SecretStr` halten; Klartext nur an der API-Boundary auspacken.
- Bevorzugt `Authorization: Bearer`-Header statt URL-Query (sofern upstream API es unterstützt; WorldNewsAPI akzeptiert auch `x-api-key`-Header laut Doku — verifizieren).
- Logging-Filter, der `api-key=`-Pattern in jeder Log-Message maskiert.
- Error-Handler darf keine Request-URL / Response-Header echoen.

## Evidence

- `server.py:487` (in `news_search`):
  ```python
  p: dict[str, Any] = {"api-key": api_key, "text": params.query, ...}
  r = await _get_client().get("/search-news", params=p)
  ```
- `server.py:225` UA-Header — kein Header-basierter Auth-Versuch
- `server.py:33` `logger = logging.getLogger("news-monitor-mcp")` — kein Mask-Filter angehängt
- `server.py:284` `return f"Fehler: {type(e).__name__}: {e!s}"` — `repr(e)` von `httpx.HTTPStatusError` enthält Request-URL

## Risk Description

- **Log-Leak:** Bei `LOG_LEVEL=DEBUG` (Render-Default für Build-Phase) logt `httpx` die volle URL inkl. `api-key=...` in Render-Logs, die für jede·n im Render-Team lesbar sind.
- **Error-Pass-Through:** Wenn WorldNewsAPI 5xx liefert, gibt der Server eine Error-Message zurück, in der mit `e!s` der Original-Fehler steckt — bei manchen httpx-Versionen inkl. URL.
- **Multi-Tenant-Cloud:** Sobald HTTP-Mode produktiv ist (s. SEC-HTTP-NO-AUTH), reicht jede·r Aufrufer indirekt den Key über den Server an WorldNewsAPI weiter — der Server selbst leakt den Key nicht direkt, aber Quota wird auf User-Aktion verbrannt (siehe verbundenes Finding).

## Remediation

```diff
- def _get_api_key() -> Optional[str]:
-     return os.environ.get("WORLD_NEWS_API_KEY")
+ from pydantic import SecretStr
+
+ def _get_api_key() -> Optional[SecretStr]:
+     raw = os.environ.get("WORLD_NEWS_API_KEY")
+     return SecretStr(raw) if raw else None
```

```diff
- p: dict[str, Any] = {"api-key": api_key, "text": params.query, ...}
- r = await _get_client().get("/search-news", params=p)
+ p: dict[str, Any] = {"text": params.query, ...}
+ headers = {"x-api-key": api_key.get_secret_value()}
+ r = await _get_client().get("/search-news", params=p, headers=headers)
```

Plus:

1. Globaler Logging-Filter, der `api-key=[^&\s]+` → `api-key=***` redacted.
2. `_handle_api_error()`: nur Status-Code und sanitisierte Phrase zurückgeben, nie `str(e)`.
3. Bei WorldNewsAPI verifizieren, ob `x-api-key`-Header ebenso akzeptiert wird (Doku-Stand prüfen). Falls nicht, URL-Query unvermeidbar → dann zwingend Mask-Filter + httpx-Logger auf `WARNING` setzen.

## Effort Estimate

**S** (< 1 Tag).

## Dependencies / Blockers

Keine.

## Verification After Fix

- `pytest tests/test_server.py::test_no_api_key_in_logs` — Mock-Logger fängt alle Records ab und assertet, dass kein Record `os.environ["WORLD_NEWS_API_KEY"]` enthält.
- Manueller Run mit `LOG_LEVEL=DEBUG` und gegrepptem stderr.
