# Datenschutz-Hinweis (revDSG) — news-monitor-mcp

Dieses Dokument adressiert die Anforderungen des **revidierten Schweizer Datenschutzgesetzes** (revDSG, in Kraft seit 1.9.2023) für Behörden und Organisationen, die `news-monitor-mcp` produktiv einsetzen. Es ergänzt die [ISDS-Klassifikation](isds-klassifikation.md) und ist Voraussetzung für rechtskonformen Einsatz, insbesondere im Schweizer Verwaltungskontext.

> **Wichtig:** Der Maintainer dieses Projekts ist **nicht** Verantwortlicher im Sinne des DSG für die Daten, die Endkunden mit dem Server verarbeiten. Verantwortlicher ist die Organisation, die den Server hostet und mit Anfragen befüllt. Dieses Dokument ist eine **Hilfestellung**, kein Rechtsgutachten.

## 1. Rolle der Beteiligten

| Rolle (DSG) | Wer |
|---|---|
| **Verantwortlicher** (Art. 5 lit. j DSG) | Die Behörde / Organisation, die den Server hostet und Suchanfragen formuliert |
| **Auftragsbearbeiter** (Art. 5 lit. k DSG) | [WorldNewsAPI](https://worldnewsapi.com) (USA) — verarbeitet jede Suchanfrage |
| **Drittland-Empfänger** (Art. 16 DSG) | WorldNewsAPI (USA) |
| **Software-Anbieter** | malkreide (MIT-Lizenz, keine Verantwortlichen-Rolle) |

## 2. Verarbeitete Personendaten

Der Server selbst speichert **keine** Personendaten der Nutzer:innen. **Indirekt** können jedoch Personendaten verarbeitet werden:

- **Abfrage-Strings:** `entity`, `query`, `location`, `keyword` können Personennamen oder Identifikatoren enthalten (z. B. *"Schulamt Zürich"*, *"Frau Müller"*, *"Direktor X"*).
- **Artikel-Inhalte:** WorldNewsAPI liefert journalistische Texte zurück, die Personendaten enthalten können (Politikernamen, Quotierungen, etc.).
- **Alert-Konfigurationen** (`alerts.json`): persistieren `entity`-Strings — also potenziell Personendaten — im Klartext auf dem Server-Host.
- **Cache (in-memory):** spiegelt zwischenzeitlich die obigen Daten.

## 3. Rechtsgrundlagen

Der Server selbst legt **keine** Rechtsgrundlage fest. Die Organisation muss vor produktivem Einsatz prüfen:

- **Öffentliches Interesse / Aufgabenerfüllung** (Art. 6 Abs. 2 lit. e DSG für Behörden; meist über kantonale IDG/IDV)
- **Berechtigtes Interesse** (Art. 31 Abs. 1 lit. d DSG für Private)
- **Einwilligung** (Art. 6 Abs. 6 DSG) — selten praktikabel bei Medien-Monitoring

## 4. Auftragsbearbeitungsvertrag (ADV / DPA)

Bevor Sie produktiv Anfragen mit Personenbezug stellen, müssen Sie **selbst** einen Auftragsbearbeitungsvertrag (engl. Data Processing Agreement) mit WorldNewsAPI abschliessen. Inhaltlich nach Art. 9 DSG:

- Zweck und Dauer der Bearbeitung
- Datenkategorien
- Pflichten des Auftragsbearbeiters (Vertraulichkeit, technisch-organisatorische Massnahmen, Sub-Auftragsbearbeiter, Mitwirkung bei Betroffenenrechten, Löschung am Ende des Vertrags)
- Recht auf Audit / Kontrolle

WorldNewsAPI hat kein öffentlich publiziertes Standard-DPA — Sie müssen ggf. eines anfragen oder eigene Standardklauseln vorlegen. Bei Ablehnung der DPA: **kein produktiver Einsatz mit Personenbezug**.

## 5. Drittlandtransfer (Art. 16 DSG)

WorldNewsAPI ist in den USA ansässig. Der Schweizer Bundesrat hat den USA mit dem **Swiss-US Data Privacy Framework (DPF)** einen Angemessenheits-Beschluss erteilt — wirksam, sofern der konkrete Empfänger im DPF zertifiziert ist:

- Prüfen Sie auf [www.dataprivacyframework.gov](https://www.dataprivacyframework.gov), ob WorldNewsAPI (Firmensitz "ddsky") als Teilnehmer gelistet ist.
- Falls **nein**: Übermittlung nur möglich auf Basis der **Standardvertragsklauseln des EDÖB** oder einer Ausnahme nach Art. 17 DSG (z. B. ausdrückliche Einwilligung).
- Bei kantonalen Behörden gelten zusätzlich die kantonalen Drittlands-Regeln (z. B. § 18 IDG ZH).

## 6. Profiling (Art. 5 lit. f DSG)

> **Warnung:** Sentiment-Analysen auf eine **benannte Person** sind Profiling im Sinne des DSG.

`news_sentiment_monitor(entity="Frau Müller", ...)` ordnet einer namentlich genannten Person eine algorithmische Bewertung der medialen Tonalität zu. Das erfüllt die Definition: *"jede Art der automatisierten Bearbeitung von Personendaten [...], um persönliche Aspekte zu bewerten"*.

Gleiches gilt für `news_alert_create` mit `condition_type=sentiment_below/above` und `entity` mit Personenbezug.

**Pflichten bei Profiling:**

- **Informationspflicht** (Art. 19 DSG): Betroffene müssen über das Profiling informiert werden, ausser eine Ausnahme nach Art. 20 DSG greift.
- **Profiling mit hohem Risiko** (Art. 5 lit. g DSG): triggert eine **Datenschutz-Folgenabschätzung** (Art. 22 DSG), wenn Persönlichkeit oder Verhalten der Person umfassend bewertet wird.
- **Recht auf menschliches Eingreifen** (Art. 21 DSG) bei automatisierten Einzelentscheidungen — relevant, wenn Sentiment-Werte über z. B. personelle Massnahmen entscheiden würden. **Nicht in den Empfehlungs-Use-Cases dieses Servers.**

**Empfehlung des Maintainers:** Sentiment-Monitoring nur auf **Institutionen** und **Themen** richten, nicht auf einzelne Personen. Wenn Personenbezug unvermeidbar: vorgängige DSFA durchführen und dokumentieren.

## 7. Betroffenenrechte (Art. 25–29 DSG)

Da der Server keine personenbezogenen Profile aufbaut, sondern nur Konfigurations- und Cache-Daten hält, sind die folgenden Mechanismen vorgesehen:

| Recht | Umsetzung |
|---|---|
| **Auskunft** (Art. 25) | Verantwortliche Organisation muss `alerts.json` und Cache-Inhalt offenlegen können. `news_alert_list` liefert alle aktiven Alerts; `news_cache_stats` zeigt Cache-Inhalt nach Typ. |
| **Berichtigung** (Art. 32) | `news_alert_delete` + neu erstellen |
| **Löschung** (Art. 32) | `news_alert_delete` (Bestätigung erforderlich) + `news_cache_clear` |
| **Datenübertragbarkeit** (Art. 28) | `alerts.json` ist eine flache JSON-Datei und kann direkt exportiert werden |

## 8. Retention (Aufbewahrungsfristen)

Per Default löscht der Server Alerts älter als **90 Tage** automatisch beim Start. Konfigurierbar über die Env-Variable `MCP_ALERT_RETENTION_DAYS`:

- `MCP_ALERT_RETENTION_DAYS=90` (Default) — 90 Tage
- `MCP_ALERT_RETENTION_DAYS=30` — kürzere Frist
- `MCP_ALERT_RETENTION_DAYS=0` — Retention deaktiviert (manuell verwalten)

Die Frist beginnt mit dem `created_at`-Zeitstempel des Alerts. Bei `last_triggered`-Updates wird sie **nicht** zurückgesetzt — d. h. ein 91 Tage alter Alert, der gestern getriggert hat, wird beim nächsten Server-Start dennoch gelöscht.

Cache-Daten sind in-memory mit Tool-spezifischen TTLs (15 Min bis 24 h) und gehen bei Server-Restart verloren.

Server-Logs werden nicht vom Server selbst persistiert; Retention wird durch den Hosting-Provider (Render, Docker-Volume, etc.) bestimmt — **30 Tage** sind ein vernünftiger Default für Audit-Zwecke.

## 9. Konkrete Schritte vor produktivem Einsatz

1. **DSFA** durchführen, wenn Personenbezug in Abfragen erwartet wird (Art. 22 DSG).
2. **ADV** mit WorldNewsAPI abschliessen (Art. 9 DSG).
3. **Verzeichnis der Bearbeitungstätigkeiten** anlegen (Art. 12 DSG): Verantwortlicher, Bearbeitungszweck, Datenkategorien, Empfänger (inkl. Drittland), Aufbewahrungsfrist, Sicherheitsmassnahmen.
4. **Informationspflicht** erfüllen (Art. 19 DSG): interne und ggf. externe Information.
5. **Drittland-Mechanismus** verifizieren (DPF-Listung oder Standardklauseln).
6. **Retention** konfigurieren (`MCP_ALERT_RETENTION_DAYS`) und dokumentieren.
7. **Audit-Logs** (siehe [`isds-klassifikation.md`](isds-klassifikation.md) §8) für 30 Tage aufbewahren.

## 10. Referenzen

- [revDSG (SR 235.1)](https://www.fedlex.admin.ch/eli/cc/2022/491/de) — Schweizer Datenschutzgesetz
- [DSV (SR 235.11)](https://www.fedlex.admin.ch/eli/cc/2022/568/de) — Datenschutzverordnung
- [EDÖB — Übersicht zum revDSG](https://www.edoeb.admin.ch/edoeb/de/home/datenschutz/dsg.html)
- [EDÖB — Leitfaden Datenschutz-Folgenabschätzung](https://www.edoeb.admin.ch/edoeb/de/home/datenschutz/grundlagen/datenschutz-folgenabschaetzung.html)
- [Swiss-US Data Privacy Framework](https://www.dataprivacyframework.gov/s/europe-and-switzerland)

## 11. Änderungshistorie

| Datum | Änderung |
|---|---|
| 2026-05-13 | Initial — Self-Assessment auf Basis des Audits 2026-05-13. Closes `CH-DSG`. |
