# Repository Guidelines

## Project Structure & Module Organization
This repository uses a `src` layout. Core package code lives in `src/mendeley_mcp/`:
- `server.py` defines the FastMCP server, tools, and resources.
- `client.py` contains the async Mendeley API client plus `Document`, `Folder`, and credential models.
- `auth.py` handles the OAuth CLI, local callback flow, and credential storage.

Tests live in `tests/` and currently focus on client-side models and formatting behavior. CI workflows are in `.github/workflows/`. Keep end-user documentation in `README.md`, and place feature-specific design notes in standalone Markdown files at the repo root only when they support active work.

## Build, Test, and Development Commands
- `python -m venv .venv` then `.venv\Scripts\Activate.ps1`: create and activate a local environment on Windows.
- `pip install -e ".[dev]"`: install the package in editable mode with test, lint, and type-check tools.
- `pytest`: run the test suite.
- `pytest --cov=mendeley_mcp`: run tests with coverage reporting.
- `ruff check src tests`: lint imports, naming, and Python style.
- `mypy src/mendeley_mcp`: run strict static type checking.
- `python -m build`: build source and wheel artifacts.
- `npx @modelcontextprotocol/inspector mendeley-mcp`: inspect the MCP server locally.

## Coding Style & Naming Conventions
Target Python 3.10+, use 4-space indentation, and keep lines within Ruff’s 100-character limit. Follow the existing pattern of `snake_case` for functions, variables, and module names, and `PascalCase` for dataclasses and other types. Preserve explicit type hints: `mypy` runs in strict mode. Prefer small async methods in `client.py` for API calls and keep MCP-facing formatting logic in `server.py`.

## Testing Guidelines
Use `pytest` with files named `test_*.py` under `tests/`. Add focused unit tests alongside any new parsing, citation-formatting, auth, or API wrapper behavior. There is no documented coverage gate, but new changes should include tests for normal and edge cases, especially around token refresh and response shaping.

## Commit & Pull Request Guidelines
Recent history uses short, imperative subjects such as `Add Docker support`, `Fix logo URL for PyPI`, and `Bump version to 0.1.3`. Keep commits scoped and descriptive. Pull requests should summarize the user-visible change, list validation performed (`pytest`, `ruff`, `mypy`, build), and note any credential, OAuth, or MCP tool contract changes. Include screenshots only when documentation or UI-facing assets change.

## Security & Configuration Tips
Never commit real `MENDELEY_CLIENT_ID`, `MENDELEY_CLIENT_SECRET`, access tokens, or refresh tokens. Prefer `mendeley-auth login` and system keyring storage over file-based secrets. When changing auth flows, verify both environment-variable and saved-credential paths.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read `specs/001-create-folder/plan.md`
<!-- SPECKIT END -->
