[🇬🇧 English Version](README.md)

> 🇨🇭 **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide)**

# 📰 news-monitor-mcp

![Version](https://img.shields.io/badge/version-0.3.6-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![Datenquelle](https://img.shields.io/badge/Daten-WorldNewsAPI-orange)](https://worldnewsapi.com/)
![CI](https://github.com/malkreide/news-monitor-mcp/actions/workflows/ci.yml/badge.svg)

> MCP-Server für globales Nachrichten-Monitoring, Medienanalyse und Sentiment-Tracking via WorldNewsAPI — Volltextsuche in 150+ Ländern, Sentiment-Analyse auf Deutsch und Englisch, Top-Schlagzeilen, GL-Briefings, Zeitungscovers und Geo-Suche. API-Schlüssel erforderlich.

---

## Übersicht

**news-monitor-mcp** verwandelt jeden KI-Assistenten in einen proaktiven Medienintelligenz-Agenten. Der Server verbindet LLMs wie Claude mit globalen Nachrichtendaten: vom Reputationsmonitoring Schweizer Institutionen bis zu wöchentlichen GL-Briefings und Trenderkennung nach Kategorien.

**Quelle:** WorldNewsAPI (worldnewsapi.com) — die einzige frei zugängliche News-API mit deutschsprachiger Sentiment-Analyse.

**API-Schlüssel erforderlich.** Kostenloser Key unter [worldnewsapi.com/console](https://worldnewsapi.com/console/) (1'000 Calls/Monat im Free Tier).

**Anker-Demo-Abfrage:**
*«Wie wurde das Schulamt Zürich in den letzten 30 Tagen in den Medien dargestellt, und wie ist das Gesamt-Sentiment?»*

---

## Funktionen

- 🔍 **Volltextsuche** – 150+ Länder, 50+ Sprachen, Boolean-Abfragen und exakte Phrasensuche
- 📊 **Sentiment-Analyse** – nur Deutsch und Englisch (WorldNewsAPI-Alleinstellungsmerkmal); Werte von −1 (negativ) bis +1 (positiv)
- 📰 **Top-Schlagzeilen** – nach Land und Sprache geclustert, gereiht nach Anzahl berichtender Quellen
- 📋 **Medien-Briefing** – Multi-Themen-Wochenbericht mit Sentiment-Übersicht für GL- / Geschäftsleitungs-Updates
- 🗞️ **Zeitungscovers** – digitale Titelseiten von 6'000+ Publikationen in 125 Ländern
- 📡 **Trend-Radar** – kategoriebasierte Trenderkennung (Politik, Technologie, Bildung, …) pro Land
- 📍 **Geo-Suche** – standortspezifische Nachrichten (Zürich, Bern, Basel, Kanton Zürich, …)
- ☁️ **Dual Transport** – stdio für Claude Desktop, Streamable HTTP für Cloud-Deployment

| # | Tool | Beschreibung |
|---|---|---|
| 1 | `news_search` | Volltextsuche in 150+ Ländern |
| 2 | `news_top_headlines` | Top-Schlagzeilen nach Land und Sprache |
| 3 | `news_sentiment_monitor` | Sentiment-Analyse für Entität oder Thema |
| 4 | `news_media_briefing` | Multi-Themen-Wochenbericht |
| 5 | `news_retrieve_article` | Vollständigen Artikel per ID abrufen |
| 6 | `news_search_sources` | Nachrichtenquellen nach Name/Land suchen |
| 7 | `news_front_pages` | Digitale Zeitungscovers |
| 8 | `news_trend_radar` | Kategorie-basierte Trenderkennung pro Land |
| 9 | `news_geo_search` | Standortspezifische Nachrichtensuche |
| 10 | `news_alert_create` | Persistenten Alert erstellen (Sentiment / Volume / Keyword) |
| 11 | `news_alert_list` | Konfigurierte Alerts mit Status auflisten |
| 12 | `news_alert_check` | Alerts gegen aktuelle Daten prüfen |
| 13 | `news_alert_delete` | Alert permanent löschen |
| 14 | `news_cache_stats` | Cache-Trefferquote und Einträge nach Typ |
| 15 | `news_cache_clear` | Cache leeren (komplett oder pro Tool-Typ) |

---

## Demo

![Media Briefing Demo](assets/demo-media-briefing.png)

> *"Erstelle ein Medien-Briefing für: KI in Bildung, Volksschule Zürich, Schuldigitalisierung"*

---

## Datenquellen

| Quelle | API-Typ | Inhalt |
|---|---|---|
| **WorldNewsAPI** | REST JSON | 150+ Länder, 50+ Sprachen, Volltext, Sentiment |

---

## Voraussetzungen

- Python 3.11+
- `uv` oder `pip`
- API-Schlüssel von [worldnewsapi.com/console](https://worldnewsapi.com/console/) (Free Tier verfügbar)

---

## Installation

```bash
# Empfohlen: uvx (kein Installationsschritt nötig)
uvx news-monitor-mcp

# Alternativ: pip
pip install news-monitor-mcp
```

---

## Schnellstart

```bash
# Server starten (stdio-Modus für Claude Desktop)
WORLD_NEWS_API_KEY=dein-key uvx news-monitor-mcp
```

Sofort in Claude Desktop ausprobieren:
> *«Zeig mir die Top-Nachrichten aus der Schweiz heute»*
> *«Wie wird das Schulamt Zürich in deutschsprachigen Medien diesen Monat dargestellt?»*
> *«Erstelle ein Medien-Briefing zu: Volksschule Zürich, KI in der Bildung, Schuldigitalisierung»*

---

## Konfiguration

### Umgebungsvariablen

| Umgebungsvariable | Standard | Beschreibung |
|---|---|---|
| `WORLD_NEWS_API_KEY` | – | **Erforderlich.** API-Schlüssel von worldnewsapi.com |
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` oder `streamable_http` |
| `MCP_HOST` | `127.0.0.1` | HTTP-Bind-Host. `0.0.0.0` nur innerhalb eines Containers verwenden. |
| `MCP_PORT` | `8000` | Port für HTTP-Transport |
| `MCP_BEARER_TOKEN` | – | **Pflicht im `--http`-Mode.** Bearer-Token, den Clients per `Authorization: Bearer <token>` mitsenden müssen. Generieren mit `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |
| `MCP_ALLOWED_ORIGINS` | – | Optionale CSV-Allowlist für den `Origin`-Header (Schutz gegen DNS-Rebinding). Beispiel: `https://claude.ai`. |
| `LOG_LEVEL` | `INFO` | Log-Level: `DEBUG` / `INFO` / `WARNING` / `ERROR`. Logs werden als JSON nach stderr geschrieben; `api-key=`-Query-Parameter und `Authorization: Bearer`-Header werden automatisch maskiert. |
| `NEWS_MONITOR_ALERTS_DIR` | `~/.news-monitor-mcp` | Verzeichnis für `alerts.json`. Das Parent-Verzeichnis darf kein Symlink sein (wird beim Start als Schutz gegen Path-Injection abgewiesen). File wird mit Mode `0o600`, Dir mit `0o700` angelegt. |
| `NEWS_MONITOR_ALERTS_FILE` | – | *(Back-Compat)* expliziter Pfad zur Alert-Datei. Gleiche Symlink-Prüfung. Bevorzugt `NEWS_MONITOR_ALERTS_DIR`. |
| `MCP_ALERT_RETENTION_DAYS` | `90` | Alerts älter als diese Anzahl Tage werden beim Server-Start gelöscht (Privacy-Default per [`docs/privacy-dsg.md`](docs/privacy-dsg.md)). `0` deaktiviert Retention. |
| `MCP_CACHE_MAX_PER_TYPE` | `1000` | Maximale Cache-Einträge pro Tool-Typ. Wenn überschritten, wird der am längsten ungenutzte Eintrag dieses Typs verdrängt. `0` deaktiviert den Cap (unbegrenztes Wachstum — nur für kurzlebige Prozesse sicher). |
| `MCP_CACHE_SWEEP_SECONDS` | `300` | Intervall für den Background-Task, der TTL-abgelaufene Cache-Einträge entfernt. `0` deaktiviert den Sweep (abgelaufene Einträge werden weiterhin lazy bei `news_cache_stats` aufgeräumt). |

### Claude Desktop Konfiguration

```json
{
  "mcpServers": {
    "news-monitor": {
      "command": "uvx",
      "args": ["news-monitor-mcp"],
      "env": {
        "WORLD_NEWS_API_KEY": "dein-api-key-hier"
      }
    }
  }
}
```

**Pfad zur Konfigurationsdatei:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Nach Neustart von Claude Desktop stehen alle Tools zur Verfügung. Beispielfragen:
- «Zeig mir die Top-Schweizer-Nachrichten heute»
- «Wie ist das Medien-Sentiment zu KI in der Bildung diesen Monat?»
- «Erstelle ein Wochen-Briefing für: Schulamt Zürich, Volksschule, KI Bildung»
- «Alle deutschsprachigen Artikel zur Schuldigitalisierung der letzten 14 Tage»
- «Zeig mir die Titelseiten Schweizer Zeitungen heute»

### Cloud-Deployment (Streamable HTTP)

Für den Einsatz via **claude.ai im Browser** (z. B. auf verwalteten Arbeitsplätzen ohne lokale Software-Installation):

**Authentifizierung ist Pflicht.** Der HTTP-Transport weist jeden Request ohne gültigen `Authorization: Bearer <token>`-Header mit HTTP 401 ab. Token einmalig erzeugen und geheim halten:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Render.com (empfohlen):**
1. Repository auf GitHub pushen/forken
2. Auf [render.com](https://render.com): New Web Service → GitHub-Repo verbinden
3. Folgende Umgebungsvariablen in Render setzen:
   - `WORLD_NEWS_API_KEY` — dein WorldNewsAPI-Schlüssel
   - `MCP_BEARER_TOKEN` — der oben generierte Token
   - `MCP_HOST=0.0.0.0` — Bind auf alle Interfaces innerhalb des Containers
   - `MCP_ALLOWED_ORIGINS=https://claude.ai` *(optional, empfohlen)*
4. In claude.ai unter Settings → MCP Servers `https://your-app.onrender.com/mcp` eintragen und den Bearer-Token als Auth-Header konfigurieren.

```bash
# Lokaler HTTP-Modus (bindet standardmaessig auf 127.0.0.1)
WORLD_NEWS_API_KEY=dein-key \
  MCP_BEARER_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))") \
  news-monitor-mcp --http --port 8000

# Auth-Erzwingung verifizieren
curl -i http://127.0.0.1:8000/mcp                                  # → 401
curl -i -H "Authorization: Bearer $MCP_BEARER_TOKEN" http://127.0.0.1:8000/mcp
```

### Container-Image

Ein non-root Multi-Stage-`Dockerfile` liegt im Repo und wird in jedem CI-Lauf gebaut. Im Container läuft der Server per Default mit `--http`, bindet `0.0.0.0:8000`, persistiert Alerts unter `/data` und weigert sich zu starten, wenn `MCP_BEARER_TOKEN` fehlt.

```bash
docker build -t news-monitor-mcp .

docker run --rm -p 8000:8000 \
  -e WORLD_NEWS_API_KEY=dein-key \
  -e MCP_BEARER_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))") \
  -e MCP_ALLOWED_ORIGINS=https://claude.ai \
  -v news-monitor-data:/data \
  news-monitor-mcp
```

---

## Architektur

```
┌─────────────────┐    ┌──────────────────────────┐    ┌──────────────────────────┐
│  Claude / KI    │────▶│   News Monitor MCP        │────▶│   WorldNewsAPI           │
│  (MCP Host)     │◀────│   (MCP Server)            │◀────│   REST JSON API          │
└─────────────────┘    │                            │    │   150+ Länder            │
                       │  9 Tools                   │    │   50+ Sprachen           │
                       │  Stdio | Streamable HTTP   │    │   Sentiment DE/EN        │
                       └──────────────────────────┘    └──────────────────────────┘
```

---

## Projektstruktur

```
news-monitor-mcp/
├── src/
│   └── news_monitor_mcp/
│       ├── __init__.py
│       └── server.py          # Alle 9 Tools
├── tests/
│   ├── __init__.py
│   ├── fixtures/              # Aufgezeichneter Routenbestand + PROVENANCE.md
│   ├── test_antwortform.py    # Vertragstests (laufen in der CI)
│   └── test_server.py         # Unit- und Live-Tests
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md                  # Englische Hauptversion
└── README.de.md               # Diese Datei (Deutsch)
```

---

## Tests

```bash
# Unit- und Vertragstests (ohne Netz) — das fährt die CI
PYTHONPATH=src pytest tests/ -m "not live"

# Live-Tests. Die Routenprüfung braucht keinen Schlüssel;
# die Datentests überspringen sich ohne einen.
PYTHONPATH=src pytest tests/ -m "live"

# Routenbestand neu aufzeichnen (schreibt tests/fixtures/ + PROVENANCE.md)
PYTHONPATH=src python scripts/record_fixtures.py
```

**135 Tests** — 130 offline, 5 live (zwei davon ohne API-Key).

### Drei Live-Tests liefen nie

Bis zum 2026-08-08 trugen die drei Live-Tests dieses Repos `@pytest.mark.live`,
aber keinen `@pytest.mark.asyncio`. Im Strict-Default von pytest-asyncio heisst
das nicht «übersprungen», sondern `async def functions are not natively
supported`. Sie liefen also nie, und wer `-m live` aufrief, bekam drei Fehler,
die nichts über die Quelle aussagten. Die CI schliesst `-m live` aus, also
meldete es niemand.

`asyncio_mode = "auto"` macht eine vergessene Markierung jetzt wirkungslos.

Und laufend hätten sie ebenfalls wenig gezeigt:

```python
assert "Volksschule" in result or "Ergebnisse" in result
```

Der zweite Zweig trifft die eigene Ergebnis-Überschrift des Werkzeugs, die
Disjunktion konnte also nicht fehlschlagen. `assert "Top-Schlagzeilen" in
result` und `assert "Sentiment" in result` trafen ebenfalls nur die Vorlage.
Alle drei sichern jetzt etwas zu, das fehlschlagen kann — und sie
**überspringen** sich ohne Schlüssel, statt rot zu melden: «rot» soll heissen,
dass etwas nicht stimmt, nicht dass jemand keinen Schlüssel hat.

### Was ohne Schlüssel belegt ist — und was nicht

`tests/fixtures/api_routen.json` hält für jeden der fünf Pfade, die die
Werkzeuge bauen, Statuscode und Content-Type fest, ohne Schlüssel gemessen. Das
Gateway routet **vor** der Authentifizierung:

| Pfad | Antwort |
|---|---|
| die fünf Pfade, die der Server baut | 401, `application/json` |
| ein frei erfundener Pfad (Kontrolle) | 404, `text/html` |

Ein 401 heisst dort also «diese Route gibt es». Ohne die Kontrolle hiesse es nur
«ich habe einen 401 bekommen» — und das ist keine Selbstverständlichkeit:
`epl.bag.admin.ch` im selben Portfolio antwortet auch auf erfundene Pfade mit
401. Der Recorder misst die Kontrolle deshalb bei jedem Lauf mit und bricht ab,
wenn sie nicht mehr unterscheidet.

**Offen und in `PROVENANCE.md` als offen markiert:** ob die
Query-Parameternamen stimmen, die der Server sendet. Die API antwortet
unabhängig von den Parametern mit 401; ohne Schlüssel ist das nicht prüfbar. In
`global-education-mcp` desselben Portfolios ging genau das schief — zwei Filter
waren still wirkungslos, weil unbekannte Parameter mit HTTP 200 beantwortet und
fallengelassen wurden. Diese Prüfung steht aus, sie gilt nicht als erledigt.

### Leere Treffermenge ist nicht dasselbe wie geänderte Antwortform

`data.get("news", [])` beantwortet zwei völlig verschiedene Fälle gleich: «die
Quelle hat nichts gefunden» und «die Quelle antwortet anders, als wir
annehmen». Aus dem zweiten wird «0 Ergebnisse» — vollständig, plausibel,
formatiert und falsch. Das ist kein Gedankenspiel: In `global-education-mcp`
hiess der Umschlag inzwischen anders, aus **jeder** Antwort kam eine leere
Liste, und 128 Tests blieben grün.

`articles_of()` liest den Umschlag jetzt. Ein leeres `news` bleibt eine leere
Liste — das ist eine Aussage der Quelle. Ein *fehlendes* `news` ist keine
Aussage über die Nachrichten, sondern über die Antwort, und wird als solche
gemeldet.

---

## Anwendungsbeispiele

### Schulamt / Institutionskommunikation
```
«Wie wurde das Schulamt Zürich in den letzten 30 Tagen in den Medien dargestellt?»
→ news_sentiment_monitor(entity="Schulamt Zürich", language="de", days_back=30)

«Erstelle ein wöchentliches Medien-Briefing für die Geschäftsleitung»
→ news_media_briefing(topics=["Volksschule Zürich", "KI Bildung", "Schuldigitalisierung"])

«Was berichten Schweizer Medien zur Schuldigitalisierung?»
→ news_search(query="Schuldigitalisierung", language="de", source_country="ch")
```

### KI-Fachgruppe
```
«Was sind die aktuellen Tech-Trends in der Schweizer Presse diese Woche?»
→ news_trend_radar(category="technology", source_country="ch", language="de")

«Wie wird KI-Entwicklung in der Bildung international berichtet?»
→ news_search(query="AI education classroom", language="en", number=20)

«Vergleich Schweizer und deutscher Medien zur KI-Regulierung»
→ news_search(query="KI Regulierung", source_country="ch", language="de")
→ news_search(query="KI Regulierung", source_country="de", language="de")
```

### Stadtverwaltung / Standortrecherche
```
«Was wird über die Schulinfrastruktur in Zürich berichtet?»
→ news_geo_search(location="Zürich", query="Schule")

«Zeig die heutigen Titelseiten Schweizer Zeitungen»
→ news_front_pages(source_country="ch")
```

→ [Weitere Anwendungsbeispiele nach Zielgruppe](EXAMPLES.md) →

---

## Sentiment-Analyse

WorldNewsAPI bietet deutschsprachige Sentiment-Analyse — ein Alleinstellungsmerkmal unter News-APIs:

| Score | Label | Bedeutung |
|---|---|---|
| > 0,3 | positiv 😊 | Positive Berichterstattung |
| −0,3 bis 0,3 | neutral 😐 | Neutrale / sachliche Berichterstattung |
| < −0,3 | negativ 😟 | Kritische / negative Berichterstattung |

⚠️ **Sentiment ist nur für Deutsch (`de`) und Englisch (`en`) verfügbar.**

---

## Sicherheit, Grenzen & verantwortungsvoller Einsatz

### Nur-Lese-Betrieb
12 der 15 Tools tragen `readOnlyHint: true`. Alle 9 Monitoring-Tools (Suche,
Headlines, Sentiment, Briefing, Artikel, Quellen, Titelseiten, Trends, Geo)
sind vollständig schreibgeschützt und senden nur GET-Anfragen an die WorldNewsAPI.
Die 3 Ausnahmen sind lokale Operationen: `news_alert_create` und `news_alert_delete`
(schreiben/löschen `~/.news-monitor-mcp/alerts.json`) und `news_cache_clear`
(leert den In-Memory-Cache). Keines der 15 Tools verändert externe Datenquellen.

### API-Rate-Limits

| Einschränkung | WorldNewsAPI Free Tier | Kostenpflichtige Pläne |
|---|---|---|
| Calls/Monat | 1'000 | Bis 1M |
| Artikel/Call | 10 | Bis 100 |
| Historische Tiefe | 30 Tage | Erweitert |
| Timeout pro Call | 30 Sekunden | 30 Sekunden |

Der TTL-Cache (v0.2+) reduziert redundante API-Calls um bis zu 80%.

### Datenschutz

- **Keine personenbezogenen Daten gespeichert:** Der Server speichert keine persistenten Nutzerdaten. Cache-Einträge liegen im Arbeitsspeicher und werden beim Serverneustart zurückgesetzt.
- **Kein Profiling:** Der Server ruft ausschliesslich öffentlich erschienene Nachrichtenartikel ab. Er ist nicht für die Überwachung oder das Profiling von Personen konzipiert.
- **Alert-Daten:** Alert-Konfigurationen werden lokal in `~/.news-monitor-mcp/alerts.json` gespeichert — ausschliesslich auf dem eigenen Gerät, niemals übertragen.

### Verantwortungsvoller Einsatz

- Nur öffentliche Nachrichten abfragen — nicht als Profiling-Tool für Einzelpersonen einsetzen.
- Sentiment-Scores spiegeln die algorithmische Analyse des journalistischen Tons wider, keine verifizierten redaktionellen Urteile.
- Ergebnisse hängen von der Indexierung durch WorldNewsAPI ab; Schweizer Regionalmedien sind möglicherweise weniger gut abgedeckt als nationale Titel.

### Nutzungsbedingungen

Nutzerinnen und Nutzer müssen folgende Bedingungen einhalten:
- [WorldNewsAPI Nutzungsbedingungen](https://worldnewsapi.com/terms-of-service/)
- [WorldNewsAPI Datenschutzerklärung](https://worldnewsapi.com/privacy-policy/)

Dieser MCP-Server ist ein unabhängiges Open-Source-Projekt und steht in keiner Verbindung mit WorldNewsAPI.

---

## Synergie mit anderen MCP-Servern

`news-monitor-mcp` lässt sich mit anderen Servern des Portfolios kombinieren:

| Kombination | Anwendungsfall |
|---|---|
| `+ fedlex-mcp` | Recht trifft Diskurs: Rechtsgrundlagen + Medienberichterstattung |
| `+ global-education-mcp` | OECD-Statistiken + aktueller Medienkontext |
| `+ srgssr-mcp` | Schweizer Öffentlichkeitsmedien + internationaler Nachrichtenvergleich |
| `+ swiss-environment-mcp` | Umweltdaten + Medienberichterstattung |
| `+ swiss-statistics-mcp` | BFS-Statistiken + aktuelles Mediennarrativ |
| `+ zurich-opendata-mcp` | Stadtdaten + lokale Medienberichterstattung |

---

## Mitwirken

Siehe [CONTRIBUTING.de.md](CONTRIBUTING.de.md) ([English](CONTRIBUTING.md)).

---

## Sicherheit & Compliance

- Schwachstellen privat melden: siehe [SECURITY.md](SECURITY.md)
- Schweizer Behörden-Einsatz: [`docs/isds-klassifikation.md`](docs/isds-klassifikation.md) (ISDS / Schutzbedarfsfeststellung)
- Schweizer Datenschutz (revDSG) — Pflichten, Profiling, Retention, Drittlandtransfer: [`docs/privacy-dsg.md`](docs/privacy-dsg.md)
- Audit-Historie: [`audits/`](audits/)

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

---

## Lizenz

MIT-Lizenz – siehe [LICENSE](LICENSE)

---

## Autor

Hayal Oezkan · [malkreide](https://github.com/malkreide)

---

## Credits & Verwandte Projekte

- **Daten:** [WorldNewsAPI](https://worldnewsapi.com/) – globale Nachrichtendaten mit Sentiment-Analyse
- **Protokoll:** [Model Context Protocol](https://modelcontextprotocol.io/) – Anthropic / Linux Foundation
- **Verwandt:** [swiss-culture-mcp](https://github.com/malkreide/swiss-culture-mcp) – MCP-Server für Schweizer Kulturdaten
- **Verwandt:** [srgssr-mcp](https://github.com/malkreide/srgssr-mcp) – MCP-Server für SRG SSR Schweizer Öffentlichkeitsmedien
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide)
