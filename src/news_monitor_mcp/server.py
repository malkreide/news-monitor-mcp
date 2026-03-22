"""News Monitor MCP Server – 9 Tools für globales News-Monitoring.

MCP Server für globale Nachrichtenrecherche und Medienmonitoring via WorldNewsAPI.
Unterstützt Volltextsuche, Sentiment-Analyse (Deutsch/Englisch), Top-Schlagzeilen,
Zeitungscovers, Entity-basierte Suche und Quellen-Management.

Metapher: Stell dir vor, du hast einen persönlichen Medienspiegel-Agenten,
der 150+ Länder in 50+ Sprachen gleichzeitig beobachtet – und dir nicht nur
berichtet WAS passiert, sondern auch WIE darüber gesprochen wird (Sentiment).

API key required: Kostenloser Key via https://worldnewsapi.com/console/
Set environment variable: WORLD_NEWS_API_KEY

Anchor Demo (Schulamt):
  "Zeige mir alle Berichte über das Schulamt Zürich der letzten 30 Tage,
   sortiert nach Sentiment."
"""

import json
import logging
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger("news-monitor-mcp")

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

BASE_URL = "https://api.worldnewsapi.com"
DEFAULT_TIMEOUT = 30.0
MAX_RESULTS = 100
DEFAULT_RESULTS = 10

# Schweizer Quellenländer für Standardabfragen
SWISS_SOURCE_COUNTRIES = "ch"
DACH_SOURCE_COUNTRIES = "ch,de,at"

# ---------------------------------------------------------------------------
# Server-Initialisierung
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "news_monitor_mcp",
    instructions=(
        "News-Monitoring-Server mit 9 Tools via WorldNewsAPI. "
        "Unterstützt Volltextsuche in 150+ Ländern / 50+ Sprachen, "
        "Sentiment-Analyse auf Deutsch und Englisch, Top-Schlagzeilen "
        "nach Land/Kategorie, Zeitungscovers und Entity-basierte Suche. "
        "Ideal für Medienmonitoring, Reputationsanalyse und Themen-Radar. "
        "API-Key erforderlich: WORLD_NEWS_API_KEY als Umgebungsvariable setzen. "
        "Tipp: Für Schweizer Institutionen source-country='ch' oder 'ch,de,at' verwenden. "
        "Sentiment-Werte: negativ < 0 < positiv (nur DE und EN unterstützt)."
    ),
)


# ---------------------------------------------------------------------------
# HTTP-Client (lazy initialization)
# ---------------------------------------------------------------------------

_client: Optional[httpx.AsyncClient] = None


def _get_api_key() -> Optional[str]:
    """Liest den API-Key aus der Umgebungsvariable."""
    return os.environ.get("WORLD_NEWS_API_KEY")


def _get_client() -> httpx.AsyncClient:
    """Lazy Initialization des HTTP-Clients."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": "news-monitor-mcp/0.1.0"},
        )
    return _client


def _check_api_key() -> Optional[str]:
    """Prüft ob API-Key vorhanden. Gibt Key zurück oder None."""
    return _get_api_key()


def _no_key_message(tool_name: str) -> str:
    """Standardmeldung wenn kein API-Key konfiguriert ist."""
    return (
        f"⚠️ Kein API-Key für '{tool_name}' konfiguriert.\n"
        "Bitte WORLD_NEWS_API_KEY als Umgebungsvariable setzen.\n"
        "Kostenloser Key unter: https://worldnewsapi.com/console/"
    )


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _format_article(article: dict[str, Any], include_text: bool = False) -> dict[str, Any]:
    """Formatiert einen Artikel-Dict für einheitliche Ausgabe."""
    result = {
        "id": article.get("id"),
        "titel": article.get("title"),
        "zusammenfassung": article.get("summary", ""),
        "quelle_url": article.get("url"),
        "bild_url": article.get("image"),
        "veroeffentlicht": article.get("publish_date"),
        "autoren": article.get("authors", []),
        "kategorie": article.get("category"),
        "sprache": article.get("language"),
        "quellland": article.get("source_country"),
        "sentiment": article.get("sentiment"),
    }
    if include_text:
        result["volltext"] = article.get("text", "")
    return result


def _sentiment_label(score: Optional[float]) -> str:
    """Übersetzt Sentiment-Score in ein lesbares Label."""
    if score is None:
        return "n/a"
    if score > 0.3:
        return "positiv"
    if score < -0.3:
        return "negativ"
    return "neutral"


def _format_articles_markdown(
    articles: list[dict[str, Any]],
    include_sentiment: bool = True,
    include_text: bool = False,
) -> str:
    """Formatiert eine Liste von Artikeln als Markdown."""
    if not articles:
        return "Keine Artikel gefunden."

    lines = []
    for i, art in enumerate(articles, 1):
        formatted = _format_article(art, include_text=include_text)
        sentiment_str = ""
        if include_sentiment and formatted["sentiment"] is not None:
            score = formatted["sentiment"]
            label = _sentiment_label(score)
            sentiment_str = f" | Sentiment: **{label}** ({score:.2f})"

        lines.append(f"\n### {i}. {formatted['titel']}")
        lines.append(
            f"📅 {formatted['veroeffentlicht']} | 🌍 {formatted['quellland']} "
            f"| 🏷️ {formatted['kategorie']}{sentiment_str}"
        )
        if formatted["zusammenfassung"]:
            lines.append(f"\n{formatted['zusammenfassung']}")
        lines.append(f"\n🔗 {formatted['quelle_url']}")
        if include_text and formatted.get("volltext"):
            preview = formatted["volltext"][:500] + "..." if len(formatted["volltext"]) > 500 else formatted["volltext"]
            lines.append(f"\n> {preview}")

    return "\n".join(lines)


def _handle_api_error(e: Exception) -> str:
    """Einheitliche Fehlerbehandlung für alle Tools."""
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 401:
            return "❌ Fehler: Ungültiger API-Key. Bitte WORLD_NEWS_API_KEY prüfen."
        if e.response.status_code == 402:
            return "❌ Fehler: API-Kontingent erschöpft. Bitte Plan upgraden oder warten."
        if e.response.status_code == 429:
            return "❌ Fehler: Rate Limit erreicht. Bitte kurz warten und nochmals versuchen."
        if e.response.status_code == 404:
            return "❌ Fehler: Ressource nicht gefunden."
        return f"❌ API-Fehler: HTTP {e.response.status_code} – {e.response.text[:200]}"
    if isinstance(e, httpx.TimeoutException):
        return "❌ Fehler: Zeitüberschreitung (Timeout). Bitte nochmals versuchen."
    if isinstance(e, httpx.ConnectError):
        return "❌ Fehler: Keine Verbindung zur WorldNewsAPI. Internetverbindung prüfen."
    return f"❌ Unerwarteter Fehler: {type(e).__name__}: {e!s}"


# ---------------------------------------------------------------------------
# Pydantic-Modelle für alle Tools
# ---------------------------------------------------------------------------


class ResponseFormat(str, Enum):
    """Ausgabeformat für Tool-Antworten."""

    MARKDOWN = "markdown"
    JSON = "json"


class SortOrder(str, Enum):
    """Sortiermöglichkeiten für Nachrichtensuche."""

    PUBLISH_TIME = "publish-time"
    RELEVANCE = "relevance"


class SearchNewsInput(BaseModel):
    """Eingabeparameter für die Nachrichtensuche."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: str = Field(
        ...,
        description="Suchbegriff(e). Unterstützt Anführungszeichen für exakte Phrasen, z.B. '\"Schulamt Zürich\"'",
        min_length=1,
        max_length=500,
    )
    language: Optional[str] = Field(
        default=None,
        description="Sprache als ISO-Code, z.B. 'de' für Deutsch, 'en' für Englisch, 'fr' für Französisch",
        max_length=10,
    )
    source_country: Optional[str] = Field(
        default=None,
        description="Quellland(er) als kommagetrennte ISO-Codes, z.B. 'ch' für Schweiz, 'ch,de,at' für DACH",
        max_length=100,
    )
    earliest_date: Optional[str] = Field(
        default=None,
        description="Frühestes Veröffentlichungsdatum im Format 'YYYY-MM-DD', z.B. '2024-01-01'",
    )
    latest_date: Optional[str] = Field(
        default=None,
        description="Spätestes Veröffentlichungsdatum im Format 'YYYY-MM-DD', z.B. '2024-12-31'",
    )
    sort: SortOrder = Field(
        default=SortOrder.RELEVANCE,
        description="Sortierung: 'relevance' nach Relevanz, 'publish-time' nach Datum (erfordert Datumsangaben)",
    )
    number: int = Field(
        default=DEFAULT_RESULTS,
        description=f"Anzahl Ergebnisse (1–{MAX_RESULTS})",
        ge=1,
        le=MAX_RESULTS,
    )
    include_full_text: bool = Field(
        default=False,
        description="Volltext der Artikel einschliessen (erhöht Antwortgrösse erheblich)",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' für lesbare Darstellung, 'json' für maschinelle Verarbeitung",
    )

    @field_validator("earliest_date", "latest_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError("Datum muss im Format 'YYYY-MM-DD' sein, z.B. '2024-01-15'") from e
        return v


class TopNewsInput(BaseModel):
    """Eingabeparameter für Top-Schlagzeilen."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    source_country: str = Field(
        default="ch",
        description="Quellland als ISO-Code, z.B. 'ch' (Schweiz), 'de' (Deutschland), 'us' (USA)",
        min_length=2,
        max_length=5,
    )
    language: str = Field(
        default="de",
        description="Sprache als ISO-Code, z.B. 'de', 'en', 'fr', 'it'",
        min_length=2,
        max_length=5,
    )
    date: Optional[str] = Field(
        default=None,
        description="Datum im Format 'YYYY-MM-DD'. Leer lassen für heute.",
    )
    number: int = Field(
        default=10,
        description="Anzahl Top-News (1–100)",
        ge=1,
        le=100,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' oder 'json'",
    )

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError("Datum muss im Format 'YYYY-MM-DD' sein") from e
        return v


class SentimentMonitorInput(BaseModel):
    """Eingabeparameter für Sentiment-Monitoring eines Themas oder einer Institution."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    entity: str = Field(
        ...,
        description="Name der Institution, Person oder des Themas, z.B. 'Schulamt Zürich', 'Volksschule', 'KI in der Bildung'",
        min_length=2,
        max_length=300,
    )
    language: str = Field(
        default="de",
        description="Sprache für Sentiment-Analyse: 'de' (Deutsch) oder 'en' (Englisch) – nur diese zwei unterstützt",
    )
    days_back: int = Field(
        default=30,
        description="Zeitraum in Tagen rückwirkend (1–365)",
        ge=1,
        le=365,
    )
    source_country: Optional[str] = Field(
        default="ch,de,at",
        description="Quellländer, z.B. 'ch,de,at' für DACH-Raum",
    )
    number: int = Field(
        default=20,
        description="Anzahl Artikel für die Analyse (1–100)",
        ge=1,
        le=100,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' oder 'json'",
    )

    @field_validator("language")
    @classmethod
    def validate_sentiment_language(cls, v: str) -> str:
        if v not in ("de", "en"):
            raise ValueError(
                "Sentiment-Analyse ist nur für 'de' (Deutsch) und 'en' (Englisch) verfügbar."
            )
        return v


class RetrieveArticleInput(BaseModel):
    """Eingabeparameter für das Abrufen eines einzelnen Artikels."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    article_id: int = Field(
        ...,
        description="Artikel-ID aus vorherigen Suchergebnissen (z.B. 206030983)",
        gt=0,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' oder 'json'",
    )


class SearchSourcesInput(BaseModel):
    """Eingabeparameter für die Quellen-Suche."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    name: Optional[str] = Field(
        default=None,
        description="Teilname der Nachrichtenquelle, z.B. 'NZZ', 'Tages-Anzeiger', 'SRF'",
        max_length=200,
    )
    country: Optional[str] = Field(
        default=None,
        description="Land der Quelle als ISO-Code, z.B. 'ch', 'de'",
        max_length=5,
    )
    language: Optional[str] = Field(
        default=None,
        description="Sprache der Quelle, z.B. 'de', 'fr'",
        max_length=5,
    )
    number: int = Field(
        default=20,
        description="Anzahl Ergebnisse (1–100)",
        ge=1,
        le=100,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' oder 'json'",
    )


class MediaBriefingInput(BaseModel):
    """Eingabeparameter für das wöchentliche Medien-Briefing."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    topics: list[str] = Field(
        ...,
        description="Liste von Themen/Entitäten für das Briefing, z.B. ['Volksschule Zürich', 'KI Bildung', 'Schuldigitalisierung']",
        min_length=1,
        max_length=5,
    )
    language: str = Field(
        default="de",
        description="Sprache: 'de' oder 'en' (für Sentiment-Analyse)",
    )
    days_back: int = Field(
        default=7,
        description="Zeitraum in Tagen (1–31 für wöchentlich/monatlich)",
        ge=1,
        le=31,
    )
    source_country: str = Field(
        default="ch,de,at",
        description="Quellländer, z.B. 'ch,de,at' für DACH-Raum",
    )

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in ("de", "en"):
            raise ValueError("Für Sentiment muss Sprache 'de' oder 'en' sein.")
        return v

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v: list[str]) -> list[str]:
        if len(v) > 5:
            raise ValueError("Maximal 5 Themen pro Briefing (API-Kontingent schonen)")
        return v


class FrontPagesInput(BaseModel):
    """Eingabeparameter für Zeitungscovers."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    source_country: str = Field(
        default="ch",
        description="Land als ISO-Code, z.B. 'ch' (Schweiz), 'de' (Deutschland)",
        min_length=2,
        max_length=5,
    )
    source_name: Optional[str] = Field(
        default=None,
        description="Name der Zeitung (optional), z.B. 'NZZ', 'Blick'",
        max_length=200,
    )
    date: Optional[str] = Field(
        default=None,
        description="Datum im Format 'YYYY-MM-DD'. Leer für heute.",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' oder 'json'",
    )

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError("Datum muss im Format 'YYYY-MM-DD' sein") from e
        return v


class TrendRadarInput(BaseModel):
    """Eingabeparameter für den Themen-Trend-Radar."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    category: str = Field(
        ...,
        description="Nachrichtenkategorie, z.B. 'politics', 'technology', 'education', 'business', 'science', 'entertainment', 'environment', 'food', 'health', 'sports'",
        min_length=2,
        max_length=50,
    )
    source_country: str = Field(
        default="ch",
        description="Quellland(er), z.B. 'ch' oder 'ch,de,at'",
    )
    language: str = Field(
        default="de",
        description="Sprache, z.B. 'de', 'fr', 'it', 'en'",
    )
    days_back: int = Field(
        default=7,
        description="Zeitraum in Tagen (1–30)",
        ge=1,
        le=30,
    )
    number: int = Field(
        default=15,
        description="Anzahl Artikel (1–50)",
        ge=1,
        le=50,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' oder 'json'",
    )


class GeoNewsInput(BaseModel):
    """Eingabeparameter für standortbasierte Nachrichtensuche."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    location: str = Field(
        ...,
        description="Ortsname, z.B. 'Zürich', 'Bern', 'Basel', 'Luzern'",
        min_length=2,
        max_length=200,
    )
    query: Optional[str] = Field(
        default=None,
        description="Zusätzlicher Suchbegriff (optional), z.B. 'Schule', 'Digitalisierung'",
        max_length=300,
    )
    language: str = Field(
        default="de",
        description="Sprache der Artikel",
    )
    days_back: int = Field(
        default=14,
        description="Zeitraum in Tagen (1–90)",
        ge=1,
        le=90,
    )
    number: int = Field(
        default=10,
        description="Anzahl Ergebnisse (1–50)",
        ge=1,
        le=50,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' oder 'json'",
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="news_search",
    annotations={
        "title": "Nachrichtensuche",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def news_search(params: SearchNewsInput) -> str:
    """Volltext-Nachrichtensuche in 150+ Ländern und 50+ Sprachen.

    Sucht Artikel nach Stichworten mit optionaler Filterung nach Sprache,
    Land, Datum und Sentiment-Analyse. Ideal für Medienmonitoring,
    Themenrecherche und Reputationsanalyse.

    Args:
        params (SearchNewsInput): Suchparameter mit:
            - query (str): Suchbegriff(e), Anführungszeichen für exakte Phrasen
            - language (str, optional): ISO-Code, z.B. 'de', 'en', 'fr'
            - source_country (str, optional): ISO-Code(s), z.B. 'ch,de,at'
            - earliest_date / latest_date (str, optional): Format 'YYYY-MM-DD'
            - sort (str): 'relevance' oder 'publish-time'
            - number (int): Anzahl Ergebnisse (1–100)
            - include_full_text (bool): Volltext einschliessen
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Gefundene Artikel mit Titel, Zusammenfassung, Quelle, Datum und Sentiment
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_search")

    params_dict: dict[str, Any] = {
        "api-key": api_key,
        "text": params.query,
        "number": params.number,
        "sort": params.sort.value,
        "sort-direction": "DESC",
    }
    if params.language:
        params_dict["language"] = params.language
    if params.source_country:
        params_dict["source-country"] = params.source_country
    if params.earliest_date:
        params_dict["earliest-publish-date"] = f"{params.earliest_date} 00:00:00"
    if params.latest_date:
        params_dict["latest-publish-date"] = f"{params.latest_date} 23:59:59"

    try:
        client = _get_client()
        response = await client.get("/search-news", params=params_dict)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return _handle_api_error(e)

    articles = data.get("news", [])
    total = data.get("available", 0)

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "total_verfuegbar": total,
                "zurueckgegeben": len(articles),
                "query": params.query,
                "artikel": [_format_article(a, include_text=params.include_full_text) for a in articles],
            },
            ensure_ascii=False,
            indent=2,
        )

    header = f"## 🔍 Suchergebnisse: «{params.query}»\n\n"
    header += f"**{len(articles)} von {total} Treffern** "
    if params.source_country:
        header += f"| Land: `{params.source_country}` "
    if params.language:
        header += f"| Sprache: `{params.language}` "
    header += "\n"

    return header + _format_articles_markdown(articles, include_text=params.include_full_text)


@mcp.tool(
    name="news_top_headlines",
    annotations={
        "title": "Top-Schlagzeilen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def news_top_headlines(params: TopNewsInput) -> str:
    """Abrufen der meistberichteten Top-Schlagzeilen eines Landes.

    Liefert nach Relevanz geclusterte Schlagzeilen aus einem bestimmten Land
    und einer Sprache. Die Top News werden aus mehreren Quellen des jeweiligen
    Landes aggregiert – je mehr Quellen über ein Thema berichten, desto höher
    das Ranking.

    Args:
        params (TopNewsInput): Parameter mit:
            - source_country (str): Quellland, z.B. 'ch' (Standard), 'de', 'us'
            - language (str): Sprache, z.B. 'de' (Standard), 'en', 'fr'
            - date (str, optional): Datum 'YYYY-MM-DD', leer = heute
            - number (int): Anzahl Top-News (1–100)
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Top-Schlagzeilen nach Relevanz geclustert
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_top_headlines")

    params_dict: dict[str, Any] = {
        "api-key": api_key,
        "source-country": params.source_country,
        "language": params.language,
        "number": params.number,
    }
    if params.date:
        params_dict["date"] = params.date

    try:
        client = _get_client()
        response = await client.get("/top-news", params=params_dict)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return _handle_api_error(e)

    clusters = data.get("top_news", [])

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "land": params.source_country,
                "sprache": params.language,
                "datum": params.date or "heute",
                "cluster": [
                    {
                        "rang": i + 1,
                        "artikel": [_format_article(a) for a in cluster.get("news", [])],
                    }
                    for i, cluster in enumerate(clusters)
                ],
            },
            ensure_ascii=False,
            indent=2,
        )

    date_display = params.date or datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"## 📰 Top-Schlagzeilen: {params.source_country.upper()} | {params.language.upper()} | {date_display}\n"
    ]

    for i, cluster in enumerate(clusters, 1):
        cluster_articles = cluster.get("news", [])
        if not cluster_articles:
            continue
        top_article = cluster_articles[0]
        lines.append(f"\n### #{i} {top_article.get('title', 'Kein Titel')}")
        lines.append(
            f"📅 {top_article.get('publish_date', 'n/a')} | "
            f"🗞️ {len(cluster_articles)} Quellen berichten"
        )
        if top_article.get("summary"):
            lines.append(f"\n{top_article['summary']}")
        lines.append(f"\n🔗 {top_article.get('url', '')}")

    return "\n".join(lines)


@mcp.tool(
    name="news_sentiment_monitor",
    annotations={
        "title": "Sentiment-Monitoring",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def news_sentiment_monitor(params: SentimentMonitorInput) -> str:
    """Sentiment-Analyse der Medienberichterstattung zu einer Institution oder einem Thema.

    Analysiert die emotionale Tonalität der Berichterstattung über eine
    Organisation, Person oder ein Thema. Sentiment-Werte: negativ (-1) bis
    positiv (+1). Nur für Deutsch (de) und Englisch (en) verfügbar.

    Typischer Einsatz: Reputationsmonitoring für das Schulamt Zürich,
    Stimmungsanalyse zu KI-Themen, Medientendenzen verfolgen.

    Args:
        params (SentimentMonitorInput): Parameter mit:
            - entity (str): Institution/Thema, z.B. 'Schulamt Zürich'
            - language (str): 'de' oder 'en' (nur diese zwei unterstützt)
            - days_back (int): Zeitraum in Tagen (1–365)
            - source_country (str, optional): z.B. 'ch,de,at'
            - number (int): Anzahl Artikel für Analyse (1–100)
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Sentiment-Auswertung mit Statistiken und Einzelartikeln
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_sentiment_monitor")

    latest_date = datetime.now()
    earliest_date = latest_date - timedelta(days=params.days_back)

    params_dict: dict[str, Any] = {
        "api-key": api_key,
        "text": params.entity,
        "language": params.language,
        "number": params.number,
        "earliest-publish-date": earliest_date.strftime("%Y-%m-%d 00:00:00"),
        "latest-publish-date": latest_date.strftime("%Y-%m-%d 23:59:59"),
        "sort": "publish-time",
        "sort-direction": "DESC",
    }
    if params.source_country:
        params_dict["source-country"] = params.source_country

    try:
        client = _get_client()
        response = await client.get("/search-news", params=params_dict)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return _handle_api_error(e)

    articles = data.get("news", [])
    total_available = data.get("available", 0)

    # Sentiment-Statistiken berechnen
    sentiments = [
        a["sentiment"]
        for a in articles
        if a.get("sentiment") is not None
    ]
    positive = [s for s in sentiments if s > 0.1]
    negative = [s for s in sentiments if s < -0.1]
    neutral = [s for s in sentiments if -0.1 <= s <= 0.1]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else None

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "entity": params.entity,
                "zeitraum_tage": params.days_back,
                "total_verfuegbar": total_available,
                "analysiert": len(articles),
                "sentiment_statistik": {
                    "durchschnitt": round(avg_sentiment, 3) if avg_sentiment is not None else None,
                    "label": _sentiment_label(avg_sentiment),
                    "positiv": len(positive),
                    "neutral": len(neutral),
                    "negativ": len(negative),
                },
                "artikel": [
                    {**_format_article(a), "sentiment_label": _sentiment_label(a.get("sentiment"))}
                    for a in articles
                ],
            },
            ensure_ascii=False,
            indent=2,
        )

    # Markdown-Report
    lines = [f"## 📊 Sentiment-Monitor: «{params.entity}»\n"]
    lines.append(
        f"**Zeitraum:** {earliest_date.strftime('%d.%m.%Y')} – {latest_date.strftime('%d.%m.%Y')} "
        f"({params.days_back} Tage)\n"
    )
    lines.append(f"**Gefunden:** {total_available} Artikel | **Analysiert:** {len(articles)}\n")

    if avg_sentiment is not None:
        label = _sentiment_label(avg_sentiment)
        emoji = "😊" if avg_sentiment > 0.1 else ("😟" if avg_sentiment < -0.1 else "😐")
        lines.append(f"\n### {emoji} Gesamt-Sentiment: **{label}** ({avg_sentiment:.3f})\n")
        lines.append(f"✅ Positiv: **{len(positive)}** | 😐 Neutral: **{len(neutral)}** | ❌ Negativ: **{len(negative)}**\n")
    else:
        lines.append("\n⚠️ Keine Sentiment-Daten verfügbar (Sprache prüfen: nur 'de' / 'en')\n")

    if articles:
        lines.append("\n### Aktuellste Berichte\n")
        # Sortiere nach Sentiment für bessere Übersicht
        sorted_articles = sorted(
            articles,
            key=lambda a: a.get("sentiment") or 0,
        )
        # Zeige negativste und positivste
        top_neg = sorted_articles[:3]
        top_pos = sorted_articles[-3:][::-1]

        if top_neg and top_neg[0].get("sentiment", 0) < -0.1:
            lines.append("#### ❌ Kritischste Berichte")
            lines.append(_format_articles_markdown(top_neg, include_sentiment=True))

        if top_pos and top_pos[0].get("sentiment", 0) > 0.1:
            lines.append("\n#### ✅ Positivste Berichte")
            lines.append(_format_articles_markdown(top_pos, include_sentiment=True))

    return "\n".join(lines)


@mcp.tool(
    name="news_media_briefing",
    annotations={
        "title": "Wöchentliches Medien-Briefing",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def news_media_briefing(params: MediaBriefingInput) -> str:
    """Generiert ein kompaktes Medien-Briefing für mehrere Themen parallel.

    Ideal für den wöchentlichen GL-Briefing-Report oder KI-Fachgruppen-Update.
    Fasst die Medienlage zu mehreren Themen in einem Bericht zusammen,
    inkl. Sentiment-Übersicht.

    Achtung: Pro Thema 1 API-Call – maximal 5 Themen gleichzeitig.

    Args:
        params (MediaBriefingInput): Parameter mit:
            - topics (list[str]): Liste von Themen (max. 5), z.B. ['Volksschule Zürich', 'KI Bildung']
            - language (str): 'de' oder 'en'
            - days_back (int): Zeitraum in Tagen (1–31)
            - source_country (str): Quellländer, z.B. 'ch,de,at'

    Returns:
        str: Kompaktes Medien-Briefing als Markdown-Bericht
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_media_briefing")

    latest_date = datetime.now()
    earliest_date = latest_date - timedelta(days=params.days_back)

    lines = [
        f"# 📋 Medien-Briefing\n",
        f"**Zeitraum:** {earliest_date.strftime('%d.%m.%Y')} – {latest_date.strftime('%d.%m.%Y')} | "
        f"**Quellen:** {params.source_country} | **Sprache:** {params.language}\n",
        "---\n",
    ]

    for topic in params.topics:
        params_dict: dict[str, Any] = {
            "api-key": api_key,
            "text": topic,
            "language": params.language,
            "source-country": params.source_country,
            "number": 5,
            "earliest-publish-date": earliest_date.strftime("%Y-%m-%d 00:00:00"),
            "latest-publish-date": latest_date.strftime("%Y-%m-%d 23:59:59"),
            "sort": "publish-time",
            "sort-direction": "DESC",
        }

        try:
            client = _get_client()
            response = await client.get("/search-news", params=params_dict)
            response.raise_for_status()
            data = response.json()
            articles = data.get("news", [])
            total = data.get("available", 0)

            sentiments = [a["sentiment"] for a in articles if a.get("sentiment") is not None]
            avg = sum(sentiments) / len(sentiments) if sentiments else None
            label = _sentiment_label(avg)
            emoji = "😊" if avg and avg > 0.1 else ("😟" if avg and avg < -0.1 else "😐")

            lines.append(f"\n## {emoji} {topic}\n")
            lines.append(
                f"**{total} Artikel** gefunden | "
                f"Sentiment: **{label}**"
                + (f" ({avg:.2f})" if avg is not None else "")
                + "\n"
            )

            if articles:
                for a in articles[:3]:
                    lines.append(
                        f"- [{a.get('title', 'Kein Titel')}]({a.get('url', '#')}) "
                        f"({a.get('publish_date', 'n/a')[:10]})"
                    )
            else:
                lines.append("_Keine Artikel im Zeitraum gefunden._")

        except Exception as e:
            lines.append(f"\n## ⚠️ {topic}\n")
            lines.append(f"Fehler beim Abrufen: {_handle_api_error(e)}")

        lines.append("\n---")

    return "\n".join(lines)


@mcp.tool(
    name="news_retrieve_article",
    annotations={
        "title": "Artikel abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def news_retrieve_article(params: RetrieveArticleInput) -> str:
    """Ruft den vollständigen Inhalt eines einzelnen Artikels anhand seiner ID ab.

    Die Artikel-ID stammt aus vorherigen Suchergebnissen (news_search oder
    news_top_headlines). Liefert Volltext, Metadaten und Sentiment.

    Args:
        params (RetrieveArticleInput): Parameter mit:
            - article_id (int): Artikel-ID aus Suchergebnissen
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Vollständiger Artikel mit Metadaten
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_retrieve_article")

    try:
        client = _get_client()
        response = await client.get(
            "/retrieve-news",
            params={"api-key": api_key, "ids": params.article_id},
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return _handle_api_error(e)

    news_list = data.get("news", [])
    if not news_list:
        return f"❌ Kein Artikel mit ID {params.article_id} gefunden."

    article = news_list[0]

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(_format_article(article, include_text=True), ensure_ascii=False, indent=2)

    formatted = _format_article(article, include_text=True)
    sentiment_str = ""
    if formatted["sentiment"] is not None:
        score = formatted["sentiment"]
        label = _sentiment_label(score)
        sentiment_str = f"\n**Sentiment:** {label} ({score:.3f})"

    return (
        f"## 📰 {formatted['titel']}\n\n"
        f"**Veröffentlicht:** {formatted['veroeffentlicht']}  \n"
        f"**Autoren:** {', '.join(formatted['autoren']) if formatted['autoren'] else 'n/a'}  \n"
        f"**Kategorie:** {formatted['kategorie']} | **Sprache:** {formatted['sprache']} | "
        f"**Land:** {formatted['quellland']}"
        f"{sentiment_str}\n\n"
        f"**Quelle:** {formatted['quelle_url']}\n\n"
        f"---\n\n{formatted.get('volltext', '')}"
    )


@mcp.tool(
    name="news_search_sources",
    annotations={
        "title": "Nachrichtenquellen suchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def news_search_sources(params: SearchSourcesInput) -> str:
    """Sucht nach verfügbaren Nachrichtenquellen/-medien in der WorldNewsAPI.

    Ermöglicht die Entdeckung verfügbarer Schweizer und internationaler
    Medienquellen nach Name, Land oder Sprache. Nützlich um zu prüfen,
    welche Schweizer Medien (NZZ, SRF, Blick, etc.) indexiert sind.

    Args:
        params (SearchSourcesInput): Parameter mit:
            - name (str, optional): Teilname der Quelle, z.B. 'NZZ', 'SRF'
            - country (str, optional): Land als ISO-Code, z.B. 'ch', 'de'
            - language (str, optional): Sprache, z.B. 'de', 'fr'
            - number (int): Anzahl Ergebnisse (1–100)
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Liste der gefundenen Nachrichtenquellen mit URL und Metadaten
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_search_sources")

    params_dict: dict[str, Any] = {
        "api-key": api_key,
        "number": params.number,
    }
    if params.name:
        params_dict["name"] = params.name
    if params.country:
        params_dict["source-country"] = params.country
    if params.language:
        params_dict["language"] = params.language

    try:
        client = _get_client()
        response = await client.get("/search-news-sources", params=params_dict)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return _handle_api_error(e)

    sources = data.get("news_sources", [])

    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"anzahl": len(sources), "quellen": sources}, ensure_ascii=False, indent=2)

    if not sources:
        return "Keine Quellen gefunden."

    lines = [f"## 🗞️ Nachrichtenquellen ({len(sources)} gefunden)\n"]
    for src in sources:
        lines.append(
            f"- **{src.get('name', 'n/a')}** – {src.get('url', 'n/a')} "
            f"| 🌍 {src.get('source_country', 'n/a')} | 🌐 {src.get('language', 'n/a')}"
        )

    return "\n".join(lines)


@mcp.tool(
    name="news_front_pages",
    annotations={
        "title": "Zeitungscovers abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def news_front_pages(params: FrontPagesInput) -> str:
    """Ruft die Titelseiten / Front Pages von Zeitungen eines Landes ab.

    WorldNewsAPI aggregiert digitale Titelseiten von über 6'000 Zeitungen in
    125 Ländern. Nützlich für Komparativstudien, Themen-Agenda-Analyse und
    als Überblick was die wichtigsten Schweizer Zeitungen heute berichten.

    Args:
        params (FrontPagesInput): Parameter mit:
            - source_country (str): Quellland, z.B. 'ch' (Standard)
            - source_name (str, optional): Name der Zeitung, z.B. 'NZZ'
            - date (str, optional): Datum 'YYYY-MM-DD', leer = heute
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Titelseiten-Übersicht der Zeitungen
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_front_pages")

    params_dict: dict[str, Any] = {
        "api-key": api_key,
        "source-country": params.source_country,
    }
    if params.source_name:
        params_dict["source-name"] = params.source_name
    if params.date:
        params_dict["date"] = params.date

    try:
        client = _get_client()
        response = await client.get("/retrieve-front-page", params=params_dict)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return _handle_api_error(e)

    front_pages = data.get("front_pages", [])

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {"land": params.source_country, "anzahl": len(front_pages), "titelseiten": front_pages},
            ensure_ascii=False,
            indent=2,
        )

    if not front_pages:
        return "Keine Titelseiten gefunden."

    date_display = params.date or datetime.now().strftime("%Y-%m-%d")
    lines = [f"## 🗞️ Zeitungscovers: {params.source_country.upper()} | {date_display}\n"]

    for fp in front_pages:
        name = fp.get("name", "n/a")
        url = fp.get("url", "n/a")
        img = fp.get("image", "")
        date = fp.get("date", "n/a")
        lines.append(f"\n### {name}")
        lines.append(f"📅 {date} | 🔗 {url}")
        if img:
            lines.append(f"\n![{name}]({img})")

    return "\n".join(lines)


@mcp.tool(
    name="news_trend_radar",
    annotations={
        "title": "Themen-Trend-Radar",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def news_trend_radar(params: TrendRadarInput) -> str:
    """Analysiert Nachrichtentrends in einer bestimmten Kategorie.

    Zeigt die meistbesprochenen Themen in einer Kategorie (z.B. 'technology',
    'education', 'politics') für ein Land und eine Sprache. Nützlich für
    die strategische Themenplanung und das Erkennen aufkommender Diskurse.

    Args:
        params (TrendRadarInput): Parameter mit:
            - category (str): z.B. 'politics', 'technology', 'education', 'science'
            - source_country (str): Quellland(er), z.B. 'ch'
            - language (str): Sprache, z.B. 'de', 'fr'
            - days_back (int): Zeitraum in Tagen (1–30)
            - number (int): Anzahl Artikel (1–50)
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Trending-Themen und Artikel der gewählten Kategorie
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_trend_radar")

    latest_date = datetime.now()
    earliest_date = latest_date - timedelta(days=params.days_back)

    params_dict: dict[str, Any] = {
        "api-key": api_key,
        "source-country": params.source_country,
        "language": params.language,
        "categories": params.category,
        "number": params.number,
        "earliest-publish-date": earliest_date.strftime("%Y-%m-%d 00:00:00"),
        "latest-publish-date": latest_date.strftime("%Y-%m-%d 23:59:59"),
        "sort": "publish-time",
        "sort-direction": "DESC",
    }

    try:
        client = _get_client()
        response = await client.get("/search-news", params=params_dict)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return _handle_api_error(e)

    articles = data.get("news", [])
    total = data.get("available", 0)

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "kategorie": params.category,
                "land": params.source_country,
                "zeitraum_tage": params.days_back,
                "total": total,
                "artikel": [_format_article(a) for a in articles],
            },
            ensure_ascii=False,
            indent=2,
        )

    lines = [
        f"## 📡 Trend-Radar: Kategorie «{params.category}»\n",
        f"**Land:** {params.source_country} | **Sprache:** {params.language} | "
        f"**Zeitraum:** {params.days_back} Tage | **{total} Artikel** gefunden\n",
    ]
    lines.append(_format_articles_markdown(articles, include_sentiment=True))

    return "\n".join(lines)


@mcp.tool(
    name="news_geo_search",
    annotations={
        "title": "Standortbasierte Nachrichtensuche",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def news_geo_search(params: GeoNewsInput) -> str:
    """Sucht Nachrichten mit explizitem geografischem Bezug zu einem Ort.

    Kombiniert eine Ortsangabe mit einem optionalen Suchbegriff für
    standortspezifische Nachrichtenrecherche. Ideal für die Suche nach
    Berichten über Zürich, Bern oder andere Schweizer Gemeinden.

    Beispiele:
    - location='Zürich', query='Volksschule' → Schulnachrichten aus Zürich
    - location='Winterthur', query='Digitalisierung' → Digitalisierungsnews aus Winterthur
    - location='Kanton Zürich' → Alle News aus dem Kanton

    Args:
        params (GeoNewsInput): Parameter mit:
            - location (str): Ortsname, z.B. 'Zürich', 'Bern', 'Basel'
            - query (str, optional): Zusätzlicher Suchbegriff
            - language (str): Sprache, z.B. 'de'
            - days_back (int): Zeitraum in Tagen (1–90)
            - number (int): Anzahl Ergebnisse (1–50)
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Geolokalisierte Nachrichtenartikel
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_geo_search")

    # Kombiniere location und optionalen query
    search_text = params.location
    if params.query:
        search_text = f"{params.location} {params.query}"

    latest_date = datetime.now()
    earliest_date = latest_date - timedelta(days=params.days_back)

    params_dict: dict[str, Any] = {
        "api-key": api_key,
        "text": search_text,
        "language": params.language,
        "source-country": "ch,de,at,fr,it",  # breit suchen für Geo-Queries
        "number": params.number,
        "earliest-publish-date": earliest_date.strftime("%Y-%m-%d 00:00:00"),
        "latest-publish-date": latest_date.strftime("%Y-%m-%d 23:59:59"),
        "sort": "publish-time",
        "sort-direction": "DESC",
    }

    try:
        client = _get_client()
        response = await client.get("/search-news", params=params_dict)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return _handle_api_error(e)

    articles = data.get("news", [])
    total = data.get("available", 0)

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "ort": params.location,
                "zusatzsuche": params.query,
                "total": total,
                "artikel": [_format_article(a) for a in articles],
            },
            ensure_ascii=False,
            indent=2,
        )

    header = f"## 📍 Geo-News: {params.location}"
    if params.query:
        header += f" + «{params.query}»"
    header += f"\n\n**{total} Artikel** in den letzten {params.days_back} Tagen\n"

    return header + _format_articles_markdown(articles, include_sentiment=True)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------


def main() -> None:
    """Startet den MCP-Server."""
    import argparse

    parser = argparse.ArgumentParser(description="News Monitor MCP Server")
    parser.add_argument("--http", action="store_true", help="Startet als HTTP-Server statt stdio")
    parser.add_argument("--port", type=int, default=8000, help="HTTP-Port (Standard: 8000)")
    args = parser.parse_args()

    if args.http:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
