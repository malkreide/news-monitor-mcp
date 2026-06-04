# 🛡️ Sicherheitsrichtlinie & Sicherheitsstatus

[🇬🇧 English Version](SECURITY.md)

---

## Schwachstellen melden

Wenn Sie glauben, eine Sicherheitslücke in `news-monitor-mcp` gefunden zu haben, melden Sie diese bitte **privat** über GitHubs Funktion [Private Vulnerability Reporting](https://github.com/malkreide/news-monitor-mcp/security/advisories/new).

Bitte eröffnen Sie **kein** öffentliches GitHub-Issue und posten Sie keine Details in sozialen Medien, bevor der Maintainer die Möglichkeit zur Reaktion hatte.

### Was sollte enthalten sein

- Eine kurze Beschreibung des Problems und seiner möglichen Auswirkungen
- Schritte zur Reproduktion (Proof-of-Concept-Code, `curl`-Aufruf etc.)
- Die betroffene Version (`__version__` in `src/news_monitor_mcp/__init__.py` oder `pip show news-monitor-mcp`)
- Ob aus Ihrer Sicht ein koordinierter Offenlegungszeitplan erforderlich ist

### Erwartete Reaktionszeiten

- Eingangsbestätigung: innerhalb von **5 Arbeitstagen**
- Triage und Erstbewertung: innerhalb von **10 Arbeitstagen**
- Koordiniertes Offenlegungsfenster: typischerweise **90 Tage**, kürzer bei aktiv ausgenutzten Problemen

## Geltungsbereich

Dieses Projekt umfasst:

- Den MCP-Server selbst (`src/news_monitor_mcp/`)
- Das mitgelieferte `Dockerfile` und die CI-Workflows
- Die in `audits/` dokumentierten Schutzschichten (Auth, Redaction, atomare Schreibvorgänge, Path-Hardening)

**Ausserhalb des Geltungsbereichs:**

- Schwachstellen in [WorldNewsAPI](https://worldnewsapi.com/) — diese bitte direkt an WorldNewsAPI melden.
- Schwachstellen in Upstream-Abhängigkeiten (`mcp`, `httpx`, `pydantic`, `starlette`, `uvicorn`) — bitte Upstream melden; wir übernehmen Fixes via Dependabot.
- Probleme, die physischen oder lokalen Zugriff auf eine Entwicklermaschine mit stdio-Transport erfordern.

## Unterstützte Versionen

Der jeweils neueste Tag auf `main` wird unterstützt. Es gibt keinen LTS-Branch.

| Version | Unterstützt |
|---------|-------------|
| `main` / neuestes Release | ✅ |
| alles Ältere              | ❌ |

## Hardening-Baseline

`news-monitor-mcp` folgt den **SOLID-for-MCP**-Prinzipien. Konkret umgesetzte Massnahmen (mit Audit-ID-Referenzen):

- **Sandbox** — non-root Container, dedizierte UID `10001`, keine Shell, eingeschränkte Bind-Mounts (`SCALE-NO-DOCKERFILE`)
- **OAuth / Bearer Auth** — `MCP_BEARER_TOKEN` im HTTP-Modus zwingend (`SEC-HTTP-NO-AUTH`)
- **Least Privilege** — `alerts.json` mit `0o600`, Parent-Verzeichnis mit `0o700` (`SEC-ALERTS-PATH`)
- **Idempotenz** — atomare Schreibvorgänge via `fsync` + `os.replace` (`ARCH-CONCURRENCY`)
- **Defense in Depth** — `SecretStr`-API-Key, Header-Auth, Redaction-Filter, Origin-Allowlist (`SEC-API-KEY-HANDLING`, `OBS-LOG-UNSTRUCTURED`)

Die Audit-Historie liegt unter [`audits/`](audits/).
