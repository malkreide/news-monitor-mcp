# SessionStart-Hook: Klon-Aktualität

`session-start.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter `origin/<Standard-Branch>` liegt. Registriert ist er
in [`../settings.json`](../settings.json) für die Quellen `startup` und
`resume` — `clear` und `compact` ändern am Klon nichts.

## Warum

Ein veralteter Klon hat am 3.8.2026 **zweimal** eine rote CI erzeugt, deren
Ursache nicht im Diff stand: Es fehlten jeweils genau die Commits, die das
Gate einführten, an dem der Branch scheiterte. Der Diff war in Ordnung —
gesucht wurde trotzdem dort, weil nichts auf den Klon zeigte.

Die Prüfung kostet eine Sekunde und ersetzt eine Fehlersuche in den falschen
Dateien.

## Was er zusichert

**1. Er hält die Session nie an.** Kein Netz, kein Remote, detached HEAD,
flatterndes DNS, kein `git` — jeder dieser Fälle geht still durch: Exit 0,
keine Ausgabe. Ein Hook, der bei Netzproblemen die Arbeit anhält, wird nach
dem zweiten Mal abgeschaltet und schützt danach gar nichts.

Getragen wird das **nicht** von einer Liste abgefangener Fehlerfälle. Die
Liste wäre nie vollständig — und beim Nachmessen erwies sich jeder einzelne
Wachposten (`rev-parse --is-inside-work-tree`, `rev-parse --verify HEAD`,
`remote get-url origin`) als entbehrlich, weil ihn ein anderer verdeckte:
Entfernte man ihn, blieben alle Tests grün. Sie stehen deshalb nicht mehr im
Skript. Die Zusicherung ruht auf zwei Eigenschaften, die für *alle* Fälle
gelten:

* Kein `set -e`, und jeder Pfad endet ausdrücklich mit `exit 0`. `set -e`
  machte die Zusicherung davon abhängig, dass jeder künftige `git`-Aufruf sein
  `|| exit 0` mitbringt; vergisst einer es, bricht der Hook ab statt still
  durchzugehen — und das fällt niemandem auf, weil der Fehlerfall selten ist.
* Gemeldet wird nur, was als Zahl > 0 aus dem Repo kommt. Jeder andere Wert —
  leer, Fehlertext, `0` — bedeutet Schweigen. Damit muss kein Fehlerfall
  einzeln bekannt sein, um harmlos zu sein.

**2. Kurzes Zeitlimit.** Jeder der beiden Netzaufrufe (`ls-remote`, `fetch`)
läuft unter `timeout` — voreingestellt 5 Sekunden, überschreibbar über
`CLAUDE_KLONCHECK_TIMEOUT`. `settings.json` setzt zusätzlich ein hartes
Limit von 20 Sekunden auf den ganzen Hook.

Gibt es weder `timeout` noch `gtimeout`, unterbleibt die Prüfung ganz. Ein
ungebremstes `git fetch` wäre das größere Übel: Ein hängender Sessionstart
wiegt schwerer als eine ausgefallene Warnung.

**3. Bei 0 schweigt er.** Ausgabe erfolgt nur, wenn tatsächlich Commits
fehlen. Eine Meldung, die immer kommt, wird nicht mehr gelesen.

**4. Der Standard-Branch wird ermittelt, nicht angenommen.** Über
`git ls-remote --symref origin HEAD`, mit dem lokal notierten `origin/HEAD`
als netzloser Rückfallebene. Drei Server im Portfolio (`openlex-mcp`,
`swiss-courts-mcp`, `swisstopo-mcp`) heißen ihren Standard-Branch `master`;
ein fest verdrahtetes `main` scheitert dort mit «couldn't find remote ref
main» — was leicht für ein Netzproblem gehalten wird. Genau diese Annahme hat
einen Branch schon einmal 15 Commits alt werden lassen.

Gezählt wird gegen `FETCH_HEAD`, nicht gegen `origin/<Branch>`: `FETCH_HEAD`
stammt aus genau dem Fetch, der eben erfolgreich war. Ein Remote-Tracking-Ref
könnte älter sein und meldete dann zu wenig Rückstand.

## Von Hand fahren

```bash
CLAUDE_PROJECT_DIR="$PWD" .claude/hooks/session-start.sh; echo "Exit: $?"
```

Auf einem aktuellen Klon ist die richtige Ausgabe: keine.

## Tests

`tests/test_kloncheck.py` fährt **dieses Skript**, nicht eine Kopie, gegen
synthetische Repos. Jede Zusicherung ist einzeln neutralisiert worden, und es
fällt genau der zugehörige Test:

| Neutralisiert | Fällt |
| --- | --- |
| `standard="main"` fest verdrahtet | `test_standard_branch_wird_ermittelt_nicht_angenommen` |
| Schweigen bei 0 entfernt | `test_schweigt_wenn_der_klon_aktuell_ist` |
| Zahlenprüfung der Ausgabe entfernt | `test_ungeborenes_head_still` |
| Einzahl/Mehrzahl fest auf «Commits» | `test_meldet_die_zahl_der_fehlenden_commits[1-…]` |
| `HEAD` durch `symbolic-ref HEAD` ersetzt | `test_detached_head_wird_gemessen_und_nicht_zum_fehler` |
| Zeitlimit entfernt | `test_haengendes_remote_laeuft_ins_zeitlimit` (läuft dann 120 s in den Deckel) |
| Hook aus `settings.json` ausgetragen | `test_hook_ist_registriert_und_ausfuehrbar` |

Der Fall «Remote antwortet nie» ist `ext::sleep 300` — ein Transport, der
schlicht schweigt. Das ist das flatternde DNS aus der Anforderung, nur
reproduzierbar. Ohne Zeitlimit im Hook läuft dieser Test in den
120-Sekunden-Deckel des Test-Subprozesses; von Hand gemessen: `rc=0` nach 4 s
mit Zeitlimit, `rc=124` nach 30 s abgeschnitten ohne.

Der Hook selbst hat keine Laufzeitabhängigkeit auf Python — die Tests nutzen
nur pytest als Rahmen.
