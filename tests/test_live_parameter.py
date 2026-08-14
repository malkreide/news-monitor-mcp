"""Wirken die Filter der Quelle noch — oder laufen sie still ins Leere?

WOGEGEN DAS SCHUETZT. Am 2026-08-14 gemessen: Die Quelle verwirft unbekannte
Query-Parameter **still** und antwortet mit HTTP 200. Ein Tippfehler in einem
Parameternamen, oder eine Umbenennung auf ihrer Seite, macht einen Filter
damit wirkungslos, ohne dass irgendetwas rot wird — die Antwort ist dann
vollstaendig, plausibel, formatiert und ungefiltert. In
`global-education-mcp` desselben Portfolios waren genau so zwei Filter tot.

Die uebrigen Live-Tests fangen das nicht: Sie pruefen, dass Artikel
zurueckkommen. Ein ignorierter Filter liefert Artikel.

ZWEI ZUSICHERUNGEN, GETRENNT GEHALTEN:

1. Die Kontrolle — ein erfundener Parameter aendert nichts. Faellt sie, hat
   die Quelle ihr Verhalten geaendert (etwa: unbekannte Parameter werden jetzt
   abgewiesen). Das ist keine Katastrophe, aber es heisst, dass Test 2 neu
   eingeordnet gehoert.
2. Die Wirkung — zwei verschiedene `categories` liefern Verschiedenes. Faellt
   sie, filtert die Quelle nicht mehr nach dem, was der Server ihr schickt.

BEIDE brauchen vorher den Nachweis, dass ueberhaupt etwas gemessen wurde.
Beim ersten Anlauf dieser Messung lag das Zeitfenster ausserhalb dessen, was
der Free Tier liefert: Beide Seiten kamen leer, und «leer == leer» las sich
als bestandene Kontrolle. Ein Vergleich zweier Nicht-Antworten sieht aus wie
ein Ergebnis.

KOSTEN: vier Anfragen pro Lauf (zwei je Test). Bei 50 Punkten/Tag im Free
Tier ist das vertretbar; die drei Datentests kosten drei weitere.
"""

import os
from datetime import date, timedelta

import pytest

from news_monitor_mcp.api_client import BASE_URL, articles_of
from tests.kontingent import ueberspringe_bei_budget_status

_ohne_key = pytest.mark.skipif(
    not os.environ.get("WORLD_NEWS_API_KEY"),
    reason="WORLD_NEWS_API_KEY nicht gesetzt — ohne Schluessel gibt es keine Antwort, die etwas belegt.",
)


def _fenster() -> dict[str, str]:
    """Ein abgeschlossenes Zeitfenster in der juengeren Vergangenheit.

    Das Ende liegt zwei Tage zurueck: Faende ein neu erschienener Artikel
    zwischen die beiden Anfragen eines Vergleichs, waeren sie schon deshalb
    verschieden — und «der Parameter wirkt» waere von «es ist Zeit vergangen»
    nicht zu unterscheiden.

    Der Anfang liegt 22 Tage zurueck, nicht mehr: Der Free Tier reicht nur
    etwa einen Monat zurueck, aelteres kommt leer zurueck.
    """
    bis = date.today() - timedelta(days=2)
    von = bis - timedelta(days=20)
    return {
        "earliest-publish-date": f"{von} 00:00:00",
        "latest-publish-date": f"{bis} 23:59:59",
    }


async def _suche(**zusatz) -> tuple[object, list]:
    """Eine Suche gegen die echte Quelle. Gibt (available, IDs) zurueck."""
    import httpx

    p = {"language": "de", "number": 5, **_fenster(), **zusatz}
    async with httpx.AsyncClient(timeout=60.0) as c:
        r = await c.get(
            f"{BASE_URL}/search-news",
            params=p,
            headers={"x-api-key": os.environ["WORLD_NEWS_API_KEY"]},
        )
    # Vor `raise_for_status`: Ein aufgebrauchtes Kontingent ist kein Defekt der
    # Quelle und darf diesen Lauf nicht rot melden — er hat dann schlicht nichts
    # gemessen. Alle anderen Statuscodes bleiben ein Fehlschlag.
    ueberspringe_bei_budget_status(r.status_code)
    r.raise_for_status()
    daten = r.json()
    # `articles_of` statt `.get("news", [])`: Ein fehlender Umschlag ist keine
    # Aussage ueber die Artikel, sondern ueber die Antwort.
    artikel = articles_of(daten, "/search-news")
    return daten.get("available"), [a.get("id") for a in artikel]


def _belastbar(label: str, ids: list) -> None:
    """Ohne Treffer belegt der Vergleich darunter nichts."""
    assert ids, (
        f"{label} liefert keine Artikel. Ein Vergleich mit einer leeren Antwort "
        "kann nicht fehlschlagen und belegt darum nichts. Erst pruefen, ob das "
        "Zeitfenster noch im Bereich des Tarifs liegt und die Kategorie noch existiert."
    )


@pytest.mark.live
@_ohne_key
async def test_live_kontrolle_unbekannter_parameter_aendert_nichts():
    """Zuerst die Kontrolle — ohne sie sagt der Test darunter nichts.

    Stand 2026-08-14 verwirft die Quelle unbekannte Parameter still. Nur
    deshalb heisst «zwei Antworten sind verschieden» auch «der Parameter, in
    dem sie sich unterscheiden, hat gewirkt».
    """
    a_avail, a_ids = await _suche(categories="politics")
    _belastbar("Die Kontrollabfrage", a_ids)
    b_avail, b_ids = await _suche(categories="politics", gibtsnichtxyzquatsch="egal")

    assert (a_avail, a_ids) == (b_avail, b_ids), (
        "Ein erfundener Parameter aendert das Ergebnis. Die Quelle verwirft "
        "unbekannte Parameter also nicht mehr still, sondern wertet sie aus oder "
        "weist sie ab. Das ist an sich keine schlechte Nachricht — aber der Test "
        "darunter misst dann etwas anderes als bisher und gehoert neu eingeordnet.\n"
        f"  ohne: available={a_avail} ids={a_ids}\n"
        f"  mit:  available={b_avail} ids={b_ids}"
    )


@pytest.mark.live
@_ohne_key
async def test_live_categories_filtert_wirklich():
    """Zwei verschiedene Kategorien muessen Verschiedenes liefern.

    `news_trend_radar` steht und faellt damit. Wird `categories` von der Quelle
    ignoriert, liefert das Werkzeug weiterhin Artikel — nur eben nicht die
    angeforderte Kategorie, sondern irgendwelche. Genau diese Sorte Defekt
    meldet sich nie von selbst.
    """
    pol_avail, pol_ids = await _suche(categories="politics")
    _belastbar("Die Abfrage `categories=politics`", pol_ids)
    spo_avail, spo_ids = await _suche(categories="sports")
    _belastbar("Die Abfrage `categories=sports`", spo_ids)

    assert (pol_avail, pol_ids) != (spo_avail, spo_ids), (
        "`categories=politics` und `categories=sports` liefern dasselbe. Der "
        "Filter wirkt nicht mehr — `news_trend_radar` gibt dann beliebige "
        "Artikel als Kategorie-Treffer aus.\n"
        f"  politics: available={pol_avail} ids={pol_ids}\n"
        f"  sports:   available={spo_avail} ids={spo_ids}"
    )


# ---------------------------------------------------------------------------
# Gegenprobe zur Belastbarkeitspruefung — laeuft offline, in jeder CI.
#
# Sie ist der Teil, der beim ersten Anlauf gefehlt hat: Ohne sie waere
# `_belastbar` selbst ungeprueft, und ein Vergleich zweier leerer Antworten
# koennte wieder als bestandene Messung durchgehen.
# ---------------------------------------------------------------------------


def test_belastbarkeitspruefung_faellt_bei_leerer_antwort():
    """Keine Treffer heisst: nicht gemessen, nicht «kein Unterschied»."""
    with pytest.raises(AssertionError, match="belegt darum nichts"):
        _belastbar("Testabfrage", [])


def test_belastbarkeitspruefung_laesst_treffer_durch():
    """Mit Treffern darf sie nicht im Weg stehen."""
    _belastbar("Testabfrage", [1, 2, 3])


def test_fenster_liegt_im_bereich_des_tarifs():
    """Das Fenster muss abgeschlossen und jung genug sein.

    Beide Grenzen sind der Grund, warum der erste Messversuch nichts belegte:
    ein zu altes Fenster liefert im Free Tier nichts, ein bis heute offenes
    laesst neue Artikel zwischen die beiden Anfragen fallen.
    """
    f = _fenster()
    von = date.fromisoformat(f["earliest-publish-date"][:10])
    bis = date.fromisoformat(f["latest-publish-date"][:10])
    heute = date.today()

    assert (heute - bis).days >= 2, "Das Fenster reicht zu nah an heute heran."
    assert (heute - von).days <= 28, "Das Fenster reicht weiter zurueck, als der Free Tier liefert."
    assert von < bis
