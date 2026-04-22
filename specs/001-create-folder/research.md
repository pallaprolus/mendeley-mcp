# Research: Folder Management

## Current Public Contract Snapshot

The feature extends an existing MCP surface that already exposes these related contracts:

- `mendeley_list_folders()` returns a JSON array of folder summaries with `id`, `name`, and `parent_id`.
- `mendeley_list_documents(folder_id?, limit, sort_by)` returns a JSON array of simplified document objects produced by `format_document(...)`.
- `mendeley_get_document(document_id)` returns a JSON object with full document metadata.
- `mendeley_add_document(...)` returns a JSON object describing the created document using the existing simplified document format.

The expanded folder-management slice standardizes four write-side contracts:

- `mendeley_create_folder(...)` returns `{id, name, parent_id, created}`.
- `mendeley_rename_folder(...)` returns `{id, name, parent_id, created}`.
- `mendeley_delete_folder(...)` returns `{id, status}`.
- `mendeley_add_document_to_folder(...)` returns `{folder_id, document_id, status}`.

## Decisions

### Decision: Keep dedicated client write helpers and a thin MCP server layer

- **Decision**: Keep `MendeleyClient` responsible for authenticated folder mutations and leave `server.py` responsible for local blank-input validation, orchestration, and MCP-facing response shaping.
- **Rationale**: The repository already centralizes authenticated API calls and token refresh in `MendeleyClient._request(...)`, while `server.py` formats JSON-string tool responses. Extending that split across create, rename, delete, and assignment keeps the new scope consistent with the current package layout.
- **Alternatives considered**:
  - Build raw HTTP requests directly in `server.py`: rejected because it would duplicate auth and error-handling logic.
  - Introduce a generic mutation abstraction for all future writes: rejected because this slice still benefits from focused methods with explicit return shapes.

### Decision: Use request-body fields for folder creation context

- **Decision**: Send `parent_id` and `group_id` in the folder creation request body.
- **Rationale**: The Mendeley quick-start guides show both nested-folder creation and group-folder creation as `POST /folders` requests with `parent_id` or `group_id` in the JSON body, which matches the current feature spec and keeps request construction uniform.
- **Alternatives considered**:
  - Use a query parameter for `group_id`: rejected because the official docs are inconsistent here. The API overview mentions `group_id` in the query string for group folder creation, but the quick-start guide gives a concrete request-body example for the same action. The plan follows the explicit creation examples and the approved spec.

### Decision: Preserve the stable rename payload with a pre-rename folder read

- **Decision**: Read the current folder metadata before issuing `PATCH /folders/{id}` so the MCP tool can return the stable `{id, name, parent_id, created}` payload after a successful rename.
- **Rationale**: The Mendeley reference documents folder updates as a `PATCH` that returns `204 No Content`, while the approved contract requires the stable folder payload on rename. A pre-read preserves `parent_id` and `created` without inventing a partial or inconsistent success response.
- **Alternatives considered**:
  - Return only `{id, name}` on rename: rejected because the contract was explicitly fixed to the stable folder payload.
  - Perform an after-the-fact list scan to rebuild the folder payload: rejected because it adds unnecessary work and ambiguity when the current folder snapshot is already sufficient.

### Decision: Return deterministic delete confirmation and rely on upstream delete semantics

- **Decision**: Issue `DELETE /folders/{id}` and, on success, return the deterministic local confirmation `{id, status: "deleted"}` without adding a local preflight guard for folders that contain documents or descendants.
- **Rationale**: The Mendeley reference documents folder deletion as a `204 No Content` success path, and the core-resources overview states that deleting a folder cascades to descendant folders while documents remain available through the library or group. The approved scope explicitly keeps non-empty-folder behavior aligned with those upstream semantics instead of duplicating them locally.
- **Alternatives considered**:
  - Reject non-empty folders locally before delete: rejected because it would diverge from the approved behavior and duplicate upstream rules.
  - Perform a read-after-delete to confirm removal: rejected because the contract only requires deterministic confirmation, not a second verification call.

### Decision: Enforce duplicate assignment as an explicit error before write

- **Decision**: Add a lightweight folder-membership lookup helper and reject duplicate document-to-folder assignment before issuing `POST /folders/{id}/documents`.
- **Rationale**: The approved clarification requires a clear duplicate-assignment error. The Mendeley reference documents `GET /folders/{id}/documents` as a paginated list of document IDs and documents `POST /folders/{id}/documents` only as a `201 Created` path; it does not define duplicate semantics. A preflight membership check is the only reliable way to guarantee the requested behavior.
- **Alternatives considered**:
  - Rely entirely on the upstream `POST` response: rejected because the duplicate case is undocumented and may not yield a stable, user-facing duplicate message.
  - Treat duplicate assignment as idempotent success: rejected by clarification.

### Decision: Keep local validation narrow across all folder-management writes

- **Decision**: Limit local validation to blank or whitespace-only required inputs plus duplicate folder membership; let the upstream API enforce ownership, access, uniqueness within container, hierarchy constraints, and deletion semantics.
- **Rationale**: The clarified spec explicitly prefers local validation only for obvious blanks, and the delete flow was explicitly approved without a separate non-empty-folder guard. Mendeley documents additional folder constraints, but duplicating them locally would widen scope and create drift risk.
- **Alternatives considered**:
  - Add local checks for name length, container uniqueness, descendant-delete safety, and hierarchy rules: rejected because those rules depend on upstream context and are not part of the approved slice.

### Decision: Test at the client and tool-function layers

- **Decision**: Keep client unit tests by mocking `_request(...)` and server tests by invoking tool coroutines with a patched `get_client()`, and extend both layers for rename/delete alongside create/assignment.
- **Rationale**: The current suite is `pytest`-based and already tests dataclass/model behavior directly. Function-level async tests cover the expanded public contract without introducing heavier MCP transport harnesses into this slice.
- **Alternatives considered**:
  - End-to-end MCP transport tests: rejected because they are heavier than needed for these thin tool wrappers.
  - Client-only coverage with no server tests: rejected because the public contract lives in `server.py`.

## External Sources

- Mendeley API Reference: https://dev.mendeley.com/methods/
- Mendeley Core Resources Overview: https://dev.mendeley.com/overview/core_resources.html
- Mendeley Core APIs Quick Start Guides: https://dev.mendeley.com/code/core_quick_start_guides.html
