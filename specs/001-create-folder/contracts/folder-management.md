# MCP Contract: Folder Management

## Interface Style

This repository exposes MCP tools that return serialized JSON strings. The folder-management tools follow the same convention as the existing server surface.

## Related Existing Surface

| Tool | Purpose | Success Shape |
|------|---------|---------------|
| `mendeley_list_folders` | Enumerate available folders | JSON array of `{id, name, parent_id}` objects |
| `mendeley_list_documents` | Enumerate library or folder documents | JSON array of simplified document objects |
| `mendeley_get_document` | Retrieve full document metadata | JSON object with detailed document metadata |
| `mendeley_add_document` | Create a new library document | JSON object describing the created document |

## Tool: `mendeley_create_folder`

### Request Arguments

| Argument | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Folder name |
| `parent_id` | string \| null | No | Parent folder identifier for nested creation |
| `group_id` | string \| null | No | Group identifier for group-scoped creation |

### Local Validation

- Reject blank or whitespace-only `name`.
- Forward non-null `parent_id` and `group_id` without adding new local business rules.

### Success Payload

```json
{
  "id": "folder-uuid",
  "name": "Systematic Review 2026",
  "parent_id": null,
  "created": "2024-07-02T13:27:52.000Z"
}
```

### Failure Payload

```json
{
  "error": "clear error message"
}
```

### Behavior Notes

- The tool returns the minimum stable folder contract even if the upstream API provides additional fields.
- Upstream ownership, access, and container-validation failures are surfaced as explicit errors.

## Tool: `mendeley_rename_folder`

### Request Arguments

| Argument | Type | Required | Description |
|------|------|----------|-------------|
| `folder_id` | string | Yes | Existing folder identifier |
| `name` | string | Yes | Replacement folder name |

### Local Validation

- Reject blank or whitespace-only `folder_id`.
- Reject blank or whitespace-only `name`.

### Success Payload

```json
{
  "id": "folder-uuid",
  "name": "Included Studies",
  "parent_id": "parent-folder-uuid",
  "created": "2024-07-02T13:27:52.000Z"
}
```

### Failure Payload

```json
{
  "error": "clear error message"
}
```

### Behavior Notes

- The tool returns the same stable folder contract as folder creation even though the upstream rename request succeeds with `204 No Content`.
- The public payload preserves `parent_id` and `created` instead of widening the MCP contract with additional upstream-only fields.
- Upstream missing-folder, access, and name-conflict failures are surfaced as explicit errors.

## Tool: `mendeley_delete_folder`

### Request Arguments

| Argument | Type | Required | Description |
|------|------|----------|-------------|
| `folder_id` | string | Yes | Existing folder identifier |

### Local Validation

- Reject blank or whitespace-only `folder_id`.
- Do not add a local pre-delete guard for folders that contain documents or descendants.

### Success Payload

```json
{
  "id": "folder-uuid",
  "status": "deleted"
}
```

### Failure Payload

```json
{
  "error": "clear error message"
}
```

### Behavior Notes

- Successful deletion returns the deterministic local confirmation payload even though the upstream delete request succeeds with `204 No Content`.
- The tool defers non-empty-folder behavior to the upstream API instead of rejecting it locally.
- Upstream folder deletion may remove descendant folders while leaving the underlying documents available through the broader library or group surface.

## Tool: `mendeley_add_document_to_folder`

### Request Arguments

| Argument | Type | Required | Description |
|------|------|----------|-------------|
| `folder_id` | string | Yes | Existing folder identifier |
| `document_id` | string | Yes | Existing document identifier |

### Local Validation

- Reject blank or whitespace-only `folder_id`.
- Reject blank or whitespace-only `document_id`.
- Reject duplicate folder membership before the write call and surface it as a duplicate-assignment error.

### Success Payload

```json
{
  "folder_id": "folder-uuid",
  "document_id": "document-uuid",
  "status": "added"
}
```

### Failure Payload

```json
{
  "error": "clear error message"
}
```

### Behavior Notes

- Duplicate assignment is not treated as idempotent success.
- Successful assignment does not trigger a follow-up metadata read.
- The document remains part of the general library surface after being placed into a folder.
