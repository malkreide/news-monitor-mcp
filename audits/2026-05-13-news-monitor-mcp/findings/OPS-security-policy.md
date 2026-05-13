# Finding: OPS-SECURITY-POLICY — `SECURITY.md` fehlt; ruff-format-Check disabled

| Feld | Wert |
|---|---|
| **Severity** | **low** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | OPS (Documentation / CI-Quality) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

- Kein `SECURITY.md` (kein Disclosure-Kanal für Security-Issues).
- `.github/workflows/ci.yml:60-61` deaktiviert `ruff format --check` mit dem Kommentar "Refactoring ausstehend".
- Kein `CODEOWNERS`, kein `dependabot.yml`.
- README hat keinen Hinweis auf Reporting-Kanal für Vulns.

## Expected Behavior

- `SECURITY.md` mit Reporting-Mail / GitHub-Private-Vuln-Reporting-Hinweis.
- Aktiver `ruff format --check` in CI (oder begründete Ablehnung im Repo dokumentieren).
- `dependabot.yml` für Python-Deps + GitHub-Actions.

## Evidence

- `ls *.md` ⇒ kein `SECURITY.md`.
- `.github/workflows/ci.yml:60-61` Kommentar.

## Risk Description

- **Slow-Disclosure-Pfad:** Finder einer Schwachstelle (z.B. Quellen-Verifikation des SEC-HTTP-NO-AUTH-Findings) hat keinen klaren Kanal → öffentlicher Issue auf GitHub.
- **Dependency-Drift:** Ohne Dependabot bleiben transitiv-anfällige Versionen (httpx, pydantic) länger im Repo.
- **Format-Drift:** Disabled-Check führt zu uneinheitlichem Style; späterer Re-Enable braucht grosses Refactor-PR.

## Remediation

1. `SECURITY.md` (kurz):

```markdown
# Security Policy

Bitte melde Schwachstellen privat über GitHub Security Advisories oder per E-Mail an <…>.

Unterstützte Versionen: latest (main).
```

2. `.github/dependabot.yml` mit `pip` und `github-actions` weekly.
3. `ruff format src/` einmalig laufen lassen und Check wieder aktivieren.

## Effort Estimate

**S** (< 1 Tag).

## Verification After Fix

- `SECURITY.md` im Repo.
- `python -m ruff format --check src/` grün in CI.
- Dependabot generiert wöchentlich PRs.
