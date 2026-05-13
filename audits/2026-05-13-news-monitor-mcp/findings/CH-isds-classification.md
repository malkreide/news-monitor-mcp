# Finding: CH-ISDS — Fehlende ISDS-Klassifikation für Behörden-Einsatz

| Feld | Wert |
|---|---|
| **Severity** | **medium** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | CH (ISDS — Informationssicherheits- und Datenschutz-Konzept) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

- Server wird für Schweizer Verwaltungs-Use-Cases beworben (Schulamt Zürich, Kanton Zürich-Use-Cases).
- Kein ISDS-Klassifikations-Tag im README ("öffentlich" / "intern" / "vertraulich" / "geheim").
- Keine Aussage zur Verarbeitungsumgebung (Cloud-Region, Datenflussdiagramm).
- README-Architektur-Diagramm (`README.md:163-170`) zeigt nur 3 Boxen — kein Datenflussdiagramm im ISDS-Sinne.

## Expected Behavior

Für Verwaltungs-Software in CH wird typischerweise ein ISDS-Klassifikationsblatt mitgeliefert:

- Schutzbedarf Vertraulichkeit / Integrität / Verfügbarkeit (B/E/W/H).
- Datenkategorien (Open Data, Personendaten, besonders schützenswerte PD).
- Verarbeitungsorte (Schweiz / EU / USA).
- Kommunikationswege (TLS-Anforderung).

## Evidence

- `README.md:160-170` — Architektur-Box ohne Klassifikation
- Kein `docs/isds.md` o.ä.

## Risk Description

- **Beschaffungs-Blocker:** Schweizer Verwaltungen können den Server formell nicht abnehmen ohne ISDS-Tag.
- **Risk-Aggregation:** Ohne Klassifikation wird gerne falsche Risiko-Annahme getroffen (z.B. "ist ja nur öffentliche News" → vergisst, dass die *Abfragen* Personenbezug haben).

## Remediation

`docs/isds-klassifikation.md` anlegen mit Default-Tabelle. Beispiel-Snippet:

```markdown
| Aspekt | Klassifikation |
|---|---|
| Inhaltsdaten | "öffentlich" (Journalismus) |
| Abfragedaten | "intern" (Personenbezug möglich) |
| Konfiguration | "vertraulich" (API-Key) |
| Schutzbedarf Vertraulichkeit | B (gering bis mittel) |
| Schutzbedarf Integrität | B |
| Schutzbedarf Verfügbarkeit | B |
| Verarbeitungsort | USA (WorldNewsAPI), Schweiz/EU (Hosting empfohlen) |
```

## Effort Estimate

**S** (< 1 Tag).

## Verification After Fix

- Datei existiert, vom Maintainer reviewt.
- Verknüpfung im README ("Compliance"-Sektion).
