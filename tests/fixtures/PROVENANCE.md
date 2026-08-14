# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-08-08** von `api.worldnewsapi.com`.

Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht
mehr zu unterscheiden — die Datei sieht gleich aus.

## Aufgezeichnet ist der Vertrag, nicht die Antwort

Die WorldNewsAPI verlangt einen Schluessel; ohne ihn gibt es keine
Antwort, die man datieren koennte. Aufzeichenbar ist trotzdem genau
das, woran fuenfzehn Werkzeuge haengen: **welche Routen das Gateway
fuehrt.** Es routet vor der Schluesselpruefung und unterscheidet
deshalb selbst zwischen «Route da, Schluessel fehlt» (401,
`application/json`) und «Route gibt es nicht» (404, Tomcat-HTML).

## Die Kontrollen gehoeren zur Messung

Ohne die beiden `kontrolle_*`-Zeilen belegte die Aufzeichnung nur,
dass jemand einen 401 bekommen hat; mit ihnen belegt sie, was das
Gateway unterscheidet.

Dass diese Unterscheidung ueberhaupt traegt, ist keine
Selbstverstaendlichkeit. Im selben Portfolio antwortet
`epl.bag.admin.ch` **auch** auf frei erfundene Pfade mit 401 — dort
sagt ein 401 nichts ueber den Bestand. Deshalb wird die Kontrolle bei
jedem Lauf mitgemessen, und das Skript bricht ab, wenn sie nicht mehr
traegt.

## `api_routen.json`

- **Quelle:** `https://api.worldnewsapi.com/…`
- **Aufgezeichnet:** 2026-08-08
- **Auswahl:** Statuscode und Content-Type je Pfad, ohne API-Key abgefragt — samt zweier Kontrollen mit erfundenen Pfaden. Erst die Kontrollen machen aus «ich bekomme 401» die Aussage «diese Route fuehrt das Gateway»: Es routet vor der Schluesselpruefung, also heisst 401 «Route da» und 404 «Route weg». Dass das traegt, ist nicht selbstverstaendlich — andere Gateways im selben Portfolio antworten auch auf erfundene Pfade mit 401
- **Groesse:** 1441 B
- **SHA-256:** `0c0406247f6feefe20297b65c19a827bd0c36ecdec1b0df82d4ea58490ca3baf`

## NICHT aufgezeichnet

### `search_news.json, top_news.json, …`

- **Quelle:** `https://api.worldnewsapi.com/search-news`
- **Grund:** WORLD_NEWS_API_KEY nicht gesetzt — die API antwortet ohne Schluessel mit HTTP 401. NICHT aufgezeichnet.

Die Antwort-Payloads stehen weiterhin als Literale im Testmodul.
Sie sind damit **ausgedacht** und tragen kein Datum — das ist der
Ist-Zustand und keine Nachlaessigkeit dieses Laufs. Wer einen
Schluessel hat, setzt `WORLD_NEWS_API_KEY` und laesst das Skript
erneut laufen.

## Query-Parameternamen — gemessen am 2026-08-14

Diese Pruefung stand hier lange als offen. Sie ist jetzt gefahren,
mit einem Schluessel, gegen die echte Quelle.

**Die Kontrolle zuerst, denn ohne sie belegt nichts davon etwas.**
Dieselbe Anfrage einmal mit einem erfundenen Parameter:

    ?text=Schule&language=de&number=5&<Fenster>
    ?text=Schule&language=de&number=5&<Fenster>&gibtsnichtxyz=quatsch

    beide: available 4885, identische fuenf IDs

**Die Quelle verwirft unbekannte Parameter still und antwortet mit
200.** Ein Statuscode sagt hier also nichts darueber, ob ein
Parameter wirkt — genau das Muster, an dem in `global-education-mcp`
zwei Filter wirkungslos waren. Jeder Parameter ist deshalb
differenziell gemessen: zwei Anfragen, die sich nur in ihm
unterscheiden, und ein Vergleich der Antworten.

| Parameter | Endpunkt | Messung | Ergebnis |
|---|---|---|---|
| `categories` | `/search-news` | `politics` (available 1391) vs `sports` (137) | wirkt |
| `sort-direction` | `/search-news` | `ASC` vs `DESC` — andere IDs | wirkt |
| `sort` | `/search-news` | `relevance` -> 400, `publish-time` -> 200 | wirkt |
| `number` | `/search-news` | `50` -> 50 Artikel, `100` -> 100 | wirkt |
| `earliest`/`latest-publish-date` | `/search-news` | Juli-Fenster leer, August-Fenster 4885 | wirkt |
| `ids` | `/retrieve-news` | `ids=460136528` -> genau dieser Artikel | wirkt |
| `name` | `/search-news-sources` | `srf` -> 1 Quelle, `gibtsnichtxyz` -> 0 | wirkt |
| `date` | `/top-news` | zwei Daten -> andere Schlagzeilen | wirkt |

Nachgereicht am selben Tag, gegen je einen anderen Wert — diese drei
stehen in jeder Basisabfrage und waren deshalb zunaechst nicht gegen
eine Variante ohne sie geprueft:

| Parameter | Messung | Ergebnis |
|---|---|---|
| `text` | `Schule` (available 7057) vs `Bundesrat` (1316) | wirkt |
| `language` | `de` (7057) vs `fr` (1) | wirkt |
| `source-country` | `ch` (44) vs `at` (587) | wirkt |

Damit sind alle elf Query-Parameter, die die Werkzeuge bauen,
differenziell belegt.

Zu `source-country` eine Beobachtung, die taeuschen koennte: Die fuenf
IDs der `at`-Abfrage sind dieselben wie die der ungefilterten
`language=de`-Abfrage. Wirkungslos ist der Parameter trotzdem nicht —
`available` faellt von 7057 auf 587. Waere er ignoriert worden, muesste
auch `available` unveraendert bleiben. Die vorderen Treffer der
deutschsprachigen Suche stammen offenbar ohnehin aus Oesterreich.
Genau deshalb vergleicht die Messung `available` **und** IDs: Auf die
IDs allein gestuetzt haette dieser Fall wie «ohne Wirkung» ausgesehen.

**Befund `/retrieve-front-page`:**

    HTTP 403  {"message":"This endpoint is not available on the free plan."}

`news_front_pages` ist auf dem Free Tier nicht benutzbar. Das ist
keine Fehlfunktion dieses Servers, aber es steht in keiner
Tool-Beschreibung.

### Ein Fehlversuch, der hierher gehoert

Der erste Anlauf legte das Zeitfenster in den Juli. Der Free Tier
reicht nur etwa einen Monat zurueck, also kamen **beide Seiten
jedes Vergleichs leer** zurueck — und «leer == leer» las sich als
«Parameter ohne Wirkung». Drei Parameter waren damit faelschlich
als tot gemeldet.

Ein Vergleich zweier Nicht-Antworten sieht aus wie ein Ergebnis.
Die Messung traegt deshalb jetzt eine Basispruefung: Liefert die
Grundabfrage weniger als zwei Artikel, bricht sie ab, statt zu
vergleichen.
