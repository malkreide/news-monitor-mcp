> ✅ **Re-Audit Status:** `closed` — gemerged via PR #4.

# Finding: SEC-ERROR-PASSTHROUGH — Unsanitisierte Exception-Strings im Tool-Output

| Feld | Wert |
|---|---|
| **Severity** | **medium** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | SEC (Error Sanitization) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

`src/news_monitor_mcp/server.py:276-284`:

```python
def _handle_api_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 401: return "Fehler: Ungültiger API-Key."
        ...
        return f"API-Fehler: HTTP {e.response.status_code}"
    ...
    return f"Fehler: {type(e).__name__}: {e!s}"
```

Der Fallback `f"Fehler: {type(e).__name__}: {e!s}"` reicht beliebige Exception-Strings an den MCP-Client (also den LLM) durch. Bei httpx-internen Exceptions enthält `str(e)` häufig die Request-URL — also den `api-key`-Query-Parameter aus SEC-API-KEY-HANDLING.

Zusätzlich `server.py:1003-1005` (`news_alert_check`):

```python
results.append({"alert": alert, "triggered": False,
    "reason": f"API-Fehler: {_handle_api_error(e)}", ...})
```

Der Alert-Datensatz inkl. unsanitisierter Fehlermeldung wird ins Markdown-Output gerendert.

## Expected Behavior

- Generische Fehlerklassen mappen, keine `str(e)`-Pass-Throughs.
- Detailinfo nur in Server-Logs (mit Mask-Filter), nicht in Tool-Outputs.

## Evidence

- `server.py:284` — Fallback-Branch.
- `server.py:1004` — Übernahme in Alert-Output.

## Risk Description

- Verstärkt SEC-API-KEY-HANDLING: doppelte Leak-Oberfläche.
- Informations-Disclosure: interne Hostnames, File-Pfade, Stacktraces können via LLM dem End-User angezeigt werden.

## Remediation

```diff
- return f"Fehler: {type(e).__name__}: {e!s}"
+ logger.exception("Unerwarteter API-Fehler")
+ return f"Fehler: {type(e).__name__} – Details siehe Server-Log"
```

Plus globaler Logging-Filter (s. SEC-API-KEY-HANDLING).

## Effort Estimate

**S** (< 1 Tag, inkl. Test).

## Dependencies / Blockers

Logisch verkoppelt mit SEC-API-KEY-HANDLING (gleiche Logging-Maskierung).

## Verification After Fix

- Test: provoziere `httpx.ConnectError` mit URL, die fake `api-key=SECRET` enthält → assert `"SECRET" not in result`.
