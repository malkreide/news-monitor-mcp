# CLAUDE.md

## Teil 1 — Konventionen (portfolio-weit)

### Vor der Arbeit

Klon-Aktualität prüfen: `git fetch origin main && git rev-list --count HEAD..origin/main`
Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

### Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.

Zwei Fallen, die beide grün blieben:

- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
  echte Zeit nicht widerlegen.
- `monkeypatch.setattr(modul.asyncio, "sleep", ...)` greift ins Modul
  `asyncio` selbst und entschärft die Mechanik im ganzen Prozess. Patche
  einen Modul-Alias (`_sleep = asyncio.sleep`), nicht das fremde Modul.

Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

### Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess «nicht gefunden» nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

## Teil 2 — Dieses Repo

**ruff-Version:** CI pinnt `ruff==0.16.1` (`.github/workflows/ci.yml`, in
beiden Jobs `test` und `lint`). Es gibt **keine `.pre-commit-config.yaml`** —
also keine zweite Quelle, die abweichen könnte, aber auch keinen Hook, der
den Pin vor dem Commit durchsetzt. `pyproject.toml` führt als Dev-Abhängigkeit
`ruff>=0.4.0`; wer darüber installiert, bekommt die neuste Version, nicht die
der CI. Lokal deshalb explizit `pip install ruff==0.16.1`.

**Gates, wörtlich aus der CI:**

```bash
pip install ruff==0.16.1
python -m ruff check src/ tests/ scripts/
python -m ruff format --check src/ tests/ scripts/
python -m py_compile src/news_monitor_mcp/server.py
python -c "from news_monitor_mcp.server import mcp; print('Import OK')"
PYTHONPATH=src pytest tests/ -m "not live" -v
python scripts/check_version_sync.py
```

Dazu der Job `docker`: Image bauen, dann `--help` aus dem Image und der
Nachweis, dass der Container ohne `MCP_BEARER_TOKEN` mit Exit-Code 2 abbricht.
Test-Matrix: Python 3.11 / 3.12 / 3.13.

**Live-Tests:** Es gibt **keinen cron-getriggerten Workflow**. Die einzigen
Zeitpläne unter `.github/` stehen in `dependabot.yml`. Live-Tests
(`@pytest.mark.live`, sechs Stück in `tests/test_server.py`) sind in der CI
nur per `-m "not live"` ausgeschlossen und laufen damit nirgends automatisch.
→ **Befund: DRIFT-005** (5 von 10 geprüften Servern verletzen ihn). Ein
Schemawechsel bei `api.worldnewsapi.com` fällt hier erst auf, wenn jemand von
Hand `pytest -m live` fährt.
