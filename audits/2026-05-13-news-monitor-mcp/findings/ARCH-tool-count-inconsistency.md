> ✅ **Re-Audit Status:** `closed` — gemerged via PR #6.

# Finding: ARCH-TOOL-COUNT — README/Code-Inkonsistenz bei Tool-Anzahl

| Feld | Wert |
|---|---|
| **Severity** | **low** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | ARCH (Documentation Consistency) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

- `README.md:42-53` listet **9 Tools** (Tabelle "Tools").
- `README.md:264-269` "Safety, Limits & Responsible Use" spricht von **15 Tools**.
- `src/news_monitor_mcp/__init__.py:1` Docstring: «globales News-Monitoring».
- `src/news_monitor_mcp/server.py:1` Docstring: «News Monitor MCP Server – 15 Tools».
- `mcp = FastMCP("news_monitor_mcp", instructions="… mit 15 Tools …")` (`server.py:204-214`).
- Reale Anzahl `@mcp.tool`-Decorators: **15** (9 monitoring + 4 alerts + 2 cache).

Der vorgestellte Tools-Tabelle im README fehlen also 6 Tools: `news_alert_create`, `news_alert_list`, `news_alert_check`, `news_alert_delete`, `news_cache_stats`, `news_cache_clear`.

## Expected Behavior

README-Tools-Tabelle synchron mit `@mcp.tool`-Decorators. CHANGELOG-Eintrag für v0.2.0 dokumentiert das Hinzufügen der Alert- und Cache-Tools, aber README-Übersicht ist nicht nachgezogen.

## Evidence

```bash
$ grep -c "@mcp.tool" src/news_monitor_mcp/server.py
15
```

README-Tabelle bei Zeile 42: 9 Zeilen.

## Risk Description

- **User-Verwirrung:** Onboarding-Reibung; Tools werden nicht entdeckt.
- **Audit-Risk:** Discrepancy zwischen Doku und Implementation ist klassischer ARCH-Smell ("Drift").

## Remediation

Tabelle erweitern und `instructions=` ggf. nochmal querprüfen:

```diff
  | 9 | `news_geo_search` | Location-specific news search |
+ | 10 | `news_alert_create` | Persistenten News-Alert erstellen |
+ | 11 | `news_alert_list` | Konfigurierte Alerts auflisten |
+ | 12 | `news_alert_check` | Alerts gegen aktuelle Daten prüfen |
+ | 13 | `news_alert_delete` | Alert permanent löschen |
+ | 14 | `news_cache_stats` | Cache-Statistik anzeigen |
+ | 15 | `news_cache_clear` | Cache leeren |
```

Gleiches in `README.de.md`.

## Effort Estimate

**S** (< 30 Minuten).

## Verification After Fix

- `pytest tests/test_doc_consistency.py::test_readme_lists_all_tools` (neu hinzufügen, parst README und vergleicht mit `mcp._tool_manager`).
