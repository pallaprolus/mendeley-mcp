# Tasks: Folder Management

**Input**: Design documents from `/specs/001-create-folder/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are required for this feature because `spec.md` explicitly defines client and server testing requirements for create, rename, delete, and assignment flows.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`, `US4`, `US5`)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare shared fixtures and the server test harness for the folder-management surface.

- [X] T001 [P] Extend shared folder creation and folder assignment fixtures in `tests/conftest.py`
- [X] T002 [P] Create the patched async MCP tool test scaffold in `tests/test_server.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared helpers used by multiple folder-management stories.

**⚠️ CRITICAL**: No user story work should start until this phase is complete.

- [X] T003 [P] Add shared folder-management request helpers and media-type constants in `src/mendeley_mcp/client.py`
- [X] T004 [P] Add shared trimmed-input and JSON error-response helpers in `src/mendeley_mcp/server.py`

**Checkpoint**: Shared client/server helpers are ready for story-specific implementation.

---

## Phase 3: User Story 1 - Create a new folder (Priority: P1) 🎯 MVP

**Goal**: Let users create root, nested, and group-scoped folders with a stable success payload.

**Independent Test**: Call `mendeley_create_folder` with a valid `name`, plus optional `parent_id` or `group_id`, and confirm the response contains `id`, `name`, `parent_id`, and `created`.

### Tests for User Story 1

- [X] T005 [P] [US1] Add `create_folder` success tests for root, nested, and group folder creation in `tests/test_client.py`
- [X] T006 [P] [US1] Add `mendeley_create_folder` success-payload tests in `tests/test_server.py`

### Implementation for User Story 1

- [X] T007 [US1] Implement `create_folder(...)` and folder response parsing in `src/mendeley_mcp/client.py`
- [X] T008 [US1] Implement the `mendeley_create_folder` MCP tool success path in `src/mendeley_mcp/server.py`
- [X] T009 [US1] Add `mendeley_create_folder` to the tool table and examples in `README.md`

**Checkpoint**: User Story 1 should create folders successfully and return the stable folder payload.

---

## Phase 4: User Story 2 - Place an existing document into a folder (Priority: P2)

**Goal**: Let users attach an existing document to an existing folder and receive a deterministic confirmation payload.

**Independent Test**: Call `mendeley_add_document_to_folder` with valid `folder_id` and `document_id` and confirm the response is `{"folder_id": ..., "document_id": ..., "status": "added"}`.

### Tests for User Story 2

- [X] T010 [P] [US2] Add `add_document_to_folder` success tests in `tests/test_client.py`
- [X] T011 [P] [US2] Add `mendeley_add_document_to_folder` success-payload tests in `tests/test_server.py`

### Implementation for User Story 2

- [X] T012 [US2] Implement `add_document_to_folder(...)` for `POST /folders/{id}/documents` in `src/mendeley_mcp/client.py`
- [X] T013 [US2] Implement the `mendeley_add_document_to_folder` MCP tool success path in `src/mendeley_mcp/server.py`
- [X] T014 [US2] Add `mendeley_add_document_to_folder` usage examples in `README.md`

**Checkpoint**: User Story 2 should attach documents to folders successfully and return the deterministic assignment payload.

---

## Phase 5: User Story 3 - Receive clear validation and failure feedback (Priority: P3)

**Goal**: Reject blank inputs locally, reject duplicate folder assignment explicitly, and surface upstream failures as clear MCP errors across the folder-management tools.

**Independent Test**: Submit blank folder names, blank IDs, a duplicate folder assignment, and representative upstream failures, then confirm each returns a clear error JSON response instead of a false success.

### Tests for User Story 3

- [X] T015 [P] [US3] Add client tests for create/rename/delete failure propagation and duplicate folder-membership detection in `tests/test_client.py`
- [X] T016 [P] [US3] Add server tests for blank names, blank IDs, duplicate assignment, and upstream error propagation across folder-management tools in `tests/test_server.py`

### Implementation for User Story 3

- [X] T017 [US3] Implement folder-membership lookup and duplicate-assignment rejection in `src/mendeley_mcp/client.py`
- [X] T018 [US3] Implement blank-input validation and explicit error shaping for create, rename, delete, and assignment tools in `src/mendeley_mcp/server.py`
- [X] T019 [US3] Document validation failures, duplicate-assignment behavior, and upstream delete semantics in `README.md`

**Checkpoint**: User Story 3 should provide clear local validation and stable failure behavior for the folder-management surface.

---

## Phase 6: Polish & Cross-Cutting Concerns (Initial Slice)

**Purpose**: Validate the initial folder-management slice end-to-end before the rename/delete expansion tasks land.

- [X] T020 Run targeted `pytest` for `tests/test_client.py` and `tests/test_server.py`
- [X] T021 Run full validation for `src/mendeley_mcp/` and `tests/` with `pytest`, `ruff check src tests`, and `mypy src/mendeley_mcp`
- [X] T022 Validate the smoke-test steps in `specs/001-create-folder/quickstart.md` against `README.md`

---

## Phase 7: User Story 4 - Rename an existing folder (Priority: P4)

**Goal**: Let users rename an existing folder and receive the same stable folder payload shape used for folder creation.

**Independent Test**: Call `mendeley_rename_folder` with valid `folder_id` and `name` and confirm the response contains `id`, `name`, `parent_id`, and `created`.

### Tests for User Story 4

- [X] T023 [P] [US4] Add `rename_folder` success tests in `tests/test_client.py`
- [X] T024 [P] [US4] Add `mendeley_rename_folder` success-payload tests in `tests/test_server.py`

### Implementation for User Story 4

- [X] T025 [US4] Implement `get_folder(...)` and `rename_folder(...)` stable-payload flow in `src/mendeley_mcp/client.py`
- [X] T026 [US4] Implement the `mendeley_rename_folder` MCP tool success path in `src/mendeley_mcp/server.py`
- [X] T027 [US4] Add `mendeley_rename_folder` to the tool table and examples in `README.md`

**Checkpoint**: User Story 4 should rename folders successfully and return the stable folder payload.

---

## Phase 8: User Story 5 - Remove a folder (Priority: P5)

**Goal**: Let users delete an existing folder and receive a deterministic confirmation payload without adding a local non-empty-folder guard.

**Independent Test**: Call `mendeley_delete_folder` with a valid `folder_id` and confirm the response is `{"id": ..., "status": "deleted"}`.

### Tests for User Story 5

- [X] T028 [P] [US5] Add `delete_folder` success tests in `tests/test_client.py`
- [X] T029 [P] [US5] Add `mendeley_delete_folder` confirmation-payload tests in `tests/test_server.py`

### Implementation for User Story 5

- [X] T030 [US5] Implement `delete_folder(...)` deterministic confirmation in `src/mendeley_mcp/client.py`
- [X] T031 [US5] Implement the `mendeley_delete_folder` MCP tool success path in `src/mendeley_mcp/server.py`
- [X] T032 [US5] Add `mendeley_delete_folder` usage examples and delete-semantics notes in `README.md`

**Checkpoint**: User Story 5 should delete folders successfully and return the deterministic confirmation payload.

---

## Phase 9: Polish & Cross-Cutting Concerns (Expanded Scope)

**Purpose**: Validate the complete folder-management surface after rename and delete are included.

- [X] T033 Run targeted `pytest` for rename/delete paths in `tests/test_client.py` and `tests/test_server.py`
- [X] T034 Run full validation for the expanded folder-management surface with `pytest`, `ruff check src tests`, and `mypy src/mendeley_mcp`
- [X] T035 Validate rename/delete smoke-test steps in `specs/001-create-folder/quickstart.md` and contract examples in `specs/001-create-folder/contracts/folder-management.md` against `README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup**: No dependencies.
- **Phase 2: Foundational**: Depends on Phase 1 and blocks all user-story work.
- **Phase 3: US1**: Depends on Phase 2.
- **Phase 4: US2**: Depends on Phase 2.
- **Phase 5: US3**: Depends on US1 and US2 because it hardens the baseline write flows and shared error handling.
- **Phase 6: Initial Slice Polish**: Depends on US1, US2, and US3.
- **Phase 7: US4**: Depends on Phase 2 and reuses the stable folder payload contract established in US1.
- **Phase 8: US5**: Depends on Phase 2 and reuses the shared validation/error helpers from earlier phases.
- **Phase 9: Expanded Scope Polish**: Depends on all implemented stories being complete.

### User Story Dependencies

- **US1 (P1)**: Can start immediately after Phase 2 and is the recommended MVP.
- **US2 (P2)**: Can start immediately after Phase 2 and is independently testable using an existing folder/document pair.
- **US3 (P3)**: Depends on the baseline implementations from US1 and US2 so failure behavior can be hardened without guessing the happy path.
- **US4 (P4)**: Depends on Phase 2 and the stable folder payload shape already established for folder creation.
- **US5 (P5)**: Depends on Phase 2 and benefits from the shared validation and error response conventions used by the other write tools.

### Within Each User Story

- Story tests should be written before the corresponding implementation tasks.
- Client-layer work should land before the MCP tool wrapper that depends on it.
- README updates should follow the implemented behavior, not precede it.

### Parallel Opportunities

- `T001` and `T002` can run in parallel.
- `T003` and `T004` can run in parallel.
- Within US1, `T005` and `T006` can run in parallel.
- Within US2, `T010` and `T011` can run in parallel.
- Within US3, `T015` and `T016` can run in parallel.
- Within US4, `T023` and `T024` can run in parallel.
- Within US5, `T028` and `T029` can run in parallel.
- After Phase 2, US1 and US2 can be developed in parallel by different contributors because they converge only in shared files during merge/integration.

---

## Parallel Example: User Story 1

```bash
# Launch US1 test work in parallel:
Task: "T005 [US1] Add create_folder success tests in tests/test_client.py"
Task: "T006 [US1] Add mendeley_create_folder success-payload tests in tests/test_server.py"
```

## Parallel Example: User Story 2

```bash
# Launch US2 test work in parallel:
Task: "T010 [US2] Add add_document_to_folder success tests in tests/test_client.py"
Task: "T011 [US2] Add mendeley_add_document_to_folder success-payload tests in tests/test_server.py"
```

## Parallel Example: User Story 4

```bash
# Launch US4 test work in parallel:
Task: "T023 [US4] Add rename_folder success tests in tests/test_client.py"
Task: "T024 [US4] Add mendeley_rename_folder success-payload tests in tests/test_server.py"
```

## Parallel Example: User Story 5

```bash
# Launch US5 test work in parallel:
Task: "T028 [US5] Add delete_folder success tests in tests/test_client.py"
Task: "T029 [US5] Add mendeley_delete_folder confirmation-payload tests in tests/test_server.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1.
2. Complete Phase 2.
3. Complete Phase 3 (US1).
4. Validate folder creation independently before expanding scope.

### Incremental Delivery

1. Deliver US1 for folder creation.
2. Deliver US2 for folder assignment.
3. Deliver US3 to harden validation and failure behavior.
4. Deliver US4 for folder rename.
5. Deliver US5 for folder delete.
6. Finish with the Phase 9 validation and smoke checks.

### Parallel Team Strategy

1. One contributor completes Phase 1 and Phase 2.
2. After Phase 2:
   - Contributor A implements US1.
   - Contributor B implements US2.
3. Merge both lines of work before implementing US3.
4. Implement US4 and US5 with coordination because both touch `src/mendeley_mcp/client.py`, `src/mendeley_mcp/server.py`, `tests/test_client.py`, `tests/test_server.py`, and `README.md`.
5. Run Phase 6 and Phase 9 as the integration passes.

---

## Notes

- Task identifiers preserve the required `Txxx` checklist structure; completed work is shown as `[X]` in this tracked copy.
- `[P]` markers are used only for tasks that can be executed without file conflicts.
- US3 intentionally follows US1 and US2 because its scope is to harden the existing tool surfaces.
- The recommended MVP scope is **US1 only**.
