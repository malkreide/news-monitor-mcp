"""`/top-news` muss «leer» von «anders» unterscheiden.

WAS AM 15.8.2026 PASSIERTE. Der Live-Test meldete nur die Ueberschrift:

    ## Top-Schlagzeilen: CH | DE | 2026-08-15

Zwei voellig verschiedene Ursachen kamen infrage, und `monitoring.py` gab
beiden dieselbe Ausgabe:

    a) Die Quelle fuehrt fuer CH/de gerade keine Cluster.
    b) Der Umschlag heisst nicht mehr `top_news`.

Aufgeloest hat es erst eine Messung von Hand — `{"top_news":[],...}`, also
Fall (a). Genau diese Unterscheidung soll das Werkzeug selbst treffen.

`/top-news` war die einzige der acht Abfragen, die den Umschlag noch roh las
(`data.get("top_news", [])`); die uebrigen sieben liefen laengst ueber
`articles_of`. Ein uebersehener Aufrufort reicht, damit der Fehler bleibt.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news_monitor_mcp.api_client import UpstreamShapeError, clusters_of
from news_monitor_mcp.models import TopNewsInput
from news_monitor_mcp.tools.monitoring import news_top_headlines

_EIN_CLUSTER = [{"news": [{"title": "Bundesrat entscheidet", "publish_date": "2026-08-15", "url": "https://x"}]}]


async def _antwort(payload: dict) -> str:
    """Ruft `news_top_headlines` mit einer vorgegebenen Quell-Antwort auf."""
    antwort = MagicMock()
    antwort.json.return_value = payload
    antwort.raise_for_status = MagicMock()
    with patch.dict("os.environ", {"WORLD_NEWS_API_KEY": "test-key-123"}):
        with patch("news_monitor_mcp.tools.monitoring._get_client") as fabrik:
            client = AsyncMock()
            client.get = AsyncMock(return_value=antwort)
            fabrik.return_value = client
            return await news_top_headlines(TopNewsInput(source_country="ch", language="de", use_cache=False))


# --------------------------------------------------------------------------
# Der Umschlag-Leser selbst
# --------------------------------------------------------------------------


def test_leere_liste_ist_eine_aussage_der_quelle():
    assert clusters_of({"top_news": [], "country": "ch"}, "/top-news") == []


def test_fehlendes_feld_ist_eine_aussage_ueber_die_antwort():
    with pytest.raises(UpstreamShapeError, match="top_news"):
        clusters_of({"topNews": [], "country": "ch"}, "/top-news")


def test_falscher_typ_faellt_auf():
    with pytest.raises(UpstreamShapeError, match="nicht eine Liste"):
        clusters_of({"top_news": {"a": 1}}, "/top-news")


def test_articles_of_bleibt_unveraendert():
    """Die Verallgemeinerung darf die sieben bestehenden Aufrufe nicht bewegen."""
    from news_monitor_mcp.api_client import articles_of

    assert articles_of({"news": []}, "/search-news") == []
    with pytest.raises(UpstreamShapeError, match="news"):
        articles_of({"artikel": []}, "/search-news")


# --------------------------------------------------------------------------
# Was beim Werkzeug herauskommt
# --------------------------------------------------------------------------


async def test_null_cluster_sagt_es_ausdruecklich():
    """Sonst bleibt nur die Ueberschrift — und die sagt nichts."""
    ergebnis = await _antwort({"top_news": [], "language": "de", "country": "ch"})
    assert "keine Top-Cluster" in ergebnis, ergebnis
    assert "Fehler" not in ergebnis, "Leer ist kein Fehler."


async def test_umbenannter_umschlag_wird_als_formfehler_gemeldet():
    """Der Fall, den das Werkzeug vorher nicht von «leer» unterscheiden konnte."""
    ergebnis = await _antwort({"topNews": [], "language": "de", "country": "ch"})
    assert "Unerwartete Antwortform" in ergebnis, ergebnis
    assert "keine Top-Cluster" not in ergebnis, (
        "Ein umbenannter Umschlag darf nicht als «die Quelle hat nichts» durchgehen — "
        "genau diese Verwechslung ist der Grund fuer diesen Test."
    )


async def test_cluster_werden_weiterhin_gerendert():
    """Die Leer-Behandlung darf den Normalfall nicht verschlucken."""
    ergebnis = await _antwort({"top_news": _EIN_CLUSTER, "language": "de", "country": "ch"})
    assert "###" in ergebnis and "Bundesrat entscheidet" in ergebnis, ergebnis
    assert "keine Top-Cluster" not in ergebnis


async def test_json_format_meldet_den_formfehler_ebenfalls():
    """Der JSON-Zweig liegt hinter derselben Pruefung — nicht daneben."""
    antwort = MagicMock()
    antwort.json.return_value = {"topNews": []}
    antwort.raise_for_status = MagicMock()
    with patch.dict("os.environ", {"WORLD_NEWS_API_KEY": "test-key-123"}):
        with patch("news_monitor_mcp.tools.monitoring._get_client") as fabrik:
            client = AsyncMock()
            client.get = AsyncMock(return_value=antwort)
            fabrik.return_value = client
            ergebnis = await news_top_headlines(
                TopNewsInput(source_country="ch", language="de", use_cache=False, response_format="json")
            )
    assert "Unerwartete Antwortform" in ergebnis, ergebnis
    with pytest.raises(json.JSONDecodeError):
        json.loads(ergebnis)
