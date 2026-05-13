# Applicability Filter — news-monitor-mcp

Profil-Eingaben: dual-transport (stdio + http), no-MCP-auth, public-data + persisted-alerts, write-capable (lokal), CH-Kontext.

## Kategorien-Anwendbarkeit

| Kategorie | Anzahl | Anwendbar | Begründung |
|---|---|---|---|
| **ARCH** | 12 | **12** | Voll anwendbar. Tool-Design, Annotationen, Idempotenz, Repo-Struktur. |
| **SDK** | 5 | **5** | FastMCP-Server in Python → alle SDK-Checks relevant. |
| **SEC** | 23 | **20** | OAuth/PKCE-Checks (3) entfallen — Server hat kein MCP-Auth. Alle anderen SEC-Checks relevant, da HTTP-Transport in Production möglich. |
| **SCALE** | 6 | **6** | Streamable-HTTP-Deployment → Skalierungs-Checks gelten. |
| **OBS** | 6 | **6** | Voll anwendbar. |
| **HITL** | 5 | **2** | Server ist überwiegend read-only, kein destruktiver Daten-Eingriff in externe Systeme. Sampling-/Confirmation-Flows nur für Alerts und Cache-Clear minimal relevant. |
| **CH** | 8 | **8** | Schweizer Use-Cases (Schulamt Zürich, Volksschule) → DSG/EDÖB/ISDS-Layer gilt. |
| **OPS** | 3 | **3** | Voll anwendbar. |

**Total anwendbar:** 62 / 68 Checks.

## Nicht-Anwendbar (mit Begründung)

| Check-Bereich | Status | Begründung |
|---|---|---|
| OAuth 2.1 / PKCE / Resource Indicators (SEC-001 / SEC-002 / SEC-003 — approx.) | n/a | Server implementiert keine MCP-Auth. Wenn künftig auf Multi-Tenant-Cloud deployed, müssen diese Checks neu bewertet werden. |
| HITL Sampling für irreversible Writes (HITL-001 / HITL-002 — approx.) | n/a | Keine irreversiblen externen Writes. `news_alert_delete` und `news_cache_clear` haben `destructiveHint: true`, sind aber lokal-only und reversibel. |
| HITL Resource-Confirmation (HITL-003 — approx.) | n/a | Keine Resources exponiert. |

Die n/a-Markierungen sind konservativ: sobald HTTP-Transport öffentlich zugänglich gemacht wird (Render.com mit `claude.ai`-Anbindung), müssen die OAuth-Checks zwingend re-evaluiert werden — siehe SEC-Finding *No-Auth-HTTP-Transport*.
