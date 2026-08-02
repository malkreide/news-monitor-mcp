"""Sanitisiertes Mapping von httpx-Exceptions zu nutzerfreundlichen Strings.

Behebt Audit-Finding SEC-ERROR-PASSTHROUGH (Audit 2026-05-13): der frueher
verwendete Fallback `f"Fehler: {type(e).__name__}: {e!s}"` konnte
Request-URLs (mit `api-key=` Query) an den MCP-Client durchreichen.

Public surface:
    _no_key_message      — generische "API-Key fehlt"-Antwort pro Tool
    _handle_api_error    — httpx-Exception -> nutzerfreundlicher String
"""

import httpx

from news_monitor_mcp.logging_setup import logger


def _no_key_message(tool_name: str) -> str:
    return (
        f"Kein API-Key fuer '{tool_name}' konfiguriert.\n"
        "Bitte WORLD_NEWS_API_KEY als Umgebungsvariable setzen.\n"
        "Kostenloser Key: https://worldnewsapi.com/console/"
    )


def _handle_api_error(e: Exception) -> str:
    """Mappt httpx-Exceptions auf nutzerfreundliche Strings, ohne `str(e)` an den
    Client durchzureichen. Stacktrace + URL gehen ins Server-Log (mit Redaction)."""
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 401:
            return "Fehler: Ungültiger API-Key."
        if e.response.status_code == 402:
            return "Fehler: API-Kontingent erschöpft."
        if e.response.status_code == 429:
            return "Fehler: Rate Limit erreicht."
        return f"API-Fehler: HTTP {e.response.status_code}"
    if isinstance(e, httpx.TimeoutException):
        return "Fehler: Timeout."
    if isinstance(e, httpx.ConnectError):
        return "Fehler: Keine Verbindung zur WorldNewsAPI."
    logger.exception("Unerwarteter API-Fehler")
    return f"Fehler: {type(e).__name__} – Details siehe Server-Log"
