"""Markdown- und JSON-Formatter fuer Tool-Outputs.

Keine externen Deps ausser stdlib. Wird aus den 15 Tool-Funktionen heraus
aufgerufen, um Artikel-Dicts in lesbares Markdown oder JSON-konforme dicts
zu wandeln.
"""

from enum import Enum
from typing import Any, Optional


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


def _calc_avg_sentiment(articles: list[dict[str, Any]]) -> Optional[float]:
    scores = [a["sentiment"] for a in articles if a.get("sentiment") is not None]
    return sum(scores) / len(scores) if scores else None
