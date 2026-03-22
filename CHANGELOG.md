# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
