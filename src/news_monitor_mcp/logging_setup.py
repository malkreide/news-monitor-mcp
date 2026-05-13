"""Structured-Logging-Setup mit Request-ID-Propagation und Redaction-Pipeline.

Public surface:
    logger                 — Modul-Logger ("news-monitor-mcp")
    _request_id            — ContextVar, gesetzt durch RequestIdMiddleware
    add_redaction_pattern  — laufzeit-erweiterbare Mask-Pipeline
    configure_logging      — dictConfig-basiertes Setup, idempotent

Behebt Audit-Finding OBS-LOG-UNSTRUCTURED (medium, 2026-05-13). Liefert
ausserdem die Plattform für SEC-API-KEY-HANDLING's Mask-Filter.
"""

import json
import logging
import os
import re
from contextvars import ContextVar
from logging.config import dictConfig
from typing import Optional

logger = logging.getLogger("news-monitor-mcp")

_request_id: ContextVar[str] = ContextVar("request_id", default="-")

_redaction_patterns: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(api[-_]key=)[^&\s\"']+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(authorization:\s*bearer\s+)\S+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(x-api-key['\"]?\s*[:=]\s*['\"]?)[^\s,'\"}]+", re.IGNORECASE), r"\1***"),
]


def add_redaction_pattern(pattern: str, replacement: str = "***") -> None:
    """Registriert ein zusaetzliches Mask-Pattern fuer die Logging-Pipeline."""
    _redaction_patterns.append((re.compile(pattern), replacement))


def _redact(text: str) -> str:
    for pat, repl in _redaction_patterns:
        text = pat.sub(repl, text)
    return text


class _RequestIdFilter(logging.Filter):
    """Haengt jeden LogRecord mit der aktuellen request_id-ContextVar an."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


class _RedactionFilter(logging.Filter):
    """Maskiert sensitive Substrings (api-key, bearer-token) im final formatierten Output."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            try:
                record.args = tuple(_redact(a) if isinstance(a, str) else a
                                    for a in (record.args if isinstance(record.args, tuple)
                                              else (record.args,)))
            except Exception:
                pass
        return True


class _JsonFormatter(logging.Formatter):
    """Minimaler JSON-Formatter ohne externe Dependencies."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "lvl": record.levelname,
            "logger": record.name,
            "rid": getattr(record, "request_id", "-"),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: Optional[str] = None) -> None:
    """Initialisiert strukturiertes JSON-Logging mit Request-ID und Mask-Filter.

    Idempotent: mehrfache Aufrufe ueberschreiben das Setup ohne Handler-Leck.
    `httpx`/`httpcore` werden defensiv auf WARNING gesetzt, damit Request-URLs
    (inkl. api-key-Query) nicht im DEBUG-Log landen, selbst wenn der Mask-Filter
    eine Edge-Case verpasst.
    """
    resolved = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {"()": _RequestIdFilter},
            "redact": {"()": _RedactionFilter},
        },
        "formatters": {
            "json": {"()": _JsonFormatter},
        },
        "handlers": {
            "stderr": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "formatter": "json",
                "filters": ["request_id", "redact"],
                "level": resolved,
            },
        },
        "root": {"handlers": ["stderr"], "level": resolved},
        "loggers": {
            "httpx": {"level": "WARNING", "propagate": True},
            "httpcore": {"level": "WARNING", "propagate": True},
            "uvicorn.access": {"level": "WARNING", "propagate": True},
        },
    })
