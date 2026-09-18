# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-09-18 — Tags and keywords on update

### Added
- `mendeley_update_document` accepts `tags` and `keywords`, so a document can be
  tagged through the server, for example during a literature review. A supplied
  list replaces the existing one. Search, list, and update results now include
  `tags` and `keywords`. Requested by [@HasiVS](https://github.com/HasiVS) in
  [#12](https://github.com/pallaprolus/mendeley-mcp/issues/12); verified live
  against the Mendeley API, which stores tags as an unordered set.

### Fixed
- The README now documents the two MCP resources the server has always exposed,
  `mendeley://library/recent` and `mendeley://library/folders`, and lists
  contributors.

## [0.5.2] - 2026-09-15 — Token persistence and Intel Mac installs

### Changed
- Saved logins now persist refreshed access and refresh tokens back to their
  original keyring or file storage, so a new server process starts with a
  valid token instead of a 401-and-refresh round trip. Environment-provided
  credentials remain in memory only. Verified live against the Mendeley API,
  which currently returns the same refresh token on refresh.
- Concurrent 401s within one server share a single refresh. The full token
  response is validated before the live credentials change, and a storage
  failure keeps the usable live tokens and logs a warning without secrets.

### Fixed
- Installation on Intel Macs. `cryptography` (via the MCP SDK's `pyjwt[crypto]`)
  dropped macOS x86_64 wheels at 49.0, so installs there tried to compile it from
  source and failed without Rust. The package now pins `cryptography<49` on
  macOS x86_64 only; other platforms are unaffected.

## [0.5.1] - 2026-09-07 — Structured-content compatibility

### Fixed
- Include extracted PDF text in the structured result of
  `mendeley_get_document_text` as well as its existing text block. This keeps
  papers readable in clients that expose only structured content to the model
  (issue #11). Both representations use the same text truncation limit.
  Structured results also include the explanatory message on success and
  failure paths, including missing files, scanned PDFs, and authentication errors.
  Thanks to @Storkholm for reporting and isolating the client behavior.

## [0.5.0] - 2026-08-31 — MCP Python SDK v2

### Changed
- **BREAKING:** Migrated to MCP Python SDK v2. The requirement is now
  `mcp>=2.0.0,<3.0.0`, and the v1 line is no longer supported — an environment
  shared with another package pinned to `mcp<2` will need that conflict
  resolved. Internally `FastMCP` becomes `MCPServer`, tool results use the
  snake_case `structured_content`/`is_error` fields, and resource URIs are
  plain strings. Migration contributed by
  [@roych98](https://github.com/roych98) in
  [#8](https://github.com/pallaprolus/mendeley-mcp/pull/8).

  No change is expected for users: wire compatibility with v1 was verified
  before merge by driving the server over stdio with raw JSON-RPC. Tool
  registration, the embedded PDF resource, and the extracted-text blocks are
  byte-identical between mcp 1.29.1 and 2.1.1.
- Dropped the direct `pydantic` dependency, which existed only for the v1
  `AnyUrl` resource URI. It remains an indirect dependency of the SDK.

### Fixed
- `serverInfo` now reports this package's version. The v1 SDK defaulted the
  field to the *SDK's* version, so a client quoting it named the wrong thing;
  v2 defaults it to empty. It is now read from installed package metadata and
  cannot drift from `pyproject.toml`, as `__init__.py` had — it was still
  declaring 0.3.0 at 0.4.1.

## [0.4.1] - 2026-08-24 — Fix installs broken by MCP SDK 2.x

### Fixed
- Constrained the MCP SDK dependency to `mcp>=1.19.0,<2`. MCP Python SDK 2.0.0
  removed `mcp.server.fastmcp`, so every fresh install of 0.4.0 resolved the new
  major and failed at import with `ModuleNotFoundError: No module named
  'mcp.server.fastmcp'`. Reported in
  [#7](https://github.com/pallaprolus/mendeley-mcp/issues/7) and fixed in
  [#9](https://github.com/pallaprolus/mendeley-mcp/pull/9) by
  [@roych98](https://github.com/roych98), who diagnosed the cause and supplied
  the fix. Migrating to the v2 API is tracked separately in
  [#8](https://github.com/pallaprolus/mendeley-mcp/pull/8).
- The Docker image now installs the package from the checked-out source instead
  of from PyPI, so an image always contains the commit it was built from.
  Previously the image build and the PyPI upload both fired on a version tag and
  raced, so an image could be tagged with a new version while containing the
  previous one.

## [0.4.0] - 2026-06-14

### Added
- `mendeley_get_document_text` — extract and return the full text of a
  document's attached PDF as a text block, so the model can actually read the
  paper. `mendeley_get_file_content` returns the PDF as an embedded binary
  resource, which most MCP clients (including Claude Code) hand to the model as
  undecoded base64 rather than readable content; this tool extracts the text
  server-side instead. Born-digital PDFs only — scanned/image-only PDFs have no
  text layer and are reported as such. Output is capped at 200,000 characters,
  adjustable via the `MENDELEY_MCP_MAX_TEXT_CHARS` environment variable.
- CI workflow running ruff, mypy, and the test suite on Python 3.10–3.12 for
  every push to main and every pull request.
- Security policy (`SECURITY.md`) with private vulnerability reporting via
  GitHub security advisories.

## [0.3.0] - 2026-06-12

### Added
- `mendeley_get_annotations` — the user's PDF highlights and sticky notes on a
  document, with note text, color, and page numbers.
- `mendeley_update_document` — update bibliographic fields on an existing
  document; only supplied fields change.
- `mendeley_delete_document` — permanently delete a document; the tool
  description instructs the model to confirm with the user first.
- `mendeley_remove_document_from_folder` — completes the move-between-folders
  loop started by `mendeley_add_document_to_folder`.
- `mendeley_export_bibtex` — export one document or a whole folder as BibTeX,
  generated by Mendeley itself rather than templated locally.

### Fixed
- File download never worked against the live API: Mendeley returns the
  download URL via a `303 See Other` redirect, which the client treated as an
  error. Found by live testing.
- Credential loading locked out users whose login predated 0.2.0: those logins
  never stored the client secret in the keyring, and 0.2.0 refused to load
  without it. Tokens now load and work until they expire.

## [0.2.0] - 2026-06-12

### Added
- Folder management tools: `mendeley_create_folder` (with nesting and group
  support), `mendeley_rename_folder`, `mendeley_delete_folder`, and
  `mendeley_add_document_to_folder`. Adapted from
  [#2](https://github.com/pallaprolus/mendeley-mcp/pull/2) by Alexandre Castro
  ([@im-alexandre](https://github.com/im-alexandre)).
- `mendeley_get_file_content` — download a document's attached PDF as an
  embedded MCP resource, capped at 10 MB (override with
  `MENDELEY_MCP_MAX_FILE_BYTES`).
- Title and description metadata on all tools, and a Tool Reference section in
  the README.
- Server and client test suites.

### Changed
- Mendeley API responses are shape-validated before use; token responses are
  validated during auth.
- Minimum `mcp` dependency raised to 1.19.0 — earlier SDK versions mangle a
  `CallToolResult` returned from a tool, which the file download relies on.

## [0.1.3] - 2026-01-04

### Added
- Automatic PyPI publishing on version tags.

### Fixed
- Logo URL on PyPI.

## [0.1.2] - 2026-01-03

### Added
- Docker support and a published container image.

## [0.1.1] - 2026-01-03

### Fixed
- Keyring credential storage.

### Changed
- Improved documentation.

## [0.1.0] - 2026-01-03

### Added
- Initial release: search the personal library and the global Mendeley
  catalog, get document details, list documents and folders, DOI lookup, add
  documents, citation formatting, and an OAuth CLI (`mendeley-auth`) with
  keyring-backed credential storage.

[Unreleased]: https://github.com/pallaprolus/mendeley-mcp/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/pallaprolus/mendeley-mcp/compare/v0.5.2...v0.6.0
[0.5.2]: https://github.com/pallaprolus/mendeley-mcp/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/pallaprolus/mendeley-mcp/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/pallaprolus/mendeley-mcp/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/pallaprolus/mendeley-mcp/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/pallaprolus/mendeley-mcp/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/pallaprolus/mendeley-mcp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/pallaprolus/mendeley-mcp/releases/tag/v0.2.0
[0.1.3]: https://pypi.org/project/mendeley-mcp/0.1.3/
[0.1.2]: https://pypi.org/project/mendeley-mcp/0.1.2/
[0.1.1]: https://pypi.org/project/mendeley-mcp/0.1.1/
[0.1.0]: https://pypi.org/project/mendeley-mcp/0.1.0/
