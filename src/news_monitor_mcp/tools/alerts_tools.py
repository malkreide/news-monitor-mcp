"""Die 4 Alert-Tools: create / list / check / delete.

Aufgeteilt vom Audit-Finding ARCH-MONOLITHIC (medium, 2026-05-13).
"""

import json
from datetime import datetime, timedelta
from typing import Any

from news_monitor_mcp.alerts import ALERTS_FILE
from news_monitor_mcp.api_client import _auth_headers, _check_api_key, _get_client
from news_monitor_mcp.app import _alert_manager, mcp
from news_monitor_mcp.errors import _handle_api_error, _no_key_message
from news_monitor_mcp.formatting import (
    AlertConditionType,
    ResponseFormat,
    _calc_avg_sentiment,
    _sentiment_label,
)
from news_monitor_mcp.models import (
    CheckAlertsInput,
    CreateAlertInput,
    DeleteAlertInput,
)


@mcp.tool(
    name="news_alert_create",
    annotations={
        "title": "Alert erstellen",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
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
    if params.condition_type in (
        AlertConditionType.SENTIMENT_BELOW,
        AlertConditionType.SENTIMENT_ABOVE,
        AlertConditionType.VOLUME_ABOVE,
    ):
        if params.threshold is None:
            return f"threshold ist fuer condition_type={params.condition_type.value} erforderlich."
    if params.condition_type == AlertConditionType.KEYWORD_FOUND:
        if not params.keyword:
            return "keyword ist fuer condition_type=keyword_found erforderlich."
    alert_id = _alert_manager.create(
        {
            "name": params.name,
            "entity": params.entity,
            "language": params.language,
            "source_country": params.source_country,
            "days_back": params.days_back,
            "condition_type": params.condition_type.value,
            "threshold": params.threshold,
            "keyword": params.keyword,
        }
    )
    condition_desc = {
        "sentiment_below": f"Ø-Sentiment < {params.threshold}",
        "sentiment_above": f"Ø-Sentiment > {params.threshold}",
        "volume_above": f"Artikelanzahl > {int(params.threshold or 0)}",
        "keyword_found": f"Schluesselwort {params.keyword} gefunden",
    }.get(params.condition_type.value, params.condition_type.value)
    return (
        f"Alert erstellt: **{params.name}**\n\n"
        f"- **ID:** `{alert_id}`\n- **Entitaet:** {params.entity}\n"
        f"- **Bedingung:** {condition_desc}\n"
        f"- **Zeitfenster:** {params.days_back} Tage | **Quellen:** {params.source_country}\n\n"
        f"news_alert_check aufrufen um den Alert zu pruefen."
    )


@mcp.tool(
    name="news_alert_list",
    annotations={
        "title": "Alerts auflisten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
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
        condition_desc = {
            "sentiment_below": f"Sentiment < {a.get('threshold')}",
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
        lines.append(
            f"**Zeitfenster:** {a.get('days_back')} Tage | **Quellen:** {a.get('source_country')} | **Sprache:** {a.get('language')}"
        )
        lines.append(
            f"**Letzte Pruefung:** {last_checked} | **Letzter Alarm:** {last_triggered} | **Ausloesungen:** {trigger_count}"
        )
    lines.append(f"\n---\n*Alerts gespeichert in: `{ALERTS_FILE}`*")
    return "\n".join(lines)


@mcp.tool(
    name="news_alert_check",
    annotations={
        "title": "Alerts pruefen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
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
    if not api_key:
        return _no_key_message("news_alert_check")
    alerts_to_check = [_alert_manager.get(params.alert_id)] if params.alert_id else _alert_manager.list_all()
    alerts_to_check = [a for a in alerts_to_check if a is not None]
    if not alerts_to_check:
        return "Keine Alerts zu pruefen.\n" + (
            f"Alert-ID {params.alert_id} nicht gefunden."
            if params.alert_id
            else "Mit news_alert_create einen Alert erstellen."
        )
    results = []
    for alert in alerts_to_check:
        latest_dt = datetime.now()
        earliest_dt = latest_dt - timedelta(days=alert.get("days_back", 7))
        p: dict[str, Any] = {
            "text": alert["entity"],
            "language": alert.get("language", "de"),
            "number": 20,
            "earliest-publish-date": earliest_dt.strftime("%Y-%m-%d 00:00:00"),
            "latest-publish-date": latest_dt.strftime("%Y-%m-%d 23:59:59"),
            "sort": "publish-time",
            "sort-direction": "DESC",
        }
        if alert.get("source_country"):
            p["source-country"] = alert["source_country"]
        try:
            r = await _get_client().get("/search-news", params=p, headers=_auth_headers(api_key))
            r.raise_for_status()
            data = r.json()
            articles = data.get("news", [])
            avg_sentiment = _calc_avg_sentiment(articles)
            triggered, reason = _alert_manager.evaluate_condition(alert, articles, avg_sentiment)
        except Exception as e:
            results.append(
                {
                    "alert": alert,
                    "triggered": False,
                    "reason": f"API-Fehler: {_handle_api_error(e)}",
                    "articles_count": 0,
                    "avg_sentiment": None,
                }
            )
            _alert_manager.mark_checked(alert["id"], triggered=False)
            continue
        _alert_manager.mark_checked(alert["id"], triggered=triggered)
        results.append(
            {
                "alert": alert,
                "triggered": triggered,
                "reason": reason,
                "articles_count": len(articles),
                "avg_sentiment": avg_sentiment,
                "top_articles": articles[:3],
            }
        )
    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "geprueft": len(results),
                "ausgeloest": sum(1 for r in results if r["triggered"]),
                "ergebnisse": [
                    {
                        "id": r["alert"]["id"],
                        "name": r["alert"]["name"],
                        "triggered": r["triggered"],
                        "reason": r["reason"],
                        "artikel_anzahl": r["articles_count"],
                        "avg_sentiment": round(r["avg_sentiment"], 3) if r["avg_sentiment"] is not None else None,
                    }
                    for r in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    triggered_count = sum(1 for r in results if r["triggered"])
    lines = [
        f"## Alert-Check: {len(results)} geprueft | {triggered_count} ausgeloest\n",
        f"*Zeitpunkt: {datetime.now().strftime('%d.%m.%Y %H:%M')}*\n",
    ]
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
        lines.append(
            f"**Artikel:** {count} | **Ø-Sentiment:** {f'{avg:.3f}' if avg is not None else 'n/a'} ({_sentiment_label(avg)})"
        )
        if triggered and result.get("top_articles"):
            lines.append("\n**Top-Artikel:**")
            for art in result["top_articles"]:
                s = art.get("sentiment")
                s_str = f" ({s:.2f})" if s is not None else ""
                lines.append(f"- [{art.get('title', 'n/a')}]({art.get('url', '#')}){s_str}")
    return "\n".join(lines)


@mcp.tool(
    name="news_alert_delete",
    annotations={
        "title": "Alert loeschen",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
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
    if not params.confirm:
        return (
            f"Bestaetigung erforderlich: Alert **{name}** (`{params.alert_id}`) wird permanent geloescht. "
            f"Erneut mit `confirm=true` aufrufen."
        )
    if _alert_manager.delete(params.alert_id):
        return (
            f"Alert **{name}** (`{params.alert_id}`) geloescht.\nVerbleibende Alerts: {len(_alert_manager.list_all())}"
        )
    return f"Fehler beim Loeschen von Alert {params.alert_id}."
