"""Der Meldeweg des geplanten Live-Workflows, gegen einen `gh`-Stub gefahren.

WARUM ES DIESEN TEST GIBT. Der Schritt, der bei einem roten Cron-Lauf ein Issue
oeffnet, laeuft nur im Fehlerfall — also nie, solange alles gut geht. Er war
damit der einzige Teil des Workflows, den niemand je ausgefuehrt hatte, und er
enthielt prompt einen Fehler: `export TITEL=...` gesetzt, aber `--title "$titel"`
verwendet. Unter `set -u` bricht der Schritt damit ab, bevor irgendetwas
gemeldet wird. Aufgefallen ist das erst, als der Fehlschlag von Hand provoziert
wurde — im Echtbetrieb waere es beim ersten roten Lauf aufgefallen, also genau
dann, wenn man sich auf die Meldung verlaesst.

Geprueft wird der Block **aus dem Workflow selbst**, nicht eine Kopie: Eine
Kopie wuerde mit dem Original auseinanderlaufen und der Test bliebe gruen.

Der Stub wendet `--jq` mit dem echten `jq` an. Taete er das nicht, lieferte
`gh issue list` immer die rohe Liste zurueck, «kein offenes Issue» waere nie
leer, und der Create-Zweig liesse sich gar nicht ausloesen — der Test pruefte
dann den Stub statt den Workflow.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

_WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "live-tests.yml"
_TITEL = "Live-Tests rot: die Quelle antwortet nicht mehr wie erwartet"

pytestmark = pytest.mark.skipif(
    not (shutil.which("bash") and shutil.which("jq")),
    reason="Braucht bash und jq — beide sind auf ubuntu-latest da.",
)

_STUB = """#!/usr/bin/env bash
if [ "$1" = "label" ]; then echo "label create" >> "$PROTOKOLL"; exit 0; fi
if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
  ausdruck=""
  while [ $# -gt 0 ]; do [ "$1" = "--jq" ] && ausdruck="$2"; shift; done
  jq -r "$ausdruck" < "$FAKE_ISSUES"
  exit 0
fi
echo "$2 $3" >> "$PROTOKOLL"
exit 0
"""


def _meldeschritt() -> str:
    """Holt den Shell-Block des Melde-Schritts aus dem Workflow."""
    schritte = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))["jobs"]["live"]["steps"]
    treffer = [s for s in schritte if "Issue" in s.get("name", "")]
    assert len(treffer) == 1, f"Melde-Schritt nicht eindeutig gefunden: {len(treffer)}"
    return treffer[0]["run"]


def _fahre(tmp_path: Path, offene_issues: list[dict]) -> tuple[int, list[str]]:
    """Fuehrt den Block mit gestubbtem `gh` aus und gibt Exit-Code + Aufrufe zurueck."""
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    (stub_dir / "gh").write_text(_STUB, encoding="utf-8")
    (stub_dir / "gh").chmod(0o755)

    issues = tmp_path / "issues.json"
    issues.write_text(json.dumps(offene_issues), encoding="utf-8")
    protokoll = tmp_path / "protokoll.txt"
    protokoll.touch()

    ergebnis = subprocess.run(
        ["bash", "-c", _meldeschritt()],
        capture_output=True,
        text=True,
        env={
            "PATH": f"{stub_dir}:/usr/bin:/bin",
            "LAUF": "https://example.invalid/lauf/1",
            "GH_TOKEN": "stub",
            "FAKE_ISSUES": str(issues),
            "PROTOKOLL": str(protokoll),
        },
    )
    return ergebnis.returncode, protokoll.read_text(encoding="utf-8").split("\n")


def test_ohne_offenes_issue_wird_eines_geoeffnet(tmp_path):
    """Der Zweig, der beim ersten roten Lauf greift."""
    code, aufrufe = _fahre(tmp_path, [])
    assert code == 0, "Der Melde-Schritt bricht ab, statt zu melden."
    assert "label create" in aufrufe, "Ohne Label bricht `gh issue create` ab."
    assert any(a.startswith("create") for a in aufrufe), aufrufe


def test_bei_offenem_issue_wird_kommentiert_statt_dupliziert(tmp_path):
    """Sonst stapeln sich taeglich neue Issues zum selben Defekt."""
    code, aufrufe = _fahre(tmp_path, [{"number": 77, "title": _TITEL}])
    assert code == 0
    assert "comment 77" in aufrufe, aufrufe
    assert not any(a.startswith("create") for a in aufrufe), aufrufe


def test_fremdes_offenes_issue_zaehlt_nicht(tmp_path):
    """Ein anderes Issue mit dem Label darf den Bericht nicht schlucken.

    Ohne diesen Fall wuerde ein `.[0].number` ueber die ungefilterte Liste
    genuegen — und beim ersten unbeteiligten Issue kommentierte der Workflow
    am falschen Ort statt zu melden.
    """
    code, aufrufe = _fahre(tmp_path, [{"number": 91, "title": "etwas ganz anderes"}])
    assert code == 0
    assert any(a.startswith("create") for a in aufrufe), aufrufe
