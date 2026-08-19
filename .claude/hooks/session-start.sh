#!/usr/bin/env bash
#
# Klon-Aktualitaetspruefung beim Sessionstart.
#
# WARUM ES DIESEN HOOK GIBT
# -------------------------
# Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt, deren
# Ursache nicht im Diff stand: Es fehlten jeweils genau die Commits, die das
# Gate einfuehrten, an dem der Branch scheiterte. Gesucht wurde daraufhin in
# den falschen Dateien — im eigenen Diff, der in Ordnung war. Die Pruefung
# kostet eine Sekunde und ersetzt diese Fehlersuche.
#
# ERSTE REGEL: DIESER HOOK HAELT DIE SESSION NIE AN
# -------------------------------------------------
# Kein Netz, kein Remote, detached HEAD, flatterndes DNS, kein Git — jeder
# dieser Faelle geht still durch (Exit 0, keine Ausgabe). Ein Hook, der bei
# Netzproblemen die Arbeit anhaelt, wird nach dem zweiten Mal abgeschaltet und
# schuetzt danach gar nichts.
#
# Getragen wird diese Zusicherung nicht von einer Liste abgefangener
# Fehlerfaelle — die Liste waere nie vollstaendig, und beim Nachmessen erwies
# sich jeder einzelne Wachposten als entbehrlich, weil ihn ein anderer
# verdeckte. Sie ruht auf zwei Eigenschaften, die fuer *alle* Faelle gelten:
#
#   * Kein `set -e`, und jeder Pfad endet ausdruecklich mit `exit 0`. `set -e`
#     machte die Zusicherung davon abhaengig, dass jeder kuenftige git-Aufruf
#     sein `|| exit 0` mitbringt; vergisst einer es, bricht der Hook ab statt
#     still durchzugehen — und das faellt niemandem auf, weil der Fehlerfall
#     selten ist.
#   * Gemeldet wird nur, was als Zahl > 0 aus dem Repo kommt. Jeder andere
#     Wert — leer, Fehlertext, 0 — bedeutet Schweigen. Damit braucht kein
#     Fehlerfall einzeln bekannt zu sein, um harmlos zu sein.
#
# Dazu ein kurzes Zeitlimit auf jeden Netzaufruf. Ohne das haengt nicht der
# Aufruf, sondern der Sessionstart. Gibt es `timeout` (bzw. `gtimeout`) nicht,
# unterbleibt die Pruefung ganz: Ein ungebremstes `git fetch` waere das
# groessere Uebel — ein haengender Sessionstart wiegt schwerer als eine
# ausgefallene Warnung.
#
# Ausgabe erfolgt nur, wenn tatsaechlich Commits fehlen. Bei 0 schweigt er —
# eine Meldung, die immer kommt, wird nicht mehr gelesen.

# Sekunden je Netzaufruf. Es sind zwei (ls-remote, fetch).
zeitlimit="${CLAUDE_KLONCHECK_TIMEOUT:-5}"

if command -v timeout >/dev/null 2>&1; then
  mit_zeitlimit=(timeout -k 2 "$zeitlimit")
elif command -v gtimeout >/dev/null 2>&1; then
  mit_zeitlimit=(gtimeout -k 2 "$zeitlimit")
else
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

# Der Standard-Branch wird ermittelt, nicht angenommen. Drei Server im
# Portfolio heissen ihn `master`; ein fest verdrahtetes `main` scheitert dort
# mit «couldn't find remote ref main» — und wer das fuer ein Netzproblem
# haelt, arbeitet weiter auf genau dem veralteten Klon, vor dem hier gewarnt
# werden soll. Genau diese Annahme hat einen Branch schon einmal 15 Commits
# alt werden lassen.
standard="$("${mit_zeitlimit[@]}" git ls-remote --symref origin HEAD 2>/dev/null |
  sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')"

if [ -z "$standard" ]; then
  # Kein Netz: das lokal notierte origin/HEAD ist die zweitbeste Quelle.
  # Fehlt auch das, wird nicht geraten, sondern geschwiegen.
  standard="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)"
  standard="${standard#origin/}"
fi
[ -n "$standard" ] || exit 0

"${mit_zeitlimit[@]}" git fetch --quiet origin "$standard" >/dev/null 2>&1 || exit 0

# Gegen FETCH_HEAD, nicht gegen origin/$standard: FETCH_HEAD stammt aus genau
# dem Fetch, der eben erfolgreich war. Ein Remote-Tracking-Ref koennte aelter
# sein und meldete dann zu wenig Rueckstand.
#
# `HEAD` und nicht der Branchname: Gemessen wird der ausgecheckte Stand, und
# den gibt es auch im detached HEAD — `git symbolic-ref HEAD` gaebe dort auf.
rueckstand="$(git rev-list --count HEAD..FETCH_HEAD 2>/dev/null)"

# Alles, was keine Zahl > 0 ist, ist Schweigen — auch der leere String, den
# ein unerreichbares HEAD (frischer Klon eines leeren Repos) hier hinterlaesst.
case "$rueckstand" in
  '' | *[!0-9]*) exit 0 ;;
  0) exit 0 ;;
esac

if [ "$rueckstand" -eq 1 ]; then wort="Commit"; else wort="Commits"; fi

cat <<MELDUNG
Klon-Aktualitaet: Der ausgecheckte Stand liegt $rueckstand $wort hinter origin/$standard.

Erst nachziehen, dann arbeiten. Sonst faellt die CI moeglicherweise ueber ein
Gate, das im lokalen Stand noch gar nicht existiert — die Ursache steht dann
nicht im Diff, und die Fehlersuche laeuft in den falschen Dateien:

    git fetch origin $standard && git merge origin/$standard

(Auf einem Feature-Branch je nach Konvention stattdessen rebasen.)
MELDUNG

exit 0
