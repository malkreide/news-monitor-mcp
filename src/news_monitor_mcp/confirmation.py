"""Menschliche Bestaetigung fuer die zwei loeschenden Tools, nativ ab Spec 2026-07-28.

Bis hierher trug `confirm=true` die ganze Last von HITL-DESTRUCTIVE-TOOLS: der
Erstaufruf lieferte eine Aufforderung, der zweite Aufruf mit `confirm=true`
loeschte. Den zweiten Aufruf setzt aber das Modell ab, nicht ein Mensch — die
«Bestaetigung» war eine, die sich das Modell selbst erteilen konnte.

2026-07-28 (SEP-2322, Multi Round-Trip Requests) gibt dem Server einen Weg zum
Menschen, der keinen Rueckkanal braucht: der Server antwortet mit
`resultType: "input_required"` und einer `elicitation/create`-Anfrage, der
Client fragt die Person und wiederholt den Aufruf mit `inputResponses`. Die
Antwort kommt vom Client, nicht aus den Tool-Argumenten — das Modell kann sie
nicht mit einem Parameter vorwegnehmen.

Wann gefragt wird, ist eng gefasst und beidseitig erklaert:

* nur in der modernen Aera (die Anfrage traegt `2026-07-28`) — im Handshake
  bliebe nur `elicitation/create` ueber den Rueckkanal, und den hat der
  zustandslose HTTP-Transport nicht;
* nur wenn der Client Formular-Elicitation deklariert. Ohne sie bricht das SDK
  den Aufruf mit `MissingRequiredClientCapability` ab; stattdessen bleibt es
  dann beim `confirm`-Weg, den jeder Client kann.

Wird gefragt, entscheidet die Antwort der Person, und `confirm` spielt keine
Rolle mehr: ein vom Modell gesetztes `confirm=true` darf die Frage nicht
ueberspringen, sonst waere sie wieder die Selbstbestaetigung von vorher.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from mcp.server.mcpserver import AcceptedElicitation, Context
from mcp.types.version import is_version_at_least
from pydantic import BaseModel, Field

# Erste Revision mit `input_required`. Gepinnt, nicht `LATEST_MODERN_VERSION`:
# der Alias wandert mit dem SDK, die Revision, die das Muster einfuehrte, nicht.
MRTR_VERSION = "2026-07-28"


class Bestaetigung(BaseModel):
    """Das Formular, das die Person sieht. Ein Pflichtfeld, kein Default."""

    loeschen: bool = Field(title="Loeschen", description="Ja: endgueltig loeschen. Nein: nichts veraendern.")


@dataclass(frozen=True)
class OhneRueckfrage:
    """Der Resolver hat niemanden gefragt; es gilt das `confirm` des Aufrufs."""

    confirm: bool


class Entscheid(Enum):
    LOESCHEN = "loeschen"
    ABGELEHNT = "abgelehnt"  # die Person hat nein gesagt, abgelehnt oder abgebrochen
    OFFEN = "offen"  # niemand gefragt, confirm fehlt: Aufforderung zurueckgeben


def fragt_den_menschen(ctx: Context) -> bool:
    """True, wenn diese Anfrage die Person ueber `input_required` erreichen kann."""
    version = ctx.protocol_version
    if version is None or not is_version_at_least(version, MRTR_VERSION):
        return False
    caps = ctx.client_capabilities
    elicitation = caps.elicitation if caps is not None else None
    # Dieselbe Lesart wie das SDK: ein nacktes `elicitation: {}` (vor den Modi)
    # zaehlt als Formular, ein reines `url` nicht.
    return elicitation is not None and (elicitation.form is not None or elicitation.url is None)


def entscheid(outcome: Optional[Any], confirm: bool) -> Entscheid:
    """Uebersetzt das Resolver-Ergebnis in eine der drei Moeglichkeiten.

    `outcome` ist `None`, wenn kein Resolver lief — der direkte Funktionsaufruf
    aus Tests oder eigenem Code. Dann gilt `confirm` wie bisher.
    """
    if outcome is None:
        return Entscheid.LOESCHEN if confirm else Entscheid.OFFEN
    if not isinstance(outcome, AcceptedElicitation):
        return Entscheid.ABGELEHNT
    data = outcome.data
    if isinstance(data, OhneRueckfrage):
        return Entscheid.LOESCHEN if data.confirm else Entscheid.OFFEN
    return Entscheid.LOESCHEN if data.loeschen else Entscheid.ABGELEHNT
