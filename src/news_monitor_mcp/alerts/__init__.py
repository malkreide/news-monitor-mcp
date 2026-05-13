"""Alert-Persistence-Package.

Re-exports the public surface so callers can do
`from news_monitor_mcp.alerts import AlertManager, ALERTS_FILE, ...`
without knowing about the internal module layout.
"""

from news_monitor_mcp.alerts.manager import (
    ALERT_RETENTION_DAYS_DEFAULT,
    ALERTS_DIR_DEFAULT,
    ALERTS_FILE,
    AlertManager,
    _atomic_write_json,
    _ensure_secure_perms,
    _fcntl,
    _file_lock,
    _get_alert_retention_days,
    _resolve_alerts_path,
)

__all__ = [
    "ALERT_RETENTION_DAYS_DEFAULT",
    "ALERTS_DIR_DEFAULT",
    "ALERTS_FILE",
    "AlertManager",
    "_atomic_write_json",
    "_ensure_secure_perms",
    "_fcntl",
    "_file_lock",
    "_get_alert_retention_days",
    "_resolve_alerts_path",
]
