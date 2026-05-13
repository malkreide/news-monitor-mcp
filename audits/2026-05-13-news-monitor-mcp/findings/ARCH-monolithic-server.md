> ✅ **Re-Audit Status:** `closed` — gemerged via PR #17.

# Finding: ARCH-MONOLITHIC — Gesamter Server in einer 1130-Zeilen-Datei

| Feld | Wert |
|---|---|
| **Severity** | **medium** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | ARCH (Repo Structure / Modularity) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

`src/news_monitor_mcp/server.py` enthält **alles**:

- 15 Tool-Definitionen
- 9 Pydantic-Eingabe-Modelle
- `NewsCache` und `AlertManager` (Persistenz + Domain-Logik)
- HTTP-Client-Setup
- Error-Handling
- CLI-Entry-Point
- Markdown/JSON-Formatter

Gesamt: 1130 Zeilen (`wc -l`). Der `__init__.py` enthält nur `__version__`. Keine weiteren Module.

## Expected Behavior

Per ARCH-Best-Practice für FastMCP-Server:

```
src/news_monitor_mcp/
├── __init__.py
├── server.py            # FastMCP-Instanz + Entry-Point
├── config.py            # Env / Settings (pydantic-settings)
├── api_client.py        # httpx-Wrapper für WorldNewsAPI
├── cache.py             # NewsCache
├── alerts/
│   ├── manager.py       # AlertManager
│   └── models.py        # Alert-Pydantic-Modelle
├── tools/
│   ├── monitoring.py    # 9 read-only tools
│   ├── alerts.py        # 4 alert tools
│   └── cache_admin.py   # 2 cache tools
├── formatting.py        # Markdown/JSON
└── errors.py            # _handle_api_error
```

Tools registrieren sich beim `mcp`-Singleton (oder pro Modul mit `@mcp.tool` bei Import).

## Evidence

- `wc -l src/news_monitor_mcp/server.py` ⇒ 1130
- `find src -name "*.py" | wc -l` ⇒ 2 Files total

## Risk Description

- **Wartbarkeit:** Code-Reviews werden langsam; Merge-Konflikte häufiger bei parallelen Feature-Branches.
- **Test-Granularität:** Tests müssen den ganzen `server`-Namespace importieren; Mocking erfordert globale Patches statt Modul-lokale.
- **SOLID-Konformität:** Verstösst gegen Single-Responsibility — `AlertManager` macht Persistenz + Business-Logik (`evaluate_condition`) zugleich.
- **Onboarding:** Neue Contributor·innen müssen die ganze Datei lesen.

Kein direkter Security- oder Verfügbarkeits-Impact → Severity medium.

## Remediation

1. Snapshot des aktuellen Verhaltens via `pytest -m "not live" -q` (sollte grün sein vor Refactor).
2. Auslagern in Reihenfolge: `formatting.py` → `cache.py` → `alerts/manager.py` → `api_client.py` → `tools/*.py`.
3. Pro Schritt grüne Tests behalten.
4. Update `__init__.py` mit Convenience-Re-Exports nur dort, wo öffentliche API stabil bleiben muss (Backward-Compat für Tests).

## Effort Estimate

**M** (1–3 Tage).

## Dependencies / Blockers

Keine. Sollte vor weiteren Features priorisiert werden, weil späterer Refactor teurer wird.

## Verification After Fix

- `wc -l src/news_monitor_mcp/server.py` < 200.
- Test-Suite grün, identisches Coverage-Profil.
- `ruff check src/` ohne neue Warnings.
