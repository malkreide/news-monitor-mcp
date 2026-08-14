"""Gegenprobe zu `tests/kontingent.py` — laeuft offline, in jeder CI.

Diese Helfer verwandeln einen roten Test in einen uebersprungenen. Das ist
genau die Sorte Mechanik, die man nicht ungeprueft lassen darf: Greift sie zu
breit, verschluckt sie echte Defekte und der Lauf sieht gruen aus, obwohl die
Quelle kaputt ist. Das waere schlimmer als der Zustand, den sie behebt.

Geprueft wird deshalb in beide Richtungen — was ueberspringen MUSS und, vor
allem, was ueberspringen DARF NICHT.
"""

import pytest

from tests.kontingent import (
    BUDGET_MELDUNGEN,
    ueberspringe_bei_budget_antwort,
    ueberspringe_bei_budget_status,
)


@pytest.mark.parametrize("code", [402, 429])
def test_budget_status_ueberspringt(code):
    """402 (Kontingent) und 429 (Rate Limit) sind Budget, kein Defekt."""
    with pytest.raises(pytest.skip.Exception, match="Budget der Quelle"):
        ueberspringe_bei_budget_status(code)


@pytest.mark.parametrize("code", [200, 400, 401, 403, 404, 500, 502])
def test_andere_status_ueberspringen_nicht(code):
    """Alles andere bleibt ein Fehlschlag — besonders 401 und 500.

    Ein ungueltiger Schluessel (401) ist ein Defekt der Konfiguration, den
    jemand beheben muss; ein 500 ist einer der Quelle. Wuerde die Mechanik
    hier greifen, verschwaende sie genau die Meldungen, wegen derer es die
    Live-Tests gibt.

    Der Skip wird ABGEFANGEN und in ein `fail` verwandelt. Ohne das waere
    dieser Test wertlos: Ein `pytest.skip()` im Testkoerper laesst den Test
    ueberspringen, nicht fehlschlagen — er koennte den Fall, den er belegen
    soll, gar nicht melden. Genau daran ist der erste Anlauf gescheitert.
    """
    try:
        ueberspringe_bei_budget_status(code)
    except pytest.skip.Exception as e:
        pytest.fail(f"HTTP {code} wurde als Budget behandelt und uebersprungen: {e}")


@pytest.mark.parametrize("meldung", BUDGET_MELDUNGEN)
def test_budget_antwort_ueberspringt(meldung):
    """Die Werkzeuge geben Text zurueck, keine Exception."""
    with pytest.raises(pytest.skip.Exception, match="Budget der Quelle"):
        ueberspringe_bei_budget_antwort(f"Fehler: {meldung}.")


@pytest.mark.parametrize(
    "antwort",
    [
        "Fehler: Ungültiger API-Key.",
        "API-Fehler: HTTP 400",
        "Fehler: Timeout.",
        "Fehler: Keine Verbindung zur WorldNewsAPI.",
        "Fehler: RuntimeError – Details siehe Server-Log",
        "## Suchergebnisse: Volksschule\n**3 von 42 Treffern**",
    ],
)
def test_andere_antworten_ueberspringen_nicht(antwort):
    """Kein anderer Fehlertext darf als Budget durchgehen.

    `API-Fehler: HTTP 400` steht hier mit Absicht: Genau diese Meldung war am
    14.8.2026 der echte Defekt (`sort=relevance`). Wuerde sie kuenftig
    uebersprungen, bliebe er unentdeckt.

    Wie oben wird der Skip abgefangen — sonst uebersprange sich dieser Test
    selbst, statt zu melden.
    """
    try:
        ueberspringe_bei_budget_antwort(antwort)
    except pytest.skip.Exception as e:
        pytest.fail(f"«{antwort[:60]}» wurde als Budget behandelt und uebersprungen: {e}")


def test_meldungen_stimmen_mit_dem_server_ueberein():
    """Die Texte hier muessen die sein, die `errors.py` wirklich erzeugt.

    Eine Kopie, die auseinanderlaeuft, greift im Ernstfall nicht mehr — und
    zwar lautlos: Der Test bliebe gruen, der Lauf wuerde wieder faelschlich
    rot melden.
    """
    from pathlib import Path

    quelle = (Path(__file__).resolve().parents[1] / "src" / "news_monitor_mcp" / "errors.py").read_text(
        encoding="utf-8"
    )
    for meldung in BUDGET_MELDUNGEN:
        assert meldung in quelle, (
            f"`{meldung}` kommt in errors.py nicht mehr vor. Entweder wurde die "
            "Meldung umbenannt — dann greift das Ueberspringen nicht mehr — oder "
            "der Fall existiert nicht mehr."
        )
