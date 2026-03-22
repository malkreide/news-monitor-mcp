# Beitragen / Contributing

> 🇩🇪 [Deutsch](#deutsch) · 🇬🇧 [English](#english)

---

## Deutsch

Vielen Dank für Ihr Interesse an diesem Projekt! Beiträge sind willkommen.

### Wie kann ich beitragen?

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

### Code-Standards

- Python 3.11+, Ruff für Linting
- Docstrings auf Englisch (für internationale Kompatibilität)
- Kommentare und Fehlermeldungen dürfen Deutsch oder Englisch sein
- Alle MCP-Tools müssen `readOnlyHint: True` setzen (nur lesender Zugriff)
- Pydantic-Modelle für alle Tool-Inputs

### Datenquellen-Richtlinie

Dieser Server verwendet die **WorldNewsAPI** als einzige Datenquelle. Erweiterungen um weitere News-APIs sind willkommen, sofern sie:

- Einen Free Tier oder kostenlose Basiszugang anbieten
- Öffentlich dokumentiert und stabil verfügbar sind
- Schweizer oder deutschsprachige Quellen gut abdecken
- Den No-Auth-First-Grundsatz des Portfolios unterstützen (API-Key als Option, nicht Pflicht)

### Tests

Die Testsuite unterscheidet zwischen Unit-Tests (Mocks, kein Netzwerk) und Live-Tests (echte API-Aufrufe):

```bash
# Unit-Tests (immer ausführbar, kein Internet erforderlich)
PYTHONPATH=src pytest tests/ -m "not live"

# Live-Tests (Internet und gültiger WORLD_NEWS_API_KEY erforderlich)
WORLD_NEWS_API_KEY=dein-key PYTHONPATH=src pytest tests/ -m "live"
```

Live-Tests sind mit `@pytest.mark.live` markiert und werden in der CI-Pipeline ausgeschlossen.

---

## English

Thank you for your interest in this project! Contributions are welcome.

### How can I contribute?

**Report bugs:** Create an [Issue](../../issues) with a clear description, reproduction steps, and expected vs. actual output.

**Suggest features:** Describe the use case, ideally with a reference to the context of Swiss institutions (Schulamt, city administration, AI working group, GL briefings, etc.).

**Contribute code:**
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Write tests for your changes
5. Run linter: `ruff check src/ tests/`
6. Commit with clear message: `git commit -m "feat: add geo-search by municipality"`
7. Create a Pull Request

### Code Standards

- Python 3.11+, Ruff for linting
- Docstrings in English (for international compatibility)
- Comments and error messages may be in German or English
- All MCP tools must set `readOnlyHint: True` (read-only access)
- Pydantic models for all tool inputs

### Data Source Policy

This server uses **WorldNewsAPI** as its sole data source. Extensions with additional news APIs are welcome, provided they:

- Offer a free tier or free basic access
- Are publicly documented and reliably available
- Cover Swiss or German-language sources well
- Support the portfolio's No-Auth-First principle (API key optional, not mandatory)

### Tests

The test suite distinguishes between unit tests (mocked, no network) and live tests (real API calls):

```bash
# Unit tests (always runnable, no internet required)
PYTHONPATH=src pytest tests/ -m "not live"

# Live tests (internet and valid WORLD_NEWS_API_KEY required)
WORLD_NEWS_API_KEY=your-key PYTHONPATH=src pytest tests/ -m "live"
```

Live tests are marked with `@pytest.mark.live` and excluded from the CI pipeline.

---

## Lizenz / License

MIT – see [LICENSE](LICENSE)
