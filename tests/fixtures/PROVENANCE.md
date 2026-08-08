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

Konkret unbelegt bleibt damit: **ob die Query-Parameternamen
stimmen, die der Server sendet.** Die API antwortet ohne
Schluessel auf jede Anfrage mit 401, unabhaengig von den
Parametern. In `global-education-mcp` desselben Portfolios waren
genau hier zwei Filter still wirkungslos: Unbekannte Parameter
wurden mit HTTP 200 beantwortet und fallengelassen. Diese Pruefung
steht hier aus und ist als offen markiert, statt als erledigt zu
gelten.
