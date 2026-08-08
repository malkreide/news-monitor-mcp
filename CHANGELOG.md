# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Behoben

- **Drei Live-Tests liefen ueberhaupt nie.** Sie trugen `@pytest.mark.live`,
  aber keinen `@pytest.mark.asyncio`. Im Strict-Default von `pytest-asyncio`
  heisst das nicht «uebersprungen», sondern «async def functions are not
  natively supported» — wer `-m live` aufrief, bekam drei Fehler, die nichts
  ueber die Quelle aussagten. Die CI schliesst `-m live` aus, also meldete es
  niemand.

  Behoben ueber `asyncio_mode = "auto"` in `pyproject.toml`. Das ist der
  strukturelle Fix statt des punktuellen: Eine vergessene Markierung kann
  diesen Fehler nicht mehr erzeugen.

- **Und laufend haetten sie wenig gezeigt.** Alle drei Zusicherungen trafen
  nur die eigene Vorlage:

      assert "Volksschule" in result or "Ergebnisse" in result

  Der zweite Zweig ist die Ueberschrift der Ergebnisliste, die Disjunktion
  konnte also nicht fehlschlagen. `assert "Top-Schlagzeilen" in result` und
  `assert "Sentiment" in result` ebenso.

  Neu sichern sie zu, dass Artikel zurueckkommen, dass ein Cluster Inhalt hat
  und dass ein Sentiment eine Zahl ist. Ohne Schluessel **ueberspringen** sie
  sich, statt rot zu melden: «rot» soll heissen, dass etwas nicht stimmt,
  nicht dass jemand keinen Schluessel hat.

- **`data.get("news", [])` konnte einen Formfehler in «0 Ergebnisse»
  verwandeln.** Der Ausdruck beantwortet zwei voellig verschiedene Faelle
  gleich: «die Quelle hat nichts gefunden» und «die Quelle antwortet anders,
  als wir annehmen».

  Das ist kein hypothetisches Risiko. In `global-education-mcp` desselben
  Portfolios stand genau dieses Muster; weil der Umschlag der Quelle
  inzwischen anders hiess, kam aus **jeder** Antwort eine leere Liste — bei
  128 gruenen Tests.

  Neu liest `articles_of()` den Umschlag an sieben Aufrufstellen. Ein leeres
  `news` bleibt eine leere Liste, das ist eine Aussage der Quelle. Ein
  FEHLENDES `news` ist keine Aussage ueber die Nachrichten, sondern ueber die
  Antwort, und wird als `UpstreamShapeError` mit eigener Meldung gemeldet —
  nicht als «Details siehe Server-Log».

### Hinzugefuegt

- **Die erste Live-Abdeckung dieses Repos, die ohne API-Key laeuft** — der
  Bestand der Routen. Gemessen wurde, was die Quelle auch ohne Schluessel
  preisgibt: welche der fuenf Pfade, die die Werkzeuge bauen, es gibt.

  **Befund: alle fuenf.** Das ist eine gute Nachricht und trotzdem ein
  Ergebnis — vorher war es unbelegt.

  Getragen wird sie von einer Kontrolle. Das Gateway routet vor der
  Authentifizierung:

      /search-news                 -> 401  application/json
      /diesen-pfad-gibt-es-nicht   -> 404  text/html

  Ein 401 heisst dort also «diese Route gibt es». Ohne den erfundenen Pfad
  hiesse der Befund nur «ich habe einen 401 bekommen» — und das ist keine
  Selbstverstaendlichkeit: `epl.bag.admin.ch` im selben Portfolio antwortet
  auch auf erfundene Pfade mit 401. Der Recorder misst die Kontrolle deshalb
  bei jedem Lauf mit und bricht ab, wenn sie nicht mehr unterscheidet.

- **`scripts/record_fixtures.py` und `tests/fixtures/PROVENANCE.md`.** Die
  Antwort-Payloads sind darin ausdruecklich als **NICHT aufgezeichnet**
  gefuehrt, mit dem gemessenen Statuscode als Grund — statt ihnen ein Datum
  anzuschreiben, das nicht stimmt.

  Ausdruecklich als **offen** markiert ist damit auch: ob die
  Query-Parameternamen stimmen, die der Server sendet. Die API antwortet
  unabhaengig von den Parametern mit 401; ohne Schluessel ist das nicht
  pruefbar. In `global-education-mcp` waren genau dort zwei Filter still
  wirkungslos, weil unbekannte Parameter mit HTTP 200 beantwortet und
  fallengelassen wurden. Diese Pruefung steht aus und gilt nicht als
  erledigt.

- **`tests/test_antwortform.py`** — 15 Tests, die **in** der CI laufen. Das
  ist der Kern der Lehre aus dem ersten Befund: Was dauerhaft gelten soll,
  gehoert nicht in eine Datei, die die CI ueberspringt.

  Gegengeprueft mit drei gezielten Rueckmutationen — stiller Default zurueck
  an eine Aufrufstelle, `articles_of` faellt still auf `[]` zurueck,
  `asyncio_mode` zurueck auf `strict`. Alle drei machen die Suite rot; die
  dritte trifft dabei genau die neuen Routen-Tests und zeigt damit, dass der
  Modus-Wechsel traegt.

## [0.3.6] - 2026-08-02

### Behoben

- **`starlette` hatte keine Obergrenze, und der Index fuehrt bereits einen Major
  oberhalb der Untergrenze.** Deklariert war `starlette>=0.36.0`; auf PyPI liegt
  `1.3.1`. Das Artefakt aendert sich nicht — die Antwort des Resolvers auf
  die naechste frische Installation schon, und genau so wurde
  `swiss-energy-mcp` 0.3.3 uninstallierbar, als `mcp` 2.0.0 das Modul entfernt
  hat, das es importierte.

  Neu `starlette>=0.36.0,<2`. Die Grenze ist gemessen, nicht geraten: dieses Paket installiert
  und importiert heute gegen `starlette 1.3.1`, die Obergrenze laesst also zu,
  was nachweislich funktioniert, und stoppt nur den naechsten, unbekannten
  Major.

Ein Abhaengigkeitsbereich erreicht die Nutzenden nur ueber ein neues
Release, daher der Versions-Bump. Am Code aendert sich nichts.

## [0.3.5] - 2026-07-30

### Behoben

- **User-Agent meldet wieder die tatsaechliche Paketversion.** Das auf PyPI
  veroeffentlichte `0.3.4` sendete gegenueber jedem Upstream
  `news-monitor-mcp/0.3.0` — der Versionsstring war im Code hartkodiert und beim
  Bumpen liegengeblieben. Die Version kommt jetzt aus den Paket-Metadaten,
  kann also nicht mehr getrennt vom Paket driften.

- **`mcp` auf `<2` begrenzt.** `mcp` 2.0.0, veröffentlicht am 28.07.2026, hat
  `mcp.server.fastmcp` entfernt — genau das Modul, das dieser Server importiert.
  Mit dem bisherigen offenen `>=1.28.1` wählte jede frische Auflösung 2.0.0 und
  scheiterte beim Import mit `ModuleNotFoundError`, in der CI ebenso wie bei
  jedem `pip install`. In beide Richtungen verifiziert: 2.0.0 scheitert, `<2`
  löst auf 1.29.0 auf und importiert sauber. Die Migration auf die 2.x-API
  (`mcp.server.mcpserver`) bleibt eine eigene, bewusste Aufgabe.

## [0.3.4] - 2026-06-07
### Changed
- PyPI-Publish-Workflow nutzt jetzt `skip-existing: true`, damit erneute
  Workflow-Läufe für eine bereits veröffentlichte Version nicht mehr mit
  `400 File already exists` fehlschlagen.

## [0.2.0] - 2026-03-22
### Added
- Initial PyPI publication

## [0.3.0] - 2026-05-13

Security & compliance release. Closes 16 of 17 findings from the
[mcp-audit-skill audit 2026-05-13](audits/2026-05-13-news-monitor-mcp/audit-report.md);
SCALE-STATEFUL remains partially closed (LRU + sweep + protocol shipped, Redis
backend deferred).

### Refactored
- **`server.py` aufgeteilt (1724 → 180 LoC).** Behebt das `medium`-Finding `ARCH-MONOLITHIC` (Audit 2026-05-13). Reiner Refactor ohne Verhaltensänderung — alle 110 Tests laufen weiter grün. Neue Modul-Aufteilung:
  - `logging_setup.py` — strukturiertes JSON-Logging + Redaction (`OBS-LOG-UNSTRUCTURED`)
  - `formatting.py` — Markdown/JSON-Formatter + Enums
  - `errors.py` — sanitisiertes Exception-Mapping (`SEC-ERROR-PASSTHROUGH`)
  - `http_auth.py` — Bearer/Origin/RequestId-Middleware (`SEC-HTTP-NO-AUTH`)
  - `cache.py` — `NewsCache` + `CacheBackend`-Protocol + Sweep-Loop (`SCALE-STATEFUL`)
  - `alerts/` — `AlertManager`, atomic write, retention, flock (`SEC-ALERTS-PATH`, `ARCH-CONCURRENCY`, `CH-DSG`)
  - `api_client.py` — httpx + `SecretStr` + `x-api-key`-Header (`SEC-API-KEY-HANDLING`)
  - `models.py` — alle 13 Pydantic-Input-Modelle
  - `app.py` — FastMCP-Instanz + Singletons + Lifespan (`SDK-LIFESPAN`)
  - `tools/monitoring.py` (9 Tools), `tools/alerts_tools.py` (4), `tools/cache_admin.py` (2)
  - `server.py` — Entry-Point + Backward-Compat-Re-Exports
- **Backward-Compat:** alle bisherigen Imports aus `news_monitor_mcp.server` funktionieren weiter via Re-Exports. Test- und Downstream-Code muss nicht angepasst werden.

### Added
- **LRU-Cap pro Tool-Typ + Background-Cache-Sweep.** Adressiert Teil 1 von `SCALE-STATEFUL` (high, Audit 2026-05-13): unbegrenztes In-Memory-Wachstum bei langer Laufzeit. `NewsCache` nutzt jetzt eine `OrderedDict` mit echtem LRU (`move_to_end` bei Hit); pro Tool-Typ greift ein Cap (`MCP_CACHE_MAX_PER_TYPE`, Default 1000, `0` aus). Ein Background-Task im `server_lifespan` ruft `evict_expired()` periodisch auf (`MCP_CACHE_SWEEP_SECONDS`, Default 300 s).
- **`CacheBackend`-Protocol.** Strukturelle Schnittstelle (`get`/`set`/`clear`/`evict_expired`/`stats`); macht den Weg frei für einen späteren Redis-Backend ohne Tool-Code-Refactor.
- **README-Scaling-Sektion** dokumentiert das single-replica-Modell, das Render-Free-Tier-Sleep-Verhalten und verweist auf den offenen Teil von `SCALE-STATEFUL`.
- **`docs/privacy-dsg.md`** — Schweizer Datenschutz-Hinweis nach revDSG. Behebt das `high`-Finding `CH-DSG` (Audit 2026-05-13). Adressiert Rollen (Verantwortlicher / Auftragsbearbeiter), Rechtsgrundlagen, ADV-Pflicht gegenüber WorldNewsAPI, Drittlandtransfer (Art. 16 DSG / DPF), **Profiling-Disclaimer (Art. 5 lit. f DSG)**, Betroffenenrechte, Retention-Default und konkrete Schritte vor Produktiveinsatz.
- **Alert-Retention via `MCP_ALERT_RETENTION_DAYS`** (Default `90` Tage, `0` deaktiviert). `AlertManager._prune_old_alerts()` läuft beim Start: Alerts mit `created_at` älter als die Frist werden gelöscht und das File neu geschrieben. Legacy-Alerts ohne `created_at` und korrupte Timestamps bleiben defensive erhalten.
- **Profiling-Disclaimer** im Docstring von `news_sentiment_monitor` — der MCP-Client (also das LLM) bekommt den Hinweis bei jedem Tool-Lookup.
- **`SECURITY.md`** mit Private-Vulnerability-Reporting-Anleitung, Response-SLAs, Scope und Hardening-Baseline. Behebt das `low`-Finding `OPS-SECURITY-POLICY` (Audit 2026-05-13).
- **`.github/dependabot.yml`** für wöchentliche Updates von `pip`, `github-actions` und `docker` Dependencies (Montag 06:00 Europe/Zurich, max. 5/3/3 offene PRs).
- **`docs/isds-klassifikation.md`** — Schutzbedarfsfeststellung (Vertraulichkeit/Integrität/Verfügbarkeit), Verarbeitungsorte-Diagramm, Drittlandtransfer-Hinweis (Art. 16 DSG), Profiling-Klausel (Art. 5 lit. f DSG), Retention-Tabelle. Behebt `CH-ISDS` (medium).
- **`confirm: bool = False`** auf `news_alert_delete` und `news_cache_clear`. Erstaufruf ohne `confirm=true` liefert eine Bestätigungs-Aufforderung statt zu löschen. Behebt `HITL-DESTRUCTIVE` (low): verhindert versehentliches Löschen durch LLM-Loops oder fehlinterpretierte Anweisungen.
- **`Dockerfile` + `.dockerignore` + CI-Docker-Build-Job.** Behebt das `medium`-Finding `SCALE-NO-DOCKERFILE` (Audit 2026-05-13). Multi-Stage-Build auf `python:3.12-slim`, läuft als non-root UID `10001`, default `--http` mit `MCP_HOST=0.0.0.0`, persistiert Alerts in `/data`. CI baut das Image und prüft per Smoke-Test, dass `news-monitor-mcp --help` durchläuft und der Container ohne `MCP_BEARER_TOKEN` mit Exit-Code 2 abbricht (Härtung aus PR #2 wird also auch im Container-Pfad verifiziert).

### Changed
- **`mcp>=1.0.0`** statt `fastmcp>=2.0.0` als deklarierte Dependency. Behebt das `medium`-Finding `SDK-DEP-MISMATCH` (Audit 2026-05-13): der Code importiert ausschliesslich `mcp.server.fastmcp.FastMCP` aus dem offiziellen MCP-SDK; das standalone `fastmcp`-Paket wurde nie verwendet.
- **`hashlib.sha256` statt `hashlib.md5`** für Cache-Keys. Behebt `SEC-MD5` (low): kein FIPS-Mode-Block mehr, kein Bandit-/ruff-S324-Noise.
- **README + README.de Tool-Tabellen** listen alle 15 Tools (vorher nur 9). Behebt `ARCH-TOOL-COUNT` (low).

### Security
- **`alerts.json` mit `0o600`, Verzeichnis mit `0o700`.** Behebt das `medium`-Finding `SEC-ALERTS-PATH` (Audit 2026-05-13). Tempfile-basierter atomic write erzeugt das File bereits mit Mode `0o600`; ein `_ensure_secure_perms()`-Helper migriert bestehende Files beim Start und nach jedem Save.
- **Symlink-Schutz für den Alerts-Pfad.** `_resolve_alerts_path()` wirft `RuntimeError`, wenn das Parent-Verzeichnis ein Symlink ist (`realpath != absolute path`). Verhindert Path-Injection via attacker-kontrolliertem `NEWS_MONITOR_ALERTS_FILE` oder `NEWS_MONITOR_ALERTS_DIR`-Env in Multi-Tenant-Containern.
- **Neues Env `NEWS_MONITOR_ALERTS_DIR`** (bevorzugt). `NEWS_MONITOR_ALERTS_FILE` bleibt als Back-Compat-Fallback erhalten — mit identischem Symlink-Check.
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
