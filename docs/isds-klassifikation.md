# ISDS-Klassifikation — news-monitor-mcp

Dieses Dokument liefert eine Schutzbedarfsfeststellung im Sinne eines **Informationssicherheits- und Datenschutzkonzepts (ISDS)** für den Einsatz von `news-monitor-mcp` in Schweizer Verwaltungsumgebungen. Es ergänzt das Audit unter [`audits/`](../audits/) und ist Voraussetzung für eine formelle Abnahme durch eine Behörde.

> **Status:** Self-Assessment des Maintainers, **nicht** durch eine offizielle Stelle zertifiziert. Behörden, die den Server einsetzen, müssen die Einschätzung gegen ihren eigenen Schutzbedarfs-Katalog (z. B. EDÖB-Leitfaden, ISO/IEC 27005) abgleichen.

## 1. Übersicht

| Feld | Wert |
|---|---|
| **Anwendung** | `news-monitor-mcp` (MCP-Server für globale Medienrecherche und Sentiment-Monitoring) |
| **Datenquelle** | [WorldNewsAPI](https://worldnewsapi.com) — Drittland (USA) |
| **Klassifikationsdatum** | 2026-05-13 |
| **Anwendbarer Rechtsrahmen** | revDSG (in Kraft seit 1.9.2023), EDÖB-Empfehlungen, kantonale IDG/IDV-Regelungen wo zutreffend |

## 2. Datenkategorien

| Datenkategorie | Klassifikation | Anmerkungen |
|---|---|---|
| **Inhaltsdaten** (Artikeltexte, Headlines, Zusammenfassungen) | öffentlich | Bereits publizierte Journalismus-Inhalte. Kein Personenbezug, sofern nicht im Originaltext enthalten. |
| **Abfragedaten** (`entity`, `query`, `location`-Parameter) | **intern, ggf. Personendaten** | Suchterm kann eine namentlich genannte Person oder Institution sein. Bei Sentiment-Monitoring auf einzelne Personen → **Profiling im Sinne von Art. 5 lit. f DSG**. |
| **Alert-Konfiguration** (`alerts.json`) | **intern, ggf. Personendaten** | Enthält `entity`-Strings im Klartext. Datei-Mode `0o600` per Default (siehe `SEC-ALERTS-PATH`). |
| **Konfigurationsdaten** (`WORLD_NEWS_API_KEY`, `MCP_BEARER_TOKEN`) | **vertraulich** | Geheimnisse. Niemals in Logs, niemals in Git. Maskierung im Logger ist aktiv (`OBS-LOG-UNSTRUCTURED`). |
| **Cache-Daten** (`NewsCache`) | wie Inhaltsdaten | In-Memory, kein persistenter Speicher. Wird beim Restart geleert. |
| **Server-Logs** | intern | JSON, strukturiert, automatische Redaction von `api-key=` und `Authorization: Bearer`. |

## 3. Schutzbedarfsfeststellung

Skala: **B** = gering bis mittel · **E** = erhöht · **W** = wesentlich · **H** = hoch.

| Aspekt | Schutzbedarf | Begründung |
|---|---|---|
| **Vertraulichkeit** | **B** | Inhalts- und Abfragedaten sind unkritisch. Konfigurationsdaten sind separat vertraulich und durch Auth/Mode-Bits geschützt. |
| **Integrität** | **B** | Sentiment-Werte und Trefferzahlen sind beratend, nicht entscheidungsbindend. `alerts.json`-Korruption ist durch atomic-write ausgeschlossen (`ARCH-CONCURRENCY`). |
| **Verfügbarkeit** | **B** | Recherche-Tool, kein Echtzeit-Service. Ausfall verzögert Briefings, ist aber nicht kritisch. Externe API-Quota kann zur Nicht-Verfügbarkeit führen. |
| **Authentizität / Nachvollziehbarkeit** | **B** | Strukturierte JSON-Logs mit Request-ID pro Aufruf (`OBS-LOG-UNSTRUCTURED`). Audit-Trail für 30 Tage empfohlen. |

## 4. Verarbeitungsorte und Datenflüsse

```
Behörden-Mitarbeiter:in
        │
        │  (a) Claude Desktop / claude.ai im Browser
        ▼
    MCP-Client (Schweiz / EU)
        │
        │  (b) stdio  oder  Streamable-HTTP (Bearer-Token-Auth, TLS-Pflicht)
        ▼
    news-monitor-mcp
        │
        │  (c) HTTPS, x-api-key-Header
        ▼
    WorldNewsAPI (USA — Drittland)
        │
        ▼
    Artikel-Indexe weltweit
```

| Schritt | Verarbeitungsort | Schutzmechanismus |
|---|---|---|
| (a) Eingabe | Lokal beim Mitarbeiter | OS-Login, Disk-Verschlüsselung |
| (b) MCP-Transport | stdio: lokal; HTTP: konfigurierbar (Schweiz/EU empfohlen) | Bearer-Token + TLS (TLS via Reverse-Proxy / Render) + Origin-Allowlist |
| (c) WorldNewsAPI | **USA (Drittland)** | TLS, API-Key im Header, ADV/DPA-Vertrag durch Endkunde mit WorldNewsAPI erforderlich |

## 5. Drittlandtransfer (Art. 16 DSG)

WorldNewsAPI verarbeitet Anfragen in den USA. Anwendbare Mechanismen:

- **Angemessenheitsbeschluss:** Schweiz–US Data Privacy Framework (für zertifizierte US-Unternehmen). WorldNewsAPI muss als Teilnehmer im DPF gelistet sein — durch Endkunde zu prüfen.
- **Standardvertragsklauseln (SCC):** Falls kein Angemessenheitsbeschluss greift, bilateral mit WorldNewsAPI zu schliessen.
- **Datenminimierung:** Abfragen werden so spezifisch wie möglich gestellt; keine Bulk-Übertragung personenbezogener Daten an die API.

## 6. Profiling-Hinweis (Art. 5 lit. f DSG)

> **Achtung:** `news_sentiment_monitor` und `news_alert_create` mit `condition_type=sentiment_*` können einer benannten Person eine algorithmische Bewertung ihrer "Tonalität in der Presse" zuordnen. Das **erfüllt den Tatbestand des Profilings** gemäss revDSG. Vor produktivem Einsatz:
>
> - **Datenschutz-Folgenabschätzung** gemäss Art. 22 DSG durchführen.
> - **Informationspflicht** (Art. 19 DSG) gegenüber Betroffenen prüfen.
> - **Zweckbindung:** Nutzung dokumentieren und auf konkrete, legitime Verwaltungszwecke beschränken.

## 7. Retention

| Datenart | Aufbewahrungsfrist | Löschmechanismus |
|---|---|---|
| Cache (in-memory) | Bis Server-Restart, max. 24 h (Tool-spezifische TTL) | Automatisch (`evict_expired`) |
| Alert-Konfigurationen | Solange aktiv konfiguriert | `news_alert_delete` |
| Server-Logs | Empfehlung: 30 Tage | Log-Rotation am Hosting-Provider |
| Persistente Personendaten | **Keine** im Server selbst | n/a — Server speichert keine Personendaten ausserhalb der frei gewählten `entity`/`keyword`-Strings in Alerts |

## 8. Kontrollen und Restrisiken

| Kontrolle | Status | Audit-Ref |
|---|---|---|
| Bearer-Token-Auth auf HTTP | ✅ implementiert | `SEC-HTTP-NO-AUTH` |
| API-Key im Header statt URL | ✅ implementiert | `SEC-API-KEY-HANDLING` |
| Strukturiertes Logging + Mask-Filter | ✅ implementiert | `OBS-LOG-UNSTRUCTURED` |
| Atomic Writes auf `alerts.json` | ✅ implementiert | `ARCH-CONCURRENCY` |
| `alerts.json` mit `0o600` | ✅ implementiert | `SEC-ALERTS-PATH` |
| Non-root Container | ✅ implementiert | `SCALE-NO-DOCKERFILE` |
| Origin-Allowlist (DNS-Rebinding) | ⚠️ optional, manuell zu setzen | `SEC-HTTP-NO-AUTH` |
| Multi-Replica-Konsistenz (Storage-Backend) | ❌ offen — In-Memory-Cache + lokales Alert-File | `SCALE-STATEFUL` (geplant) |
| Privacy-Notice / DSG-Compliance-Doku | ❌ offen | `CH-DSG` (geplant) |

## 9. Empfohlene Konfiguration für Behörden-Einsatz

```bash
# Pflicht
export WORLD_NEWS_API_KEY="..."
export MCP_BEARER_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

# Empfohlen
export MCP_ALLOWED_ORIGINS="https://claude.ai"
export NEWS_MONITOR_ALERTS_DIR="/var/lib/news-monitor-mcp"  # in Container: /data
export LOG_LEVEL="INFO"

# Hosting (mindestens)
# - TLS-Terminierung an Reverse-Proxy oder PaaS-Provider in CH/EU
# - Backup von $NEWS_MONITOR_ALERTS_DIR mit gleichem Schutzbedarf
# - Log-Forwarding in zentralisiertes SIEM mit 30-Tage-Retention
```

## 10. Änderungshistorie

| Datum | Änderung |
|---|---|
| 2026-05-13 | Initial — Self-Assessment auf Basis des Audits 2026-05-13 |
