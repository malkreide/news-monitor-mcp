"""Was der Verzeichniseintrag ueber diesen Server behauptet.

`server.json` ist die einzige Datei des Repos, die niemand beim Arbeiten
liest: Sie wirkt erst im MCP-Verzeichnis, und der Eintrag dort ist das, was
ein Mensch vor der Installation sieht. Entsprechend lange stand darin
«Aggregated news monitoring across Swiss public media RSS feeds» — und
dieser Server liest keine RSS-Feeds und keine Schweizer Medien-Sites. Der
einzige Host in `src/` ist der aus `BASE_URL`.

Gemessen, bevor diese Datei entstand: Mit genau dieser Zeile liefen alle
sieben CI-Gates gruen, 208 Tests eingeschlossen. `check_version_sync.py`
vergleicht Versionsfelder und ruehrt die Beschreibung nicht an, und kein
Test las `server.json`. Der Fall fiel also nirgends — deshalb steht hier
etwas.

Warum der Positiv-Teil hier duenner ausfaellt als in den Portfolio-Repos
mit mehreren Quellen: Dieser Server hat genau eine, und sie steht in
`BASE_URL`. Es gibt keine Quellen-Tabelle, aus der sich eine Liste
ableiten liesse — dafuer ist der eine Fall vollstaendig abgedeckt.

Was die Pruefungen NICHT leisten: Sie lesen keinen Text. Eine sachlich
schiefe, aber marker-treue Beschreibung kommt durch. Sie fangen die
mechanischen Klassen, die unten je einen Test tragen, und behaupten
darueber hinaus nichts.
"""

from __future__ import annotations

import json
import pathlib
import tomllib
from urllib.parse import urlparse

import pytest

from news_monitor_mcp.api_client import BASE_URL

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SERVER_JSON = _ROOT / "server.json"
_PYPROJECT = _ROOT / "pyproject.toml"

# `ServerDetail.description.maxLength`, je Schema-Fassung. Als Zahl abgelegt,
# weil der Test sonst im CI-Lauf ans Netz muesste — aber NICHT allein: Das
# Limit steht unter dem `$schema`-Wert, aus dem es stammt.
#
# Sonst waere es eine Kopie, die ihre Quelle nicht kennt. Wer `server.json`
# auf eine neue Schema-Fassung umstellt, erbte still die Grenze der alten:
# bei einem kleineren neuen Wert bliebe das Gate gruen und die Registry
# wiese erst nach der PyPI-Veroeffentlichung zurueck, bei einem groesseren
# blockierte es gueltige Beschreibungen.
_MAX_LAENGE_JE_SCHEMA: dict[str, int] = {
    "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json": 100,
}

# Schreibweisen, unter denen die Quelle aus `BASE_URL` in einer Beschreibung
# erscheinen darf. Der Host selbst ist der Anker: Zieht der Server auf eine
# andere API um, aendert sich `BASE_URL`, der Test unten findet den Host
# nicht mehr in dieser Tabelle und verlangt einen Eintrag.
_MARKER_JE_HOST: dict[str, tuple[str, ...]] = {
    "api.worldnewsapi.com": ("WorldNewsAPI", "World News API", "worldnewsapi"),
}

# Techniken und Quellenarten, die dieser Server NICHT benutzt, je mit dem
# Beleg. Handgeschrieben, weil es hier — anders als bei einem Server mit
# Quellen-Tabelle — keine Struktur gibt, die das Nichtvorhandene fuehrt.
# Der Beleg steht dabei, damit ein Eintrag pruefbar bleibt statt geglaubt.
_NICHT_BENUTZT: dict[str, str] = {
    "RSS": "kein Feed-Parsing in src/, keine Feed-Bibliothek in den Abhaengigkeiten",
    "Atom": "dito; die grep-Treffer auf 'atom' sind '_atomic_write_json'",
}

# Pakete, deren Fehlen den Beleg oben traegt. Waere eines davon da, muesste
# die Behauptung «kein RSS» neu geprueft werden — der Test unten faellt dann
# und verlangt genau das.
_FEED_PAKETE = ("feedparser", "atoma", "listparser")


def _manifest() -> dict:
    return json.loads(_SERVER_JSON.read_text(encoding="utf-8"))


def _abhaengigkeiten() -> list[str]:
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]["dependencies"]


def test_die_beschreibung_haelt_die_schema_grenze() -> None:
    """Zu lang faellt sonst erst beim Release — und dort zu spaet.

    `publish.yml` haengt den Registry-Schritt hinter den PyPI-Job. Ein
    Manifest, das die Registry zurueckweist, bricht also ab, nachdem das
    Paket bereits veroeffentlicht ist. Geprueft wird gegen die Fassung, auf
    die `server.json` per `$schema` zeigt, nicht gegen eine fest
    verdrahtete Zahl.
    """
    manifest = _manifest()
    schema = manifest.get("$schema", "")
    grenze = _MAX_LAENGE_JE_SCHEMA.get(schema)
    assert grenze is not None, (
        f"server.json verweist auf {schema!r}. Fuer diese Schema-Fassung ist in "
        "_MAX_LAENGE_JE_SCHEMA keine Grenze hinterlegt. Ihr "
        "`ServerDetail.description.maxLength` nachschlagen und dort eintragen — "
        "die Grenze der alten Fassung weiterzuerben pruefte das falsche Schema."
    )

    beschreibung = manifest["description"]
    assert beschreibung, "leere Beschreibung — das Schema verlangt minLength 1"
    assert len(beschreibung) <= grenze, (
        f"{len(beschreibung)} Zeichen, erlaubt sind {grenze}. Die Beschreibung "
        "aus pyproject.toml ist laenger und passt deshalb NICHT unveraendert "
        "hierher — die beiden Felder koennen sich nicht gleichen."
    )


def test_die_angebundene_quelle_steht_im_verzeichniseintrag() -> None:
    """Was der Server abfragt, muss der Eintrag auch nennen.

    Der Host kommt aus `BASE_URL` und nicht aus einer Kopie hier: Zieht der
    Server um, faellt dieser Test, statt eine veraltete Angabe durchzulassen.
    """
    host = urlparse(BASE_URL).hostname or ""
    marker = _MARKER_JE_HOST.get(host)
    assert marker is not None, (
        f"BASE_URL zeigt auf {host!r}, aber _MARKER_JE_HOST kennt diesen Host "
        "nicht. Der Server fragt eine andere Quelle ab als bisher — die "
        "Schreibweisen dort eintragen und die Beschreibung pruefen."
    )
    beschreibung = _manifest()["description"]
    assert any(m.lower() in beschreibung.lower() for m in marker), (
        f"server.json nennt die Quelle nicht (erwartet eine von {list(marker)}), "
        f"obwohl der Server ausschliesslich {host} abfragt."
    )


@pytest.mark.parametrize("begriff", sorted(_NICHT_BENUTZT))
def test_der_eintrag_nennt_keine_technik_die_der_server_nicht_benutzt(
    begriff: str,
) -> None:
    """Der Rueckfall in genau den Fehler, der diese Datei ausgeloest hat.

    Als eigenes Wort geprueft, nicht als Teilzeichenkette: «Atom» steckt in
    «atomic», und ein Substring-Treffer haette hier schon einmal in die
    falsche Richtung gezeigt.
    """
    worte = {w.strip(".,:;()").lower() for w in _manifest()["description"].split()}
    assert begriff.lower() not in worte, f"server.json nennt {begriff!r}, aber: {_NICHT_BENUTZT[begriff]}."


def test_der_beleg_fuer_kein_feed_gilt_noch() -> None:
    """Die Gegenprobe zum Negativ-Test: Stimmt seine Begruendung noch?

    Ein Verbot ist nur so viel wert wie sein Beleg. Kommt eine
    Feed-Bibliothek in die Abhaengigkeiten, ist «kein RSS» nicht mehr
    belegt — dann faellt diese Zeile und verlangt, den Eintrag in
    `_NICHT_BENUTZT` neu zu pruefen, statt ihn still weiterzutragen.
    """
    deklariert = " ".join(_abhaengigkeiten()).lower()
    gefunden = [p for p in _FEED_PAKETE if p in deklariert]
    assert not gefunden, (
        f"{gefunden} steht jetzt in den Abhaengigkeiten. Der Beleg fuer "
        "_NICHT_BENUTZT['RSS'] traegt damit nicht mehr — pruefen, ob der "
        "Server inzwischen Feeds liest, und den Eintrag anpassen."
    )


def test_die_ableitung_findet_ueberhaupt_etwas() -> None:
    """Sichert die Pruefungen oben gegen leere Eingaben ab.

    Waere `_NICHT_BENUTZT` leer, erzeugte der Negativ-Test null Faelle und
    die Suite bliebe gruen, ohne den Eintrag angesehen zu haben — gruen aus
    Mangel an Pruefung.
    """
    assert _NICHT_BENUTZT, "_NICHT_BENUTZT ist leer — der Negativ-Test prueft dann nichts"
    assert _FEED_PAKETE, "_FEED_PAKETE ist leer — die Beleg-Pruefung prueft dann nichts"
    assert urlparse(BASE_URL).hostname, f"BASE_URL {BASE_URL!r} hat keinen Host"
    assert _abhaengigkeiten(), "keine Abhaengigkeiten gelesen — der Scan sucht falsch"
