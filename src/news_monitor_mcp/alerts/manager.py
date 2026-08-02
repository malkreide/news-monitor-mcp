"""Persistenter Alert-Store mit crash-sicheren Writes, Retention und Path-Hardening.

Behebt mehrere Audit-Findings (alle Audit 2026-05-13):
    SEC-ALERTS-PATH    — `_resolve_alerts_path` + `_ensure_secure_perms`
    ARCH-CONCURRENCY   — `_atomic_write_json` + `_file_lock` + `threading.RLock`
    CH-DSG             — `_prune_old_alerts` mit MCP_ALERT_RETENTION_DAYS-Env
"""

import json
import os
import tempfile
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Iterator, Optional

from news_monitor_mcp.logging_setup import logger

ALERTS_DIR_DEFAULT = os.path.expanduser("~/.news-monitor-mcp")

ALERT_RETENTION_DAYS_DEFAULT = 90


def _get_alert_retention_days() -> int:
    """Liest `MCP_ALERT_RETENTION_DAYS` aus dem Env. `0` deaktiviert Retention."""
    raw = os.environ.get("MCP_ALERT_RETENTION_DAYS")
    if raw is None:
        return ALERT_RETENTION_DAYS_DEFAULT
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "MCP_ALERT_RETENTION_DAYS=%r ist keine Zahl – fallback auf %d Tage", raw, ALERT_RETENTION_DAYS_DEFAULT
        )
        return ALERT_RETENTION_DAYS_DEFAULT
    return max(value, 0)


def _resolve_alerts_path() -> str:
    """Resolve und härte den Pfad zu alerts.json.

    Env-Präzedenz:
      NEWS_MONITOR_ALERTS_FILE  – expliziter Dateipfad (Back-Compat).
      NEWS_MONITOR_ALERTS_DIR   – Verzeichnis; File ist `<dir>/alerts.json`.
      sonst                     – `~/.news-monitor-mcp/alerts.json`.

    Security-Checks:
      * Pfad muss nach `os.path.normpath` lexikalisch unverändert sein.
      * Parent-Verzeichnis darf kein Symlink sein.
    """
    raw_file = os.environ.get("NEWS_MONITOR_ALERTS_FILE")
    if raw_file:
        candidate = os.path.expanduser(raw_file)
    else:
        base = os.environ.get("NEWS_MONITOR_ALERTS_DIR")
        base_dir = os.path.expanduser(base) if base else ALERTS_DIR_DEFAULT
        candidate = os.path.join(base_dir, "alerts.json")

    abspath = os.path.abspath(candidate)
    if abspath != os.path.normpath(abspath):
        raise RuntimeError(f"alerts path contains '..' after normalization: {candidate}")

    parent = os.path.dirname(abspath) or "."
    if os.path.lexists(parent):
        parent_real = os.path.realpath(parent)
        if parent_real != parent:
            raise RuntimeError(
                f"alerts parent dir is a symlink: {parent} -> {parent_real}; "
                "set NEWS_MONITOR_ALERTS_DIR to a non-symlinked directory"
            )
    return abspath


def _ensure_secure_perms(path: str) -> None:
    """Best-effort: 0o700 auf das Alerts-Verzeichnis, 0o600 auf alerts.json."""
    parent = os.path.dirname(path)
    if parent and os.path.isdir(parent):
        try:
            os.chmod(parent, 0o700)
        except OSError:
            pass
    if os.path.isfile(path):
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


ALERTS_FILE = _resolve_alerts_path()


try:
    import fcntl as _fcntl  # POSIX only
except ImportError:  # pragma: no cover - Windows
    _fcntl = None  # type: ignore[assignment]


@contextmanager
def _file_lock(path: str) -> Iterator[None]:
    """Cross-process advisory lock auf einem Lock-Sidecar-File.

    POSIX: nutzt fcntl.flock(LOCK_EX). Windows / unsupported FS: degradiert zu
    No-Op — in-process threading.RLock greift dann als einzige Serialisierung.
    """
    if _fcntl is None:
        yield
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    lock_path = path + ".lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        _fcntl.flock(fd, _fcntl.LOCK_EX)
        yield
    finally:
        try:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _atomic_write_json(path: str, payload: Any) -> None:
    """Atomic write via tempfile + fsync + os.replace.

    Vorgehen:
      1. NamedTemporaryFile im selben Verzeichnis (gleicher Mountpoint).
      2. JSON schreiben, flush, fsync.
      3. os.replace überschreibt das Ziel atomar.

    Crash zwischen Schritt 2 und 3 laesst die ALTE Datei intakt.
    """
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".alerts-", suffix=".json.tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class AlertManager:
    """Persistenter Alert-Store mit Crash-sicheren Writes.

    Concurrency-Modell:
      * In-Process: `threading.RLock` serialisiert alle Mutationen.
      * Cross-Process: optionaler `fcntl.flock` auf `<file>.lock` (POSIX).
      * Crash-Safety: atomic write (tmp → fsync → os.replace).

    Retention: Alerts mit `created_at` aelter als `retention_days` werden
    beim Start gepruned. Die Frist startet bei `created_at`, NICHT bei
    `last_triggered` (Privacy-Invariante per CH-DSG).
    """

    def __init__(self, file_path: str = ALERTS_FILE, retention_days: Optional[int] = None) -> None:
        self._file = file_path
        self._alerts: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._retention_days = retention_days if retention_days is not None else _get_alert_retention_days()
        self._load()
        pruned = self._prune_old_alerts()
        if pruned:
            logger.info("Alert-Retention: %d Alerts aelter als %d Tage geloescht", pruned, self._retention_days)
            self._save()
        _ensure_secure_perms(self._file)

    def _prune_old_alerts(self) -> int:
        """Loescht Alerts deren `created_at` aelter als `retention_days` ist."""
        with self._lock:
            if self._retention_days <= 0:
                return 0
            cutoff = datetime.now() - timedelta(days=self._retention_days)
            to_remove = []
            for alert_id, alert in self._alerts.items():
                created_raw = alert.get("created_at")
                if not created_raw:
                    continue
                try:
                    created = datetime.fromisoformat(created_raw)
                except ValueError:
                    continue
                if created < cutoff:
                    to_remove.append(alert_id)
            for alert_id in to_remove:
                del self._alerts[alert_id]
            return len(to_remove)

    def _load(self) -> None:
        if os.path.exists(self._file):
            try:
                with open(self._file, encoding="utf-8") as f:
                    self._alerts = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._alerts = {}

    def _save(self) -> None:
        try:
            with _file_lock(self._file):
                _atomic_write_json(self._file, self._alerts)
            _ensure_secure_perms(self._file)
        except OSError as e:
            logger.error("Alert-Datei konnte nicht gespeichert werden: %s", e)

    def create(self, data: dict[str, Any]) -> str:
        with self._lock:
            alert_id = f"alert_{uuid.uuid4().hex[:8]}"
            self._alerts[alert_id] = {
                **data,
                "id": alert_id,
                "created_at": datetime.now().isoformat(),
                "last_checked": None,
                "last_triggered": None,
                "trigger_count": 0,
            }
            self._save()
            return alert_id

    def list_all(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._alerts.values())

    def get(self, alert_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            alert = self._alerts.get(alert_id)
            return dict(alert) if alert is not None else None

    def delete(self, alert_id: str) -> bool:
        with self._lock:
            if alert_id in self._alerts:
                del self._alerts[alert_id]
                self._save()
                return True
            return False

    def mark_checked(self, alert_id: str, triggered: bool) -> None:
        with self._lock:
            if alert_id in self._alerts:
                self._alerts[alert_id]["last_checked"] = datetime.now().isoformat()
                if triggered:
                    self._alerts[alert_id]["last_triggered"] = datetime.now().isoformat()
                    self._alerts[alert_id]["trigger_count"] = self._alerts[alert_id].get("trigger_count", 0) + 1
                self._save()

    def evaluate_condition(
        self, alert: dict[str, Any], articles: list[dict[str, Any]], avg_sentiment: Optional[float]
    ) -> tuple[bool, str]:
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
            matches = [
                a
                for a in articles
                if keyword in (a.get("title") or "").lower() or keyword in (a.get("summary") or "").lower()
            ]
            if matches:
                return True, f"Schluesselwort <<{keyword}>> in {len(matches)} Artikel(n) gefunden"
            return False, f"Schluesselwort <<{keyword}>> nicht gefunden"
        return False, f"Unbekannter Condition-Typ: {condition}"
