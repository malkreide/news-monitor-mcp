# Profile Snapshot — news-monitor-mcp

| Feld | Wert |
|---|---|
| **Server-Name** | `news-monitor-mcp` |
| **Version** | 0.2.0 |
| **Repo-URL** | https://github.com/malkreide/news-monitor-mcp |
| **Branch (Audit)** | `claude/audit-mcp-skill-a04O4` |
| **Sprache / Runtime** | Python 3.11+ |
| **SDK** | MCP Python SDK / FastMCP (`mcp.server.fastmcp`) |
| **Transport** | Dual: `stdio` (default) + `streamable-http` (`--http`, `0.0.0.0:8000`) |
| **Auth-Modell** | **Keine** auf MCP-Ebene. Upstream-Auth via API-Key (`WORLD_NEWS_API_KEY`) gegen WorldNewsAPI. |
| **Datenklassifikation** | Öffentliche journalistische Daten (low). Alerts-File kann jedoch Personennamen / Institutionsnamen enthalten → mittlere Sensitivität bei Personenbezug. |
| **Write-Capability** | Ja (lokal): `~/.news-monitor-mcp/alerts.json` (create/delete). In-Memory-Cache. Keine Writes an externe Systeme. |
| **Tool-Anzahl** | 15 (9 monitoring + 4 alerts + 2 cache). README behauptet teilweise 9 — Inkonsistenz, siehe ARCH-Finding. |
| **Read-Only-Anteil** | 12 / 15 tragen `readOnlyHint: true`. |
| **Deployment-Ziele** | Claude Desktop (stdio), claude.ai via Render.com (streamable-http), Docker (Doku ohne Dockerfile). |
| **Persistenz** | Lokales JSON-File für Alerts; In-Memory-Cache. Keine DB. |
| **Externe Abhängigkeiten** | WorldNewsAPI (REST/HTTPS). |
| **Lizenz** | MIT |
| **Compliance-Layer** | Schweizer Kontext (Schulamt Zürich Use-Case) → CH-Layer (DSG/EDÖB) anwendbar. |

## Profile-Validierung

- [x] Transport: gesetzt (dual)
- [x] Auth-Modell: gesetzt (none + upstream key)
- [x] Daten-Klassifikation: gesetzt
- [x] Write-Capability: gesetzt
- [x] Deployment: gesetzt
- [x] Repo-URL: gesetzt

Keine Profile-Lücken. Audit kann fortgesetzt werden.
