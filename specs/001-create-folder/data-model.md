# Data Model: Folder Management

## Folder

Represents a user-visible folder returned by the feature after successful creation or rename.

### Fields

| Field | Type | Required | Notes |
|------|------|----------|-------|
| `id` | string | Yes | Server-assigned folder identifier |
| `name` | string | Yes | Folder name as accepted by the upstream API |
| `parent_id` | string \| null | No | Present for nested folders |
| `created` | string \| null | No | ISO 8601 creation timestamp from upstream |
| `group_id` | string \| null | No | Upstream may provide it, but it is not part of the minimum stable MCP contract for this slice |

### Validation Rules

- `name` must not be blank after trimming for create and rename requests.
- Name uniqueness within the folder container is enforced upstream, not by local validation.
- Maximum length and Unicode support are upstream constraints, not additional local validation rules for this slice.

### Relationships

- A folder may have zero or one parent folder.
- A folder belongs either to the personal library root or to a group-scoped library context.
- A folder can contain many document assignments.
- A folder can contain descendant folders, whose deletion behavior is controlled upstream.

## Folder Creation Request

Represents the user input needed to create a folder.

### Fields

| Field | Type | Required | Notes |
|------|------|----------|-------|
| `name` | string | Yes | Trimmed for blank validation, then forwarded |
| `parent_id` | string \| null | No | Targets a parent folder for nesting |
| `group_id` | string \| null | No | Targets a group-scoped container |

### Validation Rules

- `name` must contain at least one non-whitespace character.
- `parent_id` and `group_id` are optional passthrough values.
- Invalid ownership or incompatible parent/group combinations are surfaced from the upstream API.

### State Transition

`requested` -> `locally_rejected` | `api_rejected` | `created`

## Folder Rename Request

Represents the user input needed to rename an existing folder.

### Fields

| Field | Type | Required | Notes |
|------|------|----------|-------|
| `folder_id` | string | Yes | Existing target folder identifier |
| `name` | string | Yes | Replacement folder name |

### Validation Rules

- `folder_id` must not be blank after trimming.
- `name` must contain at least one non-whitespace character.
- Folder existence, access, and name conflicts are enforced upstream.

### State Transition

`requested` -> `locally_rejected` | `api_rejected` | `renamed`

## Folder Deletion Result

Represents the deterministic confirmation returned after a successful folder deletion.

### Fields

| Field | Type | Required | Notes |
|------|------|----------|-------|
| `id` | string | Yes | Identifier of the deleted folder |
| `status` | string | Yes | Stable success value: `deleted` |

### Validation Rules

- `id` must be derived from a non-blank `folder_id` request input.
- No additional local guard is added for folders with documents or descendants.

### State Transition

`requested` -> `locally_rejected` | `api_rejected` | `deleted`

## Document Reference

Represents the minimal document identity needed for folder assignment.

### Fields

| Field | Type | Required | Notes |
|------|------|----------|-------|
| `document_id` | string | Yes | Existing Mendeley document identifier |

### Validation Rules

- `document_id` must not be blank after trimming.
- Document existence and permissions are enforced upstream.

## Folder Assignment

Represents the relationship between an existing folder and an existing document.

### Fields

| Field | Type | Required | Notes |
|------|------|----------|-------|
| `folder_id` | string | Yes | Existing target folder identifier |
| `document_id` | string | Yes | Existing target document identifier |
| `status` | string | Yes | Stable success value: `added` |

### Validation Rules

- `folder_id` must not be blank after trimming.
- `document_id` must not be blank after trimming.
- If the document is already associated with the folder, the assignment is rejected as a duplicate before the write call.

### State Transition

`requested` -> `locally_rejected` | `duplicate_rejected` | `api_rejected` | `added`

## Library Context

Represents the container in which folder operations occur.

### Fields

| Field | Type | Required | Notes |
|------|------|----------|-------|
| `scope` | `personal` \| `group` | Yes | Derived from the presence of `group_id` |
| `group_id` | string \| null | No | Set only for group-scoped folder creation |

### Rules

- Personal-library folders have no `group_id`.
- Group-library folders require a valid `group_id` and upstream membership permissions.
- Parent-child relationships must stay inside the same valid container.
- Deleting a folder follows upstream semantics for descendant cascading and document preservation outside the removed folder container.
