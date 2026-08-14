"""Dass kein Test den HTTP-Client seines Vorgaengers erbt.

Der Live-Lauf vom 2026-08-14 meldete in `test_live_top_news_schweiz`:

    RuntimeError: Event loop is closed

Nicht die Quelle: Dieselbe Anfrage von Hand quittierte `/top-news` im selben
Lauf mit HTTP 200. Ursache war `api_client._client`, ein modulweiter
`AsyncClient`. Im Betrieb ist der richtig — ein Server, eine Event-Loop, ein
Lifespan, der ihn schliesst. Unter pytest gibt `asyncio_mode = "auto"` jedem
Test eine eigene Loop; der Client des vorigen Tests haengt aber an der alten
und stirbt beim Schliessen seiner Verbindung.

Sichtbar wurde das erst, als zum ersten Mal mehrere schluesselpflichtige Tests
wirklich nacheinander liefen. Solange sie sich mangels Schluessel uebersprangen,
teilten sich nie zwei Tests einen Client.

Das Tueckische daran: Der Fehler trifft nicht den Test, der ihn verursacht,
sondern den naechsten — und verdeckt, was dieser ueber die Quelle ausgesagt
haette. Die autouse-Fixture in `conftest.py` raeumt den Slot deshalb vor und
nach jedem Test.

Die beiden Tests hier haengen bewusst voneinander ab und muessen in dieser
Reihenfolge stehen: Der erste hinterlaesst einen Client, der zweite belegt,
dass davon nichts uebrig ist.
"""

from news_monitor_mcp import api_client


async def test_a_hinterlaesst_einen_client():
    """Legt einen Client an — Vorbereitung fuer den Test darunter."""
    client = api_client._get_client()
    assert api_client.get_current_client() is client
    assert client.is_closed is False


async def test_b_erbt_nichts_vom_vorigen_test():
    """Ohne die Fixture stuende hier der Client aus dem Test darueber.

    Er haengt dann an einer geschlossenen Event-Loop, und der erste Request
    dieses Tests scheitert mit `RuntimeError: Event loop is closed` — an einem
    Fehler also, den dieser Test gar nicht verursacht hat.
    """
    assert api_client.get_current_client() is None, (
        "Der Client des vorigen Tests lebt noch. Dann haengt er an dessen "
        "Event-Loop, und dieser Test misst nicht die Quelle, sondern den "
        "Zustand seines Vorgaengers."
    )
