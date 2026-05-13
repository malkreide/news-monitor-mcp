"""MCP-Tool-Registrierung — Aufgeteilt nach Tool-Kategorie.

Beim Import dieser Submodule werden ihre `@mcp.tool`-Dekoratoren ausgefuehrt
und damit die Tools beim FastMCP-Server registriert. `server.py` muss diese
Module einmalig importieren (typischerweise als
`import news_monitor_mcp.tools  # noqa: F401`), damit alle 15 Tools verfuegbar
sind.
"""

from news_monitor_mcp.tools import alerts_tools, cache_admin, monitoring  # noqa: F401

__all__ = ["monitoring", "alerts_tools", "cache_admin"]
