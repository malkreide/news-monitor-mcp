"""In-Memory-TTL-Cache mit LRU-Cap pro Tool-Typ + Background-Sweep-Loop.

Public surface:
    CacheBackend                  — strukturelles Protocol fuer Backends
    NewsCache                     — Standard-Implementation (in-memory, OrderedDict)
    CACHE_TTL                     — TTLs in Sekunden pro Tool-Typ
    CACHE_MAX_PER_TYPE_DEFAULT    — Default-Cap
    CACHE_SWEEP_SECONDS_DEFAULT   — Default-Intervall fuer Background-Sweep
    _get_cache_max_per_type       — Env-Reader
    _get_cache_sweep_seconds      — Env-Reader
    _cache_sweep_loop             — Background-Eviction-Task fuer den Lifespan

Behebt Audit-Findings SCALE-STATEFUL (high, Roadmap Schritte 4+5) und
SEC-MD5 (low — sha256 statt md5 als Key-Hash).
"""

import asyncio
import hashlib
import json
import os
import time
from collections import OrderedDict
from typing import Any, Optional, Protocol

from news_monitor_mcp.logging_setup import logger

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

CACHE_MAX_PER_TYPE_DEFAULT = 1000
CACHE_SWEEP_SECONDS_DEFAULT = 300


def _get_cache_max_per_type() -> int:
    """Liest `MCP_CACHE_MAX_PER_TYPE` aus dem Env. `0` deaktiviert den Cap."""
    raw = os.environ.get("MCP_CACHE_MAX_PER_TYPE")
    if raw is None:
        return CACHE_MAX_PER_TYPE_DEFAULT
    try:
        value = int(raw)
    except ValueError:
        logger.warning("MCP_CACHE_MAX_PER_TYPE=%r keine Zahl – fallback auf %d", raw, CACHE_MAX_PER_TYPE_DEFAULT)
        return CACHE_MAX_PER_TYPE_DEFAULT
    return max(value, 0)


def _get_cache_sweep_seconds() -> int:
    """Liest `MCP_CACHE_SWEEP_SECONDS`. `0` deaktiviert den Background-Sweep."""
    raw = os.environ.get("MCP_CACHE_SWEEP_SECONDS")
    if raw is None:
        return CACHE_SWEEP_SECONDS_DEFAULT
    try:
        value = int(raw)
    except ValueError:
        logger.warning("MCP_CACHE_SWEEP_SECONDS=%r keine Zahl – fallback auf %d s", raw, CACHE_SWEEP_SECONDS_DEFAULT)
        return CACHE_SWEEP_SECONDS_DEFAULT
    return max(value, 0)


class CacheBackend(Protocol):
    """Schmale Schnittstelle für Cache-Implementierungen.

    Aktuell nur `NewsCache` (in-memory) — diese Protokoll-Definition existiert,
    damit ein späterer PR einen Redis-Backend nahtlos einklinken kann
    (siehe Finding `SCALE-STATEFUL`, Roadmap-Schritt 2).
    """

    def get(self, tool_type: str, params: dict[str, Any]) -> Optional[Any]: ...
    def set(self, tool_type: str, params: dict[str, Any], data: Any) -> None: ...
    def clear(self, tool_type: Optional[str] = None) -> int: ...
    def evict_expired(self) -> int: ...
    def stats(self) -> dict[str, Any]: ...


class NewsCache:
    """In-Memory-Cache mit TTL pro Tool-Typ und LRU-Cap pro Tool-Typ.

    Implementiert das `CacheBackend`-Protokoll.

    Speicher: `OrderedDict[key, (timestamp, tool_type, data)]`. Ein erfolgreicher
    `get()` ruft `move_to_end(key)` → klassische LRU-Ordnung. Bei `set()` wird
    geprueft, ob der Cap pro Tool-Typ ueberschritten waere; in dem Fall werden
    die am laengsten ungenutzten Eintraege desselben Typs verdraengt
    (Standard: 1000 Eintraege pro Typ, konfigurierbar via
    `MCP_CACHE_MAX_PER_TYPE`; `0` deaktiviert den Cap).

    Verhindert OOM bei Long-Running-Servern mit hoher Query-Diversitaet
    (Finding `SCALE-STATEFUL`, Schritt 5).
    """

    def __init__(self, max_per_type: Optional[int] = None) -> None:
        self._store: OrderedDict[str, tuple[float, str, Any]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evicted_by_cap = 0
        self._max_per_type = max_per_type if max_per_type is not None else _get_cache_max_per_type()

    def _make_key(self, tool_type: str, params: dict[str, Any]) -> str:
        # sha256 statt md5: kein FIPS-Block (RHEL/CentOS mit fips-mode) und keine
        # Bandit/ruff-S324-Warnung. Cache-Key ist kein Crypto-Use-Case, aber sha256
        # ist hier ohne messbare Performance-Kosten der saubere Default.
        raw = json.dumps({"t": tool_type, "p": params}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

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
        # LRU: most-recently-used wandert ans Ende der OrderedDict.
        self._store.move_to_end(key)
        self._hits += 1
        return data

    def set(self, tool_type: str, params: dict[str, Any], data: Any) -> None:
        key = self._make_key(tool_type, params)
        if key in self._store:
            self._store[key] = (time.time(), tool_type, data)
            self._store.move_to_end(key)
            return
        self._enforce_cap(tool_type)
        self._store[key] = (time.time(), tool_type, data)

    def _enforce_cap(self, tool_type: str) -> None:
        """Verdraengt LRU-Eintraege desselben Tool-Typs, bis Platz fuer einen
        neuen Eintrag da ist."""
        if self._max_per_type <= 0:
            return
        same_type_count = sum(1 for _, t, _ in self._store.values() if t == tool_type)
        if same_type_count < self._max_per_type:
            return
        to_evict = same_type_count - self._max_per_type + 1
        for k in list(self._store.keys()):
            if to_evict <= 0:
                break
            if self._store[k][1] == tool_type:
                del self._store[k]
                self._evicted_by_cap += 1
                to_evict -= 1

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
            "max_eintraege_pro_typ": self._max_per_type,
            "verdraengt_durch_cap": self._evicted_by_cap,
            "ttl_sekunden": CACHE_TTL,
        }


async def _cache_sweep_loop(cache: CacheBackend, interval_seconds: int) -> None:
    """Aktiver Hintergrund-Sweep, der periodisch abgelaufene Cache-Eintraege
    entfernt. Verhindert, dass `NewsCache._store` ueber Stunden mit toten
    Eintraegen voll laeuft, wenn `stats()` selten aufgerufen wird (das war
    bisher die einzige Eviction-Trigger-Stelle).

    Cancellation-clean: `CancelledError` wird durchgereicht.
    """
    while True:
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise
        try:
            removed = cache.evict_expired()
            if removed:
                logger.debug("cache sweep: %d abgelaufene Eintraege entfernt", removed)
        except Exception:  # noqa: BLE001
            logger.exception("cache sweep failed")
