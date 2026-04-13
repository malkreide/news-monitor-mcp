> 🇨🇭 **Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide)**

# 📰 news-monitor-mcp

![Version](https://img.shields.io/badge/version-0.1.0-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![Data Source](https://img.shields.io/badge/Data-WorldNewsAPI-orange)](https://worldnewsapi.com/)
![CI](https://github.com/malkreide/news-monitor-mcp/actions/workflows/ci.yml/badge.svg)

> MCP server for global news monitoring, media analysis and sentiment tracking via WorldNewsAPI — full-text search across 150+ countries, German/English sentiment analysis, top headlines, GL briefings, newspaper front pages and geo-search. API key required.

[🇩🇪 Deutsche Version](README.de.md)

---

## Overview

**news-monitor-mcp** transforms any AI assistant into a proactive media intelligence agent. The server connects LLMs like Claude with global news data: from Swiss institutional reputation monitoring to weekly leadership briefings and trend detection across categories.

**Source:** WorldNewsAPI (worldnewsapi.com) — the only freely available news API with German-language sentiment analysis.

**API key required.** Get a free key at [worldnewsapi.com/console](https://worldnewsapi.com/console/) (1,000 calls/month free tier).

**Anchor demo query:**
*"How has the Schulamt Zürich been portrayed in the media over the last 30 days, and what is the overall sentiment?"*

---

## Features

- 🔍 **Full-text search** – 150+ countries, 50+ languages, Boolean queries and exact phrase matching
- 📊 **Sentiment analysis** – German and English only (WorldNewsAPI unique feature); scores from −1 (negative) to +1 (positive)
- 📰 **Top headlines** – clustered by country and language, ranked by number of sources reporting
- 📋 **Media briefing** – multi-topic weekly report with sentiment overview for GL / leadership updates
- 🗞️ **Newspaper front pages** – digital covers from 6,000+ publications in 125 countries
- 📡 **Trend radar** – category-based trend detection (politics, technology, education, …) per country
- 📍 **Geo-search** – location-specific news (Zürich, Bern, Basel, Kanton Zürich, …)
- ☁️ **Dual transport** – stdio for Claude Desktop, Streamable HTTP for cloud deployment

| # | Tool | Description |
|---|---|---|
| 1 | `news_search` | Full-text news search in 150+ countries |
| 2 | `news_top_headlines` | Top headlines by country and language |
| 3 | `news_sentiment_monitor` | Sentiment analysis for entity or topic |
| 4 | `news_media_briefing` | Multi-topic weekly briefing report |
| 5 | `news_retrieve_article` | Fetch full article by ID |
| 6 | `news_search_sources` | Find available news sources by name/country |
| 7 | `news_front_pages` | Digital newspaper front pages |
| 8 | `news_trend_radar` | Category-based trend detection per country |
| 9 | `news_geo_search` | Location-specific news search |

---

## Demo

![Media Briefing Demo](assets/demo-media-briefing.png)

> *"Create a media briefing for: AI in education, Volksschule Zürich, school digitalisation"*

---

## Data Sources

| Source | API Type | Content |
|---|---|---|
| **WorldNewsAPI** | REST JSON | 150+ countries, 50+ languages, full text, sentiment |

---

## Prerequisites

- Python 3.11+
- `uv` or `pip`
- API key from [worldnewsapi.com/console](https://worldnewsapi.com/console/) (free tier available)

---

## Installation

```bash
# Recommended: uvx (no install step needed)
uvx news-monitor-mcp

# Alternative: pip
pip install news-monitor-mcp
```

---

## Quickstart

```bash
# Start the server (stdio mode for Claude Desktop)
WORLD_NEWS_API_KEY=your-key uvx news-monitor-mcp
```

Try it immediately in Claude Desktop:
> *"Show me the top news from Switzerland today"*
> *"How is the Schulamt Zürich covered in German-language media this month?"*
> *"Create a media briefing on: Volksschule Zürich, AI in education, school digitalisation"*

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WORLD_NEWS_API_KEY` | – | **Required.** API key from worldnewsapi.com |
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` or `streamable_http` |
| `MCP_PORT` | `8000` | Port for HTTP transport |

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "news-monitor": {
      "command": "uvx",
      "args": ["news-monitor-mcp"],
      "env": {
        "WORLD_NEWS_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**Config file locations:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

After restarting Claude Desktop, all tools are available. Example queries:
- "Show me the top Swiss news today"
- "What is the media sentiment on AI in education this month?"
- "Create a weekly briefing for: Schulamt Zürich, Volksschule, KI Bildung"
- "Find all German-language articles about school digitalisation in the last 14 days"
- "Show me the front pages of Swiss newspapers today"

### Cloud Deployment (Streamable HTTP)

For use via **claude.ai in the browser** (e.g. on managed workstations without local software):

**Render.com (recommended):**
1. Push/fork the repository to GitHub
2. On [render.com](https://render.com): New Web Service → connect GitHub repo
3. Set `WORLD_NEWS_API_KEY` in the Render dashboard environment variables
4. In claude.ai under Settings → MCP Servers, add: `https://your-app.onrender.com/mcp`

```bash
# Docker / local HTTP mode
WORLD_NEWS_API_KEY=your-key MCP_TRANSPORT=streamable_http MCP_PORT=8000 python -m news_monitor_mcp.server
```

---

## Architecture

```
┌─────────────────┐    ┌──────────────────────────┐    ┌──────────────────────────┐
│  Claude / AI    │────▶│   News Monitor MCP        │────▶│   WorldNewsAPI           │
│  (MCP Host)     │◀────│   (MCP Server)            │◀────│   REST JSON API          │
└─────────────────┘    │                            │    │   150+ countries         │
                       │  9 Tools                   │    │   50+ languages          │
                       │  Stdio | Streamable HTTP   │    │   Sentiment DE/EN        │
                       └──────────────────────────┘    └──────────────────────────┘
```

---

## Project Structure

```
news-monitor-mcp/
├── src/
│   └── news_monitor_mcp/
│       ├── __init__.py
│       └── server.py          # All 9 tools
├── tests/
│   ├── __init__.py
│   └── test_server.py         # 20 tests (unit + live)
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md                  # This file (English)
└── README.de.md               # German version
```

---

## Testing

```bash
# Unit tests (no API key required)
PYTHONPATH=src pytest tests/ -m "not live"

# Integration tests (live API calls, API key required)
PYTHONPATH=src pytest tests/ -m "live"
```

---

## Example Use Cases

### Schulamt / Institutional Communication
```
"How has the Schulamt Zürich been portrayed in media over the last 30 days?"
→ news_sentiment_monitor(entity="Schulamt Zürich", language="de", days_back=30)

"Create a weekly media briefing for leadership"
→ news_media_briefing(topics=["Volksschule Zürich", "KI Bildung", "Schuldigitalisierung"])

"What are Swiss media reporting on school digitalisation?"
→ news_search(query="Schuldigitalisierung", language="de", source_country="ch")
```

### KI-Fachgruppe / AI Working Group
```
"What are the current tech trends in Swiss press this week?"
→ news_trend_radar(category="technology", source_country="ch", language="de")

"How are AI developments in education covered internationally?"
→ news_search(query="AI education classroom", language="en", number=20)

"Compare Swiss and German media coverage of AI regulation"
→ news_search(query="KI Regulierung", source_country="ch", language="de")
→ news_search(query="KI Regulierung", source_country="de", language="de")
```

### City Administration / Location Research
```
"What is being reported about Zürich school infrastructure?"
→ news_geo_search(location="Zürich", query="Schule")

"Show today's front pages of Swiss newspapers"
→ news_front_pages(source_country="ch")
```

---

## Sentiment Analysis

WorldNewsAPI offers German-language sentiment analysis — rare among news APIs:

| Score | Label | Meaning |
|---|---|---|
| > 0.3 | positiv 😊 | Positive coverage |
| −0.3 to 0.3 | neutral 😐 | Neutral / factual coverage |
| < −0.3 | negativ 😟 | Critical / negative coverage |

⚠️ **Sentiment is only available for German (`de`) and English (`en`).**

---

## Known Limitations

- **Sentiment analysis:** Only German (`de`) and English (`en`) — no French or Italian
- **Free tier:** 1,000 API calls/month, max 10 articles per call (paid plans: up to 100)
- **Historical data:** Free tier limited to 30 days; paid plans offer extended history
- **Source coverage:** Swiss regional media may be less well-indexed than national outlets

---

## Synergies with Other MCP Servers

`news-monitor-mcp` can be combined with other servers in the portfolio:

| Combination | Use Case |
|---|---|
| `+ fedlex-mcp` | Law meets discourse: legal framework + media coverage |
| `+ global-education-mcp` | OECD stats + current media context |
| `+ srgssr-mcp` | Swiss public media + international news comparison |
| `+ swiss-environment-mcp` | Environmental data + media reporting |
| `+ swiss-statistics-mcp` | BFS statistics + current media narrative |
| `+ zurich-opendata-mcp` | City data + local media coverage |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

---

## License

MIT License — see [LICENSE](LICENSE)

---

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)

---

## Credits & Related Projects

- **Data:** [WorldNewsAPI](https://worldnewsapi.com/) – global news data with sentiment analysis
- **Protocol:** [Model Context Protocol](https://modelcontextprotocol.io/) – Anthropic / Linux Foundation
- **Related:** [swiss-culture-mcp](https://github.com/malkreide/swiss-culture-mcp) – MCP server for Swiss cultural heritage data
- **Related:** [srgssr-mcp](https://github.com/malkreide/srgssr-mcp) – MCP server for SRG SSR Swiss public media
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide)
