# Feature Specification: Create Folder and Add Document to Folder

## Context

The repository already supports:

- listing folders with `mendeley_list_folders`
- listing documents, including filtering by `folder_id`, with `mendeley_list_documents`
- creating a library document with `mendeley_add_document`

What is still missing is the write path for:

1. creating a new folder
2. attaching an existing document to a folder

The official Mendeley API supports both operations, so these features should be implemented as first-class MCP tools instead of relying on manual API calls outside the server.

## Scope

This spec covers two new MCP features:

1. `mendeley_create_folder`
2. `mendeley_add_document_to_folder`

Out of scope for this slice:

- deleting folders
- moving folders
- removing documents from folders
- building a full folder tree helper
- combining document creation and folder assignment into one tool

## Current Code Touchpoints

- `src/mendeley_mcp/client.py`
- `src/mendeley_mcp/server.py`
- `tests/test_client.py`
- `README.md`

## Feature 1: Create Folder

### MCP Tool

`mendeley_create_folder`

### Goal

Create a folder in the user library, optionally under a parent folder or inside a group.

### Proposed Tool Arguments

- `name: str` required
- `parent_id: str | None = None` optional
- `group_id: str | None = None` optional

### Validation Rules

- `name` must be non-empty after trimming.
- `name` should be sent as provided after trim; no extra normalization should be invented in the server.
- `parent_id` is optional and means the new folder should be nested under an existing folder.
- `group_id` is optional and means the folder belongs to a group container instead of the personal library.
- If both `parent_id` and `group_id` are provided, the server should pass them through, but API failures must be surfaced clearly if the parent folder does not belong to that group context.

### API Contract

- HTTP method: `POST`
- Path: `/folders`
- `Accept: application/vnd.mendeley-folder.1+json`
- `Content-Type: application/vnd.mendeley-folder.1+json`

### Request Body

Minimum body:

```json
{
  "name": "My Folder"
}
```

Nested folder example:

```json
{
  "name": "Subfolder",
  "parent_id": "95342445-ab75-42ba-b98f-888bbe543c0f"
}
```

Group folder example:

```json
{
  "name": "Shared Reading List",
  "group_id": "9ab2887c-9b1c-38d7-a64a-3491306362a7"
}
```

### Response Shape

Return a JSON object shaped consistently with existing folder responses:

```json
{
  "id": "folder-uuid",
  "name": "My Folder",
  "parent_id": null,
  "created": "2024-07-02T13:27:52.000Z"
}
```

If the API returns extra fields such as `group_id`, they may be preserved if useful, but the minimum stable contract should be the four fields above.

### Client Implementation

Add a method in `MendeleyClient`:

```python
async def create_folder(
    self,
    name: str,
    parent_id: str | None = None,
    group_id: str | None = None,
) -> Folder:
```

Recommended behavior:

- build the payload from non-null fields only
- call `POST /folders`
- parse the response with `Folder.from_api(...)`

### Server Implementation

Add a new MCP tool in `server.py`:

```python
@mcp.tool()
async def mendeley_create_folder(
    name: str,
    parent_id: str | None = None,
    group_id: str | None = None,
) -> str:
```

The server should:

- validate blank names before hitting the API
- call `client.create_folder(...)`
- return JSON with `id`, `name`, `parent_id`, and `created`
- keep current error handling style by returning `{"error": "..."}`

### Acceptance Criteria

- A root folder can be created successfully.
- A nested folder can be created when `parent_id` is valid.
- A group folder can be created when `group_id` is valid.
- Blank `name` is rejected before the API call.
- Returned JSON is stable and easy for MCP clients to consume.

## Feature 2: Add Document to Folder

### MCP Tool

`mendeley_add_document_to_folder`

### Goal

Attach an existing document to an existing folder.

Important model rule from the Mendeley API: a folder is not an exclusive location. A document can appear in multiple folders and also remain accessible through the general `/documents` resource.

### Proposed Tool Arguments

- `folder_id: str` required
- `document_id: str` required

### Validation Rules

- `folder_id` must be non-empty.
- `document_id` must be non-empty.
- Local validation should only check presence and obvious blank values.
- Existence and permission errors should come from the Mendeley API and be surfaced clearly.

### API Contract

- HTTP method: `POST`
- Path: `/folders/{id}/documents`
- `Content-Type: application/vnd.mendeley-document.1+json`

### Request Body

```json
{
  "id": "document-uuid"
}
```

### Response Strategy

The Mendeley API documents a `201 Created` response but does not require a rich response body for this operation. For MCP usability, the server should return a stable confirmation object:

```json
{
  "folder_id": "folder-uuid",
  "document_id": "document-uuid",
  "status": "added"
}
```

This keeps the tool deterministic and avoids a second request unless the caller explicitly needs full document details.

### Client Implementation

Add a method in `MendeleyClient`:

```python
async def add_document_to_folder(
    self,
    folder_id: str,
    document_id: str,
) -> None:
```

Recommended behavior:

- call `POST /folders/{folder_id}/documents`
- send `{"id": document_id}` as JSON
- set `Content-Type: application/vnd.mendeley-document.1+json`
- treat any 2xx response as success

### Server Implementation

Add a new MCP tool in `server.py`:

```python
@mcp.tool()
async def mendeley_add_document_to_folder(
    folder_id: str,
    document_id: str,
) -> str:
```

The server should:

- validate blank IDs before the API call
- call `client.add_document_to_folder(...)`
- return the stable confirmation payload
- return `{"error": "..."}`
  when the API rejects the request

### Acceptance Criteria

- An existing document can be added to an existing folder.
- The tool returns a deterministic confirmation payload on success.
- Blank `folder_id` or `document_id` is rejected locally.
- API-side failures are surfaced with clear error text.

## Testing Requirements

### Client Tests

Extend `tests/test_client.py` with at least:

- success test for `create_folder`
- success test for `create_folder` with `parent_id`
- success test for `add_document_to_folder`
- failure-path test for each new client method

### Server Tests

Add a new `tests/test_server.py` with at least:

- success test for `mendeley_create_folder`
- blank-name validation test for `mendeley_create_folder`
- success test for `mendeley_add_document_to_folder`
- blank-id validation test for `mendeley_add_document_to_folder`
- error propagation test for both tools

## README Updates

Update the feature list and tool table in `README.md` to include:

- create folders
- add existing documents to folders

Also add example prompts such as:

- "Create a folder named 'Systematic Review 2026'"
- "Create a subfolder 'Screened In' under folder `<folder_id>`"
- "Add document `<document_id>` to folder `<folder_id>`"

## Non-Goals for This Change

These may be added later, but should not be bundled into this first slice:

- `mendeley_move_folder`
- `mendeley_delete_folder`
- `mendeley_remove_document_from_folder`
- automatic creation of a document and immediate insertion into a folder in one MCP call
- tree-building helpers such as `mendeley_list_folder_tree`

## References

- Mendeley API methods: <https://dev.mendeley.com/methods/>
- Mendeley core resources overview: <https://dev.mendeley.com/overview/core_resources.html>
- Mendeley core quick start guides: <https://dev.mendeley.com/code/core_quick_start_guides.html>
