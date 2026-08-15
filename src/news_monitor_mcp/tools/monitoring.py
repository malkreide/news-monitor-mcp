"""Die 9 read-only Monitoring-Tools.

Aufgeteilt vom Audit-Finding ARCH-MONOLITHIC (medium, 2026-05-13). Alle Tools
nutzen den TTL-Cache aus `cache.py` und das header-basierte Auth aus
`api_client.py` (siehe SEC-API-KEY-HANDLING).
"""

import json
from datetime import datetime, timedelta
from typing import Any

from news_monitor_mcp.api_client import (
    UpstreamShapeError,
    _auth_headers,
    _check_api_key,
    _get_client,
    articles_of,
    clusters_of,
)
from news_monitor_mcp.app import _cache, mcp
from news_monitor_mcp.errors import _handle_api_error, _no_key_message
from news_monitor_mcp.formatting import (
    ResponseFormat,
    SortOrder,
    _calc_avg_sentiment,
    _format_article,
    _format_articles_markdown,
    _sentiment_label,
)
from news_monitor_mcp.models import (
    FrontPagesInput,
    GeoNewsInput,
    MediaBriefingInput,
    RetrieveArticleInput,
    SearchNewsInput,
    SearchSourcesInput,
    SentimentMonitorInput,
    TopNewsInput,
    TrendRadarInput,
)


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
    """Volltext-Nachrichtensuche in 150+ Laendern (mit Cache, TTL: 30 Min).

    Args:
        params (SearchNewsInput): query, language, source_country, earliest/latest_date,
            sort, number, include_full_text, use_cache, response_format

    Returns:
        str: Artikel mit Titel, Zusammenfassung, Quelle, Datum und Sentiment.
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_search")
    cache_params = {
        "q": params.query,
        "lang": params.language,
        "sc": params.source_country,
        "ed": params.earliest_date,
        "ld": params.latest_date,
        "sort": params.sort.value,
        "n": params.number,
    }
    cache_info = ""
    data = None
    if params.use_cache:
        data = _cache.get("search", cache_params)
        if data is not None:
            cache_info = "\n> ℹ️ *Aus Cache (TTL: 30 Min) – `use_cache=False` fuer frische Daten*\n"
    if data is None:
        p: dict[str, Any] = {
            "text": params.query,
            "number": params.number,
            "sort-direction": "DESC",
        }
        # `relevance` quittiert die Quelle mit HTTP 400: «Sort must be either
        # 'publish-time' or empty.» Leer *ist* ihre Relevanz-Sortierung — der
        # Parameter gehoert also weggelassen, nicht uebersetzt.
        #
        # Das war kein Testproblem: `SortOrder.RELEVANCE` ist der Default von
        # `SearchNewsInput.sort`, jede Standardsuche lief damit in den 400. Alle
        # Unit-Tests blieben gruen, weil sie die Quelle mocken — gesehen hat es
        # erst der erste Live-Lauf mit Schluessel (2026-08-14).
        if params.sort is not SortOrder.RELEVANCE:
            p["sort"] = params.sort.value
        if params.language:
            p["language"] = params.language
        if params.source_country:
            p["source-country"] = params.source_country
        if params.earliest_date:
            p["earliest-publish-date"] = f"{params.earliest_date} 00:00:00"
        if params.latest_date:
            p["latest-publish-date"] = f"{params.latest_date} 23:59:59"
        try:
            r = await _get_client().get("/search-news", params=p, headers=_auth_headers(api_key))
            r.raise_for_status()
            data = r.json()
            if params.use_cache:
                _cache.set("search", cache_params, data)
        except Exception as e:
            return _handle_api_error(e)
    try:
        articles = articles_of(data, "/search-news")
    except UpstreamShapeError as e:
        return _handle_api_error(e)
    total = data.get("available", 0)
    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "total_verfuegbar": total,
                "zurueckgegeben": len(articles),
                "query": params.query,
                "cache": bool(cache_info),
                "artikel": [_format_article(a, include_text=params.include_full_text) for a in articles],
            },
            ensure_ascii=False,
            indent=2,
        )
    header = f"## Suchergebnisse: {params.query}\n{cache_info}\n"
    header += f"**{len(articles)} von {total} Treffern**"
    if params.source_country:
        header += f" | Land: `{params.source_country}`"
    if params.language:
        header += f" | Sprache: `{params.language}`"
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
    """Top-Schlagzeilen eines Landes (mit Cache, TTL: 15 Min).

    Args:
        params (TopNewsInput): source_country, language, date, number, use_cache, response_format

    Returns:
        str: Geclusterte Top-News nach Quellen-Anzahl gereiht.
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_top_headlines")
    cache_params = {"sc": params.source_country, "lang": params.language, "date": params.date, "n": params.number}
    cache_info = ""
    data = None
    if params.use_cache:
        data = _cache.get("headlines", cache_params)
        if data is not None:
            cache_info = "\n> ℹ️ *Aus Cache (TTL: 15 Min)*\n"
    if data is None:
        p: dict[str, Any] = {
            "source-country": params.source_country,
            "language": params.language,
            "number": params.number,
        }
        if params.date:
            p["date"] = params.date
        try:
            r = await _get_client().get("/top-news", params=p, headers=_auth_headers(api_key))
            r.raise_for_status()
            data = r.json()
            if params.use_cache:
                _cache.set("headlines", cache_params, data)
        except Exception as e:
            return _handle_api_error(e)
    # Nicht `data.get("top_news", [])`: Das beantwortet «die Quelle fuehrt hier
    # gerade nichts» und «die Quelle antwortet anders» mit derselben leeren
    # Liste. Am 15.8.2026 war der Unterschied der Ausgabe nicht anzusehen.
    try:
        clusters = clusters_of(data, "/top-news")
    except UpstreamShapeError as e:
        return _handle_api_error(e)
    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "land": params.source_country,
                "sprache": params.language,
                "datum": params.date or "heute",
                "cache": bool(cache_info),
                "cluster": [
                    {"rang": i + 1, "artikel": [_format_article(a) for a in c.get("news", [])]}
                    for i, c in enumerate(clusters)
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    date_display = params.date or datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"## Top-Schlagzeilen: {params.source_country.upper()} | {params.language.upper()} | {date_display}\n{cache_info}"
    ]
    # Null Cluster ist eine Aussage der Quelle — und muss als solche dastehen.
    # Vorher blieb in diesem Fall nur die Ueberschrift uebrig, und die sagt
    # nichts: Sie sieht genauso aus, wenn die Formatierung scheitert. Fuer
    # kleine Sprach-/Land-Kombinationen wie CH/de ist leer ausserdem der
    # Normalfall in ruhigen Stunden, kein Ausnahmezustand.
    if not clusters:
        # Das Wort «Fehler» darf hier NICHT vorkommen: Die Live-Tests sichern
        # `assert "Fehler" not in result` zu, und die Antwort ist ja gerade
        # keiner. Genau darueber ist die erste Fassung dieser Zeile gestolpert.
        lines.append(
            f"\n*Die Quelle fuehrt aktuell keine Top-Cluster fuer "
            f"{params.source_country.upper()}/{params.language.upper()}. "
            "Das ist ihre Antwort und keine Stoerung — in kleinen Sprachraeumen "
            "kommt das in ruhigen Stunden vor.*"
        )
        return "\n".join(lines)
    for i, cluster in enumerate(clusters, 1):
        arts = cluster.get("news", [])
        if not arts:
            continue
        top = arts[0]
        lines.append(f"\n### #{i} {top.get('title', 'Kein Titel')}")
        lines.append(f"📅 {top.get('publish_date', 'n/a')} | 🗞️ {len(arts)} Quellen berichten")
        if top.get("summary"):
            lines.append(f"\n{top['summary']}")
        lines.append(f"\n🔗 {top.get('url', '')}")
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
    """Sentiment-Analyse der Medienberichterstattung (Cache-TTL: 60 Min).

    Analysiert die emotionale Tonalitaet der Berichterstattung. Nur DE und EN.

    ⚠️ DATENSCHUTZ-HINWEIS (revDSG, Schweiz): Sentiment-Analyse auf eine
    namentlich genannte Person stellt Profiling nach Art. 5 lit. f DSG dar.
    Vor produktivem Einsatz mit Personenbezug: Datenschutz-Folgenabschaetzung
    (Art. 22 DSG) und Informationspflicht (Art. 19 DSG) pruefen. Empfehlung:
    nur auf Institutionen / Themen, nicht auf einzelne Personen anwenden.
    Siehe docs/privacy-dsg.md fuer Details.

    Args:
        params (SentimentMonitorInput): entity, language (de/en), days_back,
            source_country, number, use_cache, response_format

    Returns:
        str: Sentiment-Auswertung mit Ø-Score, Statistik und Top-Artikeln.
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_sentiment_monitor")
    latest_dt = datetime.now()
    earliest_dt = latest_dt - timedelta(days=params.days_back)
    cache_params = {
        "entity": params.entity,
        "lang": params.language,
        "days": params.days_back,
        "sc": params.source_country,
        "n": params.number,
        "ed": earliest_dt.strftime("%Y-%m-%d"),
    }
    cache_info = ""
    data = None
    if params.use_cache:
        data = _cache.get("sentiment", cache_params)
        if data is not None:
            cache_info = "\n> ℹ️ *Aus Cache (TTL: 60 Min)*\n"
    if data is None:
        p: dict[str, Any] = {
            "text": params.entity,
            "language": params.language,
            "number": params.number,
            "earliest-publish-date": earliest_dt.strftime("%Y-%m-%d 00:00:00"),
            "latest-publish-date": latest_dt.strftime("%Y-%m-%d 23:59:59"),
            "sort": "publish-time",
            "sort-direction": "DESC",
        }
        if params.source_country:
            p["source-country"] = params.source_country
        try:
            r = await _get_client().get("/search-news", params=p, headers=_auth_headers(api_key))
            r.raise_for_status()
            data = r.json()
            if params.use_cache:
                _cache.set("sentiment", cache_params, data)
        except Exception as e:
            return _handle_api_error(e)
    try:
        articles = articles_of(data, "/search-news")
    except UpstreamShapeError as e:
        return _handle_api_error(e)
    total_available = data.get("available", 0)
    sentiments = [a["sentiment"] for a in articles if a.get("sentiment") is not None]
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
                "cache": bool(cache_info),
                "sentiment_statistik": {
                    "durchschnitt": round(avg_sentiment, 3) if avg_sentiment is not None else None,
                    "label": _sentiment_label(avg_sentiment),
                    "positiv": len(positive),
                    "neutral": len(neutral),
                    "negativ": len(negative),
                },
                "artikel": [
                    {**_format_article(a), "sentiment_label": _sentiment_label(a.get("sentiment"))} for a in articles
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    lines = [f"## Sentiment-Monitor: {params.entity}\n{cache_info}"]
    lines.append(
        f"**Zeitraum:** {earliest_dt.strftime('%d.%m.%Y')} – {latest_dt.strftime('%d.%m.%Y')} ({params.days_back} Tage)\n"
    )
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


@mcp.tool(
    name="news_media_briefing",
    annotations={
        "title": "Medien-Briefing",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def news_media_briefing(params: MediaBriefingInput) -> str:
    """Multi-Themen-Medien-Briefing fuer GL/KI-Fachgruppe (Cache-TTL: 60 Min pro Thema).

    Args:
        params (MediaBriefingInput): topics (max. 5), language, days_back, source_country, use_cache

    Returns:
        str: Kompaktes Briefing mit Sentiment und Top-3-Artikeln pro Thema.
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_media_briefing")
    latest_dt = datetime.now()
    earliest_dt = latest_dt - timedelta(days=params.days_back)
    lines = [
        "# Medien-Briefing\n",
        f"**Zeitraum:** {earliest_dt.strftime('%d.%m.%Y')} – {latest_dt.strftime('%d.%m.%Y')} | "
        f"**Quellen:** {params.source_country} | **Sprache:** {params.language}\n",
        "---\n",
    ]
    for topic in params.topics:
        cache_params = {
            "topic": topic,
            "lang": params.language,
            "sc": params.source_country,
            "days": params.days_back,
            "ed": earliest_dt.strftime("%Y-%m-%d"),
        }
        data = None
        if params.use_cache:
            data = _cache.get("briefing", cache_params)
        if data is None:
            p: dict[str, Any] = {
                "text": topic,
                "language": params.language,
                "source-country": params.source_country,
                "number": 5,
                "earliest-publish-date": earliest_dt.strftime("%Y-%m-%d 00:00:00"),
                "latest-publish-date": latest_dt.strftime("%Y-%m-%d 23:59:59"),
                "sort": "publish-time",
                "sort-direction": "DESC",
            }
            try:
                r = await _get_client().get("/search-news", params=p, headers=_auth_headers(api_key))
                r.raise_for_status()
                data = r.json()
                if params.use_cache:
                    _cache.set("briefing", cache_params, data)
            except Exception as e:
                lines.append(f"\n## {topic}\n{_handle_api_error(e)}\n---")
                continue
        try:
            articles = articles_of(data, "/search-news")
        except UpstreamShapeError as e:
            return _handle_api_error(e)
        total = data.get("available", 0)
        avg = _calc_avg_sentiment(articles)
        label = _sentiment_label(avg)
        emoji = "😊" if avg and avg > 0.1 else ("😟" if avg and avg < -0.1 else "😐")
        lines.append(f"\n## {emoji} {topic}\n")
        lines.append(
            f"**{total} Artikel** | Sentiment: **{label}**" + (f" ({avg:.2f})" if avg is not None else "") + "\n"
        )
        if articles:
            for a in articles[:3]:
                lines.append(
                    f"- [{a.get('title', 'Kein Titel')}]({a.get('url', '#')}) ({a.get('publish_date', 'n/a')[:10]})"
                )
        else:
            lines.append("_Keine Artikel im Zeitraum._")
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
    """Vollstaendigen Artikel per ID abrufen (Cache-TTL: 24h).

    Args:
        params (RetrieveArticleInput): article_id, use_cache, response_format

    Returns:
        str: Volltext, Metadaten und Sentiment.
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_retrieve_article")
    cache_params = {"id": params.article_id}
    data = None
    if params.use_cache:
        data = _cache.get("article", cache_params)
    if data is None:
        try:
            r = await _get_client().get(
                "/retrieve-news", params={"ids": params.article_id}, headers=_auth_headers(api_key)
            )
            r.raise_for_status()
            data = r.json()
            if params.use_cache:
                _cache.set("article", cache_params, data)
        except Exception as e:
            return _handle_api_error(e)
    try:
        news_list = articles_of(data, "/retrieve-news")
    except UpstreamShapeError as e:
        return _handle_api_error(e)
    if not news_list:
        return f"Kein Artikel mit ID {params.article_id} gefunden."
    article = news_list[0]
    if params.response_format == ResponseFormat.JSON:
        return json.dumps(_format_article(article, include_text=True), ensure_ascii=False, indent=2)
    f = _format_article(article, include_text=True)
    s_str = ""
    if f["sentiment"] is not None:
        score = f["sentiment"]
        s_str = f"\n**Sentiment:** {_sentiment_label(score)} ({score:.3f})"
    return (
        f"## {f['titel']}\n\n**Veroeffentlicht:** {f['veroeffentlicht']}  \n"
        f"**Kategorie:** {f['kategorie']} | **Sprache:** {f['sprache']} | **Land:** {f['quellland']}"
        f"{s_str}\n\n**Quelle:** {f['quelle_url']}\n\n---\n\n{f.get('volltext', '')}"
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
    """Verfuegbare Nachrichtenquellen suchen (Cache-TTL: 24h).

    Args:
        params (SearchSourcesInput): name, country, language, number, use_cache, response_format

    Returns:
        str: Liste verfuegbarer Quellen mit URL und Metadaten.
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_search_sources")
    cache_params = {"name": params.name, "country": params.country, "lang": params.language, "n": params.number}
    data = None
    if params.use_cache:
        data = _cache.get("sources", cache_params)
    if data is None:
        p: dict[str, Any] = {"number": params.number}
        if params.name:
            p["name"] = params.name
        if params.country:
            p["source-country"] = params.country
        if params.language:
            p["language"] = params.language
        try:
            r = await _get_client().get("/search-news-sources", params=p, headers=_auth_headers(api_key))
            r.raise_for_status()
            data = r.json()
            if params.use_cache:
                _cache.set("sources", cache_params, data)
        except Exception as e:
            return _handle_api_error(e)
    sources = data.get("news_sources", [])
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({"anzahl": len(sources), "quellen": sources}, ensure_ascii=False, indent=2)
    if not sources:
        return "Keine Quellen gefunden."
    lines = [f"## Nachrichtenquellen ({len(sources)} gefunden)\n"]
    for src in sources:
        lines.append(
            f"- **{src.get('name', 'n/a')}** – {src.get('url', 'n/a')} | 🌍 {src.get('source_country', 'n/a')} | 🌐 {src.get('language', 'n/a')}"
        )
    return "\n".join(lines)


@mcp.tool(
    name="news_front_pages",
    annotations={
        "title": "Zeitungscovers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def news_front_pages(params: FrontPagesInput) -> str:
    """Digitale Zeitungscovers von 6000+ Publikationen (Cache-TTL: 4h).

    Args:
        params (FrontPagesInput): source_country, source_name, date, use_cache, response_format

    Returns:
        str: Titelseiten-Uebersicht mit Bild-URLs.
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_front_pages")
    cache_params = {"sc": params.source_country, "sn": params.source_name, "date": params.date}
    data = None
    if params.use_cache:
        data = _cache.get("front_pages", cache_params)
    if data is None:
        p: dict[str, Any] = {"source-country": params.source_country}
        if params.source_name:
            p["source-name"] = params.source_name
        if params.date:
            p["date"] = params.date
        try:
            r = await _get_client().get("/retrieve-front-page", params=p, headers=_auth_headers(api_key))
            r.raise_for_status()
            data = r.json()
            if params.use_cache:
                _cache.set("front_pages", cache_params, data)
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
    lines = [f"## Zeitungscovers: {params.source_country.upper()} | {date_display}\n"]
    for fp in front_pages:
        name = fp.get("name", "n/a")
        lines.append(f"\n### {name}")
        lines.append(f"📅 {fp.get('date', 'n/a')} | 🔗 {fp.get('url', 'n/a')}")
        if fp.get("image"):
            lines.append(f"\n![{name}]({fp['image']})")
    return "\n".join(lines)


@mcp.tool(
    name="news_trend_radar",
    annotations={
        "title": "Trend-Radar",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def news_trend_radar(params: TrendRadarInput) -> str:
    """Nachrichtentrends in einer Kategorie (Cache-TTL: 30 Min).

    Args:
        params (TrendRadarInput): category, source_country, language, days_back, number, use_cache, response_format

    Returns:
        str: Trending-Themen und Artikel mit Sentiment.
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_trend_radar")
    latest_dt = datetime.now()
    earliest_dt = latest_dt - timedelta(days=params.days_back)
    cache_params = {
        "cat": params.category,
        "sc": params.source_country,
        "lang": params.language,
        "days": params.days_back,
        "n": params.number,
        "ed": earliest_dt.strftime("%Y-%m-%d"),
    }
    data = None
    if params.use_cache:
        data = _cache.get("trend", cache_params)
    if data is None:
        p: dict[str, Any] = {
            "source-country": params.source_country,
            "language": params.language,
            "categories": params.category,
            "number": params.number,
            "earliest-publish-date": earliest_dt.strftime("%Y-%m-%d 00:00:00"),
            "latest-publish-date": latest_dt.strftime("%Y-%m-%d 23:59:59"),
            "sort": "publish-time",
            "sort-direction": "DESC",
        }
        try:
            r = await _get_client().get("/search-news", params=p, headers=_auth_headers(api_key))
            r.raise_for_status()
            data = r.json()
            if params.use_cache:
                _cache.set("trend", cache_params, data)
        except Exception as e:
            return _handle_api_error(e)
    try:
        articles = articles_of(data, "/search-news")
    except UpstreamShapeError as e:
        return _handle_api_error(e)
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
        f"## Trend-Radar: Kategorie {params.category}\n",
        f"**Land:** {params.source_country} | **Sprache:** {params.language} | **Zeitraum:** {params.days_back} Tage | **{total} Artikel**\n",
    ]
    lines.append(_format_articles_markdown(articles, include_sentiment=True))
    return "\n".join(lines)


@mcp.tool(
    name="news_geo_search",
    annotations={
        "title": "Geo-Suche",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def news_geo_search(params: GeoNewsInput) -> str:
    """Standortspezifische Nachrichtensuche (Cache-TTL: 30 Min).

    Args:
        params (GeoNewsInput): location, query, language, days_back, number, use_cache, response_format

    Returns:
        str: Geolokalisierte Nachrichtenartikel mit Sentiment.
    """
    api_key = _check_api_key()
    if not api_key:
        return _no_key_message("news_geo_search")
    search_text = f"{params.location} {params.query}" if params.query else params.location
    latest_dt = datetime.now()
    earliest_dt = latest_dt - timedelta(days=params.days_back)
    cache_params = {
        "loc": params.location,
        "q": params.query,
        "lang": params.language,
        "days": params.days_back,
        "n": params.number,
        "ed": earliest_dt.strftime("%Y-%m-%d"),
    }
    data = None
    if params.use_cache:
        data = _cache.get("geo", cache_params)
    if data is None:
        p: dict[str, Any] = {
            "text": search_text,
            "language": params.language,
            "source-country": "ch,de,at,fr,it",
            "number": params.number,
            "earliest-publish-date": earliest_dt.strftime("%Y-%m-%d 00:00:00"),
            "latest-publish-date": latest_dt.strftime("%Y-%m-%d 23:59:59"),
            "sort": "publish-time",
            "sort-direction": "DESC",
        }
        try:
            r = await _get_client().get("/search-news", params=p, headers=_auth_headers(api_key))
            r.raise_for_status()
            data = r.json()
            if params.use_cache:
                _cache.set("geo", cache_params, data)
        except Exception as e:
            return _handle_api_error(e)
    try:
        articles = articles_of(data, "/search-news")
    except UpstreamShapeError as e:
        return _handle_api_error(e)
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
    header = f"## Geo-News: {params.location}"
    if params.query:
        header += f" + {params.query}"
    header += f"\n\n**{total} Artikel** in den letzten {params.days_back} Tagen\n"
    return header + _format_articles_markdown(articles, include_sentiment=True)
