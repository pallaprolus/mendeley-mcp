# Quickstart: Folder Management

## 1. Prepare the environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## 2. Implement the client layer

Update `src/mendeley_mcp/client.py` to add or maintain:

- `create_folder(...)`
- `rename_folder(...)`
- `delete_folder(...)`
- a folder-membership helper that can detect duplicate document membership before assignment
- `add_document_to_folder(...)`

Keep all outbound calls routed through the existing `_request(...)` helper so token refresh and headers remain centralized. Preserve the stable rename payload by reading the folder metadata before the upstream `PATCH`, and return the deterministic delete confirmation locally after the upstream `DELETE` succeeds.

## 3. Implement the MCP server layer

Update `src/mendeley_mcp/server.py` to add or maintain:

- `mendeley_create_folder(...)`
- `mendeley_rename_folder(...)`
- `mendeley_delete_folder(...)`
- `mendeley_add_document_to_folder(...)`

The folder-management tools should:

- reject blank inputs locally
- keep the current JSON-string success/error convention
- return the stable success payloads defined in `contracts/folder-management.md`
- surface duplicate assignment as a clear error
- defer non-empty-folder delete behavior to the upstream API instead of adding a local guard

## 4. Add automated coverage

Update `tests/test_client.py` and `tests/test_server.py` to cover:

- folder creation success
- nested folder creation success
- folder rename success with the stable payload
- folder delete success with `{id, status: "deleted"}`
- document-to-folder success
- blank-input validation failures for create, rename, delete, and assignment
- duplicate-assignment failure
- upstream error propagation for create, rename, delete, and assignment

## 5. Update user-facing documentation

Update `README.md` to add:

- the four folder-management tools to the tool table
- example prompts for folder creation, folder rename, folder delete, and document assignment
- a short validation section that explains blank-input rejection, duplicate-assignment handling, and upstream delete semantics

## 6. Run validation

```powershell
pytest
ruff check src tests
mypy src\mendeley_mcp
```

## 7. Optional manual smoke test

Authenticate if needed:

```powershell
mendeley-auth login
```

Run the MCP inspector:

```powershell
npx @modelcontextprotocol/inspector mendeley-mcp
```

Then exercise:

- `mendeley_create_folder` with a root folder name
- `mendeley_create_folder` with `parent_id`
- `mendeley_rename_folder` with a disposable folder ID and a new valid name
- `mendeley_add_document_to_folder` with valid IDs
- `mendeley_add_document_to_folder` again with the same pair to confirm duplicate rejection
- `mendeley_delete_folder` with a disposable folder ID to confirm deterministic delete confirmation

If you want to observe upstream delete semantics for non-empty folders, do it only with disposable test data such as a temporary parent/child pair or a folder containing a copied document.
