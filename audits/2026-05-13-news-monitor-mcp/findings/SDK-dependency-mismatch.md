# Finding: SDK-DEP-MISMATCH — `fastmcp` deklariert, aber `mcp.server.fastmcp` importiert

| Feld | Wert |
|---|---|
| **Severity** | **medium** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | SDK (Dependency Hygiene) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

`pyproject.toml:31-35`:

```toml
dependencies = [
    "fastmcp>=2.0.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
]
```

`server.py:30`:

```python
from mcp.server.fastmcp import FastMCP
```

Das ist die in das offizielle **`mcp`**-Paket eingebettete FastMCP-Variante — **nicht** das eigenständige `fastmcp`-Paket auf PyPI. Konsequenzen:

- `mcp` ist nicht in `dependencies`, wird aber transitiv über `fastmcp` installiert. Bei Major-Bump von `fastmcp` kann sich die Bundle-Version verschieben und der Import bricht.
- `fastmcp>=2.0.0` ist im Code **ungenutzt** (kein `import fastmcp`).
- Audit-Tools wie `pip check` oder `deptry` würden hier alarmieren.

## Expected Behavior

Eine von beiden, konsistent:

**Variante A — offizielles MCP-SDK:**
```toml
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
]
```
```python
from mcp.server.fastmcp import FastMCP
```

**Variante B — Standalone-fastmcp (`jlowin/fastmcp`):**
```python
from fastmcp import FastMCP
```

Empfehlung: **Variante A**, weil das offizielle SDK auf der aktuellen MCP-Spec ist und die README ohnehin nur `mcp.server.fastmcp` voraussetzt.

## Evidence

- `pyproject.toml:32` `"fastmcp>=2.0.0"`
- `server.py:30` `from mcp.server.fastmcp import FastMCP`
- `grep -rn "import fastmcp\|from fastmcp" src/` ⇒ keine Treffer

## Risk Description

- **Brittle Build:** Releases von `fastmcp` v3 könnten `mcp` als Sub-Dependency anders pinnen → Import-Break.
- **Falsche Dependency-Signale:** Security-Scans tracken Vulns auf `fastmcp` statt `mcp`.
- **Verschwendete Bandbreite:** Ein zusätzliches Paket wird installiert, das nichts tut.

## Remediation

```diff
  dependencies = [
-     "fastmcp>=2.0.0",
+     "mcp>=1.2.0",
      "httpx>=0.27.0",
      "pydantic>=2.0.0",
  ]
```

Anschliessend `uv pip install -e .` und Tests laufen lassen.

## Effort Estimate

**S** (< 1 Stunde).

## Verification After Fix

- `pip show mcp` zeigt explizite Top-Level-Dependency.
- `python -c "from news_monitor_mcp.server import mcp; print('ok')"` grün.
- CI-Job `Import-Test` läuft durch (s. `.github/workflows/ci.yml:36`).
