"""WorldNewsAPI HTTP-Client + Header-basiertes API-Key-Handling.

Behebt Audit-Finding SEC-API-KEY-HANDLING (high, 2026-05-13): API-Key wandert
vom URL-Query in den `x-api-key`-Header und wird in `pydantic.SecretStr`
gewickelt, damit `str()`/`repr()` ihn nicht versehentlich leaken.

Lifecycle: der httpx-AsyncClient wird lazy in `_get_client()` erzeugt und in
`close_client()` (vom `server_lifespan` aufgerufen) sauber geschlossen.
Behebt SDK-LIFESPAN.
"""

import os
from typing import Optional

import httpx
from pydantic import SecretStr

from . import __version__

BASE_URL = "https://api.worldnewsapi.com"
DEFAULT_TIMEOUT = 30.0
MAX_RESULTS = 100
DEFAULT_RESULTS = 10

SWISS_SOURCE_COUNTRIES = "ch"
DACH_SOURCE_COUNTRIES = "ch,de,at"

_client: Optional[httpx.AsyncClient] = None


class UpstreamShapeError(RuntimeError):
    """Die Quelle hat geantwortet, aber nicht mit dem, womit sie antwortet.

    Bewusst getrennt von einem Transportfehler: Warten hilft beim einen und
    nie beim anderen.
    """


def articles_of(payload: object, endpoint: str = "") -> list:
    """Die Artikelliste einer Antwort — oder ein Fehler, nie stillschweigend [].

    WARUM DAS NICHT `payload.get("news", [])` BLEIBEN DURFTE. Der Ausdruck
    beantwortet zwei voellig verschiedene Faelle gleich: «die Quelle hat
    nichts gefunden» und «die Quelle antwortet anders, als wir annehmen». Aus
    dem zweiten wird damit die Aussage «0 Ergebnisse» — vollstaendig,
    plausibel, formatiert und falsch.

    Das ist kein hypothetisches Risiko. In `global-education-mcp` desselben
    Portfolios stand genau dieses Muster, und weil der Umschlag der Quelle
    inzwischen anders hiess, kam aus **jeder** Antwort eine leere Liste — bei
    128 gruenen Tests.

    Ein leeres `news` bleibt eine Aussage der Quelle und kommt als leere
    Liste zurueck. Ein FEHLENDES `news` ist keine Aussage ueber die Nachrichten,
    sondern ueber die Antwort, und wird als solcher gemeldet.
    """
    wo = f" von `{endpoint}`" if endpoint else ""
    if not isinstance(payload, dict):
        raise UpstreamShapeError(
            f"Die Antwort{wo} ist {type(payload).__name__}, kein Objekt. "
            "Das ist keine leere Treffermenge, sondern eine andere Antwortform."
        )
    if "news" not in payload:
        raise UpstreamShapeError(
            f"Die Antwort{wo} fuehrt kein Feld `news`. Vorhanden: "
            f"{sorted(payload)}. Das ist keine leere Treffermenge, sondern "
            "eine andere Antwortform — die Abfrage gehoert geprueft, nicht "
            "wiederholt."
        )
    news = payload["news"]
    if not isinstance(news, list):
        raise UpstreamShapeError(f"`news`{wo} ist {type(news).__name__}, nicht eine Liste.")
    return news


def _get_api_key() -> Optional[SecretStr]:
    """Liest den API-Key aus dem Env und wickelt ihn in SecretStr, um versehentliche
    Stringifizierung in Logs/Repr zu verhindern. SecretStr.__repr__ liefert
    '**********', SecretStr.__str__ ebenfalls — nur .get_secret_value() entpackt."""
    raw = os.environ.get("WORLD_NEWS_API_KEY")
    return SecretStr(raw) if raw else None


def _check_api_key() -> Optional[SecretStr]:
    return _get_api_key()


def _auth_headers(api_key: SecretStr) -> dict[str, str]:
    """Header-basierte Auth fuer WorldNewsAPI (https://worldnewsapi.com/docs/authentication/).

    Vermeidet, dass der Key als URL-Query-Parameter in HTTP-Logs, Proxy-Caches
    oder Tracing-Backends landet.
    """
    return {"x-api-key": api_key.get_secret_value()}


def _get_client() -> httpx.AsyncClient:
    """Lazy-erzeugt den globalen httpx-Client. Wird im Lifespan via close_client
    geschlossen.

    Hinweis: SecretStr-Wrapping wird im Header pro Request angewendet, nicht
    direkt auf dem Client — so muessen wir den Klartext nicht ueber die ganze
    Lebensdauer des Clients halten.
    """
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=BASE_URL, timeout=DEFAULT_TIMEOUT, headers={"User-Agent": f"news-monitor-mcp/{__version__}"}
        )
    return _client


def get_current_client() -> Optional[httpx.AsyncClient]:
    """Gibt den aktuellen Client zurueck, ohne ihn lazy zu erzeugen. Hauptsaechlich
    fuer den Lifespan-Teardown."""
    return _client


async def close_client() -> None:
    """Schliesst den globalen httpx-Client und setzt den Slot auf None. Idempotent."""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        finally:
            _client = None
