# Finding: SCALE-STATEFUL — In-Memory-State verhindert horizontale Skalierung

| Feld | Wert |
|---|---|
| **Severity** | **high** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | SCALE (Stateless Transport / Multi-Worker) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

- `NewsCache` (`server.py:59-118`) hält Daten im Prozess-RAM.
- `AlertManager` (`server.py:121-198`) persistiert in lokalem File `~/.news-monitor-mcp/alerts.json`.
- Render.com-Deployment (README-empfohlen) ist Single-Container; aber Render kann auto-scaling Replicas starten — jedes Replica hätte einen eigenen Cache und (je nach Storage-Mount) eigene `alerts.json`.
- Cache-Eviction passiv nur bei `stats()` (`server.py:97-102`). Kein Hintergrund-Sweep → unbounded Growth bei hoher Query-Vielfalt.

## Expected Behavior

Für SCALE-Best-Practice:

- Cache via Redis / Upstash (TTL serverseitig). Auf Render: `REDIS_URL` Env-Var.
- Alerts in Managed-DB (Postgres, Render-managed) oder S3-kompatiblem Bucket mit Lease/Lock.
- Lokales File / In-Mem nur als optionaler Fallback für stdio-Mode.

## Evidence

- `server.py:201-202` Singletons.
- `server.py:97-102` `evict_expired` — wird nur in `stats()` aufgerufen.
- README-Deployment-Sektion empfiehlt Render ohne Hinweis auf Single-Replica-Constraint.

## Risk Description

- **Inkonsistente Alert-Sicht:** Bei 2+ Replicas kann Alert auf Replica A erstellt sein, Check auf Replica B sieht ihn nicht.
- **Cache-Fragmentierung:** Hit-Rate sinkt linear mit Replica-Anzahl.
- **Memory-Bloat:** Lang laufende Prozesse mit vielen unterschiedlichen Queries akkumulieren Cache → OOM-Kill auf Render Free-Tier (512MB).
- **Free-Tier-Render schläft ein:** Render sleeps Free Services nach 15 min Idle → Cache verliert sich ohnehin, aber Alert-File wird im Container-FS auch resettet, wenn kein Persistent-Disk gemountet ist → **Alert-Verlust** bei jedem Idle-Restart.

## Remediation

Stufenweise:

1. **Kurzfristig (Doku):** README ergänzen: "Free-Tier-Render verliert Alerts bei Sleep. Für Persistenz: Persistent-Disk anhängen oder Postgres anbinden."
2. **Mittelfristig (Code):** Cache-Backend abstrahieren (`CacheBackend`-Protocol), zwei Implementierungen `InMemoryCache` + `RedisCache`. ENV `MCP_CACHE_BACKEND=redis|memory`.
3. **Mittelfristig:** `AlertManager`-Storage abstrahieren (`FileAlertStore`, `PostgresAlertStore`).
4. **Background-Eviction:** asyncio-Task der alle 5 Min `evict_expired` ruft (im Lifespan registriert, siehe SDK-LIFESPAN).
5. **Cache-Cap:** max. N Einträge pro Tool-Typ (LRU), siehe README-Anspruch "80% gesparte Calls" — verifizieren in Live-Telemetry.

## Effort Estimate

**L** (1–2 Wochen für volle Storage-Abstraktion). Doku-Hinweis (Schritt 1): **S**.

## Dependencies / Blockers

Hängt teilweise an SDK-LIFESPAN (Background-Task braucht Lifespan).

## Verification After Fix

- Lasttest mit `wrk`/`vegeta` gegen Render-Deployment mit zwei Replicas → Alert-Konsistenz beobachten.
- Pytest mit `MCP_CACHE_BACKEND=redis` und einem In-Process-Fakeredis.
