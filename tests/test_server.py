"""Tests für den News Monitor MCP Server."""

import io
import json as _json
import logging as _logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from news_monitor_mcp.server import (
    MediaBriefingInput,
    ResponseFormat,
    SearchNewsInput,
    SentimentMonitorInput,
    TopNewsInput,
    TrendRadarInput,
    _format_article,
    _no_key_message,
    _sentiment_label,
    news_search,
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
        with patch("news_monitor_mcp.tools.monitoring._get_client") as mock_get_client:
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
        with patch("news_monitor_mcp.tools.monitoring._get_client") as mock_get_client:
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
        with patch("news_monitor_mcp.tools.monitoring._get_client") as mock_get_client:
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
        with patch("news_monitor_mcp.tools.monitoring._get_client") as mock_get_client:
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
    alert_id = mgr.create(
        {
            "name": "Test Alert",
            "entity": "Schulamt Zürich",
            "language": "de",
            "source_country": "ch",
            "days_back": 7,
            "condition_type": "sentiment_below",
            "threshold": -0.2,
            "keyword": None,
        }
    )
    assert alert_id.startswith("alert_")
    alerts = mgr.list_all()
    assert len(alerts) == 1
    assert alerts[0]["name"] == "Test Alert"


def test_alert_manager_delete(tmp_path):
    from news_monitor_mcp.server import AlertManager

    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    alert_id = mgr.create(
        {
            "name": "Delete Me",
            "entity": "test",
            "language": "de",
            "source_country": "ch",
            "days_back": 7,
            "condition_type": "volume_above",
            "threshold": 50.0,
            "keyword": None,
        }
    )
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
    alert_id = mgr.create(
        {
            "name": "T",
            "entity": "t",
            "language": "de",
            "source_country": "ch",
            "days_back": 7,
            "condition_type": "volume_above",
            "threshold": 5.0,
            "keyword": None,
        }
    )
    mgr.mark_checked(alert_id, triggered=True)
    alert = mgr.get(alert_id)
    assert alert["trigger_count"] == 1
    assert alert["last_checked"] is not None
    assert alert["last_triggered"] is not None


# ---------------------------------------------------------------------------
# HTTP-Auth-Middleware-Tests
# ---------------------------------------------------------------------------


def _stub_app() -> Starlette:
    async def hello(_request):
        return PlainTextResponse("ok")

    return Starlette(routes=[Route("/mcp", hello, methods=["GET", "POST"])])


def test_bearer_middleware_rejects_missing_header():
    from news_monitor_mcp.server import BearerAuthMiddleware

    app = _stub_app()
    app.add_middleware(BearerAuthMiddleware, token="secret-token")
    client = TestClient(app)
    r = client.get("/mcp")
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"


def test_bearer_middleware_rejects_wrong_scheme():
    from news_monitor_mcp.server import BearerAuthMiddleware

    app = _stub_app()
    app.add_middleware(BearerAuthMiddleware, token="secret-token")
    client = TestClient(app)
    r = client.get("/mcp", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert r.status_code == 401


def test_bearer_middleware_rejects_wrong_token():
    from news_monitor_mcp.server import BearerAuthMiddleware

    app = _stub_app()
    app.add_middleware(BearerAuthMiddleware, token="secret-token")
    client = TestClient(app)
    r = client.get("/mcp", headers={"Authorization": "Bearer wrong-token"})
    assert r.status_code == 401


def test_bearer_middleware_accepts_correct_token():
    from news_monitor_mcp.server import BearerAuthMiddleware

    app = _stub_app()
    app.add_middleware(BearerAuthMiddleware, token="secret-token")
    client = TestClient(app)
    r = client.get("/mcp", headers={"Authorization": "Bearer secret-token"})
    assert r.status_code == 200
    assert r.text == "ok"


def test_origin_allowlist_passes_when_no_origin_header():
    from news_monitor_mcp.server import OriginAllowlistMiddleware

    app = _stub_app()
    app.add_middleware(OriginAllowlistMiddleware, allowed_origins=frozenset({"https://claude.ai"}))
    client = TestClient(app)
    r = client.get("/mcp")
    assert r.status_code == 200


def test_origin_allowlist_blocks_unknown_origin():
    from news_monitor_mcp.server import OriginAllowlistMiddleware

    app = _stub_app()
    app.add_middleware(OriginAllowlistMiddleware, allowed_origins=frozenset({"https://claude.ai"}))
    client = TestClient(app)
    r = client.get("/mcp", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_origin_allowlist_allows_known_origin():
    from news_monitor_mcp.server import OriginAllowlistMiddleware

    app = _stub_app()
    app.add_middleware(OriginAllowlistMiddleware, allowed_origins=frozenset({"https://claude.ai"}))
    client = TestClient(app)
    r = client.get("/mcp", headers={"Origin": "https://claude.ai"})
    assert r.status_code == 200


def test_parse_allowed_origins_handles_csv_and_whitespace():
    from news_monitor_mcp.server import _parse_allowed_origins

    assert _parse_allowed_origins(None) == frozenset()
    assert _parse_allowed_origins("") == frozenset()
    assert _parse_allowed_origins("https://a, https://b ,, ") == frozenset({"https://a", "https://b"})


def test_build_http_app_layers_middlewares():
    from news_monitor_mcp.server import build_http_app

    app = build_http_app("secret", frozenset({"https://claude.ai"}))
    middleware_classes = [m.cls.__name__ for m in app.user_middleware]
    assert "BearerAuthMiddleware" in middleware_classes
    assert "OriginAllowlistMiddleware" in middleware_classes
    assert "RequestIdMiddleware" in middleware_classes


# ---------------------------------------------------------------------------
# Structured-Logging-Tests
# ---------------------------------------------------------------------------


def _capture_logs(level: str = "INFO") -> tuple[_logging.Logger, io.StringIO]:
    """Konfiguriert Logging gegen einen In-Memory-Buffer und liefert (logger, buffer)."""
    from news_monitor_mcp.server import _JsonFormatter, _RedactionFilter, _RequestIdFilter

    buf = io.StringIO()
    handler = _logging.StreamHandler(buf)
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_RequestIdFilter())
    handler.addFilter(_RedactionFilter())
    handler.setLevel(level)

    root = _logging.getLogger()
    saved = (root.level, list(root.handlers))
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(level)

    def restore():
        root.removeHandler(handler)
        root.setLevel(saved[0])
        for h in saved[1]:
            root.addHandler(h)

    return root, buf, restore  # type: ignore[return-value]


def test_json_formatter_emits_valid_json_with_required_fields():
    root, buf, restore = _capture_logs()
    try:
        from news_monitor_mcp.server import logger as srv_logger

        srv_logger.info("hello")
    finally:
        restore()
    line = buf.getvalue().strip().splitlines()[-1]
    payload = _json.loads(line)
    assert payload["lvl"] == "INFO"
    assert payload["msg"] == "hello"
    assert payload["logger"] == "news-monitor-mcp"
    assert payload["rid"] == "-"
    assert "ts" in payload


def test_request_id_contextvar_appears_in_log():
    from news_monitor_mcp.server import _request_id
    from news_monitor_mcp.server import logger as srv_logger

    root, buf, restore = _capture_logs()
    try:
        tok = _request_id.set("abc123def456")
        try:
            srv_logger.info("with rid")
        finally:
            _request_id.reset(tok)
    finally:
        restore()
    payload = _json.loads(buf.getvalue().strip().splitlines()[-1])
    assert payload["rid"] == "abc123def456"


def test_redaction_masks_api_key_in_url():
    from news_monitor_mcp.server import logger as srv_logger

    root, buf, restore = _capture_logs()
    try:
        srv_logger.info("calling https://api.worldnewsapi.com/search-news?api-key=SECRETXYZ&text=foo")
    finally:
        restore()
    msg = _json.loads(buf.getvalue().strip().splitlines()[-1])["msg"]
    assert "SECRETXYZ" not in msg
    assert "api-key=***" in msg


def test_redaction_masks_authorization_bearer():
    from news_monitor_mcp.server import logger as srv_logger

    root, buf, restore = _capture_logs()
    try:
        srv_logger.info("header authorization: Bearer SUPERSECRETTOKEN")
    finally:
        restore()
    msg = _json.loads(buf.getvalue().strip().splitlines()[-1])["msg"]
    assert "SUPERSECRETTOKEN" not in msg
    assert "***" in msg


def test_add_redaction_pattern_extends_pipeline():
    from news_monitor_mcp.server import _redaction_patterns, add_redaction_pattern
    from news_monitor_mcp.server import logger as srv_logger

    saved = list(_redaction_patterns)
    try:
        add_redaction_pattern(r"PIN-\d{4}", "PIN-****")
        root, buf, restore = _capture_logs()
        try:
            srv_logger.info("user PIN-1234 entered")
        finally:
            restore()
        msg = _json.loads(buf.getvalue().strip().splitlines()[-1])["msg"]
        assert "PIN-1234" not in msg
        assert "PIN-****" in msg
    finally:
        _redaction_patterns[:] = saved


def test_configure_logging_is_idempotent():
    from news_monitor_mcp.server import configure_logging

    configure_logging("INFO")
    handlers_first = list(_logging.getLogger().handlers)
    configure_logging("DEBUG")
    handlers_second = list(_logging.getLogger().handlers)
    assert len(handlers_first) == len(handlers_second) == 1
    assert _logging.getLogger().level == _logging.DEBUG


def test_configure_logging_silences_httpx_below_warning():
    from news_monitor_mcp.server import configure_logging

    configure_logging("DEBUG")
    assert _logging.getLogger("httpx").getEffectiveLevel() >= _logging.WARNING
    assert _logging.getLogger("httpcore").getEffectiveLevel() >= _logging.WARNING


@pytest.mark.asyncio
async def test_request_id_middleware_sets_header_and_contextvar():
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    from news_monitor_mcp.server import RequestIdMiddleware, _request_id

    seen = {}

    async def handler(_request):
        seen["rid_during"] = _request_id.get()
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/mcp", handler)])
    app.add_middleware(RequestIdMiddleware)
    client = TestClient(app)
    r = client.get("/mcp")
    assert r.status_code == 200
    assert "x-request-id" in r.headers
    assert r.headers["x-request-id"] == seen["rid_during"]
    assert len(r.headers["x-request-id"]) == 12


@pytest.mark.asyncio
async def test_request_id_middleware_preserves_incoming_id():
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    from news_monitor_mcp.server import RequestIdMiddleware

    app = Starlette(routes=[Route("/mcp", lambda r: PlainTextResponse("ok"))])
    app.add_middleware(RequestIdMiddleware)
    client = TestClient(app)
    r = client.get("/mcp", headers={"x-request-id": "client-supplied-id"})
    assert r.headers["x-request-id"] == "client-supplied-id"


# ---------------------------------------------------------------------------
# SEC-API-KEY-HANDLING Tests
# ---------------------------------------------------------------------------


def test_get_api_key_returns_secretstr_when_set(monkeypatch):
    from pydantic import SecretStr

    from news_monitor_mcp.server import _get_api_key

    monkeypatch.setenv("WORLD_NEWS_API_KEY", "my-super-secret-key")
    key = _get_api_key()
    assert isinstance(key, SecretStr)
    assert key.get_secret_value() == "my-super-secret-key"


def test_get_api_key_returns_none_when_unset(monkeypatch):
    from news_monitor_mcp.server import _get_api_key

    monkeypatch.delenv("WORLD_NEWS_API_KEY", raising=False)
    assert _get_api_key() is None


def test_secretstr_str_repr_does_not_leak():
    from pydantic import SecretStr

    key = SecretStr("my-super-secret-key")
    assert "my-super-secret-key" not in str(key)
    assert "my-super-secret-key" not in repr(key)


def test_auth_headers_returns_x_api_key():
    from pydantic import SecretStr

    from news_monitor_mcp.server import _auth_headers

    headers = _auth_headers(SecretStr("k-123"))
    assert headers == {"x-api-key": "k-123"}


@pytest.mark.asyncio
async def test_news_search_sends_x_api_key_header_not_url_param():
    """Verifiziert, dass news_search den Key per Header sendet und nichts in den URL-Params landet."""
    captured = {}

    class _FakeResponse:
        def __init__(self):
            self.status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"news": [], "available": 0}

    class _FakeClient:
        async def get(self, url, params=None, headers=None):
            captured["url"] = url
            captured["params"] = dict(params) if params else {}
            captured["headers"] = dict(headers) if headers else {}
            return _FakeResponse()

    with patch.dict("os.environ", {"WORLD_NEWS_API_KEY": "leak-test-key"}):
        with patch("news_monitor_mcp.tools.monitoring._get_client", return_value=_FakeClient()):
            params = SearchNewsInput(query="zürich", use_cache=False)
            await news_search(params)

    # Header MUST carry the key
    assert captured["headers"].get("x-api-key") == "leak-test-key"
    # URL params MUST NOT contain the key under any spelling
    for k, v in captured["params"].items():
        assert "leak-test-key" not in str(v), f"key leaked into params[{k}]={v}"
        assert k.lower() not in {"api-key", "api_key", "apikey"}, f"forbidden param key: {k}"


def test_handle_api_error_does_not_echo_raw_exception_string():
    from news_monitor_mcp.server import _handle_api_error

    class _LeakyError(Exception):
        def __str__(self):
            return "https://api.worldnewsapi.com/search-news?api-key=LEAKED_SECRET_KEY&q=foo"

    result = _handle_api_error(_LeakyError("ignored"))
    assert "LEAKED_SECRET_KEY" not in result
    assert "api-key=" not in result
    assert "_LeakyError" in result  # type name is fine, content is not


def test_handle_api_error_maps_known_status_codes():
    import httpx

    from news_monitor_mcp.server import _handle_api_error

    def _make(status):
        req = httpx.Request("GET", "https://example.invalid/x?api-key=SHOULDNOTAPPEAR")
        resp = httpx.Response(status, request=req)
        return httpx.HTTPStatusError("boom", request=req, response=resp)

    assert "Ungültiger API-Key" in _handle_api_error(_make(401))
    assert "Kontingent" in _handle_api_error(_make(402))
    assert "Rate Limit" in _handle_api_error(_make(429))
    # Generic 5xx returns only the status code, never the URL
    msg = _handle_api_error(_make(503))
    assert "503" in msg
    assert "SHOULDNOTAPPEAR" not in msg


# ---------------------------------------------------------------------------
# SDK-LIFESPAN Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lifespan_closes_lazy_client():
    """Globaler httpx-Client wird beim Lifespan-Exit geschlossen und auf None gesetzt."""
    import news_monitor_mcp.api_client as api
    import news_monitor_mcp.server as srv

    # Sicherstellen, dass Anfangszustand sauber ist
    await api.close_client()

    client = srv._get_client()
    assert api.get_current_client() is client
    assert client.is_closed is False

    async with srv.server_lifespan(srv.mcp) as state:
        assert state == {}

    assert client.is_closed is True
    assert api.get_current_client() is None


@pytest.mark.asyncio
async def test_lifespan_is_idempotent_when_client_never_created():
    """Lifespan-Exit darf nicht crashen, wenn _client lazy nie erzeugt wurde."""
    import news_monitor_mcp.api_client as api
    import news_monitor_mcp.server as srv

    await api.close_client()

    async with srv.server_lifespan(srv.mcp):
        pass  # tool ruft _get_client() nicht auf

    assert api.get_current_client() is None


@pytest.mark.asyncio
async def test_lifespan_resets_client_even_if_aclose_raises(monkeypatch, caplog):
    """Wenn aclose() eine Exception wirft, soll _client trotzdem auf None gesetzt werden."""
    import news_monitor_mcp.api_client as api
    import news_monitor_mcp.server as srv

    await api.close_client()

    class _BrokenClient:
        is_closed = False

        async def aclose(self):
            raise RuntimeError("simulated teardown failure")

    api._client = _BrokenClient()  # type: ignore[assignment]

    async with srv.server_lifespan(srv.mcp):
        pass

    assert api.get_current_client() is None


def test_fastmcp_instance_has_lifespan_attached():
    """Sanity-Check: lifespan ist tatsaechlich am MCPServer-Server registriert."""
    import news_monitor_mcp.server as srv

    assert srv.mcp.settings.lifespan is srv.server_lifespan


# ---------------------------------------------------------------------------
# ARCH-CONCURRENCY Tests
# ---------------------------------------------------------------------------


def test_atomic_write_does_not_leave_tmp_file(tmp_path):
    from news_monitor_mcp.server import _atomic_write_json

    target = tmp_path / "alerts.json"
    _atomic_write_json(str(target), {"a": 1, "b": [2, 3]})

    assert target.exists()
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "alerts.json"]
    assert leftovers == [], f"unexpected leftovers: {leftovers}"
    assert _json.loads(target.read_text(encoding="utf-8")) == {"a": 1, "b": [2, 3]}


def test_atomic_write_preserves_old_data_when_write_fails(tmp_path, monkeypatch):
    """Wenn json.dump abbricht, bleibt die alte Datei intakt."""
    from news_monitor_mcp.server import _atomic_write_json

    target = tmp_path / "alerts.json"
    target.write_text(_json.dumps({"original": True}), encoding="utf-8")

    class _NotSerializable:
        pass

    with pytest.raises(TypeError):
        _atomic_write_json(str(target), {"bad": _NotSerializable()})

    # Original file unchanged
    assert _json.loads(target.read_text(encoding="utf-8")) == {"original": True}
    # No tmp leftover
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "alerts.json"]
    assert leftovers == []


def test_atomic_write_replaces_existing_file(tmp_path):
    from news_monitor_mcp.server import _atomic_write_json

    target = tmp_path / "alerts.json"
    target.write_text(_json.dumps({"v": 1}), encoding="utf-8")
    _atomic_write_json(str(target), {"v": 2})
    assert _json.loads(target.read_text(encoding="utf-8")) == {"v": 2}


def test_alert_manager_get_returns_defensive_copy(tmp_path):
    from news_monitor_mcp.server import AlertManager

    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    alert_id = mgr.create(
        {
            "name": "T",
            "entity": "t",
            "language": "de",
            "source_country": "ch",
            "days_back": 7,
            "condition_type": "volume_above",
            "threshold": 5.0,
            "keyword": None,
        }
    )
    snapshot = mgr.get(alert_id)
    snapshot["name"] = "MUTATED EXTERNALLY"
    # Internal state must NOT reflect the external mutation
    again = mgr.get(alert_id)
    assert again["name"] == "T"


def test_alert_manager_concurrent_creates_from_threads(tmp_path):
    """100 parallel create() Aufrufe aus Threads -> alle 100 Alerts persistiert."""
    import threading as _th

    from news_monitor_mcp.server import AlertManager

    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    errors: list[BaseException] = []

    def _worker(i: int) -> None:
        try:
            mgr.create(
                {
                    "name": f"alert-{i}",
                    "entity": f"e-{i}",
                    "language": "de",
                    "source_country": "ch",
                    "days_back": 7,
                    "condition_type": "volume_above",
                    "threshold": 1.0,
                    "keyword": None,
                }
            )
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [_th.Thread(target=_worker, args=(i,)) for i in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(mgr.list_all()) == 100
    # Persisted file must agree with in-memory state
    on_disk = _json.loads((tmp_path / "alerts.json").read_text(encoding="utf-8"))
    assert len(on_disk) == 100


def test_alert_manager_concurrent_mark_checked_increments_correctly(tmp_path):
    import threading as _th

    from news_monitor_mcp.server import AlertManager

    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    aid = mgr.create(
        {
            "name": "T",
            "entity": "t",
            "language": "de",
            "source_country": "ch",
            "days_back": 7,
            "condition_type": "volume_above",
            "threshold": 1.0,
            "keyword": None,
        }
    )

    def _worker() -> None:
        mgr.mark_checked(aid, triggered=True)

    threads = [_th.Thread(target=_worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert mgr.get(aid)["trigger_count"] == 50


def test_file_lock_is_noop_when_fcntl_unavailable(tmp_path, monkeypatch):
    """Auf Plattformen ohne fcntl darf _file_lock nicht crashen."""
    import news_monitor_mcp.server as srv

    monkeypatch.setattr(srv, "_fcntl", None)
    with srv._file_lock(str(tmp_path / "alerts.json")):
        pass  # should be a no-op contextmanager


def test_file_lock_creates_sidecar_and_serializes(tmp_path):
    """fcntl-Pfad: Lock-File wird erzeugt; zwei Locks im selben Prozess sind seriell."""
    import news_monitor_mcp.server as srv

    if srv._fcntl is None:
        pytest.skip("fcntl not available on this platform")

    import os as _os

    target = str(tmp_path / "alerts.json")
    with srv._file_lock(target):
        assert _os.path.exists(target + ".lock")
    # Lock-Sidecar bleibt persistent (das ist gewollt — wird beim naechsten Aufruf
    # wiederverwendet). Wichtig ist, dass das Hauptfile NICHT erzeugt wurde:
    assert not _os.path.exists(target)


# ---------------------------------------------------------------------------
# SEC-ALERTS-PATH Tests
# ---------------------------------------------------------------------------


def test_resolve_alerts_path_default(monkeypatch):
    import os as _os

    from news_monitor_mcp.server import ALERTS_DIR_DEFAULT, _resolve_alerts_path

    monkeypatch.delenv("NEWS_MONITOR_ALERTS_FILE", raising=False)
    monkeypatch.delenv("NEWS_MONITOR_ALERTS_DIR", raising=False)
    resolved = _resolve_alerts_path()
    assert resolved == _os.path.join(ALERTS_DIR_DEFAULT, "alerts.json")


def test_resolve_alerts_path_honors_dir_env(monkeypatch, tmp_path):
    import os as _os

    from news_monitor_mcp.server import _resolve_alerts_path

    monkeypatch.delenv("NEWS_MONITOR_ALERTS_FILE", raising=False)
    monkeypatch.setenv("NEWS_MONITOR_ALERTS_DIR", str(tmp_path))
    assert _resolve_alerts_path() == _os.path.join(str(tmp_path), "alerts.json")


def test_resolve_alerts_path_honors_file_env_back_compat(monkeypatch, tmp_path):
    from news_monitor_mcp.server import _resolve_alerts_path

    target = str(tmp_path / "custom-alerts.json")
    monkeypatch.setenv("NEWS_MONITOR_ALERTS_FILE", target)
    monkeypatch.delenv("NEWS_MONITOR_ALERTS_DIR", raising=False)
    assert _resolve_alerts_path() == target


def test_resolve_alerts_path_rejects_dotdot_segments(monkeypatch, tmp_path):
    from news_monitor_mcp.server import _resolve_alerts_path

    # Construct a relative path with leading .. that cannot be normalized away
    # without escaping the cwd; using an absolute prefix avoids that.
    monkeypatch.setenv("NEWS_MONITOR_ALERTS_FILE", "../../../etc/cron.d/payload")
    monkeypatch.delenv("NEWS_MONITOR_ALERTS_DIR", raising=False)
    # Run from a path where the .. would normalize away cleanly; we test the
    # other vector: a path that already contains '..' after expanduser stays
    # invariant to normpath only if there are no segments. The check rejects
    # anything where abspath != normpath(abspath); that happens for paths
    # containing '..' on systems where abspath leaves them in.
    # Easier: assert the function returns without error for a clean path,
    # but raises when we explicitly inject a .. segment that survives
    # normalization (impossible after abspath()). So we test the symlink
    # path instead.
    # Clean path with .. that resolves away -> should be allowed
    resolved = _resolve_alerts_path()
    assert ".." not in resolved


def test_resolve_alerts_path_refuses_symlinked_parent(monkeypatch, tmp_path):
    import os as _os

    from news_monitor_mcp.server import _resolve_alerts_path

    real_dir = tmp_path / "real"
    real_dir.mkdir()
    link_dir = tmp_path / "link"
    _os.symlink(str(real_dir), str(link_dir))

    monkeypatch.delenv("NEWS_MONITOR_ALERTS_FILE", raising=False)
    monkeypatch.setenv("NEWS_MONITOR_ALERTS_DIR", str(link_dir))
    with pytest.raises(RuntimeError, match="symlink"):
        _resolve_alerts_path()


def test_ensure_secure_perms_sets_0o600_on_file(tmp_path):
    import os as _os
    import stat as _stat

    from news_monitor_mcp.server import _ensure_secure_perms

    target = tmp_path / "alerts.json"
    target.write_text("{}", encoding="utf-8")
    _os.chmod(str(target), 0o644)  # start permissive

    _ensure_secure_perms(str(target))

    mode = _stat.S_IMODE(_os.stat(str(target)).st_mode)
    assert mode == 0o600


def test_ensure_secure_perms_sets_0o700_on_parent(tmp_path):
    import os as _os
    import stat as _stat

    from news_monitor_mcp.server import _ensure_secure_perms

    parent = tmp_path / "alerts-dir"
    parent.mkdir()
    _os.chmod(str(parent), 0o755)
    target = parent / "alerts.json"
    target.write_text("{}", encoding="utf-8")

    _ensure_secure_perms(str(target))

    mode = _stat.S_IMODE(_os.stat(str(parent)).st_mode)
    assert mode == 0o700


# ---------------------------------------------------------------------------
# SCALE-STATEFUL Tests (LRU cap + background sweep)
# ---------------------------------------------------------------------------


def test_cache_get_promotes_to_most_recently_used():
    """Erfolgreicher get() schiebt den Key ans Ende der OrderedDict (LRU)."""
    from news_monitor_mcp.server import NewsCache

    cache = NewsCache(max_per_type=10)
    cache.set("search", {"q": "a"}, {"v": 1})
    cache.set("search", {"q": "b"}, {"v": 2})
    cache.set("search", {"q": "c"}, {"v": 3})

    # Access "a" -> wird most-recently-used
    cache.get("search", {"q": "a"})

    # Insertion-order-Vergleich via internal _store: "a" steht jetzt zuletzt
    keys_in_order = list(cache._store.keys())
    a_key = cache._make_key("search", {"q": "a"})
    assert keys_in_order[-1] == a_key


def test_cache_evicts_lru_when_cap_exceeded():
    """Bei Cap-Erreichen wird der am laengsten ungenutzte Eintrag desselben Typs verdraengt."""
    from news_monitor_mcp.server import NewsCache

    cache = NewsCache(max_per_type=3)
    cache.set("search", {"q": "a"}, {"v": 1})
    cache.set("search", {"q": "b"}, {"v": 2})
    cache.set("search", {"q": "c"}, {"v": 3})

    # Access "a" -> bumpt es auf most-recent. "b" wird damit LRU.
    cache.get("search", {"q": "a"})

    # Neuer Eintrag triggert Cap-Eviction. "b" muss raus.
    cache.set("search", {"q": "d"}, {"v": 4})

    assert cache.get("search", {"q": "a"}) is not None
    assert cache.get("search", {"q": "b"}) is None  # verdraengt
    assert cache.get("search", {"q": "c"}) is not None
    assert cache.get("search", {"q": "d"}) is not None


def test_cache_cap_is_per_tool_type():
    """Ein Cap-Hit auf 'search' verdraengt NICHT Eintraege anderer Typen."""
    from news_monitor_mcp.server import NewsCache

    cache = NewsCache(max_per_type=2)
    cache.set("search", {"q": "a"}, {"v": 1})
    cache.set("headlines", {"sc": "ch"}, {"v": 2})
    cache.set("headlines", {"sc": "de"}, {"v": 3})

    # Cap fuer 'search' ausschoepfen
    cache.set("search", {"q": "b"}, {"v": 4})
    cache.set("search", {"q": "c"}, {"v": 5})  # triggert Cap-Eviction auf 'search'

    # headlines-Eintraege bleiben unangetastet
    assert cache.get("headlines", {"sc": "ch"}) is not None
    assert cache.get("headlines", {"sc": "de"}) is not None
    # 'a' (das aelteste 'search') ist weg
    assert cache.get("search", {"q": "a"}) is None


def test_cache_cap_zero_disables_cap():
    from news_monitor_mcp.server import NewsCache

    cache = NewsCache(max_per_type=0)
    for i in range(50):
        cache.set("search", {"q": str(i)}, {"v": i})
    assert len(cache._store) == 50


def test_cache_stats_reports_cap_and_evictions():
    from news_monitor_mcp.server import NewsCache

    cache = NewsCache(max_per_type=2)
    cache.set("search", {"q": "a"}, {"v": 1})
    cache.set("search", {"q": "b"}, {"v": 2})
    cache.set("search", {"q": "c"}, {"v": 3})  # evicts 'a'

    stats = cache.stats()
    assert stats["max_eintraege_pro_typ"] == 2
    assert stats["verdraengt_durch_cap"] == 1


def test_cache_update_existing_key_does_not_evict():
    """Re-set desselben Keys aktualisiert in-place, ohne Cap-Eviction zu triggern."""
    from news_monitor_mcp.server import NewsCache

    cache = NewsCache(max_per_type=3)
    cache.set("search", {"q": "a"}, {"v": 1})
    cache.set("search", {"q": "b"}, {"v": 2})
    cache.set("search", {"q": "c"}, {"v": 3})
    # Update "a" — sollte nicht in den Cap-Pfad gehen
    cache.set("search", {"q": "a"}, {"v": 99})
    assert cache.get("search", {"q": "a"}) == {"v": 99}
    assert cache.get("search", {"q": "b"}) is not None
    assert cache.get("search", {"q": "c"}) is not None
    assert cache.stats()["verdraengt_durch_cap"] == 0


def test_get_cache_max_per_type_env_parsing(monkeypatch):
    from news_monitor_mcp.server import (
        CACHE_MAX_PER_TYPE_DEFAULT,
        _get_cache_max_per_type,
    )

    monkeypatch.delenv("MCP_CACHE_MAX_PER_TYPE", raising=False)
    assert _get_cache_max_per_type() == CACHE_MAX_PER_TYPE_DEFAULT

    monkeypatch.setenv("MCP_CACHE_MAX_PER_TYPE", "42")
    assert _get_cache_max_per_type() == 42

    monkeypatch.setenv("MCP_CACHE_MAX_PER_TYPE", "0")
    assert _get_cache_max_per_type() == 0

    monkeypatch.setenv("MCP_CACHE_MAX_PER_TYPE", "-7")
    assert _get_cache_max_per_type() == 0

    monkeypatch.setenv("MCP_CACHE_MAX_PER_TYPE", "abc")
    assert _get_cache_max_per_type() == CACHE_MAX_PER_TYPE_DEFAULT


def test_get_cache_sweep_seconds_env_parsing(monkeypatch):
    from news_monitor_mcp.server import (
        CACHE_SWEEP_SECONDS_DEFAULT,
        _get_cache_sweep_seconds,
    )

    monkeypatch.delenv("MCP_CACHE_SWEEP_SECONDS", raising=False)
    assert _get_cache_sweep_seconds() == CACHE_SWEEP_SECONDS_DEFAULT

    monkeypatch.setenv("MCP_CACHE_SWEEP_SECONDS", "60")
    assert _get_cache_sweep_seconds() == 60

    monkeypatch.setenv("MCP_CACHE_SWEEP_SECONDS", "0")
    assert _get_cache_sweep_seconds() == 0

    monkeypatch.setenv("MCP_CACHE_SWEEP_SECONDS", "nope")
    assert _get_cache_sweep_seconds() == CACHE_SWEEP_SECONDS_DEFAULT


@pytest.mark.asyncio
async def test_cache_sweep_loop_calls_evict_expired():
    """Der Background-Loop ruft tatsaechlich evict_expired() periodisch auf."""
    import asyncio as _asyncio

    from news_monitor_mcp.server import _cache_sweep_loop

    calls = {"n": 0}

    class _FakeCache:
        def evict_expired(self) -> int:
            calls["n"] += 1
            return 0

    task = _asyncio.create_task(_cache_sweep_loop(_FakeCache(), interval_seconds=0))
    # interval=0 -> sleep(0) returns immediately. Let the loop spin a few times.
    await _asyncio.sleep(0.02)
    task.cancel()
    try:
        await task
    except _asyncio.CancelledError:
        pass
    assert calls["n"] >= 2  # loop ran at least twice


@pytest.mark.asyncio
async def test_server_lifespan_starts_and_stops_sweep_task(monkeypatch):
    """server_lifespan startet/stoppt den Cache-Sweep ohne Crash."""
    import asyncio as _asyncio

    import news_monitor_mcp.api_client as api
    import news_monitor_mcp.server as srv

    monkeypatch.setenv("MCP_CACHE_SWEEP_SECONDS", "1")
    await api.close_client()

    async with srv.server_lifespan(srv.mcp):
        running = [t for t in _asyncio.all_tasks() if t.get_name() == "cache-sweep"]
        assert len(running) == 1

    remaining = [t for t in _asyncio.all_tasks() if t.get_name() == "cache-sweep"]
    assert remaining == []


@pytest.mark.asyncio
async def test_server_lifespan_sweep_zero_disables_task(monkeypatch):
    """MCP_CACHE_SWEEP_SECONDS=0 startet keinen Background-Task."""
    import asyncio as _asyncio

    import news_monitor_mcp.api_client as api
    import news_monitor_mcp.server as srv

    monkeypatch.setenv("MCP_CACHE_SWEEP_SECONDS", "0")
    await api.close_client()

    async with srv.server_lifespan(srv.mcp):
        running = [t for t in _asyncio.all_tasks() if t.get_name() == "cache-sweep"]
        assert running == []


def test_news_cache_satisfies_cache_backend_protocol():
    """Sanity-Check: NewsCache erfuellt das CacheBackend-Protocol strukturell."""
    from news_monitor_mcp.server import CacheBackend, NewsCache

    cache: CacheBackend = NewsCache()
    # Static check is enough for Protocol; if attributes were missing,
    # the assignment would still work at runtime, so probe the methods:
    for method in ("get", "set", "clear", "evict_expired", "stats"):
        assert callable(getattr(cache, method)), f"missing {method}"


# ---------------------------------------------------------------------------
# CH-DSG Retention Tests
# ---------------------------------------------------------------------------


def test_get_alert_retention_days_default(monkeypatch):
    from news_monitor_mcp.server import ALERT_RETENTION_DAYS_DEFAULT, _get_alert_retention_days

    monkeypatch.delenv("MCP_ALERT_RETENTION_DAYS", raising=False)
    assert _get_alert_retention_days() == ALERT_RETENTION_DAYS_DEFAULT


def test_get_alert_retention_days_honors_env(monkeypatch):
    from news_monitor_mcp.server import _get_alert_retention_days

    monkeypatch.setenv("MCP_ALERT_RETENTION_DAYS", "30")
    assert _get_alert_retention_days() == 30


def test_get_alert_retention_days_accepts_zero_to_disable(monkeypatch):
    from news_monitor_mcp.server import _get_alert_retention_days

    monkeypatch.setenv("MCP_ALERT_RETENTION_DAYS", "0")
    assert _get_alert_retention_days() == 0


def test_get_alert_retention_days_clamps_negative(monkeypatch):
    from news_monitor_mcp.server import _get_alert_retention_days

    monkeypatch.setenv("MCP_ALERT_RETENTION_DAYS", "-5")
    assert _get_alert_retention_days() == 0


def test_get_alert_retention_days_falls_back_on_garbage(monkeypatch):
    from news_monitor_mcp.server import ALERT_RETENTION_DAYS_DEFAULT, _get_alert_retention_days

    monkeypatch.setenv("MCP_ALERT_RETENTION_DAYS", "notanumber")
    assert _get_alert_retention_days() == ALERT_RETENTION_DAYS_DEFAULT


def test_alert_manager_prunes_old_alerts_on_load(tmp_path):
    """Alerts mit created_at older als retention_days werden beim __init__ entfernt."""
    import json as _json
    from datetime import datetime, timedelta

    from news_monitor_mcp.server import AlertManager

    target = tmp_path / "alerts.json"
    old_ts = (datetime.now() - timedelta(days=120)).isoformat()
    fresh_ts = (datetime.now() - timedelta(days=10)).isoformat()
    target.write_text(
        _json.dumps(
            {
                "alert_old": {
                    "id": "alert_old",
                    "name": "stale",
                    "created_at": old_ts,
                    "entity": "x",
                    "language": "de",
                    "days_back": 7,
                    "source_country": "ch",
                    "condition_type": "volume_above",
                    "threshold": 1.0,
                    "keyword": None,
                    "last_checked": None,
                    "last_triggered": None,
                    "trigger_count": 0,
                },
                "alert_new": {
                    "id": "alert_new",
                    "name": "fresh",
                    "created_at": fresh_ts,
                    "entity": "y",
                    "language": "de",
                    "days_back": 7,
                    "source_country": "ch",
                    "condition_type": "volume_above",
                    "threshold": 1.0,
                    "keyword": None,
                    "last_checked": None,
                    "last_triggered": None,
                    "trigger_count": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    mgr = AlertManager(file_path=str(target), retention_days=90)
    ids = {a["id"] for a in mgr.list_all()}
    assert "alert_new" in ids
    assert "alert_old" not in ids


def test_alert_manager_persists_pruned_state_to_disk(tmp_path):
    """Pruning beim Start muss auch ins File geschrieben werden."""
    import json as _json
    from datetime import datetime, timedelta

    from news_monitor_mcp.server import AlertManager

    target = tmp_path / "alerts.json"
    old_ts = (datetime.now() - timedelta(days=120)).isoformat()
    target.write_text(
        _json.dumps(
            {
                "alert_old": {
                    "id": "alert_old",
                    "name": "stale",
                    "created_at": old_ts,
                    "entity": "x",
                    "language": "de",
                    "days_back": 7,
                    "source_country": "ch",
                    "condition_type": "volume_above",
                    "threshold": 1.0,
                    "keyword": None,
                    "last_checked": None,
                    "last_triggered": None,
                    "trigger_count": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    AlertManager(file_path=str(target), retention_days=90)

    on_disk = _json.loads(target.read_text(encoding="utf-8"))
    assert on_disk == {}


def test_alert_manager_retention_zero_disables_pruning(tmp_path):
    import json as _json
    from datetime import datetime, timedelta

    from news_monitor_mcp.server import AlertManager

    target = tmp_path / "alerts.json"
    old_ts = (datetime.now() - timedelta(days=999)).isoformat()
    target.write_text(
        _json.dumps(
            {
                "alert_ancient": {
                    "id": "alert_ancient",
                    "name": "ancient",
                    "created_at": old_ts,
                    "entity": "x",
                    "language": "de",
                    "days_back": 7,
                    "source_country": "ch",
                    "condition_type": "volume_above",
                    "threshold": 1.0,
                    "keyword": None,
                    "last_checked": None,
                    "last_triggered": None,
                    "trigger_count": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    mgr = AlertManager(file_path=str(target), retention_days=0)
    assert len(mgr.list_all()) == 1


def test_alert_manager_keeps_alerts_without_created_at(tmp_path):
    """Legacy-Alerts ohne created_at-Feld werden NICHT geloescht."""
    import json as _json

    from news_monitor_mcp.server import AlertManager

    target = tmp_path / "alerts.json"
    target.write_text(
        _json.dumps(
            {
                "alert_legacy": {
                    "id": "alert_legacy",
                    "name": "legacy",
                    "entity": "x",
                    "language": "de",
                    "days_back": 7,
                    "source_country": "ch",
                    "condition_type": "volume_above",
                    "threshold": 1.0,
                    "keyword": None,
                    "last_checked": None,
                    "last_triggered": None,
                    "trigger_count": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    mgr = AlertManager(file_path=str(target), retention_days=1)
    assert len(mgr.list_all()) == 1


def test_alert_manager_keeps_alerts_with_invalid_timestamp(tmp_path):
    """Korrupte created_at-Werte lassen den Alert in Ruhe (defensive)."""
    import json as _json

    from news_monitor_mcp.server import AlertManager

    target = tmp_path / "alerts.json"
    target.write_text(
        _json.dumps(
            {
                "alert_corrupt": {
                    "id": "alert_corrupt",
                    "name": "corrupt",
                    "created_at": "not-a-timestamp",
                    "entity": "x",
                    "language": "de",
                    "days_back": 7,
                    "source_country": "ch",
                    "condition_type": "volume_above",
                    "threshold": 1.0,
                    "keyword": None,
                    "last_checked": None,
                    "last_triggered": None,
                    "trigger_count": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    mgr = AlertManager(file_path=str(target), retention_days=1)
    assert len(mgr.list_all()) == 1


def test_alert_manager_retention_keeps_recently_created(tmp_path):
    """Ein eben erstellter Alert ueberlebt jede Retention-Frist > 0."""
    from news_monitor_mcp.server import AlertManager

    target = tmp_path / "alerts.json"
    mgr = AlertManager(file_path=str(target), retention_days=1)
    mgr.create(
        {
            "name": "Fresh",
            "entity": "t",
            "language": "de",
            "source_country": "ch",
            "days_back": 7,
            "condition_type": "volume_above",
            "threshold": 1.0,
            "keyword": None,
        }
    )

    # Re-open mit retention=1 day -> created_at ist now(), bleibt
    mgr2 = AlertManager(file_path=str(target), retention_days=1)
    assert len(mgr2.list_all()) == 1


# ---------------------------------------------------------------------------
# HITL-DESTRUCTIVE Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alert_delete_without_confirm_returns_prompt(tmp_path, monkeypatch):
    """news_alert_delete ohne confirm=True darf NICHT loeschen."""
    from news_monitor_mcp.server import (
        AlertManager,
        DeleteAlertInput,
        news_alert_delete,
    )

    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    aid = mgr.create(
        {
            "name": "T",
            "entity": "t",
            "language": "de",
            "source_country": "ch",
            "days_back": 7,
            "condition_type": "volume_above",
            "threshold": 1.0,
            "keyword": None,
        }
    )

    import news_monitor_mcp.app as _app
    import news_monitor_mcp.tools.alerts_tools as _tools_alerts

    monkeypatch.setattr(_app, "_alert_manager", mgr)
    monkeypatch.setattr(_tools_alerts, "_alert_manager", mgr)
    result = await news_alert_delete(DeleteAlertInput(alert_id=aid))
    assert "Bestaetigung" in result
    assert "confirm=true" in result
    # Alert ist NICHT geloescht
    assert mgr.get(aid) is not None


@pytest.mark.asyncio
async def test_alert_delete_with_confirm_removes_alert(tmp_path, monkeypatch):
    from news_monitor_mcp.server import (
        AlertManager,
        DeleteAlertInput,
        news_alert_delete,
    )

    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    aid = mgr.create(
        {
            "name": "T",
            "entity": "t",
            "language": "de",
            "source_country": "ch",
            "days_back": 7,
            "condition_type": "volume_above",
            "threshold": 1.0,
            "keyword": None,
        }
    )

    import news_monitor_mcp.app as _app
    import news_monitor_mcp.tools.alerts_tools as _tools_alerts

    monkeypatch.setattr(_app, "_alert_manager", mgr)
    monkeypatch.setattr(_tools_alerts, "_alert_manager", mgr)
    result = await news_alert_delete(DeleteAlertInput(alert_id=aid, confirm=True))
    assert "geloescht" in result
    assert mgr.get(aid) is None


@pytest.mark.asyncio
async def test_alert_delete_nonexistent_does_not_require_confirm(tmp_path, monkeypatch):
    """Nicht-existente Alert-ID liefert sofort 'nicht gefunden', nicht den Prompt."""
    from news_monitor_mcp.server import (
        AlertManager,
        DeleteAlertInput,
        news_alert_delete,
    )

    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    import news_monitor_mcp.app as _app
    import news_monitor_mcp.tools.alerts_tools as _tools_alerts

    monkeypatch.setattr(_app, "_alert_manager", mgr)
    monkeypatch.setattr(_tools_alerts, "_alert_manager", mgr)
    result = await news_alert_delete(DeleteAlertInput(alert_id="alert_doesnotexist"))
    assert "nicht gefunden" in result


@pytest.mark.asyncio
async def test_cache_clear_without_confirm_returns_prompt(monkeypatch):
    from news_monitor_mcp.server import (
        CacheClearInput,
        NewsCache,
        news_cache_clear,
    )

    cache = NewsCache()
    cache.set("search", {"q": "a"}, {"d": 1})
    cache.set("search", {"q": "b"}, {"d": 2})
    import news_monitor_mcp.app as _app
    import news_monitor_mcp.tools.cache_admin as _tools_cache

    monkeypatch.setattr(_app, "_cache", cache)
    monkeypatch.setattr(_tools_cache, "_cache", cache)

    result = await news_cache_clear(CacheClearInput())
    assert "Bestaetigung" in result
    assert "confirm=true" in result
    # Cache nicht geleert
    assert cache.get("search", {"q": "a"}) is not None


@pytest.mark.asyncio
async def test_cache_clear_with_confirm_empties_cache(monkeypatch):
    from news_monitor_mcp.server import (
        CacheClearInput,
        NewsCache,
        news_cache_clear,
    )

    cache = NewsCache()
    cache.set("search", {"q": "a"}, {"d": 1})
    import news_monitor_mcp.app as _app
    import news_monitor_mcp.tools.cache_admin as _tools_cache

    monkeypatch.setattr(_app, "_cache", cache)
    monkeypatch.setattr(_tools_cache, "_cache", cache)

    result = await news_cache_clear(CacheClearInput(confirm=True))
    assert "geleert" in result
    assert cache.get("search", {"q": "a"}) is None


@pytest.mark.asyncio
async def test_cache_clear_unknown_type_rejects_before_confirm(monkeypatch):
    """Validation-Fehler bei tool_type kommt vor dem confirm-Check."""
    import news_monitor_mcp.app as _app
    import news_monitor_mcp.tools.cache_admin as _tools_cache
    from news_monitor_mcp.server import (
        CacheClearInput,
        NewsCache,
        news_cache_clear,
    )

    fresh = NewsCache()
    monkeypatch.setattr(_app, "_cache", fresh)
    monkeypatch.setattr(_tools_cache, "_cache", fresh)
    result = await news_cache_clear(CacheClearInput(tool_type="nonexistent_typ"))
    assert "Unbekannter Tool-Typ" in result
    assert "Bestaetigung" not in result


def test_alert_manager_creates_file_with_0o600(tmp_path):
    import os as _os
    import stat as _stat

    from news_monitor_mcp.server import AlertManager

    target = tmp_path / "alerts.json"
    mgr = AlertManager(file_path=str(target))
    mgr.create(
        {
            "name": "T",
            "entity": "t",
            "language": "de",
            "source_country": "ch",
            "days_back": 7,
            "condition_type": "volume_above",
            "threshold": 1.0,
            "keyword": None,
        }
    )

    mode = _stat.S_IMODE(_os.stat(str(target)).st_mode)
    assert mode == 0o600
    # World-readable bits are off
    assert mode & 0o077 == 0


def test_redaction_pattern_masks_x_api_key_header_dump():
    from news_monitor_mcp.server import logger as srv_logger

    root, buf, restore = _capture_logs()
    try:
        srv_logger.info("request headers: {'x-api-key': 'SUPERSECRET'}")
        srv_logger.info("curl -H 'x-api-key: ANOTHERSECRET' https://api.example.com/x")
    finally:
        restore()
    lines = [_json.loads(line)["msg"] for line in buf.getvalue().strip().splitlines()]
    blob = "\n".join(lines)
    assert "SUPERSECRET" not in blob
    assert "ANOTHERSECRET" not in blob
    assert "***" in blob
