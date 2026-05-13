# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-03-22
### Added
- Initial PyPI publication

## [Unreleased]

### Changed
- **`mcp>=1.0.0`** statt `fastmcp>=2.0.0` als deklarierte Dependency. Behebt das `medium`-Finding `SDK-DEP-MISMATCH` (Audit 2026-05-13): der Code importiert ausschliesslich `mcp.server.fastmcp.FastMCP` aus dem offiziellen MCP-SDK; das standalone `fastmcp`-Paket wurde nie verwendet.
- **`hashlib.sha256` statt `hashlib.md5`** für Cache-Keys. Behebt `SEC-MD5` (low): kein FIPS-Mode-Block mehr, kein Bandit-/ruff-S324-Noise.
- **README + README.de Tool-Tabellen** listen alle 15 Tools (vorher nur 9). Behebt `ARCH-TOOL-COUNT` (low).

### Security
- **API-Key wandert vom URL-Query in den `x-api-key`-HTTP-Header.** Behebt das `high`-Finding `SEC-API-KEY-HANDLING` (Audit 2026-05-13). Alle 10 Call-Sites gegen WorldNewsAPI senden den Key jetzt im Header (von WorldNewsAPI [offiziell unterstützt](https://worldnewsapi.com/docs/authentication/)); die URL enthält den Key nicht mehr und kann nicht mehr in Proxy-/Access-Logs landen.
- **`WORLD_NEWS_API_KEY` wird in `pydantic.SecretStr` gewickelt.** `str()`/`repr()` liefern `***********`; der Klartext ist nur noch über `.get_secret_value()` an der API-Boundary zugreifbar.
- **`_handle_api_error()` sanitisiert.** Der Fallback-Branch gibt nicht mehr `str(e)` an den MCP-Client zurück (das konnte interne URLs, Hostnames oder Stacktraces leaken). Stattdessen: Typ-Name + Verweis aufs Server-Log; volle Exception geht via `logger.exception(...)` durch die Redaction-Pipeline.
- **Zusätzliches Mask-Pattern** für `x-api-key`-Header-Dumps in Logs (defense in depth, falls sich der Header doch mal in einem Log-Record materialisiert).
- **Streamable-HTTP-Transport erfordert jetzt einen Bearer-Token.** Pflicht-Env-Variable `MCP_BEARER_TOKEN` im `--http`-Mode; Requests ohne gültigen `Authorization: Bearer <token>`-Header werden mit HTTP 401 abgewiesen. Behebt das `critical`-Finding `SEC-HTTP-NO-AUTH` (Audit 2026-05-13).
- **Optionale Origin-Allowlist** via `MCP_ALLOWED_ORIGINS` (CSV) schützt gegen DNS-Rebinding-Angriffe.
- **Default-Host auf `127.0.0.1`** gewechselt (vorher `0.0.0.0`). Für Container-Deployments via `--host 0.0.0.0` oder `MCP_HOST=0.0.0.0` explizit setzen.
- **Log-Maskierung:** `api-key=...`-Query-Parameter und `Authorization: Bearer ...`-Header werden in allen Log-Records automatisch durch `***` ersetzt. Reduziert die Leak-Oberfläche aus `SEC-API-KEY-HANDLING` schon vor dem dedizierten Fix.

### Fixed
- **FastMCP-Lifespan räumt den httpx-Client auf.** Behebt das `medium`-Finding `SDK-LIFESPAN` (Audit 2026-05-13): der lazy erzeugte globale `httpx.AsyncClient` wurde nie geschlossen — bei Server-Restart blieben TCP-Connections zu WorldNewsAPI offen, bis OS-Cleanup eingriff. `server_lifespan()` ruft jetzt sowohl in stdio- als auch HTTP-Mode `client.aclose()` und setzt den globalen Slot zurück. Defensive Exception-Handling, damit ein Teardown-Fehler den Slot trotzdem auf `None` zurücksetzt.
- **`alerts.json` wird jetzt atomar geschrieben** (tmpfile + `fsync` + `os.replace`). Behebt das `high`-Finding `ARCH-CONCURRENCY` (Audit 2026-05-13): ein abrupter Kill mid-write lässt die alte Version intakt; vorher konnte ein Crash zwischen `open(w)` und `json.dump` die Datei leer hinterlassen und alle Alerts unwiederbringlich löschen.
- **`AlertManager`-Mutationen sind jetzt mit `threading.RLock` serialisiert.** Verhindert Lost-Updates bei parallelen `create()`/`mark_checked()`/`delete()`-Aufrufen aus mehreren Worker-Threads.
- **Cross-Process-Schutz via `fcntl.flock`** auf einem `<file>.lock`-Sidecar (POSIX). Wenn mehrere Container-Replicas dasselbe Volume mounten, verhindert das Lost-Updates zwischen Prozessen. Auf Windows degradiert es zu No-Op (in-process-Lock bleibt aktiv).
- **`AlertManager.get()` liefert defensive Kopien.** External-Mutation kann den internen Zustand nicht mehr verändern.

### Added
- **Strukturiertes JSON-Logging** mit Request-ID-Propagation (Finding `OBS-LOG-UNSTRUCTURED`, Audit 2026-05-13):
  - `configure_logging()` setzt JSON-Formatter, `LOG_LEVEL`-Env-Variable, `_RequestIdFilter` und `_RedactionFilter` idempotent auf.
  - `RequestIdMiddleware` setzt pro HTTP-Request eine 12-Hex-`request_id` (oder übernimmt eingehenden `x-request-id`-Header), schreibt sie zurück in den Response-Header und loggt Methode/Pfad/Dauer.
  - Öffentliche API `add_redaction_pattern(pattern, replacement)` zur Erweiterung der Mask-Pipeline.
  - `httpx` und `httpcore` werden defensiv auf `WARNING` gesetzt, um Request-URL-Leaks bei `LOG_LEVEL=DEBUG` zu vermeiden.

### Changed
- `main()` mountet die FastMCP-App jetzt unter Starlette-Middleware und startet via `uvicorn`. `starlette` und `uvicorn` sind explizite Dependencies geworden.
- `main()` ruft beim Start `configure_logging()` auf; uvicorn verwendet kein eigenes Log-Config mehr (`log_config=None`).

## [0.2.0] - 2026-03-22

### Added
- **TTL-Cache** (`NewsCache`): In-Memory-Cache reduziert API-Calls bei wiederholten Abfragen um bis zu 80%. TTLs je nach Tool-Typ: Headlines 15 Min, Suche/Trend/Geo 30 Min, Sentiment/Briefing 60 Min, Artikel/Quellen 24h.
- **`use_cache`-Parameter** bei allen 9 Monitoring-Tools: `use_cache=False` erzwingt frischen API-Call, Standard `True`.
- **`news_alert_create`**: Erstellt persistente Alerts (`~/.news-monitor-mcp/alerts.json`). 4 Bedingungstypen: `sentiment_below`, `sentiment_above`, `volume_above`, `keyword_found`.
- **`news_alert_list`**: Listet alle Alerts mit Status, letzter Pruefung und Ausloesungsanzahl.
- **`news_alert_check`**: Prueft alle (oder spezifische) Alerts gegen aktuelle Daten – 1 API-Call pro Alert, kein Cache.
- **`news_alert_delete`**: Loescht einen Alert permanent.
- **`news_cache_stats`**: Hit-Rate, Eintraege nach Typ und gesparte API-Calls.
- **`news_cache_clear`**: Leert Cache vollstaendig oder fuer einen Tool-Typ.
- 15 neue Unit-Tests fuer `NewsCache` und `AlertManager` (35 Total, alle ohne API-Key).

### Changed
- Server-Version auf 0.2.0
- `User-Agent` auf `news-monitor-mcp/0.2.0`
- Server-Instructions aktualisiert (15 Tools dokumentiert)
- `_calc_avg_sentiment` als Hilfsfunktion extrahiert

## [0.1.0] - 2025-03-19

### Added
- Initial release with 9 tools via WorldNewsAPI
- `news_search`: Full-text news search in 150+ countries / 50+ languages
- `news_top_headlines`: Top headlines by country and language
- `news_sentiment_monitor`: Sentiment analysis for entities (DE/EN)
- `news_media_briefing`: Multi-topic weekly briefing report
- `news_retrieve_article`: Full article retrieval by ID
- `news_search_sources`: Discover available news sources
- `news_front_pages`: Digital newspaper front pages
- `news_trend_radar`: Category-based trend detection
- `news_geo_search`: Location-specific news search
- Dual transport: stdio (local) and Streamable HTTP (`--http` flag)
- Bilingual documentation (EN/DE)
- 20 unit tests (mock-based, no API key required)
