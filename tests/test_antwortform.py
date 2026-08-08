"""Die Antwortform der WorldNewsAPI, gegen die Annahmen dieses Servers gehalten.

Ohne Netz. Grundlage ist `tests/fixtures/api_routen.json`, aufgezeichnet am
2026-08-08 von `scripts/record_fixtures.py`.

Diese Datei laeuft **in** der CI. Das ist kein Detail: Die drei Live-Tests
dieses Repos liefen ueberhaupt nie — sie trugen keinen `asyncio`-Marker, und
die CI schliesst `-m live` ohnehin aus. Was dauerhaft gelten soll, gehoert
deshalb hierher.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from news_monitor_mcp.api_client import BASE_URL, UpstreamShapeError, articles_of
from news_monitor_mcp.errors import _handle_api_error

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _routen() -> dict:
    pfad = FIXTURES / "api_routen.json"
    if not pfad.is_file():
        raise FileNotFoundError(f"Keine Fixture unter {pfad}. Neu aufzeichnen mit `python scripts/record_fixtures.py`.")
    return copy.deepcopy(json.loads(pfad.read_text(encoding="utf-8")))


class TestRoutenbestand:
    """Was ohne Schluessel messbar war — und was es belegt."""

    def test_jede_gebaute_route_antwortete_mit_401(self):
        routen = _routen()["routen"]
        gebaut = {k: v for k, v in routen.items() if not k.startswith("kontrolle_")}
        assert len(gebaut) == 5
        for label, v in gebaut.items():
            assert v["status"] == 401, f"{label}: {v['status']}"
            assert "json" in v["content_type"]

    def test_die_kontrollen_antworteten_mit_404(self):
        """Ohne sie hiesse der Befund oben nur «ich bekomme einen 401».

        Erst der Unterschied zwischen 401 (JSON) und 404 (Tomcat-HTML) zeigt,
        dass das Gateway vor der Schluesselpruefung routet — und damit, dass
        ein 401 «diese Route gibt es» bedeutet.
        """
        routen = _routen()["routen"]
        kontrollen = {k: v for k, v in routen.items() if k.startswith("kontrolle_")}
        assert len(kontrollen) == 2, "Ohne Kontrollen belegt die Aufzeichnung nichts."
        for label, v in kontrollen.items():
            assert v["status"] == 404, f"{label}: {v['status']}"
            assert "html" in v["content_type"]

    def test_die_aufzeichnung_nutzt_die_basis_url_des_servers(self):
        """Sonst misst sie eine Adresse, die der Server gar nicht baut."""
        assert _routen()["basis_url"] == BASE_URL

    def test_jede_aufgezeichnete_route_ist_einem_werkzeug_zugeordnet(self):
        """Eine Route ohne Aufrufer misst etwas, das niemanden interessiert."""
        for label, v in _routen()["routen"].items():
            assert v["gebaut_von"], label


class TestLeereListeIstNichtDasselbeWieFormfehler:
    """Der Fehler, den dieses Portfolio ueberall sucht.

    `data.get("news", [])` beantwortet zwei voellig verschiedene Faelle gleich:
    «die Quelle hat nichts gefunden» und «die Quelle antwortet anders, als wir
    annehmen». Aus dem zweiten wird damit «0 Ergebnisse» — vollstaendig,
    plausibel, formatiert und falsch.

    In `global-education-mcp` desselben Portfolios war genau das der Befund:
    Der Umschlag hiess inzwischen anders, aus **jeder** Antwort kam eine leere
    Liste, und 128 Tests waren gruen.
    """

    def test_eine_echte_leermenge_bleibt_leer(self):
        assert articles_of({"news": [], "available": 0}) == []

    def test_artikel_kommen_durch(self):
        assert articles_of({"news": [{"id": 1}], "available": 1}) == [{"id": 1}]

    def test_ein_fehlendes_news_ist_ein_fehler_keine_leermenge(self):
        with pytest.raises(UpstreamShapeError) as exc:
            articles_of({"articles": [{"id": 1}], "available": 1}, "/search-news")
        # Die Meldung muss nennen, was da war — sonst weiss niemand, wonach
        # er suchen soll.
        assert "articles" in str(exc.value)
        assert "/search-news" in str(exc.value)

    def test_ein_news_das_keine_liste_ist_ist_ein_fehler(self):
        with pytest.raises(UpstreamShapeError):
            articles_of({"news": {"id": 1}})

    def test_eine_antwort_die_kein_objekt_ist_ist_ein_fehler(self):
        with pytest.raises(UpstreamShapeError):
            articles_of([{"id": 1}])

    def test_der_formfehler_bekommt_eine_eigene_meldung(self):
        """Nicht «Details siehe Server-Log».

        Ein Formfehler ist kein Transportfehler: Warten hilft beim einen und
        nie beim anderen. Wer die Meldung liest, muss den Unterschied sehen.
        """
        text = _handle_api_error(UpstreamShapeError("kein Feld `news`"))
        assert "Antwortform" in text
        assert "kein Feld `news`" in text
        assert "Details siehe Server-Log" not in text


class TestKeinWerkzeugLiestDenUmschlagMehrStill:
    """Die Zusicherung, die den Befund festhaelt.

    Kehrt irgendwo `data.get("news", [])` zurueck, ist die stille Leermenge
    zurueck — und dieser Test ist die einzige Stelle, die das bemerkt.
    """

    def test_kein_stiller_default_mehr_auf_oberster_ebene(self):
        from news_monitor_mcp.tools import alerts_tools, monitoring

        for modul in (monitoring, alerts_tools):
            code = Path(modul.__file__).read_text(encoding="utf-8")
            for zeile in code.split("\n"):
                nackt = zeile.strip()
                if nackt.startswith(("articles = data.get", "news_list = data.get")):
                    pytest.fail(
                        f"{Path(modul.__file__).name}: «{nackt}» liest den "
                        "Umschlag wieder mit stillem Default. Ein Formfehler "
                        "waere damit von «0 Ergebnisse» nicht zu unterscheiden."
                    )
