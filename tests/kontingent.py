"""Ein aufgebrauchtes Kontingent ist kein Defekt der Quelle.

Am 2026-08-14 lief der Free-Tier-Schluessel waehrend einer Messreihe leer.
Die Live-Tests meldeten daraufhin rot:

    HTTP 402 Payment Required
    Fehler: API-Kontingent erschoepft.

Das ist dieselbe Meldung, die auch ein Schemawechsel bei der Quelle
ausgeloest haette — und der Meldeweg des geplanten Laufs haette daraus ein
Issue mit dem Titel «die Quelle antwortet nicht mehr wie erwartet» gemacht.
Falsch, und schlimmer als gar keine Meldung: Wer dem Issue glaubt, sucht am
falschen Ort.

Dieses Repo trennt das schon einmal an anderer Stelle: Ohne
`WORLD_NEWS_API_KEY` **ueberspringen** sich die Datentests, statt rot zu
melden — «rot» soll heissen, dass etwas nicht stimmt, nicht dass jemand
keinen Schluessel hat. Ein erschoepftes Budget gehoert in dieselbe
Kategorie. Es sagt etwas ueber unser Konto aus, nichts ueber die Quelle.

Uebersprungen heisst dabei ausdruecklich **nicht** «in Ordnung»:
`scripts/check_live_run.py` zaehlt die Uebersprungenen, schreibt ihre
Gruende ins Job-Summary und meldet rot, wenn ein Lauf gar nichts gemessen
hat. Der Unterschied ist nicht, ob es auffaellt, sondern ob die Meldung
stimmt.

ABGEGRENZT WIRD ENG. Nur 402 (Kontingent) und 429 (Rate Limit) gelten als
Budget. Ein 401 bleibt rot — ein ungueltiger Schluessel ist ein Defekt der
Konfiguration, den jemand beheben muss. Alles andere sowieso.
"""

import pytest

#: Statuscodes, die ein Budget-Limit bedeuten — nicht einen Defekt.
BUDGET_CODES = frozenset({402, 429})

#: Die Meldungen, die `errors.py` fuer diese Codes erzeugt. Die Werkzeuge
#: geben Text zurueck, keine Exception; deshalb braucht es beide Wege.
BUDGET_MELDUNGEN = ("API-Kontingent erschöpft", "Rate Limit erreicht")

_GRUND = (
    "Budget der Quelle erreicht ({}). Das sagt etwas ueber unser Konto aus, "
    "nichts ueber die Quelle — dieser Lauf hat die Antwortform nicht gemessen. "
    "Das Kontingent des Free Tiers setzt taeglich zurueck."
)


def ueberspringe_bei_budget_status(status_code: int) -> None:
    """Fuer Tests, die selbst per httpx anfragen."""
    if status_code in BUDGET_CODES:
        pytest.skip(_GRUND.format(f"HTTP {status_code}"))


def ueberspringe_bei_budget_antwort(antwort: str) -> None:
    """Fuer Tests, die ein Werkzeug aufrufen und dessen Text bekommen."""
    for meldung in BUDGET_MELDUNGEN:
        if meldung in antwort:
            ostr = meldung
            pytest.skip(_GRUND.format(ostr))
