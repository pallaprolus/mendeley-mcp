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
- **Browse folders** - Navigate your collection structure
- **Get full metadata** - Retrieve complete document details including abstracts
- **Search global catalog** - Access Mendeley's 100M+ paper database
- **DOI lookup** - Find papers by their DOI
- **Add documents** - Create new entries in your library

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

## Example Usage

Once configured, you can ask Claude things like:

- "Search my Mendeley library for papers about transformer architectures"
- "What papers do I have in my 'Machine Learning' folder?"
- "Find the paper with DOI 10.1038/nature14539 and summarize it"
- "Search the Mendeley catalog for recent papers on protein folding"
- "Add this paper to my library: [title, authors, etc.]"

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
