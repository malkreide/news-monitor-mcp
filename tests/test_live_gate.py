"""Gegenprobe fuer `scripts/check_live_run.py`.

Der Waechter existiert, weil ein uebersprungener Lauf mit Exit-Code 0 endet.
Waere er selbst ungeprueft, haette das Problem nur die Ebene gewechselt: Statt
eines gruenen Live-Laufs ohne Messung gaebe es einen gruenen Waechter ohne
Wirkung. Jede der drei Zusicherungen wird darum einzeln belegt — und zwar so,
dass sie fallen kann.
"""

import os
import subprocess
import sys
from pathlib import Path

_SKRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_live_run.py"


def _bericht(pfad: Path, *, tests: int, skipped: int, failures: int = 0) -> Path:
    """Schreibt einen JUnit-Bericht in der Form, die pytest erzeugt."""
    pfad.write_text(
        '<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest" '
        f'tests="{tests}" skipped="{skipped}" failures="{failures}" errors="0">'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    return pfad


def _lauf(pfad: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_SKRIPT), str(pfad)],
        capture_output=True,
        text=True,
    )


def test_teilweise_uebersprungen_ist_gruen_aber_sichtbar(tmp_path):
    """Der Normalfall ohne Schluessel: zwei Routentests laufen, drei nicht.

    Gruen — «rot» soll heissen, dass etwas nicht stimmt, nicht dass jemand
    keinen Schluessel hat. Aber nicht stumm: Wer die Zusammenfassung liest,
    muss sehen, dass nur der Routenbestand geprueft ist.
    """
    ergebnis = _lauf(_bericht(tmp_path / "r.xml", tests=5, skipped=3))
    assert ergebnis.returncode == 0, ergebnis.stdout
    assert "::warning::" in ergebnis.stdout
    assert "3 von 5" in ergebnis.stdout


def test_alles_uebersprungen_ist_rot(tmp_path):
    """Auch die Routenpruefung uebersprungen — dann fehlt nicht der Schluessel."""
    ergebnis = _lauf(_bericht(tmp_path / "r.xml", tests=5, skipped=5))
    assert ergebnis.returncode == 1
    assert "::error::" in ergebnis.stdout


def test_nichts_gesammelt_ist_rot(tmp_path):
    """Null gesammelte Faelle heisst: die Markierung `live` greift nicht mehr.

    Auf den Exit-Code allein darf dieser Test sich nicht stuetzen: Bei null
    gesammelten Faellen ist auch «nichts ausgefuehrt» wahr, der Zweig darueber
    faenge den Fall also mit ab. Der Test bliebe dann gruen, wenn man genau die
    Zusicherung entfernt, die er belegen soll. Gemessen wird deshalb die
    Unterscheidung — sie ist der ganze Zweck des eigenen Zweigs: «nicht
    gesammelt» ist ein anderer Defekt als «uebersprungen» und fuehrt zu einer
    anderen Suche.
    """
    ergebnis = _lauf(_bericht(tmp_path / "r.xml", tests=0, skipped=0))
    assert ergebnis.returncode == 1
    assert "Markierung `live`" in ergebnis.stdout, ergebnis.stdout


def test_fehlender_bericht_ist_rot(tmp_path):
    """Kein Bericht heisst: pytest kam nicht bis zum Schreiben."""
    ergebnis = _lauf(tmp_path / "gibtsnicht.xml")
    assert ergebnis.returncode == 1
    assert "::error::" in ergebnis.stdout


def test_ein_fehlgeschlagener_test_bleibt_sichtbar(tmp_path):
    """Der Waechter misst die Abdeckung, nicht das Ergebnis.

    Ein echter Fehlschlag wird vom pytest-Schritt rot gemeldet; der Waechter
    darf ihn weder verdecken noch doppelt zaehlen — er laeuft mit `always()`
    und muesste den Job sonst auch dann rot halten, wenn das schon geschehen
    ist. Die Zahl gehoert aber in die Zusammenfassung.
    """
    ergebnis = _lauf(_bericht(tmp_path / "r.xml", tests=5, skipped=0, failures=2))
    assert ergebnis.returncode == 0, ergebnis.stdout
    assert "fehlgeschlagen: **2**" in ergebnis.stdout


def test_uebersprungene_nennen_ihren_grund(tmp_path):
    """Die Zusammenfassung nennt den gemeldeten Grund, statt ihn zu raten.

    Vorher stand dort pauschal «ohne `WORLD_NEWS_API_KEY` ist nur der
    Routenbestand geprueft». Seit ein erschoepftes Kontingent ebenfalls
    ueberspringt (siehe `tests/kontingent.py`), waere das eine falsche
    Diagnose — und eine falsche Diagnose im Job-Summary ist schlechter als
    keine, weil ihr jemand glaubt und am falschen Ort sucht.
    """
    pfad = tmp_path / "r.xml"
    pfad.write_text(
        '<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest" '
        'tests="3" skipped="2" failures="0" errors="0">'
        '<testcase name="a"><skipped message="Budget der Quelle erreicht (HTTP 402)"/></testcase>'
        '<testcase name="b"><skipped message="WORLD_NEWS_API_KEY nicht gesetzt"/></testcase>'
        '<testcase name="c"/>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    ergebnis = _lauf(pfad)
    assert ergebnis.returncode == 0, ergebnis.stdout
    assert "Budget der Quelle erreicht (HTTP 402)" in ergebnis.stdout, ergebnis.stdout
    assert "WORLD_NEWS_API_KEY nicht gesetzt" in ergebnis.stdout, ergebnis.stdout


def _lauf_mit_output(pfad: Path, tmp_path: Path) -> dict[str, str]:
    """Wie `_lauf`, aber mit gesetztem `$GITHUB_OUTPUT` — liefert die Schluessel zurueck."""
    ziel = tmp_path / "gh-output"
    ziel.write_text("", encoding="utf-8")
    umgebung = {**os.environ, "GITHUB_OUTPUT": str(ziel)}
    subprocess.run([sys.executable, str(_SKRIPT), str(pfad)], capture_output=True, text=True, env=umgebung)
    zeilen = [z for z in ziel.read_text(encoding="utf-8").splitlines() if z]
    return dict(z.split("=", 1) for z in zeilen)


def test_ein_fehlschlag_ist_ein_befund(tmp_path):
    """Gelaufen und gefallen: der einzige Fall, in dem eine Meldung ueber die Quelle gedeckt ist."""
    bericht = _bericht(tmp_path / "r.xml", tests=5, skipped=0, failures=1)
    assert _lauf_mit_output(bericht, tmp_path)["state"] == "finding"


def test_alles_uebersprungen_ist_kein_befund_sondern_unbekannt(tmp_path):
    """Der Lauf ist rot — aber nicht, weil die Quelle abgewichen waere.

    Bis zu diesem Commit las der Workflow jedes Rot als «die Quelle antwortet
    nicht mehr wie erwartet» und oeffnete ein Issue mit genau diesem Satz. Bei
    null ausgefuehrten Tests ist das eine Behauptung ueber eine Quelle, die
    niemand gefragt hat.
    """
    bericht = _bericht(tmp_path / "r.xml", tests=5, skipped=5)
    assert _lauf_mit_output(bericht, tmp_path)["state"] == "unknown"


def test_null_eingesammelt_ist_unbekannt(tmp_path):
    bericht = _bericht(tmp_path / "r.xml", tests=0, skipped=0)
    assert _lauf_mit_output(bericht, tmp_path)["state"] == "unknown"


def test_fehlender_bericht_ist_unbekannt(tmp_path):
    assert _lauf_mit_output(tmp_path / "gibtsnicht.xml", tmp_path)["state"] == "unknown"


def test_gruener_lauf_ist_clear(tmp_path):
    """Teilweise uebersprungen bleibt gruen — der dokumentierte Zustand ohne Schluessel."""
    bericht = _bericht(tmp_path / "r.xml", tests=5, skipped=3)
    assert _lauf_mit_output(bericht, tmp_path)["state"] == "clear"


def test_ein_mehrzeiliger_grund_schiebt_kein_zweites_state_nach(tmp_path):
    """`key=value` endet an der ersten neuen Zeile — was danach steht, ist ein eigenes Output."""
    pfad = tmp_path / "r\nstate=clear.xml"
    werte = _lauf_mit_output(pfad, tmp_path)
    assert werte["state"] == "unknown"
