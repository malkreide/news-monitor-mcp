"""Tests für den News Monitor MCP Server."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news_monitor_mcp.server import (
    GeoNewsInput,
    MediaBriefingInput,
    ResponseFormat,
    SearchNewsInput,
    SearchSourcesInput,
    SentimentMonitorInput,
    SortOrder,
    TopNewsInput,
    TrendRadarInput,
    _format_article,
    _no_key_message,
    _sentiment_label,
    news_geo_search,
    news_media_briefing,
    news_search,
    news_search_sources,
    news_sentiment_monitor,
    news_top_headlines,
    news_trend_radar,
)


# ---------------------------------------------------------------------------
# Hilfsfunktionen Tests
# ---------------------------------------------------------------------------


def test_sentiment_label_positiv():
    assert _sentiment_label(0.8) == "positiv"


def test_sentiment_label_negativ():
    assert _sentiment_label(-0.5) == "negativ"


def test_sentiment_label_neutral():
    assert _sentiment_label(0.0) == "neutral"
    assert _sentiment_label(0.1) == "neutral"


def test_sentiment_label_none():
    assert _sentiment_label(None) == "n/a"


def test_no_key_message():
    msg = _no_key_message("news_search")
    assert "WORLD_NEWS_API_KEY" in msg
    assert "news_search" in msg


def test_format_article_basic():
    article = {
        "id": 123,
        "title": "Test-Artikel",
        "summary": "Kurzzusammenfassung",
        "url": "https://example.com/artikel",
        "publish_date": "2025-01-15 10:00:00",
        "authors": ["Max Muster"],
        "category": "politics",
        "language": "de",
        "source_country": "ch",
        "sentiment": -0.3,
    }
    result = _format_article(article)
    assert result["titel"] == "Test-Artikel"
    assert result["quellland"] == "ch"
    assert result["sentiment"] == -0.3
    assert "volltext" not in result


def test_format_article_with_text():
    article = {
        "id": 456,
        "title": "Artikel mit Text",
        "text": "Langer Volltext des Artikels...",
        "summary": "",
        "url": "https://example.com",
        "publish_date": "2025-01-15 10:00:00",
        "authors": [],
        "category": "technology",
        "language": "en",
        "source_country": "us",
        "sentiment": 0.5,
    }
    result = _format_article(article, include_text=True)
    assert result["volltext"] == "Langer Volltext des Artikels..."


# ---------------------------------------------------------------------------
# Pydantic-Modell Tests
# ---------------------------------------------------------------------------


def test_search_news_input_valid():
    params = SearchNewsInput(query="Schulamt Zürich", language="de", source_country="ch")
    assert params.query == "Schulamt Zürich"
    assert params.language == "de"
    assert params.number == 10


def test_search_news_input_invalid_date():
    with pytest.raises(Exception):
        SearchNewsInput(query="test", earliest_date="15.01.2025")  # falsches Format


def test_sentiment_monitor_invalid_language():
    with pytest.raises(Exception):
        SentimentMonitorInput(entity="Test", language="fr")  # nur de/en erlaubt


def test_sentiment_monitor_valid():
    params = SentimentMonitorInput(entity="KI Bildung", language="de", days_back=14)
    assert params.entity == "KI Bildung"
    assert params.days_back == 14


def test_media_briefing_max_topics():
    with pytest.raises(Exception):
        MediaBriefingInput(
            topics=["t1", "t2", "t3", "t4", "t5", "t6"],  # max 5
            language="de",
        )


def test_top_news_defaults():
    params = TopNewsInput()
    assert params.source_country == "ch"
    assert params.language == "de"


# ---------------------------------------------------------------------------
# API-Key-Prüfung Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_news_search_no_api_key():
    """Gibt saubere Fehlermeldung ohne API-Key."""
    with patch.dict("os.environ", {}, clear=True):
        # Entferne Key falls vorhanden
        import os

        os.environ.pop("WORLD_NEWS_API_KEY", None)
        params = SearchNewsInput(query="Zürich")
        result = await news_search(params)
        assert "WORLD_NEWS_API_KEY" in result


@pytest.mark.asyncio
async def test_top_headlines_no_api_key():
    import os

    os.environ.pop("WORLD_NEWS_API_KEY", None)
    params = TopNewsInput()
    result = await news_top_headlines(params)
    assert "WORLD_NEWS_API_KEY" in result


@pytest.mark.asyncio
async def test_sentiment_monitor_no_api_key():
    import os

    os.environ.pop("WORLD_NEWS_API_KEY", None)
    params = SentimentMonitorInput(entity="Schulamt")
    result = await news_sentiment_monitor(params)
    assert "WORLD_NEWS_API_KEY" in result


# ---------------------------------------------------------------------------
# Mock-Tests für API-Calls
# ---------------------------------------------------------------------------

MOCK_ARTICLES = [
    {
        "id": 1001,
        "title": "Neue KI-Strategie für Zürcher Schulen",
        "text": "Die Stadt Zürich lanciert eine umfassende KI-Strategie für ihre Volksschulen.",
        "summary": "Zürich investiert in KI-gestützten Unterricht.",
        "url": "https://nzz.ch/artikel/ki-schulen",
        "image": "https://example.com/bild.jpg",
        "video": None,
        "publish_date": "2025-03-15 09:00:00",
        "authors": ["Anna Müller"],
        "category": "education",
        "language": "de",
        "source_country": "ch",
        "sentiment": 0.6,
    },
    {
        "id": 1002,
        "title": "Kritik an digitalem Unterricht",
        "text": "Lehrkräfte äussern Bedenken über übermässigen Bildschirmkonsum.",
        "summary": "Bildungsexperten warnen vor Risiken der Digitalisierung.",
        "url": "https://tagesanzeiger.ch/kritik-digital",
        "image": None,
        "video": None,
        "publish_date": "2025-03-14 14:30:00",
        "authors": [],
        "category": "education",
        "language": "de",
        "source_country": "ch",
        "sentiment": -0.4,
    },
]


@pytest.mark.asyncio
async def test_news_search_mock():
    """Testet news_search mit gemockter API-Antwort."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"news": MOCK_ARTICLES, "available": 42}
    mock_response.raise_for_status = MagicMock()

    with patch.dict("os.environ", {"WORLD_NEWS_API_KEY": "test-key-123"}):
        with patch(
            "news_monitor_mcp.server._get_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            params = SearchNewsInput(
                query="KI Bildung Zürich",
                language="de",
                response_format=ResponseFormat.MARKDOWN,
            )
            result = await news_search(params)

    assert "KI Bildung Zürich" in result
    assert "42" in result or "2" in result
    assert "Neue KI-Strategie" in result


@pytest.mark.asyncio
async def test_news_search_json_format():
    """Testet JSON-Ausgabeformat."""
    import json

    mock_response = MagicMock()
    mock_response.json.return_value = {"news": MOCK_ARTICLES, "available": 2}
    mock_response.raise_for_status = MagicMock()

    with patch.dict("os.environ", {"WORLD_NEWS_API_KEY": "test-key-123"}):
        with patch("news_monitor_mcp.server._get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            params = SearchNewsInput(query="test", response_format=ResponseFormat.JSON)
            result = await news_search(params)

    data = json.loads(result)
    assert "artikel" in data
    assert len(data["artikel"]) == 2
    assert data["artikel"][0]["titel"] == "Neue KI-Strategie für Zürcher Schulen"


@pytest.mark.asyncio
async def test_sentiment_monitor_mock():
    """Testet Sentiment-Monitoring mit gemockter Antwort."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"news": MOCK_ARTICLES, "available": 5}
    mock_response.raise_for_status = MagicMock()

    with patch.dict("os.environ", {"WORLD_NEWS_API_KEY": "test-key-123"}):
        with patch("news_monitor_mcp.server._get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            params = SentimentMonitorInput(
                entity="Schulamt Zürich",
                language="de",
                days_back=30,
            )
            result = await news_sentiment_monitor(params)

    assert "Schulamt Zürich" in result
    assert "Sentiment" in result


@pytest.mark.asyncio
async def test_trend_radar_mock():
    """Testet Trend-Radar."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"news": MOCK_ARTICLES, "available": 8}
    mock_response.raise_for_status = MagicMock()

    with patch.dict("os.environ", {"WORLD_NEWS_API_KEY": "test-key-123"}):
        with patch("news_monitor_mcp.server._get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            params = TrendRadarInput(
                category="technology",
                source_country="ch",
                language="de",
            )
            result = await news_trend_radar(params)

    assert "technology" in result
    assert "ch" in result


# ---------------------------------------------------------------------------
# Live-Tests (nur mit echtem API-Key)
# ---------------------------------------------------------------------------


@pytest.mark.live
async def test_live_search_schweizer_news():
    """Sucht echte Schweizer News (Live-Test)."""
    params = SearchNewsInput(
        query="Volksschule",
        language="de",
        source_country="ch",
        number=3,
    )
    result = await news_search(params)
    assert "Volksschule" in result or "Ergebnisse" in result


@pytest.mark.live
async def test_live_top_news_schweiz():
    """Ruft echte Top-News der Schweiz ab (Live-Test)."""
    params = TopNewsInput(source_country="ch", language="de", number=5)
    result = await news_top_headlines(params)
    assert "Top-Schlagzeilen" in result


@pytest.mark.live
async def test_live_sentiment_ki_bildung():
    """Analysiert Sentiment zu 'KI Bildung' (Live-Test)."""
    params = SentimentMonitorInput(
        entity="KI Bildung Schweiz",
        language="de",
        days_back=30,
        source_country="ch,de,at",
    )
    result = await news_sentiment_monitor(params)
    assert "Sentiment" in result


# ---------------------------------------------------------------------------
# Cache-Tests
# ---------------------------------------------------------------------------

def test_cache_miss_returns_none():
    from news_monitor_mcp.server import NewsCache
    cache = NewsCache()
    result = cache.get("search", {"q": "test"})
    assert result is None

def test_cache_set_and_get():
    from news_monitor_mcp.server import NewsCache
    cache = NewsCache()
    data = {"news": [{"title": "Test"}], "available": 1}
    cache.set("search", {"q": "test"}, data)
    result = cache.get("search", {"q": "test"})
    assert result is not None
    assert result["news"][0]["title"] == "Test"

def test_cache_different_params_different_keys():
    from news_monitor_mcp.server import NewsCache
    cache = NewsCache()
    cache.set("search", {"q": "test1"}, {"data": "A"})
    cache.set("search", {"q": "test2"}, {"data": "B"})
    assert cache.get("search", {"q": "test1"})["data"] == "A"
    assert cache.get("search", {"q": "test2"})["data"] == "B"

def test_cache_stats_initial():
    from news_monitor_mcp.server import NewsCache
    cache = NewsCache()
    stats = cache.stats()
    assert stats["gesamt_eintraege"] == 0
    assert stats["hits"] == 0
    assert stats["misses"] == 0

def test_cache_stats_after_hit():
    from news_monitor_mcp.server import NewsCache
    cache = NewsCache()
    cache.set("search", {"q": "test"}, {"data": "x"})
    cache.get("search", {"q": "test"})  # hit
    cache.get("search", {"q": "miss"})  # miss
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["api_calls_gespart"] == 1

def test_cache_clear_all():
    from news_monitor_mcp.server import NewsCache
    cache = NewsCache()
    cache.set("search", {"q": "a"}, {"d": 1})
    cache.set("headlines", {"sc": "ch"}, {"d": 2})
    count = cache.clear()
    assert count == 2
    assert cache.stats()["gesamt_eintraege"] == 0

def test_cache_clear_by_type():
    from news_monitor_mcp.server import NewsCache
    cache = NewsCache()
    cache.set("search", {"q": "a"}, {"d": 1})
    cache.set("headlines", {"sc": "ch"}, {"d": 2})
    count = cache.clear("search")
    assert count == 1
    assert cache.get("search", {"q": "a"}) is None
    assert cache.get("headlines", {"sc": "ch"}) is not None

def test_cache_hit_rate_display():
    from news_monitor_mcp.server import NewsCache
    cache = NewsCache()
    cache.set("search", {"q": "test"}, {"data": "x"})
    cache.get("search", {"q": "test"})  # hit
    cache.get("search", {"q": "miss"})  # miss
    stats = cache.stats()
    assert stats["hit_rate"] == "50.0%"


# ---------------------------------------------------------------------------
# AlertManager-Tests
# ---------------------------------------------------------------------------

def test_alert_manager_create_and_list(tmp_path):
    from news_monitor_mcp.server import AlertManager
    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    alert_id = mgr.create({"name": "Test Alert", "entity": "Schulamt Zürich",
        "language": "de", "source_country": "ch", "days_back": 7,
        "condition_type": "sentiment_below", "threshold": -0.2, "keyword": None})
    assert alert_id.startswith("alert_")
    alerts = mgr.list_all()
    assert len(alerts) == 1
    assert alerts[0]["name"] == "Test Alert"

def test_alert_manager_delete(tmp_path):
    from news_monitor_mcp.server import AlertManager
    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    alert_id = mgr.create({"name": "Delete Me", "entity": "test",
        "language": "de", "source_country": "ch", "days_back": 7,
        "condition_type": "volume_above", "threshold": 50.0, "keyword": None})
    assert mgr.delete(alert_id) is True
    assert len(mgr.list_all()) == 0
    assert mgr.delete("nonexistent") is False

def test_alert_evaluate_sentiment_below(tmp_path):
    from news_monitor_mcp.server import AlertManager
    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    alert = {"condition_type": "sentiment_below", "threshold": -0.2, "keyword": None}
    triggered, reason = mgr.evaluate_condition(alert, [], avg_sentiment=-0.5)
    assert triggered is True
    triggered, reason = mgr.evaluate_condition(alert, [], avg_sentiment=0.1)
    assert triggered is False

def test_alert_evaluate_sentiment_above(tmp_path):
    from news_monitor_mcp.server import AlertManager
    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    alert = {"condition_type": "sentiment_above", "threshold": 0.5, "keyword": None}
    triggered, _ = mgr.evaluate_condition(alert, [], avg_sentiment=0.8)
    assert triggered is True
    triggered, _ = mgr.evaluate_condition(alert, [], avg_sentiment=0.2)
    assert triggered is False

def test_alert_evaluate_volume_above(tmp_path):
    from news_monitor_mcp.server import AlertManager
    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    alert = {"condition_type": "volume_above", "threshold": 5.0, "keyword": None}
    articles = [{"title": f"Art {i}"} for i in range(10)]
    triggered, _ = mgr.evaluate_condition(alert, articles, avg_sentiment=None)
    assert triggered is True
    triggered, _ = mgr.evaluate_condition(alert, articles[:3], avg_sentiment=None)
    assert triggered is False

def test_alert_evaluate_keyword_found(tmp_path):
    from news_monitor_mcp.server import AlertManager
    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    alert = {"condition_type": "keyword_found", "threshold": None, "keyword": "streik"}
    articles = [{"title": "Lehrerstreik in Zürich", "summary": "..."}]
    triggered, _ = mgr.evaluate_condition(alert, articles, avg_sentiment=None)
    assert triggered is True
    articles_no_match = [{"title": "Schöner Tag heute", "summary": "Gutes Wetter"}]
    triggered, _ = mgr.evaluate_condition(alert, articles_no_match, avg_sentiment=None)
    assert triggered is False

def test_alert_mark_checked_updates_count(tmp_path):
    from news_monitor_mcp.server import AlertManager
    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    alert_id = mgr.create({"name": "T", "entity": "t", "language": "de",
        "source_country": "ch", "days_back": 7, "condition_type": "volume_above",
        "threshold": 5.0, "keyword": None})
    mgr.mark_checked(alert_id, triggered=True)
    alert = mgr.get(alert_id)
    assert alert["trigger_count"] == 1
    assert alert["last_checked"] is not None
    assert alert["last_triggered"] is not None

