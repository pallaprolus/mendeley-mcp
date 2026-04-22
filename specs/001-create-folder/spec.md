# Feature Specification: Folder Management

**Feature Branch**: `001-create-folder`  
**Created**: 2026-04-22  
**Status**: Draft  
**Input**: User description: "FEATURE_SPEC_CREATE_FOLDER_AND_ADD_DOCUMENT_TO_FOLDER.md"

## Clarifications

### Session 2026-04-22

- Q: When a user tries to add a document to a folder that already contains that document, what should happen? → A: Return a clear "already in folder" error.
- Q: What should a successful folder rename return? → A: A stable folder payload with `id`, `name`, `parent_id`, and `created`.
- Q: What should a successful folder delete return? → A: A deterministic confirmation payload `{id, status: "deleted"}`.
- Q: Should blank rename/delete inputs continue to be rejected locally? → A: Yes. Blank and whitespace-only inputs remain locally validated.
- Q: Should folder deletion add a local guard for non-empty folders? → A: No. Follow upstream semantics without an extra local non-empty guard.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a new folder (Priority: P1)

A researcher wants to create a new folder so references can be organized into meaningful collections without leaving the current workflow.

**Why this priority**: Folder creation is the foundational organization action. Without it, the user cannot build the structure needed for later classification work.

**Independent Test**: Can be fully tested by requesting a new folder with a valid name and confirming that the system returns a created folder identity and created time.

**Acceptance Scenarios**:

1. **Given** a user with access to a personal library, **When** they request a new folder with a valid name, **Then** the system creates the folder and returns a confirmation that identifies it.
2. **Given** a user with access to an existing parent folder, **When** they request a new child folder under that parent, **Then** the system creates the child folder under the requested parent.
3. **Given** a user with access to a shared library context, **When** they request a new folder inside that shared context, **Then** the system creates the folder in that shared context.

---

### User Story 2 - Place an existing document into a folder (Priority: P2)

A researcher wants to add an existing saved document to a chosen folder so the document can be classified without recreating it or losing access to it elsewhere in the library.

**Why this priority**: Once folders exist, the next most valuable action is placing existing material into them. This turns folders from static containers into usable organization tools.

**Independent Test**: Can be fully tested by selecting an existing document and an existing folder, requesting the association, and confirming that the system reports the document was added to that folder.

**Acceptance Scenarios**:

1. **Given** a user with access to an existing folder and an existing saved document, **When** they request to place the document into that folder, **Then** the system adds the document to the folder and returns a success confirmation.
2. **Given** a document that already exists in the user's library, **When** it is placed into a folder, **Then** the document remains available through the general library view as well as through the folder.

---

### User Story 3 - Receive clear validation and failure feedback (Priority: P3)

A researcher wants invalid requests and rejected actions to fail clearly so they can correct the input or access issue without guessing what happened.

**Why this priority**: Clear failures reduce repeated attempts, prevent silent data mistakes, and make the organization workflow reliable enough to automate confidently.

**Independent Test**: Can be fully tested by submitting blank values, inaccessible references, or incompatible folder context information and confirming that the system returns an explicit failure instead of a misleading success response.

**Acceptance Scenarios**:

1. **Given** a request with a blank folder name or blank resource reference, **When** the user submits it, **Then** the system rejects the request before attempting the write action.
2. **Given** a request that targets a missing, inaccessible, or incompatible folder context, **When** the user submits it, **Then** the system returns a clear error and no false success confirmation.
3. **Given** a request to place a document into a folder that already contains that document, **When** the user submits it, **Then** the system returns a clear duplicate-assignment error.

---

### User Story 4 - Rename an existing folder (Priority: P4)

A researcher wants to rename an existing folder so organizational labels can be corrected without rebuilding the folder hierarchy or re-adding the folder's contents.

**Why this priority**: Renaming is part of the folder lifecycle, but it becomes valuable only after folders already exist and are actively used.

**Independent Test**: Can be fully tested by renaming an existing accessible folder with a valid new name and confirming that the response returns the same folder identity with the updated name plus the stable `parent_id` and `created` fields.

**Acceptance Scenarios**:

1. **Given** an accessible existing folder and a valid non-empty new name, **When** the user requests a rename, **Then** the system updates the folder name and returns the stable folder payload.
2. **Given** a nested folder, **When** the user renames it, **Then** the returned payload preserves the folder's existing `parent_id`.
3. **Given** an accessible folder in a shared library context, **When** the user renames it, **Then** the system returns the renamed folder payload without requiring the user to rebuild that folder.

---

### User Story 5 - Remove a folder (Priority: P5)

A researcher wants to remove an obsolete folder so outdated organizational structures can be cleared from the library when they are no longer useful.

**Why this priority**: Folder deletion is cleanup work that matters after the core creation, assignment, and validation flows are already dependable.

**Independent Test**: Can be fully tested by deleting an existing accessible folder and confirming that the system returns a deterministic deletion confirmation identifying the removed folder.

**Acceptance Scenarios**:

1. **Given** an accessible existing folder, **When** the user requests deletion, **Then** the system returns a deletion confirmation for that folder.
2. **Given** a folder that contains documents or descendant folders, **When** the user requests deletion, **Then** the system forwards the deletion request without inventing an extra local "folder not empty" rejection.
3. **Given** an accessible folder in a shared library context, **When** the user requests deletion, **Then** the system surfaces the upstream success or failure result explicitly.

---

### Edge Cases

- A folder name contains only whitespace.
- A document reference or folder reference contains only whitespace.
- A requested parent folder does not belong to the same shared context as the new folder request.
- A target folder or target document no longer exists or is not accessible to the user.
- A document is already associated with the requested folder.
- A folder rename request provides a blank folder identifier or a blank new folder name.
- A folder rename request conflicts with an existing folder name in the same container or is otherwise rejected upstream.
- A folder delete request provides a blank folder identifier.
- A folder delete request targets a folder with documents and/or descendants, and the local layer must not invent a preflight emptiness rejection.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow a user to create a top-level folder by providing a non-empty folder name.
- **FR-002**: The system MUST allow a user to create a child folder when they provide a valid parent folder reference they can access.
- **FR-003**: The system MUST allow a user to create a folder within a shared library context when they provide a valid shared context reference they can access.
- **FR-004**: The system MUST reject blank or whitespace-only folder names before attempting to create a folder.
- **FR-005**: The system MUST allow a user to place an existing document into an existing folder when both references are provided and accessible.
- **FR-006**: The system MUST preserve the document's availability in the general library after the document is placed into a folder.
- **FR-007**: The system MUST reject blank or whitespace-only folder references and document references before attempting the folder assignment.
- **FR-008**: The system MUST return deterministic success confirmations for completed folder creation, rename, deletion, and folder-assignment actions, including the relevant resource identifiers.
- **FR-009**: The system MUST reject an attempt to place a document into a folder when that document is already associated with the same folder, and it MUST return a clear duplicate-assignment error.
- **FR-010**: The system MUST surface access, existence, duplicate-assignment, context-mismatch, and upstream conflict failures as explicit errors.
- **FR-011**: The system MUST allow a user to rename an existing folder when they provide a valid folder reference they can access and a non-empty replacement name.
- **FR-012**: The system MUST reject blank or whitespace-only folder references and replacement names before attempting a folder rename.
- **FR-013**: The system MUST return a deterministic folder-rename payload containing `id`, `name`, `parent_id`, and `created`.
- **FR-014**: The system MUST allow a user to remove an existing folder when they provide a valid folder reference they can access.
- **FR-015**: The system MUST reject blank or whitespace-only folder references before attempting folder deletion.
- **FR-016**: The system MUST return a deterministic folder-deletion payload containing `id` and `status`.
- **FR-017**: The system MUST NOT add a local pre-delete guard for non-empty folders or descendant folders; valid delete requests MUST be forwarded to the upstream folder API and reflect its result.
- **FR-018**: The system MUST NOT imply that deleting a folder also removed the underlying documents from the user's accessible library surface when the upstream API preserves those documents outside the removed folder container.
- **FR-019**: The system MUST limit this slice to folder creation, folder renaming, folder deletion, and folder assignment; folder moving and document removal from folders remain out of scope.

### Key Entities *(include if feature involves data)*

- **Folder**: A user-visible container for organizing references, identified uniquely and optionally linked to a parent folder or shared library context.
- **Folder Rename Request**: A user-requested folder identifier plus a new non-empty name, expected to return the stable folder payload on success.
- **Folder Deletion Result**: A deterministic confirmation that a specific folder identifier was deleted successfully.
- **Document**: A saved reference that remains part of the user's library and may also belong to one or more folders.
- **Folder Assignment**: A user-requested relationship that links an existing document to an existing folder and returns an explicit success or failure outcome.
- **Library Context**: The personal or shared space in which a folder is created, renamed, or deleted and whose access rules determine whether the action is allowed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing, 100% of valid folder-creation requests result in a new identifiable folder and a success confirmation in a single interaction.
- **SC-002**: In acceptance testing, 100% of valid folder-assignment requests result in an explicit confirmation that identifies both the folder and the document involved.
- **SC-003**: In validation testing, 100% of blank-name and blank-reference cases for folder creation, folder rename, folder deletion, and folder assignment are rejected before any write is attempted.
- **SC-004**: In acceptance testing, users can place an existing saved document into a target folder without losing access to that document from the general library view.
- **SC-005**: In acceptance testing, 100% of valid folder-rename requests return the stable folder payload with the updated name in a single interaction.
- **SC-006**: In acceptance testing, 100% of valid folder-delete requests return an explicit deletion confirmation identifying the deleted folder in a single interaction.

## Assumptions

- Users are already authenticated and allowed to act in the relevant personal or shared library context before invoking these capabilities.
- Users can obtain existing folder and document references from capabilities that already list folders and documents.
- Shared-library permissions and membership rules are enforced by the underlying library service and should be reflected back to the user when they block an action.
- Upstream folder-deletion semantics govern descendant-folder cascading and document preservation in the broader library, and this slice should not add a separate local emptiness check ahead of delete.
- This slice does not include moving folders or combining document creation with immediate folder placement.
