# Mendeley MCP Server Docker Image
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Mendeley MCP Server"
LABEL org.opencontainers.image.description="MCP server for Mendeley reference manager"
LABEL org.opencontainers.image.source="https://github.com/pallaprolus/mendeley-mcp"
LABEL org.opencontainers.image.licenses="MIT"

# Install the package from PyPI
RUN pip install --no-cache-dir mendeley-mcp

# Environment variables for credentials (must be provided at runtime)
# MENDELEY_CLIENT_ID - Your Mendeley app client ID
# MENDELEY_CLIENT_SECRET - Your Mendeley app client secret
# MENDELEY_REFRESH_TOKEN - OAuth refresh token (get via mendeley-auth login)

# Run the MCP server
ENTRYPOINT ["mendeley-mcp"]
