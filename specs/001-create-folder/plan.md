# Implementation Plan: Folder Management

**Branch**: `001-create-folder` | **Date**: 2026-04-22 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-create-folder/spec.md`

## Summary

Expand the folder-management write surface to four MCP tools by carrying the existing create and document-assignment flow forward and adding folder rename plus folder delete. The implementation keeps `server.py` as a thin validation-and-formatting layer, preserves the repository's JSON-string tool contract, uses a pre-rename folder read to keep the stable folder payload after the upstream `PATCH` returns `204 No Content`, returns a deterministic delete confirmation after the upstream `DELETE` returns `204 No Content`, and keeps duplicate folder-assignment rejection explicit.

### Public Contract Snapshot

| Surface | Current Return Shape |
|------|----------------------|
| `mendeley_list_folders` | JSON array of `{id, name, parent_id}` objects |
| `mendeley_list_documents` | JSON array of simplified document objects from `format_document(...)` |
| `mendeley_get_document` | JSON object with full document metadata |
| `mendeley_add_document` | JSON object describing the created document |
| `mendeley_create_folder` | JSON object with `id`, `name`, `parent_id`, and `created` |
| `mendeley_rename_folder` | JSON object with `id`, `name`, `parent_id`, and `created` |
| `mendeley_delete_folder` | JSON object with `id` and `status` |
| `mendeley_add_document_to_folder` | JSON object with `folder_id`, `document_id`, and `status` |

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: `mcp`/FastMCP, `httpx`, `click`, `keyring`, standard-library `dataclasses` and `json`  
**Storage**: Remote Mendeley REST API plus local keyring/credential file; no repository-local database  
**Testing**: `pytest`, `pytest-asyncio`, `ruff`, `mypy`  
**Target Platform**: Local stdio MCP server package on Windows/macOS/Linux with outbound HTTPS access to `api.mendeley.com`  
**Project Type**: Python MCP server and companion CLI package  
**Performance Goals**: One upstream write call for successful folder creation, one pre-read plus one write for successful folder rename, one upstream delete call for successful folder deletion, no read-after-write on successful assignment, and duplicate detection that exits as soon as membership is confirmed  
**Constraints**: Preserve existing JSON-string tool outputs, keep strict typing and Ruff limits, avoid breaking existing tool names/return shapes, keep local validation narrow, do not add an extra local guard for non-empty folder deletion, and do not change auth storage flows or secret handling  
**Scale/Scope**: Four write-side MCP tools, four client write methods, one stable-payload pre-read path for rename, one folder-membership helper, one server test module, expanded client/server coverage, and README updates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- `.specify/memory/constitution.md` is still an uninitialized template and does not define enforceable project-specific principles yet.
- Repository-level constraints still apply from `AGENTS.md`, `pyproject.toml`, and the existing repo guidelines: Python 3.10+, strict mypy typing, Ruff line-length 100, pytest-based coverage for normal and edge cases, and no committed secrets.
- **Gate status before Phase 0 research**: PASS
- **Gate status after Phase 1 design**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/001-create-folder/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── folder-management.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
└── mendeley_mcp/
    ├── __init__.py
    ├── auth.py
    ├── client.py
    └── server.py

tests/
├── __init__.py
├── conftest.py
├── test_client.py
└── test_server.py

README.md
pyproject.toml
AGENTS.md
```

**Structure Decision**: Keep the existing single-package Python layout. Implement upstream HTTP behavior in `src/mendeley_mcp/client.py`, keep MCP-facing validation and JSON response shaping in `src/mendeley_mcp/server.py`, cover create/rename/delete/assignment flows in `tests/test_client.py` and `tests/test_server.py`, and document the public surface in `README.md` plus `specs/001-create-folder/contracts/folder-management.md`.

## Complexity Tracking

No constitution violations or complexity exceptions require justification for this slice.
