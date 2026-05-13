"""FastMCP-Instanz + Singletons + Lifespan.

Tools dekorieren `mcp` aus diesem Modul, statt aus `server.py`. Damit gibt es
keinen zirkulaeren Import zwischen `server.py` (das die Tools importieren muss,
um deren Registrierung anzustossen) und `tools/*` (die `mcp` brauchen).
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

import news_monitor_mcp.api_client as _api_client_module
from news_monitor_mcp.alerts import AlertManager
from news_monitor_mcp.cache import NewsCache, _cache_sweep_loop, _get_cache_sweep_seconds
from news_monitor_mcp.logging_setup import logger

_cache = NewsCache()
_alert_manager = AlertManager()


@asynccontextmanager
async def server_lifespan(_server: Any):
    """FastMCP-Lifespan: räumt prozessglobale Ressourcen beim Shutdown auf.

    Konkret:
      * Startet einen Background-Cache-Sweep (Eviction abgelaufener Eintraege),
        konfigurierbar via `MCP_CACHE_SWEEP_SECONDS` (Default 300 s, `0` aus).
      * Schliesst den lazy erzeugten httpx-Client (`api_client._client`), damit
        offene TCP-Verbindungen zu WorldNewsAPI sauber abgebaut werden und
        keine ResourceWarnings entstehen.
    Wird sowohl fuer stdio- als auch streamable-http Transport aufgerufen.
    """
    sweep_seconds = _get_cache_sweep_seconds()
    sweep_task: Optional[asyncio.Task[None]] = None
    if sweep_seconds > 0:
        sweep_task = asyncio.create_task(
            _cache_sweep_loop(_cache, sweep_seconds), name="cache-sweep"
        )
    try:
        yield {}
    finally:
        if sweep_task is not None:
            sweep_task.cancel()
            try:
                await sweep_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        try:
            await _api_client_module.close_client()
        except Exception:  # noqa: BLE001
            logger.exception("httpx-Client konnte nicht sauber geschlossen werden")


mcp = FastMCP(
    "news_monitor_mcp",
    instructions=(
        "News-Monitoring-Server mit 15 Tools via WorldNewsAPI. "
        "9 Monitoring-Tools (Suche, Headlines, Sentiment, Briefing, Artikel, Quellen, Covers, Trends, Geo) "
        "alle mit TTL-Cache. 4 Alert-Tools: erstellen/auflisten/prüfen/löschen. "
        "2 Cache-Tools: Statistiken und leeren. "
        "API-Key: WORLD_NEWS_API_KEY. DACH: source-country=ch,de,at. "
        "Sentiment nur DE/EN. Alerts: news_alert_create dann news_alert_check."
    ),
    lifespan=server_lifespan,
)
