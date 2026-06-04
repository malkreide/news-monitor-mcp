# 🛡️ Security Policy & Posture

[🇩🇪 Deutsche Version](SECURITY.de.md)

---

## Reporting a Vulnerability

If you believe you have found a security vulnerability in `news-monitor-mcp`, please report it **privately** via GitHub's [Private Vulnerability Reporting](https://github.com/malkreide/news-monitor-mcp/security/advisories/new) feature.

Please do **not** open a public GitHub issue or post details on social media before the maintainer has had a chance to respond.

### What to include

- A short description of the issue and its potential impact
- Steps to reproduce (proof-of-concept code, `curl` invocation, etc.)
- The affected version (`__version__` in `src/news_monitor_mcp/__init__.py` or `pip show news-monitor-mcp`)
- Whether you believe it requires a coordinated disclosure timeline

### Response expectations

- Acknowledgement: within **5 working days**
- Triage and initial assessment: within **10 working days**
- Coordinated disclosure window: typically **90 days**, shorter for actively exploited issues

## Scope

This project covers:

- The MCP server itself (`src/news_monitor_mcp/`)
- The supplied `Dockerfile` and CI workflows
- The advisory layers documented in `audits/` (auth, redaction, atomic writes, path hardening)

**Out of scope:**

- Vulnerabilities in [WorldNewsAPI](https://worldnewsapi.com/) — report those to WorldNewsAPI directly.
- Vulnerabilities in upstream dependencies (`mcp`, `httpx`, `pydantic`, `starlette`, `uvicorn`) — report upstream; we will pick up fixes via Dependabot.
- Issues that require physical or local access to a developer machine running the stdio transport.

## Supported Versions

The latest tag on `main` is supported. There is no LTS branch.

| Version | Supported |
|---------|-----------|
| `main` / latest release | ✅ |
| anything older          | ❌ |

## Hardening Baseline

`news-monitor-mcp` follows the **SOLID-for-MCP** principles. Concrete controls in place (with audit-ID references):

- **Sandbox** — non-root container, dedicated UID `10001`, no shell, restricted bind mounts (`SCALE-NO-DOCKERFILE`)
- **OAuth / Bearer Auth** — `MCP_BEARER_TOKEN` mandatory in HTTP mode (`SEC-HTTP-NO-AUTH`)
- **Least Privilege** — `alerts.json` at `0o600`, parent dir at `0o700` (`SEC-ALERTS-PATH`)
- **Idempotency** — atomic writes via `fsync` + `os.replace` (`ARCH-CONCURRENCY`)
- **Defense in Depth** — `SecretStr` API-key, header auth, redaction filter, origin allowlist (`SEC-API-KEY-HANDLING`, `OBS-LOG-UNSTRUCTURED`)

The audit history lives under [`audits/`](audits/).
