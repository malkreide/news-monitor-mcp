# Design Spec: Safety & Limits Section + Demo Assets
**Date:** 2026-04-12
**Repo:** news-monitor-mcp
**Status:** Approved

---

## Problem Statement

The `news-monitor-mcp` README (v0.2.0) lacks two elements that increase institutional adoption:

1. **Safety & Limits section** — Swiss public-sector institutions (Kantone, Schulämter) need governance signals (read-only, no personal data, ToS compliance) to approve MCP server deployments. The current `Known Limitations` section is purely technical and misses this.

2. **Demo asset** — Directory sites and LinkedIn posts convert significantly better with a screenshot showing Claude → Tool Call → Response. No visual assets exist in the repo.

---

## Approach: Expand & Merge (Approved)

Replace `Known Limitations` with an expanded `Safety, Limits & Responsible Use` section. Add a demo PNG after the Features Table. No new top-level headings that overlap with existing content.

---

## Design

### 1. `Safety, Limits & Responsible Use` Section

**Position:** Replaces existing `## Known Limitations` section (same location in document).
**Applies to:** `README.md` (English) and `README.de.md` (German translation).

#### German heading translations

| English | German |
|---|---|
| `## Safety, Limits & Responsible Use` | `## Sicherheit, Grenzen & verantwortungsvoller Einsatz` |
| `### Read-Only Operation` | `### Nur-Lese-Betrieb` |
| `### API Rate Limits` | `### API-Rate-Limits` |
| `### Data Privacy` | `### Datenschutz` |
| `### Responsible Use` | `### Verantwortungsvoller Einsatz` |
| `### Terms of Service` | `### Nutzungsbedingungen` |

The body text of `README.de.md` should be translated to German throughout, matching the style of the existing German README. The table structure, link URLs, and code references (`readOnlyHint`, file paths, version tags) remain unchanged.

#### Content Structure

```markdown
## Safety, Limits & Responsible Use

### Read-Only Operation
12 of the 15 tools carry `readOnlyHint: true`. All 9 monitoring tools (search,
headlines, sentiment, briefing, article, sources, front_pages, trend, geo) are
fully read-only and issue GET requests to WorldNewsAPI only. The 3 exceptions
are local-only operations: `news_alert_create` and `news_alert_delete` (write/
delete `~/.news-monitor-mcp/alerts.json`) and `news_cache_clear` (clears
in-memory cache). None of the 15 tools modify any external data source.

### API Rate Limits
| Constraint | WorldNewsAPI Free Tier | Paid Plans |
|---|---|---|
| Calls/month | 1,000 | Up to 1M |
| Articles/call | 10 | Up to 100 |
| Historical depth | 30 days | Extended |
| Timeout per call | 30 seconds | 30 seconds |

The TTL cache (v0.2+) reduces redundant calls by up to 80%.

### Data Privacy
- **No personal data stored:** The server holds no persistent user data.
  Cache entries are in-memory and reset on server restart.
- **No profiling:** The server retrieves publicly published journalism only.
  It is not designed for surveillance or personal profiling.
- **Alert data:** Alert configurations are stored locally in
  `~/.news-monitor-mcp/alerts.json` — on your machine only, never transmitted.

### Responsible Use
- Query public news only — do not use as a profiling tool for individuals.
- Sentiment scores reflect algorithmic analysis of journalistic tone,
  not verified editorial judgements.
- Results depend on WorldNewsAPI's indexing; Swiss regional media
  may be less well-covered than national outlets.

### Terms of Service
Users must comply with:
- [WorldNewsAPI Terms of Service](https://worldnewsapi.com/terms-of-service/)
- [WorldNewsAPI Privacy Policy](https://worldnewsapi.com/privacy-policy/)

This MCP server is an independent open-source project and is not affiliated
with WorldNewsAPI.
```

#### What replaces what

| Old content (Known Limitations) | New location |
|---|---|
| Sentiment: only DE/EN | Responsible Use bullet |
| Free tier: 1,000 calls/month, max 10 articles | API Rate Limits table |
| Historical data: 30 days free | API Rate Limits table |
| Source coverage: Swiss regional less indexed | Responsible Use bullet |

Nothing is lost — all existing limitation info is preserved in richer context.

---

### 2. Demo Asset

#### Files

| File | Purpose |
|---|---|
| `assets/demo-source.html` | Source HTML/CSS for the mockup (editable, version-controlled) |
| `assets/demo-media-briefing.png` | Screenshot of rendered HTML (committed to repo) |

#### README Integration

Inserted **after the Features Table**, **before `## Data Sources`**:

In `README.md` (English):
```markdown
## Demo

![Media Briefing Demo](assets/demo-media-briefing.png)

> *"Create a media briefing for: AI in education, Volksschule Zürich, school digitalisation"*
```

In `README.de.md` (German):
```markdown
## Demo

![Media Briefing Demo](assets/demo-media-briefing.png)

> *"Erstelle ein Medien-Briefing für: KI in Bildung, Volksschule Zürich, Schuldigitalisierung"*
```

#### Mockup Layout

Three-panel horizontal layout simulating a Claude conversation:

```
┌──────────────────┐  ┌────────────────────────────┐  ┌────────────────────────────┐
│  👤 User         │  │  🔧 Tool Call              │  │  🤖 Claude Response        │
│                  │  │                              │  │                            │
│ "Erstelle ein    │  │ news_media_briefing({        │  │ # Medien-Briefing          │
│  Medien-Briefing │  │   topics: [                  │  │                            │
│  für: KI Bildung,│  │    "KI in Bildung",          │  │ ## 😊 KI in Bildung        │
│  Volksschule     │  │    "Volksschule Zürich",      │  │ 12 Artikel | positiv (0.31)│
│  Zürich,         │  │    "Schuldigitalisierung"     │  │ - [Titel Artikel 1]...     │
│  Schuldigitali-  │  │   ],                         │  │                            │
│  sierung"        │  │   language: "de",             │  │ ## 😐 Volksschule Zürich   │
│                  │  │   days_back: 7,               │  │ 8 Artikel | neutral (0.04) │
│                  │  │   source_country: "ch,de,at"  │  │ - [Titel Artikel 2]...     │
└──────────────────┘  └────────────────────────────┘  └────────────────────────────┘
```

#### Visual Spec

- **Theme:** Dark mode (background `#1a1a2e`, panels `#16213e`)
- **User panel:** Gray text, soft left border
- **Tool Call panel:** Amber/orange monospace code block (distinguishes machine output)
- **Response panel:** White text, markdown-rendered headings
- **Width:** 1200px × 480px (optimised for GitHub README display and LinkedIn)
- **Font:** System sans-serif for prose, `monospace` for tool call

---

## Files Changed

| File | Change |
|---|---|
| `README.md` | Replace `## Known Limitations` → `## Safety, Limits & Responsible Use`; add `## Demo` after Features Table |
| `README.de.md` | Same changes, German translation |
| `assets/demo-source.html` | New file — HTML/CSS mockup source |
| `assets/demo-media-briefing.png` | New file — screenshot of mockup |

---

## Out of Scope

- No changes to `server.py` or any Python source
- No changes to `CHANGELOG.md` (this is a docs/asset update only)
- No changes to tests
- NewsData.io integration (separate spec)

---

## Success Criteria

- [ ] `README.md` contains `## Safety, Limits & Responsible Use` with all four sub-sections
- [ ] `README.de.md` mirrors the same structure in German
- [ ] `assets/demo-media-briefing.png` exists and renders correctly in GitHub README preview
- [ ] `assets/demo-source.html` committed for future editing
- [ ] No existing README content is lost
