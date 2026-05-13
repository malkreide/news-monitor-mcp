> ✅ **Re-Audit Status:** `closed` — gemerged via PR #8.

# Finding: SEC-ALERTS-PATH — Path-Injection-Vektor über `NEWS_MONITOR_ALERTS_FILE`

| Feld | Wert |
|---|---|
| **Severity** | **medium** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | SEC (Path Traversal / Untrusted Input) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

`src/news_monitor_mcp/server.py:55-56`:

```python
DEFAULT_ALERTS_FILE = os.path.expanduser("~/.news-monitor-mcp/alerts.json")
ALERTS_FILE = os.environ.get("NEWS_MONITOR_ALERTS_FILE", DEFAULT_ALERTS_FILE)
```

`AlertManager._save()` (`server.py:135-141`):

```python
os.makedirs(os.path.dirname(self._file), exist_ok=True)
with open(self._file, "w", encoding="utf-8") as f:
    json.dump(self._alerts, f, indent=2, ensure_ascii=False)
```

Pfad wird ohne Normalisierung / Allowlist verwendet. `os.makedirs(..., exist_ok=True)` erzeugt Verzeichnis-Hierarchie überall, wo der Prozess Schreibrechte hat.

## Expected Behavior

- Pfad gegen festen Basis-Pfad joinen und `os.path.realpath` verifizieren, dass das Resultat unter dem Basis-Pfad liegt.
- Bei HTTP-Deployment niemals User-Env an Datei-Pfade durchreichen; statt dessen pro Tenant ein isoliertes Verzeichnis.

## Evidence

- `server.py:55-56` — direkte `os.environ`-Übernahme
- `server.py:137` — `os.makedirs(os.path.dirname(self._file), exist_ok=True)` schreibt blind
- Keine `realpath`-Prüfung, keine Allowlist

## Risk Description

- **Lokal (stdio-Mode):** Wer das Env-Var setzen kann, kann sowieso bereits beliebige Files schreiben — Risk **niedrig**.
- **Cloud (Render):** Env-Vars werden im Container gesetzt; wenn ein anderer Prozess oder ein kompromittierter Build-Step das Env vor-platziert, kann Alerts-File auf `/etc/cron.d/foo` o. ä. zeigen. **Mittel**, weil Render-Container schreibgeschützte Bereiche hat, aber `/tmp`, `/app` und ähnliches überschreibbar sind.
- **Hauptrisiko:** Wenn der HTTP-Server ohne Auth (s. SEC-HTTP-NO-AUTH) zusätzlich noch durch ein Mis-Config in einem Multi-Tenant-Container läuft, können Alert-Files anderer Tenants überschrieben werden, wenn das Env-Var Default-mässig gesetzt wird.

## Remediation

```diff
+ ALERTS_BASE_DIR = os.path.expanduser(os.environ.get("NEWS_MONITOR_ALERTS_DIR", "~/.news-monitor-mcp"))
+
+ def _resolve_alerts_path() -> str:
+     base = os.path.realpath(ALERTS_BASE_DIR)
+     candidate = os.path.realpath(os.path.join(base, "alerts.json"))
+     if not candidate.startswith(base + os.sep):
+         raise RuntimeError("alerts path escapes base dir")
+     return candidate
+
+ ALERTS_FILE = _resolve_alerts_path()
- DEFAULT_ALERTS_FILE = os.path.expanduser("~/.news-monitor-mcp/alerts.json")
- ALERTS_FILE = os.environ.get("NEWS_MONITOR_ALERTS_FILE", DEFAULT_ALERTS_FILE)
```

Zusätzlich:

1. `os.makedirs(..., mode=0o700)` statt Default 0o777.
2. Datei mit `0o600` schreiben (`os.open` + `os.fchmod`).
3. In HTTP-Mode den Alert-Modus optional komplett deaktivieren (`MCP_DISABLE_ALERTS=1`) bis Multi-Tenant-Storage existiert.

## Effort Estimate

**S** (< 1 Tag).

## Dependencies / Blockers

Keine.

## Verification After Fix

- Pytest mit `NEWS_MONITOR_ALERTS_DIR=/tmp/x` und Versuch, `alerts.json` als `../../../etc/passwd` zu umgehen → `RuntimeError`.
- Stat-Check auf `alerts.json`: Mode == `0o600`.
