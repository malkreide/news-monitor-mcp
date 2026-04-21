# Use Cases & Examples — news-monitor-mcp

Hier finden Sie praxisnahe Anwendungsfälle für verschiedene Zielgruppen. Alle in diesem Server verwendeten Tools greifen auf die WorldNewsAPI zu und erfordern einen API-Key (`WORLD_NEWS_API_KEY`).

### 🏫 Bildung & Schule
Lehrpersonen, Schulbehörden, Fachreferent:innen

**Stimmungsbild zur eigenen Schule**
«Wie wurde die Volksschule Zürich in den letzten 30 Tagen in den Medien dargestellt und wie ist die Tonalität?»
→ `news_sentiment_monitor(entity="Volksschule Zürich", language="de", days_back=30)`
Warum nützlich: Schulbehörden erhalten sofort einen objektiven Überblick über die Medienpräsenz und Tonalität ihrer Einrichtung, um proaktiv auf Kritik reagieren zu können.

**Bildungsberichterstattung im Überblick**
«Erstelle ein wöchentliches Medien-Briefing zu den Themen Schuldigitalisierung, KI im Unterricht und Lehrermangel.»
→ `news_media_briefing(topics=["Schuldigitalisierung", "KI im Unterricht", "Lehrermangel"], language="de", days_back=7, source_country="ch")`
Warum nützlich: Fachreferent:innen und Schulleitungen bleiben ohne manuellen Rechercheaufwand über relevante bildungspolitische Themen informiert.

**Trends in der Bildung**
«Welche Themen dominieren aktuell die Bildungsberichterstattung in der Schweiz?»
→ `news_trend_radar(category="education", source_country="ch", language="de", days_back=7)`
Warum nützlich: Lehrpersonen und Bildungsplaner erkennen frühzeitig neue pädagogische oder schulpolitische Trends in der öffentlichen Diskussion.

### 👨‍👩‍👧 Eltern & Schulgemeinde
Elternräte, interessierte Erziehungsberechtigte

**Lokale Schulnachrichten verfolgen**
«Was berichten die Zeitungen aktuell über die Schulen in Winterthur?»
→ `news_geo_search(location="Winterthur", query="Schule", language="de", days_back=14)`
Warum nützlich: Eltern bleiben über Entwicklungen und Diskussionen informiert, die direkt die Schulen in ihrer eigenen Wohngemeinde betreffen.

**Hintergründe zu Schulreformen**
«Zeige mir aktuelle Artikel zum Thema Lehrplan 21 und Hausaufgaben aus Schweizer Quellen.»
→ `news_search(query="Lehrplan 21 Hausaufgaben", language="de", source_country="ch")`
Warum nützlich: Erziehungsberechtigte können sich rasch eine fundierte Meinung zu vieldiskutierten schulischen Themen bilden, die den Alltag ihrer Kinder prägen.

### 🗳️ Bevölkerung & öffentliches Interesse
Allgemeine Öffentlichkeit, politisch und gesellschaftlich Interessierte

**Tägliche Schweizer Schlagzeilen**
«Was sind die wichtigsten Schlagzeilen des heutigen Tages in der Schweiz?»
→ `news_top_headlines(source_country="ch", language="de", number=10)`
Warum nützlich: Bürger:innen erhalten einen schnellen und komprimierten Überblick über die relevantesten tagesaktuellen Ereignisse.

**Mediale Darstellung von politischen Vorlagen**
«Wie ist die aktuelle Medienstimmung bezüglich der BVG-Reform?»
→ `news_sentiment_monitor(entity="BVG-Reform", language="de", days_back=14, source_country="ch")`
Warum nützlich: Politisch Interessierte können vor Abstimmungen nachvollziehen, wie neutral, positiv oder kritisch ein Thema in den Leitmedien behandelt wird.

**Tageszeitungen im Blick**
«Zeige mir die heutigen Titelseiten der Schweizer Tageszeitungen.»
→ `news_front_pages(source_country="ch")`
Warum nützlich: Leser:innen können auf einen Blick vergleichen, welche Themen die verschiedenen Zeitungen priorisieren, und unterschiedliche Perspektiven erkennen.

### 🤖 KI-Interessierte & Entwickler:innen
MCP-Enthusiast:innen, Forscher:innen, Prompt Engineers, öffentliche Verwaltung

**Automatisierte Reputations-Alerts**
«Erstelle einen Alert, der mich warnt, wenn das Sentiment zum Begriff 'E-Voting Schweiz' in den Medien unter 0 fällt.»
→ `news_alert_create(name="E-Voting Reputationswarnung", entity="E-Voting Schweiz", condition_type="sentiment_below", threshold=0.0, language="de", source_country="ch")`
→ `news_alert_check()`
Warum nützlich: Entwickler:innen können proaktive Monitoring-Systeme bauen, die bei kritischen Reputationsverschiebungen automatisch auslösen.

**Kombination: Statistik und Medienresonanz**
«Zeige mir die BFS-Statistiken zur Jugendarbeitslosigkeit und suche anschliessend nach aktuellen Zeitungsartikeln zu diesem Thema.»
→ `get_bfs_data(...)` *(via [swiss-statistics-mcp](https://github.com/malkreide/swiss-statistics-mcp))*
→ `news_search(query="Jugendarbeitslosigkeit", language="de", source_country="ch")`
Warum nützlich: Zeigt die mächtige Kombination aus harten demografischen Fakten (Swiss Statistics MCP) und der aktuellen gesellschaftlichen Diskussion in den Medien.

**Kombination: Umweltdaten und Berichterstattung**
«Prüfe aktuelle Umweltdaten zur Luftqualität in der Schweiz und suche nach Medienberichten zu Feinstaub.»
→ `get_luftqualitaet_aktuell(...)` *(via [swiss-environment-mcp](https://github.com/malkreide/swiss-environment-mcp))*
→ `news_search(query="Feinstaub Luftqualität", language="de", source_country="ch")`
Warum nützlich: Demonstriert, wie sich Echtzeit-Sensordaten (Swiss Environment MCP) mit lokaler Reportage und Berichterstattung ergänzen lassen.

### 🔧 Technische Referenz: Tool-Auswahl nach Anwendungsfall

| Ich möchte… | Tool(s) | Auth nötig? |
| :--- | :--- | :--- |
| **nach bestimmten Stichworten in Nachrichten suchen** | `news_search` | Ja (API-Key) |
| **wissen, wie positiv/negativ über ein Thema berichtet wird** | `news_sentiment_monitor` | Ja (API-Key) |
| **die wichtigsten Schlagzeilen eines Landes sehen** | `news_top_headlines` | Ja (API-Key) |
| **ein wöchentliches Dossier zu mehreren Themen erstellen** | `news_media_briefing` | Ja (API-Key) |
| **Nachrichten aus einer bestimmten Stadt oder Region finden** | `news_geo_search` | Ja (API-Key) |
| **aktuelle Themen-Trends in einem Land erkennen** | `news_trend_radar` | Ja (API-Key) |
| **die Titelseiten von Tageszeitungen betrachten** | `news_front_pages` | Ja (API-Key) |
| **den gesamten Text eines bestimmten Artikels lesen** | `news_retrieve_article` | Ja (API-Key) |
| **benachrichtigt werden, wenn sich die Medienstimmung dreht** | `news_alert_create`, `news_alert_check` | Ja (API-Key) |
