> ✅ **Re-Audit Status:** `closed` — gemerged via PR #15.

# Finding: CH-DSG — DSG/EDÖB-Kontext im Schulamt-Use-Case nicht adressiert

| Feld | Wert |
|---|---|
| **Severity** | **high** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | CH (Swiss Compliance — DSG, EDÖB-Empfehlungen) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

`README.md` bewirbt den Server explizit für Schweizer Behörden-Use-Cases:

- "How has the Schulamt Zürich been portrayed in media over the last 30 days?" (`README.md:27, 211`)
- "Schulamt / Institutional Communication", "City Administration / Location Research" (`README.md:209, 235`)
- Use-Cases involvieren namentliche Recherchen über Behörden, Personen und Institutionen.

Aber:

- Kein Hinweis auf Anwendbarkeit des Schweizer Datenschutzgesetzes (revDSG, in Kraft seit 1.9.2023).
- Kein Verzeichnis von Bearbeitungstätigkeiten (Art. 12 DSG) — auch nicht als Template.
- WorldNewsAPI ist Auftragsbearbeiter im DSG-Sinne. Keine Auftragsdatenbearbeitungs-Klausel (ADV/DPA-Verweis) im README.
- Bei `news_sentiment_monitor(entity="<Personenname>")` werden Personendaten in der Cache- und Alert-Datei gespeichert — ohne Hinweis auf Aufbewahrungsfristen, Löschpflichten oder Betroffenenrechte (Art. 25 ff. DSG).
- Alert-File `alerts.json` enthält den `entity`-Suchstring; bei "Person X bei Behörde Y" entsteht ein Profiling-Vektor.

## Expected Behavior

CH-Best-Practice für MCP-Server mit Schweizer Behörden-Use-Case:

1. **Privacy-Notice-Sektion** im README mit:
   - Verweis auf DSG-Art. 19 (Informationspflicht).
   - Verarbeitungszwecke und Rechtsgrundlage.
   - Hinweis: WorldNewsAPI als Drittland-Empfänger (USA) → Art. 16 DSG / Angemessenheits-Bescheid.
2. **Auftragsbearbeitungs-Hinweis:** Nutzer müssen mit WorldNewsAPI selbst eine ADV abschliessen (B2B-Customer-Pflicht).
3. **Retention-Default:** Alerts/Cache mit max-Aufbewahrung; Doku zur Löschung.
4. **EDÖB-Empfehlungen:** Hinweis auf EDÖB-Leitfaden für Cloud-Nutzung in Verwaltung.
5. **Profiling-Klausel:** Sentiment-Analyse auf Personen ist ein Profiling (Art. 5 lit. f DSG) — explizit warnen, dass Nutzung auf einzelne Personen rechtlich heikel ist.

## Evidence

- `README.md:283-294` "Data Privacy"-Abschnitt vorhanden, aber generisch ("No personal data stored") — falsch, sobald Personennamen als Query gespeichert werden (`alerts.json`, Cache-Keys via MD5 hashen die Query — Personenbezug bleibt indirekt rekonstruierbar).
- `server.py:144-149` `alert_id` + Daten in Klartext geschrieben.
- Kein `PRIVACY.md` / `DPA.md` im Repo.

## Risk Description

- **Behördliche Reputation:** Sobald ein Schulamt den Server produktiv einsetzt, bewegt es sich rechtlich auf dünnem Eis ohne Privacy-Folgenabschätzung (Art. 22 DSG).
- **Profiling-Falle:** Sentiment-Scoring auf benannte Personen kann als hochriskante Bearbeitung gelten → Folgenabschätzung wird Pflicht.
- **EDÖB-Beanstandung:** Bei Beschwerde fehlt jegliche Compliance-Dokumentation.
- **Drittlandtransfer:** WorldNewsAPI in USA — Adequacy-Beschluss / Standardklauseln nicht referenziert.

## Remediation

1. Neuer Abschnitt `PRIVACY-DSG.md` mit obigem Inhalt.
2. README-Disclaimer: "Nutzung mit Personenbezug (z.B. Sentiment-Monitoring einzelner Personen) erfordert vorab DSFA gemäss Art. 22 DSG."
3. Alert-File: `entity`-Feld optional hashed speichern, wenn `MCP_HASH_ENTITY=1`.
4. Retention-Default: Alerts älter als 90 Tage automatisch löschen (konfigurierbar).
5. Hinweis im README, dass User selbst einen ADV mit WorldNewsAPI abschliesst.

## Effort Estimate

**M** (1–3 Tage, primär Doku + leichte Code-Anpassung Retention).

## Dependencies / Blockers

Sollte mit juristischem Review (DSG-Expert·in) abgeglichen werden.

## Verification After Fix

- `PRIVACY-DSG.md` existiert, vom Maintainer signed-off.
- Retention-Test: `pytest tests/test_retention.py::test_old_alerts_pruned` grün.
