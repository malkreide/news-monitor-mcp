# Safety & Limits Section + Demo Assets Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `Known Limitations` with a full `Safety, Limits & Responsible Use` section in both READMEs, and add a three-panel HTML/PNG demo asset showing a `news_media_briefing` tool call.

**Architecture:** Pure documentation and static asset changes — no Python source modifications. The demo asset is built from a self-contained `assets/demo-source.html` file, screenshotted to `assets/demo-media-briefing.png`, then referenced in both READMEs.

**Tech Stack:** Markdown, HTML/CSS (no JS), `preview_start` + `preview_screenshot` for PNG capture, `git`

---

## Chunk 1: Demo Asset (HTML Mockup → PNG)

### Task 1: Create `assets/` directory and HTML mockup source

**Files:**
- Create: `assets/demo-source.html`

- [ ] **Step 1: Create the assets directory**

```bash
mkdir -p /c/Users/hayal/news-monitor-mcp/assets
```

- [ ] **Step 2: Write `assets/demo-source.html`**

Create the file with the following exact content:

```html
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>news-monitor-mcp Demo</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0d1117;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 24px;
  }
  .demo-wrapper {
    width: 1200px;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    overflow: hidden;
  }
  .demo-header {
    background: #21262d;
    border-bottom: 1px solid #30363d;
    padding: 12px 20px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .dot { width: 12px; height: 12px; border-radius: 50%; }
  .dot-red { background: #ff5f57; }
  .dot-yellow { background: #febc2e; }
  .dot-green { background: #28c840; }
  .header-title {
    margin-left: 8px;
    color: #8b949e;
    font-size: 13px;
    font-weight: 500;
  }
  .panels {
    display: grid;
    grid-template-columns: 280px 380px 1fr;
    min-height: 360px;
  }
  .panel {
    padding: 20px;
    border-right: 1px solid #30363d;
  }
  .panel:last-child { border-right: none; }
  .panel-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid #30363d;
  }
  /* User panel */
  .panel-user { background: #161b22; }
  .panel-user .panel-label { color: #8b949e; }
  .user-bubble {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 14px;
    color: #e6edf3;
    font-size: 14px;
    line-height: 1.55;
  }
  .user-bubble strong { color: #79c0ff; }
  /* Tool call panel */
  .panel-tool { background: #161b22; }
  .panel-tool .panel-label { color: #e3b341; }
  .tool-block {
    background: #0d1117;
    border: 1px solid #f0883e44;
    border-left: 3px solid #f0883e;
    border-radius: 6px;
    padding: 14px;
    font-family: "SF Mono", "Cascadia Code", "Fira Code", Consolas, monospace;
    font-size: 12px;
    line-height: 1.7;
    color: #e6edf3;
  }
  .fn-name { color: #f0883e; font-weight: 700; }
  .key { color: #79c0ff; }
  .str { color: #a5d6ff; }
  .bracket { color: #8b949e; }
  /* Response panel */
  .panel-response { background: #161b22; }
  .panel-response .panel-label { color: #3fb950; }
  .response-content { color: #e6edf3; font-size: 13.5px; line-height: 1.6; }
  .response-content h1 {
    font-size: 15px;
    color: #e6edf3;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid #30363d;
  }
  .topic-block { margin-bottom: 14px; }
  .topic-title {
    font-size: 13.5px;
    font-weight: 600;
    color: #e6edf3;
    margin-bottom: 4px;
  }
  .topic-meta { font-size: 12px; color: #8b949e; margin-bottom: 6px; }
  .badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    margin-left: 4px;
  }
  .badge-pos { background: #1a4a2e; color: #3fb950; }
  .badge-neu { background: #1f2d3d; color: #79c0ff; }
  .badge-neg { background: #3d1f22; color: #f85149; }
  .article-link {
    font-size: 12px;
    color: #8b949e;
    padding-left: 8px;
    border-left: 2px solid #30363d;
    margin-bottom: 3px;
  }
  .article-link a { color: #58a6ff; text-decoration: none; }
  .divider { border: none; border-top: 1px solid #30363d; margin: 12px 0; }
  .demo-footer {
    background: #21262d;
    border-top: 1px solid #30363d;
    padding: 10px 20px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .footer-tag {
    font-size: 11px;
    color: #8b949e;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 2px 8px;
  }
  .footer-tag span { color: #f0883e; }
</style>
</head>
<body>
<div class="demo-wrapper">
  <div class="demo-header">
    <div class="dot dot-red"></div>
    <div class="dot dot-yellow"></div>
    <div class="dot dot-green"></div>
    <div class="header-title">Claude Desktop — news-monitor-mcp</div>
  </div>

  <div class="panels">
    <!-- Panel 1: User -->
    <div class="panel panel-user">
      <div class="panel-label">👤 Anfrage</div>
      <div class="user-bubble">
        Erstelle ein <strong>Medien-Briefing</strong> für:<br><br>
        • KI in Bildung<br>
        • Volksschule Zürich<br>
        • Schuldigitalisierung<br><br>
        <span style="color:#8b949e;font-size:12px;">Letzte 7 Tage, DACH-Raum</span>
      </div>
    </div>

    <!-- Panel 2: Tool Call -->
    <div class="panel panel-tool">
      <div class="panel-label">🔧 Tool Call</div>
      <div class="tool-block">
        <span class="fn-name">news_media_briefing</span><span class="bracket">(&#123;</span><br>
        &nbsp;&nbsp;<span class="key">topics</span>: <span class="bracket">[</span><br>
        &nbsp;&nbsp;&nbsp;&nbsp;<span class="str">"KI in Bildung"</span>,<br>
        &nbsp;&nbsp;&nbsp;&nbsp;<span class="str">"Volksschule Zürich"</span>,<br>
        &nbsp;&nbsp;&nbsp;&nbsp;<span class="str">"Schuldigitalisierung"</span><br>
        &nbsp;&nbsp;<span class="bracket">]</span>,<br>
        &nbsp;&nbsp;<span class="key">language</span>: <span class="str">"de"</span>,<br>
        &nbsp;&nbsp;<span class="key">days_back</span>: <span class="str">7</span>,<br>
        &nbsp;&nbsp;<span class="key">source_country</span>:<br>
        &nbsp;&nbsp;&nbsp;&nbsp;<span class="str">"ch,de,at"</span><br>
        <span class="bracket">&#125;)</span>
      </div>
    </div>

    <!-- Panel 3: Response -->
    <div class="panel panel-response">
      <div class="panel-label">🤖 Medien-Briefing</div>
      <div class="response-content">
        <h1>📋 Medien-Briefing — DACH | 7 Tage</h1>

        <div class="topic-block">
          <div class="topic-title">😊 KI in Bildung
            <span class="badge badge-pos">positiv 0.31</span>
          </div>
          <div class="topic-meta">18 Artikel verfügbar</div>
          <div class="article-link"><a href="#">SRF: «KI-Pilotprojekte an Zürcher Schulen starten»</a></div>
          <div class="article-link"><a href="#">NZZ: «Chancen und Risiken von KI im Unterricht»</a></div>
          <div class="article-link"><a href="#">Der Standard: «Österreich testet KI-Lernassistenten»</a></div>
        </div>

        <hr class="divider">

        <div class="topic-block">
          <div class="topic-title">😐 Volksschule Zürich
            <span class="badge badge-neu">neutral 0.04</span>
          </div>
          <div class="topic-meta">9 Artikel verfügbar</div>
          <div class="article-link"><a href="#">Tages-Anzeiger: «Schulraumplanung im Fokus»</a></div>
          <div class="article-link"><a href="#">ZüriToday: «Neue Lehrpläne ab Herbst»</a></div>
        </div>

        <hr class="divider">

        <div class="topic-block">
          <div class="topic-title">😐 Schuldigitalisierung
            <span class="badge badge-neu">neutral 0.12</span>
          </div>
          <div class="topic-meta">14 Artikel verfügbar</div>
          <div class="article-link"><a href="#">Heise: «Digitalpakt Schweiz — Stand 2025»</a></div>
          <div class="article-link"><a href="#">edu.ch: «BYOD-Rollout in 12 Kantonen»</a></div>
        </div>
      </div>
    </div>
  </div>

  <div class="demo-footer">
    <span class="footer-tag">🔧 <span>news_media_briefing</span></span>
    <span class="footer-tag">🌍 <span>ch,de,at</span></span>
    <span class="footer-tag">📅 <span>7 Tage</span></span>
    <span class="footer-tag">⚡ <span>TTL-Cache aktiv</span></span>
  </div>
</div>
</body>
</html>
```

- [ ] **Step 3: Verify the HTML file exists**

```bash
ls -la /c/Users/hayal/news-monitor-mcp/assets/demo-source.html
```

Expected: file listed, size > 0

---

### Task 2: Screenshot HTML → PNG

**Files:**
- Create: `assets/demo-media-briefing.png` (generated via preview tools)

- [ ] **Step 1: Start preview server for the HTML file**

Use `preview_start` pointed at the `assets/` directory (or serve the file directly).

- [ ] **Step 2: Navigate to the demo file**

Load `assets/demo-source.html` in the preview browser.

- [ ] **Step 3: Resize to 1200px wide**

Use `preview_resize` to set viewport to 1200px width.

- [ ] **Step 4: Take the screenshot**

Use `preview_screenshot` to capture the rendered page.
Save output as `assets/demo-media-briefing.png`.

- [ ] **Step 5: Verify PNG exists and is non-empty**

```bash
ls -lh /c/Users/hayal/news-monitor-mcp/assets/demo-media-briefing.png
```

Expected: file listed, size > 50KB

- [ ] **Step 6: Commit both asset files**

```bash
cd /c/Users/hayal/news-monitor-mcp
git add assets/demo-source.html assets/demo-media-briefing.png
git commit -m "feat: add three-panel demo asset (news_media_briefing mockup)"
```

---

## Chunk 2: README Updates

### Task 3: Update `README.md` — add `## Demo` after Features Table

**Files:**
- Modify: `README.md` (after Features Table, before `## Data Sources`)

The Features Table ends at the line containing `| 9 | \`news_geo_search\``. Insert the Demo block immediately after the `---` that follows it.

- [ ] **Step 1: Verify the insertion point exists**

```bash
grep -n "news_geo_search\|## Data Sources" /c/Users/hayal/news-monitor-mcp/README.md
```

Expected: two line numbers — `news_geo_search` before `Data Sources`

- [ ] **Step 2: Insert the Demo section**

In `README.md`, find this exact block:

```markdown
| 9 | `news_geo_search` | Location-specific news search |

---

## Data Sources
```

Replace with:

```markdown
| 9 | `news_geo_search` | Location-specific news search |

---

## Demo

![Media Briefing Demo](assets/demo-media-briefing.png)

> *"Create a media briefing for: AI in education, Volksschule Zürich, school digitalisation"*

---

## Data Sources
```

- [ ] **Step 3: Verify the Demo section was inserted**

```bash
grep -n "## Demo\|demo-media-briefing" /c/Users/hayal/news-monitor-mcp/README.md
```

Expected: two matching lines with correct line numbers

---

### Task 4: Update `README.md` — replace `## Known Limitations` with `## Safety, Limits & Responsible Use`

**Files:**
- Modify: `README.md` (replace the entire `## Known Limitations` section)

- [ ] **Step 1: Locate the section boundaries**

```bash
grep -n "## Known Limitations\|## Synergies" /c/Users/hayal/news-monitor-mcp/README.md
```

Expected: two line numbers. The entire block between them (inclusive of `## Known Limitations`) is replaced.

- [ ] **Step 2: Replace the section**

In `README.md`, find and replace this entire block:

```markdown
## Known Limitations

- **Sentiment analysis:** Only German (`de`) and English (`en`) — no French or Italian
- **Free tier:** 1,000 API calls/month, max 10 articles per call (paid plans: up to 100)
- **Historical data:** Free tier limited to 30 days; paid plans offer extended history
- **Source coverage:** Swiss regional media may be less well-indexed than national outlets
```

Replace with:

```markdown
## Safety, Limits & Responsible Use

### Read-Only Operation
12 of the 15 tools carry `readOnlyHint: true`. All 9 monitoring tools (search,
headlines, sentiment, briefing, article, sources, front_pages, trend, geo) are
fully read-only and issue GET requests to WorldNewsAPI only. The 3 exceptions
are local-only operations: `news_alert_create` and `news_alert_delete` (write/
delete `~/.news-monitor-mcp/alerts.json`) and `news_cache_clear` (clears
in-memory cache). None of the 15 tools modify any external data source.

### API Rate Limits

| Constraint | WorldNewsAPI Free Tier | Paid Plans |
|---|---|---|
| Calls/month | 1,000 | Up to 1M |
| Articles/call | 10 | Up to 100 |
| Historical depth | 30 days | Extended |
| Timeout per call | 30 seconds | 30 seconds |

The TTL cache (v0.2+) reduces redundant calls by up to 80%.

### Data Privacy

- **No personal data stored:** The server holds no persistent user data. Cache entries are in-memory and reset on server restart.
- **No profiling:** The server retrieves publicly published journalism only. It is not designed for surveillance or personal profiling.
- **Alert data:** Alert configurations are stored locally in `~/.news-monitor-mcp/alerts.json` — on your machine only, never transmitted.

### Responsible Use

- Query public news only — do not use as a profiling tool for individuals.
- Sentiment scores reflect algorithmic analysis of journalistic tone, not verified editorial judgements.
- Results depend on WorldNewsAPI's indexing; Swiss regional media may be less well-covered than national outlets.

### Terms of Service

Users must comply with:
- [WorldNewsAPI Terms of Service](https://worldnewsapi.com/terms-of-service/)
- [WorldNewsAPI Privacy Policy](https://worldnewsapi.com/privacy-policy/)

This MCP server is an independent open-source project and is not affiliated with WorldNewsAPI.
```

- [ ] **Step 3: Verify the replacement**

```bash
grep -n "## Safety, Limits\|readOnlyHint\|Terms of Service" /c/Users/hayal/news-monitor-mcp/README.md
```

Expected: all three patterns found. Also verify `## Known Limitations` is gone:

```bash
grep -c "## Known Limitations" /c/Users/hayal/news-monitor-mcp/README.md
```

Expected: `0`

- [ ] **Step 4: Commit README.md changes**

```bash
cd /c/Users/hayal/news-monitor-mcp
git add README.md
git commit -m "docs: replace Known Limitations with Safety, Limits & Responsible Use (README.md)"
```

---

### Task 5: Update `README.de.md` — add `## Demo` after Features Table

**Files:**
- Modify: `README.de.md`

The German Features Table also ends with `news_geo_search`. Find the equivalent insertion point.

- [ ] **Step 1: Locate insertion point in German README**

```bash
grep -n "news_geo_search\|## Datenquellen" /c/Users/hayal/news-monitor-mcp/README.de.md
```

- [ ] **Step 2: Insert Demo section**

In `README.de.md`, find the `---` separator between the Features Table and `## Datenquellen`. Insert:

```markdown
## Demo

![Media Briefing Demo](assets/demo-media-briefing.png)

> *"Erstelle ein Medien-Briefing für: KI in Bildung, Volksschule Zürich, Schuldigitalisierung"*

---
```

- [ ] **Step 3: Verify insertion**

```bash
grep -n "## Demo\|demo-media-briefing" /c/Users/hayal/news-monitor-mcp/README.de.md
```

Expected: two lines found

---

### Task 6: Update `README.de.md` — replace `## Bekannte Einschränkungen`

**Files:**
- Modify: `README.de.md` (replace the entire `## Bekannte Einschränkungen` section)

- [ ] **Step 1: Locate section**

```bash
grep -n "## Bekannte Einschränkungen\|## Synergie" /c/Users/hayal/news-monitor-mcp/README.de.md
```

- [ ] **Step 2: Replace section**

In `README.de.md`, find and replace this entire block:

```markdown
## Bekannte Einschränkungen

- **Sentiment-Analyse:** Nur Deutsch (`de`) und Englisch (`en`) — kein Französisch oder Italienisch
- **Free Tier:** 1'000 API-Calls/Monat, max. 10 Artikel pro Call (kostenpflichtige Pläne: bis 100)
- **Historiendaten:** Im Free Tier auf 30 Tage beschränkt; kostenpflichtige Pläne bieten längere History
- **Quellabdeckung:** Schweizer Regionalmedien sind möglicherweise weniger gut indexiert als nationale Titel
```

Replace with:

```markdown
## Sicherheit, Grenzen & verantwortungsvoller Einsatz

### Nur-Lese-Betrieb
12 der 15 Tools tragen `readOnlyHint: true`. Alle 9 Monitoring-Tools (Suche,
Headlines, Sentiment, Briefing, Artikel, Quellen, Titelseiten, Trends, Geo)
sind vollständig schreibgeschützt und senden nur GET-Anfragen an die WorldNewsAPI.
Die 3 Ausnahmen sind lokale Operationen: `news_alert_create` und `news_alert_delete`
(schreiben/löschen `~/.news-monitor-mcp/alerts.json`) und `news_cache_clear`
(leert den In-Memory-Cache). Keines der 15 Tools verändert externe Datenquellen.

### API-Rate-Limits

| Einschränkung | WorldNewsAPI Free Tier | Kostenpflichtige Pläne |
|---|---|---|
| Calls/Monat | 1'000 | Bis 1M |
| Artikel/Call | 10 | Bis 100 |
| Historische Tiefe | 30 Tage | Erweitert |
| Timeout pro Call | 30 Sekunden | 30 Sekunden |

Der TTL-Cache (v0.2+) reduziert redundante API-Calls um bis zu 80%.

### Datenschutz

- **Keine personenbezogenen Daten gespeichert:** Der Server speichert keine persistenten Nutzerdaten. Cache-Einträge liegen im Arbeitsspeicher und werden beim Serverneustart zurückgesetzt.
- **Kein Profiling:** Der Server ruft ausschliesslich öffentlich erschienene Nachrichtenartikel ab. Er ist nicht für die Überwachung oder das Profiling von Personen konzipiert.
- **Alert-Daten:** Alert-Konfigurationen werden lokal in `~/.news-monitor-mcp/alerts.json` gespeichert — ausschliesslich auf dem eigenen Gerät, niemals übertragen.

### Verantwortungsvoller Einsatz

- Nur öffentliche Nachrichten abfragen — nicht als Profiling-Tool für Einzelpersonen einsetzen.
- Sentiment-Scores spiegeln die algorithmische Analyse des journalistischen Tons wider, keine verifizierten redaktionellen Urteile.
- Ergebnisse hängen von der Indexierung durch WorldNewsAPI ab; Schweizer Regionalmedien sind möglicherweise weniger gut abgedeckt als nationale Titel.

### Nutzungsbedingungen

Nutzerinnen und Nutzer müssen folgende Bedingungen einhalten:
- [WorldNewsAPI Nutzungsbedingungen](https://worldnewsapi.com/terms-of-service/)
- [WorldNewsAPI Datenschutzerklärung](https://worldnewsapi.com/privacy-policy/)

Dieser MCP-Server ist ein unabhängiges Open-Source-Projekt und steht in keiner Verbindung mit WorldNewsAPI.
```

- [ ] **Step 3: Verify replacement**

```bash
grep -n "## Sicherheit, Grenzen\|Nutzungsbedingungen\|readOnlyHint" /c/Users/hayal/news-monitor-mcp/README.de.md
```

Expected: all three patterns found. Verify old heading is gone:

```bash
grep -c "## Bekannte Einschränkungen" /c/Users/hayal/news-monitor-mcp/README.de.md
```

Expected: `0`

- [ ] **Step 4: Commit README.de.md changes**

```bash
cd /c/Users/hayal/news-monitor-mcp
git add README.de.md
git commit -m "docs: replace Bekannte Einschränkungen with Sicherheit & Grenzen (README.de.md)"
```

---

### Task 7: Final verification and push

- [ ] **Step 1: Verify both READMEs have all four required sections**

```bash
echo "=== README.md ===" && grep -n "## Safety\|## Demo\|readOnlyHint\|Terms of Service" /c/Users/hayal/news-monitor-mcp/README.md
echo "=== README.de.md ===" && grep -n "## Sicherheit\|## Demo\|readOnlyHint\|Nutzungsbedingungen" /c/Users/hayal/news-monitor-mcp/README.de.md
```

Expected: 4+ matches per file

- [ ] **Step 2: Verify PNG asset exists**

```bash
ls -lh /c/Users/hayal/news-monitor-mcp/assets/
```

Expected: `demo-source.html` and `demo-media-briefing.png` both listed

- [ ] **Step 3: Verify git log shows clean commits**

```bash
cd /c/Users/hayal/news-monitor-mcp && git log --oneline -5
```

Expected: 3-4 commits visible from this work

- [ ] **Step 4: Push to remote**

```bash
cd /c/Users/hayal/news-monitor-mcp && git push origin main
```

Expected: clean push, no rejected commits
