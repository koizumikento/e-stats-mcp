# AGENTS.md

Guidance for Codex and other coding agents working in this repository.

## Project

This repository implements an MCP server for the e-Stat API using Python,
FastMCP, httpx, and Typer. Keep tool return values JSON-serializable unless a
tool explicitly returns CSV text.

## Commands

Run these before handing off changes:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy e_stats_mcp
```

Use `uv run ruff format ...` for formatting touched Python files.

## API Notes

- Live e-Stat API calls require `E_STAT_APP_ID`; do not commit real app IDs.
- Prefer the official e-Stat API 3.0 manual and sample forms when checking
  endpoint names, parameter casing, and response shapes.
- e-Stat parameter names are case-sensitive in practice. Preserve camelCase
  names such as `dataSetId`, `startPosition`, and `statsDataId`.
- `refDataset` does not expose API-side `limit` / `startPosition` for dataset
  list paging. `get_dataset` applies list paging inside the MCP server.
- `getDataCatalog` has no CSV endpoint in e-Stat API 3.0. `get_data_catalog_csv`
  fetches JSON and converts `DATA_CATALOG_INF` records to CSV locally.

## Testing

Unit tests should mock HTTP with `DummyClient` and set `E_STAT_APP_ID` via
`monkeypatch`. Avoid tests that require a real e-Stat application ID unless they
are explicitly marked or documented as integration tests.
