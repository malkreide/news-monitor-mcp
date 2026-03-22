# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-03-22
### Added
- Initial PyPI publication

## [Unreleased]

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
