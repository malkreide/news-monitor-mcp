> ✅ **Re-Audit Status:** `closed` — gemerged via PR #5.

# Finding: ARCH-CONCURRENCY — Globale Mutables ohne Locking; Alert-File-TOCTOU

| Feld | Wert |
|---|---|
| **Severity** | **high** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | ARCH (Idempotency / Concurrency Safety) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

`server.py:201-202`:

```python
_cache = NewsCache()
_alert_manager = AlertManager()
```

Beide Singletons werden bei Modul-Import erzeugt. In `streamable-http`-Mode bedient FastMCP konkurrente Anfragen aus dem gleichen Asyncio-Eventloop:

- `NewsCache._store` (`server.py:60`) ist ein `dict`. `set` / `get` / `clear` sind nicht atomisch unter Asyncio-Cooperative-Cancellation (nicht Thread-Race, aber Re-Entry möglich).
- `AlertManager._save()` (`server.py:135-141`) liest `self._alerts`, ruft `json.dump`, schreibt. Wenn zwei `news_alert_create`-Aufrufe interleaven, geht eine Mutation verloren.
- Keine `asyncio.Lock`, kein File-Locking (`fcntl.flock`), kein Atomic-Write (`tempfile + os.rename`).

Zusätzlich `_client` (`server.py:216`) wird lazily erzeugt — `_get_client()` ist ein klassisches Double-Checked-Locking-Pattern ohne Lock; bei nebenläufigem Erst-Aufruf entstehen zwei `httpx.AsyncClient`-Instanzen (geringe Wahrscheinlichkeit, aber Ressourcen-Leak).

## Expected Behavior

- Locking pro mutable Singleton (`asyncio.Lock`).
- Atomic-Writes für `alerts.json` (write → fsync → rename).
- Lifespan-gebundene Client-Erzeugung statt Lazy-Singleton.

## Evidence

- `server.py:60` `self._store: dict[str, tuple[float, str, Any]] = {}` — kein Lock.
- `server.py:135-141` — kein Atomic-Rename, kein flock.
- `server.py:222-226` `_get_client()` — Race-Window.
- `server.py:143-149` `create()` schreibt direkt in self._alerts und ruft `_save()`; bei zwei parallelen `create()` mit demselben Manager kann die letzte Schreib-Operation die erste überschreiben (read-modify-write race).

## Risk Description

- **Alert-Loss:** Zwei parallele `news_alert_create`-Calls verlieren einen Alert. Schweregrad in stdio (single-client) niedrig; in HTTP-Mode mittel.
- **Korrupte JSON-Datei:** Crash zwischen `open(w)` und `json.dump` ⇒ leere oder halbe Datei ⇒ beim nächsten `_load()` fällt `AlertManager` auf `{}` zurück → **alle Alerts weg**.
- **Resource-Leak:** Doppelter httpx-Client behält offene Connections.

In Kombination mit Single-Process-Render-Deployment ist HTTP-Mode der hauptsächliche Risiko-Pfad.

## Remediation

```diff
+ import asyncio
+
  class NewsCache:
      def __init__(self) -> None:
          self._store: dict[str, tuple[float, str, Any]] = {}
+         self._lock = asyncio.Lock()
          ...
```

```diff
  class AlertManager:
      def __init__(self, file_path: str = ALERTS_FILE) -> None:
          self._file = file_path
          self._alerts: dict[str, dict[str, Any]] = {}
+         self._lock = asyncio.Lock()
          self._load()

      def _save(self) -> None:
-         os.makedirs(os.path.dirname(self._file), exist_ok=True)
-         with open(self._file, "w", encoding="utf-8") as f:
-             json.dump(self._alerts, f, indent=2, ensure_ascii=False)
+         os.makedirs(os.path.dirname(self._file), exist_ok=True)
+         tmp = self._file + ".tmp"
+         with open(tmp, "w", encoding="utf-8") as f:
+             json.dump(self._alerts, f, indent=2, ensure_ascii=False)
+             f.flush()
+             os.fsync(f.fileno())
+         os.replace(tmp, self._file)
```

Plus:

- `create() / delete() / mark_checked()` async machen und `async with self._lock:` umschliessen.
- `_get_client()` ersetzen durch FastMCP-Lifespan (siehe SDK-Finding).
- File-Lock (`fcntl.flock`) optional für Multi-Worker-Setup.

## Effort Estimate

**M** (1–2 Tage inkl. Tests).

## Dependencies / Blockers

Async-Umstellung der `AlertManager`-Methoden ist Breaking-Change in den Tests (z. B. `test_alert_manager_create_and_list`) → Tests müssen mit `pytest.mark.asyncio` migriert werden.

## Verification After Fix

- Test: 100 parallele `create()`-Tasks → `list_all()` enthält exakt 100 Einträge.
- Test: kill -9 simuliert mid-write (mit `pytest-mock`); nächster Load lädt entweder alten oder neuen State, nie korrupt.
