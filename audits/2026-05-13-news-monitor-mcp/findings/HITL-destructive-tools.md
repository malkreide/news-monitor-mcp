# Finding: HITL-DESTRUCTIVE — `news_alert_delete` / `news_cache_clear` ohne Confirmation-Pfad

| Feld | Wert |
|---|---|
| **Severity** | **low** |
| **Status** | open |
| **Server** | `news-monitor-mcp` |
| **Check-Reference** | HITL (Human-in-the-Loop Confirmation) |
| **Audit-Datum** | 2026-05-13 |

## Observed Behavior

Zwei Tools mit `destructiveHint: true`:

- `news_alert_delete` (`server.py:1042`) löscht persistent Alert ohne Rückfrage / Soft-Delete.
- `news_cache_clear` (`server.py:1092`) leert Cache ohne Dry-Run-Mode.

Beide werden vom LLM direkt aufgerufen, ohne dass es einen `confirm`-Parameter oder ein zweistufiges Pattern gibt.

## Expected Behavior

Für destruktive Tools empfiehlt MCP-HITL-Best-Practice:

- `confirm: bool = False`-Parameter, der explizit gesetzt sein muss.
- Erstaufruf liefert "Würde X löschen — confirm=true erneut aufrufen".
- Optional Soft-Delete mit `restore`-Tool für Alerts.

Bei rein lokalen, reversiblen Operationen (Cache-Clear) ist das diskutabel; bei `alerts.json`-Delete weniger so, da der Maintainer-Use-Case dauerhafte Konfigurationen umfasst.

## Evidence

- `server.py:1042-1058` `news_alert_delete` — kein confirm-Mechanismus.
- `server.py:1092-1109` `news_cache_clear` — direkter Effekt.

## Risk Description

- **Ungewollte Löschung:** LLM interpretiert "lösche alle Alerts" zu wörtlich; `news_alert_list` zeigt 12 Alerts, LLM löscht in Loop alle.
- **Niedriger als üblich**, weil Alerts ohnehin schnell wieder erstellbar sind und Cache reversibel ist → low.

## Remediation

```diff
  class DeleteAlertInput(BaseModel):
      ...
      alert_id: str = Field(..., min_length=10)
+     confirm: bool = Field(default=False, description="Muss True sein, um zu löschen.")
```

```python
if not params.confirm:
    return f"Bestätige Löschung von Alert {alert.get('name')} (`{params.alert_id}`) — erneut mit confirm=true aufrufen."
```

Analog für `news_cache_clear`, optional weniger streng.

## Effort Estimate

**S** (< 1 Tag).

## Verification After Fix

- Pytest: `delete_without_confirm_returns_prompt`.
- Pytest: `delete_with_confirm_removes_alert`.
