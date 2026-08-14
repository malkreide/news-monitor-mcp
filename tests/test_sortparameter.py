"""Was `news_search` als `sort` an die Quelle schickt.

GEMESSEN AM 2026-08-14 gegen `api.worldnewsapi.com/search-news`, sonst
identische Parameter:

    sort=relevance          -> HTTP 400
        {"status":"failure","code":400,
         "message":"Sort must be either 'publish-time' or empty."}
    sort=publish-time       -> HTTP 200
    sort=relevance + Datum  -> HTTP 400   (der Datumsbereich ist nicht die Ursache)
    ohne sort               -> HTTP 200

`SortOrder.RELEVANCE` war der Default von `SearchNewsInput.sort` — **jede**
Standardsuche lief also in einen 400. Gruen blieb trotzdem alles: Die
Unit-Tests mocken die Quelle und bekommen die Antwort, die sie selbst
hinterlegt haben. Aufgefallen ist es erst beim ersten Live-Lauf mit
Schluessel.

Deshalb pruefen die Tests hier nicht das Ergebnis, sondern **was rausgeht**.
Eine gemockte Antwort kann nicht widerlegen, dass die Anfrage falsch war; die
Parameter der Anfrage koennen es.

Leer ist bei dieser Quelle die Relevanz-Sortierung — `RELEVANCE` wird deshalb
weggelassen und nicht uebersetzt.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news_monitor_mcp.formatting import SortOrder
from news_monitor_mcp.models import SearchNewsInput
from news_monitor_mcp.tools.monitoring import news_search


async def _gesendete_params(params: SearchNewsInput) -> dict:
    """Ruft news_search auf und gibt zurueck, was an die Quelle gegangen waere."""
    antwort = MagicMock()
    antwort.json.return_value = {"news": [], "available": 0}
    antwort.raise_for_status = MagicMock()

    with patch.dict("os.environ", {"WORLD_NEWS_API_KEY": "test-key-123"}):
        with patch("news_monitor_mcp.tools.monitoring._get_client") as fabrik:
            client = AsyncMock()
            client.get = AsyncMock(return_value=antwort)
            fabrik.return_value = client
            await news_search(params)

    assert client.get.await_count == 1, "Erwartet genau eine Anfrage an die Quelle."
    return client.get.await_args.kwargs["params"]


async def test_standardsuche_schickt_kein_sort():
    """Der Default darf den Parameter nicht setzen — sonst HTTP 400.

    `use_cache=False`, sonst kann ein Treffer aus einem frueheren Test die
    Anfrage verhindern und der Test belegte nichts.
    """
    p = await _gesendete_params(SearchNewsInput(query="Volksschule", use_cache=False))
    assert "sort" not in p, f"`sort` wurde mitgeschickt: {p.get('sort')!r} — die Quelle quittiert das mit 400."


async def test_publish_time_wird_geschickt():
    """Die eine Sortierung, die die Quelle kennt, muss ankommen.

    Ohne diesen Test waere «schick nie ein sort» die einfachste Loesung — und
    damit waere die Sortierung, die es gibt, still verloren gegangen.
    """
    p = await _gesendete_params(SearchNewsInput(query="Volksschule", sort=SortOrder.PUBLISH_TIME, use_cache=False))
    assert p.get("sort") == "publish-time", p


@pytest.mark.parametrize("sortierung", list(SortOrder))
async def test_kein_sortwert_erreicht_die_quelle_als_relevance(sortierung):
    """Fuer *jeden* Enum-Wert: `relevance` darf nie rausgehen.

    Kaeme spaeter ein dritter Wert dazu, faengt dieser Test ihn mit ab, solange
    er nicht versehentlich als `relevance` uebersetzt wird.
    """
    p = await _gesendete_params(SearchNewsInput(query="Volksschule", sort=sortierung, use_cache=False))
    assert p.get("sort") != "relevance", (
        f"{sortierung} schickt `sort=relevance` — die Quelle antwortet darauf mit "
        "«Sort must be either 'publish-time' or empty.»"
    )
