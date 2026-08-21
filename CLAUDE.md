# CLAUDE.md

## Teil 1 — Konventionen (portfolio-weit)

### Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen:

```bash
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

In diesem Repo läuft die Prüfung zusätzlich als SessionStart-Hook
(`.claude/hooks/session-start.sh`, registriert in `.claude/settings.json`).
Er meldet nur, wenn Commits fehlen, und geht bei jedem Netz-, Remote- oder
Git-Problem still durch — er ersetzt den Handgriff oben deshalb nicht,
sondern fängt das Vergessen ab. Sein Schweigen ist kein Beleg für einen
aktuellen Klon.

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

### Wenn zwei Agenten dasselbe tun

Vor dem Anlegen eines Branches mit vorgegebenem Namen prüfen, ob es ihn schon
gibt:

```bash
git ls-remote --heads origin claude/<name> | wc -l
```

Steht dort `1`, arbeitet jemand anderes daran — mit Schreibrecht auf denselben
Ref.

Ein PR mit leerem Diff wird geschlossen, nicht gemergt. Der Test ist
`get_files` auf dem PR: kommt `[]` zurück, ändert er nichts. Ein grüner Check
sagt dazu nichts — die CI prüft den Head, nicht die Differenz zur Basis.

Am 21.8.2026 liefen zwei Sessions dieselbe Aufgabe über 45 Repos, auf den
Branches `claude/codex-review-audit-templates-9sn6mx` und
`claude/codex-review-audit-7ioh56`. Wo die eine zuerst nach `main` kam, wurde
`main` in den Branch der anderen gemergt und der add/add-Konflikt zugunsten
von `main` aufgelöst. Übrig blieben 14 PRs, die durch sämtliche Gates grün
liefen und nichts enthielten; sie wurden gemergt und hinterliessen leere
Merge-Commits. Mit den zwei Folge-PRs, die aus demselben Grund gegenstandslos
waren, waren 16 der 59 PRs jenes Tages reine Reibung.

Dieselbe Klasse wie der handgeschriebene Stub, der denselben Feldnamen annahm
wie der Code: Nichts ist rot, weil nichts geprüft wird, worauf es ankommt.

## Teil 2 — Dieses Repo

**ruff: eine Quelle.** Der Pin `0.16.1` steht in `pyproject.toml` — und
**nicht** mehr als eigener Install-Schritt in der CI.

Im `test`-Job lief der entfernte CI-Schritt nach dem Install der
Abhängigkeiten und überschrieb sie. Eine Abweichung im Pin konnte deshalb in
der CI gar nicht auffallen, sondern nur lokal — wo niemand sie erwartet. Ein
manuelles Nachinstallieren von ruff vor den Gates ist damit nicht mehr nötig
und wäre schädlich: Es würde eine spätere Anhebung hier stillschweigend
überstimmen.

Im `lint`-Job lag der Fall anders: Dort war der ruff-Pin die **einzige**
Installation. An seiner Stelle steht jetzt `pip install -e ".[dev]"`, und
dieser Schritt ist nicht redundant — ohne ihn hat der Job überhaupt kein ruff
(`ruff: command not found`). Er sieht nur so aus wie der Install im `test`-Job.

**Gates, wörtlich aus der CI:**

```bash
python scripts/check_ruff_pin.py
python -m ruff check src/ tests/ scripts/
python -m ruff format --check src/ tests/ scripts/
python -m py_compile src/news_monitor_mcp/server.py
python -c "from news_monitor_mcp.server import mcp; print('Import OK')"
PYTHONPATH=src pytest tests/ -m "not live" -v
python scripts/check_version_sync.py
```

Dazu der Job `docker`: Image bauen, dann `--help` aus dem Image und der
Nachweis, dass der Container ohne `MCP_BEARER_TOKEN` mit Exit-Code 2 abbricht.
Test-Matrix: Python 3.11 / 3.12 / 3.13 — aber nur für den Job `test`. Die zwei
ruff-Gates laufen zusätzlich im Job `lint`, und der hat keine Matrix: er läuft
auf 3.11. Ein grünes 3.12/3.13 sagt über ihn nichts aus. Ein `fail-fast: false`
steht nicht da, eine rote 3.11 bricht 3.12 und 3.13 ab.

Die Gate-Zeilen rufen `python -m ruff` statt `ruff` — das ist Absicht und
gehört beim Nachfahren übernommen: ein `ruff` früher im `PATH` wäre eine andere
Version und meldete Abweichungen, die niemand verursacht hat.

**Live-Tests:** `.github/workflows/live-tests.yml` fährt die fünf
`@pytest.mark.live`-Tests täglich um 06:17 UTC (plus `workflow_dispatch`) —
DRIFT-005 ist damit geschlossen. Die reguläre CI schliesst sie weiterhin per
`-m "not live"` aus; das ist richtig so, sie messen die Quelle, nicht den Diff.

Zwei der fünf prüfen den Routenbestand und brauchen keinen Schlüssel, drei
überspringen sich ohne `WORLD_NEWS_API_KEY`. Ist das Secret im Repo nicht
gesetzt, läuft nur die halbe Messung — `scripts/check_live_run.py` macht das
im Job-Summary sichtbar und meldet rot, wenn ein Lauf **gar nichts** gemessen
hat (übersprungen ≠ geprüft, und pytest gibt für beides Exit-Code 0 zurück).

Stand 14.8.2026 ist das Secret **nicht gesetzt**: gemessen 2 ausgeführt, 3
übersprungen, Job grün. Der tägliche Lauf prüft damit nur den Routenbestand,
nicht die Form der Antwort — ein Schemawechsel bei der Quelle fällt so nicht
auf, also genau der Fehler, gegen den die Live-Tests existieren.

Den Meldeweg bei Fehlschlag kann `workflow_dispatch` nicht prüfen: der Schritt
hängt an `failure() && github.event_name == 'schedule'` und wird bei jedem
manuellen Lauf übersprungen. Wer ihn testen will, provoziert einen roten Lauf
auf einem Wegwerf-Branch — beide Zweige, denn `create` und `comment` fallen
getrennt (`tests/test_meldeweg.py` hält sie gefahren).
