"""Die 2 Cache-Admin-Tools: stats / clear.

Aufgeteilt vom Audit-Finding ARCH-MONOLITHIC (medium, 2026-05-13).
"""

from news_monitor_mcp.app import _cache, mcp
from news_monitor_mcp.cache import CACHE_TTL
from news_monitor_mcp.models import CacheClearInput


@mcp.tool(
    name="news_cache_stats",
    annotations={
        "title": "Cache-Statistiken",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def news_cache_stats() -> str:
    """Cache-Statistiken: Trefferquote, gespeicherte Eintraege, gesparte API-Calls.

    Returns:
        str: Cache-Uebersicht mit Hit-Rate, Eintraegen nach Typ und TTL-Konfiguration.
    """
    stats = _cache.stats()
    total_calls = stats["hits"] + stats["misses"]
    lines = [
        "## Cache-Statistiken\n",
        f"**Eintraege gesamt:** {stats['gesamt_eintraege']} | **Hit-Rate:** {stats['hit_rate']} | "
        f"**API-Calls gespart:** {stats['api_calls_gespart']}\n",
        f"**Hits:** {stats['hits']} | **Misses:** {stats['misses']} | **Total Abfragen:** {total_calls}\n",
    ]
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


@mcp.tool(
    name="news_cache_clear",
    annotations={
        "title": "Cache leeren",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def news_cache_clear(params: CacheClearInput) -> str:
    """Leert den Cache (vollstaendig oder fuer einen spezifischen Tool-Typ).

    Args:
        params (CacheClearInput): tool_type (leer = alles leeren)

    Returns:
        str: Anzahl geloeschter Cache-Eintraege.
    """
    if params.tool_type and params.tool_type not in CACHE_TTL:
        valid = ", ".join(f"'{k}'" for k in CACHE_TTL)
        return f"Unbekannter Tool-Typ '{params.tool_type}'. Erlaubt: {valid}"
    if not params.confirm:
        scope = f"Cache-Typ `{params.tool_type}`" if params.tool_type else "GESAMTE Cache"
        current_size = (
            sum(1 for _, (_, t, _) in _cache._store.items() if t == params.tool_type)
            if params.tool_type
            else len(_cache._store)
        )
        return (
            f"Bestaetigung erforderlich: {scope} wird geleert ({current_size} Eintraege betroffen). "
            f"Erneut mit `confirm=true` aufrufen."
        )
    if params.tool_type:
        count = _cache.clear(params.tool_type)
        return f"Cache fuer `{params.tool_type}` geleert: {count} Eintraege entfernt."
    count = _cache.clear()
    return f"Gesamter Cache geleert: {count} Eintraege entfernt."
