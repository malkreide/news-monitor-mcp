# Contributing to news-monitor-mcp

Thank you for your interest in contributing! This server follows the conventions of the Swiss Public Data MCP Portfolio.

## Data Source Policy

This server exclusively uses **open, publicly accessible APIs**:
- **WorldNewsAPI** (worldnewsapi.com) — commercial API with free tier; no proprietary or confidential data

No scraped, paywalled, or restricted content is processed. All data is fetched from the official API only.

## Commit Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new tool for newspaper front pages
fix: correct sentiment score calculation
docs: update README with portfolio integration examples
test: add mock tests for geo search tool
refactor: extract common API error handler
chore: bump fastmcp to 2.1.0
```

## Development Setup

```bash
git clone https://github.com/malkreide/news-monitor-mcp
cd news-monitor-mcp
pip install -e ".[dev]"
```

## Testing

```bash
# Unit tests (no API key required)
PYTHONPATH=src pytest -m "not live" -v

# Live tests (requires WORLD_NEWS_API_KEY)
WORLD_NEWS_API_KEY=your-key pytest -m live -v

# Lint
ruff check src/
ruff format src/
```

## Code Style

- **Formatter/Linter:** Ruff
- **Type hints:** Required for all function signatures
- **Pydantic v2:** All input models use `BaseModel` with `Field()` descriptions
- **Error messages:** In German, action-oriented (users of this server are primarily German-speaking)
- **Docstrings:** English (for international visibility)

## Adding New Tools

1. Define a Pydantic input model with `ConfigDict(extra='forbid')`
2. Add field descriptions in German (for AI agent discoverability in Swiss context)
3. Decorate with `@mcp.tool(name=..., annotations={...})`
4. Write a comprehensive docstring with Args/Returns
5. Add unit tests with `unittest.mock` (no live API calls in CI)
6. Add a `@pytest.mark.live` test for manual verification

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-new-tool`
3. Run tests: `pytest -m "not live"`
4. Commit with Conventional Commits
5. Open a Pull Request with description of changes
