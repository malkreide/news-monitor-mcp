#!/usr/bin/env python3
"""Prueft, dass ein geplanter Live-Lauf tatsaechlich etwas gemessen hat.

Warum das noetig ist: Ueberspringt pytest jeden Test, ist der Exit-Code 0.
Ein Lauf, der nichts geprueft hat, sieht dann genauso aus wie einer, der alles
geprueft hat — und ein gruener Haken, hinter dem keine Messung steht, ist
schlechter als gar keine geplante Abdeckung, weil er Sicherheit vortaeuscht.

Zwei Faelle werden deshalb rot gemeldet:

* Die Datei fehlt oder enthaelt keinen einzigen Testfall. Das heisst nicht
  «nichts zu tun», sondern dass die Sammlung nicht mehr greift — etwa weil die
  Markierung `live` umbenannt wurde.
* Jeder gesammelte Fall wurde uebersprungen. Zwei der Live-Tests pruefen den
  Routenbestand und brauchen dafuer keinen Schluessel; sie laufen ueberall.
  Ueberspringen sich auch die, fehlt nicht der Schluessel, sondern es stimmt
  etwas anderes nicht.

Ein Teil uebersprungen (kein `WORLD_NEWS_API_KEY`) ist dagegen kein Fehler,
sondern der dokumentierte Zustand — aber einer, der sichtbar sein muss, sonst
haelt man die halbe Messung fuer die ganze.
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _summary(zeilen: list[str]) -> None:
    """Schreibt in die Job-Zusammenfassung, wenn es eine gibt."""
    ziel = os.environ.get("GITHUB_STEP_SUMMARY")
    text = "\n".join(zeilen)
    print(text)
    if ziel:
        with open(ziel, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def main(argv: list[str]) -> int:
    pfad = Path(argv[1] if len(argv) > 1 else "live-report.xml")

    if not pfad.exists():
        _summary([f"::error::{pfad} fehlt — pytest hat keinen Bericht geschrieben."])
        return 1

    wurzel = ET.parse(pfad).getroot()
    suites = wurzel.iter("testsuite") if wurzel.tag == "testsuites" else [wurzel]

    gesamt = uebersprungen = fehlgeschlagen = 0
    for suite in suites:
        gesamt += int(suite.get("tests", 0))
        uebersprungen += int(suite.get("skipped", 0))
        fehlgeschlagen += int(suite.get("failures", 0)) + int(suite.get("errors", 0))

    gelaufen = gesamt - uebersprungen

    zeilen = [
        "## Live-Tests",
        "",
        f"- gesammelt: **{gesamt}**",
        f"- ausgefuehrt: **{gelaufen}**",
        f"- uebersprungen: **{uebersprungen}**",
        f"- fehlgeschlagen: **{fehlgeschlagen}**",
        "",
    ]

    if gesamt == 0:
        zeilen.append(
            "::error::Kein einziger Live-Test wurde gesammelt. Das heisst nicht "
            "«nichts zu tun», sondern dass die Markierung `live` nicht mehr greift."
        )
        _summary(zeilen)
        return 1

    if gelaufen == 0:
        zeilen.append(
            "::error::Jeder gesammelte Live-Test wurde uebersprungen — auch die "
            "Routenpruefung, die keinen Schluessel braucht. Dieser Lauf hat nichts "
            "gemessen und darf nicht gruen aussehen."
        )
        _summary(zeilen)
        return 1

    if uebersprungen:
        zeilen.append(
            f"::warning::{uebersprungen} von {gesamt} Live-Tests uebersprungen. Ohne "
            "`WORLD_NEWS_API_KEY` ist nur der Routenbestand geprueft, nicht die Form "
            "der Antwort — ein Schemawechsel faellt so nicht auf."
        )

    _summary(zeilen)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
