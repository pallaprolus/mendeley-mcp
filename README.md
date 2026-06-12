<p align="center">
  <img src="https://raw.githubusercontent.com/pallaprolus/mendeley-mcp/main/mendeley-mcp.png" alt="Mendeley MCP Logo" width="200">
</p>

# Mendeley MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that connects your Mendeley reference library to LLM applications like Claude Desktop, Cursor, and other MCP-compatible clients.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/mendeley-mcp.svg)](https://pypi.org/project/mendeley-mcp/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/mendeley-mcp?period=total&units=international_system&left_color=black&right_color=green&left_text=downloads)](https://pepy.tech/project/mendeley-mcp)
[![Docker](https://img.shields.io/badge/docker-available-blue.svg)](https://github.com/pallaprolus/mendeley-mcp/pkgs/container/mendeley-mcp)

<a href="https://glama.ai/mcp/servers/@pallaprolus/mendeley-mcp">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@pallaprolus/mendeley-mcp/badge" alt="Mendeley MCP server on Glama" />
</a>

## Features

- **Search your library** - Find papers by title, author, abstract, or notes
- **Manage folders** - Browse, create, rename, delete, and nest collections
- **Get full metadata** - Retrieve complete document details including abstracts
- **Search global catalog** - Access Mendeley's 100M+ paper database
- **DOI lookup** - Find papers by their DOI
- **Manage documents** - Add, update, delete, and organize entries across folders
- **Read your annotations** - Surface the highlights and notes you made on PDFs
- **Export BibTeX** - Generate citation entries for a document or a whole folder
- **Download attached files** - Retrieve document files when Mendeley exposes them

## Prerequisites

1. **Mendeley Account** - Sign up at [mendeley.com](https://www.mendeley.com/) (uses Elsevier authentication)
2. **Mendeley API App** - Register at [dev.mendeley.com/myapps.html](https://dev.mendeley.com/myapps.html)
   - Sign in with your Elsevier credentials
   - Click "Register a new app"
   - Set redirect URL to `http://localhost:8585/callback`
   - Select "Authorization code" flow (not Legacy)
   - Note your **Client ID** and **Client Secret**

## Installation

### Using pip

```bash
pip install mendeley-mcp
```

### Using uv (recommended)

```bash
uv tool install mendeley-mcp
```

### Using Docker

```bash
docker run -it \
  -e MENDELEY_CLIENT_ID="your-client-id" \
  -e MENDELEY_CLIENT_SECRET="your-client-secret" \
  -e MENDELEY_REFRESH_TOKEN="your-refresh-token" \
  ghcr.io/pallaprolus/mendeley-mcp
```

Or build locally:
```bash
git clone https://github.com/pallaprolus/mendeley-mcp.git
cd mendeley-mcp
docker build -t mendeley-mcp .
```

### From source

```bash
git clone https://github.com/pallaprolus/mendeley-mcp.git
cd mendeley-mcp
pip install -e .
```

## Quick Start

### 1. Authenticate with Mendeley

Run the authentication wizard:

```bash
mendeley-auth login
```

This will:
1. Prompt for your Client ID and Client Secret
2. Open your browser to authorize the app
3. Save your credentials securely in your system keyring

### 2. Add to Claude Desktop

Edit your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mendeley": {
      "command": "mendeley-mcp"
    }
  }
}
```

If installed with uv:
```json
{
  "mcpServers": {
    "mendeley": {
      "command": "uvx",
      "args": ["mendeley-mcp"]
    }
  }
}
```

### 3. Restart Claude Desktop

The Mendeley tools should now be available in Claude.

## Available Tools

| Tool | Description |
|------|-------------|
| `mendeley_search_library` | Search documents in your library |
| `mendeley_get_document` | Get full details of a specific document |
| `mendeley_list_documents` | List documents, optionally filtered by folder |
| `mendeley_list_folders` | List all folders/collections |
| `mendeley_search_catalog` | Search Mendeley's global paper database |
| `mendeley_get_by_doi` | Look up a paper by DOI |
| `mendeley_add_document` | Add a new document to your library |
| `mendeley_update_document` | Update bibliographic fields on an existing document |
| `mendeley_delete_document` | Permanently delete a document from your library |
| `mendeley_create_folder` | Create a folder in your library, optionally under a parent folder or group |
| `mendeley_rename_folder` | Rename an existing folder |
| `mendeley_delete_folder` | Delete an existing folder |
| `mendeley_add_document_to_folder` | Add an existing document to an existing folder |
| `mendeley_remove_document_from_folder` | Remove a document from a folder without deleting it |
| `mendeley_get_annotations` | Get your PDF highlights and notes on a document |
| `mendeley_export_bibtex` | Export a document or folder as BibTeX |
| `mendeley_get_file_content` | Download the first attached file for a library or catalog document |

## Tool Reference

### `mendeley_search_library`

Use this when the paper should already exist in the user's library.

- Searches title, authors, abstract, and notes
- Returns concise metadata, formatted citation text, and `has_pdf`
- Best first step before falling back to the catalog

### `mendeley_get_document`

Use this after you already know the library `document_id`.

- Returns fuller metadata than the search tool
- Includes identifiers, keywords, tags, timestamps, abstract, and PDF presence
- Best for inspection, summarization, and follow-up actions on a known document

### `mendeley_list_documents`

Use this to browse the library instead of searching by keyword.

- Can scope results to a specific `folder_id`
- Supports sorting by `last_modified`, `created`, or `title`
- Useful for reviewing recent additions or the contents of one collection

### `mendeley_list_folders`

Use this to understand the collection hierarchy before listing documents by folder.

- Returns folder IDs and names
- Includes `parent_id` to reconstruct nesting
- Useful when an LLM needs to navigate a library structure safely

### `mendeley_search_catalog`

Use this when the reference is not in the user's library or when you want broader discovery.

- Searches Mendeley's global catalog
- Returns `catalog_id`, summary metadata, and truncated abstract text
- Good fallback when `mendeley_search_library` does not find a match

### `mendeley_get_by_doi`

Use this when a DOI is known and you want a higher-confidence lookup than free-text search.

- Resolves the DOI in the Mendeley catalog
- Returns `catalog_id` plus richer catalog metadata
- Useful before `mendeley_add_document` or `mendeley_get_file_content`

### `mendeley_add_document`

Use this to create a library entry from metadata you already have.

- Creates a new Mendeley library record
- Accepts title, authors, year, source, abstract, and identifiers
- Does not upload a PDF by itself

### `mendeley_update_document`

Use this to fix or enrich an existing library entry.

- Updates only the fields you supply (title, type, authors, year, source, abstract, identifiers)
- Returns the document's state after the update
- Useful for correcting a wrong year, adding a missing abstract, or fixing identifiers

### `mendeley_delete_document`

Use this to permanently remove a document from the library.

- Destructive and not reversible through the API
- The tool description instructs the model to confirm with the user first

### `mendeley_remove_document_from_folder`

Use this to take a document out of a folder while keeping it in the library.

- Complements `mendeley_add_document_to_folder` — together they let you move documents between folders
- Does not delete the document itself

### `mendeley_get_annotations`

Use this to see what the user highlighted or noted in a paper's PDF.

- Returns the user's own annotations: highlights and sticky notes
- Includes note text, highlight color, and the page numbers involved
- The most direct signal of what the user found important in a paper

### `mendeley_export_bibtex`

Use this when the user needs citations in a real reference format.

- Provide `document_id` for one entry or `folder_id` for a whole collection
- BibTeX is generated by Mendeley itself, not templated locally
- Returns raw text ready to paste into a `.bib` file

### `mendeley_get_file_content`

Use this to try downloading the first file Mendeley exposes for a library document or catalog hit.

- Accepts either a library `document_id` or a `catalog_id`
- Returns structured metadata and an embedded PDF resource when available
- If no file exists, returns a clear no-file result instead of failing silently
- Catalog results often have no downloadable attachment for copyright or licensing reasons
- Files larger than 10 MB are reported but not embedded, to avoid flooding the client's context window (adjust with the `MENDELEY_MCP_MAX_FILE_BYTES` environment variable)

## Example Usage

Once configured, you can ask Claude things like:

- "Search my Mendeley library for papers about transformer architectures"
- "What papers do I have in my 'Machine Learning' folder?"
- "Find the paper with DOI 10.1038/nature14539 and summarize it"
- "Search the Mendeley catalog for recent papers on protein folding"
- "Add this paper to my library: [title, authors, etc.]"
- "Create a folder called 'Systematic Review 2026' in my Mendeley library"
- "Create a subfolder called 'Screening' under folder ID folder-123"
- "Create a folder called 'Weekly Reading' in group group-456"
- "Rename folder folder-123 to 'Included Studies'"
- "Delete folder folder-999 from my Mendeley library"
- "Add document doc-789 to folder folder-123"
- "Move document doc-789 from 'Screening' to 'Included Studies'"
- "Fix the year on doc-456 — it should be 2024, not 2023"
- "What did I highlight in the attention paper?"
- "Export my 'Lit Review' folder as BibTeX"
- "Download the PDF attached to the paper about protein folding"

For direct tool calls in an MCP client or inspector, the folder-management tools accept inputs like:

Create a root folder:

```json
{
  "name": "Systematic Review 2026"
}
```

Create a subfolder:

```json
{
  "name": "Screening",
  "parent_id": "folder-123"
}
```

Rename a folder:

```json
{
  "folder_id": "folder-123",
  "name": "Included Studies"
}
```

Delete a folder:

```json
{
  "folder_id": "folder-999"
}
```

Add a document to a folder:

```json
{
  "folder_id": "folder-123",
  "document_id": "doc-789"
}
```

### Folder Management Validation

- `mendeley_create_folder` requires a non-empty `name`. You can optionally provide `parent_id` for nested creation or `group_id` for a group-scoped folder.
- `mendeley_rename_folder` requires non-empty `folder_id` and `name`.
- `mendeley_delete_folder` requires a non-empty `folder_id`.
- `mendeley_add_document_to_folder` requires non-empty `folder_id` and `document_id`.
- Required string inputs are trimmed before the request is sent. Blank or whitespace-only required values return a JSON error response instead of attempting the write.
- Optional `parent_id` and `group_id` values are trimmed when provided and then forwarded upstream without additional local business rules.
- Rename and delete operations surface upstream missing-folder, access, or context errors as JSON error responses instead of false success payloads.

`mendeley_get_file_content` accepts either a library document ID or a `catalog_id`. Catalog
entries often do not have downloadable files, so a no-file result is expected in many cases.

## Configuration

### Environment Variables

If you prefer not to use `mendeley-auth login`, you can configure credentials via environment variables:

```bash
# Required
export MENDELEY_CLIENT_ID="your-client-id"
export MENDELEY_CLIENT_SECRET="your-client-secret"

# One of the following (refresh token recommended - access tokens expire quickly)
export MENDELEY_REFRESH_TOKEN="your-refresh-token"
# OR
export MENDELEY_ACCESS_TOKEN="your-access-token"
```

Or in your MCP config:

```json
{
  "mcpServers": {
    "mendeley": {
      "command": "mendeley-mcp",
      "env": {
        "MENDELEY_CLIENT_ID": "your-client-id",
        "MENDELEY_CLIENT_SECRET": "your-client-secret",
        "MENDELEY_REFRESH_TOKEN": "your-refresh-token"
      }
    }
  }
}
```

### Auth Commands

```bash
# Check authentication status
mendeley-auth status

# Show environment variables for manual config
mendeley-auth show-env

# Remove saved credentials
mendeley-auth logout
```

## Development

### Setup

```bash
git clone https://github.com/pallaprolus/mendeley-mcp.git
cd mendeley-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=mendeley_mcp

# Type checking
mypy src/mendeley_mcp

# Linting
ruff check src/
```

### Testing with MCP Inspector

```bash
# Install MCP inspector
npm install -g @modelcontextprotocol/inspector

# Run your server with inspector
npx @modelcontextprotocol/inspector mendeley-mcp
```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Claude Desktop │────▶│  mendeley-mcp    │────▶│   Mendeley API    │
│  (MCP Client)   │◀────│  (MCP Server)    │◀────│ api.mendeley.com  │
└─────────────────┘     └──────────────────┘     └───────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  Local Keyring   │
                        │  (credentials)   │
                        └──────────────────┘
```

**Important**: This server runs locally on your machine. Your credentials and data never pass through any third-party servers - all communication is directly between your computer and Mendeley's API.

**Credential Storage**: Your OAuth tokens and client secret are stored securely in your system's native keyring (macOS Keychain, Windows Credential Locker, or Linux Secret Service). Only the non-sensitive client ID is stored in `~/.config/mendeley-mcp/credentials.json`.

## Rate Limits

Mendeley API rate limits are per-user. If you hit rate limits:

- The server implements automatic token refresh
- Wait a few minutes and retry
- For heavy usage, consider spreading requests over time

## Troubleshooting

### "No credentials found"

Run `mendeley-auth login` to authenticate.

### "Token expired"

Your access token has expired. The server will attempt to refresh it automatically using your refresh token. If this fails, run `mendeley-auth login` again.

### "401 Unauthorized"

Your app may have been deauthorized. Re-authenticate with `mendeley-auth login`.

### Server not appearing in Claude

1. Check the config file path is correct for your OS
2. Ensure JSON is valid (no trailing commas)
3. Restart Claude Desktop completely
4. Check Claude's logs for errors

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file.

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Mendeley or Elsevier. Mendeley is a trademark of Elsevier B.V.

## Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [FastMCP](https://github.com/jlowin/fastmcp) Python framework
- [Mendeley API](https://dev.mendeley.com/) documentation
