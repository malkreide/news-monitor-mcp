> ✅ **Re-Audit Status:** `closed` — gemerged via PR #2.

# Finding: SEC-HTTP-NO-AUTH — Streamable-HTTP-Transport ohne Authentifizierung auf 0.0.0.0

| Feld | Wert |
|---|---|
| **Severity** | **critical** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | SEC (Transport-Auth) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

In `src/news_monitor_mcp/server.py:1116-1126` startet `main()` den HTTP-Transport ohne jegliche Auth-Schicht:

```python
def main() -> None:
    parser = argparse.ArgumentParser(description="News Monitor MCP Server v0.2.0")
    parser.add_argument("--http", action="store_true", ...)
    parser.add_argument("--port", type=int, default=8000, ...)
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port)
```

`README.md` empfiehlt explizit Deployment auf Render.com mit Anbindung an `claude.ai` (`https://your-app.onrender.com/mcp`) — der HTTP-Endpoint wäre damit **öffentlich erreichbar**, ohne dass irgendwer authentifiziert sein muss, um alle 15 Tools aufzurufen.

## Expected Behavior

Per SOLID-für-MCP-Mantra **OAuth 2.1** (zweites "O"):

- HTTP-Transport in Production hinter OAuth 2.1 mit PKCE und Resource Indicators
- Alternativ: Bearer-Token-Auth mit Token-Rotation, mindestens Reverse-Proxy mit Basic-Auth-Header-Forwarding
- `Origin`-Validierung gegen Allowlist (DNS-Rebinding-Schutz, MCP-Spec)
- Niemals `0.0.0.0` ohne Auth in Public-Cloud-Deployment

## Evidence

- File: `src/news_monitor_mcp/server.py:1124`
  ```python
  mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port)
  ```
- File: `README.md:143-156` — Render.com-Deployment-Anleitung ohne Auth-Hinweis
- Keine Auth-Middleware, kein Token-Check, kein `Origin`-Header-Check im Codebase nachweisbar

## Risk Description

- **Quota-Diebstahl:** Jede·r mit der Render-URL kann den `WORLD_NEWS_API_KEY` über den Server abrufen. WorldNewsAPI Free-Tier (1'000 Calls/Monat) ist binnen Minuten leer; bezahlte Tiers (bis 1M Calls) verursachen finanziellen Schaden.
- **Alert-Manipulation:** Unauthentifizierte Aufrufer können `news_alert_create` / `news_alert_delete` benutzen. Bei mehreren parallelen Sessions auf demselben Render-Service teilen alle dieselbe `alerts.json` → Alert-Daten vermischen sich zwischen unberechtigten Aufrufern.
- **DNS-Rebinding:** Ohne `Origin`-Validierung kann ein bösartiges Webfrontend via Browser den Server eines anderen Users reachen (klassisches MCP-Risk).
- **Reputation-Risk:** Server steht in `malkreide`-Portfolio mit Schweizer Behörden-Use-Case; ein Quota-Drain-Vorfall trifft den ganzen Portfolio-Ruf.

## Remediation

Reihenfolge: zuerst minimaler Block (Bearer-Token), danach OAuth-Roadmap.

```diff
+ import secrets
+ from starlette.middleware.base import BaseHTTPMiddleware
+ from starlette.responses import JSONResponse
+
+ MCP_BEARER_TOKEN = os.environ.get("MCP_BEARER_TOKEN")
+
+ class BearerAuthMiddleware(BaseHTTPMiddleware):
+     async def dispatch(self, request, call_next):
+         if MCP_BEARER_TOKEN is None:
+             return JSONResponse({"error": "server misconfigured: MCP_BEARER_TOKEN not set"}, status_code=503)
+         auth = request.headers.get("Authorization", "")
+         if not auth.startswith("Bearer "):
+             return JSONResponse({"error": "unauthorized"}, status_code=401)
+         token = auth[len("Bearer "):]
+         if not secrets.compare_digest(token, MCP_BEARER_TOKEN):
+             return JSONResponse({"error": "unauthorized"}, status_code=401)
+         return await call_next(request)
```

Schritte:

1. `MCP_BEARER_TOKEN` als Pflicht-Env in HTTP-Mode dokumentieren (`README.md`, Render-Setup).
2. `mcp.run(...)` durch Custom-Starlette-App ersetzen, die FastMCP-Endpoints unter Middleware mountet.
3. `Origin`-Allowlist via `MCP_ALLOWED_ORIGINS` (CSV).
4. Mittelfristig: OAuth 2.1 mit PKCE + Resource Indicators (siehe MCP-Spec 2025-06).
5. `host="0.0.0.0"` nur im Container-Modus; lokal `127.0.0.1`.

## Effort Estimate

**M** (1–3 Tage): Bearer-Token + Origin-Check + Doku.
OAuth 2.1 zusätzlich **L** (1–2 Wochen).

## Dependencies / Blockers

Keine. Kann unabhängig umgesetzt werden.

## Verification After Fix

- `curl -i https://server/mcp` ohne Token ⇒ 401
- `curl -i -H "Authorization: Bearer $TOKEN" https://server/mcp/tools` ⇒ 200
- Pytest: `test_http_requires_auth` (siehe OPS-Finding für Test-Infrastruktur).
