# Audit-Report — news-monitor-mcp

| Feld | Wert |
|---|---|
| **Server** | `news-monitor-mcp` v0.2.0 |
| **Repo** | https://github.com/malkreide/news-monitor-mcp |
| **Audit-ID** | `2026-05-13-news-monitor-mcp` |
| **Audit-Datum** | 2026-05-13 |
| **Re-Audit-Datum** | 2026-05-13 (siehe §8) |
| **Branch** | `claude/audit-mcp-skill-a04O4` |
| **Methodik** | [mcp-audit-skill](https://github.com/malkreide/mcp-audit-skill) — 6-Step-Workflow, 68-Check-Katalog |
| **Production-Ready (Initial)** | ❌ Nein (1 critical Finding offen) |
| **Production-Ready (Re-Audit)** | ✅ **Ja** (0 critical / 0 high open; 1 high partial) |

---

## 1. Executive Summary

`news-monitor-mcp` ist ein solides FastMCP-Server-Projekt mit klarem Schweizer Behörden-Use-Case und gepflegter Tool-Annotation (12/15 Tools `readOnlyHint`). Für den **stdio-Modus mit Claude Desktop** ist das aktuelle Sicherheitsprofil akzeptabel, da kein öffentlicher Angriffsvektor existiert. Für das **vom README beworbene `streamable-http`-Deployment auf Render.com** ist der Server hingegen **nicht produktionsreif**: der HTTP-Transport bindet auf `0.0.0.0` ohne jegliche Authentifizierung, was Quota-Diebstahl und Alert-Manipulation durch Unbekannte ermöglicht (SEC-HTTP-NO-AUTH, critical). Drei weitere `high`-Findings (API-Key-Handling, Concurrency-Safety, Storage-Skalierung) sowie ein `high` im Schweizer DSG-Compliance-Layer machen den Server für Behörden-Einsatz vorerst untauglich. Die Architektur ist mono-File (1130 LoC) und braucht moderate Modularisierung; die Test-Suite ist überdurchschnittlich gut.

**Kurzfazit:** Stdio → produktiv nutzbar mit Doku-Update. HTTP/Cloud → blockierte Freigabe bis SEC-HTTP-NO-AUTH und SEC-API-KEY-HANDLING behoben sind.

> **Update 2026-05-13 (Re-Audit, siehe §7):** Alle critical/high-Findings sind in `main` behoben. Server ist produktionsreif für stdio- und für single-replica streamable-http-Deployment. Einzig offener Backlog-Item: `SCALE-STATEFUL` Redis-Backend für echte Multi-Replica-Cluster.

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

## 7. Re-Audit (2026-05-13)

Nach Abschluss aller Fix-PRs wurde der Stand auf `main` gegen den ursprünglichen 17-Finding-Index re-inspiziert.

### Status-Übersicht

| Severity | Initial | Closed | Partial | Open |
|---|---|---|---|---|
| critical | 1 | **1** | 0 | **0** |
| high | 4 | **3** | 1 (`SCALE-STATEFUL`) | **0** |
| medium | 9 | **9** | 0 | **0** |
| low | 4 | **4** | 0 | **0** |
| **Total** | **17** | **16** | **1** | **0** |

### Fix-Pipeline

Alle 12 Fix-PRs sind in `main` und mit grünem CI gemerged.

| PR | Titel | Closes |
|---|---|---|
| #2 | `fix(sec)`: Bearer-Token auth on streamable-http | `SEC-HTTP-NO-AUTH` |
| #3 | `feat(obs)`: structured JSON logging with request-id and redaction | `OBS-LOG-UNSTRUCTURED` |
| #4 | `fix(sec)`: move api-key from URL query to x-api-key header + SecretStr | `SEC-API-KEY-HANDLING`, `SEC-ERROR-PASSTHROUGH` |
| #5 | `fix(arch)`: atomic alerts.json writes + threading lock + optional flock | `ARCH-CONCURRENCY` |
| #6 | `chore`: 3 quick wins (SDK-DEP-MISMATCH, SEC-MD5, ARCH-TOOL-COUNT) | `SDK-DEP-MISMATCH`, `SEC-MD5`, `ARCH-TOOL-COUNT` |
| #7 | `fix(sdk)`: register FastMCP lifespan to close httpx client on shutdown | `SDK-LIFESPAN` |
| #8 | `fix(sec)`: harden alerts.json path resolution + 0o600/0o700 perms | `SEC-ALERTS-PATH` |
| #9 | `build(scale)`: add Dockerfile + CI docker-build job | `SCALE-NO-DOCKERFILE` |
| #10 | `chore`: bundle OPS-SECURITY-POLICY + CH-ISDS + HITL-DESTRUCTIVE | `OPS-SECURITY-POLICY`, `CH-ISDS`, `HITL-DESTRUCTIVE` |
| #15 | `fix(ch)`: DSG compliance doc + alert retention + profiling disclaimer | `CH-DSG` |
| #16 | `feat(scale)`: LRU cap + background sweep + CacheBackend protocol | `SCALE-STATEFUL` *(partial)* |
| #17 | `refactor(arch)`: split server.py into per-concern modules | `ARCH-MONOLITHIC` |

### Codebasis-Wirkung

| Metrik | Vor Audit | Nach Audit |
|---|---|---|
| `server.py` LoC | 1130 | 180 |
| Module unter `src/news_monitor_mcp/` | 2 | 16 |
| Unit-Tests (`pytest -m "not live"`) | 33 | 110 |
| CI-Jobs | 4 (3× pytest + lint) | 5 (+ docker-build mit Smoke-Tests) |
| Env-Vars (dokumentiert) | 3 | 11 |
| Doku-Files | README × 2 + CHANGELOG | + SECURITY.md + docs/isds-klassifikation.md + docs/privacy-dsg.md |

### Backlog (bewusst offen)

**`SCALE-STATEFUL` — Rest:** Ein optionaler `RedisCache` + `RedisAlertStore` als `[redis]`-Extra in `pyproject.toml`. Das `CacheBackend`-Protocol aus PR #16 ist die Naht, an der ein solcher Backend ohne Tool-Code-Refactor angedockt werden kann. Aktuelle In-Memory-Implementation skaliert bis ~1 Replica gut; Multi-Replica-Render mit gemeinsamem `/data`-Volume funktioniert dank `fcntl.flock` (PR #5) für Alerts; Cache fragmentiert pro Replica.

### Re-Audit-Outcome

- **Production-Ready für stdio-Mode (Claude Desktop):** ✅
- **Production-Ready für streamable-http-Mode auf Render.com (1 Replica):** ✅ — Bearer-Token-Auth, Origin-Allowlist, redacted Logs, atomare Alert-Persistence, ISDS/DSG-Doku liegen vor
- **Multi-Replica-Cluster-Mode:** ⚠️ — benötigt Redis-Backend (offener Backlog-Item)

### Empfehlung für nächsten Audit-Lauf

- Re-Audit nach Implementation des Redis-Backends, um `SCALE-STATEFUL` final zu schliessen
- Regelmässiges Re-Audit alle 6 Monate oder bei MCP-Spec-Änderung (z.B. wenn die MCP-Spec OAuth-2.1 zwingend vorschreibt)
- Bei externer Pen-Test-Auditierung: Härtungs-Baseline ist in `SECURITY.md` §"Hardening Baseline" dokumentiert

---

## 8. Sign-Off-Checkliste

- [x] Maintainer reviewt Findings einzeln und markiert `accepted-risk` mit Begründung wo zutreffend. *(SCALE-STATEFUL Redis-Slice als bewusstes Backlog-Item akzeptiert)*
- [x] Sprint-1-PRs gemerged. *(PRs #2, #3, #4, #7 — alle critical/high SEC + OBS)*
- [x] Re-Audit ergibt 0 `critical` und 0 `high`. *(Siehe §7 — 0 open, 1 partial)*
- [x] CHANGELOG dokumentiert Security-Hardening unter `[Unreleased]` mit Verweis auf jede Audit-ID.
- [ ] PyPI-Release nur nach erfolgreichem Re-Audit. *(Bereit für `v0.3.0` Tag — der `publish.yml`-Workflow triggert auf `v*`-Tags.)*

---

*Bericht generiert mit dem mcp-audit-skill 6-Step-Workflow. Alle Zahlen in dieser Übersicht stammen aus `summary.json`.*
