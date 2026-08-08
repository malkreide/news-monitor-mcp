#!/usr/bin/env python3
"""Zeichnet auf, was ohne API-Key aufzeichenbar ist: den Bestand der Routen.

    python scripts/record_fixtures.py

WARUM ES DAS GIBT. Ein handgeschriebener Mock kodiert die Annahme seines
Autors und kann sie deshalb prinzipiell nicht widerlegen: Produktivcode und
Fixture stammen aus demselben Kopf, derselben Stunde, derselben Lektuere der
Doku. Wo beide irren, irren beide gleich, und die Suite bleibt dauerhaft
gruen.

WAS HIER NICHT AUFGEZEICHNET WIRD. Die WorldNewsAPI verlangt einen
`WORLD_NEWS_API_KEY`; ohne ihn kommt keine Antwort, die man datieren koennte.
`tests/fixtures/PROVENANCE.md` fuehrt diese Payloads deshalb ausdruecklich als
NICHT AUFGEZEICHNET, statt ihnen ein Datum anzuschreiben, das nicht stimmt.

WAS STATTDESSEN AUFGEZEICHNET WIRD, ist der Vertrag, den die Quelle auch ohne
Schluessel preisgibt: **welche Routen das Gateway fuehrt.** Das ist kein
Ersatzgegenstand — es ist genau das, woran fuenfzehn Werkzeuge haengen.

DIE MESSUNG UND IHRE KONTROLLE. Das Gateway routet **vor** der
Authentifizierung:

    /search-news                 -> 401  application/json
    /top-news                    -> 401  application/json
    /diesen-pfad-gibt-es-nicht   -> 404  text/html (Tomcat-Fehlerseite)

Ein 401 heisst also «diese Route gibt es», ein 404 «diese nicht». Ohne die
erfundenen Pfade belegte die Messung nur, dass ICH einen 401 bekomme.

Dass diese Unterscheidung traegt, ist keine Selbstverstaendlichkeit und
gehoert deshalb mitgemessen: Bei `epl.bag.admin.ch` im selben Portfolio
antwortet **auch** ein erfundener Pfad mit 401 — dort sagt ein 401 nichts
ueber den Bestand.

Ohne Aufzeichnungsdatum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht»
nicht mehr zu unterscheiden. Es steht je Datei in
`tests/fixtures/PROVENANCE.md`.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "src"))

# Die Basis-URL kommt aus dem Produktivcode, nicht aus einer Abschrift. Ein
# Aufzeichnungsskript, das eine andere Adresse fragt als der Server, misst den
# falschen Gegenstand — und das faellt niemandem auf, weil das Ergebnis
# plausibel aussieht.
from news_monitor_mcp.api_client import BASE_URL  # noqa: E402

# Die Pfade, die der Server baut. Wer hier etwas ergaenzt, ohne dass ein
# Werkzeug ihn aufruft, misst eine Adresse, die niemanden interessiert.
ROUTEN = [
    ("search-news", "/search-news", "news_search, news_sentiment_monitor, Alerts, Briefing"),
    ("top-news", "/top-news", "news_top_headlines"),
    ("retrieve-news", "/retrieve-news", "news_article_details"),
    ("retrieve-front-page", "/retrieve-front-page", "news_front_pages"),
    ("search-news-sources", "/search-news-sources", "news_source_lookup"),
]
KONTROLLEN = [
    ("kontrolle_erfundener_pfad", "/diesen-pfad-gibt-es-nicht"),
    ("kontrolle_fast_richtig", "/search-news-die-es-nicht-gibt"),
]


def record() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(UTC).strftime("%Y-%m-%d")
    entries: list[dict] = []
    skipped: list[dict] = []

    def write(name: str, payload: object, url: str, rule: str) -> None:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        (FIXTURES / name).write_text(text, encoding="utf-8")
        entries.append(
            {
                "name": name,
                "url": url,
                "rule": rule,
                "bytes": len(text.encode("utf-8")),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
        print(f"ok  {name:<26} {len(text.encode('utf-8')):>7} B")

    with httpx.Client(timeout=60.0, follow_redirects=True) as c:
        routen: dict[str, dict] = {}
        # Bewusst OHNE Schluessel — das ist der Punkt: Die Unterscheidung, um
        # die es geht, macht das Gateway vor der Schluesselpruefung.
        for label, pfad, wer in ROUTEN:
            r = c.get(f"{BASE_URL}{pfad}")
            routen[label] = {
                "pfad": pfad,
                "status": r.status_code,
                "content_type": r.headers.get("content-type", ""),
                "gebaut_von": wer,
            }
            print(f"    {r.status_code}  {label:<24} {r.headers.get('content-type', '')[:24]}")
        for label, pfad in KONTROLLEN:
            r = c.get(f"{BASE_URL}{pfad}")
            routen[label] = {
                "pfad": pfad,
                "status": r.status_code,
                "content_type": r.headers.get("content-type", ""),
                "gebaut_von": "KONTROLLE: erfundener Pfad, von keinem Werkzeug gebaut",
            }
            print(f"    {r.status_code}  {label:<24} {r.headers.get('content-type', '')[:24]}")

    st = {k: v["status"] for k, v in routen.items()}

    for label, _pfad in KONTROLLEN:
        if st[label] != 404:
            raise SystemExit(
                f"Die Kontrolle {label} antwortet mit {st[label]} statt 404. "
                "Dann unterscheidet das Gateway nicht mehr zwischen «Route "
                "vorhanden» und «Route unbekannt» — und die Messung unten "
                "belegt nichts mehr. Neu messen, nicht nachziehen."
            )
    tot = sorted(label for label, _p, _w in ROUTEN if st[label] != 401)
    if tot:
        raise SystemExit(
            f"Diese Routen antworten nicht mehr mit 401: {tot}. Ein 404 heisst "
            "hier, dass die Quelle die Route nicht mehr fuehrt — das gehoert "
            "behoben, nicht aufgezeichnet."
        )

    write(
        "api_routen.json",
        {"recorded_at": recorded_at, "basis_url": BASE_URL, "routen": routen},
        f"{BASE_URL}/…",
        "Statuscode und Content-Type je Pfad, ohne API-Key abgefragt — samt "
        "zweier Kontrollen mit erfundenen Pfaden. Erst die Kontrollen machen "
        "aus «ich bekomme 401» die Aussage «diese Route fuehrt das Gateway»: "
        "Es routet vor der Schluesselpruefung, also heisst 401 «Route da» und "
        "404 «Route weg». Dass das traegt, ist nicht selbstverstaendlich — "
        "andere Gateways im selben Portfolio antworten auch auf erfundene "
        "Pfade mit 401",
    )

    if not os.environ.get("WORLD_NEWS_API_KEY"):
        skipped.append(
            {
                "name": "search_news.json, top_news.json, …",
                "url": f"{BASE_URL}/search-news",
                "why": "WORLD_NEWS_API_KEY nicht gesetzt — die API antwortet "
                "ohne Schluessel mit HTTP 401. NICHT aufgezeichnet.",
            }
        )
        print("--  Payloads                  uebersprungen (kein API-Key)")

    _write_provenance(recorded_at, entries, skipped)
    print(f"\nPROVENANCE.md geschrieben, Aufzeichnungsdatum {recorded_at}")
    return 0


def _write_provenance(recorded_at: str, entries: list[dict], skipped: list[dict]) -> None:
    lines = [
        "# Herkunft der Fixtures",
        "",
        "**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**",
        "",
        f"Aufgezeichnet am **{recorded_at}** von `api.worldnewsapi.com`.",
        "",
        "Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht",
        "mehr zu unterscheiden — die Datei sieht gleich aus.",
        "",
        "## Aufgezeichnet ist der Vertrag, nicht die Antwort",
        "",
        "Die WorldNewsAPI verlangt einen Schluessel; ohne ihn gibt es keine",
        "Antwort, die man datieren koennte. Aufzeichenbar ist trotzdem genau",
        "das, woran fuenfzehn Werkzeuge haengen: **welche Routen das Gateway",
        "fuehrt.** Es routet vor der Schluesselpruefung und unterscheidet",
        "deshalb selbst zwischen «Route da, Schluessel fehlt» (401,",
        "`application/json`) und «Route gibt es nicht» (404, Tomcat-HTML).",
        "",
        "## Die Kontrollen gehoeren zur Messung",
        "",
        "Ohne die beiden `kontrolle_*`-Zeilen belegte die Aufzeichnung nur,",
        "dass jemand einen 401 bekommen hat; mit ihnen belegt sie, was das",
        "Gateway unterscheidet.",
        "",
        "Dass diese Unterscheidung ueberhaupt traegt, ist keine",
        "Selbstverstaendlichkeit. Im selben Portfolio antwortet",
        "`epl.bag.admin.ch` **auch** auf frei erfundene Pfade mit 401 — dort",
        "sagt ein 401 nichts ueber den Bestand. Deshalb wird die Kontrolle bei",
        "jedem Lauf mitgemessen, und das Skript bricht ab, wenn sie nicht mehr",
        "traegt.",
        "",
    ]
    for e in entries:
        lines += [
            f"## `{e['name']}`",
            "",
            f"- **Quelle:** `{e['url']}`",
            f"- **Aufgezeichnet:** {recorded_at}",
            f"- **Auswahl:** {e['rule']}",
            f"- **Groesse:** {e['bytes']} B",
            f"- **SHA-256:** `{e['sha256']}`",
            "",
        ]
    if skipped:
        lines += ["## NICHT aufgezeichnet", ""]
        for s in skipped:
            lines += [
                f"### `{s['name']}`",
                "",
                f"- **Quelle:** `{s['url']}`",
                f"- **Grund:** {s['why']}",
                "",
            ]
        lines += [
            "Die Antwort-Payloads stehen weiterhin als Literale im Testmodul.",
            "Sie sind damit **ausgedacht** und tragen kein Datum — das ist der",
            "Ist-Zustand und keine Nachlaessigkeit dieses Laufs. Wer einen",
            "Schluessel hat, setzt `WORLD_NEWS_API_KEY` und laesst das Skript",
            "erneut laufen.",
            "",
            "Konkret unbelegt bleibt damit: **ob die Query-Parameternamen",
            "stimmen, die der Server sendet.** Die API antwortet ohne",
            "Schluessel auf jede Anfrage mit 401, unabhaengig von den",
            "Parametern. In `global-education-mcp` desselben Portfolios waren",
            "genau hier zwei Filter still wirkungslos: Unbekannte Parameter",
            "wurden mit HTTP 200 beantwortet und fallengelassen. Diese Pruefung",
            "steht hier aus und ist als offen markiert, statt als erledigt zu",
            "gelten.",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(record())
    except httpx.HTTPError as exc:
        print(f"FEHLER: Quelle nicht erreichbar: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
