# Beitragen zu news-monitor-mcp

Vielen Dank für Ihr Interesse an diesem Projekt! Dieser MCP-Server ist Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide) und folgt den gemeinsamen Konventionen des Portfolios.

[🇬🇧 English Version](CONTRIBUTING.md)

---

## Wie kann ich beitragen?

**Fehler melden:** Erstellen Sie ein [Issue](../../issues) mit einer klaren Beschreibung des Problems, Schritten zur Reproduktion und der erwarteten vs. tatsächlichen Ausgabe.

**Feature vorschlagen:** Beschreiben Sie den Use Case, idealerweise mit einem Bezug zum Kontext von Schweizer Institutionen (Schulamt, Stadtverwaltung, KI-Fachgruppe, GL-Briefings etc.).

**Code beitragen:**
1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch: `git checkout -b feature/mein-feature`
3. Installieren Sie die Dev-Abhängigkeiten: `pip install -e ".[dev]"`
4. Schreiben Sie Tests für Ihre Änderungen
5. Lint prüfen: `ruff check src/ tests/`
6. Commit mit aussagekräftiger Nachricht: `git commit -m "feat: Geo-Suche nach Gemeinde hinzufügen"`
7. Pull Request erstellen

## Code-Standards

- Python 3.11+, Ruff für Linting
- Docstrings auf Englisch (für internationale Kompatibilität)
- Kommentare und Fehlermeldungen dürfen Deutsch oder Englisch sein
- Alle MCP-Tools müssen `readOnlyHint: True` setzen (nur lesender Zugriff)
- Pydantic-Modelle für alle Tool-Inputs

## Datenquellen-Richtlinie

Dieser Server verwendet die **WorldNewsAPI** als einzige Datenquelle. Erweiterungen um weitere News-APIs sind willkommen, sofern sie:

- Einen Free Tier oder kostenlosen Basiszugang anbieten
- Öffentlich dokumentiert und stabil verfügbar sind
- Schweizer oder deutschsprachige Quellen gut abdecken
- Den No-Auth-First-Grundsatz des Portfolios unterstützen (API-Key als Option, nicht Pflicht)

## Tests

Die Testsuite unterscheidet zwischen Unit-Tests (Mocks, kein Netzwerk) und Live-Tests (echte API-Aufrufe):

```bash
# Unit-Tests (immer ausführbar, kein Internet erforderlich)
PYTHONPATH=src pytest tests/ -m "not live"

# Live-Tests (Internet und gültiger WORLD_NEWS_API_KEY erforderlich)
WORLD_NEWS_API_KEY=dein-key PYTHONPATH=src pytest tests/ -m "live"
```

Live-Tests sind mit `@pytest.mark.live` markiert und werden in der Push-/PR-CI
ausgeschlossen. Stattdessen laufen sie geplant — täglich um 06:17 UTC über
[`.github/workflows/live-tests.yml`](.github/workflows/live-tests.yml), der sich
per `workflow_dispatch` auch von Hand starten lässt.

---

## Lizenz

MIT – siehe [LICENSE](LICENSE)
