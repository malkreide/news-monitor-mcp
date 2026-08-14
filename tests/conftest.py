"""Gemeinsame Fixtures.

WARUM ES DIESE DATEI GIBT. `api_client._client` ist ein modulweiter
`httpx.AsyncClient`, im Betrieb genau richtig: Der Server laeuft in einer
Event-Loop, und der Lifespan schliesst den Client am Ende. Unter pytest gilt
das nicht — `asyncio_mode = "auto"` gibt jedem Test eine eigene Loop, der
Client aus dem vorigen Test haengt aber noch an der alten. Beim Schliessen
einer so geerbten Verbindung wirft asyncio `RuntimeError: Event loop is
closed`.

Aufgefallen ist das erst, als zum ersten Mal mehrere schluesselpflichtige
Live-Tests wirklich nacheinander liefen: Solange sie sich mangels Schluessel
uebersprangen, gab es nie zwei Tests, die sich einen Client teilten. Der
Fehler traf dann nicht den Test, der ihn verursacht hatte, sondern den
darauffolgenden — und verdeckte damit, was dieser Test ueber die Quelle
ausgesagt haette.

Die Fixture setzt den Slot vor und nach jedem Test zurueck. Damit misst jeder
Test die Quelle, nicht den Zustand seines Vorgaengers.
"""

import pytest

from news_monitor_mcp import api_client


@pytest.fixture(autouse=True)
async def _frischer_http_client():
    """Jeder Test bekommt einen Client in seiner eigenen Event-Loop."""
    await api_client.close_client()
    yield
    await api_client.close_client()
