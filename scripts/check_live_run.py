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

DREI ZUSTAENDE, NICHT ZWEI
--------------------------
Der Rueckgabewert allein sagt nur «in Ordnung» oder «nicht in Ordnung», und der
Workflow las jedes «nicht in Ordnung» als gebrochenen Vertrag mit der Quelle:
Das Issue hiess «die Quelle antwortet nicht mehr wie erwartet». Fuer einen
Fehlschlag stimmt das. Fuer einen Lauf, der nichts gemessen hat — jeder Test
uebersprungen, die Marke umbenannt, kein Bericht geschrieben —, ist es eine
Behauptung ueber eine Quelle, die niemand gefragt hat.

Deshalb wird zusaetzlich ein Zustand nach `$GITHUB_OUTPUT` geschrieben:

  clear    gelaufen und gruen
  finding  gelaufen, etwas ist gefallen
  unknown  nicht gelaufen — ueber die Quelle sagt der Lauf nichts

Der Exit-Code bleibt, was er war; er entscheidet weiter ueber rot und gruen.
Der Zustand entscheidet daneben, welche Meldung dazu passt.
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CLEAR = "clear"
FINDING = "finding"
UNKNOWN = "unknown"


def _zustand(zustand: str, grund: str) -> None:
    """Schreibt den Zustand nach `$GITHUB_OUTPUT`, wenn es eine gibt.

    Der Grund wird flachgeklopft: Die `key=value`-Form endet an der ersten
    neuen Zeile, und was danach steht, liest der Runner als naechstes Output —
    ein mehrzeiliger Grund koennte so ein zweites `state=` nachschieben.
    """
    ziel = os.environ.get("GITHUB_OUTPUT")
    if not ziel:
        return
    with open(ziel, "a", encoding="utf-8") as f:
        f.write(f"state={zustand}\n")
        f.write(f"reason={' '.join(grund.split())}\n")


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
        _zustand(UNKNOWN, f"{pfad} fehlt — pytest hat keinen Bericht geschrieben")
        return 1

    wurzel = ET.parse(pfad).getroot()
    suites = wurzel.iter("testsuite") if wurzel.tag == "testsuites" else [wurzel]

    gesamt = uebersprungen = fehlgeschlagen = 0
    gruende: list[str] = []
    for suite in suites:
        gesamt += int(suite.get("tests", 0))
        uebersprungen += int(suite.get("skipped", 0))
        fehlgeschlagen += int(suite.get("failures", 0)) + int(suite.get("errors", 0))
        # Warum uebersprungen wurde, steht im Bericht. Frueher stand hier statt
        # dessen die Vermutung «dann fehlt wohl der Schluessel» — seit ein
        # erschoepftes Kontingent ebenfalls ueberspringt, waere das schlicht
        # falsch. Ein Waechter, der den Grund raet, ist keiner.
        for fall in suite.iter("testcase"):
            for skip in fall.iter("skipped"):
                text = (skip.get("message") or "").strip()
                if text and text not in gruende:
                    gruende.append(text)

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
        _zustand(UNKNOWN, "null Live-Tests eingesammelt — die Markierung greift nicht mehr")
        return 1

    if gelaufen == 0:
        zeilen.append(
            "::error::Jeder gesammelte Live-Test wurde uebersprungen — auch die "
            "Routenpruefung, die keinen Schluessel braucht. Dieser Lauf hat nichts "
            "gemessen und darf nicht gruen aussehen."
        )
        _summary(zeilen)
        _zustand(UNKNOWN, f"alle {gesamt} Live-Tests uebersprungen — geprueft wurde nichts")
        return 1

    if uebersprungen:
        zeilen.append(
            f"::warning::{uebersprungen} von {gesamt} Live-Tests uebersprungen — "
            "die Form der Antwort ist damit nicht gemessen, ein Schemawechsel "
            "faellt so nicht auf."
        )
        zeilen.append("")
        zeilen.append("Gemeldete Gruende:")
        if gruende:
            zeilen.extend(f"- {g}" for g in gruende)
        else:
            zeilen.append("- *(keiner im Bericht — pytest hat den Grund nicht mitgeschrieben)*")

    if fehlgeschlagen:
        # Hier war die Suite unterwegs und etwas ist gefallen: der einzige Fall,
        # in dem eine Meldung ueber die Quelle gedeckt ist.
        _zustand(FINDING, f"{fehlgeschlagen} von {gesamt} Live-Test(s) gefallen")
    else:
        _zustand(CLEAR, f"{gelaufen} von {gesamt} Live-Test(s) ausgefuehrt, alle gruen")

    _summary(zeilen)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
