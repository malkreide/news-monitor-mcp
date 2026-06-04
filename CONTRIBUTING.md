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

Live tests are marked with `@pytest.mark.live` and excluded from the CI pipeline.

---

## License

MIT — see [LICENSE](LICENSE)
