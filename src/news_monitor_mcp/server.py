"""News Monitor MCP Server – Entry-Point und Backward-Compat-Facade.

MCP Server für globale Nachrichtenrecherche, Medienmonitoring und automatische
Benachrichtigungen via WorldNewsAPI. **Die Implementation lebt in Submodulen**:

    api_client      — httpx + SecretStr + x-api-key-Header (SEC-API-KEY-HANDLING)
    alerts/         — AlertManager + atomic write + retention (SEC-ALERTS-PATH,
                      ARCH-CONCURRENCY, CH-DSG)
    app             — MCPServer-Instanz + Singletons + Lifespan (SDK-LIFESPAN)
    cache           — NewsCache + LRU-Cap + Sweep-Loop (SCALE-STATEFUL)
    errors          — _handle_api_error (SEC-ERROR-PASSTHROUGH)
    formatting      — Markdown/JSON + Enums
    http_auth       — Bearer/Origin/RequestId-Middleware (SEC-HTTP-NO-AUTH)
    logging_setup   — JSON-Logger + Redaction-Filter (OBS-LOG-UNSTRUCTURED)
    models          — Pydantic-Input-Modelle aller 15 Tools
    tools/          — die 15 @mcp.tool-Funktionen, aufgeteilt nach Kategorie

Diese Datei haelt nur noch:
  * `main()` als Konsolen-Entry-Point
  * `build_http_app()` Helper (braucht die MCPServer-Instanz)
  * Backward-Compat-Re-Exports — Tests und externer Code importieren weiter aus
    `news_monitor_mcp.server`, ohne von der internen Modul-Aufteilung zu wissen.

API key required: Kostenloser Key via https://worldnewsapi.com/console/
Set environment variable: WORLD_NEWS_API_KEY
"""

import logging
import os
import sys
from typing import Any

# Backward-Compat-Re-Exports: alle Symbole, die Tests + externer Code aus
# `news_monitor_mcp.server` erwarten.
import news_monitor_mcp.api_client as _api_client_module  # noqa: F401

# Trigger tool registration. Importing the tools package runs the @mcp.tool
# decorators in each submodule against the MCPServer instance from app.py.
import news_monitor_mcp.tools  # noqa: F401, E402
from news_monitor_mcp.alerts import (  # noqa: F401
    ALERT_RETENTION_DAYS_DEFAULT,
    ALERTS_DIR_DEFAULT,
    ALERTS_FILE,
    AlertManager,
    _atomic_write_json,
    _ensure_secure_perms,
    _fcntl,
    _file_lock,
    _get_alert_retention_days,
    _resolve_alerts_path,
)
from news_monitor_mcp.api_client import (  # noqa: F401
    BASE_URL,
    DACH_SOURCE_COUNTRIES,
    DEFAULT_RESULTS,
    DEFAULT_TIMEOUT,
    MAX_RESULTS,
    SWISS_SOURCE_COUNTRIES,
    _auth_headers,
    _check_api_key,
    _get_api_key,
    _get_client,
)
from news_monitor_mcp.app import _alert_manager, _cache, mcp, server_lifespan  # noqa: F401
from news_monitor_mcp.cache import (  # noqa: F401
    CACHE_MAX_PER_TYPE_DEFAULT,
    CACHE_SWEEP_SECONDS_DEFAULT,
    CACHE_TTL,
    CacheBackend,
    NewsCache,
    _cache_sweep_loop,
    _get_cache_max_per_type,
    _get_cache_sweep_seconds,
)
from news_monitor_mcp.errors import _handle_api_error, _no_key_message  # noqa: F401
from news_monitor_mcp.formatting import (  # noqa: F401
    AlertConditionType,
    ResponseFormat,
    SortOrder,
    _calc_avg_sentiment,
    _format_article,
    _format_articles_markdown,
    _sentiment_label,
)
from news_monitor_mcp.http_auth import (  # noqa: F401
    BearerAuthMiddleware,
    OriginAllowlistMiddleware,
    RequestIdMiddleware,
    _attach_middlewares,
    _parse_allowed_origins,
)
from news_monitor_mcp.logging_setup import (  # noqa: F401
    _JsonFormatter,
    _redact,
    _redaction_patterns,
    _RedactionFilter,
    _request_id,
    _RequestIdFilter,
    add_redaction_pattern,
    configure_logging,
    logger,
)
from news_monitor_mcp.models import (  # noqa: F401
    CacheClearInput,
    CheckAlertsInput,
    CreateAlertInput,
    DeleteAlertInput,
    FrontPagesInput,
    GeoNewsInput,
    MediaBriefingInput,
    RetrieveArticleInput,
    SearchNewsInput,
    SearchSourcesInput,
    SentimentMonitorInput,
    TopNewsInput,
    TrendRadarInput,
)

# Re-export tool functions so existing imports keep working.
from news_monitor_mcp.tools.alerts_tools import (  # noqa: E402,F401
    news_alert_check,
    news_alert_create,
    news_alert_delete,
    news_alert_list,
)
from news_monitor_mcp.tools.cache_admin import (  # noqa: E402,F401
    news_cache_clear,
    news_cache_stats,
)
from news_monitor_mcp.tools.monitoring import (  # noqa: E402,F401
    news_front_pages,
    news_geo_search,
    news_media_briefing,
    news_retrieve_article,
    news_search,
    news_search_sources,
    news_sentiment_monitor,
    news_top_headlines,
    news_trend_radar,
)


def build_transport_security(host: str, port: int, allowed_origins: frozenset[str]):
    """Host/Origin-Allow-List fuer den HTTP-Transport (SEC-005, eingehend).

    Ohne ``transport_security`` laesst das SDK den DNS-Rebinding-Schutz aus —
    sein eigener Kommentar: "If not specified, disable DNS rebinding protection
    by default for backwards compatibility". Ungesetzt heisst: keine Host- und
    keine Origin-Pruefung.

    Der Bearer-Token (http_auth) schuetzt bereits gegen unautorisierte Aufrufe;
    das hier ist Defense in Depth auf Transport-Ebene und faengt Rebinding ab,
    bevor ueberhaupt ein Handler laeuft.

    Rueckgabe ``None``, wenn keine Allow-List ableitbar ist — Nicht-Loopback-Bind
    ohne ``MCP_ALLOWED_HOSTS``. Der Server wird dann unter einem Service- oder
    DNS-Namen erreicht, den dieser Prozess nicht kennt; eine geratene Liste
    wuerde jede echte Anfrage mit HTTP 421 abweisen.
    """
    from mcp.server.transport_security import TransportSecuritySettings

    allowed = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    loopback = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}
    if allowed:
        hosts = set(allowed) | loopback
    elif host in ("127.0.0.1", "localhost", "::1"):
        hosts = loopback | {f"{host}:{port}"}
    else:
        return None

    origins = {o for o in allowed_origins if o != "*"}
    origins |= {f"http://{h}" for h in hosts}
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted(hosts),
        allowed_origins=sorted(origins),
    )


def build_http_app(token: str, allowed_origins: frozenset[str], security=None, host: str = "127.0.0.1") -> Any:
    """Thin wrapper: zieht die Starlette-App aus der MCPServer-Instanz und hängt
    den Middleware-Stack an (siehe `http_auth._attach_middlewares` für Details).
    """
    return _attach_middlewares(
        mcp.streamable_http_app(transport_security=security, host=host),
        token,
        allowed_origins,
    )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------


def main() -> None:
    """Startet den News Monitor MCP Server."""
    import argparse

    parser = argparse.ArgumentParser(description="News Monitor MCP Server v0.3.0")
    parser.add_argument("--http", action="store_true", help="HTTP-Server statt stdio")
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "127.0.0.1"),
        help="HTTP-Host (Standard: 127.0.0.1; fuer Container: 0.0.0.0)",
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("MCP_PORT", "8000")), help="HTTP-Port (Standard: 8000)"
    )
    args = parser.parse_args()
    configure_logging()
    if args.http:
        token = os.environ.get("MCP_BEARER_TOKEN")
        if not token:
            print(
                "ERROR: MCP_BEARER_TOKEN muss im HTTP-Mode gesetzt sein. "
                'Erzeuge z.B. mit: python -c "import secrets; print(secrets.token_urlsafe(32))"',
                file=sys.stderr,
            )
            sys.exit(2)
        allowed = _parse_allowed_origins(os.environ.get("MCP_ALLOWED_ORIGINS"))
        security = build_transport_security(args.host, args.port, allowed)
        if security is None:
            logging.getLogger("news_monitor_mcp").warning(
                "DNS-Rebinding-Schutz ist AUS: Bind auf %s ist nicht Loopback und "
                "MCP_ALLOWED_HOSTS ist leer. Setze MCP_ALLOWED_HOSTS auf die "
                "Hostnamen, unter denen dieser Server erreichbar ist.",
                args.host,
            )
        # mcp 2.x: transport_security is a per-app kwarg, not a setting.
        app = build_http_app(token, allowed, security, args.host)
        import uvicorn

        uvicorn.run(app, host=args.host, port=args.port, log_config=None)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
