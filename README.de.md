# news-monitor-mcp

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Lizenz: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-kompatibel-green.svg)](https://modelcontextprotocol.io/)

**MCP-Server für globales Nachrichten-Monitoring, Medienanalyse und Sentiment-Tracking via WorldNewsAPI.**

Entwickelt für Schweizer Behörden, Kommunikationsteams und KI-Fachgruppen, die strukturierte Medienintelligenz direkt im KI-Assistenten benötigen.

> 🇬🇧 [English Version (README.md)](README.md)

---

## Warum news-monitor-mcp?

Traditionelles Medienmonitoring erfordert manuelle Suchen in mehreren Portalen. Dieser MCP-Server verwandelt deinen KI-Assistenten in einen **proaktiven Medienintelligenz-Agenten**: Er durchsucht 150+ Länder in 50+ Sprachen, analysiert Sentiment auf Deutsch und Englisch, und erstellt strukturierte Briefings — alles über natürliche Sprache.

**Anchor Demo (für Stakeholder):**
> *«Zeige mir alle Berichte über das Schulamt Zürich der letzten 30 Tage, sortiert nach Sentiment.»*

Eine Frage. Ein Tool-Aufruf. Vollständige Medienanalyse.

---

## Funktionen

- **9 spezialisierte Tools** für Nachrichten-Monitoring-Workflows
- **Sentiment-Analyse** auf Deutsch und Englisch (WorldNewsAPI-Alleinstellungsmerkmal)
- **DACH-Fokus**: Optimiert für Schweizer, österreichische und deutsche Medienquellen
- **Medien-Briefings**: Multi-Themen-Berichte für GL- / Geschäftsleitungsupdates
- **Trend-Radar**: Kategorie-basierte Trenderkennung pro Land
- **Titelseiten**: Digitale Zeitungscovers von 6'000+ Publikationen
- **Geo-Suche**: Standortspezifische News (Zürich, Bern, Basel, ...)
- **No-Auth-First**: Kostenloser Einstieg (1'000 Calls/Monat)

---

## Tools

| Tool | Beschreibung | Einsatzbereich |
|------|-------------|----------------|
| `news_search` | Volltextsuche in 150+ Ländern | Stichwortrecherche, Themenmonitoring |
| `news_top_headlines` | Top-Schlagzeilen nach Land/Sprache | Tages-Briefing |
| `news_sentiment_monitor` | Sentiment-Analyse für Entität/Thema | Reputationsmonitoring |
| `news_media_briefing` | Wöchentlicher Multi-Themen-Bericht | GL- / Geschäftsleitungsupdate |
| `news_retrieve_article` | Vollständigen Artikel abrufen | Tiefenrecherche zu Einzelartikel |
| `news_search_sources` | Verfügbare Nachrichtenquellen finden | Schweizer Medien im Index prüfen |
| `news_front_pages` | Digitale Zeitungscovers | Agenda-Vergleich |
| `news_trend_radar` | Kategorie-Trends nach Land | Strategische Vorausschau |
| `news_geo_search` | Standortspezifische Nachrichten | Stadt-/Kantonsmonitoring |

---

## Installation

```bash
uvx news-monitor-mcp
```

Oder lokal klonen und installieren:

```bash
git clone https://github.com/malkreide/news-monitor-mcp
cd news-monitor-mcp
pip install -e .
```

**API-Key erforderlich:** Kostenloser Key unter [worldnewsapi.com/console](https://worldnewsapi.com/console/)

---

## Konfiguration

### Claude Desktop (`claude_desktop_config.json`)

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

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### HTTP-Modus (Streamable HTTP / Render.com)

```bash
news-monitor-mcp --http --port 8000
```

---

## Beispiel-Abfragen

### Reputationsmonitoring (Schulamt Zürich)
```
Analysiere die Medienberichterstattung zum Schulamt Zürich der letzten 30 Tage.
Wie ist das Sentiment?
```
→ Tool: `news_sentiment_monitor`

### Wöchentliches GL-Briefing
```
Erstelle ein Medien-Briefing zu den Themen: Volksschule Zürich, KI Bildung, 
Schuldigitalisierung, Lehrplan 21
```
→ Tool: `news_media_briefing`

### KI-Fachgruppe Trend-Radar
```
Was sind die aktuellen Tech-Trends in der Schweizer Presse diese Woche?
```
→ Tool: `news_trend_radar` (category: "technology", source_country: "ch")

### Bildungsforschung International
```
Zeige mir internationale Artikel über KI im Unterricht auf Englisch.
```
→ Tool: `news_search` (query: "AI education classroom", language: "en")

---

## Sentiment-Analyse

WorldNewsAPI bietet deutschsprachige Sentiment-Analyse — ein Alleinstellungsmerkmal unter News-APIs:

| Score | Label | Bedeutung |
|-------|-------|-----------|
| > 0,3 | positiv 😊 | Positive Berichterstattung |
| -0,3 bis 0,3 | neutral 😐 | Neutrale/sachliche Berichterstattung |
| < -0,3 | negativ 😟 | Kritische/negative Berichterstattung |

⚠️ **Sentiment ist nur für Deutsch (`de`) und Englisch (`en`) verfügbar.**

---

## Portfolio-Integration

Dieser Server ist Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide):

| Kombination | Einsatzbereich | Beispiel-Abfrage |
|-------------|----------------|------------------|
| `news-monitor-mcp` + `fedlex-mcp` | Recht trifft Diskurs | «Was sagt Schweizer Recht zu KI in Schulen — und wie wird darüber berichtet?» |
| `news-monitor-mcp` + `global-education-mcp` | Zahlen + Kontext | «OECD-PISA-Rang der Schweiz — und was sagen Medien dazu?» |
| `news-monitor-mcp` + `srgssr-mcp` | Schweiz + International | «SRF-News + internationaler Berichterstattungsvergleich» |
| `news-monitor-mcp` + `swiss-environment-mcp` | Daten + Diskurs | «Schlechte Luftqualität heute in Zürich — was berichten Medien?» |
| `news-monitor-mcp` + `swiss-statistics-mcp` | Zahlen + Narrativ | «BFS-Schulstatistiken + aktuelle Medienberichterstattung» |

---

## Entwicklung

```bash
# Abhängigkeiten installieren
pip install -e ".[dev]"

# Unit-Tests ausführen (kein API-Key nötig)
pytest -m "not live"

# Mit Coverage
pytest --cov=news_monitor_mcp -m "not live"

# Live-Tests (WORLD_NEWS_API_KEY erforderlich)
pytest -m live

# Linting
ruff check src/
```

---

## Free-Tier-Limits

WorldNewsAPI Free Tier:
- **1'000 API-Calls/Monat**
- **10 Artikel pro Call** (kostenpflichtig: bis 100)
- **30 Tage Historiendaten**

Für den Produktionseinsatz in Organisationen empfiehlt sich der Basic- oder Advanced-Plan.

---

## Lizenz

MIT-Lizenz — siehe [LICENSE](LICENSE) für Details.

---

## Mitmachen

Siehe [CONTRIBUTING.md](CONTRIBUTING.md) für Beitragsrichtlinien, Commit-Konventionen und Datenquellen-Policy.

---

*Teil des Swiss Public Data MCP Server Portfolios von [@malkreide](https://github.com/malkreide)*
