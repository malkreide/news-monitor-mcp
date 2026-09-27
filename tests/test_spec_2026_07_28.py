"""Spec 2026-07-28 nativ: was der Server selbst beitraegt, gemessen am ASGI-Stack.

`test_protocol_version.py` pinnt, WELCHE Revisionen das SDK spricht. Diese
Datei prueft, was der Server in der modernen Aera daraus macht — die Teile, die
das SDK nicht von allein richtig setzt:

* **Identitaet** (SEP-2575): ohne Handshake stellt sich der Server in jedem
  Ergebnis vor. Vor dieser Aenderung stand dort `"version": ""`.
* **Keine Sitzungen** (SEP-2567): auch die Handshake-Aera laeuft zustandslos,
  ohne `Mcp-Session-Id`.
* **Menschliche Bestaetigung ueber `input_required`** (SEP-2322, MRTR) fuer
  `news_alert_delete` und `news_cache_clear` — mit dem `confirm`-Weg als
  Rueckfall fuer jeden Client, der nicht fragen kann.

Alle Aufrufe laufen durch `build_http_app`, also durch Bearer-, Origin- und
Request-ID-Middleware: ein Test gegen die nackte Funktion saehe weder den
Envelope noch die Bindung des `requestState` an die Argumente.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

import news_monitor_mcp.app as _app
import news_monitor_mcp.tools.alerts_tools as _tools_alerts
import news_monitor_mcp.tools.cache_admin as _tools_cache
from news_monitor_mcp import __version__
from news_monitor_mcp.confirmation import (
    Bestaetigung,
    Entscheid,
    OhneRueckfrage,
    entscheid,
)
from news_monitor_mcp.server import AlertManager, NewsCache, build_http_app

MODERN = "2026-07-28"
LEGACY = "2025-11-25"
TOKEN = "probe-token"
FORM = {"elicitation": {"form": {}}}

_BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Host": "127.0.0.1:8000",
    "Authorization": f"Bearer {TOKEN}",
}


def _json(response: httpx.Response) -> dict[str, Any]:
    body = response.text
    for line in body.splitlines():  # SSE-Rahmen abstreifen, falls vorhanden
        if line.startswith("data: "):
            body = line[len("data: ") :]
    return json.loads(body)


async def _modern(method: str, params: dict[str, Any], caps: dict[str, Any] | None = None) -> dict[str, Any]:
    """Eine Anfrage im Pro-Request-Envelope, durch den ganzen Stack."""
    params = {
        **params,
        "_meta": {
            "io.modelcontextprotocol/protocolVersion": MODERN,
            "io.modelcontextprotocol/clientCapabilities": caps or {},
            "io.modelcontextprotocol/clientInfo": {"name": "probe", "version": "1"},
        },
    }
    headers = {**_BASE_HEADERS, "MCP-Protocol-Version": MODERN, "Mcp-Method": method}
    if method == "tools/call":
        headers["Mcp-Name"] = params["name"]
    app = build_http_app(TOKEN, frozenset(), None, "127.0.0.1")
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
            response = await client.post(
                "/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            )
    return _json(response)


async def _call(tool: str, args: dict[str, Any], caps: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    reply = await _modern("tools/call", {"name": tool, "arguments": {"params": args}, **extra}, caps)
    assert "result" in reply, reply
    return reply["result"]


def _text(result: dict[str, Any]) -> str:
    assert result["resultType"] == "complete", result
    return result["content"][0]["text"]


@pytest.fixture
def alert(tmp_path, monkeypatch) -> tuple[AlertManager, str]:
    mgr = AlertManager(file_path=str(tmp_path / "alerts.json"))
    aid = mgr.create(
        {
            "name": "Schulamt Negativalert",
            "entity": "Schulamt Zuerich",
            "language": "de",
            "source_country": "ch",
            "days_back": 7,
            "condition_type": "volume_above",
            "threshold": 1.0,
            "keyword": None,
        }
    )
    monkeypatch.setattr(_app, "_alert_manager", mgr)
    monkeypatch.setattr(_tools_alerts, "_alert_manager", mgr)
    return mgr, aid


@pytest.fixture
def cache(monkeypatch) -> NewsCache:
    c = NewsCache()
    c.set("search", {"q": "a"}, {"d": 1})
    monkeypatch.setattr(_app, "_cache", c)
    monkeypatch.setattr(_tools_cache, "_cache", c)
    return c


# ---------------------------------------------------------------------------
# Identitaet
# ---------------------------------------------------------------------------


async def test_server_discover_nennt_version_und_titel() -> None:
    """`serverInfo` ersetzt die Vorstellung im Handshake — und trug `version: ""`."""
    reply = await _modern("server/discover", {})
    result = reply["result"]
    info = result["_meta"]["io.modelcontextprotocol/serverInfo"]
    assert info["name"] == "news_monitor_mcp"
    assert info["version"] == __version__
    assert info["version"]  # nicht leer, auch ohne Installation ("0.0.0+source")
    assert info["title"] == "News Monitor"
    assert info["websiteUrl"] == "https://github.com/malkreide/news-monitor-mcp"
    assert MODERN in result["supportedVersions"]


async def test_jedes_ergebnis_traegt_die_identitaet(cache) -> None:
    """SHOULD in jedem Ergebnis — nicht nur in `server/discover`."""
    result = await _call("news_cache_stats", {})
    assert result["_meta"]["io.modelcontextprotocol/serverInfo"]["version"] == __version__


# ---------------------------------------------------------------------------
# Keine Sitzungen, auch nicht in der Handshake-Aera
# ---------------------------------------------------------------------------


async def test_handshake_aera_vergibt_keine_session_id() -> None:
    app = build_http_app(TOKEN, frozenset(), None, "127.0.0.1")
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
            init = await client.post(
                "/mcp",
                headers=_BASE_HEADERS,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": LEGACY,
                        "capabilities": {},
                        "clientInfo": {"name": "legacy-client", "version": "1"},
                    },
                },
            )
            assert init.status_code == 200
            assert "mcp-session-id" not in init.headers
            # Folgeanfrage ohne jede Session-ID: eine zustandsbehaftete
            # Instanz wiese sie mit 400 ab.
            listed = await client.post(
                "/mcp",
                headers={**_BASE_HEADERS, "MCP-Protocol-Version": LEGACY},
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            )
    assert listed.status_code == 200, listed.text
    assert len(_json(listed)["result"]["tools"]) == 15


# ---------------------------------------------------------------------------
# Menschliche Bestaetigung ueber input_required
# ---------------------------------------------------------------------------


def _frage(result: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    assert result["resultType"] == "input_required", result
    ((key, request),) = result["inputRequests"].items()
    return key, request


async def test_alert_loeschen_fragt_die_person_auch_bei_confirm_true(alert) -> None:
    """Der Kern: ein vom Modell gesetztes `confirm=true` ueberspringt die Frage nicht."""
    mgr, aid = alert
    result = await _call("news_alert_delete", {"alert_id": aid, "confirm": True}, FORM)
    _, request = _frage(result)
    assert request["method"] == "elicitation/create"
    assert "Schulamt Negativalert" in request["params"]["message"]
    schema = request["params"]["requestedSchema"]
    assert schema["properties"]["loeschen"]["type"] == "boolean"
    assert schema["required"] == ["loeschen"]
    assert result["requestState"]
    assert mgr.get(aid) is not None


async def test_alert_loeschen_nach_zustimmung(alert) -> None:
    mgr, aid = alert
    args = {"alert_id": aid}
    first = await _call("news_alert_delete", args, FORM)
    key, _ = _frage(first)
    second = await _call(
        "news_alert_delete",
        args,
        FORM,
        inputResponses={key: {"action": "accept", "content": {"loeschen": True}}},
        requestState=first["requestState"],
    )
    assert "geloescht" in _text(second)
    assert mgr.get(aid) is None


@pytest.mark.parametrize(
    "antwort",
    [
        {"action": "accept", "content": {"loeschen": False}},
        {"action": "decline"},
        {"action": "cancel"},
    ],
    ids=["nein", "abgelehnt", "abgebrochen"],
)
async def test_alert_bleibt_ohne_zustimmung(alert, antwort) -> None:
    mgr, aid = alert
    args = {"alert_id": aid, "confirm": True}
    first = await _call("news_alert_delete", args, FORM)
    key, _ = _frage(first)
    second = await _call(
        "news_alert_delete", args, FORM, inputResponses={key: antwort}, requestState=first["requestState"]
    )
    text = _text(second)
    assert "Abgebrochen" in text
    assert "confirm=true" not in text  # kein Hinweis, der das Modell zum Umgehen einlaedt
    assert mgr.get(aid) is not None


async def test_antwort_ohne_gestellte_frage_zaehlt_nicht(alert) -> None:
    """Eine mitgeschickte Zustimmung ohne `requestState` aus der Frage-Runde
    ist nicht die Antwort auf diese Frage — es wird neu gefragt."""
    mgr, aid = alert
    key = "news_monitor_mcp.tools.alerts_tools:_frage_alert_loeschen"
    result = await _call(
        "news_alert_delete",
        {"alert_id": aid},
        FORM,
        inputResponses={key: {"action": "accept", "content": {"loeschen": True}}},
    )
    _frage(result)
    assert mgr.get(aid) is not None


@pytest.mark.parametrize(
    "caps",
    [{}, {"elicitation": {"url": {}}}],
    ids=["ohne-elicitation", "nur-url-elicitation"],
)
async def test_ohne_formular_bleibt_es_beim_confirm_weg(alert, caps) -> None:
    """Rueckfall: wer nicht fragen kann, bekommt die Aufforderung — keinen Abbruch
    mit `MissingRequiredClientCapability`."""
    mgr, aid = alert
    text = _text(await _call("news_alert_delete", {"alert_id": aid}, caps))
    assert "confirm=true" in text
    assert mgr.get(aid) is not None
    text = _text(await _call("news_alert_delete", {"alert_id": aid, "confirm": True}, caps))
    assert "geloescht" in text
    assert mgr.get(aid) is None


async def test_unbekannter_alert_loest_keine_frage_aus(alert) -> None:
    result = await _call("news_alert_delete", {"alert_id": "alert_doesnotexist"}, FORM)
    assert "nicht gefunden" in _text(result)


async def test_handshake_aera_bleibt_beim_confirm_weg(alert) -> None:
    """Selbst mit deklarierter Elicitation: in der Handshake-Aera gibt es kein
    `input_required`, und einen Rueckkanal hat der zustandslose Transport nicht."""
    mgr, aid = alert
    app = build_http_app(TOKEN, frozenset(), None, "127.0.0.1")
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
            await client.post(
                "/mcp",
                headers=_BASE_HEADERS,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": LEGACY,
                        "capabilities": FORM,
                        "clientInfo": {"name": "legacy-client", "version": "1"},
                    },
                },
            )
            response = await client.post(
                "/mcp",
                headers={**_BASE_HEADERS, "MCP-Protocol-Version": LEGACY},
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "news_alert_delete", "arguments": {"params": {"alert_id": aid}}},
                },
            )
    result = _json(response)["result"]
    assert "confirm=true" in result["content"][0]["text"]
    assert mgr.get(aid) is not None


async def test_cache_leeren_fragt_und_leert_nach_zustimmung(cache) -> None:
    first = await _call("news_cache_clear", {}, FORM)
    key, request = _frage(first)
    assert "GESAMTEN Cache" in request["params"]["message"]
    assert cache.get("search", {"q": "a"}) is not None
    second = await _call(
        "news_cache_clear",
        {},
        FORM,
        inputResponses={key: {"action": "accept", "content": {"loeschen": True}}},
        requestState=first["requestState"],
    )
    assert "geleert" in _text(second)
    assert cache.get("search", {"q": "a"}) is None


async def test_cache_leeren_mit_unbekanntem_typ_fragt_nicht(cache) -> None:
    """Erst die Eingabe pruefen, dann fragen: keine Frage fuer einen Aufruf, der
    ohnehin scheitert."""
    text = _text(await _call("news_cache_clear", {"tool_type": "gibtsnicht"}, FORM))
    assert "Unbekannter Tool-Typ" in text


def test_das_bestaetigungsfeld_erscheint_nicht_im_input_schema() -> None:
    """Die Antwort der Person darf kein Argument sein, das das Modell setzt."""
    from news_monitor_mcp.app import mcp

    for name in ("news_alert_delete", "news_cache_clear"):
        schema = mcp._tool_manager.get_tool(name).parameters
        assert set(schema["properties"]) == {"params"}, schema["properties"]


# ---------------------------------------------------------------------------
# Die Uebersetzung selbst
# ---------------------------------------------------------------------------


def _accepted(data: Any) -> Any:
    from mcp.server.mcpserver import AcceptedElicitation

    return AcceptedElicitation[Any].model_construct(data=data)


@pytest.mark.parametrize(
    ("outcome", "confirm", "erwartet"),
    [
        (None, False, Entscheid.OFFEN),
        (None, True, Entscheid.LOESCHEN),
        ("ohne-false", True, Entscheid.OFFEN),
        ("ohne-true", False, Entscheid.LOESCHEN),
        ("ja", False, Entscheid.LOESCHEN),
        ("nein", True, Entscheid.ABGELEHNT),
        ("decline", True, Entscheid.ABGELEHNT),
        ("cancel", True, Entscheid.ABGELEHNT),
    ],
)
def test_entscheid(outcome: Any, confirm: bool, erwartet: Entscheid) -> None:
    from mcp.server.mcpserver import CancelledElicitation, DeclinedElicitation

    built = {
        None: None,
        "ohne-false": _accepted(OhneRueckfrage(confirm=False)),
        "ohne-true": _accepted(OhneRueckfrage(confirm=True)),
        "ja": _accepted(Bestaetigung(loeschen=True)),
        "nein": _accepted(Bestaetigung(loeschen=False)),
        "decline": DeclinedElicitation(),
        "cancel": CancelledElicitation(),
    }[outcome]
    assert entscheid(built, confirm) is erwartet


@pytest.mark.parametrize(
    ("version", "caps", "erwartet"),
    [
        (MODERN, FORM, True),
        (MODERN, {"elicitation": {}}, True),  # nacktes `{}` aus der Zeit vor den Modi
        (MODERN, {"elicitation": {"url": {}}}, False),
        (MODERN, {}, False),
        # Der Fall, den der HTTP-Test oben nicht trennen kann: dort kennt der
        # zustandslose Handshake gar keine Capabilities. Auf stdio schon — ohne
        # die Versionspruefung ginge dort ein `elicitation/create` ueber den
        # Rueckkanal, und das Verhalten der Handshake-Aera haette sich still
        # geaendert.
        (LEGACY, FORM, False),
        (None, FORM, False),
    ],
)
def test_fragt_den_menschen(version: str | None, caps: dict[str, Any], erwartet: bool) -> None:
    from types import SimpleNamespace

    from mcp.types import ClientCapabilities

    from news_monitor_mcp.confirmation import fragt_den_menschen

    ctx = SimpleNamespace(protocol_version=version, client_capabilities=ClientCapabilities.model_validate(caps))
    assert fragt_den_menschen(ctx) is erwartet  # type: ignore[arg-type]
