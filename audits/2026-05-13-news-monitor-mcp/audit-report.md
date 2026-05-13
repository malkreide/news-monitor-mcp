# Audit-Report — news-monitor-mcp

| Feld | Wert |
|---|---|
| **Server** | `news-monitor-mcp` v0.2.0 |
| **Repo** | https://github.com/malkreide/news-monitor-mcp |
| **Audit-ID** | `2026-05-13-news-monitor-mcp` |
| **Audit-Datum** | 2026-05-13 |
| **Branch** | `claude/audit-mcp-skill-a04O4` |
| **Methodik** | [mcp-audit-skill](https://github.com/malkreide/mcp-audit-skill) — 6-Step-Workflow, 68-Check-Katalog |
| **Production-Ready** | ❌ **Nein** (1 critical Finding offen) |

---

## 1. Executive Summary

`news-monitor-mcp` ist ein solides FastMCP-Server-Projekt mit klarem Schweizer Behörden-Use-Case und gepflegter Tool-Annotation (12/15 Tools `readOnlyHint`). Für den **stdio-Modus mit Claude Desktop** ist das aktuelle Sicherheitsprofil akzeptabel, da kein öffentlicher Angriffsvektor existiert. Für das **vom README beworbene `streamable-http`-Deployment auf Render.com** ist der Server hingegen **nicht produktionsreif**: der HTTP-Transport bindet auf `0.0.0.0` ohne jegliche Authentifizierung, was Quota-Diebstahl und Alert-Manipulation durch Unbekannte ermöglicht (SEC-HTTP-NO-AUTH, critical). Drei weitere `high`-Findings (API-Key-Handling, Concurrency-Safety, Storage-Skalierung) sowie ein `high` im Schweizer DSG-Compliance-Layer machen den Server für Behörden-Einsatz vorerst untauglich. Die Architektur ist mono-File (1130 LoC) und braucht moderate Modularisierung; die Test-Suite ist überdurchschnittlich gut.

**Kurzfazit:** Stdio → produktiv nutzbar mit Doku-Update. HTTP/Cloud → blockierte Freigabe bis SEC-HTTP-NO-AUTH und SEC-API-KEY-HANDLING behoben sind.

---

## 2. Profile Snapshot

Siehe [`profile.md`](profile.md). Kernpunkte:

- Transport: dual (`stdio` + `streamable-http`, Letzteres `0.0.0.0:8000`)
- Auth-Modell: **keines** auf MCP-Ebene
- Daten: öffentliche Journalistik; Personenbezug indirekt via Query/Alerts
- Write-Capability: lokal (Alert-File), kein externer Write
- Deployment-Ziele: Claude Desktop, Render.com, lokal

---

## 3. Applicability

Siehe [`applicability.md`](applicability.md). **62 / 68 Checks anwendbar.**

| Kategorie | Anwendbar | Befunde |
|---|---|---|
| ARCH | 12 | 3 |
| SDK | 5 | 2 |
| SEC | 20 | 5 |
| SCALE | 6 | 2 |
| OBS | 6 | 1 |
| HITL | 2 | 1 |
| CH | 8 | 2 |
| OPS | 3 | 1 |
| **Total** | **62** | **17** |

Nicht-anwendbar: OAuth-/PKCE-Checks (kein MCP-Auth implementiert) und HITL-Sampling-Checks für externe Writes (keine vorhanden).

---

## 4. Findings Overview

Nach Severity, dann Effort (S < 1 d, M = 1–3 d, L = 1–2 w):

| ID | Titel | Sev. | Eff. | Cat. | Datei |
|---|---|---|---|---|---|
| SEC-HTTP-NO-AUTH | Streamable-HTTP ohne Authentifizierung auf 0.0.0.0 | **critical** | M | SEC | [link](findings/SEC-http-no-auth.md) |
| SEC-API-KEY-HANDLING | API-Key als Klartext-Env + URL-Query-Param | **high** | S | SEC | [link](findings/SEC-api-key-handling.md) |
| ARCH-CONCURRENCY | Globale Mutables ohne Locking; TOCTOU bei alerts.json | **high** | M | ARCH | [link](findings/ARCH-concurrency.md) |
| SCALE-STATEFUL | In-Memory-State verhindert horizontale Skalierung | **high** | L | SCALE | [link](findings/SCALE-stateful-singletons.md) |
| CH-DSG | DSG/EDÖB-Kontext im Schulamt-Use-Case nicht adressiert | **high** | M | CH | [link](findings/CH-dsg-compliance.md) |
| SEC-ALERTS-PATH | Path-Injection-Vektor via `NEWS_MONITOR_ALERTS_FILE` | medium | S | SEC | [link](findings/SEC-alerts-path-injection.md) |
| SEC-ERROR-PASSTHROUGH | Unsanitisierte Exception-Strings im Tool-Output | medium | S | SEC | [link](findings/SEC-error-passthrough.md) |
| ARCH-MONOLITHIC | Gesamter Server in einer 1130-Zeilen-Datei | medium | M | ARCH | [link](findings/ARCH-monolithic-server.md) |
| SDK-LIFESPAN | Keine FastMCP-Lifespan; httpx-Client nie geschlossen | medium | S | SDK | [link](findings/SDK-lifespan-missing.md) |
| SDK-DEP-MISMATCH | `fastmcp` deklariert, aber `mcp.server.fastmcp` importiert | medium | S | SDK | [link](findings/SDK-dependency-mismatch.md) |
| SCALE-NO-DOCKERFILE | Container-Deployment dokumentiert, aber kein Dockerfile | medium | S | SCALE | [link](findings/SCALE-no-dockerfile.md) |
| OBS-LOG-UNSTRUCTURED | Logger ohne Konfiguration / Struktur / Trace-IDs | medium | M | OBS | [link](findings/OBS-logging-unstructured.md) |
| CH-ISDS | Fehlende ISDS-Klassifikation für Behörden-Einsatz | medium | S | CH | [link](findings/CH-isds-classification.md) |
| SEC-MD5 | `hashlib.md5` ohne `usedforsecurity=False` (FIPS-Issue) | low | S | SEC | [link](findings/SEC-md5-usage.md) |
| ARCH-TOOL-COUNT | README/Code-Inkonsistenz bei Tool-Anzahl (9 vs. 15) | low | S | ARCH | [link](findings/ARCH-tool-count-inconsistency.md) |
| HITL-DESTRUCTIVE | `news_alert_delete` / `news_cache_clear` ohne Confirm | low | S | HITL | [link](findings/HITL-destructive-tools.md) |
| OPS-SECURITY-POLICY | `SECURITY.md` fehlt; ruff-format-Check disabled | low | S | OPS | [link](findings/OPS-security-policy.md) |

---

## 5. Remediation-Plan

### Sprint 1 — "HTTP-Freigabe blockierend" (≈ 1 Woche)

Ziel: HTTP-Deployment auf Render.com darf produktiv freigegeben werden.

1. **SEC-HTTP-NO-AUTH** (M) — Bearer-Token-Middleware + Origin-Allowlist + README-Update.
2. **SEC-API-KEY-HANDLING** (S) — SecretStr, Header-Auth wenn von WorldNewsAPI unterstützt, Log-Mask-Filter.
3. **SEC-ERROR-PASSTHROUGH** (S) — Error-Sanitisierung; koppelt mit Mask-Filter.
4. **OBS-LOG-UNSTRUCTURED** (M) — strukturiertes Logging-Setup (Voraussetzung für sinnvolle Mask-Filter).
5. **SDK-DEP-MISMATCH** (S) — `pyproject.toml` korrigieren.

### Sprint 2 — "Concurrency & Storage" (≈ 1 Woche)

Ziel: HTTP-Mode auch unter Last und Multi-Replica stabil.

6. **ARCH-CONCURRENCY** (M) — asyncio.Lock + atomic write.
7. **SDK-LIFESPAN** (S) — FastMCP-Lifespan, kein Singleton-httpx-Client mehr.
8. **SEC-ALERTS-PATH** (S) — Path-Realpath-Check, 0o600-Mode.
9. **SCALE-NO-DOCKERFILE** (S) — `Dockerfile` + CI-Build.

### Sprint 3 — "Compliance & Modularität" (≈ 2 Wochen)

10. **CH-DSG** (M) — `PRIVACY-DSG.md`, Retention-Default, Profiling-Disclaimer.
11. **CH-ISDS** (S) — `docs/isds-klassifikation.md`.
12. **ARCH-MONOLITHIC** (M) — schrittweises Aufteilen in Module.
13. **SCALE-STATEFUL** (L) — Storage-Abstraktion (zunächst nur als Issue + Backlog).

### Sprint 4 — "Quality-of-Life" (≈ 2 Tage)

14. **ARCH-TOOL-COUNT** (S)
15. **HITL-DESTRUCTIVE** (S)
16. **SEC-MD5** (S)
17. **OPS-SECURITY-POLICY** (S)

**Effort-Aggregation:**

| Severity | Anz. | Σ Effort |
|---|---|---|
| critical | 1 | M |
| high | 3 | 1×S + 1×M + 1×L |
| medium | 9 | 5×S + 3×M |
| low | 4 | 4×S |
| **Total** | **17** | ≈ **3 Sprints** |

---

## 6. Audit-Metadaten

| Feld | Wert |
|---|---|
| Audit-Skill | mcp-audit-skill (Stand: main, geprüft 2026-05-13) |
| Catalog-Version | 68 Checks (ARCH 12 / SDK 5 / SEC 23 / SCALE 6 / OBS 6 / HITL 5 / CH 8 / OPS 3) |
| Audit-Modus | Static-Analysis + Source-Review, kein Live-Deployment-Test |
| Datenbasis | Branch `claude/audit-mcp-skill-a04O4`, Working-Tree clean |
| Geprüfte Dateien | `src/news_monitor_mcp/server.py` (1130 LoC), `pyproject.toml`, `tests/test_server.py`, `.github/workflows/*.yml`, `README.md`, `README.de.md`, `CHANGELOG.md` |
| Out-of-Scope | Live-Tests gegen WorldNewsAPI (kein API-Key vorhanden); kein dynamisches Fuzzing; keine Pentest-Ausführung gegen Render-Instanz |
| Re-Audit | nach Sprint 1 (kritische + high Findings) — empfohlen innerhalb 30 Tagen |

---

## 7. Sign-Off-Checkliste

- [ ] Maintainer reviewt Findings einzeln und markiert `accepted-risk` mit Begründung wo zutreffend.
- [ ] Sprint-1-PRs gemerged.
- [ ] Re-Audit ergibt 0 `critical` und 0 `high`.
- [ ] CHANGELOG dokumentiert Security-Hardening unter v0.3.0.
- [ ] PyPI-Release nur nach erfolgreichem Re-Audit.

---

*Bericht generiert mit dem mcp-audit-skill 6-Step-Workflow. Alle Zahlen in dieser Übersicht stammen aus `summary.json`.*
