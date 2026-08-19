"""Der SessionStart-Hook, der die Klon-Aktualitaet meldet, gegen echte Repos gefahren.

WARUM ES DIESEN TEST GIBT. Der Hook hat zwei Zusicherungen, die sich beide erst
im Betrieb zeigen — also genau dann, wenn man sich auf sie verlaesst:

  * Er haelt die Session **nie** an. Kein Netz, kein Remote, detached HEAD, ein
    Remote das nicht antwortet: alles Exit 0, keine Ausgabe. Ein Hook, der bei
    Netzproblemen die Arbeit anhaelt, wird nach dem zweiten Mal abgeschaltet
    und schuetzt danach gar nichts.
  * Er ermittelt den Standard-Branch, statt `main` anzunehmen. Drei Server im
    Portfolio heissen ihn `master`; die Annahme hat dort schon einmal einen
    Branch 15 Commits alt werden lassen.

Gefahren wird **das Skript selbst**, nicht eine Kopie: Eine Kopie wuerde mit
dem Original auseinanderlaufen und der Test bliebe gruen.

`test_standard_branch_wird_ermittelt_nicht_angenommen` ist so gebaut, dass eine
`main`-Annahme nicht etwa scheitert, sondern **schweigt**: Im Upstream steht
`main` genau auf dem Stand des Klons, `master` drei Commits weiter. Eine
Implementierung, die `main` fest verdrahtet, meldet dann 0 und faellt nicht
auf — das ist der Fehler, den es zu fangen gilt.
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

_WURZEL = Path(__file__).resolve().parents[1]
_HOOK = _WURZEL / ".claude" / "hooks" / "session-start.sh"
_SETTINGS = _WURZEL / ".claude" / "settings.json"

pytestmark = pytest.mark.skipif(
    not (shutil.which("bash") and shutil.which("git") and shutil.which("timeout")),
    reason="Braucht bash, git und timeout — alle drei sind auf ubuntu-latest da.",
)


def _git(pfad: Path, *argumente: str) -> str:
    """Fuehrt git in `pfad` aus, abgeschirmt von der Konfiguration des Laufenden."""
    umgebung = os.environ.copy()
    umgebung.update(
        {
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
    )
    ergebnis = subprocess.run(["git", *argumente], cwd=pfad, env=umgebung, capture_output=True, text=True, check=True)
    return ergebnis.stdout.strip()


def _commit(pfad: Path, text: str) -> None:
    (pfad / "datei.txt").write_text(text, encoding="utf-8")
    _git(pfad, "add", "datei.txt")
    _git(pfad, "commit", "-q", "-m", text)


def _upstream(tmp_path: Path, standard: str = "main") -> Path:
    """Ein Upstream-Repo mit `standard` als Standard-Branch (HEAD zeigt darauf)."""
    pfad = tmp_path / "upstream"
    pfad.mkdir()
    _git(pfad, "init", "-q", "-b", standard, ".")
    _commit(pfad, "A")
    return pfad


def _klon(tmp_path: Path, upstream: Path) -> Path:
    pfad = tmp_path / "klon"
    _git(tmp_path, "clone", "-q", str(upstream), str(pfad))
    return pfad


def _fahre(
    projektverzeichnis: Path,
    arbeitsverzeichnis: Path,
    zeitlimit: str = "5",
    pfad_ersatz: str | None = None,
) -> subprocess.CompletedProcess:
    """Fuehrt den Hook aus, wie Claude Code ihn ausfuehrt: ueber CLAUDE_PROJECT_DIR."""
    umgebung = os.environ.copy()
    umgebung.update(
        {
            "CLAUDE_PROJECT_DIR": str(projektverzeichnis),
            "CLAUDE_KLONCHECK_TIMEOUT": zeitlimit,
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        }
    )
    if pfad_ersatz is not None:
        umgebung["PATH"] = pfad_ersatz
    return subprocess.run(
        [str(_HOOK)], cwd=arbeitsverzeichnis, env=umgebung, capture_output=True, text=True, timeout=120
    )


def test_schweigt_wenn_der_klon_aktuell_ist(tmp_path: Path) -> None:
    """Bei 0 fehlenden Commits keine Ausgabe — eine Meldung, die immer kommt, wird nicht gelesen."""
    klon = _klon(tmp_path, _upstream(tmp_path))

    ergebnis = _fahre(klon, tmp_path)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


@pytest.mark.parametrize(
    ("neue_commits", "erwartet"),
    [(1, "1 Commit hinter"), (3, "3 Commits hinter")],
)
def test_meldet_die_zahl_der_fehlenden_commits(tmp_path: Path, neue_commits: int, erwartet: str) -> None:
    """Die Zahl stammt aus dem Repo, nicht aus einem Textbaustein — und Einzahl bleibt Einzahl."""
    upstream = _upstream(tmp_path)
    klon = _klon(tmp_path, upstream)
    for i in range(neue_commits):
        _commit(upstream, f"B{i}")

    ergebnis = _fahre(klon, tmp_path)

    assert ergebnis.returncode == 0
    assert erwartet in ergebnis.stdout
    assert "origin/main" in ergebnis.stdout


def test_standard_branch_wird_ermittelt_nicht_angenommen(tmp_path: Path) -> None:
    """Upstream heisst `master`; ein danebenliegendes `main` steht genau auf dem Klon-Stand.

    Eine `main`-Annahme meldet hier 0 und schweigt — deshalb pruefen wir auf die
    Meldung, nicht auf einen Fehler.
    """
    upstream = _upstream(tmp_path, standard="master")
    _git(upstream, "branch", "main")
    klon = _klon(tmp_path, upstream)
    for i in range(3):
        _commit(upstream, f"B{i}")

    ergebnis = _fahre(klon, tmp_path)

    assert ergebnis.returncode == 0
    assert "3 Commits hinter" in ergebnis.stdout
    assert "origin/master" in ergebnis.stdout


def test_detached_head_wird_gemessen_und_nicht_zum_fehler(tmp_path: Path) -> None:
    """`git symbolic-ref HEAD` scheitert hier — der ausgecheckte Stand ist trotzdem messbar."""
    upstream = _upstream(tmp_path)
    klon = _klon(tmp_path, upstream)
    _git(klon, "checkout", "-q", "--detach", "HEAD")
    for i in range(2):
        _commit(upstream, f"B{i}")

    ergebnis = _fahre(klon, tmp_path)

    assert ergebnis.returncode == 0
    assert "2 Commits hinter" in ergebnis.stdout


def test_ohne_remote_still(tmp_path: Path) -> None:
    """Ein Repo ohne `origin` ist kein Fehlerfall, sondern einer ohne Aussage."""
    pfad = tmp_path / "ohne-remote"
    pfad.mkdir()
    _git(pfad, "init", "-q", "-b", "main", ".")
    _commit(pfad, "A")

    ergebnis = _fahre(pfad, tmp_path)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_unerreichbares_remote_still(tmp_path: Path) -> None:
    """Stellvertreter fuer «kein Netz»: Das Remote ist da, antwortet aber nicht."""
    klon = _klon(tmp_path, _upstream(tmp_path))
    _git(klon, "remote", "set-url", "origin", str(tmp_path / "gibt-es-nicht"))

    ergebnis = _fahre(klon, tmp_path)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_ungeborenes_head_still(tmp_path: Path) -> None:
    """Alles erreichbar, nur HEAD zeigt ins Leere: `rev-list` liefert hier keine Zahl.

    Ein frischer Orphan-Branch ist der Fall, der als einziger bis zur
    Zahlenpruefung durchkommt. An ihr haengt, dass aus dem leeren Ergebnis
    keine Meldung «liegt  Commits hinter» wird — und kein Abbruch.
    """
    upstream = _upstream(tmp_path)
    klon = _klon(tmp_path, upstream)
    _git(klon, "checkout", "-q", "--orphan", "neuer-anfang")
    _commit(upstream, "B")

    ergebnis = _fahre(klon, tmp_path)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_ohne_git_im_pfad_still(tmp_path: Path) -> None:
    """Kein `git` erreichbar: Der Hook meldet nichts, statt mit «command not found» abzubrechen."""
    klon = _klon(tmp_path, _upstream(tmp_path))
    nur_werkzeug = tmp_path / "bin-ohne-git"
    nur_werkzeug.mkdir()
    for werkzeug in ("bash", "timeout", "sed", "cat"):
        ziel = shutil.which(werkzeug)
        assert ziel, f"{werkzeug} fehlt — der Test pruefte sonst den falschen Mangel"
        (nur_werkzeug / werkzeug).symlink_to(ziel)

    ergebnis = _fahre(klon, tmp_path, pfad_ersatz=str(nur_werkzeug))

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_kein_git_repo_still(tmp_path: Path) -> None:
    pfad = tmp_path / "kein-repo"
    pfad.mkdir()

    ergebnis = _fahre(pfad, tmp_path)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_haengendes_remote_laeuft_ins_zeitlimit(tmp_path: Path) -> None:
    """Die wichtigste Zusicherung: ein Remote, das nie antwortet, haelt die Session nicht an.

    `ext::sleep 300` ist ein Transport, der schlicht schweigt — das ist das
    flatternde DNS aus der Anforderung, nur reproduzierbar. Ohne Zeitlimit im
    Hook laeuft dieser Test in den 120-Sekunden-Deckel von `_fahre` und faellt.
    """
    klon = _klon(tmp_path, _upstream(tmp_path))
    _git(klon, "config", "protocol.ext.allow", "always")
    _git(klon, "remote", "set-url", "origin", "ext::sleep 300")

    beginn = time.monotonic()
    ergebnis = _fahre(klon, tmp_path, zeitlimit="2")
    gedauert = time.monotonic() - beginn

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    # Zwei Netzaufrufe a 2 Sekunden plus Nachlauf; alles darueber heisst, das
    # Zeitlimit hat nicht gegriffen.
    assert gedauert < 20, f"Hook lief {gedauert:.1f}s — das Zeitlimit greift nicht"


def test_hook_ist_registriert_und_ausfuehrbar() -> None:
    """Ein Hook, der nicht in settings.json steht, laeuft nie — und faellt auch nie auf."""
    einstellungen = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    befehle = [
        h["command"]
        for eintrag in einstellungen["hooks"]["SessionStart"]
        for h in eintrag["hooks"]
        if h.get("type") == "command"
    ]

    assert "$CLAUDE_PROJECT_DIR/.claude/hooks/session-start.sh" in befehle
    assert os.access(_HOOK, os.X_OK), "Hook ist nicht ausfuehrbar"
