"""News Monitor MCP Server – 15 Tools für globales News-Monitoring.

MCP Server für globale Nachrichtenrecherche, Medienmonitoring und automatische
Benachrichtigungen via WorldNewsAPI.

Neu in v0.2.0:
  - TTL-Cache: Reduziert API-Calls um bis zu 80% bei wiederholten Abfragen
  - Alert-System: Automatische Benachrichtigung bei Sentiment-Shifts oder
    Artikel-Schwellen (persistente Speicherung in ~/.news-monitor-mcp/alerts.json)

Metapher: Der Server ist jetzt nicht mehr nur ein Assistent, der auf Fragen
antwortet – er ist ein aktiver Wächter, der schläft wenn nichts passiert
(Cache) und dich weckt wenn es wichtig wird (Alerts).

API key required: Kostenloser Key via https://worldnewsapi.com/console/
Set environment variable: WORLD_NEWS_API_KEY
"""

import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger("news-monitor-mcp")

BASE_URL = "https://api.worldnewsapi.com"
DEFAULT_TIMEOUT = 30.0
MAX_RESULTS = 100
DEFAULT_RESULTS = 10

SWISS_SOURCE_COUNTRIES = "ch"
DACH_SOURCE_COUNTRIES = "ch,de,at"

CACHE_TTL: dict[str, int] = {
    "search": 1800,
    "headlines": 900,
    "sentiment": 3600,
    "briefing": 3600,
    "article": 86400,
    "sources": 86400,
    "front_pages": 14400,
    "trend": 1800,
    "geo": 1800,
}

DEFAULT_ALERTS_FILE = os.path.expanduser("~/.news-monitor-mcp/alerts.json")
ALERTS_FILE = os.environ.get("NEWS_MONITOR_ALERTS_FILE", DEFAULT_ALERTS_FILE)


class NewsCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str, Any]] = {}
        self._hits = 0
        self._misses = 0

    def _make_key(self, tool_type: str, params: dict[str, Any]) -> str:
        raw = json.dumps({"t": tool_type, "p": params}, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, tool_type: str, params: dict[str, Any]) -> Optional[Any]:
        key = self._make_key(tool_type, params)
        if key not in self._store:
            self._misses += 1
            return None
        timestamp, _, data = self._store[key]
        ttl = CACHE_TTL.get(tool_type, 1800)
        if time.time() - timestamp > ttl:
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return data

    def set(self, tool_type: str, params: dict[str, Any], data: Any) -> None:
        key = self._make_key(tool_type, params)
        self._store[key] = (time.time(), tool_type, data)

    def clear(self, tool_type: Optional[str] = None) -> int:
        if tool_type is None:
            count = len(self._store)
            self._store.clear()
            return count
        keys_to_delete = [k for k, (_, t, _) in self._store.items() if t == tool_type]
        for k in keys_to_delete:
            del self._store[k]
        return len(keys_to_delete)

    def evict_expired(self) -> int:
        now = time.time()
        keys_to_delete = [k for k, (ts, t, _) in self._store.items() if now - ts > CACHE_TTL.get(t, 1800)]
        for k in keys_to_delete:
            del self._store[k]
        return len(keys_to_delete)

    def stats(self) -> dict[str, Any]:
        self.evict_expired()
        total = self._hits + self._misses
        by_type: dict[str, int] = {}
        for _, (_, tool_type, _) in self._store.items():
            by_type[tool_type] = by_type.get(tool_type, 0) + 1
        return {
            "gesamt_eintraege": len(self._store),
            "nach_typ": by_type,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / total:.1%}" if total > 0 else "n/a",
            "api_calls_gespart": self._hits,
            "ttl_sekunden": CACHE_TTL,
        }


class AlertManager:
    def __init__(self, file_path: str = ALERTS_FILE) -> None:
        self._file = file_path
        self._alerts: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._file):
            try:
                with open(self._file, encoding="utf-8") as f:
                    self._alerts = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._alerts = {}

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._file), exist_ok=True)
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(self._alerts, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Alert-Datei konnte nicht gespeichert werden: {e}")

    def create(self, data: dict[str, Any]) -> str:
        alert_id = f"alert_{uuid.uuid4().hex[:8]}"
        self._alerts[alert_id] = {**data, "id": alert_id,
            "created_at": datetime.now().isoformat(),
            "last_checked": None, "last_triggered": None, "trigger_count": 0}
        self._save()
        return alert_id

    def list_all(self) -> list[dict[str, Any]]:
        return list(self._alerts.values())

    def get(self, alert_id: str) -> Optional[dict[str, Any]]:
        return self._alerts.get(alert_id)

    def delete(self, alert_id: str) -> bool:
        if alert_id in self._alerts:
            del self._alerts[alert_id]
            self._save()
            return True
        return False

    def mark_checked(self, alert_id: str, triggered: bool) -> None:
        if alert_id in self._alerts:
            self._alerts[alert_id]["last_checked"] = datetime.now().isoformat()
            if triggered:
                self._alerts[alert_id]["last_triggered"] = datetime.now().isoformat()
                self._alerts[alert_id]["trigger_count"] = self._alerts[alert_id].get("trigger_count", 0) + 1
            self._save()

    def evaluate_condition(self, alert: dict[str, Any], articles: list[dict[str, Any]],
                           avg_sentiment: Optional[float]) -> tuple[bool, str]:
        condition = alert.get("condition_type", "")
        threshold = alert.get("threshold", 0.0)
        keyword = (alert.get("keyword") or "").lower()
        if condition == "sentiment_below":
            if avg_sentiment is not None and avg_sentiment < threshold:
                return True, f"Ø-Sentiment {avg_sentiment:.3f} < Schwellenwert {threshold}"
            s_str = f"{avg_sentiment:.3f}" if avg_sentiment is not None else "n/a"
            return False, f"Ø-Sentiment {s_str} >= {threshold}"
        if condition == "sentiment_above":
            if avg_sentiment is not None and avg_sentiment > threshold:
                return True, f"Ø-Sentiment {avg_sentiment:.3f} > Schwellenwert {threshold}"
            s_str = f"{avg_sentiment:.3f}" if avg_sentiment is not None else "n/a"
            return False, f"Ø-Sentiment {s_str} <= {threshold}"
        if condition == "volume_above":
            count = len(articles)
            if count > int(threshold):
                return True, f"{count} Artikel > Schwellenwert {int(threshold)}"
            return False, f"{count} Artikel <= Schwellenwert {int(threshold)}"
        if condition == "keyword_found":
            matches = [a for a in articles if keyword in (a.get("title") or "").lower()
                       or keyword in (a.get("summary") or "").lower()]
            if matches:
                return True, f"Schluesselwort <<{keyword}>> in {len(matches)} Artikel(n) gefunden"
            return False, f"Schluesselwort <<{keyword}>> nicht gefunden"
        return False, f"Unbekannter Condition-Typ: {condition}"


_cache = NewsCache()
_alert_manager = AlertManager()

mcp = FastMCP(
    "news_monitor_mcp",
    instructions=(
        "News-Monitoring-Server mit 15 Tools via WorldNewsAPI. "
        "9 Monitoring-Tools (Suche, Headlines, Sentiment, Briefing, Artikel, Quellen, Covers, Trends, Geo) "
        "alle mit TTL-Cache. 4 Alert-Tools: erstellen/auflisten/prüfen/löschen. "
        "2 Cache-Tools: Statistiken und leeren. "
        "API-Key: WORLD_NEWS_API_KEY. DACH: source-country=ch,de,at. "
        "Sentiment nur DE/EN. Alerts: news_alert_create dann news_alert_check."
    ),
)

_client: Optional[httpx.AsyncClient] = None

def _get_api_key() -> Optional[str]:
    return os.environ.get("WORLD_NEWS_API_KEY")

def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=BASE_URL, timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": "news-monitor-mcp/0.2.0"})
    return _client

def _check_api_key() -> Optional[str]:
    return _get_api_key()

def _no_key_message(tool_name: str) -> str:
    return (f"Kein API-Key fuer '{tool_name}' konfiguriert.\n"
            "Bitte WORLD_NEWS_API_KEY als Umgebungsvariable setzen.\n"
            "Kostenloser Key: https://worldnewsapi.com/console/")

def _format_article(article: dict[str, Any], include_text: bool = False) -> dict[str, Any]:
    result = {
        "id": article.get("id"), "titel": article.get("title"),
        "zusammenfassung": article.get("summary", ""), "quelle_url": article.get("url"),
        "bild_url": article.get("image"), "veroeffentlicht": article.get("publish_date"),
        "autoren": article.get("authors", []), "kategorie": article.get("category"),
        "sprache": article.get("language"), "quellland": article.get("source_country"),
        "sentiment": article.get("sentiment"),
    }
    if include_text:
        result["volltext"] = article.get("text", "")
    return result

def _sentiment_label(score: Optional[float]) -> str:
    if score is None: return "n/a"
    if score > 0.3: return "positiv"
    if score < -0.3: return "negativ"
    return "neutral"

def _format_articles_markdown(articles: list[dict[str, Any]],
                               include_sentiment: bool = True, include_text: bool = False) -> str:
    if not articles:
        return "Keine Artikel gefunden."
    lines = []
    for i, art in enumerate(articles, 1):
        f = _format_article(art, include_text=include_text)
        s_str = ""
        if include_sentiment and f["sentiment"] is not None:
            score = f["sentiment"]
            s_str = f" | Sentiment: **{_sentiment_label(score)}** ({score:.2f})"
        lines.append(f"\n### {i}. {f['titel']}")
        lines.append(f"📅 {f['veroeffentlicht']} | 🌍 {f['quellland']} | 🏷️ {f['kategorie']}{s_str}")
        if f["zusammenfassung"]:
            lines.append(f"\n{f['zusammenfassung']}")
        lines.append(f"\n🔗 {f['quelle_url']}")
        if include_text and f.get("volltext"):
            preview = f["volltext"][:500] + "..." if len(f["volltext"]) > 500 else f["volltext"]
            lines.append(f"\n> {preview}")
    return "\n".join(lines)

def _handle_api_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 401: return "Fehler: Ungültiger API-Key."
        if e.response.status_code == 402: return "Fehler: API-Kontingent erschöpft."
        if e.response.status_code == 429: return "Fehler: Rate Limit erreicht."
        return f"API-Fehler: HTTP {e.response.status_code}"
    if isinstance(e, httpx.TimeoutException): return "Fehler: Timeout."
    if isinstance(e, httpx.ConnectError): return "Fehler: Keine Verbindung zur WorldNewsAPI."
    return f"Fehler: {type(e).__name__}: {e!s}"

def _calc_avg_sentiment(articles: list[dict[str, Any]]) -> Optional[float]:
    scores = [a["sentiment"] for a in articles if a.get("sentiment") is not None]
    return sum(scores) / len(scores) if scores else None


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"

class SortOrder(str, Enum):
    PUBLISH_TIME = "publish-time"
    RELEVANCE = "relevance"

class AlertConditionType(str, Enum):
    SENTIMENT_BELOW = "sentiment_below"
    SENTIMENT_ABOVE = "sentiment_above"
    VOLUME_ABOVE = "volume_above"
    KEYWORD_FOUND = "keyword_found"

class SearchNewsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    query: str = Field(..., description="Suchbegriff(e)", min_length=1, max_length=500)
    language: Optional[str] = Field(default=None, max_length=10)
    source_country: Optional[str] = Field(default=None, max_length=100)
    earliest_date: Optional[str] = Field(default=None, description="Format YYYY-MM-DD")
    latest_date: Optional[str] = Field(default=None)
    sort: SortOrder = Field(default=SortOrder.RELEVANCE)
    number: int = Field(default=DEFAULT_RESULTS, ge=1, le=MAX_RESULTS)
    include_full_text: bool = Field(default=False)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True, description="Cache verwenden (Standard: True)")

    @field_validator("earliest_date", "latest_date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None: return v
        try: datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e: raise ValueError("Format YYYY-MM-DD erforderlich") from e
        return v

class TopNewsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    source_country: str = Field(default="ch", min_length=2, max_length=5)
    language: str = Field(default="de", min_length=2, max_length=5)
    date: Optional[str] = Field(default=None)
    number: int = Field(default=10, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None: return v
        try: datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e: raise ValueError("Format YYYY-MM-DD erforderlich") from e
        return v

class SentimentMonitorInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    entity: str = Field(..., description="Institution, Person oder Thema", min_length=2, max_length=300)
    language: str = Field(default="de")
    days_back: int = Field(default=30, ge=1, le=365)
    source_country: Optional[str] = Field(default="ch,de,at")
    number: int = Field(default=20, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)

    @field_validator("language")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in ("de", "en"): raise ValueError("Sentiment nur fuer de und en.")
        return v

class RetrieveArticleInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    article_id: int = Field(..., gt=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)

class SearchSourcesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    name: Optional[str] = Field(default=None, max_length=200)
    country: Optional[str] = Field(default=None, max_length=5)
    language: Optional[str] = Field(default=None, max_length=5)
    number: int = Field(default=20, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)

class MediaBriefingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    topics: list[str] = Field(..., min_length=1, max_length=5)
    language: str = Field(default="de")
    days_back: int = Field(default=7, ge=1, le=31)
    source_country: str = Field(default="ch,de,at")
    use_cache: bool = Field(default=True)

    @field_validator("language")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in ("de", "en"): raise ValueError("Fuer Sentiment: de oder en.")
        return v

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v: list[str]) -> list[str]:
        if len(v) > 5: raise ValueError("Max. 5 Themen")
        return v

class FrontPagesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    source_country: str = Field(default="ch", min_length=2, max_length=5)
    source_name: Optional[str] = Field(default=None, max_length=200)
    date: Optional[str] = Field(default=None)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None: return v
        try: datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e: raise ValueError("Format YYYY-MM-DD erforderlich") from e
        return v

class TrendRadarInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    category: str = Field(..., description="z.B. politics, technology, education", min_length=2, max_length=50)
    source_country: str = Field(default="ch")
    language: str = Field(default="de")
    days_back: int = Field(default=7, ge=1, le=30)
    number: int = Field(default=15, ge=1, le=50)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)

class GeoNewsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    location: str = Field(..., description="Ortsname, z.B. Zuerich, Bern, Kanton Zuerich", min_length=2, max_length=200)
    query: Optional[str] = Field(default=None, max_length=300)
    language: str = Field(default="de")
    days_back: int = Field(default=14, ge=1, le=90)
    number: int = Field(default=10, ge=1, le=50)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)

class CreateAlertInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    name: str = Field(..., description="Name des Alerts, z.B. Schulamt Zuerich Negativalert", min_length=2, max_length=200)
    entity: str = Field(..., description="Suchbegriff / Entitaet, z.B. Schulamt Zuerich", min_length=2, max_length=300)
    language: str = Field(default="de")
    source_country: Optional[str] = Field(default="ch,de,at")
    days_back: int = Field(default=7, ge=1, le=90)
    condition_type: AlertConditionType = Field(..., description="sentiment_below | sentiment_above | volume_above | keyword_found")
    threshold: Optional[float] = Field(default=None, description="Schwellenwert fuer sentiment/volume conditions")
    keyword: Optional[str] = Field(default=None, max_length=200, description="Schluesselwort fuer keyword_found")

    @field_validator("language")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in ("de", "en"): raise ValueError("Nur de und en.")
        return v

class CheckAlertsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    alert_id: Optional[str] = Field(default=None, description="Spezifische Alert-ID (leer = alle)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

class DeleteAlertInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    alert_id: str = Field(..., description="Alert-ID aus news_alert_list", min_length=10)

class CacheClearInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    tool_type: Optional[str] = Field(default=None, description="Cache-Typ leeren: search|headlines|sentiment|briefing|article|sources|front_pages|trend|geo. Leer = alles.")


# ---------------------------------------------------------------------------
# Tools – 9 Monitoring Tools (mit Cache)
# ---------------------------------------------------------------------------

@mcp.tool(name="news_search", annotations={"title": "Nachrichtensuche", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def news_search(params: SearchNewsInput) -> str:
    """Volltext-Nachrichtensuche in 150+ Laendern (mit Cache, TTL: 30 Min).

    Args:
        params (SearchNewsInput): query, language, source_country, earliest/latest_date,
            sort, number, include_full_text, use_cache, response_format

    Returns:
        str: Artikel mit Titel, Zusammenfassung, Quelle, Datum und Sentiment.
    """
    api_key = _check_api_key()
    if not api_key: return _no_key_message("news_search")
    cache_params = {"q": params.query, "lang": params.language, "sc": params.source_country,
        "ed": params.earliest_date, "ld": params.latest_date, "sort": params.sort.value, "n": params.number}
    cache_info = ""
    data = None
    if params.use_cache:
        data = _cache.get("search", cache_params)
        if data is not None:
            cache_info = "\n> ℹ️ *Aus Cache (TTL: 30 Min) – `use_cache=False` fuer frische Daten*\n"
    if data is None:
        p: dict[str, Any] = {"api-key": api_key, "text": params.query,
            "number": params.number, "sort": params.sort.value, "sort-direction": "DESC"}
        if params.language: p["language"] = params.language
        if params.source_country: p["source-country"] = params.source_country
        if params.earliest_date: p["earliest-publish-date"] = f"{params.earliest_date} 00:00:00"
        if params.latest_date: p["latest-publish-date"] = f"{params.latest_date} 23:59:59"
        try:
            r = await _get_client().get("/search-news", params=p)
            r.raise_for_status()
            data = r.json()
            if params.use_cache: _cache.set("search", cache_params, data)
        except Exception as e: return _handle_api_error(e)
    articles = data.get("news", [])
    total = data.get("available", 0)
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"total_verfuegbar": total, "zurueckgegeben": len(articles),
            "query": params.query, "cache": bool(cache_info),
            "artikel": [_format_article(a, include_text=params.include_full_text) for a in articles]
        }, ensure_ascii=False, indent=2)
    header = f"## Suchergebnisse: {params.query}\n{cache_info}\n"
    header += f"**{len(articles)} von {total} Treffern**"
    if params.source_country: header += f" | Land: `{params.source_country}`"
    if params.language: header += f" | Sprache: `{params.language}`"
    header += "\n"
    return header + _format_articles_markdown(articles, include_text=params.include_full_text)


@mcp.tool(name="news_top_headlines", annotations={"title": "Top-Schlagzeilen", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def news_top_headlines(params: TopNewsInput) -> str:
    """Top-Schlagzeilen eines Landes (mit Cache, TTL: 15 Min).

    Args:
        params (TopNewsInput): source_country, language, date, number, use_cache, response_format

    Returns:
        str: Geclusterte Top-News nach Quellen-Anzahl gereiht.
    """
    api_key = _check_api_key()
    if not api_key: return _no_key_message("news_top_headlines")
    cache_params = {"sc": params.source_country, "lang": params.language, "date": params.date, "n": params.number}
    cache_info = ""
    data = None
    if params.use_cache:
        data = _cache.get("headlines", cache_params)
        if data is not None: cache_info = "\n> ℹ️ *Aus Cache (TTL: 15 Min)*\n"
    if data is None:
        p: dict[str, Any] = {"api-key": api_key, "source-country": params.source_country,
            "language": params.language, "number": params.number}
        if params.date: p["date"] = params.date
        try:
            r = await _get_client().get("/top-news", params=p)
            r.raise_for_status()
            data = r.json()
            if params.use_cache: _cache.set("headlines", cache_params, data)
        except Exception as e: return _handle_api_error(e)
    clusters = data.get("top_news", [])
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"land": params.source_country, "sprache": params.language,
            "datum": params.date or "heute", "cache": bool(cache_info),
            "cluster": [{"rang": i+1, "artikel": [_format_article(a) for a in c.get("news", [])]}
                        for i, c in enumerate(clusters)]}, ensure_ascii=False, indent=2)
    date_display = params.date or datetime.now().strftime("%Y-%m-%d")
    lines = [f"## Top-Schlagzeilen: {params.source_country.upper()} | {params.language.upper()} | {date_display}\n{cache_info}"]
    for i, cluster in enumerate(clusters, 1):
        arts = cluster.get("news", [])
        if not arts: continue
        top = arts[0]
        lines.append(f"\n### #{i} {top.get('title', 'Kein Titel')}")
        lines.append(f"📅 {top.get('publish_date', 'n/a')} | 🗞️ {len(arts)} Quellen berichten")
        if top.get("summary"): lines.append(f"\n{top['summary']}")
        lines.append(f"\n🔗 {top.get('url', '')}")
    return "\n".join(lines)


@mcp.tool(name="news_sentiment_monitor", annotations={"title": "Sentiment-Monitoring", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True})
async def news_sentiment_monitor(params: SentimentMonitorInput) -> str:
    """Sentiment-Analyse der Medienberichterstattung (Cache-TTL: 60 Min).

    Analysiert die emotionale Tonalitaet der Berichterstattung. Nur DE und EN.

    Args:
        params (SentimentMonitorInput): entity, language (de/en), days_back,
            source_country, number, use_cache, response_format

    Returns:
        str: Sentiment-Auswertung mit Ø-Score, Statistik und Top-Artikeln.
    """
    api_key = _check_api_key()
    if not api_key: return _no_key_message("news_sentiment_monitor")
    latest_dt = datetime.now()
    earliest_dt = latest_dt - timedelta(days=params.days_back)
    cache_params = {"entity": params.entity, "lang": params.language,
        "days": params.days_back, "sc": params.source_country, "n": params.number,
        "ed": earliest_dt.strftime("%Y-%m-%d")}
    cache_info = ""
    data = None
    if params.use_cache:
        data = _cache.get("sentiment", cache_params)
        if data is not None: cache_info = "\n> ℹ️ *Aus Cache (TTL: 60 Min)*\n"
    if data is None:
        p: dict[str, Any] = {"api-key": api_key, "text": params.entity, "language": params.language,
            "number": params.number,
            "earliest-publish-date": earliest_dt.strftime("%Y-%m-%d 00:00:00"),
            "latest-publish-date": latest_dt.strftime("%Y-%m-%d 23:59:59"),
            "sort": "publish-time", "sort-direction": "DESC"}
        if params.source_country: p["source-country"] = params.source_country
        try:
            r = await _get_client().get("/search-news", params=p)
            r.raise_for_status()
            data = r.json()
            if params.use_cache: _cache.set("sentiment", cache_params, data)
        except Exception as e: return _handle_api_error(e)
    articles = data.get("news", [])
    total_available = data.get("available", 0)
    sentiments = [a["sentiment"] for a in articles if a.get("sentiment") is not None]
    positive = [s for s in sentiments if s > 0.1]
    negative = [s for s in sentiments if s < -0.1]
    neutral = [s for s in sentiments if -0.1 <= s <= 0.1]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else None
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"entity": params.entity, "zeitraum_tage": params.days_back,
            "total_verfuegbar": total_available, "analysiert": len(articles), "cache": bool(cache_info),
            "sentiment_statistik": {"durchschnitt": round(avg_sentiment, 3) if avg_sentiment is not None else None,
                "label": _sentiment_label(avg_sentiment), "positiv": len(positive),
                "neutral": len(neutral), "negativ": len(negative)},
            "artikel": [{**_format_article(a), "sentiment_label": _sentiment_label(a.get("sentiment"))} for a in articles]
        }, ensure_ascii=False, indent=2)
    lines = [f"## Sentiment-Monitor: {params.entity}\n{cache_info}"]
    lines.append(f"**Zeitraum:** {earliest_dt.strftime('%d.%m.%Y')} – {latest_dt.strftime('%d.%m.%Y')} ({params.days_back} Tage)\n")
    lines.append(f"**Gefunden:** {total_available} | **Analysiert:** {len(articles)}\n")
    if avg_sentiment is not None:
        label = _sentiment_label(avg_sentiment)
        emoji = "😊" if avg_sentiment > 0.1 else ("😟" if avg_sentiment < -0.1 else "😐")
        lines.append(f"\n### {emoji} Gesamt-Sentiment: **{label}** ({avg_sentiment:.3f})\n")
        lines.append(f"Positiv: **{len(positive)}** | Neutral: **{len(neutral)}** | Negativ: **{len(negative)}**\n")
    else:
        lines.append("\nKeine Sentiment-Daten (nur de/en unterstuetzt)\n")
    if articles:
        sorted_arts = sorted(articles, key=lambda a: a.get("sentiment") or 0)
        top_neg = sorted_arts[:3]
        top_pos = sorted_arts[-3:][::-1]
        if top_neg and (top_neg[0].get("sentiment") or 0) < -0.1:
            lines.append("\n#### Kritischste Berichte")
            lines.append(_format_articles_markdown(top_neg, include_sentiment=True))
        if top_pos and (top_pos[0].get("sentiment") or 0) > 0.1:
            lines.append("\n#### Positivste Berichte")
            lines.append(_format_articles_markdown(top_pos, include_sentiment=True))
    return "\n".join(lines)


@mcp.tool(name="news_media_briefing", annotations={"title": "Medien-Briefing", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True})
async def news_media_briefing(params: MediaBriefingInput) -> str:
    """Multi-Themen-Medien-Briefing fuer GL/KI-Fachgruppe (Cache-TTL: 60 Min pro Thema).

    Args:
        params (MediaBriefingInput): topics (max. 5), language, days_back, source_country, use_cache

    Returns:
        str: Kompaktes Briefing mit Sentiment und Top-3-Artikeln pro Thema.
    """
    api_key = _check_api_key()
    if not api_key: return _no_key_message("news_media_briefing")
    latest_dt = datetime.now()
    earliest_dt = latest_dt - timedelta(days=params.days_back)
    lines = ["# Medien-Briefing\n",
        f"**Zeitraum:** {earliest_dt.strftime('%d.%m.%Y')} – {latest_dt.strftime('%d.%m.%Y')} | "
        f"**Quellen:** {params.source_country} | **Sprache:** {params.language}\n", "---\n"]
    for topic in params.topics:
        cache_params = {"topic": topic, "lang": params.language, "sc": params.source_country,
            "days": params.days_back, "ed": earliest_dt.strftime("%Y-%m-%d")}
        data = None
        if params.use_cache:
            data = _cache.get("briefing", cache_params)
        if data is None:
            p: dict[str, Any] = {"api-key": api_key, "text": topic, "language": params.language,
                "source-country": params.source_country, "number": 5,
                "earliest-publish-date": earliest_dt.strftime("%Y-%m-%d 00:00:00"),
                "latest-publish-date": latest_dt.strftime("%Y-%m-%d 23:59:59"),
                "sort": "publish-time", "sort-direction": "DESC"}
            try:
                r = await _get_client().get("/search-news", params=p)
                r.raise_for_status()
                data = r.json()
                if params.use_cache: _cache.set("briefing", cache_params, data)
            except Exception as e:
                lines.append(f"\n## {topic}\n{_handle_api_error(e)}\n---")
                continue
        articles = data.get("news", [])
        total = data.get("available", 0)
        avg = _calc_avg_sentiment(articles)
        label = _sentiment_label(avg)
        emoji = "😊" if avg and avg > 0.1 else ("😟" if avg and avg < -0.1 else "😐")
        lines.append(f"\n## {emoji} {topic}\n")
        lines.append(f"**{total} Artikel** | Sentiment: **{label}**" + (f" ({avg:.2f})" if avg is not None else "") + "\n")
        if articles:
            for a in articles[:3]:
                lines.append(f"- [{a.get('title', 'Kein Titel')}]({a.get('url', '#')}) ({a.get('publish_date', 'n/a')[:10]})")
        else:
            lines.append("_Keine Artikel im Zeitraum._")
        lines.append("\n---")
    return "\n".join(lines)


@mcp.tool(name="news_retrieve_article", annotations={"title": "Artikel abrufen", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def news_retrieve_article(params: RetrieveArticleInput) -> str:
    """Vollstaendigen Artikel per ID abrufen (Cache-TTL: 24h).

    Args:
        params (RetrieveArticleInput): article_id, use_cache, response_format

    Returns:
        str: Volltext, Metadaten und Sentiment.
    """
    api_key = _check_api_key()
    if not api_key: return _no_key_message("news_retrieve_article")
    cache_params = {"id": params.article_id}
    data = None
    if params.use_cache: data = _cache.get("article", cache_params)
    if data is None:
        try:
            r = await _get_client().get("/retrieve-news", params={"api-key": api_key, "ids": params.article_id})
            r.raise_for_status()
            data = r.json()
            if params.use_cache: _cache.set("article", cache_params, data)
        except Exception as e: return _handle_api_error(e)
    news_list = data.get("news", [])
    if not news_list: return f"Kein Artikel mit ID {params.article_id} gefunden."
    article = news_list[0]
    if params.response_format == ResponseFormat.JSON:
        return json.dumps(_format_article(article, include_text=True), ensure_ascii=False, indent=2)
    f = _format_article(article, include_text=True)
    s_str = ""
    if f["sentiment"] is not None:
        score = f["sentiment"]
        s_str = f"\n**Sentiment:** {_sentiment_label(score)} ({score:.3f})"
    return (f"## {f['titel']}\n\n**Veroeffentlicht:** {f['veroeffentlicht']}  \n"
        f"**Kategorie:** {f['kategorie']} | **Sprache:** {f['sprache']} | **Land:** {f['quellland']}"
        f"{s_str}\n\n**Quelle:** {f['quelle_url']}\n\n---\n\n{f.get('volltext', '')}")


@mcp.tool(name="news_search_sources", annotations={"title": "Nachrichtenquellen suchen", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def news_search_sources(params: SearchSourcesInput) -> str:
    """Verfuegbare Nachrichtenquellen suchen (Cache-TTL: 24h).

    Args:
        params (SearchSourcesInput): name, country, language, number, use_cache, response_format

    Returns:
        str: Liste verfuegbarer Quellen mit URL und Metadaten.
    """
    api_key = _check_api_key()
    if not api_key: return _no_key_message("news_search_sources")
    cache_params = {"name": params.name, "country": params.country, "lang": params.language, "n": params.number}
    data = None
    if params.use_cache: data = _cache.get("sources", cache_params)
    if data is None:
        p: dict[str, Any] = {"api-key": api_key, "number": params.number}
        if params.name: p["name"] = params.name
        if params.country: p["source-country"] = params.country
        if params.language: p["language"] = params.language
        try:
            r = await _get_client().get("/search-news-sources", params=p)
            r.raise_for_status()
            data = r.json()
            if params.use_cache: _cache.set("sources", cache_params, data)
        except Exception as e: return _handle_api_error(e)
    sources = data.get("news_sources", [])
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"anzahl": len(sources), "quellen": sources}, ensure_ascii=False, indent=2)
    if not sources: return "Keine Quellen gefunden."
    lines = [f"## Nachrichtenquellen ({len(sources)} gefunden)\n"]
    for src in sources:
        lines.append(f"- **{src.get('name', 'n/a')}** – {src.get('url', 'n/a')} | 🌍 {src.get('source_country', 'n/a')} | 🌐 {src.get('language', 'n/a')}")
    return "\n".join(lines)


@mcp.tool(name="news_front_pages", annotations={"title": "Zeitungscovers", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def news_front_pages(params: FrontPagesInput) -> str:
    """Digitale Zeitungscovers von 6000+ Publikationen (Cache-TTL: 4h).

    Args:
        params (FrontPagesInput): source_country, source_name, date, use_cache, response_format

    Returns:
        str: Titelseiten-Uebersicht mit Bild-URLs.
    """
    api_key = _check_api_key()
    if not api_key: return _no_key_message("news_front_pages")
    cache_params = {"sc": params.source_country, "sn": params.source_name, "date": params.date}
    data = None
    if params.use_cache: data = _cache.get("front_pages", cache_params)
    if data is None:
        p: dict[str, Any] = {"api-key": api_key, "source-country": params.source_country}
        if params.source_name: p["source-name"] = params.source_name
        if params.date: p["date"] = params.date
        try:
            r = await _get_client().get("/retrieve-front-page", params=p)
            r.raise_for_status()
            data = r.json()
            if params.use_cache: _cache.set("front_pages", cache_params, data)
        except Exception as e: return _handle_api_error(e)
    front_pages = data.get("front_pages", [])
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"land": params.source_country, "anzahl": len(front_pages), "titelseiten": front_pages}, ensure_ascii=False, indent=2)
    if not front_pages: return "Keine Titelseiten gefunden."
    date_display = params.date or datetime.now().strftime("%Y-%m-%d")
    lines = [f"## Zeitungscovers: {params.source_country.upper()} | {date_display}\n"]
    for fp in front_pages:
        name = fp.get("name", "n/a")
        lines.append(f"\n### {name}")
        lines.append(f"📅 {fp.get('date', 'n/a')} | 🔗 {fp.get('url', 'n/a')}")
        if fp.get("image"): lines.append(f"\n![{name}]({fp['image']})")
    return "\n".join(lines)


@mcp.tool(name="news_trend_radar", annotations={"title": "Trend-Radar", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True})
async def news_trend_radar(params: TrendRadarInput) -> str:
    """Nachrichtentrends in einer Kategorie (Cache-TTL: 30 Min).

    Args:
        params (TrendRadarInput): category, source_country, language, days_back, number, use_cache, response_format

    Returns:
        str: Trending-Themen und Artikel mit Sentiment.
    """
    api_key = _check_api_key()
    if not api_key: return _no_key_message("news_trend_radar")
    latest_dt = datetime.now()
    earliest_dt = latest_dt - timedelta(days=params.days_back)
    cache_params = {"cat": params.category, "sc": params.source_country, "lang": params.language,
        "days": params.days_back, "n": params.number, "ed": earliest_dt.strftime("%Y-%m-%d")}
    data = None
    if params.use_cache: data = _cache.get("trend", cache_params)
    if data is None:
        p: dict[str, Any] = {"api-key": api_key, "source-country": params.source_country,
            "language": params.language, "categories": params.category, "number": params.number,
            "earliest-publish-date": earliest_dt.strftime("%Y-%m-%d 00:00:00"),
            "latest-publish-date": latest_dt.strftime("%Y-%m-%d 23:59:59"),
            "sort": "publish-time", "sort-direction": "DESC"}
        try:
            r = await _get_client().get("/search-news", params=p)
            r.raise_for_status()
            data = r.json()
            if params.use_cache: _cache.set("trend", cache_params, data)
        except Exception as e: return _handle_api_error(e)
    articles = data.get("news", [])
    total = data.get("available", 0)
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"kategorie": params.category, "land": params.source_country,
            "zeitraum_tage": params.days_back, "total": total,
            "artikel": [_format_article(a) for a in articles]}, ensure_ascii=False, indent=2)
    lines = [f"## Trend-Radar: Kategorie {params.category}\n",
        f"**Land:** {params.source_country} | **Sprache:** {params.language} | **Zeitraum:** {params.days_back} Tage | **{total} Artikel**\n"]
    lines.append(_format_articles_markdown(articles, include_sentiment=True))
    return "\n".join(lines)


@mcp.tool(name="news_geo_search", annotations={"title": "Geo-Suche", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def news_geo_search(params: GeoNewsInput) -> str:
    """Standortspezifische Nachrichtensuche (Cache-TTL: 30 Min).

    Args:
        params (GeoNewsInput): location, query, language, days_back, number, use_cache, response_format

    Returns:
        str: Geolokalisierte Nachrichtenartikel mit Sentiment.
    """
    api_key = _check_api_key()
    if not api_key: return _no_key_message("news_geo_search")
    search_text = f"{params.location} {params.query}" if params.query else params.location
    latest_dt = datetime.now()
    earliest_dt = latest_dt - timedelta(days=params.days_back)
    cache_params = {"loc": params.location, "q": params.query, "lang": params.language,
        "days": params.days_back, "n": params.number, "ed": earliest_dt.strftime("%Y-%m-%d")}
    data = None
    if params.use_cache: data = _cache.get("geo", cache_params)
    if data is None:
        p: dict[str, Any] = {"api-key": api_key, "text": search_text, "language": params.language,
            "source-country": "ch,de,at,fr,it", "number": params.number,
            "earliest-publish-date": earliest_dt.strftime("%Y-%m-%d 00:00:00"),
            "latest-publish-date": latest_dt.strftime("%Y-%m-%d 23:59:59"),
            "sort": "publish-time", "sort-direction": "DESC"}
        try:
            r = await _get_client().get("/search-news", params=p)
            r.raise_for_status()
            data = r.json()
            if params.use_cache: _cache.set("geo", cache_params, data)
        except Exception as e: return _handle_api_error(e)
    articles = data.get("news", [])
    total = data.get("available", 0)
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"ort": params.location, "zusatzsuche": params.query,
            "total": total, "artikel": [_format_article(a) for a in articles]}, ensure_ascii=False, indent=2)
    header = f"## Geo-News: {params.location}"
    if params.query: header += f" + {params.query}"
    header += f"\n\n**{total} Artikel** in den letzten {params.days_back} Tagen\n"
    return header + _format_articles_markdown(articles, include_sentiment=True)


# ---------------------------------------------------------------------------
# Tools – 4 Alert-Tools
# ---------------------------------------------------------------------------

@mcp.tool(name="news_alert_create", annotations={"title": "Alert erstellen", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False})
async def news_alert_create(params: CreateAlertInput) -> str:
    """Erstellt einen neuen News-Alert fuer automatisches Monitoring.

    Alerts werden persistent gespeichert und ueberleben Server-Neustarts.
    news_alert_check prueft alle Alerts gegen aktuelle Daten.

    Condition-Typen:
      sentiment_below  – Alarm wenn Ø-Sentiment < threshold (z.B. -0.2)
      sentiment_above  – Alarm wenn Ø-Sentiment > threshold (z.B. 0.5)
      volume_above     – Alarm wenn Artikelanzahl > threshold (z.B. 50)
      keyword_found    – Alarm wenn keyword in Titeln/Zusammenfassungen

    Args:
        params (CreateAlertInput): name, entity, language, source_country, days_back,
            condition_type, threshold, keyword

    Returns:
        str: Bestaetigung mit der neuen Alert-ID.
    """
    if params.condition_type in (AlertConditionType.SENTIMENT_BELOW, AlertConditionType.SENTIMENT_ABOVE,
                                   AlertConditionType.VOLUME_ABOVE):
        if params.threshold is None:
            return f"threshold ist fuer condition_type={params.condition_type.value} erforderlich."
    if params.condition_type == AlertConditionType.KEYWORD_FOUND:
        if not params.keyword:
            return "keyword ist fuer condition_type=keyword_found erforderlich."
    alert_id = _alert_manager.create({
        "name": params.name, "entity": params.entity, "language": params.language,
        "source_country": params.source_country, "days_back": params.days_back,
        "condition_type": params.condition_type.value, "threshold": params.threshold,
        "keyword": params.keyword})
    condition_desc = {"sentiment_below": f"Ø-Sentiment < {params.threshold}",
        "sentiment_above": f"Ø-Sentiment > {params.threshold}",
        "volume_above": f"Artikelanzahl > {int(params.threshold or 0)}",
        "keyword_found": f"Schluesselwort {params.keyword} gefunden"
    }.get(params.condition_type.value, params.condition_type.value)
    return (f"Alert erstellt: **{params.name}**\n\n"
        f"- **ID:** `{alert_id}`\n- **Entitaet:** {params.entity}\n"
        f"- **Bedingung:** {condition_desc}\n"
        f"- **Zeitfenster:** {params.days_back} Tage | **Quellen:** {params.source_country}\n\n"
        f"news_alert_check aufrufen um den Alert zu pruefen.")


@mcp.tool(name="news_alert_list", annotations={"title": "Alerts auflisten", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})
async def news_alert_list() -> str:
    """Listet alle konfigurierten News-Alerts mit Status.

    Returns:
        str: Alle Alerts mit ID, Bedingung, letzter Pruefung und Trigger-Count.
             Kein API-Call – liest nur aus der lokalen Alert-Datei.
    """
    alerts = _alert_manager.list_all()
    if not alerts:
        return "Keine Alerts konfiguriert.\n\nMit news_alert_create einen neuen Alert erstellen."
    lines = [f"## Konfigurierte Alerts ({len(alerts)})\n"]
    for a in alerts:
        condition_desc = {"sentiment_below": f"Sentiment < {a.get('threshold')}",
            "sentiment_above": f"Sentiment > {a.get('threshold')}",
            "volume_above": f"Artikel > {a.get('threshold')}",
            "keyword_found": f"Keyword {a.get('keyword', '?')}",
        }.get(a.get("condition_type", ""), a.get("condition_type", "?"))
        last_triggered = a.get("last_triggered") or "–"
        last_checked = a.get("last_checked") or "–"
        trigger_count = a.get("trigger_count", 0)
        status_emoji = "🔕" if trigger_count == 0 else "🔔"
        lines.append(f"\n### {status_emoji} {a.get('name', 'Unbenannt')}")
        lines.append(f"**ID:** `{a['id']}` | **Entitaet:** {a.get('entity')} | **Bedingung:** {condition_desc}")
        lines.append(f"**Zeitfenster:** {a.get('days_back')} Tage | **Quellen:** {a.get('source_country')} | **Sprache:** {a.get('language')}")
        lines.append(f"**Letzte Pruefung:** {last_checked} | **Letzter Alarm:** {last_triggered} | **Ausloesungen:** {trigger_count}")
    lines.append(f"\n---\n*Alerts gespeichert in: `{ALERTS_FILE}`*")
    return "\n".join(lines)


@mcp.tool(name="news_alert_check", annotations={"title": "Alerts pruefen", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True})
async def news_alert_check(params: CheckAlertsInput) -> str:
    """Prueft alle (oder einen spezifischen) Alert gegen aktuelle Nachrichtendaten.

    Pro Alert 1 API-Call. Kein Cache – Alert-Checks verwenden immer aktuelle Daten.
    Ergebnisse (last_checked, trigger_count) werden im Alert-File persistiert.

    Args:
        params (CheckAlertsInput): alert_id (leer = alle), response_format

    Returns:
        str: Pruefergebnis aller Alerts mit Triggered/OK Status.
    """
    api_key = _check_api_key()
    if not api_key: return _no_key_message("news_alert_check")
    alerts_to_check = ([_alert_manager.get(params.alert_id)] if params.alert_id
                       else _alert_manager.list_all())
    alerts_to_check = [a for a in alerts_to_check if a is not None]
    if not alerts_to_check:
        return ("Keine Alerts zu pruefen.\n" +
            (f"Alert-ID {params.alert_id} nicht gefunden." if params.alert_id else
             "Mit news_alert_create einen Alert erstellen."))
    results = []
    for alert in alerts_to_check:
        latest_dt = datetime.now()
        earliest_dt = latest_dt - timedelta(days=alert.get("days_back", 7))
        p: dict[str, Any] = {"api-key": api_key, "text": alert["entity"],
            "language": alert.get("language", "de"), "number": 20,
            "earliest-publish-date": earliest_dt.strftime("%Y-%m-%d 00:00:00"),
            "latest-publish-date": latest_dt.strftime("%Y-%m-%d 23:59:59"),
            "sort": "publish-time", "sort-direction": "DESC"}
        if alert.get("source_country"): p["source-country"] = alert["source_country"]
        try:
            r = await _get_client().get("/search-news", params=p)
            r.raise_for_status()
            data = r.json()
            articles = data.get("news", [])
            avg_sentiment = _calc_avg_sentiment(articles)
            triggered, reason = _alert_manager.evaluate_condition(alert, articles, avg_sentiment)
        except Exception as e:
            results.append({"alert": alert, "triggered": False,
                "reason": f"API-Fehler: {_handle_api_error(e)}", "articles_count": 0, "avg_sentiment": None})
            _alert_manager.mark_checked(alert["id"], triggered=False)
            continue
        _alert_manager.mark_checked(alert["id"], triggered=triggered)
        results.append({"alert": alert, "triggered": triggered, "reason": reason,
            "articles_count": len(articles), "avg_sentiment": avg_sentiment, "top_articles": articles[:3]})
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"geprueft": len(results),
            "ausgeloest": sum(1 for r in results if r["triggered"]),
            "ergebnisse": [{"id": r["alert"]["id"], "name": r["alert"]["name"],
                "triggered": r["triggered"], "reason": r["reason"],
                "artikel_anzahl": r["articles_count"],
                "avg_sentiment": round(r["avg_sentiment"], 3) if r["avg_sentiment"] is not None else None}
                for r in results]}, ensure_ascii=False, indent=2)
    triggered_count = sum(1 for r in results if r["triggered"])
    lines = [f"## Alert-Check: {len(results)} geprueft | {triggered_count} ausgeloest\n",
        f"*Zeitpunkt: {datetime.now().strftime('%d.%m.%Y %H:%M')}*\n"]
    for result in sorted(results, key=lambda r: r["triggered"], reverse=True):
        a = result["alert"]
        triggered = result["triggered"]
        reason = result["reason"]
        avg = result.get("avg_sentiment")
        count = result.get("articles_count", 0)
        icon = "🚨" if triggered else "✅"
        status = "**AUSGELOEST**" if triggered else "OK"
        lines.append(f"\n### {icon} {a['name']} — {status}")
        lines.append(f"**ID:** `{a['id']}` | **Entitaet:** {a['entity']} | **Bedingung:** {reason}")
        lines.append(f"**Artikel:** {count} | **Ø-Sentiment:** {f'{avg:.3f}' if avg is not None else 'n/a'} ({_sentiment_label(avg)})")
        if triggered and result.get("top_articles"):
            lines.append("\n**Top-Artikel:**")
            for art in result["top_articles"]:
                s = art.get("sentiment")
                s_str = f" ({s:.2f})" if s is not None else ""
                lines.append(f"- [{art.get('title', 'n/a')}]({art.get('url', '#')}){s_str}")
    return "\n".join(lines)


@mcp.tool(name="news_alert_delete", annotations={"title": "Alert loeschen", "readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False})
async def news_alert_delete(params: DeleteAlertInput) -> str:
    """Loescht einen konfigurierten Alert permanent.

    Args:
        params (DeleteAlertInput): alert_id aus news_alert_list

    Returns:
        str: Bestaetigung oder Fehlermeldung.
    """
    alert = _alert_manager.get(params.alert_id)
    if alert is None:
        return f"Alert {params.alert_id} nicht gefunden.\nnews_alert_list zum Anzeigen aller Alert-IDs."
    name = alert.get("name", "Unbekannt")
    if _alert_manager.delete(params.alert_id):
        return f"Alert **{name}** (`{params.alert_id}`) geloescht.\nVerbleibende Alerts: {len(_alert_manager.list_all())}"
    return f"Fehler beim Loeschen von Alert {params.alert_id}."


# ---------------------------------------------------------------------------
# Tools – 2 Cache-Tools
# ---------------------------------------------------------------------------

@mcp.tool(name="news_cache_stats", annotations={"title": "Cache-Statistiken", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})
async def news_cache_stats() -> str:
    """Cache-Statistiken: Trefferquote, gespeicherte Eintraege, gesparte API-Calls.

    Returns:
        str: Cache-Uebersicht mit Hit-Rate, Eintraegen nach Typ und TTL-Konfiguration.
    """
    stats = _cache.stats()
    total_calls = stats["hits"] + stats["misses"]
    lines = ["## Cache-Statistiken\n",
        f"**Eintraege gesamt:** {stats['gesamt_eintraege']} | **Hit-Rate:** {stats['hit_rate']} | "
        f"**API-Calls gespart:** {stats['api_calls_gespart']}\n",
        f"**Hits:** {stats['hits']} | **Misses:** {stats['misses']} | **Total Abfragen:** {total_calls}\n"]
    if stats["nach_typ"]:
        lines.append("\n### Eintraege nach Typ\n")
        for typ, count in sorted(stats["nach_typ"].items()):
            ttl = CACHE_TTL.get(typ, 0)
            ttl_str = f"{ttl // 60} Min" if ttl < 3600 else f"{ttl // 3600} h"
            lines.append(f"- **{typ}:** {count} Eintraege (TTL: {ttl_str})")
    lines.append("\n### TTL-Konfiguration\n")
    for typ, ttl in CACHE_TTL.items():
        ttl_str = f"{ttl // 60} Min" if ttl < 3600 else f"{ttl // 3600} h"
        lines.append(f"- `{typ}`: {ttl_str}")
    lines.append("\n---\n*Cache ist In-Memory – wird bei Server-Neustart zurueckgesetzt.*")
    return "\n".join(lines)


@mcp.tool(name="news_cache_clear", annotations={"title": "Cache leeren", "readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False})
async def news_cache_clear(params: CacheClearInput) -> str:
    """Leert den Cache (vollstaendig oder fuer einen spezifischen Tool-Typ).

    Args:
        params (CacheClearInput): tool_type (leer = alles leeren)

    Returns:
        str: Anzahl geloeschter Cache-Eintraege.
    """
    if params.tool_type:
        if params.tool_type not in CACHE_TTL:
            valid = ", ".join(f"'{k}'" for k in CACHE_TTL)
            return f"Unbekannter Tool-Typ '{params.tool_type}'. Erlaubt: {valid}"
        count = _cache.clear(params.tool_type)
        return f"Cache fuer `{params.tool_type}` geleert: {count} Eintraege entfernt."
    count = _cache.clear()
    return f"Gesamter Cache geleert: {count} Eintraege entfernt."


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    """Startet den News Monitor MCP Server."""
    import argparse
    parser = argparse.ArgumentParser(description="News Monitor MCP Server v0.2.0")
    parser.add_argument("--http", action="store_true", help="HTTP-Server statt stdio")
    parser.add_argument("--port", type=int, default=8000, help="HTTP-Port (Standard: 8000)")
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port)
    else:
        mcp.run()

if __name__ == "__main__":
    main()
