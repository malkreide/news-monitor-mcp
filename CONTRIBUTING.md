# Contributing to news-monitor-mcp

Thank you for your interest in contributing to this project! This MCP server is part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide) and follows shared conventions across the portfolio.

[🇩🇪 Deutsche Version](CONTRIBUTING.de.md)

---

## How can I contribute?

**Report bugs:** Create an [Issue](../../issues) with a clear description, reproduction steps, and expected vs. actual output.

**Suggest features:** Describe the use case, ideally with a reference to the context of Swiss institutions (Schulamt, city administration, AI working group, GL briefings, etc.).

**Contribute code:**
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Write tests for your changes
5. Run linter: `ruff check src/ tests/`
6. Commit with clear message: `git commit -m "feat: add geo-search by municipality"`
7. Create a Pull Request

## Code Standards

- Python 3.11+, Ruff for linting
- Docstrings in English (for international compatibility)
- Comments and error messages may be in German or English
- All MCP tools must set `readOnlyHint: True` (read-only access)
- Pydantic models for all tool inputs

## Data Source Policy

This server uses **WorldNewsAPI** as its sole data source. Extensions with additional news APIs are welcome, provided they:

- Offer a free tier or free basic access
- Are publicly documented and reliably available
- Cover Swiss or German-language sources well
- Support the portfolio's No-Auth-First principle (API key optional, not mandatory)

## Tests

The test suite distinguishes between unit tests (mocked, no network) and live tests (real API calls):

```bash
# Unit tests (always runnable, no internet required)
PYTHONPATH=src pytest tests/ -m "not live"

# Live tests (internet and valid WORLD_NEWS_API_KEY required)
WORLD_NEWS_API_KEY=your-key PYTHONPATH=src pytest tests/ -m "live"
```

Live tests are marked with `@pytest.mark.live` and excluded from the push/PR CI
pipeline. They run on a schedule instead — daily at 06:17 UTC via
[`.github/workflows/live-tests.yml`](.github/workflows/live-tests.yml), which
can also be started by hand with `workflow_dispatch`.

---

## The live suite: when it runs, and who sees a red result

**Cadence:** daily 06:17 UTC, plus on demand via *Actions → Live-Tests (geplant) → Run
workflow*. See [`.github/workflows/live-tests.yml`](.github/workflows/live-tests.yml).

**Who sees it:** a red run opens an issue titled `Live-Tests rot: die Quelle antwortet nicht mehr
wie erwartet` with the `live-tests` label, and comments on the existing one
instead of opening a second. Only scheduled runs report; a manual run does not.

**Three answers, not two.** `scripts/check_live_run.py` reads the JUnit XML rather than
the exit code and separates `clear` (ran, green), `finding` (ran, something
fell) and `unknown` (did not run — install failed, nothing collected,
everything skipped). An `unknown` never closes an issue: closing would claim a
comparison that never happened.

**A red live run does not necessarily mean *our* bug.** It means the contract
with the source has changed, or the source is down. Both belong seen; only the
first belongs fixed. Please read the run before disabling the job — that is how
this check dies, and it is the only one in the repository that can contradict a
wrong assumption about die überwachten Quellen. Every other test asserts against a fixture, and
the fixture was written from the same assumption as the code.

## License

MIT — see [LICENSE](LICENSE)
