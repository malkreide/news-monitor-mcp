# Finding: SEC-MD5 — `hashlib.md5` ohne `usedforsecurity=False`

| Feld | Wert |
|---|---|
| **Severity** | **low** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | SEC (Crypto Hygiene) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

`src/news_monitor_mcp/server.py:67`:

```python
return hashlib.md5(raw.encode("utf-8")).hexdigest()
```

Verwendung als Cache-Key — funktional **kein** Sicherheits-Use-Case, aber:

- `hashlib.md5(...)` ohne `usedforsecurity=False` schlägt auf FIPS-Mode-Systemen fehl (RHEL/CentOS mit FIPS-fips-enabled).
- Bandit/CodeQL/ruff-`S324` flaggen den Call als Warning.

## Expected Behavior

```python
hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()
```

Oder `hashlib.sha256(...)` (Cache-Keys werden minimal länger, keine Performance-Auswirkung).

## Evidence

- `server.py:67` einzige Fundstelle (`grep -n md5 src/`).

## Risk Description

- Deployment auf FIPS-geblockten Systemen scheitert beim ersten Cache-`set`.
- Security-Scanner-Noise in Audits / CI.

## Remediation

```diff
- return hashlib.md5(raw.encode("utf-8")).hexdigest()
+ return hashlib.sha256(raw.encode("utf-8")).hexdigest()
```

## Effort Estimate

**S** (< 5 Minuten).

## Verification After Fix

- `ruff check --select S` zeigt keine S324-Warnung mehr.
- Tests laufen weiterhin grün (`test_cache_*`).
